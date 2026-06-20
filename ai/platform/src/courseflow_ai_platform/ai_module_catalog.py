from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.coverage_taxonomy import (
    CoverageTaxonomyModule,
    CoverageTaxonomyReport,
    validate_coverage_taxonomy,
)
from courseflow_ai_platform.registry import (
    RegistryValidationError,
    load_yaml,
    require_list,
    require_str,
)
from courseflow_ai_platform.runtime_roadmap import (
    RuntimeRoadmapItem,
    RuntimeRoadmapReport,
    build_runtime_roadmap_report_from_coverage,
)

REQUIRED_SPECTRUM_SEQUENCE = (
    "classical_ml",
    "deep_learning",
    "nlp_transformers",
    "genai_llm",
    "rag",
    "computer_vision",
    "speech",
    "reinforcement_learning",
)

READINESS_ORDER = {
    "production_ready": 0,
    "service_integrated": 1,
    "runtime_library": 2,
    "shadow_artifact": 3,
    "tooling": 4,
    "registry_only": 5,
}


@dataclass(frozen=True, slots=True)
class AiModuleCatalogItem:
    module_id: str
    name: str
    taxonomy_area: str
    required_spectrum: bool
    spectrum_position: int
    coverage_status: str
    runtime_status: str
    readiness_level: str
    priority: str
    owner_role: str
    next_action: str
    model_family_count: int
    lms_use_case_count: int
    enterprise_use_case_count: int
    evidence_artifact_count: int
    evaluation_gate_count: int
    business_capabilities: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "businessCapabilities": list(self.business_capabilities),
            "coverageStatus": self.coverage_status,
            "enterpriseUseCaseCount": self.enterprise_use_case_count,
            "evaluationGateCount": self.evaluation_gate_count,
            "evidenceArtifactCount": self.evidence_artifact_count,
            "lmsUseCaseCount": self.lms_use_case_count,
            "modelFamilyCount": self.model_family_count,
            "moduleId": self.module_id,
            "name": self.name,
            "nextAction": self.next_action,
            "ownerRole": self.owner_role,
            "priority": self.priority,
            "readinessLevel": self.readiness_level,
            "requiredSpectrum": self.required_spectrum,
            "runtimeStatus": self.runtime_status,
            "spectrumPosition": self.spectrum_position,
            "taxonomyArea": self.taxonomy_area,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "name": self.name,
            "taxonomy_area": self.taxonomy_area,
            "required_spectrum": self.required_spectrum,
            "spectrum_position": self.spectrum_position,
            "coverage_status": self.coverage_status,
            "runtime_status": self.runtime_status,
            "readiness_level": self.readiness_level,
            "priority": self.priority,
            "owner_role": self.owner_role,
            "next_action": self.next_action,
            "model_family_count": self.model_family_count,
            "lms_use_case_count": self.lms_use_case_count,
            "enterprise_use_case_count": self.enterprise_use_case_count,
            "evidence_artifact_count": self.evidence_artifact_count,
            "evaluation_gate_count": self.evaluation_gate_count,
            "business_capabilities": list(self.business_capabilities),
        }


@dataclass(frozen=True, slots=True)
class AiModuleCatalogReport:
    module_count: int
    required_spectrum_count: int
    required_spectrum_covered_count: int
    extended_module_count: int
    lms_module_count: int
    enterprise_module_count: int
    service_integrated_count: int
    runtime_library_count: int
    production_ready_count: int
    runtime_gap_count: int
    p1_runtime_gap_count: int
    evaluation_gate_count: int
    platform_readiness_status: str
    required_spectrum_areas: tuple[str, ...]
    covered_required_spectrum_areas: tuple[str, ...]
    extended_taxonomy_areas: tuple[str, ...]
    first_runtime_candidate_ids: tuple[str, ...]
    by_runtime_status: dict[str, int]
    by_coverage_status: dict[str, int]
    items: tuple[AiModuleCatalogItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byCoverageStatus": self.by_coverage_status,
            "byRuntimeStatus": self.by_runtime_status,
            "coveredRequiredSpectrumAreas": list(self.covered_required_spectrum_areas),
            "enterpriseModuleCount": self.enterprise_module_count,
            "evaluationGateCount": self.evaluation_gate_count,
            "extendedModuleCount": self.extended_module_count,
            "extendedTaxonomyAreas": list(self.extended_taxonomy_areas),
            "firstRuntimeCandidateIds": list(self.first_runtime_candidate_ids),
            "items": [item.to_dict() for item in self.items],
            "lmsModuleCount": self.lms_module_count,
            "moduleCount": self.module_count,
            "p1RuntimeGapCount": self.p1_runtime_gap_count,
            "platformReadinessStatus": self.platform_readiness_status,
            "productionReadyCount": self.production_ready_count,
            "requiredSpectrumAreas": list(self.required_spectrum_areas),
            "requiredSpectrumCount": self.required_spectrum_count,
            "requiredSpectrumCoveredCount": self.required_spectrum_covered_count,
            "runtimeGapCount": self.runtime_gap_count,
            "runtimeLibraryCount": self.runtime_library_count,
            "serviceIntegratedCount": self.service_integrated_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "ai-module-catalog-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "module_count": self.module_count,
                "required_spectrum_count": self.required_spectrum_count,
                "required_spectrum_covered_count": self.required_spectrum_covered_count,
                "extended_module_count": self.extended_module_count,
                "lms_module_count": self.lms_module_count,
                "enterprise_module_count": self.enterprise_module_count,
                "service_integrated_count": self.service_integrated_count,
                "runtime_library_count": self.runtime_library_count,
                "production_ready_count": self.production_ready_count,
                "runtime_gap_count": self.runtime_gap_count,
                "p1_runtime_gap_count": self.p1_runtime_gap_count,
                "evaluation_gate_count": self.evaluation_gate_count,
                "platform_readiness_status": self.platform_readiness_status,
                "required_spectrum_areas": list(self.required_spectrum_areas),
                "covered_required_spectrum_areas": list(
                    self.covered_required_spectrum_areas
                ),
                "extended_taxonomy_areas": list(self.extended_taxonomy_areas),
                "first_runtime_candidate_ids": list(self.first_runtime_candidate_ids),
            },
            "by_runtime_status": self.by_runtime_status,
            "by_coverage_status": self.by_coverage_status,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_ai_module_catalog_report(ai_root: Path | str) -> AiModuleCatalogReport:
    root = Path(ai_root)
    coverage_report = validate_coverage_taxonomy(root)
    roadmap_report = build_runtime_roadmap_report_from_coverage(coverage_report)
    metadata = load_module_metadata(root)
    return build_ai_module_catalog_report_from_reports(
        coverage_report,
        roadmap_report,
        metadata,
    )


def build_ai_module_catalog_report_from_reports(
    coverage_report: CoverageTaxonomyReport,
    roadmap_report: RuntimeRoadmapReport,
    metadata: dict[str, dict[str, Any]],
) -> AiModuleCatalogReport:
    roadmap_by_module_id = {item.module_id: item for item in roadmap_report.items}
    items = tuple(
        sorted(
            (
                build_catalog_item(
                    module,
                    metadata.get(module.module_id, {}),
                    roadmap_by_module_id.get(module.module_id),
                )
                for module in coverage_report.modules
            ),
            key=sort_catalog_item,
        )
    )
    covered_taxonomy_areas = {item.taxonomy_area for item in items}
    covered_required = tuple(
        area for area in REQUIRED_SPECTRUM_SEQUENCE if area in covered_taxonomy_areas
    )
    extended_areas = tuple(
        sorted(
            {
                item.taxonomy_area
                for item in items
                if item.taxonomy_area not in REQUIRED_SPECTRUM_SEQUENCE
            }
        )
    )
    return AiModuleCatalogReport(
        module_count=coverage_report.module_count,
        required_spectrum_count=len(REQUIRED_SPECTRUM_SEQUENCE),
        required_spectrum_covered_count=len(covered_required),
        extended_module_count=sum(1 for item in items if not item.required_spectrum),
        lms_module_count=coverage_report.lms_module_count,
        enterprise_module_count=coverage_report.enterprise_module_count,
        service_integrated_count=roadmap_report.service_integrated_count,
        runtime_library_count=roadmap_report.runtime_library_count,
        production_ready_count=roadmap_report.production_ready_count,
        runtime_gap_count=roadmap_report.runtime_gap_count,
        p1_runtime_gap_count=roadmap_report.p1_count,
        evaluation_gate_count=coverage_report.evaluation_gate_count,
        platform_readiness_status=derive_platform_readiness_status(
            coverage_report,
            roadmap_report,
            covered_required,
        ),
        required_spectrum_areas=REQUIRED_SPECTRUM_SEQUENCE,
        covered_required_spectrum_areas=covered_required,
        extended_taxonomy_areas=extended_areas,
        first_runtime_candidate_ids=roadmap_report.first_runtime_candidate_ids,
        by_runtime_status=coverage_report.runtime_status_counts,
        by_coverage_status={
            "executable_gate": coverage_report.executable_gate_count,
            "implemented_baseline": coverage_report.implemented_baseline_count,
            "privacy_gated": coverage_report.privacy_gated_count,
            "registered_roadmap": coverage_report.registered_roadmap_count,
            "simulator_required": coverage_report.simulator_required_count,
        },
        items=items,
    )


def build_ai_module_catalog_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_ai_module_catalog_report(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_ai_module_catalog_snapshot(
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
            build_ai_module_catalog_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_catalog_item(
    module: CoverageTaxonomyModule,
    metadata: dict[str, Any],
    roadmap_item: RuntimeRoadmapItem | None,
) -> AiModuleCatalogItem:
    name = metadata.get("name") or module.module_id.replace("-", " ").title()
    if not isinstance(name, str):
        raise RegistryValidationError(f"AI module catalog name is invalid: {module.module_id}")
    capabilities = normalize_string_tuple(metadata.get("business_capabilities", []))
    taxonomy_index = taxonomy_position(module.taxonomy_area)
    return AiModuleCatalogItem(
        module_id=module.module_id,
        name=name,
        taxonomy_area=module.taxonomy_area,
        required_spectrum=module.taxonomy_area in REQUIRED_SPECTRUM_SEQUENCE,
        spectrum_position=taxonomy_index,
        coverage_status=module.coverage_status,
        runtime_status=module.runtime_status,
        readiness_level=derive_readiness_level(module.runtime_status),
        priority=roadmap_item.priority if roadmap_item is not None else "",
        owner_role=roadmap_item.owner_role if roadmap_item is not None else "",
        next_action=roadmap_item.next_action if roadmap_item is not None else "",
        model_family_count=module.model_family_count,
        lms_use_case_count=module.lms_use_case_count,
        enterprise_use_case_count=module.enterprise_use_case_count,
        evidence_artifact_count=module.evidence_artifact_count,
        evaluation_gate_count=module.evaluation_gate_count,
        business_capabilities=capabilities,
    )


def derive_platform_readiness_status(
    coverage_report: CoverageTaxonomyReport,
    roadmap_report: RuntimeRoadmapReport,
    covered_required: tuple[str, ...],
) -> str:
    if len(covered_required) < len(REQUIRED_SPECTRUM_SEQUENCE):
        return "missing_required_spectrum"
    if roadmap_report.production_ready_count == coverage_report.module_count:
        return "production_ready"
    if roadmap_report.runtime_ready_count == coverage_report.module_count:
        return "runtime_ready"
    return "covered_with_runtime_gaps"


def derive_readiness_level(runtime_status: str) -> str:
    if runtime_status == "registry_only":
        return "registered"
    return runtime_status


def load_module_metadata(root: Path) -> dict[str, dict[str, Any]]:
    registry = load_yaml(root / "platform" / "coverage" / "business-capability-coverage.yaml")
    rows = require_list(registry, "modules", "business capability coverage registry")
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RegistryValidationError(
                "business capability coverage registry modules must be mappings"
            )
        module_id = require_str(row, "id", "business capability coverage module")
        metadata[module_id] = row
    return metadata


def normalize_string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise RegistryValidationError(
            "AI module catalog business_capabilities must be a list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(
                "AI module catalog business_capabilities values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def taxonomy_position(taxonomy_area: str) -> int:
    if taxonomy_area in REQUIRED_SPECTRUM_SEQUENCE:
        return REQUIRED_SPECTRUM_SEQUENCE.index(taxonomy_area) + 1
    return len(REQUIRED_SPECTRUM_SEQUENCE) + 1


def sort_catalog_item(item: AiModuleCatalogItem) -> tuple[int, int, str]:
    return (
        item.spectrum_position,
        READINESS_ORDER.get(item.runtime_status, 99),
        item.module_id,
    )


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "coverage" / "reports" / "ai-module-catalog-v1.yaml"
