from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from courseflow_ai_platform.admin_ops_dashboard import (
    build_admin_ops_dashboard_freshness_manifest,
)
from courseflow_ai_platform.delivery_state_ledger import build_delivery_state_report
from courseflow_ai_platform.governance_evaluation_incidents import (
    build_governance_evaluation_incident_export,
)
from courseflow_ai_platform.governance_evaluation_response_drill import (
    build_governance_evaluation_incident_response_drill_report,
)
from courseflow_ai_platform.operating_cockpit import build_operating_cockpit_report
from courseflow_ai_platform.product_readiness import (
    GOVERNANCE_RESPONSE_RUNBOOK_ACTION_ID,
    PRODUCT_READINESS_FRESHNESS_RESPONSE_DRILL_ACTION_ID,
    build_ai_platform_product_readiness_report,
    build_ai_platform_product_readiness_report_from_reports,
    build_ai_platform_product_readiness_snapshot,
    load_platform_product_metadata,
)
from courseflow_ai_platform.product_readiness_freshness_incidents import (
    build_product_readiness_freshness_incident_export,
)
from courseflow_ai_platform.product_readiness_freshness_response_drill import (
    build_product_readiness_freshness_incident_response_drill_report,
)
from courseflow_ai_platform.product_readiness_freshness_response_metrics import (
    build_product_readiness_freshness_response_metrics_report,
)
from courseflow_ai_platform.registry import load_yaml
from courseflow_ai_platform.serving_access_incidents import (
    build_serving_access_incident_export,
)


def test_ai_platform_product_readiness_projects_response_acceptance() -> None:
    report = build_ai_platform_product_readiness_report(
        Path(__file__).resolve().parents[2],
        generated_at="2026-06-17",
    )
    payload = report.to_dict()
    gates = {gate.gate_id: gate for gate in report.gates}

    assert payload["productId"] == "ai-platform"
    assert payload["productName"] == "Enterprise AI Platform"
    assert payload["readinessStatus"] == "stakeholder_ready_with_followups"
    assert payload["stakeholderVisibilityStatus"] == "current_with_response_acceptance"
    assert payload["releaseStatus"] == "release_ready"
    assert payload["servingStatus"] == "healthy"
    assert payload["servingMetricsConnected"] is True
    assert payload["servingRequestCount"] == 3
    assert payload["servingAuditRecordCount"] == 3
    assert payload["servingErrorCount"] == 0
    assert payload["servingAuditFailureCount"] == 0
    assert payload["dashboardFreshnessStatus"] == "current"
    assert payload["governanceResponseDrillStatus"] == "passed"
    assert payload["productReadinessFreshnessResponseDrillStatus"] == "passed"
    assert payload["productReadinessFreshnessResponseMetricsStatus"] == "slo_met"
    assert payload["productReadinessFreshnessResponseMetricsIngestStatus"] == (
        "live_ingest_connected"
    )
    assert payload["productReadinessFreshnessResponseTrendStatus"] == (
        "trend_ready_with_watch"
    )
    assert payload["productReadinessFreshnessResponseAlertStatus"] == (
        "alerts_configured_with_watch"
    )
    assert payload["productReadinessFreshnessResponseAlertDrillStatus"] == "passed"
    assert payload["productReadinessFreshnessResponseAlertCalibrationStatus"] == (
        "calibrated_with_watch"
    )
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyStatus"
    ] == "suppression_policy_codified"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyDrillStatus"
    ] == "passed"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyEffectivenessStatus"
    ] == "effectiveness_monitored"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageStatus"
    ] == "coverage_expanded"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionStatus"
    ] == "regression_monitored"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloStatus"
    ] == "coverage_slo_published"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGovernanceStatus"
    ] == "release_governance_attached"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillStatus"
    ] == "passed"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectivenessStatus"
    ] == "effectiveness_monitored"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternStatus"
    ] == "enterprise_pattern_expanded"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionStatus"
    ] == "adoption_monitored"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloStatus"
    ] == "adoption_slo_published"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceStatus"
    ] == "enterprise_adoption_slo_release_governance_attached"
    assert payload[
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillStatus"
    ] == "passed"
    assert payload["governanceResponseRunbookAccepted"] is True
    assert payload["productReadinessFreshnessResponseDrillAccepted"] is True
    assert payload["productReadinessFreshnessResponseMetricsBreachCount"] == 0
    assert (
        payload["productReadinessFreshnessResponseMetricsLiveObservationCount"]
        == 5
    )
    assert payload["productReadinessFreshnessResponseTrendWatchCount"] == 1
    assert payload["productReadinessFreshnessResponseAlertCount"] == 1
    assert payload["productReadinessFreshnessResponseAlertRoutedCount"] == 1
    assert payload["productReadinessFreshnessResponseAlertDrillScenarioCount"] == 1
    assert payload["productReadinessFreshnessResponseAlertDrillPassedCount"] == 1
    assert payload["productReadinessFreshnessResponseAlertCalibratedCount"] == 1
    assert payload["productReadinessFreshnessResponseAlertNoisyCount"] == 0
    assert payload["productReadinessFreshnessResponseAlertSuppressionRuleCount"] == 1
    assert (
        payload["productReadinessFreshnessResponseAlertSuppressionActiveRuleCount"]
        == 1
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillScenarioCount"
        ]
        == 4
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillPassedCount"
        ]
        == 4
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyEffectiveSignalCount"
        ]
        == 4
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicySuppressionEffectivenessPct"
        ]
        == 100
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyEscalationPreservationPct"
        ]
        == 100
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageScenarioCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoveredScenarioCount"
        ]
        == 5
    )
    assert (
        payload["productReadinessFreshnessResponseAlertSuppressionPolicyCoveragePct"]
        == 100
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionCheckCount"
        ]
        == 7
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyPassedRegressionCheckCount"
        ]
        == 7
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloObjectiveCount"
        ]
        == 4
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloMetObjectiveCount"
        ]
        == 4
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyAttachedReleaseGateCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillScenarioCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillPassedCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectivenessSignalCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectiveSignalCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectivenessPct"
        ]
        == 100
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternBlueprintCount"
        ]
        == 6
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternNonLmsBlueprintCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternNonLmsProductCount"
        ]
        == 4
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternTaxonomyAreaCount"
        ]
        == 9
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSignalCount"
        ]
        == 6
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptedSignalCount"
        ]
        == 6
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionPct"
        ]
        == 100
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloObjectiveCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloMetObjectiveCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloTargetPct"
        ]
        == 100
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReviewCadenceDays"
        ]
        == 30
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceGateCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceAttachedGateCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceFailedGateCount"
        ]
        == 0
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillScenarioCount"
        ]
        == 5
    )
    assert (
        payload[
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillPassedCount"
        ]
        == 5
    )
    assert payload["tenantSafe"] is True
    assert payload["openIncidentCount"] == 0
    assert payload["watchIncidentCount"] == 1
    assert payload["requiredGateCount"] == 30
    assert payload["passedRequiredGateCount"] == 30
    assert payload["failedRequiredGateCount"] == 0
    assert payload["followupCount"] == 1
    assert payload["actionRequiredCount"] == 0
    assert gates["governance_response_runbook_accepted"].gate_status == "passed"
    assert gates["governance_response_runbook_accepted"].owner_role == "Admin/Ops"
    assert (
        gates["product_readiness_freshness_response_drill_passed"].gate_status
        == "passed"
    )
    assert (
        gates["product_readiness_freshness_response_drill_accepted"].gate_status
        == "passed"
    )
    assert (
        "platform/delivery/ledgers/delivery-state-ledger.yaml"
        in gates["product_readiness_freshness_response_drill_accepted"].evidence_refs
    )
    assert (
        gates[
            "product_readiness_freshness_live_response_metrics_ingest_connected"
        ].gate_status
        == "passed"
    )
    assert (
        gates["product_readiness_freshness_response_metrics_slo_met"].gate_status
        == "passed"
    )
    assert (
        gates["product_readiness_freshness_response_slo_trend_ready"].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alerts_configured"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alert_drill_passed"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alert_calibration_monitored"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alert_suppression_policy_codified"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_drill_passed"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_monitored"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_expanded"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_monitored"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_published"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_governance_attached"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill_passed"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness_monitored"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_pattern_expanded_to_enterprise_use_cases"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_monitored"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_published"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_attached"
        ].gate_status
        == "passed"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_passed"
        ].gate_status
        == "passed"
    )
    assert "platform/delivery/ledgers/delivery-state-ledger.yaml" in (
        gates["governance_response_runbook_accepted"].evidence_refs
    )
    assert report.followups[0].followup_id == (
        "monitor_enterprise_release_gate_pattern_adoption_slo_release_governance_effectiveness"
    )
    assert report.followups[0].followup_status == "tracked"


def test_ai_platform_product_readiness_blocks_without_runbook_acceptance() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    product_id, product_name = load_platform_product_metadata(ai_root)
    delivery_state = build_delivery_state_report(ai_root, as_of="2026-06-17")
    delivery_state_without_acceptance = replace(
        delivery_state,
        items=tuple(
            item
            for item in delivery_state.items
            if item.action_id != GOVERNANCE_RESPONSE_RUNBOOK_ACTION_ID
        ),
    )

    report = build_ai_platform_product_readiness_report_from_reports(
        product_id=product_id,
        product_name=product_name,
        operating_cockpit_report=build_operating_cockpit_report(
            ai_root,
            as_of="2026-06-17",
        ),
        delivery_state_report=delivery_state_without_acceptance,
        dashboard_freshness=build_admin_ops_dashboard_freshness_manifest(
            ai_root,
            generated_at="2026-06-17",
        ),
        serving_access_incident_export=build_serving_access_incident_export(
            ai_root,
            as_of="2026-06-17",
        ),
        governance_evaluation_incident_export=(
            build_governance_evaluation_incident_export(
                ai_root,
                as_of="2026-06-17",
            )
        ),
        governance_evaluation_response_drill=(
            build_governance_evaluation_incident_response_drill_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
        product_readiness_freshness_incident_export=(
            build_product_readiness_freshness_incident_export(
                ai_root,
                as_of="2026-06-17",
            )
        ),
        product_readiness_freshness_response_drill=(
            build_product_readiness_freshness_incident_response_drill_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
        product_readiness_freshness_response_metrics=(
            build_product_readiness_freshness_response_metrics_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
    )
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.readiness_status == "blocked"
    assert report.failed_required_gate_count == 1
    assert report.action_required_count == 1
    assert report.governance_response_runbook_accepted is False
    assert gates["governance_response_runbook_accepted"].gate_status == "blocked"


def test_ai_platform_product_readiness_blocks_without_product_response_acceptance() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    product_id, product_name = load_platform_product_metadata(ai_root)
    delivery_state = build_delivery_state_report(ai_root, as_of="2026-06-17")
    delivery_state_without_acceptance = replace(
        delivery_state,
        items=tuple(
            item
            for item in delivery_state.items
            if item.action_id != PRODUCT_READINESS_FRESHNESS_RESPONSE_DRILL_ACTION_ID
        ),
    )

    report = build_ai_platform_product_readiness_report_from_reports(
        product_id=product_id,
        product_name=product_name,
        operating_cockpit_report=build_operating_cockpit_report(
            ai_root,
            as_of="2026-06-17",
        ),
        delivery_state_report=delivery_state_without_acceptance,
        dashboard_freshness=build_admin_ops_dashboard_freshness_manifest(
            ai_root,
            generated_at="2026-06-17",
        ),
        serving_access_incident_export=build_serving_access_incident_export(
            ai_root,
            as_of="2026-06-17",
        ),
        governance_evaluation_incident_export=(
            build_governance_evaluation_incident_export(
                ai_root,
                as_of="2026-06-17",
            )
        ),
        governance_evaluation_response_drill=(
            build_governance_evaluation_incident_response_drill_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
        product_readiness_freshness_incident_export=(
            build_product_readiness_freshness_incident_export(
                ai_root,
                as_of="2026-06-17",
            )
        ),
        product_readiness_freshness_response_drill=(
            build_product_readiness_freshness_incident_response_drill_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
        product_readiness_freshness_response_metrics=(
            build_product_readiness_freshness_response_metrics_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
    )
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.readiness_status == "blocked"
    assert report.failed_required_gate_count == 1
    assert report.action_required_count == 1
    assert report.product_readiness_freshness_response_drill_accepted is False
    assert report.stakeholder_visibility_status == "attention_required"
    assert (
        gates["product_readiness_freshness_response_drill_accepted"].gate_status
        == "blocked"
    )


def test_ai_platform_product_readiness_blocks_on_response_metric_breach() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    product_id, product_name = load_platform_product_metadata(ai_root)
    response_metrics = build_product_readiness_freshness_response_metrics_report(
        ai_root,
        generated_at="2026-06-17",
    )
    breached_metrics = replace(
        response_metrics,
        response_metrics_status="slo_breached",
        breach_count=1,
    )

    report = build_ai_platform_product_readiness_report_from_reports(
        product_id=product_id,
        product_name=product_name,
        operating_cockpit_report=build_operating_cockpit_report(
            ai_root,
            as_of="2026-06-17",
        ),
        delivery_state_report=build_delivery_state_report(
            ai_root,
            as_of="2026-06-17",
        ),
        dashboard_freshness=build_admin_ops_dashboard_freshness_manifest(
            ai_root,
            generated_at="2026-06-17",
        ),
        serving_access_incident_export=build_serving_access_incident_export(
            ai_root,
            as_of="2026-06-17",
        ),
        governance_evaluation_incident_export=(
            build_governance_evaluation_incident_export(
                ai_root,
                as_of="2026-06-17",
            )
        ),
        governance_evaluation_response_drill=(
            build_governance_evaluation_incident_response_drill_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
        product_readiness_freshness_incident_export=(
            build_product_readiness_freshness_incident_export(
                ai_root,
                as_of="2026-06-17",
            )
        ),
        product_readiness_freshness_response_drill=(
            build_product_readiness_freshness_incident_response_drill_report(
                ai_root,
                generated_at="2026-06-17",
            )
        ),
        product_readiness_freshness_response_metrics=breached_metrics,
    )
    gates = {gate.gate_id: gate for gate in report.gates}

    assert report.readiness_status == "blocked"
    assert report.failed_required_gate_count == 19
    assert report.action_required_count == 19
    assert report.product_readiness_freshness_response_metrics_status == (
        "slo_breached"
    )
    assert (
        gates["product_readiness_freshness_response_metrics_slo_met"].gate_status
        == "blocked"
    )
    assert (
        gates["product_readiness_freshness_response_slo_trend_ready"].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alerts_configured"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alert_drill_passed"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alert_calibration_monitored"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_alert_suppression_policy_codified"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_drill_passed"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_monitored"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_expanded"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_monitored"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_published"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_governance_attached"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill_passed"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness_monitored"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_pattern_expanded_to_enterprise_use_cases"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_monitored"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_published"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_attached"
        ].gate_status
        == "blocked"
    )
    assert (
        gates[
            "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_passed"
        ].gate_status
        == "blocked"
    )


def test_ai_platform_product_readiness_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "product"
        / "reports"
        / "ai-platform-product-readiness-v1.yaml"
    )
    generated = build_ai_platform_product_readiness_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
