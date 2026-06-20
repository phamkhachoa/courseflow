from __future__ import annotations

import argparse
import json
from datetime import date
from importlib import import_module
from pathlib import Path
from typing import Any

from courseflow_ai_platform.admin_ops_dashboard import (
    build_admin_ops_dashboard_freshness_manifest,
    build_admin_ops_dashboard_from_reports,
    default_dashboard_path,
    write_admin_ops_dashboard_freshness_manifest,
    write_admin_ops_dashboard_from_reports,
)
from courseflow_ai_platform.ai_module_catalog import (
    build_ai_module_catalog_report,
    write_ai_module_catalog_snapshot,
)
from courseflow_ai_platform.capability_taxonomy import (
    build_ai_capability_taxonomy_report,
    write_ai_capability_taxonomy_snapshot,
)
from courseflow_ai_platform.coverage_taxonomy import validate_coverage_taxonomy
from courseflow_ai_platform.data_contracts import (
    build_data_contract_coverage_report,
    write_data_contract_coverage_snapshot,
)
from courseflow_ai_platform.delivery_backlog import (
    build_delivery_backlog_report_from_cockpit,
    write_delivery_backlog_snapshot,
)
from courseflow_ai_platform.delivery_owner_views import (
    build_delivery_owner_views_report_from_sla,
    write_delivery_owner_views_snapshot,
)
from courseflow_ai_platform.delivery_sla import (
    build_delivery_sla_report_from_backlog,
    parse_optional_date,
    write_delivery_sla_snapshot,
)
from courseflow_ai_platform.delivery_state_ledger import (
    build_delivery_state_report_from_backlog,
    load_delivery_state_transitions,
    write_delivery_state_snapshot,
)
from courseflow_ai_platform.evaluation import run_registered_evaluations
from courseflow_ai_platform.evidence import validate_model_evidence
from courseflow_ai_platform.governance_evaluation_incidents import (
    build_governance_evaluation_incident_export,
    write_governance_evaluation_incident_export_snapshot,
)
from courseflow_ai_platform.governance_evaluation_ops import (
    build_governance_evaluation_ops_report,
    write_governance_evaluation_ops_snapshot,
)
from courseflow_ai_platform.governance_evaluation_response_drill import (
    build_governance_evaluation_incident_response_drill_report,
    write_governance_evaluation_incident_response_drill_snapshot,
)
from courseflow_ai_platform.llm_provider_alerts import (
    build_llm_provider_alert_routing_report,
    write_llm_provider_alert_routing_snapshot,
)
from courseflow_ai_platform.llm_provider_readiness import (
    build_llm_provider_readiness_report,
    write_llm_provider_readiness_snapshot,
)
from courseflow_ai_platform.llm_provider_runtime_probes import (
    build_llm_provider_runtime_probe_report,
    write_llm_provider_runtime_probe_snapshot,
)
from courseflow_ai_platform.llm_provider_secret_rotation import (
    build_llm_provider_secret_rotation_report,
    write_llm_provider_secret_rotation_snapshot,
)
from courseflow_ai_platform.media_privacy_review import (
    build_media_privacy_review_report,
    write_media_privacy_review_snapshot,
)
from courseflow_ai_platform.operating_cockpit import (
    build_llm_provider_ops_from_runtime_probes,
    build_operating_cockpit_report_from_reports,
    build_serving_access_governance_from_reconciliation,
    build_serving_health_report_from_metrics,
    write_operating_cockpit_snapshot,
)
from courseflow_ai_platform.product_readiness import (
    build_ai_platform_product_readiness_report_from_reports,
    load_platform_product_metadata,
    write_ai_platform_product_readiness_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness import (
    build_ai_platform_product_readiness_freshness_report,
    load_ai_platform_product_readiness_freshness_report,
    write_ai_platform_product_readiness_freshness_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_incidents import (
    build_product_readiness_freshness_incident_export,
    write_product_readiness_freshness_incident_export_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_response_drill import (
    build_product_readiness_freshness_incident_response_drill_report,
    write_product_readiness_freshness_incident_response_drill_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_response_metrics import (
    build_product_readiness_freshness_response_metrics_report,
    write_product_readiness_freshness_response_metrics_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alert_drill import (
    build_product_readiness_freshness_response_slo_drift_alert_drill_report,
    write_product_readiness_freshness_response_slo_drift_alert_drill_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_response_slo_drift_alerts import (
    build_product_readiness_freshness_response_slo_drift_alert_report,
    write_product_readiness_freshness_response_slo_drift_alert_snapshot,
)
from courseflow_ai_platform.product_readiness_freshness_response_trends import (
    build_product_readiness_freshness_response_trend_report,
    write_product_readiness_freshness_response_trend_snapshot,
)
from courseflow_ai_platform.promotion_intake import (
    build_promotion_intake_report,
    write_promotion_intake_snapshot,
)
from courseflow_ai_platform.promotion_readiness import (
    build_promotion_readiness_report,
    write_promotion_readiness_snapshot,
)
from courseflow_ai_platform.registry import (
    RegistryValidationError,
    load_yaml,
    validate_registries,
)
from courseflow_ai_platform.runtime_roadmap import (
    build_runtime_roadmap_report_from_coverage,
    write_runtime_roadmap_snapshot,
)
from courseflow_ai_platform.serving_access_apply_ledger import (
    build_serving_access_apply_ledger_report,
    write_serving_access_apply_ledger_snapshot,
)
from courseflow_ai_platform.serving_access_incidents import (
    build_serving_access_incident_export,
    write_serving_access_incident_export_snapshot,
)
from courseflow_ai_platform.serving_access_policy_applier import (
    build_serving_access_policy_apply_report,
    write_serving_access_policy_apply_report,
)
from courseflow_ai_platform.serving_access_policy_plan import (
    build_serving_access_policy_patch_plan,
    write_serving_access_policy_patch_plan_snapshot,
)
from courseflow_ai_platform.serving_access_policy_reconciliation import (
    build_serving_access_policy_reconciliation_report,
    write_serving_access_policy_reconciliation_snapshot,
)
from courseflow_ai_platform.serving_access_review import (
    build_serving_access_review_report,
    write_serving_access_review_snapshot,
)
from courseflow_ai_platform.serving_metrics_export import (
    load_model_serving_metrics_export,
    write_model_serving_metrics_export_snapshot,
)
from courseflow_ai_platform.solution_blueprint import (
    build_solution_blueprint_report,
    write_solution_blueprint_snapshot,
)

from .product_readiness_freshness_response_slo_drift_alert_calibration import (
    build_product_readiness_freshness_response_slo_drift_alert_calibration_report,
    write_product_readiness_freshness_response_slo_drift_alert_calibration_snapshot,
)
from .product_readiness_freshness_response_slo_drift_alert_suppression_policy import (
    build_product_readiness_freshness_response_slo_drift_suppression_policy_report,
    write_product_readiness_freshness_response_slo_drift_suppression_policy_snapshot,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage import (
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report,
    write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_snapshot,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression import (
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report,
    write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_snapshot,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo import (
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report,
    write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_snapshot,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_drill import (
    build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report,
    write_product_readiness_freshness_response_slo_drift_suppression_policy_drill_snapshot,
)
from .product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness import (
    build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report,
    write_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_snapshot,
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
_COVERAGE_RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance_report"
)
_COVERAGE_RELEASE_GOVERNANCE_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_governance_snapshot"
)
_COVERAGE_RELEASE_GATE_DRILL_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_drill_report"
)
_COVERAGE_RELEASE_GATE_DRILL_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_drill_snapshot"
)
_COVERAGE_RELEASE_GATE_EFFECTIVENESS_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_report"
)
_COVERAGE_RELEASE_GATE_EFFECTIVENESS_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_effectiveness_snapshot"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_PATTERN_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_report"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_PATTERN_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_pattern_snapshot"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_report"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_snapshot"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_report"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_snapshot"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_report"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_snapshot"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_REPORT_BUILDER_ATTR = (
    "build_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report"
)
_COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_SNAPSHOT_WRITER_ATTR = (
    "write_product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance_drill_snapshot"
)
coverage_release_governance_module = import_module(COVERAGE_RELEASE_GOVERNANCE_MODULE)
coverage_release_gate_drill_module = import_module(COVERAGE_RELEASE_GATE_DRILL_MODULE)
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
build_coverage_release_governance_report = getattr(
    coverage_release_governance_module,
    _COVERAGE_RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR,
)
write_coverage_release_governance_snapshot = getattr(
    coverage_release_governance_module,
    _COVERAGE_RELEASE_GOVERNANCE_SNAPSHOT_WRITER_ATTR,
)
build_coverage_release_gate_drill_report = getattr(
    coverage_release_gate_drill_module,
    _COVERAGE_RELEASE_GATE_DRILL_REPORT_BUILDER_ATTR,
)
write_coverage_release_gate_drill_snapshot = getattr(
    coverage_release_gate_drill_module,
    _COVERAGE_RELEASE_GATE_DRILL_SNAPSHOT_WRITER_ATTR,
)
build_coverage_release_gate_effectiveness_report = getattr(
    coverage_release_gate_effectiveness_module,
    _COVERAGE_RELEASE_GATE_EFFECTIVENESS_REPORT_BUILDER_ATTR,
)
write_coverage_release_gate_effectiveness_snapshot = getattr(
    coverage_release_gate_effectiveness_module,
    _COVERAGE_RELEASE_GATE_EFFECTIVENESS_SNAPSHOT_WRITER_ATTR,
)
build_coverage_release_gate_enterprise_pattern_report = getattr(
    coverage_release_gate_enterprise_pattern_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_PATTERN_REPORT_BUILDER_ATTR,
)
write_coverage_release_gate_enterprise_pattern_snapshot = getattr(
    coverage_release_gate_enterprise_pattern_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_PATTERN_SNAPSHOT_WRITER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_report = getattr(
    coverage_release_gate_enterprise_adoption_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_REPORT_BUILDER_ATTR,
)
write_coverage_release_gate_enterprise_adoption_snapshot = getattr(
    coverage_release_gate_enterprise_adoption_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SNAPSHOT_WRITER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_report = getattr(
    coverage_release_gate_enterprise_adoption_slo_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_REPORT_BUILDER_ATTR,
)
write_coverage_release_gate_enterprise_adoption_slo_snapshot = getattr(
    coverage_release_gate_enterprise_adoption_slo_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_SNAPSHOT_WRITER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_release_governance_report = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_REPORT_BUILDER_ATTR,
)
write_coverage_release_gate_enterprise_adoption_slo_release_governance_snapshot = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_SNAPSHOT_WRITER_ATTR,
)
build_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_REPORT_BUILDER_ATTR,
)
write_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_snapshot = getattr(
    coverage_release_gate_enterprise_adoption_slo_release_governance_drill_module,
    _COVERAGE_RELEASE_GATE_ENTERPRISE_ADOPTION_SLO_RELEASE_GOVERNANCE_DRILL_SNAPSHOT_WRITER_ATTR,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CourseFlow AI Platform registries.")
    parser.add_argument(
        "--ai-root",
        default=str(default_ai_root()),
        help="Path to the ai/ directory.",
    )
    parser.add_argument(
        "--write-promotion-readiness-report",
        action="store_true",
        help="Write the Admin/Ops promotion readiness YAML report.",
    )
    parser.add_argument(
        "--promotion-readiness-report-path",
        default=None,
        help="Optional output path for --write-promotion-readiness-report.",
    )
    parser.add_argument(
        "--write-promotion-intake-report",
        action="store_true",
        help="Write the Admin/Ops promotion request intake YAML report.",
    )
    parser.add_argument(
        "--promotion-intake-report-path",
        default=None,
        help="Optional output path for --write-promotion-intake-report.",
    )
    parser.add_argument(
        "--write-solution-blueprint-report",
        action="store_true",
        help="Write the PO/BA solution blueprint YAML report.",
    )
    parser.add_argument(
        "--solution-blueprint-report-path",
        default=None,
        help="Optional output path for --write-solution-blueprint-report.",
    )
    parser.add_argument(
        "--write-operating-cockpit-report",
        action="store_true",
        help="Write the AI Platform operating cockpit YAML report.",
    )
    parser.add_argument(
        "--operating-cockpit-report-path",
        default=None,
        help="Optional output path for --write-operating-cockpit-report.",
    )
    parser.add_argument(
        "--write-admin-ops-dashboard",
        action="store_true",
        help="Write the rendered AI Platform Admin/Ops dashboard HTML artifact.",
    )
    parser.add_argument(
        "--admin-ops-dashboard-path",
        default=None,
        help="Optional output path for --write-admin-ops-dashboard.",
    )
    parser.add_argument(
        "--write-admin-ops-dashboard-freshness-manifest",
        action="store_true",
        help="Write the AI Platform Admin/Ops dashboard freshness manifest YAML.",
    )
    parser.add_argument(
        "--admin-ops-dashboard-freshness-manifest-path",
        default=None,
        help="Optional output path for --write-admin-ops-dashboard-freshness-manifest.",
    )
    parser.add_argument(
        "--write-ai-platform-product-readiness-report",
        action="store_true",
        help="Write the AI Platform product readiness YAML report.",
    )
    parser.add_argument(
        "--ai-platform-product-readiness-report-path",
        default=None,
        help="Optional output path for --write-ai-platform-product-readiness-report.",
    )
    parser.add_argument(
        "--write-ai-platform-product-readiness-freshness-report",
        action="store_true",
        help="Write the AI Platform product readiness route freshness YAML report.",
    )
    parser.add_argument(
        "--ai-platform-product-readiness-freshness-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-ai-platform-product-readiness-freshness-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-incident-export-report",
        action="store_true",
        help="Write the tenant-safe product readiness freshness incident export YAML.",
    )
    parser.add_argument(
        "--product-readiness-freshness-incident-export-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-incident-export-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-incident-response-drill-report",
        action="store_true",
        help="Write the Product Readiness Freshness incident response drill YAML.",
    )
    parser.add_argument(
        "--product-readiness-freshness-incident-response-drill-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-incident-response-drill-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-metrics-report",
        action="store_true",
        help="Write the Product Readiness Freshness response metrics YAML.",
    )
    parser.add_argument(
        "--product-readiness-freshness-response-metrics-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-metrics-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-trend-report",
        action="store_true",
        help="Write the Product Readiness Freshness response SLO trend YAML.",
    )
    parser.add_argument(
        "--product-readiness-freshness-response-trend-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-trend-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-alert-report",
        action="store_true",
        help="Write the Product Readiness Freshness response SLO drift alert YAML.",
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-alert-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-alert-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-alert-drill-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift alert "
            "drill YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-alert-drill-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-alert-drill-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-alert-calibration-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift alert "
            "calibration YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-alert-calibration-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-alert-calibration-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-drill-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy drill YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-drill-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-drill-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy effectiveness YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage regression YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-report",
        action="store_true",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage SLO YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-report",
        action="store_true",
        dest="write_coverage_release_governance_report",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release governance YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-report-path",
        default=None,
        dest="coverage_release_governance_report_path",
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-report",
        action="store_true",
        dest="write_coverage_release_gate_drill_report",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release gate drill YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-report-path",
        default=None,
        dest="coverage_release_gate_drill_report_path",
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-report",
        action="store_true",
        dest="write_coverage_release_gate_effectiveness_report",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release gate effectiveness YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-report-path",
        default=None,
        dest="coverage_release_gate_effectiveness_report_path",
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-report",
        action="store_true",
        dest="write_coverage_release_gate_enterprise_pattern_report",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release gate enterprise pattern YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-report-path",
        default=None,
        dest="coverage_release_gate_enterprise_pattern_report_path",
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-report",
        action="store_true",
        dest="write_coverage_release_gate_enterprise_adoption_report",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release gate enterprise adoption YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-report-path",
        default=None,
        dest="coverage_release_gate_enterprise_adoption_report_path",
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-report",
        action="store_true",
        dest="write_coverage_release_gate_enterprise_adoption_slo_report",
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release gate enterprise adoption SLO YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-report-path",
        default=None,
        dest="coverage_release_gate_enterprise_adoption_slo_report_path",
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-report",
        action="store_true",
        dest=(
            "write_coverage_release_gate_enterprise_adoption_slo_"
            "release_governance_report"
        ),
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release gate enterprise adoption SLO "
            "release governance YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-report-path",
        default=None,
        dest=(
            "coverage_release_gate_enterprise_adoption_slo_"
            "release_governance_report_path"
        ),
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-report."
        ),
    )
    parser.add_argument(
        "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-report",
        action="store_true",
        dest=(
            "write_coverage_release_gate_enterprise_adoption_slo_"
            "release_governance_drill_report"
        ),
        help=(
            "Write the Product Readiness Freshness response SLO drift "
            "suppression policy coverage release gate enterprise adoption SLO "
            "release governance drill YAML."
        ),
    )
    parser.add_argument(
        "--product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-report-path",
        default=None,
        dest=(
            "coverage_release_gate_enterprise_adoption_slo_"
            "release_governance_drill_report_path"
        ),
        help=(
            "Optional output path for "
            "--write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-report."
        ),
    )
    parser.add_argument(
        "--write-model-serving-metrics-export-report",
        action="store_true",
        help="Write the AI Platform model-serving metrics export YAML report.",
    )
    parser.add_argument(
        "--model-serving-metrics-export-report-path",
        default=None,
        help="Optional output path for --write-model-serving-metrics-export-report.",
    )
    parser.add_argument(
        "--write-llm-provider-readiness-report",
        action="store_true",
        help="Write the AI Platform LLM provider credential readiness YAML report.",
    )
    parser.add_argument(
        "--llm-provider-readiness-report-path",
        default=None,
        help="Optional output path for --write-llm-provider-readiness-report.",
    )
    parser.add_argument(
        "--write-llm-provider-runtime-probe-report",
        action="store_true",
        help="Write the AI Platform LLM provider runtime probe YAML report.",
    )
    parser.add_argument(
        "--llm-provider-runtime-probe-report-path",
        default=None,
        help="Optional output path for --write-llm-provider-runtime-probe-report.",
    )
    parser.add_argument(
        "--write-llm-provider-alert-routing-report",
        action="store_true",
        help="Write the AI Platform LLM provider alert routing YAML report.",
    )
    parser.add_argument(
        "--llm-provider-alert-routing-report-path",
        default=None,
        help="Optional output path for --write-llm-provider-alert-routing-report.",
    )
    parser.add_argument(
        "--write-llm-provider-secret-rotation-report",
        action="store_true",
        help="Write the AI Platform LLM provider secret rotation YAML report.",
    )
    parser.add_argument(
        "--llm-provider-secret-rotation-report-path",
        default=None,
        help="Optional output path for --write-llm-provider-secret-rotation-report.",
    )
    parser.add_argument(
        "--write-media-privacy-review-report",
        action="store_true",
        help="Write the AI Platform media privacy review YAML report.",
    )
    parser.add_argument(
        "--media-privacy-review-report-path",
        default=None,
        help="Optional output path for --write-media-privacy-review-report.",
    )
    parser.add_argument(
        "--write-governance-evaluation-ops-report",
        action="store_true",
        help="Write the AI Platform governance evaluation ops YAML report.",
    )
    parser.add_argument(
        "--governance-evaluation-ops-report-path",
        default=None,
        help="Optional output path for --write-governance-evaluation-ops-report.",
    )
    parser.add_argument(
        "--write-governance-evaluation-incident-export-report",
        action="store_true",
        help="Write the tenant-safe governance evaluation incident export YAML report.",
    )
    parser.add_argument(
        "--governance-evaluation-incident-export-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-governance-evaluation-incident-export-report."
        ),
    )
    parser.add_argument(
        "--write-governance-evaluation-incident-response-drill-report",
        action="store_true",
        help="Write the Governance Evaluation incident response drill YAML report.",
    )
    parser.add_argument(
        "--governance-evaluation-incident-response-drill-report-path",
        default=None,
        help=(
            "Optional output path for "
            "--write-governance-evaluation-incident-response-drill-report."
        ),
    )
    parser.add_argument(
        "--write-data-contract-coverage-report",
        action="store_true",
        help="Write the AI Platform data contract coverage YAML report.",
    )
    parser.add_argument(
        "--data-contract-coverage-report-path",
        default=None,
        help="Optional output path for --write-data-contract-coverage-report.",
    )
    parser.add_argument(
        "--write-delivery-backlog-report",
        action="store_true",
        help="Write the AI Platform delivery backlog YAML report.",
    )
    parser.add_argument(
        "--delivery-backlog-report-path",
        default=None,
        help="Optional output path for --write-delivery-backlog-report.",
    )
    parser.add_argument(
        "--write-delivery-state-report",
        action="store_true",
        help="Write the AI Platform persisted delivery state YAML report.",
    )
    parser.add_argument(
        "--delivery-state-report-path",
        default=None,
        help="Optional output path for --write-delivery-state-report.",
    )
    parser.add_argument(
        "--write-delivery-sla-report",
        action="store_true",
        help="Write the AI Platform delivery SLA YAML report.",
    )
    parser.add_argument(
        "--delivery-sla-report-path",
        default=None,
        help="Optional output path for --write-delivery-sla-report.",
    )
    parser.add_argument(
        "--write-delivery-owner-views-report",
        action="store_true",
        help="Write the AI Platform delivery owner views YAML report.",
    )
    parser.add_argument(
        "--delivery-owner-views-report-path",
        default=None,
        help="Optional output path for --write-delivery-owner-views-report.",
    )
    parser.add_argument(
        "--write-runtime-roadmap-report",
        action="store_true",
        help="Write the AI Platform runtime roadmap YAML report.",
    )
    parser.add_argument(
        "--runtime-roadmap-report-path",
        default=None,
        help="Optional output path for --write-runtime-roadmap-report.",
    )
    parser.add_argument(
        "--write-ai-module-catalog-report",
        action="store_true",
        help="Write the AI Platform AI module catalog YAML report.",
    )
    parser.add_argument(
        "--ai-module-catalog-report-path",
        default=None,
        help="Optional output path for --write-ai-module-catalog-report.",
    )
    parser.add_argument(
        "--write-ai-capability-taxonomy-report",
        action="store_true",
        help="Write the AI Platform capability taxonomy YAML report.",
    )
    parser.add_argument(
        "--ai-capability-taxonomy-report-path",
        default=None,
        help="Optional output path for --write-ai-capability-taxonomy-report.",
    )
    parser.add_argument(
        "--write-serving-access-review-report",
        action="store_true",
        help="Write the AI Platform model-serving access review YAML report.",
    )
    parser.add_argument(
        "--serving-access-review-report-path",
        default=None,
        help="Optional output path for --write-serving-access-review-report.",
    )
    parser.add_argument(
        "--write-serving-access-policy-patch-plan",
        action="store_true",
        help="Write the AI Platform model-serving access policy patch plan YAML report.",
    )
    parser.add_argument(
        "--serving-access-policy-patch-plan-path",
        default=None,
        help="Optional output path for --write-serving-access-policy-patch-plan.",
    )
    parser.add_argument(
        "--write-serving-access-apply-ledger-report",
        action="store_true",
        help="Write the AI Platform model-serving access apply ledger YAML report.",
    )
    parser.add_argument(
        "--serving-access-apply-ledger-report-path",
        default=None,
        help="Optional output path for --write-serving-access-apply-ledger-report.",
    )
    parser.add_argument(
        "--write-serving-access-policy-apply-report",
        action="store_true",
        help="Write the AI Platform model-serving access controlled apply YAML report.",
    )
    parser.add_argument(
        "--serving-access-policy-apply-report-path",
        default=None,
        help="Optional output path for --write-serving-access-policy-apply-report.",
    )
    parser.add_argument(
        "--write-serving-access-policy-reconciliation-report",
        action="store_true",
        help="Write the AI Platform model-serving access policy reconciliation report.",
    )
    parser.add_argument(
        "--serving-access-policy-reconciliation-report-path",
        default=None,
        help="Optional output path for --write-serving-access-policy-reconciliation-report.",
    )
    parser.add_argument(
        "--write-serving-access-incident-export-report",
        action="store_true",
        help="Write the tenant-safe model-serving access incident export report.",
    )
    parser.add_argument(
        "--serving-access-incident-export-report-path",
        default=None,
        help="Optional output path for --write-serving-access-incident-export-report.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Optional YYYY-MM-DD date to stamp generated reports.",
    )
    args = parser.parse_args()

    try:
        ai_root = Path(args.ai_root)
        registry_report = validate_registries(ai_root)
        coverage_taxonomy_report = validate_coverage_taxonomy(ai_root)
        runtime_roadmap_report = build_runtime_roadmap_report_from_coverage(
            coverage_taxonomy_report
        )
        ai_module_catalog_report = build_ai_module_catalog_report(ai_root)
        ai_capability_taxonomy_report = build_ai_capability_taxonomy_report(ai_root)
        data_contract_coverage_report = build_data_contract_coverage_report(ai_root)
        evidence_report = validate_model_evidence(ai_root)
        promotion_readiness_report = build_promotion_readiness_report(
            ai_root,
            as_of=args.generated_at,
        )
        promotion_intake_report = build_promotion_intake_report(ai_root)
        solution_blueprint_report = build_solution_blueprint_report(ai_root)
        serving_access_review_report = build_serving_access_review_report(ai_root)
        serving_access_policy_patch_plan = build_serving_access_policy_patch_plan(ai_root)
        serving_access_apply_ledger_report = build_serving_access_apply_ledger_report(ai_root)
        serving_access_policy_apply_report = build_serving_access_policy_apply_report(ai_root)
        serving_access_policy_reconciliation_report = (
            build_serving_access_policy_reconciliation_report(ai_root)
        )
        serving_access_incident_export = build_serving_access_incident_export(
            ai_root,
            as_of=args.generated_at,
        )
        model_serving_metrics_export = load_model_serving_metrics_export(ai_root)
        llm_provider_readiness_report = build_llm_provider_readiness_report(
            ai_root,
            generated_at=args.generated_at,
        )
        llm_provider_runtime_probe_report = build_llm_provider_runtime_probe_report(
            ai_root,
            generated_at=args.generated_at,
        )
        llm_provider_alert_routing_report = build_llm_provider_alert_routing_report(
            ai_root,
            generated_at=args.generated_at,
        )
        llm_provider_secret_rotation_report = build_llm_provider_secret_rotation_report(
            ai_root,
            generated_at=args.generated_at,
        )
        media_privacy_review_report = build_media_privacy_review_report(
            ai_root,
            generated_at=args.generated_at,
        )
        governance_evaluation_ops_report = build_governance_evaluation_ops_report(
            ai_root,
            generated_at=args.generated_at,
        )
        governance_evaluation_incident_export = (
            build_governance_evaluation_incident_export(
                ai_root,
                as_of=args.generated_at,
            )
        )
        governance_evaluation_incident_response_drill = (
            build_governance_evaluation_incident_response_drill_report(
                ai_root,
                generated_at=args.generated_at,
            )
        )
        product_readiness_freshness_incident_export = (
            build_product_readiness_freshness_incident_export(
                ai_root,
                as_of=args.generated_at,
            )
        )
        product_readiness_freshness_response_drill = (
            build_product_readiness_freshness_incident_response_drill_report(
                ai_root,
                generated_at=args.generated_at,
            )
        )
        product_readiness_freshness_response_metrics = (
            build_product_readiness_freshness_response_metrics_report(
                ai_root,
                generated_at=args.generated_at,
                response_drill=product_readiness_freshness_response_drill,
            )
        )
        product_readiness_freshness_response_trends = (
            build_product_readiness_freshness_response_trend_report(
                ai_root,
                generated_at=args.generated_at,
                response_metrics=product_readiness_freshness_response_metrics,
            )
        )
        product_readiness_freshness_response_alerts = (
            build_product_readiness_freshness_response_slo_drift_alert_report(
                ai_root,
                generated_at=args.generated_at,
                response_trends=product_readiness_freshness_response_trends,
            )
        )
        product_readiness_freshness_response_alert_drill = (
            build_product_readiness_freshness_response_slo_drift_alert_drill_report(
                ai_root,
                generated_at=args.generated_at,
                response_alerts=product_readiness_freshness_response_alerts,
            )
        )
        product_readiness_freshness_response_alert_calibration = (
            build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
                ai_root,
                generated_at=args.generated_at,
                alert_drill=product_readiness_freshness_response_alert_drill,
            )
        )
        product_readiness_freshness_response_alert_suppression_policy = (
            build_product_readiness_freshness_response_slo_drift_suppression_policy_report(
                ai_root,
                generated_at=args.generated_at,
                calibration=product_readiness_freshness_response_alert_calibration,
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_drill = (
            build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report(
                ai_root,
                generated_at=args.generated_at,
                suppression_policy=(
                    product_readiness_freshness_response_alert_suppression_policy
                ),
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_effectiveness = (
            build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report(
                ai_root,
                generated_at=args.generated_at,
                suppression_policy_drill=(
                    product_readiness_freshness_response_alert_suppression_policy_drill
                ),
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_coverage = (
            build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report(
                ai_root,
                generated_at=args.generated_at,
                effectiveness=(
                    product_readiness_freshness_response_alert_suppression_policy_effectiveness
                ),
                response_trends=product_readiness_freshness_response_trends,
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_regression = (
            build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report(
                ai_root,
                generated_at=args.generated_at,
                coverage=product_readiness_freshness_response_alert_suppression_policy_coverage,
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_coverage_slo = (
            build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report(
                ai_root,
                generated_at=args.generated_at,
                regression=product_readiness_freshness_response_alert_suppression_policy_regression,
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_release_governance = (
            build_coverage_release_governance_report(
                ai_root,
                generated_at=args.generated_at,
                coverage_slo=(
                    product_readiness_freshness_response_alert_suppression_policy_coverage_slo
                ),
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_release_gate_drill = (
            build_coverage_release_gate_drill_report(
                ai_root,
                generated_at=args.generated_at,
                release_governance=(
                    product_readiness_freshness_response_alert_suppression_policy_release_governance
                ),
            )
        )
        product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness = (
            build_coverage_release_gate_effectiveness_report(
                ai_root,
                generated_at=args.generated_at,
                release_gate_drill=(
                    product_readiness_freshness_response_alert_suppression_policy_release_gate_drill
                ),
            )
        )
        release_gate_enterprise_pattern_report = (
            build_coverage_release_gate_enterprise_pattern_report(
                ai_root,
                generated_at=args.generated_at,
                release_gate_effectiveness=(
                    product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
                ),
                solution_blueprint=solution_blueprint_report,
            )
        )
        release_gate_enterprise_adoption_report = (
            build_coverage_release_gate_enterprise_adoption_report(
                ai_root,
                generated_at=args.generated_at,
                enterprise_pattern=release_gate_enterprise_pattern_report,
            )
        )
        release_gate_enterprise_adoption_slo_report = (
            build_coverage_release_gate_enterprise_adoption_slo_report(
                ai_root,
                generated_at=args.generated_at,
                adoption=release_gate_enterprise_adoption_report,
            )
        )
        release_gate_enterprise_adoption_slo_release_governance_report = (
            build_coverage_release_gate_enterprise_adoption_slo_release_governance_report(
                ai_root,
                generated_at=args.generated_at,
                enterprise_adoption_slo=release_gate_enterprise_adoption_slo_report,
            )
        )
        release_gate_enterprise_adoption_slo_release_governance_drill_report = (
            build_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report(
                ai_root,
                generated_at=args.generated_at,
                release_governance=(
                    release_gate_enterprise_adoption_slo_release_governance_report
                ),
            )
        )
        evaluation_report = run_registered_evaluations(ai_root)
        operating_cockpit_report = build_operating_cockpit_report_from_reports(
            registry_report=registry_report,
            coverage_report=coverage_taxonomy_report,
            evidence_report=evidence_report,
            evaluation_report=evaluation_report,
            data_contract_report=data_contract_coverage_report,
            solution_report=solution_blueprint_report,
            promotion_intake_report=promotion_intake_report,
            promotion_readiness_report=promotion_readiness_report,
            serving_health=build_serving_health_report_from_metrics(
                model_serving_metrics_export.metrics
                if model_serving_metrics_export is not None
                else None
            ),
            serving_access_governance=build_serving_access_governance_from_reconciliation(
                serving_access_policy_reconciliation_report
            ),
            llm_provider_ops=build_llm_provider_ops_from_runtime_probes(
                llm_provider_runtime_probe_report,
                llm_provider_alert_routing_report,
                llm_provider_secret_rotation_report,
            ),
            media_privacy_review_report=media_privacy_review_report,
            governance_evaluation_ops_report=governance_evaluation_ops_report,
            governance_evaluation_response_drill_report=(
                governance_evaluation_incident_response_drill
            ),
            product_readiness_freshness_response_drill_report=(
                product_readiness_freshness_response_drill
            ),
        )
        delivery_state_transitions = load_delivery_state_transitions(ai_root)
        base_delivery_backlog_report = build_delivery_backlog_report_from_cockpit(
            operating_cockpit_report
        )
        delivery_state_report = build_delivery_state_report_from_backlog(
            base_delivery_backlog_report,
            delivery_state_transitions,
        )
        delivery_backlog_report = build_delivery_backlog_report_from_cockpit(
            operating_cockpit_report,
            state_transitions=delivery_state_transitions,
        )
        delivery_sla_report = build_delivery_sla_report_from_backlog(
            delivery_backlog_report,
            load_delivery_sla_policy(ai_root),
            as_of=parse_generated_at(args.generated_at),
        )
        delivery_owner_views_report = build_delivery_owner_views_report_from_sla(
            delivery_sla_report,
            incident_export=serving_access_incident_export,
            governance_evaluation_incident_export=governance_evaluation_incident_export,
            product_readiness_freshness_incident_export=(
                product_readiness_freshness_incident_export
            ),
        )
        ai_platform_product_readiness_freshness = (
            load_ai_platform_product_readiness_freshness_report(ai_root)
        )
        dashboard_generated_at = parse_generated_at(args.generated_at).isoformat()
        admin_ops_dashboard = build_admin_ops_dashboard_from_reports(
            operating_cockpit_report=operating_cockpit_report,
            delivery_owner_views_report=delivery_owner_views_report,
            serving_access_incident_export=serving_access_incident_export,
            governance_evaluation_incident_export=governance_evaluation_incident_export,
            governance_evaluation_response_drill=(
                governance_evaluation_incident_response_drill
            ),
            product_readiness_freshness_report=(
                ai_platform_product_readiness_freshness
            ),
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
            release_gate_enterprise_adoption_report=(
                release_gate_enterprise_adoption_report
            ),
            release_gate_enterprise_adoption_slo_report=(
                release_gate_enterprise_adoption_slo_report
            ),
            release_gate_enterprise_adoption_slo_release_governance_report=(
                release_gate_enterprise_adoption_slo_release_governance_report
            ),
            release_gate_enterprise_adoption_slo_release_governance_drill_report=(
                release_gate_enterprise_adoption_slo_release_governance_drill_report
            ),
            generated_at=dashboard_generated_at,
        )
        dashboard_output_path = args.admin_ops_dashboard_path or default_dashboard_path(
            ai_root
        )
        if args.write_promotion_readiness_report:
            write_promotion_readiness_snapshot(
                ai_root,
                args.promotion_readiness_report_path,
                generated_at=args.generated_at,
            )
        if args.write_promotion_intake_report:
            write_promotion_intake_snapshot(
                ai_root,
                args.promotion_intake_report_path,
                generated_at=args.generated_at,
            )
        if args.write_solution_blueprint_report:
            write_solution_blueprint_snapshot(
                ai_root,
                args.solution_blueprint_report_path,
                generated_at=args.generated_at,
            )
        if args.write_operating_cockpit_report:
            write_operating_cockpit_snapshot(
                ai_root,
                args.operating_cockpit_report_path,
                generated_at=args.generated_at,
                governance_evaluation_ops_report=governance_evaluation_ops_report,
                governance_evaluation_response_drill_report=(
                    governance_evaluation_incident_response_drill
                ),
                product_readiness_freshness_response_drill_report=(
                    product_readiness_freshness_response_drill
                ),
            )
        if args.write_admin_ops_dashboard:
            write_admin_ops_dashboard_from_reports(
                dashboard_output_path,
                operating_cockpit_report=operating_cockpit_report,
                delivery_owner_views_report=delivery_owner_views_report,
                serving_access_incident_export=serving_access_incident_export,
                governance_evaluation_incident_export=(
                    governance_evaluation_incident_export
                ),
                governance_evaluation_response_drill=(
                    governance_evaluation_incident_response_drill
                ),
                product_readiness_freshness_report=(
                    ai_platform_product_readiness_freshness
                ),
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
                release_gate_enterprise_adoption_report=(
                    release_gate_enterprise_adoption_report
                ),
                release_gate_enterprise_adoption_slo_report=(
                    release_gate_enterprise_adoption_slo_report
                ),
                release_gate_enterprise_adoption_slo_release_governance_report=(
                    release_gate_enterprise_adoption_slo_release_governance_report
                ),
                release_gate_enterprise_adoption_slo_release_governance_drill_report=(
                    release_gate_enterprise_adoption_slo_release_governance_drill_report
                ),
                generated_at=dashboard_generated_at,
            )
        if args.write_model_serving_metrics_export_report:
            write_model_serving_metrics_export_snapshot(
                ai_root,
                args.model_serving_metrics_export_report_path,
                generated_at=args.generated_at,
            )
        if args.write_llm_provider_readiness_report:
            write_llm_provider_readiness_snapshot(
                ai_root,
                args.llm_provider_readiness_report_path,
                generated_at=args.generated_at,
            )
        if args.write_llm_provider_runtime_probe_report:
            write_llm_provider_runtime_probe_snapshot(
                ai_root,
                args.llm_provider_runtime_probe_report_path,
                generated_at=args.generated_at,
            )
        if args.write_llm_provider_alert_routing_report:
            write_llm_provider_alert_routing_snapshot(
                ai_root,
                args.llm_provider_alert_routing_report_path,
                generated_at=args.generated_at,
            )
        if args.write_llm_provider_secret_rotation_report:
            write_llm_provider_secret_rotation_snapshot(
                ai_root,
                args.llm_provider_secret_rotation_report_path,
                generated_at=args.generated_at,
            )
        if args.write_media_privacy_review_report:
            write_media_privacy_review_snapshot(
                ai_root,
                args.media_privacy_review_report_path,
                generated_at=args.generated_at,
            )
        if args.write_governance_evaluation_ops_report:
            write_governance_evaluation_ops_snapshot(
                ai_root,
                args.governance_evaluation_ops_report_path,
                generated_at=args.generated_at,
            )
        if args.write_governance_evaluation_incident_export_report:
            write_governance_evaluation_incident_export_snapshot(
                ai_root,
                args.governance_evaluation_incident_export_report_path,
                generated_at=args.generated_at,
                as_of=args.generated_at,
            )
        if args.write_governance_evaluation_incident_response_drill_report:
            write_governance_evaluation_incident_response_drill_snapshot(
                ai_root,
                args.governance_evaluation_incident_response_drill_report_path,
                generated_at=args.generated_at,
            )
        if args.write_data_contract_coverage_report:
            write_data_contract_coverage_snapshot(
                ai_root,
                args.data_contract_coverage_report_path,
                generated_at=args.generated_at,
            )
        if args.write_delivery_backlog_report:
            write_delivery_backlog_snapshot(
                ai_root,
                args.delivery_backlog_report_path,
                generated_at=args.generated_at,
            )
        if args.write_delivery_state_report:
            write_delivery_state_snapshot(
                ai_root,
                args.delivery_state_report_path,
                generated_at=args.generated_at,
            )
        if args.write_delivery_sla_report:
            write_delivery_sla_snapshot(
                ai_root,
                args.delivery_sla_report_path,
                generated_at=args.generated_at,
            )
        if args.write_delivery_owner_views_report:
            write_delivery_owner_views_snapshot(
                ai_root,
                args.delivery_owner_views_report_path,
                generated_at=args.generated_at,
            )
        if args.write_runtime_roadmap_report:
            write_runtime_roadmap_snapshot(
                ai_root,
                args.runtime_roadmap_report_path,
                generated_at=args.generated_at,
            )
        if args.write_ai_module_catalog_report:
            write_ai_module_catalog_snapshot(
                ai_root,
                args.ai_module_catalog_report_path,
                generated_at=args.generated_at,
            )
        if args.write_ai_capability_taxonomy_report:
            write_ai_capability_taxonomy_snapshot(
                ai_root,
                args.ai_capability_taxonomy_report_path,
                generated_at=args.generated_at,
            )
        if args.write_serving_access_review_report:
            write_serving_access_review_snapshot(
                ai_root,
                args.serving_access_review_report_path,
                generated_at=args.generated_at,
            )
        if args.write_serving_access_policy_patch_plan:
            write_serving_access_policy_patch_plan_snapshot(
                ai_root,
                args.serving_access_policy_patch_plan_path,
                generated_at=args.generated_at,
            )
        if args.write_serving_access_apply_ledger_report:
            write_serving_access_apply_ledger_snapshot(
                ai_root,
                args.serving_access_apply_ledger_report_path,
                generated_at=args.generated_at,
            )
        if args.write_serving_access_policy_apply_report:
            write_serving_access_policy_apply_report(
                ai_root,
                args.serving_access_policy_apply_report_path,
                generated_at=args.generated_at,
            )
        if args.write_serving_access_policy_reconciliation_report:
            write_serving_access_policy_reconciliation_snapshot(
                ai_root,
                args.serving_access_policy_reconciliation_report_path,
                generated_at=args.generated_at,
            )
        if args.write_serving_access_incident_export_report:
            write_serving_access_incident_export_snapshot(
                ai_root,
                args.serving_access_incident_export_report_path,
                generated_at=args.generated_at,
                as_of=args.generated_at,
            )
        if args.write_product_readiness_freshness_incident_export_report:
            write_product_readiness_freshness_incident_export_snapshot(
                ai_root,
                args.product_readiness_freshness_incident_export_report_path,
                generated_at=args.generated_at,
                as_of=args.generated_at,
            )
        if args.write_product_readiness_freshness_incident_response_drill_report:
            write_product_readiness_freshness_incident_response_drill_snapshot(
                ai_root,
                args.product_readiness_freshness_incident_response_drill_report_path,
                generated_at=args.generated_at,
            )
        if args.write_product_readiness_freshness_response_metrics_report:
            write_product_readiness_freshness_response_metrics_snapshot(
                ai_root,
                args.product_readiness_freshness_response_metrics_report_path,
                generated_at=args.generated_at,
            )
        if args.write_product_readiness_freshness_response_trend_report:
            write_product_readiness_freshness_response_trend_snapshot(
                ai_root,
                args.product_readiness_freshness_response_trend_report_path,
                generated_at=args.generated_at,
            )
        if args.write_product_readiness_freshness_response_slo_drift_alert_report:
            write_product_readiness_freshness_response_slo_drift_alert_snapshot(
                ai_root,
                args.product_readiness_freshness_response_slo_drift_alert_report_path,
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_alert_drill_report
        ):
            write_product_readiness_freshness_response_slo_drift_alert_drill_snapshot(
                ai_root,
                args.product_readiness_freshness_response_slo_drift_alert_drill_report_path,
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_alert_calibration_report
        ):
            write_product_readiness_freshness_response_slo_drift_alert_calibration_snapshot(
                ai_root,
                (
                    args.product_readiness_freshness_response_slo_drift_alert_calibration_report_path
                ),
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_suppression_policy_report
        ):
            write_product_readiness_freshness_response_slo_drift_suppression_policy_snapshot(
                ai_root,
                (
                    args.product_readiness_freshness_response_slo_drift_suppression_policy_report_path
                ),
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report
        ):
            write_product_readiness_freshness_response_slo_drift_suppression_policy_drill_snapshot(
                ai_root,
                (
                    args.product_readiness_freshness_response_slo_drift_suppression_policy_drill_report_path
                ),
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report
        ):
            write_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_snapshot(
                ai_root,
                (
                    args.product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report_path
                ),
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report
        ):
            write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_snapshot(
                ai_root,
                (
                    args.product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report_path
                ),
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report
        ):
            write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_snapshot(
                ai_root,
                (
                    args.product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report_path
                ),
                generated_at=args.generated_at,
            )
        if (
            args.write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report
        ):
            write_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_snapshot(
                ai_root,
                (
                    args.product_readiness_freshness_response_slo_drift_suppression_policy_coverage_slo_report_path
                ),
                generated_at=args.generated_at,
            )
        if args.write_coverage_release_governance_report:
            write_coverage_release_governance_snapshot(
                ai_root,
                args.coverage_release_governance_report_path,
                generated_at=args.generated_at,
            )
        if args.write_coverage_release_gate_drill_report:
            write_coverage_release_gate_drill_snapshot(
                ai_root,
                args.coverage_release_gate_drill_report_path,
                generated_at=args.generated_at,
            )
        if args.write_coverage_release_gate_effectiveness_report:
            write_coverage_release_gate_effectiveness_snapshot(
                ai_root,
                args.coverage_release_gate_effectiveness_report_path,
                generated_at=args.generated_at,
            )
        if args.write_coverage_release_gate_enterprise_pattern_report:
            write_coverage_release_gate_enterprise_pattern_snapshot(
                ai_root,
                args.coverage_release_gate_enterprise_pattern_report_path,
                generated_at=args.generated_at,
            )
        if args.write_coverage_release_gate_enterprise_adoption_report:
            write_coverage_release_gate_enterprise_adoption_snapshot(
                ai_root,
                args.coverage_release_gate_enterprise_adoption_report_path,
                generated_at=args.generated_at,
            )
        if args.write_coverage_release_gate_enterprise_adoption_slo_report:
            write_coverage_release_gate_enterprise_adoption_slo_snapshot(
                ai_root,
                args.coverage_release_gate_enterprise_adoption_slo_report_path,
                generated_at=args.generated_at,
            )
        if (
            args.write_coverage_release_gate_enterprise_adoption_slo_release_governance_report
        ):
            write_coverage_release_gate_enterprise_adoption_slo_release_governance_snapshot(
                ai_root,
                (
                    args.coverage_release_gate_enterprise_adoption_slo_release_governance_report_path
                ),
                generated_at=args.generated_at,
            )
        if (
            args.write_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report
        ):
            write_coverage_release_gate_enterprise_adoption_slo_release_governance_drill_snapshot(
                ai_root,
                (
                    args.coverage_release_gate_enterprise_adoption_slo_release_governance_drill_report_path
                ),
                generated_at=args.generated_at,
            )
        admin_ops_dashboard_freshness = build_admin_ops_dashboard_freshness_manifest(
            ai_root,
            generated_at=dashboard_generated_at,
            dashboard_path=dashboard_output_path,
        )
        if args.write_admin_ops_dashboard_freshness_manifest:
            write_admin_ops_dashboard_freshness_manifest(
                ai_root,
                args.admin_ops_dashboard_freshness_manifest_path,
                generated_at=dashboard_generated_at,
                dashboard_path=dashboard_output_path,
            )
        product_id, product_name = load_platform_product_metadata(ai_root)
        ai_platform_product_readiness_report = (
            build_ai_platform_product_readiness_report_from_reports(
                product_id=product_id,
                product_name=product_name,
                operating_cockpit_report=operating_cockpit_report,
                delivery_state_report=delivery_state_report,
                dashboard_freshness=admin_ops_dashboard_freshness,
                serving_access_incident_export=serving_access_incident_export,
                governance_evaluation_incident_export=(
                    governance_evaluation_incident_export
                ),
                governance_evaluation_response_drill=(
                    governance_evaluation_incident_response_drill
                ),
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
                release_gate_enterprise_adoption_report=(
                    release_gate_enterprise_adoption_report
                ),
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
        )
        if args.write_ai_platform_product_readiness_report:
            write_ai_platform_product_readiness_snapshot(
                ai_root,
                args.ai_platform_product_readiness_report_path,
                generated_at=args.generated_at,
                report=ai_platform_product_readiness_report,
            )
        if args.write_ai_platform_product_readiness_freshness_report:
            ai_platform_product_readiness_freshness = (
                build_ai_platform_product_readiness_freshness_report(
                    ai_root,
                    generated_at=args.generated_at,
                )
            )
            write_ai_platform_product_readiness_freshness_snapshot(
                ai_root,
                args.ai_platform_product_readiness_freshness_report_path,
                generated_at=args.generated_at,
                report=ai_platform_product_readiness_freshness,
            )
    except RegistryValidationError as exc:
        print(f"AI Platform registry validation failed: {exc}")
        return 1

    release_gate_effectiveness = (
        product_readiness_freshness_response_alert_suppression_policy_release_gate_effectiveness
    )
    release_gate_effectiveness_payload = release_gate_effectiveness.to_dict()
    release_gate_enterprise_pattern = release_gate_enterprise_pattern_report
    release_gate_enterprise_pattern_payload = (
        release_gate_enterprise_pattern.to_dict()
    )
    release_gate_enterprise_adoption_payload = (
        release_gate_enterprise_adoption_report.to_dict()
    )
    release_gate_enterprise_adoption_slo_payload = (
        release_gate_enterprise_adoption_slo_report.to_dict()
    )
    release_gate_enterprise_adoption_slo_release_governance_payload = (
        release_gate_enterprise_adoption_slo_release_governance_report.to_dict()
    )
    release_gate_enterprise_adoption_slo_release_governance_drill_payload = (
        release_gate_enterprise_adoption_slo_release_governance_drill_report.to_dict()
    )
    report = {
        "aiCapabilityTaxonomy": ai_capability_taxonomy_report.to_dict(),
        "aiModuleCatalog": ai_module_catalog_report.to_dict(),
        "aiPlatformProductReadiness": ai_platform_product_readiness_report.to_dict(),
        "aiPlatformProductReadinessFreshness": (
            ai_platform_product_readiness_freshness.to_dict()
            if ai_platform_product_readiness_freshness is not None
            else None
        ),
        "productReadinessFreshnessIncidentExport": (
            product_readiness_freshness_incident_export.to_dict()
        ),
        "productReadinessFreshnessIncidentResponseDrill": (
            product_readiness_freshness_response_drill.to_dict()
        ),
        "productReadinessFreshnessResponseMetrics": (
            product_readiness_freshness_response_metrics.to_dict()
        ),
        "productReadinessFreshnessResponseTrends": (
            product_readiness_freshness_response_trends.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftAlerts": (
            product_readiness_freshness_response_alerts.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftAlertDrill": (
            product_readiness_freshness_response_alert_drill.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftAlertCalibration": (
            product_readiness_freshness_response_alert_calibration.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicy": (
            product_readiness_freshness_response_alert_suppression_policy.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyDrill": (
            product_readiness_freshness_response_alert_suppression_policy_drill.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyEffectiveness": (
            product_readiness_freshness_response_alert_suppression_policy_effectiveness.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage": (
            product_readiness_freshness_response_alert_suppression_policy_coverage.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegression": (
            product_readiness_freshness_response_alert_suppression_policy_regression.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSlo": (
            product_readiness_freshness_response_alert_suppression_policy_coverage_slo.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGovernance": (
            product_readiness_freshness_response_alert_suppression_policy_release_governance.to_dict()
        ),
        "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReleaseGateDrill": (
            product_readiness_freshness_response_alert_suppression_policy_release_gate_drill.to_dict()
        ),
        (
            "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
            "ReleaseGateEffectiveness"
        ): release_gate_effectiveness_payload,
        (
            "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
            "ReleaseGateEnterprisePattern"
        ): release_gate_enterprise_pattern_payload,
        (
            "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
            "ReleaseGateEnterpriseAdoption"
        ): release_gate_enterprise_adoption_payload,
        (
            "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
            "ReleaseGateEnterpriseAdoptionSlo"
        ): release_gate_enterprise_adoption_slo_payload,
        (
            "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
            "ReleaseGateEnterpriseAdoptionSloReleaseGovernance"
        ): release_gate_enterprise_adoption_slo_release_governance_payload,
        (
            "productReadinessFreshnessResponseSloDriftSuppressionPolicyCoverage"
            "ReleaseGateEnterpriseAdoptionSloReleaseGovernanceDrill"
        ): release_gate_enterprise_adoption_slo_release_governance_drill_payload,
        "adminOpsDashboard": admin_ops_dashboard.to_dict(),
        "adminOpsDashboardFreshness": admin_ops_dashboard_freshness.to_dict(),
        "coverageTaxonomy": coverage_taxonomy_report.to_dict(),
        "dataContractCoverage": data_contract_coverage_report.to_dict(),
        "deliveryBacklog": delivery_backlog_report.to_dict(),
        "deliveryState": delivery_state_report.to_dict(),
        "deliveryOwnerViews": delivery_owner_views_report.to_dict(),
        "deliverySla": delivery_sla_report.to_dict(),
        "evidence": evidence_report.to_dict(),
        "evaluations": evaluation_report.to_dict(),
        "governanceEvaluationOps": governance_evaluation_ops_report.to_dict(),
        "governanceEvaluationIncidentExport": (
            governance_evaluation_incident_export.to_dict()
        ),
        "governanceEvaluationIncidentResponseDrill": (
            governance_evaluation_incident_response_drill.to_dict()
        ),
        "modelServingMetricsExport": (
            model_serving_metrics_export.to_dict()
            if model_serving_metrics_export is not None
            else None
        ),
        "llmProviderReadiness": llm_provider_readiness_report.to_dict(),
        "llmProviderAlertRouting": llm_provider_alert_routing_report.to_dict(),
        "llmProviderRuntimeProbes": llm_provider_runtime_probe_report.to_dict(),
        "llmProviderSecretRotation": llm_provider_secret_rotation_report.to_dict(),
        "mediaPrivacyReview": media_privacy_review_report.to_dict(),
        "operatingCockpit": operating_cockpit_report.to_dict(),
        "promotionIntake": promotion_intake_report.to_dict(),
        "promotionReadiness": promotion_readiness_report.to_dict(),
        "registry": registry_report.to_dict(),
        "runtimeRoadmap": runtime_roadmap_report.to_dict(),
        "servingAccessApplyLedger": serving_access_apply_ledger_report.to_dict(),
        "servingAccessIncidentExport": serving_access_incident_export.to_dict(),
        "servingAccessPolicyApply": serving_access_policy_apply_report.to_dict(),
        "servingAccessPolicyPatchPlan": serving_access_policy_patch_plan.to_dict(),
        "servingAccessPolicyReconciliation": (
            serving_access_policy_reconciliation_report.to_dict()
        ),
        "servingAccessReview": serving_access_review_report.to_dict(),
        "solutionBlueprints": solution_blueprint_report.to_dict(),
    }
    print(json.dumps(report, sort_keys=True))
    return 0


def default_ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_delivery_sla_policy(ai_root: Path) -> dict[str, Any]:
    return load_yaml(ai_root / "platform" / "delivery" / "policies" / "sla-policy.yaml")


def parse_generated_at(generated_at: str | None) -> date:
    return parse_optional_date(generated_at)


if __name__ == "__main__":
    raise SystemExit(main())
