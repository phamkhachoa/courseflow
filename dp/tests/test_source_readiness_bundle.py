from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.source_readiness_bundle import run_source_readiness_bundle


ROOT = Path(__file__).resolve().parents[1]
BILLING_SAMPLE = ROOT / "samples" / "billing" / "billing_transaction_settled.jsonl"
LMS_ENROLLMENT_RAW = ROOT / "samples" / "source-bridge" / "lms_enrollment_completed_raw.jsonl"
GENERATED_AT = "2026-01-18T10:00:00Z"
INGESTED_AT = "2026-01-18T10:01:00Z"
REPLAYED_AT = "2026-01-18T10:05:00Z"
BILLING_SNAPSHOT_ID = "iceberg-snapshot-billing-transaction-settled-0001"
BILLING_METADATA_URI = "s3://dp-staging-lakehouse/warehouse/bronze/events_billing_transaction_settled/metadata/00001.metadata.json"
BILLING_METADATA_HASH = "sha256:2222222222222222222222222222222222222222222222222222222222222222"


def test_source_readiness_bundle_passes_for_billing_direct_canonical_staging(tmp_path: Path) -> None:
    result = billing_bundle(tmp_path)

    assert result.summary["artifact_type"] == "source_readiness_bundle.v1"
    assert result.summary["passed"] is True
    assert result.summary["readiness_state"] == "production_ready"
    assert result.bridge is None
    assert result.ingestion.manifest["approved"]["new_row_count"] == 4
    assert result.replay.manifest["approved"]["new_row_count"] == 0
    assert result.replay.manifest["approved"]["replay_skipped_count"] == 4
    assert result.readiness["passed"] is True
    assert result.readiness["source"]["status"] == "pilot"
    assert result.summary_path.is_file()
    for artifact in result.summary["artifacts"].values():
        if artifact is not None:
            assert Path(artifact).is_file()


def test_source_readiness_bundle_runs_bridge_for_lms_local_preflight(tmp_path: Path) -> None:
    result = run_source_readiness_bundle(
        ROOT,
        "lms-courseflow-enrollment-completed-outbox",
        LMS_ENROLLMENT_RAW,
        tmp_path / "bundle",
        environment="local",
        bundle_id="lms-enrollment-local",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        replayed_at=REPLAYED_AT,
    )

    assert result.summary["passed"] is True
    assert result.bridge is not None
    assert result.bridge.manifest["quality_passed"] is True
    assert result.summary["artifacts"]["bridge_manifest"] == result.bridge.manifest_path.as_posix()
    assert result.readiness["passed"] is True
    assert result.readiness["source"]["bridge"]["status"] == "local_preflight"


def test_source_readiness_bundle_blocks_staging_without_production_evidence(tmp_path: Path) -> None:
    result = run_source_readiness_bundle(
        ROOT,
        "billing-platform-billing-transaction-settled-outbox",
        BILLING_SAMPLE,
        tmp_path / "bundle",
        environment="staging",
        bundle_id="billing-missing-evidence",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        replayed_at=REPLAYED_AT,
    )

    assert result.summary["passed"] is False
    failed_checks = {failure["check"] for failure in result.readiness["failures"]}
    assert "production_schema_registry_uri_declared" in failed_checks
    assert "offset_ledger_passed" in failed_checks
    assert "change_control_evidence_attached" in failed_checks


def test_source_readiness_bundle_cli_passes_for_billing_staging(tmp_path: Path) -> None:
    output_dir = tmp_path / "cli-bundle"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-readiness-bundle",
            "--root",
            str(ROOT),
            "--source-id",
            "billing-platform-billing-transaction-settled-outbox",
            "--input",
            str(BILLING_SAMPLE),
            "--output-dir",
            str(output_dir),
            "--environment",
            "staging",
            "--bundle-id",
            "billing-cli",
            "--generated-at",
            GENERATED_AT,
            "--ingested-at",
            INGESTED_AT,
            "--replayed-at",
            REPLAYED_AT,
            "--schema-registry-uri",
            "https://schema-registry.staging.example",
            "--change-request-id",
            "onboard_billing_platform_source_readiness",
            "--target-snapshot-id",
            BILLING_SNAPSHOT_ID,
            "--table-metadata-uri",
            BILLING_METADATA_URI,
            "--table-metadata-hash",
            BILLING_METADATA_HASH,
            "--openlineage-namespace",
            "enterprise-dp://staging",
            "--openlineage-producer",
            "https://enterprise-dp.staging.example/openlineage-export",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["source_id"] == "billing-platform-billing-transaction-settled-outbox"
    assert summary["environment"] == "staging"
    assert summary["passed"] is True
    assert summary["readiness_state"] == "production_ready"
    assert Path(summary["output"]).is_file()
    assert Path(summary["readiness_report"]).is_file()


def billing_bundle(tmp_path: Path):
    return run_source_readiness_bundle(
        ROOT,
        "billing-platform-billing-transaction-settled-outbox",
        BILLING_SAMPLE,
        tmp_path / "bundle",
        environment="staging",
        bundle_id="billing-staging",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        replayed_at=REPLAYED_AT,
        schema_registry_uri="https://schema-registry.staging.example",
        change_request_id="onboard_billing_platform_source_readiness",
        target_snapshot_id=BILLING_SNAPSHOT_ID,
        table_metadata_uri=BILLING_METADATA_URI,
        table_metadata_hash=BILLING_METADATA_HASH,
        openlineage_namespace="enterprise-dp://staging",
        openlineage_producer="https://enterprise-dp.staging.example/openlineage-export",
    )
