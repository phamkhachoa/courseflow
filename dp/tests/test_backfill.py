from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_dp.backfill import (
    build_backfill_readiness_report,
    validate_backfill_request_registry,
    write_backfill_readiness_report,
)
from enterprise_dp.catalog import hash_file
from enterprise_dp.change_requests import write_change_control_evidence_report
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.offset_ledger import write_offset_ledger_report
from enterprise_dp.pipelines import PipelineRunRequest, default_pipeline_registry
from enterprise_dp.release_profiles import hash_release_profile_registry
from enterprise_dp.snapshot_evidence import data_product_contract, write_snapshot_evidence_report


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
REQUEST_ID = "backfill_finance_benefit_reconciliation_staging"
BRONZE_SNAPSHOT_ID = "iceberg-bronze-finance-backfill-0001"
SILVER_SNAPSHOT_ID = "iceberg-silver-finance-backfill-0001"
GOLD_SNAPSHOT_ID = "iceberg-gold-finance-backfill-0001"


def test_backfill_request_registry_is_valid() -> None:
    result = validate_backfill_request_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_backfill_readiness_passes_with_bounded_scope_and_evidence(tmp_path: Path) -> None:
    artifacts = build_backfill_artifacts(tmp_path)

    report = build_backfill_readiness_report(
        ROOT,
        request_id=REQUEST_ID,
        environment="staging",
        backfill_plan_path=artifacts["backfill_plan"],
        dry_run_report_path=artifacts["dry_run"],
        quality_report_path=artifacts["quality"],
        data_diff_report_path=artifacts["data_diff"],
        source_offset_ledger_path=artifacts["ledger"],
        snapshot_evidence_path=artifacts["snapshot_evidence"],
        change_control_evidence_path=artifacts["change_control"],
        generated_at="2026-01-17T10:30:00Z",
    )

    assert report["artifact_type"] == "backfill_readiness_report.v1"
    assert report["passed"] is True
    assert report["readiness_state"] == "ready"
    assert report["scope"]["primary_output"] == "gold.finance_benefit_reconciliation"
    assert report["scope"]["affected_data_products"] == [
        "silver.finance_benefit_transactions",
        "gold.finance_benefit_reconciliation",
    ]
    assert report["plan"]["concurrencyLockId"] == "backfill.finance-benefit-reconciliation.20260115"
    assert report["baseline"]["rollbackTarget"] == "iceberg-gold-finance-benefit-reconciliation-baseline"
    assert not report["failures"]


def test_backfill_readiness_passes_with_active_pointer_baseline(tmp_path: Path) -> None:
    artifacts = build_backfill_artifacts(tmp_path)
    active_state = write_active_pointer(tmp_path / "active" / "gold.finance_benefit_reconciliation.json")
    root = copy_root_with_active_pointer_baseline(tmp_path, active_state)

    report = build_backfill_readiness_report(
        root,
        request_id=REQUEST_ID,
        environment="staging",
        backfill_plan_path=artifacts["backfill_plan"],
        active_state_path=active_state,
        dry_run_report_path=artifacts["dry_run"],
        quality_report_path=artifacts["quality"],
        data_diff_report_path=artifacts["data_diff"],
        source_offset_ledger_path=artifacts["ledger"],
        snapshot_evidence_path=artifacts["snapshot_evidence"],
        change_control_evidence_path=artifacts["change_control"],
        generated_at="2026-01-17T10:30:00Z",
    )

    assert report["passed"] is True
    assert report["evidence"]["active_pointer"]["local"] is True
    assert report["evidence"]["active_pointer"]["hash"] == hash_file(active_state)


def test_backfill_readiness_blocks_active_pointer_drift(tmp_path: Path) -> None:
    artifacts = build_backfill_artifacts(tmp_path)
    active_state = write_active_pointer(tmp_path / "active" / "gold.finance_benefit_reconciliation.json")
    root = copy_root_with_active_pointer_baseline(tmp_path, active_state)
    write_active_pointer(
        active_state,
        dataset_snapshot_id="iceberg-gold-finance-benefit-reconciliation-drifted",
    )

    report = build_backfill_readiness_report(
        root,
        request_id=REQUEST_ID,
        environment="staging",
        backfill_plan_path=artifacts["backfill_plan"],
        active_state_path=active_state,
        dry_run_report_path=artifacts["dry_run"],
        quality_report_path=artifacts["quality"],
        data_diff_report_path=artifacts["data_diff"],
        source_offset_ledger_path=artifacts["ledger"],
        snapshot_evidence_path=artifacts["snapshot_evidence"],
        change_control_evidence_path=artifacts["change_control"],
        generated_at="2026-01-17T10:30:00Z",
    )
    failed_checks = {failure["check"] for failure in report["failures"]}

    assert report["passed"] is False
    assert "active_pointer_hash_matches_baseline" in failed_checks
    assert "active_pointer_matches_baseline" in failed_checks
    assert "rollback_target_matches_active_pointer" in failed_checks


def test_backfill_readiness_blocks_mismatched_snapshot_environment(tmp_path: Path) -> None:
    artifacts = build_backfill_artifacts(tmp_path, snapshot_environment="prod")

    report = build_backfill_readiness_report(
        ROOT,
        request_id=REQUEST_ID,
        environment="staging",
        backfill_plan_path=artifacts["backfill_plan"],
        dry_run_report_path=artifacts["dry_run"],
        quality_report_path=artifacts["quality"],
        data_diff_report_path=artifacts["data_diff"],
        source_offset_ledger_path=artifacts["ledger"],
        snapshot_evidence_path=artifacts["snapshot_evidence"],
        change_control_evidence_path=artifacts["change_control"],
        generated_at="2026-01-17T10:30:00Z",
    )
    failed_checks = {failure["check"] for failure in report["failures"]}

    assert report["passed"] is False
    assert "snapshot_report_matches_request" in failed_checks


def test_backfill_readiness_report_and_cli(tmp_path: Path) -> None:
    artifacts = build_backfill_artifacts(tmp_path)
    output_path = tmp_path / "backfill" / "readiness.json"
    result = write_backfill_readiness_report(
        ROOT,
        output_path,
        request_id=REQUEST_ID,
        environment="staging",
        backfill_plan_path=artifacts["backfill_plan"],
        dry_run_report_path=artifacts["dry_run"],
        quality_report_path=artifacts["quality"],
        data_diff_report_path=artifacts["data_diff"],
        source_offset_ledger_path=artifacts["ledger"],
        snapshot_evidence_path=artifacts["snapshot_evidence"],
        change_control_evidence_path=artifacts["change_control"],
        generated_at="2026-01-17T10:30:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "backfill" / "cli-readiness.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "backfill-readiness-check",
            "--root",
            str(ROOT),
            "--request-id",
            REQUEST_ID,
            "--environment",
            "staging",
            "--backfill-plan",
            str(artifacts["backfill_plan"]),
            "--dry-run-report",
            str(artifacts["dry_run"]),
            "--quality-report",
            str(artifacts["quality"]),
            "--data-diff-report",
            str(artifacts["data_diff"]),
            "--source-offset-ledger",
            str(artifacts["ledger"]),
            "--snapshot-evidence",
            str(artifacts["snapshot_evidence"]),
            "--change-control-evidence",
            str(artifacts["change_control"]),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-01-17T10:30:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["readiness_state"] == "ready"
    assert cli_output.is_file()


def build_backfill_artifacts(tmp_path: Path, *, snapshot_environment: str = "staging") -> dict[str, Path]:
    ingestion = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:00:00Z",
        ingest_run_id="finance-backfill-first",
        schema_id="registry:finance.benefit_settled.v1:1",
    )
    replay = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:05:00Z",
        ingest_run_id="finance-backfill-replay",
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
                "snapshot_id": "finance-backfill-snapshot",
                "built_at": "2026-01-17T10:10:00Z",
            },
        ),
    )
    metadata_path = tmp_path / "snapshot" / "metadata.json"
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
            ensure_ascii=True,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    snapshot = write_snapshot_evidence_report(
        ROOT,
        tmp_path / "snapshot" / "evidence.json",
        environment=snapshot_environment,
        pipeline_manifest_path=pipeline.manifest_path,
        snapshot_metadata_path=metadata_path,
        primary_output="gold.finance_benefit_reconciliation",
        source_offset_ledger_path=ledger.output_path,
        release_id="staging-finance-backfill",
        use_case_id="finance-benefit-reconciliation",
        runner_id="finance.benefit_reconciliation.from_approved_bronze.v1",
        code_commit_sha="abc123",
        release_evidence_profile_id="local-medallion-release.v1",
        release_evidence_profile_hash=hash_release_profile_registry(ROOT),
        generated_at="2026-01-17T10:20:00Z",
    )
    change_control = write_change_control_evidence_report(
        ROOT,
        tmp_path / "change-control" / "evidence.json",
        request_id=REQUEST_ID,
        environment="staging",
        generated_at="2026-01-17T10:21:00Z",
    )
    backfill_plan = write_simple_report(
        tmp_path / "backfill" / "plan.json",
        artifact_type="backfill_plan.v1",
        passed=True,
        run_id="finance-benefit-reconciliation-backfill-20260115-staging",
    )
    dry_run = write_simple_report(tmp_path / "backfill" / "dry-run.json", artifact_type="backfill_dry_run_report.v1", passed=True)
    quality = write_simple_report(tmp_path / "backfill" / "quality.json", artifact_type="quality_report.v1", passed=True)
    data_diff = write_simple_report(
        tmp_path / "backfill" / "data-diff.json",
        artifact_type="data_diff_report.v1",
        passed=True,
        expected_row_delta=4,
        actual_row_delta=4,
    )
    return {
        "backfill_plan": backfill_plan,
        "dry_run": dry_run,
        "quality": quality,
        "data_diff": data_diff,
        "ledger": ledger.output_path,
        "snapshot_evidence": snapshot.output_path,
        "change_control": change_control.output_path,
    }


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


def write_simple_report(path: Path, **payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n",
        encoding="utf-8",
    )
    return path


def write_active_pointer(
    path: Path,
    *,
    dataset_snapshot_id: str = "iceberg-gold-finance-benefit-reconciliation-baseline",
    content_hash: str = "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "release_active_pointer.v1",
        "pointer_version": 1,
        "activation_id": "baseline-finance-benefit-reconciliation",
        "environment": "staging",
        "release_id": "staging-finance-recon-baseline",
        "data_product": "gold.finance_benefit_reconciliation",
        "dataset_snapshot_id": dataset_snapshot_id,
        "content_hash": content_hash,
        "row_count": 4,
        "activated_at": "2026-01-16T00:00:00Z",
        "activated_by": "release-manager",
        "promotion_manifest_uri": "evidence://promotion/staging-finance-recon-baseline.json",
        "promotion_manifest_hash": "sha256:1212121212121212121212121212121212121212121212121212121212121212",
        "rollback_target": None,
    }
    path.write_text(
        f"{json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n",
        encoding="utf-8",
    )
    return path


def copy_root_with_active_pointer_baseline(tmp_path: Path, active_state: Path) -> Path:
    target = tmp_path / "dp-root"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".mypy_cache"),
    )
    registry_path = target / "governance" / "backfill-requests.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    request = registry["backfill_requests"][0]
    request["baseline"]["activePointerUri"] = active_state.as_posix()
    request["baseline"]["activePointerHash"] = hash_file(active_state)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    return target
