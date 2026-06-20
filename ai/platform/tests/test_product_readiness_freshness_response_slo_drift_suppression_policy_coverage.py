from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_suppression_policy_coverage as cov,
)
from courseflow_ai_platform.registry import load_yaml

build_coverage = (
    cov.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report
)
build_coverage_from_reports = cov.build_suppression_policy_coverage_report_from_reports
build_snapshot = (
    cov.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_snapshot
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_suppression_policy_coverage_is_expanded() -> None:
    report = build_coverage(ai_root(), generated_at="2026-06-17")

    assert report.coverage_status == "coverage_expanded"
    assert report.effectiveness_status == "effectiveness_monitored"
    assert report.trend_status == "trend_ready_with_watch"
    assert report.scenario_class_count == 5
    assert report.covered_scenario_count == 5
    assert report.failed_coverage_count == 0
    assert report.active_policy_scenario_count == 1
    assert report.explicit_non_watch_scenario_count == 4
    assert report.policy_rule_count == 1
    assert report.effective_signal_count == 4
    assert report.coverage_pct == 100
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_suppression_policy_coverage_regression",
    )
    assert {item.coverage_mode for item in report.items} == {
        "active_suppression_policy",
        "explicit_non_watch_exclusion",
    }


def test_response_slo_drift_suppression_policy_coverage_blocks_on_effectiveness() -> None:
    effectiveness = replace(
        cov.build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report(
            ai_root(),
            generated_at="2026-06-17",
        ),
        monitor_status="blocked_by_drill",
    )
    response_trends = cov.build_product_readiness_freshness_response_trend_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_coverage_from_reports(
        effectiveness,
        response_trends=response_trends,
        generated_at="2026-06-17",
    )

    assert report.coverage_status == "blocked_by_effectiveness"
    assert report.next_actions == (
        "expand_product_readiness_response_slo_drift_suppression_policy_coverage",
    )


def test_response_slo_drift_suppression_policy_coverage_fails_missing_watch_signal() -> None:
    effectiveness = (
        cov.build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    response_trends = cov.build_product_readiness_freshness_response_trend_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_coverage_from_reports(
        replace(
            effectiveness,
            signals=tuple(
                signal
                for signal in effectiveness.signals
                if signal.scenario_id != "route-unreachable-p0"
            ),
        ),
        response_trends=response_trends,
        generated_at="2026-06-17",
    )

    assert report.coverage_status == "coverage_incomplete"
    assert report.failed_coverage_count == 1
    assert report.covered_scenario_count == 4


def test_response_slo_drift_suppression_policy_coverage_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1"
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


def test_response_slo_drift_suppression_policy_coverage_snapshot_matches() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml"
    )
    generated = build_snapshot(root, generated_at="2026-06-17")

    assert checked_in == generated
