from __future__ import annotations

import pytest

from causal_uplift_baseline import CausalUpliftBaseline


def test_predicts_positive_lift_for_confident_treatment_effect() -> None:
    model = CausalUpliftBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-lms",
            "experiment_id": "exp-intervention-coach-v1",
            "outcome_name": "course_completion",
            "treatment_name": "coach_nudge",
            "control_name": "standard_notification",
            "treatment_count": 1000,
            "treatment_successes": 620,
            "control_count": 1000,
            "control_successes": 520,
            "minimum_detectable_lift": 0.04,
            "confidence_level": 0.95,
            "guardrail_metric_delta": 0.004,
            "high_impact": True,
        }
    )

    assert prediction.model_id == "causal-uplift-baseline-v1"
    assert prediction.decision_band == "positive_lift"
    assert prediction.recommendation == "promote_to_shadow_review"
    assert prediction.absolute_lift == pytest.approx(0.1)
    assert prediction.requires_human_review is True
    assert "STATISTICALLY_CONFIDENT" in prediction.reason_codes
    assert "MEETS_MINIMUM_DETECTABLE_LIFT" in prediction.reason_codes


def test_predicts_inconclusive_for_small_observed_difference() -> None:
    model = CausalUpliftBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-commerce",
            "experiment_id": "exp-rank-copy-v1",
            "outcome_name": "conversion",
            "treatment_name": "new_ranker_copy",
            "control_name": "current_ranker_copy",
            "treatment_count": 1000,
            "treatment_successes": 505,
            "control_count": 1000,
            "control_successes": 500,
            "minimum_detectable_lift": 0.03,
            "confidence_level": 0.95,
            "guardrail_metric_delta": 0.0,
            "high_impact": False,
        }
    )

    assert prediction.decision_band == "inconclusive"
    assert prediction.recommendation == "continue_experiment"
    assert prediction.requires_human_review is False
    assert "BELOW_MINIMUM_DETECTABLE_LIFT" in prediction.reason_codes
    assert "NEEDS_MORE_SAMPLE" in prediction.reason_codes


def test_stops_experiment_when_guardrail_regresses() -> None:
    model = CausalUpliftBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-ops",
            "experiment_id": "exp-routing-policy-v2",
            "outcome_name": "resolved_within_sla",
            "treatment_name": "policy_v2",
            "control_name": "policy_v1",
            "treatment_count": 1000,
            "treatment_successes": 410,
            "control_count": 1000,
            "control_successes": 480,
            "minimum_detectable_lift": 0.03,
            "confidence_level": 0.95,
            "guardrail_metric_delta": -0.04,
            "high_impact": False,
            "segment_count": 12,
        }
    )

    assert prediction.decision_band == "guardrail_risk"
    assert prediction.recommendation == "stop_or_redesign"
    assert prediction.requires_human_review is True
    assert "GUARDRAIL_REGRESSION" in prediction.reason_codes
    assert "SEGMENT_MULTIPLICITY_REVIEW" in prediction.reason_codes


def test_rejects_invalid_observation_counts() -> None:
    model = CausalUpliftBaseline()

    with pytest.raises(ValueError, match="treatment_successes"):
        model.predict(
            {
                "tenant_id": "tenant-lms",
                "experiment_id": "exp-bad",
                "outcome_name": "course_completion",
                "treatment_name": "treatment",
                "control_name": "control",
                "treatment_count": 30,
                "treatment_successes": 31,
                "control_count": 30,
                "control_successes": 10,
            }
        )
