from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.contracts import load_yaml


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
SHA256_PREFIX_LENGTH = 71


@dataclass(frozen=True)
class SecretRotationOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_secret_rotation_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> SecretRotationOpsReportResult:
    report = build_secret_rotation_ops_report(
        root,
        environment=environment,
        evidence_path=evidence_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SecretRotationOpsReportResult(output_path=target, report=report)


def build_secret_rotation_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    topology_ref, p0_services = load_p0_runtime_services(platform_root)
    evidence_ref, evidence = load_secret_rotation_evidence(evidence_path)
    service_rows = [
        secret_rotation_service_row(
            service,
            secret_evidence_by_service(evidence).get(str(service.get("serviceId") or "")),
        )
        for service in p0_services
    ]
    checks = secret_rotation_ops_checks(
        environment=environment,
        generated_at=generated,
        evidence_ref=evidence_ref,
        evidence=evidence,
        p0_services=p0_services,
        service_rows=service_rows,
    )
    failed_checks = [item for item in checks if item.get("passed") is not True]
    failed_services = [row for row in service_rows if row.get("passed") is not True]
    passed = not failed_checks and not failed_services
    return {
        "artifact_type": "secret_rotation_ops_report.v1",
        "report_version": REPORT_VERSION,
        "capability_id": "production-secret-rotation",
        "report_id": stable_id("secret-rotation-ops", environment, generated, topology_ref, evidence_ref),
        "generated_at": generated,
        "environment": environment,
        "mode": "managed_secret_manager_evidence" if evidence_ref.get("attached") else "missing_managed_secret_manager_evidence",
        "readiness_state": "production_like_ready" if passed and environment in PRODUCTION_LIKE_ENVIRONMENTS else "not_ready",
        "topology": topology_ref,
        "evidence": evidence_ref,
        "checks": checks,
        "services": service_rows,
        "decision_board": {
            "failed_services": [compact_secret_service_row(row) for row in failed_services[:30]],
            "page_now": [
                action
                for row in failed_services
                for action in row.get("next_actions", [])
                if isinstance(action, dict) and action.get("priority") == "P0"
            ][:50],
        },
        "summary": secret_rotation_ops_summary(service_rows, failed_checks, evidence),
        "passed": passed,
    }


def load_p0_runtime_services(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = root / "platform" / "runtime" / "topology.yaml"
    payload = load_yaml(path)
    services = [
        service
        for service in payload.get("runtimeServices", [])
        if isinstance(service, dict) and service.get("p0Required") is True
    ]
    return {
        "attached": path.is_file(),
        "uri": path.as_posix(),
        "hash": hash_file(path) if path.is_file() else None,
        "p0_service_count": len(services),
    }, services


def load_secret_rotation_evidence(evidence_path: str | Path | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not evidence_path:
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


def secret_rotation_ops_checks(
    *,
    environment: str,
    generated_at: str,
    evidence_ref: dict[str, Any],
    evidence: dict[str, Any] | None,
    p0_services: list[dict[str, Any]],
    service_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    controls = evidence.get("controls") if isinstance(evidence, dict) and isinstance(evidence.get("controls"), dict) else {}
    secret_manager = (
        evidence.get("secret_manager")
        if isinstance(evidence, dict) and isinstance(evidence.get("secret_manager"), dict)
        else {}
    )
    audit_sink = evidence.get("audit_sink") if isinstance(evidence, dict) and isinstance(evidence.get("audit_sink"), dict) else {}
    attestation = (
        evidence.get("attestation")
        if isinstance(evidence, dict) and isinstance(evidence.get("attestation"), dict)
        else {}
    )
    return [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("environment_production_like", environment in PRODUCTION_LIKE_ENVIRONMENTS, {"environment": environment}),
        check("evidence_attached", evidence_ref.get("attached") is True, evidence_ref),
        check(
            "evidence_artifact_type_valid",
            isinstance(evidence, dict) and evidence.get("artifact_type") == "managed_secret_rotation_evidence.v1",
            {"artifact_type": evidence.get("artifact_type") if isinstance(evidence, dict) else None},
        ),
        check(
            "evidence_environment_matches",
            isinstance(evidence, dict) and evidence.get("environment") == environment,
            {"evidence_environment": evidence.get("environment") if isinstance(evidence, dict) else None, "report_environment": environment},
        ),
        check("evidence_passed", isinstance(evidence, dict) and evidence.get("passed") is True, {"passed": evidence.get("passed") if isinstance(evidence, dict) else None}),
        check("evidence_fresh", evidence_fresh(evidence, generated_at), {"generated_at": generated_at, "valid_until": evidence.get("valid_until") if isinstance(evidence, dict) else None}),
        check("p0_runtime_services_declared", bool(p0_services), {"p0_service_count": len(p0_services)}),
        check(
            "p0_runtime_service_secret_coverage",
            bool(p0_services) and len(service_rows) == len(p0_services) and all(row.get("evidence_attached") is True for row in service_rows),
            {"p0_service_count": len(p0_services), "covered_service_count": sum(1 for row in service_rows if row.get("evidence_attached") is True)},
        ),
        check("managed_secret_manager_ha", controls.get("managed_secret_manager_ha") is True, controls),
        check("workload_identity_federation", controls.get("workload_identity_federation") is True, controls),
        check("kms_hsm_custody", controls.get("kms_hsm_custody") is True, controls),
        check("rotation_policy_enforced", controls.get("rotation_policy_enforced") is True, controls),
        check("old_versions_denied", controls.get("old_versions_denied") is True, controls),
        check("unauthorized_identity_denied", controls.get("unauthorized_identity_denied") is True, controls),
        check("missing_secret_denied", controls.get("missing_secret_denied") is True, controls),
        check("orchestrator_injection_redacted", controls.get("orchestrator_injection_redacted") is True, controls),
        check("plaintext_secret_material_absent", controls.get("plaintext_secret_material_persisted") is False, controls),
        check("secret_manager_provider_declared", non_empty(secret_manager.get("provider")), secret_manager),
        check("secret_manager_kms_key_declared", sha256_value_valid(secret_manager.get("kms_key_hash")) and non_empty(secret_manager.get("kms_key_id")), secret_manager),
        check("audit_sink_attached", non_empty(audit_sink.get("sink_uri")) and sha256_value_valid(audit_sink.get("events_hash")), audit_sink),
        check("audit_sink_clean", audit_sink.get("failed_event_count") == 0 and int_value(audit_sink.get("event_count", 0)) > 0, audit_sink),
        check("audit_sink_siem_exported", audit_sink.get("siem_exported") is True, audit_sink),
        check("external_attestation_attached", attestation.get("attached") is True, attestation),
        check("external_attestation_signature_verified", attestation.get("signature_verified") is True, attestation),
        check("external_attestation_subject_hash_matches", attestation.get("subject_hash_matches") is True, attestation),
        check(
            "prod_secret_manager_dr_evidence",
            environment != "prod"
            or (
                secret_manager.get("cross_region_replication") is True
                and secret_manager.get("backup_restore_tested") is True
            ),
            secret_manager,
        ),
    ]


def secret_rotation_service_row(
    service: dict[str, Any],
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    issues: list[str] = []
    service_id = str(service.get("serviceId") or "")
    if not isinstance(evidence, dict):
        issues.append("secret_evidence_missing")
        evidence = {}
    required = {
        "secret_handle_declared": non_empty(evidence.get("secret_handle")),
        "service_identity_declared": non_empty(evidence.get("service_identity")),
        "active_version_declared": non_empty(evidence.get("active_version")),
        "kms_key_id_declared": non_empty(evidence.get("kms_key_id")),
        "key_hash_valid": sha256_value_valid(evidence.get("key_hash")),
        "rotation_policy_declared": non_empty(evidence.get("rotation_policy_id")),
        "latest_rotation_declared": non_empty(evidence.get("latest_rotation_at")),
        "old_version_revoked": evidence.get("old_version_revoked") is True,
        "old_version_denied": evidence.get("old_version_denied") is True,
        "unauthorized_identity_denied": evidence.get("unauthorized_identity_denied") is True,
        "missing_secret_denied": evidence.get("missing_secret_denied") is True,
        "plaintext_absent": evidence.get("plaintext_secret_material_persisted") is False,
    }
    issues.extend(name for name, passed in required.items() if not passed)
    if service.get("identityMode") == "service_account_oidc" and evidence.get("identity_mode") != "workload_identity":
        issues.append("workload_identity_required")
    if service.get("secretsMode") == "external_secret_reference" and not non_empty(evidence.get("secret_handle")):
        issues.append("external_secret_reference_required")
    passed = not issues
    return {
        "service_id": service_id,
        "capability": service.get("capability"),
        "runtime_role": service.get("runtimeRole"),
        "dr_tier": service.get("drTier"),
        "identity_mode": service.get("identityMode"),
        "secrets_mode": service.get("secretsMode"),
        "evidence_attached": bool(evidence),
        "secret_handle": evidence.get("secret_handle"),
        "service_identity": evidence.get("service_identity"),
        "active_version": evidence.get("active_version"),
        "kms_key_id": evidence.get("kms_key_id"),
        "key_hash": evidence.get("key_hash"),
        "rotation_policy_id": evidence.get("rotation_policy_id"),
        "latest_rotation_at": evidence.get("latest_rotation_at"),
        "passed": passed,
        "issues": sorted(set(issues)),
        "next_actions": [] if passed else [{"priority": "P0", "action": "attach_managed_secret_rotation_evidence", "owner": "data-platform-security"}],
    }


def secret_rotation_ops_summary(
    rows: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    secret_manager = (
        evidence.get("secret_manager")
        if isinstance(evidence, dict) and isinstance(evidence.get("secret_manager"), dict)
        else {}
    )
    audit_sink = evidence.get("audit_sink") if isinstance(evidence, dict) and isinstance(evidence.get("audit_sink"), dict) else {}
    return {
        "p0_service_count": len(rows),
        "covered_service_count": sum(1 for row in rows if row.get("evidence_attached") is True),
        "passed_service_count": sum(1 for row in rows if row.get("passed") is True),
        "failed_service_count": sum(1 for row in rows if row.get("passed") is not True),
        "failed_check_count": len(failed_checks),
        "managed_secret_manager_ha": get_bool(evidence, "controls", "managed_secret_manager_ha"),
        "workload_identity_federation": get_bool(evidence, "controls", "workload_identity_federation"),
        "kms_hsm_custody": get_bool(evidence, "controls", "kms_hsm_custody"),
        "rotation_policy_enforced": get_bool(evidence, "controls", "rotation_policy_enforced"),
        "old_versions_denied": get_bool(evidence, "controls", "old_versions_denied"),
        "unauthorized_identity_denied": get_bool(evidence, "controls", "unauthorized_identity_denied"),
        "missing_secret_denied": get_bool(evidence, "controls", "missing_secret_denied"),
        "orchestrator_injection_redacted": get_bool(evidence, "controls", "orchestrator_injection_redacted"),
        "plaintext_secret_material_persisted": get_bool(evidence, "controls", "plaintext_secret_material_persisted"),
        "secret_manager_provider": secret_manager.get("provider"),
        "kms_key_id": secret_manager.get("kms_key_id"),
        "kms_key_hash": secret_manager.get("kms_key_hash"),
        "cross_region_replication": secret_manager.get("cross_region_replication"),
        "backup_restore_tested": secret_manager.get("backup_restore_tested"),
        "audit_event_count": audit_sink.get("event_count", 0),
        "audit_failed_event_count": audit_sink.get("failed_event_count", 0),
        "audit_sink_siem_exported": audit_sink.get("siem_exported"),
    }


def secret_evidence_by_service(evidence: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    services = evidence.get("service_secrets") if isinstance(evidence, dict) else None
    if not isinstance(services, list):
        return {}
    return {
        str(item.get("service_id")): item
        for item in services
        if isinstance(item, dict) and item.get("service_id")
    }


def compact_secret_service_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "service_id": row.get("service_id"),
        "capability": row.get("capability"),
        "secret_handle": row.get("secret_handle"),
        "service_identity": row.get("service_identity"),
        "issues": row.get("issues", []),
    }


def evidence_fresh(evidence: dict[str, Any] | None, generated_at: str) -> bool:
    if not isinstance(evidence, dict):
        return False
    valid_until = parse_time(evidence.get("valid_until"))
    generated = parse_time(generated_at)
    return valid_until is not None and generated is not None and valid_until > generated


def get_bool(payload: dict[str, Any] | None, section: str, key: str) -> bool | None:
    value = payload.get(section) if isinstance(payload, dict) else None
    if not isinstance(value, dict):
        return None
    result = value.get(key)
    return result if isinstance(result, bool) else None


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
