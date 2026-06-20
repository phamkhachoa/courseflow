from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml
from courseflow_ai_platform.serving_access_review import (
    ServingAccessChangeRequest,
    ServingAccessReviewItem,
    build_serving_access_review_report,
    load_serving_access_change_requests,
)


@dataclass(frozen=True, slots=True)
class ServingAccessPolicyPatchOperation:
    request_id: str
    target_principal_id: str
    change_type: str
    action: str
    added_scopes: tuple[str, ...]
    added_tenant_ids: tuple[str, ...]
    added_model_ids: tuple[str, ...]
    removed_principal: bool
    before_grant: dict[str, Any] | None
    after_grant: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "addedModelIds": list(self.added_model_ids),
            "addedScopes": list(self.added_scopes),
            "addedTenantIds": list(self.added_tenant_ids),
            "afterGrant": self.after_grant,
            "beforeGrant": self.before_grant,
            "changeType": self.change_type,
            "removedPrincipal": self.removed_principal,
            "requestId": self.request_id,
            "targetPrincipalId": self.target_principal_id,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "target_principal_id": self.target_principal_id,
            "change_type": self.change_type,
            "action": self.action,
            "added_scopes": list(self.added_scopes),
            "added_tenant_ids": list(self.added_tenant_ids),
            "added_model_ids": list(self.added_model_ids),
            "removed_principal": self.removed_principal,
            "before_grant": self.before_grant,
            "after_grant": self.after_grant,
        }


@dataclass(frozen=True, slots=True)
class ServingAccessPolicyPatchPlan:
    plan_id: str
    source_policy_id: str
    ready_request_count: int
    planned_operation_count: int
    skipped_request_count: int
    proposed_principal_count: int
    human_review_required: bool
    operations: tuple[ServingAccessPolicyPatchOperation, ...]
    skipped_request_ids: tuple[str, ...]
    proposed_policy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "humanReviewRequired": self.human_review_required,
            "operations": [operation.to_dict() for operation in self.operations],
            "planId": self.plan_id,
            "plannedOperationCount": self.planned_operation_count,
            "proposedPolicy": self.proposed_policy,
            "proposedPrincipalCount": self.proposed_principal_count,
            "readyRequestCount": self.ready_request_count,
            "skippedRequestCount": self.skipped_request_count,
            "skippedRequestIds": list(self.skipped_request_ids),
            "sourcePolicyId": self.source_policy_id,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "model-serving-access-policy-patch-plan-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "plan_id": self.plan_id,
                "source_policy_id": self.source_policy_id,
                "ready_request_count": self.ready_request_count,
                "planned_operation_count": self.planned_operation_count,
                "skipped_request_count": self.skipped_request_count,
                "proposed_principal_count": self.proposed_principal_count,
                "human_review_required": self.human_review_required,
            },
            "skipped_request_ids": list(self.skipped_request_ids),
            "operations": [operation.to_snapshot_dict() for operation in self.operations],
            "proposed_policy": self.proposed_policy,
        }


def build_serving_access_policy_patch_plan(ai_root: Path | str) -> ServingAccessPolicyPatchPlan:
    root = Path(ai_root)
    policy = load_active_policy(root)
    requests_by_id = {
        request.request_id: request for request in load_serving_access_change_requests(root)
    }
    review = build_serving_access_review_report(root)
    ready_items = tuple(item for item in review.items if item.review_status == "ready_for_apply")
    skipped_request_ids = tuple(
        item.request_id for item in review.items if item.review_status != "ready_for_apply"
    )
    proposed_policy = deepcopy(policy)
    operations = tuple(
        apply_ready_request_to_policy(
            proposed_policy,
            requests_by_id[item.request_id],
            item,
        )
        for item in ready_items
    )
    sort_policy_principal_grants(proposed_policy)
    return ServingAccessPolicyPatchPlan(
        plan_id="model-serving-access-policy-patch-plan-v1",
        source_policy_id=required_policy_str(policy, "policy_id"),
        ready_request_count=len(ready_items),
        planned_operation_count=len(operations),
        skipped_request_count=len(skipped_request_ids),
        proposed_principal_count=len(require_principals(proposed_policy)),
        human_review_required=bool(operations),
        operations=operations,
        skipped_request_ids=skipped_request_ids,
        proposed_policy=proposed_policy,
    )


def build_serving_access_policy_patch_plan_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_serving_access_policy_patch_plan(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_serving_access_policy_patch_plan_snapshot(
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
            build_serving_access_policy_patch_plan_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def apply_ready_request_to_policy(
    policy: dict[str, Any],
    request: ServingAccessChangeRequest,
    review_item: ServingAccessReviewItem,
) -> ServingAccessPolicyPatchOperation:
    principals = require_principals(policy)
    policy_grant = find_principal_grant(principals, request.target_principal_id)
    before_grant = deepcopy(policy_grant)
    if request.change_type == "remove_principal":
        remove_principal_grant(principals, request.target_principal_id)
        return ServingAccessPolicyPatchOperation(
            request_id=request.request_id,
            target_principal_id=request.target_principal_id,
            change_type=request.change_type,
            action="remove_principal_grant",
            added_scopes=(),
            added_tenant_ids=(),
            added_model_ids=(),
            removed_principal=before_grant is not None,
            before_grant=before_grant,
            after_grant=None,
        )

    if policy_grant is None:
        after_grant = build_new_principal_grant(request)
        principals.append(after_grant)
        return ServingAccessPolicyPatchOperation(
            request_id=request.request_id,
            target_principal_id=request.target_principal_id,
            change_type=request.change_type,
            action="add_principal_grant",
            added_scopes=tuple(after_grant["scopes"]),
            added_tenant_ids=tuple(after_grant["tenant_ids"]),
            added_model_ids=tuple(after_grant["model_ids"]),
            removed_principal=False,
            before_grant=None,
            after_grant=deepcopy(after_grant),
        )

    added_scopes = merge_list_field(policy_grant, "scopes", request.requested_scopes)
    added_tenant_ids = merge_list_field(
        policy_grant,
        "tenant_ids",
        request.requested_tenant_ids,
    )
    added_model_ids = merge_list_field(
        policy_grant,
        "model_ids",
        request.requested_model_ids,
    )
    policy_grant["owner_role"] = request.owner_role
    policy_grant["product"] = request.product
    after_grant = deepcopy(policy_grant)
    return ServingAccessPolicyPatchOperation(
        request_id=request.request_id,
        target_principal_id=request.target_principal_id,
        change_type=request.change_type,
        action=action_for_change_type(request.change_type, review_item),
        added_scopes=added_scopes,
        added_tenant_ids=added_tenant_ids,
        added_model_ids=added_model_ids,
        removed_principal=False,
        before_grant=before_grant,
        after_grant=after_grant,
    )


def build_new_principal_grant(request: ServingAccessChangeRequest) -> dict[str, Any]:
    return {
        "principal_id": request.target_principal_id,
        "owner_role": request.owner_role,
        "product": request.product,
        "scopes": list(request.requested_scopes),
        "tenant_ids": list(request.requested_tenant_ids),
        "model_ids": list(request.requested_model_ids),
    }


def merge_list_field(
    row: dict[str, Any],
    field: str,
    requested_values: tuple[str, ...],
) -> tuple[str, ...]:
    current = normalize_list_field(row, field)
    additions = tuple(value for value in requested_values if value not in current)
    row[field] = sorted(set(current) | set(requested_values))
    return tuple(sorted(additions))


def action_for_change_type(
    change_type: str,
    review_item: ServingAccessReviewItem,
) -> str:
    if change_type == "expand_tenant":
        return "merge_tenant_allowlist"
    if change_type == "expand_scope":
        return "merge_scope_allowlist"
    if change_type == "expand_model":
        return "merge_model_allowlist"
    return review_item.action


def load_active_policy(root: Path) -> dict[str, Any]:
    return load_yaml(
        root / "platform" / "governance" / "policies" / "model-serving-access-policy.yaml"
    )


def require_principals(policy: dict[str, Any]) -> list[dict[str, Any]]:
    principals = policy.get("principals")
    if not isinstance(principals, list):
        raise RegistryValidationError("model-serving access policy must define principals list")
    for index, item in enumerate(principals):
        if not isinstance(item, dict):
            raise RegistryValidationError(
                f"model-serving access policy principals[{index}] must be a mapping"
            )
    return principals


def find_principal_grant(
    principals: list[dict[str, Any]],
    principal_id: str,
) -> dict[str, Any] | None:
    for principal in principals:
        if principal.get("principal_id") == principal_id:
            return principal
    return None


def remove_principal_grant(principals: list[dict[str, Any]], principal_id: str) -> None:
    principals[:] = [
        principal for principal in principals if principal.get("principal_id") != principal_id
    ]


def normalize_list_field(row: dict[str, Any], field: str) -> list[str]:
    value = row.get(field, [])
    if not isinstance(value, list):
        raise RegistryValidationError(f"principal grant field {field} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"principal grant field {field} must contain strings")
        result.append(item.strip())
    return result


def sort_policy_principal_grants(policy: dict[str, Any]) -> None:
    principals = require_principals(policy)
    for principal in principals:
        principal["scopes"] = sorted(normalize_list_field(principal, "scopes"))
        principal["tenant_ids"] = sorted(normalize_list_field(principal, "tenant_ids"))
        principal["model_ids"] = sorted(normalize_list_field(principal, "model_ids"))
    principals.sort(key=lambda row: str(row.get("principal_id", "")))


def required_policy_str(policy: dict[str, Any], key: str) -> str:
    value = policy.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryValidationError(f"model-serving access policy must define {key}")
    return value.strip()


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "model-serving-access-policy-patch-plan-v1.yaml"
    )
