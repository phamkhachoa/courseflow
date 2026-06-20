from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alert_drill import (
    build_product_readiness_freshness_response_slo_drift_alert_drill_report,
    build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts,
    build_product_readiness_freshness_response_slo_drift_alert_drill_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alerts import (
    build_product_readiness_freshness_response_slo_drift_alert_report,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_alert_drill_replays_routed_watch_alert() -> None:
    report = build_product_readiness_freshness_response_slo_drift_alert_drill_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    scenario = report.scenarios[0]

    assert report.drill_status == "passed"
    assert report.alert_status == "alerts_configured_with_watch"
    assert report.alert_count == 1
    assert report.routed_alert_count == 1
    assert report.scenario_count == 1
    assert report.passed_count == 1
    assert report.failed_count == 0
    assert report.max_trigger_usage_pct == 87
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_alert_calibration",
    )
    assert scenario.drill_id == "prf-response-slo-drift-route-unreachable-p0-drill"
    assert scenario.alert_id == "prf-response-slo-drift-route-unreachable-p0"
    assert scenario.expected_route == "admin-ops"
    assert scenario.observed_route == "admin-ops"
    assert scenario.expected_action == "triage_product_readiness_response_slo_drift"
    assert scenario.observed_action == "triage_product_readiness_response_slo_drift"
    assert scenario.expected_alert_status == "routed"
    assert scenario.observed_alert_status == "routed"
    assert scenario.expected_alert_severity == "p1"
    assert scenario.observed_alert_severity == "p1"
    assert scenario.trigger_metric == "recover"
    assert scenario.trigger_usage_pct == 87
    assert scenario.threshold_pct == 80
    assert scenario.passed is True
    assert scenario.validation_errors == ()


def test_response_slo_drift_alert_drill_blocks_when_alerts_block() -> None:
    alerts = build_product_readiness_freshness_response_slo_drift_alert_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts(
        replace(alerts, alert_status="blocked_by_response_trends"),
        generated_at="2026-06-17",
    )

    assert report.drill_status == "blocked_by_alerts"
    assert report.next_actions == (
        "exercise_product_readiness_response_slo_drift_alert_drill",
    )


def test_response_slo_drift_alert_drill_fails_bad_route() -> None:
    alerts = build_product_readiness_freshness_response_slo_drift_alert_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    bad_alert = replace(alerts.alerts[0], route="support-queue")
    report = build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts(
        replace(alerts, alerts=(bad_alert,)),
        generated_at="2026-06-17",
    )

    assert report.drill_status == "failed"
    assert report.failed_count == 1
    assert report.scenarios[0].validation_errors == (
        "expected route admin-ops, observed support-queue",
    )


def test_response_slo_drift_alert_drill_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_product_readiness_freshness_response_slo_drift_alert_drill_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-alert-drill-v1"
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


def test_response_slo_drift_alert_drill_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml"
    )
    generated = build_product_readiness_freshness_response_slo_drift_alert_drill_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
