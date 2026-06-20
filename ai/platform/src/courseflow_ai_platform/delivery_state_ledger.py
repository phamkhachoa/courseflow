from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

DELIVERY_STATE_TARGET_STATUSES = ("in_progress", "done", "accepted")


@dataclass(frozen=True, slots=True)
class DeliveryStateTransition:
    transition_id: str
    action_id: str
    target_status: str
    updated_at: str
    updated_by: str
    reason: str
    evidence_refs: tuple[str, ...]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> DeliveryStateTransition:
        transition_id = require_str(row, "transition_id", "delivery state transition")
        target_status = require_str(
            row,
            "target_status",
            f"delivery state transition {transition_id}",
        ).lower()
        if target_status not in DELIVERY_STATE_TARGET_STATUSES:
            raise RegistryValidationError(
                f"delivery state transition {transition_id} target_status must be one "
                f"of {', '.join(DELIVERY_STATE_TARGET_STATUSES)}"
            )
        return cls(
            transition_id=transition_id,
            action_id=require_str(
                row,
                "action_id",
                f"delivery state transition {transition_id}",
            ),
            target_status=target_status,
            updated_at=require_str(
                row,
                "updated_at",
                f"delivery state transition {transition_id}",
            ),
            updated_by=require_str(
                row,
                "updated_by",
                f"delivery state transition {transition_id}",
            ),
            reason=require_str(row, "reason", f"delivery state transition {transition_id}"),
            evidence_refs=normalize_string_tuple(row.get("evidence_refs", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionId": self.action_id,
            "evidenceRefs": list(self.evidence_refs),
            "reason": self.reason,
            "targetStatus": self.target_status,
            "transitionId": self.transition_id,
            "updatedAt": self.updated_at,
            "updatedBy": self.updated_by,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "action_id": self.action_id,
            "target_status": self.target_status,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class DeliveryStateItem:
    transition_id: str
    action_id: str
    previous_status: str
    target_status: str
    applied_status: str
    transition_status: str
    item_found: bool
    backlog_id: str
    owner_role: str
    delivery_phase: str
    updated_at: str
    updated_by: str
    reason: str
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionId": self.action_id,
            "appliedStatus": self.applied_status,
            "backlogId": self.backlog_id,
            "deliveryPhase": self.delivery_phase,
            "evidenceRefs": list(self.evidence_refs),
            "itemFound": self.item_found,
            "ownerRole": self.owner_role,
            "previousStatus": self.previous_status,
            "reason": self.reason,
            "targetStatus": self.target_status,
            "transitionId": self.transition_id,
            "transitionStatus": self.transition_status,
            "updatedAt": self.updated_at,
            "updatedBy": self.updated_by,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "action_id": self.action_id,
            "previous_status": self.previous_status,
            "target_status": self.target_status,
            "applied_status": self.applied_status,
            "transition_status": self.transition_status,
            "item_found": self.item_found,
            "backlog_id": self.backlog_id,
            "owner_role": self.owner_role,
            "delivery_phase": self.delivery_phase,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class DeliveryStateReport:
    transition_count: int
    applied_count: int
    missing_action_count: int
    in_progress_count: int
    done_count: int
    accepted_count: int
    by_target_status: dict[str, int]
    by_transition_status: dict[str, int]
    action_queue: dict[str, list[str]]
    items: tuple[DeliveryStateItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "acceptedCount": self.accepted_count,
            "actionQueue": self.action_queue,
            "appliedCount": self.applied_count,
            "byTargetStatus": self.by_target_status,
            "byTransitionStatus": self.by_transition_status,
            "doneCount": self.done_count,
            "inProgressCount": self.in_progress_count,
            "items": [item.to_dict() for item in self.items],
            "missingActionCount": self.missing_action_count,
            "transitionCount": self.transition_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "delivery-state-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "transition_count": self.transition_count,
                "applied_count": self.applied_count,
                "missing_action_count": self.missing_action_count,
                "in_progress_count": self.in_progress_count,
                "done_count": self.done_count,
                "accepted_count": self.accepted_count,
            },
            "by_target_status": self.by_target_status,
            "by_transition_status": self.by_transition_status,
            "action_queue": self.action_queue,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def load_delivery_state_transitions(
    ai_root: Path | str,
) -> tuple[DeliveryStateTransition, ...]:
    root = Path(ai_root)
    path = default_ledger_path(root)
    if not path.exists():
        return ()
    ledger = load_yaml(path)
    rows = require_mapping_list(ledger, "transitions", path)
    transitions = tuple(DeliveryStateTransition.from_dict(row) for row in rows)
    validate_unique_transition_ids(transitions, path)
    validate_unique_action_ids(transitions, path)
    return transitions


def build_delivery_state_report(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
) -> DeliveryStateReport:
    from courseflow_ai_platform.delivery_backlog import build_delivery_backlog_report

    base_backlog = build_delivery_backlog_report(
        ai_root,
        as_of=as_of,
        apply_state_ledger=False,
    )
    return build_delivery_state_report_from_backlog(
        base_backlog,
        load_delivery_state_transitions(ai_root),
    )


def build_delivery_state_report_from_backlog(
    backlog_report: Any,
    transitions: tuple[DeliveryStateTransition, ...],
) -> DeliveryStateReport:
    items_by_action_id = {item.action_id: item for item in backlog_report.items}
    items = tuple(
        build_delivery_state_item(transition, items_by_action_id.get(transition.action_id))
        for transition in transitions
    )
    return DeliveryStateReport(
        transition_count=len(items),
        applied_count=count_transition_status(items, "applied"),
        missing_action_count=count_transition_status(items, "missing_action"),
        in_progress_count=count_target_status(items, "in_progress"),
        done_count=count_target_status(items, "done"),
        accepted_count=count_target_status(items, "accepted"),
        by_target_status=count_by(items, "target_status"),
        by_transition_status=count_by(items, "transition_status"),
        action_queue={
            "applied": ids_for_transition_status(items, "applied"),
            "missing_action": ids_for_transition_status(items, "missing_action"),
            "in_progress": ids_for_target_status(items, "in_progress"),
            "done": ids_for_target_status(items, "done"),
            "accepted": ids_for_target_status(items, "accepted"),
        },
        items=items,
    )


def build_delivery_state_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_delivery_state_report(ai_root, as_of=report_date).to_snapshot_dict(
        generated_at=report_date
    )


def write_delivery_state_snapshot(
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
            build_delivery_state_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_delivery_state_item(
    transition: DeliveryStateTransition,
    backlog_item: Any | None,
) -> DeliveryStateItem:
    if backlog_item is None:
        return DeliveryStateItem(
            transition_id=transition.transition_id,
            action_id=transition.action_id,
            previous_status="",
            target_status=transition.target_status,
            applied_status="",
            transition_status="missing_action",
            item_found=False,
            backlog_id="",
            owner_role="",
            delivery_phase="",
            updated_at=transition.updated_at,
            updated_by=transition.updated_by,
            reason=transition.reason,
            evidence_refs=transition.evidence_refs,
        )
    return DeliveryStateItem(
        transition_id=transition.transition_id,
        action_id=transition.action_id,
        previous_status=backlog_item.status,
        target_status=transition.target_status,
        applied_status=transition.target_status,
        transition_status="applied",
        item_found=True,
        backlog_id=backlog_item.backlog_id,
        owner_role=backlog_item.owner_role,
        delivery_phase=backlog_item.delivery_phase,
        updated_at=transition.updated_at,
        updated_by=transition.updated_by,
        reason=transition.reason,
        evidence_refs=transition.evidence_refs,
    )


def validate_unique_transition_ids(
    transitions: tuple[DeliveryStateTransition, ...],
    path: Path,
) -> None:
    seen: set[str] = set()
    for transition in transitions:
        if transition.transition_id in seen:
            raise RegistryValidationError(
                f"{path} duplicates transition_id: {transition.transition_id}"
            )
        seen.add(transition.transition_id)


def validate_unique_action_ids(
    transitions: tuple[DeliveryStateTransition, ...],
    path: Path,
) -> None:
    seen: set[str] = set()
    for transition in transitions:
        if transition.action_id in seen:
            raise RegistryValidationError(
                f"{path} duplicates action_id: {transition.action_id}"
            )
        seen.add(transition.action_id)


def normalize_string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise RegistryValidationError("delivery state evidence_refs must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(
                "delivery state evidence_refs values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def require_mapping_list(row: dict[str, Any], key: str, path: Path) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{path} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{path} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def ids_for_transition_status(items: tuple[DeliveryStateItem, ...], status: str) -> list[str]:
    return [item.transition_id for item in items if item.transition_status == status]


def ids_for_target_status(items: tuple[DeliveryStateItem, ...], status: str) -> list[str]:
    return [item.transition_id for item in items if item.target_status == status]


def count_transition_status(items: tuple[DeliveryStateItem, ...], status: str) -> int:
    return len(ids_for_transition_status(items, status))


def count_target_status(items: tuple[DeliveryStateItem, ...], status: str) -> int:
    return len(ids_for_target_status(items, status))


def count_by(items: tuple[DeliveryStateItem, ...], attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def default_ledger_path(root: Path) -> Path:
    return root / "platform" / "delivery" / "ledgers" / "delivery-state-ledger.yaml"


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "delivery" / "reports" / "delivery-state-v1.yaml"
