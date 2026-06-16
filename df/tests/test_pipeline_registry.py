from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.ingestion import run_bronze_ingestion
from enterprise_df.pipelines import PipelineRegistry, PipelineRunRequest, default_pipeline_registry
from enterprise_df.pipelines.recommendation import RecommendationFromBronzeRunner


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
BUILT_AT = "2026-01-15T11:00:00Z"
INGESTED_AT = "2026-01-15T11:00:05Z"


def test_pipeline_registry_lists_recommendation_runners() -> None:
    registry = default_pipeline_registry()
    specs = {spec.runner_id: spec for spec in registry.list_specs()}

    assert "control_tower.materialize_gold.from_report.v1" in specs
    assert "billing.revenue_daily.from_approved_bronze.v1" in specs
    assert "customer.account_health.from_approved_bronze.v1" in specs
    assert "enterprise_reporting.executive_scorecard.from_semantic_snapshot.v1" in specs
    assert "finance.benefit_reconciliation.from_approved_bronze.v1" in specs
    assert "identity.access_governance.from_approved_bronze.v1" in specs
    assert "recommendation.from_approved_bronze.v1" in specs
    assert "recommendation.local_jsonl.v1" in specs
    assert "support.sla.from_approved_bronze.v1" in specs
    control_tower = specs["control_tower.materialize_gold.from_report.v1"]
    assert control_tower.product == "enterprise-data-foundation"
    assert control_tower.domain == "enterprise-reporting"
    assert control_tower.use_cases == ("data-product-control-tower",)
    assert control_tower.input_kind == "data_product_snapshot"
    assert control_tower.output_data_products == (
        "gold.data_product_inventory",
        "gold.contract_compliance_daily",
        "gold.quality_sla_daily",
        "gold.lineage_coverage_daily",
    )
    assert control_tower.primary_output == "gold.data_product_inventory"
    billing = specs["billing.revenue_daily.from_approved_bronze.v1"]
    assert billing.product == "billing-platform"
    assert billing.domain == "finance"
    assert billing.use_cases == ("enterprise-revenue-intelligence",)
    assert billing.input_kind == "approved_bronze_jsonl"
    assert billing.input_topics == ("finance.billing_transaction.settled.v1",)
    assert billing.input_data_products == ("bronze.events_billing_transaction_settled",)
    assert billing.output_data_products == (
        "silver.finance_billing_transactions",
        "gold.finance_revenue_daily",
    )
    assert billing.primary_output == "gold.finance_revenue_daily"
    customer = specs["customer.account_health.from_approved_bronze.v1"]
    assert customer.product == "crm-sales"
    assert customer.domain == "customer"
    assert customer.use_cases == ("customer-account-health",)
    assert customer.input_kind == "approved_bronze_jsonl"
    assert customer.input_topics == ("customer.account.changed.v1",)
    assert customer.input_data_products == ("bronze.events_customer_account_changed",)
    assert customer.output_data_products == (
        "silver.customer_identity_link",
        "gold.customer_360_profile",
    )
    assert customer.primary_output == "gold.customer_360_profile"
    scorecard = specs["enterprise_reporting.executive_scorecard.from_semantic_snapshot.v1"]
    assert scorecard.product == "enterprise-data-foundation"
    assert scorecard.domain == "enterprise-reporting"
    assert scorecard.use_cases == ("enterprise-kpi-scorecard",)
    assert scorecard.input_kind == "semantic_metric_snapshot"
    assert scorecard.input_data_products == (
        "gold.finance_revenue_daily",
        "gold.finance_benefit_reconciliation",
        "gold.customer_360_profile",
        "gold.access_risk_daily",
        "gold.support_sla_daily",
        "gold.recsys_interactions",
        "gold.data_product_inventory",
        "gold.contract_compliance_daily",
        "gold.quality_sla_daily",
        "gold.lineage_coverage_daily",
    )
    assert scorecard.output_data_products == (
        "gold.enterprise_kpi_daily",
        "gold.executive_scorecard_daily",
    )
    assert scorecard.primary_output == "gold.executive_scorecard_daily"
    finance = specs["finance.benefit_reconciliation.from_approved_bronze.v1"]
    assert finance.product == "enterprise-commerce"
    assert finance.domain == "finance"
    assert finance.use_cases == ("finance-benefit-reconciliation",)
    assert finance.input_topics == ("finance.benefit_settled.v1",)
    assert finance.input_data_products == ("bronze.events_benefit_settled",)
    assert finance.output_data_products == (
        "silver.finance_benefit_transactions",
        "gold.finance_benefit_reconciliation",
    )
    assert finance.primary_output == "gold.finance_benefit_reconciliation"
    identity = specs["identity.access_governance.from_approved_bronze.v1"]
    assert identity.product == "identity-platform"
    assert identity.domain == "compliance"
    assert identity.use_cases == ("identity-access-governance",)
    assert identity.input_topics == ("compliance.identity_subject.changed.v1",)
    assert identity.input_data_products == ("bronze.events_identity_subject_changed",)
    assert identity.output_data_products == ("silver.identity_subject", "gold.access_risk_daily")
    assert identity.primary_output == "gold.access_risk_daily"
    support = specs["support.sla.from_approved_bronze.v1"]
    assert support.product == "support-platform"
    assert support.domain == "customer"
    assert support.use_cases == ("customer-support-experience-intelligence",)
    assert support.input_topics == ("customer.support_case.changed.v1",)
    assert support.input_data_products == ("bronze.events_support_case_changed",)
    assert support.output_data_products == ("silver.support_case", "gold.support_sla_daily")
    assert support.primary_output == "gold.support_sla_daily"
    assert specs["recommendation.from_approved_bronze.v1"].product == "lms-courseflow"
    assert specs["recommendation.from_approved_bronze.v1"].use_cases == ("ml-feature-governance",)
    assert specs["recommendation.from_approved_bronze.v1"].output_data_products == (
        "silver.learner_activity",
        "gold.recsys_interactions",
    )
    assert specs["recommendation.from_approved_bronze.v1"].input_topics == ("recommendation.tracking.v1",)
    assert specs["recommendation.from_approved_bronze.v1"].input_data_products == ("bronze.events_recommendation_tracking",)
    assert specs["recommendation.from_approved_bronze.v1"].primary_output == "gold.recsys_interactions"
    assert "release_gates" in specs["recommendation.from_approved_bronze.v1"].evidence_capabilities
    assert registry.find_by_use_case("finance-benefit-reconciliation")[0].runner_id == "finance.benefit_reconciliation.from_approved_bronze.v1"
    assert registry.find_by_use_case("enterprise-revenue-intelligence")[0].runner_id == "billing.revenue_daily.from_approved_bronze.v1"
    assert registry.find_by_use_case("customer-account-health")[0].runner_id == "customer.account_health.from_approved_bronze.v1"
    assert registry.find_by_use_case("enterprise-kpi-scorecard")[0].runner_id == "enterprise_reporting.executive_scorecard.from_semantic_snapshot.v1"
    assert registry.find_by_use_case("identity-access-governance")[0].runner_id == "identity.access_governance.from_approved_bronze.v1"
    assert registry.find_by_use_case("customer-support-experience-intelligence")[0].runner_id == "support.sla.from_approved_bronze.v1"
    assert registry.find_by_use_case("data-product-control-tower")[0].runner_id == "control_tower.materialize_gold.from_report.v1"
    assert registry.find_by_use_case("ml-feature-governance")[0].runner_id == "recommendation.from_approved_bronze.v1"
    assert registry.find_by_output_data_product("gold.recsys_interactions")
    assert registry.find_by_output_data_product("gold.finance_revenue_daily")
    assert registry.find_by_output_data_product("gold.customer_360_profile")
    assert registry.find_by_output_data_product("gold.access_risk_daily")
    assert registry.find_by_output_data_product("gold.finance_benefit_reconciliation")
    assert registry.find_by_output_data_product("gold.data_product_inventory")
    assert registry.find_by_output_data_product("gold.enterprise_kpi_daily")
    assert registry.find_by_output_data_product("gold.executive_scorecard_daily")
    assert registry.find_by_output_data_product("gold.support_sla_daily")


def test_pipeline_registry_rejects_duplicate_runner_id() -> None:
    registry = PipelineRegistry(runners={})
    registry.register(RecommendationFromBronzeRunner())

    try:
        registry.register(RecommendationFromBronzeRunner())
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate runner id was accepted")


def test_pipeline_registry_runs_recommendation_from_bronze(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="registry-ingest-run",
    )
    result = default_pipeline_registry().run(
        "recommendation.from_approved_bronze.v1",
        PipelineRunRequest(
            input_path=ingestion.approved_path,
            output_dir=tmp_path / "medallion",
            options={
                "upstream_manifest_path": ingestion.manifest_path,
                "snapshot_id": "registry-recsys-snapshot",
                "built_at": BUILT_AT,
            },
        ),
    )

    assert result.snapshot_id == "registry-recsys-snapshot"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["row_count"] == 3
    assert result.gold_path.is_file()


def test_cli_lists_and_runs_registered_pipeline(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="cli-registry-ingest-run",
    )
    list_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "pipeline-list",
            "--use-case",
            "ml-feature-governance",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert list_completed.returncode == 0, list_completed.stderr
    listed = json.loads(list_completed.stdout)
    assert any(pipeline["runner_id"] == "recommendation.from_approved_bronze.v1" for pipeline in listed["pipelines"])

    describe_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "pipeline-describe",
            "--runner-id",
            "recommendation.from_approved_bronze.v1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert describe_completed.returncode == 0, describe_completed.stderr
    described = json.loads(describe_completed.stdout)
    assert described["runner_id"] == "recommendation.from_approved_bronze.v1"
    assert described["output_data_products"] == ["silver.learner_activity", "gold.recsys_interactions"]

    run_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "run-pipeline",
            "--runner-id",
            "recommendation.from_approved_bronze.v1",
            "--input",
            str(ingestion.approved_path),
            "--output-dir",
            str(tmp_path / "medallion"),
            "--upstream-manifest",
            str(ingestion.manifest_path),
            "--snapshot-id",
            "cli-registry-recsys-snapshot",
            "--built-at",
            BUILT_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert run_completed.returncode == 0, run_completed.stderr
    output = json.loads(run_completed.stdout)
    assert output["runner_id"] == "recommendation.from_approved_bronze.v1"
    assert output["snapshot_id"] == "cli-registry-recsys-snapshot"
    assert output["quality_passed"] is True
    assert Path(output["manifest_path"]).is_file()
