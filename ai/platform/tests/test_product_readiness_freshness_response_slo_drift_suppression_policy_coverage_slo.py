from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo as slo,
)
from courseflow_ai_platform.registry import load_yaml

build_slo = (
    slo.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report
)
build_slo_from_regression = (
    slo.build_suppression_policy_coverage_slo_report_from_regression
)
build_snapshot = (
    slo.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_snapshot
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_suppression_policy_coverage_slo_is_published() -> None:
    report = build_slo(ai_root(), generated_at="2026-06-17")

    assert report.slo_status == "coverage_slo_published"
    assert report.regression_status == "regression_monitored"
    assert report.coverage_status == "coverage_expanded"
    assert report.scenario_class_count == 5
    assert report.covered_scenario_count == 5
    assert report.failed_coverage_count == 0
    assert report.coverage_pct == 100
    assert report.regression_check_count == 7
    assert report.passed_regression_check_count == 7
    assert report.failed_regression_check_count == 0
    assert report.objective_count == 4
    assert report.met_objective_count == 4
    assert report.failed_objective_count == 0
    assert report.target_coverage_pct == 100
    assert report.target_regression_pass_pct == 100
    assert report.review_cadence_days == 30
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "attach_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_slo_to_release_governance",
    )


def test_response_slo_drift_suppression_policy_coverage_slo_blocks_on_regression() -> None:
    regression = (
        slo.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_slo_from_regression(
        replace(regression, regression_status="coverage_regression_detected"),
        generated_at="2026-06-17",
    )

    assert report.slo_status == "blocked_by_regression"
    assert report.next_actions == (
        "publish_product_readiness_response_slo_drift_suppression_policy_coverage_slo",
    )


def test_response_slo_drift_suppression_policy_coverage_slo_detects_at_risk() -> None:
    regression = (
        slo.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_slo_from_regression(
        replace(
            regression,
            coverage_pct=80,
            covered_scenario_count=4,
            failed_coverage_count=1,
        ),
        generated_at="2026-06-17",
    )

    assert report.slo_status == "coverage_slo_at_risk"
    assert report.failed_objective_count == 1
    assert report.objectives[0].objective_id == "scenario-coverage-slo"
    assert report.objectives[0].met is False


def test_response_slo_drift_suppression_policy_coverage_slo_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1"
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


def test_suppression_policy_coverage_slo_raw_id_detector_ignores_control_labels() -> None:
    report = build_slo(ai_root(), generated_at="2026-06-17")
    leaked_objective = replace(report.objectives[0], observed="tenant-lms")

    assert slo.count_raw_identifier_markers(report.objectives) == 0
    assert (
        slo.count_raw_identifier_markers(
            (leaked_objective, *report.objectives[1:])
        )
        == 1
    )


def test_response_slo_drift_suppression_policy_coverage_slo_snapshot_matches() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-"
        "suppression-policy-coverage-slo-v1.yaml"
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
