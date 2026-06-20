from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

ENTERPRISE_PATTERN_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_pattern"
)
_ENTERPRISE_PATTERN_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterprisePatternReport"
)
_ENTERPRISE_PATTERN_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_report"
)
_MONITOR_ADOPTION_ACTION_ATTR = (
    "MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION"
)
enterprise_pattern_module = import_module(ENTERPRISE_PATTERN_MODULE)
CoverageReleaseGateEnterprisePatternReport = getattr(
    enterprise_pattern_module,
    _ENTERPRISE_PATTERN_REPORT_ATTR,
)
build_enterprise_pattern_report = getattr(
    enterprise_pattern_module,
    _ENTERPRISE_PATTERN_BUILDER_ATTR,
)
MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION = getattr(
    enterprise_pattern_module,
    _MONITOR_ADOPTION_ACTION_ATTR,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-adoption-v1"
)
PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION = (
    "publish_enterprise_release_gate_pattern_adoption_slo"
)
EXPECTED_PATTERN_STATUS = "enterprise_pattern_expanded"
MIN_NON_LMS_BLUEPRINT_COUNT = 5
MIN_NON_LMS_PRODUCT_COUNT = 4
MIN_TAXONOMY_AREA_COUNT = 8
MIN_EVALUATION_GATE_COUNT = 30
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
OPENAI_KEY_PATTERN = re.compile(r"(^|[\"'\\s:=])sk-[a-z0-9]")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
ENTERPRISE_PATTERN_REPORT_PATH = (
    "platform/operations/reports/"
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-enterprise-pattern-v1.yaml"
)
PRODUCT_READINESS_REPORT_PATH = (
    "platform/product/reports/ai-platform-product-readiness-v1.yaml"
)
BLUEPRINT_REPORT_PATH = "platform/intake/reports/use-case-blueprints-v1.yaml"


@dataclass(frozen=True, slots=True)
class EnterprisePatternAdoptionSignal:
    signal_id: str
    signal_type: str
    condition: str
    expected: str
    observed: str
    adopted: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adopted": self.adopted,
            "condition": self.condition,
            "evidenceRefs": list(self.evidence_refs),
            "expected": self.expected,
            "observed": self.observed,
            "signalId": self.signal_id,
            "signalType": self.signal_type,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "condition": self.condition,
            "expected": self.expected,
            "observed": self.observed,
            "adopted": self.adopted,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class EnterprisePatternAdoptionReport:
    generated_at: str
    adoption_status: str
    enterprise_pattern_status: str
    blueprint_count: int
    assigned_use_case_count: int
    non_lms_blueprint_count: int
    non_lms_product_count: int
    taxonomy_area_count: int
    target_module_count: int
    executable_module_count: int
    evaluation_gate_count: int
    signal_count: int
    adopted_signal_count: int
    blocked_signal_count: int
    adoption_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    signals: tuple[EnterprisePatternAdoptionSignal, ...]

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
            "executableModuleCount": self.executable_module_count,
            "generatedAt": self.generated_at,
            "nextActions": list(self.next_actions),
            "nonLmsBlueprintCount": self.non_lms_blueprint_count,
            "nonLmsProductCount": self.non_lms_product_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "signalCount": self.signal_count,
            "signals": [signal.to_dict() for signal in self.signals],
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
                "adoption_status": self.adoption_status,
                "enterprise_pattern_status": self.enterprise_pattern_status,
                "blueprint_count": self.blueprint_count,
                "assigned_use_case_count": self.assigned_use_case_count,
                "non_lms_blueprint_count": self.non_lms_blueprint_count,
                "non_lms_product_count": self.non_lms_product_count,
                "taxonomy_area_count": self.taxonomy_area_count,
                "target_module_count": self.target_module_count,
                "executable_module_count": self.executable_module_count,
                "evaluation_gate_count": self.evaluation_gate_count,
                "signal_count": self.signal_count,
                "adopted_signal_count": self.adopted_signal_count,
                "blocked_signal_count": self.blocked_signal_count,
                "adoption_pct": self.adoption_pct,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "min_non_lms_blueprint_count": MIN_NON_LMS_BLUEPRINT_COUNT,
                "min_non_lms_product_count": MIN_NON_LMS_PRODUCT_COUNT,
                "min_taxonomy_area_count": MIN_TAXONOMY_AREA_COUNT,
                "min_evaluation_gate_count": MIN_EVALUATION_GATE_COUNT,
            },
            "action_queue": {
                "adopted": [
                    signal.signal_id for signal in self.signals if signal.adopted
                ],
                "blocked": [
                    signal.signal_id for signal in self.signals if not signal.adopted
                ],
                "next_actions": list(self.next_actions),
            },
            "signals": [signal.to_snapshot_dict() for signal in self.signals],
        }


globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSignal"
] = EnterprisePatternAdoptionSignal
globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionReport"
] = EnterprisePatternAdoptionReport


def build_suppression_policy_coverage_release_gate_enterprise_adoption_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    enterprise_pattern: CoverageReleaseGateEnterprisePatternReport | None = None,
) -> EnterprisePatternAdoptionReport:
    pattern = enterprise_pattern or build_enterprise_pattern_report(
        ai_root,
        generated_at=generated_at,
    )
    return build_release_gate_enterprise_adoption_report_from_pattern(
        pattern,
        generated_at=generated_at,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_report"
] = build_suppression_policy_coverage_release_gate_enterprise_adoption_report


def build_release_gate_enterprise_adoption_report_from_pattern(
    enterprise_pattern: CoverageReleaseGateEnterprisePatternReport,
    *,
    generated_at: str | None = None,
) -> EnterprisePatternAdoptionReport:
    report_date = generated_at or enterprise_pattern.generated_at
    signals = build_enterprise_adoption_signals(enterprise_pattern)
    raw_identifier_count = count_raw_identifier_markers(signals)
    tenant_safe = (
        enterprise_pattern.tenant_safe
        and enterprise_pattern.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    adopted_signal_count = sum(1 for signal in signals if signal.adopted)
    blocked_signal_count = len(signals) - adopted_signal_count
    adoption_pct = ratio_pct(adopted_signal_count, len(signals))
    adoption_status = derive_enterprise_adoption_status(
        enterprise_pattern,
        signal_count=len(signals),
        blocked_signal_count=blocked_signal_count,
        tenant_safe=tenant_safe,
    )
    return EnterprisePatternAdoptionReport(
        generated_at=report_date,
        adoption_status=adoption_status,
        enterprise_pattern_status=enterprise_pattern.expansion_status,
        blueprint_count=enterprise_pattern.blueprint_count,
        assigned_use_case_count=enterprise_pattern.assigned_use_case_count,
        non_lms_blueprint_count=enterprise_pattern.non_lms_blueprint_count,
        non_lms_product_count=enterprise_pattern.non_lms_product_count,
        taxonomy_area_count=enterprise_pattern.taxonomy_area_count,
        target_module_count=enterprise_pattern.target_module_count,
        executable_module_count=enterprise_pattern.executable_module_count,
        evaluation_gate_count=enterprise_pattern.evaluation_gate_count,
        signal_count=len(signals),
        adopted_signal_count=adopted_signal_count,
        blocked_signal_count=blocked_signal_count,
        adoption_pct=adoption_pct,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=enterprise_adoption_next_actions(adoption_status),
        signals=signals,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_report_from_pattern"
] = build_release_gate_enterprise_adoption_report_from_pattern


def build_enterprise_adoption_signals(
    enterprise_pattern: CoverageReleaseGateEnterprisePatternReport,
) -> tuple[EnterprisePatternAdoptionSignal, ...]:
    assigned_all = (
        enterprise_pattern.assigned_use_case_count
        == enterprise_pattern.blueprint_count
        and enterprise_pattern.blocked_assignment_count == 0
    )
    return (
        make_signal(
            signal_id="enterprise-pattern-expanded-signal",
            signal_type="enterprise_pattern_status",
            condition="enterprise release gate pattern must be expanded first",
            expected=EXPECTED_PATTERN_STATUS,
            observed=enterprise_pattern.expansion_status,
            adopted=enterprise_pattern.expansion_status == EXPECTED_PATTERN_STATUS,
            validation_message="enterprise pattern expansion is not complete",
            evidence_refs=(ENTERPRISE_PATTERN_REPORT_PATH, BLUEPRINT_REPORT_PATH),
        ),
        make_signal(
            signal_id="enterprise-pattern-assignment-coverage-signal",
            signal_type="assignment_coverage",
            condition="all ready solution blueprints must be assigned",
            expected=f"{enterprise_pattern.blueprint_count}/"
            f"{enterprise_pattern.blueprint_count} assigned",
            observed=f"{enterprise_pattern.assigned_use_case_count}/"
            f"{enterprise_pattern.blueprint_count} assigned; "
            f"{enterprise_pattern.blocked_assignment_count} blocked",
            adopted=assigned_all,
            validation_message="enterprise pattern assignment coverage is incomplete",
            evidence_refs=(ENTERPRISE_PATTERN_REPORT_PATH, BLUEPRINT_REPORT_PATH),
        ),
        make_signal(
            signal_id="enterprise-pattern-product-span-signal",
            signal_type="enterprise_product_span",
            condition="adoption must cover non-LMS blueprints and products",
            expected=(
                f">={MIN_NON_LMS_BLUEPRINT_COUNT} non-LMS blueprints and "
                f">={MIN_NON_LMS_PRODUCT_COUNT} non-LMS products"
            ),
            observed=(
                f"{enterprise_pattern.non_lms_blueprint_count} non-LMS "
                f"blueprints; {enterprise_pattern.non_lms_product_count} "
                "non-LMS products"
            ),
            adopted=(
                enterprise_pattern.non_lms_blueprint_count
                >= MIN_NON_LMS_BLUEPRINT_COUNT
                and enterprise_pattern.non_lms_product_count
                >= MIN_NON_LMS_PRODUCT_COUNT
            ),
            validation_message="enterprise product span is below adoption threshold",
            evidence_refs=(ENTERPRISE_PATTERN_REPORT_PATH, BLUEPRINT_REPORT_PATH),
        ),
        make_signal(
            signal_id="enterprise-pattern-taxonomy-evaluation-span-signal",
            signal_type="taxonomy_evaluation_span",
            condition="adoption must span enough taxonomy areas and eval gates",
            expected=(
                f">={MIN_TAXONOMY_AREA_COUNT} taxonomy areas and "
                f">={MIN_EVALUATION_GATE_COUNT} evaluation gates"
            ),
            observed=(
                f"{enterprise_pattern.taxonomy_area_count} taxonomy areas; "
                f"{enterprise_pattern.evaluation_gate_count} evaluation gates"
            ),
            adopted=(
                enterprise_pattern.taxonomy_area_count >= MIN_TAXONOMY_AREA_COUNT
                and enterprise_pattern.evaluation_gate_count
                >= MIN_EVALUATION_GATE_COUNT
            ),
            validation_message="taxonomy or evaluation span is below threshold",
            evidence_refs=(ENTERPRISE_PATTERN_REPORT_PATH, BLUEPRINT_REPORT_PATH),
        ),
        make_signal(
            signal_id="enterprise-pattern-tenant-safety-signal",
            signal_type="tenant_safety",
            condition="adoption evidence must be tenant-safe",
            expected="tenant_safe=true raw_identifier_count=0",
            observed=(
                f"tenant_safe={str(enterprise_pattern.tenant_safe).lower()} "
                f"raw_identifier_count={enterprise_pattern.raw_identifier_count}"
            ),
            adopted=(
                enterprise_pattern.tenant_safe
                and enterprise_pattern.raw_identifier_count == 0
            ),
            validation_message="enterprise pattern evidence is not tenant-safe",
            evidence_refs=(ENTERPRISE_PATTERN_REPORT_PATH, PRODUCT_READINESS_REPORT_PATH),
        ),
        make_signal(
            signal_id="enterprise-pattern-adoption-followup-signal",
            signal_type="adoption_followup",
            condition="Product Readiness must track enterprise adoption monitoring",
            expected=MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION,
            observed=",".join(enterprise_pattern.next_actions),
            adopted=(
                MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION
                in enterprise_pattern.next_actions
            ),
            validation_message="enterprise adoption monitoring follow-up is missing",
            evidence_refs=(ENTERPRISE_PATTERN_REPORT_PATH, PRODUCT_READINESS_REPORT_PATH),
        ),
    )


def make_signal(
    *,
    signal_id: str,
    signal_type: str,
    condition: str,
    expected: str,
    observed: str,
    adopted: bool,
    validation_message: str,
    evidence_refs: tuple[str, ...],
) -> EnterprisePatternAdoptionSignal:
    return EnterprisePatternAdoptionSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        condition=condition,
        expected=expected,
        observed=observed,
        adopted=adopted,
        validation_errors=() if adopted else (validation_message,),
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def derive_enterprise_adoption_status(
    enterprise_pattern: CoverageReleaseGateEnterprisePatternReport,
    *,
    signal_count: int,
    blocked_signal_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if enterprise_pattern.expansion_status != EXPECTED_PATTERN_STATUS:
        return "blocked_by_enterprise_pattern"
    if signal_count == 0:
        return "insufficient_adoption_signals"
    if blocked_signal_count:
        return "adoption_gap_detected"
    return "adoption_monitored"


def enterprise_adoption_next_actions(adoption_status: str) -> tuple[str, ...]:
    if adoption_status == "adoption_monitored":
        return (PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION,)
    return (MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION,)


def ratio_pct(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    return round((numerator / denominator) * 100)


def count_raw_identifier_markers(
    signals: tuple[EnterprisePatternAdoptionSignal, ...],
) -> int:
    payload = json.dumps(
        [signal.to_snapshot_dict() for signal in signals],
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


def build_suppression_policy_coverage_release_gate_enterprise_adoption_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_suppression_policy_coverage_release_gate_enterprise_adoption_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_snapshot"
] = build_suppression_policy_coverage_release_gate_enterprise_adoption_snapshot


def write_suppression_policy_coverage_release_gate_enterprise_adoption_snapshot(
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
            build_suppression_policy_coverage_release_gate_enterprise_adoption_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_snapshot"
] = write_suppression_policy_coverage_release_gate_enterprise_adoption_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
