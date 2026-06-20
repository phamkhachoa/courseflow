from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

RELEASE_GATE_DRILL_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_drill"
)
_RELEASE_GATE_DRILL_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrillReport"
)
_RELEASE_GATE_DRILL_SCENARIO_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrillScenario"
)
_RELEASE_GATE_DRILL_BUILDER_ATTR = (
    "build_suppression_policy_coverage_release_gate_drill_report"
)
_MONITOR_RELEASE_GATE_EFFECTIVENESS_ACTION_ATTR = (
    "MONITOR_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_EFFECTIVENESS_ACTION"
)
release_gate_drill_module = import_module(RELEASE_GATE_DRILL_MODULE)
CoverageReleaseGateDrillReport = getattr(
    release_gate_drill_module,
    _RELEASE_GATE_DRILL_REPORT_ATTR,
)
CoverageReleaseGateDrillScenario = getattr(
    release_gate_drill_module,
    _RELEASE_GATE_DRILL_SCENARIO_ATTR,
)
build_suppression_policy_coverage_release_gate_drill_report = getattr(
    release_gate_drill_module,
    _RELEASE_GATE_DRILL_BUILDER_ATTR,
)
MONITOR_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_EFFECTIVENESS_ACTION = getattr(
    release_gate_drill_module,
    _MONITOR_RELEASE_GATE_EFFECTIVENESS_ACTION_ATTR,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-"
    "coverage-release-gate-effectiveness-v1"
)
EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION = (
    "expand_product_readiness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_pattern_to_enterprise_use_cases"
)
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "sk-", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
EXPECTED_RELEASE_GATE_DRILL_STATUS = "passed"
EXPECTED_RELEASE_GOVERNANCE_STATUS = "release_governance_attached"
EXPECTED_RELEASE_GATE_OUTCOME = "release_gate_holds"


@dataclass(frozen=True, slots=True)
class ReleaseGateEffectivenessSignal:
    signal_id: str
    signal_type: str
    condition: str
    expected: str
    observed: str
    effective: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "effective": self.effective,
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
            "effective": self.effective,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ReleaseGateEffectivenessReport:
    generated_at: str
    monitor_status: str
    drill_status: str
    release_governance_status: str
    release_gate_count: int
    scenario_count: int
    passed_count: int
    failed_count: int
    signal_count: int
    effective_signal_count: int
    failed_signal_count: int
    release_gate_effectiveness_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    signals: tuple[
        ReleaseGateEffectivenessSignal,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "drillStatus": self.drill_status,
            "effectiveSignalCount": self.effective_signal_count,
            "failedCount": self.failed_count,
            "failedSignalCount": self.failed_signal_count,
            "generatedAt": self.generated_at,
            "monitorStatus": self.monitor_status,
            "nextActions": list(self.next_actions),
            "passedCount": self.passed_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "releaseGateCount": self.release_gate_count,
            "releaseGateEffectivenessPct": self.release_gate_effectiveness_pct,
            "releaseGovernanceStatus": self.release_governance_status,
            "scenarioCount": self.scenario_count,
            "signalCount": self.signal_count,
            "signals": [signal.to_dict() for signal in self.signals],
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "monitor_status": self.monitor_status,
                "drill_status": self.drill_status,
                "release_governance_status": self.release_governance_status,
                "release_gate_count": self.release_gate_count,
                "scenario_count": self.scenario_count,
                "passed_count": self.passed_count,
                "failed_count": self.failed_count,
                "signal_count": self.signal_count,
                "effective_signal_count": self.effective_signal_count,
                "failed_signal_count": self.failed_signal_count,
                "release_gate_effectiveness_pct": (
                    self.release_gate_effectiveness_pct
                ),
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "action_queue": {
                "effective": [
                    signal.signal_id
                    for signal in self.signals
                    if signal.effective
                ],
                "blocked": [
                    signal.signal_id
                    for signal in self.signals
                    if not signal.effective
                ],
                "next_actions": list(self.next_actions),
            },
            "signals": [signal.to_snapshot_dict() for signal in self.signals],
        }


globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEffectivenessSignal"
] = ReleaseGateEffectivenessSignal
globals()[
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEffectivenessReport"
] = ReleaseGateEffectivenessReport


def build_suppression_policy_coverage_release_gate_effectiveness_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    release_gate_drill: CoverageReleaseGateDrillReport | None = None,
) -> ReleaseGateEffectivenessReport:
    drill = release_gate_drill or (
        build_suppression_policy_coverage_release_gate_drill_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return build_suppression_policy_coverage_release_gate_effectiveness_report_from_drill(
        drill,
        generated_at=generated_at,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_report"
] = build_suppression_policy_coverage_release_gate_effectiveness_report


def build_suppression_policy_coverage_release_gate_effectiveness_report_from_drill(
    release_gate_drill: CoverageReleaseGateDrillReport,
    *,
    generated_at: str | None = None,
) -> ReleaseGateEffectivenessReport:
    report_date = generated_at or release_gate_drill.generated_at
    signals = build_release_gate_effectiveness_signals(release_gate_drill)
    raw_identifier_count = count_raw_identifier_markers(signals)
    tenant_safe = (
        release_gate_drill.tenant_safe
        and release_gate_drill.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    effective_signal_count = sum(1 for signal in signals if signal.effective)
    failed_signal_count = len(signals) - effective_signal_count
    release_gate_effectiveness_pct = ratio_pct(effective_signal_count, len(signals))
    monitor_status = derive_release_gate_effectiveness_status(
        release_gate_drill,
        signal_count=len(signals),
        failed_signal_count=failed_signal_count,
        tenant_safe=tenant_safe,
    )
    return ReleaseGateEffectivenessReport(
        generated_at=report_date,
        monitor_status=monitor_status,
        drill_status=release_gate_drill.drill_status,
        release_governance_status=(
            release_gate_drill.release_governance_status
        ),
        release_gate_count=release_gate_drill.release_gate_count,
        scenario_count=release_gate_drill.scenario_count,
        passed_count=release_gate_drill.passed_count,
        failed_count=release_gate_drill.failed_count,
        signal_count=len(signals),
        effective_signal_count=effective_signal_count,
        failed_signal_count=failed_signal_count,
        release_gate_effectiveness_pct=release_gate_effectiveness_pct,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=release_gate_effectiveness_next_actions(monitor_status),
        signals=signals,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_report_from_drill"
] = build_suppression_policy_coverage_release_gate_effectiveness_report_from_drill


def build_release_gate_effectiveness_signals(
    release_gate_drill: CoverageReleaseGateDrillReport,
) -> tuple[
    ReleaseGateEffectivenessSignal,
    ...,
]:
    drill_path = (
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-drill-v1.yaml"
    )
    governance_path = (
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-governance-v1.yaml"
    )
    product_readiness_path = (
        "platform/product/reports/ai-platform-product-readiness-v1.yaml"
    )
    all_scenarios_pass = (
        release_gate_drill.passed_count
        == release_gate_drill.scenario_count
        == release_gate_drill.release_gate_count
    )
    complete_scenario_count = sum(
        scenario_has_complete_evidence(scenario)
        for scenario in release_gate_drill.scenarios
    )
    evidence_complete = complete_scenario_count == len(
        release_gate_drill.scenarios
    )
    return (
        make_signal(
            signal_id="release-gate-drill-passed-signal",
            signal_type="drill_status",
            condition="release gate drill must pass before release guard rollout",
            expected=EXPECTED_RELEASE_GATE_DRILL_STATUS,
            observed=release_gate_drill.drill_status,
            effective=release_gate_drill.drill_status
            == EXPECTED_RELEASE_GATE_DRILL_STATUS,
            validation_message=(
                "release gate drill status must be passed before effectiveness "
                "monitoring"
            ),
            evidence_refs=(drill_path, governance_path),
        ),
        make_signal(
            signal_id="release-gate-scenario-pass-rate-signal",
            signal_type="scenario_pass_rate",
            condition="every release gate scenario must pass",
            expected=(
                f"{release_gate_drill.release_gate_count}/"
                f"{release_gate_drill.release_gate_count}"
            ),
            observed=(
                f"{release_gate_drill.passed_count}/"
                f"{release_gate_drill.scenario_count}"
            ),
            effective=all_scenarios_pass,
            validation_message="release gate drill pass rate is incomplete",
            evidence_refs=(drill_path,),
        ),
        make_signal(
            signal_id="release-gate-blocked-scenario-clean-signal",
            signal_type="blocked_queue",
            condition="release gate drill action queue must have no blocked scenarios",
            expected="0 blocked",
            observed=f"{release_gate_drill.failed_count} blocked",
            effective=release_gate_drill.failed_count == 0,
            validation_message="release gate drill still has blocked scenarios",
            evidence_refs=(drill_path,),
        ),
        make_signal(
            signal_id="release-gate-tenant-safety-signal",
            signal_type="tenant_safety",
            condition="release gate evidence must be tenant-safe",
            expected="tenant_safe=true raw_identifier_count=0",
            observed=(
                f"tenant_safe={str(release_gate_drill.tenant_safe).lower()} "
                f"raw_identifier_count={release_gate_drill.raw_identifier_count}"
            ),
            effective=(
                release_gate_drill.tenant_safe
                and release_gate_drill.raw_identifier_count == 0
            ),
            validation_message="release gate drill evidence is not tenant-safe",
            evidence_refs=(drill_path, product_readiness_path),
        ),
        make_signal(
            signal_id="release-gate-evidence-completeness-signal",
            signal_type="evidence_completeness",
            condition="release gate scenarios must carry complete hold evidence",
            expected="all scenarios have >=3 evidence refs and hold outcome",
            observed=(
                f"{complete_scenario_count}/"
                f"{release_gate_drill.scenario_count} complete"
            ),
            effective=evidence_complete,
            validation_message="release gate drill evidence is incomplete",
            evidence_refs=(drill_path, governance_path, product_readiness_path),
        ),
    )


def make_signal(
    *,
    signal_id: str,
    signal_type: str,
    condition: str,
    expected: str,
    observed: str,
    effective: bool,
    validation_message: str,
    evidence_refs: tuple[str, ...],
) -> ReleaseGateEffectivenessSignal:
    return ReleaseGateEffectivenessSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        condition=condition,
        expected=expected,
        observed=observed,
        effective=effective,
        validation_errors=() if effective else (validation_message,),
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def scenario_has_complete_evidence(
    scenario: CoverageReleaseGateDrillScenario,
) -> bool:
    return (
        len(scenario.evidence_refs) >= 3
        and scenario.expected_outcome == EXPECTED_RELEASE_GATE_OUTCOME
        and scenario.observed_outcome == EXPECTED_RELEASE_GATE_OUTCOME
    )


def derive_release_gate_effectiveness_status(
    release_gate_drill: CoverageReleaseGateDrillReport,
    *,
    signal_count: int,
    failed_signal_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if release_gate_drill.release_governance_status != (
        EXPECTED_RELEASE_GOVERNANCE_STATUS
    ):
        return "blocked_by_release_governance"
    if release_gate_drill.drill_status != EXPECTED_RELEASE_GATE_DRILL_STATUS:
        return "blocked_by_release_gate_drill"
    if signal_count == 0:
        return "insufficient_signals"
    if failed_signal_count:
        return "effectiveness_gap_detected"
    return "effectiveness_monitored"


def release_gate_effectiveness_next_actions(
    monitor_status: str,
) -> tuple[str, ...]:
    if monitor_status == "effectiveness_monitored":
        return (EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION,)
    return (MONITOR_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_EFFECTIVENESS_ACTION,)


def ratio_pct(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    return round((numerator / denominator) * 100)


def count_raw_identifier_markers(
    signals: tuple[
        ReleaseGateEffectivenessSignal,
        ...,
    ],
) -> int:
    payload = json.dumps(
        [signal.to_snapshot_dict() for signal in signals],
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


def build_suppression_policy_coverage_release_gate_effectiveness_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_suppression_policy_coverage_release_gate_effectiveness_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_snapshot"
] = build_suppression_policy_coverage_release_gate_effectiveness_snapshot


def write_suppression_policy_coverage_release_gate_effectiveness_snapshot(
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
            build_suppression_policy_coverage_release_gate_effectiveness_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_snapshot"
] = write_suppression_policy_coverage_release_gate_effectiveness_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
