from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .product_readiness_freshness_response_slo_drift_alert_calibration import (
    CODIFY_ALERT_SUPPRESSION_POLICY_ACTION,
    ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem,
    ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport,
    build_product_readiness_freshness_response_slo_drift_alert_calibration_report,
)

REPORT_ID = "product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1"
EXERCISE_SUPPRESSION_POLICY_DRILL_ACTION = (
    "exercise_product_readiness_response_slo_drift_suppression_policy_drill"
)
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")
DEDUPE_WINDOW_MINUTES = 30
COOLDOWN_MINUTES = 60
ESCALATION_FLOOR_PCT = 100


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionRule:
    rule_id: str
    alert_id: str
    scenario_id: str
    condition: str
    route: str
    action: str
    policy_mode: str
    trigger_floor_pct: int
    escalation_floor_pct: int
    dedupe_window_minutes: int
    cooldown_minutes: int
    preserve_escalation: bool
    suppress_under_threshold: bool
    rule_status: str
    passed: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "alertId": self.alert_id,
            "condition": self.condition,
            "cooldownMinutes": self.cooldown_minutes,
            "dedupeWindowMinutes": self.dedupe_window_minutes,
            "escalationFloorPct": self.escalation_floor_pct,
            "evidenceRefs": list(self.evidence_refs),
            "passed": self.passed,
            "policyMode": self.policy_mode,
            "preserveEscalation": self.preserve_escalation,
            "route": self.route,
            "ruleId": self.rule_id,
            "ruleStatus": self.rule_status,
            "scenarioId": self.scenario_id,
            "suppressUnderThreshold": self.suppress_under_threshold,
            "triggerFloorPct": self.trigger_floor_pct,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "alert_id": self.alert_id,
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "route": self.route,
            "action": self.action,
            "policy_mode": self.policy_mode,
            "trigger_floor_pct": self.trigger_floor_pct,
            "escalation_floor_pct": self.escalation_floor_pct,
            "dedupe_window_minutes": self.dedupe_window_minutes,
            "cooldown_minutes": self.cooldown_minutes,
            "preserve_escalation": self.preserve_escalation,
            "suppress_under_threshold": self.suppress_under_threshold,
            "rule_status": self.rule_status,
            "passed": self.passed,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport:
    generated_at: str
    policy_status: str
    calibration_status: str
    rule_count: int
    active_rule_count: int
    failed_rule_count: int
    dedupe_window_minutes: int
    cooldown_minutes: int
    escalation_floor_pct: int
    preserve_escalation_count: int
    suppress_under_threshold_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    rules: tuple[ProductReadinessFreshnessResponseSloDriftSuppressionRule, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeRuleCount": self.active_rule_count,
            "calibrationStatus": self.calibration_status,
            "cooldownMinutes": self.cooldown_minutes,
            "dedupeWindowMinutes": self.dedupe_window_minutes,
            "escalationFloorPct": self.escalation_floor_pct,
            "failedRuleCount": self.failed_rule_count,
            "generatedAt": self.generated_at,
            "nextActions": list(self.next_actions),
            "policyStatus": self.policy_status,
            "preserveEscalationCount": self.preserve_escalation_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "ruleCount": self.rule_count,
            "rules": [rule.to_dict() for rule in self.rules],
            "suppressUnderThresholdCount": self.suppress_under_threshold_count,
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "policy_status": self.policy_status,
                "calibration_status": self.calibration_status,
                "rule_count": self.rule_count,
                "active_rule_count": self.active_rule_count,
                "failed_rule_count": self.failed_rule_count,
                "dedupe_window_minutes": self.dedupe_window_minutes,
                "cooldown_minutes": self.cooldown_minutes,
                "escalation_floor_pct": self.escalation_floor_pct,
                "preserve_escalation_count": self.preserve_escalation_count,
                "suppress_under_threshold_count": (
                    self.suppress_under_threshold_count
                ),
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "action_queue": {
                "active": [
                    rule.rule_id for rule in self.rules if rule.rule_status == "active"
                ],
                "blocked": [
                    rule.rule_id for rule in self.rules if not rule.passed
                ],
                "next_actions": list(self.next_actions),
            },
            "rules": [rule.to_snapshot_dict() for rule in self.rules],
        }


def build_product_readiness_freshness_response_slo_drift_suppression_policy_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    calibration: (
        ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport | None
    ) = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport:
    calibration_report = calibration or (
        build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_report_from_calibration(
            calibration_report,
            generated_at=generated_at,
        )
    )


def build_product_readiness_freshness_response_slo_drift_suppression_policy_report_from_calibration(
    calibration: ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport:
    report_date = generated_at or calibration.generated_at
    rules = tuple(build_suppression_rule(item) for item in calibration.items)
    raw_identifier_count = count_raw_identifier_markers(rules)
    tenant_safe = (
        calibration.tenant_safe
        and calibration.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_rule_count = sum(1 for rule in rules if not rule.passed)
    policy_status = derive_policy_status(
        calibration,
        failed_rule_count=failed_rule_count,
        tenant_safe=tenant_safe,
    )
    active_rule_count = sum(1 for rule in rules if rule.rule_status == "active")
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport(
        generated_at=report_date,
        policy_status=policy_status,
        calibration_status=calibration.calibration_status,
        rule_count=len(rules),
        active_rule_count=active_rule_count,
        failed_rule_count=failed_rule_count,
        dedupe_window_minutes=DEDUPE_WINDOW_MINUTES,
        cooldown_minutes=COOLDOWN_MINUTES,
        escalation_floor_pct=ESCALATION_FLOOR_PCT,
        preserve_escalation_count=sum(
            1 for rule in rules if rule.preserve_escalation
        ),
        suppress_under_threshold_count=sum(
            1 for rule in rules if rule.suppress_under_threshold
        ),
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=policy_next_actions(policy_status),
        rules=rules,
    )


def build_suppression_rule(
    item: ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionRule:
    validation_errors = validate_suppression_rule(item)
    return ProductReadinessFreshnessResponseSloDriftSuppressionRule(
        rule_id=f"{item.alert_id}-suppression-policy",
        alert_id=item.alert_id,
        scenario_id=item.scenario_id,
        condition=item.condition,
        route=item.route,
        action=item.action,
        policy_mode="dedupe_watch_noise",
        trigger_floor_pct=item.threshold_pct,
        escalation_floor_pct=ESCALATION_FLOOR_PCT,
        dedupe_window_minutes=DEDUPE_WINDOW_MINUTES,
        cooldown_minutes=COOLDOWN_MINUTES,
        preserve_escalation=True,
        suppress_under_threshold=True,
        rule_status="active" if not validation_errors else "blocked",
        passed=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=tuple(dict.fromkeys((
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
            *item.evidence_refs,
        ))),
    )


def validate_suppression_rule(
    item: ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not item.passed:
        errors.append("alert calibration must pass before policy can be active")
    if item.calibration_status != "calibrated_watch":
        errors.append(
            f"expected calibrated_watch, observed {item.calibration_status}"
        )
    if item.noise_status != "quiet":
        errors.append(f"expected quiet noise status, observed {item.noise_status}")
    if item.escalation_status != "watch_only":
        errors.append(
            f"expected watch_only escalation status, observed {item.escalation_status}"
        )
    if item.threshold_pct >= ESCALATION_FLOOR_PCT:
        errors.append("trigger floor must remain below escalation floor")
    if item.margin_pct < 0:
        errors.append("policy cannot suppress an alert below threshold")
    return tuple(errors)


def derive_policy_status(
    calibration: ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport,
    *,
    failed_rule_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if calibration.calibration_status != "calibrated_with_watch":
        return "blocked_by_calibration"
    if failed_rule_count:
        return "policy_failed"
    return "suppression_policy_codified"


def policy_next_actions(policy_status: str) -> tuple[str, ...]:
    if policy_status == "suppression_policy_codified":
        return (EXERCISE_SUPPRESSION_POLICY_DRILL_ACTION,)
    return (CODIFY_ALERT_SUPPRESSION_POLICY_ACTION,)


def count_raw_identifier_markers(
    rules: tuple[ProductReadinessFreshnessResponseSloDriftSuppressionRule, ...],
) -> int:
    payload = json.dumps(
        [rule.to_snapshot_dict() for rule in rules],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_product_readiness_freshness_response_slo_drift_suppression_policy_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_product_readiness_freshness_response_slo_drift_suppression_policy_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_product_readiness_freshness_response_slo_drift_suppression_policy_snapshot(
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
            build_product_readiness_freshness_response_slo_drift_suppression_policy_snapshot(
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
