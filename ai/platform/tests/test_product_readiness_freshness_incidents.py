from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from courseflow_ai_platform.product_readiness_freshness import (
    build_ai_platform_product_readiness_freshness_report,
    load_ai_platform_product_readiness_freshness_report,
)
from courseflow_ai_platform.product_readiness_freshness_incidents import (
    build_product_readiness_freshness_incident_export,
    build_product_readiness_freshness_incident_export_from_report,
    build_product_readiness_freshness_incident_export_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def test_product_readiness_freshness_incident_export_has_no_baseline_incidents() -> None:
    report = build_product_readiness_freshness_incident_export(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )

    assert report.incident_count == 0
    assert report.open_count == 0
    assert report.watch_count == 0
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0


def test_product_readiness_freshness_incident_export_escalates_stale_snapshot() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    freshness_report = build_ai_platform_product_readiness_freshness_report(
        ai_root,
        generated_at="2026-06-20",
    )

    report = build_product_readiness_freshness_incident_export_from_report(
        freshness_report,
        as_of="2026-06-20",
    )
    incident = report.incidents[0]

    assert report.incident_count == 1
    assert report.open_count == 1
    assert report.p1_count == 1
    assert incident.condition == "product_readiness_static_snapshot_stale"
    assert incident.action == "refresh_product_readiness_snapshots"
    assert incident.age_days == 3
    assert incident.application_ref.startswith("product-readiness:")
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0


def test_product_readiness_freshness_incident_export_escalates_route_failure() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    freshness_report = load_ai_platform_product_readiness_freshness_report(ai_root)
    assert freshness_report is not None

    route_failure = replace(
        freshness_report,
        freshness_status="route_unreachable",
        route_registered=False,
        runtime_status_code=503,
        failed_check_count=1,
    )
    report = build_product_readiness_freshness_incident_export_from_report(
        route_failure,
        as_of="2026-06-17",
    )
    incident = report.incidents[0]

    assert report.incident_count == 1
    assert report.open_count == 1
    assert report.p0_count == 1
    assert incident.condition == "product_readiness_runtime_route_unreachable"
    assert incident.action == "triage_product_readiness_runtime_route"


def test_product_readiness_freshness_incident_export_escalates_report_staleness() -> None:
    report = build_product_readiness_freshness_incident_export(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-20",
    )
    incident = report.incidents[0]

    assert report.incident_count == 1
    assert report.open_count == 1
    assert report.p1_count == 1
    assert incident.condition == "product_readiness_freshness_report_stale"
    assert incident.action == "refresh_product_readiness_freshness_report"
    assert incident.age_days == 3


def test_product_readiness_freshness_incident_export_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "governance"
        / "reports"
        / "product-readiness-freshness-incident-export-v1.yaml"
    )
    generated = build_product_readiness_freshness_incident_export_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
