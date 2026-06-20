from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.forecasting_service import (
    FORECAST_SCORE_SCOPE,
    ForecastingPrivacyError,
    ForecastingRuntime,
    ForecastingServiceError,
    load_forecasting_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def high_demand_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ops",
        "product": "enterprise-operations",
        "useCaseId": "operations-demand-forecasting",
        "forecastId": "fc-1001",
        "queueId": "support-identity",
        "historicalDemand": [78, 82, 84, 96, 114, 132],
        "plannedCapacity": 110,
        "backlogOpenItems": 28,
        "avgHandleMinutes": 52,
        "seasonalIndex": 1.08,
        "specialEvent": True,
        "incidentOpen": True,
        "forecastHorizonDays": 7,
        "serviceLevelTarget": 0.92,
    }


def normal_demand_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ops",
        "product": "enterprise-operations",
        "useCaseId": "operations-demand-forecasting",
        "forecastId": "fc-1002",
        "queueId": "support-general",
        "historicalDemand": [96, 98, 100, 99, 101, 100],
        "plannedCapacity": 108,
        "backlogOpenItems": 3,
        "avgHandleMinutes": 24,
        "seasonalIndex": 1.0,
        "specialEvent": False,
        "incidentOpen": False,
        "forecastHorizonDays": 7,
        "serviceLevelTarget": 0.85,
    }


def test_forecasting_runtime_scores_high_demand_and_tracks_hitl_metrics() -> None:
    root = ai_root()
    policy = load_forecasting_access_policy(root)
    principal = policy.resolve_principal(
        "service:enterprise-operations-forecasting",
        (FORECAST_SCORE_SCOPE,),
    )
    runtime = ForecastingRuntime(root)

    response = runtime.score(high_demand_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["modelId"] == "operations-demand-forecast-baseline-v1"
    assert response["demandBand"] == "high"
    assert response["requiresHumanReview"] is True
    assert response["automatedCapacityChangeAllowed"] is False
    assert response["decisionPolicy"] == (
        "human_review_required_before_staffing_or_sla_impacting_action"
    )
    assert response["tenantId"] == "tenant-ops"
    assert response["forecastId"] == "fc-1001"
    assert metrics.score_count == 1
    assert metrics.high_demand_count == 1
    assert metrics.capacity_shortfall_count == 1
    assert metrics.human_review_count == 1
    assert metrics.by_demand_band == {"high": 1}


def test_forecasting_runtime_scores_normal_demand_without_hitl_queue() -> None:
    root = ai_root()
    policy = load_forecasting_access_policy(root)
    principal = policy.resolve_principal(
        "service:enterprise-operations-forecasting",
        (FORECAST_SCORE_SCOPE,),
    )
    runtime = ForecastingRuntime(root)

    response = runtime.score(normal_demand_body(), principal).to_dict()

    assert response["demandBand"] == "normal"
    assert response["requiresHumanReview"] is False
    assert response["staffingRecommendation"] == "maintain_capacity"
    assert runtime.snapshot_metrics().by_use_case == {
        "operations-demand-forecasting": 1
    }


def test_forecasting_policy_rejects_cross_tenant_and_direct_identifier() -> None:
    root = ai_root()
    policy = load_forecasting_access_policy(root)
    principal = policy.resolve_principal(
        "service:enterprise-operations-forecasting",
        (FORECAST_SCORE_SCOPE,),
    )
    runtime = ForecastingRuntime(root)

    with pytest.raises(ForecastingServiceError, match="tenant is not granted"):
        runtime.score({**high_demand_body(), "tenantId": "tenant-finance"}, principal)

    with pytest.raises(ForecastingPrivacyError, match="direct identifier"):
        runtime.score({**high_demand_body(), "employeeId": "emp-raw-001"}, principal)
    assert runtime.snapshot_metrics().direct_identifier_rejection_count == 1


def test_forecasting_policy_exposes_enterprise_and_lms_planning_grants() -> None:
    policy = load_forecasting_access_policy(ai_root())
    ops_principal = policy.resolve_principal(
        "service:enterprise-operations-forecasting",
        (FORECAST_SCORE_SCOPE,),
    )
    lms_principal = policy.resolve_principal(
        "service:lms-courseflow-planning",
        (FORECAST_SCORE_SCOPE,),
    )

    assert ops_principal.product_ids == ("enterprise-operations",)
    assert ops_principal.use_case_ids == ("operations-demand-forecasting",)
    assert "tenant-ops" in ops_principal.tenant_ids
    assert lms_principal.product_ids == ("lms-courseflow",)
    assert lms_principal.use_case_ids == ("lms-cohort-demand-forecasting",)
