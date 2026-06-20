from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import io
import json
import re
import subprocess
import time
from typing import Any, Callable

import pyarrow.parquet as pq

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.live_lakehouse_smoke import (
    DEFAULT_EVALUATION_TIME,
    DEFAULT_FINANCE_SCHEMA_ID,
    DEFAULT_GENERATED_AT,
    DEFAULT_INGESTED_AT,
    DEFAULT_BUILT_AT,
    DEFAULT_SNAPSHOT_ID,
    write_live_lakehouse_smoke_report,
)


DEFAULT_COMPOSE_FILE = Path("platform/runtime/local/docker-compose.yaml")
DEFAULT_SERVICE = "trino"
DEFAULT_SCHEMA = "enterprise_dp_smoke"
DEFAULT_TABLE = "finance_benefit_reconciliation"


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class TrinoSqlRuntimeSmokeResult:
    output_path: Path
    report: dict[str, Any]


CommandRunner = Callable[[list[str], str | None, Path, int], CommandResult]


def write_trino_sql_runtime_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    live_lakehouse_smoke_report_path: str | Path | None = None,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_SERVICE,
    schema: str = DEFAULT_SCHEMA,
    table: str = DEFAULT_TABLE,
    use_case_id: str = "finance-benefit-reconciliation",
    release_id: str = "local-trino-sql-runtime-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 12,
    wait_interval_seconds: float = 2.0,
    start_runtime: bool = True,
) -> TrinoSqlRuntimeSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    if live_lakehouse_smoke_report_path:
        live_report_path = Path(live_lakehouse_smoke_report_path)
        live_report = load_json(live_report_path)
    else:
        live_result = write_live_lakehouse_smoke_report(
            platform_root,
            target_dir / "live-lakehouse-smoke-report.json",
            output_dir=target_dir / "live-lakehouse-run",
            use_case_id=use_case_id,
            release_id=release_id,
            environment=environment,
            generated_at=generated,
            ingested_at=DEFAULT_INGESTED_AT,
            built_at=DEFAULT_BUILT_AT,
            evaluation_time=DEFAULT_EVALUATION_TIME,
            schema_id=DEFAULT_FINANCE_SCHEMA_ID,
            snapshot_id=DEFAULT_SNAPSHOT_ID,
        )
        live_report_path = live_result.output_path
        live_report = live_result.report

    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    primary_commit = primary_gold_commit(live_report)
    gold_rows = read_gold_rows(primary_commit)
    safe_schema = sql_identifier(schema)
    safe_table = sql_identifier(table)
    qualified_table = f"memory.{safe_schema}.{safe_table}"

    try:
        if start_runtime:
            execute_step(
                command_log,
                runner,
                ["docker", "compose", "-f", compose_path.as_posix(), "up", "-d", service],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="compose_up",
            )
        wait_for_trino(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            attempts=wait_attempts,
            interval_seconds=wait_interval_seconds,
        )
        execute_trino_sql(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="load_gold_rows",
            sql=load_sql(qualified_table, safe_schema, gold_rows),
        )
        query_result = execute_trino_sql(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="query_probe",
            sql=query_sql(qualified_table),
        )
        query_probe = parse_query_probe(query_result.stdout, source_table=primary_commit.get("data_product"))
    except RuntimeError as exc:
        failed_checks.append({"check": "trino_runtime_command", "message": str(exc)})
        query_probe = {"passed": False, "reason": str(exc)}

    expected_probe = expected_query_probe(gold_rows)
    failed_checks.extend(failed_trino_checks(live_report, primary_commit, gold_rows, query_probe, expected_probe))
    report = {
        "artifact_type": "trino_sql_runtime_smoke_report.v1",
        "report_version": 1,
        "capability_id": "semantic-metric-serving",
        "report_id": f"trino-sql-runtime-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "primary_output": live_report.get("primary_output"),
        "runtime_scope": {
            "mode": "local_trino_memory_catalog_sql",
            "covered": [
                "trino_container_started",
                "trino_memory_catalog_reachable",
                "gold_finance_rows_loaded_into_trino_memory_table",
                "trino_sql_aggregate_probe_executed",
                "trino_query_result_compared_to_gold_parquet_source",
            ],
            "not_covered": [
                "iceberg_catalog_commit",
                "minio_federated_query",
                "trino_iceberg_connector",
                "runtime_security_enforcement",
                "orchestrator_run_history",
            ],
        },
        "trino": {
            "compose_file": compose_path.as_posix(),
            "service": service,
            "catalog": "memory",
            "schema": safe_schema,
            "table": safe_table,
            "qualified_table": qualified_table,
        },
        "live_lakehouse_smoke": {
            "path": live_report_path.as_posix(),
            "hash": hash_file(live_report_path),
            "passed": live_report.get("passed") is True,
        },
        "gold_source": gold_source_ref(primary_commit),
        "load": {
            "row_count": len(gold_rows),
            "source_hash": primary_commit.get("parquet_hash"),
        },
        "query_probe": query_probe,
        "expected_query_probe": expected_probe,
        "commands": command_log,
        "summary": {
            "row_count": len(gold_rows),
            "query_engine": "trino",
            "query_mode": "memory_catalog",
            "query_passed": query_probe.get("passed") is True,
            "result_row_count": query_probe.get("result_row_count", 0),
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return TrinoSqlRuntimeSmokeResult(output_path=target, report=report)


def wait_for_trino(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    compose_path: Path,
    service: str,
    cwd: Path,
    timeout_seconds: int,
    attempts: int,
    interval_seconds: float,
) -> None:
    last_result: CommandResult | None = None
    for index in range(1, attempts + 1):
        result = execute_trino_sql(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step=f"trino_ready_probe_{index}",
            sql="SELECT 1",
            raise_on_error=False,
        )
        last_result = result
        if result.returncode == 0:
            return
        if interval_seconds > 0:
            time.sleep(interval_seconds)
    raise RuntimeError(command_failure_message("trino_ready_probe", last_result))


def execute_trino_sql(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    compose_path: Path,
    service: str,
    cwd: Path,
    timeout_seconds: int,
    step: str,
    sql: str,
    raise_on_error: bool = True,
) -> CommandResult:
    return execute_step(
        command_log,
        runner,
        ["docker", "compose", "-f", compose_path.as_posix(), "exec", "-T", service, "trino", "--execute", sql],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step=step,
        raise_on_error=raise_on_error,
    )


def execute_step(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    args: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    step: str,
    input_text: str | None = None,
    raise_on_error: bool = True,
) -> CommandResult:
    result = runner(args, input_text, cwd, timeout_seconds)
    command_log.append(
        {
            "step": step,
            "args": list(result.args),
            "returncode": result.returncode,
            "stdout_preview": result.stdout[:500],
            "stderr_preview": result.stderr[:500],
        }
    )
    if raise_on_error and result.returncode != 0:
        raise RuntimeError(command_failure_message(step, result))
    return result


def load_sql(qualified_table: str, schema: str, rows: list[dict[str, Any]]) -> str:
    return " ".join(
        [
            f"DROP TABLE IF EXISTS {qualified_table}",
            f"; CREATE SCHEMA IF NOT EXISTS memory.{schema}",
            f"; CREATE TABLE {qualified_table} ("
            "reconciliation_status varchar, "
            "expected_amount_cents bigint, "
            "actual_amount_cents bigint, "
            "reconciliation_delta_cents bigint, "
            "variance_points bigint"
            ")",
            f"; INSERT INTO {qualified_table} VALUES {values_sql(rows)}",
        ]
    )


def query_sql(qualified_table: str) -> str:
    return f"""
        SELECT
          reconciliation_status,
          CAST(COUNT(*) AS INTEGER) AS row_count,
          CAST(SUM(expected_amount_cents) AS BIGINT) AS expected_amount_cents,
          CAST(SUM(actual_amount_cents) AS BIGINT) AS actual_amount_cents,
          CAST(SUM(reconciliation_delta_cents) AS BIGINT) AS reconciliation_delta_cents,
          CAST(SUM(variance_points) AS BIGINT) AS variance_points
        FROM {qualified_table}
        GROUP BY reconciliation_status
        ORDER BY reconciliation_status
    """


def values_sql(rows: list[dict[str, Any]]) -> str:
    if not rows:
        raise ValueError("Gold source rows are empty")
    values = [
        "("
        + ", ".join(
            [
                sql_string(row["reconciliation_status"]),
                sql_int(row["expected_amount_cents"]),
                sql_int(row["actual_amount_cents"]),
                sql_int(row["reconciliation_delta_cents"]),
                sql_int(row["variance_points"]),
            ]
        )
        + ")"
        for row in rows
    ]
    return ", ".join(values)


def parse_query_probe(stdout: str, *, source_table: str | None) -> dict[str, Any]:
    result = []
    for row in csv.reader(io.StringIO(stdout)):
        if len(row) != 6:
            continue
        result.append(
            {
                "reconciliation_status": row[0],
                "row_count": int(row[1]),
                "expected_amount_cents": int(row[2]),
                "actual_amount_cents": int(row[3]),
                "reconciliation_delta_cents": int(row[4]),
                "variance_points": int(row[5]),
            }
        )
    return {
        "passed": bool(result),
        "query_engine": "trino",
        "query_name": "finance_reconciliation_by_status_trino_memory",
        "source_table": source_table,
        "result_row_count": len(result),
        "result": result,
    }


def expected_query_probe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        status = str(row["reconciliation_status"])
        target = grouped.setdefault(
            status,
            {
                "reconciliation_status": status,
                "row_count": 0,
                "expected_amount_cents": 0,
                "actual_amount_cents": 0,
                "reconciliation_delta_cents": 0,
                "variance_points": 0,
            },
        )
        target["row_count"] += 1
        target["expected_amount_cents"] += int(row["expected_amount_cents"])
        target["actual_amount_cents"] += int(row["actual_amount_cents"])
        target["reconciliation_delta_cents"] += int(row["reconciliation_delta_cents"])
        target["variance_points"] += int(row["variance_points"])
    return [grouped[key] for key in sorted(grouped)]


def failed_trino_checks(
    live_report: dict[str, Any],
    primary_commit: dict[str, Any],
    gold_rows: list[dict[str, Any]],
    query_probe: dict[str, Any],
    expected_probe: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if live_report.get("passed") is not True:
        failed.append({"check": "live_lakehouse_smoke_passed", "passed": live_report.get("passed")})
    if not primary_commit:
        failed.append({"check": "gold_primary_commit_present"})
    if len(gold_rows) != 4:
        failed.append({"check": "gold_row_count", "expected": 4, "actual": len(gold_rows)})
    if query_probe.get("passed") is not True:
        failed.append({"check": "trino_query_passed", "reason": query_probe.get("reason")})
    if query_probe.get("result") != expected_probe:
        failed.append(
            {
                "check": "trino_query_result_matches_gold_source",
                "expected": expected_probe,
                "actual": query_probe.get("result"),
            }
        )
    return failed


def read_gold_rows(primary_commit: dict[str, Any]) -> list[dict[str, Any]]:
    parquet_path = primary_commit.get("parquet_path") if isinstance(primary_commit, dict) else None
    if not isinstance(parquet_path, str) or not Path(parquet_path).is_file():
        raise RuntimeError("primary Gold Parquet file is missing")
    table = pq.read_table(
        parquet_path,
        columns=[
            "reconciliation_status",
            "expected_amount_cents",
            "actual_amount_cents",
            "reconciliation_delta_cents",
            "variance_points",
        ],
    )
    return table.to_pylist()


def primary_gold_commit(live_report: dict[str, Any]) -> dict[str, Any]:
    primary_output = live_report.get("primary_output")
    commits = live_report.get("table_commits")
    for commit in commits if isinstance(commits, list) else []:
        if isinstance(commit, dict) and commit.get("data_product") == primary_output:
            return commit
    raise RuntimeError("primary Gold table commit is missing from live lakehouse smoke report")


def gold_source_ref(primary_commit: dict[str, Any]) -> dict[str, Any]:
    parquet_path = Path(str(primary_commit.get("parquet_path")))
    return {
        "data_product": primary_commit.get("data_product"),
        "snapshot_id": primary_commit.get("snapshot_id"),
        "parquet_path": parquet_path.as_posix(),
        "parquet_hash": primary_commit.get("parquet_hash"),
        "row_count": primary_commit.get("row_count"),
        "schema_column_count": len(primary_commit.get("schema", [])) if isinstance(primary_commit.get("schema"), list) else 0,
    }


def run_command(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
    completed = subprocess.run(
        args,
        input=input_text,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return CommandResult(
        args=tuple(args),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def resolve_compose_path(root: Path, compose_file: str | Path | None) -> Path:
    path = Path(compose_file) if compose_file else DEFAULT_COMPOSE_FILE
    return path if path.is_absolute() else root / path


def command_failure_message(step: str, result: CommandResult | None) -> str:
    if result is None:
        return f"{step} failed without command result"
    detail = result.stderr[:500] or result.stdout[:500]
    return f"{step} failed with exit code {result.returncode}: {detail}"


def sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return value


def sql_string(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sql_int(value: Any) -> str:
    return str(int(value))
