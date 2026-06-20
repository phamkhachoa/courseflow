from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.model_audit import JsonlModelAuditStore, ModelAuditStore
from courseflow_ai_platform.model_serving import (
    ModelServingError,
    ModelServingGateway,
    ModelServingGatewayResponse,
    ModelServingMetricsSnapshot,
    safe_error_message,
)
from courseflow_ai_platform.model_serving_auth import (
    ServingAuthPolicy,
    ServingAuthTelemetry,
    ServingAuthTelemetrySnapshot,
    ServingPrincipal,
    authorize_serving_request,
)
from courseflow_ai_platform.operating_cockpit import (
    build_operating_cockpit_snapshot,
    build_serving_health_report_from_metrics,
)
from courseflow_ai_platform.product_readiness import (
    build_ai_platform_product_readiness_snapshot,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml


@dataclass(frozen=True, slots=True)
class ModelServingAdapterResponse:
    status_code: int
    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body,
            "statusCode": self.status_code,
        }


class ModelServingHostedAdapter:
    """Framework-neutral hosted serving adapter for HTTP/gRPC wrappers."""

    def __init__(
        self,
        ai_root: Path | str,
        *,
        audit_store: ModelAuditStore | None = None,
        audit_log_path: Path | str | None = None,
        audit_retention_days: int = 30,
        audit_failure_mode: str = "fail_open",
        auth_policy: ServingAuthPolicy | None = None,
        fallback_outputs: Mapping[str, dict[str, Any]] | None = None,
    ) -> None:
        if audit_store is not None and audit_log_path is not None:
            raise ModelServingError("configure either audit_store or audit_log_path, not both")
        self.ai_root = Path(ai_root)
        self.auth_policy = auth_policy
        self.security_telemetry = ServingAuthTelemetry()
        configured_audit_store = (
            JsonlModelAuditStore(audit_log_path) if audit_log_path is not None else audit_store
        )
        self.gateway = ModelServingGateway(
            self.ai_root,
            fallback_outputs=fallback_outputs,
            audit_store=configured_audit_store,
            audit_retention_days=audit_retention_days,
            audit_failure_mode=audit_failure_mode,
        )

    def handle_request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        principal: ServingPrincipal | Mapping[str, Any] | None = None,
    ) -> ModelServingAdapterResponse:
        route = normalize_route(method, path)
        if route not in MODEL_SERVING_ADAPTER_ROUTES:
            return ModelServingAdapterResponse(
                status_code=404,
                body={
                    "errorCode": "not_found",
                    "errorMessage": f"route not found: {method.upper()} {path}",
                },
            )
        auth_response = self.authorize(route, body, principal)
        if auth_response is not None:
            return auth_response
        try:
            if route == ("GET", "/v1/models"):
                return self.catalog()
            if route == ("POST", "/v1/model-invocations"):
                return self.invoke(body)
            if route == ("GET", "/v1/model-serving/metrics"):
                return self.metrics()
            if route == ("GET", "/v1/model-serving/health"):
                return self.health()
            if route == ("GET", "/v1/model-serving/cockpit"):
                return self.cockpit()
            if route == ("GET", "/v1/model-serving/product-readiness"):
                return self.product_readiness()
        except Exception as exc:
            return ModelServingAdapterResponse(
                status_code=500,
                body={
                    "errorCode": "model_serving_adapter_failed",
                    "errorMessage": safe_error_message(exc),
                },
            )

        return ModelServingAdapterResponse(
            status_code=500,
            body={
                "errorCode": "route_not_implemented",
                "errorMessage": f"route is registered but not implemented: {method.upper()} {path}",
            },
        )

    def authorize(
        self,
        route: tuple[str, str],
        body: Mapping[str, Any] | None,
        principal: ServingPrincipal | Mapping[str, Any] | None,
    ) -> ModelServingAdapterResponse | None:
        if self.auth_policy is None:
            return None
        try:
            decision = authorize_serving_request(
                route=route,
                principal=principal,
                request_body=body,
                policy=self.auth_policy,
            )
        except ValueError as exc:
            self.security_telemetry.record_denial(
                route=route,
                status_code=401,
                reason="invalid_principal",
            )
            return auth_error(401, "invalid_principal", safe_error_message(exc))
        if decision.allowed:
            return None
        self.security_telemetry.record_denial(
            route=route,
            status_code=decision.status_code,
            reason=decision.error_code,
        )
        return auth_error(decision.status_code, decision.error_code, decision.error_message)

    def catalog(self) -> ModelServingAdapterResponse:
        return ModelServingAdapterResponse(
            status_code=200,
            body={"models": [model.to_dict() for model in self.gateway.facade.catalog()]},
        )

    def invoke(self, body: Mapping[str, Any] | None) -> ModelServingAdapterResponse:
        if body is None:
            return bad_request("request body must be a JSON object")
        try:
            response = self.gateway.invoke(normalize_gateway_request(body))
        except ModelServingError as exc:
            return bad_request(safe_error_message(exc))
        return ModelServingAdapterResponse(
            status_code=status_code_for_gateway_response(response),
            body=response.to_dict(),
        )

    def metrics(self) -> ModelServingAdapterResponse:
        return ModelServingAdapterResponse(
            status_code=200,
            body={
                "metrics": self.snapshot_metrics().to_dict(),
                "securityTelemetry": self.snapshot_security_telemetry().to_dict(),
            },
        )

    def health(self) -> ModelServingAdapterResponse:
        serving_health = build_serving_health_report_from_metrics(self.snapshot_metrics())
        return ModelServingAdapterResponse(
            status_code=status_code_for_serving_health(serving_health.status),
            body={"servingHealth": serving_health.to_dict(), "status": serving_health.status},
        )

    def cockpit(self, *, generated_at: str | None = None) -> ModelServingAdapterResponse:
        return ModelServingAdapterResponse(
            status_code=200,
            body=build_operating_cockpit_snapshot(
                self.ai_root,
                generated_at=generated_at,
                serving_metrics=self.snapshot_metrics(),
            ),
        )

    def product_readiness(
        self,
        *,
        generated_at: str | None = None,
    ) -> ModelServingAdapterResponse:
        report_date = generated_at or latest_product_readiness_generated_at(self.ai_root)
        snapshot = build_ai_platform_product_readiness_snapshot(
            self.ai_root,
            generated_at=report_date,
            serving_metrics=self.snapshot_metrics(),
        )
        return ModelServingAdapterResponse(
            status_code=200,
            body=snapshot,
        )

    def snapshot_metrics(self) -> ModelServingMetricsSnapshot:
        return self.gateway.snapshot_metrics()

    def snapshot_security_telemetry(self) -> ServingAuthTelemetrySnapshot:
        return self.security_telemetry.snapshot()


def normalize_route(method: str, path: str) -> tuple[str, str]:
    normalized_path = "/" + path.strip("/")
    return method.upper(), normalized_path


MODEL_SERVING_ADAPTER_ROUTES = {
    ("GET", "/v1/models"),
    ("POST", "/v1/model-invocations"),
    ("GET", "/v1/model-serving/metrics"),
    ("GET", "/v1/model-serving/health"),
    ("GET", "/v1/model-serving/cockpit"),
    ("GET", "/v1/model-serving/product-readiness"),
}


def normalize_gateway_request(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "fallback_output": row.get("fallback_output", row.get("fallbackOutput")),
        "model_id": required_adapter_str(row, "model_id", "modelId"),
        "payload": required_adapter_mapping(row, "payload"),
        "request_id": required_adapter_str(row, "request_id", "requestId"),
        "tenant_id": required_adapter_str(row, "tenant_id", "tenantId"),
    }


def required_adapter_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise ModelServingError(
            f"model serving adapter request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def required_adapter_mapping(row: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise ModelServingError(f"model serving adapter request {key} must be a mapping")
    return value


def bad_request(message: str) -> ModelServingAdapterResponse:
    return ModelServingAdapterResponse(
        status_code=400,
        body={
            "errorCode": "bad_request",
            "errorMessage": message,
        },
    )


def auth_error(status_code: int, error_code: str, message: str) -> ModelServingAdapterResponse:
    return ModelServingAdapterResponse(
        status_code=status_code,
        body={
            "errorCode": error_code,
            "errorMessage": message,
        },
    )


def status_code_for_gateway_response(response: ModelServingGatewayResponse) -> int:
    if response.status in {"ok", "fallback"}:
        return 200
    if response.error_code == "model_audit_failed":
        return 503
    return 502


def status_code_for_serving_health(status: str) -> int:
    if status in {"healthy", "no_serving_traffic"}:
        return 200
    if status == "attention_required_audit_gap":
        return 202
    return 503


def latest_product_readiness_generated_at(ai_root: Path) -> str | None:
    freshness_path = (
        ai_root
        / "platform"
        / "product"
        / "reports"
        / "ai-platform-product-readiness-freshness-v1.yaml"
    )
    try:
        payload = load_yaml(freshness_path)
    except RegistryValidationError:
        return None
    summary = payload.get("summary", {})
    if isinstance(summary, dict):
        runtime_generated_at = summary.get("runtime_generated_at")
        if isinstance(runtime_generated_at, str) and runtime_generated_at.strip():
            return runtime_generated_at.strip()
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str) and generated_at.strip():
        return generated_at.strip()
    return None
