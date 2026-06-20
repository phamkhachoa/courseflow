from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.solution_blueprint import (
    SolutionBlueprintReport,
    UseCaseSolutionBlueprint,
    build_solution_blueprint_report,
)

RELEASE_GATE_EFFECTIVENESS_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_effectiveness"
)
_EFFECTIVENESS_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEffectivenessReport"
)
_EFFECTIVENESS_BUILDER_ATTR = (
    "build_suppression_policy_coverage_release_gate_effectiveness_report"
)
_EXPAND_ENTERPRISE_PATTERN_ACTION_ATTR = (
    "EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION"
)
release_gate_effectiveness_module = import_module(RELEASE_GATE_EFFECTIVENESS_MODULE)
ReleaseGateEffectivenessReport = getattr(
    release_gate_effectiveness_module,
    _EFFECTIVENESS_REPORT_ATTR,
)
build_release_gate_effectiveness_report = getattr(
    release_gate_effectiveness_module,
    _EFFECTIVENESS_BUILDER_ATTR,
)
EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION = getattr(
    release_gate_effectiveness_module,
    _EXPAND_ENTERPRISE_PATTERN_ACTION_ATTR,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-pattern-v1"
)
MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION = (
    "monitor_enterprise_release_gate_pattern_adoption"
)
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
OPENAI_KEY_PATTERN = re.compile(r"(^|[\"'\\s:=])sk-[a-z0-9]")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
EXPECTED_EFFECTIVENESS_STATUS = "effectiveness_monitored"
EXPECTED_BLUEPRINT_STATUS = "ready_for_solution_design"
MIN_NON_LMS_BLUEPRINT_COUNT = 5
MIN_NON_LMS_PRODUCT_COUNT = 4
MIN_TAXONOMY_AREA_COUNT = 8
PATTERN_CONTROLS = (
    "release_gate_drill_status",
    "scenario_pass_rate",
    "blocked_queue_cleanliness",
    "tenant_safety",
    "evidence_completeness",
)


@dataclass(frozen=True, slots=True)
class EnterprisePatternAssignment:
    assignment_id: str
    request_id: str
    product: str
    use_case_id: str
    use_case_name: str
    is_non_lms: bool
    blueprint_status: str
    target_module_count: int
    executable_module_count: int
    evaluation_gate_count: int
    taxonomy_areas: tuple[str, ...]
    pattern_controls: tuple[str, ...]
    expansion_ready: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignmentId": self.assignment_id,
            "blueprintStatus": self.blueprint_status,
            "evaluationGateCount": self.evaluation_gate_count,
            "evidenceRefs": list(self.evidence_refs),
            "executableModuleCount": self.executable_module_count,
            "expansionReady": self.expansion_ready,
            "isNonLms": self.is_non_lms,
            "patternControls": list(self.pattern_controls),
            "product": self.product,
            "requestId": self.request_id,
            "targetModuleCount": self.target_module_count,
            "taxonomyAreas": list(self.taxonomy_areas),
            "useCaseId": self.use_case_id,
            "useCaseName": self.use_case_name,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "request_id": self.request_id,
            "product": self.product,
            "use_case_id": self.use_case_id,
            "use_case_name": self.use_case_name,
            "is_non_lms": self.is_non_lms,
            "blueprint_status": self.blueprint_status,
            "target_module_count": self.target_module_count,
            "executable_module_count": self.executable_module_count,
            "evaluation_gate_count": self.evaluation_gate_count,
            "taxonomy_areas": list(self.taxonomy_areas),
            "pattern_controls": list(self.pattern_controls),
            "expansion_ready": self.expansion_ready,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class EnterprisePatternReport:
    generated_at: str
    expansion_status: str
    release_gate_effectiveness_status: str
    release_gate_signal_count: int
    release_gate_effective_signal_count: int
    blueprint_count: int
    ready_blueprint_count: int
    non_lms_blueprint_count: int
    product_count: int
    non_lms_product_count: int
    taxonomy_area_count: int
    target_module_count: int
    executable_module_count: int
    evaluation_gate_count: int
    assigned_use_case_count: int
    blocked_assignment_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    assignments: tuple[EnterprisePatternAssignment, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignedUseCaseCount": self.assigned_use_case_count,
            "assignments": [item.to_dict() for item in self.assignments],
            "blockedAssignmentCount": self.blocked_assignment_count,
            "blueprintCount": self.blueprint_count,
            "evaluationGateCount": self.evaluation_gate_count,
            "executableModuleCount": self.executable_module_count,
            "expansionStatus": self.expansion_status,
            "generatedAt": self.generated_at,
            "nextActions": list(self.next_actions),
            "nonLmsBlueprintCount": self.non_lms_blueprint_count,
            "nonLmsProductCount": self.non_lms_product_count,
            "productCount": self.product_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "readyBlueprintCount": self.ready_blueprint_count,
            "releaseGateEffectiveSignalCount": (
                self.release_gate_effective_signal_count
            ),
            "releaseGateEffectivenessStatus": (
                self.release_gate_effectiveness_status
            ),
            "releaseGateSignalCount": self.release_gate_signal_count,
            "targetModuleCount": self.target_module_count,
            "taxonomyAreaCount": self.taxonomy_area_count,
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "expansion_status": self.expansion_status,
                "release_gate_effectiveness_status": (
                    self.release_gate_effectiveness_status
                ),
                "release_gate_signal_count": self.release_gate_signal_count,
                "release_gate_effective_signal_count": (
                    self.release_gate_effective_signal_count
                ),
                "blueprint_count": self.blueprint_count,
                "ready_blueprint_count": self.ready_blueprint_count,
                "non_lms_blueprint_count": self.non_lms_blueprint_count,
                "product_count": self.product_count,
                "non_lms_product_count": self.non_lms_product_count,
                "taxonomy_area_count": self.taxonomy_area_count,
                "target_module_count": self.target_module_count,
                "executable_module_count": self.executable_module_count,
                "evaluation_gate_count": self.evaluation_gate_count,
                "assigned_use_case_count": self.assigned_use_case_count,
                "blocked_assignment_count": self.blocked_assignment_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "min_non_lms_blueprint_count": MIN_NON_LMS_BLUEPRINT_COUNT,
                "min_non_lms_product_count": MIN_NON_LMS_PRODUCT_COUNT,
                "min_taxonomy_area_count": MIN_TAXONOMY_AREA_COUNT,
            },
            "action_queue": {
                "assigned": [
                    item.assignment_id
                    for item in self.assignments
                    if item.expansion_ready
                ],
                "blocked": [
                    item.assignment_id
                    for item in self.assignments
                    if not item.expansion_ready
                ],
                "next_actions": list(self.next_actions),
            },
            "assignments": [
                item.to_snapshot_dict() for item in self.assignments
            ],
        }


globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterprisePatternAssignment"
] = EnterprisePatternAssignment
globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterprisePatternReport"
] = EnterprisePatternReport


def build_suppression_policy_coverage_release_gate_enterprise_pattern_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    release_gate_effectiveness: ReleaseGateEffectivenessReport | None = None,
    solution_blueprint: SolutionBlueprintReport | None = None,
) -> EnterprisePatternReport:
    effectiveness = release_gate_effectiveness or (
        build_release_gate_effectiveness_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    blueprint = solution_blueprint or build_solution_blueprint_report(ai_root)
    return build_release_gate_enterprise_pattern_report_from_reports(
        effectiveness,
        solution_blueprint=blueprint,
        generated_at=generated_at,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_report"
] = build_suppression_policy_coverage_release_gate_enterprise_pattern_report


def build_release_gate_enterprise_pattern_report_from_reports(
    release_gate_effectiveness: ReleaseGateEffectivenessReport,
    *,
    solution_blueprint: SolutionBlueprintReport,
    generated_at: str | None = None,
) -> EnterprisePatternReport:
    report_date = generated_at or release_gate_effectiveness.generated_at
    assignments = tuple(
        build_enterprise_pattern_assignment(
            blueprint,
            release_gate_effectiveness=release_gate_effectiveness,
        )
        for blueprint in solution_blueprint.blueprints
    )
    raw_identifier_count = count_raw_identifier_markers(assignments)
    tenant_safe = (
        release_gate_effectiveness.tenant_safe
        and release_gate_effectiveness.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    products = {assignment.product for assignment in assignments}
    non_lms_products = {
        assignment.product
        for assignment in assignments
        if assignment.is_non_lms
    }
    taxonomy_areas = {
        area
        for assignment in assignments
        for area in assignment.taxonomy_areas
    }
    blocked_assignment_count = sum(
        1 for assignment in assignments if not assignment.expansion_ready
    )
    expansion_status = derive_enterprise_pattern_expansion_status(
        release_gate_effectiveness,
        solution_blueprint,
        assignments=assignments,
        non_lms_product_count=len(non_lms_products),
        taxonomy_area_count=len(taxonomy_areas),
        blocked_assignment_count=blocked_assignment_count,
        tenant_safe=tenant_safe,
    )
    return EnterprisePatternReport(
        generated_at=report_date,
        expansion_status=expansion_status,
        release_gate_effectiveness_status=(
            release_gate_effectiveness.monitor_status
        ),
        release_gate_signal_count=release_gate_effectiveness.signal_count,
        release_gate_effective_signal_count=(
            release_gate_effectiveness.effective_signal_count
        ),
        blueprint_count=solution_blueprint.request_count,
        ready_blueprint_count=solution_blueprint.ready_count,
        non_lms_blueprint_count=solution_blueprint.non_lms_count,
        product_count=len(products),
        non_lms_product_count=len(non_lms_products),
        taxonomy_area_count=len(taxonomy_areas),
        target_module_count=solution_blueprint.target_module_count,
        executable_module_count=solution_blueprint.executable_module_count,
        evaluation_gate_count=sum(
            assignment.evaluation_gate_count for assignment in assignments
        ),
        assigned_use_case_count=sum(
            1 for assignment in assignments if assignment.expansion_ready
        ),
        blocked_assignment_count=blocked_assignment_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=enterprise_pattern_next_actions(expansion_status),
        assignments=assignments,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_report_from_reports"
] = build_release_gate_enterprise_pattern_report_from_reports


def build_enterprise_pattern_assignment(
    blueprint: UseCaseSolutionBlueprint,
    *,
    release_gate_effectiveness: ReleaseGateEffectivenessReport,
) -> EnterprisePatternAssignment:
    validation_errors = validate_enterprise_pattern_assignment(
        blueprint,
        release_gate_effectiveness=release_gate_effectiveness,
    )
    taxonomy_areas = tuple(
        dict.fromkeys(module.taxonomy_area for module in blueprint.target_modules)
    )
    return EnterprisePatternAssignment(
        assignment_id=f"{blueprint.request_id}-release-gate-pattern",
        request_id=blueprint.request_id,
        product=blueprint.product,
        use_case_id=blueprint.use_case_id,
        use_case_name=blueprint.use_case_name,
        is_non_lms=blueprint.is_non_lms,
        blueprint_status=blueprint.blueprint_status,
        target_module_count=blueprint.target_module_count,
        executable_module_count=blueprint.executable_module_count,
        evaluation_gate_count=blueprint.evaluation_gate_count,
        taxonomy_areas=taxonomy_areas,
        pattern_controls=PATTERN_CONTROLS,
        expansion_ready=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=(
            "platform/intake/reports/use-case-blueprints-v1.yaml",
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-"
            "policy-coverage-release-gate-effectiveness-v1.yaml",
            "platform/product/reports/ai-platform-product-readiness-v1.yaml",
        ),
    )


def validate_enterprise_pattern_assignment(
    blueprint: UseCaseSolutionBlueprint,
    *,
    release_gate_effectiveness: ReleaseGateEffectivenessReport,
) -> tuple[str, ...]:
    errors: list[str] = []
    if release_gate_effectiveness.monitor_status != EXPECTED_EFFECTIVENESS_STATUS:
        errors.append("release gate effectiveness must be monitored first")
    if blueprint.blueprint_status != EXPECTED_BLUEPRINT_STATUS:
        errors.append("solution blueprint must be ready for solution design")
    if not blueprint.target_module_count:
        errors.append("solution blueprint must target at least one module")
    if blueprint.executable_module_count != blueprint.target_module_count:
        errors.append("all target modules must be executable")
    if blueprint.evaluation_gate_count == 0:
        errors.append("solution blueprint must have evaluation gates")
    if not blueprint.workstreams:
        errors.append("solution blueprint must assign workstreams")
    return tuple(errors)


def derive_enterprise_pattern_expansion_status(
    release_gate_effectiveness: ReleaseGateEffectivenessReport,
    solution_blueprint: SolutionBlueprintReport,
    *,
    assignments: tuple[EnterprisePatternAssignment, ...],
    non_lms_product_count: int,
    taxonomy_area_count: int,
    blocked_assignment_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if release_gate_effectiveness.monitor_status != EXPECTED_EFFECTIVENESS_STATUS:
        return "blocked_by_release_gate_effectiveness"
    if not assignments:
        return "insufficient_enterprise_use_cases"
    if solution_blueprint.ready_count != solution_blueprint.request_count:
        return "blocked_by_solution_blueprint"
    if solution_blueprint.non_lms_count < MIN_NON_LMS_BLUEPRINT_COUNT:
        return "insufficient_non_lms_use_cases"
    if non_lms_product_count < MIN_NON_LMS_PRODUCT_COUNT:
        return "insufficient_enterprise_product_span"
    if taxonomy_area_count < MIN_TAXONOMY_AREA_COUNT:
        return "insufficient_taxonomy_span"
    if blocked_assignment_count:
        return "enterprise_pattern_gap_detected"
    return "enterprise_pattern_expanded"


def enterprise_pattern_next_actions(expansion_status: str) -> tuple[str, ...]:
    if expansion_status == "enterprise_pattern_expanded":
        return (MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION,)
    return (EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION,)


def count_raw_identifier_markers(
    assignments: tuple[EnterprisePatternAssignment, ...],
) -> int:
    payload = json.dumps(
        [assignment.to_snapshot_dict() for assignment in assignments],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    marker_count = sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)
    marker_count += len(OPENAI_KEY_PATTERN.findall(payload))
    tenant_identifier_count = sum(
        1
        for match in TENANT_IDENTIFIER_PATTERN.findall(payload)
        if not match.startswith(SAFE_TENANT_MARKERS)
    )
    return marker_count + tenant_identifier_count


def build_suppression_policy_coverage_release_gate_enterprise_pattern_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_suppression_policy_coverage_release_gate_enterprise_pattern_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_snapshot"
] = build_suppression_policy_coverage_release_gate_enterprise_pattern_snapshot


def write_suppression_policy_coverage_release_gate_enterprise_pattern_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_suppression_policy_coverage_release_gate_enterprise_pattern_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_snapshot"
] = write_suppression_policy_coverage_release_gate_enterprise_pattern_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
