from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.product_readiness_freshness import (
    build_ai_platform_product_readiness_freshness_report,
    build_ai_platform_product_readiness_freshness_snapshot,
    load_ai_platform_product_readiness_freshness_report,
)
from courseflow_ai_platform.registry import load_yaml


def test_product_readiness_freshness_probe_confirms_runtime_route() -> None:
    report = build_ai_platform_product_readiness_freshness_report(
        Path(__file__).resolve().parents[2],
        generated_at="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["freshnessStatus"] == "current"
    assert payload["routePath"] == "/v1/model-serving/product-readiness"
    assert payload["routeRegistered"] is True
    assert payload["runtimeStatusCode"] == 200
    assert payload["runtimeReportId"] == "ai-platform-product-readiness-v1"
    assert payload["runtimeReadinessStatus"] == "stakeholder_ready_with_followups"
    assert payload["staticSnapshotStatus"] == "current"
    assert payload["staticReadinessStatus"] == "stakeholder_ready_with_followups"
    assert payload["requiredSpectrumCount"] == 8
    assert payload["coveredRequiredSpectrumCount"] == 8
    assert payload["extendedModuleCount"] == 6
    assert payload["runtimeServingMetricsConnected"] is True
    assert payload["runtimeServingRequestCount"] == 1
    assert payload["runtimeServingAuditRecordCount"] == 1
    assert payload["runtimeServingErrorCount"] == 0
    assert payload["runtimeServingAuditFailureCount"] == 0
    assert payload["failedCheckCount"] == 0
    assert {check["checkId"] for check in payload["checks"]} == {
        "required_ai_spectrum_runtime_ready",
        "runtime_route_reachable",
        "runtime_serving_metrics_live",
        "static_runtime_gate_alignment",
        "static_snapshot_current",
    }


def test_product_readiness_freshness_detects_stale_static_snapshot() -> None:
    report = build_ai_platform_product_readiness_freshness_report(
        Path(__file__).resolve().parents[2],
        generated_at="2026-06-20",
    )

    assert report.freshness_status == "static_snapshot_stale"
    assert report.static_snapshot_status == "stale"
    assert report.failed_check_count == 2


def test_product_readiness_freshness_loads_checked_in_snapshot() -> None:
    report = load_ai_platform_product_readiness_freshness_report(
        Path(__file__).resolve().parents[2]
    )

    assert report is not None
    assert report.freshness_status == "current"
    assert report.runtime_status_code == 200
    assert report.runtime_serving_request_count == 1
    assert report.covered_required_spectrum_count == 8
    assert report.failed_check_count == 0


def test_product_readiness_freshness_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "product"
        / "reports"
        / "ai-platform-product-readiness-freshness-v1.yaml"
    )
    generated = build_ai_platform_product_readiness_freshness_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
