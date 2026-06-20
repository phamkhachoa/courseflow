from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.registry import load_yaml
from courseflow_ai_platform.serving_access_policy_plan import (
    build_serving_access_policy_patch_plan,
    build_serving_access_policy_patch_plan_snapshot,
)


def test_serving_access_policy_patch_plan_only_uses_ready_requests() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    plan = build_serving_access_policy_patch_plan(ai_root)

    assert plan.source_policy_id == "model-serving-access-policy-v1"
    assert plan.ready_request_count == 1
    assert plan.planned_operation_count == 1
    assert plan.skipped_request_count == 4
    assert plan.human_review_required is True
    assert plan.skipped_request_ids == (
        "lms-sequence-risk-serving-grant",
        "support-agent-assist-serving-grant",
        "enterprise-operations-serving-ops-observability",
        "finance-cross-product-support-risk-grant",
    )


def test_serving_access_policy_patch_plan_merges_tenant_without_mutating_active_policy() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    plan = build_serving_access_policy_patch_plan(ai_root)
    operation = plan.operations[0]

    assert operation.request_id == "lms-sequence-risk-sandbox-tenant"
    assert operation.action == "merge_tenant_allowlist"
    assert operation.added_scopes == ()
    assert operation.added_tenant_ids == ("tenant-lms-sandbox",)
    assert operation.added_model_ids == ()
    assert operation.before_grant is not None
    assert operation.before_grant["tenant_ids"] == ["tenant-lms"]
    assert operation.after_grant is not None
    assert operation.after_grant["tenant_ids"] == ["tenant-lms", "tenant-lms-sandbox"]

    proposed_lms = find_principal(plan.proposed_policy, "service:lms-courseflow-serving")
    assert proposed_lms["tenant_ids"] == ["tenant-lms", "tenant-lms-sandbox"]

    active_policy = load_yaml(
        ai_root / "platform" / "governance" / "policies" / "model-serving-access-policy.yaml"
    )
    active_lms = find_principal(active_policy, "service:lms-courseflow-serving")
    assert active_lms["tenant_ids"] == ["tenant-lms"]


def test_serving_access_policy_patch_plan_snapshot_includes_proposed_policy() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    snapshot = build_serving_access_policy_patch_plan_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert snapshot["report_id"] == "model-serving-access-policy-patch-plan-v1"
    assert snapshot["summary"]["ready_request_count"] == 1
    assert snapshot["summary"]["planned_operation_count"] == 1
    assert snapshot["summary"]["human_review_required"] is True
    proposed_lms = find_principal(snapshot["proposed_policy"], "service:lms-courseflow-serving")
    assert proposed_lms["tenant_ids"] == ["tenant-lms", "tenant-lms-sandbox"]


def find_principal(policy: dict[str, object], principal_id: str) -> dict[str, object]:
    principals = policy["principals"]
    assert isinstance(principals, list)
    for principal in principals:
        assert isinstance(principal, dict)
        if principal["principal_id"] == principal_id:
            return principal
    raise AssertionError(f"principal not found: {principal_id}")
