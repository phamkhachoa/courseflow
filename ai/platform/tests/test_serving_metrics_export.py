from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.model_serving import ModelServingMetricsSnapshot
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml
from courseflow_ai_platform.serving_metrics_export import (
    build_model_serving_metrics_export_snapshot,
    derive_export_status,
    load_model_serving_metrics_export,
    model_serving_metrics_export_from_snapshot,
)


def test_serving_metrics_export_loads_checked_in_snapshot() -> None:
    report = load_model_serving_metrics_export(Path(__file__).resolve().parents[2])

    assert report is not None
    assert report.export_status == "connected"
    assert report.source_adapter == "hosted-model-serving-adapter"
    assert report.metrics.request_count == 3
    assert report.metrics.success_count == 3
    assert report.metrics.audit_record_count == 3
    assert report.metrics.error_count == 0
    assert sorted(report.metrics.by_model) == [
        "operations-demand-forecast-baseline-v1",
        "sequence-risk-baseline-v1",
        "support-agent-assist-baseline-v1",
    ]


def test_serving_metrics_export_derives_status_from_metrics() -> None:
    assert derive_export_status(
        ModelServingMetricsSnapshot(
            request_count=0,
            success_count=0,
            fallback_count=0,
            error_count=0,
            human_review_count=0,
            audit_record_count=0,
            audit_failure_count=0,
            by_model={},
        )
    ) == "connected_no_traffic"


def test_serving_metrics_export_rejects_mismatched_totals(tmp_path: Path) -> None:
    path = tmp_path / "metrics.yaml"
    payload = {
        "generated_at": "2026-06-17",
        "source_adapter": "hosted-model-serving-adapter",
        "summary": {
            "audit_failure_count": 0,
            "audit_record_count": 0,
            "error_count": 0,
            "export_status": "connected",
            "fallback_count": 0,
            "human_review_count": 0,
            "model_count": 1,
            "request_count": 2,
            "success_count": 1,
        },
        "by_model": {
            "sequence-risk-baseline-v1": {
                "auditFailure": 0,
                "auditRecord": 0,
                "error": 0,
                "fallback": 0,
                "humanReview": 0,
                "ok": 1,
                "request": 1,
            }
        },
    }

    with pytest.raises(RegistryValidationError, match="request_count"):
        model_serving_metrics_export_from_snapshot(payload, path)


def test_serving_metrics_export_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / "model-serving-metrics-export-v1.yaml"
    )
    generated = build_model_serving_metrics_export_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
