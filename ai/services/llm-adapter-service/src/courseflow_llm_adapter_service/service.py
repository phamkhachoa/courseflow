from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.llm_provider_adapter import (
    LLM_ADAPTER_GENERATE_SCOPE,
    LLM_ADAPTER_OPS_SCOPE,
    LlmAdapterAccessPolicy,
    LlmAdapterPrincipal,
    LlmProviderAdapterError,
    LlmProviderAdapterRuntime,
    load_llm_adapter_access_policy,
)

LLM_ADAPTER_SERVICE_ID = "llm-adapter-service"


@dataclass(frozen=True, slots=True)
class LlmAdapterServiceResponse:
    status_code: int
    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body,
            "statusCode": self.status_code,
        }


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
        method="POST",
        path="/v1/llm-adapter/generate",
        scope=LLM_ADAPTER_GENERATE_SCOPE,
        purpose="prompt_gateway_bound_generation",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/llm-adapter/health",
        scope=LLM_ADAPTER_OPS_SCOPE,
        purpose="llm_adapter_health",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/llm-adapter/metrics",
        scope=LLM_ADAPTER_OPS_SCOPE,
        purpose="llm_adapter_metrics",
    ),
)


@dataclass(frozen=True, slots=True)
class LlmAdapterServiceConfig:
    ai_root: Path
    audit_log_path: Path | None = None
    auth_enabled: bool = True
    audit_retention_days: int = 30

    @classmethod
    def from_paths(
        cls,
        *,
        ai_root: Path | str | None = None,
        audit_log_path: Path | str | None = None,
        auth_enabled: bool = True,
        audit_retention_days: int = 30,
    ) -> LlmAdapterServiceConfig:
        return cls(
            ai_root=Path(ai_root) if ai_root is not None else default_ai_root(),
            audit_log_path=Path(audit_log_path) if audit_log_path is not None else None,
            auth_enabled=auth_enabled,
            audit_retention_days=audit_retention_days,
        )


class LlmAdapterService:
    """Policy-enforced service boundary around LLM provider adapter runtime."""

    def __init__(self, config: LlmAdapterServiceConfig) -> None:
        self.config = config
        self.access_policy: LlmAdapterAccessPolicy | None = (
            load_llm_adapter_access_policy(config.ai_root) if config.auth_enabled else None
        )
        self.runtime = LlmProviderAdapterRuntime(
            config.ai_root,
            audit_log_path=config.audit_log_path,
            audit_retention_days=config.audit_retention_days,
        )

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        principal_id: str | None = None,
        requested_scopes: Sequence[str] | None = None,
        principal: LlmAdapterPrincipal | Mapping[str, Any] | None = None,
    ) -> LlmAdapterServiceResponse:
        route = normalize_route(method, path)
        route_scope = route_scope_index().get(route)
        if route_scope is None:
            return error_response(404, "not_found", f"route not found: {method.upper()} {path}")
        resolved_principal = principal
        if self.config.auth_enabled and resolved_principal is None:
            if principal_id is None:
                return error_response(
                    401,
                    "auth_required",
                    "LLM adapter principal is required",
                )
            try:
                resolved_principal = self.resolve_principal(
                    principal_id,
                    requested_scopes=requested_scopes or (route_scope,),
                )
            except LlmProviderAdapterError as exc:
                return error_response(403, "principal_policy_forbidden", str(exc))

        try:
            if route == ("POST", "/v1/llm-adapter/generate"):
                return self.generate(body, resolved_principal)
            if route == ("GET", "/v1/llm-adapter/health"):
                return self.health()
            if route == ("GET", "/v1/llm-adapter/metrics"):
                return self.metrics()
        except LlmProviderAdapterError as exc:
            return error_response(400, "bad_request", str(exc))
        except Exception as exc:
            return error_response(500, "llm_adapter_service_failed", str(exc))

        return error_response(500, "route_not_implemented", f"route is not implemented: {path}")

    def generate(
        self,
        body: Mapping[str, Any] | None,
        principal: LlmAdapterPrincipal | Mapping[str, Any] | None,
    ) -> LlmAdapterServiceResponse:
        if body is None:
            return error_response(400, "bad_request", "request body must be a JSON object")
        return LlmAdapterServiceResponse(
            status_code=200,
            body=self.runtime.generate(body, principal).to_dict(),
        )

    def health(self) -> LlmAdapterServiceResponse:
        return LlmAdapterServiceResponse(status_code=200, body=self.runtime.health())

    def metrics(self) -> LlmAdapterServiceResponse:
        return LlmAdapterServiceResponse(
            status_code=200,
            body={"metrics": self.runtime.snapshot_metrics().to_dict()},
        )

    def resolve_principal(
        self,
        principal_id: str,
        *,
        requested_scopes: Sequence[str],
    ) -> LlmAdapterPrincipal:
        if self.access_policy is None:
            raise LlmProviderAdapterError("LLM adapter access policy is disabled")
        return self.access_policy.resolve_principal(principal_id, requested_scopes)

    def manifest(self) -> dict[str, Any]:
        return build_service_manifest()


def build_service_manifest() -> dict[str, Any]:
    return {
        "serviceId": LLM_ADAPTER_SERVICE_ID,
        "owner": "ai-platform",
        "status": "service_package_ready",
        "runtime": {
            "entrypoint": "courseflow_llm_adapter_service.cli:main",
            "language": "python",
        },
        "security": {
            "defaultAuth": "policy_enforced",
            "policyArtifacts": [
                "platform/governance/policies/ai-governance-policy.yaml",
                "platform/governance/policies/llm-adapter-access-policy.yaml",
                "platform/governance/policies/llm-provider-credential-readiness.yaml",
                "platform/governance/policies/llm-provider-ops-policy.yaml",
                "platform/governance/policies/llm-provider-runtime-probe-policy.yaml",
                "platform/governance/policies/prompt-gateway-access-policy.yaml",
            ],
        },
        "observability": {
            "auditEventContract": "contracts/prompts/prompt-audit-event.v1.yaml",
            "credentialReadiness": "platform/governance/reports/llm-provider-readiness-v1.yaml",
            "runtimeProbes": "platform/operations/reports/llm-provider-runtime-probes-v1.yaml",
            "metrics": (
                "in_memory_gateway_provider_rate_limit_failover_audit_cost_latency_counters"
            ),
        },
        "providerOps": {
            "circuitBreaker": "configured_per_provider",
            "failover": "configured_per_provider",
            "rateLimit": "configured_per_principal_tenant_provider_window",
            "timeout": "configured_per_provider",
        },
        "routes": [route.to_dict() for route in SERVICE_ROUTES],
    }


def route_scope_index() -> dict[tuple[str, str], str]:
    return {
        (route.method, route.path): route.scope
        for route in SERVICE_ROUTES
    }


def normalize_route(method: str, path: str) -> tuple[str, str]:
    return method.upper(), "/" + path.strip("/")


def error_response(status_code: int, error_code: str, message: str) -> LlmAdapterServiceResponse:
    return LlmAdapterServiceResponse(
        status_code=status_code,
        body={
            "errorCode": error_code,
            "errorMessage": message,
        },
    )


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[4]
