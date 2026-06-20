from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

ENTERPRISE_ADOPTION_SLO_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo"
)
_ENTERPRISE_ADOPTION_SLO_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReport"
)
_ENTERPRISE_ADOPTION_SLO_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_report"
)
_ATTACH_ADOPTION_SLO_ACTION_ATTR = (
    "ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION"
)
enterprise_adoption_slo_module = import_module(ENTERPRISE_ADOPTION_SLO_MODULE)
EnterpriseAdoptionSloReport = getattr(
    enterprise_adoption_slo_module,
    _ENTERPRISE_ADOPTION_SLO_REPORT_ATTR,
)
build_enterprise_adoption_slo_report = getattr(
    enterprise_adoption_slo_module,
    _ENTERPRISE_ADOPTION_SLO_BUILDER_ATTR,
)
ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION = getattr(
    enterprise_adoption_slo_module,
    _ATTACH_ADOPTION_SLO_ACTION_ATTR,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-adoption-slo-release-governance-v1"
)
EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION = (
    "exercise_enterprise_release_gate_pattern_adoption_slo_release_governance_drill"
)
EXPECTED_SLO_STATUS = "adoption_slo_published"
TARGET_ADOPTION_PCT = 100
MIN_NON_LMS_BLUEPRINT_COUNT = 5
MIN_NON_LMS_PRODUCT_COUNT = 4
MIN_TAXONOMY_AREA_COUNT = 8
MIN_EVALUATION_GATE_COUNT = 30
MAX_RAW_IDENTIFIER_COUNT = 0
RELEASE_GOVERNANCE_REVIEW_CADENCE_DAYS = 30
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "sk-", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
ENTERPRISE_ADOPTION_SLO_REPORT_PATH = (
    "platform/operations/reports/product-readiness-freshness-response-slo-drift-"
    "suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml"
)
ENTERPRISE_ADOPTION_REPORT_PATH = (
    "platform/operations/reports/product-readiness-freshness-response-slo-drift-"
    "suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml"
)
ENTERPRISE_PATTERN_REPORT_PATH = (
    "platform/operations/reports/product-readiness-freshness-response-slo-drift-"
    "suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml"
)
PRODUCT_READINESS_REPORT_PATH = (
    "platform/product/reports/ai-platform-product-readiness-v1.yaml"
)
ADMIN_OPS_DASHBOARD_PATH = "platform/operations/reports/admin-ops-dashboard-v1.html"


@dataclass(frozen=True, slots=True)
class EnterpriseAdoptionSloReleaseGovernanceGate:
    gate_id: str
    gate_type: str
    owner_role: str
    target: str
    observed: str
    attached: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attached": self.attached,
            "evidenceRefs": list(self.evidence_refs),
            "gateId": self.gate_id,
            "gateType": self.gate_type,
            "observed": self.observed,
            "ownerRole": self.owner_role,
            "target": self.target,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "owner_role": self.owner_role,
            "target": self.target,
            "observed": self.observed,
            "attached": self.attached,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class EnterpriseAdoptionSloReleaseGovernanceReport:
    generated_at: str
    release_governance_status: str
    slo_status: str
    adoption_status: str
    enterprise_pattern_status: str
    adoption_pct: int
    target_adoption_pct: int
    objective_count: int
    met_objective_count: int
    failed_objective_count: int
    release_gate_count: int
    attached_release_gate_count: int
    failed_release_gate_count: int
    review_cadence_days: int
    non_lms_blueprint_count: int
    non_lms_product_count: int
    taxonomy_area_count: int
    evaluation_gate_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    gates: tuple[EnterpriseAdoptionSloReleaseGovernanceGate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adoptionPct": self.adoption_pct,
            "adoptionStatus": self.adoption_status,
            "attachedReleaseGateCount": self.attached_release_gate_count,
            "enterprisePatternStatus": self.enterprise_pattern_status,
            "evaluationGateCount": self.evaluation_gate_count,
            "failedObjectiveCount": self.failed_objective_count,
            "failedReleaseGateCount": self.failed_release_gate_count,
            "gates": [gate.to_dict() for gate in self.gates],
            "generatedAt": self.generated_at,
            "metObjectiveCount": self.met_objective_count,
            "nextActions": list(self.next_actions),
            "nonLmsBlueprintCount": self.non_lms_blueprint_count,
            "nonLmsProductCount": self.non_lms_product_count,
            "objectiveCount": self.objective_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "releaseGateCount": self.release_gate_count,
            "releaseGovernanceStatus": self.release_governance_status,
            "reviewCadenceDays": self.review_cadence_days,
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
                "release_governance_status": self.release_governance_status,
                "slo_status": self.slo_status,
                "adoption_status": self.adoption_status,
                "enterprise_pattern_status": self.enterprise_pattern_status,
                "adoption_pct": self.adoption_pct,
                "target_adoption_pct": self.target_adoption_pct,
                "objective_count": self.objective_count,
                "met_objective_count": self.met_objective_count,
                "failed_objective_count": self.failed_objective_count,
                "release_gate_count": self.release_gate_count,
                "attached_release_gate_count": self.attached_release_gate_count,
                "failed_release_gate_count": self.failed_release_gate_count,
                "review_cadence_days": self.review_cadence_days,
                "non_lms_blueprint_count": self.non_lms_blueprint_count,
                "non_lms_product_count": self.non_lms_product_count,
                "taxonomy_area_count": self.taxonomy_area_count,
                "evaluation_gate_count": self.evaluation_gate_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "target_adoption_pct": TARGET_ADOPTION_PCT,
                "min_non_lms_blueprint_count": MIN_NON_LMS_BLUEPRINT_COUNT,
                "min_non_lms_product_count": MIN_NON_LMS_PRODUCT_COUNT,
                "min_taxonomy_area_count": MIN_TAXONOMY_AREA_COUNT,
                "min_evaluation_gate_count": MIN_EVALUATION_GATE_COUNT,
                "max_raw_identifier_count": MAX_RAW_IDENTIFIER_COUNT,
                "release_governance_review_cadence_days": (
                    RELEASE_GOVERNANCE_REVIEW_CADENCE_DAYS
                ),
            },
            "action_queue": {
                "attached": [gate.gate_id for gate in self.gates if gate.attached],
                "blocked": [
                    gate.gate_id for gate in self.gates if not gate.attached
                ],
                "next_actions": list(self.next_actions),
            },
            "release_gates": [gate.to_snapshot_dict() for gate in self.gates],
        }


globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceGate"
] = EnterpriseAdoptionSloReleaseGovernanceGate
globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport"
] = EnterpriseAdoptionSloReleaseGovernanceReport


def build_enterprise_adoption_slo_release_governance_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    enterprise_adoption_slo: EnterpriseAdoptionSloReport | None = None,
) -> EnterpriseAdoptionSloReleaseGovernanceReport:
    adoption_slo_report = enterprise_adoption_slo or (
        build_enterprise_adoption_slo_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return build_enterprise_adoption_slo_release_governance_report_from_slo(
        adoption_slo_report,
        generated_at=generated_at,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_report"
] = build_enterprise_adoption_slo_release_governance_report


def build_enterprise_adoption_slo_release_governance_report_from_slo(
    adoption_slo: EnterpriseAdoptionSloReport,
    *,
    generated_at: str | None = None,
) -> EnterpriseAdoptionSloReleaseGovernanceReport:
    report_date = generated_at or adoption_slo.generated_at
    gates = build_release_gates(adoption_slo)
    raw_identifier_count = count_raw_identifier_markers(gates)
    tenant_safe = (
        adoption_slo.tenant_safe
        and adoption_slo.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_release_gate_count = sum(1 for gate in gates if not gate.attached)
    release_governance_status = derive_release_governance_status(
        adoption_slo,
        failed_release_gate_count=failed_release_gate_count,
        tenant_safe=tenant_safe,
    )
    return EnterpriseAdoptionSloReleaseGovernanceReport(
        generated_at=report_date,
        release_governance_status=release_governance_status,
        slo_status=adoption_slo.slo_status,
        adoption_status=adoption_slo.adoption_status,
        enterprise_pattern_status=adoption_slo.enterprise_pattern_status,
        adoption_pct=adoption_slo.adoption_pct,
        target_adoption_pct=adoption_slo.target_adoption_pct,
        objective_count=adoption_slo.objective_count,
        met_objective_count=adoption_slo.met_objective_count,
        failed_objective_count=adoption_slo.failed_objective_count,
        release_gate_count=len(gates),
        attached_release_gate_count=sum(1 for gate in gates if gate.attached),
        failed_release_gate_count=failed_release_gate_count,
        review_cadence_days=adoption_slo.review_cadence_days,
        non_lms_blueprint_count=adoption_slo.non_lms_blueprint_count,
        non_lms_product_count=adoption_slo.non_lms_product_count,
        taxonomy_area_count=adoption_slo.taxonomy_area_count,
        evaluation_gate_count=adoption_slo.evaluation_gate_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=release_governance_next_actions(release_governance_status),
        gates=gates,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_report_from_slo"
] = build_enterprise_adoption_slo_release_governance_report_from_slo


def build_release_gates(
    adoption_slo: EnterpriseAdoptionSloReport,
) -> tuple[EnterpriseAdoptionSloReleaseGovernanceGate, ...]:
    evidence_refs = (
        ENTERPRISE_ADOPTION_SLO_REPORT_PATH,
        ENTERPRISE_ADOPTION_REPORT_PATH,
        ENTERPRISE_PATTERN_REPORT_PATH,
        PRODUCT_READINESS_REPORT_PATH,
        ADMIN_OPS_DASHBOARD_PATH,
    )
    return (
        build_release_gate(
            gate_id="enterprise-adoption-slo-published-release-governance-gate",
            gate_type="slo_publication",
            owner_role="SA AI Platform + Admin/Ops",
            target=f"slo_status={EXPECTED_SLO_STATUS}",
            observed=f"slo_status={adoption_slo.slo_status}",
            attached=adoption_slo.slo_status == EXPECTED_SLO_STATUS,
            failure_message="enterprise adoption SLO must be published",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="enterprise-adoption-slo-objectives-release-governance-gate",
            gate_type="slo_objectives",
            owner_role="SA AI Platform + SA AI Engineer",
            target="met_objective_count == objective_count;failed_objective_count=0",
            observed=(
                f"met={adoption_slo.met_objective_count}/"
                f"{adoption_slo.objective_count};"
                f"failed={adoption_slo.failed_objective_count}"
            ),
            attached=(
                adoption_slo.met_objective_count == adoption_slo.objective_count
                and adoption_slo.failed_objective_count == 0
            ),
            failure_message="all enterprise adoption SLO objectives must be met",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="enterprise-adoption-slo-enterprise-span-release-governance-gate",
            gate_type="enterprise_span",
            owner_role="PO/BA + SA AI Platform",
            target=(
                f"non_lms_blueprint_count>={MIN_NON_LMS_BLUEPRINT_COUNT};"
                f"non_lms_product_count>={MIN_NON_LMS_PRODUCT_COUNT};"
                f"taxonomy_area_count>={MIN_TAXONOMY_AREA_COUNT};"
                f"evaluation_gate_count>={MIN_EVALUATION_GATE_COUNT}"
            ),
            observed=(
                f"non_lms_blueprint_count={adoption_slo.non_lms_blueprint_count};"
                f"non_lms_product_count={adoption_slo.non_lms_product_count};"
                f"taxonomy_area_count={adoption_slo.taxonomy_area_count};"
                f"evaluation_gate_count={adoption_slo.evaluation_gate_count}"
            ),
            attached=(
                adoption_slo.non_lms_blueprint_count
                >= MIN_NON_LMS_BLUEPRINT_COUNT
                and adoption_slo.non_lms_product_count >= MIN_NON_LMS_PRODUCT_COUNT
                and adoption_slo.taxonomy_area_count >= MIN_TAXONOMY_AREA_COUNT
                and adoption_slo.evaluation_gate_count >= MIN_EVALUATION_GATE_COUNT
            ),
            failure_message="enterprise adoption SLO release governance span is low",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="enterprise-adoption-slo-owner-cadence-release-governance-gate",
            gate_type="owner_cadence",
            owner_role="PO/BA + Admin/Ops",
            target=(
                f"target_adoption_pct>={TARGET_ADOPTION_PCT};"
                f"review_cadence_days<={RELEASE_GOVERNANCE_REVIEW_CADENCE_DAYS}"
            ),
            observed=(
                f"target_adoption_pct={adoption_slo.target_adoption_pct};"
                f"review_cadence_days={adoption_slo.review_cadence_days}"
            ),
            attached=(
                adoption_slo.target_adoption_pct >= TARGET_ADOPTION_PCT
                and adoption_slo.review_cadence_days
                <= RELEASE_GOVERNANCE_REVIEW_CADENCE_DAYS
            ),
            failure_message="enterprise adoption SLO needs governance cadence",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="enterprise-adoption-slo-tenant-safety-release-governance-gate",
            gate_type="tenant_safety",
            owner_role="Governance Reviewer",
            target="tenant_safe=true;raw_identifier_count=0",
            observed=(
                f"tenant_safe={str(adoption_slo.tenant_safe).lower()};"
                f"raw_identifier_count={adoption_slo.raw_identifier_count}"
            ),
            attached=(
                adoption_slo.tenant_safe
                and adoption_slo.raw_identifier_count == MAX_RAW_IDENTIFIER_COUNT
            ),
            failure_message="enterprise adoption SLO release governance must be tenant-safe",
            evidence_refs=evidence_refs,
        ),
    )


def build_release_gate(
    *,
    gate_id: str,
    gate_type: str,
    owner_role: str,
    target: str,
    observed: str,
    attached: bool,
    failure_message: str,
    evidence_refs: tuple[str, ...],
) -> EnterpriseAdoptionSloReleaseGovernanceGate:
    return EnterpriseAdoptionSloReleaseGovernanceGate(
        gate_id=gate_id,
        gate_type=gate_type,
        owner_role=owner_role,
        target=target,
        observed=observed,
        attached=attached,
        validation_errors=() if attached else (failure_message,),
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def derive_release_governance_status(
    adoption_slo: EnterpriseAdoptionSloReport,
    *,
    failed_release_gate_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if adoption_slo.slo_status != EXPECTED_SLO_STATUS:
        return "blocked_by_unpublished_adoption_slo"
    if failed_release_gate_count:
        return "enterprise_adoption_slo_release_governance_attachment_incomplete"
    return "enterprise_adoption_slo_release_governance_attached"


def release_governance_next_actions(
    release_governance_status: str,
) -> tuple[str, ...]:
    if (
        release_governance_status
        == "enterprise_adoption_slo_release_governance_attached"
    ):
        return (
            EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION,
        )
    return (
        ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION,
    )


def count_raw_identifier_markers(
    gates: tuple[EnterpriseAdoptionSloReleaseGovernanceGate, ...],
) -> int:
    payload = json.dumps(
        [gate.to_snapshot_dict() for gate in gates],
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


def build_enterprise_adoption_slo_release_governance_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_enterprise_adoption_slo_release_governance_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_snapshot"
] = build_enterprise_adoption_slo_release_governance_snapshot


def write_enterprise_adoption_slo_release_governance_snapshot(
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
            build_enterprise_adoption_slo_release_governance_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_snapshot"
] = write_enterprise_adoption_slo_release_governance_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
