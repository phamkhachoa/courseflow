from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MODEL_ID = "operations-demand-forecast-baseline-v1"
MODEL_VERSION = "2026-06-17"


@dataclass(frozen=True, slots=True)
class DemandForecastInput:
    tenant_id: str
    forecast_id: str
    queue_id: str
    historical_demand: tuple[int, ...]
    planned_capacity: int
    backlog_open_items: int = 0
    avg_handle_minutes: int = 30
    seasonal_index: float = 1.0
    special_event: bool = False
    incident_open: bool = False
    forecast_horizon_days: int = 7
    service_level_target: float = 0.85

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> DemandForecastInput:
        history = row.get("historical_demand")
        if not isinstance(history, list):
            raise ValueError("historical_demand must be a list")
        return cls(
            tenant_id=require_non_empty_str(row, "tenant_id", "demand forecast input"),
            forecast_id=require_non_empty_str(row, "forecast_id", "demand forecast input"),
            queue_id=require_non_empty_str(row, "queue_id", "demand forecast input"),
            historical_demand=tuple(
                require_non_negative_int(
                    {"value": value},
                    "value",
                    "historical demand value",
                )
                for value in history
            ),
            planned_capacity=require_non_negative_int(
                row,
                "planned_capacity",
                "demand forecast input",
            ),
            backlog_open_items=require_non_negative_int(
                row,
                "backlog_open_items",
                "demand forecast input",
            ),
            avg_handle_minutes=require_positive_int(
                {"avg_handle_minutes": row.get("avg_handle_minutes", 30)},
                "avg_handle_minutes",
                "demand forecast input",
            ),
            seasonal_index=require_positive_float(
                {"seasonal_index": row.get("seasonal_index", 1.0)},
                "seasonal_index",
                "demand forecast input",
            ),
            special_event=bool(row.get("special_event", False)),
            incident_open=bool(row.get("incident_open", False)),
            forecast_horizon_days=require_positive_int(
                {"forecast_horizon_days": row.get("forecast_horizon_days", 7)},
                "forecast_horizon_days",
                "demand forecast input",
            ),
            service_level_target=require_bounded_float(
                {"service_level_target": row.get("service_level_target", 0.85)},
                "service_level_target",
                "demand forecast input",
                minimum=0.0,
                maximum=1.0,
            ),
        )


@dataclass(frozen=True, slots=True)
class DemandForecastPrediction:
    model_id: str
    forecast_units: int
    demand_band: str
    capacity_gap_units: int
    utilization_ratio: float
    staffing_recommendation: str
    reason_codes: tuple[str, ...]
    scenario_actions: tuple[str, ...]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "capacityGapUnits": self.capacity_gap_units,
            "demandBand": self.demand_band,
            "forecastUnits": self.forecast_units,
            "modelId": self.model_id,
            "reasonCodes": list(self.reason_codes),
            "requiresHumanReview": self.requires_human_review,
            "scenarioActions": list(self.scenario_actions),
            "staffingRecommendation": self.staffing_recommendation,
            "utilizationRatio": self.utilization_ratio,
        }


class DemandForecastBaseline:
    """Deterministic time-series and planning baseline for operations demand."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def predict(
        self,
        payload: DemandForecastInput | dict[str, Any],
    ) -> DemandForecastPrediction:
        request = (
            payload
            if isinstance(payload, DemandForecastInput)
            else DemandForecastInput.from_dict(payload)
        )
        validate_request(request)

        forecast_units = forecast_demand_units(request)
        capacity_gap = forecast_units - request.planned_capacity
        utilization_ratio = round(forecast_units / max(1, request.planned_capacity), 6)
        demand_band = band_for_forecast(forecast_units, request.planned_capacity)
        reason_codes = derive_reason_codes(request, forecast_units, capacity_gap)
        staffing_recommendation = staffing_action(demand_band, capacity_gap)

        return DemandForecastPrediction(
            model_id=MODEL_ID,
            forecast_units=forecast_units,
            demand_band=demand_band,
            capacity_gap_units=capacity_gap,
            utilization_ratio=utilization_ratio,
            staffing_recommendation=staffing_recommendation,
            reason_codes=tuple(sorted(reason_codes)),
            scenario_actions=scenario_actions(
                staffing_recommendation,
                reason_codes,
                request,
            ),
            requires_human_review=requires_human_review(
                demand_band,
                capacity_gap,
                request,
            ),
        )


def validate_request(request: DemandForecastInput) -> None:
    if not request.tenant_id.startswith("tenant-"):
        raise ValueError("tenant_id must be a bounded tenant identifier")
    if len(request.historical_demand) < 4:
        raise ValueError("historical_demand must contain at least four observations")
    if request.forecast_horizon_days > 90:
        raise ValueError("forecast_horizon_days must be 90 or less")
    if request.planned_capacity == 0 and sum(request.historical_demand) > 0:
        raise ValueError("planned_capacity is required when demand history is non-zero")


def forecast_demand_units(request: DemandForecastInput) -> int:
    history = request.historical_demand
    recent_weighted = (
        history[-1] * 0.5
        + history[-2] * 0.3
        + history[-3] * 0.2
    )
    previous_window = sum(history[-6:-3] or history[:3]) / min(3, len(history[:-3]) or 3)
    trend = recent_weighted - previous_window
    trend_adjustment = max(-0.18 * recent_weighted, min(0.35 * recent_weighted, trend * 0.55))
    backlog_pressure = min(0.25 * recent_weighted, request.backlog_open_items * 0.18)
    event_multiplier = 1.0
    if request.special_event:
        event_multiplier += 0.18
    if request.incident_open:
        event_multiplier += 0.12

    horizon_multiplier = request.forecast_horizon_days / 7.0
    forecast = (
        (recent_weighted + trend_adjustment + backlog_pressure)
        * request.seasonal_index
        * event_multiplier
        * horizon_multiplier
    )
    return max(0, int(round(forecast)))


def band_for_forecast(forecast_units: int, planned_capacity: int) -> str:
    ratio = forecast_units / max(1, planned_capacity)
    if ratio >= 1.25:
        return "high"
    if ratio >= 1.05:
        return "elevated"
    if ratio <= 0.70:
        return "low"
    return "normal"


def derive_reason_codes(
    request: DemandForecastInput,
    forecast_units: int,
    capacity_gap: int,
) -> set[str]:
    reasons: set[str] = set()
    history = request.historical_demand
    recent_avg = sum(history[-3:]) / 3
    prior_avg = sum(history[-6:-3] or history[:3]) / min(3, len(history[:-3]) or 3)

    if recent_avg >= prior_avg * 1.12:
        reasons.add("DEMAND_TREND_UP")
    elif recent_avg <= prior_avg * 0.88:
        reasons.add("DEMAND_TREND_DOWN")
    else:
        reasons.add("DEMAND_STABLE")
    if request.special_event:
        reasons.add("SPECIAL_EVENT_SPIKE")
    if request.incident_open:
        reasons.add("OPEN_INCIDENT_RISK")
    if request.backlog_open_items >= max(5, int(0.15 * max(1, forecast_units))):
        reasons.add("BACKLOG_PRESSURE")
    if capacity_gap >= max(5, int(0.10 * max(1, request.planned_capacity))):
        reasons.add("CAPACITY_SHORTFALL")
    elif capacity_gap <= -max(5, int(0.20 * max(1, request.planned_capacity))):
        reasons.add("CAPACITY_SURPLUS")
    if request.avg_handle_minutes >= 45:
        reasons.add("LONG_HANDLE_TIME")
    if request.service_level_target >= 0.9:
        reasons.add("STRICT_SERVICE_LEVEL_TARGET")
    return reasons


def staffing_action(demand_band: str, capacity_gap: int) -> str:
    if demand_band == "high" or capacity_gap >= 20:
        return "trigger_capacity_plan"
    if demand_band == "elevated" or capacity_gap > 0:
        return "add_staffing"
    if demand_band == "low":
        return "reduce_or_reallocate_capacity"
    return "maintain_capacity"


def scenario_actions(
    staffing_recommendation: str,
    reason_codes: set[str],
    request: DemandForecastInput,
) -> tuple[str, ...]:
    actions: list[str] = [staffing_recommendation]
    if "SPECIAL_EVENT_SPIKE" in reason_codes:
        actions.append("run_event_surge_scenario")
    if "OPEN_INCIDENT_RISK" in reason_codes:
        actions.append("reserve_incident_response_capacity")
    if "BACKLOG_PRESSURE" in reason_codes:
        actions.append("clear_backlog_before_peak")
    if request.service_level_target >= 0.9:
        actions.append("protect_service_level_buffer")
    return tuple(dict.fromkeys(actions))


def requires_human_review(
    demand_band: str,
    capacity_gap: int,
    request: DemandForecastInput,
) -> bool:
    return (
        demand_band == "high"
        or capacity_gap >= max(20, int(0.20 * max(1, request.planned_capacity)))
        or request.incident_open
    )


def require_non_empty_str(row: dict[str, Any], field: str, owner: str) -> str:
    value = str(row.get(field, "")).strip()
    if not value:
        raise ValueError(f"{owner} requires {field}")
    return value


def require_non_negative_int(row: dict[str, Any], field: str, owner: str) -> int:
    value = int(row.get(field, 0))
    if value < 0:
        raise ValueError(f"{owner} {field} must be non-negative")
    return value


def require_positive_int(row: dict[str, Any], field: str, owner: str) -> int:
    value = int(row.get(field, 0))
    if value <= 0:
        raise ValueError(f"{owner} {field} must be positive")
    return value


def require_positive_float(row: dict[str, Any], field: str, owner: str) -> float:
    value = float(row.get(field, 1.0))
    if value <= 0:
        raise ValueError(f"{owner} {field} must be positive")
    return value


def require_bounded_float(
    row: dict[str, Any],
    field: str,
    owner: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    value = float(row.get(field, minimum))
    if value < minimum or value > maximum:
        raise ValueError(f"{owner} {field} must be between {minimum} and {maximum}")
    return value
