from __future__ import annotations

import pytest

from ai.models.deep_learning.sequence_risk_baseline.sequence_risk_baseline import (
    SequenceRiskBaseline,
)


def test_sequence_risk_baseline_scores_high_risk_sequence() -> None:
    model = SequenceRiskBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-a",
            "learner_principal_hash": "learner-hash-001",
            "course_id": "course-python",
            "feature_snapshot_at": "2026-06-17T00:00:00Z",
            "events": [
                {"event_type": "missed_deadline", "days_ago": 1},
                {"event_type": "low_quiz_score", "days_ago": 2, "score": 0.38},
                {"event_type": "inactive_day", "days_ago": 2},
                {"event_type": "late_submission", "days_ago": 4},
            ],
        }
    )

    assert prediction.model_id == "sequence-risk-baseline-v1"
    assert prediction.risk_band == "high"
    assert prediction.risk_score >= 0.7
    assert {"MISSED_DEADLINE", "LOW_ASSESSMENT_SCORE", "RECENT_INACTIVITY"} <= set(
        prediction.reason_codes
    )
    assert "advisor_outreach" in prediction.recommended_actions


def test_sequence_risk_baseline_scores_positive_progress_lower() -> None:
    model = SequenceRiskBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-a",
            "learner_principal_hash": "learner-hash-002",
            "course_id": "course-python",
            "feature_snapshot_at": "2026-06-17T00:00:00Z",
            "events": [
                {
                    "event_type": "video_completed",
                    "days_ago": 1,
                    "engagement_minutes": 50,
                },
                {"event_type": "quiz_passed", "days_ago": 1, "score": 0.92},
                {"event_type": "assignment_submitted", "days_ago": 2},
            ],
        }
    )

    assert prediction.risk_band == "low"
    assert prediction.risk_score < 0.45
    assert "POSITIVE_PROGRESS" in prediction.reason_codes
    assert prediction.recommended_actions == ("continue_monitoring",)


def test_sequence_risk_baseline_is_deterministic() -> None:
    model = SequenceRiskBaseline()
    payload = {
        "tenant_id": "tenant-a",
        "learner_principal_hash": "learner-hash-003",
        "course_id": "course-python",
        "feature_snapshot_at": "2026-06-17T00:00:00Z",
        "events": [
            {"event_type": "low_quiz_score", "days_ago": 5, "score": 0.55},
            {"event_type": "help_request", "days_ago": 2},
            {"event_type": "quiz_passed", "days_ago": 1, "score": 0.74},
        ],
    }

    assert model.predict(payload).to_dict() == model.predict(payload).to_dict()


def test_sequence_risk_baseline_requires_bounded_tenant() -> None:
    model = SequenceRiskBaseline()

    with pytest.raises(ValueError, match="tenant_id"):
        model.predict(
            {
                "tenant_id": "public",
                "learner_principal_hash": "learner-hash-004",
                "course_id": "course-python",
                "feature_snapshot_at": "2026-06-17T00:00:00Z",
                "events": [{"event_type": "inactive_day", "days_ago": 1}],
            }
        )
