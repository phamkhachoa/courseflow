from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import csv
import io

import pyarrow as pa
import pyiceberg
from pyiceberg.catalog import load_catalog

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.event_backbone_smoke import stable_id
from enterprise_dp.live_lakehouse_smoke import DEFAULT_GENERATED_AT
from enterprise_dp.object_store_smoke import (
    DEFAULT_ACCESS_KEY,
    DEFAULT_MINIO_SERVICE,
    DEFAULT_SECRET_KEY,
    ensure_bucket,
    s3_client,
)
from enterprise_dp.trino_iceberg_minio_smoke import (
    DEFAULT_BUCKET,
    DEFAULT_CATALOG,
    DEFAULT_POSTGRES_SERVICE,
    DEFAULT_SCHEMA,
    DEFAULT_SERVICE,
    initialize_jdbc_catalog,
    metadata_count_probe,
)
from enterprise_dp.trino_sql_smoke import (
    CommandRunner,
    execute_step,
    execute_trino_sql,
    resolve_compose_path,
    run_command,
    sql_identifier,
    wait_for_trino,
)


DEFAULT_CATALOG_NAME = "local_finance_iceberg"
DEFAULT_CROSS_ENGINE_TABLE = "catalog_cross_engine_probe"
DEFAULT_CONCURRENCY_TABLE = "catalog_lock_probe"
DEFAULT_CATALOG_URI = "postgresql+psycopg://iceberg:iceberg_local_only_change_me@localhost:15432/iceberg"
DEFAULT_ENDPOINT_URL = "http://localhost:19000"
DEFAULT_TRINO_ROWS = (
    {"id": 1, "engine": "trino", "amount": 100},
    {"id": 2, "engine": "trino", "amount": 200},
)
DEFAULT_PYICEBERG_ROWS = ({"id": 3, "engine": "pyiceberg", "amount": 300},)

TrinoExecutor = Callable[[str, str], Any]


@dataclass(frozen=True)
class CatalogCompatibilitySmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_catalog_compatibility_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    trino_iceberg_minio_smoke_report_path: str | Path | None = None,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_SERVICE,
    postgres_service: str = DEFAULT_POSTGRES_SERVICE,
    minio_service: str = DEFAULT_MINIO_SERVICE,
    bucket: str = DEFAULT_BUCKET,
    endpoint_url: str = DEFAULT_ENDPOINT_URL,
    access_key: str = DEFAULT_ACCESS_KEY,
    secret_key: str = DEFAULT_SECRET_KEY,
    region_name: str = "us-east-1",
    catalog: str = DEFAULT_CATALOG,
    catalog_name: str = DEFAULT_CATALOG_NAME,
    schema: str = DEFAULT_SCHEMA,
    cross_engine_table: str = DEFAULT_CROSS_ENGINE_TABLE,
    concurrency_table: str = DEFAULT_CONCURRENCY_TABLE,
    catalog_uri: str = DEFAULT_CATALOG_URI,
    warehouse_location: str | None = None,
    release_id: str = "local-catalog-cross-engine-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 12,
    wait_interval_seconds: float = 2.0,
    start_runtime: bool = True,
    s3_client_override: Any | None = None,
    pyiceberg_catalog_override: Any | None = None,
    trino_executor_override: TrinoExecutor | None = None,
) -> CatalogCompatibilitySmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    safe_catalog = sql_identifier(catalog)
    safe_schema = sql_identifier(schema)
    safe_cross_engine_table = sql_identifier(cross_engine_table)
    safe_concurrency_table = sql_identifier(concurrency_table)
    warehouse = warehouse_location or f"s3://{bucket}/warehouse"
    schema_location = f"{warehouse}/{safe_schema}"
    upstream_report, upstream_path = load_optional_upstream(trino_iceberg_minio_smoke_report_path)
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    cross_engine_probe: dict[str, Any] = {"passed": False}
    concurrency_probe: dict[str, Any] = {"passed": False}
    snapshots_probe: dict[str, Any] = {"passed": False}
    object_store_probe: dict[str, Any] = {"passed": False}

    try:
        if pyiceberg_catalog_override is None:
            if start_runtime:
                execute_step(
                    command_log,
                    runner,
                    [
                        "docker",
                        "compose",
                        "-f",
                        compose_path.as_posix(),
                        "up",
                        "-d",
                        minio_service,
                        postgres_service,
                        service,
                    ],
                    cwd=platform_root,
                    timeout_seconds=command_timeout_seconds,
                    step="compose_up_catalog_compatibility_runtime",
                )
            initialize_jdbc_catalog(
                command_log,
                runner,
                compose_path=compose_path,
                postgres_service=postgres_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
            )
            client = s3_client_override or s3_client(
                endpoint_url=endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
                region_name=region_name,
            )
            bucket_created = ensure_bucket(client, bucket)
            object_store_probe = {"passed": True, "bucket": bucket, "bucket_created": bucket_created}
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
        else:
            object_store_probe = {"passed": True, "mode": "test_catalog_override"}
        catalog_client = pyiceberg_catalog_override or load_catalog(
            catalog_name,
            **{
                "type": "sql",
                "uri": catalog_uri,
                "warehouse": warehouse,
                "s3.endpoint": endpoint_url,
                "s3.access-key-id": access_key,
                "s3.secret-access-key": secret_key,
                "s3.region": region_name,
            },
        )

        def trino_executor(sql: str, step: str) -> Any:
            if trino_executor_override is not None:
                return trino_executor_override(sql, step)
            return execute_trino_sql(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step=step,
                sql=sql,
            )

        catalog_probe = trino_executor("SHOW CATALOGS", "show_catalogs")
        if command_succeeded(catalog_probe) and safe_catalog not in command_stdout(catalog_probe):
            raise RuntimeError(f"Trino catalog {safe_catalog!r} is not available: {command_stdout(catalog_probe)[:500]}")
        cross_engine_probe = run_cross_engine_probe(
            catalog_client,
            trino_executor,
            catalog=safe_catalog,
            schema=safe_schema,
            table=safe_cross_engine_table,
            schema_location=schema_location,
        )
        concurrency_probe = run_concurrency_probe(
            catalog_client,
            trino_executor,
            catalog=safe_catalog,
            schema=safe_schema,
            table=safe_concurrency_table,
            schema_location=schema_location,
        )
        snapshots_probe = metadata_count_probe(
            command_stdout(
                trino_executor(
                    f'SELECT COUNT(*) FROM {safe_catalog}.{safe_schema}."{safe_cross_engine_table}$snapshots"',
                    "query_cross_engine_snapshots",
                )
            ),
            probe_name="cross_engine_snapshots",
        )
    except Exception as exc:
        failed_checks.append({"check": "catalog_cross_engine_runtime", "message": f"{type(exc).__name__}: {exc}"})

    failed_checks.extend(
        failed_catalog_compatibility_checks(
            upstream_report=upstream_report,
            object_store_probe=object_store_probe,
            cross_engine_probe=cross_engine_probe,
            concurrency_probe=concurrency_probe,
            snapshots_probe=snapshots_probe,
        )
    )
    report = build_catalog_compatibility_smoke_report(
        root=platform_root,
        output_dir=target_dir,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        catalog=safe_catalog,
        catalog_name=catalog_name,
        schema=safe_schema,
        cross_engine_table=safe_cross_engine_table,
        concurrency_table=safe_concurrency_table,
        catalog_uri=catalog_uri,
        warehouse_location=warehouse,
        compose_path=compose_path,
        service=service,
        postgres_service=postgres_service,
        upstream_report=upstream_report,
        upstream_path=upstream_path,
        object_store_probe=object_store_probe,
        cross_engine_probe=cross_engine_probe,
        concurrency_probe=concurrency_probe,
        snapshots_probe=snapshots_probe,
        command_log=command_log,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return CatalogCompatibilitySmokeResult(output_path=target, report=report)


def run_cross_engine_probe(
    catalog_client: Any,
    trino_executor: TrinoExecutor,
    *,
    catalog: str,
    schema: str,
    table: str,
    schema_location: str,
) -> dict[str, Any]:
    qualified_table = f"{catalog}.{schema}.{table}"
    trino_executor(
        create_probe_table_sql(
            qualified_table,
            catalog=catalog,
            schema=schema,
            schema_location=schema_location,
            rows=DEFAULT_TRINO_ROWS,
        ),
        "create_cross_engine_table_with_trino",
    )
    table_identifier = (schema, table)
    iceberg_table = catalog_client.load_table(table_identifier)
    trino_snapshot_count = len(iceberg_table.snapshots())
    trino_rows = iceberg_table.scan().to_arrow().to_pylist()
    iceberg_table.append(arrow_table(DEFAULT_PYICEBERG_ROWS))
    reloaded_table = catalog_client.load_table(table_identifier)
    pyiceberg_rows = reloaded_table.scan().to_arrow().to_pylist()
    snapshots_after_pyiceberg = reloaded_table.snapshots()
    trino_readback = parse_engine_aggregate(
        command_stdout(
            trino_executor(
                engine_aggregate_query(qualified_table),
                "query_cross_engine_table_after_pyiceberg_append",
            )
        )
    )
    expected = [
        {"engine": "pyiceberg", "row_count": 1, "amount_sum": 300},
        {"engine": "trino", "row_count": 2, "amount_sum": 300},
    ]
    return {
        "passed": (
            len(trino_rows) == 2
            and len(pyiceberg_rows) == 3
            and len(snapshots_after_pyiceberg) > trino_snapshot_count
            and trino_readback == expected
        ),
        "table": qualified_table,
        "trino_initial_row_count": len(trino_rows),
        "pyiceberg_readback_row_count": len(pyiceberg_rows),
        "snapshot_count_before_pyiceberg": trino_snapshot_count,
        "snapshot_count_after_pyiceberg": len(snapshots_after_pyiceberg),
        "latest_metadata_location": getattr(reloaded_table, "metadata_location", None),
        "trino_readback_after_pyiceberg": trino_readback,
        "expected_trino_readback": expected,
    }


def run_concurrency_probe(
    catalog_client: Any,
    trino_executor: TrinoExecutor,
    *,
    catalog: str,
    schema: str,
    table: str,
    schema_location: str,
) -> dict[str, Any]:
    qualified_table = f"{catalog}.{schema}.{table}"
    trino_executor(
        create_probe_table_sql(
            qualified_table,
            catalog=catalog,
            schema=schema,
            schema_location=schema_location,
            rows=({"id": 1, "engine": "trino", "amount": 100},),
        ),
        "create_concurrency_table_with_trino",
    )
    table_identifier = (schema, table)
    first_handle = catalog_client.load_table(table_identifier)
    stale_handle = catalog_client.load_table(table_identifier)
    snapshot_count_before = len(first_handle.snapshots())
    first_handle.append(arrow_table(({"id": 2, "engine": "pyiceberg-first", "amount": 200},)))
    stale_error: dict[str, Any] | None = None
    try:
        stale_handle.append(arrow_table(({"id": 3, "engine": "pyiceberg-stale", "amount": 300},)))
    except Exception as exc:
        stale_error = {"type": type(exc).__name__, "message": str(exc)}
    reloaded_table = catalog_client.load_table(table_identifier)
    rows = reloaded_table.scan().to_arrow().to_pylist()
    engines = {str(row.get("engine")) for row in rows}
    snapshot_count_after = len(reloaded_table.snapshots())
    stale_rejected = stale_error is not None and "pyiceberg-stale" not in engines
    return {
        "passed": stale_rejected and "pyiceberg-first" in engines and snapshot_count_after == snapshot_count_before + 1,
        "table": qualified_table,
        "snapshot_count_before": snapshot_count_before,
        "snapshot_count_after": snapshot_count_after,
        "first_append_committed": "pyiceberg-first" in engines,
        "stale_commit_rejected": stale_rejected,
        "stale_commit_error": stale_error,
        "final_row_count": len(rows),
        "final_engines": sorted(engines),
    }


def build_catalog_compatibility_smoke_report(
    *,
    root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    catalog: str,
    catalog_name: str,
    schema: str,
    cross_engine_table: str,
    concurrency_table: str,
    catalog_uri: str,
    warehouse_location: str,
    compose_path: Path,
    service: str,
    postgres_service: str,
    upstream_report: dict[str, Any] | None,
    upstream_path: Path | None,
    object_store_probe: dict[str, Any],
    cross_engine_probe: dict[str, Any],
    concurrency_probe: dict[str, Any],
    snapshots_probe: dict[str, Any],
    command_log: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = {
        "catalog": catalog,
        "catalog_name": catalog_name,
        "catalog_backend": "postgresql_jdbc_catalog",
        "schema": schema,
        "cross_engine_table": cross_engine_table,
        "concurrency_table": concurrency_table,
        "cross_engine_commit_compatibility_passed": cross_engine_probe.get("passed") is True,
        "catalog_concurrency_locking_passed": concurrency_probe.get("passed") is True,
        "stale_commit_rejected": concurrency_probe.get("stale_commit_rejected") is True,
        "trino_initial_row_count": cross_engine_probe.get("trino_initial_row_count", 0),
        "pyiceberg_readback_row_count": cross_engine_probe.get("pyiceberg_readback_row_count", 0),
        "trino_read_after_pyiceberg_passed": cross_engine_probe.get("trino_readback_after_pyiceberg")
        == cross_engine_probe.get("expected_trino_readback"),
        "snapshot_count_after_pyiceberg": cross_engine_probe.get("snapshot_count_after_pyiceberg", 0),
        "concurrency_snapshot_count_before": concurrency_probe.get("snapshot_count_before", 0),
        "concurrency_snapshot_count_after": concurrency_probe.get("snapshot_count_after", 0),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    return {
        "artifact_type": "catalog_cross_engine_smoke_report.v1",
        "report_version": 1,
        "capability_id": "bronze-lakehouse-evidence",
        "report_id": stable_id("catalog-cross-engine-smoke", environment, release_id),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_trino_pyiceberg_jdbc_catalog_minio_cross_engine",
            "covered": [
                "postgres_jdbc_iceberg_catalog_shared_by_trino_and_pyiceberg",
                "trino_created_iceberg_table_pyiceberg_readback",
                "pyiceberg_append_trino_readback",
                "iceberg_snapshot_metadata_after_cross_engine_append",
                "optimistic_concurrency_conflict_rejected",
                "stale_metadata_commit_does_not_overwrite_latest_snapshot",
            ],
            "not_covered": [
                "production_catalog_ha",
                "managed_catalog_failover",
                "multi_az_catalog_deployment",
                "production_catalog_backup_restore_pitr",
            ],
        },
        "catalog_runtime": {
            "compose_file": compose_path.as_posix(),
            "trino_service": service,
            "postgres_service": postgres_service,
            "trino_catalog": catalog,
            "iceberg_catalog_name": catalog_name,
            "catalog_uri": redact_catalog_uri(catalog_uri),
            "warehouse_location": warehouse_location,
            "pyiceberg_version": pyiceberg.__version__,
            "root": root.as_posix(),
            "output_dir": output_dir.as_posix(),
        },
        "trino_iceberg_minio_smoke": optional_ref(upstream_path, upstream_report),
        "object_store_probe": object_store_probe,
        "cross_engine_probe": cross_engine_probe,
        "concurrency_probe": concurrency_probe,
        "snapshots_probe": snapshots_probe,
        "commands": command_log,
        "summary": summary,
        "passed": not failed_checks,
    }


def failed_catalog_compatibility_checks(
    *,
    upstream_report: dict[str, Any] | None,
    object_store_probe: dict[str, Any],
    cross_engine_probe: dict[str, Any],
    concurrency_probe: dict[str, Any],
    snapshots_probe: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if upstream_report is not None and upstream_report.get("passed") is not True:
        failed.append({"check": "trino_iceberg_minio_smoke_passed", "passed": upstream_report.get("passed")})
    if object_store_probe.get("passed") is not True:
        failed.append({"check": "object_store_bucket_ready", "probe": object_store_probe})
    if cross_engine_probe.get("passed") is not True:
        failed.append({"check": "cross_engine_commit_compatibility", "probe": cross_engine_probe})
    if concurrency_probe.get("passed") is not True:
        failed.append({"check": "catalog_optimistic_concurrency_conflict_detection", "probe": concurrency_probe})
    if snapshots_probe.get("passed") is not True:
        failed.append({"check": "cross_engine_snapshots_metadata_table", "probe": snapshots_probe})
    return failed


def create_probe_table_sql(
    qualified_table: str,
    *,
    catalog: str,
    schema: str,
    schema_location: str,
    rows: tuple[dict[str, Any], ...],
) -> str:
    return " ".join(
        [
            f"DROP TABLE IF EXISTS {qualified_table}",
            f"; CREATE SCHEMA IF NOT EXISTS {catalog}.{schema} WITH (location='{schema_location}')",
            f"; CREATE TABLE {qualified_table} (id bigint, engine varchar, amount bigint) WITH (format='PARQUET')",
            f"; INSERT INTO {qualified_table} VALUES {probe_values_sql(rows)}",
        ]
    )


def engine_aggregate_query(qualified_table: str) -> str:
    return (
        "SELECT engine, CAST(COUNT(*) AS INTEGER) AS row_count, "
        f"CAST(SUM(amount) AS BIGINT) AS amount_sum FROM {qualified_table} GROUP BY engine ORDER BY engine"
    )


def probe_values_sql(rows: tuple[dict[str, Any], ...]) -> str:
    return ", ".join(f"({int(row['id'])}, '{row['engine']}', {int(row['amount'])})" for row in rows)


def arrow_table(rows: tuple[dict[str, Any], ...]) -> pa.Table:
    return pa.table(
        {
            "id": [int(row["id"]) for row in rows],
            "engine": [str(row["engine"]) for row in rows],
            "amount": [int(row["amount"]) for row in rows],
        },
        schema=pa.schema(
            [
                pa.field("id", pa.int64(), nullable=True),
                pa.field("engine", pa.string(), nullable=True),
                pa.field("amount", pa.int64(), nullable=True),
            ]
        ),
    )


def parse_engine_aggregate(stdout: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in csv.reader(io.StringIO(stdout)):
        if len(row) != 3:
            continue
        result.append({"engine": row[0], "row_count": int(row[1]), "amount_sum": int(row[2])})
    return result


def command_stdout(result: Any) -> str:
    return result.stdout if hasattr(result, "stdout") else str(result or "")


def command_succeeded(result: Any) -> bool:
    return not hasattr(result, "returncode") or result.returncode == 0


def load_optional_upstream(path_value: str | Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    if path_value is None:
        return None, None
    path = Path(path_value)
    return load_json(path), path


def optional_ref(path: Path | None, payload: dict[str, Any] | None) -> dict[str, Any]:
    if path is None or payload is None:
        return {"attached": False, "uri": None, "hash": None, "artifact_type": None, "passed": None}
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": payload.get("artifact_type"),
        "passed": payload.get("passed"),
    }


def redact_catalog_uri(uri: str) -> str:
    if "@" not in uri or "://" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    return f"{scheme}://***:***@{rest.split('@', 1)[1]}"
