from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from pathlib import Path

import yaml

from courseflow_ai_platform.registry import load_yaml

drill = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_drill"
)
governance = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance"
)

build_drill = (
    drill.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill_report
)
build_drill_from_governance = (
    drill.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill_report_from_governance
)
build_snapshot = (
    drill.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill_snapshot
)
build_release_governance = (
    governance.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_governance_report
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_suppression_policy_release_gate_drill_passes() -> None:
    report = build_drill(ai_root(), generated_at="2026-06-17")

    assert report.drill_status == "passed"
    assert report.release_governance_status == "release_governance_attached"
    assert report.release_gate_count == 5
    assert report.attached_release_gate_count == 5
    assert report.failed_release_gate_count == 0
    assert report.scenario_count == 5
    assert report.passed_count == 5
    assert report.failed_count == 0
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_effectiveness",
    )


def test_response_slo_drift_suppression_policy_release_gate_drill_blocks_gap() -> None:
    release_governance = build_release_governance(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_drill_from_governance(
        replace(
            release_governance,
            release_governance_status="release_governance_attachment_incomplete",
        ),
        generated_at="2026-06-17",
    )

    assert report.drill_status == "blocked_by_release_governance"
    assert report.failed_count == 5
    assert report.next_actions == (
        "exercise_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_drill",
    )


def test_response_slo_drift_suppression_policy_release_gate_drill_detects_gate_gap() -> None:
    release_governance = build_release_governance(
        ai_root(),
        generated_at="2026-06-17",
    )
    broken_gate = replace(
        release_governance.gates[0],
        attached=False,
        validation_errors=("release gate attachment missing",),
    )
    report = build_drill_from_governance(
        replace(
            release_governance,
            gates=(broken_gate, *release_governance.gates[1:]),
            attached_release_gate_count=4,
            failed_release_gate_count=1,
        ),
        generated_at="2026-06-17",
    )

    assert report.drill_status == "failed"
    assert report.failed_count == 1
    assert report.scenarios[0].gate_id == "coverage-slo-published-release-gate"
    assert report.scenarios[0].passed is False
    assert report.scenarios[0].observed_outcome == "release_gate_gap_detected"


def test_suppression_policy_release_gate_drill_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-drill-v1"
    )
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "tenant-support" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized


def test_suppression_policy_release_gate_drill_raw_id_detector_catches_ids() -> None:
    report = build_drill(ai_root(), generated_at="2026-06-17")
    leaked_scenario = replace(report.scenarios[0], observed_outcome="tenant-lms")

    assert drill.count_raw_identifier_markers(report.scenarios) == 0
    assert (
        drill.count_raw_identifier_markers((leaked_scenario, *report.scenarios[1:]))
        == 1
    )


def test_response_slo_drift_suppression_policy_release_gate_drill_snapshot_matches() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-drill-v1.yaml"
    )
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / report_name
    )
    generated = build_snapshot(root, generated_at="2026-06-17")

    assert checked_in == generated
