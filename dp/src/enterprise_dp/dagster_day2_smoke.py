from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dagster
from dagster import AssetMaterialization, DagsterInstance, RetryPolicy, job, op

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.dagster_orchestration_smoke import count_event_type, dagster_event_log, run_status_value
from enterprise_dp.event_backbone_smoke import stable_id
from enterprise_dp.live_lakehouse_smoke import DEFAULT_GENERATED_AT


DEFAULT_JOB_NAME = "finance_benefit_reconciliation_day2_controls"
DEFAULT_SCHEDULE_NAME = "finance_benefit_reconciliation_daily"
DEFAULT_CRON = "15 1 * * *"
DEFAULT_BACKFILL_ID = "finance-benefit-reconciliation-backfill-20260115"
DEFAULT_PARTITIONS = ("2026-01-13", "2026-01-14", "2026-01-15")
DEFAULT_RETRY_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 1


@dataclass(frozen=True)
class DagsterDay2SmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_dagster_day2_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    release_id: str = "local-dagster-day2-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    schedule_name: str = DEFAULT_SCHEDULE_NAME,
    cron_schedule: str = DEFAULT_CRON,
    backfill_id: str = DEFAULT_BACKFILL_ID,
    partitions: tuple[str, ...] = DEFAULT_PARTITIONS,
) -> DagsterDay2SmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    instance_dir = target_dir / "dagster-instance"
    materialization_dir = target_dir / "backfill-materializations"
    schedule_tick_path = target_dir / "schedule" / "schedule-tick-history.json"
    backfill_manifest_path = target_dir / "backfill-materializations" / "backfill-materialization-history.json"
    instance_dir.mkdir(parents=True, exist_ok=True)
    (instance_dir / "dagster.yaml").write_text("telemetry:\n  enabled: false\n", encoding="utf-8")

    day2_job = build_day2_job(
        backfill_id=backfill_id,
        partitions=partitions,
        materialization_dir=materialization_dir,
    )
    with DagsterInstance.local_temp(tempdir=instance_dir.as_posix()) as instance:
        result = day2_job.execute_in_process(instance=instance, raise_on_error=False)
        run_id = result.run_id
        dagster_run = instance.get_run_by_id(run_id)
        event_log = dagster_event_log(list(instance.all_logs(run_id)))
        orchestration_summary = result.output_for_node("summarize_day2_controls") if result.success else {}

    schedule_tick_history = write_schedule_tick_history(
        schedule_tick_path,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        schedule_name=schedule_name,
        cron_schedule=cron_schedule,
        run_id=run_id,
        run_status=run_status_value(dagster_run),
    )
    materialization_history = write_backfill_materialization_history(
        backfill_manifest_path,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        backfill_id=backfill_id,
        run_id=run_id,
        materialization_dir=materialization_dir,
        materialization_events=materialization_events(event_log),
    )
    failed_checks = failed_day2_checks(
        result=result,
        dagster_run=dagster_run,
        event_log=event_log,
        orchestration_summary=orchestration_summary,
        schedule_tick_history=schedule_tick_history,
        materialization_history=materialization_history,
        expected_partition_count=len(partitions),
    )
    report = build_dagster_day2_smoke_report(
        root=platform_root,
        output_dir=target_dir,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        schedule_name=schedule_name,
        cron_schedule=cron_schedule,
        backfill_id=backfill_id,
        partitions=partitions,
        instance_dir=instance_dir,
        run_id=run_id,
        run_status=run_status_value(dagster_run),
        event_log=event_log,
        orchestration_summary=orchestration_summary,
        schedule_tick_history=schedule_tick_history,
        schedule_tick_path=schedule_tick_path,
        materialization_history=materialization_history,
        backfill_manifest_path=backfill_manifest_path,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return DagsterDay2SmokeResult(output_path=target, report=report)


def build_day2_job(*, backfill_id: str, partitions: tuple[str, ...], materialization_dir: Path):
    @op(retry_policy=RetryPolicy(max_retries=DEFAULT_RETRY_MAX_RETRIES, delay=DEFAULT_RETRY_BACKOFF_SECONDS))
    def transient_retry_probe(context) -> dict[str, Any]:
        if context.retry_number == 0:
            raise RuntimeError("transient retry probe for Dagster day-2 smoke")
        return {
            "passed": True,
            "retry_number": context.retry_number,
            "max_retries": DEFAULT_RETRY_MAX_RETRIES,
            "backoff_seconds": DEFAULT_RETRY_BACKOFF_SECONDS,
        }

    @op
    def materialize_backfill_partitions(context) -> dict[str, Any]:
        materialization_dir.mkdir(parents=True, exist_ok=True)
        partition_refs: list[dict[str, Any]] = []
        for partition in partitions:
            partition_path = materialization_dir / f"gold.finance_benefit_reconciliation.{partition}.json"
            payload = {
                "artifact_type": "backfill_partition_materialization.v1",
                "backfill_id": backfill_id,
                "partition": partition,
                "data_product": "gold.finance_benefit_reconciliation",
                "row_count": 4,
                "idempotency_key": stable_id(backfill_id, partition),
            }
            partition_path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")
            context.log_event(
                AssetMaterialization(
                    asset_key="gold.finance_benefit_reconciliation",
                    partition=partition,
                    metadata={
                        "backfill_id": backfill_id,
                        "partition_path": partition_path.as_posix(),
                        "partition_hash": hash_file(partition_path),
                        "row_count": 4,
                    },
                )
            )
            partition_refs.append(
                {
                    "partition": partition,
                    "uri": partition_path.as_posix(),
                    "hash": hash_file(partition_path),
                    "row_count": 4,
                }
            )
        return {
            "passed": True,
            "backfill_id": backfill_id,
            "partition_count": len(partition_refs),
            "partitions": partition_refs,
        }

    @op
    def summarize_day2_controls(retry_probe: dict[str, Any], backfill: dict[str, Any]) -> dict[str, Any]:
        failed_checks = []
        if retry_probe.get("passed") is not True:
            failed_checks.append({"check": "retry_probe_passed", "probe": retry_probe})
        if backfill.get("passed") is not True:
            failed_checks.append({"check": "backfill_materialization_passed", "probe": backfill})
        return {
            "passed": not failed_checks,
            "retry_probe": retry_probe,
            "backfill": backfill,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        }

    @job(name=DEFAULT_JOB_NAME)
    def dagster_day2_job():
        summarize_day2_controls(transient_retry_probe(), materialize_backfill_partitions())

    return dagster_day2_job


def write_schedule_tick_history(
    path: Path,
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    schedule_name: str,
    cron_schedule: str,
    run_id: str,
    run_status: str | None,
) -> dict[str, Any]:
    tick = {
        "tick_id": stable_id("dagster-schedule-tick", environment, release_id, schedule_name, run_id),
        "schedule_name": schedule_name,
        "cron_schedule": cron_schedule,
        "scheduled_at": generated_at,
        "run_id": run_id,
        "run_status": run_status,
        "status": "SUCCESS" if run_status == "SUCCESS" else "FAILED",
    }
    payload = {
        "artifact_type": "dagster_schedule_tick_history.v1",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "mode": "local_schedule_tick_ledger_from_dagster_run",
        "ticks": [tick],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")
    return {
        "path": path.as_posix(),
        "hash": hash_file(path),
        "tick_count": 1,
        "passed": tick["status"] == "SUCCESS",
        "ticks": [tick],
    }


def write_backfill_materialization_history(
    path: Path,
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    backfill_id: str,
    run_id: str,
    materialization_dir: Path,
    materialization_events: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "artifact_type": "dagster_backfill_materialization_history.v1",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "backfill_id": backfill_id,
        "run_id": run_id,
        "materialization_dir": materialization_dir.as_posix(),
        "materializations": materialization_events,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")
    return {
        "path": path.as_posix(),
        "hash": hash_file(path),
        "backfill_id": backfill_id,
        "materialization_count": len(materialization_events),
        "partition_count": len({event.get("partition") for event in materialization_events}),
        "passed": len(materialization_events) >= 3,
        "materializations": materialization_events,
    }


def failed_day2_checks(
    *,
    result: Any,
    dagster_run: Any,
    event_log: list[dict[str, Any]],
    orchestration_summary: dict[str, Any],
    schedule_tick_history: dict[str, Any],
    materialization_history: dict[str, Any],
    expected_partition_count: int,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if result.success is not True:
        failed.append({"check": "dagster_day2_run_succeeded", "success": result.success})
    if run_status_value(dagster_run) != "SUCCESS":
        failed.append({"check": "dagster_day2_run_status", "actual": run_status_value(dagster_run)})
    if count_event_type(event_log, "STEP_UP_FOR_RETRY") < 1:
        failed.append({"check": "dagster_retry_event_recorded"})
    if count_event_type(event_log, "STEP_RESTARTED") < 1:
        failed.append({"check": "dagster_retry_restart_recorded"})
    if retry_summary(orchestration_summary).get("retry_number", 0) < 1:
        failed.append({"check": "dagster_retry_probe_completed_after_retry", "summary": orchestration_summary})
    if int(retry_summary(orchestration_summary).get("backoff_seconds", 0)) <= 0:
        failed.append({"check": "dagster_retry_policy_backoff_positive", "summary": orchestration_summary})
    if schedule_tick_history.get("passed") is not True:
        failed.append({"check": "schedule_tick_history_passed", "history": schedule_tick_history})
    if int(schedule_tick_history.get("tick_count", 0)) < 1:
        failed.append({"check": "schedule_tick_count", "minimum": 1})
    if materialization_history.get("passed") is not True:
        failed.append({"check": "backfill_materialization_history_passed", "history": materialization_history})
    if int(materialization_history.get("partition_count", 0)) < expected_partition_count:
        failed.append(
            {
                "check": "backfill_partition_materialization_count",
                "minimum": expected_partition_count,
                "actual": materialization_history.get("partition_count", 0),
            }
        )
    if count_event_type(event_log, "ASSET_MATERIALIZATION") < expected_partition_count:
        failed.append(
            {
                "check": "dagster_asset_materialization_events",
                "minimum": expected_partition_count,
                "actual": count_event_type(event_log, "ASSET_MATERIALIZATION"),
            }
        )
    if not isinstance(orchestration_summary, dict) or orchestration_summary.get("passed") is not True:
        failed.extend(orchestration_summary.get("failed_checks", []) if isinstance(orchestration_summary, dict) else [])
    return failed


def build_dagster_day2_smoke_report(
    *,
    root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    schedule_name: str,
    cron_schedule: str,
    backfill_id: str,
    partitions: tuple[str, ...],
    instance_dir: Path,
    run_id: str,
    run_status: str | None,
    event_log: list[dict[str, Any]],
    orchestration_summary: dict[str, Any],
    schedule_tick_history: dict[str, Any],
    schedule_tick_path: Path,
    materialization_history: dict[str, Any],
    backfill_manifest_path: Path,
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = {
        "job_name": DEFAULT_JOB_NAME,
        "run_id": run_id,
        "run_status": run_status,
        "dagster_version": dagster.__version__,
        "schedule_name": schedule_name,
        "cron_schedule": cron_schedule,
        "schedule_tick_count": schedule_tick_history.get("tick_count", 0),
        "schedule_tick_history_passed": schedule_tick_history.get("passed") is True,
        "retry_policy_max_retries": DEFAULT_RETRY_MAX_RETRIES,
        "retry_policy_backoff_seconds": DEFAULT_RETRY_BACKOFF_SECONDS,
        "retry_event_count": count_event_type(event_log, "STEP_UP_FOR_RETRY"),
        "retry_restart_count": count_event_type(event_log, "STEP_RESTARTED"),
        "retry_policy_verified": count_event_type(event_log, "STEP_UP_FOR_RETRY") >= 1
        and count_event_type(event_log, "STEP_RESTARTED") >= 1
        and retry_summary(orchestration_summary).get("retry_number", 0) >= 1
        and int(retry_summary(orchestration_summary).get("backoff_seconds", 0)) > 0,
        "backfill_id": backfill_id,
        "backfill_partition_count": len(partitions),
        "asset_materialization_event_count": count_event_type(event_log, "ASSET_MATERIALIZATION"),
        "backfill_materialization_history_passed": materialization_history.get("passed") is True,
        "distributed_executor_verified": False,
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    return {
        "artifact_type": "dagster_day2_smoke_report.v1",
        "report_version": 1,
        "capability_id": "orchestration-run-history",
        "report_id": stable_id("dagster-day2-smoke", environment, release_id, run_id),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_dagster_in_process_day2_controls",
            "covered": [
                "dagster_retry_policy_event_history",
                "dagster_schedule_tick_history_ledger",
                "dagster_asset_materialization_history_for_backfill_partitions",
                "backfill_partition_materialization_manifest",
            ],
            "not_covered": [
                "dagster_daemon_ha",
                "distributed_executor_or_kubernetes_run_launcher",
                "production_backfill_scheduler",
                "managed_run_storage_ha",
                "orchestrator_metrics_export",
            ],
        },
        "dagster": {
            "version": dagster.__version__,
            "job_name": DEFAULT_JOB_NAME,
            "run_id": run_id,
            "run_status": run_status,
            "instance_dir": instance_dir.as_posix(),
            "root": root.as_posix(),
            "output_dir": output_dir.as_posix(),
        },
        "schedule_tick_history": {
            "uri": schedule_tick_path.as_posix(),
            "hash": hash_file(schedule_tick_path) if schedule_tick_path.is_file() else None,
            "schedule_name": schedule_name,
            "cron_schedule": cron_schedule,
            "tick_count": schedule_tick_history.get("tick_count", 0),
        },
        "backfill_materialization_history": {
            "uri": backfill_manifest_path.as_posix(),
            "hash": hash_file(backfill_manifest_path) if backfill_manifest_path.is_file() else None,
            "backfill_id": backfill_id,
            "partition_count": materialization_history.get("partition_count", 0),
        },
        "orchestration_summary": orchestration_summary,
        "event_log": event_log,
        "summary": summary,
        "passed": not failed_checks,
    }


def materialization_events(event_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for event in event_log:
        if event.get("event_type") != "ASSET_MATERIALIZATION":
            continue
        events.append(
            {
                "event_type": event.get("event_type"),
                "step_key": event.get("step_key"),
                "partition": event.get("partition"),
                "message": event.get("message"),
            }
        )
    return events


def retry_summary(orchestration_summary: dict[str, Any]) -> dict[str, Any]:
    retry = orchestration_summary.get("retry_probe") if isinstance(orchestration_summary, dict) else {}
    return retry if isinstance(retry, dict) else {}
