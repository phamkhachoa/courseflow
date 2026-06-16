from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.ingestion import run_bronze_ingestion
from enterprise_df.offset_ledger import build_offset_ledger_report, write_offset_ledger_report


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
SNAPSHOT_ID = "iceberg-snapshot-finance-benefit-settled-0001"
METADATA_URI = "s3://df-staging-lakehouse/warehouse/bronze/events_benefit_settled/metadata/00001.metadata.json"
METADATA_HASH = "sha256:1111111111111111111111111111111111111111111111111111111111111111"


def test_offset_ledger_report_records_watermarks_hashes_and_snapshot(tmp_path: Path) -> None:
    ingestion, replay = build_ingestion_pair(tmp_path)

    report = build_offset_ledger_report(
        ROOT,
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=ingestion.manifest_path,
        replay_manifest_path=replay.manifest_path,
        target_snapshot_id=SNAPSHOT_ID,
        table_metadata_uri=METADATA_URI,
        table_metadata_hash=METADATA_HASH,
        committed_at="2026-01-17T10:06:00Z",
        generated_at="2026-01-17T10:16:00Z",
    )

    assert report["artifact_type"] == "source_offset_ledger.v1"
    assert report["passed"] is True
    assert report["target"]["table_format"] == "iceberg"
    assert report["target"]["target_snapshot_id"] == SNAPSHOT_ID
    assert report["target"]["content_hash"] == ingestion.manifest["approved"]["content_hash"]
    assert report["counts"]["committed_record_count"] == 4
    assert report["counts"]["quarantined_record_count"] == 0
    assert report["counts"]["replay_skipped_record_count"] == 4
    assert report["watermarks"] == [
        {
            "source_topic": "finance.benefit_settled.v1",
            "source_partition": 0,
            "start_position": {"offset": 1, "inclusive": True},
            "end_position": {"offset": 5, "exclusive": True},
            "min_offset": 1,
            "max_offset": 4,
            "high_watermark_offset": 5,
            "row_count": 4,
            "first_event_id": "81000000-0000-4000-8000-000000000001",
            "last_event_id": "81000000-0000-4000-8000-000000000004",
            "min_occurred_at": "2026-01-15T09:00:00Z",
            "max_occurred_at": "2026-01-15T09:15:00Z",
            "offsets": [1, 2, 3, 4],
        }
    ]
    assert len(report["record_bindings"]) == 4
    assert all(binding["bronze_row_hash_sha256"].startswith("sha256:") for binding in report["record_bindings"])


def test_offset_ledger_blocks_missing_production_snapshot_metadata(tmp_path: Path) -> None:
    ingestion, replay = build_ingestion_pair(tmp_path)

    report = build_offset_ledger_report(
        ROOT,
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=ingestion.manifest_path,
        replay_manifest_path=replay.manifest_path,
        generated_at="2026-01-17T10:16:00Z",
    )

    assert report["passed"] is False
    failed_checks = {failure["check"] for failure in report["failures"]}
    assert "target_snapshot_id_present" in failed_checks
    assert "iceberg_metadata_uri_present" in failed_checks
    assert "iceberg_metadata_hash_present" in failed_checks


def test_offset_ledger_report_and_cli(tmp_path: Path) -> None:
    ingestion, replay = build_ingestion_pair(tmp_path)
    output_path = tmp_path / "offset-ledger" / "ledger.json"
    result = write_offset_ledger_report(
        ROOT,
        output_path,
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=ingestion.manifest_path,
        replay_manifest_path=replay.manifest_path,
        target_snapshot_id=SNAPSHOT_ID,
        table_metadata_uri=METADATA_URI,
        table_metadata_hash=METADATA_HASH,
        committed_at="2026-01-17T10:06:00Z",
        generated_at="2026-01-17T10:16:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "offset-ledger" / "cli-ledger.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "offset-ledger-record",
            "--root",
            str(ROOT),
            "--source-id",
            "enterprise-commerce-benefit-settled-outbox",
            "--environment",
            "staging",
            "--ingestion-manifest",
            str(ingestion.manifest_path),
            "--replay-manifest",
            str(replay.manifest_path),
            "--target-snapshot-id",
            SNAPSHOT_ID,
            "--table-metadata-uri",
            METADATA_URI,
            "--table-metadata-hash",
            METADATA_HASH,
            "--committed-at",
            "2026-01-17T10:06:00Z",
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-01-17T10:16:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["target_snapshot_id"] == SNAPSHOT_ID
    assert cli_output.is_file()


def build_ingestion_pair(tmp_path: Path):
    ingestion = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:00:00Z",
        ingest_run_id="finance-ledger-first",
        schema_id="registry:finance.benefit_settled.v1:1",
    )
    replay = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:05:00Z",
        ingest_run_id="finance-ledger-replay",
        schema_id="registry:finance.benefit_settled.v1:1",
    )
    return ingestion, replay
