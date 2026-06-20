from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.serving_access_policy_reconciliation import (
    build_serving_access_policy_reconciliation_report,
    build_serving_access_policy_reconciliation_snapshot,
)


def test_serving_access_policy_reconciliation_detects_pending_policy_apply() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_policy_reconciliation_report(ai_root)

    assert report.application_count == 1
    assert report.pending_apply_count == 1
    assert report.reconciled_count == 0
    assert report.ledger_update_required_count == 0
    assert report.drift_count == 0
    assert report.action_queue["pending_apply"] == [
        "lms-sequence-risk-sandbox-tenant-apply-20260617"
    ]


def test_serving_access_policy_reconciliation_item_explains_next_action() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_policy_reconciliation_report(ai_root)
    item = report.items[0]

    assert item.reconciliation_status == "pending_policy_apply"
    assert item.action == "run_controlled_policy_applier"
    assert item.ledger_status == "approved"
    assert item.active_policy_sha256 == item.source_policy_sha256
    assert item.active_policy_sha256 != item.proposed_policy_sha256
    assert item.validation_errors == ()


def test_serving_access_policy_reconciliation_snapshot_contract() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    snapshot = build_serving_access_policy_reconciliation_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert snapshot["report_id"] == "model-serving-access-policy-reconciliation-v1"
    assert snapshot["generated_at"] == "2026-06-17"
    assert snapshot["summary"]["pending_apply_count"] == 1
    assert snapshot["summary"]["drift_count"] == 0
    assert snapshot["action_queue"]["pending_apply"] == [
        "lms-sequence-risk-sandbox-tenant-apply-20260617"
    ]
