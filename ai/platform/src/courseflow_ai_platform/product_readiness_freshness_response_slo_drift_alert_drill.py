from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alerts import (
    ALERT_ACTION,
    ALERT_ROUTE,
    EXERCISE_DRIFT_ALERT_DRILL_ACTION,
    ProductReadinessFreshnessResponseSloDriftAlert,
    ProductReadinessFreshnessResponseSloDriftAlertReport,
    build_product_readiness_freshness_response_slo_drift_alert_report,
)

REPORT_ID = "product-readiness-freshness-response-slo-drift-alert-drill-v1"
MONITOR_ALERT_CALIBRATION_ACTION = (
    "monitor_product_readiness_response_slo_drift_alert_calibration"
)
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftAlertDrillScenario:
    drill_id: str
    alert_id: str
    scenario_id: str
    condition: str
    expected_route: str
    observed_route: str
    expected_action: str
    observed_action: str
    expected_alert_status: str
    observed_alert_status: str
    expected_alert_severity: str
    observed_alert_severity: str
    trigger_metric: str
    trigger_usage_pct: int
    threshold_pct: int
    passed: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertId": self.alert_id,
            "condition": self.condition,
            "drillId": self.drill_id,
            "evidenceRefs": list(self.evidence_refs),
            "expectedAction": self.expected_action,
            "expectedAlertSeverity": self.expected_alert_severity,
            "expectedAlertStatus": self.expected_alert_status,
            "expectedRoute": self.expected_route,
            "observedAction": self.observed_action,
            "observedAlertSeverity": self.observed_alert_severity,
            "observedAlertStatus": self.observed_alert_status,
            "observedRoute": self.observed_route,
            "passed": self.passed,
            "scenarioId": self.scenario_id,
            "thresholdPct": self.threshold_pct,
            "triggerMetric": self.trigger_metric,
            "triggerUsagePct": self.trigger_usage_pct,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "drill_id": self.drill_id,
            "alert_id": self.alert_id,
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "expected_route": self.expected_route,
            "observed_route": self.observed_route,
            "expected_action": self.expected_action,
            "observed_action": self.observed_action,
            "expected_alert_status": self.expected_alert_status,
            "observed_alert_status": self.observed_alert_status,
            "expected_alert_severity": self.expected_alert_severity,
            "observed_alert_severity": self.observed_alert_severity,
            "trigger_metric": self.trigger_metric,
            "trigger_usage_pct": self.trigger_usage_pct,
            "threshold_pct": self.threshold_pct,
            "passed": self.passed,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftAlertDrillReport:
    generated_at: str
    drill_status: str
    alert_status: str
    alert_count: int
    routed_alert_count: int
    scenario_count: int
    passed_count: int
    failed_count: int
    max_trigger_usage_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    scenarios: tuple[ProductReadinessFreshnessResponseSloDriftAlertDrillScenario, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertCount": self.alert_count,
            "alertStatus": self.alert_status,
            "drillStatus": self.drill_status,
            "failedCount": self.failed_count,
            "generatedAt": self.generated_at,
            "maxTriggerUsagePct": self.max_trigger_usage_pct,
            "nextActions": list(self.next_actions),
            "passedCount": self.passed_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "routedAlertCount": self.routed_alert_count,
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
                "alert_status": self.alert_status,
                "alert_count": self.alert_count,
                "routed_alert_count": self.routed_alert_count,
                "scenario_count": self.scenario_count,
                "passed_count": self.passed_count,
                "failed_count": self.failed_count,
                "max_trigger_usage_pct": self.max_trigger_usage_pct,
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


def build_product_readiness_freshness_response_slo_drift_alert_drill_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    response_alerts: ProductReadinessFreshnessResponseSloDriftAlertReport | None = None,
) -> ProductReadinessFreshnessResponseSloDriftAlertDrillReport:
    alerts = response_alerts or (
        build_product_readiness_freshness_response_slo_drift_alert_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return (
        build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts(
            alerts,
            generated_at=generated_at,
        )
    )


def build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts(
    response_alerts: ProductReadinessFreshnessResponseSloDriftAlertReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftAlertDrillReport:
    report_date = generated_at or response_alerts.generated_at
    scenarios = tuple(
        build_alert_drill_scenario(alert)
        for alert in response_alerts.alerts
        if alert.alert_status == "routed"
    )
    raw_identifier_count = count_raw_identifier_markers(scenarios)
    tenant_safe = (
        response_alerts.tenant_safe
        and response_alerts.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_count = sum(1 for scenario in scenarios if not scenario.passed)
    drill_status = derive_alert_drill_status(
        response_alerts,
        failed_count=failed_count,
        tenant_safe=tenant_safe,
    )
    return ProductReadinessFreshnessResponseSloDriftAlertDrillReport(
        generated_at=report_date,
        drill_status=drill_status,
        alert_status=response_alerts.alert_status,
        alert_count=response_alerts.alert_count,
        routed_alert_count=response_alerts.routed_alert_count,
        scenario_count=len(scenarios),
        passed_count=sum(1 for scenario in scenarios if scenario.passed),
        failed_count=failed_count,
        max_trigger_usage_pct=max(
            (scenario.trigger_usage_pct for scenario in scenarios),
            default=0,
        ),
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=alert_drill_next_actions(drill_status),
        scenarios=scenarios,
    )


def build_alert_drill_scenario(
    alert: ProductReadinessFreshnessResponseSloDriftAlert,
) -> ProductReadinessFreshnessResponseSloDriftAlertDrillScenario:
    expected_severity = expected_alert_severity(alert.scenario_severity)
    validation_errors = validate_alert_for_drill(
        alert,
        expected_alert_severity=expected_severity,
    )
    return ProductReadinessFreshnessResponseSloDriftAlertDrillScenario(
        drill_id=f"{alert.alert_id}-drill",
        alert_id=alert.alert_id,
        scenario_id=alert.scenario_id,
        condition=alert.condition,
        expected_route=ALERT_ROUTE,
        observed_route=alert.route,
        expected_action=ALERT_ACTION,
        observed_action=alert.action,
        expected_alert_status="routed",
        observed_alert_status=alert.alert_status,
        expected_alert_severity=expected_severity,
        observed_alert_severity=alert.alert_severity,
        trigger_metric=alert.trigger_metric,
        trigger_usage_pct=alert.trigger_usage_pct,
        threshold_pct=alert.threshold_pct,
        passed=not validation_errors,
        validation_errors=validation_errors,
        evidence_refs=tuple(dict.fromkeys((
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alerts-v1.yaml",
            "platform/operations/reports/"
            "product-readiness-freshness-response-trends-v1.yaml",
            "platform/operations/reports/admin-ops-dashboard-v1.html",
            *alert.evidence_refs,
        ))),
    )


def validate_alert_for_drill(
    alert: ProductReadinessFreshnessResponseSloDriftAlert,
    *,
    expected_alert_severity: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if alert.alert_status != "routed":
        errors.append(f"expected routed alert, observed {alert.alert_status}")
    if alert.route != ALERT_ROUTE:
        errors.append(f"expected route {ALERT_ROUTE}, observed {alert.route}")
    if alert.action != ALERT_ACTION:
        errors.append(f"expected action {ALERT_ACTION}, observed {alert.action}")
    if alert.alert_severity != expected_alert_severity:
        errors.append(
            "expected alert severity "
            f"{expected_alert_severity}, observed {alert.alert_severity}"
        )
    if alert.trigger_usage_pct < alert.threshold_pct:
        errors.append(
            "trigger usage must be greater than or equal to the drift threshold"
        )
    if not alert.watch_reasons:
        errors.append("alert drill requires trend watch reasons")
    if not alert.evidence_refs:
        errors.append("alert drill requires evidence refs")
    return tuple(errors)


def derive_alert_drill_status(
    response_alerts: ProductReadinessFreshnessResponseSloDriftAlertReport,
    *,
    failed_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if response_alerts.alert_status not in {
        "alerts_configured",
        "alerts_configured_with_watch",
    }:
        return "blocked_by_alerts"
    if response_alerts.routed_alert_count != response_alerts.alert_count:
        return "blocked_by_unrouted_alerts"
    if failed_count:
        return "failed"
    return "passed"


def alert_drill_next_actions(drill_status: str) -> tuple[str, ...]:
    if drill_status == "passed":
        return (MONITOR_ALERT_CALIBRATION_ACTION,)
    return (EXERCISE_DRIFT_ALERT_DRILL_ACTION,)


def expected_alert_severity(scenario_severity: str) -> str:
    if scenario_severity == "p0":
        return "p1"
    if scenario_severity == "p1":
        return "p2"
    return "p3"


def count_raw_identifier_markers(
    scenarios: tuple[ProductReadinessFreshnessResponseSloDriftAlertDrillScenario, ...],
) -> int:
    payload = json.dumps(
        [scenario.to_snapshot_dict() for scenario in scenarios],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_product_readiness_freshness_response_slo_drift_alert_drill_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_product_readiness_freshness_response_slo_drift_alert_drill_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_product_readiness_freshness_response_slo_drift_alert_drill_snapshot(
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
            build_product_readiness_freshness_response_slo_drift_alert_drill_snapshot(
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
