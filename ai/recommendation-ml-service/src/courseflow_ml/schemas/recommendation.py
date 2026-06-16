from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

MAX_TRAINING_INTERACTIONS = 250_000


class TrainingInteractionDto(BaseModel):
    principalId: str = Field(min_length=1, max_length=96)
    courseId: UUID
    eventType: str = Field(min_length=1, max_length=40)
    occurredAt: datetime | None = None
    weight: float | None = Field(default=None, ge=0, le=50)


class TrainRelatedCoursesRequestDto(BaseModel):
    trainingRunId: UUID
    requestedModelVersion: str | None = Field(default=None, max_length=80)
    minSupport: int | None = Field(default=None, ge=1, le=1000)
    maxRelatedPerCourse: int | None = Field(default=None, ge=1, le=100)
    interactions: list[TrainingInteractionDto] = Field(max_length=MAX_TRAINING_INTERACTIONS)


class ScoredRelatedCourseDto(BaseModel):
    courseId: UUID | str
    relatedCourseId: UUID | str
    rank: int
    score: float
    similarity: float
    supportCount: int
    reasonCode: str
    modelVersion: str | None = None


class TrainRelatedCoursesResponseDto(BaseModel):
    trainingRunId: UUID | str
    modelVersion: str | None
    status: str
    algorithm: str
    eventCount: int
    principalCount: int
    courseCount: int
    pairCount: int
    qualityScore: float
    generatedAt: datetime | str | None
    message: str | None
    recommendations: list[ScoredRelatedCourseDto]


class TrainingRunSummaryDto(BaseModel):
    trainingRunId: UUID | str
    requestedModelVersion: str | None
    modelVersion: str | None
    status: str
    algorithm: str
    eventCount: int
    principalCount: int
    courseCount: int
    pairCount: int
    qualityScore: float
    requestedBy: str | None
    startedAt: datetime | str
    finishedAt: datetime | str | None
    message: str | None


class RelatedCourseInferenceResponseDto(BaseModel):
    modelVersion: str
    status: str
    courseId: UUID | str
    recommendations: list[ScoredRelatedCourseDto]


class ModelVersionDto(BaseModel):
    trainingRunId: UUID | str | None = None
    modelVersion: str
    algorithm: str
    status: str
    eventCount: int
    principalCount: int
    courseCount: int
    pairCount: int
    qualityScore: float
    trainedAt: datetime | str
    activatedAt: datetime | str | None


class ActivateModelVersionRequestDto(BaseModel):
    reason: str = Field(min_length=8, max_length=500)
    evidence: dict[str, object] | None = None


class ModelActivationReviewRequestDto(BaseModel):
    reason: str = Field(min_length=8, max_length=500)
    evidence: dict[str, object] | None = None


class ModelActivationApprovalDto(BaseModel):
    id: UUID | str
    modelVersion: str
    status: str
    requestedBy: str
    requestReason: str
    requestEvidence: object | None = None
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewEvidence: object | None = None
    previousActiveModelVersion: str | None = None
    createdAt: datetime | str
    reviewedAt: datetime | str | None = None
    executedAt: datetime | str | None = None


class TrainingRunOpsRequestDto(BaseModel):
    reason: str = Field(min_length=8, max_length=500)
    evidence: dict[str, object] | None = None


class ModelOpsAuditDto(BaseModel):
    id: UUID | str
    action: str
    modelVersion: str
    previousActiveModelVersion: str | None
    actorId: str
    reason: str
    evidence: object | None = None
    createdAt: datetime | str


class TrainingOpsAuditDto(BaseModel):
    id: UUID | str
    action: str
    trainingRunId: UUID | str
    previousStatus: str | None
    newStatus: str
    actorId: str
    reason: str
    evidence: object | None = None
    createdAt: datetime | str
