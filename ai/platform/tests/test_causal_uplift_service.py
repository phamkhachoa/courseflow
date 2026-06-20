from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.causal_uplift_service import (
    CAUSAL_UPLIFT_EVALUATE_SCOPE,
    CausalUpliftPrivacyError,
    CausalUpliftRuntime,
    CausalUpliftServiceError,
    load_causal_uplift_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def enterprise_uplift_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ai",
        "product": "ai-platform",
        "useCaseId": "enterprise-experimentation-uplift",
        "experimentId": "exp-1001",
        "outcomeName": "activation",
        "treatmentName": "new_onboarding",
        "controlName": "current_onboarding",
        "treatmentCount": 320,
        "treatmentSuccesses": 154,
        "controlCount": 320,
        "controlSuccesses": 112,
        "minimumDetectableLift": 0.03,
        "confidenceLevel": 0.95,
        "guardrailMetricDelta": 0.0,
        "highImpact": True,
        "segmentCount": 3,
    }


def lms_inconclusive_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-lms",
        "product": "lms-courseflow",
        "useCaseId": "lms-intervention-effectiveness",
        "experimentId": "exp-lms-1001",
        "outcomeName": "course_completion",
        "treatmentName": "mentor_nudge",
        "controlName": "standard_reminder",
        "treatmentCount": 120,
        "treatmentSuccesses": 72,
        "controlCount": 120,
        "controlSuccesses": 70,
        "minimumDetectableLift": 0.05,
        "confidenceLevel": 0.95,
        "guardrailMetricDelta": 0.0,
        "highImpact": False,
        "segmentCount": 1,
    }


def guardrail_risk_body() -> dict[str, object]:
    return {
        **enterprise_uplift_body(),
        "experimentId": "exp-1002",
        "guardrailMetricDelta": -0.04,
    }


def test_causal_uplift_evaluates_cross_domain_experiment_without_rollout() -> None:
    root = ai_root()
    policy = load_causal_uplift_access_policy(root)
    principal = policy.resolve_principal(
        "service:ai-platform-experimentation",
        (CAUSAL_UPLIFT_EVALUATE_SCOPE,),
    )
    runtime = CausalUpliftRuntime(root)

    response = runtime.evaluate(enterprise_uplift_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["modelId"] == "causal-uplift-baseline-v1"
    assert response["decisionBand"] == "positive_lift"
    assert response["recommendation"] == "promote_to_shadow_review"
    assert response["requiresHumanReview"] is True
    assert response["automatedRolloutAllowed"] is False
    assert response["decisionPolicy"] == (
        "aggregate_uplift_review_only_human_approval_before_rollout"
    )
    assert metrics.evaluation_count == 1
    assert metrics.positive_lift_count == 1
    assert metrics.human_review_count == 1
    assert metrics.by_product == {"ai-platform": 1}


def test_causal_uplift_serves_lms_aggregate_snapshot() -> None:
    root = ai_root()
    policy = load_causal_uplift_access_policy(root)
    principal = policy.resolve_principal(
        "service:lms-experimentation-uplift",
        (CAUSAL_UPLIFT_EVALUATE_SCOPE,),
    )
    runtime = CausalUpliftRuntime(root)

    response = runtime.evaluate(lms_inconclusive_body(), principal).to_dict()

    assert response["tenantId"] == "tenant-lms"
    assert response["product"] == "lms-courseflow"
    assert response["useCaseId"] == "lms-intervention-effectiveness"
    assert response["decisionBand"] == "inconclusive"
    assert response["requiresHumanReview"] is False


def test_causal_uplift_marks_guardrail_risk_for_human_review() -> None:
    root = ai_root()
    policy = load_causal_uplift_access_policy(root)
    principal = policy.resolve_principal(
        "service:ai-platform-experimentation",
        (CAUSAL_UPLIFT_EVALUATE_SCOPE,),
    )
    runtime = CausalUpliftRuntime(root)

    response = runtime.evaluate(guardrail_risk_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["decisionBand"] == "guardrail_risk"
    assert response["recommendation"] == "stop_or_redesign"
    assert response["requiresHumanReview"] is True
    assert "GUARDRAIL_REGRESSION" in response["reasonCodes"]
    assert metrics.guardrail_risk_count == 1
    assert metrics.human_review_count == 1


def test_causal_uplift_rejects_cross_tenant_and_direct_identifier() -> None:
    root = ai_root()
    policy = load_causal_uplift_access_policy(root)
    principal = policy.resolve_principal(
        "service:ai-platform-experimentation",
        (CAUSAL_UPLIFT_EVALUATE_SCOPE,),
    )
    runtime = CausalUpliftRuntime(root)

    with pytest.raises(CausalUpliftServiceError, match="tenant is not granted"):
        runtime.evaluate({**enterprise_uplift_body(), "tenantId": "tenant-lms"}, principal)

    with pytest.raises(CausalUpliftPrivacyError, match="direct identifier"):
        runtime.evaluate({**enterprise_uplift_body(), "learnerId": "learner-001"}, principal)
    assert runtime.snapshot_metrics().direct_identifier_rejection_count == 1


def test_causal_uplift_policy_exposes_ai_platform_and_lms_grants() -> None:
    policy = load_causal_uplift_access_policy(ai_root())
    ai_platform = policy.resolve_principal(
        "service:ai-platform-experimentation",
        (CAUSAL_UPLIFT_EVALUATE_SCOPE,),
    )
    lms = policy.resolve_principal(
        "service:lms-experimentation-uplift",
        (CAUSAL_UPLIFT_EVALUATE_SCOPE,),
    )

    assert ai_platform.product_ids == ("ai-platform",)
    assert ai_platform.use_case_ids == ("enterprise-experimentation-uplift",)
    assert "tenant-ai" in ai_platform.tenant_ids
    assert lms.product_ids == ("lms-courseflow",)
    assert lms.use_case_ids == ("lms-intervention-effectiveness",)
