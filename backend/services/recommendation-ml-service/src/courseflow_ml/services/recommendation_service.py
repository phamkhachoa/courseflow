from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from courseflow_ml.domain.recommendation import (
    ModelActivationApprovalRecord,
    ModelOpsAuditRecord,
    ModelVersionRecord,
    ScoredRecommendation,
    TrainingInteraction,
    TrainingOpsAuditRecord,
    TrainingResult,
    TrainingRunRecord,
)
from courseflow_ml.repositories.recommendation_repository import (
    PendingModelActivationApprovalError,
    RecommendationRepository,
)
from courseflow_ml.training.implicit_cf import ALGORITHM, ImplicitCfConfig, ImplicitItemCfTrainer


class RecommendationConflictError(RuntimeError):
    pass


class RecommendationNotFoundError(RuntimeError):
    pass


class RecommendationBadRequestError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedTrainingRequest:
    requested_model_version: str | None
    min_support: int
    max_related_per_course: int
    request_hash: str
    legacy_request_hash: str
    interactions: list[TrainingInteraction]


PAYLOAD_SCRUB_ELIGIBLE_STATUSES = (
    "ACTIVE",
    "PENDING_ACTIVATION",
    "ACTIVATION_REJECTED",
    "INSUFFICIENT_DATA",
    "QUALITY_GATE_FAILED",
    "FAILED",
    "CANCELLED",
)
TRAINING_RUN_STATUSES = frozenset(
    {
        "QUEUED",
        "RUNNING",
        "STARTED",
        "ACTIVE",
        "PENDING_ACTIVATION",
        "ACTIVATION_REJECTED",
        "INSUFFICIENT_DATA",
        "QUALITY_GATE_FAILED",
        "FAILED",
        "CANCELLED",
    }
)
MODEL_VERSION_STATUSES = frozenset({"CANDIDATE", "ACTIVE", "SUPERSEDED", "REJECTED"})
MODEL_ACTIVATION_APPROVAL_STATUSES = frozenset({"PENDING", "REJECTED", "EXECUTED"})
SUPPORTED_TRAINING_EVENT_TYPES = frozenset({"ENROLLMENT", "CLICK", "IMPRESSION"})
MAX_AUDIT_EVIDENCE_BYTES = 2000
MAX_AUDIT_EVIDENCE_DEPTH = 8
MAX_AUDIT_EVIDENCE_COLLECTION_SIZE = 100
MAX_AUDIT_EVIDENCE_STRING_LENGTH = 1000
SENSITIVE_EVIDENCE_KEY_FRAGMENTS = (
    "apikey",
    "authorization",
    "clientsecret",
    "credential",
    "password",
    "privatekey",
    "secret",
    "token",
)
JWT_LIKE_VALUE = re.compile(
    r"^[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}$"
)
MODEL_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
LOCAL_PRINCIPAL_HASH_SECRET = (
    "courseflow-local-recommendation-ml-principal-hash-secret-change-me-32"
)
MIN_PRINCIPAL_HASH_SECRET_BYTES = 32


class RecommendationMlService:
    def __init__(
        self,
        repository: RecommendationRepository,
        default_max_related_per_course: int = 24,
        max_related_per_course: int = 100,
        default_min_support: int = 1,
        max_training_events: int = 250_000,
        training_job_lease_seconds: int = 1800,
        training_job_max_attempts: int = 3,
        training_job_requeue_delay_seconds: int = 60,
        min_activation_event_count: int = 10,
        min_activation_principal_count: int = 3,
        min_activation_course_count: int = 2,
        min_activation_pair_count: int = 1,
        min_activation_quality_score: float = 0.01,
        auto_activate_trained_models: bool = True,
        training_payload_retention_days: int = 30,
        principal_hash_secret: str = LOCAL_PRINCIPAL_HASH_SECRET,
    ) -> None:
        self.repository = repository
        self.default_max_related_per_course = default_max_related_per_course
        self.max_related_per_course = max_related_per_course
        self.default_min_support = default_min_support
        self.max_training_events = max_training_events
        self.training_job_lease_seconds = max(60, training_job_lease_seconds)
        self.training_job_max_attempts = max(1, training_job_max_attempts)
        self.training_job_requeue_delay_seconds = max(0, training_job_requeue_delay_seconds)
        self.min_activation_event_count = max(0, min_activation_event_count)
        self.min_activation_principal_count = max(0, min_activation_principal_count)
        self.min_activation_course_count = max(0, min_activation_course_count)
        self.min_activation_pair_count = max(0, min_activation_pair_count)
        self.min_activation_quality_score = max(0.0, min(1.0, min_activation_quality_score))
        self.auto_activate_trained_models = auto_activate_trained_models
        self.training_payload_retention_days = max(1, min(training_payload_retention_days, 3650))
        if len(principal_hash_secret.encode("utf-8")) < MIN_PRINCIPAL_HASH_SECRET_BYTES:
            raise RecommendationBadRequestError(
                "Recommendation ML principal hash secret must be at least "
                f"{MIN_PRINCIPAL_HASH_SECRET_BYTES} bytes"
            )
        self.principal_hash_secret = principal_hash_secret

    def train_related_courses(
        self,
        training_run_id: UUID,
        requested_model_version: str | None,
        min_support: int | None,
        max_related_per_course: int | None,
        interactions: list[TrainingInteraction],
        actor_id: str,
    ) -> dict[str, object]:
        prepared = self.prepare_training_request(
            requested_model_version,
            min_support,
            max_related_per_course,
            interactions,
        )
        existing = self.repository.training_run(training_run_id)
        if existing is not None:
            return self._duplicate_training_run(existing, prepared)

        self.assert_model_version_available(prepared.requested_model_version)

        started_at = now_utc()
        self.repository.create_training_run(
            training_run_id,
            prepared.requested_model_version,
            ALGORITHM,
            prepared.request_hash,
            prepared.min_support,
            prepared.max_related_per_course,
            actor_id,
            started_at,
        )
        return self._execute_training_run(training_run_id, prepared, actor_id)

    def enqueue_related_courses(
        self,
        training_run_id: UUID,
        requested_model_version: str | None,
        min_support: int | None,
        max_related_per_course: int | None,
        interactions: list[TrainingInteraction],
        actor_id: str,
    ) -> dict[str, object]:
        prepared = self.prepare_training_request(
            requested_model_version,
            min_support,
            max_related_per_course,
            interactions,
        )
        existing = self.repository.training_run(training_run_id)
        if existing is not None:
            return self._duplicate_training_run(existing, prepared)

        self.assert_model_version_available(prepared.requested_model_version)

        run = self.repository.enqueue_training_run(
            training_run_id,
            prepared.requested_model_version,
            ALGORITHM,
            prepared.request_hash,
            prepared.min_support,
            prepared.max_related_per_course,
            actor_id,
            training_payload_json(prepared, self.principal_hash_secret),
            now_utc(),
        )
        return response_from_run(run, [])

    def training_run(self, training_run_id: UUID) -> dict[str, object]:
        run = self.repository.training_run(training_run_id)
        if run is None:
            raise RecommendationNotFoundError("Recommendation ML training run was not found")
        rows = (
            self.repository.scores_for_model(run.activated_model_version)
            if run.activated_model_version
            else []
        )
        return response_from_run(run, rows)

    def list_training_runs(self, status: str | None, limit: int) -> list[dict[str, object]]:
        return [
            training_run_summary_to_dict(run)
            for run in self.repository.list_training_runs(
                normalize_status(status, TRAINING_RUN_STATUSES, "training run"),
                limit,
            )
        ]

    def list_model_versions(self, status: str | None, limit: int) -> list[dict[str, object]]:
        return [
            model_to_dict(model)
            for model in self.repository.list_model_versions(
                normalize_status(status, MODEL_VERSION_STATUSES, "model version"),
                limit,
            )
        ]

    def list_model_ops_audit(self, limit: int) -> list[dict[str, object]]:
        return [audit_to_dict(row) for row in self.repository.list_model_ops_audit(limit)]

    def list_model_activation_approvals(
        self,
        status: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        return [
            model_activation_approval_to_dict(row)
            for row in self.repository.list_model_activation_approvals(
                normalize_status(
                    status,
                    MODEL_ACTIVATION_APPROVAL_STATUSES,
                    "model activation approval",
                ),
                limit,
            )
        ]

    def list_training_ops_audit(self, limit: int) -> list[dict[str, object]]:
        return [
            training_ops_audit_to_dict(row)
            for row in self.repository.list_training_ops_audit(limit)
        ]

    def cancel_training_run(
        self,
        training_run_id: UUID,
        reason: str,
        evidence: dict[str, object] | None,
        actor_id: str,
    ) -> dict[str, object]:
        self.assert_training_run_exists(training_run_id)
        normalized_reason = normalize_required_reason(reason)
        run = self.repository.cancel_training_run(
            training_run_id,
            actor_id,
            normalized_reason,
            evidence_to_json(evidence),
            now_utc(),
        )
        if run is None:
            raise RecommendationConflictError(
                "Recommendation ML training run cannot be cancelled from its current state"
            )
        return training_run_summary_to_dict(run)

    def requeue_training_run(
        self,
        training_run_id: UUID,
        reason: str,
        evidence: dict[str, object] | None,
        actor_id: str,
    ) -> dict[str, object]:
        self.assert_training_run_exists(training_run_id)
        normalized_reason = normalize_required_reason(reason)
        run = self.repository.requeue_training_run(
            training_run_id,
            actor_id,
            normalized_reason,
            evidence_to_json(evidence),
            now_utc(),
        )
        if run is None:
            raise RecommendationConflictError(
                "Recommendation ML training run cannot be requeued from its current state"
            )
        return training_run_summary_to_dict(run)

    def reactivate_model_version(
        self,
        model_version: str,
        reason: str,
        evidence: dict[str, object] | None,
        actor_id: str,
    ) -> dict[str, object]:
        del reason, evidence, actor_id
        normalized_model_version = normalize_model_version(model_version)
        if normalized_model_version is None:
            raise RecommendationBadRequestError("modelVersion is required")
        if self.repository.model_version(normalized_model_version) is None:
            raise RecommendationNotFoundError("Recommendation ML model version was not found")
        raise RecommendationConflictError(
            "Direct model reactivation is disabled; create and approve a model "
            "activation request"
        )

    def request_model_activation(
        self,
        model_version: str,
        reason: str,
        evidence: dict[str, object] | None,
        actor_id: str,
    ) -> dict[str, object]:
        normalized_model_version = normalize_model_version(model_version)
        if normalized_model_version is None:
            raise RecommendationBadRequestError("modelVersion is required")
        normalized_reason = normalize_required_reason(reason)
        target = self.repository.model_version(normalized_model_version)
        if target is None:
            raise RecommendationNotFoundError("Recommendation ML model version was not found")
        if target.status == "REJECTED":
            raise RecommendationConflictError("Recommendation ML model version was rejected")
        active = self.repository.active_model()
        if active is not None and active.model_version == normalized_model_version:
            raise RecommendationConflictError("Recommendation ML model version is already active")
        if self.repository.pending_model_activation_approval(normalized_model_version) is not None:
            raise RecommendationConflictError(
                "Recommendation ML model activation request is already pending"
            )
        try:
            approval = self.repository.create_model_activation_approval(
                uuid4(),
                normalized_model_version,
                actor_id,
                normalized_reason,
                evidence_to_json(evidence),
                now_utc(),
            )
        except PendingModelActivationApprovalError as exc:
            raise RecommendationConflictError(
                "Recommendation ML model activation request is already pending"
            ) from exc
        if approval is None:
            raise RecommendationNotFoundError("Recommendation ML model version was not found")
        return model_activation_approval_to_dict(approval)

    def approve_model_activation(
        self,
        approval_id: UUID,
        reason: str,
        evidence: dict[str, object] | None,
        actor_id: str,
    ) -> dict[str, object]:
        approval = self.assert_model_activation_approval_reviewable(approval_id, actor_id)
        model = self.repository.approve_model_activation_approval(
            approval.id,
            actor_id,
            normalize_required_reason(reason),
            evidence_to_json(evidence),
            now_utc(),
        )
        if model is None:
            raise RecommendationConflictError(
                "Recommendation ML model activation request cannot be approved"
            )
        return model_to_dict(model)

    def reject_model_activation(
        self,
        approval_id: UUID,
        reason: str,
        evidence: dict[str, object] | None,
        actor_id: str,
    ) -> dict[str, object]:
        approval = self.assert_model_activation_approval_reviewable(approval_id, actor_id)
        rejected = self.repository.reject_model_activation_approval(
            approval.id,
            actor_id,
            normalize_required_reason(reason),
            evidence_to_json(evidence),
            now_utc(),
        )
        if rejected is None:
            raise RecommendationConflictError(
                "Recommendation ML model activation request cannot be rejected"
            )
        return model_activation_approval_to_dict(rejected)

    def process_next_training_job(self, worker_id: str) -> dict[str, object] | None:
        claimed_at = now_utc()
        self.recover_stale_training_jobs(claimed_at)
        job = self.repository.claim_next_training_job(worker_id, claimed_at)
        if job is None:
            return None
        try:
            interactions = interactions_from_payload(job.payload_json, self.principal_hash_secret)
            prepared = PreparedTrainingRequest(
                requested_model_version=job.run.requested_model_version,
                min_support=job.run.min_support,
                max_related_per_course=job.run.max_related_per_course,
                request_hash=job.run.request_hash,
                legacy_request_hash=job.run.request_hash,
                interactions=interactions,
            )
        except Exception as exc:
            run = self.repository.finish_training_run(
                job.run.id,
                "FAILED",
                None,
                0,
                0,
                0,
                0,
                0.0,
                exc.__class__.__name__,
                str(exc),
                now_utc(),
            )
            return response_from_run(run, [])
        return self._execute_training_run(
            job.run.id,
            prepared,
            job.run.requested_by or worker_id,
        )

    def recover_stale_training_jobs(self, recovered_at: datetime | None = None) -> int:
        safe_recovered_at = recovered_at or now_utc()
        stale_before = safe_recovered_at - timedelta(seconds=self.training_job_lease_seconds)
        return self.repository.recover_stale_training_jobs(
            stale_before,
            safe_recovered_at,
            self.training_job_max_attempts,
            self.training_job_requeue_delay_seconds,
        )

    def scrub_expired_training_payloads(self, observed_at: datetime | None = None) -> int:
        safe_observed_at = observed_at or now_utc()
        completed_before = safe_observed_at - timedelta(days=self.training_payload_retention_days)
        return self.repository.scrub_training_payloads(
            completed_before,
            PAYLOAD_SCRUB_ELIGIBLE_STATUSES,
        )

    def prepare_training_request(
        self,
        requested_model_version: str | None,
        min_support: int | None,
        max_related_per_course: int | None,
        interactions: list[TrainingInteraction],
    ) -> PreparedTrainingRequest:
        safe_min_support = self.normalize_min_support(min_support)
        safe_max_related = self.normalize_max_related(max_related_per_course)
        normalized_model_version = normalize_model_version(requested_model_version)
        if len(interactions) > self.max_training_events:
            message = (
                "Training payload exceeds configured "
                f"max_training_events={self.max_training_events}"
            )
            raise RecommendationBadRequestError(message)
        normalized_interactions = normalize_training_interactions(interactions)
        request_hash = training_request_hash(
            normalized_model_version,
            safe_min_support,
            safe_max_related,
            normalized_interactions,
            self.principal_hash_secret,
        )
        legacy_request_hash = training_request_hash(
            normalized_model_version,
            safe_min_support,
            safe_max_related,
            normalized_interactions,
            None,
        )
        return PreparedTrainingRequest(
            normalized_model_version,
            safe_min_support,
            safe_max_related,
            request_hash,
            legacy_request_hash,
            normalized_interactions,
        )

    def assert_training_run_exists(self, training_run_id: UUID) -> TrainingRunRecord:
        run = self.repository.training_run(training_run_id)
        if run is None:
            raise RecommendationNotFoundError("Recommendation ML training run was not found")
        return run

    def assert_model_activation_approval_reviewable(
        self,
        approval_id: UUID,
        actor_id: str,
    ) -> ModelActivationApprovalRecord:
        approval = self.repository.model_activation_approval(approval_id)
        if approval is None:
            raise RecommendationNotFoundError(
                "Recommendation ML model activation request was not found"
            )
        if approval.status != "PENDING":
            raise RecommendationConflictError(
                "Recommendation ML model activation request is not pending"
            )
        if approval.requested_by == actor_id:
            raise RecommendationConflictError(
                "Recommendation ML model activation maker cannot approve "
                "or reject their own request"
            )
        return approval

    def assert_model_version_available(self, model_version: str | None) -> None:
        if model_version is not None and self.repository.model_version(model_version) is not None:
            raise RecommendationConflictError(
                f"Recommendation ML modelVersion already exists: {model_version}"
            )

    def _execute_training_run(
        self,
        training_run_id: UUID,
        prepared: PreparedTrainingRequest,
        actor_id: str,
    ) -> dict[str, object]:
        try:
            result = ImplicitItemCfTrainer(
                ImplicitCfConfig(
                    min_support=prepared.min_support,
                    max_related_per_course=prepared.max_related_per_course,
                )
            ).train(prepared.interactions)
            if not result.recommendations:
                run = self.repository.finish_training_run(
                    training_run_id,
                    "INSUFFICIENT_DATA",
                    None,
                    result.event_count,
                    result.principal_count,
                    result.course_count,
                    0,
                    0.0,
                    "INSUFFICIENT_DATA",
                    "Not enough overlapping learner-course interactions to train a model",
                    now_utc(),
                )
                return response_from_run(run, [])

            quality_gate_failure = self.activation_quality_gate_failure(result)
            if quality_gate_failure is not None:
                run = self.repository.finish_training_run(
                    training_run_id,
                    "QUALITY_GATE_FAILED",
                    None,
                    result.event_count,
                    result.principal_count,
                    result.course_count,
                    result.pair_count,
                    result.quality_score,
                    "QUALITY_GATE_FAILED",
                    quality_gate_failure,
                    now_utc(),
                )
                return response_from_run(run, [])

            trained_at = now_utc()
            model_version = prepared.requested_model_version or auto_model_version(
                training_run_id,
                trained_at,
            )
            activated_scores = [
                ScoredRecommendation(
                    course_id=row.course_id,
                    related_course_id=row.related_course_id,
                    rank=row.rank,
                    score=row.score,
                    similarity=row.similarity,
                    support_count=row.support_count,
                    reason_code=row.reason_code,
                    model_version=model_version,
                )
                for row in result.recommendations
            ]
            if not self.auto_activate_trained_models:
                registered = self.repository.register_candidate_model(
                    training_run_id,
                    model_version,
                    ALGORITHM,
                    result.event_count,
                    result.principal_count,
                    result.course_count,
                    len(activated_scores),
                    result.quality_score,
                    json.dumps(
                        {
                            "minSupport": prepared.min_support,
                            "maxRelatedPerCourse": prepared.max_related_per_course,
                        },
                        separators=(",", ":"),
                    ),
                    prepared.request_hash,
                    actor_id,
                    trained_at,
                    activated_scores,
                )
                if not registered:
                    cancelled = self.repository.training_run(training_run_id)
                    if cancelled is None:
                        raise RecommendationNotFoundError(
                            "Recommendation ML training run was not found"
                        )
                    return response_from_run(cancelled, [])
                run = self.repository.finish_training_run(
                    training_run_id,
                    "PENDING_ACTIVATION",
                    model_version,
                    result.event_count,
                    result.principal_count,
                    result.course_count,
                    len(activated_scores),
                    result.quality_score,
                    None,
                    "Model passed quality gates and is waiting for activation approval",
                    trained_at,
                )
                return response_from_run(run, activated_scores)
            activated = self.repository.activate_model(
                training_run_id,
                model_version,
                ALGORITHM,
                result.event_count,
                result.principal_count,
                result.course_count,
                len(activated_scores),
                result.quality_score,
                json.dumps(
                    {
                        "minSupport": prepared.min_support,
                        "maxRelatedPerCourse": prepared.max_related_per_course,
                    },
                    separators=(",", ":"),
                ),
                prepared.request_hash,
                actor_id,
                trained_at,
                activated_scores,
            )
            if not activated:
                cancelled = self.repository.training_run(training_run_id)
                if cancelled is None:
                    raise RecommendationNotFoundError(
                        "Recommendation ML training run was not found"
                    )
                return response_from_run(cancelled, [])
            run = self.repository.finish_training_run(
                training_run_id,
                "ACTIVE",
                model_version,
                result.event_count,
                result.principal_count,
                result.course_count,
                len(activated_scores),
                result.quality_score,
                None,
                None,
                trained_at,
            )
            return response_from_run(run, activated_scores)
        except Exception as exc:
            run = self.repository.finish_training_run(
                training_run_id,
                "FAILED",
                None,
                len(prepared.interactions),
                0,
                0,
                0,
                0.0,
                exc.__class__.__name__,
                str(exc),
                now_utc(),
            )
            return response_from_run(run, [])

    def active_model(self) -> ModelVersionRecord:
        model = self.repository.active_model()
        if model is None:
            raise RecommendationNotFoundError("No active recommendation ML model is available")
        return model

    def related_courses(
        self,
        course_id: UUID,
        model_version: str | None,
        limit: int,
    ) -> dict[str, object]:
        normalized_model_version = normalize_model_version(model_version)
        model = (
            self.repository.model_version(normalized_model_version)
            if normalized_model_version
            else self.repository.active_model()
        )
        if model is None:
            raise RecommendationNotFoundError("Recommendation ML model was not found")
        safe_limit = max(1, min(limit, self.max_related_per_course))
        rows = self.repository.scores_for_course(model.model_version, course_id, safe_limit)
        return {
            "modelVersion": model.model_version,
            "status": model.status,
            "courseId": str(course_id),
            "recommendations": [score_to_dict(row) for row in rows],
        }

    def normalize_min_support(self, requested: int | None) -> int:
        value = self.default_min_support if requested is None else requested
        return max(1, min(value, 1000))

    def normalize_max_related(self, requested: int | None) -> int:
        value = self.default_max_related_per_course if requested is None else requested
        return max(1, min(value, self.max_related_per_course))

    def activation_quality_gate_failure(self, result: TrainingResult) -> str | None:
        failures: list[str] = []
        if result.event_count < self.min_activation_event_count:
            failures.append(
                f"eventCount {result.event_count} < {self.min_activation_event_count}"
            )
        if result.principal_count < self.min_activation_principal_count:
            failures.append(
                f"principalCount {result.principal_count} < {self.min_activation_principal_count}"
            )
        if result.course_count < self.min_activation_course_count:
            failures.append(
                f"courseCount {result.course_count} < {self.min_activation_course_count}"
            )
        if result.pair_count < self.min_activation_pair_count:
            failures.append(f"pairCount {result.pair_count} < {self.min_activation_pair_count}")
        if result.quality_score < self.min_activation_quality_score:
            failures.append(
                f"qualityScore {result.quality_score:.6f} < "
                f"{self.min_activation_quality_score:.6f}"
            )
        if not failures:
            return None
        return "Recommendation ML model did not pass activation quality gates: " + "; ".join(
            failures
        )

    def _duplicate_training_run(
        self,
        existing: TrainingRunRecord,
        prepared: PreparedTrainingRequest,
    ) -> dict[str, object]:
        if existing.request_hash not in {prepared.request_hash, prepared.legacy_request_hash}:
            raise RecommendationConflictError(
                "trainingRunId was already used with a different payload"
            )
        rows = (
            self.repository.scores_for_model(existing.activated_model_version)
            if existing.activated_model_version
            else []
        )
        return response_from_run(existing, rows)


def response_from_run(
    run: TrainingRunRecord,
    scores: list[ScoredRecommendation],
) -> dict[str, object]:
    return {
        "trainingRunId": str(run.id),
        "modelVersion": run.activated_model_version,
        "status": run.status,
        "algorithm": run.algorithm,
        "eventCount": run.event_count,
        "principalCount": run.principal_count,
        "courseCount": run.course_count,
        "pairCount": run.pair_count,
        "qualityScore": run.quality_score,
        "generatedAt": run.finished_at.isoformat() if run.finished_at else None,
        "message": run.error_message,
        "recommendations": [score_to_dict(row) for row in scores],
    }


def model_to_dict(model: ModelVersionRecord) -> dict[str, object]:
    return {
        "trainingRunId": str(model.training_run_id) if model.training_run_id else None,
        "modelVersion": model.model_version,
        "algorithm": model.algorithm,
        "status": model.status,
        "eventCount": model.event_count,
        "principalCount": model.principal_count,
        "courseCount": model.course_count,
        "pairCount": model.pair_count,
        "qualityScore": model.quality_score,
        "trainedAt": model.trained_at.isoformat(),
        "activatedAt": model.activated_at.isoformat() if model.activated_at else None,
    }


def training_run_summary_to_dict(run: TrainingRunRecord) -> dict[str, object]:
    return {
        "trainingRunId": str(run.id),
        "requestedModelVersion": run.requested_model_version,
        "modelVersion": run.activated_model_version,
        "status": run.status,
        "algorithm": run.algorithm,
        "eventCount": run.event_count,
        "principalCount": run.principal_count,
        "courseCount": run.course_count,
        "pairCount": run.pair_count,
        "qualityScore": run.quality_score,
        "requestedBy": run.requested_by,
        "startedAt": run.started_at.isoformat(),
        "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
        "message": run.error_message,
    }


def audit_to_dict(row: ModelOpsAuditRecord) -> dict[str, object]:
    evidence: object = None
    if row.evidence_json:
        try:
            evidence = json.loads(row.evidence_json)
        except json.JSONDecodeError:
            evidence = row.evidence_json
    return {
        "id": str(row.id),
        "action": row.action,
        "modelVersion": row.model_version,
        "previousActiveModelVersion": row.previous_active_model_version,
        "actorId": row.actor_id,
        "reason": row.reason,
        "evidence": evidence,
        "createdAt": row.created_at.isoformat(),
    }


def model_activation_approval_to_dict(
    row: ModelActivationApprovalRecord,
) -> dict[str, object]:
    return {
        "id": str(row.id),
        "modelVersion": row.model_version,
        "status": row.status,
        "requestedBy": row.requested_by,
        "requestReason": row.request_reason,
        "requestEvidence": evidence_from_json(row.request_evidence_json),
        "reviewedBy": row.reviewed_by,
        "reviewReason": row.review_reason,
        "reviewEvidence": evidence_from_json(row.review_evidence_json),
        "previousActiveModelVersion": row.previous_active_model_version,
        "createdAt": row.created_at.isoformat(),
        "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "executedAt": row.executed_at.isoformat() if row.executed_at else None,
    }


def training_ops_audit_to_dict(row: TrainingOpsAuditRecord) -> dict[str, object]:
    return {
        "id": str(row.id),
        "action": row.action,
        "trainingRunId": str(row.training_run_id),
        "previousStatus": row.previous_status,
        "newStatus": row.new_status,
        "actorId": row.actor_id,
        "reason": row.reason,
        "evidence": evidence_from_json(row.evidence_json),
        "createdAt": row.created_at.isoformat(),
    }


def evidence_from_json(value: str | None) -> object | None:
    if not value:
        return None
    try:
        return cast(object, json.loads(value))
    except json.JSONDecodeError:
        return value


def score_to_dict(row: ScoredRecommendation) -> dict[str, object]:
    return {
        "courseId": str(row.course_id),
        "relatedCourseId": str(row.related_course_id),
        "rank": row.rank,
        "score": row.score,
        "similarity": row.similarity,
        "supportCount": row.support_count,
        "reasonCode": row.reason_code,
        "modelVersion": row.model_version,
    }


def normalize_model_version(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > 80 or MODEL_VERSION_PATTERN.fullmatch(trimmed) is None:
        raise RecommendationBadRequestError(
            "modelVersion may only contain letters, digits, dot, underscore, colon, "
            "or hyphen, must start with a letter or digit, and must be at most 80 characters"
        )
    return trimmed


def normalize_status(
    value: str | None,
    allowed_values: frozenset[str],
    label: str,
) -> str | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().upper()
    if normalized not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise RecommendationBadRequestError(
            f"Unsupported {label} status '{normalized}'. Allowed values: {allowed}"
        )
    return normalized


def normalize_required_reason(value: str | None) -> str:
    if value is None or not value.strip():
        raise RecommendationBadRequestError("reason is required")
    reason = value.strip()
    if len(reason) < 8:
        raise RecommendationBadRequestError("reason must be at least 8 characters")
    return reason[:500]


def evidence_to_json(value: dict[str, object] | None) -> str | None:
    if not value:
        return None
    validate_audit_evidence(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_AUDIT_EVIDENCE_BYTES:
        raise RecommendationBadRequestError(
            f"evidence exceeds {MAX_AUDIT_EVIDENCE_BYTES} serialized bytes"
        )
    return encoded


def validate_audit_evidence(value: object, path: str = "evidence", depth: int = 0) -> None:
    if depth > MAX_AUDIT_EVIDENCE_DEPTH:
        raise RecommendationBadRequestError("evidence is too deeply nested")
    if isinstance(value, dict):
        if len(value) > MAX_AUDIT_EVIDENCE_COLLECTION_SIZE:
            raise RecommendationBadRequestError("evidence contains too many fields")
        for key, child in value.items():
            normalized_key = normalize_evidence_key(str(key))
            if any(fragment in normalized_key for fragment in SENSITIVE_EVIDENCE_KEY_FRAGMENTS):
                raise RecommendationBadRequestError(
                    f"evidence contains sensitive field at {path}.{key}"
                )
            validate_audit_evidence(child, f"{path}.{key}", depth + 1)
        return
    if isinstance(value, list):
        if len(value) > MAX_AUDIT_EVIDENCE_COLLECTION_SIZE:
            raise RecommendationBadRequestError("evidence contains too many list items")
        for index, child in enumerate(value):
            validate_audit_evidence(child, f"{path}[{index}]", depth + 1)
        return
    if isinstance(value, str):
        if len(value) > MAX_AUDIT_EVIDENCE_STRING_LENGTH:
            raise RecommendationBadRequestError("evidence string value is too long")
        stripped = value.strip()
        lowered = stripped.lower()
        if (
            lowered.startswith(("bearer ", "basic "))
            or "-----begin " in lowered
            or JWT_LIKE_VALUE.fullmatch(stripped) is not None
        ):
            raise RecommendationBadRequestError(f"evidence contains sensitive value at {path}")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise RecommendationBadRequestError(f"evidence contains unsupported value at {path}")


def normalize_evidence_key(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def normalize_training_interactions(
    interactions: list[TrainingInteraction],
) -> list[TrainingInteraction]:
    return [
        TrainingInteraction(
            principal_id=row.principal_id,
            course_id=row.course_id,
            event_type=normalize_training_event_type(row.event_type),
            occurred_at=row.occurred_at,
            weight=row.weight,
        )
        for row in interactions
    ]


def normalize_training_event_type(value: str) -> str:
    normalized = value.strip().upper().replace("-", "_") if value else ""
    if not normalized:
        raise RecommendationBadRequestError("Training eventType is required")
    if normalized not in SUPPORTED_TRAINING_EVENT_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_TRAINING_EVENT_TYPES))
        raise RecommendationBadRequestError(
            f"Unsupported training eventType '{normalized}'. Allowed values: {allowed}"
        )
    return normalized


def auto_model_version(training_run_id: UUID, generated_at: datetime) -> str:
    stamp = generated_at.strftime("%Y%m%d%H%M%S")
    return f"implicit-cf-v1-{stamp}-{str(training_run_id)[:8]}"


def training_request_hash(
    requested_model_version: str | None,
    min_support: int,
    max_related_per_course: int,
    interactions: list[TrainingInteraction],
    principal_hash_secret: str | None,
) -> str:
    payload = [requested_model_version or "", str(min_support), str(max_related_per_course)]
    for row in sorted(
        interactions,
        key=lambda item: (
            principal_hash_for_request(item.principal_id, principal_hash_secret),
            str(item.course_id),
            item.event_type,
            item.weight if item.weight is not None else -1,
        ),
    ):
        principal_id = principal_hash_for_request(row.principal_id, principal_hash_secret)
        payload.append(
            ",".join(
                [
                    principal_id,
                    str(row.course_id),
                    row.event_type,
                    "" if row.weight is None else f"{row.weight:.3f}",
                ]
            )
        )
    return hashlib.sha256("|".join(payload).encode("utf-8")).hexdigest()


def training_payload_json(
    prepared: PreparedTrainingRequest,
    principal_hash_secret: str,
) -> str:
    return json.dumps(
        {
            "requestedModelVersion": prepared.requested_model_version,
            "minSupport": prepared.min_support,
            "maxRelatedPerCourse": prepared.max_related_per_course,
            "principalIdEncoding": "hmac-sha256:v1",
            "interactions": [
                {
                    "principalHash": pseudonymized_principal_id(
                        row.principal_id,
                        principal_hash_secret,
                    ),
                    "courseId": str(row.course_id),
                    "eventType": row.event_type,
                    "occurredAt": row.occurred_at.isoformat() if row.occurred_at else None,
                    "weight": row.weight,
                }
                for row in prepared.interactions
            ],
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def interactions_from_payload(
    payload_json: str,
    principal_hash_secret: str,
) -> list[TrainingInteraction]:
    payload = json.loads(payload_json)
    raw_interactions = payload.get("interactions")
    if not isinstance(raw_interactions, list):
        raise RecommendationBadRequestError("Training job payload has no interactions")
    return [
        interaction_from_payload_row(row, principal_hash_secret)
        for row in raw_interactions
    ]


def interaction_from_payload_row(
    row: object,
    principal_hash_secret: str,
) -> TrainingInteraction:
    if not isinstance(row, dict):
        raise RecommendationBadRequestError("Training job interaction row must be an object")
    raw_principal_hash = row.get("principalHash")
    if raw_principal_hash is not None and str(raw_principal_hash).strip():
        principal_id = str(raw_principal_hash)
    else:
        principal_id = pseudonymized_principal_id(str(row["principalId"]), principal_hash_secret)
    course_id = UUID(str(row["courseId"]))
    event_type = normalize_training_event_type(str(row["eventType"]))
    occurred_at = parse_optional_datetime(row.get("occurredAt"))
    raw_weight = row.get("weight")
    weight = float(raw_weight) if raw_weight is not None else None
    return TrainingInteraction(principal_id, course_id, event_type, occurred_at, weight)


def principal_hash_for_request(value: str, principal_hash_secret: str | None) -> str:
    if principal_hash_secret is None:
        return value
    return pseudonymized_principal_id(value, principal_hash_secret)


def pseudonymized_principal_id(value: str, principal_hash_secret: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    digest = hmac.new(
        principal_hash_secret.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"hmac-sha256:{digest}"


def parse_optional_datetime(value: object) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def now_utc() -> datetime:
    return datetime.now(UTC)
