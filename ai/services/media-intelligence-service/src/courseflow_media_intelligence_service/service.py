from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.media_intelligence_service import (
    MEDIA_DOCUMENT_ANALYZE_SCOPE,
    MEDIA_OPS_SCOPE,
    MEDIA_SPEECH_ASSESS_SCOPE,
    MediaIntelligenceAccessPolicy,
    MediaIntelligencePrincipal,
    MediaIntelligenceRuntime,
    MediaIntelligenceServiceError,
    MediaPrivacyControlError,
    load_media_intelligence_access_policy,
)

MEDIA_INTELLIGENCE_SERVICE_ID = "media-intelligence-service"


@dataclass(frozen=True, slots=True)
class MediaIntelligenceServiceResponse:
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
        path="/v1/media-intelligence/document:analyze",
        scope=MEDIA_DOCUMENT_ANALYZE_SCOPE,
        purpose="bounded_ocr_token_document_intelligence",
    ),
    ServiceRoute(
        method="POST",
        path="/v1/media-intelligence/speech:assess",
        scope=MEDIA_SPEECH_ASSESS_SCOPE,
        purpose="transcript_segment_speech_quality_assessment",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/media-intelligence/health",
        scope=MEDIA_OPS_SCOPE,
        purpose="media_intelligence_health",
    ),
    ServiceRoute(
        method="GET",
        path="/v1/media-intelligence/metrics",
        scope=MEDIA_OPS_SCOPE,
        purpose="media_intelligence_metrics",
    ),
)


@dataclass(frozen=True, slots=True)
class MediaIntelligenceServiceConfig:
    ai_root: Path
    auth_enabled: bool = True

    @classmethod
    def from_paths(
        cls,
        *,
        ai_root: Path | str | None = None,
        auth_enabled: bool = True,
    ) -> MediaIntelligenceServiceConfig:
        return cls(
            ai_root=Path(ai_root) if ai_root is not None else default_ai_root(),
            auth_enabled=auth_enabled,
        )


class MediaIntelligenceService:
    """Policy-enforced service boundary around document and speech AI runtimes."""

    def __init__(self, config: MediaIntelligenceServiceConfig) -> None:
        self.config = config
        self.access_policy: MediaIntelligenceAccessPolicy | None = (
            load_media_intelligence_access_policy(config.ai_root) if config.auth_enabled else None
        )
        self.runtime = MediaIntelligenceRuntime(config.ai_root)

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        principal_id: str | None = None,
        requested_scopes: Sequence[str] | None = None,
        principal: MediaIntelligencePrincipal | Mapping[str, Any] | None = None,
    ) -> MediaIntelligenceServiceResponse:
        route = normalize_route(method, path)
        route_scope = route_scope_index().get(route)
        if route_scope is None:
            return MediaIntelligenceServiceResponse(
                status_code=404,
                body={
                    "errorCode": "not_found",
                    "errorMessage": f"route not found: {method.upper()} {path}",
                },
            )
        resolved_principal = principal
        if self.config.auth_enabled and resolved_principal is None:
            if principal_id is None:
                return MediaIntelligenceServiceResponse(
                    status_code=401,
                    body={
                        "errorCode": "auth_required",
                        "errorMessage": "media intelligence principal is required",
                    },
                )
            try:
                resolved_principal = self.resolve_principal(
                    principal_id,
                    requested_scopes=requested_scopes or (route_scope,),
                )
            except MediaIntelligenceServiceError as exc:
                return error_response(403, "principal_policy_forbidden", str(exc))

        try:
            if route == ("POST", "/v1/media-intelligence/document:analyze"):
                return self.analyze_document(body, resolved_principal)
            if route == ("POST", "/v1/media-intelligence/speech:assess"):
                return self.assess_speech(body, resolved_principal)
            if route == ("GET", "/v1/media-intelligence/health"):
                return self.health()
            if route == ("GET", "/v1/media-intelligence/metrics"):
                return self.metrics()
        except MediaPrivacyControlError as exc:
            return error_response(403, "privacy_control_violation", str(exc))
        except MediaIntelligenceServiceError as exc:
            return error_response(400, "bad_request", str(exc))
        except Exception as exc:
            return error_response(500, "media_intelligence_service_failed", str(exc))

        return error_response(500, "route_not_implemented", f"route is not implemented: {path}")

    def analyze_document(
        self,
        body: Mapping[str, Any] | None,
        principal: MediaIntelligencePrincipal | Mapping[str, Any] | None,
    ) -> MediaIntelligenceServiceResponse:
        if body is None:
            return error_response(400, "bad_request", "request body must be a JSON object")
        return MediaIntelligenceServiceResponse(
            status_code=200,
            body=self.runtime.analyze_document(body, principal).to_dict(),
        )

    def assess_speech(
        self,
        body: Mapping[str, Any] | None,
        principal: MediaIntelligencePrincipal | Mapping[str, Any] | None,
    ) -> MediaIntelligenceServiceResponse:
        if body is None:
            return error_response(400, "bad_request", "request body must be a JSON object")
        return MediaIntelligenceServiceResponse(
            status_code=200,
            body=self.runtime.assess_speech(body, principal).to_dict(),
        )

    def health(self) -> MediaIntelligenceServiceResponse:
        return MediaIntelligenceServiceResponse(status_code=200, body=self.runtime.health())

    def metrics(self) -> MediaIntelligenceServiceResponse:
        return MediaIntelligenceServiceResponse(
            status_code=200,
            body={"metrics": self.runtime.snapshot_metrics().to_dict()},
        )

    def resolve_principal(
        self,
        principal_id: str,
        *,
        requested_scopes: Sequence[str],
    ) -> MediaIntelligencePrincipal:
        if self.access_policy is None:
            raise MediaIntelligenceServiceError("media intelligence access policy is disabled")
        return self.access_policy.resolve_principal(principal_id, requested_scopes)


def build_service_manifest() -> dict[str, Any]:
    return {
        "serviceId": MEDIA_INTELLIGENCE_SERVICE_ID,
        "owner": "ai-platform",
        "status": "service_package_ready",
        "runtime": {
            "entrypoint": "courseflow_media_intelligence_service.cli:main",
            "language": "python",
        },
        "security": {
            "defaultAuth": "policy_enforced",
            "policyArtifacts": [
                "platform/governance/policies/ai-governance-policy.yaml",
                "platform/governance/policies/media-privacy-review-policy.yaml",
                "platform/governance/policies/media-intelligence-access-policy.yaml",
            ],
        },
        "observability": {
            "metrics": "in_memory_document_speech_error_privacy_counters",
            "tenantSafety": "cross_tenant_media_intelligence_forbidden",
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
) -> MediaIntelligenceServiceResponse:
    return MediaIntelligenceServiceResponse(
        status_code=status_code,
        body={
            "errorCode": error_code,
            "errorMessage": message,
        },
    )


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[4]
