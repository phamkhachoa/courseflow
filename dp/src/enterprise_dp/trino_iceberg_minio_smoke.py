from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.live_lakehouse_smoke import (
    DEFAULT_BUILT_AT,
    DEFAULT_EVALUATION_TIME,
    DEFAULT_FINANCE_SCHEMA_ID,
    DEFAULT_GENERATED_AT,
    DEFAULT_INGESTED_AT,
    DEFAULT_SNAPSHOT_ID,
    write_live_lakehouse_smoke_report,
)
from enterprise_dp.object_store_smoke import (
    DEFAULT_ACCESS_KEY,
    DEFAULT_SECRET_KEY,
    DEFAULT_SSE_ALGORITHM,
    DEFAULT_MINIO_SERVICE,
    DEFAULT_PROBE_ACCESS_KEY,
    DEFAULT_PROBE_SECRET_KEY,
    configure_minio_probe_user,
    configure_bucket_encryption_policy,
    s3_client,
)
from enterprise_dp.trino_sql_smoke import (
    CommandResult,
    CommandRunner,
    DEFAULT_COMPOSE_FILE,
    execute_step,
    execute_trino_sql,
    expected_query_probe,
    gold_source_ref,
    parse_query_probe,
    primary_gold_commit,
    read_gold_rows,
    resolve_compose_path,
    run_command,
    sql_identifier,
    values_sql,
    wait_for_trino,
)


DEFAULT_SERVICE = "trino"
DEFAULT_POSTGRES_SERVICE = "iceberg-postgres"
DEFAULT_BUCKET = "enterprise-dp-local-iceberg"
DEFAULT_ENDPOINT_URL = "http://localhost:19000"
DEFAULT_CONTAINER_ENDPOINT_URL = "http://minio:9000"
DEFAULT_CATALOG = "iceberg"
DEFAULT_SCHEMA = "finance_iceberg_smoke"
DEFAULT_TABLE = "finance_benefit_reconciliation"


@dataclass(frozen=True)
class TrinoIcebergMinioSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_trino_iceberg_minio_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    live_lakehouse_smoke_report_path: str | Path | None = None,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_SERVICE,
    postgres_service: str = DEFAULT_POSTGRES_SERVICE,
    minio_service: str = DEFAULT_MINIO_SERVICE,
    bucket: str = DEFAULT_BUCKET,
    endpoint_url: str = DEFAULT_ENDPOINT_URL,
    access_key: str = DEFAULT_ACCESS_KEY,
    secret_key: str = DEFAULT_SECRET_KEY,
    region_name: str = "us-east-1",
    sse_algorithm: str = DEFAULT_SSE_ALGORITHM,
    probe_access_key: str = DEFAULT_PROBE_ACCESS_KEY,
    probe_secret_key: str = DEFAULT_PROBE_SECRET_KEY,
    catalog: str = DEFAULT_CATALOG,
    schema: str = DEFAULT_SCHEMA,
    table: str = DEFAULT_TABLE,
    use_case_id: str = "finance-benefit-reconciliation",
    release_id: str = "local-trino-iceberg-minio-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 12,
    wait_interval_seconds: float = 2.0,
    start_runtime: bool = True,
    s3_client_override: Any | None = None,
) -> TrinoIcebergMinioSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    live_report_path, live_report = load_or_create_live_report(
        platform_root,
        target_dir,
        live_lakehouse_smoke_report_path=live_lakehouse_smoke_report_path,
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated,
    )
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    client = s3_client_override or s3_client(
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        region_name=region_name,
    )
    safe_catalog = sql_identifier(catalog)
    safe_schema = sql_identifier(schema)
    safe_table = sql_identifier(table)
    qualified_table = f"{safe_catalog}.{safe_schema}.{safe_table}"
    warehouse_location = f"s3://{bucket}/warehouse/{safe_schema}"
    object_prefix = f"warehouse/{safe_schema}/{safe_table}"
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    primary_commit = primary_gold_commit(live_report)
    gold_rows = read_gold_rows(primary_commit)
    query_probe: dict[str, Any] = {"passed": False}
    snapshots_probe: dict[str, Any] = {"passed": False}
    files_probe: dict[str, Any] = {"passed": False}
    minio_probe: dict[str, Any] = {"passed": False}
    bucket_created = False
    encryption_policy: dict[str, Any] = {"passed": False}

    try:
        probe_client = client
        if s3_client_override is None:
            configure_minio_probe_user(
                runner,
                platform_root=platform_root,
                compose_path=compose_path,
                minio_service=minio_service,
                root_access_key=access_key,
                root_secret_key=secret_key,
                bucket=bucket,
                prefix=object_prefix,
                sse_algorithm=sse_algorithm,
                probe_access_key=probe_access_key,
                probe_secret_key=probe_secret_key,
                command_timeout_seconds=command_timeout_seconds,
            )
            probe_client = s3_client(
                endpoint_url=endpoint_url,
                access_key=probe_access_key,
                secret_key=probe_secret_key,
                region_name=region_name,
            )
        encryption_policy = configure_bucket_encryption_policy(
            client,
            bucket=bucket,
            prefix=object_prefix,
            sse_algorithm=sse_algorithm,
            probe_client=probe_client,
        )
        bucket_created = encryption_policy.get("bucket_created", False)
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
                    "minio",
                    postgres_service,
                    service,
                ],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="compose_up",
            )
        initialize_jdbc_catalog(
            command_log,
            runner,
            compose_path=compose_path,
            postgres_service=postgres_service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
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
        catalog_probe = execute_trino_sql(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="show_catalogs",
            sql="SHOW CATALOGS",
        )
        if f'"{safe_catalog}"' not in catalog_probe.stdout and safe_catalog not in catalog_probe.stdout:
            raise RuntimeError(f"Trino catalog {safe_catalog!r} is not available: {catalog_probe.stdout[:500]}")
        execute_trino_sql(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="create_insert_iceberg_table",
            sql=create_insert_sql(qualified_table, safe_catalog, safe_schema, warehouse_location, gold_rows),
        )
        query_result = execute_trino_sql(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="query_iceberg_probe",
            sql=query_sql(qualified_table),
        )
        query_probe = parse_query_probe(query_result.stdout, source_table=primary_commit.get("data_product"))
        query_probe["query_name"] = "finance_reconciliation_by_status_trino_iceberg_minio"
        snapshots_probe = metadata_count_probe(
            execute_trino_sql(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="query_iceberg_snapshots",
                sql=f'SELECT COUNT(*) FROM {safe_catalog}.{safe_schema}."{safe_table}$snapshots"',
            ).stdout,
            probe_name="snapshots",
        )
        files_probe = metadata_count_probe(
            execute_trino_sql(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="query_iceberg_files",
                sql=f'SELECT COUNT(*) FROM {safe_catalog}.{safe_schema}."{safe_table}$files"',
            ).stdout,
            probe_name="files",
        )
        minio_probe = minio_object_probe(client, bucket=bucket, prefix=object_prefix, sse_algorithm=sse_algorithm)
    except RuntimeError as exc:
        failed_checks.append({"check": "trino_iceberg_minio_runtime_command", "message": str(exc)})
    expected_probe = expected_query_probe(gold_rows)
    failed_checks.extend(
        failed_trino_iceberg_minio_checks(
            live_report=live_report,
            primary_commit=primary_commit,
            gold_rows=gold_rows,
            query_probe=query_probe,
            expected_probe=expected_probe,
            snapshots_probe=snapshots_probe,
            files_probe=files_probe,
            minio_probe=minio_probe,
            encryption_policy=encryption_policy,
        )
    )
    report = {
        "artifact_type": "trino_iceberg_minio_smoke_report.v1",
        "report_version": 1,
        "capability_id": "semantic-metric-serving",
        "report_id": f"trino-iceberg-minio-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "primary_output": live_report.get("primary_output"),
        "runtime_scope": {
            "mode": "local_trino_iceberg_jdbc_catalog_minio_s3",
            "covered": [
                "trino_iceberg_connector_loaded",
                "postgres_jdbc_iceberg_catalog_initialized",
                "minio_iceberg_warehouse_bucket_created_or_reused",
                "trino_iceberg_schema_created_with_s3_location",
                "trino_iceberg_table_created_and_inserted",
                "trino_iceberg_gold_query_probe_executed",
                "iceberg_snapshots_metadata_table_queried",
                "iceberg_files_metadata_table_queried",
                "minio_iceberg_data_and_metadata_objects_verified",
                "minio_sse_s3_bucket_default_encryption_configured",
                "minio_bucket_policy_denies_unencrypted_puts",
                "trino_iceberg_data_and_metadata_objects_have_sse_header",
            ],
            "not_covered": [
                "production_catalog_ha",
                "production_catalog_concurrency_locking",
                "cross_engine_commit_compatibility",
                "production_cloud_kms_key_rotation",
                "cloud_provider_bucket_policy_attestation",
                "cross_account_object_store_access_policy",
                "runtime_security_enforcement",
            ],
        },
        "trino": {
            "compose_file": compose_path.as_posix(),
            "service": service,
            "catalog": safe_catalog,
            "schema": safe_schema,
            "table": safe_table,
            "qualified_table": qualified_table,
        },
        "iceberg_catalog": {
            "type": "jdbc",
            "postgres_service": postgres_service,
            "warehouse_location": warehouse_location,
        },
        "object_store": {
            "provider": "minio",
            "endpoint_url": endpoint_url,
            "container_endpoint_url": DEFAULT_CONTAINER_ENDPOINT_URL,
            "bucket": bucket,
            "bucket_created": bucket_created,
            "prefix": object_prefix,
        },
        "encryption_policy": encryption_policy,
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
        "snapshots_probe": snapshots_probe,
        "files_probe": files_probe,
        "minio_probe": minio_probe,
        "commands": command_log,
        "summary": {
            "row_count": len(gold_rows),
            "query_engine": "trino",
            "query_mode": "iceberg_jdbc_catalog_minio_s3",
            "query_passed": query_probe.get("passed") is True,
            "result_row_count": query_probe.get("result_row_count", 0),
            "snapshot_count": snapshots_probe.get("count", 0),
            "iceberg_file_count": files_probe.get("count", 0),
            "minio_object_count": minio_probe.get("object_count", 0),
            "minio_data_object_count": minio_probe.get("data_object_count", 0),
            "minio_metadata_object_count": minio_probe.get("metadata_object_count", 0),
            "minio_encrypted_object_count": minio_probe.get("encrypted_object_count", 0),
            "object_store_encryption_policy_enforced": encryption_policy.get("passed") is True,
            "trino_iceberg_objects_encrypted": minio_probe.get("all_objects_encrypted") is True,
            "sse_algorithm": sse_algorithm,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return TrinoIcebergMinioSmokeResult(output_path=target, report=report)


def load_or_create_live_report(
    platform_root: Path,
    target_dir: Path,
    *,
    live_lakehouse_smoke_report_path: str | Path | None,
    use_case_id: str,
    release_id: str,
    environment: str,
    generated_at: str,
) -> tuple[Path, dict[str, Any]]:
    if live_lakehouse_smoke_report_path:
        live_report_path = Path(live_lakehouse_smoke_report_path)
        return live_report_path, load_json(live_report_path)
    live_result = write_live_lakehouse_smoke_report(
        platform_root,
        target_dir / "live-lakehouse-smoke-report.json",
        output_dir=target_dir / "live-lakehouse-run",
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated_at,
        ingested_at=DEFAULT_INGESTED_AT,
        built_at=DEFAULT_BUILT_AT,
        evaluation_time=DEFAULT_EVALUATION_TIME,
        schema_id=DEFAULT_FINANCE_SCHEMA_ID,
        snapshot_id=DEFAULT_SNAPSHOT_ID,
    )
    return live_result.output_path, live_result.report


def initialize_jdbc_catalog(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    compose_path: Path,
    postgres_service: str,
    cwd: Path,
    timeout_seconds: int,
) -> None:
    execute_step(
        command_log,
        runner,
        [
            "docker",
            "compose",
            "-f",
            compose_path.as_posix(),
            "exec",
            "-T",
            postgres_service,
            "psql",
            "-U",
            "iceberg",
            "-d",
            "iceberg",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="initialize_jdbc_catalog",
        input_text=jdbc_catalog_ddl(),
    )


def jdbc_catalog_ddl() -> str:
    return """
CREATE TABLE IF NOT EXISTS iceberg_tables (
    catalog_name VARCHAR(255) NOT NULL,
    table_namespace VARCHAR(255) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    metadata_location VARCHAR(1000),
    previous_metadata_location VARCHAR(1000),
    PRIMARY KEY (catalog_name, table_namespace, table_name)
);
CREATE TABLE IF NOT EXISTS iceberg_namespace_properties (
    catalog_name VARCHAR(255) NOT NULL,
    namespace VARCHAR(255) NOT NULL,
    property_key VARCHAR(255) NOT NULL,
    property_value VARCHAR(1000) NOT NULL,
    PRIMARY KEY (catalog_name, namespace, property_key)
);
"""


def create_insert_sql(
    qualified_table: str,
    catalog: str,
    schema: str,
    warehouse_location: str,
    rows: list[dict[str, Any]],
) -> str:
    return " ".join(
        [
            f"DROP TABLE IF EXISTS {qualified_table}",
            f"; CREATE SCHEMA IF NOT EXISTS {catalog}.{schema} WITH (location='{warehouse_location}')",
            f"; CREATE TABLE {qualified_table} ("
            "reconciliation_status varchar, "
            "expected_amount_cents bigint, "
            "actual_amount_cents bigint, "
            "reconciliation_delta_cents bigint, "
            "variance_points bigint"
            ") WITH (format='PARQUET')",
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


def metadata_count_probe(stdout: str, *, probe_name: str) -> dict[str, Any]:
    count = parse_single_int(stdout)
    return {"passed": count > 0, "name": probe_name, "count": count}


def parse_single_int(stdout: str) -> int:
    for line in stdout.splitlines():
        stripped = line.strip().strip('"')
        if stripped.isdigit():
            return int(stripped)
    return 0


def minio_object_probe(client: Any, *, bucket: str, prefix: str, sse_algorithm: str = DEFAULT_SSE_ALGORITHM) -> dict[str, Any]:
    response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = response.get("Contents", []) if isinstance(response, dict) else []
    all_keys = [item.get("Key") for item in objects if isinstance(item, dict) and isinstance(item.get("Key"), str)]
    keys = [key for key in all_keys if "/_encryption_policy_probe/" not in key]
    data_count = sum(1 for key in keys if "/data/" in key)
    metadata_count = sum(1 for key in keys if "/metadata/" in key)
    object_heads = [object_head_probe(client, bucket=bucket, key=key, sse_algorithm=sse_algorithm) for key in keys]
    encrypted_count = sum(1 for item in object_heads if item.get("encrypted") is True)
    return {
        "passed": bool(keys) and data_count > 0 and metadata_count > 0 and encrypted_count == len(keys),
        "object_count": len(keys),
        "data_object_count": data_count,
        "metadata_object_count": metadata_count,
        "encrypted_object_count": encrypted_count,
        "all_objects_encrypted": bool(keys) and encrypted_count == len(keys),
        "sse_algorithm": sse_algorithm,
        "object_heads": object_heads[:20],
        "sample_keys": keys[:20],
    }


def object_head_probe(client: Any, *, bucket: str, key: str, sse_algorithm: str) -> dict[str, Any]:
    head = client.head_object(Bucket=bucket, Key=key)
    return {
        "key": key,
        "content_length": head.get("ContentLength"),
        "server_side_encryption": head.get("ServerSideEncryption"),
        "encrypted": head.get("ServerSideEncryption") == sse_algorithm,
    }


def failed_trino_iceberg_minio_checks(
    *,
    live_report: dict[str, Any],
    primary_commit: dict[str, Any],
    gold_rows: list[dict[str, Any]],
    query_probe: dict[str, Any],
    expected_probe: list[dict[str, Any]],
    snapshots_probe: dict[str, Any],
    files_probe: dict[str, Any],
    minio_probe: dict[str, Any],
    encryption_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if live_report.get("passed") is not True:
        failed.append({"check": "live_lakehouse_smoke_passed", "passed": live_report.get("passed")})
    if not primary_commit:
        failed.append({"check": "gold_primary_commit_present"})
    if len(gold_rows) != 4:
        failed.append({"check": "gold_row_count", "expected": 4, "actual": len(gold_rows)})
    if query_probe.get("passed") is not True:
        failed.append({"check": "trino_iceberg_query_passed", "reason": query_probe.get("reason")})
    if query_probe.get("result") != expected_probe:
        failed.append(
            {
                "check": "trino_iceberg_query_result_matches_gold_source",
                "expected": expected_probe,
                "actual": query_probe.get("result"),
            }
        )
    if snapshots_probe.get("passed") is not True:
        failed.append({"check": "iceberg_snapshots_metadata_table", "actual": snapshots_probe.get("count", 0)})
    if files_probe.get("passed") is not True:
        failed.append({"check": "iceberg_files_metadata_table", "actual": files_probe.get("count", 0)})
    if minio_probe.get("passed") is not True:
        failed.append(
            {
                "check": "minio_iceberg_data_and_metadata_objects",
                "object_count": minio_probe.get("object_count", 0),
                "data_object_count": minio_probe.get("data_object_count", 0),
                "metadata_object_count": minio_probe.get("metadata_object_count", 0),
                "encrypted_object_count": minio_probe.get("encrypted_object_count", 0),
            }
        )
    if encryption_policy.get("passed") is not True:
        failed.append(
            {
                "check": "object_store_encryption_policy_enforced",
                "unencrypted_put_denied": encryption_policy.get("unencrypted_put_denied"),
                "encrypted_put_allowed": encryption_policy.get("encrypted_put_allowed"),
                "encrypted_head_sse": encryption_policy.get("encrypted_head_sse"),
                "errors": encryption_policy.get("errors", []),
            }
        )
    return failed
