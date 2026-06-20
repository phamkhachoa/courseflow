from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import timedelta
from pathlib import Path
import re
from typing import Any

import yaml

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.contracts import ValidationResult, load_yaml, require_int, require_string, require_string_list


MANIFEST_VERSION = 1
VALID_ENVIRONMENTS = {"local", "staging", "prod"}
VALID_ACTIVATION_STATES = {"active", "pending", "failed", "stale", "revoked", "expired"}
VALID_GATE_STATUSES = {"passed", "failed", "not_required", "pending_runtime", "not_applicable"}
REQUIRED_GATE_BADGES = {
    "schema",
    "bronzeReplay",
    "offsetLedger",
    "bridge",
    "privacyTenant",
    "catalogLineage",
    "changeControl",
    "runtimeSlo",
}
PASSING_GATE_STATUSES = {"passed", "not_required", "not_applicable"}
SHA256_VALUE = re.compile(r"^sha256:[0-9a-f]{64}$")
DEFAULT_ACTIVATION_TTL_DAYS = 180
SOURCE_ACTIVATION_CRITICAL_RISK_STATES = {
    "source_registry_hash_mismatch",
    "activation_expired",
    "readiness_evidence_missing",
    "readiness_evidence_unverifiable",
    "readiness_hash_invalid",
    "readiness_hash_mismatch",
    "evidence_bundle_evidence_missing",
    "evidence_bundle_evidence_unverifiable",
    "evidence_bundle_hash_invalid",
    "evidence_bundle_hash_mismatch",
    "runtime_readiness_evidence_missing",
    "runtime_readiness_hash_invalid",
    "runtime_readiness_evidence_unverifiable",
    "runtime_readiness_hash_mismatch",
    "active_pointer_missing",
    "active_pointer_mismatch",
    "activation_not_active",
    "p0_source_unactivated",
    "revoked",
}
RUNTIME_READINESS_EVIDENCE_ISSUES = {
    "runtime_readiness_evidence_missing",
    "runtime_readiness_hash_invalid",
    "runtime_readiness_evidence_unverifiable",
    "runtime_readiness_hash_mismatch",
}
SOURCE_EVIDENCE_INTEGRITY_ISSUES = {
    "readiness_evidence_missing",
    "readiness_evidence_unverifiable",
    "readiness_hash_invalid",
    "readiness_hash_mismatch",
    "evidence_bundle_evidence_missing",
    "evidence_bundle_evidence_unverifiable",
    "evidence_bundle_hash_invalid",
    "evidence_bundle_hash_mismatch",
    *RUNTIME_READINESS_EVIDENCE_ISSUES,
}


@dataclass(frozen=True)
class SourceActivationManifestResult:
    output_path: Path
    manifest: dict[str, Any]
    ledger_path: Path
    active_state_path: Path


@dataclass(frozen=True)
class SourceActivationOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def validate_source_activation_registry(root: str | Path, ledger_path: str | Path | None = None) -> ValidationResult:
    platform_root = Path(root)
    path = activation_ledger_path(platform_root, ledger_path)
    result = ValidationResult()
    if not path.is_file():
        result.error(path, "governance/source-activations.yaml is required")
        return result

    registry = load_yaml(path)
    result.checked_count += 1
    require_int(path, result, registry, "version", minimum=1)
    require_string(path, result, registry, "registry_scope")
    require_string(path, result, registry, "owner")
    require_string(path, result, registry, "description")
    activations = registry.get("activations")
    if not isinstance(activations, list) or not activations:
        result.error(path, "activations must be a non-empty list")
        return result

    sources = source_index(platform_root)
    change_requests = change_request_index(platform_root)
    use_cases = use_case_ids(platform_root)
    seen: set[str] = set()
    for index, activation in enumerate(activations):
        result.checked_count += 1
        validate_source_activation_record(
            path,
            activation,
            index,
            seen=seen,
            sources=sources,
            change_requests=change_requests,
            use_cases=use_cases,
            result=result,
        )
    return result


def write_source_activation_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "staging",
    ledger_path: str | Path | None = None,
    active_pointer_dir: str | Path | None = None,
    generated_at: str | None = None,
    expiry_warning_days: int = 30,
) -> SourceActivationOpsReportResult:
    report = build_source_activation_ops_report(
        root,
        environment=environment,
        ledger_path=ledger_path,
        active_pointer_dir=active_pointer_dir,
        generated_at=generated_at,
        expiry_warning_days=expiry_warning_days,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SourceActivationOpsReportResult(output_path=target, report=report)


def build_source_activation_ops_report(
    root: str | Path,
    *,
    environment: str = "staging",
    ledger_path: str | Path | None = None,
    active_pointer_dir: str | Path | None = None,
    generated_at: str | None = None,
    expiry_warning_days: int = 30,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    observed_at = parse_timestamp(generated)
    ledger_file = activation_ledger_path(platform_root, ledger_path)
    pointer_root = resolve_active_pointer_dir(platform_root, active_pointer_dir)
    sources = source_index(platform_root)
    records = load_source_activations(ledger_file) if ledger_file.is_file() else []
    latest_records = latest_records_by_source_environment(records, environment, observed_at=observed_at)
    rows = [
        source_activation_ops_row(
            platform_root,
            source,
            latest_records.get(source_id),
            environment=environment,
            observed_at=observed_at,
            expiry_warning_days=expiry_warning_days,
            pointer_root=pointer_root,
        )
        for source_id, source in sorted(sources.items())
    ]
    summary = source_activation_ops_summary(rows)
    decision_board = source_activation_ops_decision_board(rows)
    validation = validate_source_activation_registry(platform_root, ledger_file) if ledger_file.is_file() else ValidationResult()
    if not ledger_file.is_file():
        validation.error(ledger_file, "activation ledger is missing")
    passed = source_activation_ops_passed(summary, environment=environment, validation_passed=validation.ok)
    runtime_attested = source_activation_ops_runtime_attested(
        summary,
        decision_board,
        environment=environment,
        validation_passed=validation.ok,
    )
    report = {
        "artifact_type": "source_activation_ops_report.v1",
        "report_version": MANIFEST_VERSION,
        "capability_id": "source-onboarding",
        "report_id": stable_id(
            "source-activation-ops",
            environment,
            generated,
            hash_file(ledger_file) if ledger_file.is_file() else None,
            hash_file(platform_root / "platform" / "ingestion" / "source-registry.yaml"),
        ),
        "generated_at": generated,
        "environment": environment,
        "mode": source_activation_ops_mode(environment, runtime_attested=runtime_attested),
        "readiness_state": source_activation_ops_readiness_state(
            environment,
            passed=passed,
            runtime_attested=runtime_attested,
        ),
        "ledger": {
            "path": ledger_file.as_posix(),
            "exists": ledger_file.is_file(),
            "hash": hash_file(ledger_file) if ledger_file.is_file() else None,
            "record_count": len(records),
            "validation_passed": validation.ok,
            "validation_errors": validation.errors,
        },
        "source_registry": {
            "path": (platform_root / "platform" / "ingestion" / "source-registry.yaml").as_posix(),
            "current_hash": hash_file(platform_root / "platform" / "ingestion" / "source-registry.yaml"),
        },
        "active_pointer_dir": pointer_root.as_posix(),
        "expiry_warning_days": expiry_warning_days,
        "summary": summary,
        "decision_board": decision_board,
        "sources": rows,
        "passed": passed,
    }
    return report


def write_source_activation_manifest_from_bundle(
    root: str | Path,
    bundle_path: str | Path,
    output_path: str | Path,
    *,
    requested_by: str,
    approved_by: str,
    change_request_id: str,
    ledger_path: str | Path | None = None,
    active_state_path: str | Path | None = None,
    expires_at: str | None = None,
    generated_at: str | None = None,
    impacted_use_cases: list[str] | None = None,
    reason: str | None = None,
    runtime_readiness_report_path: str | Path | None = None,
) -> SourceActivationManifestResult:
    platform_root = Path(root)
    bundle_file = Path(bundle_path)
    ledger_file = activation_ledger_path(platform_root, ledger_path)
    if active_state_path is not None:
        active_file = Path(active_state_path)
    else:
        bundle_identity = load_json(bundle_file)
        source_id = str(bundle_identity.get("source_id") or "unknown-source")
        environment = str(bundle_identity.get("environment") or "unknown-env")
        active_file = platform_root / "governance" / "source-active-pointers" / f"{source_id}.{environment}.json"
    if active_state_path is not None and not active_file.is_absolute():
        active_file = platform_root / active_file
    previous_state = load_json(active_file) if active_file.is_file() else None
    manifest = build_source_activation_manifest_from_bundle(
        platform_root,
        bundle_file,
        output_path=Path(output_path),
        ledger_path=ledger_file,
        active_state_path=active_file,
        previous_state=previous_state,
        requested_by=requested_by,
        approved_by=approved_by,
        change_request_id=change_request_id,
        expires_at=expires_at,
        generated_at=generated_at,
        impacted_use_cases=impacted_use_cases,
        reason=reason,
        runtime_readiness_report_path=runtime_readiness_report_path,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    if manifest["passed"]:
        append_activation_record(ledger_file, manifest["activation_record"])
        active_file.parent.mkdir(parents=True, exist_ok=True)
        active_file.write_text(f"{canonical_json(manifest['active_pointer'])}\n", encoding="utf-8")
    return SourceActivationManifestResult(
        output_path=target,
        manifest=manifest,
        ledger_path=ledger_file,
        active_state_path=active_file,
    )


def write_source_revocation_manifest(
    root: str | Path,
    output_path: str | Path,
    *,
    source_id: str,
    environment: str,
    requested_by: str,
    approved_by: str,
    change_request_id: str,
    ledger_path: str | Path | None = None,
    active_state_path: str | Path | None = None,
    generated_at: str | None = None,
    reason: str | None = None,
    evidence_uri: str | None = None,
    impacted_use_cases: list[str] | None = None,
    allow_missing_active_pointer: bool = False,
) -> SourceActivationManifestResult:
    platform_root = Path(root)
    ledger_file = activation_ledger_path(platform_root, ledger_path)
    active_file = Path(active_state_path) if active_state_path is not None else default_active_pointer_path(platform_root, source_id, environment)
    if active_state_path is not None and not active_file.is_absolute():
        active_file = platform_root / active_file
    previous_state = load_json(active_file) if active_file.is_file() else None
    manifest = build_source_revocation_manifest(
        platform_root,
        output_path=Path(output_path),
        ledger_path=ledger_file,
        active_state_path=active_file,
        previous_state=previous_state,
        source_id=source_id,
        environment=environment,
        requested_by=requested_by,
        approved_by=approved_by,
        change_request_id=change_request_id,
        generated_at=generated_at,
        reason=reason,
        evidence_uri=evidence_uri,
        impacted_use_cases=impacted_use_cases,
        allow_missing_active_pointer=allow_missing_active_pointer,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    if manifest["passed"]:
        append_activation_record(ledger_file, manifest["revocation_record"])
        active_file.parent.mkdir(parents=True, exist_ok=True)
        active_file.write_text(f"{canonical_json(manifest['active_pointer'])}\n", encoding="utf-8")
    return SourceActivationManifestResult(
        output_path=target,
        manifest=manifest,
        ledger_path=ledger_file,
        active_state_path=active_file,
    )


def build_source_activation_manifest_from_bundle(
    root: Path,
    bundle_path: Path,
    *,
    output_path: Path,
    ledger_path: Path,
    active_state_path: Path,
    previous_state: dict[str, Any] | None,
    requested_by: str,
    approved_by: str,
    change_request_id: str,
    expires_at: str | None = None,
    generated_at: str | None = None,
    impacted_use_cases: list[str] | None = None,
    reason: str | None = None,
    runtime_readiness_report_path: str | Path | None = None,
) -> dict[str, Any]:
    generated = generated_at or utc_now()
    activated_at = parse_timestamp(generated)
    resolved_expires_at = expires_at or format_timestamp(activated_at + timedelta(days=DEFAULT_ACTIVATION_TTL_DAYS))
    bundle = load_json(bundle_path)
    readiness_path = resolve_artifact_path(bundle.get("artifacts", {}).get("source_readiness_report"), root, bundle_path)
    readiness = load_json(readiness_path) if readiness_path.is_file() else {}
    runtime_path = resolve_optional_artifact_path(runtime_readiness_report_path, root, bundle_path)
    runtime_readiness = load_json(runtime_path) if runtime_path and runtime_path.is_file() else None
    source_id = str(bundle.get("source_id") or readiness.get("source_id") or "")
    environment = str(bundle.get("environment") or readiness.get("environment") or "")
    source = source_index(root).get(source_id)
    change_request = change_request_index(root).get(change_request_id)
    source_snapshot = readiness.get("source") if isinstance(readiness.get("source"), dict) else {}
    canonical = source.get("canonical") if isinstance(source, dict) and isinstance(source.get("canonical"), dict) else {}
    bridge = source.get("bridge") if isinstance(source, dict) and isinstance(source.get("bridge"), dict) else {}
    gate_badges = source_activation_gate_badges(readiness, runtime_readiness=runtime_readiness)
    impacted = impacted_use_cases or impacted_use_cases_from_change_request(change_request)
    activation_id = stable_id(
        "source-activation",
        source_id,
        environment,
        readiness.get("readiness_id"),
        hash_file(bundle_path),
        requested_by,
        approved_by,
        generated,
    )
    activation_record = {
        "activationId": activation_id,
        "sourceId": source_id,
        "environment": environment,
        "activationState": "active",
        "requestedBy": requested_by,
        "approvedBy": approved_by,
        "changeRequestId": change_request_id,
        "activatedAt": generated,
        "expiresAt": resolved_expires_at,
        "readinessId": readiness.get("readiness_id"),
        "readinessReportUri": readiness_path.as_posix(),
        "readinessReportHash": hash_file(readiness_path) if readiness_path.is_file() else None,
        "evidenceBundleUri": bundle_path.as_posix(),
        "evidenceBundleHash": hash_file(bundle_path),
        "sourceRegistryHash": hash_file(root / "platform" / "ingestion" / "source-registry.yaml"),
        "activationManifestUri": output_path.as_posix(),
        "canonicalTopic": canonical.get("topic") or source_snapshot.get("canonical_topic"),
        "bronzeTarget": canonical.get("bronzeTarget") or source_snapshot.get("bronze_target"),
        "schemaSubject": canonical.get("schemaSubject") or source_snapshot.get("schema_subject"),
        "mode": bridge.get("mode") or (source_snapshot.get("bridge") if isinstance(source_snapshot.get("bridge"), dict) else {}).get("mode"),
        "gateBadges": gate_badges,
        "impactedUseCases": impacted,
    }
    if runtime_path is not None:
        activation_record["runtimeReadinessReportUri"] = runtime_path.as_posix()
        activation_record["runtimeReadinessReportHash"] = hash_file(runtime_path) if runtime_path.is_file() else None
        activation_record["runtimeReadinessId"] = runtime_readiness.get("report_id") if isinstance(runtime_readiness, dict) else None
    if reason:
        activation_record["reason"] = reason
    active_pointer = {
        "artifact_type": "source_active_pointer.v1",
        "pointer_version": 1,
        "source_id": source_id,
        "environment": environment,
        "activation_id": activation_id,
        "readiness_id": readiness.get("readiness_id"),
        "canonical_topic": activation_record["canonicalTopic"],
        "bronze_target": activation_record["bronzeTarget"],
        "activated_at": generated,
        "expires_at": resolved_expires_at,
        "activated_by": approved_by,
        "activation_manifest_uri": output_path.as_posix(),
        "ledger_uri": ledger_path.as_posix(),
        "rollback_target": rollback_target(previous_state, source_id=source_id, environment=environment),
    }
    checks = source_activation_checks(
        bundle,
        readiness,
        source=source,
        change_request=change_request,
        source_id=source_id,
        environment=environment,
        requested_by=requested_by,
        approved_by=approved_by,
        change_request_id=change_request_id,
        readiness_path=readiness_path,
        bundle_path=bundle_path,
        activated_at=generated,
        expires_at=resolved_expires_at,
        gate_badges=gate_badges,
        impacted_use_cases=impacted,
        runtime_readiness=runtime_readiness,
        runtime_readiness_path=runtime_path,
    )
    passed = all(item["passed"] is True for item in checks)
    if not passed:
        activation_record["activationState"] = "failed"
    return {
        "artifact_type": "source_activation_manifest.v1",
        "manifest_version": MANIFEST_VERSION,
        "activation_id": activation_id,
        "activation_state": "activated" if passed else "blocked",
        "generated_at": generated,
        "source_id": source_id,
        "environment": environment,
        "requested_by": requested_by,
        "approved_by": approved_by,
        "change_request_id": change_request_id,
        "source_readiness_bundle_uri": bundle_path.as_posix(),
        "source_readiness_bundle_hash": hash_file(bundle_path),
        "source_readiness_report_uri": readiness_path.as_posix(),
        "source_readiness_report_hash": hash_file(readiness_path) if readiness_path.is_file() else None,
        "runtime_readiness_report_uri": runtime_path.as_posix() if runtime_path else None,
        "runtime_readiness_report_hash": hash_file(runtime_path) if runtime_path and runtime_path.is_file() else None,
        "source_registry_uri": (root / "platform" / "ingestion" / "source-registry.yaml").as_posix(),
        "source_registry_hash": hash_file(root / "platform" / "ingestion" / "source-registry.yaml"),
        "ledger_uri": ledger_path.as_posix(),
        "active_state_path": active_state_path.as_posix(),
        "activation_record": activation_record,
        "previous_active": rollback_target(previous_state, source_id=source_id, environment=environment),
        "active_pointer": active_pointer,
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def build_source_revocation_manifest(
    root: Path,
    *,
    output_path: Path,
    ledger_path: Path,
    active_state_path: Path,
    previous_state: dict[str, Any] | None,
    source_id: str,
    environment: str,
    requested_by: str,
    approved_by: str,
    change_request_id: str,
    generated_at: str | None = None,
    reason: str | None = None,
    evidence_uri: str | None = None,
    impacted_use_cases: list[str] | None = None,
    allow_missing_active_pointer: bool = False,
) -> dict[str, Any]:
    generated = generated_at or utc_now()
    expires_at = format_timestamp(parse_timestamp(generated) + timedelta(days=DEFAULT_ACTIVATION_TTL_DAYS))
    source = source_index(root).get(source_id)
    change_request = change_request_index(root).get(change_request_id)
    previous_record = latest_activation_record(root, ledger_path, source_id=source_id, environment=environment)
    previous_active_pointer_missing = not active_state_path.is_file()
    previous_pointer_hash = hash_file(active_state_path) if active_state_path.is_file() else None
    canonical = source.get("canonical") if isinstance(source, dict) and isinstance(source.get("canonical"), dict) else {}
    bridge = source.get("bridge") if isinstance(source, dict) and isinstance(source.get("bridge"), dict) else {}
    impacted = impacted_use_cases or string_list((previous_record or {}).get("impactedUseCases")) or impacted_use_cases_from_change_request(change_request)
    revocation_id = stable_id(
        "source-revocation",
        source_id,
        environment,
        (previous_record or {}).get("activationId"),
        requested_by,
        approved_by,
        generated,
    )
    revocation_record = {
        "activationId": revocation_id,
        "sourceId": source_id,
        "environment": environment,
        "activationState": "revoked",
        "requestedBy": requested_by,
        "approvedBy": approved_by,
        "changeRequestId": change_request_id,
        "activatedAt": generated,
        "expiresAt": expires_at,
        "readinessId": (previous_record or {}).get("readinessId"),
        "readinessReportUri": (previous_record or {}).get("readinessReportUri"),
        "readinessReportHash": (previous_record or {}).get("readinessReportHash"),
        "evidenceBundleUri": (previous_record or {}).get("evidenceBundleUri"),
        "evidenceBundleHash": (previous_record or {}).get("evidenceBundleHash"),
        "sourceRegistryHash": hash_file(root / "platform" / "ingestion" / "source-registry.yaml"),
        "revocationManifestUri": output_path.as_posix(),
        "revokedActivationId": (previous_record or {}).get("activationId"),
        "previousActivePointerUri": active_state_path.as_posix(),
        "previousActivePointerHash": previous_pointer_hash,
        "previousActivePointerMissing": previous_active_pointer_missing,
        "missingActivePointerBreakGlass": allow_missing_active_pointer and previous_active_pointer_missing,
        "revokedAt": generated,
        "revokedBy": approved_by,
        "revocationReason": reason,
        "revocationEvidenceUri": evidence_uri,
        "canonicalTopic": canonical.get("topic") or (previous_record or {}).get("canonicalTopic"),
        "bronzeTarget": canonical.get("bronzeTarget") or (previous_record or {}).get("bronzeTarget"),
        "schemaSubject": canonical.get("schemaSubject") or (previous_record or {}).get("schemaSubject"),
        "mode": bridge.get("mode") or (previous_record or {}).get("mode"),
        "gateBadges": (previous_record or {}).get("gateBadges") if isinstance((previous_record or {}).get("gateBadges"), dict) else default_revocation_gate_badges(),
        "impactedUseCases": impacted,
    }
    active_pointer = {
        "artifact_type": "source_active_pointer.v1",
        "pointer_version": 1,
        "source_id": source_id,
        "environment": environment,
        "activation_id": revocation_id,
        "activation_state": "revoked",
        "revoked_activation_id": (previous_record or {}).get("activationId"),
        "readiness_id": revocation_record["readinessId"],
        "canonical_topic": revocation_record["canonicalTopic"],
        "bronze_target": revocation_record["bronzeTarget"],
        "activated_at": generated,
        "revoked_at": generated,
        "expires_at": expires_at,
        "activated_by": approved_by,
        "revocation_manifest_uri": output_path.as_posix(),
        "ledger_uri": ledger_path.as_posix(),
        "rollback_target": rollback_target(previous_state, source_id=source_id, environment=environment),
        "previous_active_pointer_missing": previous_active_pointer_missing,
        "missing_active_pointer_break_glass": allow_missing_active_pointer and previous_active_pointer_missing,
    }
    checks = source_revocation_checks(
        source=source,
        change_request=change_request,
        previous_record=previous_record,
        previous_state=previous_state,
        source_id=source_id,
        environment=environment,
        requested_by=requested_by,
        approved_by=approved_by,
        change_request_id=change_request_id,
        ledger_path=ledger_path,
        active_state_path=active_state_path,
        reason=reason,
        evidence_uri=evidence_uri,
        impacted_use_cases=impacted,
        allow_missing_active_pointer=allow_missing_active_pointer,
    )
    passed = all(item["passed"] is True for item in checks)
    return {
        "artifact_type": "source_revocation_manifest.v1",
        "manifest_version": MANIFEST_VERSION,
        "revocation_id": revocation_id,
        "activation_id": revocation_id,
        "revocation_state": "revoked" if passed else "blocked",
        "activation_state": "revoked" if passed else "blocked",
        "generated_at": generated,
        "source_id": source_id,
        "environment": environment,
        "requested_by": requested_by,
        "approved_by": approved_by,
        "change_request_id": change_request_id,
        "ledger_uri": ledger_path.as_posix(),
        "active_state_path": active_state_path.as_posix(),
        "previous_active_pointer_hash": previous_pointer_hash,
        "previous_active_pointer_missing": previous_active_pointer_missing,
        "missing_active_pointer_break_glass": allow_missing_active_pointer and previous_active_pointer_missing,
        "revoked_activation_id": (previous_record or {}).get("activationId"),
        "revocation_record": revocation_record,
        "previous_active": rollback_target(previous_state, source_id=source_id, environment=environment),
        "active_pointer": active_pointer,
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def build_source_activation_index(
    root: str | Path,
    *,
    environment: str = "local",
    as_of: str | datetime | None = None,
    ledger_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    platform_root = Path(root)
    path = activation_ledger_path(platform_root, ledger_path)
    if not path.is_file():
        return {}
    if environment not in VALID_ENVIRONMENTS:
        raise ValueError(f"environment must be one of {sorted(VALID_ENVIRONMENTS)}")

    observed_at = parse_timestamp(as_of) if as_of is not None else datetime.now(UTC)
    registry_file = platform_root / "platform" / "ingestion" / "source-registry.yaml"
    current_registry_hash = hash_file(registry_file) if registry_file.is_file() else None
    activations = load_source_activations(path)
    compatible = [
        activation_summary(
            activation,
            observed_at,
            environment,
            current_registry_hash=current_registry_hash,
            root=platform_root,
        )
        for activation in activations
        if activation_environment_compatible(str(activation.get("environment") or ""), environment)
        and activation_effective_at_or_before(activation, observed_at)
    ]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for activation in compatible:
        by_source.setdefault(str(activation.get("source_id")), []).append(activation)

    index: dict[str, dict[str, Any]] = {}
    for source_id, candidates in by_source.items():
        ordered = sorted(candidates, key=lambda item: item.get("activated_at") or "", reverse=True)
        current = ordered[0]
        if current["activation_state"] == "active" and not current.get("block_reason"):
            current["effective_status"] = "production_ready"
            current["business_readiness"] = "production_ready_verified"
        else:
            current["effective_status"] = "blocked"
            current["business_readiness"] = "blocked"
        index[source_id] = current
    return index


def source_effective_status(source: dict[str, Any], activation_index: dict[str, dict[str, Any]] | None = None) -> str:
    source_id = str(source.get("sourceId") or "")
    activation = (activation_index or {}).get(source_id)
    if activation and activation.get("effective_status") == "production_ready":
        return "production_ready"
    return str(source.get("status") or "unknown")


def source_activation_summary(source_id: object, activation_index: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    activation = (activation_index or {}).get(str(source_id or ""))
    if not activation:
        return None
    return {
        "activation_id": activation.get("activation_id"),
        "activation_state": activation.get("activation_state"),
        "effective_status": activation.get("effective_status"),
        "business_readiness": activation.get("business_readiness"),
        "environment": activation.get("environment"),
        "activated_at": activation.get("activated_at"),
        "expires_at": activation.get("expires_at"),
        "readiness_id": activation.get("readiness_id"),
        "readiness_report_hash": activation.get("readiness_report_hash"),
        "evidence_bundle_hash": activation.get("evidence_bundle_hash"),
        "runtime_readiness": activation.get("runtime_readiness", {}),
        "source_registry_hash": activation.get("source_registry_hash"),
        "gate_badges": activation.get("gate_badges", {}),
        "impacted_use_cases": activation.get("impacted_use_cases", []),
        "block_reason": activation.get("block_reason"),
    }


def activation_state_counts(activation_index: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for activation in activation_index.values():
        state = str(activation.get("activation_state") or "unknown")
        counts[state] = counts.get(state, 0) + 1
    return dict(sorted(counts.items()))


def activation_ledger_path(root: Path, ledger_path: str | Path | None) -> Path:
    if ledger_path is None:
        return root / "governance" / "source-activations.yaml"
    path = Path(ledger_path)
    return path if path.is_absolute() else root / path


def load_source_activations(path: Path) -> list[dict[str, Any]]:
    registry = load_yaml(path)
    activations = registry.get("activations")
    return [item for item in activations if isinstance(item, dict)] if isinstance(activations, list) else []


def append_activation_record(path: Path, record: dict[str, Any]) -> None:
    if path.is_file():
        registry = load_yaml(path)
    else:
        registry = {
            "version": 1,
            "registry_scope": "group-enterprise-data-platform",
            "owner": "data-platform-team",
            "description": "Append-only source activation ledger.",
            "activations": [],
        }
    activations = registry.get("activations")
    if not isinstance(activations, list):
        activations = []
        registry["activations"] = activations
    activations.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")


def source_activation_ops_row(
    root: Path,
    source: dict[str, Any],
    record: dict[str, Any] | None,
    *,
    environment: str,
    observed_at: datetime,
    expiry_warning_days: int,
    pointer_root: Path,
) -> dict[str, Any]:
    source_id = str(source.get("sourceId") or "")
    pointer_path = pointer_root / f"{source_id}.{environment}.json"
    pointer = load_json(pointer_path) if pointer_path.is_file() else None
    current_registry_hash = hash_file(root / "platform" / "ingestion" / "source-registry.yaml")
    activation = (
        activation_summary(
            record,
            observed_at,
            environment,
            current_registry_hash=current_registry_hash,
            root=root,
        )
        if record
        else None
    )
    if activation and activation.get("activation_state") == "active" and not activation.get("block_reason"):
        activation["effective_status"] = "production_ready"
        activation["business_readiness"] = "production_ready_verified"
    expires_at = parse_optional_timestamp(record.get("expiresAt") if record else None)
    days_to_expiry = (expires_at.date() - observed_at.date()).days if expires_at else None
    pointer_matches = (
        isinstance(pointer, dict)
        and record is not None
        and pointer.get("activation_id") == record.get("activationId")
        and pointer.get("source_id") == source_id
        and pointer.get("environment") == environment
    )
    pointer_mismatches = active_pointer_mismatches(pointer, record, source_id=source_id, environment=environment)
    issues = source_activation_ops_issues(
        source,
        record,
        activation,
        pointer=pointer,
        pointer_matches=pointer_matches,
        days_to_expiry=days_to_expiry,
        expiry_warning_days=expiry_warning_days,
        root=root,
    )
    return {
        "source_id": source_id,
        "product": source.get("product"),
        "domain": source.get("domain"),
        "priority": source.get("priority"),
        "static_status": source.get("status"),
        "environment": environment,
        "activation_id": record.get("activationId") if record else None,
        "activation_state": record.get("activationState") if record else "unactivated",
        "effective_status": activation.get("effective_status") if activation else "unactivated",
        "business_readiness": activation.get("business_readiness") if activation else "unproven",
        "block_reason": activation.get("block_reason") if activation else None,
        "activated_at": record.get("activatedAt") if record else None,
        "expires_at": record.get("expiresAt") if record else None,
        "days_to_expiry": days_to_expiry,
        "readiness_id": record.get("readinessId") if record else None,
        "evidence_integrity": source_evidence_integrity_summary(record, root=root),
        "runtime_readiness": runtime_readiness_evidence_summary(record, root=root),
        "source_registry_hash": record.get("sourceRegistryHash") if record else None,
        "current_source_registry_hash": current_registry_hash,
        "pointer": {
            "path": pointer_path.as_posix(),
            "exists": pointer_path.is_file(),
            "hash": hash_file(pointer_path) if pointer_path.is_file() else None,
            "activation_id": pointer.get("activation_id") if isinstance(pointer, dict) else None,
            "activation_state": pointer.get("activation_state") if isinstance(pointer, dict) else None,
            "readiness_id": pointer.get("readiness_id") if isinstance(pointer, dict) else None,
            "expires_at": pointer.get("expires_at") if isinstance(pointer, dict) else None,
            "ledger_uri": pointer.get("ledger_uri") if isinstance(pointer, dict) else None,
            "revoked_activation_id": pointer.get("revoked_activation_id") if isinstance(pointer, dict) else None,
            "matches_latest_record": pointer_matches,
            "consistency_state": "consistent" if pointer_matches else ("missing" if not pointer_path.is_file() else "mismatch"),
            "mismatches": pointer_mismatches,
        },
        "gate_badges": record.get("gateBadges") if isinstance(record, dict) and isinstance(record.get("gateBadges"), dict) else {},
        "impacted_use_cases": string_list(record.get("impactedUseCases")) if record else [],
        "issues": issues,
        "risk_state": source_activation_risk_state(issues),
        "next_actions": source_activation_next_actions(issues, source),
    }


def source_activation_ops_issues(
    source: dict[str, Any],
    record: dict[str, Any] | None,
    activation: dict[str, Any] | None,
    *,
    pointer: dict[str, Any] | None,
    pointer_matches: bool,
    days_to_expiry: int | None,
    expiry_warning_days: int,
    root: Path | None = None,
) -> list[str]:
    issues: list[str] = []
    if record is None:
        if source.get("priority") == "P0":
            issues.append("p0_source_unactivated")
        return issues
    state = record.get("activationState")
    if state == "revoked":
        issues.append("activation_revoked")
    elif state != "active":
        issues.append(f"activation_not_active:{state}")
    if activation and activation.get("block_reason"):
        issues.append(str(activation["block_reason"]))
    if days_to_expiry is not None:
        if days_to_expiry < 0:
            issues.append("activation_expired")
        elif days_to_expiry <= expiry_warning_days and state == "active":
            issues.append("activation_expiring_soon")
    if state == "active":
        issues.extend(source_evidence_integrity_issues(record, root=root))
        if not isinstance(pointer, dict):
            issues.append("active_pointer_missing")
        elif not pointer_matches:
            issues.append("active_pointer_mismatch")
    return sorted(set(issues))


def active_pointer_mismatches(
    pointer: dict[str, Any] | None,
    record: dict[str, Any] | None,
    *,
    source_id: str,
    environment: str,
) -> list[str]:
    if not isinstance(pointer, dict):
        return ["missing"]
    mismatches = []
    if pointer.get("source_id") != source_id:
        mismatches.append("source_id")
    if pointer.get("environment") != environment:
        mismatches.append("environment")
    if record is not None and pointer.get("activation_id") != record.get("activationId"):
        mismatches.append("activation_id")
    if record is not None and record.get("activationState") == "revoked" and pointer.get("activation_state") != "revoked":
        mismatches.append("activation_state")
    return mismatches


def source_activation_risk_state(issues: list[str]) -> str:
    if not issues:
        return "ok"
    if "activation_revoked" in issues:
        return "revoked"
    for issue in (
        "source_registry_hash_mismatch",
        "activation_expired",
        "readiness_evidence_missing",
        "readiness_evidence_unverifiable",
        "readiness_hash_invalid",
        "readiness_hash_mismatch",
        "evidence_bundle_evidence_missing",
        "evidence_bundle_evidence_unverifiable",
        "evidence_bundle_hash_invalid",
        "evidence_bundle_hash_mismatch",
        "runtime_readiness_evidence_missing",
        "runtime_readiness_hash_invalid",
        "runtime_readiness_evidence_unverifiable",
        "runtime_readiness_hash_mismatch",
        "active_pointer_missing",
        "active_pointer_mismatch",
        "p0_source_unactivated",
    ):
        if issue in issues:
            return issue
    if any(issue.startswith("activation_not_active") for issue in issues):
        return "activation_not_active"
    if "activation_expiring_soon" in issues:
        return "expiring_soon"
    return "attention"


def source_activation_next_actions(issues: list[str], source: dict[str, Any]) -> list[dict[str, Any]]:
    owner = source.get("product") or "data-platform-team"
    source_priority = str(source.get("priority") or "")
    activation_state_action_priority = "P0" if source_priority == "P0" else "P1"
    actions = []
    if "p0_source_unactivated" in issues:
        actions.append({"priority": "P0", "action": "activate_source_with_evidence", "owner": owner})
    if "source_registry_hash_mismatch" in issues:
        actions.append({"priority": "P0", "action": "renew_source_activation_after_registry_drift", "owner": owner})
    if "activation_expired" in issues:
        actions.append({"priority": "P0", "action": "renew_expired_source_activation", "owner": owner})
    if SOURCE_EVIDENCE_INTEGRITY_ISSUES.intersection(issues):
        actions.append({"priority": "P0", "action": "attach_verifiable_source_activation_evidence", "owner": "platform-engineering"})
    if RUNTIME_READINESS_EVIDENCE_ISSUES.intersection(issues):
        actions.append({"priority": "P0", "action": "attach_valid_runtime_readiness_evidence", "owner": "platform-engineering"})
    if "activation_expiring_soon" in issues:
        actions.append({"priority": "P1", "action": "renew_source_activation_before_expiry", "owner": owner})
    if "active_pointer_missing" in issues or "active_pointer_mismatch" in issues:
        actions.append({"priority": "P0", "action": "repair_source_active_pointer", "owner": "data-platform-team"})
    if "activation_revoked" in issues or any(issue.startswith("activation_not_active") for issue in issues):
        actions.append(
            {
                "priority": activation_state_action_priority,
                "action": "review_source_activation_state",
                "owner": owner,
            }
        )
    return actions or [{"priority": "P3", "action": "no_action", "owner": owner}]


def source_activation_ops_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    p0_rows = [row for row in rows if row.get("priority") == "P0"]
    critical_rows = [row for row in rows if row.get("risk_state") in SOURCE_ACTIVATION_CRITICAL_RISK_STATES]
    p0_critical_rows = [row for row in p0_rows if row.get("risk_state") in SOURCE_ACTIVATION_CRITICAL_RISK_STATES]
    evidence_issue_rows = [row for row in rows if row_has_issue(row, SOURCE_EVIDENCE_INTEGRITY_ISSUES)]
    p0_evidence_issue_rows = [row for row in p0_rows if row_has_issue(row, SOURCE_EVIDENCE_INTEGRITY_ISSUES)]
    return {
        "source_count": len(rows),
        "p0_source_count": len(p0_rows),
        "active_count": sum(1 for row in rows if row.get("activation_state") == "active"),
        "p0_active_count": sum(1 for row in p0_rows if row.get("activation_state") == "active"),
        "revoked_count": sum(1 for row in rows if row.get("activation_state") == "revoked"),
        "pending_count": sum(1 for row in rows if row.get("activation_state") == "pending"),
        "failed_count": sum(1 for row in rows if row.get("activation_state") == "failed"),
        "stale_count": sum(1 for row in rows if row.get("activation_state") == "stale"),
        "unactivated_count": sum(1 for row in rows if row.get("activation_state") == "unactivated"),
        "p0_unactivated_count": sum(1 for row in p0_rows if row.get("activation_state") == "unactivated"),
        "production_ready_count": sum(1 for row in rows if row.get("effective_status") == "production_ready"),
        "p0_production_ready_count": sum(1 for row in p0_rows if row.get("effective_status") == "production_ready"),
        "expiring_soon_count": sum(1 for row in rows if row_has_issue(row, {"activation_expiring_soon"})),
        "expired_count": sum(1 for row in rows if row_has_issue(row, {"activation_expired"})),
        "registry_drift_count": sum(1 for row in rows if row_has_issue(row, {"source_registry_hash_mismatch"})),
        "runtime_readiness_attached_count": sum(
            1
            for row in rows
            if isinstance(row.get("runtime_readiness"), dict) and row["runtime_readiness"].get("attached") is True
        ),
        "p0_runtime_readiness_attached_count": sum(
            1
            for row in p0_rows
            if isinstance(row.get("runtime_readiness"), dict) and row["runtime_readiness"].get("attached") is True
        ),
        "runtime_readiness_issue_count": sum(1 for row in rows if row_has_issue(row, RUNTIME_READINESS_EVIDENCE_ISSUES)),
        "p0_runtime_readiness_issue_count": sum(1 for row in p0_rows if row_has_issue(row, RUNTIME_READINESS_EVIDENCE_ISSUES)),
        "evidence_integrity_issue_count": len(evidence_issue_rows),
        "p0_evidence_integrity_issue_count": len(p0_evidence_issue_rows),
        "pointer_issue_count": sum(1 for row in rows if row_has_issue(row, {"active_pointer_missing", "active_pointer_mismatch"})),
        "p0_activation_gap_count": sum(
            1
            for row in p0_rows
            if row.get("activation_state") != "active" or row.get("effective_status") != "production_ready"
        ),
        "p0_critical_issue_count": len(p0_critical_rows),
        "p0_next_action_count": sum(
            1
            for row in p0_rows
            for action in row.get("next_actions", [])
            if isinstance(action, dict)
            and action.get("priority") == "P0"
            and action.get("action") != "no_action"
        ),
        "critical_issue_count": len(critical_rows),
        "by_activation_state": count_by(rows, "activation_state"),
        "by_risk_state": count_by(rows, "risk_state"),
    }


def source_activation_ops_decision_board(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "critical_sources": [
            compact_source_activation_row(row)
            for row in rows
            if row.get("risk_state") in SOURCE_ACTIVATION_CRITICAL_RISK_STATES
        ][:20],
        "expiring_sources": [
            compact_source_activation_row(row)
            for row in rows
            if row.get("risk_state") == "expiring_soon"
        ][:20],
        "revoked_sources": [
            compact_source_activation_row(row)
            for row in rows
            if row.get("risk_state") == "revoked"
        ][:20],
        "next_actions": sorted(
            [
                {"source_id": row.get("source_id"), **action}
                for row in rows
                for action in row.get("next_actions", [])
                if action.get("action") != "no_action"
            ],
            key=lambda item: (item.get("priority") != "P0", str(item.get("source_id")), str(item.get("action"))),
        )[:30],
    }


def source_activation_ops_passed(
    summary: dict[str, Any],
    *,
    environment: str,
    validation_passed: bool,
) -> bool:
    if not validation_passed:
        return False
    if environment in {"staging", "prod"}:
        p0_source_count = int(summary.get("p0_source_count", 0))
        return (
            int(summary.get("source_count", 0)) > 0
            and p0_source_count > 0
            and int(summary.get("p0_active_count", 0)) == p0_source_count
            and int(summary.get("p0_production_ready_count", 0)) == p0_source_count
            and int(summary.get("p0_runtime_readiness_attached_count", 0)) == p0_source_count
            and int(summary.get("p0_unactivated_count", 0)) == 0
            and int(summary.get("p0_activation_gap_count", 0)) == 0
            and int(summary.get("p0_critical_issue_count", 0)) == 0
            and int(summary.get("p0_next_action_count", 0)) == 0
            and int(summary.get("critical_issue_count", 0)) == 0
            and int(summary.get("registry_drift_count", 0)) == 0
            and int(summary.get("runtime_readiness_issue_count", 0)) == 0
            and int(summary.get("evidence_integrity_issue_count", 0)) == 0
            and int(summary.get("p0_evidence_integrity_issue_count", 0)) == 0
            and int(summary.get("pointer_issue_count", 0)) == 0
            and int(summary.get("expired_count", 0)) == 0
            and int(summary.get("revoked_count", 0)) == 0
            and int(summary.get("pending_count", 0)) == 0
            and int(summary.get("failed_count", 0)) == 0
            and int(summary.get("stale_count", 0)) == 0
        )
    return int(summary.get("critical_issue_count", 0)) == 0


def source_activation_ops_runtime_attested(
    summary: dict[str, Any],
    decision_board: dict[str, Any],
    *,
    environment: str,
    validation_passed: bool,
) -> bool:
    p0_source_count = int(summary.get("p0_source_count", 0))
    next_actions = decision_board.get("next_actions") if isinstance(decision_board.get("next_actions"), list) else []
    p0_next_actions = [
        action
        for action in next_actions
        if isinstance(action, dict)
        and action.get("priority") == "P0"
        and action.get("action") != "no_action"
    ]
    return (
        environment in {"staging", "prod"}
        and validation_passed
        and int(summary.get("source_count", 0)) > 0
        and p0_source_count > 0
        and int(summary.get("p0_active_count", 0)) == p0_source_count
        and int(summary.get("p0_production_ready_count", 0)) == p0_source_count
        and int(summary.get("p0_runtime_readiness_attached_count", 0)) == p0_source_count
        and int(summary.get("p0_unactivated_count", 0)) == 0
        and int(summary.get("p0_activation_gap_count", 0)) == 0
        and int(summary.get("p0_critical_issue_count", 0)) == 0
        and int(summary.get("critical_issue_count", 0)) == 0
        and int(summary.get("registry_drift_count", 0)) == 0
        and int(summary.get("runtime_readiness_issue_count", 0)) == 0
        and int(summary.get("evidence_integrity_issue_count", 0)) == 0
        and int(summary.get("p0_evidence_integrity_issue_count", 0)) == 0
        and int(summary.get("pointer_issue_count", 0)) == 0
        and int(summary.get("expired_count", 0)) == 0
        and int(summary.get("revoked_count", 0)) == 0
        and int(summary.get("pending_count", 0)) == 0
        and int(summary.get("failed_count", 0)) == 0
        and int(summary.get("stale_count", 0)) == 0
        and not p0_next_actions
    )


def source_activation_ops_mode(environment: str, *, runtime_attested: bool) -> str:
    if runtime_attested:
        return "runtime_attested"
    if environment == "local":
        return "local_preflight"
    return "metadata_preflight"


def source_activation_ops_readiness_state(
    environment: str,
    *,
    passed: bool,
    runtime_attested: bool,
) -> str:
    if runtime_attested:
        return "production_like_ready"
    if environment == "local" and passed:
        return "local_preflight_ready"
    return "not_ready"


def compact_source_activation_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": row.get("source_id"),
        "product": row.get("product"),
        "environment": row.get("environment"),
        "activation_state": row.get("activation_state"),
        "risk_state": row.get("risk_state"),
        "block_reason": row.get("block_reason"),
        "evidence_integrity": row.get("evidence_integrity"),
        "runtime_readiness": row.get("runtime_readiness"),
        "days_to_expiry": row.get("days_to_expiry"),
    }


def source_evidence_integrity_summary(record: dict[str, Any] | None, *, root: Path | None = None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {"required": False, "passed": False, "issues": []}
    required = record.get("activationState") == "active" and record.get("environment") in {"staging", "prod"}
    issues = source_evidence_integrity_issues(record, root=root)
    return {
        "required": required,
        "passed": required and not issues,
        "issues": issues,
        "readiness_report": evidence_artifact_summary(
            record,
            "readinessReportUri",
            "readinessReportHash",
            root=root,
        ),
        "evidence_bundle": evidence_artifact_summary(
            record,
            "evidenceBundleUri",
            "evidenceBundleHash",
            root=root,
        ),
        "runtime_readiness": evidence_artifact_summary(
            record,
            "runtimeReadinessReportUri",
            "runtimeReadinessReportHash",
            root=root,
        ),
    }


def runtime_readiness_evidence_summary(record: dict[str, Any] | None, *, root: Path | None = None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {"required": False, "attached": False}
    required = runtime_readiness_evidence_required(record)
    artifact = evidence_artifact_summary(
        record,
        "runtimeReadinessReportUri",
        "runtimeReadinessReportHash",
        root=root,
    )
    return {
        "required": required,
        "attached": all(non_empty(record.get(field)) for field in runtime_readiness_fields()),
        "report_uri": record.get("runtimeReadinessReportUri"),
        "report_hash": record.get("runtimeReadinessReportHash"),
        "runtime_readiness_id": record.get("runtimeReadinessId"),
        "hash_valid": runtime_readiness_hash_valid(record),
        "artifact_verifiable": artifact.get("verifiable"),
        "hash_matches_artifact": artifact.get("hash_matches"),
        "integrity_issues": runtime_readiness_evidence_issues(record, root=root),
    }


def runtime_readiness_evidence_required(record: dict[str, Any]) -> bool:
    gate_badges = record.get("gateBadges") if isinstance(record.get("gateBadges"), dict) else {}
    return (
        record.get("activationState") == "active"
        and record.get("environment") in {"staging", "prod"}
        and gate_badges.get("runtimeSlo") == "passed"
    )


def runtime_readiness_fields() -> tuple[str, str, str]:
    return ("runtimeReadinessReportUri", "runtimeReadinessReportHash", "runtimeReadinessId")


def runtime_readiness_hash_valid(record: dict[str, Any]) -> bool:
    value = record.get("runtimeReadinessReportHash")
    return isinstance(value, str) and SHA256_VALUE.fullmatch(value) is not None


def runtime_readiness_evidence_issues(record: dict[str, Any] | None, *, root: Path | None = None) -> list[str]:
    if not isinstance(record, dict) or not runtime_readiness_evidence_required(record):
        return []
    missing = [field for field in runtime_readiness_fields() if not non_empty(record.get(field))]
    issues = []
    if missing:
        issues.append("runtime_readiness_evidence_missing")
    if non_empty(record.get("runtimeReadinessReportHash")) and not runtime_readiness_hash_valid(record):
        issues.append("runtime_readiness_hash_invalid")
    if not issues:
        issues.extend(
            evidence_artifact_issues(
                record,
                "runtimeReadinessReportUri",
                "runtimeReadinessReportHash",
                "runtime_readiness",
                root=root,
            )
        )
    return issues


def source_evidence_integrity_issues(record: dict[str, Any] | None, *, root: Path | None = None) -> list[str]:
    if not isinstance(record, dict):
        return []
    if record.get("activationState") != "active" or record.get("environment") not in {"staging", "prod"}:
        return []
    issues = []
    issues.extend(evidence_artifact_issues(record, "readinessReportUri", "readinessReportHash", "readiness", root=root))
    issues.extend(
        evidence_artifact_issues(
            record,
            "evidenceBundleUri",
            "evidenceBundleHash",
            "evidence_bundle",
            root=root,
        )
    )
    issues.extend(runtime_readiness_evidence_issues(record, root=root))
    return sorted(set(issues))


def evidence_artifact_summary(
    record: dict[str, Any],
    uri_field: str,
    hash_field: str,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    uri = record.get(uri_field)
    expected_hash = record.get(hash_field)
    path = evidence_artifact_path(uri, root=root)
    exists = path.is_file() if path else False
    actual_hash = hash_file(path) if exists and path is not None else None
    return {
        "uri": uri,
        "hash": expected_hash,
        "hash_valid": isinstance(expected_hash, str) and SHA256_VALUE.fullmatch(expected_hash) is not None,
        "local_path": path.as_posix() if path else None,
        "exists": exists,
        "actual_hash": actual_hash,
        "hash_matches": actual_hash == expected_hash if actual_hash and expected_hash else False,
        "verifiable": exists and actual_hash == expected_hash,
    }


def evidence_artifact_issues(
    record: dict[str, Any],
    uri_field: str,
    hash_field: str,
    prefix: str,
    *,
    root: Path | None = None,
) -> list[str]:
    uri = record.get(uri_field)
    expected_hash = record.get(hash_field)
    if not non_empty(uri) or not non_empty(expected_hash):
        return [f"{prefix}_evidence_missing"]
    if not isinstance(expected_hash, str) or SHA256_VALUE.fullmatch(expected_hash) is None:
        return [f"{prefix}_hash_invalid"]
    if root is None:
        return []
    path = evidence_artifact_path(uri, root=root)
    if path is None:
        return [] if is_external_evidence_uri(uri) else [f"{prefix}_evidence_unverifiable"]
    if not path.is_file():
        return [f"{prefix}_evidence_unverifiable"]
    return [] if hash_file(path) == expected_hash else [f"{prefix}_hash_mismatch"]


def is_external_evidence_uri(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    uri = value.strip()
    return "://" in uri and not uri.startswith("file://")


def evidence_artifact_path(value: object, *, root: Path | None) -> Path | None:
    if root is None or not isinstance(value, str) or not value.strip():
        return None
    uri = value.strip()
    if uri.startswith("file://"):
        return Path(uri.removeprefix("file://"))
    if "://" in uri:
        return None
    path = Path(uri)
    return path if path.is_absolute() else root / path


def source_activation_checks(
    bundle: dict[str, Any],
    readiness: dict[str, Any],
    *,
    source: dict[str, Any] | None,
    change_request: dict[str, Any] | None,
    source_id: str,
    environment: str,
    requested_by: str,
    approved_by: str,
    change_request_id: str,
    readiness_path: Path,
    bundle_path: Path,
    activated_at: str,
    expires_at: str,
    gate_badges: dict[str, str],
    impacted_use_cases: list[str],
    runtime_readiness: dict[str, Any] | None,
    runtime_readiness_path: Path | None,
) -> list[dict[str, Any]]:
    source_snapshot = readiness.get("source") if isinstance(readiness.get("source"), dict) else {}
    production_like = environment in {"staging", "prod"}
    checks = [
        check("bundle_type_valid", bundle.get("artifact_type") == "source_readiness_bundle.v1", {"artifact_type": bundle.get("artifact_type")}),
        check("readiness_report_present", readiness_path.is_file(), {"readiness_report": readiness_path.as_posix()}),
        check("readiness_type_valid", readiness.get("artifact_type") == "source_readiness_report.v1", {"artifact_type": readiness.get("artifact_type")}),
        check("bundle_passed", bundle.get("passed") is True, {"passed": bundle.get("passed")}),
        check("readiness_passed", readiness.get("passed") is True, {"passed": readiness.get("passed")}),
        check(
            "readiness_state_production_ready",
            readiness.get("readiness_state") == "production_ready",
            {"readiness_state": readiness.get("readiness_state")},
        ),
        check("source_registered", source is not None, {"source_id": source_id}),
        check("source_id_matches_bundle_and_readiness", source_id == bundle.get("source_id") == readiness.get("source_id"), {"bundle_source_id": bundle.get("source_id"), "readiness_source_id": readiness.get("source_id")}),
        check("environment_matches_bundle_and_readiness", environment == bundle.get("environment") == readiness.get("environment"), {"bundle_environment": bundle.get("environment"), "readiness_environment": readiness.get("environment")}),
        check("readiness_id_matches_bundle", bundle.get("readiness_id") == readiness.get("readiness_id"), {"bundle_readiness_id": bundle.get("readiness_id"), "readiness_id": readiness.get("readiness_id")}),
        check("readiness_id_is_sha256_hex", isinstance(readiness.get("readiness_id"), str) and re.fullmatch(r"[0-9a-f]{64}", str(readiness.get("readiness_id"))) is not None, {"readiness_id": readiness.get("readiness_id")}),
        check("requested_by_declared", non_empty(requested_by), {"requested_by": requested_by}),
        check("approved_by_declared", non_empty(approved_by), {"approved_by": approved_by}),
        check("maker_checker_separated", non_empty(requested_by) and non_empty(approved_by) and requested_by != approved_by, {"requested_by": requested_by, "approved_by": approved_by}),
        check("change_request_declared", non_empty(change_request_id), {"change_request_id": change_request_id}),
        check("change_request_registered", change_request is not None, {"change_request_id": change_request_id}),
        check("change_request_source_onboarding", change_request is not None and change_request.get("type") == "source_onboarding", {"type": change_request.get("type") if change_request else None}),
        check("change_request_approved", change_request is not None and change_request.get("status") == "approved", {"status": change_request.get("status") if change_request else None}),
        check("change_request_environment_matches", change_request is not None and change_request.get("targetEnvironment") == environment, {"change_request_environment": change_request.get("targetEnvironment") if change_request else None, "activation_environment": environment}),
        check("change_request_product_matches", source is not None and change_request is not None and change_request.get("product") == source.get("product"), {"change_request_product": change_request.get("product") if change_request else None, "source_product": source.get("product") if source else None}),
        check("change_request_domain_matches", source is not None and change_request is not None and change_request.get("domain") == source.get("domain"), {"change_request_domain": change_request.get("domain") if change_request else None, "source_domain": source.get("domain") if source else None}),
        check("readiness_report_hash_calculated", SHA256_VALUE.fullmatch(hash_file(readiness_path)) is not None if readiness_path.is_file() else False, {"readiness_report": readiness_path.as_posix()}),
        check("bundle_hash_calculated", SHA256_VALUE.fullmatch(hash_file(bundle_path)) is not None, {"bundle": bundle_path.as_posix()}),
        check("registry_hash_calculated", source is not None, {"source_id": source_id}),
        check("expires_after_activation", timestamp_after(expires_at, activated_at), {"activated_at": activated_at, "expires_at": expires_at}),
        check("all_gate_badges_present", REQUIRED_GATE_BADGES <= set(gate_badges), {"gate_badges": gate_badges}),
        check(
            "all_activation_gate_badges_passing",
            all(value in PASSING_GATE_STATUSES for value in gate_badges.values()),
            {"gate_badges": gate_badges},
        ),
        check(
            "runtime_readiness_report_present",
            not production_like or (runtime_readiness_path is not None and runtime_readiness_path.is_file()),
            {
                "environment": environment,
                "runtime_readiness_report": runtime_readiness_path.as_posix() if runtime_readiness_path else None,
            },
        ),
        check(
            "runtime_readiness_report_type_valid",
            not production_like or (isinstance(runtime_readiness, dict) and runtime_readiness.get("artifact_type") == "runtime_readiness_report.v1"),
            {"artifact_type": runtime_readiness.get("artifact_type") if isinstance(runtime_readiness, dict) else None},
        ),
        check(
            "runtime_readiness_environment_matches",
            not production_like or (isinstance(runtime_readiness, dict) and runtime_readiness.get("environment") == environment),
            {"runtime_environment": runtime_readiness.get("environment") if isinstance(runtime_readiness, dict) else None, "activation_environment": environment},
        ),
        check(
            "runtime_readiness_report_passed",
            not production_like or (isinstance(runtime_readiness, dict) and runtime_readiness.get("passed") is True),
            {"passed": runtime_readiness.get("passed") if isinstance(runtime_readiness, dict) else None},
        ),
        check("impacted_use_cases_declared", bool(impacted_use_cases), {"impacted_use_cases": impacted_use_cases}),
    ]
    if source is not None:
        canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
        bridge = source.get("bridge") if isinstance(source.get("bridge"), dict) else {}
        checks.extend(
            [
                check("canonical_topic_matches_registry", source_snapshot.get("canonical_topic") == canonical.get("topic"), {"readiness": source_snapshot.get("canonical_topic"), "registry": canonical.get("topic")}),
                check("bronze_target_matches_registry", source_snapshot.get("bronze_target") == canonical.get("bronzeTarget"), {"readiness": source_snapshot.get("bronze_target"), "registry": canonical.get("bronzeTarget")}),
                check("schema_subject_matches_registry", source_snapshot.get("schema_subject") == canonical.get("schemaSubject"), {"readiness": source_snapshot.get("schema_subject"), "registry": canonical.get("schemaSubject")}),
                check("bridge_mode_matches_registry", (source_snapshot.get("bridge") if isinstance(source_snapshot.get("bridge"), dict) else {}).get("mode") == bridge.get("mode"), {"readiness": (source_snapshot.get("bridge") if isinstance(source_snapshot.get("bridge"), dict) else {}).get("mode"), "registry": bridge.get("mode")}),
            ]
        )
    return checks


def source_revocation_checks(
    *,
    source: dict[str, Any] | None,
    change_request: dict[str, Any] | None,
    previous_record: dict[str, Any] | None,
    previous_state: dict[str, Any] | None,
    source_id: str,
    environment: str,
    requested_by: str,
    approved_by: str,
    change_request_id: str,
    ledger_path: Path,
    active_state_path: Path,
    reason: str | None,
    evidence_uri: str | None,
    impacted_use_cases: list[str],
    allow_missing_active_pointer: bool = False,
) -> list[dict[str, Any]]:
    active_record_matches_source_environment = (
        previous_record is not None
        and previous_record.get("sourceId") == source_id
        and previous_record.get("environment") == environment
    )
    active_record_is_active = previous_record is not None and previous_record.get("activationState") == "active"
    pointer_exists = active_state_path.is_file()
    missing_pointer_break_glass = (
        allow_missing_active_pointer
        and not pointer_exists
        and active_record_matches_source_environment
        and active_record_is_active
    )
    return [
        check("source_registered", source is not None, {"source_id": source_id}),
        check("environment_supported", environment in VALID_ENVIRONMENTS, {"environment": environment}),
        check("ledger_exists", ledger_path.is_file(), {"ledger": ledger_path.as_posix()}),
        check(
            "active_pointer_exists",
            pointer_exists or missing_pointer_break_glass,
            {
                "active_state_path": active_state_path.as_posix(),
                "exists": pointer_exists,
                "allow_missing_active_pointer": allow_missing_active_pointer,
                "missing_pointer_break_glass": missing_pointer_break_glass,
            },
        ),
        check(
            "active_pointer_matches_source_environment",
            (
                isinstance(previous_state, dict)
                and previous_state.get("source_id") == source_id
                and previous_state.get("environment") == environment
            )
            or missing_pointer_break_glass,
            {
                "pointer_source_id": previous_state.get("source_id") if isinstance(previous_state, dict) else None,
                "pointer_environment": previous_state.get("environment") if isinstance(previous_state, dict) else None,
                "missing_pointer_break_glass": missing_pointer_break_glass,
            },
        ),
        check(
            "active_pointer_matches_latest_activation",
            (
                isinstance(previous_state, dict)
                and previous_record is not None
                and previous_state.get("activation_id") == previous_record.get("activationId")
            )
            or missing_pointer_break_glass,
            {
                "pointer_activation_id": previous_state.get("activation_id") if isinstance(previous_state, dict) else None,
                "latest_activation_id": previous_record.get("activationId") if previous_record else None,
                "missing_pointer_break_glass": missing_pointer_break_glass,
            },
        ),
        check("active_activation_found", previous_record is not None, {"source_id": source_id, "environment": environment}),
        check(
            "active_activation_matches_source_environment",
            active_record_matches_source_environment,
            {
                "record_source_id": previous_record.get("sourceId") if previous_record else None,
                "record_environment": previous_record.get("environment") if previous_record else None,
            },
        ),
        check(
            "active_activation_is_active",
            active_record_is_active,
            {"activation_state": previous_record.get("activationState") if previous_record else None},
        ),
        check(
            "missing_active_pointer_break_glass_valid",
            pointer_exists or not allow_missing_active_pointer or missing_pointer_break_glass,
            {
                "active_state_path": active_state_path.as_posix(),
                "exists": pointer_exists,
                "allow_missing_active_pointer": allow_missing_active_pointer,
                "missing_pointer_break_glass": missing_pointer_break_glass,
            },
        ),
        check("requested_by_declared", non_empty(requested_by), {"requested_by": requested_by}),
        check("approved_by_declared", non_empty(approved_by), {"approved_by": approved_by}),
        check("maker_checker_separated", non_empty(requested_by) and non_empty(approved_by) and requested_by != approved_by, {"requested_by": requested_by, "approved_by": approved_by}),
        check("change_request_declared", non_empty(change_request_id), {"change_request_id": change_request_id}),
        check("change_request_registered", change_request is not None, {"change_request_id": change_request_id}),
        check(
            "change_request_source_activation_revoke",
            change_request is not None and change_request.get("type") == "source_activation_revoke",
            {"type": change_request.get("type") if change_request else None},
        ),
        check("change_request_approved", change_request is not None and change_request.get("status") == "approved", {"status": change_request.get("status") if change_request else None}),
        check(
            "change_request_environment_matches",
            change_request is not None and change_request.get("targetEnvironment") == environment,
            {"change_request_environment": change_request.get("targetEnvironment") if change_request else None, "revocation_environment": environment},
        ),
        check(
            "change_request_product_matches",
            source is not None and change_request is not None and change_request.get("product") == source.get("product"),
            {"change_request_product": change_request.get("product") if change_request else None, "source_product": source.get("product") if source else None},
        ),
        check(
            "change_request_domain_matches",
            source is not None and change_request is not None and change_request.get("domain") == source.get("domain"),
            {"change_request_domain": change_request.get("domain") if change_request else None, "source_domain": source.get("domain") if source else None},
        ),
        check("revocation_reason_declared", non_empty(reason), {"reason": reason}),
        check("revocation_evidence_declared", non_empty(evidence_uri), {"evidence_uri": evidence_uri}),
        check("impacted_use_cases_declared", bool(impacted_use_cases), {"impacted_use_cases": impacted_use_cases}),
    ]


def source_activation_gate_badges(
    readiness: dict[str, Any],
    *,
    runtime_readiness: dict[str, Any] | None = None,
) -> dict[str, str]:
    check_status = {
        str(item.get("name")): item.get("passed") is True
        for item in readiness.get("checks", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    bridge_required = (readiness.get("source") if isinstance(readiness.get("source"), dict) else {}).get("bridge")
    bridge_is_required = isinstance(bridge_required, dict) and bridge_required.get("required") is True
    runtime_slo = runtime_slo_badge(readiness, runtime_readiness)
    return {
        "schema": badge_status(check_status, "schema_"),
        "bronzeReplay": badge_status(check_status, "ingestion_", "replay_"),
        "offsetLedger": badge_status(check_status, "offset_ledger_"),
        "bridge": badge_status(check_status, "bridge_") if bridge_is_required else "not_required",
        "privacyTenant": badge_status(check_status, "privacy_", "tenant_"),
        "catalogLineage": badge_status(check_status, "catalog_", "openlineage_"),
        "changeControl": badge_status(check_status, "change_control_", "source_onboarding_change_"),
        "runtimeSlo": runtime_slo,
    }


def runtime_slo_badge(readiness: dict[str, Any], runtime_readiness: dict[str, Any] | None) -> str:
    environment = readiness.get("environment")
    if environment not in {"staging", "prod"}:
        return "not_applicable"
    if not isinstance(runtime_readiness, dict):
        return "pending_runtime"
    if runtime_readiness.get("artifact_type") != "runtime_readiness_report.v1":
        return "failed"
    if runtime_readiness.get("environment") != environment:
        return "failed"
    return "passed" if runtime_readiness.get("passed") is True else "failed"


def badge_status(check_status: dict[str, bool], *prefixes: str) -> str:
    relevant = [passed for name, passed in check_status.items() if any(name.startswith(prefix) for prefix in prefixes)]
    if not relevant:
        return "not_applicable"
    return "passed" if all(relevant) else "failed"


def resolve_artifact_path(value: object, root: Path, bundle_path: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        return bundle_path.parent / "missing-source-readiness-report.json"
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = root / path
    if candidate.is_file():
        return candidate
    return bundle_path.parent / path


def resolve_optional_artifact_path(value: str | Path | None, root: Path, bundle_path: Path) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = root / path
    if candidate.is_file():
        return candidate
    return bundle_path.parent / path


def impacted_use_cases_from_change_request(change_request: dict[str, Any] | None) -> list[str]:
    if not isinstance(change_request, dict):
        return []
    use_case = change_request.get("useCase")
    return [use_case] if isinstance(use_case, str) and use_case.strip() else []


def rollback_target(previous_state: dict[str, Any] | None, *, source_id: str, environment: str) -> dict[str, Any] | None:
    if not isinstance(previous_state, dict):
        return None
    if previous_state.get("source_id") != source_id or previous_state.get("environment") != environment:
        return None
    return {
        "activation_id": previous_state.get("activation_id"),
        "readiness_id": previous_state.get("readiness_id"),
        "activated_at": previous_state.get("activated_at"),
        "expires_at": previous_state.get("expires_at"),
        "activation_manifest_uri": previous_state.get("activation_manifest_uri"),
    }


def latest_activation_record(root: Path, ledger_path: Path, *, source_id: str, environment: str) -> dict[str, Any] | None:
    if not ledger_path.is_file():
        return None
    records = [
        record
        for record in load_source_activations(ledger_path)
        if record.get("sourceId") == source_id and record.get("environment") == environment
    ]
    if not records:
        return None
    return sorted(records, key=lambda item: str(item.get("activatedAt") or ""), reverse=True)[0]


def latest_records_by_source_environment(
    records: list[dict[str, Any]],
    environment: str,
    *,
    observed_at: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    compatible = [
        record
        for record in records
        if activation_environment_compatible(str(record.get("environment") or ""), environment)
        and (observed_at is None or activation_effective_at_or_before(record, observed_at))
    ]
    for record in sorted(compatible, key=lambda item: str(item.get("activatedAt") or ""), reverse=True):
        source_id = str(record.get("sourceId") or "")
        if source_id and source_id not in latest:
            latest[source_id] = record
    return latest


def activation_effective_at_or_before(record: dict[str, Any], observed_at: datetime) -> bool:
    activated_at = parse_optional_timestamp(record.get("activatedAt"))
    return activated_at is None or activated_at <= observed_at


def resolve_active_pointer_dir(root: Path, active_pointer_dir: str | Path | None) -> Path:
    if active_pointer_dir is None:
        return root / "governance" / "source-active-pointers"
    path = Path(active_pointer_dir)
    return path if path.is_absolute() else root / path


def default_active_pointer_path(root: Path, source_id: str, environment: str) -> Path:
    return root / "governance" / "source-active-pointers" / f"{source_id}.{environment}.json"


def default_revocation_gate_badges() -> dict[str, str]:
    return {key: "not_applicable" for key in REQUIRED_GATE_BADGES}


def string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def parse_optional_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return parse_timestamp(value)
    except ValueError:
        return None


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def row_has_issue(row: dict[str, Any], issue_names: set[str]) -> bool:
    issues = row.get("issues")
    return isinstance(issues, list) and any(isinstance(issue, str) and issue in issue_names for issue in issues)


def validate_source_activation_record(
    path: Path,
    record: object,
    index: int,
    *,
    seen: set[str],
    sources: dict[str, dict[str, Any]],
    change_requests: dict[str, dict[str, Any]],
    use_cases: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"activations[{index}]"
    if not isinstance(record, dict):
        result.error(path, f"{prefix} must be an object")
        return

    activation_id = require_string(path, result, record, "activationId", prefix)
    source_id = require_string(path, result, record, "sourceId", prefix)
    environment = require_string(path, result, record, "environment", prefix)
    activation_state = require_string(path, result, record, "activationState", prefix)
    requested_by = require_string(path, result, record, "requestedBy", prefix)
    approved_by = require_string(path, result, record, "approvedBy", prefix)
    change_request_id = require_string(path, result, record, "changeRequestId", prefix)
    activated_at = require_string(path, result, record, "activatedAt", prefix)
    expires_at = require_string(path, result, record, "expiresAt", prefix)
    readiness_id = require_string(path, result, record, "readinessId", prefix)
    require_string(path, result, record, "readinessReportUri", prefix)
    readiness_hash = require_string(path, result, record, "readinessReportHash", prefix)
    require_string(path, result, record, "evidenceBundleUri", prefix)
    bundle_hash = require_string(path, result, record, "evidenceBundleHash", prefix)
    registry_hash = require_string(path, result, record, "sourceRegistryHash", prefix)
    canonical_topic = require_string(path, result, record, "canonicalTopic", prefix)
    bronze_target = require_string(path, result, record, "bronzeTarget", prefix)
    schema_subject = require_string(path, result, record, "schemaSubject", prefix)
    mode = require_string(path, result, record, "mode", prefix)
    impacted_use_cases = require_string_list(path, result, record, "impactedUseCases", prefix)

    if activation_id:
        if activation_id in seen:
            result.error(path, f"{prefix}.activationId duplicates activation {activation_id}")
        seen.add(activation_id)
    if environment and environment not in VALID_ENVIRONMENTS:
        result.error(path, f"{prefix}.environment must be one of {sorted(VALID_ENVIRONMENTS)}")
    if activation_state and activation_state not in VALID_ACTIVATION_STATES:
        result.error(path, f"{prefix}.activationState must be one of {sorted(VALID_ACTIVATION_STATES)}")
    if requested_by and approved_by and requested_by == approved_by:
        result.error(path, f"{prefix}.approvedBy must differ from requestedBy for maker-checker")
    if readiness_id and not re.fullmatch(r"[0-9a-f]{64}", readiness_id):
        result.error(path, f"{prefix}.readinessId must be a sha256 hex digest")
    for field, value in (
        ("readinessReportHash", readiness_hash),
        ("evidenceBundleHash", bundle_hash),
        ("sourceRegistryHash", registry_hash),
    ):
        if value and not SHA256_VALUE.fullmatch(value):
            result.error(path, f"{prefix}.{field} must be sha256:<64 lowercase hex>")

    activated = parse_record_timestamp(path, result, activated_at, f"{prefix}.activatedAt")
    expires = parse_record_timestamp(path, result, expires_at, f"{prefix}.expiresAt")
    if activated and expires and expires <= activated:
        result.error(path, f"{prefix}.expiresAt must be later than activatedAt")

    source = sources.get(source_id or "")
    if not source:
        result.error(path, f"{prefix}.sourceId references unknown source {source_id!r}")
    else:
        canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
        bridge = source.get("bridge") if isinstance(source.get("bridge"), dict) else {}
        if canonical_topic and canonical.get("topic") != canonical_topic:
            result.error(path, f"{prefix}.canonicalTopic must match source registry canonical.topic")
        if bronze_target and canonical.get("bronzeTarget") != bronze_target:
            result.error(path, f"{prefix}.bronzeTarget must match source registry canonical.bronzeTarget")
        if schema_subject and canonical.get("schemaSubject") != schema_subject:
            result.error(path, f"{prefix}.schemaSubject must match source registry canonical.schemaSubject")
        if mode and bridge.get("mode") != mode:
            result.error(path, f"{prefix}.mode must match source registry bridge.mode")

    change_request = change_requests.get(change_request_id or "")
    if not change_request:
        result.error(path, f"{prefix}.changeRequestId references unknown change request {change_request_id!r}")
    else:
        expected_type = "source_activation_revoke" if activation_state == "revoked" else "source_onboarding"
        if change_request.get("type") != expected_type:
            result.error(path, f"{prefix}.changeRequestId must reference a {expected_type} request")
        if change_request.get("status") != "approved":
            result.error(path, f"{prefix}.changeRequestId must reference an approved request")
        if environment and change_request.get("targetEnvironment") != environment:
            result.error(path, f"{prefix}.environment must match change request targetEnvironment")
        if source:
            if change_request.get("product") != source.get("product"):
                result.error(path, f"{prefix}.changeRequestId product must match source product")
            if change_request.get("domain") != source.get("domain"):
                result.error(path, f"{prefix}.changeRequestId domain must match source domain")

    gate_badges = record.get("gateBadges")
    if not isinstance(gate_badges, dict):
        result.error(path, f"{prefix}.gateBadges must be an object")
    else:
        missing = sorted(REQUIRED_GATE_BADGES - set(gate_badges))
        if missing:
            result.error(path, f"{prefix}.gateBadges missing required badges {missing}")
        for key, value in gate_badges.items():
            if key not in REQUIRED_GATE_BADGES:
                result.error(path, f"{prefix}.gateBadges.{key} is not a supported badge")
            if value not in VALID_GATE_STATUSES:
                result.error(path, f"{prefix}.gateBadges.{key} must be one of {sorted(VALID_GATE_STATUSES)}")
        if runtime_readiness_evidence_required(record):
            for field in runtime_readiness_fields():
                require_string(path, result, record, field, prefix)
            runtime_hash = record.get("runtimeReadinessReportHash")
            if runtime_hash and not runtime_readiness_hash_valid(record):
                result.error(path, f"{prefix}.runtimeReadinessReportHash must be sha256:<64 lowercase hex>")

    if impacted_use_cases:
        unknown = sorted(item for item in impacted_use_cases if item not in use_cases)
        if unknown:
            result.error(path, f"{prefix}.impactedUseCases references unknown use cases {unknown}")


def activation_summary(
    record: dict[str, Any],
    observed_at: datetime,
    report_environment: str,
    *,
    current_registry_hash: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    activated_at = parse_timestamp(record.get("activatedAt"))
    expires_at = parse_timestamp(record.get("expiresAt"))
    gate_badges = record.get("gateBadges") if isinstance(record.get("gateBadges"), dict) else {}
    block_reason = activation_block_reason(
        record,
        gate_badges,
        observed_at,
        report_environment,
        expires_at,
        current_registry_hash,
        root=root,
    )
    return {
        "source_id": record.get("sourceId"),
        "activation_id": record.get("activationId"),
        "activation_state": record.get("activationState"),
        "effective_status": "blocked",
        "business_readiness": "blocked",
        "environment": record.get("environment"),
        "activated_at": format_timestamp(activated_at),
        "expires_at": format_timestamp(expires_at),
        "readiness_id": record.get("readinessId"),
        "readiness_report_hash": record.get("readinessReportHash"),
        "evidence_bundle_hash": record.get("evidenceBundleHash"),
        "runtime_readiness": runtime_readiness_evidence_summary(record, root=root),
        "source_registry_hash": record.get("sourceRegistryHash"),
        "gate_badges": dict(sorted(gate_badges.items())),
        "impacted_use_cases": sorted(str(item) for item in record.get("impactedUseCases", []) if isinstance(item, str)),
        "block_reason": block_reason,
    }


def activation_block_reason(
    record: dict[str, Any],
    gate_badges: dict[str, Any],
    observed_at: datetime,
    report_environment: str,
    expires_at: datetime | None,
    current_registry_hash: str | None = None,
    *,
    root: Path | None = None,
) -> str | None:
    state = str(record.get("activationState") or "unknown")
    if state != "active":
        return f"activation_not_active:{state}"
    if not activation_environment_compatible(str(record.get("environment") or ""), report_environment):
        return "environment_not_compatible"
    if expires_at is None:
        return "expires_at_invalid"
    if expires_at <= observed_at:
        return "activation_expired"
    if current_registry_hash and record.get("sourceRegistryHash") != current_registry_hash:
        return "source_registry_hash_mismatch"
    evidence_issues = source_evidence_integrity_issues(record, root=root)
    if evidence_issues:
        return evidence_issues[0]
    failed_gates = sorted(key for key, value in gate_badges.items() if value not in PASSING_GATE_STATUSES)
    if failed_gates:
        return f"gate_badges_not_passing:{','.join(failed_gates)}"
    return None


def activation_environment_compatible(activation_environment: str, report_environment: str) -> bool:
    if report_environment == "prod":
        return activation_environment == "prod"
    if report_environment == "staging":
        return activation_environment in {"staging", "prod"}
    if report_environment == "local":
        return activation_environment in VALID_ENVIRONMENTS
    return False


def source_index(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "platform" / "ingestion" / "source-registry.yaml"
    if not path.is_file():
        return {}
    registry = load_yaml(path)
    sources = registry.get("sources")
    if not isinstance(sources, list):
        return {}
    return {
        str(source["sourceId"]): source
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("sourceId"), str)
    }


def change_request_index(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "governance" / "change-requests.yaml"
    if not path.is_file():
        return {}
    registry = load_yaml(path)
    requests = registry.get("change_requests")
    if not isinstance(requests, list):
        return {}
    return {
        str(request["id"]): request
        for request in requests
        if isinstance(request, dict) and isinstance(request.get("id"), str)
    }


def use_case_ids(root: Path) -> set[str]:
    path = root / "use-cases" / "registry.yaml"
    if not path.is_file():
        return set()
    registry = load_yaml(path)
    use_cases = registry.get("useCases") or registry.get("use_cases")
    if not isinstance(use_cases, list):
        return set()
    return {str(use_case["id"]) for use_case in use_cases if isinstance(use_case, dict) and isinstance(use_case.get("id"), str)}


def parse_record_timestamp(path: Path, result: ValidationResult, value: str | None, field: str) -> datetime | None:
    if not value:
        return None
    try:
        return parse_timestamp(value)
    except ValueError as exc:
        result.error(path, f"{field} must be an ISO-8601 UTC timestamp: {exc}")
        return None


def parse_timestamp(value: str | datetime | object) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a non-empty string")
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_after(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    try:
        return parse_timestamp(left) > parse_timestamp(right)
    except ValueError:
        return False


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def stable_id(*parts: object) -> str:
    import hashlib

    payload = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
