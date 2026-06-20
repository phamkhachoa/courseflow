from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.prompt_gateway import (
    PromptContext,
    PromptCostBudget,
    PromptGatewayRequest,
    PromptGatewayResult,
    PromptOutputPolicy,
    run_prompt_gateway,
)
from courseflow_ai_platform.registry import (
    RegistryValidationError,
    load_yaml,
    require_str,
)

PROMPT_GATEWAY_EVALUATE_SCOPE = "internal:ai-platform:prompt-gateway:evaluate"
PROMPT_GATEWAY_OPS_SCOPE = "internal:ai-platform:prompt-gateway:ops"
PROMPT_GATEWAY_ROUTE_SCOPES = {
    ("POST", "/v1/prompt-gateway/evaluate"): PROMPT_GATEWAY_EVALUATE_SCOPE,
    ("GET", "/v1/prompt-gateway/health"): PROMPT_GATEWAY_OPS_SCOPE,
    ("GET", "/v1/prompt-gateway/metrics"): PROMPT_GATEWAY_OPS_SCOPE,
}


class PromptGatewayServiceError(ValueError):
    """Raised when prompt gateway service input or policy is invalid."""


@dataclass(frozen=True, slots=True)
class PromptGatewayPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> PromptGatewayPrincipal:
        return cls(
            principal_id=required_non_empty_str(row, "principal_id", "principalId"),
            scopes=normalize_string_tuple(row.get("scopes", row.get("scope"))),
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            product_ids=normalize_string_tuple(row.get("product_ids", row.get("productIds"))),
            use_case_ids=normalize_string_tuple(
                row.get("use_case_ids", row.get("useCaseIds"))
            ),
        )


@dataclass(frozen=True, slots=True)
class PromptGatewayPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> PromptGatewayPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise PromptGatewayServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return PromptGatewayPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class PromptGatewayAccessPolicy:
    policy_id: str
    principals: Mapping[str, PromptGatewayPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    external_auto_send_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> PromptGatewayPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise PromptGatewayServiceError(
                f"prompt gateway principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class PromptGatewayEvaluation:
    tenant_id: str
    product: str
    use_case_id: str
    result: PromptGatewayResult

    def to_dict(self) -> dict[str, Any]:
        payload = self.result.to_dict()
        payload.update(
            {
                "product": self.product,
                "tenantId": self.tenant_id,
                "useCaseId": self.use_case_id,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class PromptGatewayMetricsSnapshot:
    request_count: int
    evaluation_count: int
    allowed_count: int
    blocked_count: int
    error_count: int
    human_review_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowedCount": self.allowed_count,
            "blockedCount": self.blocked_count,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "errorCount": self.error_count,
            "evaluationCount": self.evaluation_count,
            "humanReviewCount": self.human_review_count,
            "requestCount": self.request_count,
        }


class PromptGatewayMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.evaluation_count = 0
        self.allowed_count = 0
        self.blocked_count = 0
        self.error_count = 0
        self.human_review_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}

    def record_evaluation(self, request: PromptGatewayRequest, result: PromptGatewayResult) -> None:
        self.request_count += 1
        self.evaluation_count += 1
        if result.allowed:
            self.allowed_count += 1
        else:
            self.blocked_count += 1
        if result.require_human_review:
            self.human_review_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )

    def record_error(self) -> None:
        self.request_count += 1
        self.error_count += 1

    def snapshot(self) -> PromptGatewayMetricsSnapshot:
        return PromptGatewayMetricsSnapshot(
            request_count=self.request_count,
            evaluation_count=self.evaluation_count,
            allowed_count=self.allowed_count,
            blocked_count=self.blocked_count,
            error_count=self.error_count,
            human_review_count=self.human_review_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
        )


class PromptGatewayRuntime:
    """Policy-aware runtime for prompt redaction, tenant filtering and budget gates."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = PromptGatewayMetrics()

    def evaluate(
        self,
        request: PromptGatewayRequest | Mapping[str, Any],
        principal: PromptGatewayPrincipal | Mapping[str, Any] | None = None,
    ) -> PromptGatewayEvaluation:
        gateway_request = (
            request
            if isinstance(request, PromptGatewayRequest)
            else prompt_gateway_request_from_dict(request)
        )
        try:
            authorize_prompt_gateway_evaluate(normalize_principal(principal), gateway_request)
            result = run_prompt_gateway(gateway_request)
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_evaluation(gateway_request, result)
        return PromptGatewayEvaluation(
            tenant_id=gateway_request.tenant_id,
            product=gateway_request.product,
            use_case_id=gateway_request.use_case_id,
            result=result,
        )

    def health(self) -> dict[str, Any]:
        return {
            "serviceStatus": "healthy",
            "routeCount": len(PROMPT_GATEWAY_ROUTE_SCOPES),
        }

    def snapshot_metrics(self) -> PromptGatewayMetricsSnapshot:
        return self.metrics.snapshot()


def load_prompt_gateway_access_policy(ai_root: Path | str) -> PromptGatewayAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "prompt-gateway-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "evaluate": PROMPT_GATEWAY_EVALUATE_SCOPE,
        "ops": PROMPT_GATEWAY_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, PromptGatewayPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = PromptGatewayPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_prompt_gateway_scope_alias(scope, scope_aliases, policy_path)
                        for scope in normalize_string_tuple(row.get("scopes", []))
                    }
                )
            ),
            tenant_ids=tuple(sorted(normalize_string_tuple(row.get("tenant_ids", [])))),
            product_ids=tuple(sorted(product_ids)),
            use_case_ids=tuple(sorted(normalize_string_tuple(row.get("use_case_ids", [])))),
        )
    defaults = policy.get("defaults", {})
    if not isinstance(defaults, dict):
        raise RegistryValidationError(f"{policy_path} defaults must be a mapping")
    return PromptGatewayAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        external_auto_send_allowed=bool(defaults.get("external_auto_send_allowed", False)),
    )


def authorize_prompt_gateway_evaluate(
    principal: PromptGatewayPrincipal | None,
    request: PromptGatewayRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise PromptGatewayServiceError("wildcard prompt gateway scopes are forbidden")
    if PROMPT_GATEWAY_EVALUATE_SCOPE not in principal.scopes:
        raise PromptGatewayServiceError("prompt gateway evaluate scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise PromptGatewayServiceError("prompt gateway tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise PromptGatewayServiceError("prompt gateway product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise PromptGatewayServiceError("prompt gateway use case is not granted to principal")


def prompt_gateway_request_from_dict(row: Mapping[str, Any]) -> PromptGatewayRequest:
    cost_budget = required_mapping_any(row, "cost_budget", "costBudget", "prompt request")
    output_policy = required_mapping_any(row, "output_policy", "outputPolicy", "prompt request")
    return PromptGatewayRequest(
        tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
        product=required_non_empty_str(row, "product", "product"),
        use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
        system_prompt=required_non_empty_str(row, "system_prompt", "systemPrompt"),
        user_input=required_non_empty_str(row, "user_input", "userInput"),
        retrieved_context=tuple(
            PromptContext(
                context_id=required_non_empty_str(context, "context_id", "contextId"),
                tenant_id=required_non_empty_str(context, "tenant_id", "tenantId"),
                source_ref=required_non_empty_str(context, "source_ref", "sourceRef"),
                text=required_non_empty_str(context, "text", "text"),
            )
            for context in required_mapping_sequence_any(
                row,
                "retrieved_context",
                "retrievedContext",
                "prompt request",
            )
        ),
        output_policy=PromptOutputPolicy(
            require_human_review=required_bool_any(
                output_policy,
                "require_human_review",
                "requireHumanReview",
                "prompt output policy",
            ),
            allow_external_auto_send=required_bool_any(
                output_policy,
                "allow_external_auto_send",
                "allowExternalAutoSend",
                "prompt output policy",
            ),
            require_citations=required_bool_any(
                output_policy,
                "require_citations",
                "requireCitations",
                "prompt output policy",
            ),
        ),
        cost_budget=PromptCostBudget(
            max_estimated_input_tokens=required_positive_int_any(
                cost_budget,
                "max_estimated_input_tokens",
                "maxEstimatedInputTokens",
                "prompt cost budget",
            ),
            max_estimated_output_tokens=required_positive_int_any(
                cost_budget,
                "max_estimated_output_tokens",
                "maxEstimatedOutputTokens",
                "prompt cost budget",
            ),
            max_estimated_total_tokens=required_positive_int_any(
                cost_budget,
                "max_estimated_total_tokens",
                "maxEstimatedTotalTokens",
                "prompt cost budget",
            ),
        ),
        case_id=optional_string_any(row, "case_id", "caseId"),
    )


def normalize_principal(
    principal: PromptGatewayPrincipal | Mapping[str, Any] | None,
) -> PromptGatewayPrincipal | None:
    if principal is None or isinstance(principal, PromptGatewayPrincipal):
        return principal
    return PromptGatewayPrincipal.from_dict(principal)


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise PromptGatewayServiceError(
            "prompt gateway policy values must be strings or lists"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PromptGatewayServiceError(
                "prompt gateway policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_prompt_gateway_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:prompt-gateway:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported prompt gateway scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise PromptGatewayServiceError(
            f"prompt gateway request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def optional_string_any(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key, ""))
    if value is None:
        return ""
    if not isinstance(value, str):
        raise PromptGatewayServiceError(
            f"prompt gateway request field {snake_key} must be a string"
        )
    return value.strip()


def required_mapping_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> dict[str, Any]:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, dict):
        raise PromptGatewayServiceError(
            f"{owner} must define mapping field {snake_key} or {camel_key}"
        )
    return value


def required_mapping_sequence_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> tuple[Mapping[str, Any], ...]:
    value = row.get(snake_key, row.get(camel_key, []))
    if not isinstance(value, list | tuple):
        raise PromptGatewayServiceError(
            f"{owner} field {snake_key} or {camel_key} must be a list"
        )
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise PromptGatewayServiceError(
                f"{owner} context item {index} must be a mapping"
            )
        result.append(item)
    return tuple(result)


def required_bool_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> bool:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, bool):
        raise PromptGatewayServiceError(
            f"{owner} must define boolean field {snake_key} or {camel_key}"
        )
    return value


def required_positive_int_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PromptGatewayServiceError(
            f"{owner} must define positive integer field {snake_key} or {camel_key}"
        )
    return value


def require_mapping_list(row: Mapping[str, Any], key: str, owner: Path) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result
