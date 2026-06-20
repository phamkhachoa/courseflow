from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .product_readiness_freshness_response_slo_drift_alert_suppression_policy import (
    EXERCISE_SUPPRESSION_POLICY_DRILL_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport,
    ProductReadinessFreshnessResponseSloDriftSuppressionRule,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_report,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1"
)
MONITOR_SUPPRESSION_POLICY_EFFECTIVENESS_ACTION = (
    "monitor_product_readiness_response_slo_drift_suppression_policy_effectiveness"
)
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")
UNDER_THRESHOLD_CASE = "under_threshold_suppressed"
DEDUPE_WINDOW_CASE = "dedupe_window_suppressed"
COOLDOWN_WINDOW_CASE = "cooldown_window_suppressed"
ESCALATION_PRESERVED_CASE = "escalation_preserved"
SUPPRESSED_DECISION = "suppressed"
ROUTED_DECISION = "routed"


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario:
    drill_id: str
    rule_id: str
    alert_id: str
    scenario_id: str
    condition: str
    drill_case: str
    trigger_usage_pct: int
    trigger_floor_pct: int
    escalation_floor_pct: int
    replay_age_minutes: int
    dedupe_window_minutes: int
    cooldown_minutes: int
    expected_decision: str
    observed_decision: str
    expected_route: str
    observed_route: str
    expected_action: str
    observed_action: str
    passed: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertId": self.alert_id,
            "condition": self.condition,
            "cooldownMinutes": self.cooldown_minutes,
            "dedupeWindowMinutes": self.dedupe_window_minutes,
            "drillCase": self.drill_case,
            "drillId": self.drill_id,
            "escalationFloorPct": self.escalation_floor_pct,
            "evidenceRefs": list(self.evidence_refs),
            "expectedAction": self.expected_action,
            "expectedDecision": self.expected_decision,
            "expectedRoute": self.expected_route,
            "observedAction": self.observed_action,
            "observedDecision": self.observed_decision,
            "observedRoute": self.observed_route,
            "passed": self.passed,
            "replayAgeMinutes": self.replay_age_minutes,
            "ruleId": self.rule_id,
            "scenarioId": self.scenario_id,
            "triggerFloorPct": self.trigger_floor_pct,
            "triggerUsagePct": self.trigger_usage_pct,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "drill_id": self.drill_id,
            "rule_id": self.rule_id,
            "alert_id": self.alert_id,
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "drill_case": self.drill_case,
            "trigger_usage_pct": self.trigger_usage_pct,
            "trigger_floor_pct": self.trigger_floor_pct,
            "escalation_floor_pct": self.escalation_floor_pct,
            "replay_age_minutes": self.replay_age_minutes,
            "dedupe_window_minutes": self.dedupe_window_minutes,
            "cooldown_minutes": self.cooldown_minutes,
            "expected_decision": self.expected_decision,
            "observed_decision": self.observed_decision,
            "expected_route": self.expected_route,
            "observed_route": self.observed_route,
            "expected_action": self.expected_action,
            "observed_action": self.observed_action,
            "passed": self.passed,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport:
    generated_at: str
    drill_status: str
    policy_status: str
    rule_count: int
    active_rule_count: int
    scenario_count: int
    passed_count: int
    failed_count: int
    suppressed_count: int
    escalation_preserved_count: int
    expected_scenario_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    scenarios: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeRuleCount": self.active_rule_count,
            "drillStatus": self.drill_status,
            "escalationPreservedCount": self.escalation_preserved_count,
            "expectedScenarioCount": self.expected_scenario_count,
            "failedCount": self.failed_count,
            "generatedAt": self.generated_at,
            "nextActions": list(self.next_actions),
            "passedCount": self.passed_count,
            "policyStatus": self.policy_status,
            "rawIdentifierCount": self.raw_identifier_count,
            "ruleCount": self.rule_count,
            "scenarioCount": self.scenario_count,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "suppressedCount": self.suppressed_count,
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
                "policy_status": self.policy_status,
                "rule_count": self.rule_count,
                "active_rule_count": self.active_rule_count,
                "scenario_count": self.scenario_count,
                "passed_count": self.passed_count,
                "failed_count": self.failed_count,
                "suppressed_count": self.suppressed_count,
                "escalation_preserved_count": self.escalation_preserved_count,
                "expected_scenario_count": self.expected_scenario_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
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


def build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    suppression_policy: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport | None
    ) = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport:
    policy = suppression_policy or (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return (
        build_suppression_policy_drill_report_from_policy(
            policy,
            generated_at=generated_at,
        )
    )


def build_suppression_policy_drill_report_from_policy(
    policy: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport:
    report_date = generated_at or policy.generated_at
    scenarios = tuple(
        scenario
        for rule in policy.rules
        if rule.rule_status == "active"
        for scenario in build_drill_scenarios(rule)
    )
    raw_identifier_count = count_raw_identifier_markers(scenarios)
    tenant_safe = (
        policy.tenant_safe
        and policy.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_count = sum(1 for scenario in scenarios if not scenario.passed)
    expected_scenario_count = policy.active_rule_count * 4
    drill_status = derive_suppression_policy_drill_status(
        policy,
        scenario_count=len(scenarios),
        expected_scenario_count=expected_scenario_count,
        failed_count=failed_count,
        tenant_safe=tenant_safe,
    )
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport(
        generated_at=report_date,
        drill_status=drill_status,
        policy_status=policy.policy_status,
        rule_count=policy.rule_count,
        active_rule_count=policy.active_rule_count,
        scenario_count=len(scenarios),
        passed_count=sum(1 for scenario in scenarios if scenario.passed),
        failed_count=failed_count,
        suppressed_count=sum(
            1
            for scenario in scenarios
            if scenario.observed_decision == SUPPRESSED_DECISION
        ),
        escalation_preserved_count=sum(
            1
            for scenario in scenarios
            if scenario.drill_case == ESCALATION_PRESERVED_CASE
            and scenario.observed_decision == ROUTED_DECISION
        ),
        expected_scenario_count=expected_scenario_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=suppression_policy_drill_next_actions(drill_status),
        scenarios=scenarios,
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_drill_report_from_policy"
] = build_suppression_policy_drill_report_from_policy


def build_drill_scenarios(
    rule: ProductReadinessFreshnessResponseSloDriftSuppressionRule,
) -> tuple[
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario,
    ...,
]:
    return (
        build_drill_scenario(
            rule,
            drill_case=UNDER_THRESHOLD_CASE,
            trigger_usage_pct=max(0, rule.trigger_floor_pct - 1),
            replay_age_minutes=0,
            expected_decision=SUPPRESSED_DECISION,
        ),
        build_drill_scenario(
            rule,
            drill_case=DEDUPE_WINDOW_CASE,
            trigger_usage_pct=rule.trigger_floor_pct,
            replay_age_minutes=max(1, min(10, rule.dedupe_window_minutes - 1)),
            expected_decision=SUPPRESSED_DECISION,
        ),
        build_drill_scenario(
            rule,
            drill_case=COOLDOWN_WINDOW_CASE,
            trigger_usage_pct=rule.trigger_floor_pct,
            replay_age_minutes=max(
                rule.dedupe_window_minutes + 1,
                min(rule.cooldown_minutes - 1, rule.dedupe_window_minutes + 15),
            ),
            expected_decision=SUPPRESSED_DECISION,
        ),
        build_drill_scenario(
            rule,
            drill_case=ESCALATION_PRESERVED_CASE,
            trigger_usage_pct=rule.escalation_floor_pct,
            replay_age_minutes=rule.cooldown_minutes + 1,
            expected_decision=ROUTED_DECISION,
        ),
    )


def build_drill_scenario(
    rule: ProductReadinessFreshnessResponseSloDriftSuppressionRule,
    *,
    drill_case: str,
    trigger_usage_pct: int,
    replay_age_minutes: int,
    expected_decision: str,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario:
    observed_decision = evaluate_policy_decision(
        rule,
        drill_case=drill_case,
        trigger_usage_pct=trigger_usage_pct,
        replay_age_minutes=replay_age_minutes,
    )
    expected_route = rule.route if expected_decision == ROUTED_DECISION else ""
    expected_action = rule.action if expected_decision == ROUTED_DECISION else ""
    observed_route = rule.route if observed_decision == ROUTED_DECISION else ""
    observed_action = rule.action if observed_decision == ROUTED_DECISION else ""
    validation_errors = validate_drill_scenario(
        rule,
        drill_case=drill_case,
        trigger_usage_pct=trigger_usage_pct,
        replay_age_minutes=replay_age_minutes,
        expected_decision=expected_decision,
        observed_decision=observed_decision,
        observed_route=observed_route,
        observed_action=observed_action,
    )
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario(
        drill_id=f"{rule.rule_id}-{drill_case}",
        rule_id=rule.rule_id,
        alert_id=rule.alert_id,
        scenario_id=rule.scenario_id,
        condition=rule.condition,
        drill_case=drill_case,
        trigger_usage_pct=trigger_usage_pct,
        trigger_floor_pct=rule.trigger_floor_pct,
        escalation_floor_pct=rule.escalation_floor_pct,
        replay_age_minutes=replay_age_minutes,
        dedupe_window_minutes=rule.dedupe_window_minutes,
        cooldown_minutes=rule.cooldown_minutes,
        expected_decision=expected_decision,
        observed_decision=observed_decision,
        expected_route=expected_route,
        observed_route=observed_route,
        expected_action=expected_action,
        observed_action=observed_action,
        passed=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=tuple(dict.fromkeys((
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml",
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
            *rule.evidence_refs,
        ))),
    )


def evaluate_policy_decision(
    rule: ProductReadinessFreshnessResponseSloDriftSuppressionRule,
    *,
    drill_case: str,
    trigger_usage_pct: int,
    replay_age_minutes: int,
) -> str:
    if (
        drill_case == ESCALATION_PRESERVED_CASE
        and rule.preserve_escalation
        and trigger_usage_pct >= rule.escalation_floor_pct
    ):
        return ROUTED_DECISION
    if rule.suppress_under_threshold and trigger_usage_pct < rule.trigger_floor_pct:
        return SUPPRESSED_DECISION
    if replay_age_minutes < rule.dedupe_window_minutes:
        return SUPPRESSED_DECISION
    if replay_age_minutes < rule.cooldown_minutes:
        return SUPPRESSED_DECISION
    return ROUTED_DECISION


def validate_drill_scenario(
    rule: ProductReadinessFreshnessResponseSloDriftSuppressionRule,
    *,
    drill_case: str,
    trigger_usage_pct: int,
    replay_age_minutes: int,
    expected_decision: str,
    observed_decision: str,
    observed_route: str,
    observed_action: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if rule.rule_status != "active":
        errors.append(f"expected active rule, observed {rule.rule_status}")
    if not rule.passed:
        errors.append("suppression policy drill requires a passed rule")
    if observed_decision != expected_decision:
        errors.append(
            f"expected decision {expected_decision}, observed {observed_decision}"
        )
    if expected_decision == SUPPRESSED_DECISION and (observed_route or observed_action):
        errors.append("suppressed policy replay must not route or attach an action")
    if expected_decision == ROUTED_DECISION:
        if observed_route != rule.route:
            errors.append(f"expected escalation route {rule.route}, observed {observed_route}")
        if observed_action != rule.action:
            errors.append(
                f"expected escalation action {rule.action}, observed {observed_action}"
            )
    if drill_case == UNDER_THRESHOLD_CASE:
        if trigger_usage_pct >= rule.trigger_floor_pct:
            errors.append("under-threshold drill must replay below trigger floor")
        if not rule.suppress_under_threshold:
            errors.append("under-threshold suppression is not enabled")
    if drill_case == DEDUPE_WINDOW_CASE and (
        replay_age_minutes >= rule.dedupe_window_minutes
    ):
        errors.append("dedupe drill must replay inside the dedupe window")
    if drill_case == COOLDOWN_WINDOW_CASE and not (
        rule.dedupe_window_minutes <= replay_age_minutes < rule.cooldown_minutes
    ):
        errors.append("cooldown drill must replay after dedupe and before cooldown ends")
    if drill_case == ESCALATION_PRESERVED_CASE:
        if trigger_usage_pct < rule.escalation_floor_pct:
            errors.append("escalation drill must replay at or above escalation floor")
        if not rule.preserve_escalation:
            errors.append("escalation preservation is not enabled")
    if not rule.evidence_refs:
        errors.append("suppression policy drill requires rule evidence refs")
    return tuple(errors)


def derive_suppression_policy_drill_status(
    policy: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport,
    *,
    scenario_count: int,
    expected_scenario_count: int,
    failed_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if policy.policy_status != "suppression_policy_codified":
        return "blocked_by_policy"
    if scenario_count != expected_scenario_count or scenario_count == 0:
        return "blocked_by_policy"
    if failed_count:
        return "failed"
    return "passed"


def suppression_policy_drill_next_actions(drill_status: str) -> tuple[str, ...]:
    if drill_status == "passed":
        return (MONITOR_SUPPRESSION_POLICY_EFFECTIVENESS_ACTION,)
    return (EXERCISE_SUPPRESSION_POLICY_DRILL_ACTION,)


def count_raw_identifier_markers(
    scenarios: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillScenario,
        ...,
    ],
) -> int:
    payload = json.dumps(
        [scenario.to_snapshot_dict() for scenario in scenarios],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


def write_product_readiness_freshness_response_slo_drift_suppression_policy_drill_snapshot(
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
            build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_snapshot(
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
