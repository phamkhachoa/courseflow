from __future__ import annotations

import pytest

from demand_forecast_baseline import DemandForecastBaseline


def test_predicts_high_capacity_plan_for_event_and_incident() -> None:
    model = DemandForecastBaseline()

    prediction = model.predict(
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
        }
    )

    assert prediction.model_id == "operations-demand-forecast-baseline-v1"
    assert prediction.forecast_units >= 175
    assert prediction.demand_band == "high"
    assert prediction.staffing_recommendation == "trigger_capacity_plan"
    assert prediction.requires_human_review is True
    assert "CAPACITY_SHORTFALL" in prediction.reason_codes
    assert "SPECIAL_EVENT_SPIKE" in prediction.reason_codes
    assert "reserve_incident_response_capacity" in prediction.scenario_actions


def test_predicts_normal_maintain_capacity_for_stable_workload() -> None:
    model = DemandForecastBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-1002",
            "queue_id": "support-general",
            "historical_demand": [96, 98, 100, 99, 101, 100],
            "planned_capacity": 108,
            "backlog_open_items": 3,
            "avg_handle_minutes": 24,
            "seasonal_index": 1.0,
            "special_event": False,
            "incident_open": False,
            "forecast_horizon_days": 7,
            "service_level_target": 0.85,
        }
    )

    assert 98 <= prediction.forecast_units <= 104
    assert prediction.demand_band == "normal"
    assert prediction.staffing_recommendation == "maintain_capacity"
    assert prediction.requires_human_review is False
    assert "DEMAND_STABLE" in prediction.reason_codes


def test_predicts_low_reallocation_for_declining_demand() -> None:
    model = DemandForecastBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-1003",
            "queue_id": "support-billing",
            "historical_demand": [150, 136, 120, 94, 82, 68],
            "planned_capacity": 120,
            "backlog_open_items": 0,
            "avg_handle_minutes": 28,
            "seasonal_index": 0.92,
            "special_event": False,
            "incident_open": False,
            "forecast_horizon_days": 7,
            "service_level_target": 0.8,
        }
    )

    assert prediction.forecast_units <= 70
    assert prediction.demand_band == "low"
    assert prediction.staffing_recommendation == "reduce_or_reallocate_capacity"
    assert "DEMAND_TREND_DOWN" in prediction.reason_codes
    assert "CAPACITY_SURPLUS" in prediction.reason_codes


def test_rejects_invalid_forecast_payload() -> None:
    model = DemandForecastBaseline()

    with pytest.raises(ValueError, match="tenant_id"):
        model.predict(
            {
                "tenant_id": "ops",
                "forecast_id": "fc-1004",
                "queue_id": "support-general",
                "historical_demand": [1, 2, 3, 4],
                "planned_capacity": 10,
            }
        )
