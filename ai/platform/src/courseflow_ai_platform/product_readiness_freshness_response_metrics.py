from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness_response_drill import (
    RAW_IDENTIFIER_MARKERS,
    ProductReadinessFreshnessIncidentResponseDrillReport,
    ProductReadinessFreshnessResponseDrillScenario,
    build_product_readiness_freshness_incident_response_drill_report,
    default_runbook_spec_path,
    load_runbook_spec,
)

REPORT_ID = "product-readiness-freshness-response-metrics-v1"
LIVE_RESPONSE_METRICS_REPORT_ID = (
    "product-readiness-freshness-live-response-metrics-v1"
)
CONNECT_LIVE_INGEST_ACTION = (
    "connect_product_readiness_freshness_live_response_metrics_ingest"
)
DEFAULT_NEXT_ACTION = "trend_product_readiness_freshness_response_slo_by_owner"
DEFAULT_RESPONSE_METRICS = {
    "severity_slos": {
        "p0": {
            "acknowledge_minutes": 5,
            "contain_minutes": 15,
            "recover_minutes": 60,
            "close_minutes": 90,
        },
        "p1": {
            "acknowledge_minutes": 15,
            "contain_minutes": 45,
            "recover_minutes": 240,
            "close_minutes": 300,
        },
    },
    "synthetic_observations": {
        "product_readiness_freshness_report_stale": {
            "acknowledge_minutes": 10,
            "contain_minutes": 24,
            "remediate_minutes": 110,
            "verify_minutes": 130,
            "close_minutes": 170,
        },
        "product_readiness_runtime_route_unreachable": {
            "acknowledge_minutes": 4,
            "contain_minutes": 12,
            "remediate_minutes": 42,
            "verify_minutes": 52,
            "close_minutes": 70,
        },
        "product_readiness_static_snapshot_stale": {
            "acknowledge_minutes": 9,
            "contain_minutes": 22,
            "remediate_minutes": 100,
            "verify_minutes": 118,
            "close_minutes": 158,
        },
        "product_readiness_runtime_error_or_audit_failure": {
            "acknowledge_minutes": 11,
            "contain_minutes": 30,
            "remediate_minutes": 145,
            "verify_minutes": 170,
            "close_minutes": 210,
        },
        "product_readiness_runtime_audit_gap": {
            "acknowledge_minutes": 8,
            "contain_minutes": 20,
            "remediate_minutes": 90,
            "verify_minutes": 112,
            "close_minutes": 150,
        },
    },
    "next_actions": (DEFAULT_NEXT_ACTION,),
}


@dataclass(frozen=True, slots=True)
class LiveResponseMetricsObservation:
    observation_id: str
    scenario_id: str
    condition: str
    incident_id: str
    detected_at: str
    acknowledged_at: str
    contained_at: str
    remediated_at: str
    recovered_at: str
    closed_at: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LiveResponseMetricsIngest:
    source_status: str
    source_path: str
    generated_at: str
    raw_identifier_count: int
    observations: tuple[LiveResponseMetricsObservation, ...]


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseMetricItem:
    scenario_id: str
    condition: str
    severity: str
    measurement_source: str
    observation_id: str
    owner_role: str
    action: str
    incident_id: str
    incident_status: str
    detected_at: str
    acknowledged_at: str
    contained_at: str
    remediated_at: str
    recovered_at: str
    closed_at: str
    acknowledge_minutes: int
    contain_minutes: int
    remediate_minutes: int
    recover_minutes: int
    close_minutes: int
    acknowledge_slo_minutes: int
    contain_slo_minutes: int
    recover_slo_minutes: int
    close_slo_minutes: int
    acknowledge_slo_met: bool
    contain_slo_met: bool
    recover_slo_met: bool
    close_slo_met: bool
    metric_status: str
    breach_reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "acknowledgeMinutes": self.acknowledge_minutes,
            "acknowledgeSloMet": self.acknowledge_slo_met,
            "acknowledgeSloMinutes": self.acknowledge_slo_minutes,
            "acknowledgedAt": self.acknowledged_at,
            "action": self.action,
            "breachReasons": list(self.breach_reasons),
            "closeMinutes": self.close_minutes,
            "closeSloMet": self.close_slo_met,
            "closeSloMinutes": self.close_slo_minutes,
            "closedAt": self.closed_at,
            "condition": self.condition,
            "containMinutes": self.contain_minutes,
            "containSloMet": self.contain_slo_met,
            "containSloMinutes": self.contain_slo_minutes,
            "containedAt": self.contained_at,
            "detectedAt": self.detected_at,
            "evidenceRefs": list(self.evidence_refs),
            "incidentId": self.incident_id,
            "incidentStatus": self.incident_status,
            "metricStatus": self.metric_status,
            "measurementSource": self.measurement_source,
            "observationId": self.observation_id,
            "ownerRole": self.owner_role,
            "recoverMinutes": self.recover_minutes,
            "recoverSloMet": self.recover_slo_met,
            "recoverSloMinutes": self.recover_slo_minutes,
            "recoveredAt": self.recovered_at,
            "remediateMinutes": self.remediate_minutes,
            "remediatedAt": self.remediated_at,
            "scenarioId": self.scenario_id,
            "severity": self.severity,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "severity": self.severity,
            "measurement_source": self.measurement_source,
            "observation_id": self.observation_id,
            "owner_role": self.owner_role,
            "action": self.action,
            "incident_id": self.incident_id,
            "incident_status": self.incident_status,
            "detected_at": self.detected_at,
            "acknowledged_at": self.acknowledged_at,
            "contained_at": self.contained_at,
            "remediated_at": self.remediated_at,
            "recovered_at": self.recovered_at,
            "closed_at": self.closed_at,
            "acknowledge_minutes": self.acknowledge_minutes,
            "contain_minutes": self.contain_minutes,
            "remediate_minutes": self.remediate_minutes,
            "recover_minutes": self.recover_minutes,
            "close_minutes": self.close_minutes,
            "acknowledge_slo_minutes": self.acknowledge_slo_minutes,
            "contain_slo_minutes": self.contain_slo_minutes,
            "recover_slo_minutes": self.recover_slo_minutes,
            "close_slo_minutes": self.close_slo_minutes,
            "acknowledge_slo_met": self.acknowledge_slo_met,
            "contain_slo_met": self.contain_slo_met,
            "recover_slo_met": self.recover_slo_met,
            "close_slo_met": self.close_slo_met,
            "metric_status": self.metric_status,
            "breach_reasons": list(self.breach_reasons),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseMetricsReport:
    generated_at: str
    response_metrics_status: str
    ingest_status: str
    drill_status: str
    scenario_count: int
    measured_count: int
    live_observation_count: int
    synthetic_observation_count: int
    missing_live_observation_count: int
    breach_count: int
    p0_count: int
    p1_count: int
    max_acknowledge_minutes: int
    max_recover_minutes: int
    max_close_minutes: int
    average_recover_minutes: int
    tenant_safe: bool
    raw_identifier_count: int
    live_source_path: str
    next_actions: tuple[str, ...]
    items: tuple[ProductReadinessFreshnessResponseMetricItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "averageRecoverMinutes": self.average_recover_minutes,
            "breachCount": self.breach_count,
            "drillStatus": self.drill_status,
            "generatedAt": self.generated_at,
            "ingestStatus": self.ingest_status,
            "items": [item.to_dict() for item in self.items],
            "liveObservationCount": self.live_observation_count,
            "liveSourcePath": self.live_source_path,
            "maxAcknowledgeMinutes": self.max_acknowledge_minutes,
            "maxCloseMinutes": self.max_close_minutes,
            "maxRecoverMinutes": self.max_recover_minutes,
            "measuredCount": self.measured_count,
            "missingLiveObservationCount": self.missing_live_observation_count,
            "nextActions": list(self.next_actions),
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "responseMetricsStatus": self.response_metrics_status,
            "scenarioCount": self.scenario_count,
            "syntheticObservationCount": self.synthetic_observation_count,
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "response_metrics_status": self.response_metrics_status,
                "ingest_status": self.ingest_status,
                "drill_status": self.drill_status,
                "scenario_count": self.scenario_count,
                "measured_count": self.measured_count,
                "live_observation_count": self.live_observation_count,
                "synthetic_observation_count": self.synthetic_observation_count,
                "missing_live_observation_count": (
                    self.missing_live_observation_count
                ),
                "breach_count": self.breach_count,
                "p0_count": self.p0_count,
                "p1_count": self.p1_count,
                "max_acknowledge_minutes": self.max_acknowledge_minutes,
                "max_recover_minutes": self.max_recover_minutes,
                "max_close_minutes": self.max_close_minutes,
                "average_recover_minutes": self.average_recover_minutes,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
                "live_source_path": self.live_source_path,
            },
            "action_queue": {
                "slo_breached": [
                    item.scenario_id for item in self.items if item.breach_reasons
                ],
                "measured": [
                    item.scenario_id
                    for item in self.items
                    if item.metric_status == "slo_met"
                ],
                "live_ingested": [
                    item.scenario_id
                    for item in self.items
                    if item.measurement_source == "live_ingest"
                ],
                "synthetic_baseline": [
                    item.scenario_id
                    for item in self.items
                    if item.measurement_source == "synthetic_baseline"
                ],
                "next_actions": list(self.next_actions),
            },
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_product_readiness_freshness_response_metrics_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    response_drill: ProductReadinessFreshnessIncidentResponseDrillReport | None = None,
) -> ProductReadinessFreshnessResponseMetricsReport:
    root = Path(ai_root)
    report_date = generated_at or date.today().isoformat()
    live_ingest = load_live_response_metrics_ingest(root)
    drill_report = response_drill or (
        build_product_readiness_freshness_incident_response_drill_report(
            root,
            generated_at=report_date,
        )
    )
    runbook = load_runbook_spec(default_runbook_spec_path(root))
    return build_product_readiness_freshness_response_metrics_report_from_drill(
        drill_report,
        runbook=runbook,
        live_ingest=live_ingest,
        generated_at=report_date,
    )


def build_product_readiness_freshness_response_metrics_report_from_drill(
    response_drill: ProductReadinessFreshnessIncidentResponseDrillReport,
    *,
    runbook: dict[str, Any] | None = None,
    live_ingest: LiveResponseMetricsIngest | None = None,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseMetricsReport:
    report_date = generated_at or response_drill.generated_at
    metrics_spec = normalized_response_metrics_spec(runbook)
    ingest = live_ingest or empty_live_response_metrics_ingest()
    live_observations = live_observations_by_scenario(ingest)
    base_time = response_metrics_anchor(report_date)
    items = tuple(
        build_response_metric_item(
            scenario,
            detected_at=base_time + timedelta(minutes=index * 20),
            metrics_spec=metrics_spec,
            live_observation=live_observations.get(scenario.scenario_id),
        )
        for index, scenario in enumerate(response_drill.scenarios)
    )
    raw_identifier_count = count_raw_identifier_markers(items) + ingest.raw_identifier_count
    tenant_safe = response_drill.tenant_safe and raw_identifier_count == 0
    breach_count = sum(1 for item in items if item.breach_reasons)
    live_observation_count = sum(
        1 for item in items if item.measurement_source == "live_ingest"
    )
    synthetic_observation_count = len(items) - live_observation_count
    ingest_status = derive_ingest_status(
        ingest,
        live_observation_count=live_observation_count,
        scenario_count=len(items),
        tenant_safe=tenant_safe,
    )
    response_metrics_status = derive_response_metrics_status(
        response_drill,
        breach_count=breach_count,
        tenant_safe=tenant_safe,
    )
    recover_minutes = [item.recover_minutes for item in items]
    return ProductReadinessFreshnessResponseMetricsReport(
        generated_at=report_date,
        response_metrics_status=response_metrics_status,
        ingest_status=ingest_status,
        drill_status=response_drill.drill_status,
        scenario_count=len(items),
        measured_count=sum(1 for item in items if item.metric_status == "slo_met"),
        live_observation_count=live_observation_count,
        synthetic_observation_count=synthetic_observation_count,
        missing_live_observation_count=synthetic_observation_count,
        breach_count=breach_count,
        p0_count=sum(1 for item in items if item.severity == "p0"),
        p1_count=sum(1 for item in items if item.severity == "p1"),
        max_acknowledge_minutes=max(
            (item.acknowledge_minutes for item in items),
            default=0,
        ),
        max_recover_minutes=max(recover_minutes, default=0),
        max_close_minutes=max((item.close_minutes for item in items), default=0),
        average_recover_minutes=(
            round(sum(recover_minutes) / len(recover_minutes)) if recover_minutes else 0
        ),
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        live_source_path=ingest.source_path,
        next_actions=response_metrics_next_actions(metrics_spec, ingest_status),
        items=items,
    )


def build_response_metric_item(
    scenario: ProductReadinessFreshnessResponseDrillScenario,
    *,
    detected_at: datetime,
    metrics_spec: dict[str, Any],
    live_observation: LiveResponseMetricsObservation | None = None,
) -> ProductReadinessFreshnessResponseMetricItem:
    severity = scenario.expected_severity.lower()
    severity_slo = normalized_severity_slo(metrics_spec, severity)
    if live_observation is not None:
        detected_at = parse_response_metric_timestamp(live_observation.detected_at)
        acknowledge_minutes = elapsed_minutes(
            detected_at,
            parse_response_metric_timestamp(live_observation.acknowledged_at),
        )
        contain_minutes = elapsed_minutes(
            detected_at,
            parse_response_metric_timestamp(live_observation.contained_at),
        )
        remediate_minutes = elapsed_minutes(
            detected_at,
            parse_response_metric_timestamp(live_observation.remediated_at),
        )
        recover_minutes = elapsed_minutes(
            detected_at,
            parse_response_metric_timestamp(live_observation.recovered_at),
        )
        close_minutes = elapsed_minutes(
            detected_at,
            parse_response_metric_timestamp(live_observation.closed_at),
        )
        measurement_source = "live_ingest"
        observation_id = live_observation.observation_id
        timestamp_refs = {
            "detected_at": live_observation.detected_at,
            "acknowledged_at": live_observation.acknowledged_at,
            "contained_at": live_observation.contained_at,
            "remediated_at": live_observation.remediated_at,
            "recovered_at": live_observation.recovered_at,
            "closed_at": live_observation.closed_at,
        }
        evidence_refs = (
            "platform/operations/metrics/"
            f"{LIVE_RESPONSE_METRICS_REPORT_ID}.yaml",
            *live_observation.evidence_refs,
        )
    else:
        observation = normalized_observation(metrics_spec, scenario.condition, severity)
        acknowledge_minutes = observation["acknowledge_minutes"]
        contain_minutes = observation["contain_minutes"]
        remediate_minutes = observation["remediate_minutes"]
        recover_minutes = observation["verify_minutes"]
        close_minutes = observation["close_minutes"]
        measurement_source = "synthetic_baseline"
        observation_id = f"synthetic-{scenario.scenario_id}"
        timestamp_refs = {
            "detected_at": format_timestamp(detected_at),
            "acknowledged_at": format_timestamp(
                detected_at + timedelta(minutes=acknowledge_minutes)
            ),
            "contained_at": format_timestamp(
                detected_at + timedelta(minutes=contain_minutes)
            ),
            "remediated_at": format_timestamp(
                detected_at + timedelta(minutes=remediate_minutes)
            ),
            "recovered_at": format_timestamp(
                detected_at + timedelta(minutes=recover_minutes)
            ),
            "closed_at": format_timestamp(detected_at + timedelta(minutes=close_minutes)),
        }
        evidence_refs = ()
    breach_reasons = tuple(
        build_breach_reasons(
            scenario,
            acknowledge_minutes=acknowledge_minutes,
            contain_minutes=contain_minutes,
            recover_minutes=recover_minutes,
            close_minutes=close_minutes,
            severity_slo=severity_slo,
        )
    )
    return ProductReadinessFreshnessResponseMetricItem(
        scenario_id=scenario.scenario_id,
        condition=scenario.condition,
        severity=severity,
        measurement_source=measurement_source,
        observation_id=observation_id,
        owner_role=scenario.observed_owner_role,
        action=scenario.observed_action,
        incident_id=scenario.incident_id,
        incident_status=scenario.incident_status,
        detected_at=timestamp_refs["detected_at"],
        acknowledged_at=timestamp_refs["acknowledged_at"],
        contained_at=timestamp_refs["contained_at"],
        remediated_at=timestamp_refs["remediated_at"],
        recovered_at=timestamp_refs["recovered_at"],
        closed_at=timestamp_refs["closed_at"],
        acknowledge_minutes=acknowledge_minutes,
        contain_minutes=contain_minutes,
        remediate_minutes=remediate_minutes,
        recover_minutes=recover_minutes,
        close_minutes=close_minutes,
        acknowledge_slo_minutes=severity_slo["acknowledge_minutes"],
        contain_slo_minutes=severity_slo["contain_minutes"],
        recover_slo_minutes=severity_slo["recover_minutes"],
        close_slo_minutes=severity_slo["close_minutes"],
        acknowledge_slo_met=(
            acknowledge_minutes <= severity_slo["acknowledge_minutes"]
        ),
        contain_slo_met=contain_minutes <= severity_slo["contain_minutes"],
        recover_slo_met=recover_minutes <= severity_slo["recover_minutes"],
        close_slo_met=close_minutes <= severity_slo["close_minutes"],
        metric_status="slo_breached" if breach_reasons else "slo_met",
        breach_reasons=breach_reasons,
        evidence_refs=(
            "platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml",
            "platform/operations/runbooks/product-readiness-freshness-incident-response-v1.yaml",
            *evidence_refs,
            *scenario.evidence_refs,
        ),
    )


def build_product_readiness_freshness_response_metrics_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_product_readiness_freshness_response_metrics_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_product_readiness_freshness_response_metrics_snapshot(
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
            build_product_readiness_freshness_response_metrics_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


def load_live_response_metrics_ingest(ai_root: Path | str) -> LiveResponseMetricsIngest:
    root = Path(ai_root)
    source_path = default_live_metrics_path(root)
    relative_source_path = str(source_path.relative_to(root))
    if not source_path.exists():
        return LiveResponseMetricsIngest(
            source_status="missing",
            source_path=relative_source_path,
            generated_at="",
            raw_identifier_count=0,
            observations=(),
        )

    payload = load_runbook_spec(source_path)
    observations = tuple(
        observation
        for row in payload.get("observations", ())
        if isinstance(row, dict)
        for observation in (build_live_response_metric_observation(row),)
        if observation is not None
    )
    return LiveResponseMetricsIngest(
        source_status="loaded",
        source_path=relative_source_path,
        generated_at=str(payload.get("generated_at", "")),
        raw_identifier_count=count_raw_identifier_markers_in_payload(payload),
        observations=observations,
    )


def empty_live_response_metrics_ingest() -> LiveResponseMetricsIngest:
    return LiveResponseMetricsIngest(
        source_status="missing",
        source_path=(
            "platform/operations/metrics/"
            f"{LIVE_RESPONSE_METRICS_REPORT_ID}.yaml"
        ),
        generated_at="",
        raw_identifier_count=0,
        observations=(),
    )


def build_live_response_metric_observation(
    row: dict[str, Any],
) -> LiveResponseMetricsObservation | None:
    observation_id = clean_string(row.get("observation_id"))
    scenario_id = clean_string(row.get("scenario_id"))
    condition = clean_string(row.get("condition"))
    incident_id = clean_string(row.get("incident_id"))
    timestamps = {
        key: clean_string(row.get(key))
        for key in (
            "detected_at",
            "acknowledged_at",
            "contained_at",
            "remediated_at",
            "recovered_at",
            "closed_at",
        )
    }
    if not all((observation_id, scenario_id, condition, incident_id, *timestamps.values())):
        return None
    parsed = {
        key: parse_response_metric_timestamp(value)
        for key, value in timestamps.items()
        if value is not None
    }
    ordered = (
        parsed["detected_at"],
        parsed["acknowledged_at"],
        parsed["contained_at"],
        parsed["remediated_at"],
        parsed["recovered_at"],
        parsed["closed_at"],
    )
    if any(later < earlier for earlier, later in zip(ordered, ordered[1:], strict=False)):
        return None
    evidence_refs = tuple(
        clean_string(value)
        for value in row.get("evidence_refs", ())
        if clean_string(value) is not None
    )
    return LiveResponseMetricsObservation(
        observation_id=observation_id,
        scenario_id=scenario_id,
        condition=condition,
        incident_id=incident_id,
        detected_at=format_timestamp(parsed["detected_at"]),
        acknowledged_at=format_timestamp(parsed["acknowledged_at"]),
        contained_at=format_timestamp(parsed["contained_at"]),
        remediated_at=format_timestamp(parsed["remediated_at"]),
        recovered_at=format_timestamp(parsed["recovered_at"]),
        closed_at=format_timestamp(parsed["closed_at"]),
        evidence_refs=evidence_refs,
    )


def live_observations_by_scenario(
    ingest: LiveResponseMetricsIngest,
) -> dict[str, LiveResponseMetricsObservation]:
    return {
        observation.scenario_id: observation
        for observation in ingest.observations
        if observation.scenario_id
    }


def normalized_response_metrics_spec(runbook: dict[str, Any] | None) -> dict[str, Any]:
    if runbook is None:
        return dict(DEFAULT_RESPONSE_METRICS)
    configured = runbook.get("response_metrics", {})
    if not isinstance(configured, dict):
        return dict(DEFAULT_RESPONSE_METRICS)
    return {
        "severity_slos": {
            **DEFAULT_RESPONSE_METRICS["severity_slos"],
            **{
                str(key).lower(): value
                for key, value in configured.get("severity_slos", {}).items()
                if isinstance(value, dict)
            },
        },
        "synthetic_observations": {
            **DEFAULT_RESPONSE_METRICS["synthetic_observations"],
            **{
                str(key): value
                for key, value in configured.get("synthetic_observations", {}).items()
                if isinstance(value, dict)
            },
        },
        "next_actions": tuple(
            str(action)
            for action in configured.get(
                "next_actions",
                DEFAULT_RESPONSE_METRICS["next_actions"],
            )
            if isinstance(action, str) and action.strip()
        ),
    }


def response_metrics_next_actions(
    metrics_spec: dict[str, Any],
    ingest_status: str,
) -> tuple[str, ...]:
    if ingest_status != "live_ingest_connected":
        return (CONNECT_LIVE_INGEST_ACTION,)
    configured = tuple(
        str(action)
        for action in metrics_spec.get("next_actions", ())
        if isinstance(action, str) and action.strip()
    )
    return configured or (DEFAULT_NEXT_ACTION,)


def normalized_severity_slo(
    metrics_spec: dict[str, Any],
    severity: str,
) -> dict[str, int]:
    rows = metrics_spec.get("severity_slos", {})
    row = rows.get(severity) if isinstance(rows, dict) else None
    if not isinstance(row, dict):
        row = DEFAULT_RESPONSE_METRICS["severity_slos"].get(severity, {})
    return {
        "acknowledge_minutes": positive_int(row, "acknowledge_minutes", 15),
        "contain_minutes": positive_int(row, "contain_minutes", 45),
        "recover_minutes": positive_int(row, "recover_minutes", 240),
        "close_minutes": positive_int(row, "close_minutes", 300),
    }


def normalized_observation(
    metrics_spec: dict[str, Any],
    condition: str,
    severity: str,
) -> dict[str, int]:
    rows = metrics_spec.get("synthetic_observations", {})
    row = rows.get(condition) if isinstance(rows, dict) else None
    if not isinstance(row, dict):
        p0_default = DEFAULT_RESPONSE_METRICS["synthetic_observations"][
            "product_readiness_runtime_route_unreachable"
        ]
        default_observation = DEFAULT_RESPONSE_METRICS["synthetic_observations"][
            "product_readiness_freshness_report_stale"
        ]
        row = {"p0": p0_default}.get(
            severity,
            default_observation,
        )
    return {
        "acknowledge_minutes": positive_int(row, "acknowledge_minutes", 10),
        "contain_minutes": positive_int(row, "contain_minutes", 30),
        "remediate_minutes": positive_int(row, "remediate_minutes", 120),
        "verify_minutes": positive_int(row, "verify_minutes", 150),
        "close_minutes": positive_int(row, "close_minutes", 180),
    }


def build_breach_reasons(
    scenario: ProductReadinessFreshnessResponseDrillScenario,
    *,
    acknowledge_minutes: int,
    contain_minutes: int,
    recover_minutes: int,
    close_minutes: int,
    severity_slo: dict[str, int],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not scenario.passed:
        reasons.append("response_drill_scenario_not_passed")
    if acknowledge_minutes > severity_slo["acknowledge_minutes"]:
        reasons.append("acknowledge_slo_breached")
    if contain_minutes > severity_slo["contain_minutes"]:
        reasons.append("contain_slo_breached")
    if recover_minutes > severity_slo["recover_minutes"]:
        reasons.append("recover_slo_breached")
    if close_minutes > severity_slo["close_minutes"]:
        reasons.append("close_slo_breached")
    return tuple(reasons)


def derive_response_metrics_status(
    response_drill: ProductReadinessFreshnessIncidentResponseDrillReport,
    *,
    breach_count: int,
    tenant_safe: bool,
) -> str:
    if response_drill.drill_status != "passed":
        return "blocked_by_response_drill"
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if breach_count:
        return "slo_breached"
    return "slo_met"


def derive_ingest_status(
    ingest: LiveResponseMetricsIngest,
    *,
    live_observation_count: int,
    scenario_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if live_observation_count == scenario_count and scenario_count > 0:
        return "live_ingest_connected"
    if live_observation_count:
        return "live_ingest_partial"
    if ingest.source_status == "loaded":
        return "live_ingest_empty"
    return "synthetic_baseline"


def response_metrics_anchor(generated_at: str) -> datetime:
    report_date = date.fromisoformat(generated_at)
    return datetime.combine(report_date, datetime.min.time()).replace(hour=9)


def format_timestamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat() + "Z"


def parse_response_metric_timestamp(value: str) -> datetime:
    normalized = value[:-1] if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def elapsed_minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def positive_int(row: dict[str, Any], key: str, default: int) -> int:
    value = row.get(key)
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    return default


def count_raw_identifier_markers(
    items: tuple[ProductReadinessFreshnessResponseMetricItem, ...],
) -> int:
    payload = json.dumps(
        [item.to_snapshot_dict() for item in items],
        ensure_ascii=True,
        sort_keys=True,
    )
    return count_raw_identifier_markers_in_text(payload)


def count_raw_identifier_markers_in_payload(payload: Any) -> int:
    return count_raw_identifier_markers_in_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True)
    )


def count_raw_identifier_markers_in_text(payload: str) -> int:
    normalized = payload.lower()
    return sum(normalized.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def default_live_metrics_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "operations"
        / "metrics"
        / f"{LIVE_RESPONSE_METRICS_REPORT_ID}.yaml"
    )


def count_raw_identifier_markers_in_yaml(payload: str) -> int:
    payload = payload.lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
