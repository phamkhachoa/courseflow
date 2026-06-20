from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.serving_access_review import (
    OPS_APPROVER,
    TENANT_GOVERNANCE_APPROVER,
    build_serving_access_review_report,
    build_serving_access_review_snapshot,
)


def test_serving_access_review_projects_change_control_queues() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_review_report(ai_root)

    assert report.request_count == 5
    assert report.applied_count == 2
    assert report.ready_for_apply_count == 1
    assert report.needs_approval_count == 1
    assert report.blocked_count == 1
    assert report.rejected_count == 0
    assert report.action_queue["applied"] == [
        "lms-sequence-risk-serving-grant",
        "support-agent-assist-serving-grant",
    ]
    assert report.action_queue["ready_for_apply"] == ["lms-sequence-risk-sandbox-tenant"]
    assert report.action_queue["needs_approval"] == [
        "enterprise-operations-serving-ops-observability"
    ]
    assert report.action_queue["blocked"] == ["finance-cross-product-support-risk-grant"]


def test_serving_access_review_requires_extra_approvals_for_tenant_and_ops_scope() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_review_report(ai_root)
    by_request = {item.request_id: item for item in report.items}

    tenant_request = by_request["lms-sequence-risk-sandbox-tenant"]
    assert tenant_request.review_status == "ready_for_apply"
    assert TENANT_GOVERNANCE_APPROVER in tenant_request.required_approval_roles
    assert tenant_request.missing_approval_roles == ()

    ops_request = by_request["enterprise-operations-serving-ops-observability"]
    assert ops_request.review_status == "needs_approval"
    assert OPS_APPROVER in ops_request.required_approval_roles
    assert ops_request.missing_approval_roles == ("Admin/Ops", "PO/BA")


def test_serving_access_review_blocks_cross_product_model_grants() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_review_report(ai_root)
    blocked = {
        item.request_id: item
        for item in report.items
        if item.review_status == "blocked"
    }

    item = blocked["finance-cross-product-support-risk-grant"]
    assert item.risk_level == "critical"
    assert item.current_policy_covered is False
    assert item.validation_errors == (
        "product billing-finance cannot grant model support-sla-risk-baseline-v1 "
        "owned by support-platform",
    )


def test_serving_access_review_snapshot_uses_snake_case_report_contract() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    snapshot = build_serving_access_review_snapshot(ai_root, generated_at="2026-06-17")

    assert snapshot["report_id"] == "model-serving-access-review-v1"
    assert snapshot["generated_at"] == "2026-06-17"
    assert snapshot["summary"]["request_count"] == 5
    assert snapshot["summary"]["ready_for_apply_count"] == 1
    assert snapshot["action_queue"]["blocked"] == ["finance-cross-product-support-risk-grant"]
