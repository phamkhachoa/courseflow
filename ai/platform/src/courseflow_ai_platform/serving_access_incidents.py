from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.serving_access_apply_ledger import (
    ServingAccessApplyLedgerItem,
    ServingAccessApplyLedgerReport,
    build_serving_access_apply_ledger_report,
)
from courseflow_ai_platform.serving_access_policy_reconciliation import (
    ServingAccessPolicyReconciliationItem,
    ServingAccessPolicyReconciliationReport,
    build_serving_access_policy_reconciliation_report,
)

STALE_PENDING_APPLY_DAYS = 2
RAW_IDENTIFIER_MARKERS = ("tenant-lms", "service:", "token", "secret")
DRIFT_RECONCILIATION_STATUSES = {
    "active_policy_drift",
    "ledger_claims_apply_but_source_policy_active",
    "ledger_invalid",
}


@dataclass(frozen=True, slots=True)
class ServingAccessIncident:
    incident_id: str
    condition: str
    severity: str
    incident_status: str
    owner_role: str
    action: str
    application_ref: str
    ledger_status: str
    reconciliation_status: str
    age_days: int | None
    stale_threshold_days: int
    request_count: int
    checksum_refs: dict[str, str]
    evidence_refs: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "ageDays": self.age_days,
            "applicationRef": self.application_ref,
            "checksumRefs": self.checksum_refs,
            "condition": self.condition,
            "evidenceRefs": list(self.evidence_refs),
            "incidentId": self.incident_id,
            "ledgerStatus": self.ledger_status,
            "ownerRole": self.owner_role,
            "reason": self.reason,
            "reconciliationStatus": self.reconciliation_status,
            "requestCount": self.request_count,
            "severity": self.severity,
            "staleThresholdDays": self.stale_threshold_days,
            "status": self.incident_status,
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
            "ledger_status": self.ledger_status,
            "reconciliation_status": self.reconciliation_status,
            "age_days": self.age_days,
            "stale_threshold_days": self.stale_threshold_days,
            "request_count": self.request_count,
            "checksum_refs": self.checksum_refs,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ServingAccessIncidentExport:
    as_of: date
    stale_threshold_days: int
    incident_count: int
    open_count: int
    watch_count: int
    p0_count: int
    p1_count: int
    p2_count: int
    drift_count: int
    blocked_apply_count: int
    stale_pending_apply_count: int
    tenant_safe: bool
    raw_identifier_count: int
    omitted_sensitive_fields: tuple[str, ...]
    by_condition: dict[str, int]
    by_severity: dict[str, int]
    by_status: dict[str, int]
    action_queue: dict[str, list[str]]
    incidents: tuple[ServingAccessIncident, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": self.action_queue,
            "asOf": self.as_of.isoformat(),
            "blockedApplyCount": self.blocked_apply_count,
            "byCondition": self.by_condition,
            "bySeverity": self.by_severity,
            "byStatus": self.by_status,
            "driftCount": self.drift_count,
            "incidentCount": self.incident_count,
            "incidents": [incident.to_dict() for incident in self.incidents],
            "omittedSensitiveFields": list(self.omitted_sensitive_fields),
            "openCount": self.open_count,
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "p2Count": self.p2_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "stalePendingApplyCount": self.stale_pending_apply_count,
            "staleThresholdDays": self.stale_threshold_days,
            "tenantSafe": self.tenant_safe,
            "watchCount": self.watch_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "model-serving-access-incident-export-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "as_of": self.as_of.isoformat(),
                "incident_count": self.incident_count,
                "open_count": self.open_count,
                "watch_count": self.watch_count,
                "p0_count": self.p0_count,
                "p1_count": self.p1_count,
                "p2_count": self.p2_count,
                "drift_count": self.drift_count,
                "blocked_apply_count": self.blocked_apply_count,
                "stale_pending_apply_count": self.stale_pending_apply_count,
                "stale_threshold_days": self.stale_threshold_days,
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


def build_serving_access_incident_export(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
    stale_threshold_days: int = STALE_PENDING_APPLY_DAYS,
) -> ServingAccessIncidentExport:
    root = Path(ai_root)
    return build_serving_access_incident_export_from_reports(
        reconciliation_report=build_serving_access_policy_reconciliation_report(root),
        apply_ledger_report=build_serving_access_apply_ledger_report(root),
        as_of=as_of,
        stale_threshold_days=stale_threshold_days,
    )


def build_serving_access_incident_export_from_reports(
    *,
    reconciliation_report: ServingAccessPolicyReconciliationReport,
    apply_ledger_report: ServingAccessApplyLedgerReport,
    as_of: str | date | None = None,
    stale_threshold_days: int = STALE_PENDING_APPLY_DAYS,
) -> ServingAccessIncidentExport:
    report_date = parse_report_date(as_of)
    ledger_items_by_id = {
        item.application_id: item for item in apply_ledger_report.items
    }
    incidents: list[ServingAccessIncident] = []
    for item in reconciliation_report.items:
        ledger_item = ledger_items_by_id.get(item.application_id)
        incident = incident_from_reconciliation_item(
            item,
            ledger_item=ledger_item,
            as_of=report_date,
            stale_threshold_days=stale_threshold_days,
        )
        if incident is not None:
            incidents.append(incident)
    for item in apply_ledger_report.items:
        if item.action == "block_policy_apply_until_ledger_fixed":
            incidents.append(
                incident_from_blocked_apply_item(
                    item,
                    stale_threshold_days=stale_threshold_days,
                )
            )

    sorted_incidents = tuple(sorted(incidents, key=incident_sort_key))
    raw_identifier_count = count_raw_identifier_markers(sorted_incidents)
    return ServingAccessIncidentExport(
        as_of=report_date,
        stale_threshold_days=stale_threshold_days,
        incident_count=len(sorted_incidents),
        open_count=count_status(sorted_incidents, "open"),
        watch_count=count_status(sorted_incidents, "watch"),
        p0_count=count_severity(sorted_incidents, "p0"),
        p1_count=count_severity(sorted_incidents, "p1"),
        p2_count=count_severity(sorted_incidents, "p2"),
        drift_count=sum(
            1
            for incident in sorted_incidents
            if incident.condition in {"policy_drift", "ledger_invalid"}
        ),
        blocked_apply_count=count_condition(sorted_incidents, "blocked_policy_apply"),
        stale_pending_apply_count=count_condition(
            sorted_incidents,
            "stale_pending_policy_apply",
        ),
        tenant_safe=raw_identifier_count == 0,
        raw_identifier_count=raw_identifier_count,
        omitted_sensitive_fields=(
            "principal_ids",
            "tenant_ids",
            "request_ids",
            "credential_values",
        ),
        by_condition=count_by(sorted_incidents, "condition"),
        by_severity=count_by(sorted_incidents, "severity"),
        by_status=count_by(sorted_incidents, "incident_status"),
        action_queue=build_action_queue(sorted_incidents),
        incidents=sorted_incidents,
    )


def build_serving_access_incident_export_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    as_of: str | date | None = None,
    stale_threshold_days: int = STALE_PENDING_APPLY_DAYS,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_serving_access_incident_export(
        ai_root,
        as_of=as_of or generated_at,
        stale_threshold_days=stale_threshold_days,
    ).to_snapshot_dict(generated_at=report_date)


def write_serving_access_incident_export_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
    as_of: str | date | None = None,
    stale_threshold_days: int = STALE_PENDING_APPLY_DAYS,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_serving_access_incident_export_snapshot(
                root,
                generated_at=generated_at,
                as_of=as_of,
                stale_threshold_days=stale_threshold_days,
            ),
            handle,
            sort_keys=False,
        )
    return target


def incident_from_reconciliation_item(
    item: ServingAccessPolicyReconciliationItem,
    *,
    ledger_item: ServingAccessApplyLedgerItem | None,
    as_of: date,
    stale_threshold_days: int,
) -> ServingAccessIncident | None:
    if item.reconciliation_status in DRIFT_RECONCILIATION_STATUSES:
        return build_incident(
            item,
            condition=condition_for_drift_status(item.reconciliation_status),
            severity="p0",
            incident_status="open",
            owner_role="Admin/Ops + Governance Reviewer",
            action=item.action,
            age_days=age_days_for_ledger_item(ledger_item, as_of=as_of),
            stale_threshold_days=stale_threshold_days,
            reason="Active serving access policy differs from the ledger checkpoint.",
        )
    if item.reconciliation_status == "ledger_update_required":
        return build_incident(
            item,
            condition="ledger_update_required",
            severity="p1",
            incident_status="open",
            owner_role="Admin/Ops + Governance Reviewer",
            action=item.action,
            age_days=age_days_for_ledger_item(ledger_item, as_of=as_of),
            stale_threshold_days=stale_threshold_days,
            reason="Active policy matches the proposal but the apply ledger is not closed.",
        )
    if item.reconciliation_status != "pending_policy_apply":
        return None

    age_days = age_days_for_ledger_item(ledger_item, as_of=as_of)
    if age_days is not None and age_days > stale_threshold_days:
        return build_incident(
            item,
            condition="stale_pending_policy_apply",
            severity="p1",
            incident_status="open",
            owner_role="Admin/Ops",
            action="escalate_stale_policy_apply",
            age_days=age_days,
            stale_threshold_days=stale_threshold_days,
            reason="Approved policy application has waited beyond the apply handoff SLA.",
        )
    return build_incident(
        item,
        condition="pending_policy_apply",
        severity="p2",
        incident_status="watch",
        owner_role="Admin/Ops",
        action=item.action,
        age_days=age_days,
        stale_threshold_days=stale_threshold_days,
        reason="Approved policy application is queued for the controlled applier.",
    )


def incident_from_blocked_apply_item(
    item: ServingAccessApplyLedgerItem,
    *,
    stale_threshold_days: int,
) -> ServingAccessIncident:
    application_ref = application_ref_for(item.application_id)
    incident_id = incident_id_for(item.application_id, "blocked_policy_apply")
    return ServingAccessIncident(
        incident_id=incident_id,
        condition="blocked_policy_apply",
        severity="p0",
        incident_status="open",
        owner_role="Admin/Ops + Governance Reviewer",
        action=item.action,
        application_ref=application_ref,
        ledger_status=item.status,
        reconciliation_status="not_reconciled",
        age_days=None,
        stale_threshold_days=stale_threshold_days,
        request_count=len(item.request_ids),
        checksum_refs={
            "expected_proposed_policy": item.expected_proposed_policy_sha256,
            "expected_source_policy": item.expected_source_policy_sha256,
            "proposed_policy": item.proposed_policy_sha256,
            "source_policy": item.source_policy_sha256,
        },
        evidence_refs=(
            "ledger:model-serving-access-policy-apply-ledger-v1",
            "report:model-serving-access-policy-apply-ledger-v1",
        ),
        reason="Apply ledger validation or reviewer state blocks policy application.",
    )


def build_incident(
    item: ServingAccessPolicyReconciliationItem,
    *,
    condition: str,
    severity: str,
    incident_status: str,
    owner_role: str,
    action: str,
    age_days: int | None,
    stale_threshold_days: int,
    reason: str,
) -> ServingAccessIncident:
    return ServingAccessIncident(
        incident_id=incident_id_for(item.application_id, condition),
        condition=condition,
        severity=severity,
        incident_status=incident_status,
        owner_role=owner_role,
        action=action,
        application_ref=application_ref_for(item.application_id),
        ledger_status=item.ledger_status,
        reconciliation_status=item.reconciliation_status,
        age_days=age_days,
        stale_threshold_days=stale_threshold_days,
        request_count=len(item.request_ids),
        checksum_refs={
            "active_policy": item.active_policy_sha256,
            "applied_policy": item.applied_policy_sha256,
            "proposed_policy": item.proposed_policy_sha256,
            "source_policy": item.source_policy_sha256,
        },
        evidence_refs=(
            "ledger:model-serving-access-policy-apply-ledger-v1",
            "report:model-serving-access-policy-reconciliation-v1",
        ),
        reason=reason,
    )


def condition_for_drift_status(reconciliation_status: str) -> str:
    if reconciliation_status == "ledger_invalid":
        return "ledger_invalid"
    return "policy_drift"


def age_days_for_ledger_item(
    item: ServingAccessApplyLedgerItem | None,
    *,
    as_of: date,
) -> int | None:
    if item is None:
        return None
    reviewed_dates = tuple(
        parsed
        for parsed in (
            parse_ledger_timestamp(reviewer.reviewed_at) for reviewer in item.reviewers
        )
        if parsed is not None
    )
    if not reviewed_dates:
        return None
    return max(0, (as_of - max(reviewed_dates)).days)


def parse_ledger_timestamp(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_report_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    if value is None:
        return date.today()
    return date.fromisoformat(value[:10])


def application_ref_for(application_id: str) -> str:
    digest = hashlib.sha256(application_id.encode("utf-8")).hexdigest()[:16]
    return f"application:{digest}"


def incident_id_for(application_id: str, condition: str) -> str:
    digest = hashlib.sha256(f"{application_id}:{condition}".encode()).hexdigest()[:16]
    return f"sai-{digest}-{condition.replace('_', '-')}"


def count_raw_identifier_markers(
    incidents: tuple[ServingAccessIncident, ...],
) -> int:
    payload = json.dumps(
        [incident.to_snapshot_dict() for incident in incidents],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_action_queue(
    incidents: tuple[ServingAccessIncident, ...],
) -> dict[str, list[str]]:
    queue = {
        "open": ids_for_status(incidents, "open"),
        "watch": ids_for_status(incidents, "watch"),
        "p0": ids_for_severity(incidents, "p0"),
        "p1": ids_for_severity(incidents, "p1"),
        "p2": ids_for_severity(incidents, "p2"),
    }
    for condition in (
        "policy_drift",
        "ledger_invalid",
        "blocked_policy_apply",
        "stale_pending_policy_apply",
        "pending_policy_apply",
        "ledger_update_required",
    ):
        queue[condition] = ids_for_condition(incidents, condition)
    return queue


def ids_for_status(
    incidents: tuple[ServingAccessIncident, ...],
    status: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.incident_status == status]


def ids_for_severity(
    incidents: tuple[ServingAccessIncident, ...],
    severity: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.severity == severity]


def ids_for_condition(
    incidents: tuple[ServingAccessIncident, ...],
    condition: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.condition == condition]


def count_status(
    incidents: tuple[ServingAccessIncident, ...],
    status: str,
) -> int:
    return len(ids_for_status(incidents, status))


def count_severity(
    incidents: tuple[ServingAccessIncident, ...],
    severity: str,
) -> int:
    return len(ids_for_severity(incidents, severity))


def count_condition(
    incidents: tuple[ServingAccessIncident, ...],
    condition: str,
) -> int:
    return len(ids_for_condition(incidents, condition))


def count_by(
    incidents: tuple[ServingAccessIncident, ...],
    attribute: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for incident in incidents:
        value = getattr(incident, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def incident_sort_key(incident: ServingAccessIncident) -> tuple[int, str, str]:
    severity_rank = {"p0": 0, "p1": 1, "p2": 2}.get(incident.severity, 9)
    return severity_rank, incident.condition, incident.incident_id


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "model-serving-access-incident-export-v1.yaml"
    )
