from __future__ import annotations

from pathlib import Path

import yaml

from courseflow_ai_platform.governance_evaluation_incidents import (
    build_governance_evaluation_incident_export,
)
from courseflow_ai_platform.governance_evaluation_response_drill import (
    build_governance_evaluation_incident_response_drill_report,
    build_governance_evaluation_incident_response_drill_report_from_spec,
    build_governance_evaluation_incident_response_drill_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_governance_evaluation_response_drill_passes_baseline() -> None:
    report = build_governance_evaluation_incident_response_drill_report(
        ai_root(),
        generated_at="2026-06-17",
    )

    assert report.drill_status == "passed"
    assert report.current_incident_count == 0
    assert report.current_open_incident_count == 0
    assert report.scenario_count == 3
    assert report.p0_scenario_count == 2
    assert report.p1_scenario_count == 1
    assert report.failed_count == 0
    assert report.response_step_count == 8
    assert report.tenant_safe is True


def test_governance_evaluation_response_drill_validates_routes_and_steps() -> None:
    report = build_governance_evaluation_incident_response_drill_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    scenarios = {scenario.scenario_id: scenario for scenario in report.scenarios}

    mismatch = scenarios["release-gate-mismatch-p0"]
    assert mismatch.condition == "governance_evaluation_release_gate_mismatch"
    assert mismatch.expected_severity == "p0"
    assert mismatch.observed_owner_role == "Admin/Ops"
    assert mismatch.observed_action == (
        "escalate_governance_evaluation_release_gate_mismatch"
    )
    assert mismatch.incident_status == "open"
    assert mismatch.application_ref.startswith("platform:")
    assert "detect" in mismatch.runbook_step_ids
    assert "close" in mismatch.runbook_step_ids

    guardrail = scenarios["guardrail-gap-p1"]
    assert guardrail.expected_severity == "p1"
    assert guardrail.observed_action == "complete_governance_evaluation_guardrail_drills"


def test_governance_evaluation_response_drill_blocks_missing_runbook_step() -> None:
    root = ai_root()
    runbook = load_yaml(
        root
        / "platform"
        / "operations"
        / "runbooks"
        / "governance-evaluation-incident-response-v1.yaml"
    )
    runbook["required_steps"] = [
        step for step in runbook["required_steps"] if step["step_id"] != "close"
    ]
    current_export = build_governance_evaluation_incident_export(
        root,
        as_of="2026-06-17",
    )

    report = build_governance_evaluation_incident_response_drill_report_from_spec(
        runbook,
        current_export=current_export,
        generated_at="2026-06-17",
        root=root,
    )

    assert report.drill_status == "blocked"
    assert report.failed_count == 3
    assert all(
        "runbook missing required steps: close" in scenario.validation_errors
        for scenario in report.scenarios
    )


def test_governance_evaluation_response_drill_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_governance_evaluation_incident_response_drill_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == "governance-evaluation-incident-response-drill-v1"
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "tenant-support" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "sk-" not in serialized


def test_governance_evaluation_response_drill_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "governance-evaluation-incident-response-drill-v1.yaml"
    )
    generated = build_governance_evaluation_incident_response_drill_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
