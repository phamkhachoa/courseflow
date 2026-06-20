from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_trends import (
    ProductReadinessFreshnessResponseTrendReport,
    ProductReadinessFreshnessScenarioTrend,
    build_product_readiness_freshness_response_trend_report,
)

REPORT_ID = "product-readiness-freshness-response-slo-drift-alerts-v1"
CONFIGURE_DRIFT_ALERT_ACTION = (
    "configure_product_readiness_response_slo_drift_alerts"
)
EXERCISE_DRIFT_ALERT_DRILL_ACTION = (
    "exercise_product_readiness_response_slo_drift_alert_drill"
)
ALERT_ROUTE = "admin-ops"
ALERT_ACTION = "triage_product_readiness_response_slo_drift"


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftAlert:
    alert_id: str
    scenario_id: str
    condition: str
    scenario_severity: str
    alert_severity: str
    owner_role: str
    route: str
    action: str
    alert_status: str
    threshold_pct: int
    trigger_metric: str
    trigger_usage_pct: int
    watch_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "alertId": self.alert_id,
            "alertSeverity": self.alert_severity,
            "alertStatus": self.alert_status,
            "condition": self.condition,
            "evidenceRefs": list(self.evidence_refs),
            "ownerRole": self.owner_role,
            "route": self.route,
            "scenarioId": self.scenario_id,
            "scenarioSeverity": self.scenario_severity,
            "thresholdPct": self.threshold_pct,
            "triggerMetric": self.trigger_metric,
            "triggerUsagePct": self.trigger_usage_pct,
            "watchReasons": list(self.watch_reasons),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "scenario_severity": self.scenario_severity,
            "alert_severity": self.alert_severity,
            "owner_role": self.owner_role,
            "route": self.route,
            "action": self.action,
            "alert_status": self.alert_status,
            "threshold_pct": self.threshold_pct,
            "trigger_metric": self.trigger_metric,
            "trigger_usage_pct": self.trigger_usage_pct,
            "watch_reasons": list(self.watch_reasons),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftAlertReport:
    generated_at: str
    alert_status: str
    trend_status: str
    watch_count: int
    alert_count: int
    routed_alert_count: int
    p0_alert_count: int
    p1_alert_count: int
    max_trigger_usage_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    alerts: tuple[ProductReadinessFreshnessResponseSloDriftAlert, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertCount": self.alert_count,
            "alerts": [alert.to_dict() for alert in self.alerts],
            "alertStatus": self.alert_status,
            "generatedAt": self.generated_at,
            "maxTriggerUsagePct": self.max_trigger_usage_pct,
            "nextActions": list(self.next_actions),
            "p0AlertCount": self.p0_alert_count,
            "p1AlertCount": self.p1_alert_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "routedAlertCount": self.routed_alert_count,
            "tenantSafe": self.tenant_safe,
            "trendStatus": self.trend_status,
            "watchCount": self.watch_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "alert_status": self.alert_status,
                "trend_status": self.trend_status,
                "watch_count": self.watch_count,
                "alert_count": self.alert_count,
                "routed_alert_count": self.routed_alert_count,
                "p0_alert_count": self.p0_alert_count,
                "p1_alert_count": self.p1_alert_count,
                "max_trigger_usage_pct": self.max_trigger_usage_pct,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "action_queue": {
                "routed": [
                    alert.alert_id
                    for alert in self.alerts
                    if alert.alert_status == "routed"
                ],
                "next_actions": list(self.next_actions),
            },
            "alerts": [alert.to_snapshot_dict() for alert in self.alerts],
        }


def build_product_readiness_freshness_response_slo_drift_alert_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    response_trends: ProductReadinessFreshnessResponseTrendReport | None = None,
) -> ProductReadinessFreshnessResponseSloDriftAlertReport:
    trends = response_trends or build_product_readiness_freshness_response_trend_report(
        ai_root,
        generated_at=generated_at,
    )
    return build_product_readiness_freshness_response_slo_drift_alert_report_from_trends(
        trends,
        generated_at=generated_at,
    )


def build_product_readiness_freshness_response_slo_drift_alert_report_from_trends(
    response_trends: ProductReadinessFreshnessResponseTrendReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftAlertReport:
    report_date = generated_at or response_trends.generated_at
    alerts = tuple(
        build_slo_drift_alert(trend)
        for trend in response_trends.scenario_trends
        if trend.trend_status == "watch"
    )
    routed_alert_count = sum(1 for alert in alerts if alert.alert_status == "routed")
    alert_status = derive_alert_status(
        response_trends,
        alert_count=len(alerts),
        routed_alert_count=routed_alert_count,
    )
    return ProductReadinessFreshnessResponseSloDriftAlertReport(
        generated_at=report_date,
        alert_status=alert_status,
        trend_status=response_trends.trend_status,
        watch_count=response_trends.watch_count,
        alert_count=len(alerts),
        routed_alert_count=routed_alert_count,
        p0_alert_count=sum(1 for alert in alerts if alert.alert_severity == "p0"),
        p1_alert_count=sum(1 for alert in alerts if alert.alert_severity == "p1"),
        max_trigger_usage_pct=max(
            (alert.trigger_usage_pct for alert in alerts),
            default=0,
        ),
        tenant_safe=response_trends.tenant_safe,
        raw_identifier_count=response_trends.raw_identifier_count,
        next_actions=alert_next_actions(alert_status),
        alerts=alerts,
    )


def build_slo_drift_alert(
    trend: ProductReadinessFreshnessScenarioTrend,
) -> ProductReadinessFreshnessResponseSloDriftAlert:
    trigger_metric, trigger_usage_pct = strongest_trigger_metric(trend)
    return ProductReadinessFreshnessResponseSloDriftAlert(
        alert_id=f"prf-response-slo-drift-{trend.scenario_id}",
        scenario_id=trend.scenario_id,
        condition=trend.condition,
        scenario_severity=trend.severity,
        alert_severity=alert_severity_for_scenario(trend.severity),
        owner_role=trend.owner_role,
        route=ALERT_ROUTE,
        action=ALERT_ACTION,
        alert_status="routed",
        threshold_pct=80,
        trigger_metric=trigger_metric,
        trigger_usage_pct=trigger_usage_pct,
        watch_reasons=trend.watch_reasons,
        evidence_refs=(
            "platform/operations/reports/"
            "product-readiness-freshness-response-trends-v1.yaml",
            *trend.evidence_refs,
        ),
    )


def derive_alert_status(
    response_trends: ProductReadinessFreshnessResponseTrendReport,
    *,
    alert_count: int,
    routed_alert_count: int,
) -> str:
    if not response_trends.tenant_safe or response_trends.raw_identifier_count:
        return "blocked_by_tenant_safety"
    if response_trends.trend_status not in {
        "trend_ready",
        "trend_ready_with_watch",
    }:
        return "blocked_by_response_trends"
    if alert_count != response_trends.watch_count or routed_alert_count != alert_count:
        return "alerts_incomplete"
    if alert_count:
        return "alerts_configured_with_watch"
    return "alerts_configured"


def alert_next_actions(alert_status: str) -> tuple[str, ...]:
    if alert_status in {"alerts_configured", "alerts_configured_with_watch"}:
        return (EXERCISE_DRIFT_ALERT_DRILL_ACTION,)
    return (CONFIGURE_DRIFT_ALERT_ACTION,)


def strongest_trigger_metric(
    trend: ProductReadinessFreshnessScenarioTrend,
) -> tuple[str, int]:
    usage = (
        ("acknowledge", trend.acknowledge_slo_usage_pct),
        ("contain", trend.contain_slo_usage_pct),
        ("recover", trend.recover_slo_usage_pct),
        ("close", trend.close_slo_usage_pct),
    )
    return max(usage, key=lambda item: item[1])


def alert_severity_for_scenario(scenario_severity: str) -> str:
    if scenario_severity == "p0":
        return "p1"
    if scenario_severity == "p1":
        return "p2"
    return "p3"


def build_product_readiness_freshness_response_slo_drift_alert_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_product_readiness_freshness_response_slo_drift_alert_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_product_readiness_freshness_response_slo_drift_alert_snapshot(
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
            build_product_readiness_freshness_response_slo_drift_alert_snapshot(
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
