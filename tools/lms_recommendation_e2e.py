from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

REPO_ROOT = Path(__file__).resolve().parents[1]
ORG_ID = "11111111-1111-4111-8111-111111111111"
JAVA_COURSE_ID = UUID("30000000-0000-0000-0000-000000000101")
SPRING_COURSE_ID = UUID("30000000-0000-0000-0000-000000000102")
DEFAULT_BUILT_AT = "2026-06-20T01:30:00Z"
DEFAULT_MIN_TRAINING_INTERACTIONS = 1000
DEFAULT_MIN_DISTINCT_LEARNERS = 100
DEFAULT_MIN_DISTINCT_COURSES = 24
DEFAULT_MIN_JAVA_SPRING_SUPPORT = 100


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LMS -> DP -> AI -> LMS recommendation E2E flow")
    parser.add_argument("--repo-root", default=REPO_ROOT.as_posix())
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--course-count", type=int, default=360)
    parser.add_argument("--learner-count", type=int, default=5000)
    parser.add_argument("--max-enrollments", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=20260620)
    parser.add_argument("--min-support", type=int, default=8)
    parser.add_argument("--max-related-per-course", type=int, default=12)
    parser.add_argument("--min-training-interactions", type=int, default=DEFAULT_MIN_TRAINING_INTERACTIONS)
    parser.add_argument("--min-distinct-learners", type=int, default=DEFAULT_MIN_DISTINCT_LEARNERS)
    parser.add_argument("--min-distinct-courses", type=int, default=DEFAULT_MIN_DISTINCT_COURSES)
    parser.add_argument("--min-java-spring-support", type=int, default=DEFAULT_MIN_JAVA_SPRING_SUPPORT)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    configure_repo_imports(repo_root)

    from enterprise_dp.ingestion import run_bronze_ingestion
    from enterprise_dp.pipelines.lms_recommendation import run_lms_recommendation_training_from_bronze
    from enterprise_dp.source_bridge import run_source_bridge_preflight

    dp_root = repo_root / "dp"
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    bridge_dir = output_dir / "bridge"
    bronze_dir = output_dir / "bronze"
    feature_dir = output_dir / "features"
    ai_dir = output_dir / "ai"
    lms_dir = output_dir / "lms"

    courses, enrollments = generate_lms_source_data(
        course_count=args.course_count,
        learner_count=args.learner_count,
        max_enrollments=args.max_enrollments,
        seed=args.seed,
    )
    course_raw_path = raw_dir / "lms_course_published_raw.jsonl"
    enrollment_raw_path = raw_dir / "lms_enrollment_completed_raw.jsonl"
    write_jsonl(course_raw_path, courses)
    write_jsonl(enrollment_raw_path, enrollments)

    course_bridge = run_source_bridge_preflight(
        dp_root,
        "lms-courseflow-course-published-outbox",
        course_raw_path,
        bridge_dir / "course",
        normalized_at=DEFAULT_BUILT_AT,
        bridge_run_id="lms-recsys-course-bridge",
    )
    enrollment_bridge = run_source_bridge_preflight(
        dp_root,
        "lms-courseflow-enrollment-completed-outbox",
        enrollment_raw_path,
        bridge_dir / "enrollment",
        normalized_at=DEFAULT_BUILT_AT,
        bridge_run_id="lms-recsys-enrollment-bridge",
    )
    assert_quality(course_bridge.manifest, "course source bridge")
    assert_quality(enrollment_bridge.manifest, "enrollment source bridge")

    course_bronze = run_bronze_ingestion(
        dp_root,
        "course.published.v1",
        course_bridge.normalized_path,
        bronze_dir / "course",
        ingested_at=DEFAULT_BUILT_AT,
        ingest_run_id="lms-recsys-course-bronze",
    )
    enrollment_bronze = run_bronze_ingestion(
        dp_root,
        "enrollment.completed.v1",
        enrollment_bridge.normalized_path,
        bronze_dir / "enrollment",
        ingested_at=DEFAULT_BUILT_AT,
        ingest_run_id="lms-recsys-enrollment-bronze",
    )
    assert_quality(course_bronze.manifest, "course bronze ingestion")
    assert_quality(enrollment_bronze.manifest, "enrollment bronze ingestion")

    feature_snapshot = run_lms_recommendation_training_from_bronze(
        course_bronze.approved_path,
        enrollment_bronze.approved_path,
        feature_dir,
        snapshot_id="lms-recsys-large-snapshot",
        built_at=DEFAULT_BUILT_AT,
        upstream_manifest_paths=[
            course_bridge.manifest_path,
            enrollment_bridge.manifest_path,
            course_bronze.manifest_path,
            enrollment_bronze.manifest_path,
        ],
    )
    assert_quality(feature_snapshot.manifest, "lms recommendation feature snapshot")

    artifact_path = ai_dir / "related_course_recommendations.json"
    artifact = train_related_courses_from_dp_gold(
        feature_snapshot.training_path.as_posix(),
        manifest_path=feature_snapshot.manifest_path.as_posix(),
        model_version="lms-recsys-java-spring-v1",
        min_support=args.min_support,
        max_related_per_course=args.max_related_per_course,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert_data_volume(
        feature_snapshot.manifest,
        artifact,
        min_training_interactions=args.min_training_interactions,
        min_distinct_learners=args.min_distinct_learners,
        min_distinct_courses=args.min_distinct_courses,
    )

    lms_rows = lms_related_course_rows(artifact)
    lms_path = lms_dir / "related_courses_materialization_preview.jsonl"
    write_jsonl(lms_path, lms_rows)

    java_to_spring = find_recommendation(artifact, JAVA_COURSE_ID, SPRING_COURSE_ID)
    if java_to_spring is None:
        raise AssertionError("Java course did not recommend Spring course in AI artifact")
    if int(java_to_spring["rank"]) != 1:
        raise AssertionError(f"Java -> Spring must be the top recommendation, got rank {java_to_spring['rank']}")
    if int(java_to_spring["supportCount"]) < args.min_java_spring_support:
        raise AssertionError(
            "Java -> Spring support is too small: "
            f"{java_to_spring['supportCount']} < {args.min_java_spring_support}"
        )

    lms_java_to_spring = find_materialized_recommendation(lms_rows, JAVA_COURSE_ID, SPRING_COURSE_ID)
    if lms_java_to_spring is None:
        raise AssertionError("Java -> Spring is missing from LMS materialization preview")
    if int(lms_java_to_spring["rank"]) != 1:
        raise AssertionError(
            "Java -> Spring must stay top-ranked in LMS materialization preview, "
            f"got rank {lms_java_to_spring['rank']}"
        )

    summary = {
        "passed": True,
        "courseCount": len(courses),
        "requestedLearnerCount": args.learner_count,
        "sourceLearnerCount": source_learner_count(enrollments),
        "rawEnrollmentCount": len(enrollments),
        "trainingLearnerCount": feature_snapshot.manifest["metrics"]["training_learner_count"],
        "trainingCourseCount": feature_snapshot.manifest["metrics"]["training_course_count"],
        "trainingInteractionCount": feature_snapshot.manifest["metrics"]["training_interaction_count"],
        "artifactRecommendationCount": len(artifact["recommendations"]),
        "javaCourseId": str(JAVA_COURSE_ID),
        "springCourseId": str(SPRING_COURSE_ID),
        "javaToSpring": java_to_spring,
        "lmsPreviewJavaToSpring": lms_java_to_spring,
        "thresholds": {
            "minTrainingInteractions": args.min_training_interactions,
            "minDistinctLearners": args.min_distinct_learners,
            "minDistinctCourses": args.min_distinct_courses,
            "minJavaSpringSupport": args.min_java_spring_support,
        },
        "paths": {
            "courseRaw": course_raw_path.as_posix(),
            "enrollmentRaw": enrollment_raw_path.as_posix(),
            "dpFeatureManifest": feature_snapshot.manifest_path.as_posix(),
            "dpTrainingGold": feature_snapshot.training_path.as_posix(),
            "aiArtifact": artifact_path.as_posix(),
            "lmsMaterializationPreview": lms_path.as_posix(),
        },
    }
    summary_path = output_dir / "lms_recommendation_e2e_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def configure_repo_imports(repo_root: Path) -> None:
    import_roots = [
        ("Data Platform source", repo_root / "dp" / "src"),
        ("Recommendation ML service source", repo_root / "ai" / "services" / "recommendation-ml-service" / "src"),
    ]
    for label, path in import_roots:
        prepend_import_path(path, label)


def prepend_import_path(path: Path, label: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"{label} import path does not exist: {path}")
    path_text = path.as_posix()
    if path_text in sys.path:
        sys.path.remove(path_text)
    sys.path.insert(0, path_text)


def generate_lms_source_data(
    *,
    course_count: int,
    learner_count: int,
    max_enrollments: int,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    safe_course_count = max(24, course_count)
    safe_learner_count = max(100, learner_count)
    rng = random.Random(seed)
    started_at = datetime(2026, 1, 1, 9, tzinfo=UTC)
    courses = course_records(safe_course_count, started_at)
    course_ids = [UUID(row["courseId"]) for row in courses]
    tracks = course_tracks(course_ids)
    enrollments: list[dict[str, Any]] = []
    offset = 0
    for learner_index in range(safe_learner_count):
        learner_id = f"learner-{learner_index:06d}"
        selected = learner_courses(learner_index, tracks, course_ids, rng)
        for course_order, course_id in enumerate(selected):
            if len(enrollments) >= max_enrollments:
                break
            completed_at = started_at + timedelta(days=learner_index % 90, hours=course_order)
            offset += 1
            enrollments.append(
                {
                    "eventId": str(uuid5(NAMESPACE_URL, f"enrollment:{learner_id}:{course_id}:{course_order}")),
                    "eventType": "enrollment.completed",
                    "orgId": ORG_ID,
                    "enrollmentId": str(uuid5(NAMESPACE_URL, f"enrollment-id:{learner_id}:{course_id}")),
                    "learnerId": learner_id,
                    "courseId": str(course_id),
                    "completedAt": timestamp(completed_at),
                    "completionSource": "LEARNER",
                    "sourceTopic": "enrollment.completed",
                    "sourcePartition": learner_index % 12,
                    "sourceOffset": offset,
                    "publishedAt": timestamp(completed_at + timedelta(seconds=2)),
                    "correlationId": f"lms-recsys-enrollment-{offset}",
                    "metadata": {
                        "completionMode": "self_paced",
                        "syntheticScenario": "lms_recommendation_e2e",
                    },
                }
            )
        if len(enrollments) >= max_enrollments:
            break
    return courses, enrollments


def course_records(course_count: int, started_at: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fixed = [
        (JAVA_COURSE_ID, "java-foundations", "Java Foundations", "java", "beginner"),
        (SPRING_COURSE_ID, "spring-boot-foundations", "Spring Boot Foundations", "java", "intermediate"),
    ]
    topics = ["java", "python", "data", "cloud", "security", "frontend", "devops", "architecture"]
    for index in range(course_count):
        if index < len(fixed):
            course_id, slug, title, topic, level = fixed[index]
        else:
            topic = topics[index % len(topics)]
            level = ["beginner", "intermediate", "advanced"][index % 3]
            course_id = uuid5(NAMESPACE_URL, f"courseflow-lms-course:{index}:{topic}:{level}")
            slug = f"{topic}-{level}-{index:03d}"
            title = f"{topic.title()} {level.title()} {index:03d}"
        published_at = started_at - timedelta(days=30) + timedelta(minutes=index)
        rows.append(
            {
                "eventId": str(uuid5(NAMESPACE_URL, f"course-published:{course_id}")),
                "eventType": "course.published",
                "orgId": ORG_ID,
                "courseId": str(course_id),
                "courseSlug": slug,
                "coursePublishedAt": timestamp(published_at),
                "publishingState": "PUBLISHED",
                "catalogVisibility": "PUBLIC",
                "sourceTopic": "course.published",
                "sourcePartition": index % 6,
                "sourceOffset": index + 1,
                "publishedAt": timestamp(published_at + timedelta(seconds=2)),
                "correlationId": f"lms-recsys-course-{index + 1}",
                "metadata": {
                    "title": title,
                    "topic": topic,
                    "level": level,
                    "syntheticScenario": "lms_recommendation_e2e",
                },
            }
        )
    return rows


def course_tracks(course_ids: list[UUID]) -> dict[str, list[UUID]]:
    fixed_course_ids = {JAVA_COURSE_ID, SPRING_COURSE_ID}
    by_topic = {
        "java": [
            course_id
            for index, course_id in enumerate(course_ids)
            if course_id in fixed_course_ids or (index >= 2 and index % 8 == 0)
        ],
        "python": [course_id for index, course_id in enumerate(course_ids) if index >= 2 and index % 8 == 1],
        "data": [course_id for index, course_id in enumerate(course_ids) if index >= 2 and index % 8 == 2],
        "cloud": [course_id for index, course_id in enumerate(course_ids) if index >= 2 and index % 8 == 3],
    }
    java_extras = [course_id for course_id in by_topic["java"] if course_id not in fixed_course_ids]
    by_topic["java"] = [JAVA_COURSE_ID, SPRING_COURSE_ID, *java_extras[:24]]
    return by_topic


def learner_courses(
    learner_index: int,
    tracks: dict[str, list[UUID]],
    course_ids: list[UUID],
    rng: random.Random,
) -> list[UUID]:
    bucket = learner_index % 100
    if bucket < 62:
        base = [JAVA_COURSE_ID, SPRING_COURSE_ID]
        pool = tracks["java"]
    elif bucket < 78:
        base = tracks["python"][:2]
        pool = tracks["python"]
    elif bucket < 90:
        base = tracks["data"][:2]
        pool = tracks["data"]
    else:
        base = tracks["cloud"][:2]
        pool = tracks["cloud"]
    extra_count = 2 + (learner_index % 4)
    candidates = [course_id for course_id in pool if course_id not in base]
    extras = rng.sample(candidates, k=min(extra_count, len(candidates))) if candidates else []
    electives = rng.sample(course_ids, k=2)
    unique: list[UUID] = []
    for course_id in [*base, *extras, *electives]:
        if course_id not in unique:
            unique.append(course_id)
    return unique


def lms_related_course_rows(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    generated_at = artifact["generatedAt"]
    model_version = artifact["modelVersion"]
    rows = []
    for row in artifact["recommendations"]:
        rows.append(
            {
                "course_id": row["courseId"],
                "related_course_id": row["relatedCourseId"],
                "score": row["score"],
                "source": "ML",
                "rank": row["rank"],
                "similarity": row["similarity"],
                "support_count": row["supportCount"],
                "reason": ml_artifact_reason(row, artifact),
                "reason_code": row["reasonCode"],
                "model_version": model_version,
                "generated_at": generated_at,
                "artifact_type": artifact["artifactType"],
                "algorithm": artifact["algorithm"],
            }
        )
    return rows


def find_recommendation(
    artifact: dict[str, Any],
    course_id: UUID,
    related_course_id: UUID,
) -> dict[str, Any] | None:
    for row in artifact["recommendations"]:
        if row["courseId"] == str(course_id) and row["relatedCourseId"] == str(related_course_id):
            return row
    return None


def find_materialized_recommendation(
    rows: list[dict[str, Any]],
    course_id: UUID,
    related_course_id: UUID,
) -> dict[str, Any] | None:
    for row in rows:
        if row["course_id"] == str(course_id) and row["related_course_id"] == str(related_course_id):
            return row
    return None


def assert_data_volume(
    feature_manifest: dict[str, Any],
    artifact: dict[str, Any],
    *,
    min_training_interactions: int,
    min_distinct_learners: int,
    min_distinct_courses: int,
) -> None:
    feature_metrics = feature_manifest.get("metrics", {})
    artifact_metrics = artifact.get("metrics", {})
    errors: list[str] = []
    training_interactions = int(feature_metrics.get("training_interaction_count", 0))
    training_learners = int(feature_metrics.get("training_learner_count", 0))
    training_courses = int(feature_metrics.get("training_course_count", 0))
    accepted_interactions = int(artifact.get("dpSnapshot", {}).get("acceptedInteractionCount", 0))
    if training_interactions < min_training_interactions:
        errors.append(f"training interactions {training_interactions} < {min_training_interactions}")
    if training_learners < min_distinct_learners:
        errors.append(f"training learners {training_learners} < {min_distinct_learners}")
    if training_courses < min_distinct_courses:
        errors.append(f"training courses {training_courses} < {min_distinct_courses}")
    if accepted_interactions != training_interactions:
        errors.append(
            f"AI accepted interactions {accepted_interactions} != DP training interactions {training_interactions}"
        )
    if int(artifact_metrics.get("eventCount", 0)) != accepted_interactions:
        errors.append("AI artifact eventCount does not match acceptedInteractionCount")
    if errors:
        raise AssertionError("LMS recommendation dataset is not large/consistent enough: " + "; ".join(errors))


def train_related_courses_from_dp_gold(
    input_path: str,
    *,
    manifest_path: str | None,
    model_version: str,
    min_support: int,
    max_related_per_course: int,
) -> dict[str, Any]:
    from courseflow_ml.training.implicit_cf import ImplicitCfConfig, ImplicitItemCfTrainer

    source_path = Path(input_path)
    rows = read_jsonl(source_path)
    interactions, rejected_rows, snapshot_ids = dp_gold_training_interactions(rows)
    result = ImplicitItemCfTrainer(
        ImplicitCfConfig(
            min_support=min_support,
            max_related_per_course=max_related_per_course,
        )
    ).train(interactions)
    manifest_hash = sha256_file(Path(manifest_path)) if manifest_path else None
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "artifactVersion": 1,
        "artifactType": "courseflow.lms.related_course_recommendations",
        "algorithm": "IMPLICIT_ITEM_CF_V1",
        "status": "ACTIVE" if result.recommendations else "INSUFFICIENT_DATA",
        "modelVersion": model_version,
        "generatedAt": generated_at,
        "dpSnapshot": {
            "snapshotIds": sorted(snapshot_ids),
            "trainingPath": source_path.as_posix(),
            "trainingContentHash": sha256_file(source_path),
            "manifestPath": manifest_path,
            "manifestContentHash": manifest_hash,
            "rowCount": len(rows),
            "acceptedInteractionCount": len(interactions),
            "rejectedRowCount": len(rejected_rows),
        },
        "metrics": {
            "eventCount": result.event_count,
            "principalCount": result.principal_count,
            "courseCount": result.course_count,
            "pairCount": result.pair_count,
            "qualityScore": result.quality_score,
            "minSupport": min_support,
            "maxRelatedPerCourse": max_related_per_course,
        },
        "recommendations": [
            {
                "courseId": str(row.course_id),
                "relatedCourseId": str(row.related_course_id),
                "rank": row.rank,
                "score": row.score,
                "similarity": row.similarity,
                "supportCount": row.support_count,
                "reasonCode": row.reason_code,
                "modelVersion": model_version,
            }
            for row in result.recommendations
        ],
        "rejectedRowsSample": rejected_rows[:20],
    }


def dp_gold_training_interactions(rows: list[dict[str, Any]]) -> tuple[list[Any], list[dict[str, Any]], set[str]]:
    from courseflow_ml.domain.recommendation import TrainingInteraction

    interactions: list[Any] = []
    rejected_rows: list[dict[str, Any]] = []
    snapshot_ids: set[str] = set()
    for index, row in enumerate(rows):
        if row.get("dataset_snapshot_id"):
            snapshot_ids.add(str(row["dataset_snapshot_id"]))
        if row.get("quality_passed") is not True:
            rejected_rows.append({"rowIndex": index, "reason": "quality_passed_false"})
            continue
        principal_id = str(row.get("learner_id_hash") or "").strip()
        event_type = str(row.get("event_type") or "").strip().upper()
        course_id = row.get("course_id")
        if not principal_id or not event_type or not course_id:
            rejected_rows.append({"rowIndex": index, "reason": "missing principal_id, course_id or event_type"})
            continue
        try:
            parsed_course_id = UUID(str(course_id))
            weight = float(row["event_weight"]) if row.get("event_weight") is not None else None
        except (TypeError, ValueError):
            rejected_rows.append({"rowIndex": index, "reason": "invalid course_id or event_weight"})
            continue
        interactions.append(
            TrainingInteraction(
                principal_id=principal_id,
                course_id=parsed_course_id,
                event_type=event_type,
                weight=weight,
            )
        )
    return interactions, rejected_rows, snapshot_ids


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL record") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: JSONL record must be an object")
            records.append(record)
    return records


def source_learner_count(enrollments: list[dict[str, Any]]) -> int:
    return len({str(row["learnerId"]) for row in enrollments if row.get("learnerId")})


def ml_artifact_reason(row: dict[str, Any], artifact: dict[str, Any]) -> str:
    reason = ml_reason(str(row.get("reasonCode") or ""), int(row.get("supportCount") or 0))
    snapshot_ids = artifact.get("dpSnapshot", {}).get("snapshotIds", [])
    if not snapshot_ids:
        return reason
    combined = f"{reason} DP snapshot: {snapshot_ids[0]}."
    return combined[:160]


def ml_reason(reason_code: str, support_count: int) -> str:
    if reason_code.upper() == "ML_CO_ENROLLMENT":
        return "ML model found strong co-enrollment patterns across similar learners."
    if support_count > 0:
        return "ML model found overlapping learner behavior for this course pair."
    return "ML model ranked this course as a related next step."


def assert_quality(manifest: dict[str, Any], label: str) -> None:
    if manifest.get("quality_passed") is not True:
        raise AssertionError(f"{label} failed quality checks: {manifest}")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
