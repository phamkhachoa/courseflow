from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.data_plane_smoke import (
    DEFAULT_RELEASE_ID,
    DEFAULT_USE_CASE_ID,
    write_data_plane_smoke_report,
)


DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_INGESTED_AT = "2026-01-15T09:15:05Z"
DEFAULT_BUILT_AT = "2026-01-15T09:15:10Z"
DEFAULT_EVALUATION_TIME = "2026-01-15T09:15:15Z"
DEFAULT_FINANCE_SCHEMA_ID = "registry:finance.benefit_settled.v1:1"
DEFAULT_SNAPSHOT_ID = "finance-benefit-local-live-lakehouse-smoke"


@dataclass(frozen=True)
class LiveLakehouseSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_live_lakehouse_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    input_path: str | Path | None = None,
    use_case_id: str = DEFAULT_USE_CASE_ID,
    release_id: str = DEFAULT_RELEASE_ID,
    environment: str = "local",
    generated_at: str | None = None,
    ingested_at: str | None = None,
    built_at: str | None = None,
    evaluation_time: str | None = None,
    schema_id: str | None = None,
    snapshot_id: str | None = None,
) -> LiveLakehouseSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    resolved_snapshot_id = snapshot_id or DEFAULT_SNAPSHOT_ID
    data_plane_report_path = target_dir / "jsonl-data-plane-smoke-report.json"
    data_plane = write_data_plane_smoke_report(
        platform_root,
        data_plane_report_path,
        input_path=input_path,
        output_dir=target_dir / "jsonl-run",
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated,
        ingested_at=ingested_at or DEFAULT_INGESTED_AT,
        built_at=built_at or DEFAULT_BUILT_AT,
        evaluation_time=evaluation_time or DEFAULT_EVALUATION_TIME,
        schema_id=schema_id or DEFAULT_FINANCE_SCHEMA_ID,
        snapshot_id=resolved_snapshot_id,
    )
    table_commits = [
        write_parquet_table_commit(
            layer,
            target_dir / "lakehouse",
            snapshot_id=resolved_snapshot_id,
            committed_at=generated,
        )
        for layer in data_plane.report.get("layers", [])
        if isinstance(layer, dict)
    ]
    primary_commit = next(
        (commit for commit in table_commits if commit.get("data_product") == data_plane.report.get("primary_output")),
        table_commits[-1] if table_commits else None,
    )
    query_probe = run_duckdb_gold_query(primary_commit)
    failed_checks = failed_live_checks(data_plane.report, table_commits, query_probe)
    report = {
        "artifact_type": "live_lakehouse_smoke_report.v1",
        "report_version": 1,
        "capability_id": "bronze-lakehouse-evidence",
        "report_id": f"live-lakehouse-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "primary_output": data_plane.report.get("primary_output"),
        "runtime_scope": {
            "mode": "local_parquet_duckdb_sql",
            "covered": [
                "jsonl_medallion_pipeline_reused_as_source",
                "bronze_silver_gold_parquet_table_commits",
                "parquet_schema_and_file_hash_evidence",
                "duckdb_sql_runtime_query_over_gold_parquet",
            ],
            "not_covered": [
                "iceberg_catalog_commit",
                "minio_object_store_commit",
                "trino_or_dremio_remote_query_runtime",
                "dagster_or_airflow_run_history",
                "runtime_security_enforcement",
            ],
        },
        "data_plane_smoke": {
            "path": data_plane_report_path.as_posix(),
            "hash": hash_file(data_plane_report_path),
            "passed": data_plane.report.get("passed") is True,
            "runtime_mode": data_plane.report.get("runtime_scope", {}).get("mode"),
        },
        "table_commits": table_commits,
        "query_probe": query_probe,
        "summary": {
            "table_count": len(table_commits),
            "parquet_commit_passed_count": sum(1 for commit in table_commits if commit.get("passed") is True),
            "query_engine": "duckdb",
            "query_passed": query_probe.get("passed") is True,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return LiveLakehouseSmokeResult(output_path=target, report=report)


def write_parquet_table_commit(
    layer: dict[str, Any],
    lakehouse_root: Path,
    *,
    snapshot_id: str,
    committed_at: str,
) -> dict[str, Any]:
    data_product = str(layer.get("name"))
    source_path = Path(str(layer.get("path")))
    rows = read_jsonl(source_path)
    table_dir = lakehouse_root / data_product.replace(".", "/")
    parquet_path = table_dir / f"{snapshot_id}.parquet"
    commit_path = table_dir / f"{snapshot_id}.commit.json"
    table = pa.Table.from_pylist(normalize_rows(rows))
    table_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, parquet_path, compression="zstd")
    commit = {
        "artifact_type": "parquet_table_commit.v1",
        "table_format": "parquet",
        "data_product": data_product,
        "source_jsonl_path": source_path.as_posix(),
        "source_jsonl_hash": hash_file(source_path),
        "snapshot_id": snapshot_id,
        "committed_at": committed_at,
        "parquet_path": parquet_path.as_posix(),
        "parquet_hash": hash_file(parquet_path),
        "row_count": table.num_rows,
        "column_count": table.num_columns,
        "schema": [{"name": field.name, "type": str(field.type)} for field in table.schema],
        "passed": parquet_path.is_file() and table.num_rows == layer.get("actual_row_count"),
    }
    commit_path.write_text(f"{canonical_json(commit)}\n", encoding="utf-8")
    commit["commit_path"] = commit_path.as_posix()
    commit["commit_hash"] = hash_file(commit_path)
    return commit


def run_duckdb_gold_query(primary_commit: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(primary_commit, dict):
        return {"passed": False, "reason": "primary Parquet commit is missing"}
    parquet_path = primary_commit.get("parquet_path")
    if not isinstance(parquet_path, str) or not Path(parquet_path).is_file():
        return {"passed": False, "reason": "primary Parquet file is missing"}
    con = duckdb.connect(database=":memory:")
    try:
        rows = con.execute(
            """
            SELECT
              reconciliation_status,
              COUNT(*)::INTEGER AS row_count,
              SUM(expected_amount_cents)::BIGINT AS expected_amount_cents,
              SUM(actual_amount_cents)::BIGINT AS actual_amount_cents,
              SUM(reconciliation_delta_cents)::BIGINT AS reconciliation_delta_cents,
              SUM(variance_points)::BIGINT AS variance_points
            FROM read_parquet(?)
            GROUP BY reconciliation_status
            ORDER BY reconciliation_status
            """,
            [parquet_path],
        ).fetchall()
    finally:
        con.close()
    result = [
        {
            "reconciliation_status": row[0],
            "row_count": row[1],
            "expected_amount_cents": row[2],
            "actual_amount_cents": row[3],
            "reconciliation_delta_cents": row[4],
            "variance_points": row[5],
        }
        for row in rows
    ]
    return {
        "passed": bool(result),
        "query_engine": "duckdb",
        "query_name": "finance_reconciliation_by_status_parquet",
        "source_table": primary_commit.get("data_product"),
        "source_parquet_path": parquet_path,
        "result_row_count": len(result),
        "result": result,
    }


def failed_live_checks(
    data_plane_report: dict[str, Any],
    table_commits: list[dict[str, Any]],
    query_probe: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if data_plane_report.get("passed") is not True:
        failed.append({"check": "upstream_data_plane_smoke_passed", "passed": data_plane_report.get("passed")})
    if not table_commits:
        failed.append({"check": "parquet_table_commits_present"})
    for commit in table_commits:
        if commit.get("passed") is not True:
            failed.append({"check": "parquet_table_commit", "data_product": commit.get("data_product")})
    if query_probe.get("passed") is not True:
        failed.append({"check": "duckdb_gold_query_passed", "reason": query_probe.get("reason")})
    return failed


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    columns = sorted({key for row in rows for key in row})
    return [{column: row.get(column) for column in columns} for row in rows]


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: JSONL record must be an object")
            records.append(record)
    return records


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
