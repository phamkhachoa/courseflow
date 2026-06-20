from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.contracts import load_yaml


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
ALLOWED_EVIDENCE_SOURCES = {"ci_tool_output", "external_attestation"}
SHA256_PREFIX_LENGTH = 71
CATALOG_RUNTIME_GAPS = {
    "production_catalog_ha",
    "production_catalog_concurrency_locking",
    "managed_catalog_failover",
    "multi_az_catalog_deployment",
    "production_catalog_backup_restore_pitr",
}
FORBIDDEN_SECRET_KEYS = {
    "access_key",
    "api_key",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "secret_key",
    "token",
}
REDACTED_VALUES = {"", "***", "****", "[redacted]", "redacted", "<redacted>"}


@dataclass(frozen=True)
class CatalogRuntimeOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_catalog_runtime_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> CatalogRuntimeOpsReportResult:
    report = build_catalog_runtime_ops_report(
        root,
        environment=environment,
        evidence_path=evidence_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return CatalogRuntimeOpsReportResult(output_path=target, report=report)


def build_catalog_runtime_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    topology_ref, catalog_service = load_catalog_runtime_service(platform_root)
    evidence_ref, evidence = load_catalog_runtime_evidence(evidence_path)
    checks = catalog_runtime_ops_checks(
        environment=environment,
        generated_at=generated,
        evidence_ref=evidence_ref,
        evidence=evidence,
        topology_ref=topology_ref,
        catalog_service=catalog_service,
    )
    failed_checks = [item for item in checks if item.get("passed") is not True]
    service_row = catalog_runtime_service_row(catalog_service, evidence)
    passed = not failed_checks and service_row.get("passed") is True
    return {
        "artifact_type": "catalog_runtime_ops_report.v1",
        "report_version": REPORT_VERSION,
        "capability_id": "production-catalog-runtime",
        "report_id": stable_id("catalog-runtime-ops", environment, generated, topology_ref, evidence_ref),
        "generated_at": generated,
        "environment": environment,
        "release_id": evidence.get("release_id") if isinstance(evidence, dict) else None,
        "change_ticket": evidence.get("change_ticket") if isinstance(evidence, dict) else None,
        "mode": "runtime_attested" if evidence_ref.get("attached") is True else "missing_managed_catalog_runtime_evidence",
        "readiness_state": "production_like_ready" if passed and environment in PRODUCTION_LIKE_ENVIRONMENTS else "not_ready",
        "topology": topology_ref,
        "evidence": evidence_ref,
        "checks": checks,
        "catalog_service": service_row,
        "decision_board": {
            "failed_checks": [compact_check(item) for item in failed_checks[:30]],
            "page_now": [] if passed else [{"priority": "P0", "action": "attach_managed_catalog_runtime_evidence", "owner": "data-platform"}],
        },
        "summary": catalog_runtime_ops_summary(evidence, failed_checks, service_row),
        "passed": passed,
    }


def load_catalog_runtime_service(root: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    path = root / "platform" / "runtime" / "topology.yaml"
    payload = load_yaml(path)
    services = [
        service
        for service in payload.get("runtimeServices", [])
        if isinstance(service, dict) and service.get("p0Required") is True
    ]
    table_format = next((service for service in services if service.get("serviceId") == "table_format"), None)
    return {
        "attached": path.is_file(),
        "uri": path.as_posix(),
        "hash": hash_file(path) if path.is_file() else None,
        "p0_service_count": len(services),
        "catalog_service_found": table_format is not None,
    }, table_format


def load_catalog_runtime_evidence(evidence_path: str | Path | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
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


def catalog_runtime_ops_checks(
    *,
    environment: str,
    generated_at: str,
    evidence_ref: dict[str, Any],
    evidence: dict[str, Any] | None,
    topology_ref: dict[str, Any],
    catalog_service: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    catalog = section(evidence, "catalog")
    deployment = section(evidence, "deployment")
    failover = section(evidence, "failover")
    concurrency = section(evidence, "concurrency")
    backup_restore = section(evidence, "backup_restore")
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
        check("catalog_runtime_service_declared", catalog_service is not None, topology_ref),
        check("evidence_attached", evidence_ref.get("attached") is True, evidence_ref),
        check(
            "evidence_artifact_type_valid",
            isinstance(evidence, dict) and evidence.get("artifact_type") == "managed_catalog_runtime_evidence.v1",
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
        check("catalog_provider_declared", non_empty(catalog.get("provider")), catalog),
        check("catalog_endpoint_declared", non_empty(catalog.get("endpoint_uri")), catalog),
        check("catalog_warehouse_declared", non_empty(catalog.get("warehouse_uri")), catalog),
        check("catalog_service_identity_declared", non_empty(catalog.get("service_identity")), catalog),
        check("catalog_hash_valid", sha256_value_valid(catalog.get("catalog_hash")), catalog),
        check("catalog_service_matches_topology", catalog.get("service_id") == "table_format", {"service_id": catalog.get("service_id")}),
        check("deployment_replicated", int_value(deployment.get("replica_count")) >= 2, deployment),
        check("deployment_multi_az", deployment.get("multi_az") is True and int_value(deployment.get("availability_zones")) >= 2, deployment),
        check("deployment_health_check_passed", deployment.get("health_check_passed") is True, deployment),
        check("managed_or_ha_catalog_mode", deployment.get("managed_service") is True or deployment.get("ha_mode") in {"active_active", "active_standby", "managed_ha"}, deployment),
        check("failover_tested", failover.get("failover_tested") is True, failover),
        check("failover_passed", failover.get("failover_passed") is True, failover),
        check("failover_rto_within_sla", 0 < int_value(failover.get("failover_seconds")) <= 300, failover),
        check("read_after_failover_passed", failover.get("read_after_failover_passed") is True, failover),
        check("write_after_failover_passed", failover.get("write_after_failover_passed") is True, failover),
        check("optimistic_locking_enabled", concurrency.get("optimistic_locking") is True, concurrency),
        check("concurrent_commit_probe_passed", concurrency.get("concurrent_commit_probe_passed") is True, concurrency),
        check("stale_commit_rejected", concurrency.get("stale_commit_rejected") is True, concurrency),
        check("lost_update_prevented", concurrency.get("lost_update_prevented") is True, concurrency),
        check("latest_snapshot_preserved", concurrency.get("latest_snapshot_preserved") is True, concurrency),
        check("cross_engine_read_after_conflict_passed", concurrency.get("cross_engine_read_after_conflict_passed") is True, concurrency),
        check("conflict_observed", int_value(concurrency.get("conflict_count")) >= 1, concurrency),
        check("backup_enabled", backup_restore.get("backup_enabled") is True, backup_restore),
        check("pitr_enabled", backup_restore.get("pitr_enabled") is True, backup_restore),
        check("restore_tested", backup_restore.get("restore_tested") is True, backup_restore),
        check("restore_test_passed", backup_restore.get("restore_test_passed") is True, backup_restore),
        check("backup_rpo_within_sla", 0 <= int_value(backup_restore.get("rpo_minutes")) <= 15, backup_restore),
        check("backup_rto_within_sla", 0 < int_value(backup_restore.get("rto_minutes")) <= 60, backup_restore),
        check("audit_sink_attached", non_empty(audit_sink.get("sink_uri")) and sha256_value_valid(audit_sink.get("events_hash")), audit_sink),
        check("audit_sink_clean", int_value(audit_sink.get("event_count")) > 0 and int_value(audit_sink.get("failed_event_count")) == 0, audit_sink),
        check("external_attestation_attached", attestation.get("attached") is True, attestation),
        check("external_attestation_signature_verified", attestation.get("signature_verified") is True, attestation),
        check("external_attestation_subject_hash_matches", attestation.get("subject_hash_matches") is True, attestation),
        check("attestation_subject_hash_valid", sha256_value_valid(attestation.get("subject_hash")), attestation),
        check("release_binding_hash_matches", hash_matches(binding.get("release_id_hash"), release_id), binding),
        check("change_ticket_binding_hash_matches", hash_matches(binding.get("change_ticket_hash"), change_ticket), binding),
        check("warehouse_binding_hash_matches", hash_matches(binding.get("warehouse_uri_hash"), catalog.get("warehouse_uri")), binding),
        check("service_identity_binding_hash_matches", hash_matches(binding.get("catalog_service_identity_hash"), catalog.get("service_identity")), binding),
        check("upstream_evidence_hashes_bound", upstream_hashes_bound(binding, upstream_hashes), {"bound_hash_count": len(binding.get("upstream_evidence_hashes", [])) if isinstance(binding.get("upstream_evidence_hashes"), list) else 0, "upstream_hash_count": len(upstream_hashes)}),
    ]


def catalog_runtime_service_row(
    service: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(service, dict):
        return {"service_id": None, "passed": False, "issues": ["table_format_runtime_service_missing"]}
    catalog = section(evidence, "catalog")
    if catalog.get("service_id") != service.get("serviceId"):
        issues.append("service_id_mismatch")
    if service.get("haMode") != "catalog_ha_required_in_prod":
        issues.append("catalog_ha_topology_not_required")
    if service.get("backupRequired") is not True:
        issues.append("catalog_backup_topology_not_required")
    if service.get("stateful") is not True:
        issues.append("catalog_stateful_topology_not_declared")
    if service.get("identityMode") != "workload_identity":
        issues.append("workload_identity_required")
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
        "evidence_service_id": catalog.get("service_id"),
        "passed": not issues,
        "issues": sorted(set(issues)),
    }


def catalog_runtime_ops_summary(
    evidence: dict[str, Any] | None,
    failed_checks: list[dict[str, Any]],
    service_row: dict[str, Any],
) -> dict[str, Any]:
    catalog = section(evidence, "catalog")
    deployment = section(evidence, "deployment")
    failover = section(evidence, "failover")
    concurrency = section(evidence, "concurrency")
    backup_restore = section(evidence, "backup_restore")
    audit_sink = section(evidence, "audit_sink")
    return {
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
        "catalog_service_passed": service_row.get("passed"),
        "evidence_source": evidence_source_type(evidence),
        "production_evidence": evidence.get("production_evidence") if isinstance(evidence, dict) else None,
        "sample": evidence.get("sample") if isinstance(evidence, dict) else None,
        "redacted": evidence.get("redacted") if isinstance(evidence, dict) else None,
        "release_id": evidence.get("release_id") if isinstance(evidence, dict) else None,
        "change_ticket": evidence.get("change_ticket") if isinstance(evidence, dict) else None,
        "catalog_provider": catalog.get("provider"),
        "catalog_id": catalog.get("catalog_id"),
        "catalog_hash": catalog.get("catalog_hash"),
        "replica_count": int_value(deployment.get("replica_count")),
        "availability_zones": int_value(deployment.get("availability_zones")),
        "multi_az": deployment.get("multi_az"),
        "health_check_passed": deployment.get("health_check_passed"),
        "managed_service": deployment.get("managed_service"),
        "failover_tested": failover.get("failover_tested"),
        "failover_passed": failover.get("failover_passed"),
        "failover_seconds": int_value(failover.get("failover_seconds")),
        "read_after_failover_passed": failover.get("read_after_failover_passed"),
        "write_after_failover_passed": failover.get("write_after_failover_passed"),
        "optimistic_locking": concurrency.get("optimistic_locking"),
        "concurrent_commit_probe_passed": concurrency.get("concurrent_commit_probe_passed"),
        "stale_commit_rejected": concurrency.get("stale_commit_rejected"),
        "lost_update_prevented": concurrency.get("lost_update_prevented"),
        "latest_snapshot_preserved": concurrency.get("latest_snapshot_preserved"),
        "cross_engine_read_after_conflict_passed": concurrency.get("cross_engine_read_after_conflict_passed"),
        "conflict_count": int_value(concurrency.get("conflict_count")),
        "backup_enabled": backup_restore.get("backup_enabled"),
        "pitr_enabled": backup_restore.get("pitr_enabled"),
        "restore_test_passed": backup_restore.get("restore_test_passed"),
        "rpo_minutes": int_value(backup_restore.get("rpo_minutes")),
        "rto_minutes": int_value(backup_restore.get("rto_minutes")),
        "audit_event_count": int_value(audit_sink.get("event_count")),
        "audit_failed_event_count": int_value(audit_sink.get("failed_event_count")),
    }


def catalog_runtime_ops_closes_gap(gap: str, release_gate_passed: bool) -> bool:
    return release_gate_passed and gap in CATALOG_RUNTIME_GAPS


def strict_catalog_runtime_ops_release_gate_passed(
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
        "catalog_service_matches_topology",
        "deployment_replicated",
        "deployment_multi_az",
        "failover_passed",
        "read_after_failover_passed",
        "write_after_failover_passed",
        "concurrent_commit_probe_passed",
        "stale_commit_rejected",
        "lost_update_prevented",
        "backup_enabled",
        "pitr_enabled",
        "restore_test_passed",
        "audit_sink_clean",
        "external_attestation_signature_verified",
        "external_attestation_subject_hash_matches",
        "release_binding_hash_matches",
        "change_ticket_binding_hash_matches",
        "warehouse_binding_hash_matches",
        "service_identity_binding_hash_matches",
        "upstream_evidence_hashes_bound",
    }
    passed_checks = {str(item.get("name")) for item in checks if isinstance(item, dict) and item.get("passed") is True}
    return (
        report.get("artifact_type") == "catalog_runtime_ops_report.v1"
        and report.get("capability_id") == "production-catalog-runtime"
        and report.get("passed") is True
        and report.get("readiness_state") == "production_like_ready"
        and report.get("mode") == "runtime_attested"
        and environment in PRODUCTION_LIKE_ENVIRONMENTS
        and int_value(summary.get("failed_check_count")) == 0
        and summary.get("catalog_service_passed") is True
        and summary.get("production_evidence") is True
        and summary.get("sample") is False
        and summary.get("redacted") is True
        and int_value(summary.get("replica_count")) >= 2
        and int_value(summary.get("availability_zones")) >= 2
        and summary.get("multi_az") is True
        and summary.get("failover_passed") is True
        and summary.get("stale_commit_rejected") is True
        and summary.get("backup_enabled") is True
        and summary.get("pitr_enabled") is True
        and summary.get("restore_test_passed") is True
        and summary.get("audit_failed_event_count") == 0
        and required_checks.issubset(passed_checks)
    )


def compact_check(item: dict[str, Any]) -> dict[str, Any]:
    return {"name": item.get("name"), "passed": item.get("passed")}


def section(payload: dict[str, Any] | None, name: str) -> dict[str, Any]:
    value = payload.get(name) if isinstance(payload, dict) else None
    return value if isinstance(value, dict) else {}


def evidence_source_type(evidence: dict[str, Any] | None) -> str | None:
    source = evidence.get("evidence_source") if isinstance(evidence, dict) else None
    if isinstance(source, dict):
        value = source.get("type")
        return str(value) if value is not None else None
    return str(source) if source is not None else None


def contains_unredacted_secret_material(payload: object) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_SECRET_KEYS and not is_redacted_value(value):
                return True
            if contains_unredacted_secret_material(value):
                return True
    elif isinstance(payload, list):
        return any(contains_unredacted_secret_material(item) for item in payload)
    return False


def is_redacted_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in REDACTED_VALUES
    return False


def upstream_hashes_bound(binding: dict[str, Any], upstream_hashes: list[str]) -> bool:
    values = binding.get("upstream_evidence_hashes")
    if not isinstance(values, list) or not values:
        return False
    bound = {str(value) for value in values if sha256_value_valid(value)}
    return bool(upstream_hashes) and set(upstream_hashes).issubset(bound)


def hash_matches(hash_value: object, value: object) -> bool:
    if not sha256_value_valid(hash_value) or not non_empty(value):
        return False
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return hash_value == f"sha256:{digest}"


def list_of_dicts(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def evidence_fresh(evidence: dict[str, Any] | None, generated_at: str) -> bool:
    if not isinstance(evidence, dict):
        return False
    valid_until = parse_time(evidence.get("valid_until"))
    generated = parse_time(generated_at)
    return valid_until is not None and generated is not None and valid_until > generated


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256_value_valid(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == SHA256_PREFIX_LENGTH
        and all(char in "0123456789abcdef" for char in value.removeprefix("sha256:"))
    )


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
