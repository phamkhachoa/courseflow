from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from enterprise_dp.contracts import ValidationResult
from enterprise_dp.semantic_metrics import validate_metric_entry, validate_semantic_metric_registry, validation_context


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "platform" / "serving" / "semantic-metrics.yaml"


def test_repository_semantic_metric_registry_is_valid() -> None:
    result = validate_semantic_metric_registry(ROOT)

    assert result.errors == []
    assert result.checked_count >= 10


def test_access_risk_metrics_are_registered_for_compliance_serving() -> None:
    metric = load_metric("critical_access_risk_subject_count")

    assert metric["domain"] == "compliance"
    assert metric["source"]["dataProduct"] == "gold.access_risk_daily"
    assert metric["source"]["timeColumn"] == "report_date"
    assert metric["useCases"] == ["identity-access-governance", "enterprise-kpi-scorecard"]
    assert "ComplianceConsumer" in metric["consumers"]
    assert "RiskOperator" in metric["consumers"]
    assert metric["serving"]["dremioVirtualDataset"].endswith(".critical_access_risk_subject_count")


def test_customer_360_metrics_are_registered_for_customer_serving() -> None:
    metric = load_metric("at_risk_customer_account_count")

    assert metric["domain"] == "customer"
    assert metric["source"]["dataProduct"] == "gold.customer_360_profile"
    assert metric["source"]["timeColumn"] == "report_date"
    assert metric["useCases"] == ["customer-account-health", "enterprise-kpi-scorecard"]
    assert "ApprovedBIConsumer" in metric["consumers"]
    assert "ApprovedMLConsumer" in metric["consumers"]
    assert metric["serving"]["dremioVirtualDataset"].endswith(".at_risk_customer_account_count")


def test_enterprise_revenue_metrics_use_certified_billing_gold() -> None:
    metric = load_metric("revenue_net")

    assert metric["domain"] == "finance"
    assert metric["source"]["dataProduct"] == "gold.finance_revenue_daily"
    assert metric["source"]["timeColumn"] == "report_date"
    assert metric["useCases"] == ["enterprise-kpi-scorecard", "enterprise-revenue-intelligence"]
    assert metric["calculation"]["referencedColumns"] == ["net_revenue_cents"]
    assert "ExecutiveConsumer" in metric["consumers"]


def test_support_metrics_are_registered_for_customer_experience_serving() -> None:
    metric = load_metric("support_case_count")

    assert metric["domain"] == "customer"
    assert metric["source"]["dataProduct"] == "gold.support_sla_daily"
    assert metric["source"]["timeColumn"] == "report_date"
    assert metric["useCases"] == ["customer-support-experience-intelligence", "enterprise-kpi-scorecard"]
    assert "ApprovedBIConsumer" in metric["consumers"]
    assert "ExecutiveConsumer" in metric["consumers"]
    assert metric["serving"]["trinoView"].endswith(".support_case_count")


def test_control_tower_metrics_are_registered_for_executive_scorecard() -> None:
    blocker_metric = load_metric("p0_data_product_blocker_count")
    lineage_metric = load_metric("runtime_lineage_gap_count")

    assert blocker_metric["domain"] == "enterprise-reporting"
    assert blocker_metric["source"]["dataProduct"] == "gold.data_product_inventory"
    assert blocker_metric["useCases"] == ["data-product-control-tower", "enterprise-kpi-scorecard"]
    assert "ExecutiveConsumer" in blocker_metric["consumers"]
    assert lineage_metric["source"]["dataProduct"] == "gold.lineage_coverage_daily"
    assert lineage_metric["serving"]["dremioVirtualDataset"].endswith(".runtime_lineage_gap_count")


def test_semantic_metric_rejects_unknown_source_column() -> None:
    metric = load_metric("revenue_net")
    metric["calculation"]["referencedColumns"] = ["missing_revenue_column"]
    metric["calculation"]["expressionSql"] = "SUM(missing_revenue_column)"
    result = ValidationResult()

    validate_metric_entry(REGISTRY_PATH, metric, 0, set(), validation_context(ROOT), result)

    assert any("references unknown source column 'missing_revenue_column'" in error for error in result.errors)


def test_semantic_metric_expression_must_mention_referenced_columns() -> None:
    metric = load_metric("revenue_net")
    metric["calculation"]["referencedColumns"] = ["net_revenue_cents"]
    metric["calculation"]["expressionSql"] = "COUNT(*)"
    result = ValidationResult()

    validate_metric_entry(REGISTRY_PATH, metric, 0, set(), validation_context(ROOT), result)

    assert any("expressionSql does not mention referenced columns" in error for error in result.errors)


def test_semantic_metric_rejects_unknown_use_case_and_consumer() -> None:
    metric = load_metric("benefit_reconciliation_gap")
    metric["useCases"] = ["unknown-use-case"]
    metric["consumers"] = ["UnknownPersona"]
    result = ValidationResult()

    validate_metric_entry(REGISTRY_PATH, metric, 0, set(), validation_context(ROOT), result)

    assert any("useCases contains unknown use case" in error for error in result.errors)
    assert any("consumers references unknown persona" in error for error in result.errors)


def test_semantic_metric_requires_serving_name_to_end_with_metric_id() -> None:
    metric = load_metric("points_earned")
    metric["serving"]["trinoView"] = "semantic.enterprise_metrics.points"
    result = ValidationResult()

    validate_metric_entry(REGISTRY_PATH, metric, 0, set(), validation_context(ROOT), result)

    assert any("serving.trinoView must end with .points_earned" in error for error in result.errors)


def load_metric(metric_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for metric in registry["metrics"]:
        if metric["metricId"] == metric_id:
            return deepcopy(metric)
    raise AssertionError(f"metric not found: {metric_id}")
