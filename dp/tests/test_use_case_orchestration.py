from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from enterprise_dp.release import build_pipeline_release_evidence
from enterprise_dp.orchestration import run_use_case


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
INGESTED_AT = "2026-01-15T10:10:00Z"
BUILT_AT = "2026-01-15T10:10:05Z"
EVALUATION_TIME = "2026-01-15T10:10:10Z"
FINANCE_INGESTED_AT = "2026-01-15T09:15:05Z"
FINANCE_BUILT_AT = "2026-01-15T09:15:10Z"
FINANCE_EVALUATION_TIME = "2026-01-15T09:15:15Z"


def test_run_use_case_orchestrates_full_generic_evidence(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        SAMPLE_INPUT,
        tmp_path,
        use_case_id="ml-feature-governance",
        release_id="local-ml-feature-test",
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        code_commit_sha="abc123",
        approver="sa-data-platform",
    )

    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    gates = gates_by_id(evidence)

    assert evidence == result.evidence
    assert evidence["release_passed"] is True
    assert result.use_case_id == "ml-feature-governance"
    assert result.runner_id == "recommendation.from_approved_bronze.v1"
    assert result.topic == "recommendation.tracking.v1"
    assert result.primary_output == "gold.recsys_interactions"
    assert evidence["input_topics"] == ["recommendation.tracking.v1"]
    assert evidence["input_data_products"] == ["bronze.events_recommendation_tracking"]
    assert evidence["output_data_products"] == ["silver.learner_activity", "gold.recsys_interactions"]
    assert evidence["quality_profile_id"] == "p0-gold-ml-feature"
    assert str(evidence["quality_profile_hash"]).startswith("sha256:")
    assert evidence["release_evidence_profile_id"] == "local-medallion-release.v1"
    assert str(evidence["release_evidence_profile_hash"]).startswith("sha256:")
    assert evidence["quality_report"]["approved_rows"] == 3
    assert evidence["quality_report"]["quarantine_rows"] == 0
    assert gates["P0-PIPELINE-QUALITY"]["passed"] is True
    assert gates["P0-INGESTION-LAG"]["passed"] is True
    assert gates["P0-FRESHNESS"]["passed"] is True
    assert gates["P0-ACCESS-GRANT-EVIDENCE"]["passed"] is True
    assert gates["P0-RETENTION-ERASURE"]["passed"] is True
    assert gates["P0-QUALITY-PROFILE"]["passed"] is True
    assert gates["P0-QUALITY-PROFILE"]["details"]["profile_id"] == "p0-gold-ml-feature"
    assert gates["P0-OUTPUT-EVIDENCE"]["passed"] is True
    assert gates["P0-RELEASE-EVIDENCE-PROFILE"]["passed"] is True
    assert gates["P0-CATALOG-LINEAGE"]["passed"] is True
    assert result.ingestion is not None
    assert result.ingestion.manifest_path.is_file()
    assert result.pipeline.manifest_path.is_file()
    assert result.catalog_bundle_path.is_file()
    assert evidence["access_grant_evidence_uri"]
    assert evidence["retention_evidence_uri"]


def test_cli_runs_use_case_with_auto_resolved_runner_topic_and_output(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "run-use-case",
            "--root",
            str(ROOT),
            "--use-case-id",
            "ml-feature-governance",
            "--input",
            str(SAMPLE_INPUT),
            "--output-dir",
            str(tmp_path),
            "--release-id",
            "cli-ml-feature-test",
            "--environment",
            "local",
            "--ingested-at",
            INGESTED_AT,
            "--built-at",
            BUILT_AT,
            "--evaluation-time",
            EVALUATION_TIME,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["use_case_id"] == "ml-feature-governance"
    assert output["runner_id"] == "recommendation.from_approved_bronze.v1"
    assert output["topic"] == "recommendation.tracking.v1"
    assert output["primary_output"] == "gold.recsys_interactions"
    assert output["release_passed"] is True
    assert output["gates"]["P0-OUTPUT-EVIDENCE"] is True
    assert Path(output["ingestion_manifest_path"]).is_file()
    assert Path(output["pipeline_manifest_path"]).is_file()
    assert Path(output["evidence_path"]).is_file()


def test_run_use_case_orchestrates_finance_reconciliation(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path,
        use_case_id="finance-benefit-reconciliation",
        release_id="local-finance-recon-test",
        environment="local",
        ingested_at=FINANCE_INGESTED_AT,
        built_at=FINANCE_BUILT_AT,
        evaluation_time=FINANCE_EVALUATION_TIME,
    )

    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    gates = gates_by_id(evidence)

    assert evidence == result.evidence
    assert evidence["release_passed"] is True
    assert result.runner_id == "finance.benefit_reconciliation.from_approved_bronze.v1"
    assert result.topic == "finance.benefit_settled.v1"
    assert result.primary_output == "gold.finance_benefit_reconciliation"
    assert evidence["input_data_products"] == ["bronze.events_benefit_settled"]
    assert evidence["output_data_products"] == [
        "silver.finance_benefit_transactions",
        "gold.finance_benefit_reconciliation",
    ]
    assert evidence["quality_profile_id"] == "p0-finance-benefit-reconciliation"
    assert str(evidence["quality_profile_hash"]).startswith("sha256:")
    assert evidence["release_evidence_profile_id"] == "local-medallion-release.v1"
    assert str(evidence["release_evidence_profile_hash"]).startswith("sha256:")
    assert evidence["quality_report"]["approved_rows"] == 4
    assert evidence["quality_report"]["primary_output_rows"] == 4
    assert gates["P0-PIPELINE-QUALITY"]["passed"] is True
    assert gates["P0-INGESTION-LAG"]["passed"] is True
    assert gates["P0-FRESHNESS"]["passed"] is True
    assert gates["P0-ACCESS-GRANT-EVIDENCE"]["passed"] is True
    assert gates["P0-RETENTION-ERASURE"]["passed"] is True
    assert gates["P0-QUALITY-PROFILE"]["passed"] is True
    assert gates["P0-QUALITY-PROFILE"]["details"]["profile_id"] == "p0-finance-benefit-reconciliation"
    assert gates["P0-OUTPUT-EVIDENCE"]["passed"] is True
    assert gates["P0-RELEASE-EVIDENCE-PROFILE"]["passed"] is True
    assert gates["P0-CATALOG-LINEAGE"]["passed"] is True


def test_cli_runs_finance_use_case(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "run-use-case",
            "--root",
            str(ROOT),
            "--use-case-id",
            "finance-benefit-reconciliation",
            "--input",
            str(FINANCE_SAMPLE_INPUT),
            "--output-dir",
            str(tmp_path),
            "--release-id",
            "cli-finance-recon-test",
            "--environment",
            "local",
            "--ingested-at",
            FINANCE_INGESTED_AT,
            "--built-at",
            FINANCE_BUILT_AT,
            "--evaluation-time",
            FINANCE_EVALUATION_TIME,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["use_case_id"] == "finance-benefit-reconciliation"
    assert output["runner_id"] == "finance.benefit_reconciliation.from_approved_bronze.v1"
    assert output["topic"] == "finance.benefit_settled.v1"
    assert output["primary_output"] == "gold.finance_benefit_reconciliation"
    assert output["release_passed"] is True
    assert output["gates"]["P0-OUTPUT-EVIDENCE"] is True
    assert Path(output["evidence_path"]).is_file()


def test_run_use_case_blocks_when_generic_ingestion_lag_exceeds_slo(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path,
        use_case_id="finance-benefit-reconciliation",
        release_id="local-finance-lag-test",
        environment="local",
        ingested_at="2026-01-15T09:40:00Z",
        built_at="2026-01-15T09:40:05Z",
        evaluation_time="2026-01-15T09:40:10Z",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert gates["P0-INGESTION-LAG"]["passed"] is False
    assert gates["P0-INGESTION-LAG"]["details"]["max_lag_seconds"] > 900
    assert gates["P0-FRESHNESS"]["passed"] is True


def test_run_use_case_blocks_when_generic_freshness_exceeds_slo(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path,
        use_case_id="finance-benefit-reconciliation",
        release_id="local-finance-freshness-test",
        environment="local",
        ingested_at=FINANCE_INGESTED_AT,
        built_at=FINANCE_BUILT_AT,
        evaluation_time="2026-01-15T14:00:00Z",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert gates["P0-INGESTION-LAG"]["passed"] is True
    assert gates["P0-FRESHNESS"]["passed"] is False
    assert gates["P0-FRESHNESS"]["details"]["gold.finance_benefit_reconciliation"]["age_seconds"] > 14400


def test_pipeline_release_rejects_catalog_with_wrong_run_transform_lineage(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path / "source",
        use_case_id="finance-benefit-reconciliation",
        release_id="local-finance-lineage-test",
        environment="local",
        ingested_at=FINANCE_INGESTED_AT,
        built_at=FINANCE_BUILT_AT,
        evaluation_time=FINANCE_EVALUATION_TIME,
    )
    broken_bundle = json.loads(result.catalog_bundle_path.read_text(encoding="utf-8"))
    for edge in broken_bundle["lineage_edges"]:
        if edge.get("type") == "RUN_LAYER_TRANSFORM":
            edge["source"] = "urn:enterprise-dp:data-product:gold.finance_benefit_reconciliation"
            edge["target"] = "urn:enterprise-dp:data-product:silver.finance_benefit_transactions"
    broken_bundle_path = tmp_path / "broken-catalog.json"
    broken_bundle_path.write_text(json.dumps(broken_bundle, sort_keys=True), encoding="utf-8")

    evidence = build_pipeline_release_evidence(
        ROOT,
        release_id="local-finance-lineage-test",
        environment="local",
        use_case_id="finance-benefit-reconciliation",
        runner_id="finance.benefit_reconciliation.from_approved_bronze.v1",
        runner_input_kind="approved_bronze_jsonl",
        pipeline_manifest_path=result.pipeline.manifest_path,
        catalog_bundle_path=broken_bundle_path,
        primary_output="gold.finance_benefit_reconciliation",
        output_path=tmp_path / "broken-evidence.json",
        input_topics=["finance.benefit_settled.v1"],
        input_data_products=["bronze.events_benefit_settled"],
        output_data_products=["silver.finance_benefit_transactions", "gold.finance_benefit_reconciliation"],
        quality_profile_id="p0-finance-benefit-reconciliation",
        release_profile_id="local-medallion-release.v1",
        ingestion_manifest_path=result.ingestion.manifest_path,
        generated_at=FINANCE_EVALUATION_TIME,
        schema_registry_report_uri=result.evidence["schema_registry_report_uri"],
        access_policy_check_id=result.evidence["access_policy_check_id"],
        access_policy_report_uri=result.evidence["access_policy_report_uri"],
        access_grant_evidence_uri=result.evidence["access_grant_evidence_uri"],
        retention_evidence_uri=result.evidence["retention_evidence_uri"],
    )
    gates = gates_by_id(evidence)

    assert evidence["release_passed"] is False
    assert gates["P0-CATALOG-LINEAGE"]["passed"] is False
    assert gates["P0-CATALOG-LINEAGE"]["details"]["missing_transform_edges"] == [
        {
            "source": "bronze.events_benefit_settled",
            "target": "silver.finance_benefit_transactions",
        },
        {
            "source": "silver.finance_benefit_transactions",
            "target": "gold.finance_benefit_reconciliation",
        },
    ]


def test_run_use_case_requires_registered_implementation_pipeline(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no implementation pipelines"):
        run_use_case(
            ROOT,
            SAMPLE_INPUT,
            tmp_path,
            use_case_id="workforce-training-compliance",
            release_id="missing-implementation-test",
        )


def gates_by_id(evidence: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(gate["gate_id"]): gate
        for gate in evidence["gates"]
        if isinstance(gate, dict)
    }
