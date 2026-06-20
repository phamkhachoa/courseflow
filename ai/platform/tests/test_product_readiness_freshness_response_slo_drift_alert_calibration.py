from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_alert_calibration as cal,
)
from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alert_drill import (
    build_product_readiness_freshness_response_slo_drift_alert_drill_report,
)
from courseflow_ai_platform.registry import load_yaml

build_calibration_from_drill = (
    cal.build_product_readiness_freshness_response_slo_drift_alert_calibration_report_from_drill
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_alert_calibration_monitors_watch_alert_margin() -> None:
    report = cal.build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    item = report.items[0]

    assert report.calibration_status == "calibrated_with_watch"
    assert report.drill_status == "passed"
    assert report.alert_count == 1
    assert report.routed_alert_count == 1
    assert report.scenario_count == 1
    assert report.calibrated_count == 1
    assert report.failed_count == 0
    assert report.noisy_alert_count == 0
    assert report.under_threshold_count == 0
    assert report.escalation_required_count == 0
    assert report.max_margin_pct == 7
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "codify_product_readiness_response_slo_drift_alert_suppression_policy",
    )
    assert item.calibration_id == (
        "prf-response-slo-drift-route-unreachable-p0-calibration"
    )
    assert item.alert_id == "prf-response-slo-drift-route-unreachable-p0"
    assert item.trigger_metric == "recover"
    assert item.trigger_usage_pct == 87
    assert item.threshold_pct == 80
    assert item.margin_pct == 7
    assert item.calibration_status == "calibrated_watch"
    assert item.noise_status == "quiet"
    assert item.escalation_status == "watch_only"
    assert item.passed is True
    assert item.validation_errors == ()


def test_response_slo_drift_alert_calibration_blocks_when_drill_blocks() -> None:
    drill = build_product_readiness_freshness_response_slo_drift_alert_drill_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_calibration_from_drill(
        replace(drill, drill_status="blocked_by_alerts"),
        generated_at="2026-06-17",
    )

    assert report.calibration_status == "blocked_by_alert_drill"
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_alert_calibration",
    )


def test_response_slo_drift_alert_calibration_fails_under_threshold_alert() -> None:
    drill = build_product_readiness_freshness_response_slo_drift_alert_drill_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    under_threshold = replace(drill.scenarios[0], trigger_usage_pct=79)
    report = build_calibration_from_drill(
        replace(drill, scenarios=(under_threshold,)),
        generated_at="2026-06-17",
    )

    assert report.calibration_status == "calibration_failed"
    assert report.under_threshold_count == 1
    assert report.items[0].margin_pct == -1
    assert report.items[0].noise_status == "missed"
    assert report.items[0].validation_errors == (
        "expected calibrated_watch, observed under_threshold",
        "expected quiet noise status, observed missed",
    )


def test_response_slo_drift_alert_calibration_snapshot_suppresses_raw_ids() -> None:
    snapshot = cal.build_product_readiness_freshness_response_slo_drift_alert_calibration_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-alert-calibration-v1"
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


def test_response_slo_drift_alert_calibration_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml"
    )
    generated = cal.build_product_readiness_freshness_response_slo_drift_alert_calibration_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
