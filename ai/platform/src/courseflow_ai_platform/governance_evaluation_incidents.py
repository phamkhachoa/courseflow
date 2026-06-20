from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.governance_evaluation_ops import (
    GovernanceEvaluationOpsReport,
    build_governance_evaluation_ops_report,
)

DEFAULT_REPEATED_FAILURE_THRESHOLD = 2
OBSERVABLE_STATUS = "release_gate_observable"
POLICY_ID = "governance-evaluation-incident-policy-v1"
LEDGER_ID = "governance-evaluation-alert-drill-ledger-v1"
REPORT_ID = "governance-evaluation-incident-export-v1"
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-")

DEFAULT_INCIDENT_ROUTES: dict[str, dict[str, str]] = {
    "blocked_by_release_gate_drill_mismatch": {
        "severity": "p0",
        "owner_role": "Admin/Ops",
        "action": "escalate_governance_evaluation_release_gate_mismatch",
        "condition": "governance_evaluation_release_gate_mismatch",
    },
    "blocked_by_unexpected_governance_evaluation_error": {
        "severity": "p0",
        "owner_role": "Admin/Ops",
        "action": "triage_governance_evaluation_runtime_error",
        "condition": "governance_evaluation_unexpected_error",
    },
    "attention_required_guardrail_drill_gap": {
        "severity": "p1",
        "owner_role": "Admin/Ops",
        "action": "complete_governance_evaluation_guardrail_drills",
        "condition": "governance_evaluation_guardrail_gap",
    },
}


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationIncidentPolicy:
    policy_id: str
    repeated_failure_threshold: int
    incident_routes: dict[str, dict[str, str]]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GovernanceEvaluationIncidentPolicy:
        raw_threshold = payload.get(
            "repeated_failure_threshold",
            DEFAULT_REPEATED_FAILURE_THRESHOLD,
        )
        threshold = max(1, int(raw_threshold))
        raw_routes = payload.get("incident_routes")
        routes = DEFAULT_INCIDENT_ROUTES if not isinstance(raw_routes, dict) else raw_routes
        return cls(
            policy_id=str(payload.get("policy_id") or POLICY_ID),
            repeated_failure_threshold=threshold,
            incident_routes={
                str(status): {str(key): str(value) for key, value in route.items()}
                for status, route in routes.items()
                if isinstance(route, dict)
            },
        )


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationAlertDrillEvent:
    event_id: str
    occurred_at: str
    ops_status: str
    failed_drill_count: int
    unexpected_error_count: int
    evidence_refs: tuple[str, ...]

    @property
    def occurred_date(self) -> date | None:
        try:
            return date.fromisoformat(self.occurred_at[:10])
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationIncident:
    incident_id: str
    condition: str
    severity: str
    incident_status: str
    owner_role: str
    action: str
    application_ref: str
    ops_status: str
    consecutive_failure_count: int
    repeated_failure_threshold: int
    failed_drill_count: int
    unexpected_error_count: int
    age_days: int | None
    stale_threshold_days: int
    evidence_refs: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "ageDays": self.age_days,
            "applicationRef": self.application_ref,
            "condition": self.condition,
            "consecutiveFailureCount": self.consecutive_failure_count,
            "evidenceRefs": list(self.evidence_refs),
            "failedDrillCount": self.failed_drill_count,
            "incidentId": self.incident_id,
            "opsStatus": self.ops_status,
            "ownerRole": self.owner_role,
            "reason": self.reason,
            "repeatedFailureThreshold": self.repeated_failure_threshold,
            "severity": self.severity,
            "staleThresholdDays": self.stale_threshold_days,
            "status": self.incident_status,
            "unexpectedErrorCount": self.unexpected_error_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "condition": self.condition,
            "severity": self.severity,
            "status": self.incident_status,
            "owner_role": self.owner_role,
            "action": self.action,
            "application_ref": self.application_ref,
            "ops_status": self.ops_status,
            "consecutive_failure_count": self.consecutive_failure_count,
            "repeated_failure_threshold": self.repeated_failure_threshold,
            "failed_drill_count": self.failed_drill_count,
            "unexpected_error_count": self.unexpected_error_count,
            "age_days": self.age_days,
            "stale_threshold_days": self.stale_threshold_days,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationIncidentExport:
    as_of: date
    current_ops_status: str
    repeated_failure_threshold: int
    observation_count: int
    consecutive_failure_count: int
    incident_count: int
    open_count: int
    watch_count: int
    p0_count: int
    p1_count: int
    p2_count: int
    repeated_failure_count: int
    tenant_safe: bool
    raw_identifier_count: int
    omitted_sensitive_fields: tuple[str, ...]
    by_condition: dict[str, int]
    by_severity: dict[str, int]
    by_status: dict[str, int]
    action_queue: dict[str, list[str]]
    incidents: tuple[GovernanceEvaluationIncident, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": self.action_queue,
            "asOf": self.as_of.isoformat(),
            "byCondition": self.by_condition,
            "bySeverity": self.by_severity,
            "byStatus": self.by_status,
            "consecutiveFailureCount": self.consecutive_failure_count,
            "currentOpsStatus": self.current_ops_status,
            "incidentCount": self.incident_count,
            "incidents": [incident.to_dict() for incident in self.incidents],
            "observationCount": self.observation_count,
            "omittedSensitiveFields": list(self.omitted_sensitive_fields),
            "openCount": self.open_count,
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "p2Count": self.p2_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "repeatedFailureCount": self.repeated_failure_count,
            "repeatedFailureThreshold": self.repeated_failure_threshold,
            "tenantSafe": self.tenant_safe,
            "watchCount": self.watch_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "as_of": self.as_of.isoformat(),
                "current_ops_status": self.current_ops_status,
                "observation_count": self.observation_count,
                "consecutive_failure_count": self.consecutive_failure_count,
                "repeated_failure_threshold": self.repeated_failure_threshold,
                "repeated_failure_count": self.repeated_failure_count,
                "incident_count": self.incident_count,
                "open_count": self.open_count,
                "watch_count": self.watch_count,
                "p0_count": self.p0_count,
                "p1_count": self.p1_count,
                "p2_count": self.p2_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
                "omitted_sensitive_fields": list(self.omitted_sensitive_fields),
            },
            "by_condition": self.by_condition,
            "by_severity": self.by_severity,
            "by_status": self.by_status,
            "action_queue": self.action_queue,
            "incidents": [incident.to_snapshot_dict() for incident in self.incidents],
        }


def build_governance_evaluation_incident_export(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
) -> GovernanceEvaluationIncidentExport:
    root = Path(ai_root)
    report_date = parse_report_date(as_of)
    return build_governance_evaluation_incident_export_from_report(
        ops_report=build_governance_evaluation_ops_report(
            root,
            generated_at=report_date.isoformat(),
        ),
        policy=load_incident_policy(root),
        events=load_alert_drill_events(root),
        as_of=report_date,
    )


def build_governance_evaluation_incident_export_from_report(
    *,
    ops_report: GovernanceEvaluationOpsReport,
    policy: GovernanceEvaluationIncidentPolicy | None = None,
    events: tuple[GovernanceEvaluationAlertDrillEvent, ...] = (),
    as_of: str | date | None = None,
) -> GovernanceEvaluationIncidentExport:
    report_date = parse_report_date(as_of)
    resolved_policy = policy or GovernanceEvaluationIncidentPolicy(
        policy_id=POLICY_ID,
        repeated_failure_threshold=DEFAULT_REPEATED_FAILURE_THRESHOLD,
        incident_routes=DEFAULT_INCIDENT_ROUTES,
    )
    relevant_events = tuple(
        event
        for event in sorted(events, key=event_sort_key)
        if event.occurred_date is not None and event.occurred_date <= report_date
    )
    consecutive_failure_count = current_consecutive_failure_count(
        ops_report,
        relevant_events,
        as_of=report_date,
    )
    duplicate_current = has_current_observation(
        ops_report,
        relevant_events,
        as_of=report_date,
    )
    observation_count = len(relevant_events) + (0 if duplicate_current else 1)
    incidents = build_incidents(
        ops_report,
        policy=resolved_policy,
        consecutive_failure_count=consecutive_failure_count,
    )
    raw_identifier_count = count_raw_identifier_markers(incidents)
    return GovernanceEvaluationIncidentExport(
        as_of=report_date,
        current_ops_status=ops_report.ops_status,
        repeated_failure_threshold=resolved_policy.repeated_failure_threshold,
        observation_count=observation_count,
        consecutive_failure_count=consecutive_failure_count,
        incident_count=len(incidents),
        open_count=count_status(incidents, "open"),
        watch_count=count_status(incidents, "watch"),
        p0_count=count_severity(incidents, "p0"),
        p1_count=count_severity(incidents, "p1"),
        p2_count=count_severity(incidents, "p2"),
        repeated_failure_count=sum(
            1
            for incident in incidents
            if incident.consecutive_failure_count
            >= incident.repeated_failure_threshold
        ),
        tenant_safe=raw_identifier_count == 0,
        raw_identifier_count=raw_identifier_count,
        omitted_sensitive_fields=(
            "principal_ids",
            "tenant_ids",
            "request_bodies",
            "credential_values",
            "raw_drill_payloads",
        ),
        by_condition=count_by(incidents, "condition"),
        by_severity=count_by(incidents, "severity"),
        by_status=count_by(incidents, "incident_status"),
        action_queue=build_action_queue(incidents),
        incidents=incidents,
    )


def build_governance_evaluation_incident_export_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    as_of: str | date | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_governance_evaluation_incident_export(
        ai_root,
        as_of=as_of or generated_at,
    ).to_snapshot_dict(generated_at=report_date)


def write_governance_evaluation_incident_export_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
    as_of: str | date | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_governance_evaluation_incident_export_snapshot(
                root,
                generated_at=generated_at,
                as_of=as_of,
            ),
            handle,
            sort_keys=False,
        )
    return target


def build_incidents(
    ops_report: GovernanceEvaluationOpsReport,
    *,
    policy: GovernanceEvaluationIncidentPolicy,
    consecutive_failure_count: int,
) -> tuple[GovernanceEvaluationIncident, ...]:
    if ops_report.ops_status == OBSERVABLE_STATUS:
        return ()
    if consecutive_failure_count < policy.repeated_failure_threshold:
        return ()
    route = route_for_status(policy, ops_report.ops_status)
    condition = route.get("condition") or condition_for_status(ops_report.ops_status)
    incident = GovernanceEvaluationIncident(
        incident_id=incident_id_for(condition),
        condition=condition,
        severity=route.get("severity", severity_for_status(ops_report.ops_status)),
        incident_status="open",
        owner_role=route.get("owner_role", "Admin/Ops"),
        action=route.get("action", "triage_governance_evaluation_ops_status"),
        application_ref=application_ref_for(REPORT_ID),
        ops_status=ops_report.ops_status,
        consecutive_failure_count=consecutive_failure_count,
        repeated_failure_threshold=policy.repeated_failure_threshold,
        failed_drill_count=count_failed_drills(ops_report),
        unexpected_error_count=ops_report.unexpected_error_count,
        age_days=None,
        stale_threshold_days=policy.repeated_failure_threshold,
        evidence_refs=(
            f"policy:{policy.policy_id}",
            f"ledger:{LEDGER_ID}",
            "report:governance-evaluation-service-v1",
        ),
        reason=(
            "Governance Evaluation alert drill has failed "
            f"{consecutive_failure_count} consecutive observations, meeting "
            f"the repeated failure threshold of {policy.repeated_failure_threshold}."
        ),
    )
    return (incident,)


def current_consecutive_failure_count(
    ops_report: GovernanceEvaluationOpsReport,
    events: tuple[GovernanceEvaluationAlertDrillEvent, ...],
    *,
    as_of: date,
) -> int:
    if ops_report.ops_status == OBSERVABLE_STATUS:
        return 0
    history_streak = consecutive_failure_count_from_events(events)
    if has_current_observation(ops_report, events, as_of=as_of):
        return history_streak
    return history_streak + 1 if history_streak else 1


def consecutive_failure_count_from_events(
    events: tuple[GovernanceEvaluationAlertDrillEvent, ...],
) -> int:
    count = 0
    for event in reversed(events):
        if event.ops_status == OBSERVABLE_STATUS:
            break
        count += 1
    return count


def has_current_observation(
    ops_report: GovernanceEvaluationOpsReport,
    events: tuple[GovernanceEvaluationAlertDrillEvent, ...],
    *,
    as_of: date,
) -> bool:
    if not events:
        return False
    latest = events[-1]
    return latest.occurred_date == as_of and latest.ops_status == ops_report.ops_status


def route_for_status(
    policy: GovernanceEvaluationIncidentPolicy,
    ops_status: str,
) -> dict[str, str]:
    return policy.incident_routes.get(
        ops_status,
        {
            "severity": severity_for_status(ops_status),
            "owner_role": "Admin/Ops",
            "action": "triage_governance_evaluation_ops_status",
            "condition": condition_for_status(ops_status),
        },
    )


def severity_for_status(ops_status: str) -> str:
    if ops_status.startswith("blocked"):
        return "p0"
    return "p1"


def condition_for_status(ops_status: str) -> str:
    normalized = ops_status.replace("blocked_by_", "").replace("attention_required_", "")
    return f"governance_evaluation_{normalized}"


def count_failed_drills(ops_report: GovernanceEvaluationOpsReport) -> int:
    return sum(1 for drill in ops_report.drills if not drill.passed)


def load_incident_policy(root: Path) -> GovernanceEvaluationIncidentPolicy:
    path = (
        root
        / "platform"
        / "governance"
        / "policies"
        / "governance-evaluation-incident-policy.yaml"
    )
    if not path.exists():
        return GovernanceEvaluationIncidentPolicy(
            policy_id=POLICY_ID,
            repeated_failure_threshold=DEFAULT_REPEATED_FAILURE_THRESHOLD,
            incident_routes=DEFAULT_INCIDENT_ROUTES,
        )
    payload = load_yaml(path)
    return GovernanceEvaluationIncidentPolicy.from_dict(payload)


def load_alert_drill_events(root: Path) -> tuple[GovernanceEvaluationAlertDrillEvent, ...]:
    path = (
        root
        / "platform"
        / "governance"
        / "ledgers"
        / "governance-evaluation-alert-drill-ledger.yaml"
    )
    if not path.exists():
        return ()
    payload = load_yaml(path)
    raw_events = payload.get("events") or ()
    if not isinstance(raw_events, list):
        return ()
    return tuple(
        GovernanceEvaluationAlertDrillEvent(
            event_id=str(item.get("event_id") or ""),
            occurred_at=str(item.get("occurred_at") or ""),
            ops_status=str(item.get("ops_status") or ""),
            failed_drill_count=int(item.get("failed_drill_count") or 0),
            unexpected_error_count=int(item.get("unexpected_error_count") or 0),
            evidence_refs=tuple(str(ref) for ref in item.get("evidence_refs") or ()),
        )
        for item in raw_events
        if isinstance(item, dict)
    )


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


def parse_report_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    if value is None:
        return date.today()
    return date.fromisoformat(value[:10])


def event_sort_key(event: GovernanceEvaluationAlertDrillEvent) -> tuple[str, str]:
    return event.occurred_at, event.event_id


def application_ref_for(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"platform:{digest}"


def incident_id_for(condition: str) -> str:
    digest = hashlib.sha256(f"{REPORT_ID}:{condition}".encode()).hexdigest()[:16]
    return f"gei-{digest}-{condition.replace('_', '-')}"


def count_raw_identifier_markers(
    incidents: tuple[GovernanceEvaluationIncident, ...],
) -> int:
    payload = json.dumps(
        [incident.to_snapshot_dict() for incident in incidents],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_action_queue(
    incidents: tuple[GovernanceEvaluationIncident, ...],
) -> dict[str, list[str]]:
    queue = {
        "open": ids_for_status(incidents, "open"),
        "watch": ids_for_status(incidents, "watch"),
        "p0": ids_for_severity(incidents, "p0"),
        "p1": ids_for_severity(incidents, "p1"),
        "p2": ids_for_severity(incidents, "p2"),
    }
    for condition in (
        "governance_evaluation_release_gate_mismatch",
        "governance_evaluation_unexpected_error",
        "governance_evaluation_guardrail_gap",
    ):
        queue[condition] = ids_for_condition(incidents, condition)
    return queue


def ids_for_status(
    incidents: tuple[GovernanceEvaluationIncident, ...],
    status: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.incident_status == status]


def ids_for_severity(
    incidents: tuple[GovernanceEvaluationIncident, ...],
    severity: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.severity == severity]


def ids_for_condition(
    incidents: tuple[GovernanceEvaluationIncident, ...],
    condition: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.condition == condition]


def count_status(
    incidents: tuple[GovernanceEvaluationIncident, ...],
    status: str,
) -> int:
    return len(ids_for_status(incidents, status))


def count_severity(
    incidents: tuple[GovernanceEvaluationIncident, ...],
    severity: str,
) -> int:
    return len(ids_for_severity(incidents, severity))


def count_by(
    incidents: tuple[GovernanceEvaluationIncident, ...],
    attribute: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for incident in incidents:
        value = getattr(incident, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "governance-evaluation-incident-export-v1.yaml"
    )
