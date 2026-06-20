from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.contracts import load_yaml
from enterprise_dp.data_plane_smoke import (
    DEFAULT_INPUTS,
    DEFAULT_RELEASE_ID,
    DEFAULT_USE_CASE_ID,
    write_data_plane_smoke_report,
)
from enterprise_dp.ingestion_runtime import (
    ingestion_runtime_evidence_manifest,
    load_source_registry,
    write_ingestion_runtime_ops_report,
)
from enterprise_dp.schema import validate_json_schema
from enterprise_dp.source_bridge import run_source_bridge_preflight


DEFAULT_COMPOSE_FILE = Path("platform/runtime/local/docker-compose.yaml")
DEFAULT_SERVICE = "redpanda"
DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_INGESTED_AT = "2026-01-15T09:15:05Z"
DEFAULT_BUILT_AT = "2026-01-15T09:15:10Z"
DEFAULT_EVALUATION_TIME = "2026-01-15T09:15:15Z"
DEFAULT_FINANCE_SCHEMA_ID = "registry:finance.benefit_settled.v1:1"
DEFAULT_SNAPSHOT_ID = "finance-benefit-local-event-backbone-smoke"


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class EventBackboneSmokeResult:
    output_path: Path
    report: dict[str, Any]


CommandRunner = Callable[[list[str], str | None, Path, int], CommandResult]


def write_event_backbone_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    input_path: str | Path | None = None,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_SERVICE,
    topic: str | None = None,
    use_case_id: str = DEFAULT_USE_CASE_ID,
    release_id: str = DEFAULT_RELEASE_ID,
    environment: str = "local",
    generated_at: str | None = None,
    ingested_at: str | None = None,
    built_at: str | None = None,
    evaluation_time: str | None = None,
    schema_id: str | None = None,
    snapshot_id: str | None = None,
    schema_registry_runtime_report_path: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 90,
    start_runtime: bool = True,
) -> EventBackboneSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    source_path = resolve_input_path(platform_root, use_case_id, input_path)
    compose_path = resolve_compose_path(platform_root, compose_file)
    resolved_topic = topic or default_topic(release_id, generated)
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    source_round_trips: list[dict[str, Any]] = []
    consumed_path = target_dir / "event-backbone" / "consumed.jsonl"
    data_plane_report_path = target_dir / "data-plane-smoke-report.json"
    ingestion_runtime_evidence_path = target_dir / "ingestion-runtime" / "ingestion-runtime-evidence.json"
    ingestion_runtime_manifest_path = target_dir / "ingestion-runtime" / "ingestion-runtime-evidence-manifest.json"
    ingestion_runtime_report_path = target_dir / "ingestion-runtime" / "event-cdc-ingestion-runtime-report.json"
    data_plane_report: dict[str, Any] | None = None
    ingestion_runtime_report: dict[str, Any] | None = None
    multi_partition_probe: dict[str, Any] = {"passed": False, "skipped": True}
    schema_registry_runtime_report = load_optional_json_object(schema_registry_runtime_report_path)
    schema_registry_subjects = schema_registry_subject_index(schema_registry_runtime_report)

    primary_source = find_source_for_topic(platform_root, "finance.benefit_settled.v1")
    if primary_source:
        source_records, producer_input_path, normalization, producer_schema_id_guard = source_records_for_round_trip(
            platform_root,
            primary_source,
            source_path,
            target_dir=target_dir,
            generated_at=generated,
            schema_registry_subjects=schema_registry_subjects,
        )
    else:
        source_records = read_jsonl(source_path)
        producer_input_path = source_path
        normalization = {"required": False}
        producer_schema_id_guard = {
            "required": False,
            "passed": False,
            "mode": "source_registry_entry_missing",
            "error_count": 1,
            "errors": ["source registry entry is missing for finance.benefit_settled.v1"],
        }
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
        consumed = round_trip_topic(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            topic=resolved_topic,
            records=source_records,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
        )
        consumed_records = consumed
        write_jsonl(consumed_path, consumed_records)
        if primary_source:
            source_round_trips.append(
                source_round_trip_summary(
                    primary_source,
                    topic=resolved_topic,
                    input_path=producer_input_path,
                    consumed_path=consumed_path,
                    source_records=source_records,
                    consumed_records=consumed_records,
                    role="primary_data_plane_smoke_source",
                    root=platform_root,
                    raw_input_path=source_path,
                    normalization=normalization,
                    producer_schema_id_guard=producer_schema_id_guard,
                )
            )
        if consumed_records != source_records:
            failed_checks.append(
                {
                    "check": "event_backbone_round_trip_records_match",
                    "expected_count": len(source_records),
                    "actual_count": len(consumed_records),
                }
            )
        failed_schema_round_trips = [
            item for item in source_round_trips if item.get("schema_validation", {}).get("passed") is not True
        ]
        if failed_schema_round_trips:
            failed_checks.append(
                {
                    "check": "sink_schema_validation_passed",
                    "failed_sources": [item.get("source_id") for item in failed_schema_round_trips],
                }
            )
        if not failed_checks:
            data_plane = write_data_plane_smoke_report(
                platform_root,
                data_plane_report_path,
                input_path=consumed_path,
                output_dir=target_dir / "data-plane-smoke-run",
                use_case_id=use_case_id,
                release_id=release_id,
                environment=environment,
                generated_at=generated,
                ingested_at=ingested_at or DEFAULT_INGESTED_AT,
                built_at=built_at or DEFAULT_BUILT_AT,
                evaluation_time=evaluation_time or DEFAULT_EVALUATION_TIME,
                schema_id=schema_id or DEFAULT_FINANCE_SCHEMA_ID,
                snapshot_id=snapshot_id or DEFAULT_SNAPSHOT_ID,
            )
            data_plane_report = data_plane.report
            if data_plane.report.get("passed") is not True:
                failed_checks.append(
                    {
                        "check": "downstream_data_plane_smoke_passed",
                        "failed_checks": data_plane.report.get("summary", {}).get("failed_checks", []),
                    }
                )
            if not failed_checks:
                source_round_trips.extend(
                    run_p0_source_round_trips(
                        platform_root,
                        target_dir=target_dir,
                        compose_path=compose_path,
                        service=service,
                        release_id=release_id,
                        generated_at=generated,
                        command_log=command_log,
                        runner=runner,
                        timeout_seconds=command_timeout_seconds,
                        exclude_source_ids={str(primary_source.get("sourceId"))} if primary_source else set(),
                        schema_registry_subjects=schema_registry_subjects,
                    )
                )
                failed_round_trips = [item for item in source_round_trips if item.get("matched") is not True]
                failed_schema_round_trips = [
                    item for item in source_round_trips if item.get("schema_validation", {}).get("passed") is not True
                ]
                if failed_round_trips:
                    failed_checks.append(
                        {
                            "check": "p0_source_round_trips_match",
                            "failed_sources": [
                                item.get("source_id")
                                for item in failed_round_trips
                            ],
                        }
                    )
                if failed_schema_round_trips:
                    failed_checks.append(
                        {
                            "check": "p0_sink_schema_validation_passed",
                            "failed_sources": [
                                item.get("source_id")
                                for item in failed_schema_round_trips
                            ],
                        }
                    )
            if not failed_checks:
                multi_partition_probe = run_multi_partition_rebalance_probe(
                    command_log,
                    runner,
                    target_dir=target_dir,
                    compose_path=compose_path,
                    service=service,
                    release_id=release_id,
                    generated_at=generated,
                    cwd=platform_root,
                    timeout_seconds=command_timeout_seconds,
                )
                if multi_partition_probe.get("passed") is not True:
                    failed_checks.append(
                        {
                            "check": "multi_partition_rebalance_probe_passed",
                            "failed_checks": multi_partition_probe.get("failed_checks", []),
                        }
                    )
            if not failed_checks:
                ingestion_runtime_report = write_local_ingestion_runtime_evidence(
                    platform_root,
                    evidence_path=ingestion_runtime_evidence_path,
                    manifest_path=ingestion_runtime_manifest_path,
                    report_path=ingestion_runtime_report_path,
                    environment=environment,
                    generated_at=generated,
                    topic=resolved_topic,
                    source_record_count=len(source_records),
                    consumed_record_count=len(consumed_records),
                    consumed_path=consumed_path,
                    data_plane_report_path=data_plane_report_path,
                    source_round_trips=source_round_trips,
                )
                if ingestion_runtime_report.get("passed") is not True:
                    failed_checks.append(
                        {
                            "check": "ingestion_runtime_ops_report_passed",
                            "failed_checks": ingestion_runtime_report.get("decision_board", {}).get("page_now", []),
                        }
                    )
    except RuntimeError as exc:
        failed_checks.append({"check": "event_backbone_command", "message": str(exc)})

    report = build_event_backbone_smoke_report(
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        use_case_id=use_case_id,
        topic=resolved_topic,
        source_path=source_path,
        consumed_path=consumed_path,
        data_plane_report_path=data_plane_report_path,
        data_plane_report=data_plane_report,
        ingestion_runtime_report_path=ingestion_runtime_report_path,
        ingestion_runtime_report=ingestion_runtime_report,
        schema_registry_runtime_report_path=Path(schema_registry_runtime_report_path)
        if schema_registry_runtime_report_path
        else None,
        schema_registry_runtime_report=schema_registry_runtime_report,
        multi_partition_probe=multi_partition_probe,
        command_log=command_log,
        failed_checks=failed_checks,
        source_record_count=len(source_records),
        source_round_trips=source_round_trips,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return EventBackboneSmokeResult(output_path=target, report=report)


def build_event_backbone_smoke_report(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    topic: str,
    source_path: Path,
    consumed_path: Path,
    data_plane_report_path: Path,
    data_plane_report: dict[str, Any] | None,
    ingestion_runtime_report_path: Path,
    ingestion_runtime_report: dict[str, Any] | None,
    schema_registry_runtime_report_path: Path | None,
    schema_registry_runtime_report: dict[str, Any] | None,
    multi_partition_probe: dict[str, Any],
    command_log: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
    source_record_count: int,
    source_round_trips: list[dict[str, Any]],
) -> dict[str, Any]:
    consumed_exists = consumed_path.is_file()
    consumed_count = count_jsonl(consumed_path) if consumed_exists else 0
    data_plane_passed = bool(data_plane_report and data_plane_report.get("passed") is True)
    ingestion_runtime_passed = bool(ingestion_runtime_report and ingestion_runtime_report.get("passed") is True)
    producer_schema_id_guard_passed = bool(source_round_trips) and all(
        item.get("producer_schema_id_guard", {}).get("passed") is True for item in source_round_trips
    )
    schema_registry_report_exists = bool(schema_registry_runtime_report_path and schema_registry_runtime_report_path.is_file())
    covered_runtime_scope = [
        "redpanda_container_started",
        "topic_created",
        "records_produced_to_event_backbone",
        "records_consumed_from_event_backbone",
        "consumed_records_reused_by_data_plane_smoke",
        "consumed_records_validated_against_topic_contracts",
        "local_ingestion_runtime_evidence_generated",
    ]
    if producer_schema_id_guard_passed:
        covered_runtime_scope.append("producer_records_stamped_with_schema_registry_ids")
    multi_partition_passed = multi_partition_probe.get("passed") is True
    if multi_partition_passed:
        covered_runtime_scope.append("multi_partition_consumer_group_lag_zero_probe")
    not_covered_runtime_scope = [
        "debezium_or_transactional_outbox_source_connector",
        "broker_acl_enforcement",
        "production_schema_registry_subject_publication",
    ]
    if not multi_partition_passed:
        not_covered_runtime_scope.append("multi_partition_rebalance")
    report = {
        "artifact_type": "event_backbone_smoke_report.v1",
        "report_version": 1,
        "capability_id": "event-cdc-ingestion-runtime",
        "report_id": f"event-backbone-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "topic": topic,
        "runtime_scope": {
            "mode": "local_redpanda_rpk_round_trip",
            "covered": covered_runtime_scope,
            "not_covered": not_covered_runtime_scope,
        },
        "input": {
            "path": source_path.as_posix(),
            "content_hash": hash_file(source_path),
            "row_count": source_record_count,
        },
        "consumed_output": {
            "path": consumed_path.as_posix(),
            "exists": consumed_exists,
            "content_hash": hash_file(consumed_path) if consumed_exists else None,
            "row_count": consumed_count,
        },
        "data_plane_smoke": {
            "path": data_plane_report_path.as_posix(),
            "exists": data_plane_report_path.is_file(),
            "content_hash": hash_file(data_plane_report_path) if data_plane_report_path.is_file() else None,
            "passed": data_plane_passed,
            "primary_output": data_plane_report.get("primary_output") if data_plane_report else None,
            "query_name": data_plane_report.get("query_smoke", {}).get("query_name") if data_plane_report else None,
        },
        "ingestion_runtime": {
            "path": ingestion_runtime_report_path.as_posix(),
            "exists": ingestion_runtime_report_path.is_file(),
            "content_hash": hash_file(ingestion_runtime_report_path) if ingestion_runtime_report_path.is_file() else None,
            "passed": ingestion_runtime_passed,
            "readiness_state": ingestion_runtime_report.get("readiness_state") if ingestion_runtime_report else None,
            "mode": ingestion_runtime_report.get("mode") if ingestion_runtime_report else None,
        },
        "schema_registry_runtime": {
            "path": schema_registry_runtime_report_path.as_posix() if schema_registry_runtime_report_path else None,
            "exists": schema_registry_report_exists,
            "content_hash": hash_file(schema_registry_runtime_report_path) if schema_registry_report_exists else None,
            "passed": schema_registry_runtime_report.get("passed") if isinstance(schema_registry_runtime_report, dict) else None,
            "subject_count": schema_registry_runtime_report.get("summary", {}).get("subject_count")
            if isinstance(schema_registry_runtime_report, dict) and isinstance(schema_registry_runtime_report.get("summary"), dict)
            else None,
        },
        "multi_partition_probe": multi_partition_probe,
        "source_round_trips": source_round_trips,
        "commands": command_log,
        "summary": {
            "source_record_count": source_record_count,
            "consumed_record_count": consumed_count,
            "round_trip_count_matches": source_record_count == consumed_count,
            "source_round_trip_count": len(source_round_trips),
            "p0_source_round_trip_count": sum(1 for item in source_round_trips if item.get("priority") == "P0"),
            "source_round_trip_failed_count": sum(1 for item in source_round_trips if item.get("matched") is not True),
            "sink_schema_validation_passed": bool(source_round_trips)
            and all(item.get("schema_validation", {}).get("passed") is True for item in source_round_trips),
            "sink_schema_validated_source_count": sum(
                1 for item in source_round_trips if item.get("schema_validation", {}).get("passed") is True
            ),
            "sink_schema_validation_failed_count": sum(
                1 for item in source_round_trips if item.get("schema_validation", {}).get("passed") is not True
            ),
            "producer_schema_id_guard_passed": producer_schema_id_guard_passed,
            "producer_schema_id_guarded_source_count": sum(
                1 for item in source_round_trips if item.get("producer_schema_id_guard", {}).get("passed") is True
            ),
            "producer_schema_id_guard_failed_count": sum(
                1 for item in source_round_trips if item.get("producer_schema_id_guard", {}).get("passed") is not True
            ),
            "multi_partition_rebalance_passed": multi_partition_passed,
            "multi_partition_topic_partition_count": multi_partition_probe.get("partition_count"),
            "multi_partition_consumed_partition_count": len(multi_partition_probe.get("consumed_partition_counts", {}))
            if isinstance(multi_partition_probe.get("consumed_partition_counts"), dict)
            else 0,
            "multi_partition_group_total_lag": multi_partition_probe.get("group_describe", {}).get("total_lag")
            if isinstance(multi_partition_probe.get("group_describe"), dict)
            else None,
            "data_plane_smoke_passed": data_plane_passed,
            "ingestion_runtime_report_passed": ingestion_runtime_passed,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = (
        source_record_count > 0
        and consumed_count == source_record_count
        and data_plane_passed
        and ingestion_runtime_passed
        and multi_partition_passed
        and not failed_checks
    )
    return report


def run_multi_partition_rebalance_probe(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    target_dir: Path,
    compose_path: Path,
    service: str,
    release_id: str,
    generated_at: str,
    cwd: Path,
    timeout_seconds: int,
    partition_count: int = 3,
    records_per_partition: int = 2,
) -> dict[str, Any]:
    topic = f"{default_topic(release_id, generated_at)}.multi.partition"
    group = f"{topic}.group"
    records: list[tuple[int, dict[str, Any]]] = []
    for partition in range(partition_count):
        for sequence in range(records_per_partition):
            records.append(
                (
                    partition,
                    {
                        "probe": "multi_partition_rebalance",
                        "partition": partition,
                        "sequence": sequence,
                        "releaseId": release_id,
                        "generatedAt": generated_at,
                    },
                )
            )
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
        "--partitions",
        str(partition_count),
    ]
    topic_create = execute_step(
        command_log,
        runner,
        topic_create_args,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="multi_partition_topic_create",
        raise_on_error=False,
    )
    if topic_create.returncode != 0 and topic_exists_error(topic_create):
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
                service,
                "rpk",
                "topic",
                "delete",
                topic,
            ],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step="multi_partition_topic_delete_existing",
        )
        execute_step(
            command_log,
            runner,
            topic_create_args,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step="multi_partition_topic_create_retry",
        )
    elif topic_create.returncode != 0:
        raise RuntimeError(command_failure_message("multi_partition_topic_create", topic_create))

    producer_input = "".join(f"{partition} {canonical_json(record)}\n" for partition, record in records)
    produce = execute_step(
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
            "produce",
            "--partition",
            "0",
            "--format",
            "%p %v\n",
            "--output-format",
            "%p %o\n",
            topic,
        ],
        input_text=producer_input,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="multi_partition_topic_produce",
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
            "--group",
            group,
            "--offset",
            "start",
            "--num",
            str(len(records)),
            "--format",
            "%p %v\n",
        ],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="multi_partition_group_consume",
    )
    group_describe = execute_step(
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
            "group",
            "describe",
            group,
        ],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step="multi_partition_group_describe",
    )
    consumed_records = parse_partitioned_consumed_records(consumed.stdout)
    consumed_path = target_dir / "event-backbone" / "multi-partition" / "consumed-partitions.jsonl"
    write_jsonl(
        consumed_path,
        [
            {"partition": item["partition"], "record": item["record"]}
            for item in consumed_records
        ],
    )
    produced_counts = partition_counts([partition for partition, _record in records], partition_count=partition_count)
    consumed_counts = partition_counts(
        [int(item["partition"]) for item in consumed_records],
        partition_count=partition_count,
    )
    expected_payloads = sorted(canonical_json(record) for _partition, record in records)
    consumed_payloads = sorted(canonical_json(item["record"]) for item in consumed_records)
    group_state = parse_rpk_group_describe(group_describe.stdout, topic=topic)
    failed_checks = failed_multi_partition_checks(
        produced_counts=produced_counts,
        consumed_counts=consumed_counts,
        expected_payloads=expected_payloads,
        consumed_payloads=consumed_payloads,
        group_state=group_state,
        partition_count=partition_count,
    )
    return {
        "passed": not failed_checks,
        "mode": "local_redpanda_multi_partition_consumer_group_probe",
        "topic": topic,
        "group": group,
        "partition_count": partition_count,
        "records_per_partition": records_per_partition,
        "record_count": len(records),
        "produced_partition_counts": produced_counts,
        "consumed_partition_counts": consumed_counts,
        "produce_output_hash": stable_id("multi-partition-produce-output", produce.stdout[:4000]),
        "consume_output": {
            "path": consumed_path.as_posix(),
            "content_hash": hash_file(consumed_path),
            "row_count": len(consumed_records),
        },
        "group_describe": group_state,
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }


def parse_partitioned_consumed_records(stdout: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            partition_text, payload_text = stripped.split(" ", 1)
            partition = int(partition_text)
            payload = json.loads(payload_text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"multi-partition consumed row {line_number} is invalid: {stripped!r}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"multi-partition consumed row {line_number} payload must be an object")
        rows.append({"partition": partition, "record": payload})
    return rows


def partition_counts(partitions: list[int], *, partition_count: int) -> dict[str, int]:
    counts = {str(partition): 0 for partition in range(partition_count)}
    for partition in partitions:
        key = str(partition)
        counts[key] = counts.get(key, 0) + 1
    return counts


def parse_rpk_group_describe(stdout: str, *, topic: str) -> dict[str, Any]:
    total_lag: int | None = None
    partition_lags: dict[str, dict[str, int]] = {}
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if parts[0] == "TOTAL-LAG" and len(parts) >= 2:
            try:
                total_lag = int(parts[-1])
            except ValueError:
                total_lag = None
        elif parts[0] == topic and len(parts) >= 6:
            partition = parts[1]
            try:
                partition_lags[partition] = {
                    "current_offset": int(parts[2]),
                    "log_start_offset": int(parts[3]),
                    "log_end_offset": int(parts[4]),
                    "lag": int(parts[5]),
                }
            except ValueError:
                continue
    return {
        "total_lag": total_lag,
        "partition_lags": partition_lags,
        "partition_lag_count": len(partition_lags),
        "all_partition_lag_zero": bool(partition_lags) and all(item["lag"] == 0 for item in partition_lags.values()),
        "stdout_preview_hash": stable_id("multi-partition-group-describe", stdout[:4000]),
    }


def failed_multi_partition_checks(
    *,
    produced_counts: dict[str, int],
    consumed_counts: dict[str, int],
    expected_payloads: list[str],
    consumed_payloads: list[str],
    group_state: dict[str, Any],
    partition_count: int,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if consumed_payloads != expected_payloads:
        failed.append(
            {
                "check": "multi_partition_payloads_match",
                "expected_count": len(expected_payloads),
                "actual_count": len(consumed_payloads),
            }
        )
    if consumed_counts != produced_counts:
        failed.append(
            {
                "check": "multi_partition_counts_match",
                "produced_partition_counts": produced_counts,
                "consumed_partition_counts": consumed_counts,
            }
        )
    active_partitions = [partition for partition, count in consumed_counts.items() if count > 0]
    if len(active_partitions) != partition_count:
        failed.append(
            {
                "check": "multi_partition_all_partitions_consumed",
                "expected_partition_count": partition_count,
                "active_partitions": active_partitions,
            }
        )
    if group_state.get("total_lag") != 0 or group_state.get("all_partition_lag_zero") is not True:
        failed.append(
            {
                "check": "multi_partition_group_lag_zero",
                "total_lag": group_state.get("total_lag"),
                "partition_lags": group_state.get("partition_lags", {}),
            }
        )
    if group_state.get("partition_lag_count") != partition_count:
        failed.append(
            {
                "check": "multi_partition_group_describes_all_partitions",
                "expected_partition_count": partition_count,
                "partition_lag_count": group_state.get("partition_lag_count"),
            }
        )
    return failed


def write_local_ingestion_runtime_evidence(
    root: Path,
    *,
    evidence_path: Path,
    manifest_path: Path,
    report_path: Path,
    environment: str,
    generated_at: str,
    topic: str,
    source_record_count: int,
    consumed_record_count: int,
    consumed_path: Path,
    data_plane_report_path: Path,
    source_round_trips: list[dict[str, Any]],
) -> dict[str, Any]:
    source = find_source_for_topic(root, "finance.benefit_settled.v1")
    sources = load_source_registry(root)
    source_index = {str(item.get("sourceId")): item for item in sources if item.get("sourceId")}
    connectors = [
        local_round_trip_connector(item, generated_at=generated_at)
        for item in source_round_trips
        if item.get("matched") is True and item.get("source_id")
    ]
    source_id = str(source.get("sourceId") or "enterprise-commerce-benefit-settled-outbox")
    if not connectors:
        connectors = [
            local_round_trip_connector(
                {
                    "source_id": source_id,
                    "topic": topic,
                    "input": {"row_count": source_record_count},
                    "consumed_output": {
                        "row_count": consumed_record_count,
                        "path": consumed_path.as_posix(),
                        "content_hash": hash_file(consumed_path),
                    },
                    "matched": source_record_count == consumed_record_count,
                    "priority": source.get("priority", "P0"),
                },
                generated_at=generated_at,
            )
        ]
    p0_connector_count = sum(
        1
        for connector in connectors
        if source_index.get(str(connector.get("source_id")), {}).get("priority") == "P0"
    )
    evidence = {
        "artifact_type": "ingestion_runtime_evidence.v1",
        "report_version": 1,
        "evidence_id": stable_id(
            "local-redpanda-ingestion-runtime",
            environment,
            generated_at,
            topic,
            source_id,
            source_record_count,
            consumed_record_count,
            hash_file(consumed_path),
            hash_file(data_plane_report_path),
            connectors,
        ),
        "generated_at": generated_at,
        "valid_until": None,
        "environment": environment,
        "source_kind": "ci_tool_output",
        "issuer": {
            "tool": "enterprise-dp event-backbone-smoke",
            "tool_version": "0.1.0",
        },
        "runtime_scope": {
            "mode": "local_redpanda_rpk_round_trip_to_ingestion_runtime_evidence",
            "covered": [
                "local_redpanda_topic_created",
                "records_produced",
                "records_consumed",
                "consumer_lag_zero_for_smoke_topic",
                "backpressure_clear_for_smoke_topic",
                "downstream_data_plane_smoke_bound",
            ],
            "not_covered": [
                "kafka_connect_or_debezium_connector_runtime",
                "transactional_outbox_source_connector_to_bronze",
                "broker_acl_enforcement",
                "production_dlt_runtime_policy",
                "production_multi_partition_rebalance",
            ],
        },
        "connectors": connectors,
        "summary": {
            "source_count": len(sources),
            "p0_source_count": sum(1 for item in sources if item.get("priority") == "P0"),
            "connector_count": len(connectors),
            "p0_connector_count": p0_connector_count,
            "source_record_count": sum(int(item.get("input", {}).get("row_count") or 0) for item in source_round_trips)
            or source_record_count,
            "consumed_record_count": sum(
                int(item.get("consumed_output", {}).get("row_count") or 0)
                for item in source_round_trips
            )
            or consumed_record_count,
        },
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(f"{canonical_json(evidence)}\n", encoding="utf-8")
    manifest = ingestion_runtime_evidence_manifest(evidence_path, evidence)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    result = write_ingestion_runtime_ops_report(
        root,
        report_path,
        environment=environment,
        evidence_path=evidence_path,
        generated_at=generated_at,
    )
    return result.report


def run_p0_source_round_trips(
    root: Path,
    *,
    target_dir: Path,
    compose_path: Path,
    service: str,
    release_id: str,
    generated_at: str,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    timeout_seconds: int,
    exclude_source_ids: set[str],
    schema_registry_subjects: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    round_trips: list[dict[str, Any]] = []
    for source in sorted(load_source_registry(root), key=lambda item: str(item.get("sourceId") or "")):
        source_id = str(source.get("sourceId") or "")
        if source.get("priority") != "P0" or source_id in exclude_source_ids:
            continue
        sample_path = source_sample_path(root, source)
        if sample_path is None:
            raise RuntimeError(f"{source_id}: local source sample is missing for P0 event-backbone coverage")
        records, producer_input_path, normalization, producer_schema_id_guard = source_records_for_round_trip(
            root,
            source,
            sample_path,
            target_dir=target_dir,
            generated_at=generated_at,
            schema_registry_subjects=schema_registry_subjects,
        )
        topic = source_smoke_topic(source, release_id=release_id, generated_at=generated_at)
        consumed_path = target_dir / "event-backbone" / "source-round-trips" / f"{source_id}.jsonl"
        consumed_records = round_trip_topic(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            topic=topic,
            records=records,
            cwd=root,
            timeout_seconds=timeout_seconds,
            step_prefix=f"source_{safe_id(source_id)}",
        )
        write_jsonl(consumed_path, consumed_records)
        round_trips.append(
            source_round_trip_summary(
                source,
                topic=topic,
                input_path=producer_input_path,
                consumed_path=consumed_path,
                source_records=records,
                consumed_records=consumed_records,
                role="p0_source_runtime_coverage",
                root=root,
                raw_input_path=sample_path,
                normalization=normalization,
                producer_schema_id_guard=producer_schema_id_guard,
            )
        )
    return round_trips


def source_records_for_round_trip(
    root: Path,
    source: dict[str, Any],
    sample_path: Path,
    *,
    target_dir: Path,
    generated_at: str,
    schema_registry_subjects: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], Path, dict[str, Any], dict[str, Any]]:
    bridge = source.get("bridge") if isinstance(source.get("bridge"), dict) else {}
    if bridge.get("required") is not True:
        records = read_jsonl(sample_path)
        guarded_records, guarded_path, producer_schema_id_guard = apply_producer_schema_id_guard(
            root,
            source,
            records,
            sample_path,
            target_dir=target_dir,
            schema_registry_subjects=schema_registry_subjects,
        )
        return (
            guarded_records,
            guarded_path,
            {"required": False, "mode": bridge.get("mode"), "quality_passed": None},
            producer_schema_id_guard,
        )

    source_id = str(source.get("sourceId") or "unknown-source")
    result = run_source_bridge_preflight(
        root,
        source_id,
        sample_path,
        target_dir / "event-backbone" / "source-normalized" / source_id,
        normalized_at=generated_at,
        bridge_run_id=f"event-backbone-{safe_id(source_id)}-{safe_id(generated_at)}",
    )
    if result.manifest.get("quality_passed") is not True:
        raise RuntimeError(f"{source_id}: source bridge normalization failed before event-backbone round trip")
    records = read_jsonl(result.normalized_path)
    guarded_records, guarded_path, producer_schema_id_guard = apply_producer_schema_id_guard(
        root,
        source,
        records,
        result.normalized_path,
        target_dir=target_dir,
        schema_registry_subjects=schema_registry_subjects,
    )
    return (
        guarded_records,
        guarded_path,
        {
            "required": True,
            "mode": bridge.get("mode"),
            "normalizer_id": bridge.get("normalizerId"),
            "manifest_path": result.manifest_path.as_posix(),
            "manifest_hash": hash_file(result.manifest_path),
            "quality_passed": True,
            "quarantine_row_count": result.manifest.get("quarantine", {}).get("row_count"),
        },
        producer_schema_id_guard,
    )


def apply_producer_schema_id_guard(
    root: Path,
    source: dict[str, Any],
    records: list[dict[str, Any]],
    input_path: Path,
    *,
    target_dir: Path,
    schema_registry_subjects: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], Path, dict[str, Any]]:
    guard = validate_producer_schema_id_guard(root, source, records, schema_registry_subjects)
    if guard.get("required") is not True:
        return records, input_path, guard
    if guard.get("passed") is not True:
        source_id = str(source.get("sourceId") or "unknown-source")
        raise RuntimeError(f"{source_id}: producer schema-id guard failed before Redpanda produce")

    stamped = [
        stamp_record_with_schema_registry_metadata(record, guard)
        for record in records
    ]
    source_id = str(source.get("sourceId") or "unknown-source")
    guarded_path = target_dir / "event-backbone" / "producer-schema-id-guard" / f"{source_id}.jsonl"
    write_jsonl(guarded_path, stamped)
    guard = {
        **guard,
        "producer_input": {
            "path": guarded_path.as_posix(),
            "content_hash": hash_file(guarded_path),
            "row_count": len(stamped),
        },
    }
    return stamped, guarded_path, guard


def validate_producer_schema_id_guard(
    root: Path,
    source: dict[str, Any],
    records: list[dict[str, Any]],
    schema_registry_subjects: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    subject = canonical.get("schemaSubject")
    topic_name = canonical.get("topic")
    if not schema_registry_subjects:
        return {
            "required": False,
            "passed": False,
            "mode": "schema_registry_runtime_report_not_attached",
            "schema_subject": subject,
            "topic": topic_name,
            "record_count": len(records),
            "error_count": 0,
            "errors": [],
        }
    errors: list[str] = []
    if not isinstance(subject, str) or not subject:
        errors.append("canonical.schemaSubject is required")
    if not isinstance(topic_name, str) or not topic_name:
        errors.append("canonical.topic is required")
    registry_subject = schema_registry_subjects.get(str(subject))
    if registry_subject is None:
        errors.append(f"schema subject is missing from schema registry runtime report: {subject}")
        registry_subject = {}
    topic_contract_path = root / "contracts" / "topics" / f"{topic_name}.yaml" if isinstance(topic_name, str) else None
    topic_contract = load_yaml(topic_contract_path) if topic_contract_path and topic_contract_path.is_file() else {}
    schema = topic_contract.get("schema") if isinstance(topic_contract.get("schema"), dict) else {}
    payload_schema_ref = str(schema.get("payloadSchema") or "")
    payload_schema_path = root / payload_schema_ref if payload_schema_ref else None
    payload_schema_hash = hash_file(payload_schema_path) if payload_schema_path and payload_schema_path.is_file() else None
    accepted_refs = producer_payload_schema_refs(canonical, payload_schema_ref)
    schema_id = registry_subject.get("schema_id")
    if registry_subject.get("registered") is not True:
        errors.append(f"schema subject is not registered: {subject}")
    if not schema_id:
        errors.append(f"schema id is missing for subject: {subject}")
    if registry_subject.get("payload_schema_hash") != payload_schema_hash:
        errors.append(
            "schema registry payload hash does not match topic contract "
            f"for {subject}: registry={registry_subject.get('payload_schema_hash')} contract={payload_schema_hash}"
        )
    for index, record in enumerate(records):
        payload_schema = record.get("payloadSchema") if isinstance(record, dict) else None
        if not isinstance(payload_schema, str) or payload_schema not in accepted_refs:
            errors.append(
                f"record[{index}].payloadSchema must be one of {sorted(accepted_refs)}; actual={payload_schema!r}"
            )
    return {
        "required": True,
        "passed": not errors and bool(records),
        "mode": "local_producer_schema_id_guard",
        "schema_subject": subject,
        "topic": topic_name,
        "schema_id": str(schema_id) if schema_id is not None else None,
        "schema_version": registry_subject.get("version"),
        "registry_uri": registry_subject.get("registry_uri"),
        "payload_schema_hash": payload_schema_hash,
        "registry_payload_schema_hash": registry_subject.get("payload_schema_hash"),
        "accepted_payload_schema_refs": sorted(accepted_refs),
        "record_count": len(records),
        "error_count": len(errors),
        "errors": errors[:30],
    }


def producer_payload_schema_refs(canonical: dict[str, Any], payload_schema_ref: str) -> set[str]:
    topic = canonical.get("topic")
    subject = canonical.get("schemaSubject")
    refs = {payload_schema_ref}
    if isinstance(topic, str) and topic:
        refs.add(topic)
    if isinstance(subject, str) and subject:
        refs.add(subject)
        if subject.endswith("-value"):
            refs.add(subject[: -len("-value")])
    return {ref for ref in refs if isinstance(ref, str) and ref}


def stamp_record_with_schema_registry_metadata(record: dict[str, Any], guard: dict[str, Any]) -> dict[str, Any]:
    stamped = json.loads(canonical_json(record))
    headers = stamped.get("headers") if isinstance(stamped.get("headers"), dict) else {}
    stamped["headers"] = {
        **headers,
        "schemaSubject": guard.get("schema_subject"),
        "schemaId": guard.get("schema_id"),
        "schemaVersion": guard.get("schema_version"),
        "schemaRegistryUri": guard.get("registry_uri"),
    }
    return stamped


def round_trip_topic(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    compose_path: Path,
    service: str,
    topic: str,
    records: list[dict[str, Any]],
    cwd: Path,
    timeout_seconds: int,
    step_prefix: str = "",
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
        step=prefixed_step(step_prefix, "topic_create"),
        raise_on_error=False,
    )
    if topic_create.returncode != 0 and topic_exists_error(topic_create):
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
                service,
                "rpk",
                "topic",
                "delete",
                topic,
            ],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step=prefixed_step(step_prefix, "topic_delete_existing"),
        )
        execute_step(
            command_log,
            runner,
            topic_create_args,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step=prefixed_step(step_prefix, "topic_create_retry"),
        )
    elif topic_create.returncode != 0:
        raise RuntimeError(command_failure_message(prefixed_step(step_prefix, "topic_create"), topic_create))
    execute_step(
        command_log,
        runner,
        ["docker", "compose", "-f", compose_path.as_posix(), "exec", "-T", service, "rpk", "topic", "produce", topic],
        input_text="".join(f"{canonical_json(record)}\n" for record in records),
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step=prefixed_step(step_prefix, "topic_produce"),
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
            "%v\n",
        ],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step=prefixed_step(step_prefix, "topic_consume"),
    )
    return parse_consumed_jsonl(consumed.stdout)


def source_round_trip_summary(
    source: dict[str, Any],
    *,
    topic: str,
    input_path: Path,
    consumed_path: Path,
    source_records: list[dict[str, Any]],
    consumed_records: list[dict[str, Any]],
    role: str,
    root: Path,
    raw_input_path: Path | None = None,
    normalization: dict[str, Any] | None = None,
    producer_schema_id_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    raw_source = source.get("source") if isinstance(source.get("source"), dict) else {}
    schema_validation = validate_consumed_records_against_source_contract(root, source, consumed_records)
    return {
        "source_id": source.get("sourceId"),
        "priority": source.get("priority"),
        "role": role,
        "topic": topic,
        "raw_topic": raw_source.get("rawTopic"),
        "canonical_topic": canonical.get("topic"),
        "bronze_target": canonical.get("bronzeTarget"),
        "input": {
            "path": input_path.as_posix(),
            "content_hash": hash_file(input_path),
            "row_count": len(source_records),
        },
        "raw_input": (
            {
                "path": raw_input_path.as_posix(),
                "content_hash": hash_file(raw_input_path),
            }
            if raw_input_path is not None and raw_input_path != input_path
            else None
        ),
        "normalization": normalization or {"required": False},
        "producer_schema_id_guard": producer_schema_id_guard or {"required": False, "passed": False},
        "consumed_output": {
            "path": consumed_path.as_posix(),
            "content_hash": hash_file(consumed_path) if consumed_path.is_file() else None,
            "row_count": len(consumed_records),
        },
        "schema_validation": schema_validation,
        "matched": consumed_records == source_records,
    }


def validate_consumed_records_against_source_contract(
    root: Path,
    source: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    topic_name = canonical.get("topic")
    if not isinstance(topic_name, str) or not topic_name:
        return {"passed": False, "error_count": 1, "errors": ["canonical.topic is required"]}
    topic_contract_path = root / "contracts" / "topics" / f"{topic_name}.yaml"
    if not topic_contract_path.is_file():
        return {
            "passed": False,
            "topic": topic_name,
            "error_count": 1,
            "errors": [f"topic contract is missing: {topic_contract_path.as_posix()}"],
        }
    topic_contract = load_yaml(topic_contract_path)
    schema = topic_contract.get("schema") if isinstance(topic_contract.get("schema"), dict) else {}
    envelope_schema = load_json_object(root / str(schema.get("envelopeSchema") or "contracts/event-envelope.v1.schema.json"))
    payload_schema = load_json_object(root / str(schema.get("payloadSchema") or ""))
    errors: list[str] = []
    for index, record in enumerate(records):
        envelope_errors = validate_json_schema(record, envelope_schema)
        payload = record.get("payload")
        payload_errors = validate_json_schema(payload, payload_schema) if isinstance(payload, dict) else ("$.payload must be object",)
        errors.extend(f"record[{index}].envelope {error}" for error in envelope_errors)
        errors.extend(f"record[{index}].payload {error}" for error in payload_errors)
    return {
        "passed": not errors and bool(records),
        "mode": "local_sink_json_schema_validation",
        "topic": topic_name,
        "schema_subject": canonical.get("schemaSubject"),
        "record_count": len(records),
        "error_count": len(errors),
        "errors": errors[:30],
        "topic_contract": {
            "path": topic_contract_path.as_posix(),
            "hash": hash_file(topic_contract_path),
        },
        "envelope_schema": {
            "path": str(schema.get("envelopeSchema") or "contracts/event-envelope.v1.schema.json"),
            "hash": hash_file(root / str(schema.get("envelopeSchema") or "contracts/event-envelope.v1.schema.json")),
        },
        "payload_schema": {
            "path": str(schema.get("payloadSchema") or ""),
            "hash": hash_file(root / str(schema.get("payloadSchema") or "")),
        },
    }


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"JSON schema file is missing: {path.as_posix()}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"JSON schema must be an object: {path.as_posix()}")
    return data


def load_optional_json_object(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    if not target.is_file():
        return None
    return load_json_object(target)


def schema_registry_subject_index(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(report, dict) or report.get("passed") is not True:
        return {}
    subjects = report.get("subjects")
    if not isinstance(subjects, list):
        return {}
    return {
        str(subject.get("subject")): subject
        for subject in subjects
        if isinstance(subject, dict) and subject.get("subject")
    }


def local_round_trip_connector(round_trip: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    source_id = str(round_trip.get("source_id") or "unknown-source")
    input_count = int(round_trip.get("input", {}).get("row_count") or 0)
    consumed = round_trip.get("consumed_output") if isinstance(round_trip.get("consumed_output"), dict) else {}
    consumed_count = int(consumed.get("row_count") or 0)
    return {
        "source_id": source_id,
        "connector_id": f"local-redpanda-rpk-{safe_id(source_id)}-smoke",
        "connector_type": "local_redpanda_rpk_round_trip",
        "deployment_state": "running",
        "tasks_total": 1,
        "tasks_running": 1,
        "backpressure_state": "clear",
        "lag": {
            "max_lag_records": max(input_count - consumed_count, 0),
            "max_lag_seconds": 0,
        },
        "dlt": {
            "enabled": False,
            "topic": None,
            "unresolved_count": 0,
        },
        "broker": {
            "topic": round_trip.get("topic"),
            "topic_exists": True,
            "producer_acl": False,
            "consumer_acl": False,
        },
        "offset_ledger": {
            "uri": consumed.get("path"),
            "hash": consumed.get("content_hash"),
        },
        "last_successful_commit_at": generated_at,
    }


def source_sample_path(root: Path, source: dict[str, Any]) -> Path | None:
    evidence = source.get("evidence") if isinstance(source.get("evidence"), dict) else {}
    sample = evidence.get("localSamplePath") or source.get("localSamplePath")
    if not isinstance(sample, str) or not sample:
        return None
    path = Path(sample)
    if not path.is_absolute():
        path = root / path
    return path if path.is_file() else None


def source_smoke_topic(source: dict[str, Any], *, release_id: str, generated_at: str) -> str:
    source_id = str(source.get("sourceId") or "unknown-source")
    return f"dp.local.source.{safe_id(source_id)}.{safe_id(release_id)}.{safe_id(generated_at)}"


def prefixed_step(prefix: str, step: str) -> str:
    return f"{prefix}_{step}" if prefix else step


def find_source_for_topic(root: Path, topic: str) -> dict[str, Any]:
    for source in load_source_registry(root):
        canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
        if canonical.get("topic") == topic:
            return source
    return {}


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


def command_failure_message(step: str, result: CommandResult) -> str:
    detail = result.stderr[:500] or result.stdout[:500]
    return f"{step} failed with exit code {result.returncode}: {detail}"


def topic_exists_error(result: CommandResult) -> bool:
    output = f"{result.stdout}\n{result.stderr}"
    return "TOPIC_ALREADY_EXISTS" in output or "topic_already_exists" in output.lower()


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


def parse_consumed_jsonl(stdout: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"consumed record {line_number} is not JSON") from exc
        if not isinstance(record, dict):
            raise RuntimeError(f"consumed record {line_number} must be a JSON object")
        records.append(record)
    return records


def resolve_input_path(root: Path, use_case_id: str, input_path: str | Path | None) -> Path:
    if input_path:
        source = Path(input_path)
        if source.is_absolute() or source.exists():
            return source
        return root / source
    default_input = DEFAULT_INPUTS.get(use_case_id)
    if default_input is None:
        raise ValueError(f"input_path is required for use case {use_case_id!r}")
    return root / default_input


def resolve_compose_path(root: Path, compose_file: str | Path | None) -> Path:
    value = Path(compose_file) if compose_file else DEFAULT_COMPOSE_FILE
    return value if value.is_absolute() else root / value


def default_topic(release_id: str, generated_at: str) -> str:
    return f"dp.local.smoke.{safe_id(release_id)}.{safe_id(generated_at)}"


def safe_id(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "." for char in value).strip(".")


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


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


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(f"{canonical_json(record)}\n" for record in records), encoding="utf-8")


def count_jsonl(path: str | Path) -> int:
    if not Path(path).is_file():
        return 0
    return len(read_jsonl(path))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
