from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.governance_evaluation_service import (
    GOVERNANCE_EVALUATION_ASSESS_SCOPE,
    GovernanceEvaluationPrivacyError,
    GovernanceEvaluationRuntime,
    GovernanceEvaluationServiceError,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_governance_evaluation_approves_active_lms_baseline_and_metrics() -> None:
    runtime = GovernanceEvaluationRuntime(ai_root())

    response = runtime.assess(
        {
            "tenantId": "tenant-lms",
            "product": "lms-courseflow",
            "useCaseId": "lms-related-course-recommendation",
            "promotionId": "recommendation-item-cf-v1-active-baseline",
            "asOf": "2026-06-17",
        },
        {
            "principalId": "service:lms-courseflow-governance-evaluation",
            "scopes": [GOVERNANCE_EVALUATION_ASSESS_SCOPE],
            "tenantIds": ["tenant-lms"],
            "productIds": ["lms-courseflow"],
            "useCaseIds": ["lms-related-course-recommendation"],
        },
    )
    metrics = runtime.snapshot_metrics().to_dict()

    assert response.decision == "approved"
    assert response.ready_for_release is True
    assert response.requires_human_review is False
    assert response.required_gate_count == 1
    assert response.gate_ready_count == 1
    assert response.reason_codes == (
        "maker_checker_satisfied",
        "rollback_target_ready",
        "active_monitoring",
        "quality_gates_ready",
    )
    assert metrics["approvedCount"] == 1
    assert metrics["byUseCase"] == {"lms-related-course-recommendation": 1}


def test_governance_evaluation_requires_review_for_support_promotion() -> None:
    runtime = GovernanceEvaluationRuntime(ai_root())

    response = runtime.assess(
        {
            "tenantId": "tenant-support",
            "product": "support-platform",
            "useCaseId": "support-agent-assist",
            "promotionId": "support-agent-assist-baseline-approved",
            "riskLevel": "high",
            "asOf": "2026-06-17",
        },
        {
            "principalId": "service:support-platform-governance-evaluation",
            "scopes": [GOVERNANCE_EVALUATION_ASSESS_SCOPE],
            "tenantIds": ["tenant-support"],
            "productIds": ["support-platform"],
            "useCaseIds": ["support-agent-assist"],
        },
    )

    assert response.decision == "review_required"
    assert response.governance_status == "ready_for_human_review"
    assert response.ready_for_release is True
    assert response.requires_human_review is True
    assert response.promotion_id == "support-agent-assist-baseline-approved"
    assert response.stage_group == "approved"
    assert response.evaluation_result_count >= 2
    assert "ready_to_activate" in response.reason_codes


def test_governance_evaluation_blocks_external_auto_send() -> None:
    runtime = GovernanceEvaluationRuntime(ai_root())

    response = runtime.assess(
        {
            "tenantId": "tenant-support",
            "product": "support-platform",
            "useCaseId": "support-agent-assist",
            "promotionId": "support-agent-assist-baseline-approved",
            "externalAutoSend": True,
            "asOf": "2026-06-17",
        },
        {
            "principalId": "service:support-platform-governance-evaluation",
            "scopes": [GOVERNANCE_EVALUATION_ASSESS_SCOPE],
            "tenantIds": ["tenant-support"],
            "productIds": ["support-platform"],
            "useCaseIds": ["support-agent-assist"],
        },
    )

    assert response.decision == "blocked"
    assert response.ready_for_release is False
    assert response.blocked_reasons == ("external_auto_send_forbidden",)
    assert "external_auto_send_forbidden" in response.reason_codes


def test_governance_evaluation_enforces_policy_and_privacy_controls() -> None:
    runtime = GovernanceEvaluationRuntime(ai_root())

    try:
        runtime.assess(
            {
                "tenantId": "tenant-finance",
                "product": "support-platform",
                "useCaseId": "support-agent-assist",
                "promotionId": "support-agent-assist-baseline-approved",
            },
            {
                "principalId": "service:support-platform-governance-evaluation",
                "scopes": [GOVERNANCE_EVALUATION_ASSESS_SCOPE],
                "tenantIds": ["tenant-support"],
                "productIds": ["support-platform"],
                "useCaseIds": ["support-agent-assist"],
            },
        )
    except GovernanceEvaluationServiceError as exc:
        assert "tenant is not granted" in str(exc)
    else:
        raise AssertionError("expected tenant policy denial")

    try:
        runtime.assess(
            {
                "tenantId": "tenant-support",
                "product": "support-platform",
                "useCaseId": "support-agent-assist",
                "email": "agent@example.com",
            },
            None,
        )
    except GovernanceEvaluationPrivacyError as exc:
        assert "direct identifier evidence is forbidden" in str(exc)
    else:
        raise AssertionError("expected direct identifier rejection")

    try:
        runtime.assess(
            {
                "tenantId": "tenant-support",
                "product": "support-platform",
                "useCaseId": "support-agent-assist",
                "apiKey": "sk-not-allowed",
            },
            None,
        )
    except GovernanceEvaluationPrivacyError as exc:
        assert "secret value evidence is forbidden" in str(exc)
    else:
        raise AssertionError("expected secret value rejection")
