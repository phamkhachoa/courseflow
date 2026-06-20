from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import (
    RegistryValidationError,
    collect_model_family_ids,
    load_yaml,
    require_list,
    require_str,
)

ALLOWED_COVERAGE_STATUSES = frozenset(
    {
        "implemented_baseline",
        "executable_gate",
        "registered_roadmap",
        "privacy_gated",
        "simulator_required",
    }
)

ALLOWED_RUNTIME_STATUSES = frozenset(
    {
        "registry_only",
        "tooling",
        "runtime_library",
        "service_integrated",
        "shadow_artifact",
        "production_ready",
    }
)

REQUIRED_TAXONOMY_AREAS = frozenset(
    {
        "classical_ml",
        "deep_learning",
        "nlp_transformers",
        "genai_llm",
        "rag",
        "computer_vision",
        "speech",
        "reinforcement_learning",
    }
)


@dataclass(frozen=True, slots=True)
class CoverageTaxonomyModule:
    module_id: str
    taxonomy_area: str
    coverage_status: str
    runtime_status: str
    model_family_count: int
    lms_use_case_count: int
    enterprise_use_case_count: int
    evidence_artifact_count: int
    evaluation_gate_count: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "moduleId": self.module_id,
            "taxonomyArea": self.taxonomy_area,
            "coverageStatus": self.coverage_status,
            "runtimeStatus": self.runtime_status,
            "modelFamilyCount": self.model_family_count,
            "lmsUseCaseCount": self.lms_use_case_count,
            "enterpriseUseCaseCount": self.enterprise_use_case_count,
            "evidenceArtifactCount": self.evidence_artifact_count,
            "evaluationGateCount": self.evaluation_gate_count,
        }


@dataclass(frozen=True, slots=True)
class CoverageTaxonomyReport:
    module_count: int
    required_area_count: int
    missing_required_areas: tuple[str, ...]
    implemented_baseline_count: int
    executable_gate_count: int
    registered_roadmap_count: int
    privacy_gated_count: int
    simulator_required_count: int
    runtime_status_counts: dict[str, int]
    lms_module_count: int
    enterprise_module_count: int
    model_family_count: int
    use_case_count: int
    evidence_artifact_count: int
    evaluation_gate_count: int
    modules: tuple[CoverageTaxonomyModule, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "moduleCount": self.module_count,
            "requiredAreaCount": self.required_area_count,
            "missingRequiredAreas": list(self.missing_required_areas),
            "implementedBaselineCount": self.implemented_baseline_count,
            "executableGateCount": self.executable_gate_count,
            "registeredRoadmapCount": self.registered_roadmap_count,
            "privacyGatedCount": self.privacy_gated_count,
            "simulatorRequiredCount": self.simulator_required_count,
            "runtimeStatusCounts": self.runtime_status_counts,
            "lmsModuleCount": self.lms_module_count,
            "enterpriseModuleCount": self.enterprise_module_count,
            "modelFamilyCount": self.model_family_count,
            "useCaseCount": self.use_case_count,
            "evidenceArtifactCount": self.evidence_artifact_count,
            "evaluationGateCount": self.evaluation_gate_count,
            "modules": [module.to_dict() for module in self.modules],
        }


def validate_coverage_taxonomy(ai_root: Path | str) -> CoverageTaxonomyReport:
    root = Path(ai_root)
    coverage_path = root / "platform" / "coverage" / "business-capability-coverage.yaml"
    coverage_registry = load_yaml(coverage_path)

    configured_statuses = require_string_set(
        coverage_registry,
        "coverage_statuses",
        "business capability coverage registry",
    )
    missing_statuses = sorted(ALLOWED_COVERAGE_STATUSES - configured_statuses)
    if missing_statuses:
        raise RegistryValidationError(
            "business capability coverage registry misses statuses: "
            + ", ".join(missing_statuses)
        )

    configured_runtime_statuses = require_string_set(
        coverage_registry,
        "runtime_statuses",
        "business capability coverage registry",
    )
    missing_runtime_statuses = sorted(ALLOWED_RUNTIME_STATUSES - configured_runtime_statuses)
    if missing_runtime_statuses:
        raise RegistryValidationError(
            "business capability coverage registry misses runtime statuses: "
            + ", ".join(missing_runtime_statuses)
        )

    modules = require_mapping_list(
        coverage_registry,
        "modules",
        "business capability coverage registry",
    )
    if not modules:
        raise RegistryValidationError("business capability coverage registry must define modules")

    model_family_registry = load_yaml(root / "model-families" / "registry.yaml")
    model_family_rows = require_list(
        model_family_registry,
        "families",
        "model-family registry",
    )
    model_family_ids, model_family_aliases = collect_model_family_ids(model_family_rows)
    known_model_families = model_family_ids | model_family_aliases

    use_case_registry = load_yaml(root / "use-cases" / "registry.yaml")
    use_cases = {
        require_str(row, "id", "use-case registry"): row
        for row in require_list(use_case_registry, "use_cases", "use-case registry")
    }

    evaluation_registry = load_yaml(root / "platform" / "evaluation" / "registry.yaml")
    evaluations = {
        require_str(row, "id", "evaluation registry"): row
        for row in require_list(evaluation_registry, "evaluations", "evaluation registry")
    }

    seen_modules: set[str] = set()
    covered_areas: set[str] = set()
    status_counts = dict.fromkeys(ALLOWED_COVERAGE_STATUSES, 0)
    runtime_status_counts = dict.fromkeys(ALLOWED_RUNTIME_STATUSES, 0)
    lms_module_count = 0
    enterprise_module_count = 0
    model_family_refs: set[str] = set()
    use_case_refs: set[str] = set()
    evidence_refs: set[str] = set()
    evaluation_gate_refs: set[str] = set()
    report_modules: list[CoverageTaxonomyModule] = []

    for row in modules:
        module_id = require_str(row, "id", "business capability coverage module")
        owner = f"business capability coverage module {module_id}"
        if module_id in seen_modules:
            raise RegistryValidationError(f"business capability coverage duplicate id: {module_id}")
        seen_modules.add(module_id)

        taxonomy_area = require_str(row, "taxonomy_area", owner)
        covered_areas.add(taxonomy_area)

        coverage_status = require_str(row, "coverage_status", owner)
        if coverage_status not in configured_statuses:
            raise RegistryValidationError(
                f"{owner} has unsupported coverage_status: {coverage_status}"
            )
        status_counts[coverage_status] = status_counts.get(coverage_status, 0) + 1

        runtime_status = require_str(row, "runtime_status", owner)
        if runtime_status not in configured_runtime_statuses:
            raise RegistryValidationError(
                f"{owner} has unsupported runtime_status: {runtime_status}"
            )
        runtime_status_counts[runtime_status] = runtime_status_counts.get(runtime_status, 0) + 1

        model_families = require_string_list(row, "model_families", owner)
        if not model_families:
            raise RegistryValidationError(f"{owner} must reference at least one model family")
        for family in model_families:
            if family not in known_model_families:
                raise RegistryValidationError(
                    f"{owner} references unknown model family: {family}"
                )
            model_family_refs.add(family)

        lms_use_cases = require_string_list(row, "lms_use_cases", owner)
        enterprise_use_cases = require_string_list(row, "enterprise_use_cases", owner)
        if not lms_use_cases:
            raise RegistryValidationError(f"{owner} must reference at least one LMS use case")
        if not enterprise_use_cases:
            raise RegistryValidationError(
                f"{owner} must reference at least one enterprise use case"
            )
        lms_module_count += 1
        enterprise_module_count += 1

        validate_use_case_refs(use_cases, lms_use_cases, "lms-courseflow", owner)
        validate_use_case_refs(use_cases, enterprise_use_cases, None, owner)
        use_case_refs.update(lms_use_cases)
        use_case_refs.update(enterprise_use_cases)

        evidence_artifacts = require_string_list(row, "evidence_artifacts", owner)
        if not evidence_artifacts:
            raise RegistryValidationError(f"{owner} must reference evidence artifacts")
        for artifact in evidence_artifacts:
            if not (root / artifact).exists():
                raise RegistryValidationError(
                    f"{owner} evidence artifact does not exist: {artifact}"
                )
            evidence_refs.add(artifact)

        evaluation_gate_ids = require_string_list(row, "evaluation_gate_ids", owner)
        needs_gate = coverage_status in {"implemented_baseline", "executable_gate"}
        if needs_gate and not evaluation_gate_ids:
            raise RegistryValidationError(
                f"{owner} with status {coverage_status} must reference evaluation gates"
            )
        for gate_id in evaluation_gate_ids:
            evaluation = evaluations.get(gate_id)
            if evaluation is None:
                raise RegistryValidationError(
                    f"{owner} references unknown evaluation gate: {gate_id}"
                )
            report_path = require_str(evaluation, "report", f"evaluation {gate_id}")
            if not (root / report_path).exists():
                raise RegistryValidationError(
                    f"{owner} evaluation report does not exist: {report_path}"
                )
            evaluation_gate_refs.add(gate_id)

        report_modules.append(
            CoverageTaxonomyModule(
                module_id=module_id,
                taxonomy_area=taxonomy_area,
                coverage_status=coverage_status,
                runtime_status=runtime_status,
                model_family_count=len(set(model_families)),
                lms_use_case_count=len(set(lms_use_cases)),
                enterprise_use_case_count=len(set(enterprise_use_cases)),
                evidence_artifact_count=len(set(evidence_artifacts)),
                evaluation_gate_count=len(set(evaluation_gate_ids)),
            )
        )

    missing_required_areas = tuple(sorted(REQUIRED_TAXONOMY_AREAS - covered_areas))
    if missing_required_areas:
        raise RegistryValidationError(
            "business capability coverage misses required taxonomy areas: "
            + ", ".join(missing_required_areas)
        )

    return CoverageTaxonomyReport(
        module_count=len(report_modules),
        required_area_count=len(REQUIRED_TAXONOMY_AREAS),
        missing_required_areas=missing_required_areas,
        implemented_baseline_count=status_counts["implemented_baseline"],
        executable_gate_count=status_counts["executable_gate"],
        registered_roadmap_count=status_counts["registered_roadmap"],
        privacy_gated_count=status_counts["privacy_gated"],
        simulator_required_count=status_counts["simulator_required"],
        runtime_status_counts=dict(sorted(runtime_status_counts.items())),
        lms_module_count=lms_module_count,
        enterprise_module_count=enterprise_module_count,
        model_family_count=len(model_family_refs),
        use_case_count=len(use_case_refs),
        evidence_artifact_count=len(evidence_refs),
        evaluation_gate_count=len(evaluation_gate_refs),
        modules=tuple(report_modules),
    )


def validate_use_case_refs(
    use_cases: dict[str, dict[str, Any]],
    refs: list[str],
    required_product: str | None,
    owner: str,
) -> None:
    for use_case_id in refs:
        use_case = use_cases.get(use_case_id)
        if use_case is None:
            raise RegistryValidationError(f"{owner} references unknown use case: {use_case_id}")
        product = require_str(use_case, "product", f"use case {use_case_id}")
        if required_product is not None and product != required_product:
            raise RegistryValidationError(
                f"{owner} lms_use_cases must reference {required_product}: {use_case_id}"
            )
        if required_product is None and product == "lms-courseflow":
            raise RegistryValidationError(
                f"{owner} enterprise_use_cases cannot reference LMS use case: {use_case_id}"
            )


def require_mapping_list(row: dict[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


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


def require_string_set(row: dict[str, Any], key: str, owner: str) -> set[str]:
    values = require_string_list(row, key, owner)
    result = set(values)
    if len(result) != len(values):
        raise RegistryValidationError(f"{owner} {key} must not contain duplicates")
    return result
