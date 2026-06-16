from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.ingestion import run_bronze_ingestion
from enterprise_df.pipelines import run_recommendation_pipeline, run_recommendation_pipeline_from_bronze


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
BUILT_AT = "2026-01-15T11:00:00Z"
INGESTED_AT = "2026-01-15T11:00:05Z"


def test_recommendation_pipeline_builds_medallion_outputs_and_manifest(tmp_path: Path) -> None:
    result = run_recommendation_pipeline(
        SAMPLE_INPUT,
        tmp_path,
        snapshot_id="test-recsys-snapshot",
        built_at=BUILT_AT,
        ingested_at=INGESTED_AT,
    )

    bronze = read_jsonl(result.bronze_path)
    silver = read_jsonl(result.silver_path)
    gold = read_jsonl(result.gold_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert [row["event_type"] for row in bronze] == ["IMPRESSION", "CLICK", "ENROLLMENT"]
    assert {row["product_id"] for row in bronze} == {"lms-courseflow"}
    assert bronze[0]["raw_payload"]["eventType"] == "IMPRESSION"
    assert bronze[0]["ingested_at"] == INGESTED_AT

    assert [row["activity_type"] for row in silver] == [
        "RECOMMENDATION_IMPRESSION",
        "RECOMMENDATION_CLICK",
        "RECOMMENDATION_ENROLLMENT",
    ]
    assert {row["product_id"] for row in silver} == {"lms-courseflow"}
    assert all(row["activity_id"] for row in silver)

    assert [row["event_weight"] for row in gold] == [0.1, 1.0, 3.0]
    assert {row["product_id"] for row in gold} == {"lms-courseflow"}
    assert {row["dataset_snapshot_id"] for row in gold} == {"test-recsys-snapshot"}
    assert all(row["built_at"] == BUILT_AT for row in gold)
    assert all(row["quality_passed"] is True for row in gold)

    assert manifest == result.manifest
    assert manifest["pipeline"] == "recommendation.local_jsonl.v1"
    assert manifest["product_id"] == "lms-courseflow"
    assert manifest["snapshot_id"] == "test-recsys-snapshot"
    assert manifest["row_count"] == 3
    assert manifest["content_hash"] == sha256_text(result.gold_path)
    assert manifest["quality_passed"] is True

    for layer_name in (
        "bronze.events_recommendation_tracking",
        "silver.learner_activity",
        "gold.recsys_interactions",
    ):
        layer = manifest["layers"][layer_name]
        assert layer["row_count"] == 3
        assert layer["content_hash"].startswith("sha256:")
        assert layer["quality_passed"] is True
        assert layer["quality_errors"] == []


def test_manifest_records_bronze_quality_failure_without_dropping_outputs(tmp_path: Path) -> None:
    first, second, *_ = read_jsonl(SAMPLE_INPUT)
    first["sourceOffset"] = 10
    second["sourceOffset"] = 10
    duplicate_input = tmp_path / "duplicate-source-position.jsonl"
    write_jsonl(duplicate_input, [first, second])

    result = run_recommendation_pipeline(
        duplicate_input,
        tmp_path / "out",
        snapshot_id="duplicate-source-position",
        built_at=BUILT_AT,
        ingested_at=INGESTED_AT,
    )

    manifest = result.manifest
    bronze_layer = manifest["layers"]["bronze.events_recommendation_tracking"]

    assert len(read_jsonl(result.bronze_path)) == 2
    assert len(read_jsonl(result.gold_path)) == 2
    assert bronze_layer["quality_passed"] is False
    assert any("source_position_unique" in error for error in bronze_layer["quality_errors"])
    assert manifest["quality_passed"] is False


def test_gold_quality_gate_rejects_self_recommendations(tmp_path: Path) -> None:
    event = read_jsonl(SAMPLE_INPUT)[0]
    course_id = event["payload"]["courseId"]
    event["payload"]["relatedCourseId"] = course_id
    self_recommendation_input = tmp_path / "self-recommendation.jsonl"
    write_jsonl(self_recommendation_input, [event])

    result = run_recommendation_pipeline(
        self_recommendation_input,
        tmp_path / "out",
        snapshot_id="self-recommendation",
        built_at=BUILT_AT,
        ingested_at=INGESTED_AT,
    )

    gold = read_jsonl(result.gold_path)
    gold_layer = result.manifest["layers"]["gold.recsys_interactions"]

    assert gold[0]["course_id"] == gold[0]["related_course_id"]
    assert gold[0]["quality_passed"] is False
    assert gold_layer["quality_passed"] is False
    assert any("no_self_recommendation" in error for error in gold_layer["quality_errors"])
    assert result.manifest["quality_passed"] is False


def test_recommendation_pipeline_builds_from_approved_bronze_with_upstream_evidence(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="approved-bronze-run",
        schema_id="local-schema-001",
    )
    result = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        tmp_path / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="from-approved-bronze",
        built_at=BUILT_AT,
    )

    silver = read_jsonl(result.silver_path)
    gold = read_jsonl(result.gold_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert [row["activity_type"] for row in silver] == [
        "RECOMMENDATION_IMPRESSION",
        "RECOMMENDATION_CLICK",
        "RECOMMENDATION_ENROLLMENT",
    ]
    assert [row["event_weight"] for row in gold] == [0.1, 1.0, 3.0]
    assert manifest == result.manifest
    assert manifest["pipeline"] == "recommendation.from_approved_bronze.v1"
    assert manifest["input"]["upstream_manifest_hash"] == sha256_text(ingestion.manifest_path)
    assert manifest["source_positions"] == ingestion.manifest["source_positions"]
    assert manifest["upstream_quality_passed"] is True
    assert manifest["quality_passed"] is True
    assert manifest["layers"]["bronze.events_recommendation_tracking"]["path"] == ingestion.approved_path.as_posix()
    assert manifest["lineage_edges"] == [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "bronze.events_recommendation_tracking",
            "target": "silver.learner_activity",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "silver.learner_activity",
            "target": "gold.recsys_interactions",
        },
    ]


def test_recommendation_pipeline_marks_handoff_unpublishable_when_upstream_had_quarantine(tmp_path: Path) -> None:
    good, bad, *_ = read_jsonl(SAMPLE_INPUT)
    bad["headers"] = {"Authorization": "secret-token"}
    source = tmp_path / "mixed.jsonl"
    write_jsonl(source, [good, bad])
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        source,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="mixed-bronze-run",
    )

    result = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        tmp_path / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="mixed-upstream",
        built_at=BUILT_AT,
    )

    assert ingestion.manifest["quality_passed"] is False
    assert result.manifest["upstream_quality_passed"] is False
    assert result.manifest["quality_passed"] is False
    assert result.manifest["row_count"] == 1


def test_cli_builds_recommendation_from_approved_bronze(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="cli-upstream-run",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "build-recommendation",
            "--bronze",
            str(ingestion.approved_path),
            "--output-dir",
            str(tmp_path / "medallion"),
            "--upstream-manifest",
            str(ingestion.manifest_path),
            "--snapshot-id",
            "cli-recsys-snapshot",
            "--built-at",
            BUILT_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["snapshot_id"] == "cli-recsys-snapshot"
    assert output["row_count"] == 3
    assert output["quality_passed"] is True
    assert output["upstream_quality_passed"] is True
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


def sha256_text(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
