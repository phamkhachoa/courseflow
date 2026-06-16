from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.observability import (
    build_observability_snapshot,
    validate_observability_snapshot,
    write_observability_artifacts,
)
from enterprise_df.orchestration import run_use_case


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
FINANCE_INGESTED_AT = "2026-01-15T09:15:05Z"
FINANCE_BUILT_AT = "2026-01-15T09:15:10Z"
FINANCE_EVALUATION_TIME = "2026-01-15T09:15:15Z"


def test_observability_export_writes_metrics_and_summary_without_high_cardinality_labels(tmp_path: Path) -> None:
    run = run_finance_use_case(tmp_path / "run")
    metrics_path = tmp_path / "observability" / "enterprise-df.prom"
    summary_path = tmp_path / "observability" / "summary.json"

    result = write_observability_artifacts(
        run.catalog_bundle_path,
        metrics_output_path=metrics_path,
        summary_output_path=summary_path,
        release_evidence_paths=[run.evidence_path],
        environment="local",
        generated_at="2026-01-15T09:15:20Z",
    )
    metrics = metrics_path.read_text(encoding="utf-8")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert result["metrics_count"] > 0
    assert "enterprise_df_release_gate_status" in metrics
    assert 'gate_id="P0-FRESHNESS"' in metrics
    assert "enterprise_df_data_product_freshness_seconds" in metrics
    assert "enterprise_df_ingestion_lag_seconds" in metrics
    assert "enterprise_df_cost_attribution_rows_total" in metrics
    assert "cost_usd" not in metrics
    assert "local-finance-observability-test" not in metrics
    assert "finance-pipeline-snapshot" not in metrics
    assert "sha256:" not in metrics
    assert "manifest_path" not in metrics
    assert "tenant-acme" not in metrics
    assert "1234567890abcdef1234567890abcdef" not in metrics

    assert summary["artifact_type"] == "enterprise_df_observability_snapshot.v1"
    assert summary["environment"] == "local"
    assert summary["release_evidence"][0]["release_id"] == "local-finance-observability-test"
    assert summary["release_evidence"][0]["evidence_hash"].startswith("sha256:")
    assert summary["high_cardinality_omitted_from_metric_labels"]
    assert summary["cost_attribution"][0]["row_count"] >= 4


def test_observability_export_emits_failed_gate_zero(tmp_path: Path) -> None:
    run = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path / "stale",
        use_case_id="finance-benefit-reconciliation",
        release_id="local-finance-observability-stale-test",
        environment="local",
        ingested_at=FINANCE_INGESTED_AT,
        built_at=FINANCE_BUILT_AT,
        evaluation_time="2026-01-15T14:00:00Z",
    )
    snapshot = build_observability_snapshot(
        json.loads(run.catalog_bundle_path.read_text(encoding="utf-8")),
        release_evidences=[run.evidence],
        environment="local",
        generated_at="2026-01-15T14:00:05Z",
    )
    gate_metrics = [
        metric for metric in snapshot["metrics"]
        if metric["name"] == "enterprise_df_release_gate_status"
        and metric["labels"].get("gate_id") == "P0-FRESHNESS"
    ]

    assert run.evidence["release_passed"] is False
    assert gate_metrics
    assert gate_metrics[0]["value"] == 0


def test_observability_cli_export(tmp_path: Path) -> None:
    run = run_finance_use_case(tmp_path / "run")
    metrics_path = tmp_path / "cli" / "metrics.prom"
    summary_path = tmp_path / "cli" / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "observability-export",
            "--catalog",
            str(run.catalog_bundle_path),
            "--release-evidence",
            str(run.evidence_path),
            "--output-metrics",
            str(metrics_path),
            "--output-summary",
            str(summary_path),
            "--environment",
            "local",
            "--generated-at",
            "2026-01-15T09:15:20Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["metrics_count"] > 0
    assert output["metrics_output"] == str(metrics_path)
    assert output["summary_output"] == str(summary_path)
    assert metrics_path.is_file()
    assert summary_path.is_file()


def test_observability_validation_rejects_high_cardinality_metric_labels() -> None:
    result = validate_observability_snapshot(
        {
            "artifact_type": "enterprise_df_observability_snapshot.v1",
            "metrics": [
                {
                    "name": "enterprise_df_bad_metric",
                    "value": 1,
                    "labels": {
                        "environment": "local",
                        "release_id": "release-123",
                    },
                    "help": "Bad metric.",
                    "type": "gauge",
                }
            ],
        }
    )

    assert any("high-cardinality" in error for error in result.errors)


def run_finance_use_case(output_dir: Path):
    return run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        output_dir,
        use_case_id="finance-benefit-reconciliation",
        release_id="local-finance-observability-test",
        environment="local",
        ingested_at=FINANCE_INGESTED_AT,
        built_at=FINANCE_BUILT_AT,
        evaluation_time=FINANCE_EVALUATION_TIME,
        snapshot_id="finance-pipeline-snapshot",
    )
