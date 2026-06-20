from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.coverage_taxonomy import (
    REQUIRED_TAXONOMY_AREAS,
    CoverageTaxonomyModule,
    CoverageTaxonomyReport,
    validate_coverage_taxonomy,
)

RUNTIME_READY_STATUSES = frozenset({"service_integrated", "production_ready"})
PRIORITY_ORDER = {"p1": 0, "p2": 1, "p3": 2}
TAXONOMY_ORDER = {
    "deep_learning": 0,
    "rag": 1,
    "genai_llm": 2,
    "nlp_transformers": 3,
    "computer_vision": 4,
    "speech": 5,
    "reinforcement_learning": 6,
    "anomaly_fraud_risk": 7,
    "forecasting_time_series": 8,
    "causal_experimentation": 9,
    "graph_knowledge": 10,
    "governance_safety": 11,
    "recommender_systems": 12,
    "classical_ml": 13,
}


@dataclass(frozen=True, slots=True)
class RuntimeRoadmapItem:
    module_id: str
    taxonomy_area: str
    coverage_status: str
    runtime_status: str
    priority: str
    owner_role: str
    next_action: str
    reason: str
    model_family_count: int
    lms_use_case_count: int
    enterprise_use_case_count: int
    evidence_artifact_count: int
    evaluation_gate_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "coverageStatus": self.coverage_status,
            "enterpriseUseCaseCount": self.enterprise_use_case_count,
            "evaluationGateCount": self.evaluation_gate_count,
            "evidenceArtifactCount": self.evidence_artifact_count,
            "lmsUseCaseCount": self.lms_use_case_count,
            "modelFamilyCount": self.model_family_count,
            "moduleId": self.module_id,
            "nextAction": self.next_action,
            "ownerRole": self.owner_role,
            "priority": self.priority,
            "reason": self.reason,
            "runtimeStatus": self.runtime_status,
            "taxonomyArea": self.taxonomy_area,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "taxonomy_area": self.taxonomy_area,
            "coverage_status": self.coverage_status,
            "runtime_status": self.runtime_status,
            "priority": self.priority,
            "owner_role": self.owner_role,
            "next_action": self.next_action,
            "reason": self.reason,
            "model_family_count": self.model_family_count,
            "lms_use_case_count": self.lms_use_case_count,
            "enterprise_use_case_count": self.enterprise_use_case_count,
            "evidence_artifact_count": self.evidence_artifact_count,
            "evaluation_gate_count": self.evaluation_gate_count,
        }


@dataclass(frozen=True, slots=True)
class RuntimeRoadmapReport:
    module_count: int
    runtime_ready_count: int
    runtime_gap_count: int
    service_integrated_count: int
    production_ready_count: int
    p1_count: int
    p2_count: int
    p3_count: int
    registry_only_count: int
    tooling_count: int
    runtime_library_count: int
    shadow_artifact_count: int
    first_runtime_candidate_ids: tuple[str, ...]
    by_priority: dict[str, int]
    by_runtime_status: dict[str, int]
    items: tuple[RuntimeRoadmapItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byPriority": self.by_priority,
            "byRuntimeStatus": self.by_runtime_status,
            "firstRuntimeCandidateIds": list(self.first_runtime_candidate_ids),
            "items": [item.to_dict() for item in self.items],
            "moduleCount": self.module_count,
            "p1Count": self.p1_count,
            "p2Count": self.p2_count,
            "p3Count": self.p3_count,
            "productionReadyCount": self.production_ready_count,
            "registryOnlyCount": self.registry_only_count,
            "runtimeGapCount": self.runtime_gap_count,
            "runtimeLibraryCount": self.runtime_library_count,
            "runtimeReadyCount": self.runtime_ready_count,
            "serviceIntegratedCount": self.service_integrated_count,
            "shadowArtifactCount": self.shadow_artifact_count,
            "toolingCount": self.tooling_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "runtime-roadmap-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "module_count": self.module_count,
                "runtime_ready_count": self.runtime_ready_count,
                "runtime_gap_count": self.runtime_gap_count,
                "service_integrated_count": self.service_integrated_count,
                "production_ready_count": self.production_ready_count,
                "p1_count": self.p1_count,
                "p2_count": self.p2_count,
                "p3_count": self.p3_count,
                "registry_only_count": self.registry_only_count,
                "tooling_count": self.tooling_count,
                "runtime_library_count": self.runtime_library_count,
                "shadow_artifact_count": self.shadow_artifact_count,
                "first_runtime_candidate_ids": list(self.first_runtime_candidate_ids),
            },
            "by_priority": self.by_priority,
            "by_runtime_status": self.by_runtime_status,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_runtime_roadmap_report(ai_root: Path | str) -> RuntimeRoadmapReport:
    coverage_report = validate_coverage_taxonomy(ai_root)
    return build_runtime_roadmap_report_from_coverage(coverage_report)


def build_runtime_roadmap_report_from_coverage(
    coverage_report: CoverageTaxonomyReport,
) -> RuntimeRoadmapReport:
    items = tuple(
        sorted(
            (
                build_runtime_roadmap_item(module)
                for module in coverage_report.modules
                if module.runtime_status not in RUNTIME_READY_STATUSES
            ),
            key=sort_roadmap_item,
        )
    )
    by_priority = count_by(items, "priority")
    by_runtime_status = count_by(items, "runtime_status")
    runtime_counts = coverage_report.runtime_status_counts
    return RuntimeRoadmapReport(
        module_count=coverage_report.module_count,
        runtime_ready_count=sum(
            runtime_counts.get(status, 0) for status in RUNTIME_READY_STATUSES
        ),
        runtime_gap_count=len(items),
        service_integrated_count=runtime_counts.get("service_integrated", 0),
        production_ready_count=runtime_counts.get("production_ready", 0),
        p1_count=by_priority.get("p1", 0),
        p2_count=by_priority.get("p2", 0),
        p3_count=by_priority.get("p3", 0),
        registry_only_count=runtime_counts.get("registry_only", 0),
        tooling_count=runtime_counts.get("tooling", 0),
        runtime_library_count=runtime_counts.get("runtime_library", 0),
        shadow_artifact_count=runtime_counts.get("shadow_artifact", 0),
        first_runtime_candidate_ids=tuple(
            item.module_id for item in items if item.priority == "p1"
        ),
        by_priority=by_priority,
        by_runtime_status=by_runtime_status,
        items=items,
    )


def build_runtime_roadmap_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_runtime_roadmap_report(ai_root).to_snapshot_dict(generated_at=report_date)


def write_runtime_roadmap_snapshot(
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
            build_runtime_roadmap_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_runtime_roadmap_item(module: CoverageTaxonomyModule) -> RuntimeRoadmapItem:
    return RuntimeRoadmapItem(
        module_id=module.module_id,
        taxonomy_area=module.taxonomy_area,
        coverage_status=module.coverage_status,
        runtime_status=module.runtime_status,
        priority=derive_priority(module),
        owner_role=derive_owner_role(module),
        next_action=derive_next_action(module),
        reason=derive_reason(module),
        model_family_count=module.model_family_count,
        lms_use_case_count=module.lms_use_case_count,
        enterprise_use_case_count=module.enterprise_use_case_count,
        evidence_artifact_count=module.evidence_artifact_count,
        evaluation_gate_count=module.evaluation_gate_count,
    )


def derive_priority(module: CoverageTaxonomyModule) -> str:
    if (
        module.taxonomy_area in REQUIRED_TAXONOMY_AREAS
        and module.runtime_status == "registry_only"
    ):
        return "p1"
    if module.coverage_status in {"privacy_gated", "simulator_required"}:
        return "p1"
    if module.runtime_status in {"tooling", "runtime_library", "shadow_artifact"}:
        return "p2"
    if module.runtime_status == "registry_only":
        return "p2"
    return "p3"


def derive_owner_role(module: CoverageTaxonomyModule) -> str:
    if module.coverage_status == "privacy_gated":
        return "SA AI Platform + Governance Reviewer"
    if module.coverage_status == "simulator_required":
        return "SA AI Engineer"
    if module.runtime_status == "runtime_library":
        return "SA AI Platform"
    if module.runtime_status == "shadow_artifact":
        return "SA AI Engineer"
    if module.runtime_status == "tooling":
        return "SA AI Platform + SA AI Engineer"
    return "SA AI Engineer"


def derive_next_action(module: CoverageTaxonomyModule) -> str:
    if module.coverage_status == "privacy_gated":
        return "complete_privacy_review_and_publish_runtime_artifact_plan"
    if module.coverage_status == "simulator_required":
        return "build_simulator_and_offline_policy_evaluation"
    if module.runtime_status == "runtime_library":
        return "host_or_service_integrate_runtime_library"
    if module.runtime_status == "shadow_artifact":
        return "promote_shadow_artifact_to_service_runtime"
    if module.runtime_status == "tooling":
        return "promote_tooling_to_runtime_library_or_service"
    return "publish_runtime_artifact_manifest_and_evaluation_gate"


def derive_reason(module: CoverageTaxonomyModule) -> str:
    if module.coverage_status == "privacy_gated":
        return "privacy review is required before media, document or audio runtime"
    if module.coverage_status == "simulator_required":
        return "simulator and offline policy evaluation are required before decision runtime"
    if module.runtime_status == "runtime_library":
        return "runtime library exists but is not hosted or service-integrated"
    if module.runtime_status == "shadow_artifact":
        return "shadow artifact exists but is not service-integrated"
    if module.runtime_status == "tooling":
        return "module has executable tooling but no runtime library or service integration"
    return "module is covered in registry but has no runtime artifact yet"


def sort_roadmap_item(item: RuntimeRoadmapItem) -> tuple[int, int, str]:
    return (
        PRIORITY_ORDER.get(item.priority, 99),
        TAXONOMY_ORDER.get(item.taxonomy_area, 99),
        item.module_id,
    )


def count_by(items: tuple[RuntimeRoadmapItem, ...], attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "coverage" / "reports" / "runtime-roadmap-v1.yaml"
