from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.governance_evaluation_service import (
    GOVERNANCE_EVALUATION_ASSESS_SCOPE,
    GOVERNANCE_EVALUATION_OPS_SCOPE,
    GovernanceEvaluationAccessPolicy,
    GovernanceEvaluationPrincipal,
    GovernanceEvaluationPrivacyError,
    GovernanceEvaluationRuntime,
    GovernanceEvaluationServiceError,
    load_governance_evaluation_access_policy,
)

GOVERNANCE_EVALUATION_SERVICE_ID = "governance-evaluation-service"


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationServiceResponse:
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
        path="/v1/governance-evaluation/assess",
        scope=GOVERNANCE_EVALUATION_ASSESS_SCOPE,
        purpose="release_promotion_safety_evaluation_assessment",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/governance-evaluation/health",
        scope=GOVERNANCE_EVALUATION_OPS_SCOPE,
        purpose="governance_evaluation_health",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/governance-evaluation/metrics",
        scope=GOVERNANCE_EVALUATION_OPS_SCOPE,
        purpose="governance_evaluation_metrics",
    ),
)


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationServiceConfig:
    ai_root: Path
    auth_enabled: bool = True

    @classmethod
    def from_paths(
        cls,
        *,
        ai_root: Path | str | None = None,
        auth_enabled: bool = True,
    ) -> GovernanceEvaluationServiceConfig:
        return cls(
            ai_root=Path(ai_root) if ai_root is not None else default_ai_root(),
            auth_enabled=auth_enabled,
        )


class GovernanceEvaluationService:
    """Policy-enforced service boundary around AI governance evaluation."""

    def __init__(self, config: GovernanceEvaluationServiceConfig) -> None:
        self.config = config
        self.access_policy: GovernanceEvaluationAccessPolicy | None = (
            load_governance_evaluation_access_policy(config.ai_root)
            if config.auth_enabled
            else None
        )
        self.runtime = GovernanceEvaluationRuntime(config.ai_root)

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        principal_id: str | None = None,
        requested_scopes: Sequence[str] | None = None,
        principal: GovernanceEvaluationPrincipal | Mapping[str, Any] | None = None,
    ) -> GovernanceEvaluationServiceResponse:
        route = normalize_route(method, path)
        route_scope = route_scope_index().get(route)
        if route_scope is None:
            return GovernanceEvaluationServiceResponse(
                status_code=404,
                body={
                    "errorCode": "not_found",
                    "errorMessage": f"route not found: {method.upper()} {path}",
                },
            )
        resolved_principal = principal
        if self.config.auth_enabled and resolved_principal is None:
            if principal_id is None:
                return GovernanceEvaluationServiceResponse(
                    status_code=401,
                    body={
                        "errorCode": "auth_required",
                        "errorMessage": "Governance evaluation principal is required",
                    },
                )
            try:
                resolved_principal = self.resolve_principal(
                    principal_id,
                    requested_scopes=requested_scopes or (route_scope,),
                )
            except GovernanceEvaluationServiceError as exc:
                return error_response(403, "principal_policy_forbidden", str(exc))

        try:
            if route == ("POST", "/v1/governance-evaluation/assess"):
                return self.assess(body, resolved_principal)
            if route == ("GET", "/v1/governance-evaluation/health"):
                return self.health()
            if route == ("GET", "/v1/governance-evaluation/metrics"):
                return self.metrics()
        except GovernanceEvaluationPrivacyError as exc:
            return error_response(403, "privacy_control_violation", str(exc))
        except GovernanceEvaluationServiceError as exc:
            return error_response(400, "bad_request", str(exc))
        except Exception as exc:
            return error_response(500, "governance_evaluation_service_failed", str(exc))

        return error_response(500, "route_not_implemented", f"route is not implemented: {path}")

    def assess(
        self,
        body: Mapping[str, Any] | None,
        principal: GovernanceEvaluationPrincipal | Mapping[str, Any] | None,
    ) -> GovernanceEvaluationServiceResponse:
        if body is None:
            return error_response(400, "bad_request", "request body must be a JSON object")
        return GovernanceEvaluationServiceResponse(
            status_code=200,
            body=self.runtime.assess(body, principal).to_dict(),
        )

    def health(self) -> GovernanceEvaluationServiceResponse:
        return GovernanceEvaluationServiceResponse(status_code=200, body=self.runtime.health())

    def metrics(self) -> GovernanceEvaluationServiceResponse:
        return GovernanceEvaluationServiceResponse(
            status_code=200,
            body={"metrics": self.runtime.snapshot_metrics().to_dict()},
        )

    def resolve_principal(
        self,
        principal_id: str,
        *,
        requested_scopes: Sequence[str],
    ) -> GovernanceEvaluationPrincipal:
        if self.access_policy is None:
            raise GovernanceEvaluationServiceError(
                "governance evaluation access policy is disabled"
            )
        return self.access_policy.resolve_principal(principal_id, requested_scopes)


def build_service_manifest() -> dict[str, Any]:
    return {
        "serviceId": GOVERNANCE_EVALUATION_SERVICE_ID,
        "owner": "ai-platform",
        "status": "service_package_ready",
        "runtime": {
            "entrypoint": "courseflow_governance_evaluation_service.cli:main",
            "language": "python",
        },
        "security": {
            "defaultAuth": "policy_enforced",
            "policyArtifacts": [
                "platform/governance/policies/ai-governance-policy.yaml",
                "platform/governance/policies/governance-evaluation-access-policy.yaml",
            ],
        },
        "observability": {
            "metrics": "in_memory_assessment_decision_error_identifier_secret_counters",
            "tenantSafety": "cross_tenant_governance_assessment_forbidden",
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
) -> GovernanceEvaluationServiceResponse:
    return GovernanceEvaluationServiceResponse(
        status_code=status_code,
        body={
            "errorCode": error_code,
            "errorMessage": message,
        },
    )


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[4]
