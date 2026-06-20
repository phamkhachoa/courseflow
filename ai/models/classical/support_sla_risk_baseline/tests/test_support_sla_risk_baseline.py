from __future__ import annotations

import pytest

from ai.models.classical.support_sla_risk_baseline.support_sla_risk_baseline import (
    SupportSlaRiskBaseline,
)


def test_high_risk_case_requires_human_review_and_reason_codes() -> None:
    prediction = SupportSlaRiskBaseline().predict(
        {
            "tenant_id": "tenant-support",
            "case_id": "case-001",
            "priority": "p1",
            "status": "open",
            "minutes_until_sla_due": 30,
            "age_minutes": 780,
            "public_comment_count": 7,
            "internal_note_count": 0,
            "assigned_team_available": False,
            "customer_tier": "enterprise",
            "reopen_count": 1,
        }
    )

    assert prediction.model_id == "support-sla-risk-baseline-v1"
    assert prediction.risk_band == "high"
    assert prediction.requires_human_review is True
    assert "SLA_DUE_SOON" in prediction.reason_codes
    assert "NO_AVAILABLE_TEAM_CAPACITY" in prediction.reason_codes
    assert "page_supervisor_for_review" in prediction.recommended_actions


def test_low_risk_case_uses_monitoring_action() -> None:
    prediction = SupportSlaRiskBaseline().predict(
        {
            "tenant_id": "tenant-support",
            "case_id": "case-002",
            "priority": "p3",
            "status": "open",
            "minutes_until_sla_due": 720,
            "age_minutes": 45,
            "public_comment_count": 1,
            "internal_note_count": 2,
            "assigned_team_available": True,
            "customer_tier": "standard",
            "reopen_count": 0,
        }
    )

    assert prediction.risk_band == "low"
    assert prediction.requires_human_review is False
    assert prediction.reason_codes == ("SLA_RISK_LOW",)
    assert prediction.recommended_actions == ("monitor_standard_queue",)


def test_closed_case_reduces_risk_even_with_old_age() -> None:
    prediction = SupportSlaRiskBaseline().predict(
        {
            "tenant_id": "tenant-support",
            "case_id": "case-003",
            "priority": "p2",
            "status": "resolved",
            "minutes_until_sla_due": 180,
            "age_minutes": 900,
            "public_comment_count": 2,
            "internal_note_count": 3,
            "assigned_team_available": True,
            "customer_tier": "standard",
            "reopen_count": 0,
        }
    )

    assert prediction.risk_band == "low"
    assert "SLA_WINDOW_COMPRESSED" in prediction.reason_codes


def test_invalid_tenant_is_rejected() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        SupportSlaRiskBaseline().predict(
            {
                "tenant_id": "public",
                "case_id": "case-004",
                "priority": "p2",
                "status": "open",
                "minutes_until_sla_due": 120,
                "age_minutes": 10,
                "public_comment_count": 0,
                "internal_note_count": 0,
                "assigned_team_available": True,
                "customer_tier": "standard",
                "reopen_count": 0,
            }
        )
