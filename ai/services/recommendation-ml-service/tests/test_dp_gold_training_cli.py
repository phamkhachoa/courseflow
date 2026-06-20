from __future__ import annotations

import json
import sys
from pathlib import Path

from courseflow_ml.training.cli import main, train_related_courses_from_dp_gold

JAVA = "30000000-0000-0000-0000-000000000101"
SPRING = "30000000-0000-0000-0000-000000000102"
PYTHON = "30000000-0000-0000-0000-000000000201"
DP_TRAINING_PRODUCT = "gold.lms_recommendation_training_interactions"


def test_train_related_courses_from_dp_gold_writes_artifact_contract(tmp_path: Path) -> None:
    gold_path = tmp_path / "gold" / "lms_recommendation_training_interactions.jsonl"
    manifest_path = tmp_path / "manifests" / "snapshot.json"
    write_jsonl(
        gold_path,
        [
            row("learner-a", JAVA),
            row("learner-a", SPRING),
            row("learner-b", JAVA),
            row("learner-b", SPRING),
            row("learner-c", PYTHON),
            {**row("learner-bad", JAVA), "quality_passed": False},
        ],
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "pipeline": "lms.recommendation_training.from_bronze.v1",
                "snapshot_id": "lms-recsys-test",
                "quality_passed": True,
                "layers": {
                    DP_TRAINING_PRODUCT: {
                        "path": "gold/lms_recommendation_training_interactions.jsonl",
                        "row_count": 6,
                        "content_hash": "sha256:manifest-training-hash",
                    }
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    artifact = train_related_courses_from_dp_gold(
        gold_path.as_posix(),
        manifest_path=manifest_path.as_posix(),
        model_version="lms-recsys-java-spring-v1",
        min_support=2,
        max_related_per_course=5,
    )

    assert artifact["artifactType"] == "courseflow.lms.related_course_recommendations"
    assert artifact["algorithm"] == "IMPLICIT_ITEM_CF_V1"
    assert artifact["sourceDataProduct"] == DP_TRAINING_PRODUCT
    assert artifact["modelVersion"] == "lms-recsys-java-spring-v1"
    assert artifact["status"] == "ACTIVE"
    assert artifact["dpSnapshot"]["snapshotIds"] == ["lms-recsys-test"]
    assert artifact["dpSnapshot"]["acceptedInteractionCount"] == 5
    assert artifact["dpSnapshot"]["rejectedRowCount"] == 1
    assert artifact["dpSnapshot"]["manifestContentHash"].startswith("sha256:")
    assert artifact["dpSnapshot"]["manifestSnapshotId"] == "lms-recsys-test"
    assert artifact["dpSnapshot"]["manifestQualityPassed"] is True
    assert (
        artifact["dpSnapshot"]["manifestLayerPath"]
        == "gold/lms_recommendation_training_interactions.jsonl"
    )
    assert artifact["dpSnapshot"]["manifestLayerContentHash"] == "sha256:manifest-training-hash"
    assert artifact["dpSnapshot"]["manifestLayerRowCount"] == 6
    assert artifact["dpSnapshot"]["eventTypes"] == ["ENROLLMENT"]
    java_spring = [
        item
        for item in artifact["recommendations"]
        if item["courseId"] == JAVA and item["relatedCourseId"] == SPRING
    ]
    assert java_spring
    assert java_spring[0]["rank"] == 1
    assert java_spring[0]["reasonCode"] == "ML_SIMILAR_LEARNER"


def test_train_related_courses_from_dp_gold_rejects_contract_drift(tmp_path: Path) -> None:
    gold_path = tmp_path / "gold" / "lms_recommendation_training_interactions.jsonl"
    write_jsonl(
        gold_path,
        [
            row("learner-a", JAVA),
            row("learner-a", SPRING),
            row("learner-b", JAVA),
            row("learner-b", SPRING),
            {**row("learner-c", JAVA), "event_type": "PURCHASE"},
            {**row("learner-d", JAVA), "event_weight": 0.0},
            {**row("learner-e", SPRING), "source_event_id": ""},
        ],
    )

    artifact = train_related_courses_from_dp_gold(
        gold_path.as_posix(),
        manifest_path=None,
        model_version="lms-recsys-contract-drift-v1",
        min_support=2,
        max_related_per_course=5,
    )

    assert artifact["status"] == "ACTIVE"
    assert artifact["dpSnapshot"]["rowCount"] == 7
    assert artifact["dpSnapshot"]["acceptedRowCount"] == 4
    assert artifact["dpSnapshot"]["acceptedInteractionCount"] == 4
    assert artifact["dpSnapshot"]["rejectedRowCount"] == 3
    assert artifact["metrics"]["eventCount"] == 4
    assert {row["reason"] for row in artifact["rejectedRowsSample"]} == {
        "invalid course_id or event_weight",
        "missing_required_fields",
        "unsupported_event_type",
    }


def test_train_related_courses_cli_keeps_legacy_command_contract(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    input_path = tmp_path / "training.json"
    input_path.write_text(
        json.dumps(
            {
                "interactions": [
                    legacy_row("learner-a", JAVA),
                    legacy_row("learner-a", SPRING),
                    legacy_row("learner-b", JAVA),
                    legacy_row("learner-b", SPRING),
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ml",
            "train-related-courses",
            "--input",
            input_path.as_posix(),
            "--min-support",
            "2",
            "--max-related-per-course",
            "5",
        ],
    )

    assert main() == 0
    output = json.loads(capsys.readouterr().out)

    assert output["algorithm"] == "IMPLICIT_ITEM_CF_V1"
    assert output["eventCount"] == 4
    assert output["recommendations"][0]["courseId"] == JAVA
    assert "artifactVersion" not in output


def test_train_related_courses_from_dp_gold_cli_writes_output_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    gold_path = tmp_path / "gold.jsonl"
    output_path = tmp_path / "artifact" / "related-courses.json"
    write_jsonl(
        gold_path,
        [
            row("learner-a", JAVA),
            row("learner-a", SPRING),
            row("learner-b", JAVA),
            row("learner-b", SPRING),
        ],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-ml",
            "train-related-courses-from-dp-gold",
            "--input",
            gold_path.as_posix(),
            "--output",
            output_path.as_posix(),
            "--model-version",
            "lms-recsys-cli-output-v1",
            "--min-support",
            "2",
        ],
    )

    assert main() == 0
    stdout_artifact = json.loads(capsys.readouterr().out)
    file_artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert file_artifact == stdout_artifact
    assert file_artifact["artifactVersion"] == 1
    assert file_artifact["status"] == "ACTIVE"


def row(learner_id_hash: str, course_id: str) -> dict[str, object]:
    return {
        "dataset_snapshot_id": "lms-recsys-test",
        "product_id": "lms-courseflow",
        "org_id": "11111111-1111-4111-8111-111111111111",
        "learner_id_hash": learner_id_hash,
        "course_id": course_id,
        "event_type": "ENROLLMENT",
        "event_weight": 6.0,
        "occurred_at": "2026-01-01T00:00:00Z",
        "source_event_id": f"{learner_id_hash}:{course_id}",
        "source_enrollment_id": f"enrollment:{learner_id_hash}:{course_id}",
        "built_at": "2026-06-20T01:30:00Z",
        "quality_passed": True,
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def legacy_row(learner_id_hash: str, course_id: str) -> dict[str, object]:
    return {
        "principalId": learner_id_hash,
        "courseId": course_id,
        "eventType": "ENROLLMENT",
        "weight": 6.0,
    }
