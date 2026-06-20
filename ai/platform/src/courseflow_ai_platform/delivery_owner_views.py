from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.delivery_sla import (
    DeliverySlaItem,
    DeliverySlaReport,
    build_delivery_sla_report,
    parse_optional_date,
)
from courseflow_ai_platform.governance_evaluation_incidents import (
    GovernanceEvaluationIncident,
    GovernanceEvaluationIncidentExport,
    build_governance_evaluation_incident_export,
)
from courseflow_ai_platform.product_readiness_freshness_incidents import (
    ProductReadinessFreshnessIncident,
    ProductReadinessFreshnessIncidentExport,
    build_product_readiness_freshness_incident_export,
)
from courseflow_ai_platform.serving_access_incidents import (
    ServingAccessIncident,
    ServingAccessIncidentExport,
    build_serving_access_incident_export,
)

OVERLOADED_OWNER_ITEM_THRESHOLD = 5
PRIORITY_ORDER = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
SLA_STATUS_ORDER = {"overdue": 0, "due_soon": 1, "on_track": 2, "monitoring": 3}
INCIDENT_PRIORITY_ORDER = {"p0": 0, "p1": 1}
OwnerVisibleIncident = (
    ServingAccessIncident
    | GovernanceEvaluationIncident
    | ProductReadinessFreshnessIncident
)
OwnerVisibleIncidentExport = (
    ServingAccessIncidentExport
    | GovernanceEvaluationIncidentExport
    | ProductReadinessFreshnessIncidentExport
)


@dataclass(frozen=True, slots=True)
class DeliveryOwnerViewItem:
    backlog_id: str
    title: str
    priority: str
    status: str
    delivery_phase: str
    sla_status: str
    due_at: str
    days_until_due: int
    next_review_at: str
    refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "backlogId": self.backlog_id,
            "daysUntilDue": self.days_until_due,
            "deliveryPhase": self.delivery_phase,
            "dueAt": self.due_at,
            "nextReviewAt": self.next_review_at,
            "priority": self.priority,
            "refs": list(self.refs),
            "slaStatus": self.sla_status,
            "status": self.status,
            "title": self.title,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "backlog_id": self.backlog_id,
            "title": self.title,
            "priority": self.priority,
            "status": self.status,
            "delivery_phase": self.delivery_phase,
            "sla_status": self.sla_status,
            "due_at": self.due_at,
            "days_until_due": self.days_until_due,
            "next_review_at": self.next_review_at,
            "refs": list(self.refs),
        }


@dataclass(frozen=True, slots=True)
class DeliveryOwnerIncidentItem:
    incident_id: str
    condition: str
    severity: str
    status: str
    action: str
    application_ref: str
    age_days: int | None
    stale_threshold_days: int
    refs: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "ageDays": self.age_days,
            "applicationRef": self.application_ref,
            "condition": self.condition,
            "incidentId": self.incident_id,
            "reason": self.reason,
            "refs": list(self.refs),
            "severity": self.severity,
            "staleThresholdDays": self.stale_threshold_days,
            "status": self.status,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "condition": self.condition,
            "severity": self.severity,
            "status": self.status,
            "action": self.action,
            "application_ref": self.application_ref,
            "age_days": self.age_days,
            "stale_threshold_days": self.stale_threshold_days,
            "refs": list(self.refs),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DeliveryOwnerView:
    owner_alias: str
    owner_roles: tuple[str, ...]
    escalation_roles: tuple[str, ...]
    item_count: int
    overdue_count: int
    due_soon_count: int
    on_track_count: int
    monitoring_count: int
    p0_count: int
    p1_count: int
    p2_count: int
    p3_count: int
    incident_count: int
    open_incident_count: int
    p0_incident_count: int
    p1_incident_count: int
    next_due_at: str
    next_review_at: str
    by_phase: dict[str, int]
    backlog_ids: tuple[str, ...]
    incident_ids: tuple[str, ...]
    items: tuple[DeliveryOwnerViewItem, ...]
    incidents: tuple[DeliveryOwnerIncidentItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "backlogIds": list(self.backlog_ids),
            "byPhase": self.by_phase,
            "dueSoonCount": self.due_soon_count,
            "escalationRoles": list(self.escalation_roles),
            "incidentCount": self.incident_count,
            "incidentIds": list(self.incident_ids),
            "incidents": [incident.to_dict() for incident in self.incidents],
            "itemCount": self.item_count,
            "items": [item.to_dict() for item in self.items],
            "monitoringCount": self.monitoring_count,
            "nextDueAt": self.next_due_at,
            "nextReviewAt": self.next_review_at,
            "onTrackCount": self.on_track_count,
            "overdueCount": self.overdue_count,
            "ownerAlias": self.owner_alias,
            "ownerRoles": list(self.owner_roles),
            "openIncidentCount": self.open_incident_count,
            "p0Count": self.p0_count,
            "p0IncidentCount": self.p0_incident_count,
            "p1Count": self.p1_count,
            "p1IncidentCount": self.p1_incident_count,
            "p2Count": self.p2_count,
            "p3Count": self.p3_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "owner_alias": self.owner_alias,
            "owner_roles": list(self.owner_roles),
            "escalation_roles": list(self.escalation_roles),
            "item_count": self.item_count,
            "overdue_count": self.overdue_count,
            "due_soon_count": self.due_soon_count,
            "on_track_count": self.on_track_count,
            "monitoring_count": self.monitoring_count,
            "p0_count": self.p0_count,
            "p1_count": self.p1_count,
            "p2_count": self.p2_count,
            "p3_count": self.p3_count,
            "incident_count": self.incident_count,
            "open_incident_count": self.open_incident_count,
            "p0_incident_count": self.p0_incident_count,
            "p1_incident_count": self.p1_incident_count,
            "next_due_at": self.next_due_at,
            "next_review_at": self.next_review_at,
            "by_phase": self.by_phase,
            "backlog_ids": list(self.backlog_ids),
            "incident_ids": list(self.incident_ids),
            "items": [item.to_snapshot_dict() for item in self.items],
            "incidents": [incident.to_snapshot_dict() for incident in self.incidents],
        }


@dataclass(frozen=True, slots=True)
class DeliveryOwnerViewsReport:
    owner_count: int
    item_count: int
    overloaded_owner_count: int
    due_soon_owner_count: int
    overdue_owner_count: int
    monitoring_owner_count: int
    missing_owner_alias_count: int
    incident_count: int
    open_incident_count: int
    owners_with_open_incidents_count: int
    top_owner_alias: str
    views: tuple[DeliveryOwnerView, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dueSoonOwnerCount": self.due_soon_owner_count,
            "itemCount": self.item_count,
            "missingOwnerAliasCount": self.missing_owner_alias_count,
            "monitoringOwnerCount": self.monitoring_owner_count,
            "incidentCount": self.incident_count,
            "openIncidentCount": self.open_incident_count,
            "overdueOwnerCount": self.overdue_owner_count,
            "overloadedOwnerCount": self.overloaded_owner_count,
            "ownerCount": self.owner_count,
            "ownersWithOpenIncidentsCount": self.owners_with_open_incidents_count,
            "topOwnerAlias": self.top_owner_alias,
            "views": [view.to_dict() for view in self.views],
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "delivery-owner-views-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "owner_count": self.owner_count,
                "item_count": self.item_count,
                "overloaded_owner_count": self.overloaded_owner_count,
                "due_soon_owner_count": self.due_soon_owner_count,
                "overdue_owner_count": self.overdue_owner_count,
                "monitoring_owner_count": self.monitoring_owner_count,
                "missing_owner_alias_count": self.missing_owner_alias_count,
                "incident_count": self.incident_count,
                "open_incident_count": self.open_incident_count,
                "owners_with_open_incidents_count": self.owners_with_open_incidents_count,
                "top_owner_alias": self.top_owner_alias,
            },
            "owner_views": [view.to_snapshot_dict() for view in self.views],
        }


def build_delivery_owner_views_report(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
) -> DeliveryOwnerViewsReport:
    report_date = parse_optional_date(as_of)
    sla_report = build_delivery_sla_report(ai_root, as_of=report_date)
    incident_export = build_serving_access_incident_export(ai_root, as_of=report_date)
    governance_evaluation_incident_export = (
        build_governance_evaluation_incident_export(ai_root, as_of=report_date)
    )
    product_readiness_freshness_incident_export = (
        build_product_readiness_freshness_incident_export(
            ai_root,
            as_of=report_date,
        )
    )
    return build_delivery_owner_views_report_from_sla(
        sla_report,
        incident_export=incident_export,
        governance_evaluation_incident_export=governance_evaluation_incident_export,
        product_readiness_freshness_incident_export=(
            product_readiness_freshness_incident_export
        ),
    )


def build_delivery_owner_views_report_from_sla(
    sla_report: DeliverySlaReport,
    *,
    incident_export: ServingAccessIncidentExport | None = None,
    governance_evaluation_incident_export: GovernanceEvaluationIncidentExport | None = None,
    product_readiness_freshness_incident_export: (
        ProductReadinessFreshnessIncidentExport | None
    ) = None,
) -> DeliveryOwnerViewsReport:
    grouped: dict[str, list[DeliverySlaItem]] = {}
    for item in sla_report.items:
        owner_alias = item.owner_alias or "unassigned"
        grouped.setdefault(owner_alias, []).append(item)

    incident_groups = group_open_incidents_by_owner_alias(
        visible_owner_view_incidents(
            incident_export,
            governance_evaluation_incident_export,
            product_readiness_freshness_incident_export,
        ),
        owner_aliases_by_role=owner_aliases_by_role(sla_report.items),
    )
    owner_aliases = set(grouped) | set(incident_groups)
    views = tuple(
        sorted(
            (
                build_delivery_owner_view(
                    owner_alias,
                    tuple(grouped.get(owner_alias, [])),
                    incidents=tuple(incident_groups.get(owner_alias, [])),
                )
                for owner_alias in owner_aliases
            ),
            key=lambda view: (-view.item_count, view.owner_alias),
        )
    )
    top_owner_alias = views[0].owner_alias if views else ""
    return DeliveryOwnerViewsReport(
        owner_count=len(views),
        item_count=sla_report.item_count,
        overloaded_owner_count=sum(
            1 for view in views if view.item_count >= OVERLOADED_OWNER_ITEM_THRESHOLD
        ),
        due_soon_owner_count=sum(1 for view in views if view.due_soon_count > 0),
        overdue_owner_count=sum(1 for view in views if view.overdue_count > 0),
        monitoring_owner_count=sum(1 for view in views if view.monitoring_count > 0),
        missing_owner_alias_count=sla_report.missing_owner_alias_count,
        incident_count=sum(view.incident_count for view in views),
        open_incident_count=sum(view.open_incident_count for view in views),
        owners_with_open_incidents_count=sum(
            1 for view in views if view.open_incident_count > 0
        ),
        top_owner_alias=top_owner_alias,
        views=views,
    )


def build_delivery_owner_views_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = parse_optional_date(generated_at).isoformat()
    return build_delivery_owner_views_report(ai_root, as_of=report_date).to_snapshot_dict(
        generated_at=report_date
    )


def write_delivery_owner_views_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_delivery_owner_views_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_delivery_owner_view(
    owner_alias: str,
    items: tuple[DeliverySlaItem, ...],
    *,
    incidents: tuple[OwnerVisibleIncident, ...] = (),
) -> DeliveryOwnerView:
    ordered_items = tuple(sorted(items, key=sort_sla_item))
    ordered_incidents = tuple(sorted(incidents, key=sort_incident))
    due_dates = tuple(item.due_at for item in ordered_items if item.sla_status != "monitoring")
    review_dates = tuple(item.next_review_at for item in ordered_items if item.next_review_at)
    return DeliveryOwnerView(
        owner_alias=owner_alias,
        owner_roles=tuple(
            sorted(
                {item.owner_role for item in ordered_items}
                | {incident.owner_role for incident in ordered_incidents}
            )
        ),
        escalation_roles=tuple(
            sorted({item.escalation_role for item in ordered_items if item.escalation_role})
        ),
        item_count=len(ordered_items),
        overdue_count=count_sla_status(ordered_items, "overdue"),
        due_soon_count=count_sla_status(ordered_items, "due_soon"),
        on_track_count=count_sla_status(ordered_items, "on_track"),
        monitoring_count=count_sla_status(ordered_items, "monitoring"),
        p0_count=count_priority(ordered_items, "p0"),
        p1_count=count_priority(ordered_items, "p1"),
        p2_count=count_priority(ordered_items, "p2"),
        p3_count=count_priority(ordered_items, "p3"),
        incident_count=len(ordered_incidents),
        open_incident_count=sum(
            1 for incident in ordered_incidents if incident.incident_status == "open"
        ),
        p0_incident_count=sum(1 for incident in ordered_incidents if incident.severity == "p0"),
        p1_incident_count=sum(1 for incident in ordered_incidents if incident.severity == "p1"),
        next_due_at=min(due_dates) if due_dates else "",
        next_review_at=min(review_dates) if review_dates else "",
        by_phase=count_by_phase(ordered_items),
        backlog_ids=tuple(item.backlog_id for item in ordered_items),
        incident_ids=tuple(incident.incident_id for incident in ordered_incidents),
        items=tuple(to_owner_view_item(item) for item in ordered_items),
        incidents=tuple(to_owner_incident_item(incident) for incident in ordered_incidents),
    )


def to_owner_view_item(item: DeliverySlaItem) -> DeliveryOwnerViewItem:
    return DeliveryOwnerViewItem(
        backlog_id=item.backlog_id,
        title=item.title,
        priority=item.priority,
        status=item.status,
        delivery_phase=item.delivery_phase,
        sla_status=item.sla_status,
        due_at=item.due_at,
        days_until_due=item.days_until_due,
        next_review_at=item.next_review_at,
        refs=item.refs,
    )


def to_owner_incident_item(incident: OwnerVisibleIncident) -> DeliveryOwnerIncidentItem:
    return DeliveryOwnerIncidentItem(
        incident_id=incident.incident_id,
        condition=incident.condition,
        severity=incident.severity,
        status=incident.incident_status,
        action=incident.action,
        application_ref=incident.application_ref,
        age_days=incident.age_days,
        stale_threshold_days=incident.stale_threshold_days,
        refs=incident.evidence_refs,
        reason=incident.reason,
    )


def sort_sla_item(item: DeliverySlaItem) -> tuple[int, int, str, str]:
    sla_order = SLA_STATUS_ORDER.get(item.sla_status, 99)
    priority_order = PRIORITY_ORDER.get(item.priority, 99)
    return (sla_order, priority_order, item.due_at, item.backlog_id)


def sort_incident(incident: OwnerVisibleIncident) -> tuple[int, str, str]:
    priority_order = INCIDENT_PRIORITY_ORDER.get(incident.severity, 99)
    return priority_order, incident.condition, incident.incident_id


def visible_owner_view_incidents(
    *incident_exports: OwnerVisibleIncidentExport | None,
) -> tuple[OwnerVisibleIncident, ...]:
    incidents: list[OwnerVisibleIncident] = []
    for incident_export in incident_exports:
        if incident_export is None:
            continue
        incidents.extend(
            incident
            for incident in incident_export.incidents
            if incident.incident_status == "open" and incident.severity in {"p0", "p1"}
        )
    return tuple(
        sorted(
            incidents,
            key=sort_incident,
        )
    )


def group_open_incidents_by_owner_alias(
    incidents: tuple[OwnerVisibleIncident, ...],
    *,
    owner_aliases_by_role: dict[str, str],
) -> dict[str, list[OwnerVisibleIncident]]:
    grouped: dict[str, list[OwnerVisibleIncident]] = {}
    for incident in incidents:
        owner_alias = owner_aliases_by_role.get(
            incident.owner_role,
            fallback_owner_alias(incident.owner_role),
        )
        grouped.setdefault(owner_alias, []).append(incident)
    return grouped


def owner_aliases_by_role(items: tuple[DeliverySlaItem, ...]) -> dict[str, str]:
    return {
        item.owner_role: item.owner_alias
        for item in items
        if item.owner_role and item.owner_alias
    }


def fallback_owner_alias(owner_role: str) -> str:
    return (
        owner_role.lower()
        .replace("+", "")
        .replace("/", "-")
        .replace(" ", "-")
        .replace("--", "-")
        .strip("-")
    )


def count_sla_status(items: tuple[DeliverySlaItem, ...], status: str) -> int:
    return sum(1 for item in items if item.sla_status == status)


def count_priority(items: tuple[DeliverySlaItem, ...], priority: str) -> int:
    return sum(1 for item in items if item.priority == priority)


def count_by_phase(items: tuple[DeliverySlaItem, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.delivery_phase] = counts.get(item.delivery_phase, 0) + 1
    return dict(sorted(counts.items()))


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "delivery" / "reports" / "delivery-owner-views-v1.yaml"
