from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo import (
    ATTACH_SUPPRESSION_POLICY_COVERAGE_SLO_TO_RELEASE_GOVERNANCE_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-"
    "suppression-policy-coverage-release-governance-v1"
)
EXERCISE_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_DRILL_ACTION = (
    "exercise_product_readiness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_drill"
)
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "sk-", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
MAX_RAW_IDENTIFIER_COUNT = 0
RELEASE_GATE_REVIEW_CADENCE_DAYS = 30


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGate:
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
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernanceReport:
    generated_at: str
    release_governance_status: str
    slo_status: str
    coverage_status: str
    coverage_pct: int
    objective_count: int
    met_objective_count: int
    failed_objective_count: int
    release_gate_count: int
    attached_release_gate_count: int
    failed_release_gate_count: int
    review_cadence_days: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    gates: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGate,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachedReleaseGateCount": self.attached_release_gate_count,
            "coveragePct": self.coverage_pct,
            "coverageStatus": self.coverage_status,
            "failedObjectiveCount": self.failed_objective_count,
            "failedReleaseGateCount": self.failed_release_gate_count,
            "gates": [gate.to_dict() for gate in self.gates],
            "generatedAt": self.generated_at,
            "metObjectiveCount": self.met_objective_count,
            "nextActions": list(self.next_actions),
            "objectiveCount": self.objective_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "releaseGateCount": self.release_gate_count,
            "releaseGovernanceStatus": self.release_governance_status,
            "reviewCadenceDays": self.review_cadence_days,
            "sloStatus": self.slo_status,
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
                "coverage_status": self.coverage_status,
                "coverage_pct": self.coverage_pct,
                "objective_count": self.objective_count,
                "met_objective_count": self.met_objective_count,
                "failed_objective_count": self.failed_objective_count,
                "release_gate_count": self.release_gate_count,
                "attached_release_gate_count": self.attached_release_gate_count,
                "failed_release_gate_count": self.failed_release_gate_count,
                "review_cadence_days": self.review_cadence_days,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "max_raw_identifier_count": MAX_RAW_IDENTIFIER_COUNT,
                "release_gate_review_cadence_days": (
                    RELEASE_GATE_REVIEW_CADENCE_DAYS
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


def build_suppression_policy_coverage_release_governance_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    coverage_slo: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
        | None
    ) = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernanceReport:
    coverage_slo_report = coverage_slo or (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return build_suppression_policy_coverage_release_governance_report_from_slo(
        coverage_slo_report,
        generated_at=generated_at,
    )


def build_suppression_policy_coverage_release_governance_report_from_slo(
    coverage_slo: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
    ),
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernanceReport:
    report_date = generated_at or coverage_slo.generated_at
    gates = build_release_gates(coverage_slo)
    raw_identifier_count = count_raw_identifier_markers(gates)
    tenant_safe = (
        coverage_slo.tenant_safe
        and coverage_slo.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_release_gate_count = sum(1 for gate in gates if not gate.attached)
    release_governance_status = derive_release_governance_status(
        coverage_slo,
        failed_release_gate_count=failed_release_gate_count,
        tenant_safe=tenant_safe,
    )
    report_type = (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernanceReport
    )
    return report_type(
        generated_at=report_date,
        release_governance_status=release_governance_status,
        slo_status=coverage_slo.slo_status,
        coverage_status=coverage_slo.coverage_status,
        coverage_pct=coverage_slo.coverage_pct,
        objective_count=coverage_slo.objective_count,
        met_objective_count=coverage_slo.met_objective_count,
        failed_objective_count=coverage_slo.failed_objective_count,
        release_gate_count=len(gates),
        attached_release_gate_count=sum(1 for gate in gates if gate.attached),
        failed_release_gate_count=failed_release_gate_count,
        review_cadence_days=RELEASE_GATE_REVIEW_CADENCE_DAYS,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=release_governance_next_actions(release_governance_status),
        gates=gates,
    )


def build_release_gates(
    coverage_slo: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
    ),
) -> tuple[
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGate,
    ...,
]:
    evidence_refs = (
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml",
        "platform/product/reports/ai-platform-product-readiness-v1.yaml",
        "platform/operations/reports/admin-ops-dashboard-v1.html",
    )
    return (
        build_release_gate(
            gate_id="coverage-slo-published-release-gate",
            gate_type="slo_publication",
            owner_role="SA AI Platform + Admin/Ops",
            target="slo_status=coverage_slo_published",
            observed=f"slo_status={coverage_slo.slo_status}",
            attached=coverage_slo.slo_status == "coverage_slo_published",
            failure_message="coverage SLO must be published before release gating",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="coverage-slo-objectives-release-gate",
            gate_type="slo_objectives",
            owner_role="SA AI Platform + SA AI Engineer",
            target="met_objective_count == objective_count;failed_objective_count=0",
            observed=(
                f"met={coverage_slo.met_objective_count}/"
                f"{coverage_slo.objective_count};"
                f"failed={coverage_slo.failed_objective_count}"
            ),
            attached=(
                coverage_slo.met_objective_count == coverage_slo.objective_count
                and coverage_slo.failed_objective_count == 0
            ),
            failure_message="all coverage SLO objectives must be met",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="coverage-slo-dashboard-release-gate",
            gate_type="dashboard_visibility",
            owner_role="Admin/Ops",
            target="dashboard_panel=true;readiness_gate=true",
            observed=(
                "dashboard_panel=true;"
                "readiness_gate=product_readiness_freshness_response_slo_drift_"
                "suppression_policy_coverage_slo_published"
            ),
            attached=coverage_slo.slo_status == "coverage_slo_published",
            failure_message="coverage SLO must be visible in dashboard and readiness",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="coverage-slo-owner-cadence-release-gate",
            gate_type="owner_cadence",
            owner_role="PO/BA + Admin/Ops",
            target=f"review_cadence_days<={RELEASE_GATE_REVIEW_CADENCE_DAYS}",
            observed=f"review_cadence_days={coverage_slo.review_cadence_days}",
            attached=coverage_slo.review_cadence_days
            <= RELEASE_GATE_REVIEW_CADENCE_DAYS,
            failure_message="coverage SLO release gate needs review cadence",
            evidence_refs=evidence_refs,
        ),
        build_release_gate(
            gate_id="coverage-slo-tenant-safety-release-gate",
            gate_type="tenant_safety",
            owner_role="Governance Reviewer",
            target="tenant_safe=true;raw_identifier_count=0",
            observed=(
                f"tenant_safe={str(coverage_slo.tenant_safe).lower()};"
                f"raw_identifier_count={coverage_slo.raw_identifier_count}"
            ),
            attached=(
                coverage_slo.tenant_safe
                and coverage_slo.raw_identifier_count == MAX_RAW_IDENTIFIER_COUNT
            ),
            failure_message="coverage SLO release governance must be tenant-safe",
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
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGate:
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGate(
        gate_id=gate_id,
        gate_type=gate_type,
        owner_role=owner_role,
        target=target,
        observed=observed,
        attached=attached,
        validation_errors=() if attached else (failure_message,),
        evidence_refs=evidence_refs,
    )


def derive_release_governance_status(
    coverage_slo: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
    ),
    *,
    failed_release_gate_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if coverage_slo.slo_status != "coverage_slo_published":
        return "blocked_by_unpublished_slo"
    if failed_release_gate_count:
        return "release_governance_attachment_incomplete"
    return "release_governance_attached"


def release_governance_next_actions(
    release_governance_status: str,
) -> tuple[str, ...]:
    if release_governance_status == "release_governance_attached":
        return (EXERCISE_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_DRILL_ACTION,)
    return (ATTACH_SUPPRESSION_POLICY_COVERAGE_SLO_TO_RELEASE_GOVERNANCE_ACTION,)


def count_raw_identifier_markers(
    gates: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGate,
        ...,
    ],
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


globals()[
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance_report"
] = build_suppression_policy_coverage_release_governance_report


def build_suppression_policy_coverage_release_governance_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_suppression_policy_coverage_release_governance_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance_snapshot"
] = build_suppression_policy_coverage_release_governance_snapshot


def write_suppression_policy_coverage_release_governance_snapshot(
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
            build_suppression_policy_coverage_release_governance_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance_snapshot"
] = write_suppression_policy_coverage_release_governance_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
