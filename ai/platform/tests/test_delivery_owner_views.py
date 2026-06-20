from __future__ import annotations

from datetime import date
from pathlib import Path

from courseflow_ai_platform.delivery_owner_views import (
    build_delivery_owner_views_report,
    build_delivery_owner_views_report_from_sla,
    build_delivery_owner_views_snapshot,
)
from courseflow_ai_platform.delivery_sla import build_delivery_sla_report
from courseflow_ai_platform.governance_evaluation_incidents import (
    GovernanceEvaluationIncident,
    GovernanceEvaluationIncidentExport,
)
from courseflow_ai_platform.product_readiness_freshness import (
    build_ai_platform_product_readiness_freshness_report,
)
from courseflow_ai_platform.product_readiness_freshness_incidents import (
    build_product_readiness_freshness_incident_export_from_report,
)
from courseflow_ai_platform.registry import load_yaml


def test_delivery_owner_views_group_sla_items_by_owner_alias() -> None:
    report = build_delivery_owner_views_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["ownerCount"] == 6
    assert payload["itemCount"] == 23
    assert payload["topOwnerAlias"] == "admin-ops"
    assert payload["dueSoonOwnerCount"] == 5
    assert payload["monitoringOwnerCount"] == 2
    assert payload["overloadedOwnerCount"] == 2
    assert payload["missingOwnerAliasCount"] == 0
    assert payload["incidentCount"] == 0
    assert payload["openIncidentCount"] == 0
    assert payload["ownersWithOpenIncidentsCount"] == 0


def test_delivery_owner_views_expose_owner_work_queues() -> None:
    report = build_delivery_owner_views_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    views = {view.owner_alias: view for view in report.views}

    engineering = views["sa-ai-engineering"]
    assert engineering.item_count == 4
    assert engineering.due_soon_count == 2
    assert engineering.on_track_count == 0
    assert engineering.monitoring_count == 2
    assert engineering.next_due_at == "2026-06-20"
    assert engineering.next_review_at == "2026-06-24"
    assert engineering.backlog_ids[:3] == (
        "AIP-BLG-0013",
        "AIP-BLG-0014",
        "AIP-BLG-0017",
    )

    platform = views["sa-ai-platform"]
    assert platform.item_count == 6
    assert platform.due_soon_count == 6
    assert platform.on_track_count == 0
    assert platform.monitoring_count == 0
    assert platform.next_due_at == "2026-06-20"
    assert platform.backlog_ids == (
        "AIP-BLG-0001",
        "AIP-BLG-0002",
        "AIP-BLG-0003",
        "AIP-BLG-0004",
        "AIP-BLG-0005",
        "AIP-BLG-0006",
    )

    governance = views["sa-ai-platform-governance"]
    assert governance.item_count == 3
    assert governance.due_soon_count == 3
    assert governance.backlog_ids == (
        "AIP-BLG-0010",
        "AIP-BLG-0011",
        "AIP-BLG-0012",
    )

    admin_ops = views["admin-ops"]
    assert admin_ops.item_count == 6
    assert admin_ops.due_soon_count == 1
    assert admin_ops.on_track_count == 4
    assert admin_ops.monitoring_count == 1
    assert admin_ops.open_incident_count == 0
    assert admin_ops.backlog_ids == (
        "AIP-BLG-0019",
        "AIP-BLG-0020",
        "AIP-BLG-0021",
        "AIP-BLG-0022",
        "AIP-BLG-0023",
        "AIP-BLG-0016",
    )
    assert admin_ops.items[0].backlog_id == "AIP-BLG-0019"
    assert admin_ops.items[0].status == "in_progress"
    assert admin_ops.items[1].backlog_id == "AIP-BLG-0020"
    assert admin_ops.items[1].delivery_phase == "runtime_observability"
    assert admin_ops.items[2].backlog_id == "AIP-BLG-0021"
    assert admin_ops.items[2].delivery_phase == "governance_review"
    assert admin_ops.items[2].status == "accepted"
    assert admin_ops.items[3].backlog_id == "AIP-BLG-0022"
    assert admin_ops.items[3].delivery_phase == "governance_review"
    assert admin_ops.items[3].status == "accepted"
    assert admin_ops.items[4].backlog_id == "AIP-BLG-0023"
    assert admin_ops.items[4].delivery_phase == "governance_review"
    assert admin_ops.items[4].status == "accepted"


def test_delivery_owner_views_roll_up_stale_serving_access_incidents() -> None:
    report = build_delivery_owner_views_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-20",
    )
    views = {view.owner_alias: view for view in report.views}
    admin_ops = views["admin-ops"]

    assert report.incident_count == 2
    assert report.open_incident_count == 2
    assert report.owners_with_open_incidents_count == 1
    assert admin_ops.item_count == 5
    assert admin_ops.open_incident_count == 2
    assert admin_ops.p1_incident_count == 2
    incidents_by_condition = {
        incident.condition: incident for incident in admin_ops.incidents
    }
    stale_policy_apply = incidents_by_condition["stale_pending_policy_apply"]
    freshness_stale = incidents_by_condition[
        "product_readiness_freshness_report_stale"
    ]
    assert stale_policy_apply.action == "escalate_stale_policy_apply"
    assert stale_policy_apply.age_days == 3
    assert stale_policy_apply.application_ref.startswith("application:")
    assert freshness_stale.action == "refresh_product_readiness_freshness_report"
    assert freshness_stale.application_ref.startswith("product-readiness:")
    assert "lms-sequence-risk-sandbox-tenant" not in stale_policy_apply.application_ref


def test_delivery_owner_views_roll_up_governance_evaluation_incidents() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    sla_report = build_delivery_sla_report(ai_root, as_of="2026-06-17")

    report = build_delivery_owner_views_report_from_sla(
        sla_report,
        governance_evaluation_incident_export=repeated_governance_incident_export(),
    )
    views = {view.owner_alias: view for view in report.views}
    admin_ops = views["admin-ops"]

    assert report.incident_count == 1
    assert report.open_incident_count == 1
    assert report.owners_with_open_incidents_count == 1
    assert admin_ops.open_incident_count == 1
    assert admin_ops.p0_incident_count == 1
    assert admin_ops.incidents[0].condition == (
        "governance_evaluation_release_gate_mismatch"
    )
    assert admin_ops.incidents[0].action == (
        "escalate_governance_evaluation_release_gate_mismatch"
    )
    assert admin_ops.incidents[0].application_ref.startswith("platform:")


def test_delivery_owner_views_roll_up_product_readiness_freshness_incidents() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    sla_report = build_delivery_sla_report(ai_root, as_of="2026-06-17")
    freshness_report = build_ai_platform_product_readiness_freshness_report(
        ai_root,
        generated_at="2026-06-20",
    )

    report = build_delivery_owner_views_report_from_sla(
        sla_report,
        product_readiness_freshness_incident_export=(
            build_product_readiness_freshness_incident_export_from_report(
                freshness_report,
                as_of="2026-06-20",
            )
        ),
    )
    views = {view.owner_alias: view for view in report.views}
    admin_ops = views["admin-ops"]

    assert report.incident_count == 1
    assert report.open_incident_count == 1
    assert report.owners_with_open_incidents_count == 1
    assert admin_ops.open_incident_count == 1
    assert admin_ops.p1_incident_count == 1
    assert admin_ops.incidents[0].condition == (
        "product_readiness_static_snapshot_stale"
    )
    assert admin_ops.incidents[0].action == "refresh_product_readiness_snapshots"
    assert admin_ops.incidents[0].application_ref.startswith("product-readiness:")


def test_delivery_owner_views_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "delivery"
        / "reports"
        / "delivery-owner-views-v1.yaml"
    )
    generated = build_delivery_owner_views_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["owner_views"] == generated["owner_views"]


def repeated_governance_incident_export() -> GovernanceEvaluationIncidentExport:
    incident = GovernanceEvaluationIncident(
        incident_id="gei-test-release-gate-mismatch",
        condition="governance_evaluation_release_gate_mismatch",
        severity="p0",
        incident_status="open",
        owner_role="Admin/Ops",
        action="escalate_governance_evaluation_release_gate_mismatch",
        application_ref="platform:test-hash",
        ops_status="blocked_by_release_gate_drill_mismatch",
        consecutive_failure_count=2,
        repeated_failure_threshold=2,
        failed_drill_count=1,
        unexpected_error_count=0,
        age_days=None,
        stale_threshold_days=2,
        evidence_refs=(
            "policy:governance-evaluation-incident-policy-v1",
            "ledger:governance-evaluation-alert-drill-ledger-v1",
            "report:governance-evaluation-service-v1",
        ),
        reason="Repeated Governance Evaluation release-gate drill mismatch.",
    )
    return GovernanceEvaluationIncidentExport(
        as_of=date(2026, 6, 17),
        current_ops_status="blocked_by_release_gate_drill_mismatch",
        repeated_failure_threshold=2,
        observation_count=2,
        consecutive_failure_count=2,
        incident_count=1,
        open_count=1,
        watch_count=0,
        p0_count=1,
        p1_count=0,
        p2_count=0,
        repeated_failure_count=1,
        tenant_safe=True,
        raw_identifier_count=0,
        omitted_sensitive_fields=(
            "principal_ids",
            "tenant_ids",
            "request_bodies",
            "credential_values",
            "raw_drill_payloads",
        ),
        by_condition={"governance_evaluation_release_gate_mismatch": 1},
        by_severity={"p0": 1},
        by_status={"open": 1},
        action_queue={
            "open": [incident.incident_id],
            "watch": [],
            "p0": [incident.incident_id],
            "p1": [],
            "p2": [],
            "governance_evaluation_release_gate_mismatch": [incident.incident_id],
        },
        incidents=(incident,),
    )
