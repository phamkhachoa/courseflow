from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

RELEASE_GOVERNANCE_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance"
)
_RELEASE_GOVERNANCE_GATE_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceGate"
)
_RELEASE_GOVERNANCE_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport"
)
_RELEASE_GOVERNANCE_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_report"
)
_RELEASE_GOVERNANCE_DRILL_ACTION_ATTR = (
    "EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_"
    "DRILL_ACTION"
)
release_governance_module = import_module(RELEASE_GOVERNANCE_MODULE)
EnterpriseAdoptionSloReleaseGovernanceGate = getattr(
    release_governance_module,
    _RELEASE_GOVERNANCE_GATE_ATTR,
)
EnterpriseAdoptionSloReleaseGovernanceReport = getattr(
    release_governance_module,
    _RELEASE_GOVERNANCE_REPORT_ATTR,
)
build_enterprise_adoption_slo_release_governance_report = getattr(
    release_governance_module,
    _RELEASE_GOVERNANCE_BUILDER_ATTR,
)
EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION = getattr(
    release_governance_module,
    _RELEASE_GOVERNANCE_DRILL_ACTION_ATTR,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1"
)
MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_EFFECTIVENESS_ACTION = (
    "monitor_enterprise_release_gate_pattern_adoption_slo_release_governance_"
    "effectiveness"
)
EXPECTED_RELEASE_GOVERNANCE_STATUS = (
    "enterprise_adoption_slo_release_governance_attached"
)
EXPECTED_DRILL_OUTCOME = "enterprise_adoption_slo_release_governance_gate_holds"
FAILED_DRILL_OUTCOME = "enterprise_adoption_slo_release_governance_gap_detected"
MIN_EVIDENCE_REF_COUNT = 5
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "sk-", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")


@dataclass(frozen=True, slots=True)
class EnterpriseAdoptionSloReleaseGovernanceDrillScenario:
    drill_id: str
    gate_id: str
    gate_type: str
    owner_role: str
    drill_case: str
    expected_release_governance_status: str
    observed_release_governance_status: str
    expected_gate_attached: bool
    observed_gate_attached: bool
    expected_validation_error_count: int
    observed_validation_error_count: int
    expected_evidence_ref_count: int
    observed_evidence_ref_count: int
    expected_outcome: str
    observed_outcome: str
    passed: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "drillCase": self.drill_case,
            "drillId": self.drill_id,
            "evidenceRefs": list(self.evidence_refs),
            "expectedEvidenceRefCount": self.expected_evidence_ref_count,
            "expectedGateAttached": self.expected_gate_attached,
            "expectedOutcome": self.expected_outcome,
            "expectedReleaseGovernanceStatus": (
                self.expected_release_governance_status
            ),
            "expectedValidationErrorCount": (
                self.expected_validation_error_count
            ),
            "gateId": self.gate_id,
            "gateType": self.gate_type,
            "observedEvidenceRefCount": self.observed_evidence_ref_count,
            "observedGateAttached": self.observed_gate_attached,
            "observedOutcome": self.observed_outcome,
            "observedReleaseGovernanceStatus": (
                self.observed_release_governance_status
            ),
            "observedValidationErrorCount": (
                self.observed_validation_error_count
            ),
            "ownerRole": self.owner_role,
            "passed": self.passed,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "drill_id": self.drill_id,
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "owner_role": self.owner_role,
            "drill_case": self.drill_case,
            "expected_release_governance_status": (
                self.expected_release_governance_status
            ),
            "observed_release_governance_status": (
                self.observed_release_governance_status
            ),
            "expected_gate_attached": self.expected_gate_attached,
            "observed_gate_attached": self.observed_gate_attached,
            "expected_validation_error_count": (
                self.expected_validation_error_count
            ),
            "observed_validation_error_count": (
                self.observed_validation_error_count
            ),
            "expected_evidence_ref_count": self.expected_evidence_ref_count,
            "observed_evidence_ref_count": self.observed_evidence_ref_count,
            "expected_outcome": self.expected_outcome,
            "observed_outcome": self.observed_outcome,
            "passed": self.passed,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class EnterpriseAdoptionSloReleaseGovernanceDrillReport:
    generated_at: str
    drill_status: str
    release_governance_status: str
    release_gate_count: int
    attached_release_gate_count: int
    failed_release_gate_count: int
    scenario_count: int
    passed_count: int
    failed_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    scenarios: tuple[EnterpriseAdoptionSloReleaseGovernanceDrillScenario, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachedReleaseGateCount": self.attached_release_gate_count,
            "drillStatus": self.drill_status,
            "failedCount": self.failed_count,
            "failedReleaseGateCount": self.failed_release_gate_count,
            "generatedAt": self.generated_at,
            "nextActions": list(self.next_actions),
            "passedCount": self.passed_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "releaseGateCount": self.release_gate_count,
            "releaseGovernanceStatus": self.release_governance_status,
            "scenarioCount": self.scenario_count,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "drill_status": self.drill_status,
                "release_governance_status": self.release_governance_status,
                "release_gate_count": self.release_gate_count,
                "attached_release_gate_count": self.attached_release_gate_count,
                "failed_release_gate_count": self.failed_release_gate_count,
                "scenario_count": self.scenario_count,
                "passed_count": self.passed_count,
                "failed_count": self.failed_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "min_evidence_ref_count": MIN_EVIDENCE_REF_COUNT,
            },
            "action_queue": {
                "passed": [
                    scenario.drill_id
                    for scenario in self.scenarios
                    if scenario.passed
                ],
                "blocked": [
                    scenario.drill_id
                    for scenario in self.scenarios
                    if not scenario.passed
                ],
                "next_actions": list(self.next_actions),
            },
            "scenarios": [
                scenario.to_snapshot_dict() for scenario in self.scenarios
            ],
        }


globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillScenario"
] = EnterpriseAdoptionSloReleaseGovernanceDrillScenario
globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport"
] = EnterpriseAdoptionSloReleaseGovernanceDrillReport


def build_enterprise_adoption_slo_release_governance_drill_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    release_governance: EnterpriseAdoptionSloReleaseGovernanceReport | None = None,
) -> EnterpriseAdoptionSloReleaseGovernanceDrillReport:
    governance = release_governance or (
        build_enterprise_adoption_slo_release_governance_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return build_enterprise_adoption_slo_release_governance_drill_report_from_governance(
        governance,
        generated_at=generated_at,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report"
] = build_enterprise_adoption_slo_release_governance_drill_report


def build_enterprise_adoption_slo_release_governance_drill_report_from_governance(
    release_governance: EnterpriseAdoptionSloReleaseGovernanceReport,
    *,
    generated_at: str | None = None,
) -> EnterpriseAdoptionSloReleaseGovernanceDrillReport:
    report_date = generated_at or release_governance.generated_at
    scenarios = tuple(
        build_release_governance_drill_scenario(
            gate,
            release_governance_status=(
                release_governance.release_governance_status
            ),
        )
        for gate in release_governance.gates
    )
    raw_identifier_count = count_raw_identifier_markers(scenarios)
    tenant_safe = (
        release_governance.tenant_safe
        and release_governance.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_count = sum(1 for scenario in scenarios if not scenario.passed)
    drill_status = derive_drill_status(
        release_governance,
        scenario_count=len(scenarios),
        failed_count=failed_count,
        tenant_safe=tenant_safe,
    )
    return EnterpriseAdoptionSloReleaseGovernanceDrillReport(
        generated_at=report_date,
        drill_status=drill_status,
        release_governance_status=release_governance.release_governance_status,
        release_gate_count=release_governance.release_gate_count,
        attached_release_gate_count=(
            release_governance.attached_release_gate_count
        ),
        failed_release_gate_count=release_governance.failed_release_gate_count,
        scenario_count=len(scenarios),
        passed_count=sum(1 for scenario in scenarios if scenario.passed),
        failed_count=failed_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=drill_next_actions(drill_status),
        scenarios=scenarios,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_"
    "report_from_governance"
] = build_enterprise_adoption_slo_release_governance_drill_report_from_governance


def build_release_governance_drill_scenario(
    gate: EnterpriseAdoptionSloReleaseGovernanceGate,
    *,
    release_governance_status: str,
) -> EnterpriseAdoptionSloReleaseGovernanceDrillScenario:
    validation_errors = validate_release_governance_gate_for_drill(
        gate,
        release_governance_status=release_governance_status,
    )
    observed_outcome = (
        EXPECTED_DRILL_OUTCOME if not validation_errors else FAILED_DRILL_OUTCOME
    )
    return EnterpriseAdoptionSloReleaseGovernanceDrillScenario(
        drill_id=f"{gate.gate_id}-drill",
        gate_id=gate.gate_id,
        gate_type=gate.gate_type,
        owner_role=gate.owner_role,
        drill_case=f"{gate.gate_type}_release_governance_replay",
        expected_release_governance_status=EXPECTED_RELEASE_GOVERNANCE_STATUS,
        observed_release_governance_status=release_governance_status,
        expected_gate_attached=True,
        observed_gate_attached=gate.attached,
        expected_validation_error_count=0,
        observed_validation_error_count=len(gate.validation_errors),
        expected_evidence_ref_count=MIN_EVIDENCE_REF_COUNT,
        observed_evidence_ref_count=len(gate.evidence_refs),
        expected_outcome=EXPECTED_DRILL_OUTCOME,
        observed_outcome=observed_outcome,
        passed=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=gate.evidence_refs,
    )


def validate_release_governance_gate_for_drill(
    gate: EnterpriseAdoptionSloReleaseGovernanceGate,
    *,
    release_governance_status: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if release_governance_status != EXPECTED_RELEASE_GOVERNANCE_STATUS:
        errors.append(
            "enterprise adoption SLO release governance drill requires "
            "attached release governance, observed "
            f"{release_governance_status}"
        )
    if not gate.attached:
        errors.append(f"release governance gate {gate.gate_id} is not attached")
    if gate.validation_errors:
        errors.append(
            f"release governance gate {gate.gate_id} has validation errors"
        )
    if not gate.gate_type:
        errors.append("release governance drill requires a gate type")
    if not gate.owner_role:
        errors.append("release governance drill requires an owner role")
    if not gate.target:
        errors.append("release governance drill requires a target")
    if not gate.observed:
        errors.append("release governance drill requires observed evidence")
    if len(gate.evidence_refs) < MIN_EVIDENCE_REF_COUNT:
        errors.append(
            "enterprise adoption SLO release governance drill requires "
            f"at least {MIN_EVIDENCE_REF_COUNT} evidence refs"
        )
    return tuple(errors)


def derive_drill_status(
    release_governance: EnterpriseAdoptionSloReleaseGovernanceReport,
    *,
    scenario_count: int,
    failed_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if (
        release_governance.release_governance_status
        != EXPECTED_RELEASE_GOVERNANCE_STATUS
    ):
        return "blocked_by_release_governance"
    if (
        scenario_count != release_governance.release_gate_count
        or scenario_count == 0
    ):
        return "blocked_by_release_governance"
    if failed_count:
        return "failed"
    return "passed"


def drill_next_actions(drill_status: str) -> tuple[str, ...]:
    if drill_status == "passed":
        return (
            MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_EFFECTIVENESS_ACTION,
        )
    return (
        EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION,
    )


def count_raw_identifier_markers(
    scenarios: tuple[EnterpriseAdoptionSloReleaseGovernanceDrillScenario, ...],
) -> int:
    payload = json.dumps(
        [scenario.to_snapshot_dict() for scenario in scenarios],
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


def build_enterprise_adoption_slo_release_governance_drill_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_enterprise_adoption_slo_release_governance_drill_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_"
    "snapshot"
] = build_enterprise_adoption_slo_release_governance_drill_snapshot


def write_enterprise_adoption_slo_release_governance_drill_snapshot(
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
            build_enterprise_adoption_slo_release_governance_drill_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_"
    "snapshot"
] = write_enterprise_adoption_slo_release_governance_drill_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
