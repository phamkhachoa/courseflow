from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.schema_registry import write_schema_registry_report
from enterprise_dp.source_bridge import run_source_bridge_preflight
from enterprise_dp.source_registry import build_source_readiness_report


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_AT = "2026-01-15T09:20:00Z"
INGESTED_AT = "2026-01-15T09:20:05Z"
SOURCE_FIXTURES = [
    (
        "lms-courseflow-course-published-outbox",
        "course.published.v1",
        ROOT / "samples" / "source-bridge" / "lms_course_published_raw.jsonl",
    ),
    (
        "lms-courseflow-enrollment-completed-outbox",
        "enrollment.completed.v1",
        ROOT / "samples" / "source-bridge" / "lms_enrollment_completed_raw.jsonl",
    ),
    (
        "lms-courseflow-gradebook-final-grade-outbox",
        "gradebook.final_grade.updated.v1",
        ROOT / "samples" / "source-bridge" / "lms_gradebook_final_grade_raw.jsonl",
    ),
    (
        "lms-courseflow-recommendation-tracking-collector",
        "recommendation.tracking.v1",
        ROOT / "samples" / "source-bridge" / "lms_recommendation_tracking_raw.jsonl",
    ),
]


@pytest.mark.parametrize(("source_id", "topic", "sample_path"), SOURCE_FIXTURES)
def test_source_bridge_normalizes_raw_lms_events_for_bronze_ingestion(
    tmp_path: Path,
    source_id: str,
    topic: str,
    sample_path: Path,
) -> None:
    bridge = run_source_bridge_preflight(
        ROOT,
        source_id,
        sample_path,
        tmp_path / "bridge",
        normalized_at=NORMALIZED_AT,
        bridge_run_id=f"{source_id}-bridge-test",
    )
    ingestion = run_bronze_ingestion(
        ROOT,
        topic,
        bridge.normalized_path,
        tmp_path / "bronze",
        ingested_at=INGESTED_AT,
        ingest_run_id=f"{source_id}-ingest-test",
    )
    approved_rows = read_jsonl(ingestion.approved_path)

    assert bridge.manifest["quality_passed"] is True
    assert bridge.manifest["source"]["canonical_topic"] == topic
    assert bridge.manifest["normalized"]["row_count"] == 1
    assert bridge.manifest["quarantine"]["row_count"] == 0
    assert ingestion.manifest["quality_passed"] is True
    assert ingestion.manifest["approved"]["new_row_count"] == 1
    assert ingestion.manifest["quarantine"]["row_count"] == 0
    assert approved_rows[0]["source_topic"] == bridge.manifest["source"]["raw_topic"]
    assert approved_rows[0]["source_offset"] is not None
    assert_no_plain_subject_keys(approved_rows[0]["raw_payload"])


def test_source_bridge_replay_is_idempotent_after_normalization(tmp_path: Path) -> None:
    source_id = "lms-courseflow-enrollment-completed-outbox"
    bridge = run_source_bridge_preflight(
        ROOT,
        source_id,
        ROOT / "samples" / "source-bridge" / "lms_enrollment_completed_raw.jsonl",
        tmp_path / "bridge",
        normalized_at=NORMALIZED_AT,
        bridge_run_id="enrollment-bridge-idempotency",
    )
    first = run_bronze_ingestion(
        ROOT,
        "enrollment.completed.v1",
        bridge.normalized_path,
        tmp_path / "bronze",
        ingested_at=INGESTED_AT,
        ingest_run_id="enrollment-first-ingest",
    )
    replay = run_bronze_ingestion(
        ROOT,
        "enrollment.completed.v1",
        bridge.normalized_path,
        tmp_path / "bronze",
        ingested_at="2026-01-15T09:25:00Z",
        ingest_run_id="enrollment-replay-ingest",
    )

    assert first.manifest["approved"]["new_row_count"] == 1
    assert replay.manifest["approved"]["new_row_count"] == 0
    assert replay.manifest["approved"]["replay_skipped_count"] == 1
    assert replay.manifest["source_positions"] == first.manifest["source_positions"]


def test_source_bridge_quarantines_records_without_source_offset(tmp_path: Path) -> None:
    raw = json.loads((ROOT / "samples" / "source-bridge" / "lms_enrollment_completed_raw.jsonl").read_text(encoding="utf-8"))
    raw.pop("sourceOffset")
    raw_path = tmp_path / "missing_offset.jsonl"
    raw_path.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")

    bridge = run_source_bridge_preflight(
        ROOT,
        "lms-courseflow-enrollment-completed-outbox",
        raw_path,
        tmp_path / "bridge",
        normalized_at=NORMALIZED_AT,
    )

    assert bridge.manifest["quality_passed"] is False
    assert bridge.manifest["normalized"]["row_count"] == 0
    assert bridge.manifest["quarantine"]["row_count"] == 1
    assert "sourceOffset" in read_jsonl(bridge.quarantine_path)[0]["errors"][0]


def test_source_readiness_requires_bridge_manifest_for_bridge_required_source(tmp_path: Path) -> None:
    bridge = run_source_bridge_preflight(
        ROOT,
        "lms-courseflow-enrollment-completed-outbox",
        ROOT / "samples" / "source-bridge" / "lms_enrollment_completed_raw.jsonl",
        tmp_path / "bridge",
        normalized_at=NORMALIZED_AT,
    )
    ingestion = run_bronze_ingestion(
        ROOT,
        "enrollment.completed.v1",
        bridge.normalized_path,
        tmp_path / "bronze",
        ingested_at=INGESTED_AT,
        ingest_run_id="enrollment-readiness-first",
    )
    replay = run_bronze_ingestion(
        ROOT,
        "enrollment.completed.v1",
        bridge.normalized_path,
        tmp_path / "bronze",
        ingested_at="2026-01-15T09:25:00Z",
        ingest_run_id="enrollment-readiness-replay",
    )
    schema = write_schema_registry_report(
        ROOT,
        tmp_path / "schema" / "schema-registry.json",
        topic_name="enrollment.completed.v1",
        generated_at="2026-01-15T09:25:05Z",
    )

    missing_bridge = build_source_readiness_report(
        ROOT,
        source_id="lms-courseflow-enrollment-completed-outbox",
        environment="local",
        ingestion_manifest_path=ingestion.manifest_path,
        replay_manifest_path=replay.manifest_path,
        schema_registry_report_path=schema.output_path,
        generated_at="2026-01-15T09:30:00Z",
    )
    with_bridge = build_source_readiness_report(
        ROOT,
        source_id="lms-courseflow-enrollment-completed-outbox",
        environment="local",
        ingestion_manifest_path=ingestion.manifest_path,
        bridge_manifest_path=bridge.manifest_path,
        replay_manifest_path=replay.manifest_path,
        schema_registry_report_path=schema.output_path,
        generated_at="2026-01-15T09:30:00Z",
    )

    assert "bridge_manifest_attached" in {failure["check"] for failure in missing_bridge["failures"]}
    assert with_bridge["passed"] is True
    assert with_bridge["readiness_state"] == "production_ready"


def test_source_bridge_cli_writes_manifest_and_normalized_jsonl(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-bridge-normalize",
            "--root",
            str(ROOT),
            "--source-id",
            "lms-courseflow-course-published-outbox",
            "--input",
            str(ROOT / "samples" / "source-bridge" / "lms_course_published_raw.jsonl"),
            "--output-dir",
            str(tmp_path / "bridge"),
            "--normalized-at",
            NORMALIZED_AT,
            "--bridge-run-id",
            "course-bridge-cli",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["source_id"] == "lms-courseflow-course-published-outbox"
    assert summary["canonical_topic"] == "course.published.v1"
    assert summary["quality_passed"] is True
    assert Path(summary["normalized_path"]).is_file()
    assert Path(summary["manifest_path"]).is_file()


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def assert_no_plain_subject_keys(value: object) -> None:
    if isinstance(value, dict):
        assert "learnerId" not in value
        assert "learner_id" not in value
        assert "sessionId" not in value
        assert "session_id" not in value
        for item in value.values():
            assert_no_plain_subject_keys(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_plain_subject_keys(item)
