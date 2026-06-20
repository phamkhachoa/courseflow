from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt
from typing import Any

MODEL_ID = "causal-uplift-baseline-v1"
MODEL_VERSION = "2026-06-17"


@dataclass(frozen=True, slots=True)
class CausalUpliftInput:
    tenant_id: str
    experiment_id: str
    outcome_name: str
    treatment_name: str
    control_name: str
    treatment_count: int
    treatment_successes: int
    control_count: int
    control_successes: int
    minimum_detectable_lift: float = 0.03
    confidence_level: float = 0.95
    guardrail_metric_delta: float = 0.0
    high_impact: bool = True
    segment_count: int = 1

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> CausalUpliftInput:
        return cls(
            tenant_id=require_non_empty_str(row, "tenant_id", "causal uplift input"),
            experiment_id=require_non_empty_str(
                row,
                "experiment_id",
                "causal uplift input",
            ),
            outcome_name=require_non_empty_str(
                row,
                "outcome_name",
                "causal uplift input",
            ),
            treatment_name=require_non_empty_str(
                row,
                "treatment_name",
                "causal uplift input",
            ),
            control_name=require_non_empty_str(
                row,
                "control_name",
                "causal uplift input",
            ),
            treatment_count=require_positive_int(
                row,
                "treatment_count",
                "causal uplift input",
            ),
            treatment_successes=require_non_negative_int(
                row,
                "treatment_successes",
                "causal uplift input",
            ),
            control_count=require_positive_int(
                row,
                "control_count",
                "causal uplift input",
            ),
            control_successes=require_non_negative_int(
                row,
                "control_successes",
                "causal uplift input",
            ),
            minimum_detectable_lift=require_bounded_float(
                {"minimum_detectable_lift": row.get("minimum_detectable_lift", 0.03)},
                "minimum_detectable_lift",
                "causal uplift input",
                minimum=0.0,
                maximum=1.0,
            ),
            confidence_level=require_bounded_float(
                {"confidence_level": row.get("confidence_level", 0.95)},
                "confidence_level",
                "causal uplift input",
                minimum=0.5,
                maximum=0.99,
            ),
            guardrail_metric_delta=require_float(
                {"guardrail_metric_delta": row.get("guardrail_metric_delta", 0.0)},
                "guardrail_metric_delta",
                "causal uplift input",
            ),
            high_impact=bool(row.get("high_impact", True)),
            segment_count=require_positive_int(
                {"segment_count": row.get("segment_count", 1)},
                "segment_count",
                "causal uplift input",
            ),
        )


@dataclass(frozen=True, slots=True)
class CausalUpliftPrediction:
    model_id: str
    treatment_rate: float
    control_rate: float
    absolute_lift: float
    relative_lift: float
    z_score: float
    confidence_score: float
    decision_band: str
    recommendation: str
    reason_codes: tuple[str, ...]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "absoluteLift": self.absolute_lift,
            "confidenceScore": self.confidence_score,
            "controlRate": self.control_rate,
            "decisionBand": self.decision_band,
            "modelId": self.model_id,
            "reasonCodes": list(self.reason_codes),
            "recommendation": self.recommendation,
            "relativeLift": self.relative_lift,
            "requiresHumanReview": self.requires_human_review,
            "treatmentRate": self.treatment_rate,
            "zScore": self.z_score,
        }


class CausalUpliftBaseline:
    """Deterministic uplift baseline for experiment and intervention review."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def predict(
        self,
        payload: CausalUpliftInput | dict[str, Any],
    ) -> CausalUpliftPrediction:
        request = (
            payload
            if isinstance(payload, CausalUpliftInput)
            else CausalUpliftInput.from_dict(payload)
        )
        validate_request(request)

        treatment_rate = request.treatment_successes / request.treatment_count
        control_rate = request.control_successes / request.control_count
        absolute_lift = treatment_rate - control_rate
        relative_lift = absolute_lift / control_rate if control_rate > 0 else 0.0
        z_score = two_proportion_z_score(
            request.treatment_successes,
            request.treatment_count,
            request.control_successes,
            request.control_count,
        )
        confidence_score = normal_confidence_score(z_score)
        threshold = confidence_threshold(request.confidence_level)
        decision_band = derive_decision_band(request, absolute_lift, z_score, threshold)
        recommendation = derive_recommendation(decision_band)
        reason_codes = derive_reason_codes(request, absolute_lift, z_score, threshold)

        return CausalUpliftPrediction(
            model_id=MODEL_ID,
            treatment_rate=round(treatment_rate, 6),
            control_rate=round(control_rate, 6),
            absolute_lift=round(absolute_lift, 6),
            relative_lift=round(relative_lift, 6),
            z_score=round(z_score, 6),
            confidence_score=round(confidence_score, 6),
            decision_band=decision_band,
            recommendation=recommendation,
            reason_codes=tuple(sorted(reason_codes)),
            requires_human_review=requires_human_review(
                request,
                decision_band,
                z_score,
                threshold,
            ),
        )


def validate_request(request: CausalUpliftInput) -> None:
    if not request.tenant_id.startswith("tenant-"):
        raise ValueError("tenant_id must be a bounded tenant identifier")
    if request.treatment_successes > request.treatment_count:
        raise ValueError("treatment_successes cannot exceed treatment_count")
    if request.control_successes > request.control_count:
        raise ValueError("control_successes cannot exceed control_count")
    if request.treatment_count < 30 or request.control_count < 30:
        raise ValueError("each experiment arm must contain at least 30 observations")
    if request.segment_count > 100:
        raise ValueError("segment_count must be 100 or less")
    if request.treatment_name == request.control_name:
        raise ValueError("treatment_name and control_name must differ")


def two_proportion_z_score(
    treatment_successes: int,
    treatment_count: int,
    control_successes: int,
    control_count: int,
) -> float:
    treatment_rate = treatment_successes / treatment_count
    control_rate = control_successes / control_count
    pooled = (treatment_successes + control_successes) / (
        treatment_count + control_count
    )
    standard_error = sqrt(
        pooled
        * (1.0 - pooled)
        * ((1.0 / treatment_count) + (1.0 / control_count))
    )
    if standard_error == 0:
        return 0.0
    return (treatment_rate - control_rate) / standard_error


def normal_confidence_score(z_score: float) -> float:
    return erf(abs(z_score) / sqrt(2.0))


def confidence_threshold(confidence_level: float) -> float:
    if confidence_level >= 0.99:
        return 2.576
    if confidence_level >= 0.95:
        return 1.96
    if confidence_level >= 0.90:
        return 1.645
    return 1.282


def derive_decision_band(
    request: CausalUpliftInput,
    absolute_lift: float,
    z_score: float,
    threshold: float,
) -> str:
    if request.guardrail_metric_delta <= -0.02:
        return "guardrail_risk"
    if absolute_lift >= request.minimum_detectable_lift and z_score >= threshold:
        return "positive_lift"
    if absolute_lift <= -request.minimum_detectable_lift and z_score <= -threshold:
        return "negative_lift"
    if abs(absolute_lift) >= request.minimum_detectable_lift:
        return "directional_lift"
    return "inconclusive"


def derive_recommendation(decision_band: str) -> str:
    if decision_band == "positive_lift":
        return "promote_to_shadow_review"
    if decision_band in {"negative_lift", "guardrail_risk"}:
        return "stop_or_redesign"
    if decision_band == "directional_lift":
        return "continue_until_confident"
    return "continue_experiment"


def derive_reason_codes(
    request: CausalUpliftInput,
    absolute_lift: float,
    z_score: float,
    threshold: float,
) -> set[str]:
    reasons: set[str] = set()
    if absolute_lift > 0:
        reasons.add("OBSERVED_POSITIVE_LIFT")
    elif absolute_lift < 0:
        reasons.add("OBSERVED_NEGATIVE_LIFT")
    else:
        reasons.add("NO_OBSERVED_LIFT")

    if abs(absolute_lift) >= request.minimum_detectable_lift:
        reasons.add("MEETS_MINIMUM_DETECTABLE_LIFT")
    else:
        reasons.add("BELOW_MINIMUM_DETECTABLE_LIFT")

    if abs(z_score) >= threshold:
        reasons.add("STATISTICALLY_CONFIDENT")
    else:
        reasons.add("NEEDS_MORE_SAMPLE")

    if request.guardrail_metric_delta <= -0.02:
        reasons.add("GUARDRAIL_REGRESSION")
    if request.treatment_count < 100 or request.control_count < 100:
        reasons.add("SMALL_SAMPLE")
    if request.segment_count > 10:
        reasons.add("SEGMENT_MULTIPLICITY_REVIEW")
    if request.high_impact:
        reasons.add("HIGH_IMPACT_REVIEW")
    return reasons


def requires_human_review(
    request: CausalUpliftInput,
    decision_band: str,
    z_score: float,
    threshold: float,
) -> bool:
    if request.high_impact:
        return True
    if decision_band in {"positive_lift", "negative_lift", "guardrail_risk"}:
        return True
    return abs(z_score) >= threshold and abs(request.guardrail_metric_delta) >= 0.01


def require_non_empty_str(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} requires non-empty string field {key}")
    return value.strip()


def require_positive_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{owner} requires positive integer field {key}")
    return value


def require_non_negative_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{owner} requires non-negative integer field {key}")
    return value


def require_float(row: dict[str, Any], key: str, owner: str) -> float:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{owner} requires numeric field {key}")
    return float(value)


def require_bounded_float(
    row: dict[str, Any],
    key: str,
    owner: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    value = require_float(row, key, owner)
    if value < minimum or value > maximum:
        raise ValueError(f"{owner} requires {key} between {minimum} and {maximum}")
    return value
