from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.coverage_taxonomy import (
    CoverageTaxonomyReport,
    validate_coverage_taxonomy,
)
from courseflow_ai_platform.data_contracts import (
    DataContractCoverageReport,
    build_data_contract_coverage_report,
)
from courseflow_ai_platform.evaluation import EvaluationRegistryReport, run_registered_evaluations
from courseflow_ai_platform.evidence import EvidenceValidationReport, validate_model_evidence
from courseflow_ai_platform.governance_evaluation_ops import (
    GovernanceEvaluationOpsReport,
    build_governance_evaluation_ops_report,
)
from courseflow_ai_platform.governance_evaluation_response_drill import (
    GovernanceEvaluationIncidentResponseDrillReport,
    build_governance_evaluation_incident_response_drill_report,
)
from courseflow_ai_platform.llm_provider_alerts import (
    LlmProviderAlertRoutingReport,
    build_llm_provider_alert_routing_report,
)
from courseflow_ai_platform.llm_provider_runtime_probes import (
    LlmProviderRuntimeProbeReport,
    build_llm_provider_runtime_probe_report,
)
from courseflow_ai_platform.llm_provider_secret_rotation import (
    LlmProviderSecretRotationReport,
    build_llm_provider_secret_rotation_report,
)
from courseflow_ai_platform.media_privacy_review import (
    MediaPrivacyReviewReport,
    build_media_privacy_review_report,
)
from courseflow_ai_platform.model_serving import ModelServingMetricsSnapshot
from courseflow_ai_platform.product_readiness_freshness_response_drill import (
    ProductReadinessFreshnessIncidentResponseDrillReport,
    build_product_readiness_freshness_incident_response_drill_report,
)
from courseflow_ai_platform.promotion_intake import (
    PromotionIntakeReport,
    build_promotion_intake_report,
)
from courseflow_ai_platform.promotion_readiness import (
    PromotionReadinessReport,
    build_promotion_readiness_report,
)
from courseflow_ai_platform.registry import RegistryValidationReport, validate_registries
from courseflow_ai_platform.serving_access_policy_reconciliation import (
    ServingAccessPolicyReconciliationReport,
    build_serving_access_policy_reconciliation_report,
)
from courseflow_ai_platform.serving_metrics_export import load_model_serving_metrics_export
from courseflow_ai_platform.solution_blueprint import (
    SolutionBlueprintReport,
    build_solution_blueprint_report,
)


@dataclass(frozen=True, slots=True)
class OperatingCockpitAction:
    action_id: str
    source: str
    action_type: str
    owner_role: str
    priority: str
    status: str
    reason: str
    refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionId": self.action_id,
            "actionType": self.action_type,
            "ownerRole": self.owner_role,
            "priority": self.priority,
            "reason": self.reason,
            "refs": list(self.refs),
            "source": self.source,
            "status": self.status,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "source": self.source,
            "action_type": self.action_type,
            "owner_role": self.owner_role,
            "priority": self.priority,
            "status": self.status,
            "reason": self.reason,
            "refs": list(self.refs),
        }


@dataclass(frozen=True, slots=True)
class OperatingCockpitServingHealth:
    status: str
    metrics_connected: bool
    request_count: int
    success_count: int
    fallback_count: int
    error_count: int
    human_review_count: int
    audit_record_count: int
    audit_failure_count: int
    model_count: int
    models_with_errors: tuple[str, ...]
    models_with_audit_failures: tuple[str, ...]
    models_without_audit_coverage: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "auditFailureCount": self.audit_failure_count,
            "auditRecordCount": self.audit_record_count,
            "errorCount": self.error_count,
            "fallbackCount": self.fallback_count,
            "humanReviewCount": self.human_review_count,
            "metricsConnected": self.metrics_connected,
            "modelCount": self.model_count,
            "modelsWithAuditFailures": list(self.models_with_audit_failures),
            "modelsWithErrors": list(self.models_with_errors),
            "modelsWithoutAuditCoverage": list(self.models_without_audit_coverage),
            "requestCount": self.request_count,
            "status": self.status,
            "successCount": self.success_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "metrics_connected": self.metrics_connected,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "fallback_count": self.fallback_count,
            "error_count": self.error_count,
            "human_review_count": self.human_review_count,
            "audit_record_count": self.audit_record_count,
            "audit_failure_count": self.audit_failure_count,
            "model_count": self.model_count,
            "models_with_errors": list(self.models_with_errors),
            "models_with_audit_failures": list(self.models_with_audit_failures),
            "models_without_audit_coverage": list(self.models_without_audit_coverage),
        }


@dataclass(frozen=True, slots=True)
class OperatingCockpitServingAccessGovernance:
    status: str
    application_count: int
    pending_apply_count: int
    reconciled_count: int
    ledger_update_required_count: int
    drift_count: int
    active_policy_sha256: str
    pending_application_ids: tuple[str, ...]
    ledger_update_required_application_ids: tuple[str, ...]
    drift_application_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activePolicySha256": self.active_policy_sha256,
            "applicationCount": self.application_count,
            "driftApplicationIds": list(self.drift_application_ids),
            "driftCount": self.drift_count,
            "ledgerUpdateRequiredApplicationIds": list(
                self.ledger_update_required_application_ids
            ),
            "ledgerUpdateRequiredCount": self.ledger_update_required_count,
            "pendingApplicationIds": list(self.pending_application_ids),
            "pendingApplyCount": self.pending_apply_count,
            "reconciledCount": self.reconciled_count,
            "status": self.status,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "application_count": self.application_count,
            "pending_apply_count": self.pending_apply_count,
            "reconciled_count": self.reconciled_count,
            "ledger_update_required_count": self.ledger_update_required_count,
            "drift_count": self.drift_count,
            "active_policy_sha256": self.active_policy_sha256,
            "pending_application_ids": list(self.pending_application_ids),
            "ledger_update_required_application_ids": list(
                self.ledger_update_required_application_ids
            ),
            "drift_application_ids": list(self.drift_application_ids),
        }


@dataclass(frozen=True, slots=True)
class OperatingCockpitLlmProviderOps:
    status: str
    rollout_status: str
    alert_routing_status: str
    secret_rotation_status: str
    provider_count: int
    live_provider_count: int
    blocked_provider_count: int
    cost_monitoring_provider_count: int
    latency_monitoring_provider_count: int
    alert_sink_count: int
    alert_route_count: int
    routed_provider_count: int
    secret_manager_binding_count: int
    rotation_automation_provider_count: int
    rotation_evidence_provider_count: int
    total_estimated_cost_micros: int
    max_p95_latency_ms: int
    blocked_provider_ids: tuple[str, ...]
    providers_without_cost_monitoring: tuple[str, ...]
    providers_without_latency_monitoring: tuple[str, ...]
    providers_without_alert_routes: tuple[str, ...]
    providers_without_secret_rotation: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertRouteCount": self.alert_route_count,
            "alertRoutingStatus": self.alert_routing_status,
            "alertSinkCount": self.alert_sink_count,
            "blockedProviderCount": self.blocked_provider_count,
            "blockedProviderIds": list(self.blocked_provider_ids),
            "costMonitoringProviderCount": self.cost_monitoring_provider_count,
            "latencyMonitoringProviderCount": self.latency_monitoring_provider_count,
            "liveProviderCount": self.live_provider_count,
            "maxP95LatencyMs": self.max_p95_latency_ms,
            "providerCount": self.provider_count,
            "providersWithoutCostMonitoring": list(
                self.providers_without_cost_monitoring
            ),
            "providersWithoutLatencyMonitoring": list(
                self.providers_without_latency_monitoring
            ),
            "providersWithoutAlertRoutes": list(self.providers_without_alert_routes),
            "providersWithoutSecretRotation": list(
                self.providers_without_secret_rotation
            ),
            "rolloutStatus": self.rollout_status,
            "rotationAutomationProviderCount": (
                self.rotation_automation_provider_count
            ),
            "rotationEvidenceProviderCount": self.rotation_evidence_provider_count,
            "routedProviderCount": self.routed_provider_count,
            "secretManagerBindingCount": self.secret_manager_binding_count,
            "secretRotationStatus": self.secret_rotation_status,
            "status": self.status,
            "totalEstimatedCostMicros": self.total_estimated_cost_micros,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "rollout_status": self.rollout_status,
            "alert_routing_status": self.alert_routing_status,
            "secret_rotation_status": self.secret_rotation_status,
            "provider_count": self.provider_count,
            "live_provider_count": self.live_provider_count,
            "blocked_provider_count": self.blocked_provider_count,
            "cost_monitoring_provider_count": self.cost_monitoring_provider_count,
            "latency_monitoring_provider_count": self.latency_monitoring_provider_count,
            "alert_sink_count": self.alert_sink_count,
            "alert_route_count": self.alert_route_count,
            "routed_provider_count": self.routed_provider_count,
            "secret_manager_binding_count": self.secret_manager_binding_count,
            "rotation_automation_provider_count": (
                self.rotation_automation_provider_count
            ),
            "rotation_evidence_provider_count": self.rotation_evidence_provider_count,
            "total_estimated_cost_micros": self.total_estimated_cost_micros,
            "max_p95_latency_ms": self.max_p95_latency_ms,
            "blocked_provider_ids": list(self.blocked_provider_ids),
            "providers_without_cost_monitoring": list(
                self.providers_without_cost_monitoring
            ),
            "providers_without_latency_monitoring": list(
                self.providers_without_latency_monitoring
            ),
            "providers_without_alert_routes": list(self.providers_without_alert_routes),
            "providers_without_secret_rotation": list(
                self.providers_without_secret_rotation
            ),
        }


@dataclass(frozen=True, slots=True)
class OperatingCockpitReport:
    platform_status: str
    delivery_status: str
    release_status: str
    serving_health: OperatingCockpitServingHealth
    serving_access_governance: OperatingCockpitServingAccessGovernance
    llm_provider_ops: OperatingCockpitLlmProviderOps
    governance_evaluation_ops: GovernanceEvaluationOpsReport | None
    product_count: int
    use_case_count: int
    non_lms_use_case_count: int
    capability_count: int
    coverage_module_count: int
    missing_required_area_count: int
    executable_surface_count: int
    evaluation_required_count: int
    evaluation_required_passed_count: int
    data_contract_count: int
    data_contract_design_ready_request_count: int
    data_contract_production_ready_request_count: int
    data_contract_missing_domain_count: int
    artifact_manifest_count: int
    artifact_promotion_count: int
    solution_request_count: int
    solution_ready_count: int
    solution_waiting_count: int
    solution_non_lms_count: int
    promotion_request_count: int
    promotion_request_ready_count: int
    promotion_request_waiting_count: int
    promotion_count: int
    promotion_ready_count: int
    promotion_blocked_count: int
    promotion_non_lms_count: int
    media_privacy_review_status: str
    media_privacy_review_count: int
    media_privacy_approved_count: int
    media_privacy_waiting_count: int
    media_privacy_blocked_count: int
    media_privacy_raw_media_request_count: int
    media_privacy_control_gap_count: int
    action_count: int
    actions: tuple[OperatingCockpitAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionCount": self.action_count,
            "actions": [action.to_dict() for action in self.actions],
            "artifactManifestCount": self.artifact_manifest_count,
            "artifactPromotionCount": self.artifact_promotion_count,
            "capabilityCount": self.capability_count,
            "coverageModuleCount": self.coverage_module_count,
            "dataContractCount": self.data_contract_count,
            "dataContractDesignReadyRequestCount": (
                self.data_contract_design_ready_request_count
            ),
            "dataContractMissingDomainCount": self.data_contract_missing_domain_count,
            "dataContractProductionReadyRequestCount": (
                self.data_contract_production_ready_request_count
            ),
            "deliveryStatus": self.delivery_status,
            "evaluationRequiredCount": self.evaluation_required_count,
            "evaluationRequiredPassedCount": self.evaluation_required_passed_count,
            "executableSurfaceCount": self.executable_surface_count,
            "governanceEvaluationOps": (
                self.governance_evaluation_ops.to_dict()
                if self.governance_evaluation_ops is not None
                else None
            ),
            "governanceEvaluationOpsStatus": (
                self.governance_evaluation_ops.ops_status
                if self.governance_evaluation_ops is not None
                else "not_connected"
            ),
            "missingRequiredAreaCount": self.missing_required_area_count,
            "nonLmsUseCaseCount": self.non_lms_use_case_count,
            "platformStatus": self.platform_status,
            "productCount": self.product_count,
            "promotionBlockedCount": self.promotion_blocked_count,
            "promotionCount": self.promotion_count,
            "promotionNonLmsCount": self.promotion_non_lms_count,
            "promotionReadyCount": self.promotion_ready_count,
            "promotionRequestCount": self.promotion_request_count,
            "promotionRequestReadyCount": self.promotion_request_ready_count,
            "promotionRequestWaitingCount": self.promotion_request_waiting_count,
            "releaseStatus": self.release_status,
            "llmProviderOps": self.llm_provider_ops.to_dict(),
            "llmProviderOpsStatus": self.llm_provider_ops.status,
            "mediaPrivacyApprovedCount": self.media_privacy_approved_count,
            "mediaPrivacyBlockedCount": self.media_privacy_blocked_count,
            "mediaPrivacyControlGapCount": self.media_privacy_control_gap_count,
            "mediaPrivacyRawMediaRequestCount": (
                self.media_privacy_raw_media_request_count
            ),
            "mediaPrivacyReviewCount": self.media_privacy_review_count,
            "mediaPrivacyReviewStatus": self.media_privacy_review_status,
            "mediaPrivacyWaitingCount": self.media_privacy_waiting_count,
            "servingAccessGovernance": self.serving_access_governance.to_dict(),
            "servingAccessGovernanceStatus": self.serving_access_governance.status,
            "servingHealth": self.serving_health.to_dict(),
            "servingStatus": self.serving_health.status,
            "solutionNonLmsCount": self.solution_non_lms_count,
            "solutionReadyCount": self.solution_ready_count,
            "solutionRequestCount": self.solution_request_count,
            "solutionWaitingCount": self.solution_waiting_count,
            "useCaseCount": self.use_case_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "operating-cockpit-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "platform_status": self.platform_status,
                "delivery_status": self.delivery_status,
                "release_status": self.release_status,
                "serving_status": self.serving_health.status,
                "serving_metrics_connected": self.serving_health.metrics_connected,
                "serving_request_count": self.serving_health.request_count,
                "serving_error_count": self.serving_health.error_count,
                "serving_audit_failure_count": self.serving_health.audit_failure_count,
                "serving_audit_record_count": self.serving_health.audit_record_count,
                "serving_access_governance_status": (
                    self.serving_access_governance.status
                ),
                "serving_access_pending_apply_count": (
                    self.serving_access_governance.pending_apply_count
                ),
                "serving_access_ledger_update_required_count": (
                    self.serving_access_governance.ledger_update_required_count
                ),
                "serving_access_drift_count": self.serving_access_governance.drift_count,
                "llm_provider_ops_status": self.llm_provider_ops.status,
                "llm_provider_rollout_status": self.llm_provider_ops.rollout_status,
                "llm_provider_alert_routing_status": (
                    self.llm_provider_ops.alert_routing_status
                ),
                "llm_provider_secret_rotation_status": (
                    self.llm_provider_ops.secret_rotation_status
                ),
                "llm_provider_count": self.llm_provider_ops.provider_count,
                "llm_provider_blocked_count": (
                    self.llm_provider_ops.blocked_provider_count
                ),
                "llm_provider_cost_monitoring_count": (
                    self.llm_provider_ops.cost_monitoring_provider_count
                ),
                "llm_provider_latency_monitoring_count": (
                    self.llm_provider_ops.latency_monitoring_provider_count
                ),
                "llm_provider_alert_route_count": (
                    self.llm_provider_ops.alert_route_count
                ),
                "llm_provider_alert_sink_count": (
                    self.llm_provider_ops.alert_sink_count
                ),
                "llm_provider_secret_manager_binding_count": (
                    self.llm_provider_ops.secret_manager_binding_count
                ),
                "llm_provider_rotation_evidence_count": (
                    self.llm_provider_ops.rotation_evidence_provider_count
                ),
                "llm_provider_estimated_cost_micros": (
                    self.llm_provider_ops.total_estimated_cost_micros
                ),
                "llm_provider_max_p95_latency_ms": (
                    self.llm_provider_ops.max_p95_latency_ms
                ),
                "product_count": self.product_count,
                "use_case_count": self.use_case_count,
                "non_lms_use_case_count": self.non_lms_use_case_count,
                "capability_count": self.capability_count,
                "coverage_module_count": self.coverage_module_count,
                "missing_required_area_count": self.missing_required_area_count,
                "executable_surface_count": self.executable_surface_count,
                "evaluation_required_count": self.evaluation_required_count,
                "evaluation_required_passed_count": self.evaluation_required_passed_count,
                "governance_evaluation_ops_status": (
                    self.governance_evaluation_ops.ops_status
                    if self.governance_evaluation_ops is not None
                    else "not_connected"
                ),
                "governance_evaluation_assessment_count": (
                    self.governance_evaluation_ops.assessment_count
                    if self.governance_evaluation_ops is not None
                    else 0
                ),
                "governance_evaluation_approved_count": (
                    self.governance_evaluation_ops.approved_count
                    if self.governance_evaluation_ops is not None
                    else 0
                ),
                "governance_evaluation_review_required_count": (
                    self.governance_evaluation_ops.review_required_count
                    if self.governance_evaluation_ops is not None
                    else 0
                ),
                "governance_evaluation_blocked_count": (
                    self.governance_evaluation_ops.blocked_count
                    if self.governance_evaluation_ops is not None
                    else 0
                ),
                "governance_evaluation_direct_identifier_rejection_count": (
                    self.governance_evaluation_ops.direct_identifier_rejection_count
                    if self.governance_evaluation_ops is not None
                    else 0
                ),
                "governance_evaluation_secret_value_rejection_count": (
                    self.governance_evaluation_ops.secret_value_rejection_count
                    if self.governance_evaluation_ops is not None
                    else 0
                ),
                "governance_evaluation_unexpected_error_count": (
                    self.governance_evaluation_ops.unexpected_error_count
                    if self.governance_evaluation_ops is not None
                    else 0
                ),
                "data_contract_count": self.data_contract_count,
                "data_contract_design_ready_request_count": (
                    self.data_contract_design_ready_request_count
                ),
                "data_contract_production_ready_request_count": (
                    self.data_contract_production_ready_request_count
                ),
                "data_contract_missing_domain_count": (
                    self.data_contract_missing_domain_count
                ),
                "artifact_manifest_count": self.artifact_manifest_count,
                "artifact_promotion_count": self.artifact_promotion_count,
                "solution_request_count": self.solution_request_count,
                "solution_ready_count": self.solution_ready_count,
                "solution_waiting_count": self.solution_waiting_count,
                "solution_non_lms_count": self.solution_non_lms_count,
                "promotion_request_count": self.promotion_request_count,
                "promotion_request_ready_count": self.promotion_request_ready_count,
                "promotion_request_waiting_count": self.promotion_request_waiting_count,
                "promotion_count": self.promotion_count,
                "promotion_ready_count": self.promotion_ready_count,
                "promotion_blocked_count": self.promotion_blocked_count,
                "promotion_non_lms_count": self.promotion_non_lms_count,
                "media_privacy_review_status": self.media_privacy_review_status,
                "media_privacy_review_count": self.media_privacy_review_count,
                "media_privacy_approved_count": self.media_privacy_approved_count,
                "media_privacy_waiting_count": self.media_privacy_waiting_count,
                "media_privacy_blocked_count": self.media_privacy_blocked_count,
                "media_privacy_raw_media_request_count": (
                    self.media_privacy_raw_media_request_count
                ),
                "media_privacy_control_gap_count": (
                    self.media_privacy_control_gap_count
                ),
                "action_count": self.action_count,
            },
            "serving_health": self.serving_health.to_snapshot_dict(),
            "serving_access_governance": self.serving_access_governance.to_snapshot_dict(),
            "llm_provider_ops": self.llm_provider_ops.to_snapshot_dict(),
            "governance_evaluation_ops": (
                self.governance_evaluation_ops.to_snapshot_dict(
                    generated_at=generated_at
                )
                if self.governance_evaluation_ops is not None
                else None
            ),
            "actions": [action.to_snapshot_dict() for action in self.actions],
        }


def build_operating_cockpit_report(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
    serving_metrics: ModelServingMetricsSnapshot | None = None,
    llm_provider_runtime_probes: LlmProviderRuntimeProbeReport | None = None,
    llm_provider_alert_routing: LlmProviderAlertRoutingReport | None = None,
    llm_provider_secret_rotation: LlmProviderSecretRotationReport | None = None,
    media_privacy_review_report: MediaPrivacyReviewReport | None = None,
    governance_evaluation_ops_report: GovernanceEvaluationOpsReport | None = None,
    governance_evaluation_response_drill_report: (
        GovernanceEvaluationIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_response_drill_report: (
        ProductReadinessFreshnessIncidentResponseDrillReport | None
    ) = None,
) -> OperatingCockpitReport:
    root = Path(ai_root)
    loaded_metrics = serving_metrics
    if loaded_metrics is None:
        metrics_export = load_model_serving_metrics_export(root)
        loaded_metrics = metrics_export.metrics if metrics_export is not None else None
    return build_operating_cockpit_report_from_reports(
        registry_report=validate_registries(root),
        coverage_report=validate_coverage_taxonomy(root),
        evidence_report=validate_model_evidence(root),
        evaluation_report=run_registered_evaluations(root),
        data_contract_report=build_data_contract_coverage_report(root),
        solution_report=build_solution_blueprint_report(root),
        promotion_intake_report=build_promotion_intake_report(root),
        promotion_readiness_report=build_promotion_readiness_report(root, as_of=as_of),
        serving_health=build_serving_health_report_from_metrics(loaded_metrics),
        serving_access_governance=build_serving_access_governance_from_reconciliation(
            build_serving_access_policy_reconciliation_report(root)
        ),
        llm_provider_ops=build_llm_provider_ops_from_runtime_probes(
            llm_provider_runtime_probes
            or build_llm_provider_runtime_probe_report(
                root,
                generated_at=parse_report_date(as_of).isoformat(),
            ),
            llm_provider_alert_routing
            or build_llm_provider_alert_routing_report(
                root,
                generated_at=parse_report_date(as_of).isoformat(),
            ),
            llm_provider_secret_rotation
            or build_llm_provider_secret_rotation_report(
                root,
                generated_at=parse_report_date(as_of).isoformat(),
            ),
        ),
        media_privacy_review_report=media_privacy_review_report
        or build_media_privacy_review_report(
            root,
            generated_at=parse_report_date(as_of).isoformat(),
        ),
        governance_evaluation_ops_report=governance_evaluation_ops_report
        or build_governance_evaluation_ops_report(
            root,
            generated_at=parse_report_date(as_of).isoformat(),
        ),
        governance_evaluation_response_drill_report=(
            governance_evaluation_response_drill_report
            or build_governance_evaluation_incident_response_drill_report(
                root,
                generated_at=parse_report_date(as_of).isoformat(),
            )
        ),
        product_readiness_freshness_response_drill_report=(
            product_readiness_freshness_response_drill_report
            or build_product_readiness_freshness_incident_response_drill_report(
                root,
                generated_at=parse_report_date(as_of).isoformat(),
            )
        ),
    )


def build_operating_cockpit_report_from_reports(
    *,
    registry_report: RegistryValidationReport,
    coverage_report: CoverageTaxonomyReport,
    evidence_report: EvidenceValidationReport,
    evaluation_report: EvaluationRegistryReport,
    data_contract_report: DataContractCoverageReport,
    solution_report: SolutionBlueprintReport,
    promotion_intake_report: PromotionIntakeReport,
    promotion_readiness_report: PromotionReadinessReport,
    serving_health: OperatingCockpitServingHealth | None = None,
    serving_access_governance: OperatingCockpitServingAccessGovernance | None = None,
    llm_provider_ops: OperatingCockpitLlmProviderOps | None = None,
    media_privacy_review_report: MediaPrivacyReviewReport | None = None,
    governance_evaluation_ops_report: GovernanceEvaluationOpsReport | None = None,
    governance_evaluation_response_drill_report: (
        GovernanceEvaluationIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_response_drill_report: (
        ProductReadinessFreshnessIncidentResponseDrillReport | None
    ) = None,
) -> OperatingCockpitReport:
    serving_health = serving_health or build_serving_health_report_from_metrics(None)
    serving_access_governance = (
        serving_access_governance or build_empty_serving_access_governance()
    )
    llm_provider_ops = llm_provider_ops or build_empty_llm_provider_ops()
    actions = tuple(
        build_solution_actions(solution_report)
        + build_data_contract_actions(data_contract_report)
        + build_promotion_intake_actions(promotion_intake_report)
        + build_promotion_readiness_actions(promotion_readiness_report)
        + build_serving_health_actions(serving_health)
        + build_serving_access_governance_actions(serving_access_governance)
        + build_llm_provider_ops_actions(llm_provider_ops)
        + build_governance_evaluation_ops_actions(governance_evaluation_ops_report)
        + build_governance_evaluation_response_drill_actions(
            governance_evaluation_response_drill_report
        )
        + build_product_readiness_freshness_response_drill_actions(
            product_readiness_freshness_response_drill_report
        )
        + build_media_privacy_review_actions(media_privacy_review_report)
    )

    release_status = derive_release_status(evaluation_report, promotion_readiness_report)
    delivery_status = derive_delivery_status(solution_report, promotion_intake_report)
    platform_status = derive_platform_status(
        coverage_report,
        evaluation_report,
        promotion_readiness_report,
        serving_health,
        serving_access_governance,
        llm_provider_ops,
        governance_evaluation_ops_report,
        media_privacy_review_report,
        delivery_status,
        release_status,
    )

    return OperatingCockpitReport(
        platform_status=platform_status,
        delivery_status=delivery_status,
        release_status=release_status,
        serving_health=serving_health,
        serving_access_governance=serving_access_governance,
        llm_provider_ops=llm_provider_ops,
        governance_evaluation_ops=governance_evaluation_ops_report,
        product_count=registry_report.product_count,
        use_case_count=registry_report.use_case_count,
        non_lms_use_case_count=registry_report.non_lms_use_case_count,
        capability_count=registry_report.capability_count,
        coverage_module_count=coverage_report.module_count,
        missing_required_area_count=len(coverage_report.missing_required_areas),
        executable_surface_count=coverage_report.implemented_baseline_count
        + coverage_report.executable_gate_count,
        evaluation_required_count=evaluation_report.required_count,
        evaluation_required_passed_count=evaluation_report.required_passed_count,
        data_contract_count=data_contract_report.contract_count,
        data_contract_design_ready_request_count=(
            data_contract_report.design_ready_request_count
        ),
        data_contract_production_ready_request_count=(
            data_contract_report.production_ready_request_count
        ),
        data_contract_missing_domain_count=data_contract_report.missing_domain_count,
        artifact_manifest_count=evidence_report.manifest_count,
        artifact_promotion_count=evidence_report.promotion_count,
        solution_request_count=solution_report.request_count,
        solution_ready_count=solution_report.ready_count,
        solution_waiting_count=solution_report.waiting_count,
        solution_non_lms_count=solution_report.non_lms_count,
        promotion_request_count=promotion_intake_report.request_count,
        promotion_request_ready_count=promotion_intake_report.ready_count,
        promotion_request_waiting_count=promotion_intake_report.waiting_count,
        promotion_count=promotion_readiness_report.promotion_count,
        promotion_ready_count=promotion_readiness_report.ready_count,
        promotion_blocked_count=promotion_readiness_report.blocked_count,
        promotion_non_lms_count=promotion_readiness_report.non_lms_count,
        media_privacy_review_status=(
            media_privacy_review_report.review_status
            if media_privacy_review_report is not None
            else "not_connected"
        ),
        media_privacy_review_count=(
            media_privacy_review_report.review_count
            if media_privacy_review_report is not None
            else 0
        ),
        media_privacy_approved_count=(
            media_privacy_review_report.approved_count
            if media_privacy_review_report is not None
            else 0
        ),
        media_privacy_waiting_count=(
            media_privacy_review_report.waiting_for_controls_count
            if media_privacy_review_report is not None
            else 0
        ),
        media_privacy_blocked_count=(
            media_privacy_review_report.blocked_count
            if media_privacy_review_report is not None
            else 0
        ),
        media_privacy_raw_media_request_count=(
            media_privacy_review_report.raw_media_request_count
            if media_privacy_review_report is not None
            else 0
        ),
        media_privacy_control_gap_count=(
            media_privacy_review_report.control_gap_count
            if media_privacy_review_report is not None
            else 0
        ),
        action_count=len(actions),
        actions=actions,
    )


def build_operating_cockpit_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    serving_metrics: ModelServingMetricsSnapshot | None = None,
    llm_provider_runtime_probes: LlmProviderRuntimeProbeReport | None = None,
    llm_provider_alert_routing: LlmProviderAlertRoutingReport | None = None,
    llm_provider_secret_rotation: LlmProviderSecretRotationReport | None = None,
    media_privacy_review_report: MediaPrivacyReviewReport | None = None,
    governance_evaluation_ops_report: GovernanceEvaluationOpsReport | None = None,
    governance_evaluation_response_drill_report: (
        GovernanceEvaluationIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_response_drill_report: (
        ProductReadinessFreshnessIncidentResponseDrillReport | None
    ) = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_operating_cockpit_report(
        ai_root,
        as_of=report_date,
        serving_metrics=serving_metrics,
        llm_provider_runtime_probes=llm_provider_runtime_probes,
        llm_provider_alert_routing=llm_provider_alert_routing,
        llm_provider_secret_rotation=llm_provider_secret_rotation,
        media_privacy_review_report=media_privacy_review_report,
        governance_evaluation_ops_report=governance_evaluation_ops_report,
        governance_evaluation_response_drill_report=(
            governance_evaluation_response_drill_report
        ),
        product_readiness_freshness_response_drill_report=(
            product_readiness_freshness_response_drill_report
        ),
    ).to_snapshot_dict(generated_at=report_date)


def write_operating_cockpit_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
    serving_metrics: ModelServingMetricsSnapshot | None = None,
    llm_provider_runtime_probes: LlmProviderRuntimeProbeReport | None = None,
    llm_provider_alert_routing: LlmProviderAlertRoutingReport | None = None,
    llm_provider_secret_rotation: LlmProviderSecretRotationReport | None = None,
    media_privacy_review_report: MediaPrivacyReviewReport | None = None,
    governance_evaluation_ops_report: GovernanceEvaluationOpsReport | None = None,
    governance_evaluation_response_drill_report: (
        GovernanceEvaluationIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_response_drill_report: (
        ProductReadinessFreshnessIncidentResponseDrillReport | None
    ) = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_operating_cockpit_snapshot(
                root,
                generated_at=generated_at,
                serving_metrics=serving_metrics,
                llm_provider_runtime_probes=llm_provider_runtime_probes,
                llm_provider_alert_routing=llm_provider_alert_routing,
                llm_provider_secret_rotation=llm_provider_secret_rotation,
                media_privacy_review_report=media_privacy_review_report,
                governance_evaluation_ops_report=governance_evaluation_ops_report,
                governance_evaluation_response_drill_report=(
                    governance_evaluation_response_drill_report
                ),
                product_readiness_freshness_response_drill_report=(
                    product_readiness_freshness_response_drill_report
                ),
            ),
            handle,
            sort_keys=False,
        )
    return target


def derive_release_status(
    evaluation_report: EvaluationRegistryReport,
    promotion_readiness_report: PromotionReadinessReport,
) -> str:
    if evaluation_report.required_passed_count < evaluation_report.required_count:
        return "blocked_by_evaluation"
    if promotion_readiness_report.blocked_count:
        return "blocked_by_promotion_readiness"
    if promotion_readiness_report.stale_gate_count:
        return "blocked_by_stale_gate"
    if promotion_readiness_report.stale_artifact_count:
        return "blocked_by_stale_artifact"
    return "release_ready"


def derive_delivery_status(
    solution_report: SolutionBlueprintReport,
    promotion_intake_report: PromotionIntakeReport,
) -> str:
    if solution_report.ready_count or promotion_intake_report.ready_count:
        return "ready_work_available"
    if solution_report.waiting_count or promotion_intake_report.waiting_count:
        return "waiting_on_inputs"
    return "steady_state"


def derive_platform_status(
    coverage_report: CoverageTaxonomyReport,
    evaluation_report: EvaluationRegistryReport,
    promotion_readiness_report: PromotionReadinessReport,
    serving_health: OperatingCockpitServingHealth,
    serving_access_governance: OperatingCockpitServingAccessGovernance,
    llm_provider_ops: OperatingCockpitLlmProviderOps,
    governance_evaluation_ops_report: GovernanceEvaluationOpsReport | None,
    media_privacy_review_report: MediaPrivacyReviewReport | None,
    delivery_status: str,
    release_status: str,
) -> str:
    if coverage_report.missing_required_areas:
        return "blocked_by_coverage_gap"
    if release_status != "release_ready":
        return release_status
    if evaluation_report.required_passed_count < evaluation_report.required_count:
        return "blocked_by_evaluation"
    if promotion_readiness_report.blocked_count:
        return "blocked_by_release"
    if serving_health.status in {
        "blocked_by_model_audit_failure",
        "degraded_by_model_serving_errors",
    }:
        return serving_health.status
    if serving_access_governance.status == "drift_detected":
        return "blocked_by_serving_access_drift"
    if llm_provider_ops.status == "blocked_by_llm_provider_runtime_probe":
        return "blocked_by_llm_provider_runtime_probe"
    if llm_provider_ops.alert_routing_status == "blocked":
        return "blocked_by_llm_provider_alert_routing"
    if llm_provider_ops.secret_rotation_status == "blocked":
        return "blocked_by_llm_provider_secret_rotation"
    if (
        governance_evaluation_ops_report is not None
        and governance_evaluation_ops_report.ops_status.startswith("blocked")
    ):
        return governance_evaluation_ops_report.ops_status
    if (
        media_privacy_review_report is not None
        and media_privacy_review_report.review_status == "blocked"
    ):
        return "blocked_by_media_privacy_review"
    if delivery_status in {"ready_work_available", "waiting_on_inputs"}:
        return "attention_required"
    if serving_health.status in {
        "metrics_not_connected",
        "attention_required_audit_gap",
    }:
        return "attention_required"
    if serving_access_governance.status in {
        "pending_policy_apply",
        "ledger_update_required",
    }:
        return "attention_required"
    if llm_provider_ops.status in {
        "runtime_probes_not_connected",
        "attention_required_llm_provider_observability_gap",
    }:
        return "attention_required"
    if llm_provider_ops.alert_routing_status in {
        "not_connected",
        "attention_required_alert_route_gap",
    }:
        return "attention_required"
    if llm_provider_ops.secret_rotation_status in {
        "not_connected",
        "attention_required_secret_rotation_gap",
    }:
        return "attention_required"
    if governance_evaluation_ops_report is None:
        return "attention_required"
    if governance_evaluation_ops_report.ops_status.startswith("attention_required"):
        return "attention_required"
    if media_privacy_review_report is None:
        return "attention_required"
    if media_privacy_review_report.review_status in {
        "waiting_for_controls",
        "ready_for_approval",
    }:
        return "attention_required"
    return "healthy"


def build_serving_health_report_from_metrics(
    metrics: ModelServingMetricsSnapshot | None,
) -> OperatingCockpitServingHealth:
    if metrics is None:
        return OperatingCockpitServingHealth(
            status="metrics_not_connected",
            metrics_connected=False,
            request_count=0,
            success_count=0,
            fallback_count=0,
            error_count=0,
            human_review_count=0,
            audit_record_count=0,
            audit_failure_count=0,
            model_count=0,
            models_with_errors=(),
            models_with_audit_failures=(),
            models_without_audit_coverage=(),
        )

    models_with_errors = tuple(
        sorted(
            model_id
            for model_id, row in metrics.by_model.items()
            if row.get("error", 0) > 0 or row.get("fallback", 0) > 0
        )
    )
    models_with_audit_failures = tuple(
        sorted(
            model_id
            for model_id, row in metrics.by_model.items()
            if row.get("auditFailure", 0) > 0
        )
    )
    models_without_audit_coverage = tuple(
        sorted(
            model_id
            for model_id, row in metrics.by_model.items()
            if row.get("request", 0) > row.get("auditRecord", 0)
        )
    )
    status = derive_serving_health_status(
        request_count=metrics.request_count,
        error_count=metrics.error_count,
        audit_record_count=metrics.audit_record_count,
        audit_failure_count=metrics.audit_failure_count,
    )
    return OperatingCockpitServingHealth(
        status=status,
        metrics_connected=True,
        request_count=metrics.request_count,
        success_count=metrics.success_count,
        fallback_count=metrics.fallback_count,
        error_count=metrics.error_count,
        human_review_count=metrics.human_review_count,
        audit_record_count=metrics.audit_record_count,
        audit_failure_count=metrics.audit_failure_count,
        model_count=len(metrics.by_model),
        models_with_errors=models_with_errors,
        models_with_audit_failures=models_with_audit_failures,
        models_without_audit_coverage=models_without_audit_coverage,
    )


def derive_serving_health_status(
    *,
    request_count: int,
    error_count: int,
    audit_record_count: int,
    audit_failure_count: int,
) -> str:
    if request_count == 0:
        return "no_serving_traffic"
    if audit_failure_count:
        return "blocked_by_model_audit_failure"
    if error_count:
        return "degraded_by_model_serving_errors"
    if audit_record_count < request_count:
        return "attention_required_audit_gap"
    return "healthy"


def build_serving_access_governance_from_reconciliation(
    report: ServingAccessPolicyReconciliationReport,
) -> OperatingCockpitServingAccessGovernance:
    return OperatingCockpitServingAccessGovernance(
        status=derive_serving_access_governance_status(report),
        application_count=report.application_count,
        pending_apply_count=report.pending_apply_count,
        reconciled_count=report.reconciled_count,
        ledger_update_required_count=report.ledger_update_required_count,
        drift_count=report.drift_count,
        active_policy_sha256=report.active_policy_sha256,
        pending_application_ids=tuple(report.action_queue["pending_apply"]),
        ledger_update_required_application_ids=tuple(
            report.action_queue["ledger_update_required"]
        ),
        drift_application_ids=tuple(report.action_queue["drift"]),
    )


def build_empty_serving_access_governance() -> OperatingCockpitServingAccessGovernance:
    return OperatingCockpitServingAccessGovernance(
        status="not_connected",
        application_count=0,
        pending_apply_count=0,
        reconciled_count=0,
        ledger_update_required_count=0,
        drift_count=0,
        active_policy_sha256="",
        pending_application_ids=(),
        ledger_update_required_application_ids=(),
        drift_application_ids=(),
    )


def build_llm_provider_ops_from_runtime_probes(
    report: LlmProviderRuntimeProbeReport | None,
    alert_routing_report: LlmProviderAlertRoutingReport | None = None,
    secret_rotation_report: LlmProviderSecretRotationReport | None = None,
) -> OperatingCockpitLlmProviderOps:
    if report is None:
        return build_empty_llm_provider_ops()
    blocked_provider_ids = tuple(
        item.provider_id for item in report.items if item.rollout_status == "blocked"
    )
    providers_without_cost_monitoring = tuple(
        item.provider_id for item in report.items if not item.cost_monitoring_enabled
    )
    providers_without_latency_monitoring = tuple(
        item.provider_id for item in report.items if not item.latency_monitoring_enabled
    )
    providers_without_alert_routes = (
        tuple(
            route.provider_id
            for route in alert_routing_report.routes
            if route.alert_route_status == "blocked"
        )
        if alert_routing_report is not None
        else ()
    )
    providers_without_secret_rotation = (
        tuple(
            item.provider_id
            for item in secret_rotation_report.items
            if item.rotation_status == "blocked"
        )
        if secret_rotation_report is not None
        else ()
    )
    return OperatingCockpitLlmProviderOps(
        status=derive_llm_provider_ops_status(
            report,
            blocked_provider_ids=blocked_provider_ids,
            providers_without_cost_monitoring=providers_without_cost_monitoring,
            providers_without_latency_monitoring=providers_without_latency_monitoring,
        ),
        rollout_status=report.rollout_status,
        alert_routing_status=(
            alert_routing_report.alert_routing_status
            if alert_routing_report is not None
            else "not_connected"
        ),
        secret_rotation_status=(
            secret_rotation_report.secret_rotation_status
            if secret_rotation_report is not None
            else "not_connected"
        ),
        provider_count=report.provider_count,
        live_provider_count=report.live_provider_count,
        blocked_provider_count=report.blocked_provider_count,
        cost_monitoring_provider_count=report.cost_monitoring_provider_count,
        latency_monitoring_provider_count=report.latency_monitoring_provider_count,
        alert_sink_count=(
            alert_routing_report.sink_count if alert_routing_report is not None else 0
        ),
        alert_route_count=(
            len(alert_routing_report.routes) if alert_routing_report is not None else 0
        ),
        routed_provider_count=(
            alert_routing_report.routed_provider_count
            if alert_routing_report is not None
            else 0
        ),
        secret_manager_binding_count=(
            secret_rotation_report.secret_manager_binding_count
            if secret_rotation_report is not None
            else 0
        ),
        rotation_automation_provider_count=(
            secret_rotation_report.rotation_automation_provider_count
            if secret_rotation_report is not None
            else 0
        ),
        rotation_evidence_provider_count=(
            secret_rotation_report.rotation_evidence_provider_count
            if secret_rotation_report is not None
            else 0
        ),
        total_estimated_cost_micros=report.total_estimated_cost_micros,
        max_p95_latency_ms=report.max_p95_latency_ms,
        blocked_provider_ids=blocked_provider_ids,
        providers_without_cost_monitoring=providers_without_cost_monitoring,
        providers_without_latency_monitoring=providers_without_latency_monitoring,
        providers_without_alert_routes=providers_without_alert_routes,
        providers_without_secret_rotation=providers_without_secret_rotation,
    )


def build_empty_llm_provider_ops() -> OperatingCockpitLlmProviderOps:
    return OperatingCockpitLlmProviderOps(
        status="runtime_probes_not_connected",
        rollout_status="not_connected",
        alert_routing_status="not_connected",
        secret_rotation_status="not_connected",
        provider_count=0,
        live_provider_count=0,
        blocked_provider_count=0,
        cost_monitoring_provider_count=0,
        latency_monitoring_provider_count=0,
        alert_sink_count=0,
        alert_route_count=0,
        routed_provider_count=0,
        secret_manager_binding_count=0,
        rotation_automation_provider_count=0,
        rotation_evidence_provider_count=0,
        total_estimated_cost_micros=0,
        max_p95_latency_ms=0,
        blocked_provider_ids=(),
        providers_without_cost_monitoring=(),
        providers_without_latency_monitoring=(),
        providers_without_alert_routes=(),
        providers_without_secret_rotation=(),
    )


def derive_llm_provider_ops_status(
    report: LlmProviderRuntimeProbeReport,
    *,
    blocked_provider_ids: tuple[str, ...],
    providers_without_cost_monitoring: tuple[str, ...],
    providers_without_latency_monitoring: tuple[str, ...],
) -> str:
    if blocked_provider_ids:
        return "blocked_by_llm_provider_runtime_probe"
    if (
        providers_without_cost_monitoring
        or providers_without_latency_monitoring
        or report.cost_monitoring_provider_count < report.provider_count
        or report.latency_monitoring_provider_count < report.provider_count
    ):
        return "attention_required_llm_provider_observability_gap"
    if report.rollout_status == "live_rollout_ready":
        return "live_rollout_ready"
    if report.rollout_status == "contract_stub_observable":
        return "contract_stub_observable"
    return report.rollout_status


def derive_serving_access_governance_status(
    report: ServingAccessPolicyReconciliationReport,
) -> str:
    if report.drift_count:
        return "drift_detected"
    if report.ledger_update_required_count:
        return "ledger_update_required"
    if report.pending_apply_count:
        return "pending_policy_apply"
    if report.application_count and report.reconciled_count == report.application_count:
        return "reconciled"
    return "steady_state"


def build_solution_actions(
    report: SolutionBlueprintReport,
) -> list[OperatingCockpitAction]:
    queue = report.to_dict()["actionQueue"]
    actions: list[OperatingCockpitAction] = []
    actions.extend(
        queue_actions(
            queue["readyForSolutionDesign"],
            source="solution_blueprint",
            action_type="publish_solution_architecture",
            owner_role="SA AI Platform",
            priority="p1",
            status="ready",
            reason="solution blueprint has no blockers",
        )
    )
    actions.extend(
        queue_actions(
            queue["needsDataContract"],
            source="solution_blueprint",
            action_type="define_data_contract",
            owner_role="PO/BA + Data Platform",
            priority="p1",
            status="waiting",
            reason="feature or training data contract is missing",
        )
    )
    actions.extend(
        queue_actions(
            queue["needsEvaluationStrategy"],
            source="solution_blueprint",
            action_type="define_evaluation_strategy",
            owner_role="SA AI Engineer",
            priority="p1",
            status="waiting",
            reason="offline or shadow evaluation strategy is missing",
        )
    )
    actions.extend(
        queue_actions(
            queue["needsPrivacyReview"],
            source="solution_blueprint",
            action_type="complete_privacy_review",
            owner_role="SA AI Platform + Governance Reviewer",
            priority="p1",
            status="waiting",
            reason="privacy review is required before media, document or high-impact AI",
        )
    )
    actions.extend(
        queue_actions(
            queue["needsSimulator"],
            source="solution_blueprint",
            action_type="build_simulator_or_offline_policy_eval",
            owner_role="SA AI Engineer",
            priority="p2",
            status="waiting",
            reason="decision policy requires simulator or offline policy evaluation",
        )
    )
    actions.extend(
        queue_actions(
            queue["needsPlatformBuild"],
            source="solution_blueprint",
            action_type="plan_platform_runtime_build",
            owner_role="SA AI Platform",
            priority="p2",
            status="waiting",
            reason="target taxonomy module is still roadmap or gated",
        )
    )
    return actions


def build_data_contract_actions(
    report: DataContractCoverageReport,
) -> list[OperatingCockpitAction]:
    queue = report.to_dict()["actionQueue"]
    actions: list[OperatingCockpitAction] = []
    actions.extend(
        queue_actions(
            queue["missingContract"],
            source="data_contract_coverage",
            action_type="define_missing_data_contract",
            owner_role="PO/BA + Data Platform",
            priority="p1",
            status="waiting",
            reason="use-case request has data domains without a registered contract",
        )
    )
    actions.extend(
        queue_actions(
            queue["needsProductionHardening"],
            source="data_contract_coverage",
            action_type="harden_data_contract_for_production",
            owner_role="Data Platform + Product Owner",
            priority="p2",
            status="draft",
            reason="data contract is sufficient for design but not production-ready",
        )
    )
    return actions


def build_promotion_intake_actions(
    report: PromotionIntakeReport,
) -> list[OperatingCockpitAction]:
    queue = report.to_dict()["actionQueue"]
    actions: list[OperatingCockpitAction] = []
    actions.extend(
        queue_actions(
            queue["readyForApproval"],
            source="promotion_intake",
            action_type="review_promotion_request",
            owner_role="SA AI Platform + Governance Reviewer",
            priority="p1",
            status="ready",
            reason="candidate artifact has enough evidence for approval review",
        )
    )
    actions.extend(
        queue_actions(
            queue["waitingForArtifact"],
            source="promotion_intake",
            action_type="publish_artifact_manifest",
            owner_role="SA AI Engineer",
            priority="p1",
            status="waiting",
            reason="promotion request is missing model or artifact evidence",
        )
    )
    actions.extend(
        queue_actions(
            queue["waitingForEvaluation"],
            source="promotion_intake",
            action_type="run_required_evaluation",
            owner_role="SA AI Engineer",
            priority="p1",
            status="waiting",
            reason="promotion request is missing accepted evaluation evidence",
        )
    )
    actions.extend(
        queue_actions(
            queue["waitingForPrivacyReview"],
            source="promotion_intake",
            action_type="complete_privacy_review",
            owner_role="Governance Reviewer",
            priority="p1",
            status="waiting",
            reason="artifact cannot enter promotion without privacy review",
        )
    )
    actions.extend(
        queue_actions(
            queue["waitingForSimulator"],
            source="promotion_intake",
            action_type="publish_simulator_evidence",
            owner_role="SA AI Engineer",
            priority="p2",
            status="waiting",
            reason="policy artifact needs simulator evidence before promotion",
        )
    )
    return actions


def build_promotion_readiness_actions(
    report: PromotionReadinessReport,
) -> list[OperatingCockpitAction]:
    queue = report.to_dict()["actionQueue"]
    actions: list[OperatingCockpitAction] = []
    actions.extend(
        queue_actions(
            queue["readyToActivate"],
            source="promotion_readiness",
            action_type="activate_approved_artifact",
            owner_role="Admin/Ops + Governance Reviewer",
            priority="p1",
            status="ready",
            reason="approved artifact is ready for activation",
        )
    )
    actions.extend(
        queue_actions(
            queue["activeMonitoring"],
            source="promotion_readiness",
            action_type="monitor_active_artifact",
            owner_role="Admin/Ops",
            priority="p2",
            status="active",
            reason="active artifact needs ongoing monitoring",
        )
    )
    actions.extend(
        queue_actions(
            queue["keepShadow"],
            source="promotion_readiness",
            action_type="keep_shadow_monitoring",
            owner_role="SA AI Engineer",
            priority="p2",
            status="shadow",
            reason="shadow artifact should continue collecting rollout evidence",
        )
    )
    actions.extend(
        queue_actions(
            queue["blocked"],
            source="promotion_readiness",
            action_type="resolve_release_blocker",
            owner_role="SA AI Platform + Governance Reviewer",
            priority="p0",
            status="blocked",
            reason="promotion readiness found a release blocker",
        )
    )
    return actions


def build_serving_health_actions(
    report: OperatingCockpitServingHealth,
) -> list[OperatingCockpitAction]:
    actions: list[OperatingCockpitAction] = []
    if report.status == "metrics_not_connected":
        actions.append(
            OperatingCockpitAction(
                action_id="serving_health:connect_serving_metrics_export:model-serving-gateway",
                source="serving_health",
                action_type="connect_serving_metrics_export",
                owner_role="SA AI Platform",
                priority="p1",
                status="waiting",
                reason="serving gateway metrics are not connected to the operating cockpit",
                refs=("model-serving-gateway",),
            )
        )
    if report.models_with_audit_failures:
        actions.append(
            OperatingCockpitAction(
                action_id="serving_health:investigate_model_audit_failures:"
                + ",".join(report.models_with_audit_failures),
                source="serving_health",
                action_type="investigate_model_audit_failures",
                owner_role="Admin/Ops + Governance Reviewer",
                priority="p0",
                status="blocked",
                reason="model audit storage failures require regulated workflow review",
                refs=report.models_with_audit_failures,
            )
        )
    if report.models_with_errors:
        actions.append(
            OperatingCockpitAction(
                action_id="serving_health:investigate_model_serving_errors:"
                + ",".join(report.models_with_errors),
                source="serving_health",
                action_type="investigate_model_serving_errors",
                owner_role="SA AI Engineer",
                priority="p1",
                status="active",
                reason="model serving errors or fallbacks were observed",
                refs=report.models_with_errors,
            )
        )
    if report.status == "attention_required_audit_gap":
        actions.append(
            OperatingCockpitAction(
                action_id="serving_health:enable_model_audit_store:"
                + ",".join(report.models_without_audit_coverage),
                source="serving_health",
                action_type="enable_model_audit_store",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p1",
                status="waiting",
                reason="model serving traffic is missing matching audit records",
                refs=report.models_without_audit_coverage,
            )
        )
    return actions


def build_serving_access_governance_actions(
    report: OperatingCockpitServingAccessGovernance,
) -> list[OperatingCockpitAction]:
    actions: list[OperatingCockpitAction] = []
    actions.extend(
        queue_actions(
            list(report.pending_application_ids),
            source="serving_access_governance",
            action_type="run_controlled_policy_applier",
            owner_role="Admin/Ops",
            priority="p1",
            status="ready",
            reason="serving access policy proposal is approved and pending apply",
        )
    )
    actions.extend(
        queue_actions(
            list(report.ledger_update_required_application_ids),
            source="serving_access_governance",
            action_type="record_serving_access_applied_checksum",
            owner_role="Admin/Ops + Governance Reviewer",
            priority="p1",
            status="waiting",
            reason="active policy matches proposal but apply ledger needs applied evidence",
        )
    )
    actions.extend(
        queue_actions(
            list(report.drift_application_ids),
            source="serving_access_governance",
            action_type="investigate_serving_access_policy_drift",
            owner_role="Admin/Ops + Governance Reviewer",
            priority="p0",
            status="blocked",
            reason="active policy checksum differs from source and proposed ledger checksums",
        )
    )
    return actions


def build_llm_provider_ops_actions(
    report: OperatingCockpitLlmProviderOps,
) -> list[OperatingCockpitAction]:
    actions: list[OperatingCockpitAction] = []
    if report.status == "runtime_probes_not_connected":
        actions.append(
            OperatingCockpitAction(
                action_id=(
                    "llm_provider_ops:connect_llm_provider_runtime_probe_export:"
                    "llm-provider-runtime-probes-v1"
                ),
                source="llm_provider_ops",
                action_type="connect_llm_provider_runtime_probe_export",
                owner_role="SA AI Platform",
                priority="p1",
                status="waiting",
                reason="LLM provider runtime probe report is not connected",
                refs=("llm-provider-runtime-probes-v1",),
            )
        )
    if report.blocked_provider_ids:
        actions.append(
            OperatingCockpitAction(
                action_id=(
                    "llm_provider_ops:investigate_llm_provider_runtime_probe_failures:"
                    + ",".join(report.blocked_provider_ids)
                ),
                source="llm_provider_ops",
                action_type="investigate_llm_provider_runtime_probe_failures",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p0",
                status="blocked",
                reason="LLM provider runtime probes block live provider rollout",
                refs=report.blocked_provider_ids,
            )
        )
    if (
        report.providers_without_cost_monitoring
        or report.providers_without_latency_monitoring
    ):
        refs = tuple(
            sorted(
                set(report.providers_without_cost_monitoring)
                | set(report.providers_without_latency_monitoring)
            )
        )
        actions.append(
            OperatingCockpitAction(
                action_id=(
                    "llm_provider_ops:connect_llm_provider_cost_latency_metrics:"
                    + ",".join(refs)
                ),
                source="llm_provider_ops",
                action_type="connect_llm_provider_cost_latency_metrics",
                owner_role="SA AI Platform",
                priority="p1",
                status="waiting",
                reason="LLM provider cost or latency monitoring is incomplete",
                refs=refs,
            )
        )
    if (
        report.status in {"contract_stub_observable", "live_rollout_ready"}
        and report.alert_routing_status
        in {"not_connected", "blocked", "attention_required_alert_route_gap"}
    ):
        actions.append(
            OperatingCockpitAction(
                action_id=(
                    "llm_provider_ops:configure_llm_provider_budget_latency_alerts:"
                    "llm-provider-runtime-probes-v1"
                ),
                source="llm_provider_ops",
                action_type="configure_llm_provider_budget_latency_alerts",
                owner_role="Admin/Ops",
                priority="p2",
                status="ready",
                reason=(
                    "LLM provider cost and latency evidence is available for "
                    "Admin/Ops alert configuration"
                ),
                refs=("llm-provider-runtime-probes-v1",),
            )
        )
    if (
        report.status in {"contract_stub_observable", "live_rollout_ready"}
        and report.secret_rotation_status
        in {"not_connected", "blocked", "attention_required_secret_rotation_gap"}
    ):
        refs = report.providers_without_secret_rotation or (
            "llm-provider-secret-rotation-v1",
        )
        actions.append(
            OperatingCockpitAction(
                action_id=(
                    "llm_provider_ops:configure_llm_provider_secret_rotation:"
                    + ",".join(refs)
                ),
                source="llm_provider_ops",
                action_type="configure_llm_provider_secret_rotation",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p1",
                status="waiting",
                reason=(
                    "Live LLM provider rollout requires secret manager binding, "
                    "rotation automation and evidence refs"
                ),
                refs=refs,
            )
        )
    if (
        report.status in {"contract_stub_observable", "live_rollout_ready"}
        and report.alert_routing_status
        in {"contract_stub_alerts_configured", "live_alert_ready"}
    ):
        actions.append(
            OperatingCockpitAction(
                action_id=(
                    "llm_provider_ops:run_llm_provider_alert_delivery_drill:"
                    "llm-provider-alert-routing-v1"
                ),
                source="llm_provider_ops",
                action_type="run_llm_provider_alert_delivery_drill",
                owner_role="Admin/Ops",
                priority="p2",
                status="ready",
                reason=(
                    "LLM provider alert routes are configured and need an "
                    "Admin/Ops delivery drill"
                ),
                refs=("llm-provider-alert-routing-v1",),
            )
        )
    return actions


def build_governance_evaluation_ops_actions(
    report: GovernanceEvaluationOpsReport | None,
) -> list[OperatingCockpitAction]:
    if report is None:
        return [
            OperatingCockpitAction(
                action_id=(
                    "governance_evaluation_ops:"
                    "connect_governance_evaluation_ops_report:"
                    "governance-evaluation-service-v1"
                ),
                source="governance_evaluation_ops",
                action_type="connect_governance_evaluation_ops_report",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p1",
                status="waiting",
                reason="governance evaluation ops report is not connected",
                refs=("governance-evaluation-service-v1",),
            )
        ]
    if report.ops_status.startswith("blocked"):
        return [
            OperatingCockpitAction(
                action_id=(
                    "governance_evaluation_ops:"
                    "investigate_governance_evaluation_ops_blocker:"
                    "governance-evaluation-service-v1"
                ),
                source="governance_evaluation_ops",
                action_type="investigate_governance_evaluation_ops_blocker",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p0",
                status="blocked",
                reason=(
                    "governance evaluation release gate drills block release "
                    "observability"
                ),
                refs=("governance-evaluation-service-v1", report.ops_status),
            )
        ]
    if report.ops_status.startswith("attention_required"):
        return [
            OperatingCockpitAction(
                action_id=(
                    "governance_evaluation_ops:"
                    "complete_governance_evaluation_guardrail_drills:"
                    "governance-evaluation-service-v1"
                ),
                source="governance_evaluation_ops",
                action_type="complete_governance_evaluation_guardrail_drills",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p1",
                status="waiting",
                reason=(
                    "governance evaluation ops report needs approved, review, "
                    "blocked and privacy rejection drill coverage"
                ),
                refs=("governance-evaluation-service-v1", report.ops_status),
            )
        ]
    return [
        OperatingCockpitAction(
            action_id=(
                "governance_evaluation_ops:"
                "run_governance_evaluation_release_gate_alert_drill:"
                "governance-evaluation-service-v1"
            ),
            source="governance_evaluation_ops",
            action_type="run_governance_evaluation_release_gate_alert_drill",
            owner_role="Admin/Ops",
            priority="p2",
            status="ready",
            reason=(
                "governance evaluation release gate metrics are observable and "
                "need an Admin/Ops alert drill"
            ),
            refs=("governance-evaluation-service-v1",),
        )
    ]


def build_governance_evaluation_response_drill_actions(
    report: GovernanceEvaluationIncidentResponseDrillReport | None,
) -> list[OperatingCockpitAction]:
    if report is None:
        return [
            OperatingCockpitAction(
                action_id=(
                    "governance_evaluation_response_drill:"
                    "connect_governance_evaluation_incident_response_drill:"
                    "governance-evaluation-incident-response-drill-v1"
                ),
                source="governance_evaluation_response_drill",
                action_type="connect_governance_evaluation_incident_response_drill",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p1",
                status="waiting",
                reason="Governance Evaluation incident response drill report is not connected",
                refs=("governance-evaluation-incident-response-drill-v1",),
            )
        ]
    if report.drill_status != "passed":
        return [
            OperatingCockpitAction(
                action_id=(
                    "governance_evaluation_response_drill:"
                    "fix_governance_evaluation_incident_response_runbook_drill:"
                    "governance-evaluation-incident-response-drill-v1"
                ),
                source="governance_evaluation_response_drill",
                action_type="fix_governance_evaluation_incident_response_runbook_drill",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p1",
                status="blocked",
                reason=(
                    "Governance Evaluation incident response drill must pass before "
                    "Admin/Ops can accept the runbook"
                ),
                refs=(
                    "governance-evaluation-incident-response-drill-v1",
                    report.drill_status,
                ),
            )
        ]
    return [
        OperatingCockpitAction(
            action_id=(
                "governance_evaluation_response_drill:"
                "accept_governance_evaluation_incident_response_runbook_drill:"
                "governance-evaluation-incident-response-drill-v1"
            ),
            source="governance_evaluation_response_drill",
            action_type="accept_governance_evaluation_incident_response_runbook_drill",
            owner_role="Admin/Ops",
            priority="p2",
            status="ready",
            reason=(
                "Governance Evaluation incident response drill passed and needs "
                "Admin/Ops acceptance evidence"
            ),
            refs=(
                "governance-evaluation-incident-response-drill-v1",
                report.runbook_id,
            ),
        )
    ]


def build_product_readiness_freshness_response_drill_actions(
    report: ProductReadinessFreshnessIncidentResponseDrillReport | None,
) -> list[OperatingCockpitAction]:
    if report is None:
        return [
            OperatingCockpitAction(
                action_id=(
                    "product_readiness_freshness_response_drill:"
                    "connect_product_readiness_freshness_incident_response_drill:"
                    "product-readiness-freshness-incident-response-drill-v1"
                ),
                source="product_readiness_freshness_response_drill",
                action_type="connect_product_readiness_freshness_incident_response_drill",
                owner_role="SA AI Platform + Admin/Ops",
                priority="p1",
                status="waiting",
                reason=(
                    "Product Readiness Freshness incident response drill report "
                    "is not connected"
                ),
                refs=("product-readiness-freshness-incident-response-drill-v1",),
            )
        ]
    if report.drill_status != "passed":
        return [
            OperatingCockpitAction(
                action_id=(
                    "product_readiness_freshness_response_drill:"
                    "fix_product_readiness_freshness_incident_response_drill:"
                    "product-readiness-freshness-incident-response-drill-v1"
                ),
                source="product_readiness_freshness_response_drill",
                action_type="fix_product_readiness_freshness_incident_response_drill",
                owner_role="SA AI Platform + Admin/Ops",
                priority="p1",
                status="blocked",
                reason=(
                    "Product Readiness Freshness incident response drill must pass "
                    "before Admin/Ops can accept the drill state"
                ),
                refs=(
                    "product-readiness-freshness-incident-response-drill-v1",
                    report.drill_status,
                ),
            )
        ]
    return [
        OperatingCockpitAction(
            action_id=(
                "product_readiness_freshness_response_drill:"
                "accept_product_readiness_freshness_incident_response_drill_state:"
                "product-readiness-freshness-incident-response-drill-v1"
            ),
            source="product_readiness_freshness_response_drill",
            action_type="accept_product_readiness_freshness_incident_response_drill_state",
            owner_role="Admin/Ops",
            priority="p2",
            status="ready",
            reason=(
                "Product Readiness Freshness incident response drill passed and "
                "needs Admin/Ops delivery-state acceptance evidence"
            ),
            refs=(
                "product-readiness-freshness-incident-response-drill-v1",
                report.runbook_id,
            ),
        )
    ]


def build_media_privacy_review_actions(
    report: MediaPrivacyReviewReport | None,
) -> list[OperatingCockpitAction]:
    if report is None:
        return [
            OperatingCockpitAction(
                action_id="media_privacy_review:connect_media_privacy_review_report:ai-platform",
                source="media_privacy_review",
                action_type="connect_media_privacy_review_report",
                owner_role="SA AI Platform + Governance Reviewer",
                priority="p1",
                status="waiting",
                reason="media privacy review report is not connected to the cockpit",
                refs=("ai-platform",),
            )
        ]
    queue = report.to_dict()["actionQueue"]
    actions: list[OperatingCockpitAction] = []
    actions.extend(
        queue_actions(
            queue["readyForApproval"],
            source="media_privacy_review",
            action_type="approve_media_privacy_review",
            owner_role="SA AI Platform + Governance Reviewer",
            priority="p1",
            status="ready",
            reason="media review has all required controls and is ready for decision",
        )
    )
    actions.extend(
        queue_actions(
            queue["waitingForControls"],
            source="media_privacy_review",
            action_type="complete_media_privacy_controls",
            owner_role="SA AI Platform + Governance Reviewer",
            priority="p1",
            status="waiting",
            reason="raw media request is missing required privacy control evidence",
        )
    )
    actions.extend(
        queue_actions(
            queue["blocked"],
            source="media_privacy_review",
            action_type="resolve_media_privacy_blocker",
            owner_role="SA AI Platform + Governance Reviewer",
            priority="p0",
            status="blocked",
            reason="media review has validation errors or blocked processing modes",
        )
    )
    return actions


def queue_actions(
    refs: list[str],
    *,
    source: str,
    action_type: str,
    owner_role: str,
    priority: str,
    status: str,
    reason: str,
) -> list[OperatingCockpitAction]:
    return [
        OperatingCockpitAction(
            action_id=f"{source}:{action_type}:{ref}",
            source=source,
            action_type=action_type,
            owner_role=owner_role,
            priority=priority,
            status=status,
            reason=reason,
            refs=(ref,),
        )
        for ref in refs
    ]


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "operations" / "reports" / "operating-cockpit-v1.yaml"


def parse_report_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)
