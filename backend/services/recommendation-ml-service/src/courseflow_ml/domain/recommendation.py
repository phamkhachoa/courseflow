from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TrainingInteraction:
    principal_id: str
    course_id: UUID
    event_type: str
    occurred_at: datetime | None = None
    weight: float | None = None


@dataclass(frozen=True, slots=True)
class ScoredRecommendation:
    course_id: UUID
    related_course_id: UUID
    rank: int
    score: float
    similarity: float
    support_count: int
    reason_code: str
    model_version: str | None = None


@dataclass(frozen=True, slots=True)
class TrainingResult:
    recommendations: list[ScoredRecommendation]
    event_count: int
    principal_count: int
    course_count: int
    pair_count: int
    quality_score: float


@dataclass(frozen=True, slots=True)
class TrainingRunRecord:
    id: UUID
    requested_model_version: str | None
    activated_model_version: str | None
    algorithm: str
    status: str
    request_hash: str
    event_count: int
    principal_count: int
    course_count: int
    pair_count: int
    quality_score: float
    min_support: int
    max_related_per_course: int
    error_class: str | None
    error_message: str | None
    requested_by: str | None
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class TrainingJobRecord:
    run: TrainingRunRecord
    payload_json: str


@dataclass(frozen=True, slots=True)
class ModelVersionRecord:
    model_version: str
    algorithm: str
    status: str
    event_count: int
    principal_count: int
    course_count: int
    pair_count: int
    quality_score: float
    trained_at: datetime
    activated_at: datetime | None
    training_run_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ModelOpsAuditRecord:
    id: UUID
    action: str
    model_version: str
    previous_active_model_version: str | None
    actor_id: str
    reason: str
    evidence_json: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ModelActivationApprovalRecord:
    id: UUID
    model_version: str
    status: str
    requested_by: str
    request_reason: str
    request_evidence_json: str | None
    reviewed_by: str | None
    review_reason: str | None
    review_evidence_json: str | None
    previous_active_model_version: str | None
    created_at: datetime
    reviewed_at: datetime | None
    executed_at: datetime | None


@dataclass(frozen=True, slots=True)
class TrainingOpsAuditRecord:
    id: UUID
    action: str
    training_run_id: UUID
    previous_status: str | None
    new_status: str
    actor_id: str
    reason: str
    evidence_json: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecommendationOperationalMetrics:
    training_runs_by_status: dict[str, int]
    stale_running_training_runs: int
    oldest_queued_age_seconds: float
    oldest_running_age_seconds: float
    pending_activation_approvals: int
    oldest_pending_activation_approval_age_seconds: float
    active_model_present: bool
    active_model_age_seconds: float | None
    active_model_stale: bool
    migration_ready: bool
