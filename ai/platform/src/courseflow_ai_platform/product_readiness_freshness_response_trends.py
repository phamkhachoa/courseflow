from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_metrics import (
    ProductReadinessFreshnessResponseMetricItem,
    ProductReadinessFreshnessResponseMetricsReport,
    build_product_readiness_freshness_response_metrics_report,
)

REPORT_ID = "product-readiness-freshness-response-trends-v1"
TREND_BY_OWNER_ACTION = "trend_product_readiness_freshness_response_slo_by_owner"
CONFIGURE_DRIFT_ALERT_ACTION = (
    "configure_product_readiness_response_slo_drift_alerts"
)
SLO_USAGE_WATCH_PERCENT = 80


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessScenarioTrend:
    scenario_id: str
    condition: str
    severity: str
    owner_role: str
    measurement_source: str
    metric_status: str
    acknowledge_minutes: int
    acknowledge_slo_minutes: int
    acknowledge_slo_usage_pct: int
    contain_minutes: int
    contain_slo_minutes: int
    contain_slo_usage_pct: int
    recover_minutes: int
    recover_slo_minutes: int
    recover_slo_usage_pct: int
    close_minutes: int
    close_slo_minutes: int
    close_slo_usage_pct: int
    trend_status: str
    watch_reasons: tuple[str, ...]
    breach_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "acknowledgeMinutes": self.acknowledge_minutes,
            "acknowledgeSloMinutes": self.acknowledge_slo_minutes,
            "acknowledgeSloUsagePct": self.acknowledge_slo_usage_pct,
            "breachReasons": list(self.breach_reasons),
            "closeMinutes": self.close_minutes,
            "closeSloMinutes": self.close_slo_minutes,
            "closeSloUsagePct": self.close_slo_usage_pct,
            "condition": self.condition,
            "containMinutes": self.contain_minutes,
            "containSloMinutes": self.contain_slo_minutes,
            "containSloUsagePct": self.contain_slo_usage_pct,
            "evidenceRefs": list(self.evidence_refs),
            "measurementSource": self.measurement_source,
            "metricStatus": self.metric_status,
            "ownerRole": self.owner_role,
            "recoverMinutes": self.recover_minutes,
            "recoverSloMinutes": self.recover_slo_minutes,
            "recoverSloUsagePct": self.recover_slo_usage_pct,
            "scenarioId": self.scenario_id,
            "severity": self.severity,
            "trendStatus": self.trend_status,
            "watchReasons": list(self.watch_reasons),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "severity": self.severity,
            "owner_role": self.owner_role,
            "measurement_source": self.measurement_source,
            "metric_status": self.metric_status,
            "acknowledge_minutes": self.acknowledge_minutes,
            "acknowledge_slo_minutes": self.acknowledge_slo_minutes,
            "acknowledge_slo_usage_pct": self.acknowledge_slo_usage_pct,
            "contain_minutes": self.contain_minutes,
            "contain_slo_minutes": self.contain_slo_minutes,
            "contain_slo_usage_pct": self.contain_slo_usage_pct,
            "recover_minutes": self.recover_minutes,
            "recover_slo_minutes": self.recover_slo_minutes,
            "recover_slo_usage_pct": self.recover_slo_usage_pct,
            "close_minutes": self.close_minutes,
            "close_slo_minutes": self.close_slo_minutes,
            "close_slo_usage_pct": self.close_slo_usage_pct,
            "trend_status": self.trend_status,
            "watch_reasons": list(self.watch_reasons),
            "breach_reasons": list(self.breach_reasons),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessOwnerTrend:
    owner_role: str
    trend_status: str
    scenario_count: int
    p0_count: int
    p1_count: int
    breach_count: int
    watch_count: int
    live_observation_count: int
    max_recover_slo_usage_pct: int
    max_close_slo_usage_pct: int
    average_recover_minutes: int
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "averageRecoverMinutes": self.average_recover_minutes,
            "breachCount": self.breach_count,
            "evidenceRefs": list(self.evidence_refs),
            "liveObservationCount": self.live_observation_count,
            "maxCloseSloUsagePct": self.max_close_slo_usage_pct,
            "maxRecoverSloUsagePct": self.max_recover_slo_usage_pct,
            "ownerRole": self.owner_role,
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "scenarioCount": self.scenario_count,
            "trendStatus": self.trend_status,
            "watchCount": self.watch_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "owner_role": self.owner_role,
            "trend_status": self.trend_status,
            "scenario_count": self.scenario_count,
            "p0_count": self.p0_count,
            "p1_count": self.p1_count,
            "breach_count": self.breach_count,
            "watch_count": self.watch_count,
            "live_observation_count": self.live_observation_count,
            "max_recover_slo_usage_pct": self.max_recover_slo_usage_pct,
            "max_close_slo_usage_pct": self.max_close_slo_usage_pct,
            "average_recover_minutes": self.average_recover_minutes,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseTrendReport:
    generated_at: str
    trend_status: str
    metrics_status: str
    ingest_status: str
    owner_count: int
    scenario_class_count: int
    live_observation_count: int
    breach_count: int
    watch_count: int
    p0_count: int
    p1_count: int
    max_recover_slo_usage_pct: int
    max_close_slo_usage_pct: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    owner_trends: tuple[ProductReadinessFreshnessOwnerTrend, ...]
    scenario_trends: tuple[ProductReadinessFreshnessScenarioTrend, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "breachCount": self.breach_count,
            "generatedAt": self.generated_at,
            "ingestStatus": self.ingest_status,
            "liveObservationCount": self.live_observation_count,
            "maxCloseSloUsagePct": self.max_close_slo_usage_pct,
            "maxRecoverSloUsagePct": self.max_recover_slo_usage_pct,
            "metricsStatus": self.metrics_status,
            "nextActions": list(self.next_actions),
            "ownerCount": self.owner_count,
            "ownerTrends": [trend.to_dict() for trend in self.owner_trends],
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "scenarioClassCount": self.scenario_class_count,
            "scenarioTrends": [trend.to_dict() for trend in self.scenario_trends],
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
                "trend_status": self.trend_status,
                "metrics_status": self.metrics_status,
                "ingest_status": self.ingest_status,
                "owner_count": self.owner_count,
                "scenario_class_count": self.scenario_class_count,
                "live_observation_count": self.live_observation_count,
                "breach_count": self.breach_count,
                "watch_count": self.watch_count,
                "p0_count": self.p0_count,
                "p1_count": self.p1_count,
                "max_recover_slo_usage_pct": self.max_recover_slo_usage_pct,
                "max_close_slo_usage_pct": self.max_close_slo_usage_pct,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "action_queue": {
                "blocked": [
                    trend.scenario_id
                    for trend in self.scenario_trends
                    if trend.trend_status == "slo_breached"
                ],
                "watch": [
                    trend.scenario_id
                    for trend in self.scenario_trends
                    if trend.trend_status == "watch"
                ],
                "by_owner": [trend.owner_role for trend in self.owner_trends],
                "next_actions": list(self.next_actions),
            },
            "owner_trends": [
                trend.to_snapshot_dict() for trend in self.owner_trends
            ],
            "scenario_trends": [
                trend.to_snapshot_dict() for trend in self.scenario_trends
            ],
        }


def build_product_readiness_freshness_response_trend_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    response_metrics: ProductReadinessFreshnessResponseMetricsReport | None = None,
) -> ProductReadinessFreshnessResponseTrendReport:
    metrics = response_metrics or build_product_readiness_freshness_response_metrics_report(
        ai_root,
        generated_at=generated_at,
    )
    return build_product_readiness_freshness_response_trend_report_from_metrics(
        metrics,
        generated_at=generated_at,
    )


def build_product_readiness_freshness_response_trend_report_from_metrics(
    response_metrics: ProductReadinessFreshnessResponseMetricsReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseTrendReport:
    report_date = generated_at or response_metrics.generated_at
    scenario_trends = tuple(
        build_scenario_trend(item) for item in response_metrics.items
    )
    owner_trends = tuple(build_owner_trend(owner, scenario_trends) for owner in sorted(
        {trend.owner_role for trend in scenario_trends}
    ))
    watch_count = sum(1 for trend in scenario_trends if trend.trend_status == "watch")
    breach_count = sum(
        1 for trend in scenario_trends if trend.trend_status == "slo_breached"
    )
    max_recover_slo_usage_pct = max(
        (trend.recover_slo_usage_pct for trend in scenario_trends),
        default=0,
    )
    max_close_slo_usage_pct = max(
        (trend.close_slo_usage_pct for trend in scenario_trends),
        default=0,
    )
    trend_status = derive_response_trend_status(
        response_metrics,
        owner_count=len(owner_trends),
        scenario_class_count=len(scenario_trends),
        breach_count=breach_count,
        watch_count=watch_count,
    )
    return ProductReadinessFreshnessResponseTrendReport(
        generated_at=report_date,
        trend_status=trend_status,
        metrics_status=response_metrics.response_metrics_status,
        ingest_status=response_metrics.ingest_status,
        owner_count=len(owner_trends),
        scenario_class_count=len(scenario_trends),
        live_observation_count=response_metrics.live_observation_count,
        breach_count=breach_count,
        watch_count=watch_count,
        p0_count=sum(1 for trend in scenario_trends if trend.severity == "p0"),
        p1_count=sum(1 for trend in scenario_trends if trend.severity == "p1"),
        max_recover_slo_usage_pct=max_recover_slo_usage_pct,
        max_close_slo_usage_pct=max_close_slo_usage_pct,
        tenant_safe=response_metrics.tenant_safe,
        raw_identifier_count=response_metrics.raw_identifier_count,
        next_actions=response_trend_next_actions(trend_status),
        owner_trends=owner_trends,
        scenario_trends=scenario_trends,
    )


def build_scenario_trend(
    item: ProductReadinessFreshnessResponseMetricItem,
) -> ProductReadinessFreshnessScenarioTrend:
    acknowledge_usage = slo_usage_pct(
        item.acknowledge_minutes,
        item.acknowledge_slo_minutes,
    )
    contain_usage = slo_usage_pct(item.contain_minutes, item.contain_slo_minutes)
    recover_usage = slo_usage_pct(item.recover_minutes, item.recover_slo_minutes)
    close_usage = slo_usage_pct(item.close_minutes, item.close_slo_minutes)
    watch_reasons = build_watch_reasons(
        acknowledge_usage=acknowledge_usage,
        contain_usage=contain_usage,
        recover_usage=recover_usage,
        close_usage=close_usage,
    )
    trend_status = derive_scenario_trend_status(
        item,
        watch_reasons=watch_reasons,
    )
    return ProductReadinessFreshnessScenarioTrend(
        scenario_id=item.scenario_id,
        condition=item.condition,
        severity=item.severity,
        owner_role=item.owner_role,
        measurement_source=item.measurement_source,
        metric_status=item.metric_status,
        acknowledge_minutes=item.acknowledge_minutes,
        acknowledge_slo_minutes=item.acknowledge_slo_minutes,
        acknowledge_slo_usage_pct=acknowledge_usage,
        contain_minutes=item.contain_minutes,
        contain_slo_minutes=item.contain_slo_minutes,
        contain_slo_usage_pct=contain_usage,
        recover_minutes=item.recover_minutes,
        recover_slo_minutes=item.recover_slo_minutes,
        recover_slo_usage_pct=recover_usage,
        close_minutes=item.close_minutes,
        close_slo_minutes=item.close_slo_minutes,
        close_slo_usage_pct=close_usage,
        trend_status=trend_status,
        watch_reasons=watch_reasons,
        breach_reasons=item.breach_reasons,
        evidence_refs=(
            "platform/operations/reports/"
            "product-readiness-freshness-response-metrics-v1.yaml",
            *item.evidence_refs,
        ),
    )


def build_owner_trend(
    owner_role: str,
    scenario_trends: tuple[ProductReadinessFreshnessScenarioTrend, ...],
) -> ProductReadinessFreshnessOwnerTrend:
    owned = tuple(trend for trend in scenario_trends if trend.owner_role == owner_role)
    recover_minutes = tuple(trend.recover_minutes for trend in owned)
    breach_count = sum(1 for trend in owned if trend.trend_status == "slo_breached")
    watch_count = sum(1 for trend in owned if trend.trend_status == "watch")
    return ProductReadinessFreshnessOwnerTrend(
        owner_role=owner_role,
        trend_status=derive_owner_trend_status(
            breach_count=breach_count,
            watch_count=watch_count,
        ),
        scenario_count=len(owned),
        p0_count=sum(1 for trend in owned if trend.severity == "p0"),
        p1_count=sum(1 for trend in owned if trend.severity == "p1"),
        breach_count=breach_count,
        watch_count=watch_count,
        live_observation_count=sum(
            1 for trend in owned if trend.measurement_source == "live_ingest"
        ),
        max_recover_slo_usage_pct=max(
            (trend.recover_slo_usage_pct for trend in owned),
            default=0,
        ),
        max_close_slo_usage_pct=max(
            (trend.close_slo_usage_pct for trend in owned),
            default=0,
        ),
        average_recover_minutes=(
            round(sum(recover_minutes) / len(recover_minutes))
            if recover_minutes
            else 0
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                ref
                for trend in owned
                for ref in trend.evidence_refs
            )
        ),
    )


def derive_response_trend_status(
    response_metrics: ProductReadinessFreshnessResponseMetricsReport,
    *,
    owner_count: int,
    scenario_class_count: int,
    breach_count: int,
    watch_count: int,
) -> str:
    if not response_metrics.tenant_safe or response_metrics.raw_identifier_count:
        return "blocked_by_tenant_safety"
    if (
        response_metrics.response_metrics_status != "slo_met"
        or response_metrics.breach_count
        or breach_count
    ):
        return "blocked_by_response_slo"
    if response_metrics.ingest_status != "live_ingest_connected":
        return "blocked_by_live_ingest"
    if owner_count == 0 or scenario_class_count == 0:
        return "blocked_by_missing_trend"
    if watch_count:
        return "trend_ready_with_watch"
    return "trend_ready"


def derive_scenario_trend_status(
    item: ProductReadinessFreshnessResponseMetricItem,
    *,
    watch_reasons: tuple[str, ...],
) -> str:
    if item.metric_status != "slo_met" or item.breach_reasons:
        return "slo_breached"
    if watch_reasons:
        return "watch"
    return "within_slo"


def derive_owner_trend_status(*, breach_count: int, watch_count: int) -> str:
    if breach_count:
        return "slo_breached"
    if watch_count:
        return "watch"
    return "within_slo"


def build_watch_reasons(
    *,
    acknowledge_usage: int,
    contain_usage: int,
    recover_usage: int,
    close_usage: int,
) -> tuple[str, ...]:
    usage_by_reason = (
        ("acknowledge_slo_usage_watch", acknowledge_usage),
        ("contain_slo_usage_watch", contain_usage),
        ("recover_slo_usage_watch", recover_usage),
        ("close_slo_usage_watch", close_usage),
    )
    return tuple(
        reason for reason, usage in usage_by_reason if usage >= SLO_USAGE_WATCH_PERCENT
    )


def response_trend_next_actions(trend_status: str) -> tuple[str, ...]:
    if trend_status in {"trend_ready", "trend_ready_with_watch"}:
        return (CONFIGURE_DRIFT_ALERT_ACTION,)
    return (TREND_BY_OWNER_ACTION,)


def slo_usage_pct(minutes: int, slo_minutes: int) -> int:
    if slo_minutes <= 0:
        return 0
    return round((minutes / slo_minutes) * 100)


def build_product_readiness_freshness_response_trend_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_product_readiness_freshness_response_trend_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_product_readiness_freshness_response_trend_snapshot(
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
            build_product_readiness_freshness_response_trend_snapshot(
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
