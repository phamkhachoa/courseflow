from __future__ import annotations

import re
from pathlib import Path

from courseflow_ai_platform.admin_ops_dashboard import (
    build_admin_ops_dashboard,
    build_admin_ops_dashboard_freshness_manifest,
    write_admin_ops_dashboard,
    write_admin_ops_dashboard_freshness_manifest,
)
from courseflow_ai_platform.registry import load_yaml

OPENAI_KEY_PATTERN = re.compile(r"(^|[\"'\s:=])sk-[a-z0-9]")


def test_admin_ops_dashboard_builds_human_readable_html() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    artifact = build_admin_ops_dashboard(ai_root, generated_at="2026-06-17")

    assert artifact.platform_status == "attention_required"
    assert artifact.serving_access_status == "pending_policy_apply"
    assert artifact.llm_provider_ops_status == "contract_stub_observable"
    assert artifact.llm_provider_alert_routing_status == (
        "contract_stub_alerts_configured"
    )
    assert artifact.llm_provider_secret_rotation_status == (
        "contract_stub_rotation_controls_ready"
    )
    assert artifact.governance_evaluation_ops_status == "release_gate_observable"
    assert artifact.governance_evaluation_response_drill_status == "passed"
    assert artifact.product_readiness_freshness_status == "current"
    assert artifact.product_readiness_freshness_response_drill_status == "passed"
    assert artifact.product_readiness_freshness_response_metrics_status == "slo_met"
    assert artifact.product_readiness_freshness_response_metrics_ingest_status == (
        "live_ingest_connected"
    )
    assert artifact.product_readiness_freshness_response_metrics_breach_count == 0
    assert (
        artifact.product_readiness_freshness_response_metrics_live_observation_count
        == 5
    )
    assert artifact.product_readiness_freshness_response_metrics_max_recover_minutes == 170
    assert artifact.product_readiness_freshness_response_trend_status == (
        "trend_ready_with_watch"
    )
    assert artifact.product_readiness_freshness_response_trend_watch_count == 1
    assert artifact.product_readiness_freshness_response_alert_status == (
        "alerts_configured_with_watch"
    )
    assert artifact.product_readiness_freshness_response_alert_count == 1
    assert artifact.product_readiness_freshness_response_alert_routed_count == 1
    assert artifact.product_readiness_freshness_response_alert_drill_status == "passed"
    assert artifact.product_readiness_freshness_response_alert_drill_scenario_count == 1
    assert artifact.product_readiness_freshness_response_alert_drill_passed_count == 1
    assert artifact.product_readiness_freshness_response_alert_calibration_status == (
        "calibrated_with_watch"
    )
    assert artifact.product_readiness_freshness_response_alert_calibrated_count == 1
    assert artifact.product_readiness_freshness_response_alert_noisy_count == 0
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_status
        == "suppression_policy_codified"
    )
    assert artifact.product_readiness_freshness_response_alert_suppression_rule_count == 1
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_active_rule_count
        == 1
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_drill_status
        == "passed"
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count
        == 4
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_drill_passed_count
        == 4
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_effectiveness_status
        == "effectiveness_monitored"
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_effective_signal_count
        == 4
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct
        == 100
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct
        == 100
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_coverage_status
        == "coverage_expanded"
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count
        == 5
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count
        == 5
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_coverage_pct
        == 100
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_regression_status
        == "regression_monitored"
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_regression_check_count
        == 7
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count
        == 7
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status
        == "coverage_slo_published"
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count
        == 4
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count
        == 4
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_release_governance_status
        == "release_governance_attached"
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_release_gate_count
        == 5
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count
        == 5
    )
    assert (
        artifact.product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status
        == "passed"
    )
    assert artifact.release_gate_drill_scenario_count == 5
    assert artifact.release_gate_drill_passed_count == 5
    assert artifact.release_gate_effectiveness_status == "effectiveness_monitored"
    assert artifact.release_gate_effectiveness_signal_count == 5
    assert artifact.release_gate_effective_signal_count == 5
    assert artifact.release_gate_effectiveness_pct == 100
    assert artifact.release_gate_enterprise_pattern_status == (
        "enterprise_pattern_expanded"
    )
    assert artifact.release_gate_enterprise_pattern_blueprint_count == 6
    assert artifact.release_gate_enterprise_pattern_non_lms_blueprint_count == 5
    assert artifact.release_gate_enterprise_pattern_non_lms_product_count == 4
    assert artifact.release_gate_enterprise_pattern_taxonomy_area_count == 9
    assert artifact.release_gate_enterprise_adoption_status == "adoption_monitored"
    assert artifact.release_gate_enterprise_adoption_signal_count == 6
    assert artifact.release_gate_enterprise_adopted_signal_count == 6
    assert artifact.release_gate_enterprise_adoption_pct == 100
    assert artifact.release_gate_enterprise_adoption_slo_status == (
        "adoption_slo_published"
    )
    assert artifact.release_gate_enterprise_adoption_slo_objective_count == 5
    assert artifact.release_gate_enterprise_adoption_slo_met_objective_count == 5
    assert artifact.release_gate_enterprise_adoption_slo_target_pct == 100
    assert artifact.release_gate_enterprise_adoption_slo_release_governance_status == (
        "enterprise_adoption_slo_release_governance_attached"
    )
    assert artifact.release_gate_enterprise_adoption_slo_release_governance_gate_count == 5
    assert (
        artifact.release_gate_enterprise_adoption_slo_release_governance_attached_gate_count
        == 5
    )
    assert (
        artifact.release_gate_enterprise_adoption_slo_release_governance_failed_gate_count
        == 0
    )
    assert (
        artifact.release_gate_enterprise_adoption_slo_release_governance_drill_status
        == "passed"
    )
    assert (
        artifact.release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count
        == 5
    )
    assert (
        artifact.release_gate_enterprise_adoption_slo_release_governance_drill_passed_count
        == 5
    )
    assert artifact.product_readiness_runtime_readiness_status == (
        "stakeholder_ready_with_followups"
    )
    assert artifact.product_readiness_runtime_status_code == 200
    assert artifact.product_readiness_runtime_request_count == 1
    assert artifact.product_readiness_failed_check_count == 0
    assert artifact.owner_queue_count == 6
    assert artifact.admin_ops_item_count == 7
    assert artifact.admin_ops_open_incident_count == 0
    assert artifact.governance_evaluation_open_incident_count == 0
    assert artifact.governance_evaluation_watch_incident_count == 0
    assert artifact.product_readiness_freshness_open_incident_count == 0
    assert artifact.product_readiness_freshness_watch_incident_count == 0
    assert "AI Platform Admin/Ops Dashboard" in artifact.html
    assert "Operating Cockpit" in artifact.html
    assert "LLM Providers" in artifact.html
    assert "LLM Alerts" in artifact.html
    assert "LLM Secrets" in artifact.html
    assert "Governance Eval" in artifact.html
    assert "Product Freshness" in artifact.html
    assert "Governance assessments" in artifact.html
    assert "Product Readiness Freshness" in artifact.html
    assert "Product Readiness Freshness Incident Export" in artifact.html
    assert "Product Readiness Freshness Response Drill" in artifact.html
    assert "Product Readiness Freshness Response Metrics" in artifact.html
    assert "Product Readiness Freshness Response Trends" in artifact.html
    assert "Product Readiness Freshness Response SLO Drift Alerts" in artifact.html
    assert (
        "Product Readiness Freshness Response SLO Drift Alert Drill"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Alert Calibration"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Alert Suppression Policy"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy Drill"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy Effectiveness"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy Coverage"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Regression"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy Coverage SLO"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy "
        "Coverage Release Governance"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy "
        "Coverage Release Gate Drill"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy "
        "Coverage Release Gate Effectiveness"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy "
        "Coverage Release Gate Enterprise Pattern"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy "
        "Coverage Release Gate Enterprise Adoption"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy "
        "Coverage Release Gate Enterprise Adoption SLO"
        in artifact.html
    )
    assert (
        "Product Readiness Freshness Response SLO Drift Suppression Policy "
        "Coverage Release Gate Enterprise Adoption SLO Release Governance Drill"
        in artifact.html
    )
    assert "slo_met" in artifact.html
    assert "trend_ready_with_watch" in artifact.html
    assert "alerts_configured_with_watch" in artifact.html
    assert "coverage_expanded" in artifact.html
    assert "regression_monitored" in artifact.html
    assert "coverage_slo_published" in artifact.html
    assert "release_governance_attached" in artifact.html
    assert "release_gate_holds" in artifact.html
    assert "effectiveness_monitored" in artifact.html
    assert "enterprise_pattern_expanded" in artifact.html
    assert "adoption_monitored" in artifact.html
    assert "adoption_slo_published" in artifact.html
    assert "enterprise_adoption_slo_release_governance_attached" in artifact.html
    assert "enterprise_adoption_slo_release_governance_gate_holds" in artifact.html
    assert "live_ingest_connected" in artifact.html
    assert "required_ai_spectrum_runtime_ready" in artifact.html
    assert "8/8" in artifact.html
    assert "contract_stub_alerts_configured" in artifact.html
    assert "contract_stub_rotation_controls_ready" in artifact.html
    assert "contract_stub_observable" in artifact.html
    assert "release_gate_observable" in artifact.html
    assert "Admin/Ops Owner Queues" in artifact.html
    assert "Serving Access Incident Export" in artifact.html
    assert "Governance Evaluation Incident Export" in artifact.html
    assert "Governance Evaluation Response Drill" in artifact.html


def test_admin_ops_dashboard_uses_tenant_safe_incident_refs() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    artifact = build_admin_ops_dashboard(ai_root, generated_at="2026-06-20")
    html = artifact.html.lower()

    assert artifact.open_incident_count == 2
    assert artifact.admin_ops_open_incident_count == 2
    assert artifact.product_readiness_freshness_open_incident_count == 1
    assert "stale_pending_policy_apply" in html
    assert "escalate_stale_policy_apply" in html
    assert "product_readiness_freshness_report_stale" in html
    assert "refresh_product_readiness_freshness_report" in html
    assert "application:" in html
    assert "product-readiness:" in html
    assert "lms-sequence-risk-sandbox-tenant" not in html
    assert "tenant-lms" not in html
    assert "service:lms-courseflow-serving" not in html
    assert "token" not in html
    assert OPENAI_KEY_PATTERN.search(html) is None
    assert "api_key" not in html


def test_admin_ops_dashboard_write_artifact(tmp_path: Path) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "admin-ops-dashboard.html"

    written_path = write_admin_ops_dashboard(
        ai_root,
        output_path,
        generated_at="2026-06-17",
    )

    assert written_path == output_path
    assert output_path.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_admin_ops_dashboard_freshness_manifest_tracks_source_reports() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    manifest = build_admin_ops_dashboard_freshness_manifest(
        ai_root,
        generated_at="2026-06-17",
    )

    assert manifest.freshness_status == "current"
    assert manifest.dashboard_present is True
    assert manifest.dashboard_matches_generated_html is True
    assert manifest.source_count == 27
    assert manifest.present_source_count == 27
    assert manifest.current_source_count == 27
    assert manifest.stale_source_count == 0
    assert {source.source_id for source in manifest.sources} == {
        "delivery_owner_views",
        "governance_evaluation_incident_export",
        "governance_evaluation_response_drill",
        "operating_cockpit",
        "product_readiness_freshness",
        "product_readiness_freshness_incident_export",
        "product_readiness_freshness_response_drill",
        "product_readiness_freshness_response_metrics",
        "product_readiness_freshness_response_slo_drift_alert_calibration",
        "product_readiness_freshness_response_slo_drift_alert_drill",
        "product_readiness_freshness_response_slo_drift_alert_suppression_policy",
        "product_readiness_freshness_response_slo_drift_alerts",
        "product_readiness_freshness_response_slo_drift_suppression_policy_drill",
        "product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_drill",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_pattern",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_governance",
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo",
        "product_readiness_freshness_response_trends",
        "serving_access_incident_export",
    }


def test_admin_ops_dashboard_freshness_manifest_detects_stale_sources() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    manifest = build_admin_ops_dashboard_freshness_manifest(
        ai_root,
        generated_at="2026-06-20",
    )

    assert manifest.freshness_status == "source_stale"
    assert manifest.stale_source_count == 27
    assert manifest.current_source_count == 0
    assert manifest.dashboard_matches_generated_html is False


def test_admin_ops_dashboard_write_freshness_manifest(tmp_path: Path) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "dashboard-freshness.yaml"

    written_path = write_admin_ops_dashboard_freshness_manifest(
        ai_root,
        output_path,
        generated_at="2026-06-17",
    )

    payload = load_yaml(written_path)
    assert payload["manifest_id"] == "admin-ops-dashboard-freshness-v1"
    assert payload["summary"]["freshness_status"] == "current"
    assert payload["summary"]["source_count"] == 27


def test_admin_ops_dashboard_checked_in_artifact_matches_generator() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / "admin-ops-dashboard-v1.html"
    ).read_text(encoding="utf-8")
    generated = build_admin_ops_dashboard(
        ai_root,
        generated_at="2026-06-17",
    ).html

    assert checked_in == generated


def test_admin_ops_dashboard_checked_in_freshness_manifest_matches_generator() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / "admin-ops-dashboard-freshness-v1.yaml"
    )
    generated = build_admin_ops_dashboard_freshness_manifest(
        ai_root,
        generated_at="2026-06-17",
    ).to_snapshot_dict()

    assert checked_in == generated
