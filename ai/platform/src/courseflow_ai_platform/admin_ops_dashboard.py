from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from html import escape
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.delivery_owner_views import (
    DeliveryOwnerView,
    DeliveryOwnerViewsReport,
    build_delivery_owner_views_report,
)
from courseflow_ai_platform.governance_evaluation_incidents import (
    GovernanceEvaluationIncidentExport,
    build_governance_evaluation_incident_export,
)
from courseflow_ai_platform.governance_evaluation_response_drill import (
    GovernanceEvaluationIncidentResponseDrillReport,
    build_governance_evaluation_incident_response_drill_report,
)
from courseflow_ai_platform.operating_cockpit import (
    OperatingCockpitAction,
    OperatingCockpitReport,
    build_operating_cockpit_report,
)
from courseflow_ai_platform.product_readiness_freshness import (
    AiPlatformProductReadinessFreshnessReport,
    load_ai_platform_product_readiness_freshness_report,
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
    ProductReadinessFreshnessResponseSloDriftAlertDrillReport,
    build_product_readiness_freshness_response_slo_drift_alert_drill_report,
)
from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alerts import (
    ProductReadinessFreshnessResponseSloDriftAlertReport,
    build_product_readiness_freshness_response_slo_drift_alert_report,
)
from courseflow_ai_platform.product_readiness_freshness_response_trends import (
    ProductReadinessFreshnessResponseTrendReport,
    build_product_readiness_freshness_response_trend_report,
)
from courseflow_ai_platform.serving_access_incidents import (
    ServingAccessIncidentExport,
    build_serving_access_incident_export,
)
from courseflow_ai_platform.solution_blueprint import build_solution_blueprint_report

from .product_readiness_freshness_response_slo_drift_alert_calibration import (
    ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport,
    build_product_readiness_freshness_response_slo_drift_alert_calibration_report,
)
from .product_readiness_freshness_response_slo_drift_alert_suppression_policy import (
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_report,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage import (
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report,
    build_suppression_policy_coverage_report_from_reports,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression import (
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report,
    build_suppression_policy_coverage_regression_report_from_coverage,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo import (
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report,
    build_suppression_policy_coverage_slo_report_from_regression,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_drill import (
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness import (
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report,
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
_RELEASE_GOVERNANCE_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernanceReport"
)
_RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance_report"
)
_RELEASE_GOVERNANCE_FROM_SLO_BUILDER_ATTR = (
    "build_suppression_policy_coverage_release_governance_report_from_slo"
)
_RELEASE_GATE_DRILL_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrillReport"
)
_RELEASE_GATE_DRILL_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_drill_report"
)
_RELEASE_GATE_DRILL_FROM_GOVERNANCE_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_drill_report_from_governance"
)
_RELEASE_GATE_EFFECTIVENESS_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateEffectivenessReport"
)
_RELEASE_GATE_EFFECTIVENESS_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_report"
)
_RELEASE_GATE_EFFECTIVENESS_FROM_DRILL_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_report_from_drill"
)
_ENTERPRISE_PATTERN_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterprisePatternReport"
)
_ENTERPRISE_PATTERN_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_report"
)
_ENTERPRISE_PATTERN_FROM_REPORTS_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_report_from_reports"
)
_ENTERPRISE_ADOPTION_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionReport"
)
_ENTERPRISE_ADOPTION_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_report"
)
_ENTERPRISE_ADOPTION_FROM_PATTERN_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_report_from_pattern"
)
_ENTERPRISE_ADOPTION_SLO_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReport"
)
_ENTERPRISE_ADOPTION_SLO_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_report"
)
_ENTERPRISE_ADOPTION_SLO_FROM_ADOPTION_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_report_from_adoption"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_report"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_FROM_SLO_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_report_from_slo"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_REPORT_ATTR = (
    "ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
    "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report"
)
_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_FROM_GOVERNANCE_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_"
    "report_from_governance"
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
build_coverage_release_governance_report = getattr(
    coverage_release_governance_module,
    _RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR,
)
build_coverage_release_governance_report_from_slo = getattr(
    coverage_release_governance_module,
    _RELEASE_GOVERNANCE_FROM_SLO_BUILDER_ATTR,
)
build_coverage_release_gate_drill_report = getattr(
    coverage_release_gate_drill_module,
    _RELEASE_GATE_DRILL_REPORT_BUILDER_ATTR,
)
build_coverage_release_gate_drill_report_from_governance = getattr(
    coverage_release_gate_drill_module,
    _RELEASE_GATE_DRILL_FROM_GOVERNANCE_BUILDER_ATTR,
)
build_coverage_release_gate_effectiveness_report = getattr(
    coverage_release_gate_effectiveness_module,
    _RELEASE_GATE_EFFECTIVENESS_REPORT_BUILDER_ATTR,
)
build_coverage_release_gate_effectiveness_report_from_drill = getattr(
    coverage_release_gate_effectiveness_module,
    _RELEASE_GATE_EFFECTIVENESS_FROM_DRILL_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_pattern_report = getattr(
    coverage_release_gate_enterprise_pattern_module,
    _ENTERPRISE_PATTERN_REPORT_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_pattern_report_from_reports = getattr(
    coverage_release_gate_enterprise_pattern_module,
    _ENTERPRISE_PATTERN_FROM_REPORTS_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_report = getattr(
    coverage_release_gate_enterprise_adoption_module,
    _ENTERPRISE_ADOPTION_REPORT_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_report_from_pattern = getattr(
    coverage_release_gate_enterprise_adoption_module,
    _ENTERPRISE_ADOPTION_FROM_PATTERN_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_report = getattr(
    coverage_release_gate_enterprise_adoption_slo_module,
    _ENTERPRISE_ADOPTION_SLO_REPORT_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_report_from_adoption = getattr(
    coverage_release_gate_enterprise_adoption_slo_module,
    _ENTERPRISE_ADOPTION_SLO_FROM_ADOPTION_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_release_governance_report = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_release_governance_report_from_slo = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_FROM_SLO_BUILDER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_REPORT_BUILDER_ATTR,
)
build_enterprise_adoption_slo_governance_drill_from_governance = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module,
    _ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_FROM_GOVERNANCE_BUILDER_ATTR,
)

ADMIN_OPS_OWNER_ALIASES = ("admin-ops", "admin-ops-governance")
FRESHNESS_SOURCE_REPORTS = (
    (
        "operating_cockpit",
        "platform/operations/reports/operating-cockpit-v1.yaml",
    ),
    (
        "delivery_owner_views",
        "platform/delivery/reports/delivery-owner-views-v1.yaml",
    ),
    (
        "serving_access_incident_export",
        "platform/governance/reports/model-serving-access-incident-export-v1.yaml",
    ),
    (
        "governance_evaluation_incident_export",
        "platform/governance/reports/governance-evaluation-incident-export-v1.yaml",
    ),
    (
        "governance_evaluation_response_drill",
        "platform/operations/reports/governance-evaluation-incident-response-drill-v1.yaml",
    ),
    (
        "product_readiness_freshness",
        "platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml",
    ),
    (
        "product_readiness_freshness_incident_export",
        (
            "platform/governance/reports/"
            "product-readiness-freshness-incident-export-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_drill",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-incident-response-drill-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_metrics",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-metrics-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_trends",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-trends-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_alerts",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alerts-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_alert_drill",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_alert_calibration",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_alert_suppression_policy",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_drill",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_governance",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_drill",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_pattern",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml"
        ),
    ),
    (
        "product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_drill",
        (
            "platform/operations/reports/"
            "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1.yaml"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class AdminOpsDashboardArtifact:
    generated_at: str
    platform_status: str
    delivery_status: str
    release_status: str
    serving_status: str
    serving_access_status: str
    llm_provider_ops_status: str
    llm_provider_alert_routing_status: str
    llm_provider_secret_rotation_status: str
    governance_evaluation_ops_status: str
    governance_evaluation_response_drill_status: str
    product_readiness_freshness_status: str
    product_readiness_freshness_response_drill_status: str
    product_readiness_freshness_response_metrics_status: str
    product_readiness_freshness_response_metrics_ingest_status: str
    product_readiness_freshness_response_metrics_breach_count: int
    product_readiness_freshness_response_metrics_live_observation_count: int
    product_readiness_freshness_response_metrics_max_recover_minutes: int
    product_readiness_freshness_response_trend_status: str
    product_readiness_freshness_response_trend_watch_count: int
    product_readiness_freshness_response_alert_status: str
    product_readiness_freshness_response_alert_count: int
    product_readiness_freshness_response_alert_routed_count: int
    product_readiness_freshness_response_alert_drill_status: str
    product_readiness_freshness_response_alert_drill_scenario_count: int
    product_readiness_freshness_response_alert_drill_passed_count: int
    product_readiness_freshness_response_alert_calibration_status: str
    product_readiness_freshness_response_alert_calibrated_count: int
    product_readiness_freshness_response_alert_noisy_count: int
    product_readiness_freshness_response_alert_suppression_policy_status: str
    product_readiness_freshness_response_alert_suppression_rule_count: int
    product_readiness_freshness_response_alert_suppression_active_rule_count: int
    product_readiness_freshness_response_alert_suppression_policy_drill_status: str
    product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count: int
    product_readiness_freshness_response_alert_suppression_policy_drill_passed_count: int
    product_readiness_freshness_response_alert_suppression_policy_effectiveness_status: str
    product_readiness_freshness_response_alert_suppression_policy_effective_signal_count: int
    product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct: int
    product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_status: str
    product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count: int
    product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_pct: int
    product_readiness_freshness_response_alert_suppression_policy_regression_status: str
    product_readiness_freshness_response_alert_suppression_policy_regression_check_count: int
    product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status: str
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count: int
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count: int
    product_readiness_freshness_response_alert_suppression_policy_release_governance_status: str
    product_readiness_freshness_response_alert_suppression_policy_release_gate_count: int
    product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count: int
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status: (
        str
    )
    release_gate_drill_scenario_count: int
    release_gate_drill_passed_count: int
    release_gate_effectiveness_status: str
    release_gate_effectiveness_signal_count: int
    release_gate_effective_signal_count: int
    release_gate_effectiveness_pct: int
    release_gate_enterprise_pattern_status: str
    release_gate_enterprise_pattern_blueprint_count: int
    release_gate_enterprise_pattern_non_lms_blueprint_count: int
    release_gate_enterprise_pattern_non_lms_product_count: int
    release_gate_enterprise_pattern_taxonomy_area_count: int
    release_gate_enterprise_adoption_status: str
    release_gate_enterprise_adoption_signal_count: int
    release_gate_enterprise_adopted_signal_count: int
    release_gate_enterprise_adoption_pct: int
    release_gate_enterprise_adoption_slo_status: str
    release_gate_enterprise_adoption_slo_objective_count: int
    release_gate_enterprise_adoption_slo_met_objective_count: int
    release_gate_enterprise_adoption_slo_target_pct: int
    release_gate_enterprise_adoption_slo_release_governance_status: str
    release_gate_enterprise_adoption_slo_release_governance_gate_count: int
    release_gate_enterprise_adoption_slo_release_governance_attached_gate_count: int
    release_gate_enterprise_adoption_slo_release_governance_failed_gate_count: int
    release_gate_enterprise_adoption_slo_release_governance_drill_status: str
    release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count: int
    release_gate_enterprise_adoption_slo_release_governance_drill_passed_count: int
    product_readiness_runtime_readiness_status: str
    product_readiness_runtime_status_code: int
    product_readiness_runtime_request_count: int
    product_readiness_failed_check_count: int
    owner_queue_count: int
    delivery_item_count: int
    due_soon_owner_count: int
    overloaded_owner_count: int
    open_incident_count: int
    watch_incident_count: int
    governance_evaluation_open_incident_count: int
    governance_evaluation_watch_incident_count: int
    product_readiness_freshness_open_incident_count: int
    product_readiness_freshness_watch_incident_count: int
    admin_ops_item_count: int
    admin_ops_open_incident_count: int
    html: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "adminOpsItemCount": self.admin_ops_item_count,
            "adminOpsOpenIncidentCount": self.admin_ops_open_incident_count,
            "deliveryItemCount": self.delivery_item_count,
            "deliveryStatus": self.delivery_status,
            "dueSoonOwnerCount": self.due_soon_owner_count,
            "generatedAt": self.generated_at,
            "governanceEvaluationOpsStatus": self.governance_evaluation_ops_status,
            "governanceEvaluationResponseDrillStatus": (
                self.governance_evaluation_response_drill_status
            ),
            "governanceEvaluationOpenIncidentCount": (
                self.governance_evaluation_open_incident_count
            ),
            "governanceEvaluationWatchIncidentCount": (
                self.governance_evaluation_watch_incident_count
            ),
            "productReadinessFreshnessOpenIncidentCount": (
                self.product_readiness_freshness_open_incident_count
            ),
            "productReadinessFreshnessWatchIncidentCount": (
                self.product_readiness_freshness_watch_incident_count
            ),
            "llmProviderAlertRoutingStatus": (
                self.llm_provider_alert_routing_status
            ),
            "llmProviderOpsStatus": self.llm_provider_ops_status,
            "llmProviderSecretRotationStatus": (
                self.llm_provider_secret_rotation_status
            ),
            "htmlByteCount": len(self.html.encode()),
            "openIncidentCount": self.open_incident_count,
            "overloadedOwnerCount": self.overloaded_owner_count,
            "ownerQueueCount": self.owner_queue_count,
            "platformStatus": self.platform_status,
            "productReadinessFailedCheckCount": (
                self.product_readiness_failed_check_count
            ),
            "productReadinessFreshnessStatus": (
                self.product_readiness_freshness_status
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
            "productReadinessFreshnessResponseMetricsBreachCount": (
                self.product_readiness_freshness_response_metrics_breach_count
            ),
            "productReadinessFreshnessResponseMetricsLiveObservationCount": (
                self.product_readiness_freshness_response_metrics_live_observation_count
            ),
            "productReadinessFreshnessResponseMetricsMaxRecoverMinutes": (
                self.product_readiness_freshness_response_metrics_max_recover_minutes
            ),
            "productReadinessFreshnessResponseTrendStatus": (
                self.product_readiness_freshness_response_trend_status
            ),
            "productReadinessFreshnessResponseTrendWatchCount": (
                self.product_readiness_freshness_response_trend_watch_count
            ),
            "productReadinessFreshnessResponseAlertStatus": (
                self.product_readiness_freshness_response_alert_status
            ),
            "productReadinessFreshnessResponseAlertCount": (
                self.product_readiness_freshness_response_alert_count
            ),
            "productReadinessFreshnessResponseAlertRoutedCount": (
                self.product_readiness_freshness_response_alert_routed_count
            ),
            "productReadinessFreshnessResponseAlertDrillStatus": (
                self.product_readiness_freshness_response_alert_drill_status
            ),
            "productReadinessFreshnessResponseAlertDrillScenarioCount": (
                self.product_readiness_freshness_response_alert_drill_scenario_count
            ),
            "productReadinessFreshnessResponseAlertDrillPassedCount": (
                self.product_readiness_freshness_response_alert_drill_passed_count
            ),
            "productReadinessFreshnessResponseAlertCalibrationStatus": (
                self.product_readiness_freshness_response_alert_calibration_status
            ),
            "productReadinessFreshnessResponseAlertCalibratedCount": (
                self.product_readiness_freshness_response_alert_calibrated_count
            ),
            "productReadinessFreshnessResponseAlertNoisyCount": (
                self.product_readiness_freshness_response_alert_noisy_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionRuleCount": (
                self.product_readiness_freshness_response_alert_suppression_rule_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionActiveRuleCount": (
                self.product_readiness_freshness_response_alert_suppression_active_rule_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_drill_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillScenarioCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyDrillPassedCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_drill_passed_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyEffectivenessStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_effectiveness_status
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
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_status
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
            "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_regression_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyRegressionCheckCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_regression_check_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyPassedRegressionCheckCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloObjectiveCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyCoverageSloMetObjectiveCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGovernanceStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_release_governance_status
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_release_gate_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyAttachedReleaseGateCount": (
                self.product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count
            ),
            "productReadinessFreshnessResponseAlertSuppressionPolicyReleaseGateDrillStatus": (
                self.product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status
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
                "ReleaseGateEffectivenessStatus"
            ): (
                self.release_gate_effectiveness_status
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
                "ReleaseGateEnterprisePatternStatus"
            ): (
                self.release_gate_enterprise_pattern_status
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
                "ReleaseGateEnterpriseAdoptionStatus"
            ): (
                self.release_gate_enterprise_adoption_status
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
                "ReleaseGateEnterpriseAdoptionSloStatus"
            ): (
                self.release_gate_enterprise_adoption_slo_status
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
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceStatus"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_status
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
                "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillStatus"
            ): (
                self.release_gate_enterprise_adoption_slo_release_governance_drill_status
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
            "productReadinessRuntimeReadinessStatus": (
                self.product_readiness_runtime_readiness_status
            ),
            "productReadinessRuntimeRequestCount": (
                self.product_readiness_runtime_request_count
            ),
            "productReadinessRuntimeStatusCode": (
                self.product_readiness_runtime_status_code
            ),
            "releaseStatus": self.release_status,
            "servingAccessStatus": self.serving_access_status,
            "servingStatus": self.serving_status,
            "watchIncidentCount": self.watch_incident_count,
        }


@dataclass(frozen=True, slots=True)
class AdminOpsDashboardFreshnessSource:
    source_id: str
    path: str
    report_id: str
    generated_at: str
    sha256: str
    byte_count: int
    present: bool
    current: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "byteCount": self.byte_count,
            "current": self.current,
            "generatedAt": self.generated_at,
            "path": self.path,
            "present": self.present,
            "reportId": self.report_id,
            "sha256": self.sha256,
            "sourceId": self.source_id,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "path": self.path,
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
            "present": self.present,
            "current": self.current,
        }


@dataclass(frozen=True, slots=True)
class AdminOpsDashboardFreshnessManifest:
    generated_at: str
    freshness_status: str
    dashboard_path: str
    dashboard_sha256: str
    dashboard_byte_count: int
    dashboard_present: bool
    dashboard_matches_generated_html: bool
    source_count: int
    present_source_count: int
    current_source_count: int
    stale_source_count: int
    missing_source_count: int
    sources: tuple[AdminOpsDashboardFreshnessSource, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "currentSourceCount": self.current_source_count,
            "dashboardByteCount": self.dashboard_byte_count,
            "dashboardMatchesGeneratedHtml": self.dashboard_matches_generated_html,
            "dashboardPath": self.dashboard_path,
            "dashboardPresent": self.dashboard_present,
            "dashboardSha256": self.dashboard_sha256,
            "freshnessStatus": self.freshness_status,
            "generatedAt": self.generated_at,
            "missingSourceCount": self.missing_source_count,
            "presentSourceCount": self.present_source_count,
            "sourceCount": self.source_count,
            "sources": [source.to_dict() for source in self.sources],
            "staleSourceCount": self.stale_source_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "manifest_id": "admin-ops-dashboard-freshness-v1",
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "freshness_status": self.freshness_status,
                "dashboard_path": self.dashboard_path,
                "dashboard_sha256": self.dashboard_sha256,
                "dashboard_byte_count": self.dashboard_byte_count,
                "dashboard_present": self.dashboard_present,
                "dashboard_matches_generated_html": (
                    self.dashboard_matches_generated_html
                ),
                "source_count": self.source_count,
                "present_source_count": self.present_source_count,
                "current_source_count": self.current_source_count,
                "stale_source_count": self.stale_source_count,
                "missing_source_count": self.missing_source_count,
            },
            "sources": [source.to_snapshot_dict() for source in self.sources],
        }


def build_admin_ops_dashboard(
    ai_root: Path | str,
    *,
    generated_at: str | date | None = None,
) -> AdminOpsDashboardArtifact:
    report_date = parse_report_date(generated_at)
    root = Path(ai_root)
    operating_cockpit_report = build_operating_cockpit_report(root, as_of=report_date)
    serving_access_incident_export = build_serving_access_incident_export(
        root,
        as_of=report_date,
    )
    governance_evaluation_incident_export = build_governance_evaluation_incident_export(
        root,
        as_of=report_date,
    )
    governance_evaluation_response_drill = (
        build_governance_evaluation_incident_response_drill_report(
            root,
            generated_at=report_date.isoformat(),
        )
    )
    product_readiness_freshness_report = (
        load_ai_platform_product_readiness_freshness_report(root)
    )
    product_readiness_freshness_incident_export = (
        build_product_readiness_freshness_incident_export(
            root,
            as_of=report_date,
        )
    )
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
        build_product_readiness_freshness_response_trend_report(
            root,
            generated_at=report_date.isoformat(),
            response_metrics=product_readiness_freshness_response_metrics,
        )
    )
    product_readiness_freshness_response_alerts = (
        build_product_readiness_freshness_response_slo_drift_alert_report(
            root,
            generated_at=report_date.isoformat(),
            response_trends=product_readiness_freshness_response_trends,
        )
    )
    product_readiness_freshness_response_alert_drill = (
        build_product_readiness_freshness_response_slo_drift_alert_drill_report(
            root,
            generated_at=report_date.isoformat(),
            response_alerts=product_readiness_freshness_response_alerts,
        )
    )
    product_readiness_freshness_response_alert_calibration = (
        build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
            root,
            generated_at=report_date.isoformat(),
            alert_drill=product_readiness_freshness_response_alert_drill,
        )
    )
    product_readiness_freshness_response_alert_suppression_policy = (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_report(
            root,
            generated_at=report_date.isoformat(),
            calibration=product_readiness_freshness_response_alert_calibration,
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_drill = (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report(
            root,
            generated_at=report_date.isoformat(),
            suppression_policy=(
                product_readiness_freshness_response_alert_suppression_policy
            ),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_effectiveness = (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report(
            root,
            generated_at=report_date.isoformat(),
            suppression_policy_drill=(
                product_readiness_freshness_response_alert_suppression_policy_drill
            ),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_coverage = (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report(
            root,
            generated_at=report_date.isoformat(),
            effectiveness=(
                product_readiness_freshness_response_alert_suppression_policy_effectiveness
            ),
            response_trends=product_readiness_freshness_response_trends,
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_regression = (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report(
            root,
            generated_at=report_date.isoformat(),
            coverage=product_readiness_freshness_response_alert_suppression_policy_coverage,
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo = (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report(
            root,
            generated_at=report_date.isoformat(),
            regression=(
                product_readiness_freshness_response_alert_suppression_policy_regression
            ),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_release_governance = (
        build_coverage_release_governance_report(
            root,
            generated_at=report_date.isoformat(),
            coverage_slo=(
                product_readiness_freshness_response_alert_suppression_policy_coverage_slo
            ),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill = (
        build_coverage_release_gate_drill_report(
            root,
            generated_at=report_date.isoformat(),
            release_governance=(
                product_readiness_freshness_response_alert_suppression_policy_release_governance
            ),
        )
    )
    product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness = (
        build_coverage_release_gate_effectiveness_report(
            root,
            generated_at=report_date.isoformat(),
            release_gate_drill=(
                product_readiness_freshness_response_alert_suppression_policy_release_gate_drill
            ),
        )
    )
    release_gate_enterprise_pattern_report = (
        build_coverage_release_gate_enterprise_pattern_report(
            root,
            generated_at=report_date.isoformat(),
            release_gate_effectiveness=(
                product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
            ),
            solution_blueprint=build_solution_blueprint_report(root),
        )
    )
    release_gate_enterprise_adoption_report = (
        build_coverage_release_gate_enterprise_adoption_report(
            root,
            generated_at=report_date.isoformat(),
            enterprise_pattern=release_gate_enterprise_pattern_report,
        )
    )
    release_gate_enterprise_adoption_slo_report = (
        build_coverage_release_gate_enterprise_adoption_slo_report(
            root,
            generated_at=report_date.isoformat(),
            adoption=release_gate_enterprise_adoption_report,
        )
    )
    release_gate_enterprise_adoption_slo_release_governance_report = (
        build_coverage_release_gate_enterprise_adoption_slo_release_governance_report(
            root,
            generated_at=report_date.isoformat(),
            enterprise_adoption_slo=release_gate_enterprise_adoption_slo_report,
        )
    )
    release_gate_enterprise_adoption_slo_release_governance_drill_report = (
        build_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report(
            root,
            generated_at=report_date.isoformat(),
            release_governance=(
                release_gate_enterprise_adoption_slo_release_governance_report
            ),
        )
    )
    delivery_owner_views_report = build_delivery_owner_views_report(root, as_of=report_date)
    return build_admin_ops_dashboard_from_reports(
        operating_cockpit_report=operating_cockpit_report,
        delivery_owner_views_report=delivery_owner_views_report,
        serving_access_incident_export=serving_access_incident_export,
        governance_evaluation_incident_export=governance_evaluation_incident_export,
        governance_evaluation_response_drill=governance_evaluation_response_drill,
        product_readiness_freshness_report=product_readiness_freshness_report,
        product_readiness_freshness_incident_export=(
            product_readiness_freshness_incident_export
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
        release_gate_enterprise_adoption_slo_release_governance_drill_report=(
            release_gate_enterprise_adoption_slo_release_governance_drill_report
        ),
        generated_at=report_date.isoformat(),
    )


def build_admin_ops_dashboard_from_reports(
    *,
    operating_cockpit_report: OperatingCockpitReport,
    delivery_owner_views_report: DeliveryOwnerViewsReport,
    serving_access_incident_export: ServingAccessIncidentExport,
    governance_evaluation_incident_export: GovernanceEvaluationIncidentExport | None = None,
    governance_evaluation_response_drill: (
        GovernanceEvaluationIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_report: (
        AiPlatformProductReadinessFreshnessReport | None
    ) = None,
    product_readiness_freshness_incident_export: (
        ProductReadinessFreshnessIncidentExport | None
    ) = None,
    product_readiness_freshness_response_drill: (
        ProductReadinessFreshnessIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_response_metrics: (
        ProductReadinessFreshnessResponseMetricsReport | None
    ) = None,
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
        CoverageReleaseGovernanceReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill: (
        CoverageReleaseGateDrillReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness: (
        CoverageReleaseGateEffectivenessReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern: (
        CoverageReleaseGateEnterprisePatternReport | None
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
    release_gate_enterprise_adoption_slo_release_governance_drill_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport | None
    ) = None,
    generated_at: str,
) -> AdminOpsDashboardArtifact:
    admin_ops_views = tuple(
        view
        for view in delivery_owner_views_report.views
        if view.owner_alias in ADMIN_OPS_OWNER_ALIASES
    )
    response_alert_suppression_policy_coverage = (
        product_readiness_freshness_response_alert_suppression_policy_coverage
    )
    if (
        response_alert_suppression_policy_coverage is None
        and product_readiness_freshness_response_alert_suppression_policy_effectiveness
        is not None
        and product_readiness_freshness_response_trends is not None
    ):
        response_alert_suppression_policy_coverage = (
            build_suppression_policy_coverage_report_from_reports(
                product_readiness_freshness_response_alert_suppression_policy_effectiveness,
                response_trends=product_readiness_freshness_response_trends,
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_regression = (
        product_readiness_freshness_response_alert_suppression_policy_regression
    )
    if (
        response_alert_suppression_policy_regression is None
        and response_alert_suppression_policy_coverage is not None
    ):
        response_alert_suppression_policy_regression = (
            build_suppression_policy_coverage_regression_report_from_coverage(
                response_alert_suppression_policy_coverage,
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_coverage_slo = (
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo
    )
    if (
        response_alert_suppression_policy_coverage_slo is None
        and response_alert_suppression_policy_regression is not None
    ):
        response_alert_suppression_policy_coverage_slo = (
            build_suppression_policy_coverage_slo_report_from_regression(
                response_alert_suppression_policy_regression,
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_release_governance = (
        product_readiness_freshness_response_alert_suppression_policy_release_governance
    )
    if (
        response_alert_suppression_policy_release_governance is None
        and response_alert_suppression_policy_coverage_slo is not None
    ):
        response_alert_suppression_policy_release_governance = (
            build_coverage_release_governance_report_from_slo(
                response_alert_suppression_policy_coverage_slo,
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_release_gate_drill = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_drill
    )
    if (
        response_alert_suppression_policy_release_gate_drill is None
        and response_alert_suppression_policy_release_governance is not None
    ):
        response_alert_suppression_policy_release_gate_drill = (
            build_coverage_release_gate_drill_report_from_governance(
                response_alert_suppression_policy_release_governance,
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_release_gate_effectiveness = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
    )
    if (
        response_alert_suppression_policy_release_gate_effectiveness is None
        and response_alert_suppression_policy_release_gate_drill is not None
    ):
        response_alert_suppression_policy_release_gate_effectiveness = (
            build_coverage_release_gate_effectiveness_report_from_drill(
                response_alert_suppression_policy_release_gate_drill,
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_release_gate_enterprise_pattern = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern
    )
    if (
        response_alert_suppression_policy_release_gate_enterprise_pattern is None
        and response_alert_suppression_policy_release_gate_effectiveness is not None
    ):
        response_alert_suppression_policy_release_gate_enterprise_pattern = (
            build_coverage_release_gate_enterprise_pattern_report_from_reports(
                response_alert_suppression_policy_release_gate_effectiveness,
                solution_blueprint=build_solution_blueprint_report(default_ai_root()),
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_release_gate_enterprise_adoption = (
        release_gate_enterprise_adoption_report
    )
    if (
        response_alert_suppression_policy_release_gate_enterprise_adoption is None
        and response_alert_suppression_policy_release_gate_enterprise_pattern is not None
    ):
        response_alert_suppression_policy_release_gate_enterprise_adoption = (
            build_coverage_release_gate_enterprise_adoption_report_from_pattern(
                response_alert_suppression_policy_release_gate_enterprise_pattern,
                generated_at=generated_at,
            )
        )
    response_alert_suppression_policy_release_gate_enterprise_adoption_slo = (
        release_gate_enterprise_adoption_slo_report
    )
    if (
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo
        is None
        and response_alert_suppression_policy_release_gate_enterprise_adoption
        is not None
    ):
        response_alert_suppression_policy_release_gate_enterprise_adoption_slo = (
            build_coverage_release_gate_enterprise_adoption_slo_report_from_adoption(
                response_alert_suppression_policy_release_gate_enterprise_adoption,
                generated_at=generated_at,
            )
        )
    enterprise_adoption_slo_governance = (
        release_gate_enterprise_adoption_slo_release_governance_report
    )
    if (
        enterprise_adoption_slo_governance is None
        and response_alert_suppression_policy_release_gate_enterprise_adoption_slo
        is not None
    ):
        enterprise_adoption_slo_governance = (
            build_coverage_release_gate_enterprise_adoption_slo_release_governance_report_from_slo(
                response_alert_suppression_policy_release_gate_enterprise_adoption_slo,
                generated_at=generated_at,
            )
        )
    enterprise_adoption_slo_governance_drill = (
        release_gate_enterprise_adoption_slo_release_governance_drill_report
    )
    if (
        enterprise_adoption_slo_governance_drill is None
        and enterprise_adoption_slo_governance is not None
    ):
        enterprise_adoption_slo_governance_drill = (
            build_enterprise_adoption_slo_governance_drill_from_governance(
                enterprise_adoption_slo_governance,
                generated_at=generated_at,
            )
        )
    html = render_admin_ops_dashboard_html(
        operating_cockpit_report=operating_cockpit_report,
        delivery_owner_views_report=delivery_owner_views_report,
        serving_access_incident_export=serving_access_incident_export,
        governance_evaluation_incident_export=governance_evaluation_incident_export,
        governance_evaluation_response_drill=governance_evaluation_response_drill,
        product_readiness_freshness_report=product_readiness_freshness_report,
        product_readiness_freshness_incident_export=(
            product_readiness_freshness_incident_export
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
            response_alert_suppression_policy_coverage
        ),
        product_readiness_freshness_response_alert_suppression_policy_regression=(
            response_alert_suppression_policy_regression
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo=(
            response_alert_suppression_policy_coverage_slo
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_governance=(
            response_alert_suppression_policy_release_governance
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_drill=(
            response_alert_suppression_policy_release_gate_drill
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness=(
            response_alert_suppression_policy_release_gate_effectiveness
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern=(
            response_alert_suppression_policy_release_gate_enterprise_pattern
        ),
        release_gate_enterprise_adoption_report=(
            response_alert_suppression_policy_release_gate_enterprise_adoption
        ),
        release_gate_enterprise_adoption_slo_report=(
            response_alert_suppression_policy_release_gate_enterprise_adoption_slo
        ),
        release_gate_enterprise_adoption_slo_release_governance_report=(
            enterprise_adoption_slo_governance
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_report=(
            enterprise_adoption_slo_governance_drill
        ),
        admin_ops_views=admin_ops_views,
        generated_at=generated_at,
    )
    governance_open_count = (
        governance_evaluation_incident_export.open_count
        if governance_evaluation_incident_export is not None
        else 0
    )
    governance_watch_count = (
        governance_evaluation_incident_export.watch_count
        if governance_evaluation_incident_export is not None
        else 0
    )
    product_freshness_open_count = (
        product_readiness_freshness_incident_export.open_count
        if product_readiness_freshness_incident_export is not None
        else 0
    )
    product_freshness_watch_count = (
        product_readiness_freshness_incident_export.watch_count
        if product_readiness_freshness_incident_export is not None
        else 0
    )
    return AdminOpsDashboardArtifact(
        generated_at=generated_at,
        platform_status=operating_cockpit_report.platform_status,
        delivery_status=operating_cockpit_report.delivery_status,
        release_status=operating_cockpit_report.release_status,
        serving_status=operating_cockpit_report.serving_health.status,
        serving_access_status=(
            operating_cockpit_report.serving_access_governance.status
        ),
        llm_provider_ops_status=operating_cockpit_report.llm_provider_ops.status,
        llm_provider_alert_routing_status=(
            operating_cockpit_report.llm_provider_ops.alert_routing_status
        ),
        llm_provider_secret_rotation_status=(
            operating_cockpit_report.llm_provider_ops.secret_rotation_status
        ),
        governance_evaluation_ops_status=(
            operating_cockpit_report.governance_evaluation_ops.ops_status
            if operating_cockpit_report.governance_evaluation_ops is not None
            else "not_connected"
        ),
        governance_evaluation_response_drill_status=(
            governance_evaluation_response_drill.drill_status
            if governance_evaluation_response_drill is not None
            else "not_connected"
        ),
        product_readiness_freshness_status=(
            product_readiness_freshness_report.freshness_status
            if product_readiness_freshness_report is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_drill_status=(
            product_readiness_freshness_response_drill.drill_status
            if product_readiness_freshness_response_drill is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_metrics_status=(
            product_readiness_freshness_response_metrics.response_metrics_status
            if product_readiness_freshness_response_metrics is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_metrics_ingest_status=(
            product_readiness_freshness_response_metrics.ingest_status
            if product_readiness_freshness_response_metrics is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_metrics_breach_count=(
            product_readiness_freshness_response_metrics.breach_count
            if product_readiness_freshness_response_metrics is not None
            else 0
        ),
        product_readiness_freshness_response_metrics_live_observation_count=(
            product_readiness_freshness_response_metrics.live_observation_count
            if product_readiness_freshness_response_metrics is not None
            else 0
        ),
        product_readiness_freshness_response_metrics_max_recover_minutes=(
            product_readiness_freshness_response_metrics.max_recover_minutes
            if product_readiness_freshness_response_metrics is not None
            else 0
        ),
        product_readiness_freshness_response_trend_status=(
            product_readiness_freshness_response_trends.trend_status
            if product_readiness_freshness_response_trends is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_trend_watch_count=(
            product_readiness_freshness_response_trends.watch_count
            if product_readiness_freshness_response_trends is not None
            else 0
        ),
        product_readiness_freshness_response_alert_status=(
            product_readiness_freshness_response_alerts.alert_status
            if product_readiness_freshness_response_alerts is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_count=(
            product_readiness_freshness_response_alerts.alert_count
            if product_readiness_freshness_response_alerts is not None
            else 0
        ),
        product_readiness_freshness_response_alert_routed_count=(
            product_readiness_freshness_response_alerts.routed_alert_count
            if product_readiness_freshness_response_alerts is not None
            else 0
        ),
        product_readiness_freshness_response_alert_drill_status=(
            product_readiness_freshness_response_alert_drill.drill_status
            if product_readiness_freshness_response_alert_drill is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_drill_scenario_count=(
            product_readiness_freshness_response_alert_drill.scenario_count
            if product_readiness_freshness_response_alert_drill is not None
            else 0
        ),
        product_readiness_freshness_response_alert_drill_passed_count=(
            product_readiness_freshness_response_alert_drill.passed_count
            if product_readiness_freshness_response_alert_drill is not None
            else 0
        ),
        product_readiness_freshness_response_alert_calibration_status=(
            product_readiness_freshness_response_alert_calibration.calibration_status
            if product_readiness_freshness_response_alert_calibration is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_calibrated_count=(
            product_readiness_freshness_response_alert_calibration.calibrated_count
            if product_readiness_freshness_response_alert_calibration is not None
            else 0
        ),
        product_readiness_freshness_response_alert_noisy_count=(
            product_readiness_freshness_response_alert_calibration.noisy_alert_count
            if product_readiness_freshness_response_alert_calibration is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_status=(
            (
                product_readiness_freshness_response_alert_suppression_policy.policy_status
            )
            if product_readiness_freshness_response_alert_suppression_policy
            is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_suppression_rule_count=(
            product_readiness_freshness_response_alert_suppression_policy.rule_count
            if product_readiness_freshness_response_alert_suppression_policy
            is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_active_rule_count=(
            (
                product_readiness_freshness_response_alert_suppression_policy.active_rule_count
            )
            if product_readiness_freshness_response_alert_suppression_policy
            is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_drill_status=(
            (
                product_readiness_freshness_response_alert_suppression_policy_drill.drill_status
            )
            if product_readiness_freshness_response_alert_suppression_policy_drill
            is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_suppression_policy_drill_scenario_count=(
            (
                product_readiness_freshness_response_alert_suppression_policy_drill.scenario_count
            )
            if product_readiness_freshness_response_alert_suppression_policy_drill
            is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_drill_passed_count=(
            (
                product_readiness_freshness_response_alert_suppression_policy_drill.passed_count
            )
            if product_readiness_freshness_response_alert_suppression_policy_drill
            is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_effectiveness_status=(
            (
                product_readiness_freshness_response_alert_suppression_policy_effectiveness.monitor_status
            )
            if product_readiness_freshness_response_alert_suppression_policy_effectiveness
            is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_suppression_policy_effective_signal_count=(
            (
                product_readiness_freshness_response_alert_suppression_policy_effectiveness.effective_signal_count
            )
            if product_readiness_freshness_response_alert_suppression_policy_effectiveness
            is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_suppression_effectiveness_pct=(
            (
                product_readiness_freshness_response_alert_suppression_policy_effectiveness.suppression_effectiveness_pct
            )
            if product_readiness_freshness_response_alert_suppression_policy_effectiveness
            is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_escalation_preservation_pct=(
            (
                product_readiness_freshness_response_alert_suppression_policy_effectiveness.escalation_preservation_pct
            )
            if product_readiness_freshness_response_alert_suppression_policy_effectiveness
            is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_status=(
            (
                response_alert_suppression_policy_coverage.coverage_status
            )
            if response_alert_suppression_policy_coverage is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_scenario_count=(
            (
                response_alert_suppression_policy_coverage.scenario_class_count
            )
            if response_alert_suppression_policy_coverage is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_covered_scenario_count=(
            (
                response_alert_suppression_policy_coverage.covered_scenario_count
            )
            if response_alert_suppression_policy_coverage is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_pct=(
            (
                response_alert_suppression_policy_coverage.coverage_pct
            )
            if response_alert_suppression_policy_coverage is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_regression_status=(
            (
                response_alert_suppression_policy_regression.regression_status
            )
            if response_alert_suppression_policy_regression is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_suppression_policy_regression_check_count=(
            (
                response_alert_suppression_policy_regression.regression_check_count
            )
            if response_alert_suppression_policy_regression is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_passed_regression_check_count=(
            (
                response_alert_suppression_policy_regression.passed_regression_check_count
            )
            if response_alert_suppression_policy_regression is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo_status=(
            (
                response_alert_suppression_policy_coverage_slo.slo_status
            )
            if response_alert_suppression_policy_coverage_slo is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo_objective_count=(
            (
                response_alert_suppression_policy_coverage_slo.objective_count
            )
            if response_alert_suppression_policy_coverage_slo is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo_met_count=(
            (
                response_alert_suppression_policy_coverage_slo.met_objective_count
            )
            if response_alert_suppression_policy_coverage_slo is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_governance_status=(
            (
                response_alert_suppression_policy_release_governance.release_governance_status
            )
            if response_alert_suppression_policy_release_governance is not None
            else "not_connected"
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_count=(
            (
                response_alert_suppression_policy_release_governance.release_gate_count
            )
            if response_alert_suppression_policy_release_governance is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_attached_release_gate_count=(
            (
                response_alert_suppression_policy_release_governance.attached_release_gate_count
            )
            if response_alert_suppression_policy_release_governance is not None
            else 0
        ),
        product_readiness_freshness_response_alert_suppression_policy_release_gate_drill_status=(
            (
                response_alert_suppression_policy_release_gate_drill.drill_status
            )
            if response_alert_suppression_policy_release_gate_drill is not None
            else "not_connected"
        ),
        release_gate_drill_scenario_count=(
            (
                response_alert_suppression_policy_release_gate_drill.scenario_count
            )
            if response_alert_suppression_policy_release_gate_drill is not None
            else 0
        ),
        release_gate_drill_passed_count=(
            (
                response_alert_suppression_policy_release_gate_drill.passed_count
            )
            if response_alert_suppression_policy_release_gate_drill is not None
            else 0
        ),
        release_gate_effectiveness_status=(
            (
                response_alert_suppression_policy_release_gate_effectiveness.monitor_status
            )
            if response_alert_suppression_policy_release_gate_effectiveness
            is not None
            else "not_connected"
        ),
        release_gate_effectiveness_signal_count=(
            (
                response_alert_suppression_policy_release_gate_effectiveness.signal_count
            )
            if response_alert_suppression_policy_release_gate_effectiveness
            is not None
            else 0
        ),
        release_gate_effective_signal_count=(
            (
                response_alert_suppression_policy_release_gate_effectiveness.effective_signal_count
            )
            if response_alert_suppression_policy_release_gate_effectiveness
            is not None
            else 0
        ),
        release_gate_effectiveness_pct=(
            (
                response_alert_suppression_policy_release_gate_effectiveness.release_gate_effectiveness_pct
            )
            if response_alert_suppression_policy_release_gate_effectiveness
            is not None
            else 0
        ),
        release_gate_enterprise_pattern_status=(
            (
                response_alert_suppression_policy_release_gate_enterprise_pattern.expansion_status
            )
            if response_alert_suppression_policy_release_gate_enterprise_pattern
            is not None
            else "not_connected"
        ),
        release_gate_enterprise_pattern_blueprint_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_pattern.blueprint_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_pattern
            is not None
            else 0
        ),
        release_gate_enterprise_pattern_non_lms_blueprint_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_pattern.non_lms_blueprint_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_pattern
            is not None
            else 0
        ),
        release_gate_enterprise_pattern_non_lms_product_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_pattern.non_lms_product_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_pattern
            is not None
            else 0
        ),
        release_gate_enterprise_pattern_taxonomy_area_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_pattern.taxonomy_area_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_pattern
            is not None
            else 0
        ),
        release_gate_enterprise_adoption_status=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption.adoption_status
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption
            is not None
            else "not_connected"
        ),
        release_gate_enterprise_adoption_signal_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption.signal_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption
            is not None
            else 0
        ),
        release_gate_enterprise_adopted_signal_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption.adopted_signal_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption
            is not None
            else 0
        ),
        release_gate_enterprise_adoption_pct=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption.adoption_pct
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption
            is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_status=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption_slo.slo_status
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption_slo
            is not None
            else "not_connected"
        ),
        release_gate_enterprise_adoption_slo_objective_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption_slo.objective_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption_slo
            is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_met_objective_count=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption_slo.met_objective_count
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption_slo
            is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_target_pct=(
            (
                response_alert_suppression_policy_release_gate_enterprise_adoption_slo.target_adoption_pct
            )
            if response_alert_suppression_policy_release_gate_enterprise_adoption_slo
            is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_release_governance_status=(
            enterprise_adoption_slo_governance.release_governance_status
            if enterprise_adoption_slo_governance is not None
            else "not_connected"
        ),
        release_gate_enterprise_adoption_slo_release_governance_gate_count=(
            enterprise_adoption_slo_governance.release_gate_count
            if enterprise_adoption_slo_governance is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_release_governance_attached_gate_count=(
            enterprise_adoption_slo_governance.attached_release_gate_count
            if enterprise_adoption_slo_governance is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_release_governance_failed_gate_count=(
            enterprise_adoption_slo_governance.failed_release_gate_count
            if enterprise_adoption_slo_governance is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_status=(
            enterprise_adoption_slo_governance_drill.drill_status
            if enterprise_adoption_slo_governance_drill is not None
            else "not_connected"
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_scenario_count=(
            enterprise_adoption_slo_governance_drill.scenario_count
            if enterprise_adoption_slo_governance_drill is not None
            else 0
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_passed_count=(
            enterprise_adoption_slo_governance_drill.passed_count
            if enterprise_adoption_slo_governance_drill is not None
            else 0
        ),
        product_readiness_runtime_readiness_status=(
            product_readiness_freshness_report.runtime_readiness_status
            if product_readiness_freshness_report is not None
            else "not_connected"
        ),
        product_readiness_runtime_status_code=(
            product_readiness_freshness_report.runtime_status_code
            if product_readiness_freshness_report is not None
            else 0
        ),
        product_readiness_runtime_request_count=(
            product_readiness_freshness_report.runtime_serving_request_count
            if product_readiness_freshness_report is not None
            else 0
        ),
        product_readiness_failed_check_count=(
            product_readiness_freshness_report.failed_check_count
            if product_readiness_freshness_report is not None
            else 0
        ),
        owner_queue_count=delivery_owner_views_report.owner_count,
        delivery_item_count=delivery_owner_views_report.item_count,
        due_soon_owner_count=delivery_owner_views_report.due_soon_owner_count,
        overloaded_owner_count=delivery_owner_views_report.overloaded_owner_count,
        open_incident_count=(
            serving_access_incident_export.open_count
            + governance_open_count
            + product_freshness_open_count
        ),
        watch_incident_count=serving_access_incident_export.watch_count
        + governance_watch_count
        + product_freshness_watch_count,
        governance_evaluation_open_incident_count=governance_open_count,
        governance_evaluation_watch_incident_count=governance_watch_count,
        product_readiness_freshness_open_incident_count=(
            product_freshness_open_count
        ),
        product_readiness_freshness_watch_incident_count=(
            product_freshness_watch_count
        ),
        admin_ops_item_count=sum(view.item_count for view in admin_ops_views),
        admin_ops_open_incident_count=sum(
            view.open_incident_count for view in admin_ops_views
        ),
        html=html,
    )


def write_admin_ops_dashboard(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | date | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_dashboard_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    artifact = build_admin_ops_dashboard(root, generated_at=generated_at)
    target.write_text(artifact.html, encoding="utf-8")
    return target


def build_admin_ops_dashboard_freshness_manifest(
    ai_root: Path | str,
    *,
    generated_at: str | date | None = None,
    dashboard_path: Path | str | None = None,
) -> AdminOpsDashboardFreshnessManifest:
    root = Path(ai_root)
    report_date = parse_report_date(generated_at).isoformat()
    dashboard = build_admin_ops_dashboard(root, generated_at=report_date)
    resolved_dashboard_path = (
        Path(dashboard_path) if dashboard_path is not None else default_dashboard_path(root)
    )
    dashboard_present = resolved_dashboard_path.exists()
    if dashboard_present:
        dashboard_bytes = resolved_dashboard_path.read_bytes()
        dashboard_sha256 = sha256_bytes(dashboard_bytes)
        dashboard_byte_count = len(dashboard_bytes)
    else:
        dashboard_bytes = b""
        dashboard_sha256 = ""
        dashboard_byte_count = 0

    generated_dashboard_bytes = dashboard.html.encode("utf-8")
    sources = tuple(
        build_freshness_source(
            root,
            source_id=source_id,
            relative_path=relative_path,
            expected_generated_at=report_date,
        )
        for source_id, relative_path in FRESHNESS_SOURCE_REPORTS
    )
    current_source_count = sum(1 for source in sources if source.current)
    present_source_count = sum(1 for source in sources if source.present)
    missing_source_count = len(sources) - present_source_count
    stale_source_count = sum(
        1 for source in sources if source.present and not source.current
    )
    dashboard_matches_generated_html = (
        dashboard_present
        and dashboard_sha256 == sha256_bytes(generated_dashboard_bytes)
    )
    freshness_status = determine_freshness_status(
        dashboard_present=dashboard_present,
        dashboard_matches_generated_html=dashboard_matches_generated_html,
        missing_source_count=missing_source_count,
        stale_source_count=stale_source_count,
    )
    return AdminOpsDashboardFreshnessManifest(
        generated_at=report_date,
        freshness_status=freshness_status,
        dashboard_path=relative_path_for(root, resolved_dashboard_path),
        dashboard_sha256=dashboard_sha256,
        dashboard_byte_count=dashboard_byte_count,
        dashboard_present=dashboard_present,
        dashboard_matches_generated_html=dashboard_matches_generated_html,
        source_count=len(sources),
        present_source_count=present_source_count,
        current_source_count=current_source_count,
        stale_source_count=stale_source_count,
        missing_source_count=missing_source_count,
        sources=sources,
    )


def write_admin_ops_dashboard_freshness_manifest(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | date | None = None,
    dashboard_path: Path | str | None = None,
) -> Path:
    root = Path(ai_root)
    target = (
        Path(output_path)
        if output_path is not None
        else default_freshness_manifest_path(root)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_admin_ops_dashboard_freshness_manifest(
                root,
                generated_at=generated_at,
                dashboard_path=dashboard_path,
            ).to_snapshot_dict(),
            handle,
            sort_keys=False,
        )
    return target


def write_admin_ops_dashboard_from_reports(
    output_path: Path | str,
    *,
    operating_cockpit_report: OperatingCockpitReport,
    delivery_owner_views_report: DeliveryOwnerViewsReport,
    serving_access_incident_export: ServingAccessIncidentExport,
    governance_evaluation_incident_export: GovernanceEvaluationIncidentExport | None = None,
    governance_evaluation_response_drill: (
        GovernanceEvaluationIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_report: (
        AiPlatformProductReadinessFreshnessReport | None
    ) = None,
    product_readiness_freshness_incident_export: (
        ProductReadinessFreshnessIncidentExport | None
    ) = None,
    product_readiness_freshness_response_drill: (
        ProductReadinessFreshnessIncidentResponseDrillReport | None
    ) = None,
    product_readiness_freshness_response_metrics: (
        ProductReadinessFreshnessResponseMetricsReport | None
    ) = None,
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
        CoverageReleaseGovernanceReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill: (
        CoverageReleaseGateDrillReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness: (
        CoverageReleaseGateEffectivenessReport | None
    ) = None,
    product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern: (
        CoverageReleaseGateEnterprisePatternReport | None
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
    release_gate_enterprise_adoption_slo_release_governance_drill_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport | None
    ) = None,
    generated_at: str,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    artifact = build_admin_ops_dashboard_from_reports(
        operating_cockpit_report=operating_cockpit_report,
        delivery_owner_views_report=delivery_owner_views_report,
        serving_access_incident_export=serving_access_incident_export,
        governance_evaluation_incident_export=governance_evaluation_incident_export,
        governance_evaluation_response_drill=governance_evaluation_response_drill,
        product_readiness_freshness_report=product_readiness_freshness_report,
        product_readiness_freshness_incident_export=(
            product_readiness_freshness_incident_export
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
            product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern
        ),
        release_gate_enterprise_adoption_report=release_gate_enterprise_adoption_report,
        release_gate_enterprise_adoption_slo_report=(
            release_gate_enterprise_adoption_slo_report
        ),
        release_gate_enterprise_adoption_slo_release_governance_report=(
            release_gate_enterprise_adoption_slo_release_governance_report
        ),
        release_gate_enterprise_adoption_slo_release_governance_drill_report=(
            release_gate_enterprise_adoption_slo_release_governance_drill_report
        ),
        generated_at=generated_at,
    )
    target.write_text(artifact.html, encoding="utf-8")
    return target


def render_admin_ops_dashboard_html(
    *,
    operating_cockpit_report: OperatingCockpitReport,
    delivery_owner_views_report: DeliveryOwnerViewsReport,
    serving_access_incident_export: ServingAccessIncidentExport,
    governance_evaluation_incident_export: GovernanceEvaluationIncidentExport | None,
    governance_evaluation_response_drill: (
        GovernanceEvaluationIncidentResponseDrillReport | None
    ),
    product_readiness_freshness_report: (
        AiPlatformProductReadinessFreshnessReport | None
    ),
    product_readiness_freshness_incident_export: (
        ProductReadinessFreshnessIncidentExport | None
    ),
    product_readiness_freshness_response_drill: (
        ProductReadinessFreshnessIncidentResponseDrillReport | None
    ),
    product_readiness_freshness_response_metrics: (
        ProductReadinessFreshnessResponseMetricsReport | None
    ),
    product_readiness_freshness_response_trends: (
        ProductReadinessFreshnessResponseTrendReport | None
    ),
    product_readiness_freshness_response_alerts: (
        ProductReadinessFreshnessResponseSloDriftAlertReport | None
    ),
    product_readiness_freshness_response_alert_drill: (
        ProductReadinessFreshnessResponseSloDriftAlertDrillReport | None
    ),
    product_readiness_freshness_response_alert_calibration: (
        ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport | None
    ),
    product_readiness_freshness_response_alert_suppression_policy: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_drill: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_effectiveness: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
        | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_coverage: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport
        | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_regression: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
        | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_coverage_slo: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
        | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_release_governance: (
        CoverageReleaseGovernanceReport | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill: (
        CoverageReleaseGateDrillReport | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness: (
        CoverageReleaseGateEffectivenessReport | None
    ),
    product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern: (
        CoverageReleaseGateEnterprisePatternReport | None
    ),
    release_gate_enterprise_adoption_report: (
        CoverageReleaseGateEnterpriseAdoptionReport | None
    ),
    release_gate_enterprise_adoption_slo_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReport | None
    ),
    release_gate_enterprise_adoption_slo_release_governance_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport | None
    ),
    release_gate_enterprise_adoption_slo_release_governance_drill_report: (
        CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport
        | None
    ),
    admin_ops_views: tuple[DeliveryOwnerView, ...],
    generated_at: str,
) -> str:
    governance_open_count = (
        governance_evaluation_incident_export.open_count
        if governance_evaluation_incident_export is not None
        else 0
    )
    product_freshness_open_count = (
        product_readiness_freshness_incident_export.open_count
        if product_readiness_freshness_incident_export is not None
        else 0
    )
    release_gate_effectiveness = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
    )
    release_gate_effectiveness_status = (
        release_gate_effectiveness.monitor_status
        if release_gate_effectiveness is not None
        else "not_connected"
    )
    release_gate_enterprise_pattern = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern
    )
    release_gate_enterprise_pattern_status = (
        release_gate_enterprise_pattern.expansion_status
        if release_gate_enterprise_pattern is not None
        else "not_connected"
    )
    release_gate_enterprise_adoption = (
        release_gate_enterprise_adoption_report
    )
    release_gate_enterprise_adoption_status = (
        release_gate_enterprise_adoption.adoption_status
        if release_gate_enterprise_adoption is not None
        else "not_connected"
    )
    release_gate_enterprise_adoption_slo = (
        release_gate_enterprise_adoption_slo_report
    )
    release_gate_enterprise_adoption_slo_status = (
        release_gate_enterprise_adoption_slo.slo_status
        if release_gate_enterprise_adoption_slo is not None
        else "not_connected"
    )
    release_gate_enterprise_adoption_slo_release_governance = (
        release_gate_enterprise_adoption_slo_release_governance_report
    )
    release_gate_enterprise_adoption_slo_release_governance_status = (
        release_gate_enterprise_adoption_slo_release_governance.release_governance_status
        if release_gate_enterprise_adoption_slo_release_governance is not None
        else "not_connected"
    )
    release_gate_enterprise_adoption_slo_release_governance_drill = (
        release_gate_enterprise_adoption_slo_release_governance_drill_report
    )
    release_gate_enterprise_adoption_slo_release_governance_drill_status = (
        release_gate_enterprise_adoption_slo_release_governance_drill.drill_status
        if release_gate_enterprise_adoption_slo_release_governance_drill is not None
        else "not_connected"
    )
    status_cards = (
        ("Platform", operating_cockpit_report.platform_status),
        ("Delivery", operating_cockpit_report.delivery_status),
        ("Release", operating_cockpit_report.release_status),
        ("Serving", operating_cockpit_report.serving_health.status),
        (
            "Access",
            operating_cockpit_report.serving_access_governance.status,
        ),
        ("LLM Providers", operating_cockpit_report.llm_provider_ops.status),
        (
            "LLM Alerts",
            operating_cockpit_report.llm_provider_ops.alert_routing_status,
        ),
        (
            "LLM Secrets",
            operating_cockpit_report.llm_provider_ops.secret_rotation_status,
        ),
        (
            "Governance Eval",
            operating_cockpit_report.governance_evaluation_ops.ops_status
            if operating_cockpit_report.governance_evaluation_ops is not None
            else "not_connected",
        ),
        (
            "Gov Eval Runbook",
            governance_evaluation_response_drill.drill_status
            if governance_evaluation_response_drill is not None
            else "not_connected",
        ),
        (
            "Product Freshness",
            product_readiness_freshness_report.freshness_status
            if product_readiness_freshness_report is not None
            else "not_connected",
        ),
        (
            "Product Runbook",
            product_readiness_freshness_response_drill.drill_status
            if product_readiness_freshness_response_drill is not None
            else "not_connected",
        ),
        (
            "Product Metrics",
            product_readiness_freshness_response_metrics.response_metrics_status
            if product_readiness_freshness_response_metrics is not None
            else "not_connected",
        ),
        (
            "Product Metrics Ingest",
            product_readiness_freshness_response_metrics.ingest_status
            if product_readiness_freshness_response_metrics is not None
            else "not_connected",
        ),
        (
            "Product Trend",
            product_readiness_freshness_response_trends.trend_status
            if product_readiness_freshness_response_trends is not None
            else "not_connected",
        ),
        (
            "Product Alerts",
            product_readiness_freshness_response_alerts.alert_status
            if product_readiness_freshness_response_alerts is not None
            else "not_connected",
        ),
        (
            "Product Alert Drill",
            product_readiness_freshness_response_alert_drill.drill_status
            if product_readiness_freshness_response_alert_drill is not None
            else "not_connected",
        ),
        (
            "Product Alert Calibration",
            (
                product_readiness_freshness_response_alert_calibration.calibration_status
                if product_readiness_freshness_response_alert_calibration is not None
                else "not_connected"
            ),
        ),
        (
            "Product Alert Policy",
            (
                product_readiness_freshness_response_alert_suppression_policy.policy_status
                if product_readiness_freshness_response_alert_suppression_policy
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy Drill",
            (
                product_readiness_freshness_response_alert_suppression_policy_drill.drill_status
                if product_readiness_freshness_response_alert_suppression_policy_drill
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy Monitor",
            (
                product_readiness_freshness_response_alert_suppression_policy_effectiveness.monitor_status
                if product_readiness_freshness_response_alert_suppression_policy_effectiveness
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy Coverage",
            (
                product_readiness_freshness_response_alert_suppression_policy_coverage.coverage_status
                if product_readiness_freshness_response_alert_suppression_policy_coverage
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy Regression",
            (
                product_readiness_freshness_response_alert_suppression_policy_regression.regression_status
                if product_readiness_freshness_response_alert_suppression_policy_regression
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy SLO",
            (
                product_readiness_freshness_response_alert_suppression_policy_coverage_slo.slo_status
                if product_readiness_freshness_response_alert_suppression_policy_coverage_slo
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy Release Gate",
            (
                product_readiness_freshness_response_alert_suppression_policy_release_governance.release_governance_status
                if product_readiness_freshness_response_alert_suppression_policy_release_governance
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy Gate Drill",
            (
                product_readiness_freshness_response_alert_suppression_policy_release_gate_drill.drill_status
                if product_readiness_freshness_response_alert_suppression_policy_release_gate_drill
                is not None
                else "not_connected"
            ),
        ),
        (
            "Product Policy Gate Effectiveness",
            release_gate_effectiveness_status,
        ),
        (
            "Product Policy Enterprise Pattern",
            release_gate_enterprise_pattern_status,
        ),
        (
            "Product Policy Enterprise Adoption",
            release_gate_enterprise_adoption_status,
        ),
        (
            "Product Policy Enterprise Adoption SLO",
            release_gate_enterprise_adoption_slo_status,
        ),
        (
            "Product Policy Enterprise Adoption SLO Governance",
            release_gate_enterprise_adoption_slo_release_governance_status,
        ),
        (
            "Product Policy Enterprise Adoption SLO Governance Drill",
            release_gate_enterprise_adoption_slo_release_governance_drill_status,
        ),
        (
            "Open Incidents",
            str(
                serving_access_incident_export.open_count
                + governance_open_count
                + product_freshness_open_count
            ),
        ),
        ("Gov Eval Incidents", str(governance_open_count)),
        ("Product Incidents", str(product_freshness_open_count)),
        ("Owner Queues", str(delivery_owner_views_report.owner_count)),
        ("Due Soon Owners", str(delivery_owner_views_report.due_soon_owner_count)),
    )
    body = "\n".join(
        (
            render_status_cards(status_cards),
            render_operating_summary(operating_cockpit_report),
            render_admin_ops_owner_queues(admin_ops_views),
            render_incident_panel(serving_access_incident_export),
            render_governance_evaluation_incident_panel(
                governance_evaluation_incident_export
            ),
            render_governance_evaluation_response_drill_panel(
                governance_evaluation_response_drill
            ),
            render_product_readiness_freshness_panel(
                product_readiness_freshness_report
            ),
            render_product_readiness_freshness_incident_panel(
                product_readiness_freshness_incident_export
            ),
            render_product_readiness_freshness_response_drill_panel(
                product_readiness_freshness_response_drill
            ),
            render_product_readiness_freshness_response_metrics_panel(
                product_readiness_freshness_response_metrics
            ),
            render_product_readiness_freshness_response_trend_panel(
                product_readiness_freshness_response_trends
            ),
            render_product_readiness_freshness_response_alert_panel(
                product_readiness_freshness_response_alerts
            ),
            render_product_readiness_freshness_response_alert_drill_panel(
                product_readiness_freshness_response_alert_drill
            ),
            render_product_readiness_freshness_response_alert_calibration_panel(
                product_readiness_freshness_response_alert_calibration
            ),
            render_product_readiness_freshness_response_alert_suppression_policy_panel(
                product_readiness_freshness_response_alert_suppression_policy
            ),
            render_product_readiness_freshness_response_suppression_policy_drill_panel(
                product_readiness_freshness_response_alert_suppression_policy_drill
            ),
            render_product_readiness_freshness_response_suppression_policy_effectiveness_panel(
                product_readiness_freshness_response_alert_suppression_policy_effectiveness
            ),
            render_product_readiness_freshness_response_suppression_policy_coverage_panel(
                product_readiness_freshness_response_alert_suppression_policy_coverage
            ),
            render_product_readiness_freshness_response_suppression_policy_regression_panel(
                product_readiness_freshness_response_alert_suppression_policy_regression
            ),
            render_product_readiness_freshness_response_suppression_policy_coverage_slo_panel(
                product_readiness_freshness_response_alert_suppression_policy_coverage_slo
            ),
            render_product_readiness_freshness_response_suppression_policy_release_governance_panel(
                product_readiness_freshness_response_alert_suppression_policy_release_governance
            ),
            render_product_readiness_freshness_response_suppression_policy_release_gate_drill_panel(
                product_readiness_freshness_response_alert_suppression_policy_release_gate_drill
            ),
            render_product_readiness_freshness_response_suppression_policy_release_gate_effectiveness_panel(
                product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
            ),
            render_product_readiness_freshness_response_suppression_policy_enterprise_pattern_panel(
                product_readiness_freshness_response_alert_suppression_policy_release_gate_enterprise_pattern
            ),
            render_product_readiness_freshness_response_suppression_policy_enterprise_adoption_panel(
                release_gate_enterprise_adoption_report
            ),
            render_product_readiness_freshness_response_suppression_policy_enterprise_adoption_slo_panel(
                release_gate_enterprise_adoption_slo_report
            ),
            render_enterprise_adoption_slo_release_governance_panel(
                release_gate_enterprise_adoption_slo_release_governance_report
            ),
            render_enterprise_adoption_slo_release_governance_drill_panel(
                release_gate_enterprise_adoption_slo_release_governance_drill_report
            ),
            render_action_panel(operating_cockpit_report.actions),
        )
    )
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            (
                "  <meta name=\"viewport\" "
                'content="width=device-width, initial-scale=1">'
            ),
            "  <title>AI Platform Admin/Ops Dashboard</title>",
            f"  <style>{DASHBOARD_CSS}</style>",
            "</head>",
            "<body>",
            "  <main>",
            '    <header class="masthead">',
            "      <div>",
            "        <p>CourseFlow Enterprise AI Platform</p>",
            "        <h1>Admin/Ops Dashboard</h1>",
            "      </div>",
            f"      <time>{html_text(generated_at)}</time>",
            "    </header>",
            body,
            "  </main>",
            "</body>",
            "</html>",
            "",
        )
    )


def render_status_cards(cards: tuple[tuple[str, str], ...]) -> str:
    items = "\n".join(
        "\n".join(
            (
                '      <article class="metric-card">',
                f"        <span>{html_text(label)}</span>",
                f'        <strong class="{status_class(value)}">{html_text(value)}</strong>',
                "      </article>",
            )
        )
        for label, value in cards
    )
    return "\n".join(
        (
            '    <section class="metric-grid" aria-label="Platform status">',
            items,
            "    </section>",
        )
    )


def render_operating_summary(report: OperatingCockpitReport) -> str:
    governance_evaluation_ops = report.governance_evaluation_ops
    rows = (
        ("Products", report.product_count),
        ("Use cases", report.use_case_count),
        ("Non-LMS use cases", report.non_lms_use_case_count),
        ("Coverage modules", report.coverage_module_count),
        (
            "Evaluations passed",
            (
                f"{report.evaluation_required_passed_count}/"
                f"{report.evaluation_required_count}"
            ),
        ),
        ("Control-plane actions", report.action_count),
        ("Serving requests", report.serving_health.request_count),
        ("Serving audit failures", report.serving_health.audit_failure_count),
        ("LLM provider rollout", report.llm_provider_ops.rollout_status),
        ("LLM provider alerts", report.llm_provider_ops.alert_routing_status),
        ("LLM provider secret rotation", report.llm_provider_ops.secret_rotation_status),
        ("LLM provider alert routes", report.llm_provider_ops.alert_route_count),
        (
            "LLM provider secret bindings",
            report.llm_provider_ops.secret_manager_binding_count,
        ),
        (
            "LLM provider rotation evidence",
            report.llm_provider_ops.rotation_evidence_provider_count,
        ),
        ("LLM provider blocked", report.llm_provider_ops.blocked_provider_count),
        (
            "LLM provider cost micros",
            report.llm_provider_ops.total_estimated_cost_micros,
        ),
        ("LLM provider max p95 ms", report.llm_provider_ops.max_p95_latency_ms),
        (
            "Governance evaluation",
            governance_evaluation_ops.ops_status
            if governance_evaluation_ops is not None
            else "not_connected",
        ),
        (
            "Governance assessments",
            governance_evaluation_ops.assessment_count
            if governance_evaluation_ops is not None
            else 0,
        ),
        (
            "Governance review required",
            governance_evaluation_ops.review_required_count
            if governance_evaluation_ops is not None
            else 0,
        ),
        (
            "Governance blocked",
            governance_evaluation_ops.blocked_count
            if governance_evaluation_ops is not None
            else 0,
        ),
        (
            "Governance identifier rejects",
            governance_evaluation_ops.direct_identifier_rejection_count
            if governance_evaluation_ops is not None
            else 0,
        ),
        (
            "Governance secret rejects",
            governance_evaluation_ops.secret_value_rejection_count
            if governance_evaluation_ops is not None
            else 0,
        ),
    )
    return render_key_value_section("Operating Cockpit", rows)


def render_admin_ops_owner_queues(views: tuple[DeliveryOwnerView, ...]) -> str:
    if not views:
        return render_empty_section("Admin/Ops Owner Queues")
    view_cards = "\n".join(render_owner_view(view) for view in views)
    return "\n".join(
        (
            '    <section class="panel">',
            "      <h2>Admin/Ops Owner Queues</h2>",
            f'      <div class="owner-grid">{view_cards}</div>',
            "    </section>",
        )
    )


def render_owner_view(view: DeliveryOwnerView) -> str:
    item_rows = "\n".join(
        render_owner_item(
            item.backlog_id,
            item.priority,
            item.status,
            item.sla_status,
            item.due_at,
            safe_title(item.title),
        )
        for item in view.items[:5]
    ) or '<li class="empty-row">No delivery work</li>'
    incident_rows = "\n".join(
        render_incident_row(
            incident.incident_id,
            incident.severity,
            incident.condition,
            incident.action,
            incident.application_ref,
        )
        for incident in view.incidents[:5]
    ) or '<li class="empty-row">No open P0/P1 incidents</li>'
    return "\n".join(
        (
            '        <article class="owner-card">',
            f"          <h3>{html_text(view.owner_alias)}</h3>",
            '          <div class="mini-metrics">',
            f"            <span>{view.item_count} items</span>",
            f"            <span>{view.due_soon_count} due soon</span>",
            f"            <span>{view.open_incident_count} incidents</span>",
            "          </div>",
            '          <h4>Delivery work</h4>',
            f'          <ul class="work-list">{item_rows}</ul>',
            '          <h4>Incident handoffs</h4>',
            f'          <ul class="work-list incident-list">{incident_rows}</ul>',
            "        </article>",
        )
    )


def render_incident_panel(export: ServingAccessIncidentExport) -> str:
    rows = "\n".join(
        render_incident_row(
            incident.incident_id,
            incident.severity,
            incident.condition,
            incident.action,
            incident.application_ref,
        )
        for incident in export.incidents[:8]
    ) or '<li class="empty-row">No serving-access incidents</li>'
    summary = (
        ("Open", export.open_count),
        ("Watch", export.watch_count),
        ("P0", export.p0_count),
        ("P1", export.p1_count),
        ("P2", export.p2_count),
        ("Tenant safe", str(export.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Serving Access Incident Export</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_governance_evaluation_incident_panel(
    export: GovernanceEvaluationIncidentExport | None,
) -> str:
    if export is None:
        return render_empty_section("Governance Evaluation Incident Export")
    rows = "\n".join(
        render_incident_row(
            incident.incident_id,
            incident.severity,
            incident.condition,
            incident.action,
            incident.application_ref,
        )
        for incident in export.incidents[:8]
    ) or '<li class="empty-row">No repeated governance evaluation incidents</li>'
    summary = (
        ("Open", export.open_count),
        ("Watch", export.watch_count),
        ("P0", export.p0_count),
        ("P1", export.p1_count),
        ("Repeated failures", export.repeated_failure_count),
        ("Failure streak", export.consecutive_failure_count),
        ("Threshold", export.repeated_failure_threshold),
        ("Tenant safe", str(export.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Governance Evaluation Incident Export</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_governance_evaluation_response_drill_panel(
    report: GovernanceEvaluationIncidentResponseDrillReport | None,
) -> str:
    if report is None:
        return render_empty_section("Governance Evaluation Response Drill")
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    f'              <span class="badge {status_class(scenario.expected_severity)}">'
                    f"{html_text(scenario.expected_severity)}</span>"
                ),
                f"              <strong>{html_text(scenario.condition)}</strong>",
                f"              <span>{html_text(scenario.expected_action)}</span>",
                (
                    f"              <small>{html_text(scenario.scenario_id)} / "
                    f"{html_text('passed' if scenario.passed else 'blocked')}</small>"
                ),
                "            </li>",
            )
        )
        for scenario in report.scenarios
    ) or '<li class="empty-row">No response drill scenarios</li>'
    summary = (
        ("Status", report.drill_status),
        ("Scenarios", report.scenario_count),
        ("Passed", report.passed_count),
        ("Failed", report.failed_count),
        ("P0 drills", report.p0_scenario_count),
        ("P1 drills", report.p1_scenario_count),
        ("Runbook steps", report.response_step_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Governance Evaluation Response Drill</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_panel(
    report: AiPlatformProductReadinessFreshnessReport | None,
) -> str:
    if report is None:
        return render_empty_section("Product Readiness Freshness")
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    f'              <span class="badge {status_class(check.check_status)}">'
                    f"{html_text(check.check_status)}</span>"
                ),
                f"              <strong>{html_text(check.check_id)}</strong>",
                f"              <span>{html_text(check.reason)}</span>",
                "            </li>",
            )
        )
        for check in report.checks
    ) or '<li class="empty-row">No product readiness freshness checks</li>'
    summary = (
        ("Freshness", report.freshness_status),
        ("Runtime readiness", report.runtime_readiness_status),
        ("Route", report.route_path),
        ("Route status", report.runtime_status_code),
        ("Runtime requests", report.runtime_serving_request_count),
        ("Runtime audit records", report.runtime_serving_audit_record_count),
        ("Runtime errors", report.runtime_serving_error_count),
        ("Runtime audit failures", report.runtime_serving_audit_failure_count),
        ("Failed checks", report.failed_check_count),
        (
            "Required AI spectrum",
            (
                f"{report.covered_required_spectrum_count}/"
                f"{report.required_spectrum_count}"
            ),
        ),
        ("Extended modules", report.extended_module_count),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Product Readiness Freshness</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_incident_panel(
    export: ProductReadinessFreshnessIncidentExport | None,
) -> str:
    if export is None:
        return render_empty_section("Product Readiness Freshness Incident Export")
    rows = "\n".join(
        render_incident_row(
            incident.incident_id,
            incident.severity,
            incident.condition,
            incident.action,
            incident.application_ref,
        )
        for incident in export.incidents[:8]
    ) or '<li class="empty-row">No product-readiness freshness incidents</li>'
    summary = (
        ("Freshness", export.freshness_status),
        ("Open", export.open_count),
        ("Watch", export.watch_count),
        ("P0", export.p0_count),
        ("P1", export.p1_count),
        ("P2", export.p2_count),
        ("Tenant safe", str(export.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Product Readiness Freshness Incident Export</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_drill_panel(
    report: ProductReadinessFreshnessIncidentResponseDrillReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response Drill"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    f'              <span class="badge {status_class(scenario.expected_severity)}">'
                    f"{html_text(scenario.expected_severity)}</span>"
                ),
                f"              <strong>{html_text(scenario.condition)}</strong>",
                f"              <span>{html_text(scenario.expected_action)}</span>",
                (
                    f"              <small>{html_text(scenario.scenario_id)} / "
                    f"{html_text('passed' if scenario.passed else 'blocked')}</small>"
                ),
                "            </li>",
            )
        )
        for scenario in report.scenarios
    ) or '<li class="empty-row">No product readiness response drill scenarios</li>'
    summary = (
        ("Status", report.drill_status),
        ("Scenarios", report.scenario_count),
        ("Passed", report.passed_count),
        ("Failed", report.failed_count),
        ("P0 drills", report.p0_scenario_count),
        ("P1 drills", report.p1_scenario_count),
        ("Runbook steps", report.response_step_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Product Readiness Freshness Response Drill</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_metrics_panel(
    report: ProductReadinessFreshnessResponseMetricsReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response Metrics"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    f'              <span class="badge {status_class(item.metric_status)}">'
                    f"{html_text(item.metric_status)}</span>"
                ),
                f"              <strong>{html_text(item.condition)}</strong>",
                (
                    f"              <span>{item.recover_minutes}/"
                    f"{item.recover_slo_minutes} min recovery</span>"
                ),
                (
                    f"              <small>{html_text(item.scenario_id)} / "
                    f"{html_text(item.severity)}</small>"
                ),
                "            </li>",
            )
        )
        for item in report.items
    ) or '<li class="empty-row">No product readiness response metrics</li>'
    summary = (
        ("Status", report.response_metrics_status),
        ("Ingest", report.ingest_status),
        ("Measured", report.measured_count),
        ("Live observations", report.live_observation_count),
        ("Synthetic observations", report.synthetic_observation_count),
        ("Missing live observations", report.missing_live_observation_count),
        ("Breaches", report.breach_count),
        ("Max ack min", report.max_acknowledge_minutes),
        ("Max recover min", report.max_recover_minutes),
        ("Max close min", report.max_close_minutes),
        ("Avg recover min", report.average_recover_minutes),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Product Readiness Freshness Response Metrics</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_trend_panel(
    report: ProductReadinessFreshnessResponseTrendReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response Trends"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    f'              <span class="badge {status_class(trend.trend_status)}">'
                    f"{html_text(trend.trend_status)}</span>"
                ),
                f"              <strong>{html_text(trend.owner_role)}</strong>",
                (
                    f"              <span>{trend.watch_count} watch / "
                    f"{trend.breach_count} breach</span>"
                ),
                (
                    f"              <small>{trend.scenario_count} scenarios, "
                    f"{trend.max_recover_slo_usage_pct}% max recover budget</small>"
                ),
                "            </li>",
            )
        )
        for trend in report.owner_trends
    ) or '<li class="empty-row">No response SLO owner trends</li>'
    scenario_rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    f'              <span class="badge {status_class(trend.trend_status)}">'
                    f"{html_text(trend.trend_status)}</span>"
                ),
                f"              <strong>{html_text(trend.condition)}</strong>",
                (
                    f"              <span>{trend.recover_slo_usage_pct}% recover / "
                    f"{trend.close_slo_usage_pct}% close budget</span>"
                ),
                (
                    f"              <small>{html_text(trend.owner_role)} / "
                    f"{html_text(trend.severity)}</small>"
                ),
                "            </li>",
            )
        )
        for trend in report.scenario_trends
    ) or '<li class="empty-row">No response SLO scenario trends</li>'
    summary = (
        ("Status", report.trend_status),
        ("Metrics", report.metrics_status),
        ("Ingest", report.ingest_status),
        ("Owners", report.owner_count),
        ("Scenarios", report.scenario_class_count),
        ("Live observations", report.live_observation_count),
        ("Watch", report.watch_count),
        ("Breaches", report.breach_count),
        ("Max recover budget", f"{report.max_recover_slo_usage_pct}%"),
        ("Max close budget", f"{report.max_close_slo_usage_pct}%"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Product Readiness Freshness Response Trends</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            f'        <ul class="work-list incident-list">{scenario_rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_alert_panel(
    report: ProductReadinessFreshnessResponseSloDriftAlertReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Alerts"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    f'              <span class="badge {status_class(alert.alert_status)}">'
                    f"{html_text(alert.alert_status)}</span>"
                ),
                f"              <strong>{html_text(alert.condition)}</strong>",
                (
                    f"              <span>{html_text(alert.route)} / "
                    f"{html_text(alert.action)}</span>"
                ),
                (
                    f"              <small>{html_text(alert.alert_severity)} alert, "
                    f"{alert.trigger_usage_pct}% {html_text(alert.trigger_metric)} budget</small>"
                ),
                "            </li>",
            )
        )
        for alert in report.alerts
    ) or '<li class="empty-row">No response SLO drift alerts routed</li>'
    summary = (
        ("Status", report.alert_status),
        ("Trend", report.trend_status),
        ("Watch scenarios", report.watch_count),
        ("Alerts", report.alert_count),
        ("Routed", report.routed_alert_count),
        ("P0 alerts", report.p0_alert_count),
        ("P1 alerts", report.p1_alert_count),
        ("Max trigger usage", f"{report.max_trigger_usage_pct}%"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Product Readiness Freshness Response SLO Drift Alerts</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_alert_drill_panel(
    report: ProductReadinessFreshnessResponseSloDriftAlertDrillReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Alert Drill"
        )
    passed_status = str(report.passed_count == report.scenario_count).lower()
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(scenario.passed).lower())}\">"
                    f"{html_text(str(scenario.passed).lower())}</span>"
                ),
                f"              <strong>{html_text(scenario.condition)}</strong>",
                (
                    f"              <span>{html_text(scenario.observed_route)} / "
                    f"{html_text(scenario.observed_action)}</span>"
                ),
                (
                    f"              <small>{scenario.trigger_usage_pct}% "
                    f"{html_text(scenario.trigger_metric)} budget replayed</small>"
                ),
                "            </li>",
            )
        )
        for scenario in report.scenarios
    ) or '<li class="empty-row">No response SLO drift alert drill scenarios</li>'
    summary = (
        ("Status", report.drill_status),
        ("Alert status", report.alert_status),
        ("Alerts", report.alert_count),
        ("Routed", report.routed_alert_count),
        ("Scenarios", report.scenario_count),
        ("Passed", report.passed_count),
        ("Failed", report.failed_count),
        ("Max trigger usage", f"{report.max_trigger_usage_pct}%"),
        ("Tenant safe", str(report.tenant_safe).lower()),
        ("All passed", passed_status),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            "        <h2>Product Readiness Freshness Response SLO Drift Alert Drill</h2>",
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_alert_calibration_panel(
    report: ProductReadinessFreshnessResponseSloDriftAlertCalibrationReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Alert Calibration"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(item.calibration_status)}\">"
                    f"{html_text(item.calibration_status)}</span>"
                ),
                f"              <strong>{html_text(item.condition)}</strong>",
                (
                    f"              <span>{html_text(item.noise_status)} / "
                    f"{html_text(item.escalation_status)}</span>"
                ),
                (
                    f"              <small>{item.margin_pct}% margin over "
                    f"{item.threshold_pct}% threshold</small>"
                ),
                "            </li>",
            )
        )
        for item in report.items
    ) or '<li class="empty-row">No response SLO drift alert calibrations</li>'
    summary = (
        ("Status", report.calibration_status),
        ("Drill", report.drill_status),
        ("Alerts", report.alert_count),
        ("Routed", report.routed_alert_count),
        ("Scenarios", report.scenario_count),
        ("Calibrated", report.calibrated_count),
        ("Failed", report.failed_count),
        ("Noisy", report.noisy_alert_count),
        ("Under threshold", report.under_threshold_count),
        ("Escalation required", report.escalation_required_count),
        ("Max margin", f"{report.max_margin_pct}%"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Alert Calibration</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_alert_suppression_policy_panel(
    report: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Alert Suppression Policy"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(rule.rule_status)}\">"
                    f"{html_text(rule.rule_status)}</span>"
                ),
                f"              <strong>{html_text(rule.condition)}</strong>",
                (
                    f"              <span>{html_text(rule.policy_mode)} / "
                    f"{html_text(rule.route)}</span>"
                ),
                (
                    f"              <small>{rule.dedupe_window_minutes}m dedupe, "
                    f"{rule.cooldown_minutes}m cooldown, "
                    f"{rule.escalation_floor_pct}% escalation floor</small>"
                ),
                "            </li>",
            )
        )
        for rule in report.rules
    ) or '<li class="empty-row">No response SLO drift suppression policies</li>'
    summary = (
        ("Status", report.policy_status),
        ("Calibration", report.calibration_status),
        ("Rules", report.rule_count),
        ("Active", report.active_rule_count),
        ("Failed", report.failed_rule_count),
        ("Dedupe window", f"{report.dedupe_window_minutes}m"),
        ("Cooldown", f"{report.cooldown_minutes}m"),
        ("Escalation floor", f"{report.escalation_floor_pct}%"),
        ("Preserve escalation", report.preserve_escalation_count),
        ("Suppress under threshold", report.suppress_under_threshold_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Alert Suppression Policy</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_drill_panel(
    report: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyDrillReport | None
    ),
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression Policy Drill"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(scenario.passed).lower())}\">"
                    f"{html_text(str(scenario.passed).lower())}</span>"
                ),
                f"              <strong>{html_text(scenario.drill_case)}</strong>",
                (
                    f"              <span>{html_text(scenario.observed_decision)} / "
                    f"{html_text(scenario.condition)}</span>"
                ),
                (
                    f"              <small>{scenario.trigger_usage_pct}% trigger, "
                    f"{scenario.replay_age_minutes}m replay age</small>"
                ),
                "            </li>",
            )
        )
        for scenario in report.scenarios
    ) or '<li class="empty-row">No response SLO drift suppression policy drills</li>'
    summary = (
        ("Status", report.drill_status),
        ("Policy", report.policy_status),
        ("Rules", report.rule_count),
        ("Active", report.active_rule_count),
        ("Scenarios", report.scenario_count),
        ("Expected", report.expected_scenario_count),
        ("Passed", report.passed_count),
        ("Failed", report.failed_count),
        ("Suppressed", report.suppressed_count),
        ("Escalation preserved", report.escalation_preserved_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Drill</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_effectiveness_panel(
    report: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyEffectivenessReport
        | None
    ),
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression Policy Effectiveness"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(signal.effective).lower())}\">"
                    f"{html_text(str(signal.effective).lower())}</span>"
                ),
                f"              <strong>{html_text(signal.signal_type)}</strong>",
                (
                    f"              <span>{html_text(signal.observed_decision)} / "
                    f"{html_text(signal.condition)}</span>"
                ),
                (
                    f"              <small>{html_text(signal.rule_id)}</small>"
                ),
                "            </li>",
            )
        )
        for signal in report.signals
    ) or '<li class="empty-row">No suppression policy effectiveness signals</li>'
    summary = (
        ("Status", report.monitor_status),
        ("Drill", report.drill_status),
        ("Policy", report.policy_status),
        ("Signals", report.signal_count),
        ("Effective", report.effective_signal_count),
        ("Failed", report.failed_signal_count),
        ("Suppression candidates", report.suppression_candidate_count),
        ("Suppressed", report.suppressed_signal_count),
        ("Suppression effectiveness", f"{report.suppression_effectiveness_pct}%"),
        ("Escalation signals", report.escalation_signal_count),
        ("Escalation preserved", report.escalation_preserved_count),
        ("Escalation preservation", f"{report.escalation_preservation_pct}%"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Effectiveness</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_coverage_panel(
    report: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport | None
    ),
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression Policy Coverage"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(item.covered).lower())}\">"
                    f"{html_text(str(item.covered).lower())}</span>"
                ),
                f"              <strong>{html_text(item.coverage_mode)}</strong>",
                (
                    f"              <span>{html_text(item.coverage_decision)} / "
                    f"{html_text(item.condition)}</span>"
                ),
                (
                    f"              <small>{html_text(item.scenario_id)}; "
                    f"{item.matched_effective_signal_count}/"
                    f"{item.matched_signal_count} signals</small>"
                ),
                "            </li>",
            )
        )
        for item in report.items
    ) or '<li class="empty-row">No suppression policy coverage items</li>'
    summary = (
        ("Status", report.coverage_status),
        ("Effectiveness", report.effectiveness_status),
        ("Trend", report.trend_status),
        ("Scenario classes", report.scenario_class_count),
        ("Covered", report.covered_scenario_count),
        ("Failed", report.failed_coverage_count),
        ("Active policy scenarios", report.active_policy_scenario_count),
        ("Non-watch exclusions", report.explicit_non_watch_scenario_count),
        ("Coverage", f"{report.coverage_pct}%"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_regression_panel(
    report: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
        | None
    ),
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Regression"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(check.passed).lower())}\">"
                    f"{html_text(str(check.passed).lower())}</span>"
                ),
                f"              <strong>{html_text(check.check_type)}</strong>",
                (
                    f"              <span>{html_text(check.observed)} / "
                    f"{html_text(check.expected)}</span>"
                ),
                f"              <small>{html_text(check.check_id)}</small>",
                "            </li>",
            )
        )
        for check in report.checks
    ) or '<li class="empty-row">No suppression policy regression checks</li>'
    summary = (
        ("Status", report.regression_status),
        ("Coverage", report.coverage_status),
        ("Scenario classes", report.scenario_class_count),
        ("Covered", report.covered_scenario_count),
        ("Coverage pct", f"{report.coverage_pct}%"),
        ("Checks", report.regression_check_count),
        ("Passed", report.passed_regression_check_count),
        ("Failed", report.failed_regression_check_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Regression</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_coverage_slo_panel(
    report: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport
        | None
    ),
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression Policy Coverage SLO"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(objective.met).lower())}\">"
                    f"{html_text(str(objective.met).lower())}</span>"
                ),
                f"              <strong>{html_text(objective.objective_type)}</strong>",
                (
                    f"              <span>{html_text(objective.observed)} / "
                    f"{html_text(objective.target)}</span>"
                ),
                f"              <small>{html_text(objective.objective_id)}</small>",
                "            </li>",
            )
        )
        for objective in report.objectives
    ) or '<li class="empty-row">No suppression policy coverage SLO objectives</li>'
    summary = (
        ("Status", report.slo_status),
        ("Regression", report.regression_status),
        ("Coverage", report.coverage_status),
        ("Coverage pct", f"{report.coverage_pct}%"),
        ("Objectives", report.objective_count),
        ("Met", report.met_objective_count),
        ("Failed", report.failed_objective_count),
        ("Review cadence", f"{report.review_cadence_days} days"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage SLO</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_release_governance_panel(
    report: CoverageReleaseGovernanceReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Governance"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(gate.attached).lower())}\">"
                    f"{html_text(str(gate.attached).lower())}</span>"
                ),
                f"              <strong>{html_text(gate.gate_type)}</strong>",
                (
                    f"              <span>{html_text(gate.observed)} / "
                    f"{html_text(gate.target)}</span>"
                ),
                (
                    f"              <small>{html_text(gate.gate_id)}; "
                    f"{html_text(gate.owner_role)}</small>"
                ),
                "            </li>",
            )
        )
        for gate in report.gates
    ) or '<li class="empty-row">No suppression policy release gates</li>'
    summary = (
        ("Status", report.release_governance_status),
        ("SLO", report.slo_status),
        ("Coverage", report.coverage_status),
        ("Coverage pct", f"{report.coverage_pct}%"),
        ("Release gates", report.release_gate_count),
        ("Attached", report.attached_release_gate_count),
        ("Failed", report.failed_release_gate_count),
        ("Review cadence", f"{report.review_cadence_days} days"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Governance</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_release_gate_drill_panel(
    report: CoverageReleaseGateDrillReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Gate Drill"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(scenario.passed).lower())}\">"
                    f"{html_text(str(scenario.passed).lower())}</span>"
                ),
                f"              <strong>{html_text(scenario.drill_case)}</strong>",
                (
                    f"              <span>{html_text(scenario.observed_outcome)} / "
                    f"{html_text(scenario.expected_outcome)}</span>"
                ),
                (
                    f"              <small>{html_text(scenario.gate_id)}; "
                    f"{html_text(scenario.owner_role)}</small>"
                ),
                "            </li>",
            )
        )
        for scenario in report.scenarios
    ) or '<li class="empty-row">No suppression policy release gate drills</li>'
    summary = (
        ("Status", report.drill_status),
        ("Release governance", report.release_governance_status),
        ("Release gates", report.release_gate_count),
        ("Attached", report.attached_release_gate_count),
        ("Scenarios", report.scenario_count),
        ("Passed", report.passed_count),
        ("Failed", report.failed_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Gate Drill</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_release_gate_effectiveness_panel(
    report: CoverageReleaseGateEffectivenessReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Gate Effectiveness"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(signal.effective).lower())}\">"
                    f"{html_text(str(signal.effective).lower())}</span>"
                ),
                f"              <strong>{html_text(signal.signal_type)}</strong>",
                (
                    f"              <span>{html_text(signal.observed)} / "
                    f"{html_text(signal.expected)}</span>"
                ),
                f"              <small>{html_text(signal.signal_id)}</small>",
                "            </li>",
            )
        )
        for signal in report.signals
    ) or '<li class="empty-row">No release gate effectiveness signals</li>'
    summary = (
        ("Status", report.monitor_status),
        ("Drill", report.drill_status),
        ("Release governance", report.release_governance_status),
        ("Release gates", report.release_gate_count),
        ("Scenarios", report.scenario_count),
        ("Passed", report.passed_count),
        ("Signals", report.signal_count),
        ("Effective", report.effective_signal_count),
        ("Failed", report.failed_signal_count),
        ("Effectiveness", f"{report.release_gate_effectiveness_pct}%"),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Gate Effectiveness</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_enterprise_pattern_panel(
    report: CoverageReleaseGateEnterprisePatternReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Gate Enterprise Pattern"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(item.expansion_ready).lower())}\">"
                    f"{html_text(str(item.expansion_ready).lower())}</span>"
                ),
                f"              <strong>{html_text(item.use_case_id)}</strong>",
                (
                    f"              <span>{html_text(item.product)} / "
                    f"{html_text(item.blueprint_status)}</span>"
                ),
                (
                    f"              <small>{item.evaluation_gate_count} eval gates; "
                    f"{len(item.taxonomy_areas)} taxonomy areas</small>"
                ),
                "            </li>",
            )
        )
        for item in report.assignments
    ) or '<li class="empty-row">No enterprise release gate pattern assignments</li>'
    summary = (
        ("Status", report.expansion_status),
        ("Release gate effectiveness", report.release_gate_effectiveness_status),
        ("Blueprints", report.blueprint_count),
        ("Assigned", report.assigned_use_case_count),
        ("Non-LMS blueprints", report.non_lms_blueprint_count),
        ("Non-LMS products", report.non_lms_product_count),
        ("Taxonomy areas", report.taxonomy_area_count),
        ("Target modules", report.target_module_count),
        ("Executable modules", report.executable_module_count),
        ("Evaluation gates", report.evaluation_gate_count),
        ("Blocked", report.blocked_assignment_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Gate Enterprise Pattern</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_enterprise_adoption_panel(
    report: CoverageReleaseGateEnterpriseAdoptionReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Gate Enterprise Adoption"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(signal.adopted).lower())}\">"
                    f"{html_text(str(signal.adopted).lower())}</span>"
                ),
                f"              <strong>{html_text(signal.signal_type)}</strong>",
                f"              <span>{html_text(signal.observed)}</span>",
                f"              <small>{html_text(signal.condition)}</small>",
                "            </li>",
            )
        )
        for signal in report.signals
    ) or '<li class="empty-row">No enterprise release gate adoption signals</li>'
    summary = (
        ("Status", report.adoption_status),
        ("Enterprise pattern", report.enterprise_pattern_status),
        ("Signals", report.signal_count),
        ("Adopted", report.adopted_signal_count),
        ("Blocked", report.blocked_signal_count),
        ("Adoption pct", f"{report.adoption_pct}%"),
        ("Blueprints", report.blueprint_count),
        ("Non-LMS products", report.non_lms_product_count),
        ("Evaluation gates", report.evaluation_gate_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Gate Enterprise Adoption</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_product_readiness_freshness_response_suppression_policy_enterprise_adoption_slo_panel(
    report: CoverageReleaseGateEnterpriseAdoptionSloReport | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Gate Enterprise Adoption SLO"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(objective.met).lower())}\">"
                    f"{html_text(str(objective.met).lower())}</span>"
                ),
                f"              <strong>{html_text(objective.objective_type)}</strong>",
                f"              <span>{html_text(objective.observed)}</span>",
                f"              <small>{html_text(objective.target)}</small>",
                "            </li>",
            )
        )
        for objective in report.objectives
    ) or '<li class="empty-row">No enterprise release gate adoption SLO objectives</li>'
    summary = (
        ("SLO status", report.slo_status),
        ("Adoption status", report.adoption_status),
        ("Objectives", report.objective_count),
        ("Met objectives", report.met_objective_count),
        ("Failed objectives", report.failed_objective_count),
        ("Adoption pct", f"{report.adoption_pct}%"),
        ("Target adoption pct", f"{report.target_adoption_pct}%"),
        ("Review cadence days", report.review_cadence_days),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Gate Enterprise Adoption SLO</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_enterprise_adoption_slo_release_governance_panel(
    report: CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceReport
    | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Gate Enterprise Adoption SLO Release "
            "Governance"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(gate.attached).lower())}\">"
                    f"{html_text(str(gate.attached).lower())}</span>"
                ),
                f"              <strong>{html_text(gate.gate_type)}</strong>",
                f"              <span>{html_text(gate.observed)}</span>",
                f"              <small>{html_text(gate.target)}</small>",
                "            </li>",
            )
        )
        for gate in report.gates
    ) or '<li class="empty-row">No enterprise adoption SLO governance gates</li>'
    summary = (
        ("Release governance", report.release_governance_status),
        ("SLO status", report.slo_status),
        ("Adoption status", report.adoption_status),
        ("Release gates", report.release_gate_count),
        ("Attached gates", report.attached_release_gate_count),
        ("Failed gates", report.failed_release_gate_count),
        ("Target adoption pct", f"{report.target_adoption_pct}%"),
        ("Review cadence days", report.review_cadence_days),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Gate Enterprise Adoption "
                "SLO Release Governance</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_enterprise_adoption_slo_release_governance_drill_panel(
    report: CoverageReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrillReport
    | None,
) -> str:
    if report is None:
        return render_empty_section(
            "Product Readiness Freshness Response SLO Drift Suppression "
            "Policy Coverage Release Gate Enterprise Adoption SLO Release "
            "Governance Drill"
        )
    rows = "\n".join(
        "\n".join(
            (
                "            <li>",
                (
                    "              <span class=\"badge "
                    f"{status_class(str(scenario.passed).lower())}\">"
                    f"{html_text(str(scenario.passed).lower())}</span>"
                ),
                f"              <strong>{html_text(scenario.gate_type)}</strong>",
                f"              <span>{html_text(scenario.observed_outcome)}</span>",
                f"              <small>{html_text(scenario.drill_case)}</small>",
                "            </li>",
            )
        )
        for scenario in report.scenarios
    ) or '<li class="empty-row">No enterprise adoption SLO governance drills</li>'
    summary = (
        ("Drill status", report.drill_status),
        ("Release governance", report.release_governance_status),
        ("Scenarios", report.scenario_count),
        ("Passed", report.passed_count),
        ("Failed", report.failed_count),
        ("Release gates", report.release_gate_count),
        ("Attached gates", report.attached_release_gate_count),
        ("Tenant safe", str(report.tenant_safe).lower()),
    )
    return "\n".join(
        (
            '    <section class="panel split-panel">',
            "      <div>",
            (
                "        <h2>Product Readiness Freshness Response SLO Drift "
                "Suppression Policy Coverage Release Gate Enterprise Adoption "
                "SLO Release Governance Drill</h2>"
            ),
            f'        <ul class="work-list incident-list">{rows}</ul>',
            "      </div>",
            "      <div>",
            render_key_value_table(summary),
            "      </div>",
            "    </section>",
        )
    )


def render_action_panel(actions: tuple[OperatingCockpitAction, ...]) -> str:
    visible_actions = sorted(actions, key=action_sort_key)[:8]
    rows = "\n".join(
        "\n".join(
            (
                "        <tr>",
                f"          <td>{html_text(action.priority)}</td>",
                f"          <td>{html_text(action.status)}</td>",
                f"          <td>{html_text(action.owner_role)}</td>",
                f"          <td>{html_text(action.action_type.replace('_', ' '))}</td>",
                "        </tr>",
            )
        )
        for action in visible_actions
    )
    return "\n".join(
        (
            '    <section class="panel">',
            "      <h2>Next Control-Plane Actions</h2>",
            '      <table class="action-table">',
            (
                "        <thead><tr><th>Priority</th><th>Status</th>"
                "<th>Owner</th><th>Action</th></tr></thead>"
            ),
            f"        <tbody>{rows}</tbody>",
            "      </table>",
            "    </section>",
        )
    )


def render_key_value_section(title: str, rows: tuple[tuple[str, Any], ...]) -> str:
    return "\n".join(
        (
            '    <section class="panel">',
            f"      <h2>{html_text(title)}</h2>",
            render_key_value_table(rows),
            "    </section>",
        )
    )


def render_key_value_table(rows: tuple[tuple[str, Any], ...]) -> str:
    rendered_rows = "\n".join(
        "\n".join(
            (
                "        <tr>",
                f"          <th>{html_text(label)}</th>",
                f"          <td>{html_text(value)}</td>",
                "        </tr>",
            )
        )
        for label, value in rows
    )
    return "\n".join(
        (
            '      <table class="kv-table">',
            f"        <tbody>{rendered_rows}</tbody>",
            "      </table>",
        )
    )


def render_empty_section(title: str) -> str:
    return "\n".join(
        (
            '    <section class="panel">',
            f"      <h2>{html_text(title)}</h2>",
            '      <p class="empty-row">No matching records</p>',
            "    </section>",
        )
    )


def render_owner_item(
    backlog_id: str,
    priority: str,
    status: str,
    sla_status: str,
    due_at: str,
    title: str,
) -> str:
    return "\n".join(
        (
            "            <li>",
            (
                f'              <span class="badge {status_class(priority)}">'
                f"{html_text(priority)}</span>"
            ),
            f"              <strong>{html_text(backlog_id)}</strong>",
            f"              <span>{html_text(title)}</span>",
            (
                f"              <small>{html_text(status)} / "
                f"{html_text(sla_status)} / {html_text(due_at)}</small>"
            ),
            "            </li>",
        )
    )


def render_incident_row(
    incident_id: str,
    severity: str,
    condition: str,
    action: str,
    application_ref: str,
) -> str:
    return "\n".join(
        (
            "            <li>",
            (
                f'              <span class="badge {status_class(severity)}">'
                f"{html_text(severity)}</span>"
            ),
            f"              <strong>{html_text(condition)}</strong>",
            f"              <span>{html_text(action)}</span>",
            f"              <small>{html_text(incident_id)} / {html_text(application_ref)}</small>",
            "            </li>",
        )
    )


def safe_title(value: str) -> str:
    return value.split(":", 1)[0].strip()


def status_class(value: Any) -> str:
    normalized = str(value).lower().replace("_", "-")
    if normalized in {
        "p0",
        "attention-required",
        "failed",
        "open",
        "blocked",
        "overdue",
        "route-unreachable",
        "slo-breached",
        "static-snapshot-stale",
    }:
        return "status-critical"
    if normalized in {
        "p1",
        "pending-policy-apply",
        "ready-work-available",
        "due-soon",
        "waiting",
    }:
        return "status-warn"
    if normalized in {"p2", "watch", "metrics-not-connected", "shadow"}:
        return "status-info"
    return "status-ok"


def action_sort_key(action: OperatingCockpitAction) -> tuple[int, str, str]:
    priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}.get(action.priority, 9)
    return priority_order, action.owner_role, action.action_type


def parse_report_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def html_text(value: Any) -> str:
    return escape(str(value), quote=True)


def default_dashboard_path(root: Path) -> Path:
    return root / "platform" / "operations" / "reports" / "admin-ops-dashboard-v1.html"


def default_freshness_manifest_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "operations"
        / "reports"
        / "admin-ops-dashboard-freshness-v1.yaml"
    )


def build_freshness_source(
    root: Path,
    *,
    source_id: str,
    relative_path: str,
    expected_generated_at: str,
) -> AdminOpsDashboardFreshnessSource:
    source_path = root / relative_path
    if not source_path.exists():
        return AdminOpsDashboardFreshnessSource(
            source_id=source_id,
            path=relative_path,
            report_id="",
            generated_at="",
            sha256="",
            byte_count=0,
            present=False,
            current=False,
        )
    source_bytes = source_path.read_bytes()
    payload = yaml.safe_load(source_bytes) or {}
    generated_at = normalized_yaml_string(payload.get("generated_at"))
    return AdminOpsDashboardFreshnessSource(
        source_id=source_id,
        path=relative_path,
        report_id=normalized_yaml_string(
            payload.get("report_id") or payload.get("manifest_id")
        ),
        generated_at=generated_at,
        sha256=sha256_bytes(source_bytes),
        byte_count=len(source_bytes),
        present=True,
        current=generated_at == expected_generated_at,
    )


def determine_freshness_status(
    *,
    dashboard_present: bool,
    dashboard_matches_generated_html: bool,
    missing_source_count: int,
    stale_source_count: int,
) -> str:
    if not dashboard_present:
        return "dashboard_missing"
    if missing_source_count:
        return "source_missing"
    if stale_source_count:
        return "source_stale"
    if not dashboard_matches_generated_html:
        return "dashboard_stale"
    return "current"


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def normalized_yaml_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def relative_path_for(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


DASHBOARD_CSS = """
:root {
  color-scheme: light;
  --bg: #f6f8fb;
  --panel: #ffffff;
  --ink: #17202a;
  --muted: #667085;
  --line: #d8dee9;
  --ok: #13795b;
  --warn: #a15c07;
  --critical: #b42318;
  --info: #255e9c;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px;
}
.masthead {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.masthead p,
.masthead h1 {
  margin: 0;
}
.masthead p,
time,
small {
  color: var(--muted);
}
.masthead h1 {
  font-size: 28px;
  font-weight: 700;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.metric-card,
.panel,
.owner-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.metric-card {
  padding: 12px;
}
.metric-card span {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.metric-card strong {
  display: block;
  margin-top: 6px;
  font-size: 17px;
}
.panel {
  padding: 16px;
  margin-top: 14px;
}
.panel h2,
.owner-card h3,
.owner-card h4 {
  margin: 0 0 12px;
}
.panel h2 {
  font-size: 18px;
}
.owner-card h3 {
  font-size: 16px;
}
.owner-card h4 {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
}
.split-panel {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(240px, 1fr);
  gap: 20px;
}
.owner-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 12px;
}
.owner-card {
  padding: 14px;
}
.mini-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.mini-metrics span,
.badge {
  border-radius: 999px;
  padding: 3px 8px;
  background: #eef2f6;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}
.work-list {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 0 0 14px;
  padding: 0;
}
.work-list li {
  display: grid;
  grid-template-columns: auto 96px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  border-top: 1px solid var(--line);
  padding-top: 8px;
}
.work-list small {
  grid-column: 3;
}
.incident-list li {
  grid-template-columns: auto minmax(120px, 1fr) minmax(0, 1.5fr);
}
.empty-row {
  color: var(--muted);
}
.kv-table,
.action-table {
  width: 100%;
  border-collapse: collapse;
}
.kv-table th,
.kv-table td,
.action-table th,
.action-table td {
  border-top: 1px solid var(--line);
  padding: 8px 6px;
  text-align: left;
  vertical-align: top;
}
.kv-table th {
  color: var(--muted);
  font-weight: 600;
  width: 45%;
}
.status-ok {
  color: var(--ok);
}
.status-warn {
  color: var(--warn);
}
.status-critical {
  color: var(--critical);
}
.status-info {
  color: var(--info);
}
.badge.status-ok,
.badge.status-warn,
.badge.status-critical,
.badge.status-info {
  color: #ffffff;
}
.badge.status-ok {
  background: var(--ok);
}
.badge.status-warn {
  background: var(--warn);
}
.badge.status-critical {
  background: var(--critical);
}
.badge.status-info {
  background: var(--info);
}
@media (max-width: 760px) {
  main {
    padding: 18px;
  }
  .masthead,
  .split-panel {
    display: block;
  }
  .work-list li,
  .incident-list li {
    grid-template-columns: 1fr;
  }
  .work-list small {
    grid-column: auto;
  }
}
""".strip()
