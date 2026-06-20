from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml

MODEL_SERVING_CATALOG_SCOPE = "internal:ai-platform:model-serving:catalog"
MODEL_SERVING_INVOKE_SCOPE = "internal:ai-platform:model-serving:invoke"
MODEL_SERVING_OPS_SCOPE = "internal:ai-platform:model-serving:ops"

MODEL_SERVING_ROUTE_SCOPES = {
    ("GET", "/v1/models"): MODEL_SERVING_CATALOG_SCOPE,
    ("POST", "/v1/model-invocations"): MODEL_SERVING_INVOKE_SCOPE,
    ("GET", "/v1/model-serving/metrics"): MODEL_SERVING_OPS_SCOPE,
    ("GET", "/v1/model-serving/health"): MODEL_SERVING_OPS_SCOPE,
    ("GET", "/v1/model-serving/cockpit"): MODEL_SERVING_OPS_SCOPE,
    ("GET", "/v1/model-serving/product-readiness"): MODEL_SERVING_OPS_SCOPE,
}


@dataclass(frozen=True, slots=True)
class ServingPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    allowed_model_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> ServingPrincipal:
        return cls(
            principal_id=required_principal_str(row, "principal_id", "principalId"),
            scopes=normalize_string_tuple(row.get("scopes", row.get("scope"))),
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            allowed_model_ids=normalize_string_tuple(
                row.get("allowed_model_ids", row.get("allowedModelIds", row.get("modelIds")))
            ),
        )


@dataclass(frozen=True, slots=True)
class ServingAuthPolicy:
    required_route_scopes: Mapping[tuple[str, str], str]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True

    @classmethod
    def enforced(cls) -> ServingAuthPolicy:
        return cls(required_route_scopes=MODEL_SERVING_ROUTE_SCOPES)


@dataclass(frozen=True, slots=True)
class ServingPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    allowed_model_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> ServingPrincipal:
        if requested_scopes is None:
            scopes = self.scopes
        else:
            scopes = normalize_string_tuple(requested_scopes)
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise ValueError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return ServingPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            allowed_model_ids=self.allowed_model_ids,
        )


@dataclass(frozen=True, slots=True)
class ServingAccessPolicy:
    policy_id: str
    principals: Mapping[str, ServingPrincipalGrant]

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> ServingPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise ValueError(f"serving principal is not registered: {principal_id}")
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class ServingAuthDecision:
    allowed: bool
    status_code: int
    error_code: str
    error_message: str


@dataclass(frozen=True, slots=True)
class ServingAuthTelemetrySnapshot:
    denial_count: int
    by_reason: dict[str, int]
    by_route: dict[str, int]
    by_status_code: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byReason": self.by_reason,
            "byRoute": self.by_route,
            "byStatusCode": self.by_status_code,
            "denialCount": self.denial_count,
        }


@dataclass(slots=True)
class ServingAuthTelemetry:
    denial_count: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)
    by_route: dict[str, int] = field(default_factory=dict)
    by_status_code: dict[str, int] = field(default_factory=dict)

    def record_denial(
        self,
        *,
        route: tuple[str, str],
        status_code: int,
        reason: str,
    ) -> None:
        self.denial_count += 1
        increment(self.by_reason, normalize_rejection_reason(reason))
        increment(self.by_route, normalize_telemetry_route(route))
        increment(self.by_status_code, normalize_status_code(status_code))

    def snapshot(self) -> ServingAuthTelemetrySnapshot:
        return ServingAuthTelemetrySnapshot(
            denial_count=self.denial_count,
            by_reason=dict(sorted(self.by_reason.items())),
            by_route=dict(sorted(self.by_route.items())),
            by_status_code=dict(sorted(self.by_status_code.items())),
        )


def load_serving_auth_policy(ai_root: Path | str) -> ServingAuthPolicy:
    policy = load_yaml(
        Path(ai_root) / "platform" / "governance" / "policies" / "ai-governance-policy.yaml"
    )
    security = policy.get("policies", {}).get("security", {})
    endpoint_scopes = security.get("serving_endpoint_scopes", {})
    return ServingAuthPolicy(
        required_route_scopes={
            ("GET", "/v1/models"): required_scope(
                endpoint_scopes,
                "catalog",
                MODEL_SERVING_CATALOG_SCOPE,
            ),
            ("POST", "/v1/model-invocations"): required_scope(
                endpoint_scopes,
                "invoke",
                MODEL_SERVING_INVOKE_SCOPE,
            ),
            ("GET", "/v1/model-serving/metrics"): required_scope(
                endpoint_scopes,
                "ops",
                MODEL_SERVING_OPS_SCOPE,
            ),
            ("GET", "/v1/model-serving/health"): required_scope(
                endpoint_scopes,
                "ops",
                MODEL_SERVING_OPS_SCOPE,
            ),
            ("GET", "/v1/model-serving/cockpit"): required_scope(
                endpoint_scopes,
                "ops",
                MODEL_SERVING_OPS_SCOPE,
            ),
            ("GET", "/v1/model-serving/product-readiness"): required_scope(
                endpoint_scopes,
                "ops",
                MODEL_SERVING_OPS_SCOPE,
            ),
        },
        wildcard_scopes_allowed=bool(security.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(
            policy.get("policies", {})
            .get("privacy", {})
            .get("tenant_isolation_required", True)
        ),
    )


def load_serving_access_policy(ai_root: Path | str) -> ServingAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "model-serving-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    scope_aliases = {
        "catalog": MODEL_SERVING_CATALOG_SCOPE,
        "invoke": MODEL_SERVING_INVOKE_SCOPE,
        "ops": MODEL_SERVING_OPS_SCOPE,
        **require_mapping(policy.get("scope_aliases", {}), "scope_aliases", policy_path),
    }
    model_products = load_model_product_index(root)
    grants: dict[str, ServingPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = required_policy_str(row, "principal_id", policy_path)
        if principal_id in grants:
            raise RegistryValidationError(
                f"{policy_path} duplicates serving principal: {principal_id}"
            )
        product = required_policy_str(row, "product", policy_path)
        model_ids = tuple(sorted(normalize_string_tuple(row.get("model_ids", []))))
        validate_principal_model_grants(
            policy_path=policy_path,
            principal_id=principal_id,
            product=product,
            model_ids=model_ids,
            model_products=model_products,
        )
        grants[principal_id] = ServingPrincipalGrant(
            principal_id=principal_id,
            owner_role=required_policy_str(row, "owner_role", policy_path),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_scope_alias(scope, scope_aliases, policy_path)
                        for scope in normalize_string_tuple(row.get("scopes", []))
                    }
                )
            ),
            tenant_ids=tuple(sorted(normalize_string_tuple(row.get("tenant_ids", [])))),
            allowed_model_ids=model_ids,
        )

    return ServingAccessPolicy(
        policy_id=required_policy_str(policy, "policy_id", policy_path),
        principals=dict(sorted(grants.items())),
    )


def load_model_product_index(root: Path) -> dict[str, str]:
    manifest_dir = root / "platform" / "artifacts" / "manifests"
    model_products: dict[str, str] = {}
    for manifest_path in sorted(manifest_dir.glob("*.yaml")):
        manifest = load_yaml(manifest_path)
        model_id = manifest.get("model_id")
        product = manifest.get("product")
        if isinstance(model_id, str) and isinstance(product, str):
            model_products[model_id] = product
    return model_products


def validate_principal_model_grants(
    *,
    policy_path: Path,
    principal_id: str,
    product: str,
    model_ids: tuple[str, ...],
    model_products: Mapping[str, str],
) -> None:
    for model_id in model_ids:
        model_product = model_products.get(model_id)
        if model_product is None:
            raise RegistryValidationError(
                f"{policy_path} principal {principal_id} references unknown model: {model_id}"
            )
        if product != "ai-platform" and model_product != product:
            raise RegistryValidationError(
                f"{policy_path} principal {principal_id} product {product} "
                f"cannot grant model {model_id} owned by {model_product}"
            )


def expand_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    if scope in scope_aliases:
        return scope_aliases[scope]
    if scope.startswith("internal:"):
        return scope
    raise RegistryValidationError(f"{policy_path} references unknown scope alias: {scope}")


def authorize_serving_request(
    *,
    route: tuple[str, str],
    principal: ServingPrincipal | Mapping[str, Any] | None,
    request_body: Mapping[str, Any] | None = None,
    policy: ServingAuthPolicy,
) -> ServingAuthDecision:
    required_scope = policy.required_route_scopes.get(route)
    if required_scope is None:
        return allow()
    if principal is None:
        return deny(401, "auth_required", "serving adapter principal is required")

    serving_principal = principal
    if not isinstance(principal, ServingPrincipal):
        serving_principal = ServingPrincipal.from_dict(principal)
    if "*" in serving_principal.scopes and not policy.wildcard_scopes_allowed:
        return deny(403, "wildcard_scope_forbidden", "wildcard scopes are not allowed")
    if required_scope not in serving_principal.scopes:
        return deny(403, "scope_forbidden", f"required scope missing: {required_scope}")
    if route == ("POST", "/v1/model-invocations"):
        tenant_decision = authorize_tenant(serving_principal, request_body, policy)
        if not tenant_decision.allowed:
            return tenant_decision
        model_decision = authorize_model(serving_principal, request_body)
        if not model_decision.allowed:
            return model_decision

    return allow()


def authorize_tenant(
    principal: ServingPrincipal,
    request_body: Mapping[str, Any] | None,
    policy: ServingAuthPolicy,
) -> ServingAuthDecision:
    if not policy.tenant_isolation_required:
        return allow()
    tenant_id = optional_request_str(request_body, "tenant_id", "tenantId")
    if tenant_id is None:
        return deny(400, "bad_request", "tenant_id or tenantId is required for model invoke")
    if tenant_id not in principal.tenant_ids:
        return deny(403, "tenant_forbidden", f"principal cannot access tenant: {tenant_id}")
    payload = request_body.get("payload") if request_body is not None else None
    if isinstance(payload, dict):
        payload_tenant = payload.get("tenant_id") or payload.get("tenantId")
        if isinstance(payload_tenant, str) and payload_tenant.strip() != tenant_id:
            return deny(
                403,
                "tenant_mismatch",
                "request tenant does not match payload tenant",
            )
    return allow()


def authorize_model(
    principal: ServingPrincipal,
    request_body: Mapping[str, Any] | None,
) -> ServingAuthDecision:
    model_id = optional_request_str(request_body, "model_id", "modelId")
    if model_id is None:
        return deny(400, "bad_request", "model_id or modelId is required for model invoke")
    if principal.allowed_model_ids and model_id not in principal.allowed_model_ids:
        return deny(403, "model_forbidden", f"principal cannot invoke model: {model_id}")
    return allow()


def allow() -> ServingAuthDecision:
    return ServingAuthDecision(
        allowed=True,
        status_code=200,
        error_code="",
        error_message="",
    )


def deny(status_code: int, error_code: str, error_message: str) -> ServingAuthDecision:
    return ServingAuthDecision(
        allowed=False,
        status_code=status_code,
        error_code=error_code,
        error_message=error_message,
    )


def required_scope(row: Mapping[str, Any], key: str, default: str) -> str:
    value = row.get(key, default)
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip()


def required_principal_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"serving principal must define {snake_key} or {camel_key}")
    return value.strip()


def optional_request_str(
    row: Mapping[str, Any] | None,
    snake_key: str,
    camel_key: str,
) -> str | None:
    if row is None:
        return None
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def normalize_string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item for item in value.split() if item)
    if isinstance(value, list | tuple | set):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def increment(values: dict[str, int], key: str) -> None:
    values[key] = values.get(key, 0) + 1


def normalize_rejection_reason(reason: str) -> str:
    normalized = "".join(
        char if char.isalnum() or char == "_" else "_"
        for char in reason.strip().lower()
    )
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized[:80] or "unknown"


def normalize_telemetry_route(route: tuple[str, str]) -> str:
    method, path = route
    if route not in MODEL_SERVING_ROUTE_SCOPES:
        return "__unmatched__"
    return f"{method.upper()} {path}"


def normalize_status_code(status_code: int) -> str:
    if status_code < 100 or status_code > 599:
        return "unknown"
    return str(status_code)


def require_mapping(value: object, key: str, policy_path: Path) -> Mapping[str, str]:
    if not isinstance(value, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field {key}")
    result: dict[str, str] = {}
    for row_key, row_value in value.items():
        if not isinstance(row_key, str) or not isinstance(row_value, str):
            raise RegistryValidationError(f"{policy_path} {key} entries must be strings")
        result[row_key] = row_value
    return result


def require_mapping_list(
    row: Mapping[str, object],
    key: str,
    policy_path: Path,
) -> list[Mapping[str, object]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{policy_path} must define list field {key}")
    result: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{policy_path} {key} entries must be mappings")
        result.append(item)
    return result


def required_policy_str(row: Mapping[str, object], key: str, policy_path: Path) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryValidationError(f"{policy_path} must define non-empty string field {key}")
    return value.strip()
