from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.delivery_backlog import (
    DeliveryBacklogItem,
    DeliveryBacklogReport,
    build_delivery_backlog_report,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str


@dataclass(frozen=True, slots=True)
class OwnerAlias:
    owner_role: str
    alias: str
    escalation_role: str


@dataclass(frozen=True, slots=True)
class DeliverySlaItem:
    backlog_id: str
    title: str
    owner_role: str
    owner_alias: str
    escalation_role: str
    priority: str
    status: str
    delivery_phase: str
    sla_status: str
    opened_at: str
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
            "escalationRole": self.escalation_role,
            "nextReviewAt": self.next_review_at,
            "openedAt": self.opened_at,
            "ownerAlias": self.owner_alias,
            "ownerRole": self.owner_role,
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
            "owner_role": self.owner_role,
            "owner_alias": self.owner_alias,
            "escalation_role": self.escalation_role,
            "priority": self.priority,
            "status": self.status,
            "delivery_phase": self.delivery_phase,
            "sla_status": self.sla_status,
            "opened_at": self.opened_at,
            "due_at": self.due_at,
            "days_until_due": self.days_until_due,
            "next_review_at": self.next_review_at,
            "refs": list(self.refs),
        }


@dataclass(frozen=True, slots=True)
class DeliverySlaReport:
    item_count: int
    tracked_item_count: int
    monitoring_item_count: int
    overdue_count: int
    due_soon_count: int
    on_track_count: int
    missing_owner_alias_count: int
    by_owner_alias: dict[str, int]
    by_sla_status: dict[str, int]
    items: tuple[DeliverySlaItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byOwnerAlias": self.by_owner_alias,
            "bySlaStatus": self.by_sla_status,
            "dueSoonCount": self.due_soon_count,
            "itemCount": self.item_count,
            "items": [item.to_dict() for item in self.items],
            "missingOwnerAliasCount": self.missing_owner_alias_count,
            "monitoringItemCount": self.monitoring_item_count,
            "onTrackCount": self.on_track_count,
            "overdueCount": self.overdue_count,
            "trackedItemCount": self.tracked_item_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "delivery-sla-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "item_count": self.item_count,
                "tracked_item_count": self.tracked_item_count,
                "monitoring_item_count": self.monitoring_item_count,
                "overdue_count": self.overdue_count,
                "due_soon_count": self.due_soon_count,
                "on_track_count": self.on_track_count,
                "missing_owner_alias_count": self.missing_owner_alias_count,
            },
            "by_owner_alias": self.by_owner_alias,
            "by_sla_status": self.by_sla_status,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_delivery_sla_report(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
) -> DeliverySlaReport:
    root = Path(ai_root)
    as_of_date = parse_optional_date(as_of)
    policy = load_yaml(root / "platform" / "delivery" / "policies" / "sla-policy.yaml")
    backlog = build_delivery_backlog_report(root, as_of=as_of_date)
    return build_delivery_sla_report_from_backlog(backlog, policy, as_of=as_of_date)


def build_delivery_sla_report_from_backlog(
    backlog: DeliveryBacklogReport,
    policy: dict[str, Any],
    *,
    as_of: date,
) -> DeliverySlaReport:
    priority_sla_days = require_positive_int_mapping(
        policy,
        "priority_sla_days",
        "delivery SLA policy",
    )
    monitoring_review_days = require_positive_int_mapping(
        policy,
        "monitoring_review_days",
        "delivery SLA policy",
    )
    due_soon_threshold_days = require_positive_int(
        policy,
        "due_soon_threshold_days",
        "delivery SLA policy",
    )
    owner_aliases = load_owner_aliases(policy)

    items = tuple(
        build_delivery_sla_item(
            item,
            owner_aliases,
            priority_sla_days,
            monitoring_review_days,
            due_soon_threshold_days,
            as_of,
        )
        for item in backlog.items
    )
    return DeliverySlaReport(
        item_count=len(items),
        tracked_item_count=sum(1 for item in items if item.sla_status != "monitoring"),
        monitoring_item_count=sum(1 for item in items if item.sla_status == "monitoring"),
        overdue_count=sum(1 for item in items if item.sla_status == "overdue"),
        due_soon_count=sum(1 for item in items if item.sla_status == "due_soon"),
        on_track_count=sum(1 for item in items if item.sla_status == "on_track"),
        missing_owner_alias_count=sum(1 for item in items if item.owner_alias == ""),
        by_owner_alias=count_by(items, "owner_alias"),
        by_sla_status=count_by(items, "sla_status"),
        items=items,
    )


def build_delivery_sla_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = parse_optional_date(generated_at).isoformat()
    return build_delivery_sla_report(ai_root, as_of=report_date).to_snapshot_dict(
        generated_at=report_date
    )


def write_delivery_sla_snapshot(
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
            build_delivery_sla_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_delivery_sla_item(
    item: DeliveryBacklogItem,
    owner_aliases: dict[str, OwnerAlias],
    priority_sla_days: dict[str, int],
    monitoring_review_days: dict[str, int],
    due_soon_threshold_days: int,
    as_of: date,
) -> DeliverySlaItem:
    owner_alias = owner_aliases.get(item.owner_role)
    if owner_alias is None:
        alias = ""
        escalation_role = ""
    else:
        alias = owner_alias.alias
        escalation_role = owner_alias.escalation_role

    if item.monitoring_item:
        review_days = monitoring_review_days.get(item.status)
        if review_days is None:
            raise RegistryValidationError(
                f"delivery SLA policy misses monitoring review days for {item.status}"
            )
        due_at = as_of + timedelta(days=review_days)
        sla_status = "monitoring"
        next_review_at = due_at.isoformat()
    else:
        sla_days = priority_sla_days.get(item.priority)
        if sla_days is None:
            raise RegistryValidationError(
                f"delivery SLA policy misses priority SLA days for {item.priority}"
            )
        due_at = as_of + timedelta(days=sla_days)
        days_until_due = (due_at - as_of).days
        if days_until_due < 0:
            sla_status = "overdue"
        elif days_until_due <= due_soon_threshold_days:
            sla_status = "due_soon"
        else:
            sla_status = "on_track"
        next_review_at = ""

    return DeliverySlaItem(
        backlog_id=item.backlog_id,
        title=item.title,
        owner_role=item.owner_role,
        owner_alias=alias,
        escalation_role=escalation_role,
        priority=item.priority,
        status=item.status,
        delivery_phase=item.delivery_phase,
        sla_status=sla_status,
        opened_at=as_of.isoformat(),
        due_at=due_at.isoformat(),
        days_until_due=(due_at - as_of).days,
        next_review_at=next_review_at,
        refs=item.refs,
    )


def load_owner_aliases(policy: dict[str, Any]) -> dict[str, OwnerAlias]:
    rows = require_mapping_list(policy, "owner_aliases", "delivery SLA policy")
    aliases: dict[str, OwnerAlias] = {}
    for row in rows:
        owner_role = require_str(row, "owner_role", "delivery SLA owner alias")
        if owner_role in aliases:
            raise RegistryValidationError(
                f"delivery SLA policy duplicate owner alias: {owner_role}"
            )
        aliases[owner_role] = OwnerAlias(
            owner_role=owner_role,
            alias=require_str(row, "alias", f"delivery SLA owner alias {owner_role}"),
            escalation_role=require_str(
                row,
                "escalation_role",
                f"delivery SLA owner alias {owner_role}",
            ),
        )
    return aliases


def require_positive_int_mapping(
    row: dict[str, Any],
    key: str,
    owner: str,
) -> dict[str, int]:
    value = row.get(key)
    if not isinstance(value, dict) or not value:
        raise RegistryValidationError(f"{owner} must define non-empty mapping field {key}")
    result: dict[str, int] = {}
    for name, item in value.items():
        if not isinstance(name, str) or not name.strip():
            raise RegistryValidationError(f"{owner} {key} keys must be strings")
        if not isinstance(item, int) or item <= 0:
            raise RegistryValidationError(f"{owner} {key}.{name} must be a positive integer")
        result[name.strip()] = item
    return result


def require_positive_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or value <= 0:
        raise RegistryValidationError(f"{owner} {key} must be a positive integer")
    return value


def require_mapping_list(row: dict[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def count_by(items: tuple[DeliverySlaItem, ...], attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def parse_optional_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RegistryValidationError(f"invalid delivery SLA date: {value}") from exc


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "delivery" / "reports" / "delivery-sla-v1.yaml"
