from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.registry import RegistryValidationError
from courseflow_ai_platform.serving_access_apply_ledger import (
    ServingAccessApplyLedgerItem,
    build_serving_access_apply_ledger_report,
)
from courseflow_ai_platform.serving_access_policy_plan import (
    build_serving_access_policy_patch_plan,
    load_active_policy,
)

READY_APPLY_ACTION = "apply_proposed_policy_to_access_policy"


@dataclass(frozen=True, slots=True)
class ServingAccessPolicyApplyReport:
    apply_status: str
    ready_application_count: int
    blocked_count: int
    checksum_mismatch_count: int
    source_policy_path: str
    target_policy_path: str
    source_policy_sha256: str
    proposed_policy_sha256: str
    active_policy_would_change: bool
    planned_operation_count: int
    ready_application_ids: tuple[str, ...]
    validation_errors: tuple[str, ...]
    proposed_policy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activePolicyWouldChange": self.active_policy_would_change,
            "applyStatus": self.apply_status,
            "blockedCount": self.blocked_count,
            "checksumMismatchCount": self.checksum_mismatch_count,
            "plannedOperationCount": self.planned_operation_count,
            "proposedPolicy": self.proposed_policy,
            "proposedPolicySha256": self.proposed_policy_sha256,
            "readyApplicationCount": self.ready_application_count,
            "readyApplicationIds": list(self.ready_application_ids),
            "sourcePolicyPath": self.source_policy_path,
            "sourcePolicySha256": self.source_policy_sha256,
            "targetPolicyPath": self.target_policy_path,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "model-serving-access-policy-apply-report-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "apply_status": self.apply_status,
                "ready_application_count": self.ready_application_count,
                "blocked_count": self.blocked_count,
                "checksum_mismatch_count": self.checksum_mismatch_count,
                "source_policy_path": self.source_policy_path,
                "target_policy_path": self.target_policy_path,
                "source_policy_sha256": self.source_policy_sha256,
                "proposed_policy_sha256": self.proposed_policy_sha256,
                "active_policy_would_change": self.active_policy_would_change,
                "planned_operation_count": self.planned_operation_count,
            },
            "ready_application_ids": list(self.ready_application_ids),
            "validation_errors": list(self.validation_errors),
            "proposed_policy": self.proposed_policy,
        }


@dataclass(frozen=True, slots=True)
class ServingAccessPolicyApplyWriteResult:
    output_policy_path: str
    applied_policy_sha256: str
    source_policy_sha256: str
    ready_application_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "appliedPolicySha256": self.applied_policy_sha256,
            "outputPolicyPath": self.output_policy_path,
            "readyApplicationIds": list(self.ready_application_ids),
            "sourcePolicySha256": self.source_policy_sha256,
        }


def build_serving_access_policy_apply_report(
    ai_root: Path | str,
    *,
    target_policy_path: Path | str | None = None,
) -> ServingAccessPolicyApplyReport:
    root = Path(ai_root)
    source_policy_path = active_policy_path(root)
    target_path = Path(target_policy_path) if target_policy_path is not None else source_policy_path
    patch_plan = build_serving_access_policy_patch_plan(root)
    apply_ledger = build_serving_access_apply_ledger_report(root)
    ready_items = tuple(
        item for item in apply_ledger.items if item.action == READY_APPLY_ACTION
    )
    validation_errors = validate_apply_readiness(
        ready_items=ready_items,
        blocked_count=apply_ledger.blocked_count,
        checksum_mismatch_count=apply_ledger.checksum_mismatch_count,
        planned_operation_count=patch_plan.planned_operation_count,
    )
    source_policy = load_active_policy(root)
    apply_status = "ready_to_write" if not validation_errors else "blocked"
    return ServingAccessPolicyApplyReport(
        apply_status=apply_status,
        ready_application_count=len(ready_items),
        blocked_count=apply_ledger.blocked_count,
        checksum_mismatch_count=apply_ledger.checksum_mismatch_count,
        source_policy_path=str(source_policy_path),
        target_policy_path=str(target_path),
        source_policy_sha256=apply_ledger.source_policy_sha256,
        proposed_policy_sha256=apply_ledger.proposed_policy_sha256,
        active_policy_would_change=source_policy != patch_plan.proposed_policy,
        planned_operation_count=patch_plan.planned_operation_count,
        ready_application_ids=tuple(item.application_id for item in ready_items),
        validation_errors=tuple(sorted(validation_errors)),
        proposed_policy=patch_plan.proposed_policy,
    )


def write_serving_access_policy_apply_report(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
    target_policy_path: Path | str | None = None,
) -> Path:
    root = Path(ai_root)
    report_date = generated_at or date.today().isoformat()
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_serving_access_policy_apply_report(
                root,
                target_policy_path=target_policy_path,
            ).to_snapshot_dict(generated_at=report_date),
            handle,
            sort_keys=False,
        )
    return target


def write_serving_access_policy_from_ledger(
    ai_root: Path | str,
    *,
    output_policy_path: Path | str,
) -> ServingAccessPolicyApplyWriteResult:
    root = Path(ai_root)
    output_path = Path(output_policy_path)
    report = build_serving_access_policy_apply_report(
        root,
        target_policy_path=output_path,
    )
    if report.validation_errors:
        raise RegistryValidationError(
            "serving access policy is not ready to apply: "
            + "; ".join(report.validation_errors)
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(report.proposed_policy, handle, sort_keys=False)
    return ServingAccessPolicyApplyWriteResult(
        output_policy_path=str(output_path),
        applied_policy_sha256=report.proposed_policy_sha256,
        source_policy_sha256=report.source_policy_sha256,
        ready_application_ids=report.ready_application_ids,
    )


def validate_apply_readiness(
    *,
    ready_items: tuple[ServingAccessApplyLedgerItem, ...],
    blocked_count: int,
    checksum_mismatch_count: int,
    planned_operation_count: int,
) -> list[str]:
    errors: list[str] = []
    if planned_operation_count == 0:
        errors.append("no patch plan operations are ready")
    if not ready_items:
        errors.append("no apply ledger entries are ready to apply")
    if blocked_count:
        errors.append("apply ledger has blocked entries")
    if checksum_mismatch_count:
        errors.append("apply ledger has checksum mismatches")
    for item in ready_items:
        if item.validation_errors:
            errors.append(
                f"apply ledger entry {item.application_id} has validation errors"
            )
        if item.missing_reviewer_roles:
            errors.append(
                f"apply ledger entry {item.application_id} is missing reviewer roles"
            )
    return errors


def active_policy_path(root: Path) -> Path:
    return root / "platform" / "governance" / "policies" / "model-serving-access-policy.yaml"


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "model-serving-access-policy-apply-report-v1.yaml"
    )
