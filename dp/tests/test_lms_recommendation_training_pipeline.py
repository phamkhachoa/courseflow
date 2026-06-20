from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.pipelines.lms_recommendation import (
    run_lms_recommendation_training_from_bronze,
)


JAVA = "30000000-0000-0000-0000-000000000101"
SPRING = "30000000-0000-0000-0000-000000000102"
PYTHON = "30000000-0000-0000-0000-000000000201"
ORG = "11111111-1111-4111-8111-111111111111"
BUILT_AT = "2026-06-20T01:30:00Z"
COURSE_EVENT_IDS = {
    JAVA: "40000000-0000-4000-8000-000000000101",
    SPRING: "40000000-0000-4000-8000-000000000102",
    PYTHON: "40000000-0000-4000-8000-000000000201",
}
ENROLLMENT_EVENT_IDS = {
    "event-1": "50000000-0000-4000-8000-000000000001",
    "event-2": "50000000-0000-4000-8000-000000000002",
    "event-3": "50000000-0000-4000-8000-000000000003",
    "event-4": "50000000-0000-4000-8000-000000000004",
    "event-5": "50000000-0000-4000-8000-000000000005",
}
ENROLLMENT_IDS = {
    "event-1": "60000000-0000-4000-8000-000000000001",
    "event-2": "60000000-0000-4000-8000-000000000002",
    "event-3": "60000000-0000-4000-8000-000000000003",
    "event-4": "60000000-0000-4000-8000-000000000004",
    "event-5": "60000000-0000-4000-8000-000000000005",
}


def test_lms_recommendation_training_builds_catalog_and_training_features(tmp_path: Path) -> None:
    course_bronze = tmp_path / "bronze" / "course.jsonl"
    enrollment_bronze = tmp_path / "bronze" / "enrollment.jsonl"
    write_jsonl(
        course_bronze,
        [
            course_row(JAVA, "java-foundations", "Java Foundations"),
            course_row(SPRING, "spring-boot-foundations", "Spring Boot Foundations"),
            course_row(PYTHON, "python-foundations", "Python Foundations"),
        ],
    )
    write_jsonl(
        enrollment_bronze,
        [
            enrollment_row("event-1", "learner-a", JAVA),
            enrollment_row("event-2", "learner-a", SPRING),
            enrollment_row("event-3", "learner-b", JAVA),
            enrollment_row("event-4", "learner-b", SPRING),
            enrollment_row("event-5", "learner-c", PYTHON),
        ],
    )

    result = run_lms_recommendation_training_from_bronze(
        course_bronze,
        enrollment_bronze,
        tmp_path / "out",
        snapshot_id="lms-recsys-test",
        built_at=BUILT_AT,
    )

    catalog = read_jsonl(result.course_catalog_path)
    training = read_jsonl(result.training_path)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert {row["course_id"] for row in catalog} == {JAVA, SPRING, PYTHON}
    assert {row["source_event_id"] for row in catalog} == set(COURSE_EVENT_IDS.values())
    assert {row["title"] for row in catalog} == {
        "Java Foundations",
        "Spring Boot Foundations",
        "Python Foundations",
    }
    assert len(training) == 5
    assert {row["event_type"] for row in training} == {"ENROLLMENT"}
    assert {row["event_weight"] for row in training} == {6.0}
    assert {row["source_enrollment_id"] for row in training} == set(ENROLLMENT_IDS.values())
    assert all(row["quality_passed"] is True for row in training)
    assert manifest == result.manifest
    assert manifest["pipeline"] == "lms.recommendation_training.from_bronze.v1"
    assert manifest["primary_output"] == "gold.lms_recommendation_training_interactions"
    assert manifest["quality_passed"] is True
    assert manifest["metrics"]["published_course_count"] == 3
    assert manifest["metrics"]["training_learner_count"] == 3
    assert manifest["layers"]["gold.lms_recommendation_training_interactions"]["row_count"] == 5


def test_lms_recommendation_training_rejects_unpublished_course_enrollments(tmp_path: Path) -> None:
    course_bronze = tmp_path / "course.jsonl"
    enrollment_bronze = tmp_path / "enrollment.jsonl"
    write_jsonl(course_bronze, [course_row(JAVA, "java-foundations", "Java Foundations")])
    write_jsonl(
        enrollment_bronze,
        [
            enrollment_row("event-1", "learner-a", JAVA),
            enrollment_row("event-2", "learner-b", SPRING),
        ],
    )

    result = run_lms_recommendation_training_from_bronze(
        course_bronze,
        enrollment_bronze,
        tmp_path / "out",
        snapshot_id="lms-recsys-test",
        built_at=BUILT_AT,
    )

    training = read_jsonl(result.training_path)

    assert [row["course_id"] for row in training] == [JAVA]
    assert result.manifest["quality_passed"] is False
    assert result.manifest["metrics"]["rejected_enrollment_count"] == 1
    assert any("enrollment rows were rejected" in error for error in result.manifest["quality_errors"])


def test_lms_recommendation_training_rejects_rows_missing_contract_required_fields(tmp_path: Path) -> None:
    course_bronze = tmp_path / "course.jsonl"
    enrollment_bronze = tmp_path / "enrollment.jsonl"
    invalid_course = course_row(PYTHON, "python-foundations", "Python Foundations")
    invalid_course["raw_payload"].pop("coursePublishedAt")
    invalid_course.pop("course_published_at")
    invalid_enrollment = enrollment_row("event-3", "learner-c", JAVA)
    invalid_enrollment["raw_payload"].pop("enrollmentId")
    write_jsonl(
        course_bronze,
        [
            course_row(JAVA, "java-foundations", "Java Foundations"),
            course_row(SPRING, "spring-boot-foundations", "Spring Boot Foundations"),
            invalid_course,
        ],
    )
    write_jsonl(
        enrollment_bronze,
        [
            enrollment_row("event-1", "learner-a", JAVA),
            enrollment_row("event-2", "learner-b", SPRING),
            invalid_enrollment,
        ],
    )

    result = run_lms_recommendation_training_from_bronze(
        course_bronze,
        enrollment_bronze,
        tmp_path / "out",
        snapshot_id="lms-recsys-test",
        built_at=BUILT_AT,
    )

    catalog = read_jsonl(result.course_catalog_path)
    training = read_jsonl(result.training_path)

    assert {row["course_id"] for row in catalog} == {JAVA, SPRING}
    assert {row["source_enrollment_id"] for row in training} == {
        ENROLLMENT_IDS["event-1"],
        ENROLLMENT_IDS["event-2"],
    }
    assert result.manifest["quality_passed"] is False
    assert result.manifest["metrics"]["published_course_count"] == 2
    assert result.manifest["metrics"]["rejected_enrollment_count"] == 1
    assert any("course_published_at is required" in error for error in result.manifest["quality_errors"])
    assert any("enrollment rows were rejected" in error for error in result.manifest["quality_errors"])


def test_cli_run_pipeline_builds_lms_training_with_second_bronze(tmp_path: Path) -> None:
    course_bronze = tmp_path / "course.jsonl"
    enrollment_bronze = tmp_path / "enrollment.jsonl"
    upstream_manifest = tmp_path / "upstream.json"
    write_jsonl(
        course_bronze,
        [
            course_row(JAVA, "java-foundations", "Java Foundations"),
            course_row(SPRING, "spring-boot-foundations", "Spring Boot Foundations"),
        ],
    )
    write_jsonl(
        enrollment_bronze,
        [
            enrollment_row("event-1", "learner-a", JAVA),
            enrollment_row("event-2", "learner-a", SPRING),
            enrollment_row("event-3", "learner-b", JAVA),
            enrollment_row("event-4", "learner-b", SPRING),
        ],
    )
    upstream_manifest.write_text(json.dumps({"run_id": "bronze-test-run"}, sort_keys=True), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "run-pipeline",
            "--runner-id",
            "lms.recommendation_training.from_bronze.v1",
            "--input",
            str(course_bronze),
            "--enrollment-bronze",
            str(enrollment_bronze),
            "--output-dir",
            str(tmp_path / "out"),
            "--upstream-manifest",
            str(upstream_manifest),
            "--snapshot-id",
            "lms-recsys-cli",
            "--built-at",
            BUILT_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    manifest = json.loads(Path(output["manifest_path"]).read_text(encoding="utf-8"))
    assert output["row_count"] == 4
    assert output["quality_passed"] is True
    assert output["output_paths"]["gold.lms_recommendation_training_interactions"]
    assert manifest["inputs"]["upstream_manifests"][0]["path"] == upstream_manifest.as_posix()


def course_row(course_id: str, slug: str, title: str) -> dict[str, object]:
    return {
        "event_id": COURSE_EVENT_IDS[course_id],
        "event_type": "course.published.v1",
        "product_id": "lms-courseflow",
        "org_id": ORG,
        "course_id": course_id,
        "course_slug": slug,
        "course_published_at": "2026-01-01T00:00:00Z",
        "raw_payload": {
            "orgId": ORG,
            "courseId": course_id,
            "courseSlug": slug,
            "coursePublishedAt": "2026-01-01T00:00:00Z",
            "publishingState": "PUBLISHED",
            "catalogVisibility": "PUBLIC",
            "metadata": {"title": title, "topic": "java", "level": "beginner"},
        },
    }


def enrollment_row(event_id: str, learner_id_hash: str, course_id: str) -> dict[str, object]:
    return {
        "event_id": ENROLLMENT_EVENT_IDS[event_id],
        "event_type": "enrollment.completed.v1",
        "product_id": "lms-courseflow",
        "org_id": ORG,
        "learner_id_hash": learner_id_hash,
        "course_id": course_id,
        "completed_at": "2026-01-02T00:00:00Z",
        "raw_payload": {
            "orgId": ORG,
            "enrollmentId": ENROLLMENT_IDS[event_id],
            "learnerIdHash": learner_id_hash,
            "courseId": course_id,
            "completedAt": "2026-01-02T00:00:00Z",
            "completionSource": "LEARNER",
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
