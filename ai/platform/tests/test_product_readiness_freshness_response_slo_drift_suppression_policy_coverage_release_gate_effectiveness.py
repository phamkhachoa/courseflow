from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from pathlib import Path

import yaml

from courseflow_ai_platform.registry import load_yaml

effectiveness = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_effectiveness"
)
drill = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_drill"
)

build_effectiveness = (
    effectiveness.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness_report
)
build_effectiveness_from_drill = (
    effectiveness.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness_report_from_drill
)
build_snapshot = (
    effectiveness.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness_snapshot
)
build_drill = (
    drill.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill_report
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_release_gate_effectiveness_is_monitored() -> None:
    report = build_effectiveness(ai_root(), generated_at="2026-06-17")

    assert report.monitor_status == "effectiveness_monitored"
    assert report.drill_status == "passed"
    assert report.release_governance_status == "release_governance_attached"
    assert report.release_gate_count == 5
    assert report.scenario_count == 5
    assert report.passed_count == 5
    assert report.failed_count == 0
    assert report.signal_count == 5
    assert report.effective_signal_count == 5
    assert report.failed_signal_count == 0
    assert report.release_gate_effectiveness_pct == 100
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "expand_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_pattern_to_enterprise_use_cases",
    )


def test_response_slo_drift_release_gate_effectiveness_blocks_on_drill() -> None:
    drill_report = build_drill(ai_root(), generated_at="2026-06-17")
    report = build_effectiveness_from_drill(
        replace(drill_report, drill_status="failed"),
        generated_at="2026-06-17",
    )

    assert report.monitor_status == "blocked_by_release_gate_drill"
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_effectiveness",
    )


def test_response_slo_drift_release_gate_effectiveness_detects_gap() -> None:
    drill_report = build_drill(ai_root(), generated_at="2026-06-17")
    broken_scenario = replace(
        drill_report.scenarios[0],
        observed_outcome="release_gate_gap_detected",
        passed=False,
    )
    report = build_effectiveness_from_drill(
        replace(
            drill_report,
            scenarios=(broken_scenario, *drill_report.scenarios[1:]),
            passed_count=4,
            failed_count=1,
        ),
        generated_at="2026-06-17",
    )

    assert report.monitor_status == "effectiveness_gap_detected"
    assert report.failed_signal_count == 3
    blocked = [
        signal.signal_id
        for signal in report.signals
        if not signal.effective
    ]
    assert blocked == [
        "release-gate-scenario-pass-rate-signal",
        "release-gate-blocked-scenario-clean-signal",
        "release-gate-evidence-completeness-signal",
    ]


def test_release_gate_effectiveness_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-effectiveness-v1"
    )
    assert snapshot["summary"]["monitor_status"] == "effectiveness_monitored"
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "tenant-support" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized


def test_release_gate_effectiveness_raw_id_detector_catches_ids() -> None:
    report = build_effectiveness(ai_root(), generated_at="2026-06-17")
    leaked_signal = replace(report.signals[0], observed="tenant-lms")

    assert effectiveness.count_raw_identifier_markers(report.signals) == 0
    assert (
        effectiveness.count_raw_identifier_markers(
            (leaked_signal, *report.signals[1:])
        )
        == 1
    )


def test_response_slo_drift_release_gate_effectiveness_snapshot_matches() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-effectiveness-v1.yaml"
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
