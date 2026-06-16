from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.ingestion import run_bronze_ingestion


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
INGESTED_AT = "2026-01-15T11:00:05Z"


def test_bronze_ingestion_writes_approved_rows_manifest_and_hashes(tmp_path: Path) -> None:
    result = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path,
        ingested_at=INGESTED_AT,
        ingest_run_id="test-ingest-run",
        schema_id="local-schema-001",
    )

    approved = read_jsonl(result.approved_path)
    quarantine = read_jsonl(result.quarantine_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert len(approved) == 3
    assert quarantine == []
    assert {row["product_id"] for row in approved} == {"lms-courseflow"}
    assert {row["domain_id"] for row in approved} == {"recommendation"}
    assert [row["source_offset"] for row in approved] == [100, 101, 102]
    assert approved[0]["schema_subject"] == "recommendation.tracking.v1-value"
    assert approved[0]["schema_id"] == "local-schema-001"
    assert approved[0]["source_record_hash_sha256"].startswith("sha256:")
    assert approved[0]["payload_hash_sha256"].startswith("sha256:")
    assert approved[0]["ingest_run_id"] == "test-ingest-run"
    assert approved[0]["event_date"] == "2026-01-15"
    assert approved[0]["ingest_date"] == "2026-01-15"

    assert manifest == result.manifest
    assert manifest["pipeline"] == "bronze_ingestion.local_jsonl.v1"
    assert manifest["product_id"] == "lms-courseflow"
    assert manifest["topic"] == "recommendation.tracking.v1"
    assert manifest["bronze_target"] == "bronze.events_recommendation_tracking"
    assert manifest["approved"]["row_count"] == 3
    assert manifest["approved"]["new_row_count"] == 3
    assert manifest["approved"]["replay_skipped_count"] == 0
    assert manifest["quarantine"]["row_count"] == 0
    assert manifest["quality_passed"] is True
    assert manifest["source_positions"] == [
        {
            "source_topic": "recommendation.tracking.v1",
            "source_partition": 0,
            "min_offset": 100,
            "max_offset": 102,
            "row_count": 3,
        }
    ]


def test_bronze_ingestion_quarantines_invalid_schema_and_pii(tmp_path: Path) -> None:
    first, second, *_ = read_jsonl(SAMPLE_INPUT)
    first.pop("productId")
    second["payload"]["metadata"]["student_id"] = "raw-student-id"
    second["headers"] = {"Authorization": "secret-token"}
    source = tmp_path / "invalid.jsonl"
    write_jsonl(source, [first, second])

    result = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        source,
        tmp_path / "out",
        ingested_at=INGESTED_AT,
    )

    approved = read_jsonl(result.approved_path)
    quarantine = read_jsonl(result.quarantine_path)

    assert approved == []
    assert len(quarantine) == 2
    assert "SCHEMA_INVALID" in quarantine[0]["reason_codes"]
    assert "PRODUCT_MISMATCH" in quarantine[0]["reason_codes"]
    assert "PII_POLICY_VIOLATION" in quarantine[1]["reason_codes"]
    assert any("headers contain" in error for error in quarantine[1]["errors"])
    assert result.manifest["quality_passed"] is False
    assert result.manifest["quarantine"]["reason_counts"]["PII_POLICY_VIOLATION"] == 1


def test_bronze_ingestion_quarantines_duplicate_source_position(tmp_path: Path) -> None:
    first, second, *_ = read_jsonl(SAMPLE_INPUT)
    second["sourceOffset"] = first["sourceOffset"]
    source = tmp_path / "duplicate.jsonl"
    write_jsonl(source, [first, second])

    result = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        source,
        tmp_path / "out",
        ingested_at=INGESTED_AT,
    )

    approved = read_jsonl(result.approved_path)
    quarantine = read_jsonl(result.quarantine_path)

    assert len(approved) == 1
    assert len(quarantine) == 1
    assert "DUPLICATE_SOURCE_POSITION" in quarantine[0]["reason_codes"]
    assert result.manifest["approved"]["row_count"] == 1
    assert result.manifest["quarantine"]["row_count"] == 1


def test_bronze_ingestion_quarantines_missing_source_position(tmp_path: Path) -> None:
    event = read_jsonl(SAMPLE_INPUT)[0]
    event.pop("sourceTopic")
    event.pop("sourcePartition")
    event.pop("sourceOffset")
    source = tmp_path / "missing-source-position.jsonl"
    write_jsonl(source, [event])

    result = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        source,
        tmp_path / "out",
        ingested_at=INGESTED_AT,
    )

    assert read_jsonl(result.approved_path) == []
    quarantine = read_jsonl(result.quarantine_path)
    assert "SOURCE_POSITION_MISSING" in quarantine[0]["reason_codes"]


def test_bronze_ingestion_replay_is_idempotent_for_same_output_dir(tmp_path: Path) -> None:
    first = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path,
        ingested_at=INGESTED_AT,
        ingest_run_id="first-run",
    )
    second = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path,
        ingested_at=INGESTED_AT,
        ingest_run_id="second-run",
    )

    assert len(read_jsonl(first.approved_path)) == 3
    assert len(read_jsonl(second.approved_path)) == 3
    assert second.manifest["approved"]["row_count"] == 3
    assert second.manifest["approved"]["new_row_count"] == 0
    assert second.manifest["approved"]["replay_skipped_count"] == 3
    assert second.manifest["quarantine"]["row_count"] == 0


def test_bronze_ingestion_quarantines_replay_hash_mismatch(tmp_path: Path) -> None:
    run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path,
        ingested_at=INGESTED_AT,
        ingest_run_id="first-run",
    )
    event = read_jsonl(SAMPLE_INPUT)[0]
    event["payload"]["position"] = 99
    source = tmp_path / "hash-mismatch.jsonl"
    write_jsonl(source, [event])

    result = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        source,
        tmp_path,
        ingested_at=INGESTED_AT,
        ingest_run_id="second-run",
    )

    quarantine = read_jsonl(result.quarantine_path)
    assert len(read_jsonl(result.approved_path)) == 3
    assert "HASH_MISMATCH" in quarantine[0]["reason_codes"]


def test_bronze_ingestion_requires_non_null_identity_hash(tmp_path: Path) -> None:
    event = read_jsonl(SAMPLE_INPUT)[0]
    event["payload"]["learnerIdHash"] = None
    event["payload"]["sessionIdHash"] = None
    source = tmp_path / "missing-identity-hash.jsonl"
    write_jsonl(source, [event])

    result = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        source,
        tmp_path / "out",
        ingested_at=INGESTED_AT,
    )

    assert read_jsonl(result.approved_path) == []
    quarantine = read_jsonl(result.quarantine_path)
    assert "SCHEMA_INVALID" in quarantine[0]["reason_codes"]


def test_bronze_ingestion_enforces_required_subject_key_policy(tmp_path: Path) -> None:
    event = read_jsonl(SAMPLE_INPUT)[0]
    event["payload"]["learnerIdHash"] = None
    event["payload"]["sessionIdHash"] = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    source = tmp_path / "missing-required-subject-key.jsonl"
    write_jsonl(source, [event])

    result = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        source,
        tmp_path / "out",
        ingested_at=INGESTED_AT,
    )

    assert read_jsonl(result.approved_path) == []
    quarantine = read_jsonl(result.quarantine_path)
    assert "SUBJECT_KEY_MISSING" in quarantine[0]["reason_codes"]


def test_cli_runs_bronze_ingestion(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "ingest-bronze",
            "--root",
            str(ROOT),
            "--topic",
            "recommendation.tracking.v1",
            "--input",
            str(SAMPLE_INPUT),
            "--output-dir",
            str(tmp_path),
            "--ingested-at",
            INGESTED_AT,
            "--ingest-run-id",
            "cli-test-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["approved_rows"] == 3
    assert output["quarantine_rows"] == 0
    assert output["quality_passed"] is True
    assert Path(output["manifest_path"]).is_file()


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    content = "".join(
        f"{json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n"
        for record in records
    )
    path.write_text(content, encoding="utf-8")
