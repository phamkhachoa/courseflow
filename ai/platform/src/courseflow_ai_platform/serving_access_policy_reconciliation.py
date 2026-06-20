from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.serving_access_apply_ledger import (
    ServingAccessApplyEntry,
    load_serving_access_apply_entries,
    stable_sha256,
)
from courseflow_ai_platform.serving_access_policy_plan import load_active_policy


@dataclass(frozen=True, slots=True)
class ServingAccessPolicyReconciliationItem:
    application_id: str
    ledger_status: str
    reconciliation_status: str
    action: str
    active_policy_sha256: str
    source_policy_sha256: str
    proposed_policy_sha256: str
    applied_policy_sha256: str
    request_ids: tuple[str, ...]
    validation_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "activePolicySha256": self.active_policy_sha256,
            "applicationId": self.application_id,
            "appliedPolicySha256": self.applied_policy_sha256,
            "ledgerStatus": self.ledger_status,
            "proposedPolicySha256": self.proposed_policy_sha256,
            "reconciliationStatus": self.reconciliation_status,
            "requestIds": list(self.request_ids),
            "sourcePolicySha256": self.source_policy_sha256,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "ledger_status": self.ledger_status,
            "reconciliation_status": self.reconciliation_status,
            "action": self.action,
            "active_policy_sha256": self.active_policy_sha256,
            "source_policy_sha256": self.source_policy_sha256,
            "proposed_policy_sha256": self.proposed_policy_sha256,
            "applied_policy_sha256": self.applied_policy_sha256,
            "request_ids": list(self.request_ids),
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class ServingAccessPolicyReconciliationReport:
    application_count: int
    pending_apply_count: int
    reconciled_count: int
    ledger_update_required_count: int
    drift_count: int
    rejected_count: int
    active_policy_sha256: str
    by_status: dict[str, int]
    by_action: dict[str, int]
    action_queue: dict[str, list[str]]
    items: tuple[ServingAccessPolicyReconciliationItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": self.action_queue,
            "activePolicySha256": self.active_policy_sha256,
            "applicationCount": self.application_count,
            "byAction": self.by_action,
            "byStatus": self.by_status,
            "driftCount": self.drift_count,
            "items": [item.to_dict() for item in self.items],
            "ledgerUpdateRequiredCount": self.ledger_update_required_count,
            "pendingApplyCount": self.pending_apply_count,
            "reconciledCount": self.reconciled_count,
            "rejectedCount": self.rejected_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "model-serving-access-policy-reconciliation-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "application_count": self.application_count,
                "pending_apply_count": self.pending_apply_count,
                "reconciled_count": self.reconciled_count,
                "ledger_update_required_count": self.ledger_update_required_count,
                "drift_count": self.drift_count,
                "rejected_count": self.rejected_count,
                "active_policy_sha256": self.active_policy_sha256,
            },
            "by_status": self.by_status,
            "by_action": self.by_action,
            "action_queue": self.action_queue,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_serving_access_policy_reconciliation_report(
    ai_root: Path | str,
) -> ServingAccessPolicyReconciliationReport:
    root = Path(ai_root)
    active_policy_sha256 = stable_sha256(load_active_policy(root))
    entries = load_serving_access_apply_entries(root)
    items = tuple(build_reconciliation_item(entry, active_policy_sha256) for entry in entries)
    return build_report_from_items(items, active_policy_sha256=active_policy_sha256)


def build_serving_access_policy_reconciliation_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_serving_access_policy_reconciliation_report(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_serving_access_policy_reconciliation_snapshot(
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
            build_serving_access_policy_reconciliation_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


def build_reconciliation_item(
    entry: ServingAccessApplyEntry,
    active_policy_sha256: str,
) -> ServingAccessPolicyReconciliationItem:
    validation_errors = validate_reconciliation_entry(entry)
    reconciliation_status = reconciliation_status_for_entry(
        entry,
        active_policy_sha256=active_policy_sha256,
        validation_errors=validation_errors,
    )
    return ServingAccessPolicyReconciliationItem(
        application_id=entry.application_id,
        ledger_status=entry.status,
        reconciliation_status=reconciliation_status,
        action=action_for_reconciliation_status(reconciliation_status),
        active_policy_sha256=active_policy_sha256,
        source_policy_sha256=entry.source_policy_sha256,
        proposed_policy_sha256=entry.proposed_policy_sha256,
        applied_policy_sha256=entry.applied_policy_sha256,
        request_ids=entry.request_ids,
        validation_errors=tuple(sorted(validation_errors)),
    )


def validate_reconciliation_entry(entry: ServingAccessApplyEntry) -> list[str]:
    errors: list[str] = []
    if entry.status == "applied":
        if not entry.applied_policy_sha256:
            errors.append("applied ledger entry is missing applied_policy_sha256")
        elif entry.applied_policy_sha256 != entry.proposed_policy_sha256:
            errors.append("applied_policy_sha256 does not match proposed_policy_sha256")
        if not entry.applied_at:
            errors.append("applied ledger entry is missing applied_at")
    return errors


def reconciliation_status_for_entry(
    entry: ServingAccessApplyEntry,
    *,
    active_policy_sha256: str,
    validation_errors: list[str],
) -> str:
    if validation_errors:
        return "ledger_invalid"
    if entry.status == "rejected":
        return "closed_rejected"
    if active_policy_sha256 == entry.proposed_policy_sha256:
        if entry.status == "applied" and entry.applied_policy_sha256 == active_policy_sha256:
            return "reconciled"
        return "ledger_update_required"
    if active_policy_sha256 == entry.source_policy_sha256:
        if entry.status == "applied":
            return "ledger_claims_apply_but_source_policy_active"
        return "pending_policy_apply"
    return "active_policy_drift"


def action_for_reconciliation_status(reconciliation_status: str) -> str:
    return {
        "active_policy_drift": "investigate_active_policy_drift",
        "closed_rejected": "close_without_policy_change",
        "ledger_claims_apply_but_source_policy_active": "investigate_missing_policy_write",
        "ledger_invalid": "fix_apply_ledger_entry",
        "ledger_update_required": "record_applied_checksum_in_ledger",
        "pending_policy_apply": "run_controlled_policy_applier",
        "reconciled": "monitor_applied_policy",
    }.get(reconciliation_status, "review_reconciliation_status")


def build_report_from_items(
    items: tuple[ServingAccessPolicyReconciliationItem, ...],
    *,
    active_policy_sha256: str,
) -> ServingAccessPolicyReconciliationReport:
    return ServingAccessPolicyReconciliationReport(
        application_count=len(items),
        pending_apply_count=count_status(items, "pending_policy_apply"),
        reconciled_count=count_status(items, "reconciled"),
        ledger_update_required_count=count_status(items, "ledger_update_required"),
        drift_count=sum(
            1
            for item in items
            if item.reconciliation_status
            in {
                "active_policy_drift",
                "ledger_claims_apply_but_source_policy_active",
                "ledger_invalid",
            }
        ),
        rejected_count=count_status(items, "closed_rejected"),
        active_policy_sha256=active_policy_sha256,
        by_status=count_by(items, "reconciliation_status"),
        by_action=count_by(items, "action"),
        action_queue={
            "pending_apply": ids_for_status(items, "pending_policy_apply"),
            "ledger_update_required": ids_for_status(items, "ledger_update_required"),
            "reconciled": ids_for_status(items, "reconciled"),
            "drift": [
                item.application_id
                for item in items
                if item.reconciliation_status
                in {
                    "active_policy_drift",
                    "ledger_claims_apply_but_source_policy_active",
                    "ledger_invalid",
                }
            ],
            "rejected": ids_for_status(items, "closed_rejected"),
        },
        items=items,
    )


def ids_for_status(
    items: tuple[ServingAccessPolicyReconciliationItem, ...],
    status: str,
) -> list[str]:
    return [item.application_id for item in items if item.reconciliation_status == status]


def count_status(
    items: tuple[ServingAccessPolicyReconciliationItem, ...],
    status: str,
) -> int:
    return len(ids_for_status(items, status))


def count_by(
    items: tuple[ServingAccessPolicyReconciliationItem, ...],
    attribute: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "model-serving-access-policy-reconciliation-v1.yaml"
    )
