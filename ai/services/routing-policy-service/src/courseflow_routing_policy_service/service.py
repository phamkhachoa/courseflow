from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.routing_policy_service import (
    ROUTING_POLICY_OPS_SCOPE,
    ROUTING_POLICY_RECOMMEND_SCOPE,
    RoutingPolicyAccessPolicy,
    RoutingPolicyPrincipal,
    RoutingPolicyPrivacyError,
    RoutingPolicyRuntime,
    RoutingPolicyServiceError,
    load_routing_policy_access_policy,
)

ROUTING_POLICY_SERVICE_ID = "routing-policy-service"


@dataclass(frozen=True, slots=True)
class RoutingPolicyServiceResponse:
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
        path="/v1/routing-policy/recommend",
        scope=ROUTING_POLICY_RECOMMEND_SCOPE,
        purpose="constrained_routing_policy_recommendation",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/routing-policy/health",
        scope=ROUTING_POLICY_OPS_SCOPE,
        purpose="routing_policy_health",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/routing-policy/metrics",
        scope=ROUTING_POLICY_OPS_SCOPE,
        purpose="routing_policy_metrics",
    ),
)


@dataclass(frozen=True, slots=True)
class RoutingPolicyServiceConfig:
    ai_root: Path
    auth_enabled: bool = True

    @classmethod
    def from_paths(
        cls,
        *,
        ai_root: Path | str | None = None,
        auth_enabled: bool = True,
    ) -> RoutingPolicyServiceConfig:
        return cls(
            ai_root=Path(ai_root) if ai_root is not None else default_ai_root(),
            auth_enabled=auth_enabled,
        )


class RoutingPolicyService:
    """Policy-enforced service boundary around routing-policy simulator runtime."""

    def __init__(self, config: RoutingPolicyServiceConfig) -> None:
        self.config = config
        self.access_policy: RoutingPolicyAccessPolicy | None = (
            load_routing_policy_access_policy(config.ai_root)
            if config.auth_enabled
            else None
        )
        self.runtime = RoutingPolicyRuntime(config.ai_root)

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        principal_id: str | None = None,
        requested_scopes: Sequence[str] | None = None,
        principal: RoutingPolicyPrincipal | Mapping[str, Any] | None = None,
    ) -> RoutingPolicyServiceResponse:
        route = normalize_route(method, path)
        route_scope = route_scope_index().get(route)
        if route_scope is None:
            return RoutingPolicyServiceResponse(
                status_code=404,
                body={
                    "errorCode": "not_found",
                    "errorMessage": f"route not found: {method.upper()} {path}",
                },
            )
        resolved_principal = principal
        if self.config.auth_enabled and resolved_principal is None:
            if principal_id is None:
                return RoutingPolicyServiceResponse(
                    status_code=401,
                    body={
                        "errorCode": "auth_required",
                        "errorMessage": "routing policy principal is required",
                    },
                )
            try:
                resolved_principal = self.resolve_principal(
                    principal_id,
                    requested_scopes=requested_scopes or (route_scope,),
                )
            except RoutingPolicyServiceError as exc:
                return error_response(403, "principal_policy_forbidden", str(exc))

        try:
            if route == ("POST", "/v1/routing-policy/recommend"):
                return self.recommend(body, resolved_principal)
            if route == ("GET", "/v1/routing-policy/health"):
                return self.health()
            if route == ("GET", "/v1/routing-policy/metrics"):
                return self.metrics()
        except RoutingPolicyPrivacyError as exc:
            return error_response(403, "privacy_control_violation", str(exc))
        except RoutingPolicyServiceError as exc:
            return error_response(400, "bad_request", str(exc))
        except Exception as exc:
            return error_response(500, "routing_policy_service_failed", str(exc))

        return error_response(
            500,
            "route_not_implemented",
            f"route is not implemented: {path}",
        )

    def recommend(
        self,
        body: Mapping[str, Any] | None,
        principal: RoutingPolicyPrincipal | Mapping[str, Any] | None,
    ) -> RoutingPolicyServiceResponse:
        if body is None:
            return error_response(
                400,
                "bad_request",
                "request body must be a JSON object",
            )
        return RoutingPolicyServiceResponse(
            status_code=200,
            body=self.runtime.recommend(body, principal).to_dict(),
        )

    def health(self) -> RoutingPolicyServiceResponse:
        return RoutingPolicyServiceResponse(status_code=200, body=self.runtime.health())

    def metrics(self) -> RoutingPolicyServiceResponse:
        return RoutingPolicyServiceResponse(
            status_code=200,
            body={"metrics": self.runtime.snapshot_metrics().to_dict()},
        )

    def resolve_principal(
        self,
        principal_id: str,
        *,
        requested_scopes: Sequence[str],
    ) -> RoutingPolicyPrincipal:
        if self.access_policy is None:
            raise RoutingPolicyServiceError("routing policy access policy is disabled")
        return self.access_policy.resolve_principal(principal_id, requested_scopes)


def build_service_manifest() -> dict[str, Any]:
    return {
        "serviceId": ROUTING_POLICY_SERVICE_ID,
        "owner": "ai-platform",
        "status": "service_package_ready",
        "runtime": {
            "entrypoint": "courseflow_routing_policy_service.cli:main",
            "language": "python",
        },
        "security": {
            "defaultAuth": "policy_enforced",
            "policyArtifacts": [
                "platform/governance/policies/ai-governance-policy.yaml",
                "platform/governance/policies/routing-policy-access-policy.yaml",
            ],
        },
        "observability": {
            "metrics": (
                "in_memory_recommendation_error_identifier_constraint_"
                "exploration_counters"
            ),
            "tenantSafety": "cross_tenant_routing_policy_forbidden",
        },
        "routes": [route.to_dict() for route in SERVICE_ROUTES],
    }


def route_scope_index() -> dict[tuple[str, str], str]:
    return {(route.method, route.path): route.scope for route in SERVICE_ROUTES}


def normalize_route(method: str, path: str) -> tuple[str, str]:
    return method.upper(), "/" + path.strip("/")


def error_response(
    status_code: int,
    error_code: str,
    message: str,
) -> RoutingPolicyServiceResponse:
    return RoutingPolicyServiceResponse(
        status_code=status_code,
        body={
            "errorCode": error_code,
            "errorMessage": message,
        },
    )


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[4]
