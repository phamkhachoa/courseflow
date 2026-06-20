from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.retrieval_service import (
    RETRIEVAL_CATALOG_SCOPE,
    RETRIEVAL_OPS_SCOPE,
    RETRIEVAL_SEARCH_SCOPE,
    RetrievalAccessPolicy,
    RetrievalPrincipal,
    RetrievalRuntime,
    RetrievalServiceError,
    load_retrieval_access_policy,
)

RETRIEVAL_SERVICE_ID = "retrieval-service"


@dataclass(frozen=True, slots=True)
class RetrievalServiceResponse:
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
        method="GET",
        path="/v1/retrieval/collections",
        scope=RETRIEVAL_CATALOG_SCOPE,
        purpose="collection_catalog",
    ),
    ServiceRoute(
        method="POST",
        path="/v1/retrieval/search",
        scope=RETRIEVAL_SEARCH_SCOPE,
        purpose="lexical_vector_hybrid_search",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/retrieval/health",
        scope=RETRIEVAL_OPS_SCOPE,
        purpose="retrieval_health",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/retrieval/metrics",
        scope=RETRIEVAL_OPS_SCOPE,
        purpose="retrieval_metrics",
    ),
)


@dataclass(frozen=True, slots=True)
class RetrievalServiceConfig:
    ai_root: Path
    auth_enabled: bool = True

    @classmethod
    def from_paths(
        cls,
        *,
        ai_root: Path | str | None = None,
        auth_enabled: bool = True,
    ) -> RetrievalServiceConfig:
        return cls(
            ai_root=Path(ai_root) if ai_root is not None else default_ai_root(),
            auth_enabled=auth_enabled,
        )


class RetrievalService:
    """Policy-enforced service boundary around AI Platform retrieval runtime."""

    def __init__(self, config: RetrievalServiceConfig) -> None:
        self.config = config
        self.access_policy: RetrievalAccessPolicy | None = (
            load_retrieval_access_policy(config.ai_root) if config.auth_enabled else None
        )
        self.runtime = RetrievalRuntime(config.ai_root)

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        principal_id: str | None = None,
        requested_scopes: Sequence[str] | None = None,
        principal: RetrievalPrincipal | Mapping[str, Any] | None = None,
    ) -> RetrievalServiceResponse:
        route = normalize_route(method, path)
        route_scope = route_scope_index().get(route)
        if route_scope is None:
            return RetrievalServiceResponse(
                status_code=404,
                body={
                    "errorCode": "not_found",
                    "errorMessage": f"route not found: {method.upper()} {path}",
                },
            )
        resolved_principal = principal
        if self.config.auth_enabled and resolved_principal is None:
            if principal_id is None:
                return RetrievalServiceResponse(
                    status_code=401,
                    body={
                        "errorCode": "auth_required",
                        "errorMessage": "retrieval principal is required",
                    },
                )
            try:
                resolved_principal = self.resolve_principal(
                    principal_id,
                    requested_scopes=requested_scopes or (route_scope,),
                )
            except RetrievalServiceError as exc:
                return error_response(403, "principal_policy_forbidden", str(exc))

        try:
            if route == ("GET", "/v1/retrieval/collections"):
                return self.catalog()
            if route == ("POST", "/v1/retrieval/search"):
                return self.search(body, resolved_principal)
            if route == ("GET", "/v1/retrieval/health"):
                return self.health()
            if route == ("GET", "/v1/retrieval/metrics"):
                return self.metrics()
        except RetrievalServiceError as exc:
            return error_response(400, "bad_request", str(exc))
        except Exception as exc:
            return error_response(500, "retrieval_service_failed", str(exc))

        return error_response(500, "route_not_implemented", f"route is not implemented: {path}")

    def catalog(self) -> RetrievalServiceResponse:
        return RetrievalServiceResponse(
            status_code=200,
            body={"collections": [collection.to_dict() for collection in self.runtime.catalog()]},
        )

    def search(
        self,
        body: Mapping[str, Any] | None,
        principal: RetrievalPrincipal | Mapping[str, Any] | None,
    ) -> RetrievalServiceResponse:
        if body is None:
            return error_response(400, "bad_request", "request body must be a JSON object")
        return RetrievalServiceResponse(
            status_code=200,
            body=self.runtime.search(body, principal).to_dict(),
        )

    def health(self) -> RetrievalServiceResponse:
        health = self.runtime.health()
        return RetrievalServiceResponse(status_code=200, body=health)

    def metrics(self) -> RetrievalServiceResponse:
        return RetrievalServiceResponse(
            status_code=200,
            body={"metrics": self.runtime.snapshot_metrics().to_dict()},
        )

    def resolve_principal(
        self,
        principal_id: str,
        *,
        requested_scopes: Sequence[str],
    ) -> RetrievalPrincipal:
        if self.access_policy is None:
            raise RetrievalServiceError("retrieval access policy is disabled")
        return self.access_policy.resolve_principal(principal_id, requested_scopes)


def build_service_manifest() -> dict[str, Any]:
    return {
        "serviceId": RETRIEVAL_SERVICE_ID,
        "owner": "ai-platform",
        "status": "service_package_ready",
        "runtime": {
            "entrypoint": "courseflow_retrieval_service.cli:main",
            "language": "python",
        },
        "security": {
            "defaultAuth": "policy_enforced",
            "policyArtifacts": [
                "platform/governance/policies/ai-governance-policy.yaml",
                "platform/governance/policies/retrieval-access-policy.yaml",
            ],
        },
        "observability": {
            "metrics": "in_memory_request_search_error_counters",
            "tenantSafety": "cross_tenant_retrieval_forbidden",
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


def error_response(status_code: int, error_code: str, message: str) -> RetrievalServiceResponse:
    return RetrievalServiceResponse(
        status_code=status_code,
        body={
            "errorCode": error_code,
            "errorMessage": message,
        },
    )


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[4]
