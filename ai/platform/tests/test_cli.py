from __future__ import annotations

import json
import sys
from pathlib import Path

from courseflow_ai_platform.cli import main
from courseflow_ai_platform.registry import load_yaml


def test_cli_includes_business_capability_coverage(
    capsys,
    monkeypatch,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["adminOpsDashboard"]["platformStatus"] == "attention_required"
    assert payload["adminOpsDashboard"]["ownerQueueCount"] == 6
    assert payload["adminOpsDashboard"]["adminOpsItemCount"] == 7
    assert payload["adminOpsDashboard"]["llmProviderOpsStatus"] == (
        "contract_stub_observable"
    )
    assert payload["adminOpsDashboard"]["llmProviderAlertRoutingStatus"] == (
        "contract_stub_alerts_configured"
    )
    assert payload["adminOpsDashboard"]["llmProviderSecretRotationStatus"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert payload["adminOpsDashboard"]["governanceEvaluationOpsStatus"] == (
        "release_gate_observable"
    )
    assert payload["adminOpsDashboard"]["governanceEvaluationResponseDrillStatus"] == (
        "passed"
    )
    assert payload["adminOpsDashboard"]["governanceEvaluationOpenIncidentCount"] == 0
    assert payload["adminOpsDashboard"]["governanceEvaluationWatchIncidentCount"] == 0
    assert payload["adminOpsDashboard"]["productReadinessFreshnessStatus"] == "current"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseDrillStatus"
    ] == "passed"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseMetricsStatus"
    ] == "slo_met"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseMetricsIngestStatus"
    ] == "live_ingest_connected"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseMetricsBreachCount"
    ] == 0
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseMetricsLiveObservationCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseMetricsMaxRecoverMinutes"
    ] == 170
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseTrendStatus"
    ] == "trend_ready_with_watch"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseTrendWatchCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertStatus"
    ] == "alerts_configured_with_watch"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertRoutedCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertDrillStatus"
    ] == "passed"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertDrillScenarioCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertDrillPassedCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertCalibrationStatus"
    ] == "calibrated_with_watch"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertCalibratedCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertNoisyCount"
    ] == 0
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyStatus"
    ] == "suppression_policy_codified"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionRuleCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionActiveRuleCount"
    ] == 1
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyDrillStatus"
    ] == "passed"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyDrillScenarioCount"
    ] == 4
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyDrillPassedCount"
    ] == 4
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyEffectivenessStatus"
    ] == "effectiveness_monitored"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyEffectiveSignalCount"
    ] == 4
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicySuppressionEffectivenessPct"
    ] == 100
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyEscalationPreservationPct"
    ] == 100
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageStatus"
    ] == "coverage_expanded"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageScenarioCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoveredScenarioCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoveragePct"
    ] == 100
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionStatus"
    ] == "regression_monitored"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionCheckCount"
    ] == 7
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyPassedRegressionCheckCount"
    ] == 7
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloStatus"
    ] == "coverage_slo_published"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloObjectiveCount"
    ] == 4
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloMetObjectiveCount"
    ] == 4
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGovernanceStatus"
    ] == "release_governance_attached"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyAttachedReleaseGateCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillStatus"
    ] == "passed"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillScenarioCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillPassedCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectivenessStatus"
    ] == "effectiveness_monitored"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectivenessSignalCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectiveSignalCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEffectivenessPct"
    ] == 100
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternStatus"
    ] == "enterprise_pattern_expanded"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionStatus"
    ] == "adoption_monitored"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSignalCount"
    ] == 6
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptedSignalCount"
    ] == 6
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionPct"
    ] == 100
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloStatus"
    ] == "adoption_slo_published"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloObjectiveCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloMetObjectiveCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloTargetPct"
    ] == 100
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceStatus"
    ] == "enterprise_adoption_slo_release_governance_attached"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceGateCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceAttachedGateCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillStatus"
    ] == "passed"
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillScenarioCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillPassedCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternBlueprintCount"
    ] == 6
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternNonLmsBlueprintCount"
    ] == 5
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternNonLmsProductCount"
    ] == 4
    assert payload["adminOpsDashboard"][
        "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateEnterprisePatternTaxonomyAreaCount"
    ] == 9
    assert payload["adminOpsDashboard"]["productReadinessRuntimeStatusCode"] == 200
    assert payload["adminOpsDashboard"]["productReadinessRuntimeRequestCount"] == 1
    assert payload["adminOpsDashboard"]["productReadinessFailedCheckCount"] == 0
    assert payload["adminOpsDashboard"]["productReadinessFreshnessOpenIncidentCount"] == 0
    assert payload["adminOpsDashboard"]["adminOpsOpenIncidentCount"] == 0
    assert payload["adminOpsDashboardFreshness"]["freshnessStatus"] == "current"
    assert payload["adminOpsDashboardFreshness"]["sourceCount"] == 27
    assert payload["adminOpsDashboardFreshness"]["dashboardMatchesGeneratedHtml"] is True
    assert payload["productReadinessFreshnessIncidentExport"]["incidentCount"] == 0
    assert payload["productReadinessFreshnessIncidentResponseDrill"]["drillStatus"] == (
        "passed"
    )
    assert payload["productReadinessFreshnessResponseMetrics"][
        "responseMetricsStatus"
    ] == "slo_met"
    assert payload["productReadinessFreshnessResponseMetrics"]["ingestStatus"] == (
        "live_ingest_connected"
    )
    assert payload["productReadinessFreshnessResponseMetrics"]["breachCount"] == 0
    assert payload["productReadinessFreshnessResponseTrends"]["trendStatus"] == (
        "trend_ready_with_watch"
    )
    assert payload["productReadinessFreshnessResponseTrends"]["watchCount"] == 1
    assert payload["productReadinessFreshnessResponseSloDriftAlerts"][
        "alertStatus"
    ] == "alerts_configured_with_watch"
    assert payload["productReadinessFreshnessResponseSloDriftAlerts"][
        "routedAlertCount"
    ] == 1
    assert payload["productReadinessFreshnessResponseSloDriftAlertDrill"][
        "drillStatus"
    ] == "passed"
    assert payload["productReadinessFreshnessResponseSloDriftAlertDrill"][
        "passedCount"
    ] == 1
    assert payload["productReadinessFreshnessResponseSloDriftAlertCalibration"][
        "calibrationStatus"
    ] == "calibrated_with_watch"
    assert payload["productReadinessFreshnessResponseSloDriftAlertCalibration"][
        "calibratedCount"
    ] == 1
    assert payload["productReadinessFreshnessResponseSloDriftSuppressionPolicy"][
        "policyStatus"
    ] == "suppression_policy_codified"
    assert payload["productReadinessFreshnessResponseSloDriftSuppressionPolicy"][
        "activeRuleCount"
    ] == 1
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyDrill"
    ]["drillStatus"] == "passed"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyDrill"
    ]["passedCount"] == 4
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyEffectiveness"
    ]["monitorStatus"] == "effectiveness_monitored"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyEffectiveness"
    ]["suppressionEffectivenessPct"] == 100
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    ]["coverageStatus"] == "coverage_expanded"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    ]["coveredScenarioCount"] == 5
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegression"
    ]["regressionStatus"] == "regression_monitored"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegression"
    ]["passedRegressionCheckCount"] == 7
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSlo"
    ]["sloStatus"] == "coverage_slo_published"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSlo"
    ]["metObjectiveCount"] == 4
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernance"
    ]["releaseGovernanceStatus"] == "release_governance_attached"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernance"
    ]["attachedReleaseGateCount"] == 5
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrill"
    ]["drillStatus"] == "passed"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrill"
    ]["passedCount"] == 5
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEffectiveness"
    ]["monitorStatus"] == "effectiveness_monitored"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEffectiveness"
    ]["releaseGateEffectivenessPct"] == 100
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterprisePattern"
    ]["expansionStatus"] == "enterprise_pattern_expanded"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterprisePattern"
    ]["nonLmsBlueprintCount"] == 5
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoption"
    ]["adoptionStatus"] == "adoption_monitored"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoption"
    ]["adoptedSignalCount"] == 6
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoptionSlo"
    ]["sloStatus"] == "adoption_slo_published"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoptionSlo"
    ]["metObjectiveCount"] == 5
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoptionSloReleaseGovernance"
    ]["releaseGovernanceStatus"] == (
        "enterprise_adoption_slo_release_governance_attached"
    )
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoptionSloReleaseGovernance"
    ]["attachedReleaseGateCount"] == 5
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrill"
    ]["drillStatus"] == "passed"
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrill"
    ]["passedCount"] == 5
    assert payload["aiPlatformProductReadiness"]["readinessStatus"] == (
        "stakeholder_ready_with_followups"
    )
    assert payload["aiPlatformProductReadiness"]["requiredGateCount"] == 30
    assert payload["aiPlatformProductReadiness"]["passedRequiredGateCount"] == 30
    assert (
        payload["aiPlatformProductReadiness"][
            "productReadinessFreshnessResponseDrillAccepted"
        ]
        is True
    )
    assert payload["aiPlatformProductReadiness"]["actionRequiredCount"] == 0
    assert payload["aiPlatformProductReadiness"]["governanceResponseRunbookAccepted"] is True
    assert payload["aiPlatformProductReadiness"]["stakeholderVisibilityStatus"] == (
        "current_with_response_acceptance"
    )
    assert payload["coverageTaxonomy"]["moduleCount"] >= 13
    assert payload["coverageTaxonomy"]["missingRequiredAreas"] == []
    assert payload["coverageTaxonomy"]["runtimeStatusCounts"]["service_integrated"] == 14
    assert payload["coverageTaxonomy"]["runtimeStatusCounts"]["runtime_library"] == 0
    assert payload["coverageTaxonomy"]["runtimeStatusCounts"]["registry_only"] == 0
    assert payload["aiModuleCatalog"]["requiredSpectrumCoveredCount"] == 8
    assert payload["aiModuleCatalog"]["extendedModuleCount"] == 6
    assert payload["aiModuleCatalog"]["platformReadinessStatus"] == "runtime_ready"
    assert payload["aiCapabilityTaxonomy"]["requiredAreaCoveredCount"] == 13
    assert payload["aiCapabilityTaxonomy"]["modelAreaCount"] == 10
    assert payload["aiCapabilityTaxonomy"]["platformAreaCount"] == 5
    assert payload["runtimeRoadmap"]["runtimeGapCount"] == 0
    assert payload["runtimeRoadmap"]["p1Count"] == 0
    assert payload["runtimeRoadmap"]["runtimeReadyCount"] == 14
    assert (
        payload["coverageTaxonomy"]["lmsModuleCount"]
        == payload["coverageTaxonomy"]["moduleCount"]
    )
    assert (
        payload["coverageTaxonomy"]["enterpriseModuleCount"]
        == payload["coverageTaxonomy"]["moduleCount"]
    )
    assert payload["promotionReadiness"]["promotionCount"] == 4
    assert payload["promotionReadiness"]["readyCount"] == 4
    assert payload["promotionReadiness"]["blockedCount"] == 0
    assert payload["promotionReadiness"]["nonLmsCount"] == 2
    assert payload["promotionIntake"]["requestCount"] == 5
    assert payload["promotionIntake"]["readyCount"] == 3
    assert payload["promotionIntake"]["waitingCount"] == 2
    assert payload["promotionIntake"]["nonLmsCount"] == 4
    assert payload["dataContractCoverage"]["contractCount"] == 7
    assert payload["dataContractCoverage"]["designReadyRequestCount"] == 6
    assert payload["dataContractCoverage"]["missingDomainCount"] == 0
    assert payload["solutionBlueprints"]["requestCount"] == 6
    assert payload["solutionBlueprints"]["readyCount"] == 6
    assert payload["solutionBlueprints"]["waitingCount"] == 0
    assert payload["solutionBlueprints"]["nonLmsCount"] == 5
    assert payload["operatingCockpit"]["platformStatus"] == "attention_required"
    assert payload["operatingCockpit"]["deliveryStatus"] == "ready_work_available"
    assert payload["operatingCockpit"]["releaseStatus"] == "release_ready"
    assert payload["modelServingMetricsExport"]["exportStatus"] == "connected"
    assert payload["modelServingMetricsExport"]["metrics"]["requestCount"] == 3
    assert payload["llmProviderReadiness"]["readinessStatus"] == "contract_stub_ready"
    assert payload["llmProviderReadiness"]["activeProviderCount"] == 2
    assert payload["llmProviderReadiness"]["blockedProviderCount"] == 0
    assert payload["llmProviderRuntimeProbes"]["rolloutStatus"] == (
        "contract_stub_observable"
    )
    assert payload["llmProviderRuntimeProbes"]["blockedProviderCount"] == 0
    assert payload["llmProviderRuntimeProbes"]["costMonitoringProviderCount"] == 2
    assert payload["llmProviderAlertRouting"]["alertRoutingStatus"] == (
        "contract_stub_alerts_configured"
    )
    assert payload["llmProviderAlertRouting"]["routedProviderCount"] == 2
    assert payload["llmProviderSecretRotation"]["secretRotationStatus"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert payload["llmProviderSecretRotation"]["providerCount"] == 2
    assert payload["llmProviderSecretRotation"]["blockedProviderCount"] == 0
    assert payload["mediaPrivacyReview"]["reviewStatus"] == "approved"
    assert payload["mediaPrivacyReview"]["rawMediaRequestCount"] == 2
    assert payload["mediaPrivacyReview"]["controlGapCount"] == 0
    assert payload["governanceEvaluationOps"]["opsStatus"] == (
        "release_gate_observable"
    )
    assert payload["governanceEvaluationOps"]["assessmentCount"] == 3
    assert payload["governanceEvaluationOps"]["reviewRequiredCount"] == 1
    assert payload["governanceEvaluationOps"]["blockedCount"] == 1
    assert payload["governanceEvaluationOps"]["directIdentifierRejectionCount"] == 1
    assert payload["governanceEvaluationOps"]["secretValueRejectionCount"] == 1
    assert payload["governanceEvaluationIncidentExport"]["currentOpsStatus"] == (
        "release_gate_observable"
    )
    assert payload["governanceEvaluationIncidentExport"]["incidentCount"] == 0
    assert payload["governanceEvaluationIncidentExport"]["tenantSafe"] is True
    assert payload["governanceEvaluationIncidentResponseDrill"]["drillStatus"] == (
        "passed"
    )
    assert payload["governanceEvaluationIncidentResponseDrill"]["scenarioCount"] == 3
    assert payload["governanceEvaluationIncidentResponseDrill"]["tenantSafe"] is True
    assert payload["operatingCockpit"]["llmProviderOpsStatus"] == (
        "contract_stub_observable"
    )
    assert payload["operatingCockpit"]["llmProviderOps"]["providerCount"] == 2
    assert payload["operatingCockpit"]["llmProviderOps"]["alertRoutingStatus"] == (
        "contract_stub_alerts_configured"
    )
    assert payload["operatingCockpit"]["llmProviderOps"]["secretRotationStatus"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert payload["operatingCockpit"]["servingStatus"] == "healthy"
    assert payload["operatingCockpit"]["servingHealth"]["metricsConnected"] is True
    assert payload["operatingCockpit"]["servingAccessGovernanceStatus"] == (
        "pending_policy_apply"
    )
    assert payload["operatingCockpit"]["governanceEvaluationOpsStatus"] == (
        "release_gate_observable"
    )
    assert payload["operatingCockpit"]["mediaPrivacyReviewStatus"] == "approved"
    assert payload["operatingCockpit"]["mediaPrivacyWaitingCount"] == 0
    assert payload["operatingCockpit"]["actionCount"] == 23
    assert payload["deliveryBacklog"]["itemCount"] == 23
    assert payload["deliveryBacklog"]["readyToStartCount"] == 16
    assert payload["deliveryBacklog"]["monitoringCount"] == 3
    assert payload["deliveryState"]["transitionCount"] == 4
    assert payload["deliveryState"]["appliedCount"] == 4
    assert payload["deliveryState"]["inProgressCount"] == 1
    assert payload["deliveryState"]["acceptedCount"] == 3
    assert payload["deliveryState"]["missingActionCount"] == 0
    assert payload["deliverySla"]["itemCount"] == 23
    assert payload["deliverySla"]["dueSoonCount"] == 13
    assert payload["deliverySla"]["overdueCount"] == 0
    assert payload["deliveryOwnerViews"]["ownerCount"] == 6
    assert payload["deliveryOwnerViews"]["topOwnerAlias"] == "admin-ops"
    assert payload["deliveryOwnerViews"]["overloadedOwnerCount"] == 2
    assert payload["deliveryOwnerViews"]["incidentCount"] == 0
    assert payload["deliveryOwnerViews"]["openIncidentCount"] == 0
    assert payload["servingAccessReview"]["requestCount"] == 5
    assert payload["servingAccessReview"]["appliedCount"] == 2
    assert payload["servingAccessReview"]["readyForApplyCount"] == 1
    assert payload["servingAccessReview"]["needsApprovalCount"] == 1
    assert payload["servingAccessReview"]["blockedCount"] == 1
    assert payload["servingAccessPolicyPatchPlan"]["readyRequestCount"] == 1
    assert payload["servingAccessPolicyPatchPlan"]["plannedOperationCount"] == 1
    assert payload["servingAccessPolicyPatchPlan"]["humanReviewRequired"] is True
    assert payload["servingAccessApplyLedger"]["applicationCount"] == 1
    assert payload["servingAccessApplyLedger"]["readyToApplyCount"] == 1
    assert payload["servingAccessApplyLedger"]["checksumMismatchCount"] == 0
    assert payload["servingAccessPolicyApply"]["applyStatus"] == "ready_to_write"
    assert payload["servingAccessPolicyApply"]["readyApplicationCount"] == 1
    assert payload["servingAccessPolicyApply"]["activePolicyWouldChange"] is True
    assert payload["servingAccessPolicyReconciliation"]["pendingApplyCount"] == 1
    assert payload["servingAccessPolicyReconciliation"]["driftCount"] == 0
    assert payload["servingAccessIncidentExport"]["incidentCount"] == 1
    assert payload["servingAccessIncidentExport"]["watchCount"] == 1
    assert payload["servingAccessIncidentExport"]["tenantSafe"] is True


def test_cli_writes_promotion_readiness_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "promotion-readiness.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-promotion-readiness-report",
            "--promotion-readiness-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["promotionReadiness"]["readyCount"] == 4
    assert report["summary"]["promotion_count"] == 4
    assert report["action_queue"]["ready_to_activate"] == [
        "support-agent-assist-baseline-approved"
    ]


def test_cli_writes_promotion_intake_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "promotion-intake.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-promotion-intake-report",
            "--promotion-intake-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-16",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["promotionIntake"]["readyCount"] == 3
    assert report["summary"]["request_count"] == 5
    assert report["action_queue"]["ready_for_approval"] == [
        "support-agent-assist-active-request",
        "finance-document-intelligence-privacy-request",
        "operations-routing-rl-simulator-request",
    ]


def test_cli_writes_solution_blueprint_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "solution-blueprints.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-solution-blueprint-report",
            "--solution-blueprint-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-16",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["solutionBlueprints"]["requestCount"] == 6
    assert report["summary"]["non_lms_count"] == 5
    assert report["action_queue"]["ready_for_solution_design"] == [
        "enterprise-knowledge-assistant-discovery",
        "lms-at-risk-prediction-baseline",
        "support-sla-risk-discovery",
        "finance-document-intelligence-discovery",
        "operations-routing-optimization-simulator",
        "finance-payment-fraud-scoring-discovery",
    ]


def test_cli_writes_operating_cockpit_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "operating-cockpit.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-operating-cockpit-report",
            "--operating-cockpit-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["operatingCockpit"]["platformStatus"] == "attention_required"
    assert report["summary"]["release_status"] == "release_ready"
    assert report["summary"]["serving_status"] == "healthy"
    assert report["summary"]["serving_metrics_connected"] is True
    assert report["summary"]["serving_request_count"] == 3
    assert report["summary"]["serving_access_governance_status"] == "pending_policy_apply"
    assert report["summary"]["action_count"] == 23
    assert report["summary"]["media_privacy_review_status"] == "approved"
    assert report["summary"]["llm_provider_ops_status"] == "contract_stub_observable"
    assert report["summary"]["llm_provider_alert_routing_status"] == (
        "contract_stub_alerts_configured"
    )
    assert report["summary"]["llm_provider_secret_rotation_status"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert report["summary"]["governance_evaluation_ops_status"] == (
        "release_gate_observable"
    )
    assert report["summary"]["governance_evaluation_assessment_count"] == 3


def test_cli_writes_admin_ops_dashboard(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "admin-ops-dashboard.html"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-admin-ops-dashboard",
            "--admin-ops-dashboard-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    rendered = output_path.read_text(encoding="utf-8")
    assert payload["adminOpsDashboard"]["adminOpsItemCount"] == 7
    assert payload["adminOpsDashboard"]["llmProviderOpsStatus"] == (
        "contract_stub_observable"
    )
    assert payload["adminOpsDashboard"]["llmProviderAlertRoutingStatus"] == (
        "contract_stub_alerts_configured"
    )
    assert payload["adminOpsDashboard"]["llmProviderSecretRotationStatus"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert payload["adminOpsDashboard"]["governanceEvaluationOpsStatus"] == (
        "release_gate_observable"
    )
    assert payload["adminOpsDashboard"]["productReadinessFreshnessStatus"] == "current"
    assert payload["adminOpsDashboard"]["openIncidentCount"] == 0
    assert "AI Platform Admin/Ops Dashboard" in rendered
    assert "Governance Eval" in rendered
    assert "Product Readiness Freshness" in rendered
    assert "Product Readiness Freshness Incident Export" in rendered
    assert "Product Readiness Freshness Response Drill" in rendered
    assert "Serving Access Incident Export" in rendered
    assert "Governance Evaluation Incident Export" in rendered
    assert "Governance Evaluation Response Drill" in rendered


def test_cli_writes_ai_platform_product_readiness_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "ai-platform-product-readiness.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-ai-platform-product-readiness-report",
            "--ai-platform-product-readiness-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["aiPlatformProductReadiness"]["readinessStatus"] == (
        "stakeholder_ready_with_followups"
    )
    assert report["summary"]["governance_response_runbook_accepted"] is True
    assert (
        report["summary"]["product_readiness_freshness_response_drill_accepted"]
        is True
    )
    assert report["summary"]["passed_required_gate_count"] == 30
    assert report["summary"][
        "product_readiness_freshness_response_metrics_status"
    ] == "slo_met"
    assert report["summary"][
        "product_readiness_freshness_response_metrics_ingest_status"
    ] == "live_ingest_connected"
    assert report["summary"][
        "product_readiness_freshness_response_metrics_breach_count"
    ] == 0
    assert report["summary"][
        "product_readiness_freshness_response_trend_status"
    ] == "trend_ready_with_watch"
    assert report["summary"][
        "product_readiness_freshness_response_trend_watch_count"
    ] == 1
    assert report["summary"][
        "product_readiness_freshness_response_alert_status"
    ] == "alerts_configured_with_watch"
    assert report["summary"][
        "product_readiness_freshness_response_alert_routed_count"
    ] == 1
    assert report["summary"][
        "product_readiness_freshness_response_alert_drill_status"
    ] == "passed"
    assert report["summary"][
        "product_readiness_freshness_response_alert_drill_passed_count"
    ] == 1
    assert report["summary"][
        "product_readiness_freshness_response_alert_calibration_status"
    ] == "calibrated_with_watch"
    assert report["summary"][
        "product_readiness_freshness_response_alert_calibrated_count"
    ] == 1
    assert report["summary"][
        "product_readiness_freshness_response_alert_noisy_count"
    ] == 0
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_status"
    ] == "suppression_policy_codified"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_active_rule_count"
    ] == 1
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_drill_status"
    ] == "passed"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_drill_passed_count"
    ] == 4
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_effectiveness_status"
    ] == "effectiveness_monitored"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_effective_signal_count"
    ] == 4
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct"
    ] == 100
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct"
    ] == 100
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_coverage_status"
    ] == "coverage_expanded"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_coverage_pct"
    ] == 100
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_regression_status"
    ] == "regression_monitored"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_regression_check_count"
    ] == 7
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count"
    ] == 7
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status"
    ] == "coverage_slo_published"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count"
    ] == 4
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_objective_count"
    ] == 4
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_governance_status"
    ] == "release_governance_attached"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status"
    ] == "passed"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_scenario_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_passed_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness_status"
    ] == "effectiveness_monitored"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness_signal_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_effective_signal_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness_pct"
    ] == 100
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern_status"
    ] == "enterprise_pattern_expanded"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern_blueprint_count"
    ] == 6
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern_non_lms_blueprint_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern_non_lms_product_count"
    ] == 4
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern_taxonomy_area_count"
    ] == 9
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_status"
    ] == "adoption_monitored"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_signal_count"
    ] == 6
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adopted_signal_count"
    ] == 6
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_pct"
    ] == 100
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_slo_status"
    ] == "adoption_slo_published"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_slo_objective_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_slo_met_objective_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance_status"
    ] == "enterprise_adoption_slo_release_governance_attached"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance_attached_gate_count"
    ] == 5
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance_drill_status"
    ] == "passed"
    assert report["summary"][
        "product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance_drill_passed_count"
    ] == 5
    assert report["action_queue"]["blocked"] == []
    assert report["action_queue"]["tracked_followups"] == [
        "monitor_enterprise_release_gate_pattern_adoption_slo_release_governance_effectiveness"
    ]


def test_cli_writes_product_readiness_freshness_response_trend_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-trends.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-trend-report",
            "--product-readiness-freshness-response-trend-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["productReadinessFreshnessResponseTrends"]["trendStatus"] == (
        "trend_ready_with_watch"
    )
    assert report["summary"]["trend_status"] == "trend_ready_with_watch"
    assert report["summary"]["watch_count"] == 1
    assert report["action_queue"]["next_actions"] == [
        "configure_product_readiness_response_slo_drift_alerts"
    ]


def test_cli_writes_product_readiness_freshness_response_slo_drift_alert_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-alerts.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-alert-report",
            "--product-readiness-freshness-response-slo-drift-alert-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["productReadinessFreshnessResponseSloDriftAlerts"][
        "alertStatus"
    ] == "alerts_configured_with_watch"
    assert report["summary"]["alert_status"] == "alerts_configured_with_watch"
    assert report["summary"]["routed_alert_count"] == 1
    assert report["action_queue"]["next_actions"] == [
        "exercise_product_readiness_response_slo_drift_alert_drill"
    ]


def test_cli_writes_product_readiness_freshness_response_slo_drift_alert_drill_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-alert-drill.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-alert-drill-report",
            "--product-readiness-freshness-response-slo-drift-alert-drill-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["productReadinessFreshnessResponseSloDriftAlertDrill"][
        "drillStatus"
    ] == "passed"
    assert report["summary"]["drill_status"] == "passed"
    assert report["summary"]["passed_count"] == 1
    assert report["action_queue"]["next_actions"] == [
        "monitor_product_readiness_response_slo_drift_alert_calibration"
    ]


def test_cli_writes_product_readiness_freshness_response_slo_drift_alert_calibration_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-calibration.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-alert-calibration-report",
            "--product-readiness-freshness-response-slo-drift-alert-calibration-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["productReadinessFreshnessResponseSloDriftAlertCalibration"][
        "calibrationStatus"
    ] == "calibrated_with_watch"
    assert report["summary"]["calibration_status"] == "calibrated_with_watch"
    assert report["summary"]["calibrated_count"] == 1
    assert report["summary"]["noisy_alert_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "codify_product_readiness_response_slo_drift_alert_suppression_policy"
    ]


def test_cli_writes_product_readiness_freshness_response_slo_drift_suppression_policy_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-policy.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-report",
            "--product-readiness-freshness-response-slo-drift-suppression-policy-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["productReadinessFreshnessResponseSloDriftSuppressionPolicy"][
        "policyStatus"
    ] == "suppression_policy_codified"
    assert report["summary"]["policy_status"] == "suppression_policy_codified"
    assert report["summary"]["active_rule_count"] == 1
    assert report["summary"]["failed_rule_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "exercise_product_readiness_response_slo_drift_suppression_policy_drill"
    ]


def test_cli_writes_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-policy-drill.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-drill-report",
            "--product-readiness-freshness-response-slo-drift-suppression-policy-drill-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyDrill"
    ]["drillStatus"] == "passed"
    assert report["summary"]["drill_status"] == "passed"
    assert report["summary"]["scenario_count"] == 4
    assert report["summary"]["passed_count"] == 4
    assert report["summary"]["suppressed_count"] == 3
    assert report["summary"]["escalation_preserved_count"] == 1
    assert report["action_queue"]["next_actions"] == [
        "monitor_product_readiness_response_slo_drift_suppression_policy_effectiveness"
    ]


def test_cli_writes_product_readiness_suppression_policy_effectiveness_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-effectiveness.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-report",
            "--product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyEffectiveness"
    ]["monitorStatus"] == "effectiveness_monitored"
    assert report["summary"]["monitor_status"] == "effectiveness_monitored"
    assert report["summary"]["signal_count"] == 4
    assert report["summary"]["effective_signal_count"] == 4
    assert report["summary"]["suppression_effectiveness_pct"] == 100
    assert report["summary"]["escalation_preservation_pct"] == 100
    assert report["action_queue"]["next_actions"] == [
        "expand_product_readiness_response_slo_drift_suppression_policy_coverage"
    ]


def test_cli_writes_product_readiness_suppression_policy_coverage_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-coverage.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-report",
            "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    ]["coverageStatus"] == "coverage_expanded"
    assert report["summary"]["coverage_status"] == "coverage_expanded"
    assert report["summary"]["scenario_class_count"] == 5
    assert report["summary"]["covered_scenario_count"] == 5
    assert report["summary"]["active_policy_scenario_count"] == 1
    assert report["summary"]["explicit_non_watch_scenario_count"] == 4
    assert report["summary"]["coverage_pct"] == 100
    assert report["action_queue"]["next_actions"] == [
        "monitor_product_readiness_response_slo_drift_suppression_policy_coverage_regression"
    ]


def test_cli_writes_product_readiness_suppression_policy_regression_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-regression.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-report",
            "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegression"
    ]["regressionStatus"] == "regression_monitored"
    assert report["summary"]["regression_status"] == "regression_monitored"
    assert report["summary"]["regression_check_count"] == 7
    assert report["summary"]["passed_regression_check_count"] == 7
    assert report["summary"]["failed_regression_check_count"] == 0
    assert report["summary"]["coverage_pct"] == 100
    assert report["action_queue"]["next_actions"] == [
        "publish_product_readiness_response_slo_drift_suppression_policy_coverage_slo"
    ]


def test_cli_writes_product_readiness_suppression_policy_coverage_slo_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-coverage-slo.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-report",
            "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSlo"
    ]["sloStatus"] == "coverage_slo_published"
    assert report["summary"]["slo_status"] == "coverage_slo_published"
    assert report["summary"]["objective_count"] == 4
    assert report["summary"]["met_objective_count"] == 4
    assert report["summary"]["failed_objective_count"] == 0
    assert report["summary"]["coverage_pct"] == 100
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "attach_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_slo_to_release_governance"
    ]


def test_cli_writes_product_readiness_suppression_policy_coverage_release_governance_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-release-gate.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-governance-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-governance-report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernance"
    ]["releaseGovernanceStatus"] == "release_governance_attached"
    assert report["summary"]["release_governance_status"] == (
        "release_governance_attached"
    )
    assert report["summary"]["release_gate_count"] == 5
    assert report["summary"]["attached_release_gate_count"] == 5
    assert report["summary"]["failed_release_gate_count"] == 0
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "exercise_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_drill"
    ]


def test_cli_writes_product_readiness_suppression_policy_coverage_release_gate_drill_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-slo-drift-gate-drill.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-drill-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-drill-report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrill"
    ]["drillStatus"] == "passed"
    assert report["summary"]["drill_status"] == "passed"
    assert report["summary"]["release_governance_status"] == (
        "release_governance_attached"
    )
    assert report["summary"]["scenario_count"] == 5
    assert report["summary"]["passed_count"] == 5
    assert report["summary"]["failed_count"] == 0
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "monitor_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_effectiveness"
    ]


def test_cli_writes_product_readiness_suppression_policy_coverage_release_gate_effectiveness_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-gate-effectiveness.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-effectiveness-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-effectiveness-report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEffectiveness"
    ]["monitorStatus"] == "effectiveness_monitored"
    assert report["summary"]["monitor_status"] == "effectiveness_monitored"
    assert report["summary"]["drill_status"] == "passed"
    assert report["summary"]["release_governance_status"] == (
        "release_governance_attached"
    )
    assert report["summary"]["signal_count"] == 5
    assert report["summary"]["effective_signal_count"] == 5
    assert report["summary"]["release_gate_effectiveness_pct"] == 100
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "expand_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_pattern_to_enterprise_use_cases"
    ]


def test_cli_writes_product_readiness_release_gate_enterprise_pattern_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-gate-enterprise-pattern.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-pattern-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-pattern-"
                "report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
        "ReleaseGateEnterprisePattern"
    ]["expansionStatus"] == "enterprise_pattern_expanded"
    assert report["summary"]["expansion_status"] == "enterprise_pattern_expanded"
    assert report["summary"]["blueprint_count"] == 6
    assert report["summary"]["non_lms_blueprint_count"] == 5
    assert report["summary"]["non_lms_product_count"] == 4
    assert report["summary"]["taxonomy_area_count"] == 9
    assert report["summary"]["evaluation_gate_count"] == 36
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "monitor_enterprise_release_gate_pattern_adoption"
    ]


def test_cli_writes_product_readiness_release_gate_enterprise_adoption_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-response-gate-enterprise-adoption.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
        "ReleaseGateEnterpriseAdoption"
    ]["adoptionStatus"] == "adoption_monitored"
    assert report["summary"]["adoption_status"] == "adoption_monitored"
    assert report["summary"]["enterprise_pattern_status"] == (
        "enterprise_pattern_expanded"
    )
    assert report["summary"]["signal_count"] == 6
    assert report["summary"]["adopted_signal_count"] == 6
    assert report["summary"]["blocked_signal_count"] == 0
    assert report["summary"]["adoption_pct"] == 100
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "publish_enterprise_release_gate_pattern_adoption_slo"
    ]


def test_cli_writes_product_readiness_release_gate_enterprise_adoption_slo_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "enterprise-adoption-slo.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-slo-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-slo-report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload[
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
        "ReleaseGateEnterpriseAdoptionSlo"
    ]["sloStatus"] == "adoption_slo_published"
    assert report["summary"]["slo_status"] == "adoption_slo_published"
    assert report["summary"]["adoption_status"] == "adoption_monitored"
    assert report["summary"]["objective_count"] == 5
    assert report["summary"]["met_objective_count"] == 5
    assert report["summary"]["failed_objective_count"] == 0
    assert report["summary"]["adoption_pct"] == 100
    assert report["summary"]["target_adoption_pct"] == 100
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "attach_enterprise_release_gate_pattern_adoption_slo_to_release_governance"
    ]


def test_cli_writes_enterprise_adoption_slo_release_governance_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "enterprise-adoption-slo-release-governance.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-slo-release-governance-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-slo-release-governance-report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    payload_key = (
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
        "ReleaseGateEnterpriseAdoptionSloReleaseGovernance"
    )
    assert payload[payload_key]["releaseGovernanceStatus"] == (
        "enterprise_adoption_slo_release_governance_attached"
    )
    assert report["summary"]["release_governance_status"] == (
        "enterprise_adoption_slo_release_governance_attached"
    )
    assert report["summary"]["slo_status"] == "adoption_slo_published"
    assert report["summary"]["release_gate_count"] == 5
    assert report["summary"]["attached_release_gate_count"] == 5
    assert report["summary"]["failed_release_gate_count"] == 0
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "exercise_enterprise_release_gate_pattern_adoption_slo_release_governance_drill"
    ]


def test_cli_writes_enterprise_adoption_slo_release_governance_drill_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "enterprise-adoption-slo-release-governance-drill.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            (
                "--write-product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-slo-release-governance-drill-report"
            ),
            (
                "--product-readiness-freshness-response-slo-drift-"
                "suppression-policy-coverage-release-gate-enterprise-"
                "adoption-slo-release-governance-drill-report-path"
            ),
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    payload_key = (
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
        "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrill"
    )
    assert payload[payload_key]["drillStatus"] == "passed"
    assert payload[payload_key]["scenarioCount"] == 5
    assert payload[payload_key]["passedCount"] == 5
    assert report["summary"]["drill_status"] == "passed"
    assert report["summary"]["release_governance_status"] == (
        "enterprise_adoption_slo_release_governance_attached"
    )
    assert report["summary"]["scenario_count"] == 5
    assert report["summary"]["passed_count"] == 5
    assert report["summary"]["failed_count"] == 0
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["raw_identifier_count"] == 0
    assert report["action_queue"]["next_actions"] == [
        "monitor_enterprise_release_gate_pattern_adoption_slo_release_governance_"
        "effectiveness"
    ]


def test_cli_writes_ai_platform_product_readiness_freshness_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "ai-platform-product-readiness-freshness.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-ai-platform-product-readiness-freshness-report",
            "--ai-platform-product-readiness-freshness-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["aiPlatformProductReadinessFreshness"]["freshnessStatus"] == (
        "current"
    )
    assert report["summary"]["freshness_status"] == "current"
    assert report["summary"]["runtime_serving_request_count"] == 1
    assert report["summary"]["covered_required_spectrum_count"] == 8
    assert report["summary"]["failed_check_count"] == 0


def test_cli_writes_product_readiness_freshness_incident_export_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-freshness-incident-export.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-incident-export-report",
            "--product-readiness-freshness-incident-export-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["productReadinessFreshnessIncidentExport"]["incidentCount"] == 0
    assert report["report_id"] == "product-readiness-freshness-incident-export-v1"
    assert report["summary"]["freshness_status"] == "current"
    assert report["summary"]["tenant_safe"] is True
    assert report["action_queue"]["open"] == []


def test_cli_writes_product_readiness_freshness_incident_response_drill_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "product-readiness-freshness-response-drill.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-product-readiness-freshness-incident-response-drill-report",
            "--product-readiness-freshness-incident-response-drill-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["productReadinessFreshnessIncidentResponseDrill"][
        "drillStatus"
    ] == "passed"
    assert (
        report["report_id"]
        == "product-readiness-freshness-incident-response-drill-v1"
    )
    assert report["summary"]["scenario_count"] == 5
    assert report["summary"]["tenant_safe"] is True
    assert report["summary"]["failed_count"] == 0


def test_cli_writes_model_serving_metrics_export_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "model-serving-metrics-export.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-model-serving-metrics-export-report",
            "--model-serving-metrics-export-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["modelServingMetricsExport"]["metrics"]["requestCount"] == 3
    assert report["summary"]["export_status"] == "connected"
    assert report["summary"]["audit_record_count"] == 3


def test_cli_writes_llm_provider_readiness_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "llm-provider-readiness.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-llm-provider-readiness-report",
            "--llm-provider-readiness-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["llmProviderReadiness"]["readinessStatus"] == "contract_stub_ready"
    assert report["summary"]["contract_stub_count"] == 2
    assert report["summary"]["blocked_provider_count"] == 0


def test_cli_writes_llm_provider_runtime_probe_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "llm-provider-runtime-probes.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-llm-provider-runtime-probe-report",
            "--llm-provider-runtime-probe-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["llmProviderRuntimeProbes"]["rolloutStatus"] == (
        "contract_stub_observable"
    )
    assert report["summary"]["contract_stub_count"] == 2
    assert report["summary"]["blocked_provider_count"] == 0


def test_cli_writes_llm_provider_alert_routing_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "llm-provider-alert-routing.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-llm-provider-alert-routing-report",
            "--llm-provider-alert-routing-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["llmProviderAlertRouting"]["alertRoutingStatus"] == (
        "contract_stub_alerts_configured"
    )
    assert report["summary"]["routed_provider_count"] == 2
    assert report["summary"]["tenant_safe"] is True


def test_cli_writes_llm_provider_secret_rotation_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "llm-provider-secret-rotation.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-llm-provider-secret-rotation-report",
            "--llm-provider-secret-rotation-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["llmProviderSecretRotation"]["secretRotationStatus"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert report["summary"]["secret_rotation_status"] == (
        "contract_stub_rotation_controls_ready"
    )
    assert report["summary"]["plaintext_secret_count"] == 0


def test_cli_writes_admin_ops_dashboard_freshness_manifest(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    dashboard_path = tmp_path / "admin-ops-dashboard.html"
    manifest_path = tmp_path / "admin-ops-dashboard-freshness.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-admin-ops-dashboard",
            "--admin-ops-dashboard-path",
            str(dashboard_path),
            "--write-admin-ops-dashboard-freshness-manifest",
            "--admin-ops-dashboard-freshness-manifest-path",
            str(manifest_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    manifest = load_yaml(manifest_path)
    assert payload["adminOpsDashboardFreshness"]["freshnessStatus"] == "current"
    assert manifest["summary"]["freshness_status"] == "current"
    assert manifest["summary"]["dashboard_matches_generated_html"] is True
    assert manifest["summary"]["source_count"] == 27


def test_cli_writes_data_contract_coverage_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "data-contract-coverage.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-data-contract-coverage-report",
            "--data-contract-coverage-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["dataContractCoverage"]["contractCount"] == 7
    assert report["summary"]["mapped_domain_count"] == 16
    assert report["action_queue"]["missing_contract"] == []


def test_cli_writes_delivery_backlog_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "delivery-backlog.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-delivery-backlog-report",
            "--delivery-backlog-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["deliveryBacklog"]["itemCount"] == 23
    assert report["summary"]["ready_to_start_count"] == 16
    assert report["by_source"]["solution_blueprint"] == 6
    assert report["by_source"]["governance_evaluation_ops"] == 1
    assert report["by_source"]["governance_evaluation_response_drill"] == 1
    assert report["by_source"]["product_readiness_freshness_response_drill"] == 1
    assert report["by_source"]["llm_provider_ops"] == 1
    assert "media_privacy_review" not in report["by_source"]
    assert "serving_health" not in report["by_source"]
    assert report["by_source"]["serving_access_governance"] == 1
    assert report["by_status"]["accepted"] == 3
    assert report["by_status"]["in_progress"] == 1


def test_cli_writes_delivery_state_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "delivery-state.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-delivery-state-report",
            "--delivery-state-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["deliveryState"]["transitionCount"] == 4
    assert payload["deliveryState"]["appliedCount"] == 4
    assert report["summary"]["in_progress_count"] == 1
    assert report["summary"]["accepted_count"] == 3
    applied_status_by_transition = {
        item["transition_id"]: item["applied_status"] for item in report["items"]
    }
    assert (
        applied_status_by_transition["serving-access-policy-applier-started-20260617"]
        == "in_progress"
    )
    assert (
        applied_status_by_transition[
            "governance-evaluation-alert-drill-accepted-20260617"
        ]
        == "accepted"
    )
    assert (
        applied_status_by_transition[
            "governance-evaluation-response-runbook-drill-accepted-20260617"
        ]
        == "accepted"
    )


def test_cli_writes_delivery_sla_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "delivery-sla.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-delivery-sla-report",
            "--delivery-sla-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["deliverySla"]["itemCount"] == 23
    assert report["summary"]["due_soon_count"] == 13
    assert report["summary"]["on_track_count"] == 7
    assert report["summary"]["missing_owner_alias_count"] == 0


def test_cli_writes_delivery_owner_views_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "delivery-owner-views.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-delivery-owner-views-report",
            "--delivery-owner-views-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["deliveryOwnerViews"]["ownerCount"] == 6
    assert report["summary"]["top_owner_alias"] == "admin-ops"
    assert report["summary"]["overloaded_owner_count"] == 2
    assert report["summary"]["incident_count"] == 0
    assert report["summary"]["open_incident_count"] == 0


def test_cli_writes_runtime_roadmap_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "runtime-roadmap.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-runtime-roadmap-report",
            "--runtime-roadmap-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["runtimeRoadmap"]["runtimeGapCount"] == 0
    assert report["summary"]["p1_count"] == 0
    assert report["summary"]["runtime_gap_count"] == 0
    assert report["summary"]["runtime_ready_count"] == 14
    assert report["summary"]["runtime_library_count"] == 0
    assert report["summary"]["registry_only_count"] == 0
    assert report["summary"]["first_runtime_candidate_ids"] == []


def test_cli_writes_media_privacy_review_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "media-privacy-review.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-media-privacy-review-report",
            "--media-privacy-review-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["mediaPrivacyReview"]["reviewStatus"] == "approved"
    assert payload["mediaPrivacyReview"]["waitingForControlsCount"] == 0
    assert report["summary"]["raw_media_request_count"] == 2
    assert report["action_queue"]["waiting_for_controls"] == []


def test_cli_writes_governance_evaluation_ops_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "governance-evaluation-service.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-governance-evaluation-ops-report",
            "--governance-evaluation-ops-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["governanceEvaluationOps"]["opsStatus"] == (
        "release_gate_observable"
    )
    assert payload["governanceEvaluationOps"]["directIdentifierRejectionCount"] == 1
    assert report["summary"]["ops_status"] == "release_gate_observable"
    assert report["summary"]["assessment_count"] == 3
    assert report["summary"]["secret_value_rejection_count"] == 1


def test_cli_writes_governance_evaluation_incident_export_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "governance-evaluation-incident-export.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-governance-evaluation-incident-export-report",
            "--governance-evaluation-incident-export-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["governanceEvaluationIncidentExport"]["incidentCount"] == 0
    assert report["report_id"] == "governance-evaluation-incident-export-v1"
    assert report["summary"]["current_ops_status"] == "release_gate_observable"
    assert report["summary"]["tenant_safe"] is True
    assert report["action_queue"]["open"] == []


def test_cli_writes_governance_evaluation_incident_response_drill_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "governance-evaluation-response-drill.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-governance-evaluation-incident-response-drill-report",
            "--governance-evaluation-incident-response-drill-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["governanceEvaluationIncidentResponseDrill"]["drillStatus"] == (
        "passed"
    )
    assert report["report_id"] == (
        "governance-evaluation-incident-response-drill-v1"
    )
    assert report["summary"]["scenario_count"] == 3
    assert report["summary"]["failed_count"] == 0
    assert report["summary"]["tenant_safe"] is True


def test_cli_writes_ai_module_catalog_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "ai-module-catalog.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-ai-module-catalog-report",
            "--ai-module-catalog-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["aiModuleCatalog"]["moduleCount"] == 14
    assert report["summary"]["required_spectrum_covered_count"] == 8
    assert report["summary"]["platform_readiness_status"] == "runtime_ready"


def test_cli_writes_ai_capability_taxonomy_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "ai-capability-taxonomy.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-ai-capability-taxonomy-report",
            "--ai-capability-taxonomy-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["aiCapabilityTaxonomy"]["areaCount"] == 15
    assert report["summary"]["required_area_covered_count"] == 13
    assert report["summary"]["platform_area_count"] == 5


def test_cli_writes_serving_access_review_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "serving-access-review.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-serving-access-review-report",
            "--serving-access-review-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["servingAccessReview"]["requestCount"] == 5
    assert report["summary"]["blocked_count"] == 1
    assert report["action_queue"]["ready_for_apply"] == ["lms-sequence-risk-sandbox-tenant"]


def test_cli_writes_serving_access_policy_patch_plan(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "serving-access-policy-patch-plan.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-serving-access-policy-patch-plan",
            "--serving-access-policy-patch-plan-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["servingAccessPolicyPatchPlan"]["plannedOperationCount"] == 1
    assert report["summary"]["ready_request_count"] == 1
    assert report["operations"][0]["request_id"] == "lms-sequence-risk-sandbox-tenant"


def test_cli_writes_serving_access_apply_ledger_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "serving-access-apply-ledger.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-serving-access-apply-ledger-report",
            "--serving-access-apply-ledger-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["servingAccessApplyLedger"]["readyToApplyCount"] == 1
    assert report["summary"]["application_count"] == 1
    assert report["action_queue"]["ready_to_apply"] == [
        "lms-sequence-risk-sandbox-tenant-apply-20260617"
    ]


def test_cli_writes_serving_access_policy_apply_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "serving-access-policy-apply.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-serving-access-policy-apply-report",
            "--serving-access-policy-apply-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["servingAccessPolicyApply"]["applyStatus"] == "ready_to_write"
    assert report["summary"]["ready_application_count"] == 1
    assert report["summary"]["active_policy_would_change"] is True


def test_cli_writes_serving_access_policy_reconciliation_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "serving-access-policy-reconciliation.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-serving-access-policy-reconciliation-report",
            "--serving-access-policy-reconciliation-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["servingAccessPolicyReconciliation"]["pendingApplyCount"] == 1
    assert report["summary"]["pending_apply_count"] == 1
    assert report["action_queue"]["pending_apply"] == [
        "lms-sequence-risk-sandbox-tenant-apply-20260617"
    ]


def test_cli_writes_serving_access_incident_export_report(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "serving-access-incident-export.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ai-platform",
            "--ai-root",
            str(ai_root),
            "--write-serving-access-incident-export-report",
            "--serving-access-incident-export-report-path",
            str(output_path),
            "--generated-at",
            "2026-06-17",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    report = load_yaml(output_path)
    assert payload["servingAccessIncidentExport"]["incidentCount"] == 1
    assert report["summary"]["incident_count"] == 1
    assert report["summary"]["tenant_safe"] is True
    assert report["action_queue"]["pending_policy_apply"] == [
        report["incidents"][0]["incident_id"]
    ]
