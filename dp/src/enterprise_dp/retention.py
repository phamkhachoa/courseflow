from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.contracts import (
    COLUMN_NAME,
    DATA_PRODUCT_NAME,
    TOPIC_NAME,
    VALID_CLASSIFICATIONS,
    VALID_LAYERS,
    ValidationResult,
    load_yaml,
    require_bool,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)


VALID_POLICY_STATUSES = {"draft", "active", "deprecated"}
VALID_POLICY_SEVERITIES = {"P0", "P1", "P2"}
REPORT_VERSION = 1


@dataclass(frozen=True)
class RetentionEvidenceResult:
    output_path: Path
    report: dict[str, Any]


def validate_retention_policy_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = retention_policy_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "contracts/policies/retention-policies.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    policies = registry.get("policies")
    if not isinstance(policies, list) or not policies:
        result.error(registry_path, "policies must be a non-empty list")
        return result

    seen_ids: set[str] = set()
    for index, policy in enumerate(policies):
        validate_retention_policy(registry_path, policy, index, seen_ids, result)
    return result


def validate_retention_policy(
    registry_path: Path,
    policy: object,
    index: int,
    seen_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"policies[{index}]"
    if not isinstance(policy, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    policy_id = require_string(registry_path, result, policy, "id", prefix)
    if policy_id:
        if not COLUMN_NAME.fullmatch(policy_id):
            result.error(registry_path, f"{prefix}.id must be snake_case")
        if policy_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates policy {policy_id}")
        seen_ids.add(policy_id)
    for key in ("name", "owner", "description", "effectiveFrom"):
        require_string(registry_path, result, policy, key, prefix)
    require_int(registry_path, result, policy, "policyVersion", minimum=1, prefix=prefix)
    status = require_string(registry_path, result, policy, "status", prefix)
    if status and status not in VALID_POLICY_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_POLICY_STATUSES)}")
    severity = require_string(registry_path, result, policy, "severity", prefix)
    if severity and severity not in VALID_POLICY_SEVERITIES:
        result.error(registry_path, f"{prefix}.severity must be one of {sorted(VALID_POLICY_SEVERITIES)}")
    require_int(registry_path, result, policy, "maxRetentionDays", minimum=1, prefix=prefix)
    require_int(registry_path, result, policy, "minRetentionDays", minimum=1, prefix=prefix)
    require_bool(registry_path, result, policy, "erasureRequired", prefix)

    applies_to = require_mapping(registry_path, result, policy, "appliesTo")
    if applies_to:
        for layer in require_string_list(registry_path, result, applies_to, "layers", f"{prefix}.appliesTo") or []:
            if layer not in VALID_LAYERS:
                result.error(registry_path, f"{prefix}.appliesTo.layers contains unsupported layer {layer!r}")
        for classification in require_string_list(registry_path, result, applies_to, "classifications", f"{prefix}.appliesTo") or []:
            if classification not in VALID_CLASSIFICATIONS:
                result.error(registry_path, f"{prefix}.appliesTo.classifications contains unsupported classification {classification!r}")
        require_string_list(registry_path, result, applies_to, "domains", f"{prefix}.appliesTo")
        require_string_list(registry_path, result, applies_to, "products", f"{prefix}.appliesTo")

    evidence = require_string_list(registry_path, result, policy, "evidenceRequirements", prefix)
    for evidence_id in evidence or []:
        if not COLUMN_NAME.fullmatch(evidence_id):
            result.error(registry_path, f"{prefix}.evidenceRequirements contains non-snake-case item {evidence_id!r}")

    controls = require_mapping(registry_path, result, policy, "controls")
    if controls:
        for key in (
            "requirePartitionPruning",
            "requireDeleteVectorOrRewrite",
            "requireAuditLog",
            "requireLegalHoldCheck",
        ):
            require_bool(registry_path, result, controls, key, f"{prefix}.controls")


def evaluate_retention_contract(
    root: Path,
    *,
    artifact_name: str,
    artifact_type: str,
    layer: str | None,
    domain: str | None,
    product: str | None,
    privacy: dict[str, Any],
) -> dict[str, Any]:
    policy = select_retention_policy(
        root,
        layer=layer,
        domain=domain,
        product=product,
        classification=privacy.get("classification"),
        retention_days=privacy.get("retentionDays"),
    )
    registry = load_retention_policy_registry(root)
    registry_hash = hash_retention_policy_registry(root)
    retention_days = privacy.get("retentionDays")
    min_days = policy.get("minRetentionDays")
    max_days = policy.get("maxRetentionDays")
    erasure_required = policy.get("erasureRequired")
    checks = [
        check("retention_policy_registered", True, {}),
        check("retention_policy_active", policy.get("status") == "active", {"status": policy.get("status")}),
        check(
            "subject_keys_declared_for_pii",
            privacy.get("containsPii") is not True or bool(privacy.get("subjectKeys")),
            {"subject_keys": privacy.get("subjectKeys", [])},
        ),
        check(
            "erasure_mode_declared",
            isinstance(privacy.get("erasureMode"), str) and bool(str(privacy.get("erasureMode")).strip()),
            {"erasure_mode": privacy.get("erasureMode")},
        ),
        check(
            "legal_hold_policy_declared",
            isinstance(privacy.get("legalHoldPolicy"), str) and bool(str(privacy.get("legalHoldPolicy")).strip()),
            {"legal_hold_policy": privacy.get("legalHoldPolicy")},
        ),
        check(
            "raw_payload_policy_declared",
            isinstance(privacy.get("rawPayloadPolicy"), str) and bool(str(privacy.get("rawPayloadPolicy")).strip()),
            {"raw_payload_policy": privacy.get("rawPayloadPolicy")},
        ),
        check(
            "retention_days_within_policy",
            isinstance(retention_days, int)
            and isinstance(min_days, int)
            and isinstance(max_days, int)
            and min_days <= retention_days <= max_days,
            {"retention_days": retention_days, "min_retention_days": min_days, "max_retention_days": max_days},
        ),
        check(
            "erasure_support_matches_policy",
            erasure_required is not True or privacy.get("erasureSupported") is True,
            {"erasure_required": erasure_required, "erasure_supported": privacy.get("erasureSupported")},
        ),
        check(
            "erasure_mode_matches_policy",
            erasure_required is not True or privacy.get("erasureMode") in {"SUBJECT_DELETE", "REGULATED_SUBJECT_DELETE"},
            {"erasure_required": erasure_required, "erasure_mode": privacy.get("erasureMode")},
        ),
        check(
            "regulated_erasure_uses_regulated_legal_hold",
            privacy.get("erasureMode") != "REGULATED_SUBJECT_DELETE" or privacy.get("legalHoldPolicy") == "regulated_legal_hold_check",
            {"erasure_mode": privacy.get("erasureMode"), "legal_hold_policy": privacy.get("legalHoldPolicy")},
        ),
        check(
            "residency_declared",
            isinstance(privacy.get("dataResidency"), str) and bool(str(privacy.get("dataResidency")).strip()),
            {"data_residency": privacy.get("dataResidency")},
        ),
    ]
    return {
        "policy_id": policy.get("id"),
        "policy_name": policy.get("name"),
        "policy_version": policy.get("policyVersion"),
        "status": policy.get("status"),
        "severity": policy.get("severity"),
        "owner": policy.get("owner"),
        "effective_from": policy.get("effectiveFrom"),
        "registry_scope": registry.get("registry_scope"),
        "registry_hash": registry_hash,
        "artifact_name": artifact_name,
        "artifact_type": artifact_type,
        "required_evidence": policy.get("evidenceRequirements", []),
        "resolved_controls": policy.get("controls", {}),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def write_retention_evidence_report(
    root: str | Path,
    output_path: str | Path,
    *,
    data_product_name: str,
    environment: str = "local",
    release_id: str | None = None,
    dataset_snapshot_id: str | None = None,
    table_version: str | None = None,
    content_hash: str | None = None,
    row_count: int | None = None,
    generated_at: str | None = None,
    evidence_input_path: str | Path | None = None,
) -> RetentionEvidenceResult:
    report = build_retention_evidence_report(
        root,
        data_product_name=data_product_name,
        environment=environment,
        release_id=release_id,
        dataset_snapshot_id=dataset_snapshot_id,
        table_version=table_version,
        content_hash=content_hash,
        row_count=row_count,
        generated_at=generated_at,
        evidence_input_path=evidence_input_path,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return RetentionEvidenceResult(output_path=target, report=report)


def build_retention_evidence_report(
    root: str | Path,
    *,
    data_product_name: str,
    environment: str = "local",
    release_id: str | None = None,
    dataset_snapshot_id: str | None = None,
    table_version: str | None = None,
    content_hash: str | None = None,
    row_count: int | None = None,
    generated_at: str | None = None,
    evidence_input_path: str | Path | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    contract_path = find_data_product_contract(platform_root, data_product_name)
    contract = load_yaml(contract_path)
    data_product = _mapping(contract, "dataProduct")
    privacy = _mapping(contract, "privacy")
    evaluation = evaluate_retention_contract(
        platform_root,
        artifact_name=data_product_name,
        artifact_type="data_product",
        layer=str(data_product.get("layer")),
        domain=str(data_product.get("domain")),
        product=str(data_product.get("product")),
        privacy=privacy,
    )
    evidence_source, evidence_items, input_checks = resolve_retention_evidence_input(
        evaluation,
        data_product_name=data_product_name,
        environment=environment,
        release_id=release_id,
        dataset_snapshot_id=dataset_snapshot_id,
        table_version=table_version,
        content_hash=content_hash,
        generated_at=generated,
        evidence_input_path=evidence_input_path,
    )
    evidence_checks = input_checks + retention_evidence_checks(evaluation, evidence_items, privacy)
    checks = list(evaluation.get("checks", [])) + evidence_checks
    evidence_id = stable_id(
        "retention-erasure",
        release_id,
        data_product_name,
        dataset_snapshot_id,
        table_version,
        content_hash,
    )
    return {
        "artifact_type": "retention_erasure_evidence.v1",
        "report_version": REPORT_VERSION,
        "evidence_id": evidence_id,
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "data_product": data_product_name,
        "contract_path": contract_path.as_posix(),
        "contract_hash": hash_file(contract_path),
        "contract_version": contract.get("contractVersion"),
        "dataset_snapshot_id": dataset_snapshot_id,
        "table_version": table_version,
        "content_hash": content_hash,
        "row_count": row_count,
        "privacy": {
            "classification": privacy.get("classification"),
            "contains_pii": privacy.get("containsPii"),
            "tenant_isolation": privacy.get("tenantIsolation"),
            "data_residency": privacy.get("dataResidency"),
            "retention_days": privacy.get("retentionDays"),
            "erasure_supported": privacy.get("erasureSupported"),
            "subject_keys": privacy.get("subjectKeys", []),
            "erasure_mode": privacy.get("erasureMode"),
            "legal_hold_policy": privacy.get("legalHoldPolicy"),
            "raw_payload_policy": privacy.get("rawPayloadPolicy"),
        },
        "policy": {
            "policy_id": evaluation.get("policy_id"),
            "policy_name": evaluation.get("policy_name"),
            "policy_version": evaluation.get("policy_version"),
            "status": evaluation.get("status"),
            "severity": evaluation.get("severity"),
            "owner": evaluation.get("owner"),
            "effective_from": evaluation.get("effective_from"),
            "registry_scope": evaluation.get("registry_scope"),
            "registry_hash": evaluation.get("registry_hash"),
            "required_evidence": evaluation.get("required_evidence", []),
            "resolved_controls": evaluation.get("resolved_controls", {}),
        },
        "evidence_source": evidence_source,
        "evidence": evidence_items,
        "checks": checks,
        "failures": [
            {
                "check": item["name"],
                "details": item.get("details", {}),
            }
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": all(item.get("passed") is True for item in checks),
    }


def resolve_retention_evidence_input(
    evaluation: dict[str, Any],
    *,
    data_product_name: str,
    environment: str,
    release_id: str | None,
    dataset_snapshot_id: str | None,
    table_version: str | None,
    content_hash: str | None,
    generated_at: str,
    evidence_input_path: str | Path | None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    production_like = environment not in {"local", "dev"}
    if evidence_input_path is None:
        evidence_items = synthetic_evidence_items(
            evaluation.get("required_evidence", []),
            data_product_name=data_product_name,
            release_id=release_id,
            generated_at=generated_at,
        )
        return (
            {
                "type": "synthetic_local",
                "verified": not production_like,
                "producer": "enterprise_dp.retention.synthetic",
            },
            evidence_items,
            [
                check(
                    "production_retention_evidence_input_required",
                    not production_like,
                    {"environment": environment, "evidence_input_path": None},
                )
            ],
        )

    path = Path(evidence_input_path)
    if not path.is_file():
        return (
            {
                "type": "external_input",
                "verified": False,
                "path": path.as_posix(),
            },
            {},
            [check("retention_evidence_input_file_exists", False, {"path": path.as_posix()})],
        )
    try:
        evidence_document = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return (
            {
                "type": "external_input",
                "verified": False,
                "path": path.as_posix(),
                "hash": hash_file(path),
            },
            {},
            [
                check(
                    "retention_evidence_input_json_parseable",
                    False,
                    {"path": path.as_posix(), "error": str(exc)},
                )
            ],
        )
    evidence_items = normalize_evidence_items(evidence_document)
    source = {
        "type": "external_input",
        "verified": True,
        "path": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": evidence_document.get("artifact_type"),
        "producer": evidence_document.get("producer"),
        "generated_at": evidence_document.get("generated_at"),
    }
    checks = validate_retention_evidence_input_document(
        evidence_document,
        evidence_items,
        data_product_name=data_product_name,
        release_id=release_id,
        dataset_snapshot_id=dataset_snapshot_id,
        table_version=table_version,
        content_hash=content_hash,
    )
    if production_like:
        checks = production_metadata_binding_checks(
            release_id=release_id,
            dataset_snapshot_id=dataset_snapshot_id,
            table_version=table_version,
            content_hash=content_hash,
        ) + checks
    return source, evidence_items, checks


def production_metadata_binding_checks(
    *,
    release_id: str | None,
    dataset_snapshot_id: str | None,
    table_version: str | None,
    content_hash: str | None,
) -> list[dict[str, Any]]:
    required = {
        "release_id": release_id,
        "dataset_snapshot_id": dataset_snapshot_id,
        "table_version": table_version,
        "content_hash": content_hash,
    }
    return [
        check(
            f"production_retention_{key}_required",
            isinstance(value, str) and bool(value.strip()),
            {"value": value},
        )
        for key, value in required.items()
    ]


def validate_retention_evidence_input_document(
    document: dict[str, Any],
    evidence_items: dict[str, Any],
    *,
    data_product_name: str,
    release_id: str | None,
    dataset_snapshot_id: str | None,
    table_version: str | None,
    content_hash: str | None,
) -> list[dict[str, Any]]:
    return [
        check(
            "retention_evidence_input_artifact_type",
            document.get("artifact_type") == "retention_erasure_job_evidence.v1",
            {"artifact_type": document.get("artifact_type")},
        ),
        check(
            "retention_evidence_input_data_product_matches",
            document.get("data_product") == data_product_name,
            {"expected": data_product_name, "actual": document.get("data_product")},
        ),
        check(
            "retention_evidence_input_release_matches",
            release_id is None or document.get("release_id") == release_id,
            {"expected": release_id, "actual": document.get("release_id")},
        ),
        check(
            "retention_evidence_input_snapshot_matches",
            dataset_snapshot_id is None or document.get("dataset_snapshot_id") == dataset_snapshot_id,
            {"expected": dataset_snapshot_id, "actual": document.get("dataset_snapshot_id")},
        ),
        check(
            "retention_evidence_input_table_version_matches",
            table_version is None or document.get("table_version") == table_version,
            {"expected": table_version, "actual": document.get("table_version")},
        ),
        check(
            "retention_evidence_input_content_hash_matches",
            content_hash is None or document.get("content_hash") == content_hash,
            {"expected": content_hash, "actual": document.get("content_hash")},
        ),
        check(
            "retention_evidence_input_producer_declared",
            isinstance(document.get("producer"), str) and bool(str(document.get("producer")).strip()),
            {"producer": document.get("producer")},
        ),
        check(
            "retention_evidence_input_generated_at_declared",
            isinstance(document.get("generated_at"), str) and bool(str(document.get("generated_at")).strip()),
            {"generated_at": document.get("generated_at")},
        ),
        check(
            "retention_evidence_input_generated_at_valid",
            is_iso_timestamp(document.get("generated_at")),
            {"generated_at": document.get("generated_at")},
        ),
        check(
            "retention_evidence_input_items_declared",
            bool(evidence_items),
            {"evidence_keys": sorted(evidence_items.keys())},
        ),
    ]


def normalize_evidence_items(document: dict[str, Any]) -> dict[str, Any]:
    evidence = document.get("evidence")
    if isinstance(evidence, dict):
        return {
            key: value
            for key, value in evidence.items()
            if isinstance(key, str) and isinstance(value, dict)
        }
    items = document.get("evidence_items")
    if isinstance(items, list):
        normalized: dict[str, Any] = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("type"), str):
                continue
            normalized[str(item["type"])] = {
                key: value
                for key, value in item.items()
                if key != "type"
            }
        return normalized
    return {}


def select_retention_policy(
    root: Path,
    *,
    layer: str | None,
    domain: str | None,
    product: str | None,
    classification: object,
    retention_days: object,
) -> dict[str, Any]:
    policies = [
        policy
        for policy in list_retention_policies(root)
        if policy.get("status") == "active"
        and retention_policy_applies(policy, layer=layer, domain=domain, product=product, classification=classification)
    ]
    if not policies:
        raise KeyError(f"no active retention policy applies to layer={layer!r}, domain={domain!r}, product={product!r}, classification={classification!r}")
    if isinstance(retention_days, int):
        covering = [
            policy
            for policy in policies
            if isinstance(policy.get("minRetentionDays"), int)
            and isinstance(policy.get("maxRetentionDays"), int)
            and policy["minRetentionDays"] <= retention_days <= policy["maxRetentionDays"]
        ]
        if covering:
            return sorted(covering, key=lambda policy: int(policy.get("maxRetentionDays", 999999)))[0]
    return sorted(policies, key=lambda policy: int(policy.get("maxRetentionDays", 999999)))[0]


def retention_policy_applies(
    policy: dict[str, Any],
    *,
    layer: str | None,
    domain: str | None,
    product: str | None,
    classification: object,
) -> bool:
    applies_to = _mapping(policy, "appliesTo")
    return (
        layer in applies_to.get("layers", [])
        and classification in applies_to.get("classifications", [])
        and domain in applies_to.get("domains", [])
        and product in applies_to.get("products", [])
    )


def synthetic_evidence_items(
    required_evidence: object,
    *,
    data_product_name: str,
    release_id: str | None,
    generated_at: str,
) -> dict[str, Any]:
    evidence_ids = [item for item in required_evidence if isinstance(item, str)] if isinstance(required_evidence, list) else []
    evidence: dict[str, Any] = {}
    for evidence_id in evidence_ids:
        evidence[evidence_id] = {
            "id": stable_id("retention-evidence", release_id, data_product_name, evidence_id),
            "status": "passed",
            "observed_at": generated_at,
        }
    if "expired_record_scan" in evidence:
        evidence["expired_record_scan"]["expired_record_count"] = 0
    if "retention_job_run_id" in evidence:
        evidence["retention_job_run_id"]["job_run_id"] = evidence["retention_job_run_id"]["id"]
    if "subject_key_coverage" in evidence:
        evidence["subject_key_coverage"]["coverage_percent"] = 100.0
    if "erasure_request_replay" in evidence:
        evidence["erasure_request_replay"]["sample_request_count"] = 1
        evidence["erasure_request_replay"]["replay_passed"] = True
    if "residual_subject_scan" in evidence:
        evidence["residual_subject_scan"]["residual_match_count"] = 0
    if "legal_hold_check" in evidence:
        evidence["legal_hold_check"]["active_legal_hold_count"] = 0
    return evidence


def retention_evidence_checks(
    evaluation: dict[str, Any],
    evidence_items: dict[str, Any],
    privacy: dict[str, Any],
) -> list[dict[str, Any]]:
    required = [item for item in evaluation.get("required_evidence", []) if isinstance(item, str)]
    missing = [item for item in required if item not in evidence_items]
    failed = [
        item
        for item, payload in evidence_items.items()
        if not isinstance(payload, dict) or payload.get("status") != "passed"
    ]
    retention_job_run = evidence_items.get("retention_job_run_id")
    erasure_replay = evidence_items.get("erasure_request_replay")
    legal_hold = evidence_items.get("legal_hold_check")
    expired_scan = evidence_items.get("expired_record_scan")
    subject_coverage = evidence_items.get("subject_key_coverage")
    residual_scan = evidence_items.get("residual_subject_scan")
    return [
        check("retention_required_evidence_present", not missing, {"missing_evidence": missing}),
        check("retention_required_evidence_passed", not failed, {"failed_evidence": failed}),
        check(
            "retention_job_run_id_declared",
            not isinstance(retention_job_run, dict)
            or (isinstance(retention_job_run.get("job_run_id"), str) and bool(str(retention_job_run.get("job_run_id")).strip())),
            {"job_run_id": retention_job_run.get("job_run_id") if isinstance(retention_job_run, dict) else None},
        ),
        check(
            "retention_expired_record_scan_clean",
            not isinstance(expired_scan, dict) or expired_scan.get("expired_record_count") == 0,
            {"expired_record_count": expired_scan.get("expired_record_count") if isinstance(expired_scan, dict) else None},
        ),
        check(
            "subject_key_coverage_complete",
            privacy.get("containsPii") is not True or (isinstance(subject_coverage, dict) and subject_coverage.get("coverage_percent") == 100.0),
            {"coverage_percent": subject_coverage.get("coverage_percent") if isinstance(subject_coverage, dict) else None},
        ),
        check(
            "erasure_replay_passed_when_required",
            privacy.get("erasureSupported") is not True or (isinstance(erasure_replay, dict) and erasure_replay.get("replay_passed") is True),
            {"erasure_supported": privacy.get("erasureSupported")},
        ),
        check(
            "residual_subject_scan_clean",
            privacy.get("erasureSupported") is not True or (isinstance(residual_scan, dict) and residual_scan.get("residual_match_count") == 0),
            {"residual_match_count": residual_scan.get("residual_match_count") if isinstance(residual_scan, dict) else None},
        ),
        check(
            "legal_hold_check_clear",
            isinstance(legal_hold, dict) and legal_hold.get("active_legal_hold_count") == 0,
            {"active_legal_hold_count": legal_hold.get("active_legal_hold_count") if isinstance(legal_hold, dict) else None},
        ),
    ]


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
    }


def retention_policy_registry_path(root: Path) -> Path:
    return root / "contracts" / "policies" / "retention-policies.yaml"


def load_retention_policy_registry(root: Path) -> dict[str, Any]:
    path = retention_policy_registry_path(root)
    if not path.is_file():
        return {}
    return load_yaml(path)


def list_retention_policies(root: Path) -> list[dict[str, Any]]:
    registry = load_retention_policy_registry(root)
    policies = registry.get("policies")
    return [policy for policy in policies if isinstance(policy, dict)] if isinstance(policies, list) else []


def hash_retention_policy_registry(root: Path) -> str | None:
    path = retention_policy_registry_path(root)
    if not path.is_file():
        return None
    return hash_file(path)


def find_data_product_contract(root: Path, data_product_name: str) -> Path:
    candidates = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    if not candidates:
        raise FileNotFoundError(f"data product contract does not exist: {data_product_name}")
    return candidates[-1]


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON object expected")
    return data


def is_iso_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}
