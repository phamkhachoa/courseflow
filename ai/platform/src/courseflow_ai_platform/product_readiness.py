from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.admin_ops_dashboard import (
    AdminOpsDashboardFreshnessManifest,
    build_admin_ops_dashboard_freshness_manifest,
)
from courseflow_ai_platform.delivery_state_ledger import (
    DeliveryStateReport,
    build_delivery_state_report,
)
from courseflow_ai_platform.governance_evaluation_incidents import (
    GovernanceEvaluationIncidentExport,
    build_governance_evaluation_incident_export,
)
from courseflow_ai_platform.governance_evaluation_response_drill import (
    GovernanceEvaluationIncidentResponseDrillReport,
    build_governance_evaluation_incident_response_drill_report,
)
from courseflow_ai_platform.model_serving import ModelServingMetricsSnapshot
from courseflow_ai_platform.operating_cockpit import (
    OperatingCockpitReport,
    build_operating_cockpit_report,
)
from courseflow_ai_platform.product_readiness_freshness_incidents import (
    ProductReadinessFreshnessIncidentExport,
    build_product_readiness_freshness_incident_export,
)
from courseflow_ai_platform.product_readiness_freshness_response_drill import (
    ProductReadinessFreshnessIncidentResponseDrillReport,
    build_product_readiness_freshness_incident_response_drill_report,
)
from courseflow_ai_platform.product_readiness_freshness_response_metrics import (
    ProductReadinessFreshnessResponseMetricsReport,
    build_product_readiness_freshness_response_metrics_report,
)
from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alert_drill import (
    EXERCISE_DRIFT_ALERT_DRILL_ACTION,
    ProductReadinessFreshnessResponseSloDriftAlertDrillReport,
    build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts,
)
from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alerts import (
    ProductReadinessFreshnessResponseSloDriftAlertReport,
    build_product_readiness_freshness_response_slo_drift_alert_report_from_trends,
)
from courseflow_ai_platform.product_readiness_freshness_response_trends import (
    ProductReadinessFreshnessResponseTrendReport,
    build_product_readiness_freshness_response_trend_report_from_metrics,
)
from courseflow_ai_platform.registry import (
    RegistryValidationError,
    load_yaml,
    require_str,
)
from courseflow_ai_platform.serving_access_incidents import (
    ServingAccessIncidentExport,
    build_serving_access_incident_export,
)
from courseflow_ai_platform.solution_blueprint import (
    build_solution_blueprint_report,
)

from .product_readiness_freshness_response_slo_drift_alert_calibration import (
    CODIFY_ALERT_SUPPRESSION_POLICY_ACTION,
    MONITOR_ALERT_CALIBRATION_ACTION,
    ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport,
    build_product_readiness_freshness_response_slo_drift_alert_calibration_report_from_drill,
)
from .product_readiness_freshness_response_slo_drift_alert_suppression_policy import (
    EXERCISE_SUPPRESSION_POLICY_DRILL_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage import (
    MONITOR_SUPPRESSION_POLICY_COVERAGE_REGRESSION_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport,
    build_suppression_policy_coverage_report_from_reports,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression import (
    PUBLISH_SUPPRESSION_POLICY_COVERAGE_SLO_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport,
    build_suppression_policy_coverage_regression_report_from_coverage,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo import (
    ATTACH_SUPPRESSION_POLICY_COVERAGE_SLO_TO_RELEASE_GOVERNANCE_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport,
    build_suppression_policy_coverage_slo_report_from_regression,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_drill import (
    MONITOR_SUPPRESSION_POLICY_EFFECTIVENESS_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report_from_policy,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness import (
    EXPAND_SUPPRESSION_POLICY_COVERAGE_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport,
    build_suppression_policy_effectiveness_report_from_drill,
)

REPORT_ID = "ai-platform-product-readiness-v1"
PRODUCT_ID = "ai-platform"
SUPPRESSION_POLICY_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_alert_suppression_policy"
)
COVERAGE_RELEASE_GOVERNANCE_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance"
)
COVERAGE_RELEASE_GATE_DRILL_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_drill"
)
COVERAGE_RELEASE_GATE_EFFECTIVENESS_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_effectiveness"
)
COVERAGE_RELEASE_GATE_ENTERPRISE_PATTERN_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_pattern"
)
COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_adoption"
)
COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_adoption_slo"
)
COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance"
)
COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_MODULE = (
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill"
)
GOVERNANCE_RESPONSE_RUNBOOK_ACTION_ID = (
    "governance_evaluation_response_drill:"
    "accept_governance_evaluation_incident_response_runbook_drill:"
    "governance-evaluation-incident-response-drill-v1"
)
PRODUCT_READINESS_FRESHNESS_RESPONSE_DRILL_ACTION_ID = (
    "product_readiness_freshness_response_drill:"
    "accept_product_readiness_freshness_incident_response_drill_state:"
    "product-readiness-freshness-incident-response-drill-v1"
)
build_suppression_policy_drill_from_policy = (
    build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report_from_policy
)
build_suppression_policy_effectiveness_from_drill = (
    build_suppression_policy_effectiveness_report_from_drill
)
build_suppression_policy_coverage_from_reports = (
    build_suppression_policy_coverage_report_from_reports
)
build_suppression_policy_coverage_regression_from_coverage = (
    build_suppression_policy_coverage_regression_report_from_coverage
)
build_suppression_policy_coverage_slo_from_regression = (
    build_suppression_policy_coverage_slo_report_from_regression
)
coverage_release_governance_module = import_module(
    COVERAGE_RELEASE_GOVERNANCE_MODULE
)
coverage_release_gate_drill_module = import_module(
    COVERAGE_RELEASE_GATE_DRILL_MODULE
)
coverage_release_gate_effectiveness_module = import_module(
    COVERAGE_RELEASE_GATE_EFFECTIVENESS_MODULE
)
coverage_release_gate_enterprise_pattern_module = import_module(
    COVERAGE_RELEASE_GATE_ENTERPRISE_PATTERN_MODULE
)
coverage_release_gate_enterprise_adoption_module = import_module(
    COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_MODULE
)
coverage_release_gate_enterprise_adoption_slo_module = import_module(
    COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_MODULE
)
coverage_release_gate_enterprise_adoption_slo_release_governance_module = (
    import_module(
        COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_MODULE
    )
)
coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module = (
    import_module(
        COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_MODULE
    )
)
_RELEASE_DRILL_ACTION_ATTR = (
    "EXERCISE_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_DRILL_ACTION"
)
_RELEASE_GOVERNANCE_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernanceReport"
)
_RELEASE_GOVERNANCE_BUILDER_ATTR = (
    "build_suppression_policy_coverage_release_governance_report_from_slo"
)
_RELEASE_GATE_EFFECTIVENESS_ACTION_ATTR = (
    "MONITOR_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_EFFECTIVENESS_ACTION"
)
_RELEASE_GATE_DRILL_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrillReport"
)
_RELEASE_GATE_DRILL_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_drill_report_from_governance"
)
_RELEASE_GATE_PATTERN_ACTION_ATTR = (
    "EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION"
)
_RELEASE_GATE_EFFECTIVENESS_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEffectivenessReport"
)
_RELEASE_GATE_EFFECTIVENESS_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_report_from_drill"
)
_ENTERPRISE_PATTERN_ACTION_ATTR = (
    "MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION"
)
_ENTERPRISE_PATTERN_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterprisePatternReport"
)
_ENTERPRISE_PATTERN_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_report_from_reports"
)
_ENTERPRISE_ADOPTION_ACTION_ATTR = (
    "PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION"
)
_ENTERPRISE_ADOPTION_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionReport"
)
_ENTERPRISE_ADOPTION_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_report_from_pattern"
)
_ENTERPRISE_ADOPTION_SLO_ACTION_ATTR = (
    "ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION"
)
_ENTERPRISE_ADOPTION_SLO_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReport"
)
_ENTERPRISE_ADOPTION_SLO_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_report_from_adoption"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_ACTION_ATTR = (
    "EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_"
    "RELEASE_GOVERNANCE_DRILL_ACTION"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_report_from_slo"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION_ATTR = (
    "MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_"
    "EFFECTIVENESS_ACTION"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_"
    "report_from_governance"
)
EXERCISE_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_DRILL_ACTION = getattr(
    coverage_release_governance_module,
    _RELEASE_DRILL_ACTION_ATTR,
)
MONITOR_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_EFFECTIVENESS_ACTION = getattr(
    coverage_release_gate_drill_module,
    _RELEASE_GATE_EFFECTIVENESS_ACTION_ATTR,
)
CoverageReleaseGovernanceReport = getattr(
    coverage_release_governance_module,
    _RELEASE_GOVERNANCE_REPORT_ATTR,
)
CoverageReleaseGateDrillReport = getattr(
    coverage_release_gate_drill_module,
    _RELEASE_GATE_DRILL_REPORT_ATTR,
)
CoverageReleaseGateEffectivenessReport = getattr(
    coverage_release_gate_effectiveness_module,
    _RELEASE_GATE_EFFECTIVENESS_REPORT_ATTR,
)
CoverageReleaseGateEnterprisePatternReport = getattr(
    coverage_release_gate_enterprise_pattern_module,
    _ENTERPRISE_PATTERN_REPORT_ATTR,
)
CoverageReleaseGateEnterpriseAdoptionReport = getattr(
    coverage_release_gate_enterprise_adoption_module,
    _ENTERPRISE_ADOPTION_REPORT_ATTR,
)
CoverageReleaseGateEnterpriseAdoptionSloReport = getattr(
    coverage_release_gate_enterprise_adoption_slo_module,
    _ENTERPRISE_ADOPTION_SLO_REPORT_ATTR,
)
CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_REPORT_ATTR,
)
CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_REPORT_ATTR,
)
build_suppression_policy_coverage_release_governance_from_slo = getattr(
    coverage_release_governance_module,
    _RELEASE_GOVERNANCE_BUILDER_ATTR,
)
build_suppression_policy_coverage_release_gate_drill_from_governance = getattr(
    coverage_release_gate_drill_module,
    _RELEASE_GATE_DRILL_BUILDER_ATTR,
)
EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION = getattr(
    coverage_release_gate_effectiveness_module,
    _RELEASE_GATE_PATTERN_ACTION_ATTR,
)
build_suppression_policy_coverage_release_gate_effectiveness_from_drill = getattr(
    coverage_release_gate_effectiveness_module,
    _RELEASE_GATE_EFFECTIVENESS_BUILDER_ATTR,
)
MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION = getattr(
    coverage_release_gate_enterprise_pattern_module,
    _ENTERPRISE_PATTERN_ACTION_ATTR,
)
build_suppression_policy_coverage_release_gate_enterprise_pattern_from_reports = getattr(
    coverage_release_gate_enterprise_pattern_module,
    _ENTERPRISE_PATTERN_BUILDER_ATTR,
)
PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION = getattr(
    coverage_release_gate_enterprise_adoption_module,
    _ENTERPRISE_ADOPTION_ACTION_ATTR,
)
build_suppression_policy_coverage_release_gate_enterprise_adoption_from_pattern = getattr(
    coverage_release_gate_enterprise_adoption_module,
    _ENTERPRISE_ADOPTION_BUILDER_ATTR,
)
ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION = getattr(
    coverage_release_gate_enterprise_adoption_slo_module,
    _ENTERPRISE_ADOPTION_SLO_ACTION_ATTR,
)
build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_from_adoption = getattr(
    coverage_release_gate_enterprise_adoption_slo_module,
    _ENTERPRISE_ADOPTION_SLO_BUILDER_ATTR,
)
EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_ACTION_ATTR,
)
build_enterprise_adoption_slo_release_governance_from_slo = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_BUILDER_ATTR,
)
MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_EFFECTIVENESS_ACTION = (
    getattr(
        coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module,
        _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION_ATTR,
    )
)
build_enterprise_adoption_slo_release_governance_drill_from_governance = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_BUILDER_ATTR,
)


@dataclass(frozen=True, slots=True)
class ProductReadinessGate:
    gate_id: str
    title: str
    owner_role: str
    required: bool
    gate_status: str
    reason: str
    evidence_refs: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.gate_status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidenceRefs": list(self.evidence_refs),
            "gateId": self.gate_id,
            "ownerRole": self.owner_role,
            "reason": self.reason,
            "required": self.required,
            "status": self.gate_status,
            "title": self.title,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "title": self.title,
            "owner_role": self.owner_role,
            "required": self.required,
            "status": self.gate_status,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFollowup:
    followup_id: str
    title: str
    owner_role: str
    priority: str
    followup_status: str
    reason: str
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidenceRefs": list(self.evidence_refs),
            "followupId": self.followup_id,
            "ownerRole": self.owner_role,
            "priority": self.priority,
            "reason": self.reason,
            "status": self.followup_status,
            "title": self.title,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "followup_id": self.followup_id,
            "title": self.title,
            "owner_role": self.owner_role,
            "priority": self.priority,
            "status": self.followup_status,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class AiPlatformProductReadinessReport:
    product_id: str
    product_name: str
    readiness_status: str
    stakeholder_visibility_status: str
    platform_status: str
    delivery_status: str
    release_status: str
    serving_status: str
    serving_metrics_connected: bool
    serving_request_count: int
    serving_audit_record_count: int
    serving_error_count: int
    serving_audit_failure_count: int
    dashboard_freshness_status: str
    governance_response_drill_status: str
    product_readiness_freshness_response_drill_status: str
    product_readiness_freshness_response_metrics_status: str
    product_readiness_freshness_response_metrics_ingest_status: str
    product_readiness_freshness_response_trend_status: str
    product_readiness_freshness_response_alert_status: str
    product_readiness_freshness_response_alert_drill_status: str
    product_readiness_freshness_response_alert_calibration_status: str
    product_readiness_freshness_response_alert_suppression_policy_status: str
    product_readiness_freshness_response_alert_suppression_policy_drill_status: str
    product_readiness_freshness_response_alert_suppression_policy_effectiveness_status: str
    product_readiness_freshness_response_alert_suppression_policy_coverage_status: str
    product_readiness_freshness_response_alert_suppression_policy_regression_status: str
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status: str
    product_readiness_freshness_response_alert_suppression_policy_release_governance_status: str
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status: str
    release_gate_effectiveness_status: str
    release_gate_enterprise_pattern_status: str
    release_gate_enterprise_adoption_status: str
    release_gate_enterprise_adoption_slo_status: str
    release_gate_enterprise_adoption_slo_release_governance_status: str
    release_gate_enterprise_adoption_slo_release_governance_drill_status: str
    governance_response_runbook_accepted: bool
    product_readiness_freshness_response_drill_accepted: bool
    product_readiness_freshness_response_metrics_breach_count: int
    product_readiness_freshness_response_metrics_live_observation_count: int
    product_readiness_freshness_response_trend_watch_count: int
    product_readiness_freshness_response_alert_count: int
    product_readiness_freshness_response_alert_routed_count: int
    product_readiness_freshness_response_alert_drill_scenario_count: int
    product_readiness_freshness_response_alert_drill_passed_count: int
    product_readiness_freshness_response_alert_calibrated_count: int
    product_readiness_freshness_response_alert_noisy_count: int
    product_readiness_freshness_response_alert_suppression_rule_count: int
    product_readiness_freshness_response_alert_suppression_active_rule_count: int
    product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count: int
    product_readiness_freshness_response_alert_suppression_policy_drill_passed_count: int
    product_readiness_freshness_response_alert_suppression_policy_effective_signal_count: int
    product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct: int
    product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count: int
    product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_pct: int
    product_readiness_freshness_response_alert_suppression_policy_regression_check_count: int
    product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count: int
    product_readiness_freshness_response_alert_suppression_policy_release_gate_count: int
    product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count: int
    release_gate_drill_scenario_count: int
    release_gate_drill_passed_count: int
    release_gate_effectiveness_signal_count: int
    release_gate_effective_signal_count: int
    release_gate_effectiveness_pct: int
    release_gate_enterprise_pattern_blueprint_count: int
    release_gate_enterprise_pattern_non_lms_blueprint_count: int
    release_gate_enterprise_pattern_non_lms_product_count: int
    release_gate_enterprise_pattern_taxonomy_area_count: int
    release_gate_enterprise_adoption_signal_count: int
    release_gate_enterprise_adopted_signal_count: int
    release_gate_enterprise_adoption_pct: int
    release_gate_enterprise_adoption_slo_objective_count: int
    release_gate_enterprise_adoption_slo_met_objective_count: int
    release_gate_enterprise_adoption_slo_target_pct: int
    release_gate_enterprise_adoption_slo_review_cadence_days: int
    release_gate_enterprise_adoption_slo_release_governance_gate_count: int
    release_gate_enterprise_adoption_slo_release_governance_attached_gate_count: int
    release_gate_enterprise_adoption_slo_release_governance_failed_gate_count: int
    release_gate_enterprise_adoption_slo_release_governance_review_cadence_days: int
    release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count: int
    release_gate_enterprise_adoption_slo_release_governance_drill_passed_count: int
    tenant_safe: bool
    open_incident_count: int
    watch_incident_count: int
    required_gate_count: int
    passed_required_gate_count: int
    failed_required_gate_count: int
    followup_count: int
    action_required_count: int
    gates: tuple[ProductReadinessGate, ...]
    followups: tuple[ProductReadinessFollowup, ...]
    source_reports: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionRequiredCount": self.action_required_count,
            "dashboardFreshnessStatus": self.dashboard_freshness_status,
            "deliveryStatus": self.delivery_status,
            "failedRequiredGateCount": self.failed_required_gate_count,
            "followupCount": self.followup_count,
            "followups": [followup.to_dict() for followup in self.followups],
            "gates": [gate.to_dict() for gate in self.gates],
            "governanceResponseDrillStatus": self.governance_response_drill_status,
            "governanceResponseRunbookAccepted": (
                self.governance_response_runbook_accepted
            ),
            "productReadinessFreshnessResponseDrillStatus": (
                self.product_readiness_freshness_response_drill_status
            ),
            "productReadinessFreshnessResponseMetricsStatus": (
                self.product_readiness_freshness_response_metrics_status
            ),
            "productReadinessFreshnessResponseMetricsIngestStatus": (
                self.product_readiness_freshness_response_metrics_ingest_status
            ),
            "productReadinessFreshnessResponseTrendStatus": (
                self.product_readiness_freshness_response_trend_status
            ),
            "productReadinessFreshnessResponseAlertStatus": (
                self.product_readiness_freshness_response_alert_status
            ),
            "productReadinessFreshnessResponseAlertDrillStatus": (
                self.product_readiness_freshness_response_alert_drill_status
            ),
            "productReadinessFreshnessResponseAlertCalibrationStatus": (
                self.product_readiness_freshness_response_alert_calibration_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_drill_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyEffectivenessStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_effectiveness_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_regression_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGovernanceStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_release_governance_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEffectivenessStatus"
            ): (
                self.release_gate_effectiveness_status
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterprisePatternStatus"
            ): (
                self.release_gate_enterprise_pattern_status
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionStatus"
            ): (
                self.release_gate_enterprise_adoption_status
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloStatus"
            ): (
                self.release_gate_enterprise_adoption_slo_status
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceStatus"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_status
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillStatus"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_drill_status
            ),
            "productReadinessFreshnessResponseDrillAccepted": (
                self.product_readiness_freshness_response_drill_accepted
            ),
            "productReadinessFreshnessResponseMetricsBreachCount": (
                self.product_readiness_freshness_response_metrics_breach_count
            ),
            "productReadinessFreshnessResponseMetricsLiveObservationCount": (
                self.product_readiness_freshness_response_metrics_live_observation_count
            ),
            "productReadinessFreshnessResponseTrendWatchCount": (
                self.product_readiness_freshness_response_trend_watch_count
            ),
            "productReadinessFreshnessResponseAlertCount": (
                self.product_readiness_freshness_response_alert_count
            ),
            "productReadinessFreshnessResponseAlertRoutedCount": (
                self.product_readiness_freshness_response_alert_routed_count
            ),
            "productReadinessFreshnessResponseAlertDrillScenarioCount": (
                self.product_readiness_freshness_response_alert_drill_scenario_count
            ),
            "productReadinessFreshnessResponseAlertDrillPassedCount": (
                self.product_readiness_freshness_response_alert_drill_passed_count
            ),
            "productReadinessFreshnessResponseAlertCalibratedCount": (
                self.product_readiness_freshness_response_alert_calibrated_count
            ),
            "productReadinessFreshnessResponseAlertNoisyCount": (
                self.product_readiness_freshness_response_alert_noisy_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionRuleCount": (
                self.product_readiness_freshness_response_alert_suppression_rule_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionActiveRuleCount": (
                self.product_readiness_freshness_response_alert_suppression_active_rule_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillScenarioCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillPassedCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_drill_passed_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyEffectiveSignalCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_effective_signal_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicySuppressionEffectivenessPct": (
                self.product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyEscalationPreservationPct": (
                self.product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageScenarioCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoveredScenarioCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoveragePct": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_pct
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionCheckCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_regression_check_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyPassedRegressionCheckCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloObjectiveCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloMetObjectiveCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_release_gate_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyAttachedReleaseGateCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateDrillScenarioCount"
            ): (
                self.release_gate_drill_scenario_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateDrillPassedCount"
            ): (
                self.release_gate_drill_passed_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEffectivenessSignalCount"
            ): (
                self.release_gate_effectiveness_signal_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEffectiveSignalCount"
            ): (
                self.release_gate_effective_signal_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEffectivenessPct"
            ): (
                self.release_gate_effectiveness_pct
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterprisePatternBlueprintCount"
            ): (
                self.release_gate_enterprise_pattern_blueprint_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterprisePatternNonLmsBlueprintCount"
            ): (
                self.release_gate_enterprise_pattern_non_lms_blueprint_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterprisePatternNonLmsProductCount"
            ): (
                self.release_gate_enterprise_pattern_non_lms_product_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterprisePatternTaxonomyAreaCount"
            ): (
                self.release_gate_enterprise_pattern_taxonomy_area_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSignalCount"
            ): (
                self.release_gate_enterprise_adoption_signal_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptedSignalCount"
            ): (
                self.release_gate_enterprise_adopted_signal_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionPct"
            ): (
                self.release_gate_enterprise_adoption_pct
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloObjectiveCount"
            ): (
                self.release_gate_enterprise_adoption_slo_objective_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloMetObjectiveCount"
            ): (
                self.release_gate_enterprise_adoption_slo_met_objective_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloTargetPct"
            ): (
                self.release_gate_enterprise_adoption_slo_target_pct
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReviewCadenceDays"
            ): (
                self.release_gate_enterprise_adoption_slo_review_cadence_days
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceGateCount"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_gate_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceAttachedGateCount"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_attached_gate_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceFailedGateCount"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_failed_gate_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceReviewCadenceDays"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_review_cadence_days
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillScenarioCount"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count
            ),
            (
                "productReadinessFreshnessResponseAlertSuppressionPolicy"
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillPassedCount"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_drill_passed_count
            ),
            "openIncidentCount": self.open_incident_count,
            "passedRequiredGateCount": self.passed_required_gate_count,
            "platformStatus": self.platform_status,
            "productId": self.product_id,
            "productName": self.product_name,
            "readinessStatus": self.readiness_status,
            "releaseStatus": self.release_status,
            "requiredGateCount": self.required_gate_count,
            "servingAuditFailureCount": self.serving_audit_failure_count,
            "servingAuditRecordCount": self.serving_audit_record_count,
            "servingErrorCount": self.serving_error_count,
            "servingMetricsConnected": self.serving_metrics_connected,
            "servingRequestCount": self.serving_request_count,
            "servingStatus": self.serving_status,
            "sourceReports": list(self.source_reports),
            "stakeholderVisibilityStatus": self.stakeholder_visibility_status,
            "tenantSafe": self.tenant_safe,
            "watchIncidentCount": self.watch_incident_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": generated_at,
            "product": {
                "product_id": self.product_id,
                "product_name": self.product_name,
            },
            "summary": {
                "readiness_status": self.readiness_status,
                "stakeholder_visibility_status": self.stakeholder_visibility_status,
                "platform_status": self.platform_status,
                "delivery_status": self.delivery_status,
                "release_status": self.release_status,
                "serving_status": self.serving_status,
                "serving_metrics_connected": self.serving_metrics_connected,
                "serving_request_count": self.serving_request_count,
                "serving_audit_record_count": self.serving_audit_record_count,
                "serving_error_count": self.serving_error_count,
                "serving_audit_failure_count": self.serving_audit_failure_count,
                "dashboard_freshness_status": self.dashboard_freshness_status,
                "governance_response_drill_status": (
                    self.governance_response_drill_status
                ),
                "product_readiness_freshness_response_drill_status": (
                    self.product_readiness_freshness_response_drill_status
                ),
                "product_readiness_freshness_response_metrics_status": (
                    self.product_readiness_freshness_response_metrics_status
                ),
                "product_readiness_freshness_response_metrics_ingest_status": (
                    self.product_readiness_freshness_response_metrics_ingest_status
                ),
                "product_readiness_freshness_response_trend_status": (
                    self.product_readiness_freshness_response_trend_status
                ),
                "product_readiness_freshness_response_alert_status": (
                    self.product_readiness_freshness_response_alert_status
                ),
                "product_readiness_freshness_response_alert_drill_status": (
                    self.product_readiness_freshness_response_alert_drill_status
                ),
                "product_readiness_freshness_response_alert_calibration_status": (
                    self.product_readiness_freshness_response_alert_calibration_status
                ),
                "product_readiness_freshness_response_alert_suppression_policy_status": (
                    self.product_readiness_freshness_response_alert_suppression_policy_status
                ),
                "product_readiness_freshness_response_alert_suppression_policy_drill_status": (
                    self.product_readiness_freshness_response_alert_suppression_policy_drill_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "effectiveness_status"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_effectiveness_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "coverage_status"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_coverage_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "regression_status"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_regression_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "coverage_slo_status"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_governance_status"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_release_governance_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_drill_status"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_effectiveness_status"
                ): (
                    self.release_gate_effectiveness_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_pattern_status"
                ): (
                    self.release_gate_enterprise_pattern_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_status"
                ): (
                    self.release_gate_enterprise_adoption_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_status"
                ): (
                    self.release_gate_enterprise_adoption_slo_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_status"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_status
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_drill_status"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_drill_status
                ),
                "governance_response_runbook_accepted": (
                    self.governance_response_runbook_accepted
                ),
                "product_readiness_freshness_response_drill_accepted": (
                    self.product_readiness_freshness_response_drill_accepted
                ),
                "product_readiness_freshness_response_metrics_breach_count": (
                    self.product_readiness_freshness_response_metrics_breach_count
                ),
                "product_readiness_freshness_response_metrics_live_observation_count": (
                    self.product_readiness_freshness_response_metrics_live_observation_count
                ),
                "product_readiness_freshness_response_trend_watch_count": (
                    self.product_readiness_freshness_response_trend_watch_count
                ),
                "product_readiness_freshness_response_alert_count": (
                    self.product_readiness_freshness_response_alert_count
                ),
                "product_readiness_freshness_response_alert_routed_count": (
                    self.product_readiness_freshness_response_alert_routed_count
                ),
                "product_readiness_freshness_response_alert_drill_scenario_count": (
                    self.product_readiness_freshness_response_alert_drill_scenario_count
                ),
                "product_readiness_freshness_response_alert_drill_passed_count": (
                    self.product_readiness_freshness_response_alert_drill_passed_count
                ),
                "product_readiness_freshness_response_alert_calibrated_count": (
                    self.product_readiness_freshness_response_alert_calibrated_count
                ),
                "product_readiness_freshness_response_alert_noisy_count": (
                    self.product_readiness_freshness_response_alert_noisy_count
                ),
                "product_readiness_freshness_response_alert_suppression_rule_count": (
                    self.product_readiness_freshness_response_alert_suppression_rule_count
                ),
                "product_readiness_freshness_response_alert_suppression_active_rule_count": (
                    self.product_readiness_freshness_response_alert_suppression_active_rule_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "drill_scenario_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "drill_passed_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_drill_passed_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "effective_signal_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_effective_signal_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "suppression_effectiveness_pct"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "escalation_preservation_pct"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "coverage_scenario_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "covered_scenario_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "coverage_pct"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_coverage_pct
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "regression_check_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_regression_check_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "passed_regression_check_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "coverage_slo_objective_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "coverage_slo_met_objective_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_release_gate_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "attached_release_gate_count"
                ): (
                    self.product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_drill_scenario_count"
                ): (
                    self.release_gate_drill_scenario_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_drill_passed_count"
                ): (
                    self.release_gate_drill_passed_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_effectiveness_signal_count"
                ): (
                    self.release_gate_effectiveness_signal_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_effective_signal_count"
                ): (
                    self.release_gate_effective_signal_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_effectiveness_pct"
                ): (
                    self.release_gate_effectiveness_pct
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_pattern_blueprint_count"
                ): (
                    self.release_gate_enterprise_pattern_blueprint_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_pattern_non_lms_blueprint_count"
                ): (
                    self.release_gate_enterprise_pattern_non_lms_blueprint_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_pattern_non_lms_product_count"
                ): (
                    self.release_gate_enterprise_pattern_non_lms_product_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_pattern_taxonomy_area_count"
                ): (
                    self.release_gate_enterprise_pattern_taxonomy_area_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_signal_count"
                ): (
                    self.release_gate_enterprise_adoption_signal_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adopted_signal_count"
                ): (
                    self.release_gate_enterprise_adopted_signal_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_pct"
                ): (
                    self.release_gate_enterprise_adoption_pct
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_objective_count"
                ): (
                    self.release_gate_enterprise_adoption_slo_objective_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_met_objective_count"
                ): (
                    self.release_gate_enterprise_adoption_slo_met_objective_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_target_pct"
                ): (
                    self.release_gate_enterprise_adoption_slo_target_pct
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_review_cadence_days"
                ): (
                    self.release_gate_enterprise_adoption_slo_review_cadence_days
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_gate_count"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_gate_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_attached_gate_count"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_attached_gate_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_failed_gate_count"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_failed_gate_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_review_cadence_days"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_review_cadence_days
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count
                ),
                (
                    "product_readiness_freshness_response_alert_suppression_policy_"
                    "release_gate_enterprise_adoption_slo_release_governance_drill_passed_count"
                ): (
                    self.release_gate_enterprise_adoption_slo_release_governance_drill_passed_count
                ),
                "tenant_safe": self.tenant_safe,
                "open_incident_count": self.open_incident_count,
                "watch_incident_count": self.watch_incident_count,
                "required_gate_count": self.required_gate_count,
                "passed_required_gate_count": self.passed_required_gate_count,
                "failed_required_gate_count": self.failed_required_gate_count,
                "followup_count": self.followup_count,
                "action_required_count": self.action_required_count,
            },
            "action_queue": build_action_queue(self.gates, self.followups),
            "source_reports": list(self.source_reports),
            "gates": [gate.to_snapshot_dict() for gate in self.gates],
            "followups": [followup.to_snapshot_dict() for followup in self.followups],
        }


def build_ai_platform_product_readiness_report(
    ai_root: Path | str,
    *,
    generated_at: str | date | None = None,
    serving_metrics: ModelServingMetricsSnapshot | None = None,
) -> AiPlatformProductReadinessReport:
    root = Path(ai_root)
    report_date = parse_report_date(generated_at)
    product_id, product_name = load_platform_product_metadata(root)
    product_readiness_freshness_response_drill = (
        build_product_readiness_freshness_incident_response_drill_report(
            root,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_metrics = (
        build_product_readiness_freshness_response_metrics_report(
            root,
            generated_at=report_date.isoformat(),
            response_drill=product_readiness_freshness_response_drill,
        )
    )
    product_readiness_freshness_response_trends = (
        build_product_readiness_freshness_response_trend_report_from_metrics(
            product_readiness_freshness_response_metrics,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alerts = (
        build_product_readiness_freshness_response_slo_drift_alert_report_from_trends(
            product_readiness_freshness_response_trends,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_drill = (
        build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts(
            product_readiness_freshness_response_alerts,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_calibration = (
        build_product_readiness_freshness_response_slo_drift_alert_calibration_report_from_drill(
            product_readiness_freshness_response_alert_drill,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy = (
        build_suppression_policy_from_calibration(
            product_readiness_freshness_response_alert_calibration,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_drill = (
        build_suppression_policy_drill_from_policy(
            product_readiness_freshness_response_alert_suppression_policy,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_effectiveness = (
        build_suppression_policy_effectiveness_from_drill(
            product_readiness_freshness_response_alert_suppression_policy_drill,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_coverage = (
        build_suppression_policy_coverage_from_reports(
            product_readiness_freshness_response_alert_suppression_policy_effectiveness,
            response_trends=product_readiness_freshness_response_trends,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_regression = (
        build_suppression_policy_coverage_regression_from_coverage(
            product_readiness_freshness_response_alert_suppression_policy_coverage,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo = (
        build_suppression_policy_coverage_slo_from_regression(
            product_readiness_freshness_response_alert_suppression_policy_regression,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_release_governance = (
        build_suppression_policy_coverage_release_governance_from_slo(
            product_readiness_freshness_response_alert_suppression_policy_coverage_slo,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill = (
        build_suppression_policy_coverage_release_gate_drill_from_governance(
            product_readiness_freshness_response_alert_suppression_policy_release_governance,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness = (
        build_suppression_policy_coverage_release_gate_effectiveness_from_drill(
            product_readiness_freshness_response_alert_suppression_policy_release_gate_drill,
            generated_at=report_date.isoformat(),
        )
    )
    release_gate_enterprise_pattern_report = (
        build_suppression_policy_coverage_release_gate_enterprise_pattern_from_reports(
            product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness,
            solution_blueprint=build_solution_blueprint_report(root),
            generated_at=report_date.isoformat(),
        )
    )
    release_gate_enterprise_adoption_report = (
        build_suppression_policy_coverage_release_gate_enterprise_adoption_from_pattern(
            release_gate_enterprise_pattern_report,
            generated_at=report_date.isoformat(),
        )
    )
    release_gate_enterprise_adoption_slo_report = (
        build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_from_adoption(
            release_gate_enterprise_adoption_report,
            generated_at=report_date.isoformat(),
        )
    )
    release_gate_enterprise_adoption_slo_release_governance_report = (
        build_enterprise_adoption_slo_release_governance_from_slo(
            release_gate_enterprise_adoption_slo_report,
            generated_at=report_date.isoformat(),
        )
    )
    release_gate_enterprise_adoption_slo_release_governance_drill_report = (
        build_enterprise_adoption_slo_release_governance_drill_from_governance(
            release_gate_enterprise_adoption_slo_release_governance_report,
            generated_at=report_date.isoformat(),
        )
    )
    return build_ai_platform_product_readiness_report_from_reports(
        product_id=product_id,
        product_name=product_name,
        operating_cockpit_report=build_operating_cockpit_report(
            root,
            as_of=report_date,
            serving_metrics=serving_metrics,
        ),
        delivery_state_report=build_delivery_state_report(root, as_of=report_date),
        dashboard_freshness=build_admin_ops_dashboard_freshness_manifest(
            root,
            generated_at=report_date.isoformat(),
        ),
        serving_access_incident_export=build_serving_access_incident_export(
            root,
            as_of=report_date,
        ),
        governance_evaluation_incident_export=(
            build_governance_evaluation_incident_export(
                root,
                as_of=report_date,
            )
        ),
        governance_evaluation_response_drill=(
            build_governance_evaluation_incident_response_drill_report(
                root,
                generated_at=report_date.isoformat(),
            )
        ),
        product_readiness_freshness_incident_export=(
            build_product_readiness_freshness_incident_export(
                root,
                as_of=report_date,
            )
        ),
        product_readiness_freshness_response_drill=(
            product_readiness_freshness_response_drill
        ),
        product_readiness_freshness_response_metrics=(
            product_readiness_freshness_response_metrics
        ),
        product_readiness_freshness_response_trends=(
            product_readiness_freshness_response_trends
        ),
        product_readiness_freshness_response_alerts=(
            product_readiness_freshness_response_alerts
        ),
        product_readiness_freshness_response_alert_drill=(
            product_readiness_freshness_response_alert_drill
        ),
        product_readiness_freshness_response_alert_calibration=(
            product_readiness_freshness_response_alert_calibration
        ),
        product_readiness_freshness_response_alert_suppression_policy=(
            product_readiness_freshness_response_alert_suppression_policy
        ),
        product_readiness_freshness_response_alert_suppression_policy_drill=(
            product_readiness_freshness_response_alert_suppression_policy_drill
        ),
        product_readiness_freshness_response_alert_suppression_policy_effectiveness=(
            product_readiness_freshness_response_alert_suppression_policy_effectiveness
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage=(
            product_readiness_freshness_response_alert_suppression_policy_coverage
        ),
        product_readiness_freshness_response_alert_suppression_policy_regression=(
            product_readiness_freshness_response_alert_suppression_policy_regression
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo=(
            product_readiness_freshness_response_alert_suppression_policy_coverage_slo
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_governance=(
            product_readiness_freshness_response_alert_suppression_policy_release_governance
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_drill=(
            product_readiness_freshness_response_alert_suppression_policy_release_gate_drill
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness=(
            product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern=(
            release_gate_enterprise_pattern_report
        ),
        release_gate_enterprise_adoption_report=release_gate_enterprise_adoption_report,
        release_gate_enterprise_adoption_slo_report=(
            release_gate_enterprise_adoption_slo_report
        ),
        release_gate_enterprise_adoption_slo_release_governance_report=(
            release_gate_enterprise_adoption_slo_release_governance_report
        ),
        enterprise_adoption_slo_governance_drill_report=(
            release_gate_enterprise_adoption_slo_release_governance_drill_report
        ),
    )


def build_ai_platform_product_readiness_report_from_reports(
    *,
    product_id: str,
    product_name: str,
    operating_cockpit_report: OperatingCockpitReport,
    delivery_state_report: DeliveryStateReport,
    dashboard_freshness: AdminOpsDashboardFreshnessManifest,
    serving_access_incident_export: ServingAccessIncidentExport,
    governance_evaluation_incident_export: GovernanceEvaluationIncidentExport,
    governance_evaluation_response_drill: GovernanceEvaluationIncidentResponseDrillReport,
    product_readiness_freshness_incident_export: ProductReadinessFreshnessIncidentExport,
    product_readiness_freshness_response_drill: (
        ProductReadinessFreshnessIncidentResponseDrillReport
    ),
    product_readiness_freshness_response_metrics: (
        ProductReadinessFreshnessResponseMetricsReport
    ),
    product_readiness_freshness_response_trends: (
        ProductReadinessFreshnessResponseTrendReport | None
    ) = None,
    product_readiness_freshness_response_alerts: (
        ProductReadinessFreshnessResponseSloDriftAlertReport | None
    ) = None,
    product_readiness_freshness_response_alert_drill: (
        ProductReadinessFreshnessResponseSloDriftAlertDrillReport | None
    ) = None,
    product_readiness_freshness_response_alert_calibration: (
        ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_drill: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
        | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_coverage: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport
        | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_regression: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
        | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
        | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_governance: (
        CoverageReleaseGovernanceReport
        | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill: (
        CoverageReleaseGateDrillReport
        | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness: (
        CoverageReleaseGateEffectivenessReport
        | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern: (
        CoverageReleaseGateEnterprisePatternReport
        | None
    ) = None,
    release_gate_enterprise_adoption_report: (
        CoverageReleaseGateEnterpriseAdoptionReport | None
    ) = None,
    release_gate_enterprise_adoption_slo_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReport | None
    ) = None,
    release_gate_enterprise_adoption_slo_release_governance_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport | None
    ) = None,
    enterprise_adoption_slo_governance_drill_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport | None
    ) = None,
) -> AiPlatformProductReadinessReport:
    response_trends = product_readiness_freshness_response_trends or (
        build_product_readiness_freshness_response_trend_report_from_metrics(
            product_readiness_freshness_response_metrics
        )
    )
    response_alerts = product_readiness_freshness_response_alerts or (
        build_product_readiness_freshness_response_slo_drift_alert_report_from_trends(
            response_trends
        )
    )
    response_alert_drill = product_readiness_freshness_response_alert_drill or (
        build_product_readiness_freshness_response_slo_drift_alert_drill_report_from_alerts(
            response_alerts
        )
    )
    response_alert_calibration = (
        product_readiness_freshness_response_alert_calibration
        or build_product_readiness_freshness_response_slo_drift_alert_calibration_report_from_drill(
            response_alert_drill
        )
    )
    response_alert_suppression_policy = (
        product_readiness_freshness_response_alert_suppression_policy
        or build_suppression_policy_from_calibration(
            response_alert_calibration
        )
    )
    response_alert_suppression_policy_drill = (
        product_readiness_freshness_response_alert_suppression_policy_drill
        or build_suppression_policy_drill_from_policy(
            response_alert_suppression_policy
        )
    )
    response_alert_suppression_policy_effectiveness = (
        product_readiness_freshness_response_alert_suppression_policy_effectiveness
        or build_suppression_policy_effectiveness_from_drill(
            response_alert_suppression_policy_drill
        )
    )
    response_alert_suppression_policy_coverage = (
        product_readiness_freshness_response_alert_suppression_policy_coverage
        or build_suppression_policy_coverage_from_reports(
            response_alert_suppression_policy_effectiveness,
            response_trends=response_trends,
        )
    )
    response_alert_suppression_policy_regression = (
        product_readiness_freshness_response_alert_suppression_policy_regression
        or build_suppression_policy_coverage_regression_from_coverage(
            response_alert_suppression_policy_coverage
        )
    )
    response_alert_suppression_policy_coverage_slo = (
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo
        or build_suppression_policy_coverage_slo_from_regression(
            response_alert_suppression_policy_regression
        )
    )
    response_alert_suppression_policy_release_governance = (
        product_readiness_freshness_response_alert_suppression_policy_release_governance
        or build_suppression_policy_coverage_release_governance_from_slo(
            response_alert_suppression_policy_coverage_slo
        )
    )
    response_alert_suppression_policy_release_gate_drill = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_drill
        or build_suppression_policy_coverage_release_gate_drill_from_governance(
            response_alert_suppression_policy_release_governance
        )
    )
    response_alert_suppression_policy_release_gate_effectiveness = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
        or build_suppression_policy_coverage_release_gate_effectiveness_from_drill(
            response_alert_suppression_policy_release_gate_drill
        )
    )
    response_alert_suppression_policy_release_gate_enterprise_pattern = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern
        or build_suppression_policy_coverage_release_gate_enterprise_pattern_from_reports(
            response_alert_suppression_policy_release_gate_effectiveness,
            solution_blueprint=build_solution_blueprint_report(default_ai_root()),
        )
    )
    response_alert_suppression_policy_release_gate_enterprise_adoption = (
        release_gate_enterprise_adoption_report
        or build_suppression_policy_coverage_release_gate_enterprise_adoption_from_pattern(
            response_alert_suppression_policy_release_gate_enterprise_pattern
        )
    )
    response_alert_suppression_policy_release_gate_enterprise_adoption_slo = (
        release_gate_enterprise_adoption_slo_report
        or build_suppression_policy_coverage_release_gate_enterprise_adoption_slo_from_adoption(
            response_alert_suppression_policy_release_gate_enterprise_adoption
        )
    )
    response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance = (
        release_gate_enterprise_adoption_slo_release_governance_report
        or build_enterprise_adoption_slo_release_governance_from_slo(
            response_alert_suppression_policy_release_gate_enterprise_adoption_slo
        )
    )
    enterprise_adoption_slo_release_governance_drill = (
        enterprise_adoption_slo_governance_drill_report
        or build_enterprise_adoption_slo_release_governance_drill_from_governance(
            response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance
        )
    )
    enterprise_adoption_slo_release_governance = (
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance
    )
    governance_response_accepted, governance_response_evidence = (
        governance_response_runbook_acceptance(delivery_state_report)
    )
    product_response_accepted, product_response_evidence = (
        product_readiness_freshness_response_drill_acceptance(delivery_state_report)
    )
    tenant_safe = (
        serving_access_incident_export.tenant_safe
        and governance_evaluation_incident_export.tenant_safe
        and product_readiness_freshness_incident_export.tenant_safe
        and product_readiness_freshness_response_drill.tenant_safe
        and product_readiness_freshness_response_metrics.tenant_safe
        and response_trends.tenant_safe
        and response_alerts.tenant_safe
        and response_alert_drill.tenant_safe
        and response_alert_calibration.tenant_safe
        and response_alert_suppression_policy.tenant_safe
        and response_alert_suppression_policy_drill.tenant_safe
        and response_alert_suppression_policy_effectiveness.tenant_safe
        and response_alert_suppression_policy_coverage.tenant_safe
        and response_alert_suppression_policy_regression.tenant_safe
        and response_alert_suppression_policy_coverage_slo.tenant_safe
        and response_alert_suppression_policy_release_governance.tenant_safe
        and response_alert_suppression_policy_release_gate_drill.tenant_safe
        and response_alert_suppression_policy_release_gate_effectiveness.tenant_safe
        and response_alert_suppression_policy_release_gate_enterprise_pattern.tenant_safe
        and response_alert_suppression_policy_release_gate_enterprise_adoption.tenant_safe
        and response_alert_suppression_policy_release_gate_enterprise_adoption_slo.tenant_safe
        and enterprise_adoption_slo_release_governance.tenant_safe
        and enterprise_adoption_slo_release_governance_drill.tenant_safe
    )
    open_incident_count = (
        serving_access_incident_export.open_count
        + governance_evaluation_incident_export.open_count
        + product_readiness_freshness_incident_export.open_count
    )
    watch_incident_count = (
        serving_access_incident_export.watch_count
        + governance_evaluation_incident_export.watch_count
        + product_readiness_freshness_incident_export.watch_count
    )
    release_gate_effectiveness = (
        response_alert_suppression_policy_release_gate_effectiveness
    )
    release_gate_effectiveness_pct = (
        release_gate_effectiveness.release_gate_effectiveness_pct
    )
    release_gate_enterprise_pattern = (
        response_alert_suppression_policy_release_gate_enterprise_pattern
    )
    release_gate_enterprise_adoption = (
        response_alert_suppression_policy_release_gate_enterprise_adoption
    )
    release_gate_enterprise_adoption_slo = (
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo
    )
    release_gate_enterprise_adoption_slo_release_governance = (
        enterprise_adoption_slo_release_governance
    )
    enterprise_adoption_slo_governance_status = (
        release_gate_enterprise_adoption_slo_release_governance.release_governance_status
    )
    enterprise_adoption_slo_governance_attached_count = (
        release_gate_enterprise_adoption_slo_release_governance.attached_release_gate_count
    )
    enterprise_adoption_slo_governance_gate_count = (
        release_gate_enterprise_adoption_slo_release_governance.release_gate_count
    )
    enterprise_adoption_slo_governance_drill_status = (
        enterprise_adoption_slo_release_governance_drill.drill_status
    )
    enterprise_adoption_slo_governance_drill_passed_count = (
        enterprise_adoption_slo_release_governance_drill.passed_count
    )
    enterprise_adoption_slo_governance_drill_scenario_count = (
        enterprise_adoption_slo_release_governance_drill.scenario_count
    )
    gates = (
        build_gate(
            gate_id="platform_product_registered",
            title="AI Platform product is registered",
            owner_role="PO/BA",
            passed=product_id == PRODUCT_ID and bool(product_name),
            reason=(
                "AI Platform is registered as the platform product."
                if product_id == PRODUCT_ID
                else "Products registry does not point at the AI Platform product."
            ),
            evidence_refs=(
                "products/registry.yaml",
                "products/ai-platform/README.md",
            ),
        ),
        build_gate(
            gate_id="required_ai_spectrum_covered",
            title="Required AI spectrum is covered",
            owner_role="SA AI Platform",
            passed=operating_cockpit_report.missing_required_area_count == 0,
            reason=(
                f"{operating_cockpit_report.coverage_module_count} modules cover all "
                "required AI areas."
            ),
            evidence_refs=(
                "platform/coverage/reports/ai-module-catalog-v1.yaml",
                "platform/coverage/reports/ai-capability-taxonomy-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="evaluation_gates_passed",
            title="Required evaluation gates pass",
            owner_role="SA AI Engineer",
            passed=(
                operating_cockpit_report.evaluation_required_count
                == operating_cockpit_report.evaluation_required_passed_count
            ),
            reason=(
                f"{operating_cockpit_report.evaluation_required_passed_count}/"
                f"{operating_cockpit_report.evaluation_required_count} required "
                "evaluations passed."
            ),
            evidence_refs=("platform/evaluation/registry.yaml",),
        ),
        build_gate(
            gate_id="release_ready",
            title="Release health is ready",
            owner_role="SA AI Platform + Governance Reviewer",
            passed=operating_cockpit_report.release_status == "release_ready",
            reason=(
                "Operating cockpit release status is "
                f"{operating_cockpit_report.release_status}."
            ),
            evidence_refs=("platform/operations/reports/operating-cockpit-v1.yaml",),
        ),
        build_gate(
            gate_id="serving_metrics_healthy",
            title="Serving metrics are healthy",
            owner_role="Admin/Ops",
            passed=(
                operating_cockpit_report.serving_health.status == "healthy"
                and operating_cockpit_report.serving_health.metrics_connected
            ),
            reason=(
                "Serving metrics are connected with status "
                f"{operating_cockpit_report.serving_health.status}."
            ),
            evidence_refs=(
                "platform/operations/reports/model-serving-metrics-export-v1.yaml",
                "platform/operations/reports/operating-cockpit-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="admin_ops_dashboard_current",
            title="Admin/Ops dashboard is current",
            owner_role="Admin/Ops",
            passed=(
                dashboard_freshness.freshness_status == "current"
                and dashboard_freshness.dashboard_matches_generated_html
            ),
            reason=(
                "Dashboard freshness status is "
                f"{dashboard_freshness.freshness_status} with "
                f"{dashboard_freshness.current_source_count}/"
                f"{dashboard_freshness.source_count} current sources."
            ),
            evidence_refs=(
                "platform/operations/reports/admin-ops-dashboard-v1.html",
                "platform/operations/reports/admin-ops-dashboard-freshness-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="tenant_safe_incident_exports",
            title="Incident exports are tenant-safe and quiet",
            owner_role="Governance Reviewer",
            passed=tenant_safe and open_incident_count == 0,
            reason=(
                f"{open_incident_count} open incidents, "
                f"{watch_incident_count} watch incidents and tenant_safe={tenant_safe}."
            ),
            evidence_refs=(
                "platform/governance/reports/model-serving-access-incident-export-v1.yaml",
                "platform/governance/reports/governance-evaluation-incident-export-v1.yaml",
                "platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="governance_response_runbook_accepted",
            title="Governance Evaluation response runbook is accepted",
            owner_role="Admin/Ops",
            passed=(
                governance_response_accepted
                and governance_evaluation_response_drill.drill_status == "passed"
            ),
            reason=(
                "Response drill status is "
                f"{governance_evaluation_response_drill.drill_status}; "
                f"delivery acceptance={governance_response_accepted}."
            ),
            evidence_refs=governance_response_evidence,
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_drill_passed",
            title="Product Readiness Freshness response drill passed",
            owner_role="Admin/Ops",
            passed=product_readiness_freshness_response_drill.drill_status == "passed",
            reason=(
                "Product Readiness Freshness response drill status is "
                f"{product_readiness_freshness_response_drill.drill_status} with "
                f"{product_readiness_freshness_response_drill.passed_count}/"
                f"{product_readiness_freshness_response_drill.scenario_count} "
                "scenarios passed."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml",
                "platform/operations/runbooks/product-readiness-freshness-incident-response-v1.yaml",
                "runbooks/product-readiness-freshness-incident-response.md",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_drill_accepted",
            title="Product Readiness Freshness response drill is accepted",
            owner_role="Admin/Ops",
            passed=(
                product_response_accepted
                and product_readiness_freshness_response_drill.drill_status == "passed"
            ),
            reason=(
                "Product Readiness Freshness response drill status is "
                f"{product_readiness_freshness_response_drill.drill_status}; "
                f"delivery acceptance={product_response_accepted}."
            ),
            evidence_refs=product_response_evidence,
        ),
        build_gate(
            gate_id="product_readiness_freshness_live_response_metrics_ingest_connected",
            title="Product Readiness Freshness live response metrics ingest is connected",
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                product_readiness_freshness_response_metrics.ingest_status
                == "live_ingest_connected"
                and (
                    product_readiness_freshness_response_metrics.live_observation_count
                    == product_readiness_freshness_response_metrics.scenario_count
                )
                and (
                    product_readiness_freshness_response_metrics.missing_live_observation_count
                    == 0
                )
            ),
            reason=(
                "Product Readiness Freshness response metrics ingest status is "
                f"{product_readiness_freshness_response_metrics.ingest_status} with "
                f"{product_readiness_freshness_response_metrics.live_observation_count}/"
                f"{product_readiness_freshness_response_metrics.scenario_count} "
                "live observations."
            ),
            evidence_refs=(
                "platform/operations/metrics/product-readiness-freshness-live-response-metrics-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-metrics-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_metrics_slo_met",
            title="Product Readiness Freshness response metrics meet SLO",
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                product_readiness_freshness_response_metrics.response_metrics_status
                == "slo_met"
                and product_readiness_freshness_response_metrics.breach_count == 0
            ),
            reason=(
                "Product Readiness Freshness response metrics status is "
                f"{product_readiness_freshness_response_metrics.response_metrics_status} "
                "with "
                f"{product_readiness_freshness_response_metrics.breach_count} "
                "SLO breaches."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-metrics-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml",
                "platform/operations/runbooks/product-readiness-freshness-incident-response-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_trend_ready",
            title="Product Readiness Freshness response SLO trend is ready",
            owner_role="SA AI Platform + Admin/Ops",
            passed=response_trends.trend_status
            in {"trend_ready", "trend_ready_with_watch"}
            and response_trends.tenant_safe
            and response_trends.raw_identifier_count == 0,
            reason=(
                "Product Readiness Freshness response trend status is "
                f"{response_trends.trend_status} across "
                f"{response_trends.owner_count} owner roles with "
                f"{response_trends.watch_count} watch scenarios and "
                f"{response_trends.breach_count} SLO breaches."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-trends-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-metrics-v1.yaml",
                "platform/operations/metrics/product-readiness-freshness-live-response-metrics-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_alerts_configured",
            title="Product Readiness Freshness response SLO drift alerts are configured",
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alerts.alert_status
                in {"alerts_configured", "alerts_configured_with_watch"}
                and response_alerts.tenant_safe
                and response_alerts.raw_identifier_count == 0
                and response_alerts.routed_alert_count == response_alerts.alert_count
                and response_alerts.alert_count == response_alerts.watch_count
            ),
            reason=(
                "Product Readiness Freshness response SLO drift alert status is "
                f"{response_alerts.alert_status} with "
                f"{response_alerts.routed_alert_count}/"
                f"{response_alerts.watch_count} watch scenarios routed."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alerts-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-trends-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_alert_drill_passed",
            title="Product Readiness Freshness response SLO drift alert drill passed",
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_drill.drill_status == "passed"
                and response_alert_drill.tenant_safe
                and response_alert_drill.raw_identifier_count == 0
                and (
                    response_alert_drill.passed_count
                    == response_alert_drill.scenario_count
                )
                and (
                    response_alert_drill.scenario_count
                    == response_alerts.routed_alert_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift alert drill status "
                f"is {response_alert_drill.drill_status} with "
                f"{response_alert_drill.passed_count}/"
                f"{response_alert_drill.scenario_count} alert paths passed."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alerts-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_alert_calibration_monitored",
            title=(
                "Product Readiness Freshness response SLO drift alert calibration "
                "is monitored"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_calibration.calibration_status
                == "calibrated_with_watch"
                and response_alert_calibration.tenant_safe
                and response_alert_calibration.raw_identifier_count == 0
                and response_alert_calibration.failed_count == 0
                and response_alert_calibration.noisy_alert_count == 0
                and response_alert_calibration.under_threshold_count == 0
            ),
            reason=(
                "Product Readiness Freshness response SLO drift alert calibration "
                f"status is {response_alert_calibration.calibration_status} with "
                f"{response_alert_calibration.calibrated_count}/"
                f"{response_alert_calibration.scenario_count} alert calibrations "
                "passing and "
                f"{response_alert_calibration.noisy_alert_count} noisy alerts."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_alert_suppression_policy_codified",
            title=(
                "Product Readiness Freshness response SLO drift alert "
                "suppression policy is codified"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy.policy_status
                == "suppression_policy_codified"
                and response_alert_suppression_policy.tenant_safe
                and response_alert_suppression_policy.raw_identifier_count == 0
                and response_alert_suppression_policy.failed_rule_count == 0
                and (
                    response_alert_suppression_policy.active_rule_count
                    == response_alert_suppression_policy.rule_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift alert "
                f"suppression policy status is "
                f"{response_alert_suppression_policy.policy_status} with "
                f"{response_alert_suppression_policy.active_rule_count}/"
                f"{response_alert_suppression_policy.rule_count} active rules."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_drill_passed",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy drill passed"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy_drill.drill_status == "passed"
                and response_alert_suppression_policy_drill.tenant_safe
                and response_alert_suppression_policy_drill.raw_identifier_count == 0
                and response_alert_suppression_policy_drill.failed_count == 0
                and (
                    response_alert_suppression_policy_drill.passed_count
                    == response_alert_suppression_policy_drill.scenario_count
                )
                and (
                    response_alert_suppression_policy_drill.scenario_count
                    == response_alert_suppression_policy_drill.expected_scenario_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                f"policy drill status is "
                f"{response_alert_suppression_policy_drill.drill_status} with "
                f"{response_alert_suppression_policy_drill.passed_count}/"
                f"{response_alert_suppression_policy_drill.scenario_count} "
                "policy scenarios passed."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_monitored",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy effectiveness is monitored"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy_effectiveness.monitor_status
                == "effectiveness_monitored"
                and response_alert_suppression_policy_effectiveness.tenant_safe
                and (
                    response_alert_suppression_policy_effectiveness.raw_identifier_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_effectiveness.failed_signal_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_effectiveness.effective_signal_count
                    == response_alert_suppression_policy_effectiveness.signal_count
                )
                and (
                    response_alert_suppression_policy_effectiveness.suppression_effectiveness_pct
                    == 100
                )
                and (
                    response_alert_suppression_policy_effectiveness.escalation_preservation_pct
                    == 100
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                f"policy effectiveness status is "
                f"{response_alert_suppression_policy_effectiveness.monitor_status} "
                "with suppression "
                f"{response_alert_suppression_policy_effectiveness.suppression_effectiveness_pct}% "
                "and escalation preservation "
                f"{response_alert_suppression_policy_effectiveness.escalation_preservation_pct}%."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_expanded",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage is expanded"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy_coverage.coverage_status
                == "coverage_expanded"
                and response_alert_suppression_policy_coverage.tenant_safe
                and response_alert_suppression_policy_coverage.raw_identifier_count == 0
                and response_alert_suppression_policy_coverage.failed_coverage_count
                == 0
                and (
                    response_alert_suppression_policy_coverage.covered_scenario_count
                    == response_alert_suppression_policy_coverage.scenario_class_count
                )
                and response_alert_suppression_policy_coverage.coverage_pct == 100
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                f"policy coverage status is "
                f"{response_alert_suppression_policy_coverage.coverage_status} "
                f"with {response_alert_suppression_policy_coverage.covered_scenario_count}/"
                f"{response_alert_suppression_policy_coverage.scenario_class_count} "
                "scenario classes covered."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-trends-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_monitored",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage regression is monitored"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy_regression.regression_status
                == "regression_monitored"
                and response_alert_suppression_policy_regression.tenant_safe
                and response_alert_suppression_policy_regression.raw_identifier_count
                == 0
                and (
                    response_alert_suppression_policy_regression.failed_regression_check_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_regression.passed_regression_check_count
                    == response_alert_suppression_policy_regression.regression_check_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                f"policy coverage regression status is "
                f"{response_alert_suppression_policy_regression.regression_status} "
                "with "
                f"{response_alert_suppression_policy_regression.passed_regression_check_count}/"
                f"{response_alert_suppression_policy_regression.regression_check_count} "
                "regression checks passed."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_published",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage SLO is published"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy_coverage_slo.slo_status
                == "coverage_slo_published"
                and response_alert_suppression_policy_coverage_slo.tenant_safe
                and response_alert_suppression_policy_coverage_slo.raw_identifier_count
                == 0
                and (
                    response_alert_suppression_policy_coverage_slo.failed_objective_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_coverage_slo.met_objective_count
                    == response_alert_suppression_policy_coverage_slo.objective_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                f"policy coverage SLO status is "
                f"{response_alert_suppression_policy_coverage_slo.slo_status} "
                "with "
                f"{response_alert_suppression_policy_coverage_slo.met_objective_count}/"
                f"{response_alert_suppression_policy_coverage_slo.objective_count} "
                "objectives met."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_governance_attached",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release governance is attached"
            ),
            owner_role="SA AI Platform + Governance Reviewer",
            passed=(
                response_alert_suppression_policy_release_governance.release_governance_status
                == "release_governance_attached"
                and response_alert_suppression_policy_release_governance.tenant_safe
                and (
                    response_alert_suppression_policy_release_governance.raw_identifier_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_release_governance.failed_release_gate_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_release_governance.attached_release_gate_count
                    == response_alert_suppression_policy_release_governance.release_gate_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release governance status is "
                f"{response_alert_suppression_policy_release_governance.release_governance_status} "
                "with "
                f"{response_alert_suppression_policy_release_governance.attached_release_gate_count}/"
                f"{response_alert_suppression_policy_release_governance.release_gate_count} "
                "release gates attached."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill_passed",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate drill passed"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy_release_gate_drill.drill_status
                == "passed"
                and response_alert_suppression_policy_release_gate_drill.tenant_safe
                and (
                    response_alert_suppression_policy_release_gate_drill.raw_identifier_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_release_gate_drill.failed_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_release_gate_drill.passed_count
                    == response_alert_suppression_policy_release_gate_drill.scenario_count
                )
                and (
                    response_alert_suppression_policy_release_gate_drill.scenario_count
                    == response_alert_suppression_policy_release_governance.release_gate_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate drill status is "
                f"{response_alert_suppression_policy_release_gate_drill.drill_status} "
                "with "
                f"{response_alert_suppression_policy_release_gate_drill.passed_count}/"
                f"{response_alert_suppression_policy_release_gate_drill.scenario_count} "
                "release gate drill scenarios passed."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness_monitored",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate effectiveness is monitored"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                response_alert_suppression_policy_release_gate_effectiveness.monitor_status
                == "effectiveness_monitored"
                and response_alert_suppression_policy_release_gate_effectiveness.tenant_safe
                and (
                    response_alert_suppression_policy_release_gate_effectiveness.raw_identifier_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_release_gate_effectiveness.failed_signal_count
                    == 0
                )
                and (
                    response_alert_suppression_policy_release_gate_effectiveness.effective_signal_count
                    == response_alert_suppression_policy_release_gate_effectiveness.signal_count
                )
                and (
                    response_alert_suppression_policy_release_gate_effectiveness.release_gate_effectiveness_pct
                    == 100
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate effectiveness status is "
                f"{response_alert_suppression_policy_release_gate_effectiveness.monitor_status} "
                "with "
                f"{response_alert_suppression_policy_release_gate_effectiveness.effective_signal_count}/"
                f"{response_alert_suppression_policy_release_gate_effectiveness.signal_count} "
                "signals effective and "
                f"{release_gate_effectiveness_pct}% "
                "release gate effectiveness."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_pattern_expanded_to_enterprise_use_cases",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate pattern is expanded to "
                "enterprise use cases"
            ),
            owner_role="SA AI Platform + PO/BA + Admin/Ops",
            passed=(
                release_gate_enterprise_pattern.expansion_status
                == "enterprise_pattern_expanded"
                and release_gate_enterprise_pattern.tenant_safe
                and release_gate_enterprise_pattern.raw_identifier_count == 0
                and release_gate_enterprise_pattern.blocked_assignment_count == 0
                and (
                    release_gate_enterprise_pattern.assigned_use_case_count
                    == release_gate_enterprise_pattern.blueprint_count
                )
                and release_gate_enterprise_pattern.non_lms_blueprint_count >= 5
                and release_gate_enterprise_pattern.non_lms_product_count >= 4
                and release_gate_enterprise_pattern.taxonomy_area_count >= 8
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise pattern status is "
                f"{release_gate_enterprise_pattern.expansion_status} across "
                f"{release_gate_enterprise_pattern.assigned_use_case_count}/"
                f"{release_gate_enterprise_pattern.blueprint_count} "
                "blueprints, "
                f"{release_gate_enterprise_pattern.non_lms_blueprint_count} "
                "non-LMS use cases and "
                f"{release_gate_enterprise_pattern.taxonomy_area_count} "
                "taxonomy areas."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml",
                "platform/intake/reports/use-case-blueprints-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_monitored",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption is monitored"
            ),
            owner_role="SA AI Platform + Admin/Ops",
            passed=(
                release_gate_enterprise_adoption.adoption_status
                == "adoption_monitored"
                and release_gate_enterprise_adoption.tenant_safe
                and release_gate_enterprise_adoption.raw_identifier_count == 0
                and release_gate_enterprise_adoption.blocked_signal_count == 0
                and (
                    release_gate_enterprise_adoption.adopted_signal_count
                    == release_gate_enterprise_adoption.signal_count
                )
                and release_gate_enterprise_adoption.adoption_pct == 100
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption status is "
                f"{release_gate_enterprise_adoption.adoption_status} with "
                f"{release_gate_enterprise_adoption.adopted_signal_count}/"
                f"{release_gate_enterprise_adoption.signal_count} signals "
                "adopted and "
                f"{release_gate_enterprise_adoption.adoption_pct}% adoption."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml",
                "platform/intake/reports/use-case-blueprints-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_published",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption SLO is published"
            ),
            owner_role="SA AI Platform + PO/BA + Admin/Ops",
            passed=(
                release_gate_enterprise_adoption_slo.slo_status
                == "adoption_slo_published"
                and release_gate_enterprise_adoption_slo.tenant_safe
                and release_gate_enterprise_adoption_slo.raw_identifier_count == 0
                and release_gate_enterprise_adoption_slo.failed_objective_count == 0
                and (
                    release_gate_enterprise_adoption_slo.met_objective_count
                    == release_gate_enterprise_adoption_slo.objective_count
                )
                and (
                    release_gate_enterprise_adoption_slo.adoption_pct
                    >= release_gate_enterprise_adoption_slo.target_adoption_pct
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption SLO status is "
                f"{release_gate_enterprise_adoption_slo.slo_status} with "
                f"{release_gate_enterprise_adoption_slo.met_objective_count}/"
                f"{release_gate_enterprise_adoption_slo.objective_count} "
                "objectives met and "
                f"{release_gate_enterprise_adoption_slo.adoption_pct}% "
                "enterprise adoption."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_attached",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption SLO release "
                "governance is attached"
            ),
            owner_role="SA AI Platform + Governance Reviewer + Admin/Ops",
            passed=(
                release_gate_enterprise_adoption_slo_release_governance.release_governance_status
                == "enterprise_adoption_slo_release_governance_attached"
                and release_gate_enterprise_adoption_slo_release_governance.tenant_safe
                and (
                    release_gate_enterprise_adoption_slo_release_governance.raw_identifier_count
                    == 0
                )
                and (
                    release_gate_enterprise_adoption_slo_release_governance.failed_release_gate_count
                    == 0
                )
                and (
                    release_gate_enterprise_adoption_slo_release_governance.attached_release_gate_count
                    == release_gate_enterprise_adoption_slo_release_governance.release_gate_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption SLO release "
                "governance status is "
                f"{enterprise_adoption_slo_governance_status} "
                "with "
                f"{enterprise_adoption_slo_governance_attached_count}/"
                f"{enterprise_adoption_slo_governance_gate_count} "
                "release governance gates attached."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
        build_gate(
            gate_id="product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_passed",
            title=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption SLO release "
                "governance drill passed"
            ),
            owner_role="SA AI Platform + Governance Reviewer + Admin/Ops",
            passed=(
                enterprise_adoption_slo_release_governance_drill.drill_status
                == "passed"
                and enterprise_adoption_slo_release_governance_drill.tenant_safe
                and (
                    enterprise_adoption_slo_release_governance_drill.raw_identifier_count
                    == 0
                )
                and (
                    enterprise_adoption_slo_release_governance_drill.failed_count
                    == 0
                )
                and (
                    enterprise_adoption_slo_release_governance_drill.passed_count
                    == enterprise_adoption_slo_release_governance_drill.scenario_count
                )
            ),
            reason=(
                "Product Readiness Freshness response SLO drift suppression "
                "policy coverage release gate enterprise adoption SLO release "
                "governance drill status is "
                f"{enterprise_adoption_slo_governance_drill_status} "
                "with "
                f"{enterprise_adoption_slo_governance_drill_passed_count}/"
                f"{enterprise_adoption_slo_governance_drill_scenario_count} "
                "scenarios passed."
            ),
            evidence_refs=(
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml",
                "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml",
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
                "platform/operations/reports/admin-ops-dashboard-v1.html",
            ),
        ),
    )
    followups = build_response_slo_drift_alert_followups(
        response_alert_drill,
        response_alert_calibration,
        response_alert_suppression_policy,
        response_alert_suppression_policy_drill,
        response_alert_suppression_policy_effectiveness,
        response_alert_suppression_policy_coverage,
        response_alert_suppression_policy_regression,
        response_alert_suppression_policy_coverage_slo,
        response_alert_suppression_policy_release_governance,
        response_alert_suppression_policy_release_gate_drill,
        response_alert_suppression_policy_release_gate_effectiveness,
        response_alert_suppression_policy_release_gate_enterprise_pattern,
        response_alert_suppression_policy_release_gate_enterprise_adoption,
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo,
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance,
        enterprise_adoption_slo_release_governance_drill,
    )
    required_gate_count = sum(1 for gate in gates if gate.required)
    passed_required_gate_count = sum(
        1 for gate in gates if gate.required and gate.passed
    )
    failed_required_gate_count = required_gate_count - passed_required_gate_count
    action_required_count = failed_required_gate_count
    readiness_status = derive_readiness_status(
        failed_required_gate_count=failed_required_gate_count,
        followup_count=len(followups),
    )
    stakeholder_visibility_status = derive_stakeholder_visibility_status(
        dashboard_freshness,
        governance_response_accepted=governance_response_accepted,
        product_readiness_freshness_response_accepted=product_response_accepted,
    )
    return AiPlatformProductReadinessReport(
        product_id=product_id,
        product_name=product_name,
        readiness_status=readiness_status,
        stakeholder_visibility_status=stakeholder_visibility_status,
        platform_status=operating_cockpit_report.platform_status,
        delivery_status=operating_cockpit_report.delivery_status,
        release_status=operating_cockpit_report.release_status,
        serving_status=operating_cockpit_report.serving_health.status,
        serving_metrics_connected=(
            operating_cockpit_report.serving_health.metrics_connected
        ),
        serving_request_count=operating_cockpit_report.serving_health.request_count,
        serving_audit_record_count=(
            operating_cockpit_report.serving_health.audit_record_count
        ),
        serving_error_count=operating_cockpit_report.serving_health.error_count,
        serving_audit_failure_count=(
            operating_cockpit_report.serving_health.audit_failure_count
        ),
        dashboard_freshness_status=dashboard_freshness.freshness_status,
        governance_response_drill_status=(
            governance_evaluation_response_drill.drill_status
        ),
        product_readiness_freshness_response_drill_status=(
            product_readiness_freshness_response_drill.drill_status
        ),
        product_readiness_freshness_response_metrics_status=(
            product_readiness_freshness_response_metrics.response_metrics_status
        ),
        product_readiness_freshness_response_metrics_ingest_status=(
            product_readiness_freshness_response_metrics.ingest_status
        ),
        product_readiness_freshness_response_trend_status=(
            response_trends.trend_status
        ),
        product_readiness_freshness_response_alert_status=(
            response_alerts.alert_status
        ),
        product_readiness_freshness_response_alert_drill_status=(
            response_alert_drill.drill_status
        ),
        product_readiness_freshness_response_alert_calibration_status=(
            response_alert_calibration.calibration_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_status=(
            response_alert_suppression_policy.policy_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_drill_status=(
            response_alert_suppression_policy_drill.drill_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_effectiveness_status=(
            response_alert_suppression_policy_effectiveness.monitor_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_status=(
            response_alert_suppression_policy_coverage.coverage_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_regression_status=(
            response_alert_suppression_policy_regression.regression_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status=(
            response_alert_suppression_policy_coverage_slo.slo_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_governance_status=(
            response_alert_suppression_policy_release_governance.release_governance_status
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status=(
            response_alert_suppression_policy_release_gate_drill.drill_status
        ),
        release_gate_effectiveness_status=(
            response_alert_suppression_policy_release_gate_effectiveness.monitor_status
        ),
        release_gate_enterprise_pattern_status=(
            release_gate_enterprise_pattern.expansion_status
        ),
        release_gate_enterprise_adoption_status=(
            release_gate_enterprise_adoption.adoption_status
        ),
        release_gate_enterprise_adoption_slo_status=(
            release_gate_enterprise_adoption_slo.slo_status
        ),
        release_gate_enterprise_adoption_slo_release_governance_status=(
            release_gate_enterprise_adoption_slo_release_governance.release_governance_status
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_status=(
            enterprise_adoption_slo_release_governance_drill.drill_status
        ),
        governance_response_runbook_accepted=governance_response_accepted,
        product_readiness_freshness_response_drill_accepted=product_response_accepted,
        product_readiness_freshness_response_metrics_breach_count=(
            product_readiness_freshness_response_metrics.breach_count
        ),
        product_readiness_freshness_response_metrics_live_observation_count=(
            product_readiness_freshness_response_metrics.live_observation_count
        ),
        product_readiness_freshness_response_trend_watch_count=(
            response_trends.watch_count
        ),
        product_readiness_freshness_response_alert_count=(
            response_alerts.alert_count
        ),
        product_readiness_freshness_response_alert_routed_count=(
            response_alerts.routed_alert_count
        ),
        product_readiness_freshness_response_alert_drill_scenario_count=(
            response_alert_drill.scenario_count
        ),
        product_readiness_freshness_response_alert_drill_passed_count=(
            response_alert_drill.passed_count
        ),
        product_readiness_freshness_response_alert_calibrated_count=(
            response_alert_calibration.calibrated_count
        ),
        product_readiness_freshness_response_alert_noisy_count=(
            response_alert_calibration.noisy_alert_count
        ),
        product_readiness_freshness_response_alert_suppression_rule_count=(
            response_alert_suppression_policy.rule_count
        ),
        product_readiness_freshness_response_alert_suppression_active_rule_count=(
            response_alert_suppression_policy.active_rule_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count=(
            response_alert_suppression_policy_drill.scenario_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_drill_passed_count=(
            response_alert_suppression_policy_drill.passed_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_effective_signal_count=(
            response_alert_suppression_policy_effectiveness.effective_signal_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct=(
            response_alert_suppression_policy_effectiveness.suppression_effectiveness_pct
        ),
        product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct=(
            response_alert_suppression_policy_effectiveness.escalation_preservation_pct
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count=(
            response_alert_suppression_policy_coverage.scenario_class_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count=(
            response_alert_suppression_policy_coverage.covered_scenario_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_pct=(
            response_alert_suppression_policy_coverage.coverage_pct
        ),
        product_readiness_freshness_response_alert_suppression_policy_regression_check_count=(
            response_alert_suppression_policy_regression.regression_check_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count=(
            response_alert_suppression_policy_regression.passed_regression_check_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count=(
            response_alert_suppression_policy_coverage_slo.objective_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count=(
            response_alert_suppression_policy_coverage_slo.met_objective_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_count=(
            response_alert_suppression_policy_release_governance.release_gate_count
        ),
        product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count=(
            response_alert_suppression_policy_release_governance.attached_release_gate_count
        ),
        release_gate_drill_scenario_count=(
            response_alert_suppression_policy_release_gate_drill.scenario_count
        ),
        release_gate_drill_passed_count=(
            response_alert_suppression_policy_release_gate_drill.passed_count
        ),
        release_gate_effectiveness_signal_count=(
            response_alert_suppression_policy_release_gate_effectiveness.signal_count
        ),
        release_gate_effective_signal_count=(
            response_alert_suppression_policy_release_gate_effectiveness.effective_signal_count
        ),
        release_gate_effectiveness_pct=(
            release_gate_effectiveness_pct
        ),
        release_gate_enterprise_pattern_blueprint_count=(
            release_gate_enterprise_pattern.blueprint_count
        ),
        release_gate_enterprise_pattern_non_lms_blueprint_count=(
            release_gate_enterprise_pattern.non_lms_blueprint_count
        ),
        release_gate_enterprise_pattern_non_lms_product_count=(
            release_gate_enterprise_pattern.non_lms_product_count
        ),
        release_gate_enterprise_pattern_taxonomy_area_count=(
            release_gate_enterprise_pattern.taxonomy_area_count
        ),
        release_gate_enterprise_adoption_signal_count=(
            release_gate_enterprise_adoption.signal_count
        ),
        release_gate_enterprise_adopted_signal_count=(
            release_gate_enterprise_adoption.adopted_signal_count
        ),
        release_gate_enterprise_adoption_pct=(
            release_gate_enterprise_adoption.adoption_pct
        ),
        release_gate_enterprise_adoption_slo_objective_count=(
            release_gate_enterprise_adoption_slo.objective_count
        ),
        release_gate_enterprise_adoption_slo_met_objective_count=(
            release_gate_enterprise_adoption_slo.met_objective_count
        ),
        release_gate_enterprise_adoption_slo_target_pct=(
            release_gate_enterprise_adoption_slo.target_adoption_pct
        ),
        release_gate_enterprise_adoption_slo_review_cadence_days=(
            release_gate_enterprise_adoption_slo.review_cadence_days
        ),
        release_gate_enterprise_adoption_slo_release_governance_gate_count=(
            release_gate_enterprise_adoption_slo_release_governance.release_gate_count
        ),
        release_gate_enterprise_adoption_slo_release_governance_attached_gate_count=(
            release_gate_enterprise_adoption_slo_release_governance.attached_release_gate_count
        ),
        release_gate_enterprise_adoption_slo_release_governance_failed_gate_count=(
            release_gate_enterprise_adoption_slo_release_governance.failed_release_gate_count
        ),
        release_gate_enterprise_adoption_slo_release_governance_review_cadence_days=(
            release_gate_enterprise_adoption_slo_release_governance.review_cadence_days
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count=(
            enterprise_adoption_slo_release_governance_drill.scenario_count
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_passed_count=(
            enterprise_adoption_slo_release_governance_drill.passed_count
        ),
        tenant_safe=tenant_safe,
        open_incident_count=open_incident_count,
        watch_incident_count=watch_incident_count,
        required_gate_count=required_gate_count,
        passed_required_gate_count=passed_required_gate_count,
        failed_required_gate_count=failed_required_gate_count,
        followup_count=len(followups),
        action_required_count=action_required_count,
        gates=gates,
        followups=followups,
        source_reports=(
            "products/registry.yaml",
            "platform/operations/reports/operating-cockpit-v1.yaml",
            "platform/delivery/reports/delivery-state-v1.yaml",
            "services/model-serving-service/service.yaml",
            "platform/operations/reports/admin-ops-dashboard-freshness-v1.yaml",
            "platform/governance/reports/model-serving-access-incident-export-v1.yaml",
            "platform/governance/reports/governance-evaluation-incident-export-v1.yaml",
            "platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml",
            "platform/operations/reports/governance-evaluation-incident-response-drill-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml",
            "platform/operations/metrics/product-readiness-freshness-live-response-metrics-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-metrics-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-trends-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-alerts-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml",
            "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1.yaml",
            "platform/intake/reports/use-case-blueprints-v1.yaml",
            "platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml",
        ),
    )


def build_response_slo_drift_alert_followups(
    response_alert_drill: ProductReadinessFreshnessResponseSloDriftAlertDrillReport,
    response_alert_calibration: (
        ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport
    ),
    response_alert_suppression_policy: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport
    ),
    response_alert_suppression_policy_drill: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport
    ),
    response_alert_suppression_policy_effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
    ),
    response_alert_suppression_policy_coverage: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport
    ),
    response_alert_suppression_policy_regression: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
    ),
    response_alert_suppression_policy_coverage_slo: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
    ),
    response_alert_suppression_policy_release_governance: (
        CoverageReleaseGovernanceReport
    ),
    response_alert_suppression_policy_release_gate_drill: (
        CoverageReleaseGateDrillReport
    ),
    response_alert_suppression_policy_release_gate_effectiveness: (
        CoverageReleaseGateEffectivenessReport
    ),
    response_alert_suppression_policy_release_gate_enterprise_pattern: (
        CoverageReleaseGateEnterprisePatternReport
    ),
    response_alert_suppression_policy_release_gate_enterprise_adoption: (
        CoverageReleaseGateEnterpriseAdoptionReport
    ),
    response_alert_suppression_policy_release_gate_enterprise_adoption_slo: (
        CoverageReleaseGateEnterpriseAdoptionSloReport
    ),
    response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport
    ),
    enterprise_adoption_slo_release_governance_drill: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport
    ),
) -> tuple[ProductReadinessFollowup, ...]:
    if response_alert_drill.drill_status != "passed":
        return (
            ProductReadinessFollowup(
                followup_id=EXERCISE_DRIFT_ALERT_DRILL_ACTION,
                title="Exercise Product Readiness response SLO drift alert drill",
                owner_role="SA AI Platform + Admin/Ops",
                priority="p2",
                followup_status="tracked",
                reason=(
                    "Product Readiness Freshness response SLO drift alerts are "
                    "configured and routed; the next hardening step is to exercise "
                    "the alert path before a watch scenario becomes a freshness "
                    "incident."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs(),
            ),
        )
    if response_alert_calibration.calibration_status != "calibrated_with_watch":
        return (
            ProductReadinessFollowup(
                followup_id=MONITOR_ALERT_CALIBRATION_ACTION,
                title="Monitor Product Readiness response SLO drift alert calibration",
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift alert drill passed; keep calibration "
                    "visible so watch-level alerts remain useful without becoming "
                    "noisy for Admin/Ops."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
                ),
            ),
        )
    if response_alert_suppression_policy.policy_status != "suppression_policy_codified":
        return (
            ProductReadinessFollowup(
                followup_id=CODIFY_ALERT_SUPPRESSION_POLICY_ACTION,
                title=(
                    "Codify Product Readiness response SLO drift alert "
                    "suppression policy"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift alert calibration is monitored and "
                    "currently quiet; codify suppression rules so future "
                    "watch-level alerts stay useful for Admin/Ops."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
                ),
            ),
        )
    if response_alert_suppression_policy_drill.drill_status != "passed":
        return (
            ProductReadinessFollowup(
                followup_id=EXERCISE_SUPPRESSION_POLICY_DRILL_ACTION,
                title=(
                    "Exercise Product Readiness response SLO drift "
                    "suppression policy"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift alert suppression policy is "
                    "codified; exercise the dedupe, cooldown and "
                    "escalation-preservation rules before broader scenario "
                    "rollout."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml",
                ),
            ),
        )
    if (
        response_alert_suppression_policy_effectiveness.monitor_status
        != "effectiveness_monitored"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=MONITOR_SUPPRESSION_POLICY_EFFECTIVENESS_ACTION,
                title=(
                    "Monitor Product Readiness response SLO drift suppression "
                    "policy effectiveness"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy drill passed; "
                    "monitor suppression volume and escalation preservation before "
                    "expanding the policy to more Product Readiness scenarios."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml",
                ),
            ),
        )
    if response_alert_suppression_policy_coverage.coverage_status != "coverage_expanded":
        return (
            ProductReadinessFollowup(
                followup_id=EXPAND_SUPPRESSION_POLICY_COVERAGE_ACTION,
                title=(
                    "Expand Product Readiness response SLO drift suppression "
                    "policy coverage"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy effectiveness "
                    "monitor is operational; expand coverage to additional "
                    "Product Readiness freshness scenarios while preserving "
                    "escalation."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
                ),
            ),
        )
    if (
        response_alert_suppression_policy_regression.regression_status
        != "regression_monitored"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=MONITOR_SUPPRESSION_POLICY_COVERAGE_REGRESSION_ACTION,
                title=(
                    "Monitor Product Readiness response SLO drift suppression "
                    "policy coverage regression"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy coverage matrix is "
                    "expanded; monitor regression so future scenario classes do "
                    "not lose noise-reduction or escalation-preservation coverage."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
                ),
            ),
        )
    if response_alert_suppression_policy_coverage_slo.slo_status != (
        "coverage_slo_published"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=PUBLISH_SUPPRESSION_POLICY_COVERAGE_SLO_ACTION,
                title=(
                    "Publish Product Readiness response SLO drift suppression "
                    "policy coverage SLO"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy coverage "
                    "regression monitor is operational; publish an owner-facing "
                    "coverage SLO so Admin/Ops can track future drift as a "
                    "managed objective."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
                ),
            ),
        )
    if (
        response_alert_suppression_policy_release_governance.release_governance_status
        != "release_governance_attached"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=(
                    ATTACH_SUPPRESSION_POLICY_COVERAGE_SLO_TO_RELEASE_GOVERNANCE_ACTION
                ),
                title=(
                    "Attach Product Readiness response SLO drift suppression "
                    "policy coverage SLO to release governance"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy coverage SLO is "
                    "published; attach it to release governance so future "
                    "Product Readiness releases cannot silently lose scenario "
                    "coverage."
                ),
                evidence_refs=response_slo_drift_alert_evidence_refs()
                + (
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
                    "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml",
                ),
            ),
        )
    release_gate_drill_evidence = response_slo_drift_alert_evidence_refs() + (
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1.yaml",
        "platform/intake/reports/use-case-blueprints-v1.yaml",
    )
    if response_alert_suppression_policy_release_gate_drill.drill_status != "passed":
        return (
            ProductReadinessFollowup(
                followup_id=(
                    EXERCISE_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_DRILL_ACTION
                ),
                title=(
                    "Exercise Product Readiness response SLO drift suppression "
                    "policy coverage release gate drill"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy coverage release "
                    "governance gate is attached; exercise the release gate drill "
                    "so future releases prove the gate blocks coverage regressions."
                ),
                evidence_refs=release_gate_drill_evidence,
            ),
        )
    if (
        response_alert_suppression_policy_release_gate_effectiveness.monitor_status
        != "effectiveness_monitored"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=(
                    MONITOR_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_EFFECTIVENESS_ACTION
                ),
                title=(
                    "Monitor Product Readiness response SLO drift suppression "
                    "policy coverage release gate effectiveness"
                ),
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy coverage release "
                    "gate drill passed; monitor release gate effectiveness so "
                    "future releases continue blocking coverage regressions."
                ),
                evidence_refs=release_gate_drill_evidence,
            ),
        )
    if (
        response_alert_suppression_policy_release_gate_enterprise_pattern.expansion_status
        != "enterprise_pattern_expanded"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=(
                    EXPAND_SUPPRESSION_POLICY_COVERAGE_RELEASE_GATE_PATTERN_ACTION
                ),
                title=(
                    "Expand Product Readiness response SLO drift suppression "
                    "policy coverage release gate pattern to enterprise use cases"
                ),
                owner_role="SA AI Platform + PO/BA + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy coverage release "
                    "gate effectiveness monitor is operational; expand the "
                    "pattern beyond Product Readiness/LMS toward cross-use-case "
                    "AI platform governance."
                ),
                evidence_refs=release_gate_drill_evidence,
            ),
        )
    if (
        response_alert_suppression_policy_release_gate_enterprise_adoption.adoption_status
        != "adoption_monitored"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=(
                    MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_ACTION
                ),
                title="Monitor enterprise release gate pattern adoption",
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "The response SLO drift suppression policy coverage release "
                    "gate pattern covers LMS and non-LMS enterprise blueprints; "
                    "monitor adoption so each promoted use case keeps release "
                    "governance evidence current."
                ),
                evidence_refs=release_gate_drill_evidence,
            ),
        )
    if (
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo.slo_status
        != "adoption_slo_published"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=(
                    PUBLISH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_ACTION
                ),
                title="Publish enterprise release gate pattern adoption SLO",
                owner_role="SA AI Platform + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "Enterprise release gate pattern adoption is monitored with "
                    "100% adopted signals; publish an owner-facing adoption SLO so "
                    "future use-case intake cannot silently drift away from the "
                    "governed release pattern."
                ),
                evidence_refs=release_gate_drill_evidence,
            ),
        )
    if (
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo_release_governance.release_governance_status
        != "enterprise_adoption_slo_release_governance_attached"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=(
                    ATTACH_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_TO_RELEASE_GOVERNANCE_ACTION
                ),
                title="Attach enterprise release gate pattern adoption SLO to governance",
                owner_role="SA AI Platform + Governance Reviewer + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "Enterprise release gate pattern adoption SLO is published; "
                    "attach it to release governance so future enterprise use-case "
                    "promotion cannot drift away from the governed release gate "
                    "pattern."
                ),
                evidence_refs=release_gate_drill_evidence,
            ),
        )
    if (
        enterprise_adoption_slo_release_governance_drill.drill_status
        != "passed"
    ):
        return (
            ProductReadinessFollowup(
                followup_id=(
                    EXERCISE_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_ACTION
                ),
                title="Exercise enterprise adoption SLO release governance drill",
                owner_role="SA AI Platform + Governance Reviewer + Admin/Ops",
                priority="p3",
                followup_status="tracked",
                reason=(
                    "Enterprise release gate pattern adoption SLO is attached to "
                    "release governance; exercise the drill so future enterprise "
                    "use-case promotions prove the gate blocks adoption drift."
                ),
                evidence_refs=release_gate_drill_evidence,
            ),
        )
    return (
        ProductReadinessFollowup(
            followup_id=(
                MONITOR_ENTERPRISE_RELEASE_GATE_PATTERN_ADOPTION_SLO_RELEASE_GOVERNANCE_EFFECTIVENESS_ACTION
            ),
            title=(
                "Monitor enterprise adoption SLO release governance "
                "effectiveness"
            ),
            owner_role="SA AI Platform + Governance Reviewer + Admin/Ops",
            priority="p3",
            followup_status="tracked",
            reason=(
                "Enterprise adoption SLO release governance drill passed; "
                "monitor effectiveness so future enterprise use-case promotions "
                "continue proving the release gate blocks adoption drift."
            ),
            evidence_refs=release_gate_drill_evidence,
        ),
    )


def build_suppression_policy_from_calibration(
    response_alert_calibration: (
        ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport
    ),
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport:
    module = import_module(SUPPRESSION_POLICY_MODULE)
    builder_name = (
        "build_product_readiness_freshness_response_slo_drift_"
        "suppression_policy_report_from_calibration"
    )
    builder = getattr(module, builder_name)
    return builder(response_alert_calibration, generated_at=generated_at)


def response_slo_drift_alert_evidence_refs() -> tuple[str, ...]:
    return (
        "services/model-serving-service/service.yaml",
        "platform/src/courseflow_ai_platform/model_serving_adapter.py",
        "platform/src/courseflow_ai_platform/product_readiness.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_incidents.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_drill.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_metrics.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_trends.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_alerts.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_alert_drill.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_alert_calibration.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_alert_suppression_policy.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_drill.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_governance.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_pattern.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance.py",
        "platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_drill.py",
        "platform/operations/metrics/product-readiness-freshness-live-response-metrics-v1.yaml",
        "platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml",
        "platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-metrics-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-trends-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-alerts-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml",
        "platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1.yaml",
        "platform/intake/reports/use-case-blueprints-v1.yaml",
        "platform/delivery/ledgers/delivery-state-ledger.yaml",
        "platform/delivery/reports/delivery-state-v1.yaml",
        "platform/operations/reports/admin-ops-dashboard-v1.html",
        "platform/operations/reports/admin-ops-dashboard-freshness-v1.yaml",
    )


def build_gate(
    *,
    gate_id: str,
    title: str,
    owner_role: str,
    passed: bool,
    reason: str,
    evidence_refs: tuple[str, ...],
) -> ProductReadinessGate:
    return ProductReadinessGate(
        gate_id=gate_id,
        title=title,
        owner_role=owner_role,
        required=True,
        gate_status="passed" if passed else "blocked",
        reason=reason,
        evidence_refs=evidence_refs,
    )


def governance_response_runbook_acceptance(
    delivery_state_report: DeliveryStateReport,
) -> tuple[bool, tuple[str, ...]]:
    for item in delivery_state_report.items:
        if item.action_id != GOVERNANCE_RESPONSE_RUNBOOK_ACTION_ID:
            continue
        evidence_refs = (
            "platform/delivery/ledgers/delivery-state-ledger.yaml",
            "platform/delivery/reports/delivery-state-v1.yaml",
            *item.evidence_refs,
        )
        return (
            item.transition_status == "applied" and item.applied_status == "accepted",
            tuple(dict.fromkeys(evidence_refs)),
        )
    return (
        False,
        (
            "platform/delivery/ledgers/delivery-state-ledger.yaml",
            "platform/delivery/reports/delivery-state-v1.yaml",
        ),
    )


def product_readiness_freshness_response_drill_acceptance(
    delivery_state_report: DeliveryStateReport,
) -> tuple[bool, tuple[str, ...]]:
    for item in delivery_state_report.items:
        if item.action_id != PRODUCT_READINESS_FRESHNESS_RESPONSE_DRILL_ACTION_ID:
            continue
        evidence_refs = (
            "platform/delivery/ledgers/delivery-state-ledger.yaml",
            "platform/delivery/reports/delivery-state-v1.yaml",
            *item.evidence_refs,
        )
        return (
            item.transition_status == "applied" and item.applied_status == "accepted",
            tuple(dict.fromkeys(evidence_refs)),
        )
    return (
        False,
        (
            "platform/delivery/ledgers/delivery-state-ledger.yaml",
            "platform/delivery/reports/delivery-state-v1.yaml",
        ),
    )


def derive_readiness_status(
    *,
    failed_required_gate_count: int,
    followup_count: int,
) -> str:
    if failed_required_gate_count:
        return "blocked"
    if followup_count:
        return "stakeholder_ready_with_followups"
    return "stakeholder_ready"


def derive_stakeholder_visibility_status(
    dashboard_freshness: AdminOpsDashboardFreshnessManifest,
    *,
    governance_response_accepted: bool,
    product_readiness_freshness_response_accepted: bool,
) -> str:
    if (
        dashboard_freshness.freshness_status == "current"
        and dashboard_freshness.dashboard_matches_generated_html
        and governance_response_accepted
        and product_readiness_freshness_response_accepted
    ):
        return "current_with_response_acceptance"
    return "attention_required"


def build_action_queue(
    gates: tuple[ProductReadinessGate, ...],
    followups: tuple[ProductReadinessFollowup, ...],
) -> dict[str, list[str]]:
    return {
        "blocked": [gate.gate_id for gate in gates if not gate.passed],
        "passed": [gate.gate_id for gate in gates if gate.passed],
        "tracked_followups": [followup.followup_id for followup in followups],
    }


def load_platform_product_metadata(ai_root: Path | str) -> tuple[str, str]:
    root = Path(ai_root)
    registry = load_yaml(root / "products" / "registry.yaml")
    platform_product = require_str(registry, "platform_product", "products registry")
    products = registry.get("products")
    if not isinstance(products, list):
        raise RegistryValidationError("products registry must define list field products")
    for row in products:
        if not isinstance(row, dict):
            continue
        product_id = require_str(row, "id", "products registry")
        if product_id == platform_product:
            return product_id, require_str(row, "name", f"product {product_id}")
    raise RegistryValidationError(
        f"products registry platform_product does not exist: {platform_product}"
    )


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_ai_platform_product_readiness_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | date | None = None,
    serving_metrics: ModelServingMetricsSnapshot | None = None,
    report: AiPlatformProductReadinessReport | None = None,
) -> dict[str, Any]:
    report_date = parse_report_date(generated_at)
    readiness_report = report or build_ai_platform_product_readiness_report(
        ai_root,
        generated_at=report_date,
        serving_metrics=serving_metrics,
    )
    return readiness_report.to_snapshot_dict(generated_at=report_date.isoformat())


def write_ai_platform_product_readiness_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | date | None = None,
    serving_metrics: ModelServingMetricsSnapshot | None = None,
    report: AiPlatformProductReadinessReport | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path else default_report_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_ai_platform_product_readiness_snapshot(
        root,
        generated_at=generated_at,
        serving_metrics=serving_metrics,
        report=report,
    )
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(snapshot, handle, sort_keys=False, allow_unicode=False)
    return target


def default_report_path(ai_root: Path) -> Path:
    return ai_root / "platform" / "product" / "reports" / f"{REPORT_ID}.yaml"


def parse_report_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RegistryValidationError(
            f"invalid product readiness report date: {value}"
        ) from exc
