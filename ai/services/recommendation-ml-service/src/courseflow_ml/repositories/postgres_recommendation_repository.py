from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import IntegrityError

from courseflow_ml.domain.recommendation import (
    ModelActivationApprovalRecord,
    ModelOpsAuditRecord,
    ModelVersionRecord,
    RecommendationOperationalMetrics,
    ScoredRecommendation,
    TrainingJobRecord,
    TrainingOpsAuditRecord,
    TrainingRunRecord,
)
from courseflow_ml.repositories.recommendation_repository import (
    PendingModelActivationApprovalError,
)


class PostgresRecommendationRepository:
    ACTIVE_MODEL_LOCK_NAMESPACE = 947201
    ACTIVE_MODEL_LOCK_KEY = 530110

    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    def database_ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def current_migration_version(self) -> str | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT version_num
                    FROM alembic_version
                    ORDER BY version_num DESC
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
        return str(row) if row is not None else None

    def training_run(self, run_id: UUID) -> TrainingRunRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM recommendation_training_runs WHERE id = :id"),
                {"id": run_id},
            ).mappings().first()
        return to_training_run(row) if row else None

    def model_version(self, model_version: str) -> ModelVersionRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT * FROM recommendation_model_versions
                    WHERE model_version = :model_version
                    """
                ),
                {"model_version": model_version},
            ).mappings().first()
        return to_model_version(row) if row else None

    def active_model(self) -> ModelVersionRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT * FROM recommendation_model_versions
                    WHERE status = 'ACTIVE'
                    ORDER BY activated_at DESC
                    LIMIT 1
                    """
                )
            ).mappings().first()
        return to_model_version(row) if row else None

    def operational_metrics(
        self,
        observed_at: datetime,
        stale_running_before: datetime,
        active_model_stale_before: datetime,
        expected_migration_revision: str,
    ) -> RecommendationOperationalMetrics:
        with self.engine.connect() as connection:
            status_rows = connection.execute(
                text(
                    """
                    SELECT status, COUNT(*) AS run_count
                    FROM recommendation_training_runs
                    GROUP BY status
                    """
                )
            ).mappings().all()
            training_runs_by_status = {
                str(row["status"]).upper(): int(row["run_count"]) for row in status_rows
            }
            training_stats = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE status = 'RUNNING'
                              AND locked_at IS NOT NULL
                              AND locked_at < :stale_running_before
                        ) AS stale_running_training_runs,
                        EXTRACT(EPOCH FROM (
                            :observed_at - MIN(started_at) FILTER (WHERE status = 'QUEUED')
                        )) AS oldest_queued_age_seconds,
                        EXTRACT(EPOCH FROM (
                            :observed_at - MIN(COALESCE(locked_at, started_at))
                                FILTER (WHERE status = 'RUNNING')
                        )) AS oldest_running_age_seconds
                    FROM recommendation_training_runs
                    """
                ),
                {
                    "observed_at": observed_at,
                    "stale_running_before": stale_running_before,
                },
            ).mappings().one()
            activation_approval_stats = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE status = 'PENDING'
                        ) AS pending_activation_approvals,
                        EXTRACT(EPOCH FROM (
                            :observed_at - MIN(created_at) FILTER (WHERE status = 'PENDING')
                        )) AS oldest_pending_activation_approval_age_seconds
                    FROM recommendation_model_activation_approvals
                    """
                ),
                {"observed_at": observed_at},
            ).mappings().one()
            active_model = connection.execute(
                text(
                    """
                    SELECT
                        EXTRACT(EPOCH FROM (
                            :observed_at - COALESCE(activated_at, trained_at)
                        )) AS active_model_age_seconds,
                        COALESCE(activated_at, trained_at) < :active_model_stale_before
                            AS active_model_stale
                    FROM recommendation_model_versions
                    WHERE status = 'ACTIVE'
                    ORDER BY activated_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "observed_at": observed_at,
                    "active_model_stale_before": active_model_stale_before,
                },
            ).mappings().first()
            current_revision = connection.execute(
                text(
                    """
                    SELECT version_num
                    FROM alembic_version
                    ORDER BY version_num DESC
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
        return RecommendationOperationalMetrics(
            training_runs_by_status=training_runs_by_status,
            stale_running_training_runs=metric_int(
                training_stats["stale_running_training_runs"]
            ),
            oldest_queued_age_seconds=metric_float(
                training_stats["oldest_queued_age_seconds"]
            ),
            oldest_running_age_seconds=metric_float(
                training_stats["oldest_running_age_seconds"]
            ),
            pending_activation_approvals=metric_int(
                activation_approval_stats["pending_activation_approvals"]
            ),
            oldest_pending_activation_approval_age_seconds=metric_float(
                activation_approval_stats[
                    "oldest_pending_activation_approval_age_seconds"
                ]
            ),
            active_model_present=active_model is not None,
            active_model_age_seconds=(
                metric_float(active_model["active_model_age_seconds"])
                if active_model is not None
                else None
            ),
            active_model_stale=(
                bool(active_model["active_model_stale"])
                if active_model is not None
                else False
            ),
            migration_ready=str(current_revision) == expected_migration_revision,
        )

    def list_training_runs(self, status: str | None, limit: int) -> list[TrainingRunRecord]:
        safe_limit = max(1, min(limit, 200))
        normalized_status = normalize_status(status)
        with self.engine.connect() as connection:
            if normalized_status is not None:
                rows = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM recommendation_training_runs
                        WHERE status = :status
                        ORDER BY started_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"status": normalized_status, "limit": safe_limit},
                ).mappings().all()
            else:
                rows = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM recommendation_training_runs
                        ORDER BY started_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"limit": safe_limit},
                ).mappings().all()
        return [to_training_run(row) for row in rows]

    def list_model_versions(self, status: str | None, limit: int) -> list[ModelVersionRecord]:
        safe_limit = max(1, min(limit, 200))
        normalized_status = normalize_status(status)
        with self.engine.connect() as connection:
            if normalized_status is not None:
                rows = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM recommendation_model_versions
                        WHERE status = :status
                        ORDER BY COALESCE(activated_at, trained_at) DESC, trained_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"status": normalized_status, "limit": safe_limit},
                ).mappings().all()
            else:
                rows = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM recommendation_model_versions
                        ORDER BY COALESCE(activated_at, trained_at) DESC, trained_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"limit": safe_limit},
                ).mappings().all()
        return [to_model_version(row) for row in rows]

    def list_model_ops_audit(self, limit: int) -> list[ModelOpsAuditRecord]:
        safe_limit = max(1, min(limit, 200))
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_ops_audit
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": safe_limit},
            ).mappings().all()
        return [to_model_ops_audit(row) for row in rows]

    def model_activation_approval(
        self,
        approval_id: UUID,
    ) -> ModelActivationApprovalRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_activation_approvals
                    WHERE id = :id
                    """
                ),
                {"id": approval_id},
            ).mappings().first()
        return to_model_activation_approval(row) if row else None

    def list_model_activation_approvals(
        self,
        status: str | None,
        limit: int,
    ) -> list[ModelActivationApprovalRecord]:
        safe_limit = max(1, min(limit, 200))
        normalized_status = normalize_status(status)
        with self.engine.connect() as connection:
            if normalized_status is not None:
                rows = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM recommendation_model_activation_approvals
                        WHERE status = :status
                        ORDER BY created_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"status": normalized_status, "limit": safe_limit},
                ).mappings().all()
            else:
                rows = connection.execute(
                    text(
                        """
                        SELECT *
                        FROM recommendation_model_activation_approvals
                        ORDER BY created_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"limit": safe_limit},
                ).mappings().all()
        return [to_model_activation_approval(row) for row in rows]

    def pending_model_activation_approval(
        self,
        model_version: str,
    ) -> ModelActivationApprovalRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_activation_approvals
                    WHERE model_version = :model_version
                      AND status = 'PENDING'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"model_version": model_version},
            ).mappings().first()
        return to_model_activation_approval(row) if row else None

    def list_training_ops_audit(self, limit: int) -> list[TrainingOpsAuditRecord]:
        safe_limit = max(1, min(limit, 200))
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_training_ops_audit
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": safe_limit},
            ).mappings().all()
        return [to_training_ops_audit(row) for row in rows]

    def scores_for_model(self, model_version: str) -> list[ScoredRecommendation]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT * FROM recommendation_related_course_scores
                    WHERE model_version = :model_version
                    ORDER BY course_id ASC, rank ASC
                    """
                ),
                {"model_version": model_version},
            ).mappings().all()
        return [to_score(row) for row in rows]

    def scores_for_course(
        self,
        model_version: str,
        course_id: UUID,
        limit: int,
    ) -> list[ScoredRecommendation]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT * FROM recommendation_related_course_scores
                    WHERE model_version = :model_version
                      AND course_id = :course_id
                    ORDER BY rank ASC, score DESC
                    LIMIT :limit
                    """
                ),
                {"model_version": model_version, "course_id": course_id, "limit": limit},
            ).mappings().all()
        return [to_score(row) for row in rows]

    def create_training_run(
        self,
        run_id: UUID,
        requested_model_version: str | None,
        algorithm: str,
        request_hash: str,
        min_support: int,
        max_related_per_course: int,
        requested_by: str,
        started_at: datetime,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_training_runs (
                        id, requested_model_version, algorithm, status, request_hash,
                        min_support, max_related_per_course, requested_by, started_at
                    )
                    VALUES (
                        :id, :requested_model_version, :algorithm, 'STARTED', :request_hash,
                        :min_support, :max_related_per_course, :requested_by, :started_at
                    )
                    """
                ),
                {
                    "id": run_id,
                    "requested_model_version": requested_model_version,
                    "algorithm": algorithm,
                    "request_hash": request_hash,
                    "min_support": min_support,
                    "max_related_per_course": max_related_per_course,
                    "requested_by": requested_by,
                    "started_at": started_at,
                },
            )

    def enqueue_training_run(
        self,
        run_id: UUID,
        requested_model_version: str | None,
        algorithm: str,
        request_hash: str,
        min_support: int,
        max_related_per_course: int,
        requested_by: str,
        payload_json: str,
        queued_at: datetime,
    ) -> TrainingRunRecord:
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    INSERT INTO recommendation_training_runs (
                        id, requested_model_version, algorithm, status, request_hash,
                        min_support, max_related_per_course, requested_by, payload_json,
                        available_at, started_at
                    )
                    VALUES (
                        :id, :requested_model_version, :algorithm, 'QUEUED', :request_hash,
                        :min_support, :max_related_per_course, :requested_by, :payload_json,
                        :queued_at, :queued_at
                    )
                    RETURNING *
                    """
                ),
                {
                    "id": run_id,
                    "requested_model_version": requested_model_version,
                    "algorithm": algorithm,
                    "request_hash": request_hash,
                    "min_support": min_support,
                    "max_related_per_course": max_related_per_course,
                    "requested_by": requested_by,
                    "payload_json": payload_json,
                    "queued_at": queued_at,
                },
            ).mappings().one()
        return to_training_run(row)

    def claim_next_training_job(
        self,
        worker_id: str,
        claimed_at: datetime,
    ) -> TrainingJobRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    WITH next_job AS (
                        SELECT id
                        FROM recommendation_training_runs
                        WHERE status = 'QUEUED'
                          AND (available_at IS NULL OR available_at <= :claimed_at)
                        ORDER BY started_at ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE recommendation_training_runs run
                       SET status = 'RUNNING',
                           locked_by = :worker_id,
                           locked_at = :claimed_at,
                           attempt_count = attempt_count + 1
                      FROM next_job
                     WHERE run.id = next_job.id
                     RETURNING run.*
                    """
                ),
                {"worker_id": worker_id, "claimed_at": claimed_at},
            ).mappings().first()
        if row is None:
            return None
        payload_json = row["payload_json"]
        return TrainingJobRecord(
            to_training_run(row),
            "{}" if payload_json is None else str(payload_json),
        )

    def recover_stale_training_jobs(
        self,
        stale_before: datetime,
        recovered_at: datetime,
        max_attempts: int,
        requeue_delay_seconds: int,
    ) -> int:
        safe_max_attempts = max(1, max_attempts)
        safe_delay_seconds = max(0, requeue_delay_seconds)
        with self.engine.begin() as connection:
            failed = connection.execute(
                text(
                    """
                    UPDATE recommendation_training_runs
                       SET status = 'FAILED',
                           error_class = 'WORKER_LEASE_EXPIRED',
                           error_message = 'Worker lease expired after max attempts',
                           finished_at = :recovered_at,
                           locked_by = NULL,
                           locked_at = NULL
                     WHERE status = 'RUNNING'
                       AND locked_at IS NOT NULL
                       AND locked_at < :stale_before
                       AND attempt_count >= :max_attempts
                    """
                ),
                {
                    "stale_before": stale_before,
                    "recovered_at": recovered_at,
                    "max_attempts": safe_max_attempts,
                },
            ).rowcount
            requeued = connection.execute(
                text(
                    """
                    UPDATE recommendation_training_runs
                       SET status = 'QUEUED',
                           error_class = 'WORKER_LEASE_EXPIRED',
                           error_message = 'Worker lease expired; job was requeued',
                           available_at = :available_at,
                           locked_by = NULL,
                           locked_at = NULL
                     WHERE status = 'RUNNING'
                       AND locked_at IS NOT NULL
                       AND locked_at < :stale_before
                       AND attempt_count < :max_attempts
                    """
                ),
                {
                    "stale_before": stale_before,
                    "available_at": recovered_at + timedelta(seconds=safe_delay_seconds),
                    "max_attempts": safe_max_attempts,
                },
            ).rowcount
        return (failed or 0) + (requeued or 0)

    def scrub_training_payloads(
        self,
        completed_before: datetime,
        statuses: tuple[str, ...],
    ) -> int:
        if not statuses:
            return 0
        statement = text(
            """
            UPDATE recommendation_training_runs
               SET payload_json = NULL
             WHERE payload_json IS NOT NULL
               AND finished_at IS NOT NULL
               AND finished_at < :completed_before
               AND status IN :statuses
            """
        ).bindparams(bindparam("statuses", expanding=True))
        with self.engine.begin() as connection:
            result = connection.execute(
                statement,
                {
                    "completed_before": completed_before,
                    "statuses": tuple(statuses),
                },
            )
        return result.rowcount or 0

    def finish_training_run(
        self,
        run_id: UUID,
        status: str,
        activated_model_version: str | None,
        event_count: int,
        principal_count: int,
        course_count: int,
        pair_count: int,
        quality_score: float,
        error_class: str | None,
        error_message: str | None,
        finished_at: datetime,
    ) -> TrainingRunRecord:
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    UPDATE recommendation_training_runs
                       SET status = :status,
                           activated_model_version = :activated_model_version,
                           event_count = :event_count,
                           principal_count = :principal_count,
                           course_count = :course_count,
                           pair_count = :pair_count,
                           quality_score = :quality_score,
                           error_class = :error_class,
                           error_message = :error_message,
                           finished_at = :finished_at,
                           locked_by = NULL,
                           locked_at = NULL
                     WHERE id = :id
                       AND status <> 'CANCELLED'
                     RETURNING *
                    """
                ),
                {
                    "id": run_id,
                    "status": status,
                    "activated_model_version": activated_model_version,
                    "event_count": event_count,
                    "principal_count": principal_count,
                    "course_count": course_count,
                    "pair_count": pair_count,
                    "quality_score": quality_score,
                    "error_class": error_class,
                    "error_message": truncate(error_message, 500),
                    "finished_at": finished_at,
                },
            ).mappings().first()
            if row is None:
                row = connection.execute(
                    text("SELECT * FROM recommendation_training_runs WHERE id = :id"),
                    {"id": run_id},
                ).mappings().one()
        return to_training_run(row)

    def activate_model(
        self,
        run_id: UUID,
        model_version: str,
        algorithm: str,
        event_count: int,
        principal_count: int,
        course_count: int,
        pair_count: int,
        quality_score: float,
        params_json: str,
        training_hash: str,
        created_by: str,
        trained_at: datetime,
        scores: list[ScoredRecommendation],
    ) -> bool:
        with self.engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:namespace, :lock_key)"),
                {
                    "namespace": self.ACTIVE_MODEL_LOCK_NAMESPACE,
                    "lock_key": self.ACTIVE_MODEL_LOCK_KEY,
                },
            )
            training_status = connection.execute(
                text(
                    """
                    SELECT status
                    FROM recommendation_training_runs
                    WHERE id = :id
                    FOR UPDATE
                    """
                ),
                {"id": run_id},
            ).scalar_one()
            if training_status == "CANCELLED":
                return False
            previous_active = connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM recommendation_model_versions
                    WHERE status = 'ACTIVE'
                    ORDER BY activated_at DESC
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            connection.execute(
                text(
                    """
                    UPDATE recommendation_model_versions
                       SET status = 'SUPERSEDED',
                           superseded_at = :trained_at
                     WHERE status = 'ACTIVE'
                    """
                ),
                {"trained_at": trained_at},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_model_versions (
                        id, model_version, training_run_id, algorithm, status, event_count,
                        principal_count, course_count, pair_count, quality_score, params_json,
                        training_hash, created_by, trained_at, activated_at
                    )
                    VALUES (
                        :id, :model_version, :training_run_id, :algorithm, 'ACTIVE', :event_count,
                        :principal_count, :course_count, :pair_count, :quality_score, :params_json,
                        :training_hash, :created_by, :trained_at, :trained_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "model_version": model_version,
                    "training_run_id": run_id,
                    "algorithm": algorithm,
                    "event_count": event_count,
                    "principal_count": principal_count,
                    "course_count": course_count,
                    "pair_count": pair_count,
                    "quality_score": quality_score,
                    "params_json": params_json,
                    "training_hash": training_hash,
                    "created_by": created_by,
                    "trained_at": trained_at,
                },
            )
            if scores:
                connection.execute(
                    text(
                        """
                        INSERT INTO recommendation_related_course_scores (
                            id, model_version, course_id, related_course_id, rank, score,
                            similarity, support_count, reason_code, generated_at
                        )
                        VALUES (
                            :id, :model_version, :course_id, :related_course_id, :rank, :score,
                            :similarity, :support_count, :reason_code, :generated_at
                        )
                        """
                    ),
                    [
                        {
                            "id": uuid4(),
                            "model_version": model_version,
                            "course_id": score.course_id,
                            "related_course_id": score.related_course_id,
                            "rank": score.rank,
                            "score": score.score,
                            "similarity": score.similarity,
                            "support_count": score.support_count,
                            "reason_code": score.reason_code,
                            "generated_at": trained_at,
                        }
                        for score in scores
                    ],
                )
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_model_ops_audit (
                        id, action, model_version, previous_active_model_version,
                        actor_id, reason, evidence_json, created_at
                    )
                    VALUES (
                        :id, 'TRAINING_ACTIVATED', :model_version, :previous_active_model_version,
                        :actor_id, :reason, :evidence_json, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "model_version": model_version,
                    "previous_active_model_version": previous_active,
                    "actor_id": created_by,
                    "reason": "Training run activated automatically after quality gates",
                    "evidence_json": training_activation_evidence(run_id, training_hash),
                    "created_at": trained_at,
                },
            )
        return True

    def register_candidate_model(
        self,
        run_id: UUID,
        model_version: str,
        algorithm: str,
        event_count: int,
        principal_count: int,
        course_count: int,
        pair_count: int,
        quality_score: float,
        params_json: str,
        training_hash: str,
        created_by: str,
        trained_at: datetime,
        scores: list[ScoredRecommendation],
    ) -> bool:
        with self.engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:namespace, :lock_key)"),
                {
                    "namespace": self.ACTIVE_MODEL_LOCK_NAMESPACE,
                    "lock_key": self.ACTIVE_MODEL_LOCK_KEY,
                },
            )
            training_status = connection.execute(
                text(
                    """
                    SELECT status
                    FROM recommendation_training_runs
                    WHERE id = :id
                    FOR UPDATE
                    """
                ),
                {"id": run_id},
            ).scalar_one()
            if training_status == "CANCELLED":
                return False
            previous_active = connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM recommendation_model_versions
                    WHERE status = 'ACTIVE'
                    ORDER BY activated_at DESC
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_model_versions (
                        id, model_version, training_run_id, algorithm, status, event_count,
                        principal_count, course_count, pair_count, quality_score, params_json,
                        training_hash, created_by, trained_at, activated_at
                    )
                    VALUES (
                        :id, :model_version, :training_run_id, :algorithm, 'CANDIDATE',
                        :event_count,
                        :principal_count, :course_count, :pair_count, :quality_score, :params_json,
                        :training_hash, :created_by, :trained_at, NULL
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "model_version": model_version,
                    "training_run_id": run_id,
                    "algorithm": algorithm,
                    "event_count": event_count,
                    "principal_count": principal_count,
                    "course_count": course_count,
                    "pair_count": pair_count,
                    "quality_score": quality_score,
                    "params_json": params_json,
                    "training_hash": training_hash,
                    "created_by": created_by,
                    "trained_at": trained_at,
                },
            )
            if scores:
                connection.execute(
                    text(
                        """
                        INSERT INTO recommendation_related_course_scores (
                            id, model_version, course_id, related_course_id, rank, score,
                            similarity, support_count, reason_code, generated_at
                        )
                        VALUES (
                            :id, :model_version, :course_id, :related_course_id, :rank, :score,
                            :similarity, :support_count, :reason_code, :generated_at
                        )
                        """
                    ),
                    [
                        {
                            "id": uuid4(),
                            "model_version": model_version,
                            "course_id": score.course_id,
                            "related_course_id": score.related_course_id,
                            "rank": score.rank,
                            "score": score.score,
                            "similarity": score.similarity,
                            "support_count": score.support_count,
                            "reason_code": score.reason_code,
                            "generated_at": trained_at,
                        }
                        for score in scores
                    ],
                )
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_model_ops_audit (
                        id, action, model_version, previous_active_model_version,
                        actor_id, reason, evidence_json, created_at
                    )
                    VALUES (
                        :id, 'TRAINING_CANDIDATE_REGISTERED', :model_version,
                        :previous_active_model_version, :actor_id, :reason,
                        :evidence_json, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "model_version": model_version,
                    "previous_active_model_version": previous_active,
                    "actor_id": created_by,
                    "reason": "Training run registered a candidate model for approval",
                    "evidence_json": training_activation_evidence(run_id, training_hash),
                    "created_at": trained_at,
                },
            )
        return True

    def reactivate_model_version(
        self,
        model_version: str,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        activated_at: datetime,
    ) -> ModelVersionRecord | None:
        with self.engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:namespace, :lock_key)"),
                {
                    "namespace": self.ACTIVE_MODEL_LOCK_NAMESPACE,
                    "lock_key": self.ACTIVE_MODEL_LOCK_KEY,
                },
            )
            target = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_versions
                    WHERE model_version = :model_version
                    """
                ),
                {"model_version": model_version},
            ).mappings().first()
            if target is None:
                return None
            previous_active = connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM recommendation_model_versions
                    WHERE status = 'ACTIVE'
                    ORDER BY activated_at DESC
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            if previous_active != model_version:
                connection.execute(
                    text(
                        """
                        UPDATE recommendation_model_versions
                           SET status = 'SUPERSEDED',
                               superseded_at = :activated_at
                         WHERE status = 'ACTIVE'
                        """
                    ),
                    {"activated_at": activated_at},
                )
                connection.execute(
                    text(
                        """
                        UPDATE recommendation_model_versions
                           SET status = 'ACTIVE',
                               activated_at = :activated_at,
                               superseded_at = NULL
                         WHERE model_version = :model_version
                        """
                    ),
                    {"model_version": model_version, "activated_at": activated_at},
                )
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_model_ops_audit (
                        id, action, model_version, previous_active_model_version,
                        actor_id, reason, evidence_json, created_at
                    )
                    VALUES (
                        :id, 'MODEL_REACTIVATED', :model_version, :previous_active_model_version,
                        :actor_id, :reason, :evidence_json, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "model_version": model_version,
                    "previous_active_model_version": previous_active,
                    "actor_id": actor_id,
                    "reason": truncate(reason, 500),
                    "evidence_json": evidence_json,
                    "created_at": activated_at,
                },
            )
            row = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_versions
                    WHERE model_version = :model_version
                    """
                ),
                {"model_version": model_version},
            ).mappings().one()
        return to_model_version(row)

    def create_model_activation_approval(
        self,
        approval_id: UUID,
        model_version: str,
        requested_by: str,
        request_reason: str,
        request_evidence_json: str | None,
        created_at: datetime,
    ) -> ModelActivationApprovalRecord | None:
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(:namespace, :lock_key)"),
                    {
                        "namespace": self.ACTIVE_MODEL_LOCK_NAMESPACE,
                        "lock_key": self.ACTIVE_MODEL_LOCK_KEY,
                    },
                )
                model_exists = connection.execute(
                    text(
                        """
                        SELECT 1
                        FROM recommendation_model_versions
                        WHERE model_version = :model_version
                        """
                    ),
                    {"model_version": model_version},
                ).scalar_one_or_none()
                if model_exists is None:
                    return None
                pending_exists = connection.execute(
                    text(
                        """
                        SELECT 1
                        FROM recommendation_model_activation_approvals
                        WHERE model_version = :model_version
                          AND status = 'PENDING'
                        LIMIT 1
                        """
                    ),
                    {"model_version": model_version},
                ).scalar_one_or_none()
                if pending_exists is not None:
                    raise PendingModelActivationApprovalError
                row = connection.execute(
                    text(
                        """
                        INSERT INTO recommendation_model_activation_approvals (
                            id, model_version, status, requested_by, request_reason,
                            request_evidence_json, created_at
                        )
                        VALUES (
                            :id, :model_version, 'PENDING', :requested_by, :request_reason,
                            :request_evidence_json, :created_at
                        )
                        RETURNING *
                        """
                    ),
                    {
                        "id": approval_id,
                        "model_version": model_version,
                        "requested_by": requested_by,
                        "request_reason": truncate(request_reason, 500),
                        "request_evidence_json": request_evidence_json,
                        "created_at": created_at,
                    },
                ).mappings().one()
        except IntegrityError as exc:
            raise PendingModelActivationApprovalError from exc
        return to_model_activation_approval(row)

    def approve_model_activation_approval(
        self,
        approval_id: UUID,
        reviewer_id: str,
        review_reason: str,
        review_evidence_json: str | None,
        reviewed_at: datetime,
    ) -> ModelVersionRecord | None:
        with self.engine.begin() as connection:
            approval = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_activation_approvals
                    WHERE id = :id
                    FOR UPDATE
                    """
                ),
                {"id": approval_id},
            ).mappings().first()
            if approval is None:
                return None
            if approval["status"] != "PENDING" or approval["requested_by"] == reviewer_id:
                return None
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:namespace, :lock_key)"),
                {
                    "namespace": self.ACTIVE_MODEL_LOCK_NAMESPACE,
                    "lock_key": self.ACTIVE_MODEL_LOCK_KEY,
                },
            )
            previous_active = connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM recommendation_model_versions
                    WHERE status = 'ACTIVE'
                    ORDER BY activated_at DESC
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            model_version = str(approval["model_version"])
            target_status = connection.execute(
                text(
                    """
                    SELECT status
                    FROM recommendation_model_versions
                    WHERE model_version = :model_version
                    FOR UPDATE
                    """
                ),
                {"model_version": model_version},
            ).scalar_one_or_none()
            if target_status not in {"CANDIDATE", "SUPERSEDED"}:
                return None
            if previous_active != model_version:
                connection.execute(
                    text(
                        """
                        UPDATE recommendation_model_versions
                           SET status = 'SUPERSEDED',
                               superseded_at = :reviewed_at
                         WHERE status = 'ACTIVE'
                        """
                    ),
                    {"reviewed_at": reviewed_at},
                )
                connection.execute(
                    text(
                        """
                        UPDATE recommendation_model_versions
                           SET status = 'ACTIVE',
                               activated_at = :reviewed_at,
                               superseded_at = NULL
                         WHERE model_version = :model_version
                        """
                    ),
                    {"model_version": model_version, "reviewed_at": reviewed_at},
                )
            if target_status == "CANDIDATE":
                connection.execute(
                    text(
                        """
                        UPDATE recommendation_training_runs
                           SET status = 'ACTIVE',
                               error_class = NULL,
                               error_message = NULL,
                               finished_at = COALESCE(finished_at, :reviewed_at)
                         WHERE activated_model_version = :model_version
                           AND status = 'PENDING_ACTIVATION'
                        """
                    ),
                    {"model_version": model_version, "reviewed_at": reviewed_at},
                )
            audit_action = (
                "TRAINING_ACTIVATED"
                if target_status == "CANDIDATE"
                else "MODEL_REACTIVATED"
            )
            connection.execute(
                text(
                    """
                    UPDATE recommendation_model_activation_approvals
                       SET status = 'EXECUTED',
                           reviewed_by = :reviewer_id,
                           review_reason = :review_reason,
                           review_evidence_json = :review_evidence_json,
                           previous_active_model_version = :previous_active_model_version,
                           reviewed_at = :reviewed_at,
                           executed_at = :reviewed_at
                     WHERE id = :id
                    """
                ),
                {
                    "id": approval_id,
                    "reviewer_id": reviewer_id,
                    "review_reason": truncate(review_reason, 500),
                    "review_evidence_json": review_evidence_json,
                    "previous_active_model_version": previous_active,
                    "reviewed_at": reviewed_at,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_model_ops_audit (
                        id, action, model_version, previous_active_model_version,
                        actor_id, reason, evidence_json, created_at
                    )
                    VALUES (
                        :id, :action, :model_version, :previous_active_model_version,
                        :actor_id, :reason, :evidence_json, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "action": audit_action,
                    "model_version": model_version,
                    "previous_active_model_version": previous_active,
                    "actor_id": reviewer_id,
                    "reason": truncate(str(approval["request_reason"]), 500),
                    "evidence_json": model_activation_approval_evidence(
                        approval_id,
                        str(approval["requested_by"]),
                        review_reason,
                        approval["request_evidence_json"],
                        review_evidence_json,
                    ),
                    "created_at": reviewed_at,
                },
            )
            row = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_versions
                    WHERE model_version = :model_version
                    """
                ),
                {"model_version": model_version},
            ).mappings().one()
        return to_model_version(row)

    def reject_model_activation_approval(
        self,
        approval_id: UUID,
        reviewer_id: str,
        review_reason: str,
        review_evidence_json: str | None,
        reviewed_at: datetime,
    ) -> ModelActivationApprovalRecord | None:
        with self.engine.begin() as connection:
            approval = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_model_activation_approvals
                    WHERE id = :id
                    FOR UPDATE
                    """
                ),
                {"id": approval_id},
            ).mappings().first()
            if approval is None:
                return None
            if approval["status"] != "PENDING" or approval["requested_by"] == reviewer_id:
                return None
            model_version = str(approval["model_version"])
            target_status = connection.execute(
                text(
                    """
                    SELECT status
                    FROM recommendation_model_versions
                    WHERE model_version = :model_version
                    FOR UPDATE
                    """
                ),
                {"model_version": model_version},
            ).scalar_one_or_none()
            if target_status is None:
                return None
            previous_active = connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM recommendation_model_versions
                    WHERE status = 'ACTIVE'
                    ORDER BY activated_at DESC
                    LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            if target_status == "CANDIDATE":
                connection.execute(
                    text(
                        """
                        UPDATE recommendation_model_versions
                           SET status = 'REJECTED'
                         WHERE model_version = :model_version
                           AND status = 'CANDIDATE'
                        """
                    ),
                    {"model_version": model_version},
                )
                connection.execute(
                    text(
                        """
                        UPDATE recommendation_training_runs
                           SET status = 'ACTIVATION_REJECTED',
                               error_class = 'ACTIVATION_REJECTED',
                               error_message = :review_reason,
                               finished_at = :reviewed_at
                         WHERE activated_model_version = :model_version
                           AND status = 'PENDING_ACTIVATION'
                        """
                    ),
                    {
                        "model_version": model_version,
                        "review_reason": truncate(review_reason, 500),
                        "reviewed_at": reviewed_at,
                    },
                )
            row = connection.execute(
                text(
                    """
                    UPDATE recommendation_model_activation_approvals approval
                       SET status = 'REJECTED',
                           reviewed_by = :reviewer_id,
                           review_reason = :review_reason,
                           review_evidence_json = :review_evidence_json,
                           previous_active_model_version = :previous_active_model_version,
                           reviewed_at = :reviewed_at
                     WHERE approval.id = :id
                     RETURNING approval.*
                    """
                ),
                {
                    "id": approval_id,
                    "reviewer_id": reviewer_id,
                    "review_reason": truncate(review_reason, 500),
                    "review_evidence_json": review_evidence_json,
                    "previous_active_model_version": previous_active,
                    "reviewed_at": reviewed_at,
                },
            ).mappings().first()
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_model_ops_audit (
                        id, action, model_version, previous_active_model_version,
                        actor_id, reason, evidence_json, created_at
                    )
                    VALUES (
                        :id, 'MODEL_ACTIVATION_REJECTED', :model_version,
                        :previous_active_model_version, :actor_id, :reason,
                        :evidence_json, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "model_version": model_version,
                    "previous_active_model_version": previous_active,
                    "actor_id": reviewer_id,
                    "reason": truncate(review_reason, 500),
                    "evidence_json": model_activation_approval_evidence(
                        approval_id,
                        str(approval["requested_by"]),
                        review_reason,
                        approval["request_evidence_json"],
                        review_evidence_json,
                    ),
                    "created_at": reviewed_at,
                },
            )
        return to_model_activation_approval(row) if row else None

    def cancel_training_run(
        self,
        run_id: UUID,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        cancelled_at: datetime,
    ) -> TrainingRunRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    WITH target AS (
                        SELECT id, status AS previous_status
                        FROM recommendation_training_runs
                        WHERE id = :id
                          AND status IN ('QUEUED', 'RUNNING', 'STARTED')
                        FOR UPDATE
                    )
                    UPDATE recommendation_training_runs run
                       SET status = 'CANCELLED',
                           error_class = 'CANCELLED_BY_OPERATOR',
                           error_message = :reason,
                           finished_at = :cancelled_at,
                           locked_by = NULL,
                           locked_at = NULL
                      FROM target
                     WHERE run.id = target.id
                     RETURNING run.*, target.previous_status
                    """
                ),
                {"id": run_id, "reason": truncate(reason, 500), "cancelled_at": cancelled_at},
            ).mappings().first()
            if row is None:
                return None
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_training_ops_audit (
                        id, action, training_run_id, previous_status, new_status,
                        actor_id, reason, evidence_json, created_at
                    )
                    VALUES (
                        :id, 'TRAINING_CANCELLED', :training_run_id, :previous_status,
                        'CANCELLED', :actor_id, :reason, :evidence_json, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "training_run_id": run_id,
                    "previous_status": row["previous_status"],
                    "actor_id": actor_id,
                    "reason": truncate(reason, 500),
                    "evidence_json": evidence_json,
                    "created_at": cancelled_at,
                },
            )
        return to_training_run(row)

    def requeue_training_run(
        self,
        run_id: UUID,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        requeued_at: datetime,
    ) -> TrainingRunRecord | None:
        with self.engine.begin() as connection:
            existing = connection.execute(
                text(
                    """
                    SELECT *
                    FROM recommendation_training_runs
                    WHERE id = :id
                    FOR UPDATE
                    """
                ),
                {"id": run_id},
            ).mappings().first()
            if existing is None:
                return None
            if existing["status"] not in {"FAILED", "CANCELLED"}:
                return None
            if existing["payload_json"] is None or existing["activated_model_version"] is not None:
                return None
            row = connection.execute(
                text(
                    """
                    UPDATE recommendation_training_runs
                       SET status = 'QUEUED',
                           error_class = NULL,
                           error_message = NULL,
                           finished_at = NULL,
                           locked_by = NULL,
                           locked_at = NULL,
                           available_at = :requeued_at
                     WHERE id = :id
                     RETURNING *
                    """
                ),
                {"id": run_id, "requeued_at": requeued_at},
            ).mappings().one()
            connection.execute(
                text(
                    """
                    INSERT INTO recommendation_training_ops_audit (
                        id, action, training_run_id, previous_status, new_status,
                        actor_id, reason, evidence_json, created_at
                    )
                    VALUES (
                        :id, 'TRAINING_REQUEUED', :training_run_id, :previous_status,
                        'QUEUED', :actor_id, :reason, :evidence_json, :created_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "training_run_id": run_id,
                    "previous_status": existing["status"],
                    "actor_id": actor_id,
                    "reason": truncate(reason, 500),
                    "evidence_json": evidence_json,
                    "created_at": requeued_at,
                },
            )
        return to_training_run(row)


def to_training_run(row: RowMapping) -> TrainingRunRecord:
    return TrainingRunRecord(
        id=row["id"],
        requested_model_version=row["requested_model_version"],
        activated_model_version=row["activated_model_version"],
        algorithm=row["algorithm"],
        status=row["status"],
        request_hash=row["request_hash"],
        event_count=row["event_count"],
        principal_count=row["principal_count"],
        course_count=row["course_count"],
        pair_count=row["pair_count"],
        quality_score=float(row["quality_score"]),
        min_support=row["min_support"],
        max_related_per_course=row["max_related_per_course"],
        error_class=row["error_class"],
        error_message=row["error_message"],
        requested_by=row["requested_by"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def to_model_version(row: RowMapping) -> ModelVersionRecord:
    return ModelVersionRecord(
        model_version=row["model_version"],
        algorithm=row["algorithm"],
        status=row["status"],
        event_count=row["event_count"],
        principal_count=row["principal_count"],
        course_count=row["course_count"],
        pair_count=row["pair_count"],
        quality_score=float(row["quality_score"]),
        trained_at=row["trained_at"],
        activated_at=row["activated_at"],
        training_run_id=row["training_run_id"],
    )


def to_model_ops_audit(row: RowMapping) -> ModelOpsAuditRecord:
    return ModelOpsAuditRecord(
        id=row["id"],
        action=row["action"],
        model_version=row["model_version"],
        previous_active_model_version=row["previous_active_model_version"],
        actor_id=row["actor_id"],
        reason=row["reason"],
        evidence_json=row["evidence_json"],
        created_at=row["created_at"],
    )


def to_model_activation_approval(row: RowMapping) -> ModelActivationApprovalRecord:
    return ModelActivationApprovalRecord(
        id=row["id"],
        model_version=row["model_version"],
        status=row["status"],
        requested_by=row["requested_by"],
        request_reason=row["request_reason"],
        request_evidence_json=row["request_evidence_json"],
        reviewed_by=row["reviewed_by"],
        review_reason=row["review_reason"],
        review_evidence_json=row["review_evidence_json"],
        previous_active_model_version=row["previous_active_model_version"],
        created_at=row["created_at"],
        reviewed_at=row["reviewed_at"],
        executed_at=row["executed_at"],
    )


def to_training_ops_audit(row: RowMapping) -> TrainingOpsAuditRecord:
    return TrainingOpsAuditRecord(
        id=row["id"],
        action=row["action"],
        training_run_id=row["training_run_id"],
        previous_status=row["previous_status"],
        new_status=row["new_status"],
        actor_id=row["actor_id"],
        reason=row["reason"],
        evidence_json=row["evidence_json"],
        created_at=row["created_at"],
    )


def to_score(row: RowMapping) -> ScoredRecommendation:
    return ScoredRecommendation(
        course_id=row["course_id"],
        related_course_id=row["related_course_id"],
        rank=row["rank"],
        score=float(row["score"]),
        similarity=float(row["similarity"]),
        support_count=row["support_count"],
        reason_code=row["reason_code"],
        model_version=row["model_version"],
    )


def metric_int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(str(value))


def metric_float(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    return float(str(value))


def truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


def normalize_status(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip().upper()[:40]


def training_activation_evidence(run_id: UUID, training_hash: str) -> str:
    return '{"trainingRunId":"' + str(run_id) + '","trainingHash":"' + training_hash + '"}'


def model_activation_approval_evidence(
    approval_id: UUID,
    requested_by: str,
    review_reason: str,
    request_evidence_json: object,
    review_evidence_json: str | None,
) -> str:
    return json.dumps(
        {
            "approvalId": str(approval_id),
            "requestedBy": requested_by,
            "reviewReason": review_reason,
            "requestEvidence": parse_json_or_raw(request_evidence_json),
            "reviewEvidence": parse_json_or_raw(review_evidence_json),
        },
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )


def parse_json_or_raw(value: object) -> object | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    try:
        return cast(object, json.loads(value))
    except json.JSONDecodeError:
        return value
