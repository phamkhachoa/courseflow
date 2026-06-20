from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.model_serving_adapter import ModelServingHostedAdapter
from courseflow_ai_platform.model_serving_auth import (
    MODEL_SERVING_CATALOG_SCOPE,
    MODEL_SERVING_INVOKE_SCOPE,
    MODEL_SERVING_OPS_SCOPE,
    load_serving_access_policy,
    load_serving_auth_policy,
)


def operations_forecast_body() -> dict[str, object]:
    return {
        "requestId": "req-policy-1001",
        "tenantId": "tenant-ops",
        "modelId": "operations-demand-forecast-baseline-v1",
        "payload": {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-policy-1001",
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
    }


def test_serving_access_policy_resolves_product_principal() -> None:
    policy = load_serving_access_policy(Path(__file__).resolve().parents[2])

    principal = policy.resolve_principal(
        "service:enterprise-operations-serving",
        requested_scopes=[MODEL_SERVING_INVOKE_SCOPE],
    )

    assert principal.principal_id == "service:enterprise-operations-serving"
    assert principal.scopes == (MODEL_SERVING_INVOKE_SCOPE,)
    assert principal.tenant_ids == ("tenant-ops",)
    assert principal.allowed_model_ids == (
        "operations-demand-forecast-baseline-v1",
        "operations-routing-policy-simulator-v1",
    )


def test_serving_access_policy_resolves_ops_principal() -> None:
    policy = load_serving_access_policy(Path(__file__).resolve().parents[2])

    principal = policy.resolve_principal(
        "service:ai-platform-ops",
        requested_scopes=[MODEL_SERVING_CATALOG_SCOPE, MODEL_SERVING_OPS_SCOPE],
    )

    assert principal.tenant_ids == ()
    assert principal.allowed_model_ids == ()
    assert principal.scopes == (
        MODEL_SERVING_CATALOG_SCOPE,
        MODEL_SERVING_OPS_SCOPE,
    )


def test_serving_access_policy_rejects_unregistered_or_ungranted_claims() -> None:
    policy = load_serving_access_policy(Path(__file__).resolve().parents[2])

    with pytest.raises(ValueError, match="not registered"):
        policy.resolve_principal("service:missing", requested_scopes=[MODEL_SERVING_INVOKE_SCOPE])

    with pytest.raises(ValueError, match="ungranted scopes"):
        policy.resolve_principal(
            "service:enterprise-operations-serving",
            requested_scopes=[MODEL_SERVING_OPS_SCOPE],
        )


def test_policy_resolved_principal_can_invoke_owned_model() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    access_policy = load_serving_access_policy(ai_root)
    adapter = ModelServingHostedAdapter(
        ai_root,
        auth_policy=load_serving_auth_policy(ai_root),
    )
    principal = access_policy.resolve_principal(
        "service:enterprise-operations-serving",
        requested_scopes=[MODEL_SERVING_INVOKE_SCOPE],
    )

    response = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        operations_forecast_body(),
        principal=principal,
    )

    assert response.status_code == 200
    assert response.body["status"] == "ok"
    assert response.body["output"]["demandBand"] == "high"


def test_policy_resolved_principal_cannot_cross_product_model_allowlist() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    access_policy = load_serving_access_policy(ai_root)
    adapter = ModelServingHostedAdapter(
        ai_root,
        auth_policy=load_serving_auth_policy(ai_root),
    )
    principal = access_policy.resolve_principal(
        "service:enterprise-operations-serving",
        requested_scopes=[MODEL_SERVING_INVOKE_SCOPE],
    )

    response = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        {
            **operations_forecast_body(),
            "modelId": "finance-payment-fraud-baseline-v1",
        },
        principal=principal,
    )

    assert response.status_code == 403
    assert response.body["errorCode"] == "model_forbidden"
    assert adapter.snapshot_metrics().request_count == 0
