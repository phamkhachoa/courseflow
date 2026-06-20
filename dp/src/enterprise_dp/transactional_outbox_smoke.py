from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.event_backbone_smoke import (
    CommandRunner,
    execute_step,
    read_jsonl,
    resolve_compose_path,
    round_trip_topic,
    run_command,
    safe_id,
    stable_id,
    write_jsonl,
)
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.ingestion_runtime import load_source_registry


DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_INGESTED_AT = "2026-01-15T09:15:05Z"
DEFAULT_RELEASE_ID = "local-transactional-outbox-smoke"
DEFAULT_SOURCE_ID = "enterprise-commerce-benefit-settled-outbox"
DEFAULT_POSTGRES_SERVICE = "iceberg-postgres"
DEFAULT_REDPANDA_SERVICE = "redpanda"


@dataclass(frozen=True)
class TransactionalOutboxSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_transactional_outbox_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    compose_file: str | Path | None = None,
    postgres_service: str = DEFAULT_POSTGRES_SERVICE,
    redpanda_service: str = DEFAULT_REDPANDA_SERVICE,
    source_id: str = DEFAULT_SOURCE_ID,
    release_id: str = DEFAULT_RELEASE_ID,
    environment: str = "local",
    generated_at: str | None = None,
    ingested_at: str | None = None,
    schema_id: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    start_runtime: bool = True,
) -> TransactionalOutboxSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    ingested = ingested_at or DEFAULT_INGESTED_AT
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    source = source_by_id(platform_root, source_id)
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    topic = str(canonical.get("topic") or "")
    bronze_target = str(canonical.get("bronzeTarget") or "")
    sample_path = source_sample_path(platform_root, source)
    source_records = read_jsonl(sample_path)
    outbox_schema = f"dp_outbox_smoke_{safe_id(release_id).replace('.', '_')}"
    outbox_table = f"{outbox_schema}.outbox_events"
    connector_output_path = target_dir / "connector" / "outbox-connector-output.jsonl"
    consumed_path = target_dir / "event-backbone" / "outbox-consumed.jsonl"
    bronze_dir = target_dir / "bronze-ingestion"
    bronze_manifest: dict[str, Any] | None = None
    connector_records: list[dict[str, Any]] = []
    consumed_records: list[dict[str, Any]] = []

    try:
        if start_runtime:
            execute_step(
                command_log,
                runner,
                ["docker", "compose", "-f", compose_path.as_posix(), "up", "-d", postgres_service, redpanda_service],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="compose_up_postgres_redpanda",
            )
        execute_step(
            command_log,
            runner,
            postgres_psql_args(compose_path, postgres_service),
            input_text=outbox_setup_sql(outbox_schema, source_id=source_id, topic=topic, records=source_records),
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="postgres_seed_transactional_outbox",
        )
        outbox_query = execute_step(
            command_log,
            runner,
            postgres_psql_args(
                compose_path,
                postgres_service,
                "-At",
                "-F",
                "\t",
                "-c",
                f"SELECT outbox_id, payload::text FROM {outbox_table} ORDER BY outbox_id;",
            ),
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="connector_poll_outbox_rows",
        )
        connector_records = parse_outbox_query_rows(outbox_query.stdout)
        write_jsonl(connector_output_path, connector_records)
        consumed_records = round_trip_topic(
            command_log,
            runner,
            compose_path=compose_path,
            service=redpanda_service,
            topic=outbox_topic(release_id, generated),
            records=connector_records,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step_prefix="transactional_outbox",
        )
        write_jsonl(consumed_path, consumed_records)
        bronze = run_bronze_ingestion(
            platform_root,
            topic,
            consumed_path,
            bronze_dir,
            ingested_at=ingested,
            ingest_run_id=f"transactional-outbox-{safe_id(release_id)}",
            schema_id=schema_id,
            source_system=str(source.get("product") or source_id),
        )
        bronze_manifest = bronze.manifest
    except RuntimeError as exc:
        failed_checks.append({"check": "transactional_outbox_smoke_command", "message": str(exc)})

    failed_checks.extend(
        failed_transactional_outbox_checks(
            source_records=source_records,
            connector_records=connector_records,
            consumed_records=consumed_records,
            bronze_manifest=bronze_manifest,
        )
    )
    report = build_transactional_outbox_smoke_report(
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        source=source,
        topic=topic,
        bronze_target=bronze_target,
        sample_path=sample_path,
        outbox_table=outbox_table,
        connector_output_path=connector_output_path,
        consumed_path=consumed_path,
        bronze_manifest=bronze_manifest,
        command_log=command_log,
        source_records=source_records,
        connector_records=connector_records,
        consumed_records=consumed_records,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return TransactionalOutboxSmokeResult(output_path=target, report=report)


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


def postgres_psql_args(compose_path: Path, postgres_service: str, *extra: str) -> list[str]:
    return [
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
        *extra,
    ]


def outbox_setup_sql(schema: str, *, source_id: str, topic: str, records: list[dict[str, Any]]) -> str:
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
    for record in records:
        event_key = str(record.get("eventId") or stable_id(record))
        statements.append(
            "INSERT INTO "
            f"{schema}.outbox_events (source_id, topic, event_key, payload, published_at) VALUES "
            f"($${source_id}$$, $${topic}$$, $${event_key}$$, $outbox${canonical_json(record)}$outbox$::jsonb, now());"
        )
    return "\n".join(statements) + "\n"


def parse_outbox_query_rows(stdout: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            _outbox_id, payload = stripped.split("\t", 1)
            row = load_json_payload(payload)
        except ValueError as exc:
            raise RuntimeError(f"outbox query row {line_number} is invalid") from exc
        rows.append(row)
    return rows


def load_json_payload(payload: str) -> dict[str, Any]:
    import json

    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("outbox payload must be a JSON object")
    return value


def outbox_topic(release_id: str, generated_at: str) -> str:
    return f"dp.local.transactional.outbox.{safe_id(release_id)}.{safe_id(generated_at)}"


def failed_transactional_outbox_checks(
    *,
    source_records: list[dict[str, Any]],
    connector_records: list[dict[str, Any]],
    consumed_records: list[dict[str, Any]],
    bronze_manifest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if sorted(canonical_json(record) for record in source_records) != sorted(canonical_json(record) for record in connector_records):
        failed.append(
            {
                "check": "transactional_outbox_connector_records_match_source",
                "source_record_count": len(source_records),
                "connector_record_count": len(connector_records),
            }
        )
    if sorted(canonical_json(record) for record in connector_records) != sorted(canonical_json(record) for record in consumed_records):
        failed.append(
            {
                "check": "transactional_outbox_redpanda_records_match_connector",
                "connector_record_count": len(connector_records),
                "consumed_record_count": len(consumed_records),
            }
        )
    if not isinstance(bronze_manifest, dict):
        failed.append({"check": "transactional_outbox_bronze_manifest_written", "passed": False})
    else:
        approved = bronze_manifest.get("approved") if isinstance(bronze_manifest.get("approved"), dict) else {}
        quarantine = bronze_manifest.get("quarantine") if isinstance(bronze_manifest.get("quarantine"), dict) else {}
        if bronze_manifest.get("quality_passed") is not True:
            failed.append({"check": "transactional_outbox_bronze_quality_passed", "manifest": bronze_manifest})
        if approved.get("new_row_count") != len(source_records):
            failed.append(
                {
                    "check": "transactional_outbox_bronze_approved_count_matches",
                    "expected": len(source_records),
                    "actual": approved.get("new_row_count"),
                }
            )
        if quarantine.get("row_count") != 0:
            failed.append({"check": "transactional_outbox_bronze_quarantine_empty", "actual": quarantine.get("row_count")})
    return failed


def build_transactional_outbox_smoke_report(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    source: dict[str, Any],
    topic: str,
    bronze_target: str,
    sample_path: Path,
    outbox_table: str,
    connector_output_path: Path,
    consumed_path: Path,
    bronze_manifest: dict[str, Any] | None,
    command_log: list[dict[str, Any]],
    source_records: list[dict[str, Any]],
    connector_records: list[dict[str, Any]],
    consumed_records: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    source_type = source.get("source", {}).get("type") if isinstance(source.get("source"), dict) else None
    approved = bronze_manifest.get("approved") if isinstance(bronze_manifest, dict) and isinstance(bronze_manifest.get("approved"), dict) else {}
    quarantine = (
        bronze_manifest.get("quarantine")
        if isinstance(bronze_manifest, dict) and isinstance(bronze_manifest.get("quarantine"), dict)
        else {}
    )
    report = {
        "artifact_type": "transactional_outbox_smoke_report.v1",
        "report_version": 1,
        "capability_id": "event-cdc-ingestion-runtime",
        "report_id": f"transactional-outbox-smoke:{environment}:{release_id}",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_postgres_transactional_outbox_to_redpanda_to_bronze",
            "covered": [
                "postgres_transactional_outbox_table_seeded",
                "local_connector_poll_reads_ordered_outbox_rows",
                "connector_records_published_to_redpanda",
                "redpanda_records_consumed_for_bronze",
                "bronze_ingestion_approves_connector_records",
                "source_offsets_preserved_in_bronze_manifest",
            ],
            "not_covered": [
                "production_debezium_connector_runtime",
                "production_connector_ha",
                "production_outbox_relay_deployment",
                "production_connector_secret_rotation",
            ],
        },
        "source": {
            "source_id": source.get("sourceId"),
            "source_type": source_type,
            "product": source.get("product"),
            "domain": source.get("domain"),
            "topic": topic,
            "bronze_target": bronze_target,
            "sample": {
                "path": sample_path.as_posix(),
                "content_hash": hash_file(sample_path),
                "row_count": len(source_records),
            },
        },
        "outbox": {
            "table": outbox_table,
            "row_count": len(connector_records),
        },
        "connector_output": {
            "path": connector_output_path.as_posix(),
            "content_hash": hash_file(connector_output_path) if connector_output_path.is_file() else None,
            "row_count": len(connector_records),
        },
        "event_backbone": {
            "topic": outbox_topic(release_id, generated_at),
            "consumed_path": consumed_path.as_posix(),
            "content_hash": hash_file(consumed_path) if consumed_path.is_file() else None,
            "consumed_record_count": len(consumed_records),
        },
        "bronze_ingestion": {
            "manifest": bronze_manifest,
        },
        "commands": command_log,
        "summary": {
            "transactional_outbox_to_bronze_passed": not failed_checks,
            "source_type": source_type,
            "outbox_row_count": len(connector_records),
            "connector_record_count": len(connector_records),
            "consumed_record_count": len(consumed_records),
            "bronze_target": bronze_target,
            "bronze_approved_new_row_count": approved.get("new_row_count"),
            "bronze_quarantine_row_count": quarantine.get("row_count"),
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    return report
