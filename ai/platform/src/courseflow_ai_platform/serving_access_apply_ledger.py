from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.model_serving_auth import normalize_string_tuple
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml
from courseflow_ai_platform.serving_access_policy_plan import (
    ServingAccessPolicyPatchPlan,
    build_serving_access_policy_patch_plan,
    load_active_policy,
)

APPLY_REVIEWER_ROLES = ("Admin/Ops", "Governance Reviewer")


@dataclass(frozen=True, slots=True)
class ServingAccessApplyReviewer:
    role: str
    reviewer_id: str
    decision: str
    reviewed_at: str

    @classmethod
    def from_dict(cls, row: dict[str, Any], *, application_id: str) -> ServingAccessApplyReviewer:
        owner = f"serving access apply entry {application_id} reviewer"
        return cls(
            role=require_str(row, "role", owner),
            reviewer_id=require_str(row, "reviewer_id", owner),
            decision=require_str(row, "decision", owner).lower().replace(" ", "_"),
            reviewed_at=require_str(row, "reviewed_at", owner),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "decision": self.decision,
            "reviewedAt": self.reviewed_at,
            "reviewerId": self.reviewer_id,
            "role": self.role,
        }

    def to_snapshot_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "reviewer_id": self.reviewer_id,
            "decision": self.decision,
            "reviewed_at": self.reviewed_at,
        }


@dataclass(frozen=True, slots=True)
class ServingAccessApplyEntry:
    application_id: str
    status: str
    plan_id: str
    source_policy_id: str
    source_policy_sha256: str
    proposed_policy_sha256: str
    request_ids: tuple[str, ...]
    reviewers: tuple[ServingAccessApplyReviewer, ...]
    decision_summary: str
    applied_policy_sha256: str
    applied_at: str

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> ServingAccessApplyEntry:
        application_id = require_str(row, "application_id", "serving access apply entry")
        reviewers = tuple(
            ServingAccessApplyReviewer.from_dict(reviewer, application_id=application_id)
            for reviewer in require_optional_mapping_list(row, "reviewers", application_id)
        )
        return cls(
            application_id=application_id,
            status=require_str(row, "status", f"serving access apply entry {application_id}")
            .lower()
            .replace(" ", "_"),
            plan_id=require_str(row, "plan_id", f"serving access apply entry {application_id}"),
            source_policy_id=require_str(
                row,
                "source_policy_id",
                f"serving access apply entry {application_id}",
            ),
            source_policy_sha256=require_str(
                row,
                "source_policy_sha256",
                f"serving access apply entry {application_id}",
            ),
            proposed_policy_sha256=require_str(
                row,
                "proposed_policy_sha256",
                f"serving access apply entry {application_id}",
            ),
            request_ids=tuple(sorted(normalize_string_tuple(row.get("request_ids", [])))),
            reviewers=reviewers,
            decision_summary=require_str(
                row,
                "decision_summary",
                f"serving access apply entry {application_id}",
            ),
            applied_policy_sha256=optional_str(row, "applied_policy_sha256"),
            applied_at=optional_str(row, "applied_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "applicationId": self.application_id,
            "appliedAt": self.applied_at,
            "appliedPolicySha256": self.applied_policy_sha256,
            "decisionSummary": self.decision_summary,
            "planId": self.plan_id,
            "proposedPolicySha256": self.proposed_policy_sha256,
            "requestIds": list(self.request_ids),
            "reviewers": [reviewer.to_dict() for reviewer in self.reviewers],
            "sourcePolicyId": self.source_policy_id,
            "sourcePolicySha256": self.source_policy_sha256,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ServingAccessApplyLedgerItem:
    application_id: str
    status: str
    plan_id: str
    request_ids: tuple[str, ...]
    required_reviewer_roles: tuple[str, ...]
    missing_reviewer_roles: tuple[str, ...]
    source_policy_sha256: str
    expected_source_policy_sha256: str
    proposed_policy_sha256: str
    expected_proposed_policy_sha256: str
    checksum_status: str
    validation_errors: tuple[str, ...]
    action: str
    reviewers: tuple[ServingAccessApplyReviewer, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "applicationId": self.application_id,
            "checksumStatus": self.checksum_status,
            "expectedProposedPolicySha256": self.expected_proposed_policy_sha256,
            "expectedSourcePolicySha256": self.expected_source_policy_sha256,
            "missingReviewerRoles": list(self.missing_reviewer_roles),
            "planId": self.plan_id,
            "proposedPolicySha256": self.proposed_policy_sha256,
            "requestIds": list(self.request_ids),
            "requiredReviewerRoles": list(self.required_reviewer_roles),
            "reviewers": [reviewer.to_dict() for reviewer in self.reviewers],
            "sourcePolicySha256": self.source_policy_sha256,
            "status": self.status,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "status": self.status,
            "plan_id": self.plan_id,
            "request_ids": list(self.request_ids),
            "required_reviewer_roles": list(self.required_reviewer_roles),
            "missing_reviewer_roles": list(self.missing_reviewer_roles),
            "source_policy_sha256": self.source_policy_sha256,
            "expected_source_policy_sha256": self.expected_source_policy_sha256,
            "proposed_policy_sha256": self.proposed_policy_sha256,
            "expected_proposed_policy_sha256": self.expected_proposed_policy_sha256,
            "checksum_status": self.checksum_status,
            "validation_errors": list(self.validation_errors),
            "action": self.action,
            "reviewers": [reviewer.to_snapshot_dict() for reviewer in self.reviewers],
        }


@dataclass(frozen=True, slots=True)
class ServingAccessApplyLedgerReport:
    application_count: int
    ready_to_apply_count: int
    pending_review_count: int
    applied_count: int
    rejected_count: int
    blocked_count: int
    checksum_mismatch_count: int
    source_policy_sha256: str
    proposed_policy_sha256: str
    by_status: dict[str, int]
    by_action: dict[str, int]
    action_queue: dict[str, list[str]]
    items: tuple[ServingAccessApplyLedgerItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": self.action_queue,
            "appliedCount": self.applied_count,
            "applicationCount": self.application_count,
            "blockedCount": self.blocked_count,
            "byAction": self.by_action,
            "byStatus": self.by_status,
            "checksumMismatchCount": self.checksum_mismatch_count,
            "items": [item.to_dict() for item in self.items],
            "pendingReviewCount": self.pending_review_count,
            "proposedPolicySha256": self.proposed_policy_sha256,
            "readyToApplyCount": self.ready_to_apply_count,
            "rejectedCount": self.rejected_count,
            "sourcePolicySha256": self.source_policy_sha256,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "model-serving-access-policy-apply-ledger-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "application_count": self.application_count,
                "ready_to_apply_count": self.ready_to_apply_count,
                "pending_review_count": self.pending_review_count,
                "applied_count": self.applied_count,
                "rejected_count": self.rejected_count,
                "blocked_count": self.blocked_count,
                "checksum_mismatch_count": self.checksum_mismatch_count,
                "source_policy_sha256": self.source_policy_sha256,
                "proposed_policy_sha256": self.proposed_policy_sha256,
            },
            "by_status": self.by_status,
            "by_action": self.by_action,
            "action_queue": self.action_queue,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_serving_access_apply_ledger_report(
    ai_root: Path | str,
) -> ServingAccessApplyLedgerReport:
    root = Path(ai_root)
    plan = build_serving_access_policy_patch_plan(root)
    expected_source_hash = stable_sha256(load_active_policy(root))
    expected_proposed_hash = stable_sha256(plan.proposed_policy)
    entries = load_serving_access_apply_entries(root)
    items = tuple(
        build_apply_item(
            entry,
            plan=plan,
            expected_source_policy_sha256=expected_source_hash,
            expected_proposed_policy_sha256=expected_proposed_hash,
        )
        for entry in entries
    )
    return build_report_from_items(
        items,
        source_policy_sha256=expected_source_hash,
        proposed_policy_sha256=expected_proposed_hash,
    )


def build_serving_access_apply_ledger_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_serving_access_apply_ledger_report(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_serving_access_apply_ledger_snapshot(
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
            build_serving_access_apply_ledger_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def load_serving_access_apply_entries(ai_root: Path | str) -> tuple[ServingAccessApplyEntry, ...]:
    root = Path(ai_root)
    path = (
        root
        / "platform"
        / "governance"
        / "ledgers"
        / "model-serving-access-policy-apply-ledger.yaml"
    )
    ledger = load_yaml(path)
    entries = require_list(ledger, "applications", path)
    seen_ids: set[str] = set()
    result: list[ServingAccessApplyEntry] = []
    for row in entries:
        entry = ServingAccessApplyEntry.from_dict(row)
        if entry.application_id in seen_ids:
            raise RegistryValidationError(
                f"{path} duplicates application_id: {entry.application_id}"
            )
        seen_ids.add(entry.application_id)
        result.append(entry)
    return tuple(result)


def build_apply_item(
    entry: ServingAccessApplyEntry,
    *,
    plan: ServingAccessPolicyPatchPlan,
    expected_source_policy_sha256: str,
    expected_proposed_policy_sha256: str,
) -> ServingAccessApplyLedgerItem:
    validation_errors = validate_apply_entry(
        entry,
        plan=plan,
        expected_source_policy_sha256=expected_source_policy_sha256,
        expected_proposed_policy_sha256=expected_proposed_policy_sha256,
    )
    missing_roles = missing_apply_reviewer_roles(entry)
    checksum_status = (
        "matched"
        if entry.source_policy_sha256 == expected_source_policy_sha256
        and entry.proposed_policy_sha256 == expected_proposed_policy_sha256
        else "mismatched"
    )
    action = action_for_apply_entry(
        entry,
        validation_errors=validation_errors,
        missing_roles=missing_roles,
    )
    return ServingAccessApplyLedgerItem(
        application_id=entry.application_id,
        status=entry.status,
        plan_id=entry.plan_id,
        request_ids=entry.request_ids,
        required_reviewer_roles=APPLY_REVIEWER_ROLES,
        missing_reviewer_roles=missing_roles,
        source_policy_sha256=entry.source_policy_sha256,
        expected_source_policy_sha256=expected_source_policy_sha256,
        proposed_policy_sha256=entry.proposed_policy_sha256,
        expected_proposed_policy_sha256=expected_proposed_policy_sha256,
        checksum_status=checksum_status,
        validation_errors=tuple(sorted(validation_errors)),
        action=action,
        reviewers=entry.reviewers,
    )


def validate_apply_entry(
    entry: ServingAccessApplyEntry,
    *,
    plan: ServingAccessPolicyPatchPlan,
    expected_source_policy_sha256: str,
    expected_proposed_policy_sha256: str,
) -> list[str]:
    errors: list[str] = []
    if entry.status not in {"pending_review", "approved", "applied", "rejected"}:
        errors.append(f"unsupported apply status: {entry.status}")
    if entry.plan_id != plan.plan_id:
        errors.append(f"plan_id mismatch: {entry.plan_id} != {plan.plan_id}")
    if entry.source_policy_id != plan.source_policy_id:
        errors.append(
            f"source_policy_id mismatch: {entry.source_policy_id} != {plan.source_policy_id}"
        )
    if entry.source_policy_sha256 != expected_source_policy_sha256:
        errors.append("source_policy_sha256 does not match current source policy")
    if entry.proposed_policy_sha256 != expected_proposed_policy_sha256:
        errors.append("proposed_policy_sha256 does not match current patch plan")
    plan_request_ids = tuple(sorted(operation.request_id for operation in plan.operations))
    if entry.request_ids != plan_request_ids:
        errors.append("request_ids must match the current patch plan operations")
    if entry.status == "applied":
        if not entry.applied_policy_sha256:
            errors.append("applied entries must define applied_policy_sha256")
        elif entry.applied_policy_sha256 != entry.proposed_policy_sha256:
            errors.append("applied_policy_sha256 must match proposed_policy_sha256")
        if not entry.applied_at:
            errors.append("applied entries must define applied_at")
    return errors


def missing_apply_reviewer_roles(
    entry: ServingAccessApplyEntry,
) -> tuple[str, ...]:
    approved_roles = {
        reviewer.role for reviewer in entry.reviewers if reviewer.decision == "approved"
    }
    return tuple(sorted(role for role in APPLY_REVIEWER_ROLES if role not in approved_roles))


def action_for_apply_entry(
    entry: ServingAccessApplyEntry,
    *,
    validation_errors: list[str],
    missing_roles: tuple[str, ...],
) -> str:
    if validation_errors:
        return "block_policy_apply_until_ledger_fixed"
    if entry.status == "rejected":
        return "close_without_policy_apply"
    if missing_roles:
        return "collect_apply_reviewer_approvals"
    if entry.status == "applied":
        return "monitor_applied_policy_checksum"
    return "apply_proposed_policy_to_access_policy"


def build_report_from_items(
    items: tuple[ServingAccessApplyLedgerItem, ...],
    *,
    source_policy_sha256: str,
    proposed_policy_sha256: str,
) -> ServingAccessApplyLedgerReport:
    return ServingAccessApplyLedgerReport(
        application_count=len(items),
        ready_to_apply_count=count_action(items, "apply_proposed_policy_to_access_policy"),
        pending_review_count=count_action(items, "collect_apply_reviewer_approvals"),
        applied_count=count_status(items, "applied"),
        rejected_count=count_status(items, "rejected"),
        blocked_count=count_action(items, "block_policy_apply_until_ledger_fixed"),
        checksum_mismatch_count=sum(1 for item in items if item.checksum_status != "matched"),
        source_policy_sha256=source_policy_sha256,
        proposed_policy_sha256=proposed_policy_sha256,
        by_status=count_by(items, "status"),
        by_action=count_by(items, "action"),
        action_queue={
            "blocked": ids_for_action(items, "block_policy_apply_until_ledger_fixed"),
            "pending_review": ids_for_action(items, "collect_apply_reviewer_approvals"),
            "ready_to_apply": ids_for_action(items, "apply_proposed_policy_to_access_policy"),
            "applied": ids_for_action(items, "monitor_applied_policy_checksum"),
            "rejected": ids_for_action(items, "close_without_policy_apply"),
        },
        items=items,
    )


def stable_sha256(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def ids_for_action(items: tuple[ServingAccessApplyLedgerItem, ...], action: str) -> list[str]:
    return [item.application_id for item in items if item.action == action]


def count_action(items: tuple[ServingAccessApplyLedgerItem, ...], action: str) -> int:
    return len(ids_for_action(items, action))


def count_status(items: tuple[ServingAccessApplyLedgerItem, ...], status: str) -> int:
    return sum(1 for item in items if item.status == status)


def count_by(items: tuple[ServingAccessApplyLedgerItem, ...], attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def require_list(row: dict[str, Any], key: str, path: Path) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{path} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{path} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def require_optional_mapping_list(
    row: dict[str, Any],
    key: str,
    application_id: str,
) -> list[dict[str, Any]]:
    value = row.get(key, [])
    if not isinstance(value, list):
        raise RegistryValidationError(
            f"serving access apply entry {application_id} {key} must be a list"
        )
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(
                f"serving access apply entry {application_id} {key}[{index}] "
                "must be a mapping"
            )
        result.append(item)
    return result


def require_str(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryValidationError(f"{owner} must define non-empty string field {key}")
    return value.strip()


def optional_str(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise RegistryValidationError(f"optional field {key} must be a string when set")
    return value.strip()


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "model-serving-access-policy-apply-ledger-v1.yaml"
    )
