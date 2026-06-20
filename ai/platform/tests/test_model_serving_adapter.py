from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.model_audit import JsonlModelAuditStore
from courseflow_ai_platform.model_serving_adapter import (
    ModelServingHostedAdapter,
    normalize_route,
)
from courseflow_ai_platform.model_serving_auth import (
    MODEL_SERVING_CATALOG_SCOPE,
    MODEL_SERVING_INVOKE_SCOPE,
    MODEL_SERVING_OPS_SCOPE,
    ServingAuthPolicy,
    ServingPrincipal,
    load_serving_auth_policy,
)


def demand_forecast_http_body() -> dict[str, object]:
    return {
        "requestId": "req-http-1001",
        "tenantId": "tenant-ops",
        "modelId": "operations-demand-forecast-baseline-v1",
        "payload": {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-http-1001",
            "queue_id": "support-identity",
            "historical_demand": [78, 82, 84, 96, 114, 132],
            "planned_capacity": 110,
            "backlog_open_items": 28,
            "avg_handle_minutes": 52,
            "seasonal_index": 1.08,
            "special_event": True,
            "incident_open": True,
            "forecast_horizon_days": 7,
            "service_level_target": 0.92,
            "operator_email": "ops.owner@example.com",
        },
    }


def test_hosted_adapter_catalog_exposes_serveable_models() -> None:
    adapter = ModelServingHostedAdapter(Path(__file__).resolve().parents[2])

    response = adapter.handle_request("GET", "/v1/models")
    model_ids = {row["modelId"] for row in response.body["models"]}

    assert response.status_code == 200
    assert "operations-demand-forecast-baseline-v1" in model_ids
    assert "support-agent-assist-baseline-v1" in model_ids
    assert "recommendation-item-cf-v1" not in model_ids


def test_hosted_adapter_invokes_model_persists_audit_and_updates_cockpit(
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "model-audit.jsonl"
    adapter = ModelServingHostedAdapter(
        Path(__file__).resolve().parents[2],
        audit_log_path=audit_path,
        audit_retention_days=7,
    )

    response = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        demand_forecast_http_body(),
    )
    metrics = adapter.handle_request("GET", "/v1/model-serving/metrics")
    health = adapter.handle_request("GET", "/v1/model-serving/health")
    cockpit = adapter.handle_request("GET", "/v1/model-serving/cockpit")
    product_readiness = adapter.handle_request(
        "GET",
        "/v1/model-serving/product-readiness",
    )
    persisted_records = JsonlModelAuditStore(audit_path).list_records()

    assert response.status_code == 200
    assert response.body["status"] == "ok"
    assert response.body["requestId"] == "req-http-1001"
    assert response.body["output"]["demandBand"] == "high"
    assert len(persisted_records) == 1
    assert persisted_records[0].request_id == "req-http-1001"
    assert "ops.owner@example.com" not in persisted_records[0].audit_payload
    assert metrics.body["metrics"]["requestCount"] == 1
    assert metrics.body["metrics"]["auditRecordCount"] == 1
    assert health.status_code == 200
    assert health.body["status"] == "healthy"
    assert cockpit.body["summary"]["serving_status"] == "healthy"
    assert cockpit.body["summary"]["serving_metrics_connected"] is True
    assert cockpit.body["summary"]["serving_request_count"] == 1
    assert all(
        action["action_type"] != "connect_serving_metrics_export"
        for action in cockpit.body["actions"]
    )
    assert product_readiness.status_code == 200
    assert product_readiness.body["report_id"] == "ai-platform-product-readiness-v1"
    assert product_readiness.body["summary"]["readiness_status"] == (
        "stakeholder_ready_with_followups"
    )
    assert product_readiness.body["summary"]["serving_metrics_connected"] is True
    assert product_readiness.body["summary"]["serving_request_count"] == 1
    assert product_readiness.body["summary"]["serving_audit_record_count"] == 1
    assert product_readiness.body["summary"]["serving_error_count"] == 0
    assert (
        "governance_response_runbook_accepted"
        in product_readiness.body["action_queue"]["passed"]
    )


def test_hosted_adapter_returns_bad_request_for_invalid_envelope() -> None:
    adapter = ModelServingHostedAdapter(Path(__file__).resolve().parents[2])

    response = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        {"tenantId": "tenant-ops", "payload": {}},
    )

    assert response.status_code == 400
    assert response.body["errorCode"] == "bad_request"
    assert "model_id or modelId" in response.body["errorMessage"]
    assert adapter.snapshot_metrics().request_count == 0


def test_hosted_adapter_surfaces_unknown_model_as_gateway_error() -> None:
    adapter = ModelServingHostedAdapter(Path(__file__).resolve().parents[2])

    response = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        {
            "requestId": "req-http-404",
            "tenantId": "tenant-ops",
            "modelId": "missing-model",
            "payload": {"tenant_id": "tenant-ops"},
        },
    )
    health = adapter.handle_request("GET", "/v1/model-serving/health")

    assert response.status_code == 502
    assert response.body["status"] == "error"
    assert response.body["errorCode"] == "model_invocation_failed"
    assert health.status_code == 503
    assert health.body["status"] == "degraded_by_model_serving_errors"


def test_hosted_adapter_routes_not_found() -> None:
    adapter = ModelServingHostedAdapter(Path(__file__).resolve().parents[2])

    response = adapter.handle_request("GET", "/missing")

    assert response.status_code == 404
    assert response.body["errorCode"] == "not_found"
    assert normalize_route("get", "v1/models") == ("GET", "/v1/models")


def test_hosted_adapter_enforces_auth_scope_tenant_and_model_policy() -> None:
    adapter = ModelServingHostedAdapter(
        Path(__file__).resolve().parents[2],
        auth_policy=ServingAuthPolicy.enforced(),
    )
    invoke_principal = ServingPrincipal(
        principal_id="svc-ops-forecast",
        scopes=(MODEL_SERVING_INVOKE_SCOPE,),
        tenant_ids=("tenant-ops",),
        allowed_model_ids=("operations-demand-forecast-baseline-v1",),
    )

    missing_principal = adapter.handle_request("GET", "/v1/models")
    catalog_denied = adapter.handle_request(
        "GET",
        "/v1/models",
        principal=invoke_principal,
    )
    invoke_allowed = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        demand_forecast_http_body(),
        principal=invoke_principal,
    )
    tenant_denied = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        {
            **demand_forecast_http_body(),
            "tenantId": "tenant-finance",
        },
        principal=invoke_principal,
    )
    model_denied = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        {
            **demand_forecast_http_body(),
            "modelId": "finance-payment-fraud-baseline-v1",
        },
        principal=invoke_principal,
    )

    assert missing_principal.status_code == 401
    assert missing_principal.body["errorCode"] == "auth_required"
    assert catalog_denied.status_code == 403
    assert catalog_denied.body["errorCode"] == "scope_forbidden"
    assert invoke_allowed.status_code == 200
    assert tenant_denied.status_code == 403
    assert tenant_denied.body["errorCode"] == "tenant_forbidden"
    assert model_denied.status_code == 403
    assert model_denied.body["errorCode"] == "model_forbidden"
    assert adapter.snapshot_metrics().request_count == 1
    security = adapter.snapshot_security_telemetry()
    assert security.denial_count == 4
    assert security.by_reason == {
        "auth_required": 1,
        "model_forbidden": 1,
        "scope_forbidden": 1,
        "tenant_forbidden": 1,
    }
    assert security.by_route == {
        "GET /v1/models": 2,
        "POST /v1/model-invocations": 2,
    }


def test_hosted_adapter_rejects_payload_tenant_mismatch_and_wildcard_scope() -> None:
    adapter = ModelServingHostedAdapter(
        Path(__file__).resolve().parents[2],
        auth_policy=ServingAuthPolicy.enforced(),
    )
    invoke_principal = {
        "principalId": "svc-ops-forecast",
        "scopes": [MODEL_SERVING_INVOKE_SCOPE],
        "tenantIds": ["tenant-ops"],
    }

    mismatch = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        {
            **demand_forecast_http_body(),
            "payload": {
                **demand_forecast_http_body()["payload"],
                "tenant_id": "tenant-finance",
            },
        },
        principal=invoke_principal,
    )
    wildcard = adapter.handle_request(
        "GET",
        "/v1/models",
        principal={"principalId": "svc-wide", "scope": "*", "tenantIds": ["tenant-ops"]},
    )

    assert mismatch.status_code == 403
    assert mismatch.body["errorCode"] == "tenant_mismatch"
    assert wildcard.status_code == 403
    assert wildcard.body["errorCode"] == "wildcard_scope_forbidden"
    assert adapter.snapshot_metrics().request_count == 0
    security = adapter.snapshot_security_telemetry()
    assert security.denial_count == 2
    assert security.by_reason == {
        "tenant_mismatch": 1,
        "wildcard_scope_forbidden": 1,
    }


def test_hosted_adapter_separates_ops_scope_from_invoke_scope() -> None:
    adapter = ModelServingHostedAdapter(
        Path(__file__).resolve().parents[2],
        auth_policy=load_serving_auth_policy(Path(__file__).resolve().parents[2]),
    )
    invoke_principal = {
        "principalId": "svc-ops-forecast",
        "scope": MODEL_SERVING_INVOKE_SCOPE,
        "tenantIds": ["tenant-ops"],
    }
    ops_principal = {
        "principalId": "svc-ai-ops",
        "scopes": [MODEL_SERVING_OPS_SCOPE, MODEL_SERVING_CATALOG_SCOPE],
    }

    metrics_denied = adapter.handle_request(
        "GET",
        "/v1/model-serving/metrics",
        principal=invoke_principal,
    )
    product_readiness_denied = adapter.handle_request(
        "GET",
        "/v1/model-serving/product-readiness",
        principal=invoke_principal,
    )
    metrics_allowed = adapter.handle_request(
        "GET",
        "/v1/model-serving/metrics",
        principal=ops_principal,
    )
    product_readiness_allowed = adapter.handle_request(
        "GET",
        "/v1/model-serving/product-readiness",
        principal=ops_principal,
    )
    catalog_allowed = adapter.handle_request(
        "GET",
        "/v1/models",
        principal=ops_principal,
    )

    assert metrics_denied.status_code == 403
    assert metrics_denied.body["errorCode"] == "scope_forbidden"
    assert product_readiness_denied.status_code == 403
    assert product_readiness_denied.body["errorCode"] == "scope_forbidden"
    assert metrics_allowed.status_code == 200
    assert product_readiness_allowed.status_code == 200
    assert product_readiness_allowed.body["report_id"] == (
        "ai-platform-product-readiness-v1"
    )
    assert metrics_allowed.body["securityTelemetry"]["denialCount"] == 2
    assert metrics_allowed.body["securityTelemetry"]["byReason"] == {"scope_forbidden": 2}
    assert metrics_allowed.body["securityTelemetry"]["byRoute"] == {
        "GET /v1/model-serving/metrics": 1,
        "GET /v1/model-serving/product-readiness": 1,
    }
    assert catalog_allowed.status_code == 200


def test_hosted_adapter_records_invalid_principal_security_telemetry() -> None:
    adapter = ModelServingHostedAdapter(
        Path(__file__).resolve().parents[2],
        auth_policy=ServingAuthPolicy.enforced(),
    )

    response = adapter.handle_request(
        "GET",
        "/v1/models",
        principal={"scopes": [MODEL_SERVING_CATALOG_SCOPE]},
    )

    assert response.status_code == 401
    assert response.body["errorCode"] == "invalid_principal"
    assert adapter.snapshot_security_telemetry().to_dict() == {
        "byReason": {"invalid_principal": 1},
        "byRoute": {"GET /v1/models": 1},
        "byStatusCode": {"401": 1},
        "denialCount": 1,
    }
