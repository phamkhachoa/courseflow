from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alert_drill import (
    MONITOR_ALERT_CALIBRATION_ACTION,
    ProductReadinessFreshnessResponseSloDriftAlertDrillReport,
    ProductReadinessFreshnessResponseSloDriftAlertDrillScenario,
    build_product_readiness_freshness_response_slo_drift_alert_drill_report,
)

REPORT_ID = "product-readiness-freshness-response-slo-drift-alert-calibration-v1"
CODIFY_ALERT_SUPPRESSION_POLICY_ACTION = (
    "codify_product_readiness_response_slo_drift_alert_suppression_policy"
)
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")
WATCH_MARGIN_MIN_PCT = 0
WATCH_MARGIN_MAX_PCT = 20


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem:
    calibration_id: str
    alert_id: str
    scenario_id: str
    condition: str
    route: str
    action: str
    trigger_metric: str
    trigger_usage_pct: int
    threshold_pct: int
    margin_pct: int
    calibration_status: str
    noise_status: str
    escalation_status: str
    passed: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "alertId": self.alert_id,
            "calibrationId": self.calibration_id,
            "calibrationStatus": self.calibration_status,
            "condition": self.condition,
            "escalationStatus": self.escalation_status,
            "evidenceRefs": list(self.evidence_refs),
            "marginPct": self.margin_pct,
            "noiseStatus": self.noise_status,
            "passed": self.passed,
            "route": self.route,
            "scenarioId": self.scenario_id,
            "thresholdPct": self.threshold_pct,
            "triggerMetric": self.trigger_metric,
            "triggerUsagePct": self.trigger_usage_pct,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "alert_id": self.alert_id,
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "route": self.route,
            "action": self.action,
            "trigger_metric": self.trigger_metric,
            "trigger_usage_pct": self.trigger_usage_pct,
            "threshold_pct": self.threshold_pct,
            "margin_pct": self.margin_pct,
            "calibration_status": self.calibration_status,
            "noise_status": self.noise_status,
            "escalation_status": self.escalation_status,
            "passed": self.passed,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport:
    generated_at: str
    calibration_status: str
    drill_status: str
    alert_count: int
    routed_alert_count: int
    scenario_count: int
    calibrated_count: int
    failed_count: int
    noisy_alert_count: int
    under_threshold_count: int
    escalation_required_count: int
    max_margin_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    items: tuple[ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertCount": self.alert_count,
            "calibratedCount": self.calibrated_count,
            "calibrationStatus": self.calibration_status,
            "drillStatus": self.drill_status,
            "escalationRequiredCount": self.escalation_required_count,
            "failedCount": self.failed_count,
            "generatedAt": self.generated_at,
            "items": [item.to_dict() for item in self.items],
            "maxMarginPct": self.max_margin_pct,
            "nextActions": list(self.next_actions),
            "noisyAlertCount": self.noisy_alert_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "routedAlertCount": self.routed_alert_count,
            "scenarioCount": self.scenario_count,
            "tenantSafe": self.tenant_safe,
            "underThresholdCount": self.under_threshold_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "calibration_status": self.calibration_status,
                "drill_status": self.drill_status,
                "alert_count": self.alert_count,
                "routed_alert_count": self.routed_alert_count,
                "scenario_count": self.scenario_count,
                "calibrated_count": self.calibrated_count,
                "failed_count": self.failed_count,
                "noisy_alert_count": self.noisy_alert_count,
                "under_threshold_count": self.under_threshold_count,
                "escalation_required_count": self.escalation_required_count,
                "max_margin_pct": self.max_margin_pct,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "action_queue": {
                "calibrated": [
                    item.calibration_id for item in self.items if item.passed
                ],
                "blocked": [
                    item.calibration_id for item in self.items if not item.passed
                ],
                "next_actions": list(self.next_actions),
            },
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    alert_drill: ProductReadinessFreshnessResponseSloDriftAlertDrillReport | None = None,
) -> ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport:
    drill = alert_drill or (
        build_product_readiness_freshness_response_slo_drift_alert_drill_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return (
        build_product_readiness_freshness_response_slo_drift_alert_calibration_report_from_drill(
            drill,
            generated_at=generated_at,
        )
    )


def build_product_readiness_freshness_response_slo_drift_alert_calibration_report_from_drill(
    alert_drill: ProductReadinessFreshnessResponseSloDriftAlertDrillReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport:
    report_date = generated_at or alert_drill.generated_at
    items = tuple(build_calibration_item(scenario) for scenario in alert_drill.scenarios)
    raw_identifier_count = count_raw_identifier_markers(items)
    tenant_safe = (
        alert_drill.tenant_safe
        and alert_drill.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_count = sum(1 for item in items if not item.passed)
    noisy_alert_count = sum(1 for item in items if item.noise_status == "noisy")
    under_threshold_count = sum(
        1 for item in items if item.calibration_status == "under_threshold"
    )
    escalation_required_count = sum(
        1 for item in items if item.escalation_status == "escalation_required"
    )
    calibration_status = derive_calibration_status(
        alert_drill,
        failed_count=failed_count,
        noisy_alert_count=noisy_alert_count,
        under_threshold_count=under_threshold_count,
        tenant_safe=tenant_safe,
    )
    return ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport(
        generated_at=report_date,
        calibration_status=calibration_status,
        drill_status=alert_drill.drill_status,
        alert_count=alert_drill.alert_count,
        routed_alert_count=alert_drill.routed_alert_count,
        scenario_count=alert_drill.scenario_count,
        calibrated_count=sum(1 for item in items if item.passed),
        failed_count=failed_count,
        noisy_alert_count=noisy_alert_count,
        under_threshold_count=under_threshold_count,
        escalation_required_count=escalation_required_count,
        max_margin_pct=max((item.margin_pct for item in items), default=0),
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=calibration_next_actions(calibration_status),
        items=items,
    )


def build_calibration_item(
    scenario: ProductReadinessFreshnessResponseSloDriftAlertDrillScenario,
) -> ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem:
    margin_pct = scenario.trigger_usage_pct - scenario.threshold_pct
    calibration_status = item_calibration_status(scenario, margin_pct)
    noise_status = item_noise_status(calibration_status, margin_pct)
    escalation_status = item_escalation_status(scenario.trigger_usage_pct)
    validation_errors = validate_calibration_item(
        scenario,
        calibration_status=calibration_status,
        noise_status=noise_status,
        escalation_status=escalation_status,
    )
    return ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem(
        calibration_id=f"{scenario.alert_id}-calibration",
        alert_id=scenario.alert_id,
        scenario_id=scenario.scenario_id,
        condition=scenario.condition,
        route=scenario.observed_route,
        action=scenario.observed_action,
        trigger_metric=scenario.trigger_metric,
        trigger_usage_pct=scenario.trigger_usage_pct,
        threshold_pct=scenario.threshold_pct,
        margin_pct=margin_pct,
        calibration_status=calibration_status,
        noise_status=noise_status,
        escalation_status=escalation_status,
        passed=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=tuple(dict.fromkeys((
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alerts-v1.yaml",
            "platform/operations/reports/"
            "product-readiness-freshness-response-trends-v1.yaml",
            *scenario.evidence_refs,
        ))),
    )


def item_calibration_status(
    scenario: ProductReadinessFreshnessResponseSloDriftAlertDrillScenario,
    margin_pct: int,
) -> str:
    if not scenario.passed:
        return "blocked_by_drill"
    if margin_pct < WATCH_MARGIN_MIN_PCT:
        return "under_threshold"
    if margin_pct > WATCH_MARGIN_MAX_PCT:
        return "over_sensitive"
    return "calibrated_watch"


def item_noise_status(calibration_status: str, margin_pct: int) -> str:
    if calibration_status == "over_sensitive" or margin_pct > WATCH_MARGIN_MAX_PCT:
        return "noisy"
    if calibration_status == "under_threshold":
        return "missed"
    return "quiet"


def item_escalation_status(trigger_usage_pct: int) -> str:
    if trigger_usage_pct >= 100:
        return "escalation_required"
    return "watch_only"


def validate_calibration_item(
    scenario: ProductReadinessFreshnessResponseSloDriftAlertDrillScenario,
    *,
    calibration_status: str,
    noise_status: str,
    escalation_status: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not scenario.passed:
        errors.append("alert drill must pass before calibration can pass")
    if calibration_status != "calibrated_watch":
        errors.append(f"expected calibrated_watch, observed {calibration_status}")
    if noise_status != "quiet":
        errors.append(f"expected quiet noise status, observed {noise_status}")
    if escalation_status != "watch_only":
        errors.append(f"expected watch_only escalation, observed {escalation_status}")
    return tuple(errors)


def derive_calibration_status(
    alert_drill: ProductReadinessFreshnessResponseSloDriftAlertDrillReport,
    *,
    failed_count: int,
    noisy_alert_count: int,
    under_threshold_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if alert_drill.drill_status != "passed":
        return "blocked_by_alert_drill"
    if failed_count:
        return "calibration_failed"
    if noisy_alert_count or under_threshold_count:
        return "calibration_needs_tuning"
    return "calibrated_with_watch"


def calibration_next_actions(calibration_status: str) -> tuple[str, ...]:
    if calibration_status == "calibrated_with_watch":
        return (CODIFY_ALERT_SUPPRESSION_POLICY_ACTION,)
    return (MONITOR_ALERT_CALIBRATION_ACTION,)


def count_raw_identifier_markers(
    items: tuple[ProductReadinessFreshnessResponseSloDriftAlertCalibrationItem, ...],
) -> int:
    payload = json.dumps(
        [item.to_snapshot_dict() for item in items],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_product_readiness_freshness_response_slo_drift_alert_calibration_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_product_readiness_freshness_response_slo_drift_alert_calibration_snapshot(
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
            build_product_readiness_freshness_response_slo_drift_alert_calibration_snapshot(
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
