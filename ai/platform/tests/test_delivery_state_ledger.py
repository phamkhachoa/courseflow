from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.delivery_backlog import build_delivery_backlog_report
from courseflow_ai_platform.delivery_state_ledger import (
    build_delivery_state_report,
    build_delivery_state_snapshot,
    load_delivery_state_transitions,
)
from courseflow_ai_platform.registry import load_yaml


def test_delivery_state_ledger_loads_persisted_transitions() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    transitions = load_delivery_state_transitions(ai_root)

    assert len(transitions) == 4
    assert transitions[0].transition_id == "serving-access-policy-applier-started-20260617"
    assert transitions[0].target_status == "in_progress"
    assert transitions[0].updated_by == "adminops-ai-platform"
    assert (
        transitions[1].transition_id
        == "governance-evaluation-alert-drill-accepted-20260617"
    )
    assert transitions[1].target_status == "accepted"
    assert transitions[1].updated_by == "adminops-ai-platform"
    assert (
        transitions[2].transition_id
        == "governance-evaluation-response-runbook-drill-accepted-20260617"
    )
    assert transitions[2].target_status == "accepted"
    assert transitions[2].updated_by == "adminops-ai-platform"
    assert (
        transitions[3].transition_id
        == "product-readiness-freshness-response-drill-accepted-20260617"
    )
    assert transitions[3].target_status == "accepted"
    assert transitions[3].updated_by == "adminops-ai-platform"


def test_delivery_state_report_projects_applied_transitions() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_delivery_state_report(ai_root, as_of="2026-06-17")

    assert report.transition_count == 4
    assert report.applied_count == 4
    assert report.missing_action_count == 0
    assert report.in_progress_count == 1
    assert report.accepted_count == 3
    items = {item.transition_id: item for item in report.items}
    serving_access_item = items["serving-access-policy-applier-started-20260617"]
    assert serving_access_item.previous_status == "ready"
    assert serving_access_item.applied_status == "in_progress"
    assert serving_access_item.backlog_id == "AIP-BLG-0019"
    assert serving_access_item.owner_role == "Admin/Ops"

    governance_eval_item = items[
        "governance-evaluation-alert-drill-accepted-20260617"
    ]
    assert governance_eval_item.previous_status == "ready"
    assert governance_eval_item.applied_status == "accepted"
    assert governance_eval_item.backlog_id == "AIP-BLG-0021"
    assert governance_eval_item.delivery_phase == "governance_review"
    assert governance_eval_item.owner_role == "Admin/Ops"

    governance_eval_response_item = items[
        "governance-evaluation-response-runbook-drill-accepted-20260617"
    ]
    assert governance_eval_response_item.previous_status == "ready"
    assert governance_eval_response_item.applied_status == "accepted"
    assert governance_eval_response_item.backlog_id == "AIP-BLG-0022"
    assert governance_eval_response_item.delivery_phase == "governance_review"
    assert governance_eval_response_item.owner_role == "Admin/Ops"

    product_readiness_response_item = items[
        "product-readiness-freshness-response-drill-accepted-20260617"
    ]
    assert product_readiness_response_item.previous_status == "ready"
    assert product_readiness_response_item.applied_status == "accepted"
    assert product_readiness_response_item.backlog_id == "AIP-BLG-0023"
    assert product_readiness_response_item.delivery_phase == "governance_review"
    assert product_readiness_response_item.owner_role == "Admin/Ops"


def test_delivery_backlog_applies_state_ledger_without_mutating_base_projection() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    base_report = build_delivery_backlog_report(
        ai_root,
        as_of="2026-06-17",
        apply_state_ledger=False,
    )
    applied_report = build_delivery_backlog_report(ai_root, as_of="2026-06-17")
    base_items = {item.backlog_id: item for item in base_report.items}
    applied_items = {item.backlog_id: item for item in applied_report.items}

    assert base_items["AIP-BLG-0019"].status == "ready"
    assert base_items["AIP-BLG-0019"].ready_to_start is True
    assert applied_items["AIP-BLG-0019"].status == "in_progress"
    assert applied_items["AIP-BLG-0019"].ready_to_start is False
    assert base_items["AIP-BLG-0021"].status == "ready"
    assert base_items["AIP-BLG-0021"].ready_to_start is True
    assert applied_items["AIP-BLG-0021"].status == "accepted"
    assert applied_items["AIP-BLG-0021"].ready_to_start is False
    assert base_items["AIP-BLG-0022"].status == "ready"
    assert base_items["AIP-BLG-0022"].ready_to_start is True
    assert applied_items["AIP-BLG-0022"].status == "accepted"
    assert applied_items["AIP-BLG-0022"].ready_to_start is False
    assert base_items["AIP-BLG-0023"].status == "ready"
    assert base_items["AIP-BLG-0023"].ready_to_start is True
    assert applied_items["AIP-BLG-0023"].status == "accepted"
    assert applied_items["AIP-BLG-0023"].ready_to_start is False
    assert applied_report.ready_to_start_count == base_report.ready_to_start_count - 4


def test_delivery_state_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "delivery" / "reports" / "delivery-state-v1.yaml"
    )
    generated = build_delivery_state_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in == generated
