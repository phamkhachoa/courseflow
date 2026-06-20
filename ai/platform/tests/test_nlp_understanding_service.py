from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.nlp_understanding_service import (
    NLP_UNDERSTANDING_ANALYZE_SCOPE,
    NlpUnderstandingPrivacyError,
    NlpUnderstandingRuntime,
    NlpUnderstandingServiceError,
    load_nlp_understanding_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_nlp_understanding_runtime_classifies_support_case_and_tracks_metrics() -> None:
    policy = load_nlp_understanding_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:support-platform-nlp",
        (NLP_UNDERSTANDING_ANALYZE_SCOPE,),
    )
    runtime = NlpUnderstandingRuntime(ai_root())

    response = runtime.analyze(
        {
            "tenantId": "tenant-a",
            "product": "support-platform",
            "useCaseId": "support-agent-assist",
            "subject": "Urgent login outage",
            "latestMessage": "All admins are blocked by MFA timeout errors.",
            "productArea": "identity",
            "priority": "urgent",
            "taskType": "case_triage",
        },
        principal,
    )
    metrics = runtime.snapshot_metrics()

    assert response.intent == "access"
    assert response.priority_signal == "high"
    assert response.requires_human_review is True
    assert "identity_access" in response.semantic_tags
    assert "access" in response.retrieval_query
    assert metrics.analysis_count == 1
    assert metrics.by_use_case == {"support-agent-assist": 1}


def test_nlp_understanding_runtime_builds_lms_rubric_feedback() -> None:
    policy = load_nlp_understanding_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:lms-courseflow-nlp",
        (NLP_UNDERSTANDING_ANALYZE_SCOPE,),
    )
    runtime = NlpUnderstandingRuntime(ai_root())

    response = runtime.analyze(
        {
            "tenantId": "tenant-a",
            "product": "lms-courseflow",
            "useCaseId": "lms-auto-grading",
            "text": "The answer explains Python loops, break and continue.",
            "taskType": "rubric_feedback",
            "rubricItems": ["mention loop control", "mention missing while loop"],
            "expectedTerms": ["Python loops", "break", "continue", "while loop"],
        },
        principal,
    )

    assert response.intent == "learning_assessment"
    assert response.requires_human_review is True
    assert response.matched_terms == ("Python loops", "break", "continue")
    assert response.missing_terms == ("while loop",)
    assert any("Needs review" in item for item in response.rubric_feedback)


def test_nlp_understanding_policy_and_privacy_controls() -> None:
    policy = load_nlp_understanding_access_policy(ai_root())
    support_principal = policy.resolve_principal(
        "service:support-platform-nlp",
        (NLP_UNDERSTANDING_ANALYZE_SCOPE,),
    )
    runtime = NlpUnderstandingRuntime(ai_root())

    with pytest.raises(NlpUnderstandingServiceError, match="ungranted scopes"):
        policy.resolve_principal(
            "service:support-platform-nlp",
            ("internal:ai-platform:nlp-understanding:ops",),
        )
    with pytest.raises(NlpUnderstandingServiceError, match="use case is not granted"):
        runtime.analyze(
            {
                "tenantId": "tenant-a",
                "product": "support-platform",
                "useCaseId": "enterprise-knowledge-assistant",
                "text": "Find policy documents about access reviews.",
            },
            support_principal,
        )
    with pytest.raises(NlpUnderstandingPrivacyError, match="direct raw identifiers"):
        runtime.analyze(
            {
                "tenantId": "tenant-a",
                "product": "support-platform",
                "useCaseId": "support-agent-assist",
                "text": "Please inspect customer_id=raw-123.",
            },
            support_principal,
        )
