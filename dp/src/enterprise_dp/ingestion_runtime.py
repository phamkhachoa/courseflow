from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.contracts import load_yaml


REPORT_VERSION = 1
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
PASSING_CONNECTOR_STATES = {"running", "healthy"}
PASSING_BACKPRESSURE_STATES = {"clear", "normal", "ok"}
VALID_EVIDENCE_SOURCE_KINDS = {"ci_tool_output", "external_attestation", "synthetic_fixture"}


@dataclass(frozen=True)
class IngestionRuntimeOpsReportResult:
    output_path: Path
    report: dict[str, Any]


@dataclass(frozen=True)
class IngestionRuntimeEvidenceResult:
    output_path: Path
    manifest_path: Path
    evidence: dict[str, Any]
    manifest: dict[str, Any]


def write_ingestion_runtime_evidence_artifact(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str,
    source_kind: str,
    kafka_connect_status_path: str | Path,
    lag_metrics_path: str | Path,
    dlt_report_path: str | Path,
    backpressure_report_path: str | Path,
    offset_ledgers_path: str | Path,
    broker_checks_path: str | Path | None = None,
    generated_at: str | None = None,
    valid_until: str | None = None,
    ci_run_id: str | None = None,
    issuer_tool: str | None = None,
    issuer_tool_version: str | None = None,
) -> IngestionRuntimeEvidenceResult:
    evidence = build_ingestion_runtime_evidence_artifact(
        root,
        environment=environment,
        source_kind=source_kind,
        kafka_connect_status_path=kafka_connect_status_path,
        lag_metrics_path=lag_metrics_path,
        dlt_report_path=dlt_report_path,
        backpressure_report_path=backpressure_report_path,
        offset_ledgers_path=offset_ledgers_path,
        broker_checks_path=broker_checks_path,
        generated_at=generated_at,
        valid_until=valid_until,
        ci_run_id=ci_run_id,
        issuer_tool=issuer_tool,
        issuer_tool_version=issuer_tool_version,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(evidence)}\n", encoding="utf-8")
    manifest = ingestion_runtime_evidence_manifest(target, evidence)
    manifest_path = target.with_name(f"{target.stem}-manifest.json")
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return IngestionRuntimeEvidenceResult(
        output_path=target,
        manifest_path=manifest_path,
        evidence=evidence,
        manifest=manifest,
    )


def build_ingestion_runtime_evidence_artifact(
    root: str | Path,
    *,
    environment: str,
    source_kind: str,
    kafka_connect_status_path: str | Path,
    lag_metrics_path: str | Path,
    dlt_report_path: str | Path,
    backpressure_report_path: str | Path,
    offset_ledgers_path: str | Path,
    broker_checks_path: str | Path | None = None,
    generated_at: str | None = None,
    valid_until: str | None = None,
    ci_run_id: str | None = None,
    issuer_tool: str | None = None,
    issuer_tool_version: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    source_registry_path = platform_root / "platform" / "ingestion" / "source-registry.yaml"
    sources = load_source_registry(platform_root)
    if source_kind not in VALID_EVIDENCE_SOURCE_KINDS:
        raise ValueError(f"source_kind must be one of {sorted(VALID_EVIDENCE_SOURCE_KINDS)}")

    connect_status_path = Path(kafka_connect_status_path)
    lag_path = Path(lag_metrics_path)
    dlt_path = Path(dlt_report_path)
    backpressure_path = Path(backpressure_report_path)
    offset_path = Path(offset_ledgers_path)
    broker_path = Path(broker_checks_path) if broker_checks_path else None
    connect_status = load_json(connect_status_path)
    lag_metrics = load_json(lag_path)
    dlt_report = load_json(dlt_path)
    backpressure_report = load_json(backpressure_path)
    offset_ledgers = load_json(offset_path)
    broker_checks = load_json(broker_path) if broker_path else {}
    connector_status = source_keyed_rows(connect_status, row_keys=("source_id", "sourceId"))
    lag_index = source_keyed_rows(lag_metrics, row_keys=("source_id", "sourceId"))
    dlt_index = source_keyed_rows(dlt_report, row_keys=("source_id", "sourceId"))
    backpressure_index = source_keyed_rows(backpressure_report, row_keys=("source_id", "sourceId"))
    offset_index = source_keyed_rows(offset_ledgers, row_keys=("source_id", "sourceId"))
    broker_index = source_keyed_rows(broker_checks, row_keys=("source_id", "sourceId"))
    input_hashes = {
        "kafka_connect_status": hash_file(connect_status_path),
        "lag_metrics": hash_file(lag_path),
        "dlt_report": hash_file(dlt_path),
        "backpressure_report": hash_file(backpressure_path),
        "offset_ledgers": hash_file(offset_path),
        "broker_checks": hash_file(broker_path) if broker_path else None,
    }
    connectors = [
        normalized_connector_evidence(
            source,
            connector_status.get(str(source.get("sourceId") or "")),
            lag_index.get(str(source.get("sourceId") or "")),
            dlt_index.get(str(source.get("sourceId") or "")),
            backpressure_index.get(str(source.get("sourceId") or "")),
            offset_index.get(str(source.get("sourceId") or "")),
            broker_index.get(str(source.get("sourceId") or "")),
        )
        for source in sorted(sources, key=lambda item: str(item.get("sourceId") or ""))
    ]
    connector_source_ids = {str(connector.get("source_id")) for connector in connectors if connector.get("source_id")}
    p0_source_ids = {str(source.get("sourceId")) for source in sources if source.get("priority") == "P0"}
    return {
        "artifact_type": "ingestion_runtime_evidence.v1",
        "report_version": REPORT_VERSION,
        "evidence_id": stable_id(
            "ingestion-runtime-evidence",
            environment,
            generated,
            source_kind,
            input_hashes,
            hash_file(source_registry_path),
        ),
        "generated_at": generated,
        "valid_until": valid_until,
        "environment": environment,
        "source_kind": source_kind,
        "ci_run_id": ci_run_id,
        "issuer": {
            "tool": issuer_tool,
            "tool_version": issuer_tool_version,
        },
        "source_registry": {
            "uri": source_registry_path.as_posix(),
            "hash": hash_file(source_registry_path),
        },
        "inputs": input_hashes,
        "summary": {
            "source_count": len(sources),
            "p0_source_count": len(p0_source_ids),
            "connector_count": len(connectors),
            "p0_connector_count": len(p0_source_ids & connector_source_ids),
        },
        "connectors": connectors,
    }


def ingestion_runtime_evidence_manifest(evidence_path: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    environment = str(evidence.get("environment") or "unknown")
    source_kind = str(evidence.get("source_kind") or "unknown")
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    return {
        "artifact_type": "ingestion_runtime_evidence_manifest.v1",
        "manifest_version": REPORT_VERSION,
        "manifest_id": stable_id("ingestion-runtime-evidence-manifest", evidence.get("evidence_id"), hash_file(evidence_path)),
        "generated_at": evidence.get("generated_at"),
        "valid_until": evidence.get("valid_until"),
        "environment": environment,
        "source_kind": source_kind,
        "passed": source_kind != "synthetic_fixture",
        "blockers": (
            [
                {
                    "blocker_id": "synthetic_fixture_not_production_evidence",
                    "message": "Synthetic ingestion runtime evidence cannot be used for staging or production readiness.",
                }
            ]
            if source_kind == "synthetic_fixture"
            else []
        ),
        "evidence": {
            "path": evidence_path.as_posix(),
            "hash": hash_file(evidence_path),
            "artifact_type": evidence.get("artifact_type"),
            "evidence_id": evidence.get("evidence_id"),
        },
        "inputs": evidence.get("inputs", {}),
        "source_registry": evidence.get("source_registry", {}),
        "connector_count": summary.get("connector_count", 0),
        "p0_connector_count": summary.get("p0_connector_count", 0),
        "readiness_args": {
            "command": "ingestion-runtime-check",
            "environment": environment,
            "evidence": evidence_path.as_posix(),
            "output": f"build/evidence/event-cdc-ingestion-runtime-{environment}.json",
        },
    }


def write_ingestion_runtime_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
    lag_slo_records: int = 1000,
    lag_slo_seconds: int = 300,
    dlt_unresolved_slo: int = 0,
) -> IngestionRuntimeOpsReportResult:
    report = build_ingestion_runtime_ops_report(
        root,
        environment=environment,
        evidence_path=evidence_path,
        generated_at=generated_at,
        lag_slo_records=lag_slo_records,
        lag_slo_seconds=lag_slo_seconds,
        dlt_unresolved_slo=dlt_unresolved_slo,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return IngestionRuntimeOpsReportResult(output_path=target, report=report)


def build_ingestion_runtime_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
    lag_slo_records: int = 1000,
    lag_slo_seconds: int = 300,
    dlt_unresolved_slo: int = 0,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    evidence_file = Path(evidence_path) if evidence_path else None
    evidence = load_json(evidence_file) if evidence_file else None
    sources = load_source_registry(platform_root)
    connector_index = connector_evidence_index(evidence)
    source_rows = [
        ingestion_runtime_source_row(
            source,
            connector_index.get(str(source.get("sourceId") or "")),
            environment=environment,
            evidence_attached=evidence is not None,
            lag_slo_records=lag_slo_records,
            lag_slo_seconds=lag_slo_seconds,
            dlt_unresolved_slo=dlt_unresolved_slo,
        )
        for source in sorted(sources, key=lambda item: str(item.get("sourceId") or ""))
    ]
    global_checks = ingestion_runtime_global_checks(evidence, environment=environment)
    failed_global_checks = [check for check in global_checks if check.get("passed") is not True]
    p0_failed_sources = [
        row
        for row in source_rows
        if row.get("priority") == "P0" and row.get("passed") is not True
    ]
    warning_sources = [
        row
        for row in source_rows
        if row.get("priority") != "P0" and row.get("passed") is not True
    ]
    passed = not failed_global_checks and not p0_failed_sources
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    return {
        "artifact_type": "event_cdc_ingestion_runtime_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "ingestion-runtime-ops",
            environment,
            generated,
            evidence_reference(evidence_file, evidence),
            lag_slo_records,
            lag_slo_seconds,
            dlt_unresolved_slo,
        ),
        "generated_at": generated,
        "environment": environment,
        "capability_id": "event-cdc-ingestion-runtime",
        "readiness_state": readiness_state,
        "mode": "local_preflight" if environment == "local" and evidence is None else "runtime_evidence",
        "slo": {
            "lag_slo_records": lag_slo_records,
            "lag_slo_seconds": lag_slo_seconds,
            "dlt_unresolved_slo": dlt_unresolved_slo,
        },
        "evidence": evidence_reference(evidence_file, evidence),
        "checks": global_checks,
        "sources": source_rows,
        "decision_board": {
            "p0_failed_sources": [compact_source_row(row) for row in p0_failed_sources[:30]],
            "warning_sources": [compact_source_row(row) for row in warning_sources[:30]],
            "page_now": [
                action
                for row in p0_failed_sources
                for action in row.get("next_actions", [])
                if action.get("priority") == "P0"
            ][:30],
        },
        "summary": ingestion_runtime_summary(
            source_rows,
            failed_global_checks=failed_global_checks,
            p0_failed_sources=p0_failed_sources,
            warning_sources=warning_sources,
        ),
        "passed": passed,
    }


def ingestion_runtime_global_checks(evidence: dict[str, Any] | None, *, environment: str) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    generated_at = parse_timestamp(evidence.get("generated_at")) if isinstance(evidence, dict) else None
    valid_until = parse_timestamp(evidence.get("valid_until")) if isinstance(evidence, dict) else None
    return [
        check(
            "evidence_attached_for_production_like",
            not production_like or evidence is not None,
            {"environment": environment, "attached": evidence is not None},
        ),
        check(
            "evidence_artifact_type_valid",
            evidence is None or evidence.get("artifact_type") == "ingestion_runtime_evidence.v1",
            {"artifact_type": evidence.get("artifact_type") if isinstance(evidence, dict) else None},
        ),
        check(
            "evidence_environment_matches",
            evidence is None or evidence.get("environment") == environment,
            {"expected": environment, "actual": evidence.get("environment") if isinstance(evidence, dict) else None},
        ),
        check(
            "production_evidence_not_synthetic",
            not production_like or (isinstance(evidence, dict) and evidence.get("source_kind") in {"ci_tool_output", "external_attestation"}),
            {"source_kind": evidence.get("source_kind") if isinstance(evidence, dict) else None},
        ),
        check(
            "production_evidence_not_expired",
            not production_like or (generated_at is not None and valid_until is not None and valid_until >= generated_at),
            {
                "generated_at": evidence.get("generated_at") if isinstance(evidence, dict) else None,
                "valid_until": evidence.get("valid_until") if isinstance(evidence, dict) else None,
            },
        ),
    ]


def ingestion_runtime_source_row(
    source: dict[str, Any],
    connector: dict[str, Any] | None,
    *,
    environment: str,
    evidence_attached: bool,
    lag_slo_records: int,
    lag_slo_seconds: int,
    dlt_unresolved_slo: int,
) -> dict[str, Any]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    source_id = str(source.get("sourceId") or "")
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    priority = str(source.get("priority") or "P2")
    dlt = connector.get("dlt") if isinstance(connector, dict) and isinstance(connector.get("dlt"), dict) else {}
    lag = connector.get("lag") if isinstance(connector, dict) and isinstance(connector.get("lag"), dict) else {}
    offset_ledger = (
        connector.get("offset_ledger")
        if isinstance(connector, dict) and isinstance(connector.get("offset_ledger"), dict)
        else {}
    )
    broker = connector.get("broker") if isinstance(connector, dict) and isinstance(connector.get("broker"), dict) else {}
    tasks_total = int_or_none(connector.get("tasks_total")) if isinstance(connector, dict) else None
    tasks_running = int_or_none(connector.get("tasks_running")) if isinstance(connector, dict) else None
    max_lag_records = int_or_none(lag.get("max_lag_records"))
    max_lag_seconds = int_or_none(lag.get("max_lag_seconds"))
    dlt_unresolved_count = int_or_none(dlt.get("unresolved_count"))
    checks = [
        check("runtime_evidence_present", not production_like or evidence_attached, {"environment": environment}),
        check("connector_evidence_present", not production_like or isinstance(connector, dict), {"source_id": source_id}),
        check(
            "connector_deployed_running",
            not production_like or (isinstance(connector, dict) and connector.get("deployment_state") in PASSING_CONNECTOR_STATES),
            {"deployment_state": connector.get("deployment_state") if isinstance(connector, dict) else None},
        ),
        check(
            "connector_tasks_running",
            not production_like or (tasks_total is not None and tasks_total > 0 and tasks_running == tasks_total),
            {"tasks_running": tasks_running, "tasks_total": tasks_total},
        ),
        check(
            "consumer_lag_records_within_slo",
            not production_like or (max_lag_records is not None and max_lag_records <= lag_slo_records),
            {"max_lag_records": max_lag_records, "lag_slo_records": lag_slo_records},
        ),
        check(
            "consumer_lag_seconds_within_slo",
            not production_like or (max_lag_seconds is not None and max_lag_seconds <= lag_slo_seconds),
            {"max_lag_seconds": max_lag_seconds, "lag_slo_seconds": lag_slo_seconds},
        ),
        check(
            "dlt_policy_enabled",
            not production_like or (dlt.get("enabled") is True and non_empty(dlt.get("topic"))),
            {"enabled": dlt.get("enabled"), "topic": dlt.get("topic")},
        ),
        check(
            "dlt_unresolved_within_slo",
            not production_like or (dlt_unresolved_count is not None and dlt_unresolved_count <= dlt_unresolved_slo),
            {"unresolved_count": dlt_unresolved_count, "dlt_unresolved_slo": dlt_unresolved_slo},
        ),
        check(
            "backpressure_clear",
            not production_like or (isinstance(connector, dict) and connector.get("backpressure_state") in PASSING_BACKPRESSURE_STATES),
            {"backpressure_state": connector.get("backpressure_state") if isinstance(connector, dict) else None},
        ),
        check(
            "broker_topic_acl_ready",
            not production_like
            or (
                broker.get("topic_exists") is True
                and broker.get("producer_acl") is True
                and broker.get("consumer_acl") is True
            ),
            {
                "topic_exists": broker.get("topic_exists"),
                "producer_acl": broker.get("producer_acl"),
                "consumer_acl": broker.get("consumer_acl"),
            },
        ),
        check(
            "offset_ledger_attached",
            not production_like or (non_empty(offset_ledger.get("uri")) and is_sha256_hash(offset_ledger.get("hash"))),
            {"uri": offset_ledger.get("uri"), "hash": offset_ledger.get("hash")},
        ),
    ]
    issues = source_issues(checks)
    return {
        "source_id": source_id,
        "product": source.get("product"),
        "domain": source.get("domain"),
        "priority": priority,
        "source_status": source.get("status"),
        "environment": environment,
        "canonical_topic": canonical.get("topic"),
        "bronze_target": canonical.get("bronzeTarget"),
        "schema_subject": canonical.get("schemaSubject"),
        "connector": connector_summary(connector),
        "checks": checks,
        "issues": issues,
        "risk_state": risk_state(issues),
        "next_actions": next_actions(issues, source),
        "passed": not issues,
    }


def source_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "runtime_evidence_present": "runtime_evidence_missing",
        "connector_evidence_present": "connector_evidence_missing",
        "connector_deployed_running": "connector_not_running",
        "connector_tasks_running": "connector_tasks_not_running",
        "consumer_lag_records_within_slo": "lag_records_over_slo",
        "consumer_lag_seconds_within_slo": "lag_seconds_over_slo",
        "dlt_policy_enabled": "dlt_policy_missing",
        "dlt_unresolved_within_slo": "dlt_unresolved_over_slo",
        "backpressure_clear": "backpressure_active",
        "broker_topic_acl_ready": "broker_topic_acl_not_ready",
        "offset_ledger_attached": "offset_ledger_missing",
    }
    return [
        issue_map[check["name"]]
        for check in checks
        if check.get("passed") is not True and check.get("name") in issue_map
    ]


def risk_state(issues: list[str]) -> str:
    if not issues:
        return "ok"
    for issue in (
        "connector_evidence_missing",
        "connector_not_running",
        "connector_tasks_not_running",
        "lag_seconds_over_slo",
        "lag_records_over_slo",
        "dlt_unresolved_over_slo",
        "dlt_policy_missing",
        "backpressure_active",
        "broker_topic_acl_not_ready",
        "offset_ledger_missing",
        "runtime_evidence_missing",
    ):
        if issue in issues:
            return issue
    return "attention"


def next_actions(issues: list[str], source: dict[str, Any]) -> list[dict[str, Any]]:
    owner = source.get("product") or "data-platform-team"
    actions = []
    if "runtime_evidence_missing" in issues or "connector_evidence_missing" in issues:
        actions.append({"priority": "P0", "action": "attach_connector_runtime_evidence", "owner": owner})
    if "connector_not_running" in issues or "connector_tasks_not_running" in issues:
        actions.append({"priority": "P0", "action": "restore_connector_runtime", "owner": owner})
    if "lag_records_over_slo" in issues or "lag_seconds_over_slo" in issues:
        actions.append({"priority": "P0", "action": "reduce_ingestion_lag", "owner": owner})
    if "dlt_policy_missing" in issues:
        actions.append({"priority": "P0", "action": "enable_dlt_policy", "owner": "data-platform-team"})
    if "dlt_unresolved_over_slo" in issues:
        actions.append({"priority": "P0", "action": "triage_dlt_records", "owner": owner})
    if "backpressure_active" in issues:
        actions.append({"priority": "P0", "action": "resolve_backpressure", "owner": owner})
    if "broker_topic_acl_not_ready" in issues:
        actions.append({"priority": "P0", "action": "repair_topic_or_acl", "owner": "data-platform-team"})
    if "offset_ledger_missing" in issues:
        actions.append({"priority": "P0", "action": "attach_source_offset_ledger", "owner": "data-platform-team"})
    return actions or [{"priority": "P3", "action": "no_action", "owner": owner}]


def ingestion_runtime_summary(
    rows: list[dict[str, Any]],
    *,
    failed_global_checks: list[dict[str, Any]],
    p0_failed_sources: list[dict[str, Any]],
    warning_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source_count": len(rows),
        "p0_source_count": sum(1 for row in rows if row.get("priority") == "P0"),
        "running_connector_count": sum(
            1
            for row in rows
            if row.get("connector", {}).get("deployment_state") in PASSING_CONNECTOR_STATES
        ),
        "p0_failed_source_count": len(p0_failed_sources),
        "warning_source_count": len(warning_sources),
        "global_failed_check_count": len(failed_global_checks),
        "by_priority": count_by(rows, "priority"),
        "by_risk_state": count_by(rows, "risk_state"),
    }


def connector_summary(connector: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(connector, dict):
        return {"present": False}
    return {
        "present": True,
        "connector_id": connector.get("connector_id"),
        "connector_type": connector.get("connector_type"),
        "deployment_state": connector.get("deployment_state"),
        "tasks_running": connector.get("tasks_running"),
        "tasks_total": connector.get("tasks_total"),
        "backpressure_state": connector.get("backpressure_state"),
        "lag": connector.get("lag") if isinstance(connector.get("lag"), dict) else {},
        "dlt": connector.get("dlt") if isinstance(connector.get("dlt"), dict) else {},
        "broker": connector.get("broker") if isinstance(connector.get("broker"), dict) else {},
        "offset_ledger": connector.get("offset_ledger") if isinstance(connector.get("offset_ledger"), dict) else {},
        "last_successful_commit_at": connector.get("last_successful_commit_at"),
    }


def normalized_connector_evidence(
    source: dict[str, Any],
    status: dict[str, Any] | None,
    lag: dict[str, Any] | None,
    dlt: dict[str, Any] | None,
    backpressure: dict[str, Any] | None,
    offset_ledger: dict[str, Any] | None,
    broker: dict[str, Any] | None,
) -> dict[str, Any]:
    source_id = str(source.get("sourceId") or "")
    source_type = source.get("source", {}).get("type", "unknown") if isinstance(source.get("source"), dict) else "unknown"
    deployment_state = connector_deployment_state(status)
    tasks_total, tasks_running = connector_task_counts(status)
    connector_id = first_non_empty(
        status.get("connector_id") if isinstance(status, dict) else None,
        status.get("name") if isinstance(status, dict) else None,
        f"{source_id}-connector",
    )
    return {
        "source_id": source_id,
        "connector_id": connector_id,
        "connector_type": first_non_empty(status.get("connector_type") if isinstance(status, dict) else None, source_type),
        "deployment_state": deployment_state,
        "tasks_total": tasks_total,
        "tasks_running": tasks_running,
        "backpressure_state": first_non_empty(
            backpressure.get("state") if isinstance(backpressure, dict) else None,
            backpressure.get("backpressure_state") if isinstance(backpressure, dict) else None,
        ),
        "lag": {
            "max_lag_records": int_or_none((lag or {}).get("max_lag_records")),
            "max_lag_seconds": int_or_none((lag or {}).get("max_lag_seconds")),
        },
        "dlt": {
            "enabled": (dlt or {}).get("enabled"),
            "topic": first_non_empty((dlt or {}).get("topic"), (dlt or {}).get("dlt_topic")),
            "unresolved_count": int_or_none((dlt or {}).get("unresolved_count")),
        },
        "broker": {
            "topic_exists": (broker or {}).get("topic_exists"),
            "producer_acl": (broker or {}).get("producer_acl"),
            "consumer_acl": (broker or {}).get("consumer_acl"),
        },
        "offset_ledger": {
            "uri": first_non_empty((offset_ledger or {}).get("uri"), (offset_ledger or {}).get("path")),
            "hash": (offset_ledger or {}).get("hash"),
        },
        "last_successful_commit_at": (offset_ledger or {}).get("last_successful_commit_at"),
    }


def connector_deployment_state(status: dict[str, Any] | None) -> str | None:
    if not isinstance(status, dict):
        return None
    direct = status.get("deployment_state") or status.get("state")
    if isinstance(direct, str) and direct:
        return direct.lower()
    connector = status.get("connector") if isinstance(status.get("connector"), dict) else {}
    state = connector.get("state")
    return state.lower() if isinstance(state, str) and state else None


def connector_task_counts(status: dict[str, Any] | None) -> tuple[int | None, int | None]:
    if not isinstance(status, dict):
        return None, None
    if isinstance(status.get("tasks_total"), int) or isinstance(status.get("tasks_running"), int):
        return int_or_none(status.get("tasks_total")), int_or_none(status.get("tasks_running"))
    tasks = status.get("tasks")
    if not isinstance(tasks, list):
        return None, None
    total = len([task for task in tasks if isinstance(task, dict)])
    running = len(
        [
            task
            for task in tasks
            if isinstance(task, dict)
            and str(task.get("state") or task.get("status") or "").lower() in PASSING_CONNECTOR_STATES
        ]
    )
    return total, running


def source_keyed_rows(payload: dict[str, Any], *, row_keys: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    rows = payload.get("sources")
    if rows is None:
        rows = payload.get("connectors")
    if rows is None:
        rows = payload.get("rows")
    if isinstance(rows, dict):
        return {
            str(key): value
            for key, value in rows.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
    if not isinstance(rows, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = first_non_empty(*(row.get(key) for key in row_keys))
        if source_id:
            index[source_id] = row
    return index


def compact_source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": row.get("source_id"),
        "product": row.get("product"),
        "domain": row.get("domain"),
        "priority": row.get("priority"),
        "canonical_topic": row.get("canonical_topic"),
        "bronze_target": row.get("bronze_target"),
        "risk_state": row.get("risk_state"),
        "issues": row.get("issues", []),
        "next_actions": row.get("next_actions", []),
    }


def evidence_reference(path: Path | None, evidence: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "attached": path is not None,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path and path.is_file() else None,
        "artifact_type": evidence.get("artifact_type") if isinstance(evidence, dict) else None,
        "generated_at": evidence.get("generated_at") if isinstance(evidence, dict) else None,
        "valid_until": evidence.get("valid_until") if isinstance(evidence, dict) else None,
        "environment": evidence.get("environment") if isinstance(evidence, dict) else None,
        "source_kind": evidence.get("source_kind") if isinstance(evidence, dict) else None,
    }


def connector_evidence_index(evidence: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(evidence, dict) or not isinstance(evidence.get("connectors"), list):
        return {}
    return {
        str(connector.get("source_id")): connector
        for connector in evidence["connectors"]
        if isinstance(connector, dict) and connector.get("source_id")
    }


def load_source_registry(root: Path) -> list[dict[str, Any]]:
    path = root / "platform" / "ingestion" / "source-registry.yaml"
    registry = load_yaml(path)
    sources = registry.get("sources")
    return [source for source in sources if isinstance(source, dict)] if isinstance(sources, list) else []


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None


def first_non_empty(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_sha256_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON artifact must be an object: {path.as_posix()}")
    return data


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
