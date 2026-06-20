from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

ROUTING_POLICY_RECOMMEND_SCOPE = "internal:ai-platform:routing-policy:recommend"
ROUTING_POLICY_OPS_SCOPE = "internal:ai-platform:routing-policy:ops"
ROUTING_POLICY_ROUTE_SCOPES = {
    ("POST", "/v1/routing-policy/recommend"): ROUTING_POLICY_RECOMMEND_SCOPE,
    ("GET", "/v1/routing-policy/health"): ROUTING_POLICY_OPS_SCOPE,
    ("GET", "/v1/routing-policy/metrics"): ROUTING_POLICY_OPS_SCOPE,
}
ROUTING_POLICY_MODEL_RELATIVE_PATH = (
    "models/bandit_rl/routing_policy_simulator/routing_policy_simulator.py"
)
RAW_ID_KEYS = (
    "agent_id",
    "agentId",
    "assignee_id",
    "assigneeId",
    "customer_id",
    "customerId",
    "learner_id",
    "learnerId",
    "student_id",
    "studentId",
    "email",
    "emailAddress",
    "phone",
    "phoneNumber",
)


class RoutingPolicyServiceError(ValueError):
    """Raised when routing policy service input or policy is invalid."""


class RoutingPolicyPrivacyError(RoutingPolicyServiceError):
    """Raised when routing requests submit direct identifiers."""


@dataclass(frozen=True, slots=True)
class RoutingPolicyPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> RoutingPolicyPrincipal:
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
class RoutingPolicyPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> RoutingPolicyPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise RoutingPolicyServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return RoutingPolicyPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class RoutingPolicyAccessPolicy:
    policy_id: str
    principals: Mapping[str, RoutingPolicyPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False
    online_policy_activation_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> RoutingPolicyPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise RoutingPolicyServiceError(
                f"routing policy principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class RoutingPolicyRecommendationRequest:
    tenant_id: str
    product: str
    use_case_id: str
    policy_id: str
    safe_exploration_budget: float
    work_item: Mapping[str, Any]
    queues: tuple[Mapping[str, Any], ...]
    baseline_queue_id: str = ""

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> RoutingPolicyRecommendationRequest:
        reject_direct_identifiers(row)
        work_item = required_mapping(row, "work_item", "workItem")
        queues = required_mapping_sequence(row, "queues", "queues")
        reject_direct_identifiers(work_item)
        for queue in queues:
            reject_direct_identifiers(queue)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            policy_id=required_non_empty_str(row, "policy_id", "policyId"),
            safe_exploration_budget=required_bounded_float(
                row,
                "safe_exploration_budget",
                "safeExplorationBudget",
                minimum=0.0,
                maximum=0.2,
            ),
            baseline_queue_id=optional_str(row, "baseline_queue_id", "baselineQueueId"),
            work_item=work_item,
            queues=queues,
        )

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "baseline_queue_id": self.baseline_queue_id,
            "policy_id": self.policy_id,
            "queues": [normalize_queue_payload(queue) for queue in self.queues],
            "safe_exploration_budget": self.safe_exploration_budget,
            "tenant_id": self.tenant_id,
            "work_item": normalize_work_item_payload(self.work_item),
        }


@dataclass(frozen=True, slots=True)
class RoutingPolicyRecommendationResponse:
    tenant_id: str
    product: str
    use_case_id: str
    policy_id: str
    work_item_id: str
    result: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.result)
        constraint_violations = payload.get("constraint_violations", [])
        requires_human_review = bool(payload.get("requires_human_review")) or bool(
            constraint_violations
        )
        payload.update(
            {
                "decisionPolicy": "simulator_only_human_review_before_online_routing",
                "onlinePolicyActivationAllowed": False,
                "policyId": self.policy_id,
                "product": self.product,
                "requires_human_review": requires_human_review,
                "tenantId": self.tenant_id,
                "useCaseId": self.use_case_id,
                "workItemId": self.work_item_id,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class RoutingPolicyMetricsSnapshot:
    request_count: int
    recommendation_count: int
    error_count: int
    direct_identifier_rejection_count: int
    human_review_count: int
    constraint_violation_count: int
    exploration_budget_used_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]
    by_work_type: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "byWorkType": self.by_work_type,
            "constraintViolationCount": self.constraint_violation_count,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "errorCount": self.error_count,
            "explorationBudgetUsedCount": self.exploration_budget_used_count,
            "humanReviewCount": self.human_review_count,
            "recommendationCount": self.recommendation_count,
            "requestCount": self.request_count,
        }


class RoutingPolicyMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.recommendation_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.human_review_count = 0
        self.constraint_violation_count = 0
        self.exploration_budget_used_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}
        self.by_work_type: dict[str, int] = {}

    def record_recommendation(
        self,
        request: RoutingPolicyRecommendationRequest,
        result: Mapping[str, Any],
    ) -> None:
        self.request_count += 1
        self.recommendation_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )
        work_type = str(request.work_item.get("work_type", request.work_item.get("workType", "")))
        if work_type:
            self.by_work_type[work_type] = self.by_work_type.get(work_type, 0) + 1
        violations = result.get("constraint_violations", [])
        if isinstance(violations, list):
            self.constraint_violation_count += len(violations)
        if bool(result.get("requires_human_review")) or bool(violations):
            self.human_review_count += 1
        exploration = result.get("exploration_budget_used")
        if isinstance(exploration, int | float) and float(exploration) > 0:
            self.exploration_budget_used_count += 1

    def record_error(self, *, direct_identifier: bool = False) -> None:
        self.request_count += 1
        self.error_count += 1
        if direct_identifier:
            self.direct_identifier_rejection_count += 1

    def snapshot(self) -> RoutingPolicyMetricsSnapshot:
        return RoutingPolicyMetricsSnapshot(
            request_count=self.request_count,
            recommendation_count=self.recommendation_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            human_review_count=self.human_review_count,
            constraint_violation_count=self.constraint_violation_count,
            exploration_budget_used_count=self.exploration_budget_used_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
            by_work_type=dict(sorted(self.by_work_type.items())),
        )


class RoutingPolicyRuntime:
    """Policy-aware runtime for constrained routing-policy simulation."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = RoutingPolicyMetrics()
        self.model = load_model_class(
            self.ai_root,
            ROUTING_POLICY_MODEL_RELATIVE_PATH,
            "RoutingPolicySimulator",
            "courseflow_routing_policy_simulator_runtime",
        )()

    def recommend(
        self,
        request: RoutingPolicyRecommendationRequest | Mapping[str, Any],
        principal: RoutingPolicyPrincipal | Mapping[str, Any] | None = None,
    ) -> RoutingPolicyRecommendationResponse:
        try:
            recommendation_request = (
                request
                if isinstance(request, RoutingPolicyRecommendationRequest)
                else RoutingPolicyRecommendationRequest.from_dict(request)
            )
            authorize_routing_policy_recommend(
                normalize_principal(principal),
                recommendation_request,
            )
            decision = self.model.recommend(recommendation_request.to_model_payload())
            result = dict(decision.to_dict())
        except RoutingPolicyPrivacyError:
            self.metrics.record_error(direct_identifier=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_recommendation(recommendation_request, result)
        work_item_id = str(
            recommendation_request.work_item.get(
                "work_item_id",
                recommendation_request.work_item.get("workItemId", ""),
            )
        )
        return RoutingPolicyRecommendationResponse(
            tenant_id=recommendation_request.tenant_id,
            product=recommendation_request.product,
            use_case_id=recommendation_request.use_case_id,
            policy_id=recommendation_request.policy_id,
            work_item_id=work_item_id,
            result=result,
        )

    def health(self) -> dict[str, Any]:
        return {
            "modelId": "operations-routing-policy-simulator-v1",
            "routeCount": len(ROUTING_POLICY_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> RoutingPolicyMetricsSnapshot:
        return self.metrics.snapshot()


def load_routing_policy_access_policy(ai_root: Path | str) -> RoutingPolicyAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "routing-policy-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "recommend": ROUTING_POLICY_RECOMMEND_SCOPE,
        "ops": ROUTING_POLICY_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, RoutingPolicyPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = RoutingPolicyPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_routing_policy_scope_alias(scope, scope_aliases, policy_path)
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
    return RoutingPolicyAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        direct_identifier_submission_allowed=bool(
            defaults.get("direct_identifier_submission_allowed", False)
        ),
        online_policy_activation_allowed=bool(
            defaults.get("online_policy_activation_allowed", False)
        ),
    )


def authorize_routing_policy_recommend(
    principal: RoutingPolicyPrincipal | None,
    request: RoutingPolicyRecommendationRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise RoutingPolicyServiceError("wildcard routing policy scopes are forbidden")
    if ROUTING_POLICY_RECOMMEND_SCOPE not in principal.scopes:
        raise RoutingPolicyServiceError("routing policy recommend scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise RoutingPolicyServiceError("routing policy tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise RoutingPolicyServiceError("routing policy product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise RoutingPolicyServiceError("routing policy use case is not granted to principal")


def normalize_principal(
    principal: RoutingPolicyPrincipal | Mapping[str, Any] | None,
) -> RoutingPolicyPrincipal | None:
    if principal is None or isinstance(principal, RoutingPolicyPrincipal):
        return principal
    return RoutingPolicyPrincipal.from_dict(principal)


def load_model_class(
    ai_root: Path,
    relative_path: str,
    class_name: str,
    module_name: str,
) -> type[Any]:
    module_path = ai_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RoutingPolicyServiceError(f"cannot load model module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise RoutingPolicyServiceError(
            f"model module {relative_path} does not define {class_name}"
        )
    return model_class


def normalize_work_item_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "customer_segment": optional_str(row, "customer_segment", "customerSegment")
        or "standard",
        "expected_effort_minutes": required_positive_int(
            row,
            "expected_effort_minutes",
            "expectedEffortMinutes",
        ),
        "priority": optional_str(row, "priority", "priority") or "p2",
        "required_skill_ids": required_string_sequence(
            row,
            "required_skill_ids",
            "requiredSkillIds",
        ),
        "work_item_id": required_non_empty_str(row, "work_item_id", "workItemId"),
        "work_type": required_non_empty_str(row, "work_type", "workType"),
    }


def normalize_queue_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "available_agent_count": required_non_negative_int(
            row,
            "available_agent_count",
            "availableAgentCount",
        ),
        "average_handle_time_minutes": required_positive_int(
            row,
            "average_handle_time_minutes",
            "averageHandleTimeMinutes",
        ),
        "backlog_count": required_non_negative_int(row, "backlog_count", "backlogCount"),
        "max_concurrency": required_positive_int(row, "max_concurrency", "maxConcurrency"),
        "queue_id": required_non_empty_str(row, "queue_id", "queueId"),
        "skill_ids": required_string_sequence(row, "skill_ids", "skillIds"),
    }


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in RAW_ID_KEYS:
        value = row.get(key)
        if value is not None and str(value).strip():
            raise RoutingPolicyPrivacyError(
                f"routing policy request must not include direct identifier field {key}"
            )


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise RoutingPolicyServiceError(
            "routing policy policy values must be strings or lists"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RoutingPolicyServiceError(
                "routing policy policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_routing_policy_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:routing-policy:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported routing policy scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise RoutingPolicyServiceError(
            f"routing policy request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def optional_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key, ""))
    return str(value).strip() if value is not None else ""


def required_mapping(row: Mapping[str, Any], snake_key: str, camel_key: str) -> Mapping[str, Any]:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, dict):
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be a mapping"
        )
    return value


def required_mapping_sequence(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
) -> tuple[Mapping[str, Any], ...]:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, list | tuple):
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be a list"
        )
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RoutingPolicyServiceError(
                f"routing policy request item {index} must be a mapping"
            )
        result.append(item)
    return tuple(result)


def required_string_sequence(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
) -> list[str]:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, list | tuple):
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be a list"
        )
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RoutingPolicyServiceError(
                f"routing policy request list item {index} must be a string"
            )
        result.append(item.strip())
    if not result:
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must not be empty"
        )
    return result


def required_non_negative_int(row: Mapping[str, Any], snake_key: str, camel_key: str) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be an integer"
        )
    if value < 0:
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be non-negative"
        )
    return value


def required_positive_int(row: Mapping[str, Any], snake_key: str, camel_key: str) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be an integer"
        )
    if value <= 0:
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be positive"
        )
    return value


def required_bounded_float(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be numeric"
        )
    result = float(value)
    if result < minimum or result > maximum:
        raise RoutingPolicyServiceError(
            f"routing policy request field {snake_key} or {camel_key} must be bounded"
        )
    return result


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
