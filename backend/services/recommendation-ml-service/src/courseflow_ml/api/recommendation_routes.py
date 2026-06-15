from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from courseflow_ml.core.config import get_settings
from courseflow_ml.core.security import (
    INFER_SCOPE,
    OPS_SCOPE,
    TRAIN_SCOPE,
    Principal,
    require_platform_admin_or_scope,
)
from courseflow_ml.core.telemetry import record_training_run
from courseflow_ml.domain.recommendation import TrainingInteraction
from courseflow_ml.repositories.postgres_recommendation_repository import (
    PostgresRecommendationRepository,
)
from courseflow_ml.schemas.recommendation import (
    ActivateModelVersionRequestDto,
    ModelActivationApprovalDto,
    ModelActivationReviewRequestDto,
    ModelOpsAuditDto,
    ModelVersionDto,
    RelatedCourseInferenceResponseDto,
    TrainingOpsAuditDto,
    TrainingRunOpsRequestDto,
    TrainingRunSummaryDto,
    TrainRelatedCoursesRequestDto,
    TrainRelatedCoursesResponseDto,
)
from courseflow_ml.services.recommendation_service import (
    RecommendationBadRequestError,
    RecommendationConflictError,
    RecommendationMlService,
    RecommendationNotFoundError,
    model_to_dict,
)

router = APIRouter(prefix="/internal/recommendation-ml", tags=["recommendation-ml"])
train_access = require_platform_admin_or_scope(TRAIN_SCOPE)
infer_access = require_platform_admin_or_scope(INFER_SCOPE)
ops_access = require_platform_admin_or_scope(OPS_SCOPE)


@lru_cache
def get_recommendation_repository() -> PostgresRecommendationRepository:
    settings = get_settings()
    return PostgresRecommendationRepository(settings.database_url)


@lru_cache
def get_recommendation_service() -> RecommendationMlService:
    settings = get_settings()
    repository = get_recommendation_repository()
    return RecommendationMlService(
        repository,
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


RecommendationServiceDep = Annotated[RecommendationMlService, Depends(get_recommendation_service)]
TrainPrincipalDep = Annotated[Principal, Depends(train_access)]
InferPrincipalDep = Annotated[Principal, Depends(infer_access)]
OpsPrincipalDep = Annotated[Principal, Depends(ops_access)]
ModelVersionQuery = Annotated[str | None, Query()]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
OpsLimitQuery = Annotated[int, Query(ge=1, le=200)]
StatusQuery = Annotated[str | None, Query(max_length=40)]


def require_sync_training_enabled() -> None:
    if not get_settings().recommendation_ml_sync_training_enabled:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Synchronous Recommendation ML training is disabled; enqueue training instead",
        )


@router.post(
    "/related-courses:train",
    response_model=TrainRelatedCoursesResponseDto,
)
def train_related_courses(
    request: TrainRelatedCoursesRequestDto,
    principal: TrainPrincipalDep,
    _: Annotated[None, Depends(require_sync_training_enabled)],
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        response = service.train_related_courses(
            request.trainingRunId,
            request.requestedModelVersion,
            request.minSupport,
            request.maxRelatedPerCourse,
            request_to_interactions(request),
            principal.actor_id,
        )
        record_training_run(str(response["status"]))
        return response
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/related-courses:enqueue",
    response_model=TrainRelatedCoursesResponseDto,
    status_code=http_status.HTTP_202_ACCEPTED,
)
def enqueue_related_courses_training(
    request: TrainRelatedCoursesRequestDto,
    principal: TrainPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.enqueue_related_courses(
            request.trainingRunId,
            request.requestedModelVersion,
            request.minSupport,
            request.maxRelatedPerCourse,
            request_to_interactions(request),
            principal.actor_id,
        )
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/training-runs",
    response_model=list[TrainingRunSummaryDto],
)
def list_training_runs(
    _: OpsPrincipalDep,
    service: RecommendationServiceDep,
    status: StatusQuery = None,
    limit: OpsLimitQuery = 50,
) -> list[dict[str, object]]:
    try:
        return service.list_training_runs(status, limit)
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/training-runs/audit",
    response_model=list[TrainingOpsAuditDto],
)
def list_training_ops_audit(
    _: OpsPrincipalDep,
    service: RecommendationServiceDep,
    limit: OpsLimitQuery = 100,
) -> list[dict[str, object]]:
    return service.list_training_ops_audit(limit)


@router.get(
    "/training-runs/{training_run_id}",
    response_model=TrainRelatedCoursesResponseDto,
)
def training_run_status(
    training_run_id: UUID,
    _: TrainPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.training_run(training_run_id)
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/training-runs/{training_run_id}:cancel",
    response_model=TrainingRunSummaryDto,
)
def cancel_training_run(
    training_run_id: UUID,
    request: TrainingRunOpsRequestDto,
    principal: OpsPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.cancel_training_run(
            training_run_id,
            request.reason,
            request.evidence,
            principal.actor_id,
        )
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/training-runs/{training_run_id}:requeue",
    response_model=TrainingRunSummaryDto,
)
def requeue_training_run(
    training_run_id: UUID,
    request: TrainingRunOpsRequestDto,
    principal: OpsPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.requeue_training_run(
            training_run_id,
            request.reason,
            request.evidence,
            principal.actor_id,
        )
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/models/active", response_model=ModelVersionDto)
def active_model(
    _: InferPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return model_to_dict(service.active_model())
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/models", response_model=list[ModelVersionDto])
def list_model_versions(
    _: OpsPrincipalDep,
    service: RecommendationServiceDep,
    status: StatusQuery = None,
    limit: OpsLimitQuery = 50,
) -> list[dict[str, object]]:
    try:
        return service.list_model_versions(status, limit)
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/models/audit", response_model=list[ModelOpsAuditDto])
def list_model_ops_audit(
    _: OpsPrincipalDep,
    service: RecommendationServiceDep,
    limit: OpsLimitQuery = 100,
) -> list[dict[str, object]]:
    return service.list_model_ops_audit(limit)


@router.get("/models/activation-requests", response_model=list[ModelActivationApprovalDto])
def list_model_activation_requests(
    _: OpsPrincipalDep,
    service: RecommendationServiceDep,
    status: StatusQuery = None,
    limit: OpsLimitQuery = 50,
) -> list[dict[str, object]]:
    try:
        return service.list_model_activation_approvals(status, limit)
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/models/{model_version}:request-activation",
    response_model=ModelActivationApprovalDto,
    status_code=http_status.HTTP_202_ACCEPTED,
)
def request_model_activation(
    model_version: str,
    request: ActivateModelVersionRequestDto,
    principal: OpsPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.request_model_activation(
            model_version,
            request.reason,
            request.evidence,
            principal.actor_id,
        )
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/models/activation-requests/{approval_id}:approve", response_model=ModelVersionDto)
def approve_model_activation(
    approval_id: UUID,
    request: ModelActivationReviewRequestDto,
    principal: OpsPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.approve_model_activation(
            approval_id,
            request.reason,
            request.evidence,
            principal.actor_id,
        )
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/models/activation-requests/{approval_id}:reject",
    response_model=ModelActivationApprovalDto,
)
def reject_model_activation(
    approval_id: UUID,
    request: ModelActivationReviewRequestDto,
    principal: OpsPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.reject_model_activation(
            approval_id,
            request.reason,
            request.evidence,
            principal.actor_id,
        )
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/models/{model_version}:activate", response_model=ModelVersionDto)
def reactivate_model_version(
    model_version: str,
    request: ActivateModelVersionRequestDto,
    principal: OpsPrincipalDep,
    service: RecommendationServiceDep,
) -> dict[str, object]:
    try:
        return service.reactivate_model_version(
            model_version,
            request.reason,
            request.evidence,
            principal.actor_id,
        )
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationConflictError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def request_to_interactions(request: TrainRelatedCoursesRequestDto) -> list[TrainingInteraction]:
    return [
        TrainingInteraction(
            principal_id=row.principalId,
            course_id=row.courseId,
            event_type=row.eventType,
            occurred_at=row.occurredAt,
            weight=row.weight,
        )
        for row in request.interactions
    ]


@router.get("/courses/{course_id}/related", response_model=RelatedCourseInferenceResponseDto)
def related_courses(
    course_id: UUID,
    _: InferPrincipalDep,
    service: RecommendationServiceDep,
    modelVersion: ModelVersionQuery = None,
    limit: LimitQuery = 24,
) -> dict[str, object]:
    try:
        return service.related_courses(course_id, modelVersion, limit)
    except RecommendationBadRequestError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
