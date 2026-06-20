from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.model_serving import ModelServingMetricsSnapshot
from courseflow_ai_platform.operating_cockpit import (
    build_operating_cockpit_report,
    build_operating_cockpit_snapshot,
    build_serving_health_report_from_metrics,
)
from courseflow_ai_platform.registry import load_yaml


def test_operating_cockpit_summarizes_platform_control_plane() -> None:
    report = build_operating_cockpit_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["platformStatus"] == "attention_required"
    assert payload["deliveryStatus"] == "ready_work_available"
    assert payload["releaseStatus"] == "release_ready"
    assert payload["coverageModuleCount"] == 14
    assert payload["missingRequiredAreaCount"] == 0
    assert payload["evaluationRequiredPassedCount"] == payload["evaluationRequiredCount"]
    assert payload["evaluationRequiredCount"] == 20
    assert payload["dataContractCount"] == 7
    assert payload["dataContractDesignReadyRequestCount"] == 6
    assert payload["dataContractProductionReadyRequestCount"] == 3
    assert payload["dataContractMissingDomainCount"] == 0
    assert payload["solutionRequestCount"] == 6
    assert payload["artifactManifestCount"] == 12
    assert payload["solutionReadyCount"] == 6
    assert payload["solutionNonLmsCount"] == 5
    assert payload["promotionRequestCount"] == 5
    assert payload["promotionRequestReadyCount"] == 3
    assert payload["promotionCount"] == 4
    assert payload["promotionReadyCount"] == 4
    assert payload["promotionBlockedCount"] == 0
    assert payload["servingStatus"] == "healthy"
    assert payload["servingHealth"]["metricsConnected"] is True
    assert payload["servingHealth"]["requestCount"] == 3
    assert payload["servingHealth"]["auditRecordCount"] == 3
    assert payload["servingAccessGovernanceStatus"] == "pending_policy_apply"
    assert payload["servingAccessGovernance"]["pendingApplyCount"] == 1
    assert payload["servingAccessGovernance"]["driftCount"] == 0
    assert payload["llmProviderOpsStatus"] == "contract_stub_observable"
    assert payload["llmProviderOps"]["providerCount"] == 2
    assert payload["llmProviderOps"]["blockedProviderCount"] == 0
    assert payload["llmProviderOps"]["costMonitoringProviderCount"] == 2
    assert payload["llmProviderOps"]["latencyMonitoringProviderCount"] == 2
    assert payload["llmProviderOps"]["secretRotationStatus"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert payload["llmProviderOps"]["secretManagerBindingCount"] == 0
    assert payload["llmProviderOps"]["rotationEvidenceProviderCount"] == 0
    assert payload["governanceEvaluationOpsStatus"] == "release_gate_observable"
    assert payload["governanceEvaluationOps"]["assessmentCount"] == 3
    assert payload["governanceEvaluationOps"]["approvedCount"] == 1
    assert payload["governanceEvaluationOps"]["reviewRequiredCount"] == 1
    assert payload["governanceEvaluationOps"]["blockedCount"] == 1
    assert payload["governanceEvaluationOps"]["directIdentifierRejectionCount"] == 1
    assert payload["governanceEvaluationOps"]["secretValueRejectionCount"] == 1
    assert payload["governanceEvaluationOps"]["unexpectedErrorCount"] == 0
    assert payload["mediaPrivacyReviewStatus"] == "approved"
    assert payload["mediaPrivacyReviewCount"] == 3
    assert payload["mediaPrivacyWaitingCount"] == 0
    assert payload["mediaPrivacyBlockedCount"] == 0
    assert payload["mediaPrivacyControlGapCount"] == 0
    assert payload["actionCount"] == 23


def test_operating_cockpit_actions_cover_blueprints_promotions_and_readiness() -> None:
    report = build_operating_cockpit_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    actions = {action.action_id: action for action in report.actions}

    assert (
        "solution_blueprint:publish_solution_architecture:"
        "enterprise-knowledge-assistant-discovery"
    ) in actions
    assert (
        actions[
            "promotion_intake:review_promotion_request:"
            "support-agent-assist-active-request"
        ].owner_role
        == "SA AI Platform + Governance Reviewer"
    )
    assert (
        "promotion_readiness:activate_approved_artifact:"
        "support-agent-assist-baseline-approved"
    ) in actions
    assert (
        "solution_blueprint:publish_solution_architecture:"
        "operations-routing-optimization-simulator"
    ) in actions
    assert (
        "promotion_intake:review_promotion_request:"
        "operations-routing-rl-simulator-request"
    ) in actions
    assert (
        "data_contract_coverage:harden_data_contract_for_production:"
        "finance-payment-fraud-scoring-discovery"
    ) in actions
    assert (
        "serving_health:connect_serving_metrics_export:model-serving-gateway"
    ) not in actions
    assert (
        "serving_access_governance:run_controlled_policy_applier:"
        "lms-sequence-risk-sandbox-tenant-apply-20260617"
    ) in actions
    assert (
        "llm_provider_ops:run_llm_provider_alert_delivery_drill:"
        "llm-provider-alert-routing-v1"
    ) in actions
    assert (
        actions[
            "llm_provider_ops:run_llm_provider_alert_delivery_drill:"
            "llm-provider-alert-routing-v1"
        ].owner_role
        == "Admin/Ops"
    )
    assert (
        "governance_evaluation_ops:"
        "run_governance_evaluation_release_gate_alert_drill:"
        "governance-evaluation-service-v1"
    ) in actions
    assert (
        actions[
            "governance_evaluation_ops:"
            "run_governance_evaluation_release_gate_alert_drill:"
            "governance-evaluation-service-v1"
        ].owner_role
        == "Admin/Ops"
    )
    assert (
        "governance_evaluation_response_drill:"
        "accept_governance_evaluation_incident_response_runbook_drill:"
        "governance-evaluation-incident-response-drill-v1"
    ) in actions
    assert (
        actions[
            "governance_evaluation_response_drill:"
            "accept_governance_evaluation_incident_response_runbook_drill:"
            "governance-evaluation-incident-response-drill-v1"
        ].owner_role
        == "Admin/Ops"
    )
    assert (
        "product_readiness_freshness_response_drill:"
        "accept_product_readiness_freshness_incident_response_drill_state:"
        "product-readiness-freshness-incident-response-drill-v1"
    ) in actions
    assert (
        actions[
            "product_readiness_freshness_response_drill:"
            "accept_product_readiness_freshness_incident_response_drill_state:"
            "product-readiness-freshness-incident-response-drill-v1"
        ].owner_role
        == "Admin/Ops"
    )
    assert (
        "promotion_intake:review_promotion_request:"
        "finance-document-intelligence-privacy-request"
    ) in actions
    assert (
        "media_privacy_review:complete_media_privacy_controls:"
        "finance-document-raw-ocr-review"
    ) not in actions
    assert (
        "media_privacy_review:complete_media_privacy_controls:"
        "speech-audio-raw-asr-diarization-review"
    ) not in actions


def test_serving_health_projection_flags_audit_and_serving_risk() -> None:
    serving_health = build_serving_health_report_from_metrics(
        ModelServingMetricsSnapshot(
            request_count=3,
            success_count=1,
            fallback_count=1,
            error_count=2,
            human_review_count=2,
            audit_record_count=2,
            audit_failure_count=1,
            by_model={
                "finance-payment-fraud-baseline-v1": {
                    "auditFailure": 1,
                    "auditRecord": 0,
                    "error": 1,
                    "fallback": 0,
                    "humanReview": 1,
                    "ok": 0,
                    "request": 1,
                },
                "operations-demand-forecast-baseline-v1": {
                    "auditFailure": 0,
                    "auditRecord": 2,
                    "error": 1,
                    "fallback": 1,
                    "humanReview": 1,
                    "ok": 1,
                    "request": 2,
                },
            },
        )
    )

    assert serving_health.status == "blocked_by_model_audit_failure"
    assert serving_health.model_count == 2
    assert serving_health.models_with_audit_failures == (
        "finance-payment-fraud-baseline-v1",
    )
    assert serving_health.models_with_errors == (
        "finance-payment-fraud-baseline-v1",
        "operations-demand-forecast-baseline-v1",
    )
    assert serving_health.models_without_audit_coverage == (
        "finance-payment-fraud-baseline-v1",
    )


def test_operating_cockpit_accepts_connected_serving_metrics() -> None:
    report = build_operating_cockpit_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
        serving_metrics=ModelServingMetricsSnapshot(
            request_count=1,
            success_count=1,
            fallback_count=0,
            error_count=0,
            human_review_count=1,
            audit_record_count=1,
            audit_failure_count=0,
            by_model={
                "operations-demand-forecast-baseline-v1": {
                    "auditFailure": 0,
                    "auditRecord": 1,
                    "error": 0,
                    "fallback": 0,
                    "humanReview": 1,
                    "ok": 1,
                    "request": 1,
                }
            },
        ),
    )
    actions = {action.action_id for action in report.actions}

    assert report.serving_health.status == "healthy"
    assert report.serving_health.metrics_connected is True
    assert report.serving_health.request_count == 1
    assert "serving_health:connect_serving_metrics_export:model-serving-gateway" not in actions


def test_operating_cockpit_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / "operating-cockpit-v1.yaml"
    )
    generated = build_operating_cockpit_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["governance_evaluation_ops"] == generated[
        "governance_evaluation_ops"
    ]
    assert checked_in["actions"] == generated["actions"]
