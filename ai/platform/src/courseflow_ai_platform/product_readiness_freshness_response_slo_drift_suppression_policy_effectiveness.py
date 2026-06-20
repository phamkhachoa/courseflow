from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .product_readiness_freshness_response_slo_drift_suppression_policy_drill import (
    ESCALATION_PRESERVED_CASE,
    MONITOR_SUPPRESSION_POLICY_EFFECTIVENESS_ACTION,
    ROUTED_DECISION,
    SUPPRESSED_DECISION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1"
)
EXPAND_SUPPRESSION_POLICY_COVERAGE_ACTION = (
    "expand_product_readiness_response_slo_drift_suppression_policy_coverage"
)
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")
MIN_SUPPRESSION_EFFECTIVENESS_PCT = 100
MIN_ESCALATION_PRESERVATION_PCT = 100


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal:
    signal_id: str
    rule_id: str
    alert_id: str
    scenario_id: str
    condition: str
    signal_type: str
    expected_decision: str
    observed_decision: str
    expected_route: str
    observed_route: str
    effective: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertId": self.alert_id,
            "condition": self.condition,
            "effective": self.effective,
            "evidenceRefs": list(self.evidence_refs),
            "expectedDecision": self.expected_decision,
            "expectedRoute": self.expected_route,
            "observedDecision": self.observed_decision,
            "observedRoute": self.observed_route,
            "ruleId": self.rule_id,
            "scenarioId": self.scenario_id,
            "signalId": self.signal_id,
            "signalType": self.signal_type,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "rule_id": self.rule_id,
            "alert_id": self.alert_id,
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "signal_type": self.signal_type,
            "expected_decision": self.expected_decision,
            "observed_decision": self.observed_decision,
            "expected_route": self.expected_route,
            "observed_route": self.observed_route,
            "effective": self.effective,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport:
    generated_at: str
    monitor_status: str
    drill_status: str
    policy_status: str
    rule_count: int
    active_rule_count: int
    signal_count: int
    effective_signal_count: int
    failed_signal_count: int
    suppression_candidate_count: int
    suppressed_signal_count: int
    escalation_signal_count: int
    escalation_preserved_count: int
    suppression_effectiveness_pct: int
    escalation_preservation_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    signals: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeRuleCount": self.active_rule_count,
            "drillStatus": self.drill_status,
            "effectiveSignalCount": self.effective_signal_count,
            "escalationPreservationPct": self.escalation_preservation_pct,
            "escalationPreservedCount": self.escalation_preserved_count,
            "escalationSignalCount": self.escalation_signal_count,
            "failedSignalCount": self.failed_signal_count,
            "generatedAt": self.generated_at,
            "monitorStatus": self.monitor_status,
            "nextActions": list(self.next_actions),
            "policyStatus": self.policy_status,
            "rawIdentifierCount": self.raw_identifier_count,
            "ruleCount": self.rule_count,
            "signalCount": self.signal_count,
            "signals": [signal.to_dict() for signal in self.signals],
            "suppressedSignalCount": self.suppressed_signal_count,
            "suppressionCandidateCount": self.suppression_candidate_count,
            "suppressionEffectivenessPct": self.suppression_effectiveness_pct,
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
                "policy_status": self.policy_status,
                "rule_count": self.rule_count,
                "active_rule_count": self.active_rule_count,
                "signal_count": self.signal_count,
                "effective_signal_count": self.effective_signal_count,
                "failed_signal_count": self.failed_signal_count,
                "suppression_candidate_count": self.suppression_candidate_count,
                "suppressed_signal_count": self.suppressed_signal_count,
                "escalation_signal_count": self.escalation_signal_count,
                "escalation_preserved_count": self.escalation_preserved_count,
                "suppression_effectiveness_pct": self.suppression_effectiveness_pct,
                "escalation_preservation_pct": self.escalation_preservation_pct,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "min_suppression_effectiveness_pct": (
                    MIN_SUPPRESSION_EFFECTIVENESS_PCT
                ),
                "min_escalation_preservation_pct": (
                    MIN_ESCALATION_PRESERVATION_PCT
                ),
            },
            "action_queue": {
                "effective": [
                    signal.signal_id for signal in self.signals if signal.effective
                ],
                "blocked": [
                    signal.signal_id for signal in self.signals if not signal.effective
                ],
                "next_actions": list(self.next_actions),
            },
            "signals": [signal.to_snapshot_dict() for signal in self.signals],
        }


def build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    suppression_policy_drill: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport | None
    ) = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport:
    drill = suppression_policy_drill or (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return build_suppression_policy_effectiveness_report_from_drill(
        drill,
        generated_at=generated_at,
    )


def build_suppression_policy_effectiveness_report_from_drill(
    drill: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport:
    report_date = generated_at or drill.generated_at
    signals = tuple(build_effectiveness_signal(scenario) for scenario in drill.scenarios)
    raw_identifier_count = count_raw_identifier_markers(signals)
    tenant_safe = (
        drill.tenant_safe
        and drill.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_signal_count = sum(1 for signal in signals if not signal.effective)
    suppression_candidate_count = sum(
        1 for signal in signals if signal.expected_decision == SUPPRESSED_DECISION
    )
    suppressed_signal_count = sum(
        1
        for signal in signals
        if signal.expected_decision == SUPPRESSED_DECISION
        and signal.observed_decision == SUPPRESSED_DECISION
    )
    escalation_signal_count = sum(
        1 for signal in signals if signal.expected_decision == ROUTED_DECISION
    )
    escalation_preserved_count = sum(
        1
        for signal in signals
        if signal.expected_decision == ROUTED_DECISION
        and signal.observed_decision == ROUTED_DECISION
    )
    suppression_effectiveness_pct = ratio_pct(
        suppressed_signal_count,
        suppression_candidate_count,
    )
    escalation_preservation_pct = ratio_pct(
        escalation_preserved_count,
        escalation_signal_count,
    )
    monitor_status = derive_effectiveness_status(
        drill,
        signal_count=len(signals),
        failed_signal_count=failed_signal_count,
        suppression_effectiveness_pct=suppression_effectiveness_pct,
        escalation_preservation_pct=escalation_preservation_pct,
        tenant_safe=tenant_safe,
    )
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport(
        generated_at=report_date,
        monitor_status=monitor_status,
        drill_status=drill.drill_status,
        policy_status=drill.policy_status,
        rule_count=drill.rule_count,
        active_rule_count=drill.active_rule_count,
        signal_count=len(signals),
        effective_signal_count=sum(1 for signal in signals if signal.effective),
        failed_signal_count=failed_signal_count,
        suppression_candidate_count=suppression_candidate_count,
        suppressed_signal_count=suppressed_signal_count,
        escalation_signal_count=escalation_signal_count,
        escalation_preserved_count=escalation_preserved_count,
        suppression_effectiveness_pct=suppression_effectiveness_pct,
        escalation_preservation_pct=escalation_preservation_pct,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=effectiveness_next_actions(monitor_status),
        signals=signals,
    )


def build_effectiveness_signal(
    scenario: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal:
    signal_type = effectiveness_signal_type(scenario.drill_case)
    validation_errors = validate_effectiveness_signal(scenario)
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal(
        signal_id=f"{scenario.drill_id}-effectiveness",
        rule_id=scenario.rule_id,
        alert_id=scenario.alert_id,
        scenario_id=scenario.scenario_id,
        condition=scenario.condition,
        signal_type=signal_type,
        expected_decision=scenario.expected_decision,
        observed_decision=scenario.observed_decision,
        expected_route=scenario.expected_route,
        observed_route=scenario.observed_route,
        effective=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=tuple(dict.fromkeys((
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml",
            *scenario.evidence_refs,
        ))),
    )


def effectiveness_signal_type(drill_case: str) -> str:
    if drill_case == ESCALATION_PRESERVED_CASE:
        return "escalation_preservation"
    return "noise_reduction"


def validate_effectiveness_signal(
    scenario: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not scenario.passed:
        errors.append("suppression policy drill scenario must pass before monitoring")
    if scenario.expected_decision == SUPPRESSED_DECISION:
        if scenario.observed_decision != SUPPRESSED_DECISION:
            errors.append("suppression effectiveness requires suppressed replay")
        if scenario.observed_route:
            errors.append("suppressed replay must not route an Admin/Ops action")
    if scenario.expected_decision == ROUTED_DECISION:
        if scenario.observed_decision != ROUTED_DECISION:
            errors.append("escalation preservation requires routed replay")
        if scenario.observed_route != scenario.expected_route:
            errors.append(
                "escalation preservation route mismatch: "
                f"{scenario.observed_route}"
            )
    if not scenario.evidence_refs:
        errors.append("effectiveness signal requires drill evidence refs")
    return tuple(errors)


def derive_effectiveness_status(
    drill: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport,
    *,
    signal_count: int,
    failed_signal_count: int,
    suppression_effectiveness_pct: int,
    escalation_preservation_pct: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if drill.drill_status != "passed":
        return "blocked_by_drill"
    if signal_count == 0:
        return "insufficient_signals"
    if failed_signal_count:
        return "effectiveness_failed"
    if suppression_effectiveness_pct < MIN_SUPPRESSION_EFFECTIVENESS_PCT:
        return "effectiveness_watch"
    if escalation_preservation_pct < MIN_ESCALATION_PRESERVATION_PCT:
        return "effectiveness_watch"
    return "effectiveness_monitored"


def effectiveness_next_actions(monitor_status: str) -> tuple[str, ...]:
    if monitor_status == "effectiveness_monitored":
        return (EXPAND_SUPPRESSION_POLICY_COVERAGE_ACTION,)
    return (MONITOR_SUPPRESSION_POLICY_EFFECTIVENESS_ACTION,)


def ratio_pct(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    return round((numerator / denominator) * 100)


def count_raw_identifier_markers(
    signals: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal,
        ...,
    ],
) -> int:
    payload = json.dumps(
        [signal.to_snapshot_dict() for signal in signals],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


def write_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_snapshot(
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
            build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
