from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from courseflow_ml.core.config import get_settings
from courseflow_ml.domain.recommendation import TrainingInteraction
from courseflow_ml.repositories.postgres_recommendation_repository import (
    PostgresRecommendationRepository,
)
from courseflow_ml.services.recommendation_service import RecommendationMlService
from courseflow_ml.training.implicit_cf import (
    ALGORITHM,
    ImplicitCfConfig,
    ImplicitItemCfTrainer,
)

ARTIFACT_TYPE = "courseflow.lms.related_course_recommendations"
ARTIFACT_VERSION = 1
DP_LMS_TRAINING_PRODUCT = "gold.lms_recommendation_training_interactions"
DP_RECSYS_INTERACTIONS_PRODUCT = "gold.recsys_interactions"
SUPPORTED_DP_EVENT_TYPES = {"ENROLLMENT", "CLICK", "IMPRESSION"}


def main() -> int:
    parser = argparse.ArgumentParser(description="CourseFlow ML training utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    related = subparsers.add_parser("train-related-courses")
    related.add_argument(
        "--input",
        required=True,
        help="JSON file containing training interactions",
    )
    related.add_argument("--min-support", type=int, default=1)
    related.add_argument("--max-related-per-course", type=int, default=24)
    dp_related = subparsers.add_parser("train-related-courses-from-dp-gold")
    dp_related.add_argument(
        "--input",
        required=True,
        help="DP Gold JSONL file containing lms recommendation training interactions",
    )
    dp_related.add_argument("--manifest", default=None, help="Optional DP pipeline manifest path")
    dp_related.add_argument(
        "--output",
        default=None,
        help="Optional recommendation artifact JSON path",
    )
    dp_related.add_argument("--model-version", required=True)
    dp_related.add_argument("--min-support", type=int, default=3)
    dp_related.add_argument("--max-related-per-course", type=int, default=24)
    worker = subparsers.add_parser("worker")
    worker.add_argument("--worker-id", default="recommendation-ml-worker")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--idle-sleep-seconds", type=float, default=5.0)
    subparsers.add_parser("scrub-training-payloads")
    args = parser.parse_args()

    if args.command == "train-related-courses":
        with open(args.input, encoding="utf-8") as handle:
            payload = json.load(handle)
        interactions = [
            TrainingInteraction(
                principal_id=row["principalId"],
                course_id=UUID(row["courseId"]),
                event_type=row["eventType"],
                weight=row.get("weight"),
            )
            for row in payload.get("interactions", payload)
        ]
        result = ImplicitItemCfTrainer(
            ImplicitCfConfig(
                min_support=args.min_support,
                max_related_per_course=args.max_related_per_course,
            )
        ).train(interactions)
        json.dump(
            {
                "algorithm": "IMPLICIT_ITEM_CF_V1",
                "eventCount": result.event_count,
                "principalCount": result.principal_count,
                "courseCount": result.course_count,
                "pairCount": result.pair_count,
                "qualityScore": result.quality_score,
                "recommendations": [
                    {
                        "courseId": str(row.course_id),
                        "relatedCourseId": str(row.related_course_id),
                        "rank": row.rank,
                        "score": row.score,
                        "similarity": row.similarity,
                        "supportCount": row.support_count,
                        "reasonCode": row.reason_code,
                    }
                    for row in result.recommendations
                ],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    if args.command == "train-related-courses-from-dp-gold":
        artifact = train_related_courses_from_dp_gold(
            args.input,
            manifest_path=args.manifest,
            model_version=args.model_version,
            min_support=args.min_support,
            max_related_per_course=args.max_related_per_course,
        )
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(artifact, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        json.dump(artifact, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    if args.command == "worker":
        return run_worker(
            worker_id=str(args.worker_id),
            once=bool(args.once),
            idle_sleep_seconds=float(args.idle_sleep_seconds),
        )
    if args.command == "scrub-training-payloads":
        return run_scrub_training_payloads()
    return 0


def train_related_courses_from_dp_gold(
    input_path: str,
    *,
    manifest_path: str | None,
    model_version: str,
    min_support: int,
    max_related_per_course: int,
) -> dict[str, object]:
    source_path = Path(input_path)
    rows = read_jsonl(source_path)
    manifest_file = Path(manifest_path) if manifest_path else None
    manifest = read_json_object(manifest_file) if manifest_file else None
    manifest_hash = sha256_file(manifest_file) if manifest_file else None
    source_data_product = infer_dp_source_data_product(rows, manifest)
    training_layer = dp_manifest_layer(manifest, source_data_product)
    batch = dp_gold_training_interactions(rows)
    result = ImplicitItemCfTrainer(
        ImplicitCfConfig(
            min_support=min_support,
            max_related_per_course=max_related_per_course,
        )
    ).train(batch.interactions)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    artifact = {
        "artifactVersion": ARTIFACT_VERSION,
        "artifactType": ARTIFACT_TYPE,
        "algorithm": ALGORITHM,
        "status": "ACTIVE" if result.recommendations else "INSUFFICIENT_DATA",
        "modelVersion": model_version,
        "generatedAt": generated_at,
        "sourceDataProduct": source_data_product,
        "dpSnapshot": {
            "snapshotIds": sorted(batch.snapshot_ids),
            "trainingPath": source_path.as_posix(),
            "trainingContentHash": sha256_file(source_path),
            "manifestPath": manifest_file.as_posix() if manifest_file else None,
            "manifestContentHash": manifest_hash,
            "manifestSnapshotId": optional_str(manifest.get("snapshot_id")) if manifest else None,
            "manifestQualityPassed": manifest.get("quality_passed") if manifest else None,
            "manifestPipeline": optional_str(manifest.get("pipeline")) if manifest else None,
            "manifestLayerPath": (
                optional_str(training_layer.get("path")) if training_layer else None
            ),
            "manifestLayerContentHash": (
                optional_str(training_layer.get("content_hash")) if training_layer else None
            ),
            "manifestLayerRowCount": training_layer.get("row_count") if training_layer else None,
            "rowCount": len(rows),
            "acceptedRowCount": batch.accepted_row_count,
            "acceptedInteractionCount": len(batch.interactions),
            "rejectedRowCount": len(batch.rejected_rows),
            "eventTypes": sorted(batch.event_types),
            "minOccurredAt": min(batch.occurred_at_values) if batch.occurred_at_values else None,
            "maxOccurredAt": max(batch.occurred_at_values) if batch.occurred_at_values else None,
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
        "rejectedRowsSample": batch.rejected_rows[:20],
    }
    return artifact


@dataclass(frozen=True, slots=True)
class DpGoldTrainingBatch:
    interactions: list[TrainingInteraction]
    rejected_rows: list[dict[str, object]]
    snapshot_ids: set[str]
    accepted_row_count: int
    event_types: set[str]
    occurred_at_values: list[str]


def dp_gold_training_interactions(
    rows: list[dict[str, object]],
) -> DpGoldTrainingBatch:
    interactions: list[TrainingInteraction] = []
    rejected_rows: list[dict[str, object]] = []
    snapshot_ids: set[str] = set()
    accepted_row_count = 0
    event_types: set[str] = set()
    occurred_at_values: list[str] = []
    for index, row in enumerate(rows):
        snapshot_id = optional_str(row.get("dataset_snapshot_id"))
        if snapshot_id:
            snapshot_ids.add(snapshot_id)
        if row.get("quality_passed") is not True:
            rejected_rows.append({"rowIndex": index, "reason": "quality_passed_false"})
            continue
        principal_id = optional_str(row.get("learner_id_hash"))
        event_type = normalize_dp_event_type(row.get("event_type"))
        course_id = optional_str(row.get("course_id"))
        if not principal_id or not event_type or not course_id:
            rejected_rows.append(
                {
                    "rowIndex": index,
                    "reason": "missing principal_id, course_id or event_type",
                    "fields": missing_fields(
                        row,
                        {
                            "learner_id_hash": principal_id,
                            "course_id": course_id,
                            "event_type": event_type,
                        },
                    ),
                }
            )
            continue
        required_fields = missing_fields(
            row,
            {
                "dataset_snapshot_id": snapshot_id,
                "product_id": optional_str(row.get("product_id")),
                "org_id": optional_str(row.get("org_id")),
                "event_weight": row.get("event_weight"),
                "occurred_at": optional_str(row.get("occurred_at")),
                "source_event_id": optional_str(row.get("source_event_id")),
                "built_at": optional_str(row.get("built_at")),
            },
        )
        if required_fields:
            rejected_rows.append(
                {"rowIndex": index, "reason": "missing_required_fields", "fields": required_fields}
            )
            continue
        if event_type not in SUPPORTED_DP_EVENT_TYPES:
            rejected_rows.append(
                {"rowIndex": index, "reason": "unsupported_event_type", "eventType": event_type}
            )
            continue
        try:
            parsed_course_id = UUID(str(course_id))
            weight = parse_dp_event_weight(row.get("event_weight"))
        except (TypeError, ValueError):
            rejected_rows.append({"rowIndex": index, "reason": "invalid course_id or event_weight"})
            continue
        if not math.isfinite(weight) or weight <= 0 or weight > 50:
            rejected_rows.append({"rowIndex": index, "reason": "invalid course_id or event_weight"})
            continue
        try:
            course_ids = dp_gold_course_ids(row, parsed_course_id)
        except ValueError as exc:
            rejected_rows.append({"rowIndex": index, "reason": str(exc)})
            continue
        accepted_row_count += 1
        event_types.add(event_type)
        occurred_at = optional_str(row.get("occurred_at"))
        if occurred_at:
            occurred_at_values.append(occurred_at)
        for interaction_course_id in course_ids:
            interactions.append(
                TrainingInteraction(
                    principal_id=principal_id,
                    course_id=interaction_course_id,
                    event_type=event_type,
                    weight=weight,
                )
            )
    return DpGoldTrainingBatch(
        interactions=interactions,
        rejected_rows=rejected_rows,
        snapshot_ids=snapshot_ids,
        accepted_row_count=accepted_row_count,
        event_types=event_types,
        occurred_at_values=occurred_at_values,
    )


def dp_gold_course_ids(row: dict[str, object], parsed_course_id: UUID) -> list[UUID]:
    course_ids = [parsed_course_id]
    related_course_id = optional_str(row.get("related_course_id"))
    if not related_course_id:
        return course_ids
    try:
        parsed_related_course_id = UUID(related_course_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_related_course_id") from exc
    if parsed_related_course_id == parsed_course_id:
        raise ValueError("self_related_course")
    course_ids.append(parsed_related_course_id)
    return course_ids


def normalize_dp_event_type(value: object) -> str | None:
    text = optional_str(value)
    return text.upper().replace("-", "_") if text else None


def parse_dp_event_weight(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("event_weight must be numeric")
    if isinstance(value, int | float | str):
        return float(value)
    raise TypeError("event_weight must be numeric")


def optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def missing_fields(row: dict[str, object], values: dict[str, object | None]) -> list[str]:
    return [field for field, value in values.items() if value is None or value == ""]


def infer_dp_source_data_product(
    rows: list[dict[str, object]],
    manifest: dict[str, object] | None,
) -> str:
    if manifest is not None:
        layers = manifest.get("layers")
        if isinstance(layers, dict):
            for candidate in (DP_LMS_TRAINING_PRODUCT, DP_RECSYS_INTERACTIONS_PRODUCT):
                if candidate in layers:
                    return candidate
    if any("related_course_id" in row for row in rows):
        return DP_RECSYS_INTERACTIONS_PRODUCT
    return DP_LMS_TRAINING_PRODUCT


def dp_manifest_layer(
    manifest: dict[str, object] | None,
    source_data_product: str,
) -> dict[str, object] | None:
    if manifest is None:
        return None
    layers = manifest.get("layers")
    if not isinstance(layers, dict):
        return None
    layer = layers.get(source_data_product)
    return layer if isinstance(layer, dict) else None


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL record") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: JSONL record must be an object")
            rows.append(row)
    return rows


def read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must be an object")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def recommendation_service_from_settings() -> RecommendationMlService:
    settings = get_settings()
    return RecommendationMlService(
        PostgresRecommendationRepository(settings.database_url),
        default_max_related_per_course=settings.recommendation_ml_default_max_related_per_course,
        max_related_per_course=settings.recommendation_ml_max_related_per_course,
        default_min_support=settings.recommendation_ml_default_min_support,
        max_training_events=settings.recommendation_ml_max_training_events,
        training_job_lease_seconds=settings.recommendation_ml_training_job_lease_seconds,
        training_job_max_attempts=settings.recommendation_ml_training_job_max_attempts,
        training_job_requeue_delay_seconds=settings.recommendation_ml_training_job_requeue_delay_seconds,
        min_activation_event_count=settings.recommendation_ml_min_activation_event_count,
        min_activation_principal_count=settings.recommendation_ml_min_activation_principal_count,
        min_activation_course_count=settings.recommendation_ml_min_activation_course_count,
        min_activation_pair_count=settings.recommendation_ml_min_activation_pair_count,
        min_activation_quality_score=settings.recommendation_ml_min_activation_quality_score,
        auto_activate_trained_models=settings.recommendation_ml_auto_activate_trained_models,
        training_payload_retention_days=settings.recommendation_ml_training_payload_retention_days,
        principal_hash_secret=settings.recommendation_ml_principal_hash_secret,
    )


def run_worker(worker_id: str, once: bool, idle_sleep_seconds: float) -> int:
    settings = get_settings()
    service = recommendation_service_from_settings()
    scrub_interval_seconds = max(60, settings.recommendation_ml_payload_scrub_interval_seconds)
    next_scrub_at = 0.0
    while True:
        monotonic_now = time.monotonic()
        if monotonic_now >= next_scrub_at:
            scrubbed = service.scrub_expired_training_payloads()
            if scrubbed > 0:
                json.dump(
                    {
                        "event": "trainingPayloadsScrubbed",
                        "scrubbedPayloads": scrubbed,
                        "retentionDays": service.training_payload_retention_days,
                    },
                    sys.stdout,
                    indent=2,
                )
                sys.stdout.write("\n")
            next_scrub_at = monotonic_now + scrub_interval_seconds
        response = service.process_next_training_job(worker_id)
        if response is not None:
            json.dump(response, sys.stdout, indent=2)
            sys.stdout.write("\n")
            if once:
                return 0
            continue
        if once:
            sys.stdout.write("No queued recommendation ML training jobs found\n")
            return 0
        time.sleep(max(0.25, idle_sleep_seconds))


def run_scrub_training_payloads() -> int:
    service = recommendation_service_from_settings()
    scrubbed = service.scrub_expired_training_payloads()
    json.dump(
        {
            "event": "trainingPayloadsScrubbed",
            "scrubbedPayloads": scrubbed,
            "retentionDays": service.training_payload_retention_days,
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
