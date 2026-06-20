from __future__ import annotations

from pathlib import Path

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_drill import (
    build_product_readiness_freshness_incident_response_drill_report,
)
from courseflow_ai_platform.product_readiness_freshness_response_metrics import (
    build_product_readiness_freshness_response_metrics_report,
    build_product_readiness_freshness_response_metrics_report_from_drill,
    build_product_readiness_freshness_response_metrics_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_product_readiness_freshness_response_metrics_meet_slos() -> None:
    report = build_product_readiness_freshness_response_metrics_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    route = {
        item.scenario_id: item for item in report.items
    }["route-unreachable-p0"]

    assert report.response_metrics_status == "slo_met"
    assert report.ingest_status == "live_ingest_connected"
    assert report.drill_status == "passed"
    assert report.scenario_count == 5
    assert report.measured_count == 5
    assert report.live_observation_count == 5
    assert report.synthetic_observation_count == 0
    assert report.missing_live_observation_count == 0
    assert report.breach_count == 0
    assert report.p0_count == 1
    assert report.p1_count == 4
    assert report.max_acknowledge_minutes == 11
    assert report.max_recover_minutes == 170
    assert report.max_close_minutes == 210
    assert report.average_recover_minutes == 116
    assert report.tenant_safe is True
    assert report.next_actions == (
        "exercise_product_readiness_response_slo_drift_alert_drill",
    )
    assert report.live_source_path == (
        "platform/operations/metrics/"
        "product-readiness-freshness-live-response-metrics-v1.yaml"
    )
    assert route.severity == "p0"
    assert route.measurement_source == "live_ingest"
    assert route.observation_id == "prf-live-route-unreachable-20260617"
    assert route.recover_minutes == 52
    assert route.recover_slo_minutes == 60
    assert route.metric_status == "slo_met"
    assert route.breach_reasons == ()


def test_product_readiness_freshness_response_metrics_detect_slo_breach() -> None:
    root = ai_root()
    drill = build_product_readiness_freshness_incident_response_drill_report(
        root,
        generated_at="2026-06-17",
    )
    runbook = load_yaml(
        root
        / "platform"
        / "operations"
        / "runbooks"
        / "product-readiness-freshness-incident-response-v1.yaml"
    )
    runbook["response_metrics"]["synthetic_observations"][
        "product_readiness_runtime_route_unreachable"
    ]["verify_minutes"] = 75

    report = build_product_readiness_freshness_response_metrics_report_from_drill(
        drill,
        runbook=runbook,
        generated_at="2026-06-17",
    )
    route = {
        item.scenario_id: item for item in report.items
    }["route-unreachable-p0"]

    assert report.response_metrics_status == "slo_breached"
    assert report.breach_count == 1
    assert route.metric_status == "slo_breached"
    assert route.breach_reasons == ("recover_slo_breached",)


def test_product_readiness_freshness_response_metrics_fall_back_to_synthetic_baseline() -> None:
    root = ai_root()
    drill = build_product_readiness_freshness_incident_response_drill_report(
        root,
        generated_at="2026-06-17",
    )
    runbook = load_yaml(
        root
        / "platform"
        / "operations"
        / "runbooks"
        / "product-readiness-freshness-incident-response-v1.yaml"
    )

    report = build_product_readiness_freshness_response_metrics_report_from_drill(
        drill,
        runbook=runbook,
        generated_at="2026-06-17",
    )

    assert report.response_metrics_status == "slo_met"
    assert report.ingest_status == "synthetic_baseline"
    assert report.live_observation_count == 0
    assert report.synthetic_observation_count == 5
    assert report.missing_live_observation_count == 5
    assert report.next_actions == (
        "connect_product_readiness_freshness_live_response_metrics_ingest",
    )


def test_product_readiness_freshness_response_metrics_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_product_readiness_freshness_response_metrics_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == "product-readiness-freshness-response-metrics-v1"
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "tenant-support" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized


def test_product_readiness_freshness_response_metrics_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-metrics-v1.yaml"
    )
    generated = build_product_readiness_freshness_response_metrics_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
