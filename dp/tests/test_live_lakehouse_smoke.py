from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pyarrow.parquet as pq

from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"
INGESTED_AT = "2026-01-15T09:15:05Z"
BUILT_AT = "2026-01-15T09:15:10Z"
EVALUATION_TIME = "2026-01-15T09:15:15Z"


def test_live_lakehouse_smoke_writes_parquet_and_queries_with_duckdb(tmp_path: Path) -> None:
    result = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="live-lakehouse-smoke-test",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        schema_id="registry:finance.benefit_settled.v1:1",
        snapshot_id="finance-benefit-live-lakehouse-test",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    commits = {commit["data_product"]: commit for commit in report["table_commits"]}

    assert report == result.report
    assert report["artifact_type"] == "live_lakehouse_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_parquet_duckdb_sql"
    assert "iceberg_catalog_commit" in report["runtime_scope"]["not_covered"]
    assert report["summary"]["table_count"] == 3
    assert report["summary"]["parquet_commit_passed_count"] == 3
    assert report["summary"]["query_engine"] == "duckdb"
    assert report["query_probe"]["query_name"] == "finance_reconciliation_by_status_parquet"
    assert report["query_probe"]["result_row_count"] >= 1

    gold = commits["gold.finance_benefit_reconciliation"]
    assert Path(gold["parquet_path"]).is_file()
    assert Path(gold["commit_path"]).is_file()
    table = pq.read_table(gold["parquet_path"])
    assert table.num_rows == gold["row_count"] == 4
    assert "reconciliation_status" in table.schema.names


def test_live_lakehouse_smoke_cli(tmp_path: Path) -> None:
    output = tmp_path / "smoke" / "live-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "live-lakehouse-smoke",
            "--root",
            str(ROOT),
            "--output-dir",
            str(tmp_path / "run"),
            "--output",
            str(output),
            "--release-id",
            "cli-live-lakehouse-smoke",
            "--generated-at",
            GENERATED_AT,
            "--ingested-at",
            INGESTED_AT,
            "--built-at",
            BUILT_AT,
            "--evaluation-time",
            EVALUATION_TIME,
            "--schema-id",
            "registry:finance.benefit_settled.v1:1",
            "--snapshot-id",
            "finance-benefit-cli-live-lakehouse",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    cli_output = json.loads(completed.stdout)
    report = json.loads(output.read_text(encoding="utf-8"))

    assert cli_output["passed"] is True
    assert cli_output["runtime_mode"] == "local_parquet_duckdb_sql"
    assert cli_output["query_engine"] == "duckdb"
    assert report["passed"] is True
