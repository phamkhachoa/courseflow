from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from enterprise_dp.contracts import PRODUCT_CODE, ValidationResult, load_yaml, require_int, require_string, require_string_list
from enterprise_dp.usecases import list_use_cases, load_domain_codes


CAPABILITY_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
VALID_PHASES = {"P0", "P1", "P2", "P3"}
VALID_LEVELS = {"L0", "L1", "L2", "L3", "L4"}
LEVEL_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
VALID_STATUSES = {"documented", "validated_as_code", "integrated_runtime", "production_enforced", "optimized", "planned"}
VALID_CATEGORIES = {
    "access_privacy",
    "catalog_lineage",
    "cost_finops",
    "governance",
    "ingestion",
    "lakehouse",
    "ml_ai",
    "observability",
    "orchestration",
    "quality",
    "semantic_serving",
}
REPORT_VERSION = 1


@dataclass(frozen=True)
class CapabilityMaturityReportResult:
    output_path: Path
    report: dict[str, Any]


def validate_capability_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = capability_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "platform/capabilities/registry.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    target_maturity = registry.get("target_maturity")
    if not isinstance(target_maturity, dict):
        result.error(registry_path, "target_maturity must be an object")
    else:
        for phase in ("P0", "P1", "P2"):
            level = require_string(registry_path, result, target_maturity, phase, "target_maturity")
            if level and level not in VALID_LEVELS:
                result.error(registry_path, f"target_maturity.{phase} must be one of {sorted(VALID_LEVELS)}")

    references = registry.get("reference_models")
    if not isinstance(references, list) or not references:
        result.error(registry_path, "reference_models must be a non-empty list")
        reference_ids: set[str] = set()
    else:
        reference_ids = validate_references(registry_path, references, result)

    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        result.error(registry_path, "capabilities must be a non-empty list")
        return result

    domain_codes = load_domain_codes(root)
    use_case_ids = {
        str(use_case.get("id"))
        for use_case in list_use_cases(root)
        if isinstance(use_case.get("id"), str)
    }
    seen_ids: set[str] = set()
    for index, capability in enumerate(capabilities):
        validate_capability(
            root,
            registry_path,
            capability,
            index,
            seen_ids,
            reference_ids,
            domain_codes,
            use_case_ids,
            result,
        )
    return result


def validate_references(path: Path, references: list[object], result: ValidationResult) -> set[str]:
    seen: set[str] = set()
    for index, reference in enumerate(references):
        prefix = f"reference_models[{index}]"
        if not isinstance(reference, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        reference_id = require_string(path, result, reference, "id", prefix)
        if reference_id:
            if not CAPABILITY_ID.fullmatch(reference_id):
                result.error(path, f"{prefix}.id must be kebab-case")
            if reference_id in seen:
                result.error(path, f"{prefix}.id duplicates reference {reference_id!r}")
            seen.add(reference_id)
        for key in ("name", "url", "adoptedPattern"):
            require_string(path, result, reference, key, prefix)
    return seen


def validate_capability(
    root: Path,
    registry_path: Path,
    capability: object,
    index: int,
    seen_ids: set[str],
    reference_ids: set[str],
    domain_codes: set[str],
    use_case_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"capabilities[{index}]"
    if not isinstance(capability, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    capability_id = require_string(registry_path, result, capability, "id", prefix)
    if capability_id:
        if not CAPABILITY_ID.fullmatch(capability_id):
            result.error(registry_path, f"{prefix}.id must be kebab-case")
        if capability_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates capability {capability_id!r}")
        seen_ids.add(capability_id)

    for key in ("name", "owner", "description", "enterpriseOutcome"):
        require_string(registry_path, result, capability, key, prefix)
    owner = capability.get("owner")
    if isinstance(owner, str) and not PRODUCT_CODE.fullmatch(owner):
        result.error(registry_path, f"{prefix}.owner must be a team code like data-platform")

    category = require_string(registry_path, result, capability, "category", prefix)
    if category and category not in VALID_CATEGORIES:
        result.error(registry_path, f"{prefix}.category must be one of {sorted(VALID_CATEGORIES)}")
    phase = require_string(registry_path, result, capability, "phase", prefix)
    if phase and phase not in VALID_PHASES:
        result.error(registry_path, f"{prefix}.phase must be one of {sorted(VALID_PHASES)}")
    status = require_string(registry_path, result, capability, "status", prefix)
    if status and status not in VALID_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_STATUSES)}")

    current_level = require_string(registry_path, result, capability, "currentLevel", prefix)
    target_level = require_string(registry_path, result, capability, "targetLevel", prefix)
    if current_level and current_level not in VALID_LEVELS:
        result.error(registry_path, f"{prefix}.currentLevel must be one of {sorted(VALID_LEVELS)}")
    if target_level and target_level not in VALID_LEVELS:
        result.error(registry_path, f"{prefix}.targetLevel must be one of {sorted(VALID_LEVELS)}")
    if current_level in VALID_LEVELS and target_level in VALID_LEVELS:
        if LEVEL_RANK[current_level] > LEVEL_RANK[target_level]:
            result.error(registry_path, f"{prefix}.currentLevel cannot exceed targetLevel")

    for key in ("platformScope", "productionGates", "requiredEvidence", "gaps", "nextMilestones"):
        require_string_list(registry_path, result, capability, key, prefix)

    validate_boolean(registry_path, result, capability, "productAgnostic", prefix)
    validate_reference_bindings(registry_path, result, capability, "referenceModels", prefix, reference_ids, "reference model")
    validate_reference_bindings(registry_path, result, capability, "domainBindings", prefix, domain_codes, "domain")
    validate_reference_bindings(registry_path, result, capability, "useCaseBindings", prefix, use_case_ids, "use case")
    validate_evidence_artifacts(root, registry_path, capability.get("evidenceArtifacts"), prefix, result)


def validate_boolean(path: Path, result: ValidationResult, mapping: dict[str, Any], key: str, prefix: str) -> None:
    if not isinstance(mapping.get(key), bool):
        result.error(path, f"{prefix}.{key} must be a boolean")


def validate_reference_bindings(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str,
    known_values: set[str],
    label: str,
) -> None:
    values = require_string_list(path, result, mapping, key, prefix)
    for value in values or []:
        if known_values and value not in known_values:
            result.error(path, f"{prefix}.{key} references unknown {label} {value!r}")


def validate_evidence_artifacts(
    root: Path,
    registry_path: Path,
    artifacts: object,
    prefix: str,
    result: ValidationResult,
) -> None:
    if not isinstance(artifacts, list) or not artifacts:
        result.error(registry_path, f"{prefix}.evidenceArtifacts must be a non-empty list")
        return
    for index, artifact in enumerate(artifacts):
        item_prefix = f"{prefix}.evidenceArtifacts[{index}]"
        if not isinstance(artifact, dict):
            result.error(registry_path, f"{item_prefix} must be an object")
            continue
        for key in ("path", "type", "purpose"):
            require_string(registry_path, result, artifact, key, item_prefix)
        required = artifact.get("requiredForCurrentLevel")
        if not isinstance(required, bool):
            result.error(registry_path, f"{item_prefix}.requiredForCurrentLevel must be a boolean")
        artifact_path = artifact.get("path")
        if required is True and isinstance(artifact_path, str) and not (root / artifact_path).exists():
            result.error(registry_path, f"{item_prefix}.path does not exist: {artifact_path}")


def write_capability_maturity_report(
    root: str | Path,
    output_path: str | Path,
    *,
    phase: str | None = None,
    generated_at: str | None = None,
) -> CapabilityMaturityReportResult:
    report = build_capability_maturity_report(root, phase=phase, generated_at=generated_at)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return CapabilityMaturityReportResult(output_path=target, report=report)


def build_capability_maturity_report(
    root: str | Path,
    *,
    phase: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    registry_path = capability_registry_path(platform_root)
    registry = load_yaml(registry_path)
    generated = generated_at or utc_now()
    capabilities = [
        capability
        for capability in registry.get("capabilities", [])
        if isinstance(capability, dict) and (phase is None or capability.get("phase") == phase)
    ]
    capability_reports = [capability_report_entry(platform_root, capability) for capability in capabilities]
    blockers = [
        {
            "capability_id": item["id"],
            "phase": item["phase"],
            "current_level": item["current_level"],
            "target_level": item["target_level"],
            "missing_level_count": item["missing_level_count"],
            "gaps": item["gaps"],
            "next_milestones": item["next_milestones"],
        }
        for item in capability_reports
        if item["meets_target"] is not True
    ]
    p0_reports = [item for item in capability_reports if item["phase"] == "P0"]
    p0_ready = bool(p0_reports) and all(item["meets_target"] for item in p0_reports)
    return {
        "artifact_type": "capability_maturity_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id("capability-maturity", registry_path, phase, generated),
        "generated_at": generated,
        "registry_uri": registry_path.as_posix(),
        "registry_hash": hash_file(registry_path),
        "registry_scope": registry.get("registry_scope"),
        "phase_filter": phase,
        "target_maturity": registry.get("target_maturity", {}),
        "summary": summary(capability_reports),
        "readiness_state": "production_ready" if p0_ready and not blockers else "not_ready",
        "p0_ready": p0_ready,
        "blockers": blockers,
        "capabilities": capability_reports,
        "passed": not blockers,
    }


def capability_report_entry(root: Path, capability: dict[str, Any]) -> dict[str, Any]:
    current_level = str(capability.get("currentLevel"))
    target_level = str(capability.get("targetLevel"))
    current_rank = LEVEL_RANK.get(current_level, -1)
    target_rank = LEVEL_RANK.get(target_level, 99)
    evidence = [
        evidence_report_entry(root, artifact)
        for artifact in capability.get("evidenceArtifacts", [])
        if isinstance(artifact, dict)
    ]
    return {
        "id": capability.get("id"),
        "name": capability.get("name"),
        "category": capability.get("category"),
        "phase": capability.get("phase"),
        "owner": capability.get("owner"),
        "status": capability.get("status"),
        "current_level": current_level,
        "target_level": target_level,
        "meets_target": current_rank >= target_rank,
        "missing_level_count": max(target_rank - current_rank, 0),
        "product_agnostic": capability.get("productAgnostic"),
        "production_gates": capability.get("productionGates", []),
        "required_evidence": capability.get("requiredEvidence", []),
        "evidence_artifacts": evidence,
        "gaps": capability.get("gaps", []),
        "next_milestones": capability.get("nextMilestones", []),
        "reference_models": capability.get("referenceModels", []),
        "domain_bindings": capability.get("domainBindings", []),
        "use_case_bindings": capability.get("useCaseBindings", []),
    }


def evidence_report_entry(root: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    path_value = str(artifact.get("path"))
    artifact_path = root / path_value
    exists = artifact_path.exists()
    return {
        "path": path_value,
        "type": artifact.get("type"),
        "purpose": artifact.get("purpose"),
        "required_for_current_level": artifact.get("requiredForCurrentLevel"),
        "exists": exists,
        "hash": hash_file(artifact_path) if exists and artifact_path.is_file() else None,
    }


def summary(capabilities: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "capability_count": len(capabilities),
        "by_phase": count_by(capabilities, "phase"),
        "by_category": count_by(capabilities, "category"),
        "by_current_level": count_by(capabilities, "current_level"),
        "target_met_count": sum(1 for item in capabilities if item.get("meets_target") is True),
        "target_gap_count": sum(1 for item in capabilities if item.get("meets_target") is not True),
    }


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def capability_registry_path(root: Path) -> Path:
    return root / "platform" / "capabilities" / "registry.yaml"


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
