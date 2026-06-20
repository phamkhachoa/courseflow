from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_trends import (
    ProductReadinessFreshnessResponseTrendReport,
    ProductReadinessFreshnessScenarioTrend,
    build_product_readiness_freshness_response_trend_report,
)

from .product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness import (
    EXPAND_SUPPRESSION_POLICY_COVERAGE_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1"
)
MONITOR_SUPPRESSION_POLICY_COVERAGE_REGRESSION_ACTION = (
    "monitor_product_readiness_response_slo_drift_suppression_policy_coverage_regression"
)
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")
ACTIVE_COVERAGE_MODE = "active_suppression_policy"
EXPLICIT_NON_WATCH_COVERAGE_MODE = "explicit_non_watch_exclusion"
MIN_COVERAGE_PCT = 100


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageItem:
    coverage_id: str
    scenario_id: str
    condition: str
    severity: str
    trend_status: str
    coverage_mode: str
    coverage_decision: str
    policy_rule_ids: tuple[str, ...]
    matched_signal_count: int
    matched_effective_signal_count: int
    required_signal_types: tuple[str, ...]
    covered: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "coverageDecision": self.coverage_decision,
            "coverageId": self.coverage_id,
            "coverageMode": self.coverage_mode,
            "covered": self.covered,
            "evidenceRefs": list(self.evidence_refs),
            "matchedEffectiveSignalCount": self.matched_effective_signal_count,
            "matchedSignalCount": self.matched_signal_count,
            "policyRuleIds": list(self.policy_rule_ids),
            "requiredSignalTypes": list(self.required_signal_types),
            "scenarioId": self.scenario_id,
            "severity": self.severity,
            "trendStatus": self.trend_status,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "coverage_id": self.coverage_id,
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "severity": self.severity,
            "trend_status": self.trend_status,
            "coverage_mode": self.coverage_mode,
            "coverage_decision": self.coverage_decision,
            "policy_rule_ids": list(self.policy_rule_ids),
            "matched_signal_count": self.matched_signal_count,
            "matched_effective_signal_count": self.matched_effective_signal_count,
            "required_signal_types": list(self.required_signal_types),
            "covered": self.covered,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport:
    generated_at: str
    coverage_status: str
    effectiveness_status: str
    trend_status: str
    scenario_class_count: int
    covered_scenario_count: int
    failed_coverage_count: int
    active_policy_scenario_count: int
    explicit_non_watch_scenario_count: int
    policy_rule_count: int
    effective_signal_count: int
    coverage_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    items: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageItem,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activePolicyScenarioCount": self.active_policy_scenario_count,
            "coveragePct": self.coverage_pct,
            "coverageStatus": self.coverage_status,
            "coveredScenarioCount": self.covered_scenario_count,
            "effectiveSignalCount": self.effective_signal_count,
            "effectivenessStatus": self.effectiveness_status,
            "explicitNonWatchScenarioCount": self.explicit_non_watch_scenario_count,
            "failedCoverageCount": self.failed_coverage_count,
            "generatedAt": self.generated_at,
            "items": [item.to_dict() for item in self.items],
            "nextActions": list(self.next_actions),
            "policyRuleCount": self.policy_rule_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "scenarioClassCount": self.scenario_class_count,
            "tenantSafe": self.tenant_safe,
            "trendStatus": self.trend_status,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "coverage_status": self.coverage_status,
                "effectiveness_status": self.effectiveness_status,
                "trend_status": self.trend_status,
                "scenario_class_count": self.scenario_class_count,
                "covered_scenario_count": self.covered_scenario_count,
                "failed_coverage_count": self.failed_coverage_count,
                "active_policy_scenario_count": self.active_policy_scenario_count,
                "explicit_non_watch_scenario_count": (
                    self.explicit_non_watch_scenario_count
                ),
                "policy_rule_count": self.policy_rule_count,
                "effective_signal_count": self.effective_signal_count,
                "coverage_pct": self.coverage_pct,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "min_coverage_pct": MIN_COVERAGE_PCT,
            },
            "action_queue": {
                "covered": [
                    item.coverage_id for item in self.items if item.covered
                ],
                "blocked": [
                    item.coverage_id for item in self.items if not item.covered
                ],
                "next_actions": list(self.next_actions),
            },
            "coverage_items": [item.to_snapshot_dict() for item in self.items],
        }


def build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
        | None
    ) = None,
    response_trends: ProductReadinessFreshnessResponseTrendReport | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport:
    root = Path(ai_root)
    effectiveness_report = effectiveness or (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report(
            root,
            generated_at=generated_at,
        )
    )
    trends = response_trends or build_product_readiness_freshness_response_trend_report(
        root,
        generated_at=generated_at,
    )
    return build_suppression_policy_coverage_report_from_reports(
        effectiveness_report,
        response_trends=trends,
        generated_at=generated_at,
    )


def build_suppression_policy_coverage_report_from_reports(
    effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
    ),
    *,
    response_trends: ProductReadinessFreshnessResponseTrendReport,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport:
    report_date = generated_at or effectiveness.generated_at
    items = tuple(
        build_coverage_item(trend, effectiveness=effectiveness)
        for trend in response_trends.scenario_trends
    )
    raw_identifier_count = count_raw_identifier_markers(items)
    tenant_safe = (
        effectiveness.tenant_safe
        and response_trends.tenant_safe
        and effectiveness.raw_identifier_count == 0
        and response_trends.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    covered_scenario_count = sum(1 for item in items if item.covered)
    failed_coverage_count = sum(1 for item in items if not item.covered)
    coverage_pct = ratio_pct(covered_scenario_count, len(items))
    coverage_status = derive_coverage_status(
        effectiveness,
        response_trends=response_trends,
        scenario_class_count=len(items),
        failed_coverage_count=failed_coverage_count,
        coverage_pct=coverage_pct,
        tenant_safe=tenant_safe,
    )
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport(
        generated_at=report_date,
        coverage_status=coverage_status,
        effectiveness_status=effectiveness.monitor_status,
        trend_status=response_trends.trend_status,
        scenario_class_count=len(items),
        covered_scenario_count=covered_scenario_count,
        failed_coverage_count=failed_coverage_count,
        active_policy_scenario_count=sum(
            1 for item in items if item.coverage_mode == ACTIVE_COVERAGE_MODE
        ),
        explicit_non_watch_scenario_count=sum(
            1
            for item in items
            if item.coverage_mode == EXPLICIT_NON_WATCH_COVERAGE_MODE
        ),
        policy_rule_count=effectiveness.rule_count,
        effective_signal_count=effectiveness.effective_signal_count,
        coverage_pct=coverage_pct,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=coverage_next_actions(coverage_status),
        items=items,
    )


def build_coverage_item(
    trend: ProductReadinessFreshnessScenarioTrend,
    *,
    effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
    ),
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageItem:
    signals = matching_signals(trend, effectiveness)
    signal_types = tuple(sorted({signal.signal_type for signal in signals}))
    policy_rule_ids = tuple(dict.fromkeys(signal.rule_id for signal in signals))
    if trend.trend_status == "watch":
        coverage_mode = ACTIVE_COVERAGE_MODE
        coverage_decision = "covered_by_effective_suppression_policy"
        required_signal_types = ("escalation_preservation", "noise_reduction")
        validation_errors = validate_active_coverage(
            trend,
            signals=signals,
            signal_types=signal_types,
        )
    else:
        coverage_mode = EXPLICIT_NON_WATCH_COVERAGE_MODE
        coverage_decision = "no_suppression_policy_required"
        required_signal_types = ()
        validation_errors = validate_non_watch_coverage(trend, signals=signals)
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageItem(
        coverage_id=f"prf-response-slo-drift-{trend.scenario_id}-policy-coverage",
        scenario_id=trend.scenario_id,
        condition=trend.condition,
        severity=trend.severity,
        trend_status=trend.trend_status,
        coverage_mode=coverage_mode,
        coverage_decision=coverage_decision,
        policy_rule_ids=policy_rule_ids,
        matched_signal_count=len(signals),
        matched_effective_signal_count=sum(1 for signal in signals if signal.effective),
        required_signal_types=required_signal_types,
        covered=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=coverage_evidence_refs(trend, signals),
    )


def matching_signals(
    trend: ProductReadinessFreshnessScenarioTrend,
    effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
    ),
) -> tuple[
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal,
    ...,
]:
    return tuple(
        signal for signal in effectiveness.signals if signal.scenario_id == trend.scenario_id
    )


def validate_active_coverage(
    trend: ProductReadinessFreshnessScenarioTrend,
    *,
    signals: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal,
        ...,
    ],
    signal_types: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    if not trend.watch_reasons:
        errors.append("active suppression coverage requires a watch scenario")
    if not signals:
        errors.append("watch scenario requires suppression effectiveness signals")
    if any(not signal.effective for signal in signals):
        errors.append("all matched suppression policy signals must be effective")
    if "noise_reduction" not in signal_types:
        errors.append("watch scenario requires noise-reduction signal coverage")
    if "escalation_preservation" not in signal_types:
        errors.append("watch scenario requires escalation-preservation signal coverage")
    return tuple(errors)


def validate_non_watch_coverage(
    trend: ProductReadinessFreshnessScenarioTrend,
    *,
    signals: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal,
        ...,
    ],
) -> tuple[str, ...]:
    errors: list[str] = []
    if trend.trend_status != "within_slo":
        errors.append(f"expected within_slo trend, observed {trend.trend_status}")
    if trend.watch_reasons:
        errors.append("watch scenario cannot be marked as non-watch coverage")
    if trend.breach_reasons:
        errors.append("breached scenario requires response remediation before coverage")
    if signals:
        errors.append("non-watch scenario must not carry active suppression signals")
    return tuple(errors)


def coverage_evidence_refs(
    trend: ProductReadinessFreshnessScenarioTrend,
    signals: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessSignal,
        ...,
    ],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys((
        "platform/operations/reports/"
        "product-readiness-freshness-response-trends-v1.yaml",
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
        *trend.evidence_refs,
        *(ref for signal in signals for ref in signal.evidence_refs),
    )))


def derive_coverage_status(
    effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
    ),
    *,
    response_trends: ProductReadinessFreshnessResponseTrendReport,
    scenario_class_count: int,
    failed_coverage_count: int,
    coverage_pct: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if effectiveness.monitor_status != "effectiveness_monitored":
        return "blocked_by_effectiveness"
    if response_trends.trend_status not in {"trend_ready", "trend_ready_with_watch"}:
        return "blocked_by_response_trends"
    if scenario_class_count == 0:
        return "insufficient_scenarios"
    if failed_coverage_count:
        return "coverage_incomplete"
    if coverage_pct < MIN_COVERAGE_PCT:
        return "coverage_incomplete"
    return "coverage_expanded"


def coverage_next_actions(coverage_status: str) -> tuple[str, ...]:
    if coverage_status == "coverage_expanded":
        return (MONITOR_SUPPRESSION_POLICY_COVERAGE_REGRESSION_ACTION,)
    return (EXPAND_SUPPRESSION_POLICY_COVERAGE_ACTION,)


def ratio_pct(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    return round((numerator / denominator) * 100)


def count_raw_identifier_markers(
    items: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageItem,
        ...,
    ],
) -> int:
    payload = json.dumps(
        [item.to_snapshot_dict() for item in items],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


def write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_snapshot(
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
            build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_snapshot(
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
