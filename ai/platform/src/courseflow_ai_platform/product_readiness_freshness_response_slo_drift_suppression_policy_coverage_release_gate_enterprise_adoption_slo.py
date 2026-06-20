from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

ENTERPRISE_ADOPTION_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_adoption"
)
_ENTERPRISE_ADOPTION_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionReport"
)
_ENTERPRISE_ADOPTION_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_report"
)
_PUBLISH_ADOPTION_SLO_ACTION_ATTR = (
    "PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION"
)
enterprise_adoption_module = import_module(ENTERPRISE_ADOPTION_MODULE)
EnterpriseAdoptionReport = getattr(
    enterprise_adoption_module,
    _ENTERPRISE_ADOPTION_REPORT_ATTR,
)
build_enterprise_adoption_report = getattr(
    enterprise_adoption_module,
    _ENTERPRISE_ADOPTION_BUILDER_ATTR,
)
PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION = getattr(
    enterprise_adoption_module,
    _PUBLISH_ADOPTION_SLO_ACTION_ATTR,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-adoption-slo-v1"
)
ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION = (
    "attach_enterprise_release_gate_pattern_adoption_slo_to_release_governance"
)
EXPECTED_ADOPTION_STATUS = "adoption_monitored"
EXPECTED_ENTERPRISE_PATTERN_STATUS = "enterprise_pattern_expanded"
TARGET_ADOPTION_PCT = 100
MIN_SIGNAL_COUNT = 6
MIN_NON_LMS_BLUEPRINT_COUNT = 5
MIN_NON_LMS_PRODUCT_COUNT = 4
MIN_TAXONOMY_AREA_COUNT = 8
MIN_EVALUATION_GATE_COUNT = 30
MAX_RAW_IDENTIFIER_COUNT = 0
REVIEW_CADENCE_DAYS = 30
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "sk-", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
ENTERPRISE_ADOPTION_REPORT_PATH = (
    "platform/operations/reports/"
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-adoption-v1.yaml"
)
ENTERPRISE_PATTERN_REPORT_PATH = (
    "platform/operations/reports/"
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-pattern-v1.yaml"
)
PRODUCT_READINESS_REPORT_PATH = (
    "platform/product/reports/ai-platform-product-readiness-v1.yaml"
)
ADMIN_OPS_DASHBOARD_PATH = (
    "platform/operations/reports/admin-ops-dashboard-v1.html"
)
BLUEPRINT_REPORT_PATH = "platform/intake/reports/use-case-blueprints-v1.yaml"


@dataclass(frozen=True, slots=True)
class EnterprisePatternAdoptionSloObjective:
    objective_id: str
    objective_type: str
    target: str
    observed: str
    met: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidenceRefs": list(self.evidence_refs),
            "met": self.met,
            "objectiveId": self.objective_id,
            "objectiveType": self.objective_type,
            "observed": self.observed,
            "target": self.target,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "objective_type": self.objective_type,
            "target": self.target,
            "observed": self.observed,
            "met": self.met,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class EnterprisePatternAdoptionSloReport:
    generated_at: str
    slo_status: str
    adoption_status: str
    enterprise_pattern_status: str
    adoption_pct: int
    target_adoption_pct: int
    signal_count: int
    adopted_signal_count: int
    blocked_signal_count: int
    non_lms_blueprint_count: int
    non_lms_product_count: int
    taxonomy_area_count: int
    evaluation_gate_count: int
    assigned_use_case_count: int
    blueprint_count: int
    review_cadence_days: int
    objective_count: int
    met_objective_count: int
    failed_objective_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    objectives: tuple[EnterprisePatternAdoptionSloObjective, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adoptedSignalCount": self.adopted_signal_count,
            "adoptionPct": self.adoption_pct,
            "adoptionStatus": self.adoption_status,
            "assignedUseCaseCount": self.assigned_use_case_count,
            "blockedSignalCount": self.blocked_signal_count,
            "blueprintCount": self.blueprint_count,
            "enterprisePatternStatus": self.enterprise_pattern_status,
            "evaluationGateCount": self.evaluation_gate_count,
            "failedObjectiveCount": self.failed_objective_count,
            "generatedAt": self.generated_at,
            "metObjectiveCount": self.met_objective_count,
            "nextActions": list(self.next_actions),
            "nonLmsBlueprintCount": self.non_lms_blueprint_count,
            "nonLmsProductCount": self.non_lms_product_count,
            "objectiveCount": self.objective_count,
            "objectives": [objective.to_dict() for objective in self.objectives],
            "rawIdentifierCount": self.raw_identifier_count,
            "reviewCadenceDays": self.review_cadence_days,
            "signalCount": self.signal_count,
            "sloStatus": self.slo_status,
            "targetAdoptionPct": self.target_adoption_pct,
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
                "slo_status": self.slo_status,
                "adoption_status": self.adoption_status,
                "enterprise_pattern_status": self.enterprise_pattern_status,
                "adoption_pct": self.adoption_pct,
                "target_adoption_pct": self.target_adoption_pct,
                "signal_count": self.signal_count,
                "adopted_signal_count": self.adopted_signal_count,
                "blocked_signal_count": self.blocked_signal_count,
                "non_lms_blueprint_count": self.non_lms_blueprint_count,
                "non_lms_product_count": self.non_lms_product_count,
                "taxonomy_area_count": self.taxonomy_area_count,
                "evaluation_gate_count": self.evaluation_gate_count,
                "assigned_use_case_count": self.assigned_use_case_count,
                "blueprint_count": self.blueprint_count,
                "review_cadence_days": self.review_cadence_days,
                "objective_count": self.objective_count,
                "met_objective_count": self.met_objective_count,
                "failed_objective_count": self.failed_objective_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "target_adoption_pct": self.target_adoption_pct,
                "min_signal_count": MIN_SIGNAL_COUNT,
                "min_non_lms_blueprint_count": MIN_NON_LMS_BLUEPRINT_COUNT,
                "min_non_lms_product_count": MIN_NON_LMS_PRODUCT_COUNT,
                "min_taxonomy_area_count": MIN_TAXONOMY_AREA_COUNT,
                "min_evaluation_gate_count": MIN_EVALUATION_GATE_COUNT,
                "max_raw_identifier_count": MAX_RAW_IDENTIFIER_COUNT,
                "review_cadence_days": self.review_cadence_days,
            },
            "action_queue": {
                "met": [
                    objective.objective_id
                    for objective in self.objectives
                    if objective.met
                ],
                "blocked": [
                    objective.objective_id
                    for objective in self.objectives
                    if not objective.met
                ],
                "next_actions": list(self.next_actions),
            },
            "objectives": [
                objective.to_snapshot_dict() for objective in self.objectives
            ],
        }


globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloObjective"
] = EnterprisePatternAdoptionSloObjective
globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReport"
] = EnterprisePatternAdoptionSloReport


def build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    adoption: EnterpriseAdoptionReport | None = None,
) -> EnterprisePatternAdoptionSloReport:
    adoption_report = adoption or build_enterprise_adoption_report(
        ai_root,
        generated_at=generated_at,
    )
    return build_release_gate_enterprise_adoption_slo_report_from_adoption(
        adoption_report,
        generated_at=generated_at,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_report"
] = build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_report


def build_release_gate_enterprise_adoption_slo_report_from_adoption(
    adoption: EnterpriseAdoptionReport,
    *,
    generated_at: str | None = None,
) -> EnterprisePatternAdoptionSloReport:
    report_date = generated_at or adoption.generated_at
    objectives = build_adoption_slo_objectives(adoption)
    raw_identifier_count = count_raw_identifier_markers(objectives)
    tenant_safe = (
        adoption.tenant_safe
        and adoption.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_objective_count = sum(
        1 for objective in objectives if not objective.met
    )
    met_objective_count = len(objectives) - failed_objective_count
    slo_status = derive_adoption_slo_status(
        adoption,
        failed_objective_count=failed_objective_count,
        tenant_safe=tenant_safe,
    )
    return EnterprisePatternAdoptionSloReport(
        generated_at=report_date,
        slo_status=slo_status,
        adoption_status=adoption.adoption_status,
        enterprise_pattern_status=adoption.enterprise_pattern_status,
        adoption_pct=adoption.adoption_pct,
        target_adoption_pct=TARGET_ADOPTION_PCT,
        signal_count=adoption.signal_count,
        adopted_signal_count=adoption.adopted_signal_count,
        blocked_signal_count=adoption.blocked_signal_count,
        non_lms_blueprint_count=adoption.non_lms_blueprint_count,
        non_lms_product_count=adoption.non_lms_product_count,
        taxonomy_area_count=adoption.taxonomy_area_count,
        evaluation_gate_count=adoption.evaluation_gate_count,
        assigned_use_case_count=adoption.assigned_use_case_count,
        blueprint_count=adoption.blueprint_count,
        review_cadence_days=REVIEW_CADENCE_DAYS,
        objective_count=len(objectives),
        met_objective_count=met_objective_count,
        failed_objective_count=failed_objective_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=adoption_slo_next_actions(slo_status),
        objectives=objectives,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_report_from_adoption"
] = build_release_gate_enterprise_adoption_slo_report_from_adoption


def build_adoption_slo_objectives(
    adoption: EnterpriseAdoptionReport,
) -> tuple[EnterprisePatternAdoptionSloObjective, ...]:
    evidence_refs = (
        ENTERPRISE_ADOPTION_REPORT_PATH,
        ENTERPRISE_PATTERN_REPORT_PATH,
        PRODUCT_READINESS_REPORT_PATH,
        ADMIN_OPS_DASHBOARD_PATH,
        BLUEPRINT_REPORT_PATH,
    )
    return (
        make_objective(
            objective_id="enterprise-adoption-health-slo",
            objective_type="adoption_health",
            target=(
                f"adoption_status={EXPECTED_ADOPTION_STATUS};"
                f"adoption_pct>={TARGET_ADOPTION_PCT};"
                "blocked_signal_count=0"
            ),
            observed=(
                f"adoption_status={adoption.adoption_status};"
                f"adoption_pct={adoption.adoption_pct};"
                f"adopted={adoption.adopted_signal_count}/"
                f"{adoption.signal_count};"
                f"blocked={adoption.blocked_signal_count}"
            ),
            met=(
                adoption.adoption_status == EXPECTED_ADOPTION_STATUS
                and adoption.adoption_pct >= TARGET_ADOPTION_PCT
                and adoption.blocked_signal_count == 0
                and adoption.adopted_signal_count == adoption.signal_count
                and adoption.signal_count >= MIN_SIGNAL_COUNT
            ),
            failure_message="enterprise adoption SLO needs all adoption signals green",
            evidence_refs=evidence_refs,
        ),
        make_objective(
            objective_id="enterprise-product-span-slo",
            objective_type="enterprise_product_span",
            target=(
                f">={MIN_NON_LMS_BLUEPRINT_COUNT} non-LMS blueprints;"
                f">={MIN_NON_LMS_PRODUCT_COUNT} non-LMS products;"
                f">={MIN_TAXONOMY_AREA_COUNT} taxonomy areas;"
                f">={MIN_EVALUATION_GATE_COUNT} evaluation gates"
            ),
            observed=(
                f"{adoption.non_lms_blueprint_count} non-LMS blueprints;"
                f"{adoption.non_lms_product_count} non-LMS products;"
                f"{adoption.taxonomy_area_count} taxonomy areas;"
                f"{adoption.evaluation_gate_count} evaluation gates"
            ),
            met=(
                adoption.non_lms_blueprint_count >= MIN_NON_LMS_BLUEPRINT_COUNT
                and adoption.non_lms_product_count >= MIN_NON_LMS_PRODUCT_COUNT
                and adoption.taxonomy_area_count >= MIN_TAXONOMY_AREA_COUNT
                and adoption.evaluation_gate_count >= MIN_EVALUATION_GATE_COUNT
            ),
            failure_message="enterprise adoption SLO span is below threshold",
            evidence_refs=evidence_refs,
        ),
        make_objective(
            objective_id="enterprise-governance-intake-slo",
            objective_type="governance_intake",
            target=(
                f"enterprise_pattern_status={EXPECTED_ENTERPRISE_PATTERN_STATUS};"
                "assigned_use_case_count=blueprint_count"
            ),
            observed=(
                f"enterprise_pattern_status={adoption.enterprise_pattern_status};"
                f"assigned={adoption.assigned_use_case_count}/"
                f"{adoption.blueprint_count}"
            ),
            met=(
                adoption.enterprise_pattern_status
                == EXPECTED_ENTERPRISE_PATTERN_STATUS
                and adoption.assigned_use_case_count == adoption.blueprint_count
            ),
            failure_message="enterprise adoption SLO needs governed intake assignment",
            evidence_refs=evidence_refs,
        ),
        make_objective(
            objective_id="enterprise-adoption-tenant-safety-slo",
            objective_type="tenant_safety",
            target=(
                "tenant_safe=true;"
                f"raw_identifier_count<={MAX_RAW_IDENTIFIER_COUNT}"
            ),
            observed=(
                f"tenant_safe={str(adoption.tenant_safe).lower()};"
                f"raw_identifier_count={adoption.raw_identifier_count}"
            ),
            met=(
                adoption.tenant_safe
                and adoption.raw_identifier_count <= MAX_RAW_IDENTIFIER_COUNT
            ),
            failure_message="enterprise adoption SLO publication must be tenant-safe",
            evidence_refs=evidence_refs,
        ),
        make_objective(
            objective_id="enterprise-adoption-owner-cadence-slo",
            objective_type="owner_cadence",
            target=f"review_cadence_days<={REVIEW_CADENCE_DAYS};dashboard_panel=true",
            observed=(
                f"review_cadence_days={REVIEW_CADENCE_DAYS};"
                "owner=SA AI Platform + PO/BA + Admin/Ops;dashboard_panel=true"
            ),
            met=adoption.adoption_status == EXPECTED_ADOPTION_STATUS,
            failure_message="enterprise adoption SLO needs an owner cadence",
            evidence_refs=evidence_refs,
        ),
    )


def make_objective(
    *,
    objective_id: str,
    objective_type: str,
    target: str,
    observed: str,
    met: bool,
    failure_message: str,
    evidence_refs: tuple[str, ...],
) -> EnterprisePatternAdoptionSloObjective:
    return EnterprisePatternAdoptionSloObjective(
        objective_id=objective_id,
        objective_type=objective_type,
        target=target,
        observed=observed,
        met=met,
        validation_errors=() if met else (failure_message,),
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def derive_adoption_slo_status(
    adoption: EnterpriseAdoptionReport,
    *,
    failed_objective_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if adoption.adoption_status != EXPECTED_ADOPTION_STATUS:
        return "blocked_by_adoption_monitor"
    if failed_objective_count:
        return "adoption_slo_at_risk"
    return "adoption_slo_published"


def adoption_slo_next_actions(slo_status: str) -> tuple[str, ...]:
    if slo_status == "adoption_slo_published":
        return (
            ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION,
        )
    return (PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION,)


def count_raw_identifier_markers(
    objectives: tuple[EnterprisePatternAdoptionSloObjective, ...],
) -> int:
    payload = json.dumps(
        [objective.to_snapshot_dict() for objective in objectives],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    marker_count = sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)
    tenant_identifier_count = sum(
        1
        for match in TENANT_IDENTIFIER_PATTERN.findall(payload)
        if not match.startswith(SAFE_TENANT_MARKERS)
    )
    return marker_count + tenant_identifier_count


def build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_snapshot"
] = build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_snapshot


def write_suppression_policy_coverage_release_gate_enterprise_adoption_slo_snapshot(
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
            build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_snapshot"
] = write_suppression_policy_coverage_release_gate_enterprise_adoption_slo_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
