from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.catalog import build_catalog_bundle, write_catalog_bundle
from enterprise_df.ingestion import run_bronze_ingestion
from enterprise_df.pipelines import run_recommendation_pipeline_from_bronze


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
BUILT_AT = "2026-01-15T11:00:00Z"
INGESTED_AT = "2026-01-15T11:00:05Z"


def test_catalog_bundle_exports_enterprise_metadata_and_static_lineage() -> None:
    bundle = build_catalog_bundle(ROOT, generated_at="2026-01-15T12:00:00Z")

    assert bundle["bundle_version"] == 1
    assert bundle["summary"]["product_count"] >= 2
    assert bundle["summary"]["domain_count"] >= 9
    assert bundle["summary"]["access_persona_count"] >= 8
    assert bundle["summary"]["consumer_contract_count"] >= 1
    assert bundle["summary"]["access_grant_count"] >= 7
    assert bundle["summary"]["change_request_count"] >= 3
    assert bundle["summary"]["access_policy_count"] >= 2
    assert bundle["summary"]["retention_policy_count"] >= 4
    assert bundle["summary"]["quality_profile_count"] >= 2
    assert bundle["summary"]["release_evidence_profile_count"] >= 1
    assert bundle["summary"]["use_case_count"] >= 7
    assert bundle["summary"]["topic_count"] >= 5
    assert bundle["summary"]["data_product_count"] >= 9

    enterprise_commerce = next(product for product in bundle["products"] if product["code"] == "enterprise-commerce")
    assert enterprise_commerce["name"] == "Enterprise Commerce Platform"

    gold = data_product(bundle, "gold.recsys_interactions")
    assert gold["urn"] == "urn:enterprise-df:data-product:gold.recsys_interactions"
    assert gold["contract_urn"] == "urn:enterprise-df:data-product:gold.recsys_interactions:v1"
    assert gold["product"] == "lms-courseflow"
    assert gold["domain"] == "recommendation"
    assert gold["data_steward"] == "enterprise-data-steward"
    assert gold["serving"]["publication_gate"] == "quality_checks_must_pass"
    assert gold["privacy"]["subject_keys"][0]["name"] == "learner_id_hash"
    assert gold["privacy"]["subject_keys"][0]["column"] == "learner_id_hash"
    assert gold["privacy"]["raw_payload_policy"] == "NO_RAW_PAYLOAD"
    assert any(column["name"] == "learner_id_hash" and column["pii"] is True for column in gold["columns"])

    topic = topic_entry(bundle, "recommendation.tracking.v1")
    assert topic["urn"] == "urn:enterprise-df:topic:recommendation.tracking.v1"
    assert topic["contract_urn"] == "urn:enterprise-df:topic:recommendation.tracking.v1:v1"
    assert topic["ingestion"]["bronze_target"] == "bronze.events_recommendation_tracking"
    assert topic["schema"]["compatibility"] == "BACKWARD_TRANSITIVE"

    edge_types = {edge["type"] for edge in bundle["lineage_edges"]}
    assert "TOPIC_TO_BRONZE" in edge_types
    assert "DATA_PRODUCT_UPSTREAM" in edge_types
    assert "USE_CASE_DATA_PRODUCT" in edge_types
    finance_use_case = next(use_case for use_case in bundle["use_cases"] if use_case["id"] == "finance-benefit-reconciliation")
    assert finance_use_case["pipeline_runners"] == ["finance.benefit_reconciliation.from_approved_bronze.v1"]
    assert finance_use_case["implementation_summary"]["input_topics"] == ["finance.benefit_settled.v1"]
    assert finance_use_case["implementation_summary"]["primary_outputs"] == ["gold.finance_benefit_reconciliation"]
    assert finance_use_case["implementation_summary"]["quality_profiles"] == ["p0-finance-benefit-reconciliation"]
    assert finance_use_case["implementation_summary"]["release_evidence_profiles"] == ["local-medallion-release.v1"]
    ml_use_case = next(use_case for use_case in bundle["use_cases"] if use_case["id"] == "ml-feature-governance")
    assert ml_use_case["pipeline_runners"] == ["recommendation.from_approved_bronze.v1"]
    assert ml_use_case["implementation_summary"]["runner_ids"] == ["recommendation.from_approved_bronze.v1"]
    assert ml_use_case["implementation_summary"]["input_topics"] == ["recommendation.tracking.v1"]
    assert ml_use_case["implementation_summary"]["input_data_products"] == ["bronze.events_recommendation_tracking"]
    assert ml_use_case["implementation_summary"]["primary_outputs"] == ["gold.recsys_interactions"]
    assert ml_use_case["implementation_summary"]["quality_profiles"] == ["p0-gold-ml-feature"]
    assert ml_use_case["implementation_summary"]["release_evidence_profiles"] == ["local-medallion-release.v1"]
    finance_profile = next(profile for profile in bundle["quality_profiles"] if profile["id"] == "p0-finance-benefit-reconciliation")
    assert finance_profile["applies_to"]["primaryOutputs"] == ["gold.finance_benefit_reconciliation"]
    assert finance_profile["thresholds"]["maxQuarantineRows"] == 0
    release_profile = next(profile for profile in bundle["release_evidence_profiles"] if profile["id"] == "local-medallion-release.v1")
    assert "P0-QUALITY-PROFILE" in release_profile["required_gates"]
    assert "pipeline_manifest_hash" in release_profile["required_artifacts"]
    access_persona = next(persona for persona in bundle["access_personas"] if persona["id"] == "ApprovedMLConsumer")
    assert access_persona["status"] == "active"
    assert "GOLD" in access_persona["allowed_layers"]
    consumer_contract = next(contract for contract in bundle["consumer_contracts"] if contract["id"] == "catalog_registered_access_request_required")
    assert consumer_contract["severity"] == "P0"
    assert "data_owner_approval" in consumer_contract["required_evidence"]
    access_grant = next(grant for grant in bundle["access_grants"] if grant["id"] == "grant_recsys_gold_ml_2026")
    assert access_grant["status"] == "active"
    assert access_grant["data_product"] == "gold.recsys_interactions"
    assert access_grant["persona"] == "ApprovedMLConsumer"
    change_request = next(request for request in bundle["change_requests"] if request["id"] == "publish_finance_benefit_reconciliation_prod")
    assert change_request["status"] == "approved"
    assert change_request["data_product"] == "gold.finance_benefit_reconciliation"
    assert change_request["target_environment"] == "prod"
    access_policy = next(policy for policy in bundle["access_policies"] if policy["id"] == "row_level_org_isolation")
    assert access_policy["severity"] == "P0"
    assert access_policy["required_columns"] == ["org_id"]
    assert "GOLD" in access_policy["applies_to"]["layers"]
    retention_policy = next(policy for policy in bundle["retention_policies"] if policy["id"] == "certified_ml_feature_2y")
    assert retention_policy["max_retention_days"] == 730
    assert retention_policy["erasure_required"] is True
    assert any(
        edge["source"].endswith("silver.learner_activity")
        and edge["target"].endswith("gold.recsys_interactions")
        for edge in bundle["lineage_edges"]
    )


def test_catalog_bundle_includes_run_evidence_from_ingestion_and_gold_manifests(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="catalog-ingest-run",
    )
    recommendation = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        tmp_path / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="catalog-recsys-snapshot",
        built_at=BUILT_AT,
    )

    bundle = build_catalog_bundle(
        ROOT,
        manifest_paths=[ingestion.manifest_path, recommendation.manifest_path],
        generated_at="2026-01-15T12:00:00Z",
    )

    assert bundle["summary"]["run_evidence_count"] == 2
    assert any(run["pipeline"] == "bronze_ingestion.local_jsonl.v1" for run in bundle["run_evidence"])
    gold_run = next(run for run in bundle["run_evidence"] if run["pipeline"] == "recommendation.from_approved_bronze.v1")
    assert gold_run["snapshot_id"] == "catalog-recsys-snapshot"
    assert gold_run["quality_passed"] is True
    assert gold_run["upstream_quality_passed"] is True
    assert gold_run["source_positions"] == ingestion.manifest["source_positions"]
    run_edges = [
        edge for edge in bundle["lineage_edges"]
        if edge["type"] == "RUN_LAYER_TRANSFORM" and edge["run"] == gold_run["urn"]
    ]
    assert [(edge["source"], edge["target"]) for edge in run_edges] == [
        (
            "urn:enterprise-df:data-product:bronze.events_recommendation_tracking",
            "urn:enterprise-df:data-product:silver.learner_activity",
        ),
        (
            "urn:enterprise-df:data-product:silver.learner_activity",
            "urn:enterprise-df:data-product:gold.recsys_interactions",
        ),
    ]
    assert any(edge["type"] == "RUN_TOPIC_TO_BRONZE" for edge in bundle["lineage_edges"])


def test_write_catalog_bundle_and_cli_export(tmp_path: Path) -> None:
    output_path = tmp_path / "catalog" / "bundle.json"
    bundle = write_catalog_bundle(
        ROOT,
        output_path,
        generated_at="2026-01-15T12:00:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == bundle

    cli_output = tmp_path / "catalog" / "cli-bundle.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "catalog-export",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-01-15T12:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["output"] == str(cli_output)
    assert summary["data_products"] >= 9
    assert summary["topics"] >= 5
    assert summary["access_personas"] >= 8
    assert summary["consumer_contracts"] >= 1
    assert summary["access_grants"] >= 7
    assert summary["change_requests"] >= 3
    assert summary["access_policies"] >= 2
    assert summary["retention_policies"] >= 4
    assert summary["quality_profiles"] >= 2
    assert summary["release_evidence_profiles"] >= 1
    assert summary["use_cases"] >= 7
    assert cli_output.is_file()


def data_product(bundle: dict[str, object], name: str) -> dict[str, object]:
    return next(item for item in bundle["data_products"] if item["name"] == name)


def topic_entry(bundle: dict[str, object], name: str) -> dict[str, object]:
    return next(item for item in bundle["topics"] if item["name"] == name)
