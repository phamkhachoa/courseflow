from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.catalog import hash_file, write_catalog_bundle
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.offset_ledger import write_offset_ledger_report
from enterprise_dp.pipelines import PipelineRunRequest, default_pipeline_registry
from enterprise_dp.release import build_pipeline_release_evidence
from enterprise_dp.release_profiles import hash_release_profile_registry
from enterprise_dp.snapshot_evidence import (
    build_snapshot_evidence_report,
    data_product_contract,
    write_snapshot_evidence_report,
)


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
BRONZE_SNAPSHOT_ID = "iceberg-bronze-finance-benefit-settled-0001"
SILVER_SNAPSHOT_ID = "iceberg-silver-finance-benefit-transactions-0001"
GOLD_SNAPSHOT_ID = "iceberg-gold-finance-benefit-reconciliation-0001"


def test_snapshot_evidence_binds_silver_gold_to_ledger_and_pipeline_manifest(tmp_path: Path) -> None:
    pipeline, ledger, metadata_path = build_finance_snapshot_inputs(tmp_path)

    report = build_snapshot_evidence_report(
        ROOT,
        environment="staging",
        pipeline_manifest_path=pipeline.manifest_path,
        snapshot_metadata_path=metadata_path,
        primary_output="gold.finance_benefit_reconciliation",
        source_offset_ledger_path=ledger.output_path,
        release_id="staging-finance-snapshot",
        use_case_id="finance-benefit-reconciliation",
        runner_id="finance.benefit_reconciliation.from_approved_bronze.v1",
        code_commit_sha="abc123",
        release_evidence_profile_id="local-medallion-release.v1",
        release_evidence_profile_hash=hash_release_profile_registry(ROOT),
        generated_at="2026-01-17T10:20:00Z",
    )

    assert report["artifact_type"] == "lakehouse_snapshot_evidence.v1"
    assert report["passed"] is True
    assert report["primary_snapshot"]["snapshot_id"] == GOLD_SNAPSHOT_ID
    assert report["source_offset_ledger"]["hash"] == hash_file(ledger.output_path)
    assert report["pipeline"]["manifest_hash"] == hash_file(pipeline.manifest_path)
    assert report["layers"]["silver.finance_benefit_transactions"]["contract"]["registered"] is True
    assert report["layers"]["gold.finance_benefit_reconciliation"]["snapshot"]["content_hash"] == (
        pipeline.manifest["layers"]["gold.finance_benefit_reconciliation"]["content_hash"]
    )


def test_snapshot_evidence_blocks_mismatched_gold_content_hash(tmp_path: Path) -> None:
    pipeline, ledger, metadata_path = build_finance_snapshot_inputs(tmp_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for snapshot in metadata["snapshots"]:
        if snapshot["data_product"] == "gold.finance_benefit_reconciliation":
            snapshot["content_hash"] = "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    metadata_path.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")

    report = build_snapshot_evidence_report(
        ROOT,
        environment="staging",
        pipeline_manifest_path=pipeline.manifest_path,
        snapshot_metadata_path=metadata_path,
        primary_output="gold.finance_benefit_reconciliation",
        source_offset_ledger_path=ledger.output_path,
        release_id="staging-finance-snapshot",
        use_case_id="finance-benefit-reconciliation",
        runner_id="finance.benefit_reconciliation.from_approved_bronze.v1",
        code_commit_sha="abc123",
        release_evidence_profile_id="local-medallion-release.v1",
        release_evidence_profile_hash=hash_release_profile_registry(ROOT),
        generated_at="2026-01-17T10:20:00Z",
    )

    assert report["passed"] is False
    failed_checks = {failure["check"] for failure in report["failures"]}
    assert "layer_snapshot_bindings_valid" in failed_checks


def test_snapshot_evidence_cli_and_release_gate_binding(tmp_path: Path) -> None:
    pipeline, ledger, metadata_path = build_finance_snapshot_inputs(tmp_path)
    output_path = tmp_path / "snapshot-evidence" / "evidence.json"
    result = write_snapshot_evidence_report(
        ROOT,
        output_path,
        environment="staging",
        pipeline_manifest_path=pipeline.manifest_path,
        snapshot_metadata_path=metadata_path,
        primary_output="gold.finance_benefit_reconciliation",
        source_offset_ledger_path=ledger.output_path,
        release_id="staging-finance-snapshot",
        use_case_id="finance-benefit-reconciliation",
        runner_id="finance.benefit_reconciliation.from_approved_bronze.v1",
        code_commit_sha="abc123",
        release_evidence_profile_id="local-medallion-release.v1",
        release_evidence_profile_hash=hash_release_profile_registry(ROOT),
        generated_at="2026-01-17T10:20:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "snapshot-evidence" / "cli-evidence.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "snapshot-evidence-record",
            "--root",
            str(ROOT),
            "--environment",
            "staging",
            "--pipeline-manifest",
            str(pipeline.manifest_path),
            "--snapshot-metadata",
            str(metadata_path),
            "--primary-output",
            "gold.finance_benefit_reconciliation",
            "--source-offset-ledger",
            str(ledger.output_path),
            "--release-id",
            "staging-finance-snapshot",
            "--use-case-id",
            "finance-benefit-reconciliation",
            "--runner-id",
            "finance.benefit_reconciliation.from_approved_bronze.v1",
            "--code-commit-sha",
            "abc123",
            "--release-evidence-profile-id",
            "local-medallion-release.v1",
            "--release-evidence-profile-hash",
            hash_release_profile_registry(ROOT),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-01-17T10:20:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["primary_snapshot_id"] == GOLD_SNAPSHOT_ID
    assert cli_output.is_file()

    catalog_bundle_path = tmp_path / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        ROOT,
        catalog_bundle_path,
        manifest_paths=[pipeline.manifest_path],
        generated_at="2026-01-17T10:20:00Z",
    )
    release_evidence = build_pipeline_release_evidence(
        ROOT,
        release_id="staging-finance-snapshot",
        environment="staging",
        use_case_id="finance-benefit-reconciliation",
        runner_id="finance.benefit_reconciliation.from_approved_bronze.v1",
        runner_input_kind="approved_bronze_jsonl",
        pipeline_manifest_path=pipeline.manifest_path,
        catalog_bundle_path=catalog_bundle_path,
        primary_output="gold.finance_benefit_reconciliation",
        output_path=tmp_path / "release" / "release.json",
        output_data_products=["silver.finance_benefit_transactions", "gold.finance_benefit_reconciliation"],
        snapshot_evidence_uri=output_path.as_posix(),
        snapshot_evidence_hash=hash_file(output_path),
        code_commit_sha="abc123",
        generated_at="2026-01-17T10:20:00Z",
    )
    gates = {gate["gate_id"]: gate for gate in release_evidence["gates"]}

    assert gates["P0-LAKEHOUSE-SNAPSHOT-EVIDENCE"]["passed"] is True
    assert gates["P0-LAKEHOUSE-SNAPSHOT-EVIDENCE"]["details"]["primary_snapshot_id"] == GOLD_SNAPSHOT_ID


def build_finance_snapshot_inputs(tmp_path: Path):
    ingestion = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:00:00Z",
        ingest_run_id="finance-snapshot-first",
        schema_id="registry:finance.benefit_settled.v1:1",
    )
    replay = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:05:00Z",
        ingest_run_id="finance-snapshot-replay",
        schema_id="registry:finance.benefit_settled.v1:1",
    )
    ledger = write_offset_ledger_report(
        ROOT,
        tmp_path / "ledger" / "source-offset-ledger.json",
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=ingestion.manifest_path,
        replay_manifest_path=replay.manifest_path,
        target_snapshot_id=BRONZE_SNAPSHOT_ID,
        table_metadata_uri="s3://dp-staging-lakehouse/warehouse/bronze/events_benefit_settled/metadata/00001.metadata.json",
        table_metadata_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        committed_at="2026-01-17T10:06:00Z",
        generated_at="2026-01-17T10:16:00Z",
    )
    pipeline = default_pipeline_registry().run(
        "finance.benefit_reconciliation.from_approved_bronze.v1",
        PipelineRunRequest(
            input_path=ingestion.approved_path,
            output_dir=tmp_path / "pipeline",
            options={
                "upstream_manifest_path": ingestion.manifest_path,
                "snapshot_id": "finance-pipeline-snapshot",
                "built_at": "2026-01-17T10:10:00Z",
            },
        ),
    )
    metadata_path = tmp_path / "snapshot-metadata" / "finance-snapshots.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "format": "iceberg",
                "snapshots": [
                    snapshot_metadata_entry(
                        data_product="silver.finance_benefit_transactions",
                        snapshot_id=SILVER_SNAPSHOT_ID,
                        upstream_snapshot_ids=[BRONZE_SNAPSHOT_ID],
                        layer_manifest=pipeline.manifest["layers"]["silver.finance_benefit_transactions"],
                    ),
                    snapshot_metadata_entry(
                        data_product="gold.finance_benefit_reconciliation",
                        snapshot_id=GOLD_SNAPSHOT_ID,
                        upstream_snapshot_ids=[SILVER_SNAPSHOT_ID],
                        layer_manifest=pipeline.manifest["layers"]["gold.finance_benefit_reconciliation"],
                    ),
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return pipeline, ledger, metadata_path


def snapshot_metadata_entry(
    *,
    data_product: str,
    snapshot_id: str,
    upstream_snapshot_ids: list[str],
    layer_manifest: dict[str, object],
) -> dict[str, object]:
    contract = data_product_contract(ROOT, data_product)
    layer = str(contract["layer"]).lower()
    table_name = data_product.split(".", 1)[1]
    return {
        "data_product": data_product,
        "layer": contract["layer"],
        "iceberg_table_identifier": f"staging_lakehouse.{layer}.{table_name}",
        "snapshot_id": snapshot_id,
        "parent_snapshot_id": None,
        "sequence_number": 1,
        "operation": "append",
        "committed_at": "2026-01-17T10:12:00Z",
        "metadata_uri": f"s3://dp-staging-lakehouse/warehouse/{layer}/{table_name}/metadata/00001.metadata.json",
        "metadata_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
        "manifest_list_uri": f"s3://dp-staging-lakehouse/warehouse/{layer}/{table_name}/metadata/snap-00001.avro",
        "manifest_list_hash": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
        "schema_id": f"contract:{data_product}:v{contract['contract_version']}",
        "schema_hash": contract["schema_hash"],
        "partition_spec_id": f"{data_product}.partition.v1",
        "partition_spec_hash": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
        "min_event_time": "2026-01-15T09:00:00Z",
        "max_event_time": "2026-01-15T09:15:00Z",
        "freshness_timestamp": "2026-01-17T10:12:00Z",
        "upstream_snapshot_ids": upstream_snapshot_ids,
        "row_count": layer_manifest["row_count"],
        "content_hash": layer_manifest["content_hash"],
    }
