from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression as reg,
)
from courseflow_ai_platform.registry import load_yaml

build_regression = (
    reg.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report
)
build_regression_from_coverage = (
    reg.build_suppression_policy_coverage_regression_report_from_coverage
)
build_snapshot = (
    reg.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_snapshot
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_suppression_policy_coverage_regression_is_monitored() -> None:
    report = build_regression(ai_root(), generated_at="2026-06-17")

    assert report.regression_status == "regression_monitored"
    assert report.coverage_status == "coverage_expanded"
    assert report.scenario_class_count == 5
    assert report.covered_scenario_count == 5
    assert report.failed_coverage_count == 0
    assert report.active_policy_scenario_count == 1
    assert report.explicit_non_watch_scenario_count == 4
    assert report.effective_signal_count == 4
    assert report.coverage_pct == 100
    assert report.regression_check_count == 7
    assert report.passed_regression_check_count == 7
    assert report.failed_regression_check_count == 0
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "publish_product_readiness_response_slo_drift_suppression_policy_coverage_slo",
    )


def test_response_slo_drift_suppression_policy_regression_blocks_on_coverage() -> None:
    coverage = (
        reg.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_regression_from_coverage(
        replace(coverage, coverage_status="coverage_incomplete"),
        generated_at="2026-06-17",
    )

    assert report.regression_status == "blocked_by_coverage"
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_suppression_policy_coverage_regression",
    )


def test_response_slo_drift_suppression_policy_regression_detects_drop() -> None:
    coverage = (
        reg.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_regression_from_coverage(
        replace(
            coverage,
            covered_scenario_count=4,
            failed_coverage_count=1,
            coverage_pct=80,
        ),
        generated_at="2026-06-17",
    )

    assert report.regression_status == "coverage_regression_detected"
    assert report.failed_regression_check_count == 2


def test_response_slo_drift_suppression_policy_regression_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1"
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


def test_suppression_policy_regression_raw_id_detector_ignores_control_labels() -> None:
    report = build_regression(ai_root(), generated_at="2026-06-17")
    leaked_check = replace(report.checks[0], observed="tenant-lms")

    assert reg.count_raw_identifier_markers(report.checks) == 0
    assert (
        reg.count_raw_identifier_markers((leaked_check, *report.checks[1:]))
        == 1
    )


def test_response_slo_drift_suppression_policy_regression_snapshot_matches() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-"
        "suppression-policy-coverage-regression-v1.yaml"
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
