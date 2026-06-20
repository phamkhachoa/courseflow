from __future__ import annotations

from pathlib import Path

import yaml

from courseflow_ai_platform.governance_evaluation_incidents import (
    GovernanceEvaluationAlertDrillEvent,
    build_governance_evaluation_incident_export,
    build_governance_evaluation_incident_export_from_report,
    build_governance_evaluation_incident_export_snapshot,
)
from courseflow_ai_platform.governance_evaluation_ops import (
    GovernanceEvaluationDrillItem,
    GovernanceEvaluationOpsReport,
)


def test_governance_evaluation_incident_export_has_no_baseline_incidents() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_governance_evaluation_incident_export(
        ai_root,
        as_of="2026-06-17",
    )

    assert report.current_ops_status == "release_gate_observable"
    assert report.observation_count == 1
    assert report.consecutive_failure_count == 0
    assert report.incident_count == 0
    assert report.open_count == 0
    assert report.repeated_failure_threshold == 2
    assert report.tenant_safe is True


def test_governance_evaluation_incident_export_waits_for_repeated_failure() -> None:
    report = build_governance_evaluation_incident_export_from_report(
        ops_report=failed_release_gate_report(),
        events=(),
        as_of="2026-06-17",
    )

    assert report.current_ops_status == "blocked_by_release_gate_drill_mismatch"
    assert report.consecutive_failure_count == 1
    assert report.incident_count == 0
    assert report.open_count == 0


def test_governance_evaluation_incident_export_escalates_repeated_failures() -> None:
    report = build_governance_evaluation_incident_export_from_report(
        ops_report=failed_release_gate_report(),
        events=(
            GovernanceEvaluationAlertDrillEvent(
                event_id="prior-release-gate-mismatch",
                occurred_at="2026-06-16T09:00:00Z",
                ops_status="blocked_by_release_gate_drill_mismatch",
                failed_drill_count=1,
                unexpected_error_count=0,
                evidence_refs=("report:governance-evaluation-service-v1",),
            ),
        ),
        as_of="2026-06-17",
    )

    assert report.incident_count == 1
    assert report.open_count == 1
    assert report.p0_count == 1
    assert report.repeated_failure_count == 1
    assert report.by_condition == {
        "governance_evaluation_release_gate_mismatch": 1
    }
    incident = report.incidents[0]
    assert incident.condition == "governance_evaluation_release_gate_mismatch"
    assert incident.severity == "p0"
    assert incident.owner_role == "Admin/Ops"
    assert incident.action == "escalate_governance_evaluation_release_gate_mismatch"
    assert incident.consecutive_failure_count == 2
    assert incident.application_ref.startswith("platform:")


def test_governance_evaluation_incident_export_snapshot_suppresses_raw_ids() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    snapshot = build_governance_evaluation_incident_export_snapshot(
        ai_root,
        generated_at="2026-06-17",
        as_of="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == "governance-evaluation-incident-export-v1"
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "tenant-support" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "sk-" not in serialized


def failed_release_gate_report() -> GovernanceEvaluationOpsReport:
    return GovernanceEvaluationOpsReport(
        ops_status="blocked_by_release_gate_drill_mismatch",
        policy_id="governance-evaluation-access-policy-v1",
        route_count=3,
        evaluation_count=20,
        promotion_count=4,
        assessment_count=3,
        approved_count=1,
        review_required_count=1,
        blocked_count=1,
        direct_identifier_rejection_count=1,
        secret_value_rejection_count=1,
        unexpected_error_count=0,
        by_product={"lms-courseflow": 1, "support-platform": 2},
        by_use_case={
            "lms-related-course-recommendation": 1,
            "support-agent-assist": 2,
        },
        drills=(
            GovernanceEvaluationDrillItem(
                scenario_id="support-agent-assist-external-auto-send",
                product="support-platform",
                use_case_id="support-agent-assist",
                expected_decision="blocked",
                decision="review_required",
                ready_for_release=False,
                requires_human_review=True,
                blocked_reasons=(),
                passed=False,
            ),
        ),
    )
