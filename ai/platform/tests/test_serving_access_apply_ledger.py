from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.serving_access_apply_ledger import (
    APPLY_REVIEWER_ROLES,
    build_serving_access_apply_ledger_report,
    build_serving_access_apply_ledger_snapshot,
)


def test_serving_access_apply_ledger_projects_ready_to_apply_queue() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_apply_ledger_report(ai_root)

    assert report.application_count == 1
    assert report.ready_to_apply_count == 1
    assert report.pending_review_count == 0
    assert report.applied_count == 0
    assert report.blocked_count == 0
    assert report.checksum_mismatch_count == 0
    assert report.action_queue["ready_to_apply"] == [
        "lms-sequence-risk-sandbox-tenant-apply-20260617"
    ]


def test_serving_access_apply_ledger_validates_checksums_and_reviewers() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_apply_ledger_report(ai_root)
    item = report.items[0]

    assert item.checksum_status == "matched"
    assert item.source_policy_sha256 == report.source_policy_sha256
    assert item.proposed_policy_sha256 == report.proposed_policy_sha256
    assert item.required_reviewer_roles == APPLY_REVIEWER_ROLES
    assert item.missing_reviewer_roles == ()
    assert item.validation_errors == ()
    assert [reviewer.role for reviewer in item.reviewers] == [
        "Admin/Ops",
        "Governance Reviewer",
    ]


def test_serving_access_apply_ledger_snapshot_uses_report_contract() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    snapshot = build_serving_access_apply_ledger_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert snapshot["report_id"] == "model-serving-access-policy-apply-ledger-v1"
    assert snapshot["generated_at"] == "2026-06-17"
    assert snapshot["summary"]["application_count"] == 1
    assert snapshot["summary"]["ready_to_apply_count"] == 1
    assert snapshot["summary"]["checksum_mismatch_count"] == 0
    assert snapshot["action_queue"]["ready_to_apply"] == [
        "lms-sequence-risk-sandbox-tenant-apply-20260617"
    ]
