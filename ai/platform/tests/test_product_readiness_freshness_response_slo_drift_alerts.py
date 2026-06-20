from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alerts import (
    build_product_readiness_freshness_response_slo_drift_alert_report,
    build_product_readiness_freshness_response_slo_drift_alert_report_from_trends,
    build_product_readiness_freshness_response_slo_drift_alert_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_response_trends import (
    build_product_readiness_freshness_response_trend_report,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_product_readiness_freshness_response_slo_drift_alerts_route_watch_scenarios() -> None:
    report = build_product_readiness_freshness_response_slo_drift_alert_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    alert = report.alerts[0]

    assert report.alert_status == "alerts_configured_with_watch"
    assert report.trend_status == "trend_ready_with_watch"
    assert report.watch_count == 1
    assert report.alert_count == 1
    assert report.routed_alert_count == 1
    assert report.p0_alert_count == 0
    assert report.p1_alert_count == 1
    assert report.max_trigger_usage_pct == 87
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "exercise_product_readiness_response_slo_drift_alert_drill",
    )
    assert alert.alert_id == "prf-response-slo-drift-route-unreachable-p0"
    assert alert.scenario_id == "route-unreachable-p0"
    assert alert.route == "admin-ops"
    assert alert.action == "triage_product_readiness_response_slo_drift"
    assert alert.alert_status == "routed"
    assert alert.scenario_severity == "p0"
    assert alert.alert_severity == "p1"
    assert alert.trigger_metric == "recover"
    assert alert.trigger_usage_pct == 87


def test_product_readiness_freshness_response_slo_drift_alerts_block_when_trends_block() -> None:
    trends = build_product_readiness_freshness_response_trend_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_product_readiness_freshness_response_slo_drift_alert_report_from_trends(
        replace(trends, trend_status="blocked_by_live_ingest"),
        generated_at="2026-06-17",
    )

    assert report.alert_status == "blocked_by_response_trends"
    assert report.next_actions == (
        "configure_product_readiness_response_slo_drift_alerts",
    )


def test_response_slo_drift_alerts_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_product_readiness_freshness_response_slo_drift_alert_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-alerts-v1"
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


def test_response_slo_drift_alerts_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-slo-drift-alerts-v1.yaml"
    )
    generated = build_product_readiness_freshness_response_slo_drift_alert_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
