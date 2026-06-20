from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.sequence_risk_service import (
    SEQUENCE_RISK_SCORE_SCOPE,
    SequenceRiskPrivacyError,
    SequenceRiskRuntime,
    SequenceRiskServiceError,
    load_sequence_risk_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def high_risk_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-lms",
        "product": "lms-courseflow",
        "useCaseId": "lms-at-risk-prediction",
        "subjectPrincipalHash": "learner-hash-001",
        "sequenceId": "course-python",
        "featureSnapshotAt": "2026-06-17T00:00:00Z",
        "events": [
            {"event_type": "missed_deadline", "days_ago": 1},
            {"event_type": "low_quiz_score", "days_ago": 2, "score": 0.38},
            {"event_type": "inactive_day", "days_ago": 2},
            {"event_type": "late_submission", "days_ago": 4},
        ],
    }


def low_risk_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-lms",
        "product": "lms-courseflow",
        "useCaseId": "lms-knowledge-tracing",
        "subjectPrincipalHash": "learner-hash-002",
        "sequenceId": "course-python",
        "featureSnapshotAt": "2026-06-17T00:00:00Z",
        "events": [
            {"event_type": "video_completed", "days_ago": 1, "engagement_minutes": 50},
            {"event_type": "quiz_passed", "days_ago": 1, "score": 0.92},
            {"event_type": "assignment_submitted", "days_ago": 2},
        ],
    }


def test_sequence_risk_runtime_scores_high_risk_and_tracks_hitl_metrics() -> None:
    root = ai_root()
    policy = load_sequence_risk_access_policy(root)
    principal = policy.resolve_principal(
        "service:lms-courseflow-sequence",
        (SEQUENCE_RISK_SCORE_SCOPE,),
    )
    runtime = SequenceRiskRuntime(root)

    response = runtime.score(high_risk_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["modelId"] == "sequence-risk-baseline-v1"
    assert response["riskBand"] == "high"
    assert response["requiresHumanReview"] is True
    assert response["interventionPolicy"] == "human_review_required_before_adverse_action"
    assert response["tenantId"] == "tenant-lms"
    assert metrics.score_count == 1
    assert metrics.high_risk_count == 1
    assert metrics.human_review_count == 1


def test_sequence_risk_runtime_scores_low_risk_without_hitl_queue() -> None:
    root = ai_root()
    policy = load_sequence_risk_access_policy(root)
    principal = policy.resolve_principal(
        "service:lms-courseflow-sequence",
        (SEQUENCE_RISK_SCORE_SCOPE,),
    )
    runtime = SequenceRiskRuntime(root)

    response = runtime.score(low_risk_body(), principal).to_dict()

    assert response["riskBand"] == "low"
    assert response["requiresHumanReview"] is False
    assert response["recommendedActions"] == ["continue_monitoring"]
    assert runtime.snapshot_metrics().by_use_case == {"lms-knowledge-tracing": 1}


def test_sequence_risk_policy_rejects_cross_tenant_and_direct_identifier() -> None:
    root = ai_root()
    policy = load_sequence_risk_access_policy(root)
    principal = policy.resolve_principal(
        "service:lms-courseflow-sequence",
        (SEQUENCE_RISK_SCORE_SCOPE,),
    )
    runtime = SequenceRiskRuntime(root)

    with pytest.raises(SequenceRiskServiceError, match="tenant is not granted"):
        runtime.score({**high_risk_body(), "tenantId": "tenant-support"}, principal)

    with pytest.raises(SequenceRiskPrivacyError, match="direct identifier"):
        runtime.score({**high_risk_body(), "learnerId": "learner-raw-001"}, principal)
    assert runtime.snapshot_metrics().direct_identifier_rejection_count == 1


def test_sequence_risk_policy_exposes_lms_grants_only_for_bounded_use_cases() -> None:
    policy = load_sequence_risk_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:lms-courseflow-sequence",
        (SEQUENCE_RISK_SCORE_SCOPE,),
    )

    assert principal.product_ids == ("lms-courseflow",)
    assert "tenant-lms" in principal.tenant_ids
    assert set(principal.use_case_ids) == {
        "lms-at-risk-prediction",
        "lms-knowledge-tracing",
    }
