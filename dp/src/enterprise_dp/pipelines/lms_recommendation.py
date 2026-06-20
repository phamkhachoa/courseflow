from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.pipelines.base import PipelineRunRequest, PipelineSpec


PIPELINE_NAME = "lms.recommendation_training.from_bronze.v1"
PRODUCT_ID = "lms-courseflow"
DOMAIN_ID = "recommendation"
COURSE_CATALOG_PRODUCT = "gold.lms_recommendation_course_catalog"
TRAINING_PRODUCT = "gold.lms_recommendation_training_interactions"
ENROLLMENT_WEIGHT = 6.0


@dataclass(frozen=True)
class LmsRecommendationTrainingResult:
    snapshot_id: str
    course_catalog_path: Path
    training_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class LmsRecommendationTrainingRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_NAME,
        name="LMS recommendation training features from Bronze",
        product=PRODUCT_ID,
        domain=DOMAIN_ID,
        use_cases=("ml-feature-governance",),
        input_kind="approved_bronze_jsonl",
        input_topics=("course.published.v1", "enrollment.completed.v1"),
        input_data_products=(
            "bronze.events_course_published",
            "bronze.events_enrollment_completed",
        ),
        output_data_products=(COURSE_CATALOG_PRODUCT, TRAINING_PRODUCT),
        primary_output=TRAINING_PRODUCT,
        description=(
            "Build a publishable LMS course catalog and learner-course implicit "
            "interaction features for AI related-course model training."
        ),
        evidence_capabilities=("schema_registry", "catalog_lineage", "release_gates"),
        required_options=("enrollment_bronze_path",),
        optional_options=("snapshot_id", "built_at", "upstream_manifest_paths"),
    )

    def run(self, request: PipelineRunRequest) -> LmsRecommendationTrainingResult:
        enrollment_bronze_path = request.options.get("enrollment_bronze_path")
        if not enrollment_bronze_path:
            raise ValueError("enrollment_bronze_path is required")
        return run_lms_recommendation_training_from_bronze(
            request.input_path,
            enrollment_bronze_path,
            request.output_dir,
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
            upstream_manifest_paths=request.options.get("upstream_manifest_paths")
            or optional_path_list(request.options.get("upstream_manifest_path")),
        )


def run_lms_recommendation_training_from_bronze(
    course_bronze_path: str | Path,
    enrollment_bronze_path: str | Path,
    output_dir: str | Path,
    *,
    snapshot_id: str | None = None,
    built_at: str | None = None,
    upstream_manifest_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
) -> LmsRecommendationTrainingResult:
    course_path = Path(course_bronze_path)
    enrollment_path = Path(enrollment_bronze_path)
    target_dir = Path(output_dir)
    build_time = built_at or utc_now()
    resolved_snapshot_id = snapshot_id or f"lms-recsys-{compact_timestamp(build_time)}"

    course_bronze_rows = read_jsonl(course_path)
    enrollment_bronze_rows = read_jsonl(enrollment_path)
    course_catalog_rows, course_errors = build_course_catalog_rows(
        course_bronze_rows,
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )
    training_rows, training_errors, rejected_rows = build_training_rows(
        enrollment_bronze_rows,
        published_course_ids={str(row["course_id"]) for row in course_catalog_rows},
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )

    course_catalog_path = target_dir / "gold" / "lms_recommendation_course_catalog.jsonl"
    training_path = target_dir / "gold" / "lms_recommendation_training_interactions.jsonl"
    course_hash = write_jsonl(course_catalog_path, course_catalog_rows)
    training_hash = write_jsonl(training_path, training_rows)

    manifest = build_manifest(
        snapshot_id=resolved_snapshot_id,
        generated_at=build_time,
        course_bronze_path=course_path,
        enrollment_bronze_path=enrollment_path,
        course_catalog_path=course_catalog_path,
        training_path=training_path,
        output_dir=target_dir,
        course_catalog_rows=course_catalog_rows,
        training_rows=training_rows,
        rejected_rows=rejected_rows,
        course_hash=course_hash,
        training_hash=training_hash,
        quality_errors=tuple(course_errors + training_errors),
        upstream_manifest_paths=upstream_manifest_paths,
    )
    manifest_path = (
        target_dir / "manifests" / f"lms_recommendation_training.{resolved_snapshot_id}.json"
    )
    write_json(manifest_path, manifest)
    return LmsRecommendationTrainingResult(
        snapshot_id=resolved_snapshot_id,
        course_catalog_path=course_catalog_path,
        training_path=training_path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def build_course_catalog_rows(
    course_bronze_rows: list[dict[str, Any]],
    *,
    snapshot_id: str,
    built_at: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, bronze in enumerate(course_bronze_rows):
        if bronze.get("event_type") != "course.published.v1":
            continue
        raw_payload = payload(bronze)
        if raw_payload.get("publishingState") != "PUBLISHED":
            continue
        course_id = str(raw_payload.get("courseId") or bronze.get("course_id") or "")
        org_id = str(raw_payload.get("orgId") or bronze.get("org_id") or "")
        course_published_at = raw_payload.get("coursePublishedAt") or bronze.get("course_published_at")
        source_event_id = bronze.get("event_id")
        row_errors: list[str] = []
        if not course_id:
            row_errors.append("course_id is required")
        if not org_id:
            row_errors.append("org_id is required")
        if not course_published_at:
            row_errors.append("course_published_at is required")
        if not source_event_id:
            row_errors.append("source_event_id is required")
        if row_errors:
            errors.append(f"course catalog row {index} failed checks: {', '.join(row_errors)}")
            continue
        if course_id in seen:
            errors.append(f"course catalog duplicate course_id {course_id}")
            continue
        seen.add(course_id)
        metadata = safe_metadata(raw_payload.get("metadata"))
        skill_tags = metadata.get("skillTags") or metadata.get("skill_tags") or []
        rows.append(
            {
                "dataset_snapshot_id": snapshot_id,
                "product_id": PRODUCT_ID,
                "org_id": org_id,
                "course_id": course_id,
                "course_slug": raw_payload.get("courseSlug") or bronze.get("course_slug"),
                "catalog_visibility": raw_payload.get("catalogVisibility")
                or bronze.get("catalog_visibility")
                or "PUBLIC",
                "title": metadata.get("title"),
                "topic": metadata.get("topic"),
                "level": metadata.get("level"),
                "skill_tags": skill_tags if isinstance(skill_tags, list) else [str(skill_tags)],
                "course_published_at": course_published_at,
                "source_event_id": source_event_id,
                "built_at": built_at,
                "quality_passed": True,
            }
        )
    if not rows:
        errors.append("course catalog must contain at least one published course")
    return rows, errors


def build_training_rows(
    enrollment_bronze_rows: list[dict[str, Any]],
    *,
    published_course_ids: set[str],
    snapshot_id: str,
    built_at: str,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    rejected_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, bronze in enumerate(enrollment_bronze_rows):
        if bronze.get("event_type") != "enrollment.completed.v1":
            continue
        raw_payload = payload(bronze)
        learner_id_hash = raw_payload.get("learnerIdHash") or bronze.get("learner_id_hash")
        course_id = raw_payload.get("courseId") or bronze.get("course_id")
        org_id = raw_payload.get("orgId") or bronze.get("org_id")
        source_enrollment_id = raw_payload.get("enrollmentId") or bronze.get("enrollment_id")
        occurred_at = raw_payload.get("completedAt") or bronze.get("completed_at") or bronze.get("occurred_at")
        source_event_id = str(bronze.get("event_id") or "")
        row_errors: list[str] = []
        if not org_id:
            row_errors.append("org_id is required")
        if not learner_id_hash:
            row_errors.append("learner_id_hash is required")
        if not course_id:
            row_errors.append("course_id is required")
        elif str(course_id) not in published_course_ids:
            row_errors.append("course_id is not in published course catalog")
        if not occurred_at:
            row_errors.append("occurred_at is required")
        if not source_event_id:
            row_errors.append("source_event_id is required")
        if not source_enrollment_id:
            row_errors.append("source_enrollment_id is required")
        dedupe_key = (str(source_event_id), str(learner_id_hash), str(course_id))
        if dedupe_key in seen:
            row_errors.append("duplicate learner-course source event")
        if row_errors:
            rejected_rows.append(
                {
                    "record_ordinal": index,
                    "event_id": bronze.get("event_id"),
                    "course_id": course_id,
                    "learner_id_hash": learner_id_hash,
                    "errors": row_errors,
                }
            )
            continue
        seen.add(dedupe_key)
        rows.append(
            {
                "dataset_snapshot_id": snapshot_id,
                "product_id": PRODUCT_ID,
                "org_id": org_id,
                "learner_id_hash": learner_id_hash,
                "course_id": str(course_id),
                "event_type": "ENROLLMENT",
                "event_weight": ENROLLMENT_WEIGHT,
                "occurred_at": occurred_at,
                "source_event_id": source_event_id,
                "source_enrollment_id": source_enrollment_id,
                "built_at": built_at,
                "quality_passed": True,
            }
        )
    if not rows:
        errors.append("training interactions must contain at least one approved enrollment")
    learner_count = len({str(row["learner_id_hash"]) for row in rows})
    course_count = len({str(row["course_id"]) for row in rows})
    if learner_count < 2:
        errors.append("training interactions require at least two learners")
    if course_count < 2:
        errors.append("training interactions require at least two courses")
    if rejected_rows:
        errors.append(f"{len(rejected_rows)} enrollment rows were rejected from training features")
    return rows, errors, rejected_rows


def build_manifest(
    *,
    snapshot_id: str,
    generated_at: str,
    course_bronze_path: Path,
    enrollment_bronze_path: Path,
    course_catalog_path: Path,
    training_path: Path,
    output_dir: Path,
    course_catalog_rows: list[dict[str, Any]],
    training_rows: list[dict[str, Any]],
    rejected_rows: list[dict[str, Any]],
    course_hash: str,
    training_hash: str,
    quality_errors: tuple[str, ...],
    upstream_manifest_paths: list[str | Path] | tuple[str | Path, ...] | None,
) -> dict[str, Any]:
    upstream_paths = [Path(path) for path in upstream_manifest_paths or []]
    learner_count = len({str(row["learner_id_hash"]) for row in training_rows})
    course_count = len({str(row["course_id"]) for row in course_catalog_rows})
    training_course_count = len({str(row["course_id"]) for row in training_rows})
    return {
        "pipeline": PIPELINE_NAME,
        "product_id": PRODUCT_ID,
        "domain_id": DOMAIN_ID,
        "snapshot_id": snapshot_id,
        "primary_output": TRAINING_PRODUCT,
        "generated_at": generated_at,
        "inputs": {
            "course_bronze": {
                "path": course_bronze_path.as_posix(),
                "content_hash": hash_file(course_bronze_path),
            },
            "enrollment_bronze": {
                "path": enrollment_bronze_path.as_posix(),
                "content_hash": hash_file(enrollment_bronze_path),
            },
            "upstream_manifests": [
                {"path": path.as_posix(), "content_hash": hash_file(path)} for path in upstream_paths
            ],
        },
        "layers": {
            COURSE_CATALOG_PRODUCT: {
                "path": relative_path(course_catalog_path, output_dir),
                "row_count": len(course_catalog_rows),
                "content_hash": course_hash,
            },
            TRAINING_PRODUCT: {
                "path": relative_path(training_path, output_dir),
                "row_count": len(training_rows),
                "content_hash": training_hash,
            },
        },
        "metrics": {
            "published_course_count": course_count,
            "training_course_count": training_course_count,
            "training_learner_count": learner_count,
            "training_interaction_count": len(training_rows),
            "rejected_enrollment_count": len(rejected_rows),
        },
        "lineage_edges": [
            {
                "type": "BUILD_PUBLISHED_COURSE_CATALOG",
                "source": "bronze.events_course_published",
                "target": COURSE_CATALOG_PRODUCT,
            },
            {
                "type": "BUILD_RECOMMENDATION_TRAINING_FEATURES",
                "source": "bronze.events_enrollment_completed",
                "target": TRAINING_PRODUCT,
            },
        ],
        "rejected_enrollments_sample": rejected_rows[:20],
        "quality_passed": not quality_errors,
        "quality_errors": list(quality_errors),
    }


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
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


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{canonical_json(record)}\n" for record in records)
    target.write_text(content, encoding="utf-8")
    return content_hash(content)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def content_hash(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def payload(row: dict[str, Any]) -> dict[str, Any]:
    raw_payload = row.get("raw_payload")
    return raw_payload if isinstance(raw_payload, dict) else {}


def safe_metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def optional_path_list(value: Any) -> list[str | Path] | None:
    if value is None:
        return None
    return list(value) if isinstance(value, (list, tuple)) else [value]


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact_timestamp(value: str) -> str:
    return (
        value.replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("+00:00", "Z")
        .replace("Z", "")
    )
