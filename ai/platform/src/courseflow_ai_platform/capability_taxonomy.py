from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.coverage_taxonomy import ALLOWED_RUNTIME_STATUSES
from courseflow_ai_platform.registry import (
    RegistryValidationError,
    collect_model_family_ids,
    load_yaml,
    require_list,
    require_str,
)

REQUIRED_CAPABILITY_AREAS = (
    "classical_ml",
    "deep_learning",
    "nlp_transformers",
    "genai_llm",
    "rag",
    "computer_vision",
    "speech",
    "reinforcement_learning",
    "responsible_ai",
    "mlops",
    "feature_store",
    "evaluation",
    "serving",
)

PLATFORM_CAPABILITY_AREAS = frozenset(
    {
        "responsible_ai",
        "mlops",
        "feature_store",
        "evaluation",
        "serving",
    }
)


@dataclass(frozen=True, slots=True)
class AiCapabilityTaxonomyArea:
    area_id: str
    name: str
    area_type: str
    required: bool
    readiness_status: str
    runtime_status: str
    priority: str
    coverage_module_count: int
    capability_count: int
    model_family_count: int
    use_case_count: int
    evidence_artifact_count: int
    evaluation_gate_count: int
    gap_count: int
    next_action_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "areaId": self.area_id,
            "areaType": self.area_type,
            "capabilityCount": self.capability_count,
            "coverageModuleCount": self.coverage_module_count,
            "evaluationGateCount": self.evaluation_gate_count,
            "evidenceArtifactCount": self.evidence_artifact_count,
            "gapCount": self.gap_count,
            "modelFamilyCount": self.model_family_count,
            "name": self.name,
            "nextActionCount": self.next_action_count,
            "priority": self.priority,
            "readinessStatus": self.readiness_status,
            "required": self.required,
            "runtimeStatus": self.runtime_status,
            "useCaseCount": self.use_case_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "area_id": self.area_id,
            "name": self.name,
            "area_type": self.area_type,
            "required": self.required,
            "readiness_status": self.readiness_status,
            "runtime_status": self.runtime_status,
            "priority": self.priority,
            "coverage_module_count": self.coverage_module_count,
            "capability_count": self.capability_count,
            "model_family_count": self.model_family_count,
            "use_case_count": self.use_case_count,
            "evidence_artifact_count": self.evidence_artifact_count,
            "evaluation_gate_count": self.evaluation_gate_count,
            "gap_count": self.gap_count,
            "next_action_count": self.next_action_count,
        }


@dataclass(frozen=True, slots=True)
class AiCapabilityTaxonomyReport:
    area_count: int
    required_area_count: int
    required_area_covered_count: int
    missing_required_areas: tuple[str, ...]
    model_area_count: int
    platform_area_count: int
    runtime_gap_area_count: int
    p1_gap_area_count: int
    capability_count: int
    evidence_artifact_count: int
    evaluation_gate_count: int
    by_area_type: dict[str, int]
    by_runtime_status: dict[str, int]
    areas: tuple[AiCapabilityTaxonomyArea, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "areaCount": self.area_count,
            "areas": [area.to_dict() for area in self.areas],
            "byAreaType": self.by_area_type,
            "byRuntimeStatus": self.by_runtime_status,
            "capabilityCount": self.capability_count,
            "evaluationGateCount": self.evaluation_gate_count,
            "evidenceArtifactCount": self.evidence_artifact_count,
            "missingRequiredAreas": list(self.missing_required_areas),
            "modelAreaCount": self.model_area_count,
            "p1GapAreaCount": self.p1_gap_area_count,
            "platformAreaCount": self.platform_area_count,
            "requiredAreaCount": self.required_area_count,
            "requiredAreaCoveredCount": self.required_area_covered_count,
            "runtimeGapAreaCount": self.runtime_gap_area_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "ai-capability-taxonomy-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "area_count": self.area_count,
                "required_area_count": self.required_area_count,
                "required_area_covered_count": self.required_area_covered_count,
                "missing_required_areas": list(self.missing_required_areas),
                "model_area_count": self.model_area_count,
                "platform_area_count": self.platform_area_count,
                "runtime_gap_area_count": self.runtime_gap_area_count,
                "p1_gap_area_count": self.p1_gap_area_count,
                "capability_count": self.capability_count,
                "evidence_artifact_count": self.evidence_artifact_count,
                "evaluation_gate_count": self.evaluation_gate_count,
            },
            "by_area_type": self.by_area_type,
            "by_runtime_status": self.by_runtime_status,
            "areas": [area.to_snapshot_dict() for area in self.areas],
        }


def build_ai_capability_taxonomy_report(ai_root: Path | str) -> AiCapabilityTaxonomyReport:
    root = Path(ai_root)
    registry = load_yaml(default_source_path(root))
    required_areas = tuple(require_string_list(registry, "required_areas", "taxonomy"))
    missing_configured_required = sorted(set(REQUIRED_CAPABILITY_AREAS) - set(required_areas))
    if missing_configured_required:
        raise RegistryValidationError(
            "AI capability taxonomy required_areas misses: "
            + ", ".join(missing_configured_required)
        )

    context = load_validation_context(root)
    rows = require_list(registry, "areas", "AI capability taxonomy")
    seen: set[str] = set()
    unique_capabilities: set[str] = set()
    unique_artifacts: set[str] = set()
    unique_evaluations: set[str] = set()
    areas: list[AiCapabilityTaxonomyArea] = []
    for row in rows:
        area = build_taxonomy_area(root, row, context)
        if area.area_id in seen:
            raise RegistryValidationError(
                f"AI capability taxonomy duplicate area_id: {area.area_id}"
            )
        seen.add(area.area_id)
        unique_capabilities.update(require_string_list(row, "capability_ids", area.area_id))
        unique_artifacts.update(require_string_list(row, "evidence_artifacts", area.area_id))
        unique_evaluations.update(require_string_list(row, "evaluation_gate_ids", area.area_id))
        areas.append(area)

    missing_required = tuple(sorted(set(REQUIRED_CAPABILITY_AREAS) - seen))
    if missing_required:
        raise RegistryValidationError(
            "AI capability taxonomy misses required areas: " + ", ".join(missing_required)
        )

    area_tuple = tuple(sorted(areas, key=sort_area))
    return AiCapabilityTaxonomyReport(
        area_count=len(area_tuple),
        required_area_count=len(REQUIRED_CAPABILITY_AREAS),
        required_area_covered_count=sum(1 for area in area_tuple if area.required),
        missing_required_areas=missing_required,
        model_area_count=sum(1 for area in area_tuple if area.area_type == "model"),
        platform_area_count=sum(1 for area in area_tuple if area.area_type == "platform"),
        runtime_gap_area_count=sum(
            1 for area in area_tuple if area.runtime_status != "production_ready"
        ),
        p1_gap_area_count=sum(1 for area in area_tuple if area.priority == "p1"),
        capability_count=len(unique_capabilities),
        evidence_artifact_count=len(unique_artifacts),
        evaluation_gate_count=len(unique_evaluations),
        by_area_type=count_by(area_tuple, "area_type"),
        by_runtime_status=count_by(area_tuple, "runtime_status"),
        areas=area_tuple,
    )


def build_ai_capability_taxonomy_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_ai_capability_taxonomy_report(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_ai_capability_taxonomy_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_ai_capability_taxonomy_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_taxonomy_area(
    root: Path,
    row: dict[str, Any],
    context: dict[str, set[str]],
) -> AiCapabilityTaxonomyArea:
    area_id = require_str(row, "id", "AI capability taxonomy area")
    owner = f"AI capability taxonomy area {area_id}"
    area_type = require_str(row, "area_type", owner)
    if area_type not in {"model", "platform"}:
        raise RegistryValidationError(f"{owner} area_type must be model or platform")

    runtime_status = require_str(row, "runtime_status", owner)
    if runtime_status not in ALLOWED_RUNTIME_STATUSES:
        raise RegistryValidationError(f"{owner} has unsupported runtime_status: {runtime_status}")

    priority = require_str(row, "priority", owner)
    if priority not in {"p1", "p2", "p3"}:
        raise RegistryValidationError(f"{owner} priority must be p1, p2 or p3")

    coverage_module_ids = require_string_list(row, "coverage_module_ids", owner)
    capability_ids = require_string_list(row, "capability_ids", owner)
    model_families = require_string_list(row, "model_families", owner)
    use_case_ids = require_string_list(row, "use_case_ids", owner)
    evidence_artifacts = require_string_list(row, "evidence_artifacts", owner)
    evaluation_gate_ids = require_string_list(row, "evaluation_gate_ids", owner)
    gaps = require_string_list(row, "gaps", owner)
    next_actions = require_string_list(row, "next_actions", owner)

    if not capability_ids:
        raise RegistryValidationError(f"{owner} must reference at least one platform capability")
    if not evidence_artifacts:
        raise RegistryValidationError(f"{owner} must reference evidence artifacts")
    if area_type == "model" and not model_families:
        raise RegistryValidationError(f"{owner} model area must reference model_families")

    validate_refs(coverage_module_ids, context["coverage_modules"], owner, "coverage module")
    validate_refs(capability_ids, context["capabilities"], owner, "capability")
    validate_refs(model_families, context["model_families"], owner, "model family")
    validate_refs(use_case_ids, context["use_cases"], owner, "use case")
    validate_refs(evaluation_gate_ids, context["evaluations"], owner, "evaluation gate")
    for artifact in evidence_artifacts:
        if not (root / artifact).exists():
            raise RegistryValidationError(f"{owner} evidence artifact does not exist: {artifact}")

    return AiCapabilityTaxonomyArea(
        area_id=area_id,
        name=require_str(row, "name", owner),
        area_type=area_type,
        required=area_id in REQUIRED_CAPABILITY_AREAS,
        readiness_status=require_str(row, "readiness_status", owner),
        runtime_status=runtime_status,
        priority=priority,
        coverage_module_count=len(set(coverage_module_ids)),
        capability_count=len(set(capability_ids)),
        model_family_count=len(set(model_families)),
        use_case_count=len(set(use_case_ids)),
        evidence_artifact_count=len(set(evidence_artifacts)),
        evaluation_gate_count=len(set(evaluation_gate_ids)),
        gap_count=len(set(gaps)),
        next_action_count=len(set(next_actions)),
    )


def load_validation_context(root: Path) -> dict[str, set[str]]:
    capability_registry = load_yaml(root / "platform" / "capabilities" / "registry.yaml")
    coverage_registry = load_yaml(
        root / "platform" / "coverage" / "business-capability-coverage.yaml"
    )
    model_family_registry = load_yaml(root / "model-families" / "registry.yaml")
    use_case_registry = load_yaml(root / "use-cases" / "registry.yaml")
    evaluation_registry = load_yaml(root / "platform" / "evaluation" / "registry.yaml")

    model_family_ids, aliases = collect_model_family_ids(
        require_list(model_family_registry, "families", "model-family registry")
    )
    return {
        "capabilities": {
            require_str(row, "id", "capability registry")
            for row in require_list(capability_registry, "capabilities", "capability registry")
        },
        "coverage_modules": {
            require_str(row, "id", "business capability coverage module")
            for row in require_list(coverage_registry, "modules", "coverage registry")
        },
        "evaluations": {
            require_str(row, "id", "evaluation registry")
            for row in require_list(evaluation_registry, "evaluations", "evaluation registry")
        },
        "model_families": model_family_ids | aliases,
        "use_cases": {
            require_str(row, "id", "use-case registry")
            for row in require_list(use_case_registry, "use_cases", "use-case registry")
        },
    }


def validate_refs(
    refs: list[str],
    known_refs: set[str],
    owner: str,
    ref_name: str,
) -> None:
    unknown = sorted(set(refs) - known_refs)
    if unknown:
        raise RegistryValidationError(
            f"{owner} references unknown {ref_name}: " + ", ".join(unknown)
        )


def require_string_list(row: dict[str, Any], key: str, owner: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a non-empty string")
        result.append(item.strip())
    return result


def sort_area(area: AiCapabilityTaxonomyArea) -> tuple[int, str]:
    try:
        index = REQUIRED_CAPABILITY_AREAS.index(area.area_id)
    except ValueError:
        index = len(REQUIRED_CAPABILITY_AREAS)
    return index, area.area_id


def count_by(
    areas: tuple[AiCapabilityTaxonomyArea, ...],
    attribute: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for area in areas:
        value = getattr(area, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def default_source_path(root: Path) -> Path:
    return root / "platform" / "coverage" / "ai-capability-taxonomy.yaml"


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "coverage" / "reports" / "ai-capability-taxonomy-v1.yaml"
