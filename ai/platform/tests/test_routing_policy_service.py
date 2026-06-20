from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.routing_policy_service import (
    ROUTING_POLICY_RECOMMEND_SCOPE,
    RoutingPolicyPrivacyError,
    RoutingPolicyRuntime,
    RoutingPolicyServiceError,
    load_routing_policy_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def high_priority_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ops",
        "product": "enterprise-operations",
        "useCaseId": "operations-routing-optimization",
        "policyId": "routing-policy-v1",
        "safeExplorationBudget": 0.0,
        "baselineQueueId": "queue-general",
        "workItem": {
            "workItemId": "work-1001",
            "workType": "identity_outage",
            "priority": "p1",
            "requiredSkillIds": ["identity", "integration"],
            "expectedEffortMinutes": 30,
        },
        "queues": [
            {
                "queueId": "queue-general",
                "availableAgentCount": 3,
                "backlogCount": 9,
                "averageHandleTimeMinutes": 45,
                "skillIds": ["general"],
                "maxConcurrency": 4,
            },
            {
                "queueId": "queue-identity",
                "availableAgentCount": 2,
                "backlogCount": 2,
                "averageHandleTimeMinutes": 30,
                "skillIds": ["identity", "integration"],
                "maxConcurrency": 3,
            },
        ],
    }


def constraint_violation_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ops",
        "product": "enterprise-operations",
        "useCaseId": "operations-routing-optimization",
        "policyId": "routing-policy-v1",
        "safeExplorationBudget": 0.0,
        "workItem": {
            "workItemId": "work-1003",
            "workType": "fraud_escalation",
            "priority": "p1",
            "requiredSkillIds": ["fraud"],
            "expectedEffortMinutes": 40,
        },
        "queues": [
            {
                "queueId": "queue-general",
                "availableAgentCount": 1,
                "backlogCount": 1,
                "averageHandleTimeMinutes": 35,
                "skillIds": ["general"],
                "maxConcurrency": 2,
            }
        ],
    }


def exploration_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ops",
        "product": "enterprise-operations",
        "useCaseId": "operations-routing-optimization",
        "policyId": "routing-policy-v1",
        "safeExplorationBudget": 0.1,
        "baselineQueueId": "queue-ops-b",
        "workItem": {
            "workItemId": "work-1002",
            "workType": "ops_question",
            "priority": "p3",
            "requiredSkillIds": ["operations"],
            "expectedEffortMinutes": 20,
        },
        "queues": [
            {
                "queueId": "queue-ops-a",
                "availableAgentCount": 2,
                "backlogCount": 3,
                "averageHandleTimeMinutes": 20,
                "skillIds": ["operations"],
                "maxConcurrency": 3,
            },
            {
                "queueId": "queue-ops-b",
                "availableAgentCount": 2,
                "backlogCount": 4,
                "averageHandleTimeMinutes": 22,
                "skillIds": ["operations"],
                "maxConcurrency": 3,
            },
        ],
    }


def test_routing_policy_recommends_queue_without_online_activation() -> None:
    root = ai_root()
    policy = load_routing_policy_access_policy(root)
    principal = policy.resolve_principal(
        "service:enterprise-operations-routing",
        (ROUTING_POLICY_RECOMMEND_SCOPE,),
    )
    runtime = RoutingPolicyRuntime(root)

    response = runtime.recommend(high_priority_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["model_id"] == "operations-routing-policy-simulator-v1"
    assert response["assigned_queue_id"] == "queue-identity"
    assert response["requires_human_review"] is False
    assert response["onlinePolicyActivationAllowed"] is False
    assert response["decisionPolicy"] == "simulator_only_human_review_before_online_routing"
    assert metrics.recommendation_count == 1
    assert metrics.human_review_count == 0
    assert metrics.by_work_type == {"identity_outage": 1}


def test_routing_policy_marks_constraint_violation_for_human_review() -> None:
    root = ai_root()
    policy = load_routing_policy_access_policy(root)
    principal = policy.resolve_principal(
        "service:enterprise-operations-routing",
        (ROUTING_POLICY_RECOMMEND_SCOPE,),
    )
    runtime = RoutingPolicyRuntime(root)

    response = runtime.recommend(constraint_violation_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["assigned_queue_id"] == "queue-general"
    assert response["requires_human_review"] is True
    assert response["constraint_violations"] == ["MISSING_REQUIRED_SKILL"]
    assert metrics.constraint_violation_count == 1
    assert metrics.human_review_count == 1


def test_routing_policy_tracks_safe_exploration_metrics() -> None:
    root = ai_root()
    policy = load_routing_policy_access_policy(root)
    principal = policy.resolve_principal(
        "service:enterprise-operations-routing",
        (ROUTING_POLICY_RECOMMEND_SCOPE,),
    )
    runtime = RoutingPolicyRuntime(root)

    response = runtime.recommend(exploration_body(), principal).to_dict()

    assert response["exploration_budget_used"] == 0.05
    assert runtime.snapshot_metrics().exploration_budget_used_count == 1


def test_routing_policy_rejects_cross_tenant_and_direct_identifier() -> None:
    root = ai_root()
    policy = load_routing_policy_access_policy(root)
    principal = policy.resolve_principal(
        "service:enterprise-operations-routing",
        (ROUTING_POLICY_RECOMMEND_SCOPE,),
    )
    runtime = RoutingPolicyRuntime(root)

    with pytest.raises(RoutingPolicyServiceError, match="tenant is not granted"):
        runtime.recommend({**high_priority_body(), "tenantId": "tenant-finance"}, principal)

    with pytest.raises(RoutingPolicyPrivacyError, match="direct identifier"):
        runtime.recommend({**high_priority_body(), "agentId": "agent-raw-001"}, principal)
    assert runtime.snapshot_metrics().direct_identifier_rejection_count == 1


def test_routing_policy_policy_exposes_enterprise_ops_grants_only() -> None:
    policy = load_routing_policy_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:enterprise-operations-routing",
        (ROUTING_POLICY_RECOMMEND_SCOPE,),
    )

    assert principal.product_ids == ("enterprise-operations",)
    assert principal.use_case_ids == ("operations-routing-optimization",)
    assert "tenant-ops" in principal.tenant_ids
