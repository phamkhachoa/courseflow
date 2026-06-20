from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import build_catalog_bundle, canonical_json
from enterprise_dp.live_quality_slo_smoke import write_live_quality_slo_smoke_report
from enterprise_dp.trino_sql_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"


def test_live_quality_slo_smoke_writes_runtime_quality_and_ops_evidence(tmp_path: Path) -> None:
    publication_report = write_publication_inputs(tmp_path)

    result = write_live_quality_slo_smoke_report(
        ROOT,
        tmp_path / "live-quality-slo-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="live-quality-slo-test",
        generated_at=GENERATED_AT,
        trino_executor_override=FakeTrinoQualityExecutor(),
        orchestrated_publication_report_override=publication_report,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report == result.report
    assert report["artifact_type"] == "live_quality_slo_smoke_report.v1"
    assert report["passed"] is True
    assert report["capability_ids"] == ["quality-slo-release-gates"]
    assert summary["target_data_product"] == "gold.finance_benefit_reconciliation"
    assert summary["gold_row_count"] == 4
    assert summary["quality_runtime_passed"] is True
    assert summary["slo_alert_passed"] is True
    assert summary["quality_slo_ops_passed"] is True
    assert summary["corrupt_gold_null_negative_test_passed"] is True
    assert summary["stale_freshness_negative_test_passed"] is True
    assert summary["red_alert_negative_test_passed"] is True
    assert summary["environment_mismatch_negative_test_passed"] is True
    assert summary["missing_alert_production_like_negative_test_passed"] is True
    assert summary["failed_check_count"] == 0
    assert report["artifacts"]["quality_runtime_evidence"]["artifact_type"] == "quality_runtime_evidence.v1"
    assert report["artifacts"]["slo_alert_evidence"]["artifact_type"] == "slo_alert_evidence.v1"
    assert report["artifacts"]["quality_slo_ops"]["artifact_type"] == "quality_slo_release_gates_ops_report.v1"


def test_live_quality_slo_smoke_fails_when_gold_has_required_nulls(tmp_path: Path) -> None:
    publication_report = write_publication_inputs(tmp_path)

    result = write_live_quality_slo_smoke_report(
        ROOT,
        tmp_path / "live-quality-slo-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="live-quality-slo-corrupt-test",
        generated_at=GENERATED_AT,
        trino_executor_override=FakeTrinoQualityExecutor(required_null_count=1),
        orchestrated_publication_report_override=publication_report,
    )

    assert result.report["passed"] is False
    assert any(item["check"] == "live_gold_quality_checks_passed" for item in result.report["summary"]["failed_checks"])
    assert result.report["summary"]["quality_runtime_passed"] is False
    assert result.report["summary"]["slo_alert_passed"] is False


def write_publication_inputs(tmp_path: Path) -> dict[str, Any]:
    release_path = tmp_path / "publication" / "release-evidence.json"
    catalog_path = tmp_path / "publication" / "catalog-bundle.json"
    catalog = build_catalog_bundle(ROOT, generated_at=GENERATED_AT)
    release = {
        "release_id": "orchestrated-publication-test",
        "environment": "local",
        "generated_at": GENERATED_AT,
        "use_case_id": "finance-benefit-reconciliation",
        "runner_id": "finance.benefit_reconciliation.from_approved_bronze.v1",
        "primary_output": "gold.finance_benefit_reconciliation",
        "output_data_products": ["silver.finance_benefit_transactions", "gold.finance_benefit_reconciliation"],
        "gates": [
            {"gate_id": "P0-INGESTION-LAG", "passed": True, "details": {"max_lag_seconds": 60}},
            {"gate_id": "P0-FRESHNESS", "passed": True, "details": {"age_seconds": 0, "slo_seconds": 900}},
            {"gate_id": "P0-PIPELINE-QUALITY", "passed": True, "details": {"pipeline_quality_passed": True}},
            {"gate_id": "P0-QUALITY-PROFILE", "passed": True, "details": {"profile_id": "p0-gold-finance-reconciliation"}},
            {"gate_id": "P0-RELEASE-EVIDENCE-PROFILE", "passed": True, "details": {"profile_id": "p0-standard-gold-release"}},
            {"gate_id": "P0-OUTPUT-EVIDENCE", "passed": True, "details": {"primary_output": "gold.finance_benefit_reconciliation"}},
        ],
        "release_passed": True,
    }
    write_json(release_path, release)
    write_json(catalog_path, catalog)
    return {
        "artifact_type": "orchestrated_live_publication_report.v1",
        "generated_at": GENERATED_AT,
        "environment": "local",
        "passed": True,
        "publication": {
            "release": {"uri": release_path.as_posix()},
            "catalog_bundle": {"uri": catalog_path.as_posix()},
            "layers": {
                "gold.finance_benefit_reconciliation": {
                    "iceberg_table": "iceberg.publication_runtime_smoke.finance_benefit_reconciliation",
                    "row_count": 4,
                }
            },
        },
        "summary": {"gold_row_count": 4, "trino_gold_row_count": 4},
    }


class FakeTrinoQualityExecutor:
    def __init__(self, *, required_null_count: int = 0, max_built_at: str = GENERATED_AT) -> None:
        self.required_null_count = required_null_count
        self.max_built_at = max_built_at

    def __call__(self, sql: str, step: str) -> CommandResult:
        if step == "query_live_gold_quality_metrics":
            return CommandResult(
                ("fake",),
                0,
                f'"4","4","{self.required_null_count}","0","0","0","{self.max_built_at}"\n',
                "",
            )
        raise AssertionError(f"unexpected Trino step: {step}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")
