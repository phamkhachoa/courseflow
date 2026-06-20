from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.model_audit import ModelAuditLedger
from courseflow_ai_platform.model_serving import (
    ModelServingError,
    ModelServingGateway,
    build_model_serving_catalog,
    invoke_model_serving_gateway,
    serve_model,
)


class FailingAuditStore:
    def append(self, record: object) -> None:
        raise ValueError("audit store unavailable")


def demand_forecast_gateway_request() -> dict[str, object]:
    return {
        "request_id": "req-1001",
        "tenant_id": "tenant-ops",
        "model_id": "operations-demand-forecast-baseline-v1",
        "payload": {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-1001",
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


def test_model_serving_catalog_exposes_runtime_baselines() -> None:
    catalog = build_model_serving_catalog(Path(__file__).resolve().parents[2])
    models = {model.model_id: model for model in catalog}

    assert "operations-demand-forecast-baseline-v1" in models
    assert "operations-routing-policy-simulator-v1" in models
    assert "finance-payment-fraud-baseline-v1" in models
    assert "support-agent-assist-baseline-v1" in models
    assert "recommendation-item-cf-v1" not in models
    assert models["operations-routing-policy-simulator-v1"].method == "recommend"
    assert models["support-agent-assist-baseline-v1"].method == "assist"


def test_serves_operations_demand_forecast_by_model_id() -> None:
    result = serve_model(
        Path(__file__).resolve().parents[2],
        "operations-demand-forecast-baseline-v1",
        {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-1001",
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
        },
    )

    assert result.model_id == "operations-demand-forecast-baseline-v1"
    assert result.method == "predict"
    assert result.output["modelId"] == "operations-demand-forecast-baseline-v1"
    assert result.output["demandBand"] == "high"
    assert result.output["staffingRecommendation"] == "trigger_capacity_plan"
    assert result.requires_human_review is True
    assert result.latency_ms >= 0


def test_serves_routing_policy_recommendation_by_model_id() -> None:
    result = serve_model(
        Path(__file__).resolve().parents[2],
        "operations-routing-policy-simulator-v1",
        {
            "tenant_id": "tenant-ops",
            "policy_id": "routing-policy-v1",
            "safe_exploration_budget": 0.0,
            "baseline_queue_id": "queue-general",
            "work_item": {
                "work_item_id": "work-1001",
                "work_type": "identity_outage",
                "priority": "p1",
                "required_skill_ids": ["identity", "integration"],
                "expected_effort_minutes": 30,
            },
            "queues": [
                {
                    "queue_id": "queue-general",
                    "available_agent_count": 3,
                    "backlog_count": 9,
                    "average_handle_time_minutes": 45,
                    "skill_ids": ["general"],
                    "max_concurrency": 4,
                },
                {
                    "queue_id": "queue-identity",
                    "available_agent_count": 2,
                    "backlog_count": 2,
                    "average_handle_time_minutes": 30,
                    "skill_ids": ["identity", "integration"],
                    "max_concurrency": 3,
                },
            ],
        },
    )

    assert result.method == "recommend"
    assert result.output["model_id"] == "operations-routing-policy-simulator-v1"
    assert result.output["assigned_queue_id"] == "queue-identity"
    assert result.requires_human_review is False


def test_serves_support_assist_with_input_coercion() -> None:
    result = serve_model(
        Path(__file__).resolve().parents[2],
        "support-agent-assist-baseline-v1",
        {
            "tenant_id": "tenant-support",
            "case_id": "case-1001",
            "subject": "Refund invoice question",
            "latest_message": "Customer says payment was charged twice.",
            "product_area": "billing",
            "priority": "normal",
            "language": "en",
        },
    )

    assert result.method == "assist"
    assert result.output["intent"] == "billing"
    assert result.output["requires_human_review"] is True
    assert result.requires_human_review is True


def test_rejects_unknown_model_id() -> None:
    with pytest.raises(ModelServingError, match="unknown model_id"):
        serve_model(
            Path(__file__).resolve().parents[2],
            "missing-model",
            {"tenant_id": "tenant-ops"},
        )


def test_gateway_returns_success_envelope_and_metrics() -> None:
    gateway = ModelServingGateway(Path(__file__).resolve().parents[2])

    response = gateway.invoke(demand_forecast_gateway_request())
    metrics = gateway.snapshot_metrics()

    assert response.request_id == "req-1001"
    assert response.tenant_id == "tenant-ops"
    assert response.status == "ok"
    assert response.output["demandBand"] == "high"
    assert response.artifact_manifest.endswith(
        "operations-demand-forecast-baseline-v1.yaml"
    )
    assert response.requires_human_review is True
    assert response.fallback_used is False
    assert metrics.request_count == 1
    assert metrics.success_count == 1
    assert metrics.human_review_count == 1
    assert metrics.audit_record_count == 0
    assert metrics.by_model["operations-demand-forecast-baseline-v1"]["ok"] == 1


def test_gateway_records_audit_when_store_is_configured() -> None:
    audit_ledger = ModelAuditLedger()
    gateway = ModelServingGateway(
        Path(__file__).resolve().parents[2],
        audit_store=audit_ledger,
        audit_retention_days=7,
    )

    response = gateway.invoke(demand_forecast_gateway_request())
    metrics = gateway.snapshot_metrics()
    records = audit_ledger.list_records()

    assert response.status == "ok"
    assert len(records) == 1
    assert records[0].request_id == "req-1001"
    assert records[0].artifact_manifest.endswith(
        "operations-demand-forecast-baseline-v1.yaml"
    )
    assert "ops.owner@example.com" not in records[0].audit_payload
    assert "[REDACTED_EMAIL]" in records[0].audit_payload
    assert metrics.audit_record_count == 1
    assert metrics.audit_failure_count == 0
    assert (
        metrics.by_model["operations-demand-forecast-baseline-v1"]["auditRecord"] == 1
    )


def test_gateway_audit_failure_defaults_to_fail_open() -> None:
    gateway = ModelServingGateway(
        Path(__file__).resolve().parents[2],
        audit_store=FailingAuditStore(),
    )

    response = gateway.invoke(demand_forecast_gateway_request())
    metrics = gateway.snapshot_metrics()

    assert response.status == "ok"
    assert response.output["demandBand"] == "high"
    assert metrics.success_count == 1
    assert metrics.audit_failure_count == 1
    assert (
        metrics.by_model["operations-demand-forecast-baseline-v1"]["auditFailure"] == 1
    )


def test_gateway_audit_failure_can_fail_closed() -> None:
    gateway = ModelServingGateway(
        Path(__file__).resolve().parents[2],
        audit_store=FailingAuditStore(),
        audit_failure_mode="fail_closed",
    )

    response = gateway.invoke(demand_forecast_gateway_request())
    metrics = gateway.snapshot_metrics()

    assert response.status == "error"
    assert response.output == {}
    assert response.requires_human_review is True
    assert response.error_code == "model_audit_failed"
    assert response.artifact_manifest.endswith(
        "operations-demand-forecast-baseline-v1.yaml"
    )
    assert metrics.success_count == 0
    assert metrics.error_count == 1
    assert metrics.audit_failure_count == 1


def test_gateway_uses_fallback_and_records_error_metrics() -> None:
    gateway = ModelServingGateway(
        Path(__file__).resolve().parents[2],
        fallback_outputs={
            "operations-demand-forecast-baseline-v1": {
                "modelId": "operations-demand-forecast-baseline-v1",
                "demandBand": "normal",
                "staffingRecommendation": "manual_review_fallback",
            }
        },
    )

    response = gateway.invoke(
        {
            "request_id": "req-1002",
            "tenant_id": "tenant-ops",
            "model_id": "operations-demand-forecast-baseline-v1",
            "payload": {
                "tenant_id": "ops",
                "forecast_id": "fc-1002",
                "queue_id": "support-general",
                "historical_demand": [1, 2, 3, 4],
                "planned_capacity": 10,
            },
        }
    )
    metrics = gateway.snapshot_metrics()

    assert response.status == "fallback"
    assert response.fallback_used is True
    assert response.requires_human_review is True
    assert response.error_code == "model_invocation_failed"
    assert response.output["staffingRecommendation"] == "manual_review_fallback"
    assert metrics.request_count == 1
    assert metrics.error_count == 1
    assert metrics.fallback_count == 1
    assert metrics.by_model["operations-demand-forecast-baseline-v1"]["fallback"] == 1


def test_gateway_returns_error_envelope_for_unknown_model() -> None:
    response = invoke_model_serving_gateway(
        Path(__file__).resolve().parents[2],
        {
            "request_id": "req-1003",
            "tenant_id": "tenant-ops",
            "model_id": "missing-model",
            "payload": {"tenant_id": "tenant-ops"},
        },
    )

    assert response.status == "error"
    assert response.output == {}
    assert response.requires_human_review is True
    assert response.error_code == "model_invocation_failed"
    assert "unknown model_id" in response.error_message


def test_gateway_request_validation_requires_api_envelope() -> None:
    gateway = ModelServingGateway(Path(__file__).resolve().parents[2])

    with pytest.raises(ModelServingError, match="request_id"):
        gateway.invoke(
            {
                "tenant_id": "tenant-ops",
                "model_id": "operations-demand-forecast-baseline-v1",
                "payload": {},
            }
        )
