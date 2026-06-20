from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.delivery_backlog import (
    build_delivery_backlog_report,
    build_delivery_backlog_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def test_delivery_backlog_projects_cockpit_actions_into_work_items() -> None:
    report = build_delivery_backlog_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["itemCount"] == 23
    assert payload["readyToStartCount"] == 16
    assert payload["monitoringCount"] == 3
    assert payload["blockedCount"] == 0
    assert payload["p1Count"] == 13
    assert payload["p2Count"] == 10
    assert payload["bySource"] == {
        "data_contract_coverage": 3,
        "governance_evaluation_ops": 1,
        "governance_evaluation_response_drill": 1,
        "llm_provider_ops": 1,
        "product_readiness_freshness_response_drill": 1,
        "promotion_intake": 5,
        "promotion_readiness": 4,
        "serving_access_governance": 1,
        "solution_blueprint": 6,
    }
    assert payload["byStatus"] == {
        "accepted": 3,
        "active": 1,
        "draft": 3,
        "in_progress": 1,
        "ready": 11,
        "shadow": 2,
        "waiting": 2,
    }


def test_delivery_backlog_items_have_phase_owner_and_acceptance_criteria() -> None:
    report = build_delivery_backlog_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    items = {item.backlog_id: item for item in report.items}

    first_item = items["AIP-BLG-0001"]
    assert first_item.action_type == "publish_solution_architecture"
    assert first_item.delivery_phase == "solution_design"
    assert first_item.owner_role == "SA AI Platform"
    assert first_item.ready_to_start is True
    assert first_item.acceptance_criteria == (
        "Solution architecture is linked to the request.",
        "Data, evaluation, artifact and serving paths are identified.",
        "Backlog items exist for the next implementation slice.",
    )

    data_contract_item = items["AIP-BLG-0009"]
    assert data_contract_item.delivery_phase == "data_contract_hardening"
    assert data_contract_item.status == "draft"
    assert data_contract_item.blocker == (
        "data contract is sufficient for design but not production-ready"
    )

    assert all(item.action_type != "connect_serving_metrics_export" for item in items.values())

    serving_access_item = items["AIP-BLG-0019"]
    assert serving_access_item.action_type == "run_controlled_policy_applier"
    assert serving_access_item.delivery_phase == "serving_access_governance"
    assert serving_access_item.owner_role == "Admin/Ops"
    assert serving_access_item.status == "in_progress"
    assert serving_access_item.ready_to_start is False
    assert serving_access_item.acceptance_criteria == (
        "Controlled applier writes the proposed policy to an explicit target.",
        "Source and proposed policy checksums match the apply ledger.",
        "Reconciliation report moves the application out of pending apply.",
    )

    llm_alert_item = items["AIP-BLG-0020"]
    assert llm_alert_item.action_type == "run_llm_provider_alert_delivery_drill"
    assert llm_alert_item.delivery_phase == "runtime_observability"
    assert llm_alert_item.owner_role == "Admin/Ops"
    assert llm_alert_item.ready_to_start is True
    assert llm_alert_item.acceptance_criteria == (
        "Provider alert routes are configured for every observable LLM provider.",
        "Admin/Ops can trigger or simulate the provider budget/latency route.",
        "Alert evidence remains tenant-safe and excludes credential or prompt payloads.",
    )

    governance_eval_alert_item = items["AIP-BLG-0021"]
    assert governance_eval_alert_item.action_type == (
        "run_governance_evaluation_release_gate_alert_drill"
    )
    assert governance_eval_alert_item.delivery_phase == "governance_review"
    assert governance_eval_alert_item.owner_role == "Admin/Ops"
    assert governance_eval_alert_item.status == "accepted"
    assert governance_eval_alert_item.ready_to_start is False
    assert governance_eval_alert_item.acceptance_criteria == (
        "Governance evaluation release-gate alert path is triggered or simulated.",
        "Approved, review-required and blocked decisions route to the expected owner.",
        "Alert evidence remains tenant-safe and excludes identity or secret payloads.",
    )

    governance_eval_response_item = items["AIP-BLG-0022"]
    assert governance_eval_response_item.action_type == (
        "accept_governance_evaluation_incident_response_runbook_drill"
    )
    assert governance_eval_response_item.delivery_phase == "governance_review"
    assert governance_eval_response_item.owner_role == "Admin/Ops"
    assert governance_eval_response_item.status == "accepted"
    assert governance_eval_response_item.ready_to_start is False
    assert governance_eval_response_item.acceptance_criteria == (
        "Governance Evaluation incident response drill report is current and passed.",
        "P0/P1 repeated-failure scenarios map to Admin/Ops actions and runbook steps.",
        "Acceptance evidence excludes raw tenant, principal, request and credential values.",
    )

    product_readiness_response_item = items["AIP-BLG-0023"]
    assert product_readiness_response_item.action_type == (
        "accept_product_readiness_freshness_incident_response_drill_state"
    )
    assert product_readiness_response_item.delivery_phase == "governance_review"
    assert product_readiness_response_item.owner_role == "Admin/Ops"
    assert product_readiness_response_item.status == "accepted"
    assert product_readiness_response_item.ready_to_start is False
    assert product_readiness_response_item.acceptance_criteria == (
        "Product Readiness Freshness incident response drill report is current and passed.",
        "P0/P1 freshness, route, snapshot and audit-gap scenarios map to runbook steps.",
        "Acceptance evidence excludes raw tenant, principal, request and credential values.",
    )

    finance_doc_promotion_item = items["AIP-BLG-0012"]
    assert finance_doc_promotion_item.action_type == "review_promotion_request"
    assert finance_doc_promotion_item.delivery_phase == "promotion_review"
    assert finance_doc_promotion_item.owner_role == "SA AI Platform + Governance Reviewer"
    assert finance_doc_promotion_item.status == "ready"
    assert finance_doc_promotion_item.acceptance_criteria == (
        "Maker-checker review decision is recorded.",
        "Required gates and rollback evidence are accepted or blocked with reasons.",
        "Promotion registry is updated when the request is approved.",
    )


def test_delivery_backlog_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "delivery" / "reports" / "delivery-backlog-v1.yaml"
    )
    generated = build_delivery_backlog_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["by_source"] == generated["by_source"]
    assert checked_in["by_phase"] == generated["by_phase"]
    assert checked_in["by_owner_role"] == generated["by_owner_role"]
    assert checked_in["by_status"] == generated["by_status"]
    assert checked_in["items"] == generated["items"]
