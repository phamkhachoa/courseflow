from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.iceberg_catalog_smoke import write_iceberg_catalog_smoke_report
from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"


def test_iceberg_catalog_smoke_commits_finance_tables_and_snapshots(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="iceberg-smoke-test",
        generated_at=GENERATED_AT,
    )

    result = write_iceberg_catalog_smoke_report(
        ROOT,
        tmp_path / "iceberg" / "iceberg-catalog-smoke-report.json",
        output_dir=tmp_path / "iceberg" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="iceberg-smoke-test",
        generated_at=GENERATED_AT,
    )
    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "iceberg_catalog_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_pyiceberg_sql_catalog_file_warehouse"
    assert "trino_iceberg_connector" in report["runtime_scope"]["not_covered"]
    assert report["iceberg"]["catalog_type"] == "sql"
    assert report["summary"]["table_count"] == 3
    assert report["summary"]["iceberg_table_passed_count"] == 3
    assert report["summary"]["snapshot_commit_count"] == 3
    assert report["summary"]["metadata_file_count"] == 3
    assert report["summary"]["readback_passed_count"] == 3
    assert {item["data_product"] for item in report["table_commits"]} == {
        "bronze.events_benefit_settled",
        "silver.finance_benefit_transactions",
        "gold.finance_benefit_reconciliation",
    }
    assert all(item["snapshot_id"] for item in report["table_commits"])
    assert all(item["metadata_hash"] for item in report["table_commits"])
    assert any(
        "course_id" in item["null_type_columns_normalized"]
        for item in report["table_commits"]
        if item["data_product"] == "bronze.events_benefit_settled"
    )


def test_iceberg_catalog_smoke_generates_live_lakehouse_when_input_is_omitted(tmp_path: Path) -> None:
    result = write_iceberg_catalog_smoke_report(
        ROOT,
        tmp_path / "iceberg" / "iceberg-catalog-smoke-report.json",
        output_dir=tmp_path / "iceberg" / "run",
        release_id="iceberg-smoke-self-contained",
        generated_at=GENERATED_AT,
    )

    assert result.report["passed"] is True
    assert result.report["live_lakehouse_smoke"]["passed"] is True
    assert result.report["summary"]["table_count"] == 3
