from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dagster
from dagster import DagsterInstance, job, op

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


DEFAULT_JOB_NAME = "finance_benefit_reconciliation_runtime_smoke"


@dataclass(frozen=True)
class DagsterOrchestrationSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_dagster_orchestration_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    live_lakehouse_smoke_report_path: str | Path | None = None,
    object_store_smoke_report_path: str | Path | None = None,
    trino_sql_smoke_report_path: str | Path | None = None,
    use_case_id: str = "finance-benefit-reconciliation",
    release_id: str = "local-dagster-orchestration-smoke",
    environment: str = "local",
    generated_at: str | None = None,
) -> DagsterOrchestrationSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    evidence = load_or_create_evidence(
        platform_root,
        target_dir,
        live_lakehouse_smoke_report_path=live_lakehouse_smoke_report_path,
        object_store_smoke_report_path=object_store_smoke_report_path,
        trino_sql_smoke_report_path=trino_sql_smoke_report_path,
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated,
    )

    instance_dir = target_dir / "dagster-instance"
    instance_dir.mkdir(parents=True, exist_ok=True)
    (instance_dir / "dagster.yaml").write_text("telemetry:\n  enabled: false\n", encoding="utf-8")

    orchestration_job = build_finance_orchestration_job(evidence)
    with DagsterInstance.local_temp(tempdir=instance_dir.as_posix()) as instance:
        result = orchestration_job.execute_in_process(instance=instance, raise_on_error=False)
        run_id = result.run_id
        dagster_run = instance.get_run_by_id(run_id)
        event_records = list(instance.all_logs(run_id))
        event_log = dagster_event_log(event_records)
        orchestration_summary = result.output_for_node("summarize_finance_runtime_evidence") if result.success else {}

    failed_checks = failed_dagster_checks(result, dagster_run, event_log, orchestration_summary)
    report = {
        "artifact_type": "dagster_orchestration_smoke_report.v1",
        "report_version": 1,
        "capability_id": "orchestration-run-history",
        "report_id": f"dagster-orchestration-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "runtime_scope": {
            "mode": "local_dagster_in_process_run_history",
            "covered": [
                "dagster_dependency_loaded",
                "dagster_local_instance_created",
                "finance_orchestration_job_executed",
                "dagster_run_id_recorded",
                "dagster_event_log_readback",
                "op_success_events_verified",
                "finance_runtime_evidence_reports_validated",
            ],
            "not_covered": [
                "dagster_daemon_or_schedule_tick_history",
                "distributed_executor_or_kubernetes_run_launcher",
                "production_retry_backoff_runtime_policy",
                "production_backfill_materialization_history",
                "orchestrator_service_identity_and_secret_injection",
                "runtime_security_enforcement",
            ],
        },
        "dagster": {
            "version": dagster.__version__,
            "job_name": DEFAULT_JOB_NAME,
            "run_id": run_id,
            "run_status": run_status_value(dagster_run),
            "instance_dir": instance_dir.as_posix(),
        },
        "input_evidence": evidence_refs(evidence),
        "orchestration_summary": orchestration_summary,
        "event_log": event_log,
        "summary": {
            "job_name": DEFAULT_JOB_NAME,
            "run_id": run_id,
            "run_status": run_status_value(dagster_run),
            "dagster_version": dagster.__version__,
            "event_count": len(event_log),
            "op_success_count": count_event_type(event_log, "STEP_SUCCESS"),
            "pipeline_success_count": count_event_type(event_log, "PIPELINE_SUCCESS"),
            "validated_report_count": orchestration_summary.get("validated_report_count", 0)
            if isinstance(orchestration_summary, dict)
            else 0,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return DagsterOrchestrationSmokeResult(output_path=target, report=report)


def load_or_create_evidence(
    platform_root: Path,
    target_dir: Path,
    *,
    live_lakehouse_smoke_report_path: str | Path | None,
    object_store_smoke_report_path: str | Path | None,
    trino_sql_smoke_report_path: str | Path | None,
    use_case_id: str,
    release_id: str,
    environment: str,
    generated_at: str,
) -> dict[str, dict[str, Any] | None]:
    if live_lakehouse_smoke_report_path:
        live_path = Path(live_lakehouse_smoke_report_path)
        live = load_json(live_path)
    else:
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
        live_path = live_result.output_path
        live = live_result.report

    return {
        "live_lakehouse_smoke": {"path": live_path, "report": live},
        "object_store_commit_smoke": load_optional_report(object_store_smoke_report_path),
        "trino_sql_runtime_smoke": load_optional_report(trino_sql_smoke_report_path),
    }


def load_optional_report(path_value: str | Path | None) -> dict[str, Any] | None:
    if path_value is None:
        return None
    path = Path(path_value)
    return {"path": path, "report": load_json(path)}


def build_finance_orchestration_job(evidence: dict[str, dict[str, Any] | None]):
    @op
    def validate_live_lakehouse_evidence() -> dict[str, Any]:
        return validate_report(
            evidence.get("live_lakehouse_smoke"),
            report_key="live_lakehouse_smoke",
            artifact_type="live_lakehouse_smoke_report.v1",
            required_summary_fields={
                "table_count": 3,
                "parquet_commit_passed_count": 3,
            },
            required_true_fields=["query_passed"],
        )

    @op
    def validate_object_store_evidence() -> dict[str, Any]:
        return validate_report(
            evidence.get("object_store_commit_smoke"),
            report_key="object_store_commit_smoke",
            artifact_type="object_store_commit_smoke_report.v1",
            required_summary_fields={
                "object_count": 3,
                "uploaded_object_count": 3,
                "readback_passed_count": 3,
            },
        )

    @op
    def validate_trino_sql_evidence() -> dict[str, Any]:
        return validate_report(
            evidence.get("trino_sql_runtime_smoke"),
            report_key="trino_sql_runtime_smoke",
            artifact_type="trino_sql_runtime_smoke_report.v1",
            required_summary_fields={
                "row_count": 1,
                "result_row_count": 1,
            },
            required_true_fields=["query_passed"],
        )

    @op
    def summarize_finance_runtime_evidence(
        live_lakehouse: dict[str, Any],
        object_store: dict[str, Any],
        trino_sql: dict[str, Any],
    ) -> dict[str, Any]:
        validations = [live_lakehouse, object_store, trino_sql]
        failed_checks = [
            failure
            for validation in validations
            for failure in validation.get("failed_checks", [])
            if isinstance(failure, dict)
        ]
        return {
            "passed": not failed_checks,
            "validated_report_count": sum(1 for validation in validations if validation.get("present") is True),
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
            "validated_reports": {
                validation.get("report_key"): {
                    "present": validation.get("present"),
                    "passed": validation.get("passed"),
                    "artifact_type": validation.get("artifact_type"),
                    "hash": validation.get("hash"),
                }
                for validation in validations
            },
        }

    @job(name=DEFAULT_JOB_NAME)
    def finance_orchestration_job():
        summarize_finance_runtime_evidence(
            validate_live_lakehouse_evidence(),
            validate_object_store_evidence(),
            validate_trino_sql_evidence(),
        )

    return finance_orchestration_job


def validate_report(
    evidence_ref: dict[str, Any] | None,
    *,
    report_key: str,
    artifact_type: str,
    required_summary_fields: dict[str, int],
    required_true_fields: list[str] | None = None,
) -> dict[str, Any]:
    failed_checks: list[dict[str, Any]] = []
    if evidence_ref is None:
        return {
            "report_key": report_key,
            "present": False,
            "passed": False,
            "artifact_type": None,
            "hash": None,
            "failed_checks": [{"check": f"{report_key}_attached", "message": "Required smoke report is not attached."}],
        }

    path = evidence_ref["path"]
    report = evidence_ref["report"]
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    if report.get("artifact_type") != artifact_type:
        failed_checks.append(
            {
                "check": f"{report_key}_artifact_type",
                "expected": artifact_type,
                "actual": report.get("artifact_type"),
            }
        )
    if report.get("passed") is not True:
        failed_checks.append({"check": f"{report_key}_passed", "passed": report.get("passed")})
    for field, minimum in required_summary_fields.items():
        value = summary.get(field, 0)
        if not isinstance(value, int) or value < minimum:
            failed_checks.append({"check": f"{report_key}_{field}", "minimum": minimum, "actual": value})
    for field in required_true_fields or []:
        if summary.get(field) is not True:
            failed_checks.append({"check": f"{report_key}_{field}", "actual": summary.get(field)})
    return {
        "report_key": report_key,
        "present": True,
        "passed": not failed_checks,
        "artifact_type": report.get("artifact_type"),
        "hash": hash_file(path),
        "summary": summary,
        "failed_checks": failed_checks,
    }


def failed_dagster_checks(
    result: Any,
    dagster_run: Any,
    event_log: list[dict[str, Any]],
    orchestration_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if not result.run_id:
        failed.append({"check": "dagster_run_id_present"})
    if result.success is not True:
        failed.append({"check": "dagster_run_succeeded", "success": result.success})
    if run_status_value(dagster_run) != "SUCCESS":
        failed.append({"check": "dagster_run_status", "actual": run_status_value(dagster_run), "expected": "SUCCESS"})
    if not event_log:
        failed.append({"check": "dagster_event_log_readback"})
    if count_event_type(event_log, "STEP_SUCCESS") < 4:
        failed.append({"check": "dagster_step_success_events", "actual": count_event_type(event_log, "STEP_SUCCESS"), "minimum": 4})
    if count_event_type(event_log, "PIPELINE_SUCCESS") < 1:
        failed.append({"check": "dagster_pipeline_success_event"})
    if not isinstance(orchestration_summary, dict) or orchestration_summary.get("passed") is not True:
        failed.extend(orchestration_summary.get("failed_checks", []) if isinstance(orchestration_summary, dict) else [])
    return failed


def dagster_event_log(event_records: list[Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for record in event_records:
        if not getattr(record, "is_dagster_event", False):
            continue
        dagster_event = record.dagster_event
        event_type = getattr(dagster_event, "event_type_value", None)
        events.append(
            {
                "event_type": event_type if isinstance(event_type, str) else str(event_type),
                "step_key": getattr(dagster_event, "step_key", None),
                "partition": getattr(dagster_event, "partition", None),
                "message": getattr(record, "message", ""),
            }
        )
    return events


def evidence_refs(evidence: dict[str, dict[str, Any] | None]) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for key, value in evidence.items():
        if value is None:
            refs[key] = {"attached": False, "uri": None, "hash": None, "artifact_type": None, "passed": None}
            continue
        path = value["path"]
        report = value["report"]
        refs[key] = {
            "attached": True,
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "artifact_type": report.get("artifact_type"),
            "generated_at": report.get("generated_at"),
            "passed": report.get("passed"),
        }
    return refs


def count_event_type(event_log: list[dict[str, Any]], event_type: str) -> int:
    return sum(1 for event in event_log if event.get("event_type") == event_type)


def run_status_value(dagster_run: Any) -> str | None:
    if dagster_run is None:
        return None
    status = getattr(dagster_run, "status", None)
    value = getattr(status, "value", status)
    return str(value) if value is not None else None
