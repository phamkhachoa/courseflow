from __future__ import annotations

import pytest

from ai.models.bandit_rl.routing_policy_simulator.routing_policy_simulator import (
    RoutingPolicySimulator,
)


def test_routing_policy_simulator_assigns_best_skill_and_capacity_queue() -> None:
    simulator = RoutingPolicySimulator()

    decision = simulator.recommend(
        {
            "tenant_id": "tenant-ops",
            "policy_id": "routing-policy-v1",
            "safe_exploration_budget": 0.0,
            "baseline_queue_id": "queue-general",
            "work_item": {
                "work_item_id": "work-1001",
                "work_type": "identity_outage",
                "priority": "p1",
                "required_skill_ids": ["identity", "integration"],
                "expected_effort_minutes": 30,
            },
            "queues": [
                {
                    "queue_id": "queue-general",
                    "available_agent_count": 3,
                    "backlog_count": 9,
                    "average_handle_time_minutes": 45,
                    "skill_ids": ["general"],
                    "max_concurrency": 4,
                },
                {
                    "queue_id": "queue-identity",
                    "available_agent_count": 2,
                    "backlog_count": 2,
                    "average_handle_time_minutes": 30,
                    "skill_ids": ["identity", "integration"],
                    "max_concurrency": 3,
                },
            ],
        }
    )

    assert decision.model_id == "operations-routing-policy-simulator-v1"
    assert decision.assigned_queue_id == "queue-identity"
    assert decision.constraint_violations == ()
    assert decision.baseline_score_delta > 0.2
    assert "NO_EXPLORATION_FOR_HIGH_PRIORITY" in decision.reason_codes


def test_routing_policy_simulator_uses_safe_exploration_for_close_low_risk_queues() -> None:
    simulator = RoutingPolicySimulator()

    decision = simulator.recommend(
        {
            "tenant_id": "tenant-ops",
            "policy_id": "routing-policy-v1",
            "safe_exploration_budget": 0.1,
            "baseline_queue_id": "queue-ops-b",
            "work_item": {
                "work_item_id": "work-1002",
                "work_type": "ops_question",
                "priority": "p3",
                "required_skill_ids": ["operations"],
                "expected_effort_minutes": 20,
            },
            "queues": [
                {
                    "queue_id": "queue-ops-a",
                    "available_agent_count": 2,
                    "backlog_count": 3,
                    "average_handle_time_minutes": 20,
                    "skill_ids": ["operations"],
                    "max_concurrency": 3,
                },
                {
                    "queue_id": "queue-ops-b",
                    "available_agent_count": 2,
                    "backlog_count": 4,
                    "average_handle_time_minutes": 22,
                    "skill_ids": ["operations"],
                    "max_concurrency": 3,
                },
            ],
        }
    )

    assert decision.assigned_queue_id == "queue-ops-a"
    assert decision.exploration_budget_used == 0.05
    assert "SAFE_EXPLORATION_AVAILABLE" in decision.reason_codes


def test_routing_policy_simulator_marks_constraint_violations_for_review() -> None:
    simulator = RoutingPolicySimulator()

    decision = simulator.recommend(
        {
            "tenant_id": "tenant-ops",
            "policy_id": "routing-policy-v1",
            "safe_exploration_budget": 0.0,
            "work_item": {
                "work_item_id": "work-1003",
                "work_type": "fraud_escalation",
                "priority": "p1",
                "required_skill_ids": ["fraud"],
                "expected_effort_minutes": 40,
            },
            "queues": [
                {
                    "queue_id": "queue-general",
                    "available_agent_count": 1,
                    "backlog_count": 1,
                    "average_handle_time_minutes": 35,
                    "skill_ids": ["general"],
                    "max_concurrency": 2,
                }
            ],
        }
    )

    assert decision.assigned_queue_id == "queue-general"
    assert decision.requires_human_review is True
    assert decision.constraint_violations == ("MISSING_REQUIRED_SKILL",)
    assert "HUMAN_REVIEW_REQUIRED" in decision.reason_codes


def test_routing_policy_simulator_requires_bounded_tenant() -> None:
    simulator = RoutingPolicySimulator()

    with pytest.raises(ValueError, match="tenant_id"):
        simulator.recommend(
            {
                "tenant_id": "public",
                "policy_id": "routing-policy-v1",
                "work_item": {
                    "work_item_id": "work-1004",
                    "work_type": "ops_question",
                    "priority": "p2",
                    "required_skill_ids": ["operations"],
                    "expected_effort_minutes": 20,
                },
                "queues": [
                    {
                        "queue_id": "queue-ops",
                        "available_agent_count": 1,
                        "backlog_count": 0,
                        "average_handle_time_minutes": 20,
                        "skill_ids": ["operations"],
                        "max_concurrency": 2,
                    }
                ],
            }
        )
