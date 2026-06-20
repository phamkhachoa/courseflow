from __future__ import annotations

from pathlib import Path

import yaml

from courseflow_ai_platform.serving_access_apply_ledger import (
    ServingAccessApplyLedgerItem,
    ServingAccessApplyLedgerReport,
)
from courseflow_ai_platform.serving_access_incidents import (
    build_serving_access_incident_export,
    build_serving_access_incident_export_from_reports,
    build_serving_access_incident_export_snapshot,
)
from courseflow_ai_platform.serving_access_policy_reconciliation import (
    ServingAccessPolicyReconciliationItem,
    ServingAccessPolicyReconciliationReport,
)


def test_serving_access_incident_export_tracks_current_pending_apply_as_watch() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_incident_export(ai_root, as_of="2026-06-17")

    assert report.incident_count == 1
    assert report.watch_count == 1
    assert report.open_count == 0
    assert report.p2_count == 1
    assert report.stale_pending_apply_count == 0
    assert report.tenant_safe is True
    incident = report.incidents[0]
    assert incident.condition == "pending_policy_apply"
    assert incident.incident_status == "watch"
    assert incident.severity == "p2"
    assert incident.action == "run_controlled_policy_applier"
    assert incident.application_ref.startswith("application:")
    assert incident.age_days == 0


def test_serving_access_incident_export_escalates_stale_pending_apply() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_incident_export(ai_root, as_of="2026-06-20")

    assert report.incident_count == 1
    assert report.open_count == 1
    assert report.watch_count == 0
    assert report.p1_count == 1
    assert report.stale_pending_apply_count == 1
    incident = report.incidents[0]
    assert incident.condition == "stale_pending_policy_apply"
    assert incident.action == "escalate_stale_policy_apply"
    assert incident.age_days == 3


def test_serving_access_incident_export_suppresses_raw_identifiers() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    snapshot = build_serving_access_incident_export_snapshot(
        ai_root,
        generated_at="2026-06-17",
        as_of="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "service:lms-courseflow-serving" not in serialized
    assert "lms-sequence-risk-sandbox-tenant" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_serving_access_incident_export_snapshot_contract() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    snapshot = build_serving_access_incident_export_snapshot(
        ai_root,
        generated_at="2026-06-17",
        as_of="2026-06-17",
    )

    assert snapshot["report_id"] == "model-serving-access-incident-export-v1"
    assert snapshot["generated_at"] == "2026-06-17"
    assert snapshot["summary"]["incident_count"] == 1
    assert snapshot["summary"]["watch_count"] == 1
    assert snapshot["by_condition"] == {"pending_policy_apply": 1}
    assert snapshot["action_queue"]["watch"] == [
        snapshot["incidents"][0]["incident_id"]
    ]
    assert snapshot["incidents"][0]["application_ref"].startswith("application:")


def test_serving_access_incident_export_promotes_drift_and_blocked_apply_to_p0() -> None:
    reconciliation_report = ServingAccessPolicyReconciliationReport(
        application_count=1,
        pending_apply_count=0,
        reconciled_count=0,
        ledger_update_required_count=0,
        drift_count=1,
        rejected_count=0,
        active_policy_sha256="sha256:active",
        by_status={"active_policy_drift": 1},
        by_action={"investigate_active_policy_drift": 1},
        action_queue={
            "pending_apply": [],
            "ledger_update_required": [],
            "reconciled": [],
            "drift": ["drift-application"],
            "rejected": [],
        },
        items=(
            ServingAccessPolicyReconciliationItem(
                application_id="drift-application",
                ledger_status="approved",
                reconciliation_status="active_policy_drift",
                action="investigate_active_policy_drift",
                active_policy_sha256="sha256:active",
                source_policy_sha256="sha256:source",
                proposed_policy_sha256="sha256:proposed",
                applied_policy_sha256="",
                request_ids=("request-a",),
                validation_errors=(),
            ),
        ),
    )
    apply_ledger_report = ServingAccessApplyLedgerReport(
        application_count=1,
        ready_to_apply_count=0,
        pending_review_count=0,
        applied_count=0,
        rejected_count=0,
        blocked_count=1,
        checksum_mismatch_count=1,
        source_policy_sha256="sha256:source",
        proposed_policy_sha256="sha256:proposed",
        by_status={"approved": 1},
        by_action={"block_policy_apply_until_ledger_fixed": 1},
        action_queue={
            "blocked": ["blocked-application"],
            "pending_review": [],
            "ready_to_apply": [],
            "applied": [],
            "rejected": [],
        },
        items=(
            ServingAccessApplyLedgerItem(
                application_id="blocked-application",
                status="approved",
                plan_id="plan-v1",
                request_ids=("request-b",),
                required_reviewer_roles=("Admin/Ops", "Governance Reviewer"),
                missing_reviewer_roles=("Governance Reviewer",),
                source_policy_sha256="sha256:wrong-source",
                expected_source_policy_sha256="sha256:source",
                proposed_policy_sha256="sha256:wrong-proposed",
                expected_proposed_policy_sha256="sha256:proposed",
                checksum_status="mismatched",
                validation_errors=("source_policy_sha256 does not match current source policy",),
                action="block_policy_apply_until_ledger_fixed",
                reviewers=(),
            ),
        ),
    )

    report = build_serving_access_incident_export_from_reports(
        reconciliation_report=reconciliation_report,
        apply_ledger_report=apply_ledger_report,
        as_of="2026-06-17",
    )

    assert report.incident_count == 2
    assert report.open_count == 2
    assert report.p0_count == 2
    assert report.drift_count == 1
    assert report.blocked_apply_count == 1
    assert report.by_condition == {
        "blocked_policy_apply": 1,
        "policy_drift": 1,
    }
