from __future__ import annotations

import argparse
import json
import sys
import time
from uuid import UUID

from courseflow_ml.core.config import get_settings
from courseflow_ml.domain.recommendation import TrainingInteraction
from courseflow_ml.repositories.postgres_recommendation_repository import (
    PostgresRecommendationRepository,
)
from courseflow_ml.services.recommendation_service import RecommendationMlService
from courseflow_ml.training.implicit_cf import ImplicitCfConfig, ImplicitItemCfTrainer


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
    if args.command == "worker":
        return run_worker(
            worker_id=str(args.worker_id),
            once=bool(args.once),
            idle_sleep_seconds=float(args.idle_sleep_seconds),
        )
    if args.command == "scrub-training-payloads":
        return run_scrub_training_payloads()
    return 0


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
