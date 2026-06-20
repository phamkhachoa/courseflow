from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.attestations import verify_attestation_file
from enterprise_dp.contracts import VALID_COMPATIBILITY_MODES, load_yaml


REPORT_VERSION = 1


@dataclass(frozen=True)
class SchemaRegistryCheckResult:
    output_path: Path
    report: dict[str, Any]


@dataclass(frozen=True)
class SchemaRegistryOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_schema_registry_report(
    root: str | Path,
    output_path: str | Path,
    *,
    topic_name: str | None = None,
    registry_uri: str | None = None,
    generated_at: str | None = None,
) -> SchemaRegistryCheckResult:
    report = build_schema_registry_report(
        root,
        topic_name=topic_name,
        registry_uri=registry_uri,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SchemaRegistryCheckResult(output_path=target, report=report)


def write_schema_registry_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    release_id: str | None = None,
    compatibility_report_path: str | Path | None = None,
    publication_evidence_path: str | Path | None = None,
    attestation_path: str | Path | None = None,
    generated_at: str | None = None,
) -> SchemaRegistryOpsReportResult:
    report = build_schema_registry_ops_report(
        root,
        environment=environment,
        release_id=release_id,
        compatibility_report_path=compatibility_report_path,
        publication_evidence_path=publication_evidence_path,
        attestation_path=attestation_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SchemaRegistryOpsReportResult(output_path=target, report=report)


def build_schema_registry_report(
    root: str | Path,
    *,
    topic_name: str | None = None,
    registry_uri: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    all_topic_contracts = load_topic_contracts(platform_root)
    topic_contracts = filter_topic_contracts(all_topic_contracts, topic_name=topic_name)
    subjects = [subject_report(platform_root, path, contract, all_topic_contracts) for path, contract in topic_contracts]
    passed = all(subject["compatibility_passed"] for subject in subjects)
    return {
        "artifact_type": "schema_registry_compatibility_report.v1",
        "report_version": REPORT_VERSION,
        "generated_at": generated_at or utc_now(),
        "registry_uri": registry_uri or "local-json-schema-registry-preflight",
        "mode": "local_preflight",
        "compatibility_passed": passed,
        "subject_count": len(subjects),
        "subjects": subjects,
        "summary": {
            "passed_subjects": sum(1 for subject in subjects if subject["compatibility_passed"]),
            "failed_subjects": sum(1 for subject in subjects if not subject["compatibility_passed"]),
        },
    }


def build_schema_registry_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    release_id: str | None = None,
    compatibility_report_path: str | Path | None = None,
    publication_evidence_path: str | Path | None = None,
    attestation_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    compatibility_report = (
        load_json(Path(compatibility_report_path))
        if compatibility_report_path
        else build_schema_registry_report(platform_root, generated_at=generated)
    )
    publication_evidence = load_json(Path(publication_evidence_path)) if publication_evidence_path else None
    publication_evidence_hash = hash_file(publication_evidence_path) if publication_evidence_path else None
    attestation_verification = (
        verify_attestation_file(
            platform_root,
            attestation_path,
            evidence_kind="schema_registry",
            environment=environment,
            release_id=release_id,
        )
        if attestation_path
        else None
    )
    registry_uri = (
        publication_evidence.get("registry_uri")
        if isinstance(publication_evidence, dict) and publication_evidence.get("registry_uri")
        else compatibility_report.get("registry_uri")
    )
    source_subjects = source_subject_index(platform_root)
    publication_subjects = publication_subject_index(publication_evidence)
    subjects = [
        schema_registry_ops_subject(
            subject,
            source_subjects.get(str(subject.get("subject") or ""), []),
            publication_subjects.get(str(subject.get("subject") or "")),
            environment=environment,
            registry_uri=registry_uri,
            publication_evidence=publication_evidence,
        )
        for subject in compatibility_report.get("subjects", [])
        if isinstance(subject, dict)
    ]
    global_checks = schema_registry_ops_global_checks(
        compatibility_report,
        publication_evidence,
        attestation_verification,
        environment=environment,
        registry_uri=registry_uri,
        publication_evidence_hash=publication_evidence_hash,
    )
    failed_subjects = [subject for subject in subjects if subject.get("passed") is not True]
    failed_global_checks = [check for check in global_checks if check.get("passed") is not True]
    p0_subjects = [
        subject
        for subject in subjects
        if any(source.get("priority") == "P0" for source in subject.get("sources", []))
    ]
    p0_failed_subjects = [
        subject
        for subject in failed_subjects
        if any(source.get("priority") == "P0" for source in subject.get("sources", []))
    ]
    passed = not failed_subjects and not failed_global_checks
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    return {
        "artifact_type": "schema_registry_ops_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id("schema-registry-ops", environment, release_id, generated, registry_uri, compatibility_report, publication_evidence),
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "capability_id": "schema-registry-compatibility",
        "readiness_state": readiness_state,
        "mode": "local_preflight" if environment == "local" and publication_evidence is None else "external_registry_evidence",
        "registry_uri": registry_uri,
        "compatibility_report": {
            "source": "artifact" if compatibility_report_path else "generated_from_root",
            "uri": Path(compatibility_report_path).as_posix() if compatibility_report_path else None,
            "hash": hash_file(compatibility_report_path) if compatibility_report_path else content_hash(compatibility_report),
            "artifact_type": compatibility_report.get("artifact_type"),
            "compatibility_passed": compatibility_report.get("compatibility_passed"),
            "subject_count": compatibility_report.get("subject_count"),
        },
        "publication_evidence": {
            "attached": publication_evidence is not None,
            "uri": Path(publication_evidence_path).as_posix() if publication_evidence_path else None,
            "hash": publication_evidence_hash,
            "artifact_type": publication_evidence.get("artifact_type") if isinstance(publication_evidence, dict) else None,
            "environment": publication_evidence.get("environment") if isinstance(publication_evidence, dict) else None,
            "registry_vendor": publication_evidence.get("registry_vendor") if isinstance(publication_evidence, dict) else None,
            "registry_api": publication_evidence.get("registry_api") if isinstance(publication_evidence, dict) else None,
            "registry_uri": publication_evidence.get("registry_uri") if isinstance(publication_evidence, dict) else None,
        },
        "attestation": {
            "attached": attestation_verification is not None,
            "uri": Path(attestation_path).as_posix() if attestation_path else None,
            "hash": hash_file(attestation_path) if attestation_path else None,
            "passed": attestation_verification.get("passed") if isinstance(attestation_verification, dict) else None,
            "subject_uri": attestation_verification.get("subject_uri") if isinstance(attestation_verification, dict) else None,
            "subject_hash": attestation_verification.get("subject_hash") if isinstance(attestation_verification, dict) else None,
            "producer": attestation_verification.get("producer") if isinstance(attestation_verification, dict) else None,
            "signing_key_id": attestation_verification.get("signing_key_id") if isinstance(attestation_verification, dict) else None,
            "required": attestation_verification.get("required", {}) if isinstance(attestation_verification, dict) else {},
        },
        "checks": global_checks,
        "subjects": subjects,
        "decision_board": {
            "failed_subjects": [compact_ops_subject(subject) for subject in failed_subjects[:30]],
            "p0_failed_subjects": [compact_ops_subject(subject) for subject in p0_failed_subjects[:30]],
            "unpublished_p0_subjects": [
                compact_ops_subject(subject)
                for subject in p0_failed_subjects
                if any(issue in subject.get("issues", []) for issue in {"subject_not_registered", "publication_evidence_missing"})
            ][:30],
        },
        "summary": {
            "subject_count": len(subjects),
            "passed_subject_count": len(subjects) - len(failed_subjects),
            "failed_subject_count": len(failed_subjects),
            "p0_subject_count": len(p0_subjects),
            "p0_failed_subject_count": len(p0_failed_subjects),
            "global_failed_check_count": len(failed_global_checks),
            "publication_evidence_attached": publication_evidence is not None,
            "producer_enforcement_gap_count": sum(
                1 for subject in subjects if "producer_not_enforced" in subject.get("issues", [])
            ),
            "broker_validation_gap_count": sum(
                1 for subject in subjects if "broker_or_sink_validation_missing" in subject.get("issues", [])
            ),
        },
        "passed": passed,
    }


def schema_registry_ops_global_checks(
    compatibility_report: dict[str, Any],
    publication_evidence: dict[str, Any] | None,
    attestation_verification: dict[str, Any] | None,
    *,
    environment: str,
    registry_uri: object,
    publication_evidence_hash: str | None,
) -> list[dict[str, Any]]:
    production_like = environment in {"staging", "prod"}
    return [
        check_result(
            "compatibility_report_type_valid",
            compatibility_report.get("artifact_type") == "schema_registry_compatibility_report.v1",
            {"artifact_type": compatibility_report.get("artifact_type")},
        ),
        check_result(
            "compatibility_report_passed",
            compatibility_report.get("compatibility_passed") is True,
            {"compatibility_passed": compatibility_report.get("compatibility_passed")},
        ),
        check_result(
            "publication_evidence_attached",
            not production_like or publication_evidence is not None,
            {"environment": environment, "attached": publication_evidence is not None},
        ),
        check_result(
            "publication_evidence_type_valid",
            publication_evidence is None or publication_evidence.get("artifact_type") == "schema_registry_publication_manifest.v1",
            {"artifact_type": publication_evidence.get("artifact_type") if isinstance(publication_evidence, dict) else None},
        ),
        check_result(
            "publication_environment_matches",
            publication_evidence is None or publication_evidence.get("environment") == environment,
            {"expected": environment, "actual": publication_evidence.get("environment") if isinstance(publication_evidence, dict) else None},
        ),
        check_result(
            "production_registry_uri_declared",
            not production_like or production_registry_uri(registry_uri),
            {"environment": environment, "registry_uri": registry_uri},
        ),
        check_result(
            "external_attestation_verified",
            not production_like or (isinstance(attestation_verification, dict) and attestation_verification.get("passed") is True),
            {
                "environment": environment,
                "attached": attestation_verification is not None,
                "passed": attestation_verification.get("passed") if isinstance(attestation_verification, dict) else None,
                "required": attestation_verification.get("required", {}) if isinstance(attestation_verification, dict) else {},
            },
        ),
        check_result(
            "attestation_subject_hash_matches_publication",
            not production_like
            or (
                isinstance(attestation_verification, dict)
                and publication_evidence_hash is not None
                and attestation_verification.get("subject_hash") == publication_evidence_hash
            ),
            {
                "attestation_subject_hash": attestation_verification.get("subject_hash") if isinstance(attestation_verification, dict) else None,
                "publication_evidence_hash": publication_evidence_hash,
            },
        ),
    ]


def schema_registry_ops_subject(
    compatibility_subject: dict[str, Any],
    source_refs: list[dict[str, Any]],
    publication_subject: dict[str, Any] | None,
    *,
    environment: str,
    registry_uri: object,
    publication_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    production_like = environment in {"staging", "prod"}
    expected_subject = str(compatibility_subject.get("subject") or "")
    expected_compatibility = compatibility_subject.get("compatibility")
    payload_schema = compatibility_subject.get("payload_schema") if isinstance(compatibility_subject.get("payload_schema"), dict) else {}
    payload_hash = payload_schema.get("hash")
    source_refs = sorted(source_refs, key=lambda item: (str(item.get("priority")), str(item.get("source_id"))))
    checks = [
        check_result(
            "compatibility_passed",
            compatibility_subject.get("compatibility_passed") is True,
            {"compatibility_passed": compatibility_subject.get("compatibility_passed")},
        ),
        check_result(
            "publication_evidence_available_for_production",
            not production_like or publication_evidence is not None,
            {"environment": environment, "attached": publication_evidence is not None},
        ),
        check_result(
            "subject_registered",
            not production_like or (isinstance(publication_subject, dict) and publication_subject.get("registered") is True),
            {"subject": expected_subject, "registered": publication_subject.get("registered") if isinstance(publication_subject, dict) else None},
        ),
        check_result(
            "subject_schema_id_present",
            not production_like or (isinstance(publication_subject, dict) and non_empty(publication_subject.get("schema_id") or publication_subject.get("artifact_id"))),
            {
                "schema_id": publication_subject.get("schema_id") if isinstance(publication_subject, dict) else None,
                "artifact_id": publication_subject.get("artifact_id") if isinstance(publication_subject, dict) else None,
            },
        ),
        check_result(
            "compatibility_mode_enforced",
            not production_like or (isinstance(publication_subject, dict) and publication_subject.get("compatibility") == expected_compatibility),
            {
                "expected": expected_compatibility,
                "actual": publication_subject.get("compatibility") if isinstance(publication_subject, dict) else None,
            },
        ),
        check_result(
            "published_schema_hash_matches_contract",
            not production_like or (isinstance(publication_subject, dict) and publication_subject.get("payload_schema_hash") == payload_hash),
            {
                "expected_payload_schema_hash": payload_hash,
                "published_payload_schema_hash": publication_subject.get("payload_schema_hash") if isinstance(publication_subject, dict) else None,
            },
        ),
        check_result(
            "producer_schema_id_enforced",
            not production_like or (isinstance(publication_subject, dict) and publication_subject.get("producer_enforced") is True),
            {"producer_enforced": publication_subject.get("producer_enforced") if isinstance(publication_subject, dict) else None},
        ),
        check_result(
            "broker_or_sink_validation_enabled",
            not production_like or (isinstance(publication_subject, dict) and publication_subject.get("broker_validation") is True),
            {"broker_validation": publication_subject.get("broker_validation") if isinstance(publication_subject, dict) else None},
        ),
        check_result(
            "production_registry_uri_declared",
            not production_like or production_registry_uri(registry_uri),
            {"registry_uri": registry_uri},
        ),
    ]
    issues = schema_registry_ops_issues(checks)
    return {
        "subject": expected_subject,
        "topic": compatibility_subject.get("topic"),
        "product": compatibility_subject.get("product"),
        "domain": compatibility_subject.get("domain"),
        "contract_path": compatibility_subject.get("contract_path"),
        "contract_hash": compatibility_subject.get("contract_hash"),
        "expected_compatibility": expected_compatibility,
        "payload_schema_hash": payload_hash,
        "sources": source_refs,
        "publication": {
            "registered": publication_subject.get("registered") if isinstance(publication_subject, dict) else None,
            "schema_id": publication_subject.get("schema_id") if isinstance(publication_subject, dict) else None,
            "artifact_id": publication_subject.get("artifact_id") if isinstance(publication_subject, dict) else None,
            "version": publication_subject.get("version") if isinstance(publication_subject, dict) else None,
            "compatibility": publication_subject.get("compatibility") if isinstance(publication_subject, dict) else None,
            "payload_schema_hash": publication_subject.get("payload_schema_hash") if isinstance(publication_subject, dict) else None,
            "producer_enforced": publication_subject.get("producer_enforced") if isinstance(publication_subject, dict) else None,
            "broker_validation": publication_subject.get("broker_validation") if isinstance(publication_subject, dict) else None,
            "registry_uri": publication_subject.get("registry_uri") if isinstance(publication_subject, dict) else None,
        },
        "checks": checks,
        "issues": issues,
        "passed": not issues,
    }


def schema_registry_ops_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "compatibility_passed": "compatibility_failed",
        "publication_evidence_available_for_production": "publication_evidence_missing",
        "subject_registered": "subject_not_registered",
        "subject_schema_id_present": "schema_id_missing",
        "compatibility_mode_enforced": "compatibility_mode_not_enforced",
        "published_schema_hash_matches_contract": "published_schema_hash_mismatch",
        "producer_schema_id_enforced": "producer_not_enforced",
        "broker_or_sink_validation_enabled": "broker_or_sink_validation_missing",
        "production_registry_uri_declared": "production_registry_uri_missing",
    }
    return [
        issue_map[check["check"]]
        for check in checks
        if check.get("passed") is not True and check.get("check") in issue_map
    ]


def compact_ops_subject(subject: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject": subject.get("subject"),
        "topic": subject.get("topic"),
        "product": subject.get("product"),
        "domain": subject.get("domain"),
        "issues": subject.get("issues", []),
        "sources": subject.get("sources", []),
        "publication": subject.get("publication", {}),
    }


def publication_subject_index(publication_evidence: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(publication_evidence, dict):
        return {}
    subjects = publication_evidence.get("subjects")
    if not isinstance(subjects, list):
        return {}
    return {
        str(subject.get("subject")): subject
        for subject in subjects
        if isinstance(subject, dict) and subject.get("subject")
    }


def source_subject_index(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = root / "platform" / "ingestion" / "source-registry.yaml"
    if not path.is_file():
        return {}
    registry = load_yaml(path)
    index: dict[str, list[dict[str, Any]]] = {}
    for source in registry.get("sources", []) if isinstance(registry.get("sources"), list) else []:
        if not isinstance(source, dict):
            continue
        canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
        subject = canonical.get("schemaSubject")
        if not isinstance(subject, str) or not subject:
            continue
        index.setdefault(subject, []).append(
            {
                "source_id": source.get("sourceId"),
                "priority": source.get("priority"),
                "status": source.get("status"),
                "product": source.get("product"),
                "domain": source.get("domain"),
                "bronze_target": canonical.get("bronzeTarget"),
                "canonical_topic": canonical.get("topic"),
            }
        )
    return index


def production_registry_uri(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = value.strip().lower()
    if candidate == "local-json-schema-registry-preflight":
        return False
    local_markers = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1")
    return candidate.startswith("https://") and not any(marker in candidate for marker in local_markers)


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON artifact must be an object: {path.as_posix()}")
    return data


def load_topic_contracts(root: Path, *, topic_name: str | None = None) -> list[tuple[Path, dict[str, Any]]]:
    contracts: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        contract = load_yaml(path)
        name = contract.get("topic", {}).get("name")
        if topic_name and name != topic_name:
            continue
        contracts.append((path, contract))
    if topic_name and not contracts:
        raise FileNotFoundError(f"topic contract does not exist: {topic_name}")
    return contracts


def filter_topic_contracts(
    contracts: list[tuple[Path, dict[str, Any]]],
    *,
    topic_name: str | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    if not topic_name:
        return contracts
    filtered = [
        (path, contract)
        for path, contract in contracts
        if contract.get("topic", {}).get("name") == topic_name
    ]
    if not filtered:
        raise FileNotFoundError(f"topic contract does not exist: {topic_name}")
    return filtered


def subject_report(
    root: Path,
    path: Path,
    contract: dict[str, Any],
    all_topic_contracts: list[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    topic = _mapping(contract, "topic")
    schema = _mapping(contract, "schema")
    topic_name = str(topic.get("name"))
    contract_version = contract.get("contractVersion")
    compatibility_mode = schema.get("compatibility")
    envelope_path = root / str(schema.get("envelopeSchema"))
    payload_path = root / str(schema.get("payloadSchema"))
    envelope_schema, envelope_errors = load_json_schema(envelope_path)
    payload_schema, payload_errors = load_json_schema(payload_path)
    prior_versions = prior_topic_versions(topic_name, all_topic_contracts)
    compatibility_checks = compatibility_check_results(
        root,
        topic_name=topic_name,
        compatibility_mode=compatibility_mode,
        payload_schema=payload_schema,
        prior_versions=prior_versions,
    )
    checks = [
        check_result("topic_contract_exists", True, {"path": path.as_posix()}),
        check_result(
            "compatibility_mode_supported",
            compatibility_mode in VALID_COMPATIBILITY_MODES,
            {"compatibility": compatibility_mode, "supported": sorted(VALID_COMPATIBILITY_MODES)},
        ),
        check_result(
            "envelope_schema_valid_json",
            not envelope_errors,
            {"path": envelope_path.as_posix(), "errors": envelope_errors},
        ),
        check_result(
            "payload_schema_valid_json",
            not payload_errors,
            {"path": payload_path.as_posix(), "errors": payload_errors},
        ),
        *compatibility_checks,
    ]
    return {
        "subject": f"{topic_name}-value",
        "topic": topic_name,
        "contract_path": path.as_posix(),
        "contract_hash": hash_file(path),
        "contract_version": contract_version,
        "product": topic.get("product"),
        "domain": topic.get("domain"),
        "compatibility": compatibility_mode,
        "envelope_schema": schema_entry(envelope_path, envelope_schema),
        "payload_schema": schema_entry(payload_path, payload_schema),
        "prior_versions_checked": [item["topic_name"] for item in prior_versions],
        "compatibility_passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def compatibility_check_results(
    root: Path,
    *,
    topic_name: str,
    compatibility_mode: object,
    payload_schema: dict[str, Any] | None,
    prior_versions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if compatibility_mode not in VALID_COMPATIBILITY_MODES:
        return [
            check_result(
                "backward_transitive_local",
                False,
                {"reason": "unsupported_compatibility_mode", "compatibility": compatibility_mode},
            )
        ]
    if payload_schema is None:
        return [
            check_result(
                "backward_transitive_local",
                False,
                {"reason": "payload_schema_invalid"},
            )
        ]
    if not prior_versions:
        return [
            check_result(
                "backward_transitive_local",
                True,
                {"reason": "no_prior_versions", "topic": topic_name},
            )
        ]

    checks: list[dict[str, Any]] = []
    for prior in prior_versions:
        prior_payload_path = root / prior["payload_schema_path"]
        prior_payload_schema, errors = load_json_schema(prior_payload_path)
        if errors or prior_payload_schema is None:
            checks.append(
                check_result(
                    "backward_transitive_local",
                    False,
                    {
                        "prior_topic": prior["topic_name"],
                        "reason": "prior_payload_schema_invalid",
                        "errors": errors,
                    },
                )
            )
            continue
        violations = backward_compatibility_violations(prior_payload_schema, payload_schema)
        checks.append(
            check_result(
                "backward_transitive_local",
                not violations,
                {
                    "prior_topic": prior["topic_name"],
                    "violations": violations,
                },
            )
        )
    return checks


def backward_compatibility_violations(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    return schema_backward_compatibility_violations(previous, current, path="$")


def schema_backward_compatibility_violations(previous: dict[str, Any], current: dict[str, Any], *, path: str) -> list[str]:
    previous_required = set(previous.get("required", [])) if isinstance(previous.get("required"), list) else set()
    current_required = set(current.get("required", [])) if isinstance(current.get("required"), list) else set()
    previous_properties = _mapping(previous, "properties")
    current_properties = _mapping(current, "properties")
    violations: list[str] = []

    removed_required = sorted(previous_required - current_required)
    if removed_required:
        violations.append(f"{path}: required fields removed or made optional: {removed_required}")

    added_required = sorted(current_required - previous_required)
    if added_required:
        violations.append(f"{path}: new required fields added: {added_required}")

    for field in sorted(previous_properties):
        if field not in current_properties:
            violations.append(f"{path}.{field}: field removed from properties")

    for field, previous_property in sorted(previous_properties.items()):
        if field not in current_properties:
            continue
        current_property = current_properties[field]
        if not isinstance(previous_property, dict) or not isinstance(current_property, dict):
            continue
        field_path = f"{path}.{field}"
        previous_type = normalize_json_type(previous_property.get("type"))
        current_type = normalize_json_type(current_property.get("type"))
        if previous_type and current_type and not previous_type.issubset(current_type):
            violations.append(f"{field_path}: type narrowed from {sorted(previous_type)} to {sorted(current_type)}")
        violations.extend(schema_constraint_violations(previous_property, current_property, path=field_path))
        if "object" in (previous_type or {"object"}) or previous_properties:
            violations.extend(schema_backward_compatibility_violations(previous_property, current_property, path=field_path))
        previous_items = previous_property.get("items")
        current_items = current_property.get("items")
        if isinstance(previous_items, dict) and isinstance(current_items, dict):
            violations.extend(schema_backward_compatibility_violations(previous_items, current_items, path=f"{field_path}[]"))
    return violations


def schema_constraint_violations(previous: dict[str, Any], current: dict[str, Any], *, path: str) -> list[str]:
    violations: list[str] = []
    previous_enum = previous.get("enum")
    current_enum = current.get("enum")
    if isinstance(previous_enum, list) and isinstance(current_enum, list):
        previous_values = {canonical_json(value) for value in previous_enum}
        current_values = {canonical_json(value) for value in current_enum}
        if not previous_values.issubset(current_values):
            violations.append(f"{path}: enum narrowed")
    if "const" in previous and "const" in current and previous.get("const") != current.get("const"):
        violations.append(f"{path}: const changed")
    for key in ("format", "pattern"):
        if key in previous and key in current and previous.get(key) != current.get(key):
            violations.append(f"{path}: {key} changed")
        if key not in previous and key in current:
            violations.append(f"{path}: {key} constraint added")
    if numeric_value(current.get("minimum")) is not None:
        previous_min = numeric_value(previous.get("minimum"))
        current_min = numeric_value(current.get("minimum"))
        if previous_min is None or current_min > previous_min:
            violations.append(f"{path}: minimum increased")
    if numeric_value(current.get("exclusiveMinimum")) is not None:
        previous_min = numeric_value(previous.get("exclusiveMinimum"))
        current_min = numeric_value(current.get("exclusiveMinimum"))
        if previous_min is None or current_min > previous_min:
            violations.append(f"{path}: exclusiveMinimum increased")
    if numeric_value(current.get("maximum")) is not None:
        previous_max = numeric_value(previous.get("maximum"))
        current_max = numeric_value(current.get("maximum"))
        if previous_max is None or current_max < previous_max:
            violations.append(f"{path}: maximum decreased")
    if numeric_value(current.get("exclusiveMaximum")) is not None:
        previous_max = numeric_value(previous.get("exclusiveMaximum"))
        current_max = numeric_value(current.get("exclusiveMaximum"))
        if previous_max is None or current_max < previous_max:
            violations.append(f"{path}: exclusiveMaximum decreased")
    if int_value(current.get("minLength")) is not None:
        previous_min = int_value(previous.get("minLength"))
        current_min = int_value(current.get("minLength"))
        if previous_min is None or current_min > previous_min:
            violations.append(f"{path}: minLength increased")
    if int_value(current.get("maxLength")) is not None:
        previous_max = int_value(previous.get("maxLength"))
        current_max = int_value(current.get("maxLength"))
        if previous_max is None or current_max < previous_max:
            violations.append(f"{path}: maxLength decreased")
    if previous.get("additionalProperties") is not False and current.get("additionalProperties") is False:
        violations.append(f"{path}: additionalProperties changed to false")
    return violations


def prior_topic_versions(topic_name: str, contracts: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    base, version = split_topic_version(topic_name)
    if version is None:
        return []
    prior: list[dict[str, Any]] = []
    for path, contract in contracts:
        other_name = contract.get("topic", {}).get("name")
        if not isinstance(other_name, str):
            continue
        other_base, other_version = split_topic_version(other_name)
        if other_base != base or other_version is None or other_version >= version:
            continue
        schema = _mapping(contract, "schema")
        payload_schema_path = schema.get("payloadSchema")
        if isinstance(payload_schema_path, str):
            prior.append(
                {
                    "topic_name": other_name,
                    "version": other_version,
                    "contract_path": path.as_posix(),
                    "payload_schema_path": payload_schema_path,
                }
            )
    return sorted(prior, key=lambda item: item["version"])


def split_topic_version(topic_name: str) -> tuple[str, int | None]:
    marker = ".v"
    if marker not in topic_name:
        return topic_name, None
    base, version_text = topic_name.rsplit(marker, 1)
    try:
        return base, int(version_text)
    except ValueError:
        return topic_name, None


def schema_entry(path: Path, schema: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "hash": hash_file(path) if path.is_file() else None,
        "id": schema.get("$id") if schema else None,
        "title": schema.get("title") if schema else None,
    }


def load_json_schema(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f"schema file does not exist: {path.as_posix()}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc.msg}"]
    if not isinstance(data, dict):
        return None, ["schema root must be a JSON object"]
    return data, []


def check_result(check: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "check": check,
        "passed": passed,
        "details": details,
    }


def normalize_json_type(value: object) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    return set()


def numeric_value(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def int_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def content_hash(payload: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(payload).encode('utf-8')).hexdigest()}"


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
