from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import csv
import io
import json
import time

import pyarrow as pa
import pyiceberg
from pyiceberg.catalog import load_catalog

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.event_backbone_smoke import (
    CommandRunner,
    command_failure_message,
    execute_step,
    read_jsonl,
    resolve_compose_path,
    run_command,
    safe_id,
    stable_id,
    topic_exists_error,
    write_jsonl,
)
from enterprise_dp.ingestion_runtime import load_source_registry
from enterprise_dp.object_store_smoke import (
    DEFAULT_ACCESS_KEY,
    DEFAULT_MINIO_SERVICE,
    DEFAULT_SECRET_KEY,
    ensure_bucket,
    s3_client,
)
from enterprise_dp.schema import validate_json_schema
from enterprise_dp.trino_iceberg_minio_smoke import (
    DEFAULT_BUCKET,
    DEFAULT_CATALOG,
    DEFAULT_POSTGRES_SERVICE,
    DEFAULT_SCHEMA,
    DEFAULT_SERVICE,
    DEFAULT_CONTAINER_ENDPOINT_URL,
    initialize_jdbc_catalog,
    metadata_count_probe,
)
from enterprise_dp.trino_sql_smoke import execute_trino_sql, sql_identifier, wait_for_trino


DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_INGESTED_AT = "2026-01-15T09:15:05Z"
DEFAULT_RELEASE_ID = "local-live-bronze-ingestion-smoke"
DEFAULT_SOURCE_ID = "enterprise-commerce-benefit-settled-outbox"
DEFAULT_SOURCE_POSTGRES_SERVICE = "source-postgres"
DEFAULT_REDPANDA_SERVICE = "redpanda"
DEFAULT_CATALOG_NAME = "local_finance_iceberg"
DEFAULT_CATALOG_URI = "postgresql+psycopg://iceberg:iceberg_local_only_change_me@localhost:15432/iceberg"
DEFAULT_ENDPOINT_URL = "http://localhost:19000"
DEFAULT_SCHEMA = "bronze_runtime_smoke"
DEFAULT_TABLE = "events_benefit_settled"
DEFAULT_SCHEMA_ID = "registry:finance.benefit_settled.v1:1"
DEFAULT_REGION = "us-east-1"

TrinoExecutor = Callable[[str, str], Any]


@dataclass(frozen=True)
class LiveBronzeIngestionSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_live_bronze_ingestion_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    compose_file: str | Path | None = None,
    source_postgres_service: str = DEFAULT_SOURCE_POSTGRES_SERVICE,
    redpanda_service: str = DEFAULT_REDPANDA_SERVICE,
    trino_service: str = DEFAULT_SERVICE,
    iceberg_postgres_service: str = DEFAULT_POSTGRES_SERVICE,
    minio_service: str = DEFAULT_MINIO_SERVICE,
    bucket: str = DEFAULT_BUCKET,
    endpoint_url: str = DEFAULT_ENDPOINT_URL,
    access_key: str = DEFAULT_ACCESS_KEY,
    secret_key: str = DEFAULT_SECRET_KEY,
    region_name: str = DEFAULT_REGION,
    catalog: str = DEFAULT_CATALOG,
    catalog_name: str = DEFAULT_CATALOG_NAME,
    catalog_uri: str = DEFAULT_CATALOG_URI,
    schema: str = DEFAULT_SCHEMA,
    table: str = DEFAULT_TABLE,
    source_id: str = DEFAULT_SOURCE_ID,
    release_id: str = DEFAULT_RELEASE_ID,
    environment: str = "local",
    generated_at: str | None = None,
    ingested_at: str | None = None,
    schema_id: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 12,
    wait_interval_seconds: float = 2.0,
    start_runtime: bool = True,
    source_records_override: list[dict[str, Any]] | None = None,
    consumed_records_override: list[dict[str, Any]] | None = None,
    pyiceberg_catalog_override: Any | None = None,
    trino_executor_override: TrinoExecutor | None = None,
    s3_client_override: Any | None = None,
) -> LiveBronzeIngestionSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    ingested = ingested_at or DEFAULT_INGESTED_AT
    resolved_schema_id = schema_id or DEFAULT_SCHEMA_ID
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    safe_catalog = sql_identifier(catalog)
    safe_schema = sql_identifier(schema)
    safe_table = sql_identifier(table)
    warehouse = f"s3://{bucket}/warehouse"
    schema_location = f"{warehouse}/{safe_schema}"
    qualified_table = f"{safe_catalog}.{safe_schema}.{safe_table}"
    source = source_by_id(platform_root, source_id)
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    topic = str(canonical.get("topic") or source_id)
    bronze_target = str(canonical.get("bronzeTarget") or f"bronze.{safe_table}")
    source_path = source_sample_path(platform_root, source)
    source_records = source_records_override or read_jsonl(source_path)
    schema_refs = schema_refs_for_source(source)
    envelope_schema = load_json(platform_root / "contracts" / "event-envelope.v1.schema.json")
    payload_schema = load_payload_schema(platform_root, topic)
    outbox_schema = f"dp_live_bronze_{safe_id(release_id).replace('.', '_')}"
    runtime_topic = f"dp.local.live.bronze.{safe_id(release_id)}.{safe_id(generated)}"
    approved_path = target_dir / "bronze-sink" / "approved.jsonl"
    quarantine_path = target_dir / "bronze-sink" / "quarantine.jsonl"
    offset_ledger_path = target_dir / "bronze-sink" / "offset-ledger.json"
    consumed_path = target_dir / "event-backbone" / "consumed-with-offsets.jsonl"
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    object_store_probe: dict[str, Any] = {"passed": False}
    bronze_probe: dict[str, Any] = {"passed": False}
    restart_resume_probe: dict[str, Any] = {"passed": False}
    dlt_probe: dict[str, Any] = {"passed": False}
    consumed_records: list[dict[str, Any]] = []

    try:
        if consumed_records_override is None:
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
                        source_postgres_service,
                        redpanda_service,
                        minio_service,
                        iceberg_postgres_service,
                        trino_service,
                    ],
                    cwd=platform_root,
                    timeout_seconds=command_timeout_seconds,
                    step="compose_up_live_bronze_runtime",
                )
            initialize_jdbc_catalog(
                command_log,
                runner,
                compose_path=compose_path,
                postgres_service=iceberg_postgres_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
            )
            wait_for_source_postgres(
                command_log,
                runner,
                compose_path=compose_path,
                source_postgres_service=source_postgres_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
            )
            execute_step(
                command_log,
                runner,
                source_postgres_psql_args(compose_path, source_postgres_service),
                input_text=outbox_setup_sql(
                    outbox_schema,
                    source_id=source_id,
                    topic=topic,
                    records=source_records,
                    invalid_record=invalid_schema_record(source_records[0]) if source_records else None,
                    duplicate_record=source_records[0] if source_records else None,
                ),
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="source_postgres_seed_outbox",
            )
            outbox_query = execute_step(
                command_log,
                runner,
                source_postgres_psql_args(
                    compose_path,
                    source_postgres_service,
                    "-At",
                    "-F",
                    "\t",
                    "-c",
                    f"SELECT outbox_id, payload::text FROM {outbox_schema}.outbox_events ORDER BY outbox_id;",
                ),
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="source_postgres_poll_outbox_rows",
            )
            outbox_records = parse_outbox_query_rows(outbox_query.stdout)
            consumed_records = redpanda_round_trip_with_offsets(
                command_log,
                runner,
                compose_path=compose_path,
                service=redpanda_service,
                topic=runtime_topic,
                records=outbox_records,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
            )
        else:
            consumed_records = consumed_records_override
        write_jsonl(consumed_path, consumed_records)

        if pyiceberg_catalog_override is None:
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
                service=trino_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                attempts=wait_attempts,
                interval_seconds=wait_interval_seconds,
            )
            catalog_client = load_catalog(
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
        else:
            object_store_probe = {"passed": True, "mode": "test_catalog_override"}
            catalog_client = pyiceberg_catalog_override

        def trino_executor(sql: str, step: str) -> Any:
            if trino_executor_override is not None:
                return trino_executor_override(sql, step)
            return execute_trino_sql(
                command_log,
                runner,
                compose_path=compose_path,
                service=trino_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step=step,
                sql=sql,
            )

        trino_executor(
            create_bronze_table_sql(
                qualified_table,
                catalog=safe_catalog,
                schema=safe_schema,
                schema_location=schema_location,
            ),
            "create_live_bronze_iceberg_table",
        )
        bronze_probe = write_bronze_iceberg_sink(
            catalog_client,
            trino_executor,
            consumed_records=consumed_records,
            envelope_schema=envelope_schema,
            payload_schema=payload_schema,
            source_id=source_id,
            topic=topic,
            schema_id=resolved_schema_id,
            ingested_at=ingested,
            table_identifier=(safe_schema, safe_table),
            qualified_table=qualified_table,
            approved_path=approved_path,
            quarantine_path=quarantine_path,
            offset_ledger_path=offset_ledger_path,
        )
        restart_resume_probe = simulate_restart_resume(bronze_probe)
        dlt_probe = {
            "passed": bronze_probe.get("quarantine_row_count", 0) >= 1,
            "quarantine_path": quarantine_path.as_posix(),
            "quarantine_hash": hash_file(quarantine_path) if quarantine_path.is_file() else None,
            "quarantine_row_count": bronze_probe.get("quarantine_row_count", 0),
        }
    except Exception as exc:
        failed_checks.append({"check": "live_bronze_ingestion_runtime", "message": f"{type(exc).__name__}: {exc}"})

    failed_checks.extend(
        failed_live_bronze_checks(
            object_store_probe=object_store_probe,
            bronze_probe=bronze_probe,
            restart_resume_probe=restart_resume_probe,
            dlt_probe=dlt_probe,
            source_record_count=len(source_records),
        )
    )
    report = build_live_bronze_ingestion_smoke_report(
        root=platform_root,
        output_dir=target_dir,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        source=source,
        source_id=source_id,
        source_path=source_path,
        source_record_count=len(source_records),
        topic=topic,
        runtime_topic=runtime_topic,
        bronze_target=bronze_target,
        schema_refs=schema_refs,
        schema_id=resolved_schema_id,
        qualified_table=qualified_table,
        consumed_path=consumed_path,
        approved_path=approved_path,
        quarantine_path=quarantine_path,
        offset_ledger_path=offset_ledger_path,
        compose_path=compose_path,
        source_postgres_service=source_postgres_service,
        redpanda_service=redpanda_service,
        trino_service=trino_service,
        iceberg_postgres_service=iceberg_postgres_service,
        bucket=bucket,
        endpoint_url=endpoint_url,
        catalog_uri=catalog_uri,
        warehouse=warehouse,
        object_store_probe=object_store_probe,
        bronze_probe=bronze_probe,
        restart_resume_probe=restart_resume_probe,
        dlt_probe=dlt_probe,
        command_log=command_log,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return LiveBronzeIngestionSmokeResult(output_path=target, report=report)


def source_by_id(root: Path, source_id: str) -> dict[str, Any]:
    for source in load_source_registry(root):
        if source.get("sourceId") == source_id:
            return source
    raise ValueError(f"source registry entry not found: {source_id}")


def source_sample_path(root: Path, source: dict[str, Any]) -> Path:
    evidence = source.get("evidence") if isinstance(source.get("evidence"), dict) else {}
    sample = evidence.get("localSamplePath")
    if not isinstance(sample, str) or not sample:
        raise ValueError(f"{source.get('sourceId')}: evidence.localSamplePath is required")
    path = Path(sample)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def load_payload_schema(root: Path, topic: str) -> dict[str, Any]:
    path = root / "contracts" / "events" / f"{topic}.schema.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return load_json(path)


def schema_refs_for_source(source: dict[str, Any]) -> dict[str, Any]:
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    return {
        "topic": canonical.get("topic"),
        "schema_subject": canonical.get("schemaSubject"),
        "compatibility": canonical.get("compatibility"),
        "bronze_target": canonical.get("bronzeTarget"),
    }


def source_postgres_psql_args(compose_path: Path, source_postgres_service: str, *extra: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        compose_path.as_posix(),
        "exec",
        "-T",
        source_postgres_service,
        "psql",
        "-U",
        "dp_source",
        "-d",
        "source_runtime",
        "-v",
        "ON_ERROR_STOP=1",
        *extra,
    ]


def wait_for_source_postgres(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    compose_path: Path,
    source_postgres_service: str,
    cwd: Path,
    timeout_seconds: int,
    attempts: int = 12,
    interval_seconds: float = 2.0,
) -> None:
    last_result = None
    for attempt in range(attempts):
        result = execute_step(
            command_log,
            runner,
            [
                "docker",
                "compose",
                "-f",
                compose_path.as_posix(),
                "exec",
                "-T",
                source_postgres_service,
                "pg_isready",
                "-U",
                "dp_source",
                "-d",
                "source_runtime",
            ],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step=f"source_postgres_wait_ready_{attempt + 1}",
            raise_on_error=False,
        )
        last_result = result
        if result.returncode == 0:
            return
        time.sleep(interval_seconds)
    raise RuntimeError(command_failure_message("source_postgres_wait_ready", last_result))


def outbox_setup_sql(
    schema: str,
    *,
    source_id: str,
    topic: str,
    records: list[dict[str, Any]],
    invalid_record: dict[str, Any] | None,
    duplicate_record: dict[str, Any] | None,
) -> str:
    statements = [
        f"DROP SCHEMA IF EXISTS {schema} CASCADE;",
        f"CREATE SCHEMA {schema};",
        f"""
CREATE TABLE {schema}.outbox_events (
  outbox_id BIGSERIAL PRIMARY KEY,
  source_id TEXT NOT NULL,
  topic TEXT NOT NULL,
  event_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  published_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""".strip(),
    ]
    outbox_records = list(records)
    if duplicate_record is not None:
        outbox_records.append(duplicate_record)
    if invalid_record is not None:
        outbox_records.append(invalid_record)
    for record in outbox_records:
        event_key = str(record.get("eventId") or stable_id(record))
        statements.append(
            "INSERT INTO "
            f"{schema}.outbox_events (source_id, topic, event_key, payload, published_at) VALUES "
            f"($${source_id}$$, $${topic}$$, $${event_key}$$, $outbox${canonical_json(record)}$outbox$::jsonb, now());"
        )
    return "\n".join(statements) + "\n"


def invalid_schema_record(record: dict[str, Any]) -> dict[str, Any]:
    invalid = json.loads(canonical_json(record))
    invalid["eventId"] = "81000000-0000-4000-8000-999999999999"
    invalid["correlationId"] = "finance-recon-invalid"
    payload = invalid.get("payload") if isinstance(invalid.get("payload"), dict) else {}
    payload.pop("orderId", None)
    invalid["payload"] = payload
    return invalid


def parse_outbox_query_rows(stdout: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            outbox_id, payload = stripped.split("\t", 1)
            row = json.loads(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"outbox query row {line_number} is invalid") from exc
        if not isinstance(row, dict):
            raise RuntimeError(f"outbox query row {line_number} payload must be an object")
        row.setdefault("headers", {})
        if isinstance(row["headers"], dict):
            row["headers"]["sourceOutboxId"] = int(outbox_id)
        rows.append(row)
    return rows


def redpanda_round_trip_with_offsets(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    compose_path: Path,
    service: str,
    topic: str,
    records: list[dict[str, Any]],
    cwd: Path,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    topic_create_args = [
        "docker",
        "compose",
        "-f",
        compose_path.as_posix(),
        "exec",
        "-T",
        service,
        "rpk",
        "topic",
        "create",
        topic,
    ]
    topic_create = execute_step(
        command_log,
        runner,
        topic_create_args,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="live_bronze_topic_create",
        raise_on_error=False,
    )
    if topic_create.returncode != 0 and topic_exists_error(topic_create):
        execute_step(
            command_log,
            runner,
            ["docker", "compose", "-f", compose_path.as_posix(), "exec", "-T", service, "rpk", "topic", "delete", topic],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step="live_bronze_topic_delete_existing",
        )
        execute_step(
            command_log,
            runner,
            topic_create_args,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step="live_bronze_topic_create_retry",
        )
    elif topic_create.returncode != 0:
        raise RuntimeError(command_failure_message("live_bronze_topic_create", topic_create))
    execute_step(
        command_log,
        runner,
        ["docker", "compose", "-f", compose_path.as_posix(), "exec", "-T", service, "rpk", "topic", "produce", topic],
        input_text="".join(f"{canonical_json(record)}\n" for record in records),
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="live_bronze_topic_produce",
    )
    consumed = execute_step(
        command_log,
        runner,
        [
            "docker",
            "compose",
            "-f",
            compose_path.as_posix(),
            "exec",
            "-T",
            service,
            "rpk",
            "topic",
            "consume",
            topic,
            "--offset",
            "start",
            "--num",
            str(len(records)),
            "--format",
            "%p %o %v\n",
        ],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="live_bronze_topic_consume_with_offsets",
    )
    return parse_consumed_with_offsets(consumed.stdout)


def parse_consumed_with_offsets(stdout: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            partition_text, offset_text, payload_text = stripped.split(" ", 2)
            payload = json.loads(payload_text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"consumed row {line_number} is invalid: {stripped!r}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"consumed row {line_number} payload must be an object")
        rows.append({"partition": int(partition_text), "offset": int(offset_text), "record": payload})
    return rows


def create_bronze_table_sql(
    qualified_table: str,
    *,
    catalog: str,
    schema: str,
    schema_location: str,
) -> str:
    return " ".join(
        [
            f"DROP TABLE IF EXISTS {qualified_table}",
            f"; CREATE SCHEMA IF NOT EXISTS {catalog}.{schema} WITH (location='{schema_location}')",
            f"; CREATE TABLE {qualified_table} ("
            "event_id varchar, source_id varchar, topic varchar, partition_id integer, source_offset bigint, "
            "kafka_offset bigint, payload_json varchar, payload_hash varchar, schema_id varchar, ingested_at varchar"
            ") WITH (format='PARQUET')",
        ]
    )


def write_bronze_iceberg_sink(
    catalog_client: Any,
    trino_executor: TrinoExecutor,
    *,
    consumed_records: list[dict[str, Any]],
    envelope_schema: dict[str, Any],
    payload_schema: dict[str, Any],
    source_id: str,
    topic: str,
    schema_id: str,
    ingested_at: str,
    table_identifier: tuple[str, str],
    qualified_table: str,
    approved_path: Path,
    quarantine_path: Path,
    offset_ledger_path: Path,
) -> dict[str, Any]:
    iceberg_table = catalog_client.load_table(table_identifier)
    snapshot_count_before = len(iceberg_table.snapshots())
    metadata_before = getattr(iceberg_table, "metadata_location", None)
    seen_event_ids: set[str] = set()
    approved_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    offsets: list[int] = []
    for item in consumed_records:
        record = item.get("record") if isinstance(item.get("record"), dict) else {}
        partition = int(item.get("partition", 0))
        offset = int(item.get("offset", 0))
        offsets.append(offset)
        validation_errors = list(validate_json_schema(record, envelope_schema))
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else None
        if payload is None:
            validation_errors.append("$.payload must be object")
        else:
            validation_errors.extend(validate_json_schema(payload, payload_schema, path="$.payload"))
        event_id = str(record.get("eventId") or "")
        if validation_errors:
            quarantine_rows.append(
                {
                    "source_id": source_id,
                    "topic": topic,
                    "partition": partition,
                    "offset": offset,
                    "event_id": event_id,
                    "errors": validation_errors,
                    "payload_hash": stable_id("payload", record),
                }
            )
            continue
        if event_id in seen_event_ids:
            duplicates.append(
                {
                    "source_id": source_id,
                    "topic": topic,
                    "partition": partition,
                    "offset": offset,
                    "event_id": event_id,
                    "payload_hash": stable_id("payload", record),
                }
            )
            continue
        seen_event_ids.add(event_id)
        approved_rows.append(
            {
                "event_id": event_id,
                "source_id": source_id,
                "topic": topic,
                "partition_id": partition,
                "source_offset": int(record.get("sourceOffset") or offset),
                "kafka_offset": offset,
                "payload_json": canonical_json(record),
                "payload_hash": stable_id("payload", record),
                "schema_id": schema_id,
                "ingested_at": ingested_at,
            }
        )
    write_jsonl(approved_path, approved_rows)
    write_jsonl(quarantine_path, quarantine_rows)
    if approved_rows:
        iceberg_table.append(bronze_arrow_table(approved_rows))
    reloaded = catalog_client.load_table(table_identifier)
    rows_after = reloaded.scan().to_arrow().to_pylist()
    snapshot_count_after = len(reloaded.snapshots())
    metadata_after = getattr(reloaded, "metadata_location", None)
    trino_count = parse_single_int(command_stdout(trino_executor(f"SELECT COUNT(*) FROM {qualified_table}", "query_live_bronze_row_count")))
    snapshots_probe = metadata_count_probe(
        command_stdout(trino_executor(f'SELECT COUNT(*) FROM {qualified_table.rsplit(".", 1)[0]}."{table_identifier[1]}$snapshots"', "query_live_bronze_snapshots")),
        probe_name="live_bronze_snapshots",
    )
    files_probe = metadata_count_probe(
        command_stdout(trino_executor(f'SELECT COUNT(*) FROM {qualified_table.rsplit(".", 1)[0]}."{table_identifier[1]}$files"', "query_live_bronze_files")),
        probe_name="live_bronze_files",
    )
    offset_ledger = {
        "source_id": source_id,
        "topic": topic,
        "partition": 0,
        "min_offset": min(offsets) if offsets else None,
        "max_offset": max(offsets) if offsets else None,
        "consumed_record_count": len(consumed_records),
        "approved_row_count": len(approved_rows),
        "duplicate_skipped_count": len(duplicates),
        "quarantine_row_count": len(quarantine_rows),
        "committed_snapshot_count": snapshot_count_after,
        "latest_metadata_location": metadata_after,
    }
    offset_ledger_path.parent.mkdir(parents=True, exist_ok=True)
    offset_ledger_path.write_text(f"{canonical_json(offset_ledger)}\n", encoding="utf-8")
    return {
        "passed": (
            len(approved_rows) > 0
            and len(rows_after) == len(approved_rows)
            and trino_count == len(approved_rows)
            and snapshot_count_after > snapshot_count_before
            and len(duplicates) >= 1
            and len(quarantine_rows) >= 1
            and snapshots_probe.get("passed") is True
            and files_probe.get("passed") is True
        ),
        "approved_row_count": len(approved_rows),
        "quarantine_row_count": len(quarantine_rows),
        "duplicate_skipped_count": len(duplicates),
        "consumed_record_count": len(consumed_records),
        "source_offset_min": min(offsets) if offsets else None,
        "source_offset_max": max(offsets) if offsets else None,
        "snapshot_count_before": snapshot_count_before,
        "snapshot_count_after": snapshot_count_after,
        "metadata_location_before": metadata_before,
        "metadata_location_after": metadata_after,
        "metadata_location_changed": metadata_before != metadata_after,
        "trino_row_count": trino_count,
        "pyiceberg_row_count": len(rows_after),
        "snapshots_probe": snapshots_probe,
        "files_probe": files_probe,
        "offset_ledger": offset_ledger,
        "duplicate_events": duplicates,
    }


def bronze_arrow_table(rows: list[dict[str, Any]]) -> pa.Table:
    return pa.table(
        {
            "event_id": [str(row["event_id"]) for row in rows],
            "source_id": [str(row["source_id"]) for row in rows],
            "topic": [str(row["topic"]) for row in rows],
            "partition_id": [int(row["partition_id"]) for row in rows],
            "source_offset": [int(row["source_offset"]) for row in rows],
            "kafka_offset": [int(row["kafka_offset"]) for row in rows],
            "payload_json": [str(row["payload_json"]) for row in rows],
            "payload_hash": [str(row["payload_hash"]) for row in rows],
            "schema_id": [str(row["schema_id"]) for row in rows],
            "ingested_at": [str(row["ingested_at"]) for row in rows],
        },
        schema=pa.schema(
            [
                pa.field("event_id", pa.string(), nullable=False),
                pa.field("source_id", pa.string(), nullable=False),
                pa.field("topic", pa.string(), nullable=False),
                pa.field("partition_id", pa.int32(), nullable=False),
                pa.field("source_offset", pa.int64(), nullable=False),
                pa.field("kafka_offset", pa.int64(), nullable=False),
                pa.field("payload_json", pa.string(), nullable=False),
                pa.field("payload_hash", pa.string(), nullable=False),
                pa.field("schema_id", pa.string(), nullable=False),
                pa.field("ingested_at", pa.string(), nullable=False),
            ]
        ),
    )


def simulate_restart_resume(bronze_probe: dict[str, Any]) -> dict[str, Any]:
    ledger = bronze_probe.get("offset_ledger") if isinstance(bronze_probe.get("offset_ledger"), dict) else {}
    return {
        "passed": bronze_probe.get("passed") is True and ledger.get("max_offset") is not None,
        "mode": "offset_ledger_resume_probe",
        "resume_from_offset": int(ledger.get("max_offset", -1)) + 1 if ledger.get("max_offset") is not None else None,
        "committed_offset": ledger.get("max_offset"),
        "duplicate_skipped_count": bronze_probe.get("duplicate_skipped_count", 0),
        "idempotency_key": "eventId",
    }


def failed_live_bronze_checks(
    *,
    object_store_probe: dict[str, Any],
    bronze_probe: dict[str, Any],
    restart_resume_probe: dict[str, Any],
    dlt_probe: dict[str, Any],
    source_record_count: int,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if object_store_probe.get("passed") is not True:
        failed.append({"check": "object_store_bucket_ready", "probe": object_store_probe})
    if bronze_probe.get("passed") is not True:
        failed.append({"check": "live_bronze_iceberg_sink_passed", "probe": bronze_probe})
    if bronze_probe.get("approved_row_count") != source_record_count:
        failed.append(
            {
                "check": "approved_source_count_matches_after_dedup",
                "expected": source_record_count,
                "actual": bronze_probe.get("approved_row_count"),
            }
        )
    if restart_resume_probe.get("passed") is not True:
        failed.append({"check": "sink_restart_resume_offset_ledger", "probe": restart_resume_probe})
    if dlt_probe.get("passed") is not True:
        failed.append({"check": "invalid_schema_quarantine_or_dlt", "probe": dlt_probe})
    return failed


def build_live_bronze_ingestion_smoke_report(
    *,
    root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    source: dict[str, Any],
    source_id: str,
    source_path: Path,
    source_record_count: int,
    topic: str,
    runtime_topic: str,
    bronze_target: str,
    schema_refs: dict[str, Any],
    schema_id: str,
    qualified_table: str,
    consumed_path: Path,
    approved_path: Path,
    quarantine_path: Path,
    offset_ledger_path: Path,
    compose_path: Path,
    source_postgres_service: str,
    redpanda_service: str,
    trino_service: str,
    iceberg_postgres_service: str,
    bucket: str,
    endpoint_url: str,
    catalog_uri: str,
    warehouse: str,
    object_store_probe: dict[str, Any],
    bronze_probe: dict[str, Any],
    restart_resume_probe: dict[str, Any],
    dlt_probe: dict[str, Any],
    command_log: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = {
        "source_id": source_id,
        "topic": topic,
        "runtime_topic": runtime_topic,
        "bronze_target": bronze_target,
        "iceberg_table": qualified_table,
        "source_record_count": source_record_count,
        "consumed_record_count": bronze_probe.get("consumed_record_count", 0),
        "approved_row_count": bronze_probe.get("approved_row_count", 0),
        "duplicate_skipped_count": bronze_probe.get("duplicate_skipped_count", 0),
        "quarantine_row_count": bronze_probe.get("quarantine_row_count", 0),
        "trino_row_count": bronze_probe.get("trino_row_count", 0),
        "pyiceberg_row_count": bronze_probe.get("pyiceberg_row_count", 0),
        "snapshot_count_before": bronze_probe.get("snapshot_count_before", 0),
        "snapshot_count_after": bronze_probe.get("snapshot_count_after", 0),
        "metadata_location_changed": bronze_probe.get("metadata_location_changed"),
        "restart_resume_passed": restart_resume_probe.get("passed") is True,
        "dlt_quarantine_passed": dlt_probe.get("passed") is True,
        "live_bronze_iceberg_sink_passed": bronze_probe.get("passed") is True,
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    return {
        "artifact_type": "live_bronze_ingestion_runtime_report.v1",
        "report_version": 1,
        "capability_ids": ["event-cdc-ingestion-runtime", "bronze-lakehouse-evidence", "source-onboarding"],
        "report_id": stable_id("live-bronze-ingestion-smoke", environment, release_id, source_id),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_source_postgres_outbox_redpanda_to_bronze_iceberg_minio",
            "covered": [
                "source_postgres_transactional_outbox_seeded",
                "outbox_rows_published_to_redpanda_topic",
                "redpanda_consume_with_partition_offset",
                "event_envelope_and_payload_schema_validation",
                "invalid_schema_record_quarantined",
                "duplicate_event_idempotently_skipped",
                "bronze_iceberg_table_written_on_minio_jdbc_catalog",
                "iceberg_snapshot_and_files_metadata_queried",
                "offset_ledger_resume_point_recorded",
            ],
            "not_covered": [
                "production_kafka_connect_or_debezium_worker",
                "production_connector_ha",
                "production_connector_secret_rotation",
                "production_backpressure_runtime_policy",
                "multi_source_p0_bronze_coverage",
                "production_catalog_ha",
            ],
        },
        "source": {
            "source_id": source_id,
            "product": source.get("product"),
            "domain": source.get("domain"),
            "source_type": source.get("source", {}).get("type") if isinstance(source.get("source"), dict) else None,
            "sample": {
                "path": source_path.as_posix(),
                "hash": hash_file(source_path),
                "row_count": source_record_count,
            },
        },
        "schema_registry_binding": {"schema_id": schema_id, **schema_refs},
        "runtime": {
            "compose_file": compose_path.as_posix(),
            "source_postgres_service": source_postgres_service,
            "redpanda_service": redpanda_service,
            "trino_service": trino_service,
            "iceberg_postgres_service": iceberg_postgres_service,
            "object_store": {
                "provider": "minio",
                "endpoint_url": endpoint_url,
                "container_endpoint_url": DEFAULT_CONTAINER_ENDPOINT_URL,
                "bucket": bucket,
                "warehouse": warehouse,
            },
            "catalog_uri": redact_catalog_uri(catalog_uri),
            "pyiceberg_version": pyiceberg.__version__,
            "root": root.as_posix(),
            "output_dir": output_dir.as_posix(),
        },
        "event_backbone": {
            "topic": runtime_topic,
            "consumed_path": consumed_path.as_posix(),
            "consumed_hash": hash_file(consumed_path) if consumed_path.is_file() else None,
        },
        "bronze_sink": {
            "iceberg_table": qualified_table,
            "approved_path": approved_path.as_posix(),
            "approved_hash": hash_file(approved_path) if approved_path.is_file() else None,
            "quarantine_path": quarantine_path.as_posix(),
            "quarantine_hash": hash_file(quarantine_path) if quarantine_path.is_file() else None,
            "offset_ledger_path": offset_ledger_path.as_posix(),
            "offset_ledger_hash": hash_file(offset_ledger_path) if offset_ledger_path.is_file() else None,
        },
        "object_store_probe": object_store_probe,
        "bronze_probe": bronze_probe,
        "restart_resume_probe": restart_resume_probe,
        "dlt_probe": dlt_probe,
        "commands": command_log,
        "summary": summary,
        "passed": not failed_checks,
    }


def command_stdout(result: Any) -> str:
    return result.stdout if hasattr(result, "stdout") else str(result or "")


def parse_single_int(stdout: str) -> int:
    for row in csv.reader(io.StringIO(stdout)):
        for cell in row:
            stripped = cell.strip().strip('"')
            if stripped.isdigit():
                return int(stripped)
    return 0


def redact_catalog_uri(uri: str) -> str:
    if "@" not in uri or "://" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    return f"{scheme}://***:***@{rest.split('@', 1)[1]}"
