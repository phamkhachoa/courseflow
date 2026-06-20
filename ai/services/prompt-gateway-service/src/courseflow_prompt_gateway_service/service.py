from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.prompt_gateway_service import (
    PROMPT_GATEWAY_EVALUATE_SCOPE,
    PROMPT_GATEWAY_OPS_SCOPE,
    PromptGatewayAccessPolicy,
    PromptGatewayPrincipal,
    PromptGatewayRuntime,
    PromptGatewayServiceError,
    load_prompt_gateway_access_policy,
)

PROMPT_GATEWAY_SERVICE_ID = "prompt-gateway-service"


@dataclass(frozen=True, slots=True)
class PromptGatewayServiceResponse:
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
        path="/v1/prompt-gateway/evaluate",
        scope=PROMPT_GATEWAY_EVALUATE_SCOPE,
        purpose="prompt_redaction_budget_context_and_human_review_gate",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/prompt-gateway/health",
        scope=PROMPT_GATEWAY_OPS_SCOPE,
        purpose="prompt_gateway_health",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/prompt-gateway/metrics",
        scope=PROMPT_GATEWAY_OPS_SCOPE,
        purpose="prompt_gateway_metrics",
    ),
)


@dataclass(frozen=True, slots=True)
class PromptGatewayServiceConfig:
    ai_root: Path
    auth_enabled: bool = True

    @classmethod
    def from_paths(
        cls,
        *,
        ai_root: Path | str | None = None,
        auth_enabled: bool = True,
    ) -> PromptGatewayServiceConfig:
        return cls(
            ai_root=Path(ai_root) if ai_root is not None else default_ai_root(),
            auth_enabled=auth_enabled,
        )


class PromptGatewayService:
    """Policy-enforced service boundary around AI Platform prompt gateway runtime."""

    def __init__(self, config: PromptGatewayServiceConfig) -> None:
        self.config = config
        self.access_policy: PromptGatewayAccessPolicy | None = (
            load_prompt_gateway_access_policy(config.ai_root) if config.auth_enabled else None
        )
        self.runtime = PromptGatewayRuntime(config.ai_root)

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        principal_id: str | None = None,
        requested_scopes: Sequence[str] | None = None,
        principal: PromptGatewayPrincipal | Mapping[str, Any] | None = None,
    ) -> PromptGatewayServiceResponse:
        route = normalize_route(method, path)
        route_scope = route_scope_index().get(route)
        if route_scope is None:
            return PromptGatewayServiceResponse(
                status_code=404,
                body={
                    "errorCode": "not_found",
                    "errorMessage": f"route not found: {method.upper()} {path}",
                },
            )
        resolved_principal = principal
        if self.config.auth_enabled and resolved_principal is None:
            if principal_id is None:
                return PromptGatewayServiceResponse(
                    status_code=401,
                    body={
                        "errorCode": "auth_required",
                        "errorMessage": "prompt gateway principal is required",
                    },
                )
            try:
                resolved_principal = self.resolve_principal(
                    principal_id,
                    requested_scopes=requested_scopes or (route_scope,),
                )
            except PromptGatewayServiceError as exc:
                return error_response(403, "principal_policy_forbidden", str(exc))

        try:
            if route == ("POST", "/v1/prompt-gateway/evaluate"):
                return self.evaluate(body, resolved_principal)
            if route == ("GET", "/v1/prompt-gateway/health"):
                return self.health()
            if route == ("GET", "/v1/prompt-gateway/metrics"):
                return self.metrics()
        except PromptGatewayServiceError as exc:
            return error_response(400, "bad_request", str(exc))
        except Exception as exc:
            return error_response(500, "prompt_gateway_service_failed", str(exc))

        return error_response(500, "route_not_implemented", f"route is not implemented: {path}")

    def evaluate(
        self,
        body: Mapping[str, Any] | None,
        principal: PromptGatewayPrincipal | Mapping[str, Any] | None,
    ) -> PromptGatewayServiceResponse:
        if body is None:
            return error_response(400, "bad_request", "request body must be a JSON object")
        return PromptGatewayServiceResponse(
            status_code=200,
            body=self.runtime.evaluate(body, principal).to_dict(),
        )

    def health(self) -> PromptGatewayServiceResponse:
        return PromptGatewayServiceResponse(status_code=200, body=self.runtime.health())

    def metrics(self) -> PromptGatewayServiceResponse:
        return PromptGatewayServiceResponse(
            status_code=200,
            body={"metrics": self.runtime.snapshot_metrics().to_dict()},
        )

    def resolve_principal(
        self,
        principal_id: str,
        *,
        requested_scopes: Sequence[str],
    ) -> PromptGatewayPrincipal:
        if self.access_policy is None:
            raise PromptGatewayServiceError("prompt gateway access policy is disabled")
        return self.access_policy.resolve_principal(principal_id, requested_scopes)


def build_service_manifest() -> dict[str, Any]:
    return {
        "serviceId": PROMPT_GATEWAY_SERVICE_ID,
        "owner": "ai-platform",
        "status": "service_package_ready",
        "runtime": {
            "entrypoint": "courseflow_prompt_gateway_service.cli:main",
            "language": "python",
        },
        "security": {
            "defaultAuth": "policy_enforced",
            "policyArtifacts": [
                "platform/governance/policies/ai-governance-policy.yaml",
                "platform/governance/policies/prompt-gateway-access-policy.yaml",
            ],
        },
        "observability": {
            "metrics": "in_memory_prompt_evaluation_block_error_counters",
            "tenantSafety": "cross_tenant_context_filtered_before_prompt_assembly",
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


def error_response(
    status_code: int,
    error_code: str,
    message: str,
) -> PromptGatewayServiceResponse:
    return PromptGatewayServiceResponse(
        status_code=status_code,
        body={
            "errorCode": error_code,
            "errorMessage": message,
        },
    )


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[4]
