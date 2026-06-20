from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from support_agent_assist import SupportAgentAssistBaseline, SupportAgentAssistInput


def test_support_agent_assist_classifies_billing_case() -> None:
    model = SupportAgentAssistBaseline()

    result = model.assist(
        SupportAgentAssistInput(
            tenant_id="tenant-a",
            case_id="case-1",
            subject="Refund request for duplicate charge",
            latest_message="The customer paid twice and needs a refund before month end.",
            product_area="billing",
        )
    )

    assert result.intent == "billing"
    assert result.requires_human_review is True
    assert "billing" in result.retrieval_query
    assert "HUMAN_REVIEW_REQUIRED" in result.reason_codes
    assert result.confidence >= 0.7


def test_support_agent_assist_marks_urgent_access_case_high_priority() -> None:
    model = SupportAgentAssistBaseline()

    result = model.assist(
        SupportAgentAssistInput(
            tenant_id="tenant-a",
            case_id="case-2",
            subject="Urgent login outage",
            latest_message="All admins are blocked by MFA timeout errors.",
            priority="urgent",
        )
    )

    assert result.intent == "access"
    assert result.priority_signal == "high"
    assert "PRIORITY_HIGH_KEYWORD" in result.reason_codes


def test_support_agent_assist_requires_tenant_and_case() -> None:
    model = SupportAgentAssistBaseline()

    try:
        model.assist(
            SupportAgentAssistInput(
                tenant_id="",
                case_id="case-3",
                subject="Question",
                latest_message="Need help",
            )
        )
    except ValueError as exc:
        assert "tenant_id" in str(exc)
    else:
        raise AssertionError("tenant_id validation did not fail")

