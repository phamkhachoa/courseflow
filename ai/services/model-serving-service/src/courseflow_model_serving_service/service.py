from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.model_audit import ModelAuditStore
from courseflow_ai_platform.model_serving import safe_error_message
from courseflow_ai_platform.model_serving_adapter import (
    ModelServingAdapterResponse,
    ModelServingHostedAdapter,
    normalize_route,
)
from courseflow_ai_platform.model_serving_auth import (
    MODEL_SERVING_CATALOG_SCOPE,
    MODEL_SERVING_INVOKE_SCOPE,
    MODEL_SERVING_OPS_SCOPE,
    ServingAccessPolicy,
    ServingAuthPolicy,
    ServingPrincipal,
    load_serving_access_policy,
    load_serving_auth_policy,
)
from courseflow_ai_platform.serving_metrics_export import (
    write_model_serving_metrics_export_snapshot,
)

MODEL_SERVING_SERVICE_ID = "model-serving-service"


@dataclass(frozen=True, slots=True)
class ServiceRoute:
    method: str
    path: str
    scope: str
    purpose: str

    def to_dict(self) -> dict[str, str]:
        return {
            "method": self.method,
            "path": self.path,
            "purpose": self.purpose,
            "scope": self.scope,
        }


SERVICE_ROUTES = (
    ServiceRoute(
        method="GET",
        path="/v1/models",
        scope=MODEL_SERVING_CATALOG_SCOPE,
        purpose="model_catalog",
    ),
    ServiceRoute(
        method="POST",
        path="/v1/model-invocations",
        scope=MODEL_SERVING_INVOKE_SCOPE,
        purpose="model_invocation",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/model-serving/metrics",
        scope=MODEL_SERVING_OPS_SCOPE,
        purpose="serving_metrics",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/model-serving/health",
        scope=MODEL_SERVING_OPS_SCOPE,
        purpose="serving_health",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/model-serving/cockpit",
        scope=MODEL_SERVING_OPS_SCOPE,
        purpose="operating_cockpit_projection",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/model-serving/product-readiness",
        scope=MODEL_SERVING_OPS_SCOPE,
        purpose="runtime_product_readiness_projection",
    ),
)


@dataclass(frozen=True, slots=True)
class ModelServingServiceConfig:
    ai_root: Path
    audit_log_path: Path | None = None
    auth_enabled: bool = True
    audit_retention_days: int = 30
    audit_failure_mode: str = "fail_open"

    @classmethod
    def from_paths(
        cls,
        *,
        ai_root: Path | str | None = None,
        audit_log_path: Path | str | None = None,
        auth_enabled: bool = True,
        audit_retention_days: int = 30,
        audit_failure_mode: str = "fail_open",
    ) -> ModelServingServiceConfig:
        return cls(
            ai_root=Path(ai_root) if ai_root is not None else default_ai_root(),
            audit_log_path=Path(audit_log_path) if audit_log_path is not None else None,
            auth_enabled=auth_enabled,
            audit_retention_days=audit_retention_days,
            audit_failure_mode=audit_failure_mode,
        )


class ModelServingService:
    """Policy-enforced service boundary around the platform hosted serving adapter."""

    def __init__(
        self,
        config: ModelServingServiceConfig,
        *,
        audit_store: ModelAuditStore | None = None,
    ) -> None:
        self.config = config
        self.auth_policy: ServingAuthPolicy | None = (
            load_serving_auth_policy(config.ai_root) if config.auth_enabled else None
        )
        self.access_policy: ServingAccessPolicy | None = (
            load_serving_access_policy(config.ai_root) if config.auth_enabled else None
        )
        self.adapter = ModelServingHostedAdapter(
            config.ai_root,
            audit_store=audit_store,
            audit_log_path=config.audit_log_path,
            audit_retention_days=config.audit_retention_days,
            audit_failure_mode=config.audit_failure_mode,
            auth_policy=self.auth_policy,
        )

    def manifest(self) -> dict[str, Any]:
        return build_service_manifest()

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        principal_id: str | None = None,
        requested_scopes: Sequence[str] | None = None,
        principal: ServingPrincipal | Mapping[str, Any] | None = None,
    ) -> ModelServingAdapterResponse:
        route = normalize_route(method, path)
        resolved_principal = principal
        if (
            self.config.auth_enabled
            and resolved_principal is None
            and principal_id is not None
            and route in route_scope_index()
        ):
            try:
                resolved_principal = self.resolve_principal_for_route(
                    route,
                    principal_id=principal_id,
                    requested_scopes=requested_scopes,
                )
            except ValueError as exc:
                return ModelServingAdapterResponse(
                    status_code=403,
                    body={
                        "errorCode": "principal_policy_forbidden",
                        "errorMessage": safe_error_message(exc),
                    },
                )
        return self.adapter.handle_request(method, path, body, resolved_principal)

    def catalog(self, *, principal_id: str | None = None) -> ModelServingAdapterResponse:
        return self.handle_request("GET", "/v1/models", principal_id=principal_id)

    def invoke(
        self,
        body: Mapping[str, Any],
        *,
        principal_id: str | None = None,
    ) -> ModelServingAdapterResponse:
        return self.handle_request(
            "POST",
            "/v1/model-invocations",
            body,
            principal_id=principal_id,
        )

    def metrics(self, *, principal_id: str | None = None) -> ModelServingAdapterResponse:
        return self.handle_request(
            "GET",
            "/v1/model-serving/metrics",
            principal_id=principal_id,
        )

    def health(self, *, principal_id: str | None = None) -> ModelServingAdapterResponse:
        return self.handle_request(
            "GET",
            "/v1/model-serving/health",
            principal_id=principal_id,
        )

    def cockpit(self, *, principal_id: str | None = None) -> ModelServingAdapterResponse:
        return self.handle_request(
            "GET",
            "/v1/model-serving/cockpit",
            principal_id=principal_id,
        )

    def product_readiness(
        self,
        *,
        principal_id: str | None = None,
    ) -> ModelServingAdapterResponse:
        return self.handle_request(
            "GET",
            "/v1/model-serving/product-readiness",
            principal_id=principal_id,
        )

    def export_metrics(
        self,
        output_path: Path | str | None = None,
        *,
        generated_at: str | None = None,
    ) -> Path:
        return write_model_serving_metrics_export_snapshot(
            self.config.ai_root,
            output_path,
            generated_at=generated_at,
            metrics=self.adapter.snapshot_metrics(),
            source_adapter=MODEL_SERVING_SERVICE_ID,
        )

    def resolve_principal_for_route(
        self,
        route: tuple[str, str],
        *,
        principal_id: str,
        requested_scopes: Sequence[str] | None = None,
    ) -> ServingPrincipal:
        if self.access_policy is None:
            raise ValueError("serving access policy is disabled")
        scopes = tuple(requested_scopes or (route_scope_index()[route],))
        return self.access_policy.resolve_principal(principal_id, scopes)


def build_service_manifest() -> dict[str, Any]:
    return {
        "serviceId": MODEL_SERVING_SERVICE_ID,
        "owner": "ai-platform",
        "status": "service_package_ready",
        "runtime": {
            "entrypoint": "courseflow_model_serving_service.cli:main",
            "language": "python",
        },
        "security": {
            "defaultAuth": "policy_enforced",
            "policyArtifacts": [
                "platform/governance/policies/ai-governance-policy.yaml",
                "platform/governance/policies/model-serving-access-policy.yaml",
            ],
        },
        "observability": {
            "auditEventContract": "contracts/models/model-audit-event.v1.yaml",
            "metricsExport": "platform/operations/reports/model-serving-metrics-export-v1.yaml",
        },
        "routes": [route.to_dict() for route in SERVICE_ROUTES],
    }


def route_scope_index() -> dict[tuple[str, str], str]:
    return {
        (route.method, route.path): route.scope
        for route in SERVICE_ROUTES
    }


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[4]
