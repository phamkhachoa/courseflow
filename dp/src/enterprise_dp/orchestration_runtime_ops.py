from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.catalog_runtime_ops import (
    ALLOWED_EVIDENCE_SOURCES,
    PRODUCTION_LIKE_ENVIRONMENTS,
    SUPPORTED_ENVIRONMENTS,
    check,
    compact_check,
    contains_unredacted_secret_material,
    evidence_fresh,
    evidence_source_type,
    hash_matches,
    int_value,
    list_of_dicts,
    non_empty,
    section,
    sha256_value_valid,
    stable_id,
    upstream_hashes_bound,
    utc_now,
)
from enterprise_dp.contracts import load_yaml


REPORT_VERSION = 1
ORCHESTRATION_RUNTIME_GAPS = {
    "dagster_daemon_or_schedule_tick_history",
    "dagster_daemon_ha",
    "dagster_or_airflow_run_history",
    "distributed_executor_or_kubernetes_run_launcher",
    "managed_run_storage_ha",
    "orchestrator_metrics_export",
    "orchestrator_run_history",
    "orchestrator_service_identity_and_secret_injection",
    "production_backfill_materialization_history",
    "production_backfill_scheduler",
    "production_retry_backoff_runtime_policy",
}


@dataclass(frozen=True)
class OrchestrationRuntimeOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_orchestration_runtime_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> OrchestrationRuntimeOpsReportResult:
    report = build_orchestration_runtime_ops_report(
        root,
        environment=environment,
        evidence_path=evidence_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return OrchestrationRuntimeOpsReportResult(output_path=target, report=report)


def build_orchestration_runtime_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    topology_ref, orchestration_service = load_orchestration_runtime_service(platform_root)
    evidence_ref, evidence = load_orchestration_runtime_evidence(evidence_path)
    checks = orchestration_runtime_ops_checks(
        environment=environment,
        generated_at=generated,
        evidence_ref=evidence_ref,
        evidence=evidence,
        topology_ref=topology_ref,
        orchestration_service=orchestration_service,
    )
    failed_checks = [item for item in checks if item.get("passed") is not True]
    service_row = orchestration_runtime_service_row(orchestration_service, evidence)
    passed = not failed_checks and service_row.get("passed") is True
    return {
        "artifact_type": "orchestration_runtime_ops_report.v1",
        "report_version": REPORT_VERSION,
        "capability_id": "production-orchestration-runtime",
        "report_id": stable_id("orchestration-runtime-ops", environment, generated, topology_ref, evidence_ref),
        "generated_at": generated,
        "environment": environment,
        "release_id": evidence.get("release_id") if isinstance(evidence, dict) else None,
        "change_ticket": evidence.get("change_ticket") if isinstance(evidence, dict) else None,
        "mode": "runtime_attested" if evidence_ref.get("attached") is True else "missing_managed_orchestration_runtime_evidence",
        "readiness_state": "production_like_ready" if passed and environment in PRODUCTION_LIKE_ENVIRONMENTS else "not_ready",
        "topology": topology_ref,
        "evidence": evidence_ref,
        "checks": checks,
        "orchestration_service": service_row,
        "decision_board": {
            "failed_checks": [compact_check(item) for item in failed_checks[:30]],
            "page_now": [] if passed else [{"priority": "P0", "action": "attach_managed_orchestration_runtime_evidence", "owner": "data-platform"}],
        },
        "summary": orchestration_runtime_ops_summary(evidence, failed_checks, service_row),
        "passed": passed,
    }


def load_orchestration_runtime_service(root: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    path = root / "platform" / "runtime" / "topology.yaml"
    payload = load_yaml(path)
    services = [
        service
        for service in payload.get("runtimeServices", [])
        if isinstance(service, dict) and service.get("p0Required") is True
    ]
    orchestration = next((service for service in services if service.get("serviceId") == "orchestration"), None)
    return {
        "attached": path.is_file(),
        "uri": path.as_posix(),
        "hash": hash_file(path) if path.is_file() else None,
        "p0_service_count": len(services),
        "orchestration_service_found": orchestration is not None,
    }, orchestration


def load_orchestration_runtime_evidence(evidence_path: str | Path | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if evidence_path is None:
        return {"attached": False}, None
    path = Path(evidence_path)
    if not path.is_file():
        return {"attached": False, "uri": path.as_posix(), "missing": True}, None
    payload = load_json(path)
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": payload.get("artifact_type") if isinstance(payload, dict) else None,
        "environment": payload.get("environment") if isinstance(payload, dict) else None,
        "generated_at": payload.get("generated_at") if isinstance(payload, dict) else None,
        "valid_until": payload.get("valid_until") if isinstance(payload, dict) else None,
        "passed": payload.get("passed") if isinstance(payload, dict) else None,
    }, payload if isinstance(payload, dict) else None


def orchestration_runtime_ops_checks(
    *,
    environment: str,
    generated_at: str,
    evidence_ref: dict[str, Any],
    evidence: dict[str, Any] | None,
    topology_ref: dict[str, Any],
    orchestration_service: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    orchestrator = section(evidence, "orchestrator")
    deployment = section(evidence, "deployment")
    run_launcher = section(evidence, "run_launcher")
    run_storage = section(evidence, "run_storage")
    day2 = section(evidence, "day2")
    security = section(evidence, "security")
    metrics = section(evidence, "metrics")
    source_version = section(evidence, "source_version")
    audit_sink = section(evidence, "audit_sink")
    attestation = section(evidence, "attestation")
    binding = section(evidence, "binding")
    source_type = evidence_source_type(evidence)
    release_id = evidence.get("release_id") if isinstance(evidence, dict) else None
    change_ticket = evidence.get("change_ticket") if isinstance(evidence, dict) else None
    upstream_hashes = [
        str(item.get("artifact_hash"))
        for item in list_of_dicts(evidence.get("upstream_evidence") if isinstance(evidence, dict) else None)
        if sha256_value_valid(item.get("artifact_hash"))
    ]
    return [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("environment_production_like", environment in PRODUCTION_LIKE_ENVIRONMENTS, {"environment": environment}),
        check("topology_attached", topology_ref.get("attached") is True, topology_ref),
        check("orchestration_runtime_service_declared", orchestration_service is not None, topology_ref),
        check("evidence_attached", evidence_ref.get("attached") is True, evidence_ref),
        check(
            "evidence_artifact_type_valid",
            isinstance(evidence, dict) and evidence.get("artifact_type") == "managed_orchestration_runtime_evidence.v1",
            {"artifact_type": evidence.get("artifact_type") if isinstance(evidence, dict) else None},
        ),
        check(
            "evidence_environment_matches",
            isinstance(evidence, dict) and evidence.get("environment") == environment,
            {"evidence_environment": evidence.get("environment") if isinstance(evidence, dict) else None, "report_environment": environment},
        ),
        check("evidence_passed", isinstance(evidence, dict) and evidence.get("passed") is True, {"passed": evidence.get("passed") if isinstance(evidence, dict) else None}),
        check("evidence_fresh", evidence_fresh(evidence, generated_at), {"generated_at": generated_at, "valid_until": evidence.get("valid_until") if isinstance(evidence, dict) else None}),
        check("evidence_source_allowed", source_type in ALLOWED_EVIDENCE_SOURCES, {"evidence_source": source_type}),
        check("production_evidence", isinstance(evidence, dict) and evidence.get("production_evidence") is True, {"production_evidence": evidence.get("production_evidence") if isinstance(evidence, dict) else None}),
        check("sample_evidence_denied", isinstance(evidence, dict) and evidence.get("sample") is False, {"sample": evidence.get("sample") if isinstance(evidence, dict) else None}),
        check("evidence_redacted", isinstance(evidence, dict) and evidence.get("redacted") is True, {"redacted": evidence.get("redacted") if isinstance(evidence, dict) else None}),
        check("plaintext_secret_material_absent", not contains_unredacted_secret_material(evidence), {}),
        check("release_id_declared", non_empty(release_id), {"release_id": release_id}),
        check("change_ticket_declared", non_empty(change_ticket), {"change_ticket": change_ticket}),
        check("git_sha_declared", git_sha_valid(source_version.get("git_sha")), source_version),
        check("image_digest_declared", sha256_value_valid(source_version.get("image_digest")), source_version),
        check("orchestrator_provider_declared", non_empty(orchestrator.get("provider")), orchestrator),
        check("orchestrator_endpoint_declared", non_empty(orchestrator.get("endpoint_uri")), orchestrator),
        check("orchestrator_deployment_declared", non_empty(orchestrator.get("deployment_id")), orchestrator),
        check("orchestrator_service_identity_declared", non_empty(orchestrator.get("service_identity")), orchestrator),
        check("orchestrator_run_history_hash_valid", sha256_value_valid(orchestrator.get("run_history_hash")), orchestrator),
        check("orchestrator_service_matches_topology", orchestrator.get("service_id") == "orchestration", {"service_id": orchestrator.get("service_id")}),
        check("deployment_replicated", int_value(deployment.get("replica_count")) >= 2, deployment),
        check("deployment_multi_az", deployment.get("multi_az") is True and int_value(deployment.get("availability_zones")) >= 2, deployment),
        check("daemon_replicated", int_value(deployment.get("daemon_replica_count")) >= 2, deployment),
        check("scheduler_replicated", int_value(deployment.get("scheduler_replica_count")) >= 2, deployment),
        check("worker_pool_replicated", int_value(deployment.get("worker_replica_count")) >= 2, deployment),
        check("deployment_health_check_passed", deployment.get("health_check_passed") is True, deployment),
        check("managed_or_ha_orchestrator_mode", deployment.get("managed_service") is True or deployment.get("ha_mode") in {"active_active", "active_standby", "managed_ha"}, deployment),
        check(
            "distributed_or_kubernetes_run_launcher",
            run_launcher.get("distributed_executor_enabled") is True or run_launcher.get("kubernetes_run_launcher_enabled") is True,
            run_launcher,
        ),
        check("isolated_run_workers_enabled", run_launcher.get("isolated_run_workers") is True, run_launcher),
        check("run_queue_enabled", run_launcher.get("run_queue_enabled") is True, run_launcher),
        check("managed_run_storage_enabled", run_storage.get("managed_run_storage") is True, run_storage),
        check("persistent_run_storage_enabled", run_storage.get("persistent") is True, run_storage),
        check("run_storage_ha_enabled", run_storage.get("ha_enabled") is True, run_storage),
        check("run_storage_backup_enabled", run_storage.get("backup_enabled") is True, run_storage),
        check("run_history_readback_passed", run_storage.get("run_history_readback_passed") is True, run_storage),
        check("asset_state_readback_passed", run_storage.get("asset_state_readback_passed") is True, run_storage),
        check("schedule_tick_history_passed", day2.get("schedule_tick_history_passed") is True, day2),
        check("retry_policy_verified", day2.get("retry_policy_verified") is True and int_value(day2.get("retry_backoff_seconds")) > 0, day2),
        check("backfill_materialization_history_passed", day2.get("backfill_materialization_history_passed") is True, day2),
        check("production_backfill_scheduler_enabled", day2.get("production_backfill_scheduler") is True, day2),
        check("backfill_materialization_volume", int_value(day2.get("backfill_partition_count")) >= 3 and int_value(day2.get("materialization_event_count")) >= int_value(day2.get("backfill_partition_count")), day2),
        check("worker_restart_recovered", day2.get("worker_restart_recovered") is True, day2),
        check("failed_run_recovered", day2.get("failed_run_recovered") is True, day2),
        check("service_identity_authorized", security.get("service_identity_authorized") is True, security),
        check("secret_injection_verified", security.get("secret_injection_verified") is True, security),
        check("raw_secret_material_not_persisted", security.get("raw_secret_material_persisted") is False, security),
        check("private_network_enabled", security.get("network_private") is True, security),
        check("metrics_exported", metrics.get("metrics_exported") is True, metrics),
        check("run_failure_alert_configured", metrics.get("run_failure_alert_configured") is True, metrics),
        check("scheduler_lag_metric_exported", metrics.get("scheduler_lag_metric_exported") is True, metrics),
        check("audit_sink_attached", non_empty(audit_sink.get("sink_uri")) and sha256_value_valid(audit_sink.get("events_hash")), audit_sink),
        check("audit_sink_clean", int_value(audit_sink.get("event_count")) > 0 and int_value(audit_sink.get("failed_event_count")) == 0, audit_sink),
        check("external_attestation_attached", attestation.get("attached") is True, attestation),
        check("external_attestation_signature_verified", attestation.get("signature_verified") is True, attestation),
        check("external_attestation_subject_hash_matches", attestation.get("subject_hash_matches") is True, attestation),
        check("attestation_subject_hash_valid", sha256_value_valid(attestation.get("subject_hash")), attestation),
        check("release_binding_hash_matches", hash_matches(binding.get("release_id_hash"), release_id), binding),
        check("change_ticket_binding_hash_matches", hash_matches(binding.get("change_ticket_hash"), change_ticket), binding),
        check("orchestrator_deployment_binding_hash_matches", hash_matches(binding.get("orchestrator_deployment_id_hash"), orchestrator.get("deployment_id")), binding),
        check("service_identity_binding_hash_matches", hash_matches(binding.get("orchestrator_service_identity_hash"), orchestrator.get("service_identity")), binding),
        check("run_storage_binding_hash_matches", hash_matches(binding.get("run_storage_uri_hash"), run_storage.get("storage_uri")), binding),
        check("upstream_evidence_hashes_bound", upstream_hashes_bound(binding, upstream_hashes), {"bound_hash_count": len(binding.get("upstream_evidence_hashes", [])) if isinstance(binding.get("upstream_evidence_hashes"), list) else 0, "upstream_hash_count": len(upstream_hashes)}),
    ]


def orchestration_runtime_service_row(
    service: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(service, dict):
        return {"service_id": None, "passed": False, "issues": ["orchestration_runtime_service_missing"]}
    orchestrator = section(evidence, "orchestrator")
    if orchestrator.get("service_id") != service.get("serviceId"):
        issues.append("service_id_mismatch")
    if service.get("haMode") != "scheduler_ha_required_in_prod":
        issues.append("scheduler_ha_topology_not_required")
    if service.get("backupRequired") is not True:
        issues.append("orchestration_backup_topology_not_required")
    if service.get("stateful") is not True:
        issues.append("orchestration_stateful_topology_not_declared")
    if service.get("identityMode") != "service_account_oidc":
        issues.append("service_account_oidc_required")
    return {
        "service_id": service.get("serviceId"),
        "capability": service.get("capability"),
        "technology": service.get("technology"),
        "runtime_role": service.get("runtimeRole"),
        "dr_tier": service.get("drTier"),
        "ha_mode": service.get("haMode"),
        "backup_required": service.get("backupRequired"),
        "stateful": service.get("stateful"),
        "identity_mode": service.get("identityMode"),
        "evidence_service_id": orchestrator.get("service_id"),
        "passed": not issues,
        "issues": sorted(set(issues)),
    }


def orchestration_runtime_ops_summary(
    evidence: dict[str, Any] | None,
    failed_checks: list[dict[str, Any]],
    service_row: dict[str, Any],
) -> dict[str, Any]:
    orchestrator = section(evidence, "orchestrator")
    deployment = section(evidence, "deployment")
    run_launcher = section(evidence, "run_launcher")
    run_storage = section(evidence, "run_storage")
    day2 = section(evidence, "day2")
    security = section(evidence, "security")
    metrics = section(evidence, "metrics")
    source_version = section(evidence, "source_version")
    audit_sink = section(evidence, "audit_sink")
    return {
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
        "orchestration_service_passed": service_row.get("passed"),
        "evidence_source": evidence_source_type(evidence),
        "production_evidence": evidence.get("production_evidence") if isinstance(evidence, dict) else None,
        "sample": evidence.get("sample") if isinstance(evidence, dict) else None,
        "redacted": evidence.get("redacted") if isinstance(evidence, dict) else None,
        "release_id": evidence.get("release_id") if isinstance(evidence, dict) else None,
        "change_ticket": evidence.get("change_ticket") if isinstance(evidence, dict) else None,
        "git_sha": source_version.get("git_sha"),
        "image_digest": source_version.get("image_digest"),
        "orchestrator_provider": orchestrator.get("provider"),
        "deployment_id": orchestrator.get("deployment_id"),
        "service_identity": orchestrator.get("service_identity"),
        "replica_count": int_value(deployment.get("replica_count")),
        "daemon_replica_count": int_value(deployment.get("daemon_replica_count")),
        "scheduler_replica_count": int_value(deployment.get("scheduler_replica_count")),
        "worker_replica_count": int_value(deployment.get("worker_replica_count")),
        "availability_zones": int_value(deployment.get("availability_zones")),
        "multi_az": deployment.get("multi_az"),
        "distributed_executor_enabled": run_launcher.get("distributed_executor_enabled"),
        "kubernetes_run_launcher_enabled": run_launcher.get("kubernetes_run_launcher_enabled"),
        "managed_run_storage": run_storage.get("managed_run_storage"),
        "run_storage_ha_enabled": run_storage.get("ha_enabled"),
        "run_storage_backup_enabled": run_storage.get("backup_enabled"),
        "run_history_readback_passed": run_storage.get("run_history_readback_passed"),
        "schedule_tick_history_passed": day2.get("schedule_tick_history_passed"),
        "retry_policy_verified": day2.get("retry_policy_verified"),
        "retry_backoff_seconds": int_value(day2.get("retry_backoff_seconds")),
        "backfill_materialization_history_passed": day2.get("backfill_materialization_history_passed"),
        "production_backfill_scheduler": day2.get("production_backfill_scheduler"),
        "backfill_partition_count": int_value(day2.get("backfill_partition_count")),
        "materialization_event_count": int_value(day2.get("materialization_event_count")),
        "worker_restart_recovered": day2.get("worker_restart_recovered"),
        "service_identity_authorized": security.get("service_identity_authorized"),
        "secret_injection_verified": security.get("secret_injection_verified"),
        "metrics_exported": metrics.get("metrics_exported"),
        "run_failure_alert_configured": metrics.get("run_failure_alert_configured"),
        "audit_event_count": int_value(audit_sink.get("event_count")),
        "audit_failed_event_count": int_value(audit_sink.get("failed_event_count")),
    }


def orchestration_runtime_ops_closes_gap(gap: str, release_gate_passed: bool) -> bool:
    return release_gate_passed and gap in ORCHESTRATION_RUNTIME_GAPS


def git_sha_valid(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def strict_orchestration_runtime_ops_release_gate_passed(
    report: dict[str, Any] | None,
    *,
    target_environment: str | None = None,
) -> bool:
    if not isinstance(report, dict):
        return False
    environment = report.get("environment")
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    if target_environment in PRODUCTION_LIKE_ENVIRONMENTS and environment != target_environment:
        return False
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    required_checks = {
        "environment_production_like",
        "evidence_artifact_type_valid",
        "evidence_environment_matches",
        "evidence_passed",
        "evidence_fresh",
        "evidence_source_allowed",
        "production_evidence",
        "sample_evidence_denied",
        "evidence_redacted",
        "plaintext_secret_material_absent",
        "release_id_declared",
        "change_ticket_declared",
        "git_sha_declared",
        "image_digest_declared",
        "orchestrator_service_matches_topology",
        "deployment_replicated",
        "deployment_multi_az",
        "daemon_replicated",
        "scheduler_replicated",
        "worker_pool_replicated",
        "distributed_or_kubernetes_run_launcher",
        "isolated_run_workers_enabled",
        "run_queue_enabled",
        "managed_run_storage_enabled",
        "run_storage_ha_enabled",
        "run_storage_backup_enabled",
        "run_history_readback_passed",
        "asset_state_readback_passed",
        "schedule_tick_history_passed",
        "retry_policy_verified",
        "backfill_materialization_history_passed",
        "production_backfill_scheduler_enabled",
        "worker_restart_recovered",
        "failed_run_recovered",
        "service_identity_authorized",
        "secret_injection_verified",
        "raw_secret_material_not_persisted",
        "metrics_exported",
        "run_failure_alert_configured",
        "audit_sink_clean",
        "external_attestation_signature_verified",
        "external_attestation_subject_hash_matches",
        "release_binding_hash_matches",
        "change_ticket_binding_hash_matches",
        "orchestrator_deployment_binding_hash_matches",
        "service_identity_binding_hash_matches",
        "run_storage_binding_hash_matches",
        "upstream_evidence_hashes_bound",
    }
    passed_checks = {str(item.get("name")) for item in checks if isinstance(item, dict) and item.get("passed") is True}
    distributed_or_kubernetes = (
        summary.get("distributed_executor_enabled") is True
        or summary.get("kubernetes_run_launcher_enabled") is True
    )
    return (
        report.get("artifact_type") == "orchestration_runtime_ops_report.v1"
        and report.get("capability_id") == "production-orchestration-runtime"
        and report.get("passed") is True
        and report.get("readiness_state") == "production_like_ready"
        and report.get("mode") == "runtime_attested"
        and environment in PRODUCTION_LIKE_ENVIRONMENTS
        and int_value(summary.get("failed_check_count")) == 0
        and summary.get("orchestration_service_passed") is True
        and summary.get("production_evidence") is True
        and summary.get("sample") is False
        and summary.get("redacted") is True
        and int_value(summary.get("replica_count")) >= 2
        and int_value(summary.get("availability_zones")) >= 2
        and summary.get("multi_az") is True
        and distributed_or_kubernetes
        and summary.get("managed_run_storage") is True
        and summary.get("run_storage_ha_enabled") is True
        and summary.get("run_history_readback_passed") is True
        and summary.get("schedule_tick_history_passed") is True
        and summary.get("retry_policy_verified") is True
        and int_value(summary.get("retry_backoff_seconds")) > 0
        and summary.get("backfill_materialization_history_passed") is True
        and summary.get("production_backfill_scheduler") is True
        and summary.get("service_identity_authorized") is True
        and summary.get("secret_injection_verified") is True
        and summary.get("metrics_exported") is True
        and summary.get("audit_failed_event_count") == 0
        and required_checks.issubset(passed_checks)
    )
