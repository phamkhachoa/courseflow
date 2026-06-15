from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from courseflow_ml.domain.recommendation import (
    ModelActivationApprovalRecord,
    ModelOpsAuditRecord,
    ModelVersionRecord,
    ScoredRecommendation,
    TrainingJobRecord,
    TrainingOpsAuditRecord,
    TrainingRunRecord,
)


class PendingModelActivationApprovalError(Exception):
    """Raised when a model already has a pending activation approval."""


class RecommendationRepository(Protocol):
    def training_run(self, run_id: UUID) -> TrainingRunRecord | None:
        ...

    def model_version(self, model_version: str) -> ModelVersionRecord | None:
        ...

    def active_model(self) -> ModelVersionRecord | None:
        ...

    def list_training_runs(self, status: str | None, limit: int) -> list[TrainingRunRecord]:
        ...

    def list_model_versions(self, status: str | None, limit: int) -> list[ModelVersionRecord]:
        ...

    def list_model_ops_audit(self, limit: int) -> list[ModelOpsAuditRecord]:
        ...

    def model_activation_approval(
        self,
        approval_id: UUID,
    ) -> ModelActivationApprovalRecord | None:
        ...

    def list_model_activation_approvals(
        self,
        status: str | None,
        limit: int,
    ) -> list[ModelActivationApprovalRecord]:
        ...

    def pending_model_activation_approval(
        self,
        model_version: str,
    ) -> ModelActivationApprovalRecord | None:
        ...

    def list_training_ops_audit(self, limit: int) -> list[TrainingOpsAuditRecord]:
        ...

    def scores_for_model(self, model_version: str) -> list[ScoredRecommendation]:
        ...

    def scores_for_course(
        self,
        model_version: str,
        course_id: UUID,
        limit: int,
    ) -> list[ScoredRecommendation]:
        ...

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
        ...

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
        ...

    def claim_next_training_job(
        self,
        worker_id: str,
        claimed_at: datetime,
    ) -> TrainingJobRecord | None:
        ...

    def recover_stale_training_jobs(
        self,
        stale_before: datetime,
        recovered_at: datetime,
        max_attempts: int,
        requeue_delay_seconds: int,
    ) -> int:
        ...

    def scrub_training_payloads(
        self,
        completed_before: datetime,
        statuses: tuple[str, ...],
    ) -> int:
        ...

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
        ...

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
        ...

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
        ...

    def reactivate_model_version(
        self,
        model_version: str,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        activated_at: datetime,
    ) -> ModelVersionRecord | None:
        ...

    def create_model_activation_approval(
        self,
        approval_id: UUID,
        model_version: str,
        requested_by: str,
        request_reason: str,
        request_evidence_json: str | None,
        created_at: datetime,
    ) -> ModelActivationApprovalRecord | None:
        ...

    def approve_model_activation_approval(
        self,
        approval_id: UUID,
        reviewer_id: str,
        review_reason: str,
        review_evidence_json: str | None,
        reviewed_at: datetime,
    ) -> ModelVersionRecord | None:
        ...

    def reject_model_activation_approval(
        self,
        approval_id: UUID,
        reviewer_id: str,
        review_reason: str,
        review_evidence_json: str | None,
        reviewed_at: datetime,
    ) -> ModelActivationApprovalRecord | None:
        ...

    def cancel_training_run(
        self,
        run_id: UUID,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        cancelled_at: datetime,
    ) -> TrainingRunRecord | None:
        ...

    def requeue_training_run(
        self,
        run_id: UUID,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        requeued_at: datetime,
    ) -> TrainingRunRecord | None:
        ...
