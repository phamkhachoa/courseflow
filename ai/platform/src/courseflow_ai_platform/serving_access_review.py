from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.model_serving_auth import (
    MODEL_SERVING_INVOKE_SCOPE,
    MODEL_SERVING_OPS_SCOPE,
    ServingAccessPolicy,
    expand_scope_alias,
    load_model_product_index,
    load_serving_access_policy,
    normalize_string_tuple,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml

REQUIRED_BASE_APPROVERS = ("PO/BA", "SA AI Platform", "SA AI Engineer")
TENANT_GOVERNANCE_APPROVER = "Governance Reviewer"
OPS_APPROVER = "Admin/Ops"


@dataclass(frozen=True, slots=True)
class ServingAccessApproval:
    role: str
    decision: str

    @classmethod
    def from_dict(cls, row: dict[str, Any], *, request_id: str) -> ServingAccessApproval:
        return cls(
            role=require_str(row, "role", f"serving access request {request_id} approval"),
            decision=require_str(row, "decision", f"serving access request {request_id} approval")
            .lower()
            .replace(" ", "_"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "decision": self.decision,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class ServingAccessChangeRequest:
    request_id: str
    status: str
    change_type: str
    target_principal_id: str
    product: str
    owner_role: str
    requested_by: str
    business_justification: str
    requested_scopes: tuple[str, ...]
    requested_tenant_ids: tuple[str, ...]
    requested_model_ids: tuple[str, ...]
    approvals: tuple[ServingAccessApproval, ...]
    evidence_refs: tuple[str, ...]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> ServingAccessChangeRequest:
        request_id = require_str(row, "request_id", "serving access request")
        approvals = tuple(
            ServingAccessApproval.from_dict(approval, request_id=request_id)
            for approval in require_optional_mapping_list(row, "approvals", request_id)
        )
        return cls(
            request_id=request_id,
            status=require_str(row, "status", f"serving access request {request_id}")
            .lower()
            .replace(" ", "_"),
            change_type=require_str(row, "change_type", f"serving access request {request_id}")
            .lower()
            .replace(" ", "_"),
            target_principal_id=require_str(
                row,
                "target_principal_id",
                f"serving access request {request_id}",
            ),
            product=require_str(row, "product", f"serving access request {request_id}"),
            owner_role=require_str(row, "owner_role", f"serving access request {request_id}"),
            requested_by=require_str(row, "requested_by", f"serving access request {request_id}"),
            business_justification=require_str(
                row,
                "business_justification",
                f"serving access request {request_id}",
            ),
            requested_scopes=tuple(sorted(normalize_string_tuple(row.get("requested_scopes", [])))),
            requested_tenant_ids=tuple(
                sorted(normalize_string_tuple(row.get("requested_tenant_ids", [])))
            ),
            requested_model_ids=tuple(
                sorted(normalize_string_tuple(row.get("requested_model_ids", [])))
            ),
            approvals=approvals,
            evidence_refs=tuple(sorted(normalize_string_tuple(row.get("evidence_refs", [])))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvals": [approval.to_dict() for approval in self.approvals],
            "businessJustification": self.business_justification,
            "changeType": self.change_type,
            "evidenceRefs": list(self.evidence_refs),
            "ownerRole": self.owner_role,
            "product": self.product,
            "requestId": self.request_id,
            "requestedBy": self.requested_by,
            "requestedModelIds": list(self.requested_model_ids),
            "requestedScopes": list(self.requested_scopes),
            "requestedTenantIds": list(self.requested_tenant_ids),
            "status": self.status,
            "targetPrincipalId": self.target_principal_id,
        }


@dataclass(frozen=True, slots=True)
class ServingAccessReviewItem:
    request_id: str
    target_principal_id: str
    change_type: str
    product: str
    requested_scopes: tuple[str, ...]
    requested_tenant_ids: tuple[str, ...]
    requested_model_ids: tuple[str, ...]
    risk_level: str
    review_status: str
    current_policy_covered: bool
    required_approval_roles: tuple[str, ...]
    missing_approval_roles: tuple[str, ...]
    validation_errors: tuple[str, ...]
    action: str
    refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "changeType": self.change_type,
            "currentPolicyCovered": self.current_policy_covered,
            "missingApprovalRoles": list(self.missing_approval_roles),
            "product": self.product,
            "refs": list(self.refs),
            "requestId": self.request_id,
            "requestedModelIds": list(self.requested_model_ids),
            "requestedScopes": list(self.requested_scopes),
            "requestedTenantIds": list(self.requested_tenant_ids),
            "requiredApprovalRoles": list(self.required_approval_roles),
            "reviewStatus": self.review_status,
            "riskLevel": self.risk_level,
            "targetPrincipalId": self.target_principal_id,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "target_principal_id": self.target_principal_id,
            "change_type": self.change_type,
            "product": self.product,
            "requested_scopes": list(self.requested_scopes),
            "requested_tenant_ids": list(self.requested_tenant_ids),
            "requested_model_ids": list(self.requested_model_ids),
            "risk_level": self.risk_level,
            "review_status": self.review_status,
            "current_policy_covered": self.current_policy_covered,
            "required_approval_roles": list(self.required_approval_roles),
            "missing_approval_roles": list(self.missing_approval_roles),
            "validation_errors": list(self.validation_errors),
            "action": self.action,
            "refs": list(self.refs),
        }


@dataclass(frozen=True, slots=True)
class ServingAccessReviewReport:
    request_count: int
    applied_count: int
    ready_for_apply_count: int
    needs_approval_count: int
    blocked_count: int
    rejected_count: int
    critical_risk_count: int
    high_risk_count: int
    by_status: dict[str, int]
    by_risk_level: dict[str, int]
    action_queue: dict[str, list[str]]
    items: tuple[ServingAccessReviewItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": self.action_queue,
            "appliedCount": self.applied_count,
            "blockedCount": self.blocked_count,
            "byRiskLevel": self.by_risk_level,
            "byStatus": self.by_status,
            "criticalRiskCount": self.critical_risk_count,
            "highRiskCount": self.high_risk_count,
            "items": [item.to_dict() for item in self.items],
            "needsApprovalCount": self.needs_approval_count,
            "readyForApplyCount": self.ready_for_apply_count,
            "rejectedCount": self.rejected_count,
            "requestCount": self.request_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "model-serving-access-review-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "request_count": self.request_count,
                "applied_count": self.applied_count,
                "ready_for_apply_count": self.ready_for_apply_count,
                "needs_approval_count": self.needs_approval_count,
                "blocked_count": self.blocked_count,
                "rejected_count": self.rejected_count,
                "critical_risk_count": self.critical_risk_count,
                "high_risk_count": self.high_risk_count,
            },
            "by_status": self.by_status,
            "by_risk_level": self.by_risk_level,
            "action_queue": self.action_queue,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def load_serving_access_change_requests(
    ai_root: Path | str,
) -> tuple[ServingAccessChangeRequest, ...]:
    root = Path(ai_root)
    path = root / "platform" / "governance" / "requests" / "model-serving-access-requests.yaml"
    registry = load_yaml(path)
    requests = require_list(registry, "requests", path)
    seen_ids: set[str] = set()
    result: list[ServingAccessChangeRequest] = []
    for row in requests:
        request = ServingAccessChangeRequest.from_dict(row)
        if request.request_id in seen_ids:
            raise RegistryValidationError(f"{path} duplicates request_id: {request.request_id}")
        seen_ids.add(request.request_id)
        result.append(request)
    return tuple(result)


def build_serving_access_review_report(ai_root: Path | str) -> ServingAccessReviewReport:
    root = Path(ai_root)
    access_policy = load_serving_access_policy(root)
    requests = load_serving_access_change_requests(root)
    model_products = load_model_product_index(root)
    scope_aliases = load_scope_aliases(root)
    items = tuple(
        build_review_item(
            request,
            access_policy=access_policy,
            model_products=model_products,
            scope_aliases=scope_aliases,
        )
        for request in requests
    )
    return build_report_from_items(items)


def build_serving_access_review_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_serving_access_review_report(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_serving_access_review_snapshot(
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
            build_serving_access_review_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_review_item(
    request: ServingAccessChangeRequest,
    *,
    access_policy: ServingAccessPolicy,
    model_products: dict[str, str],
    scope_aliases: dict[str, str],
) -> ServingAccessReviewItem:
    validation_errors = validate_change_request(
        request,
        access_policy=access_policy,
        model_products=model_products,
        scope_aliases=scope_aliases,
    )
    expanded_scopes = expand_scopes_for_report(request, scope_aliases)
    current_covered = current_policy_covers_request(
        request,
        access_policy=access_policy,
        expanded_scopes=expanded_scopes,
    )
    risk_level = risk_level_for_request(
        requested_scopes=expanded_scopes,
        requested_tenant_ids=request.requested_tenant_ids,
        requested_model_ids=request.requested_model_ids,
        validation_errors=validation_errors,
    )
    required_roles = required_approval_roles(
        requested_scopes=expanded_scopes,
        requested_tenant_ids=request.requested_tenant_ids,
        change_type=request.change_type,
    )
    missing_roles = missing_approval_roles(request, required_roles)
    review_status = review_status_for_request(
        request,
        validation_errors=validation_errors,
        missing_roles=missing_roles,
        current_policy_covered=current_covered,
    )
    return ServingAccessReviewItem(
        request_id=request.request_id,
        target_principal_id=request.target_principal_id,
        change_type=request.change_type,
        product=request.product,
        requested_scopes=expanded_scopes,
        requested_tenant_ids=request.requested_tenant_ids,
        requested_model_ids=request.requested_model_ids,
        risk_level=risk_level,
        review_status=review_status,
        current_policy_covered=current_covered,
        required_approval_roles=required_roles,
        missing_approval_roles=missing_roles,
        validation_errors=tuple(sorted(validation_errors)),
        action=action_for_status(review_status),
        refs=request.evidence_refs,
    )


def validate_change_request(
    request: ServingAccessChangeRequest,
    *,
    access_policy: ServingAccessPolicy,
    model_products: dict[str, str],
    scope_aliases: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    if request.change_type not in {
        "add_principal",
        "expand_scope",
        "expand_tenant",
        "expand_model",
        "remove_principal",
    }:
        errors.append(f"unsupported change_type: {request.change_type}")
    if not request.business_justification.strip():
        errors.append("business_justification is required")
    for scope in request.requested_scopes:
        try:
            expand_scope_alias(scope, scope_aliases, Path("model-serving-access-requests.yaml"))
        except RegistryValidationError:
            errors.append(f"unknown scope: {scope}")
    current_grant = access_policy.principals.get(request.target_principal_id)
    if request.change_type != "add_principal" and current_grant is None:
        errors.append(f"target principal does not exist: {request.target_principal_id}")
    if current_grant is not None and current_grant.product != request.product:
        errors.append(
            f"target principal product mismatch: {current_grant.product} != {request.product}"
        )
    if MODEL_SERVING_INVOKE_SCOPE in expand_scopes_for_report(request, scope_aliases):
        if not request.requested_model_ids:
            errors.append("invoke access must name at least one model_id")
        if not request.requested_tenant_ids:
            errors.append("invoke access must name at least one tenant_id")
    for model_id in request.requested_model_ids:
        model_product = model_products.get(model_id)
        if model_product is None:
            errors.append(f"unknown model_id: {model_id}")
        elif request.product != "ai-platform" and model_product != request.product:
            errors.append(
                f"product {request.product} cannot grant model {model_id} owned by {model_product}"
            )
    return errors


def expand_scopes_for_report(
    request: ServingAccessChangeRequest,
    scope_aliases: dict[str, str],
) -> tuple[str, ...]:
    expanded: list[str] = []
    for scope in request.requested_scopes:
        try:
            expanded.append(
                expand_scope_alias(scope, scope_aliases, Path("model-serving-access-requests.yaml"))
            )
        except RegistryValidationError:
            expanded.append(scope)
    return tuple(sorted(set(expanded)))


def current_policy_covers_request(
    request: ServingAccessChangeRequest,
    *,
    access_policy: ServingAccessPolicy,
    expanded_scopes: tuple[str, ...],
) -> bool:
    grant = access_policy.principals.get(request.target_principal_id)
    if grant is None:
        return False
    return (
        request.product == grant.product
        and set(expanded_scopes).issubset(set(grant.scopes))
        and set(request.requested_tenant_ids).issubset(set(grant.tenant_ids))
        and set(request.requested_model_ids).issubset(set(grant.allowed_model_ids))
    )


def required_approval_roles(
    *,
    requested_scopes: tuple[str, ...],
    requested_tenant_ids: tuple[str, ...],
    change_type: str,
) -> tuple[str, ...]:
    roles = set(REQUIRED_BASE_APPROVERS)
    if MODEL_SERVING_OPS_SCOPE in requested_scopes:
        roles.add(OPS_APPROVER)
    if len(requested_tenant_ids) > 1 or change_type == "expand_tenant":
        roles.add(TENANT_GOVERNANCE_APPROVER)
    return tuple(sorted(roles))


def missing_approval_roles(
    request: ServingAccessChangeRequest,
    required_roles: tuple[str, ...],
) -> tuple[str, ...]:
    approved_roles = {
        approval.role for approval in request.approvals if approval.decision == "approved"
    }
    return tuple(sorted(role for role in required_roles if role not in approved_roles))


def review_status_for_request(
    request: ServingAccessChangeRequest,
    *,
    validation_errors: list[str],
    missing_roles: tuple[str, ...],
    current_policy_covered: bool,
) -> str:
    if request.status in {"rejected", "withdrawn"}:
        return "rejected"
    if validation_errors:
        return "blocked"
    if missing_roles or request.status not in {"approved", "applied"}:
        return "needs_approval"
    if current_policy_covered:
        return "applied"
    return "ready_for_apply"


def action_for_status(review_status: str) -> str:
    return {
        "applied": "monitor_grant",
        "blocked": "fix_request_or_policy_before_review",
        "needs_approval": "collect_required_approvals",
        "ready_for_apply": "apply_policy_change",
        "rejected": "close_without_apply",
    }.get(review_status, "review_request")


def risk_level_for_request(
    *,
    requested_scopes: tuple[str, ...],
    requested_tenant_ids: tuple[str, ...],
    requested_model_ids: tuple[str, ...],
    validation_errors: list[str],
) -> str:
    if validation_errors or MODEL_SERVING_OPS_SCOPE in requested_scopes:
        return "critical"
    if len(requested_tenant_ids) > 1 or len(requested_model_ids) > 1:
        return "high"
    if MODEL_SERVING_INVOKE_SCOPE in requested_scopes:
        return "medium"
    return "low"


def build_report_from_items(
    items: tuple[ServingAccessReviewItem, ...],
) -> ServingAccessReviewReport:
    return ServingAccessReviewReport(
        request_count=len(items),
        applied_count=count_status(items, "applied"),
        ready_for_apply_count=count_status(items, "ready_for_apply"),
        needs_approval_count=count_status(items, "needs_approval"),
        blocked_count=count_status(items, "blocked"),
        rejected_count=count_status(items, "rejected"),
        critical_risk_count=count_risk(items, "critical"),
        high_risk_count=count_risk(items, "high"),
        by_status=count_by(items, "review_status"),
        by_risk_level=count_by(items, "risk_level"),
        action_queue={
            "applied": ids_for_status(items, "applied"),
            "blocked": ids_for_status(items, "blocked"),
            "needs_approval": ids_for_status(items, "needs_approval"),
            "ready_for_apply": ids_for_status(items, "ready_for_apply"),
            "rejected": ids_for_status(items, "rejected"),
        },
        items=items,
    )


def load_scope_aliases(root: Path) -> dict[str, str]:
    policy_path = root / "platform" / "governance" / "policies" / "model-serving-access-policy.yaml"
    policy = load_yaml(policy_path)
    aliases = policy.get("scope_aliases", {})
    if not isinstance(aliases, dict):
        raise RegistryValidationError(f"{policy_path} scope_aliases must be a mapping")
    result: dict[str, str] = {}
    for key, value in aliases.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise RegistryValidationError(f"{policy_path} scope_aliases entries must be strings")
        result[key] = value
    return result


def ids_for_status(items: tuple[ServingAccessReviewItem, ...], status: str) -> list[str]:
    return [item.request_id for item in items if item.review_status == status]


def count_status(items: tuple[ServingAccessReviewItem, ...], status: str) -> int:
    return len(ids_for_status(items, status))


def count_risk(items: tuple[ServingAccessReviewItem, ...], risk_level: str) -> int:
    return sum(1 for item in items if item.risk_level == risk_level)


def count_by(items: tuple[ServingAccessReviewItem, ...], attribute: str) -> dict[str, int]:
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
    request_id: str,
) -> list[dict[str, Any]]:
    value = row.get(key, [])
    if not isinstance(value, list):
        raise RegistryValidationError(f"serving access request {request_id} {key} must be a list")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(
                f"serving access request {request_id} {key}[{index}] must be a mapping"
            )
        result.append(item)
    return result


def require_str(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryValidationError(f"{owner} must define non-empty string field {key}")
    return value.strip()


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "governance" / "reports" / "model-serving-access-review-v1.yaml"
