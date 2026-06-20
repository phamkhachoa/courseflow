from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_metrics import (
    build_product_readiness_freshness_response_metrics_report,
)
from courseflow_ai_platform.product_readiness_freshness_response_trends import (
    build_product_readiness_freshness_response_trend_report,
    build_product_readiness_freshness_response_trend_report_from_metrics,
    build_product_readiness_freshness_response_trend_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_product_readiness_freshness_response_trends_are_ready_with_watch() -> None:
    report = build_product_readiness_freshness_response_trend_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    route = {
        trend.scenario_id: trend for trend in report.scenario_trends
    }["route-unreachable-p0"]

    assert report.trend_status == "trend_ready_with_watch"
    assert report.metrics_status == "slo_met"
    assert report.ingest_status == "live_ingest_connected"
    assert report.owner_count == 1
    assert report.scenario_class_count == 5
    assert report.live_observation_count == 5
    assert report.breach_count == 0
    assert report.watch_count == 1
    assert report.p0_count == 1
    assert report.p1_count == 4
    assert report.max_recover_slo_usage_pct == 87
    assert report.max_close_slo_usage_pct == 78
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "configure_product_readiness_response_slo_drift_alerts",
    )
    assert report.owner_trends[0].owner_role == "Admin/Ops"
    assert report.owner_trends[0].trend_status == "watch"
    assert report.owner_trends[0].watch_count == 1
    assert route.trend_status == "watch"
    assert route.recover_slo_usage_pct == 87
    assert route.close_slo_usage_pct == 78
    assert route.watch_reasons == (
        "acknowledge_slo_usage_watch",
        "contain_slo_usage_watch",
        "recover_slo_usage_watch",
    )


def test_product_readiness_freshness_response_trends_block_without_live_ingest() -> None:
    metrics = build_product_readiness_freshness_response_metrics_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_product_readiness_freshness_response_trend_report_from_metrics(
        replace(metrics, ingest_status="synthetic_baseline"),
        generated_at="2026-06-17",
    )

    assert report.trend_status == "blocked_by_live_ingest"
    assert report.next_actions == (
        "trend_product_readiness_freshness_response_slo_by_owner",
    )


def test_product_readiness_freshness_response_trends_block_on_slo_breach() -> None:
    metrics = build_product_readiness_freshness_response_metrics_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_product_readiness_freshness_response_trend_report_from_metrics(
        replace(metrics, response_metrics_status="slo_breached", breach_count=1),
        generated_at="2026-06-17",
    )

    assert report.trend_status == "blocked_by_response_slo"
    assert report.next_actions == (
        "trend_product_readiness_freshness_response_slo_by_owner",
    )


def test_product_readiness_freshness_response_trends_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_product_readiness_freshness_response_trend_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == "product-readiness-freshness-response-trends-v1"
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "tenant-support" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized


def test_product_readiness_freshness_response_trends_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-trends-v1.yaml"
    )
    generated = build_product_readiness_freshness_response_trend_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
