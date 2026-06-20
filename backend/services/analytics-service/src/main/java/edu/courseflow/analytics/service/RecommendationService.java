package edu.courseflow.analytics.service;

import edu.courseflow.analytics.dto.RecommendationDtos.ManualRelatedCourseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.MaterializeRecommendationArtifactRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationBatchRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationBatchResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationEventIngestResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationArtifactDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationArtifactRowDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationMlTrainingJobResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecordRecommendationEventRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.ReorderManualRelatedCoursesRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.UpdateManualRelatedCourseRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.UpsertManualRelatedCourseRequestDto;
import edu.courseflow.analytics.model.ManualRelatedCourse;
import edu.courseflow.analytics.model.RecommendationMlTrainingJob;
import edu.courseflow.analytics.model.RecommendationTrackingEvent;
import edu.courseflow.analytics.model.RelatedCourse;
import edu.courseflow.analytics.repository.CoursePairStatRepository;
import edu.courseflow.analytics.repository.ManualRelatedCourseRepository;
import edu.courseflow.analytics.repository.RecommendationMlTrainingJobRepository;
import edu.courseflow.analytics.repository.RecommendationTrackingEventRepository;
import edu.courseflow.analytics.repository.RelatedCourseRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RecommendationService {

    private static final int DEFAULT_LOOKBACK_DAYS = 180;
    private static final int MAX_LOOKBACK_DAYS = 730;
    private static final int DEFAULT_LIMIT_PER_COURSE = 24;
    private static final int MAX_LIMIT_PER_COURSE = 100;
    private static final BigDecimal DEFAULT_MANUAL_WEIGHT = BigDecimal.ONE;
    private static final BigDecimal MAX_WEIGHT = new BigDecimal("999.999");
    private static final String DP_AI_ARTIFACT_TYPE = "courseflow.lms.related_course_recommendations";
    private static final int SUPPORTED_DP_AI_ARTIFACT_VERSION = 1;
    private static final List<String> ML_MATERIALIZATION_PENDING_STATUSES = List.of(
            "QUEUED",
            "RUNNING",
            "STARTED",
            RecommendationMlTrainingJob.STATUS_PENDING_ACTIVATION,
            RecommendationMlTrainingJob.STATUS_UNAVAILABLE);

    private final ManualRelatedCourseRepository manualRelatedCourses;
    private final RecommendationTrackingEventRepository trackingEvents;
    private final CoursePairStatRepository pairStats;
    private final RelatedCourseRepository relatedCourses;
    private final RecommendationMlTrainingJobRepository mlTrainingJobs;
    private final RecommendationMlClient recommendationMl;

    public RecommendationService(ManualRelatedCourseRepository manualRelatedCourses,
                                 RecommendationTrackingEventRepository trackingEvents,
                                 CoursePairStatRepository pairStats,
                                 RelatedCourseRepository relatedCourses,
                                 RecommendationMlTrainingJobRepository mlTrainingJobs,
                                 RecommendationMlClient recommendationMl) {
        this.manualRelatedCourses = manualRelatedCourses;
        this.trackingEvents = trackingEvents;
        this.pairStats = pairStats;
        this.relatedCourses = relatedCourses;
        this.mlTrainingJobs = mlTrainingJobs;
        this.recommendationMl = recommendationMl;
    }

    public List<ManualRelatedCourseDto> manualRelatedCourses(UUID courseId, boolean includeArchived) {
        List<ManualRelatedCourse> rows = includeArchived
                ? manualRelatedCourses.findByCourseIdAndPlacementOrderByPositionAscWeightDescRelatedCourseIdAsc(
                        courseId,
                        ManualRelatedCourse.DEFAULT_PLACEMENT)
                : manualRelatedCourses.findByCourseIdAndPlacementAndStatusOrderByPositionAscWeightDescRelatedCourseIdAsc(
                        courseId,
                        ManualRelatedCourse.DEFAULT_PLACEMENT,
                        ManualRelatedCourse.STATUS_ACTIVE);
        return rows.stream().map(this::toDto).toList();
    }

    @Transactional
    public ManualRelatedCourseDto createManualRelatedCourse(UUID courseId,
                                                            UpsertManualRelatedCourseRequestDto request,
                                                            String actorId) {
        UUID relatedCourseId = requireRelatedCourseId(request.relatedCourseId());
        ensureNotSelf(courseId, relatedCourseId);
        var existing = manualRelatedCourses.findByCourseIdAndRelatedCourseIdAndPlacement(
                courseId,
                relatedCourseId,
                ManualRelatedCourse.DEFAULT_PLACEMENT);
        ManualRelatedCourse row = existing.orElseGet(() -> new ManualRelatedCourse(courseId, relatedCourseId, actorId));
        Integer position = request.position();
        if (position == null && existing.isEmpty()) {
            position = Math.toIntExact(manualRelatedCourses.countByCourseIdAndPlacement(
                    courseId,
                    ManualRelatedCourse.DEFAULT_PLACEMENT));
        }
        row.update(
                normalizeWeight(request.weight(), row.getWeight() == null ? DEFAULT_MANUAL_WEIGHT : row.getWeight()),
                normalizeText(request.reason(), 160),
                normalizePosition(position),
                normalizeStatus(request.status(), ManualRelatedCourse.STATUS_ACTIVE),
                request.effectiveFrom(),
                request.effectiveTo(),
                actorId);
        ensureEffectiveRange(row.getEffectiveFrom(), row.getEffectiveTo());
        return toDto(manualRelatedCourses.save(row));
    }

    @Transactional
    public ManualRelatedCourseDto updateManualRelatedCourse(UUID courseId,
                                                            UUID relatedCourseId,
                                                            UpdateManualRelatedCourseRequestDto request,
                                                            String actorId) {
        ManualRelatedCourse row = findManual(courseId, relatedCourseId);
        row.update(
                request.weight() == null ? null : normalizeWeight(request.weight(), row.getWeight()),
                normalizeText(request.reason(), 160),
                normalizePosition(request.position()),
                normalizeStatus(request.status(), null),
                request.effectiveFrom(),
                request.effectiveTo(),
                actorId);
        ensureEffectiveRange(row.getEffectiveFrom(), row.getEffectiveTo());
        return toDto(manualRelatedCourses.save(row));
    }

    @Transactional
    public ManualRelatedCourseDto archiveManualRelatedCourse(UUID courseId, UUID relatedCourseId, String actorId) {
        ManualRelatedCourse row = findManual(courseId, relatedCourseId);
        row.archive(actorId);
        return toDto(manualRelatedCourses.save(row));
    }

    @Transactional
    public void deleteManualRelatedCourse(UUID courseId, UUID relatedCourseId) {
        manualRelatedCourses.delete(findManual(courseId, relatedCourseId));
    }

    @Transactional
    public List<ManualRelatedCourseDto> reorderManualRelatedCourses(UUID courseId,
                                                                    ReorderManualRelatedCoursesRequestDto request,
                                                                    String actorId) {
        List<UUID> orderedIds = request.relatedCourseIds();
        ensureNoDuplicates(orderedIds);
        List<ManualRelatedCourse> rows = manualRelatedCourses
                .findByCourseIdAndPlacementAndRelatedCourseIdIn(
                        courseId,
                        ManualRelatedCourse.DEFAULT_PLACEMENT,
                        orderedIds);
        if (rows.size() != orderedIds.size()) {
            throw NotFoundException.coded(
                    "ANALYTICS_MANUAL_RELATED_NOT_FOUND",
                    "One or more manual related courses were not found for course " + courseId);
        }
        for (int index = 0; index < orderedIds.size(); index++) {
            UUID relatedCourseId = orderedIds.get(index);
            ManualRelatedCourse row = rows.stream()
                    .filter(candidate -> candidate.getRelatedCourseId().equals(relatedCourseId))
                    .findFirst()
                    .orElseThrow();
            row.setPosition(index, actorId);
        }
        return manualRelatedCourses.saveAll(rows).stream()
                .sorted((left, right) -> Integer.compare(left.getPosition(), right.getPosition()))
                .map(this::toDto)
                .toList();
    }

    @Transactional
    public RecommendationEventIngestResponseDto recordRecommendationEvent(
            RecordRecommendationEventRequestDto request,
            String trustedStudentId,
            String actorId) {
        NormalizedRecommendationEvent normalized = normalizeTrackingEvent(request, trustedStudentId, actorId);
        var existing = trackingEvents.findById(normalized.eventId());
        if (existing.isPresent()) {
            ensureSameEvent(existing.get(), normalized.requestHash());
            return new RecommendationEventIngestResponseDto(
                    normalized.eventId(),
                    false,
                    true,
                    normalized.eventType(),
                    normalized.occurredAt());
        }

        try {
            trackingEvents.saveAndFlush(toEntity(normalized));
        } catch (DataIntegrityViolationException duplicate) {
            RecommendationTrackingEvent event = trackingEvents.findById(normalized.eventId())
                    .orElseThrow(() -> duplicate);
            ensureSameEvent(event, normalized.requestHash());
            return new RecommendationEventIngestResponseDto(
                    normalized.eventId(),
                    false,
                    true,
                    normalized.eventType(),
                    normalized.occurredAt());
        }
        return new RecommendationEventIngestResponseDto(
                normalized.eventId(),
                true,
                false,
                normalized.eventType(),
                normalized.occurredAt());
    }

    @Transactional
    public void recordEnrollmentSignal(UUID eventId, String studentId, UUID enrolledCourseId, Instant occurredAt) {
        if (eventId == null || studentId == null || studentId.isBlank() || enrolledCourseId == null) {
            return;
        }
        RecordRecommendationEventRequestDto request = new RecordRecommendationEventRequestDto(
                eventId,
                RecommendationTrackingEvent.TYPE_ENROLLMENT,
                enrolledCourseId,
                null,
                studentId,
                null,
                ManualRelatedCourse.DEFAULT_PLACEMENT,
                "ENROLLMENT_EVENT",
                null,
                null,
                null,
                occurredAt == null ? Instant.now() : occurredAt,
                null);
        try {
            recordRecommendationEvent(request, studentId, "service:enrollment");
        } catch (ConflictException ignored) {
            // Another ingestion path already recorded this source event. Keep the Kafka projection idempotent.
        }
    }

    @Transactional
    public RecommendationBatchResponseDto recomputeRelatedCoursePairs(RecommendationBatchRequestDto request) {
        int lookbackDays = normalizeLookbackDays(request == null ? null : request.lookbackDays());
        int limitPerCourse = normalizeLimitPerCourse(request == null ? null : request.limitPerCourse());
        String requestedModelVersion = normalizeRequestedModelVersion(request == null ? null : request.modelVersion());
        String fallbackModelVersion = requestedModelVersion == null ? "behavioral-co-enrollment-v1" : requestedModelVersion;
        Instant since = Instant.now().minus(lookbackDays, ChronoUnit.DAYS);

        RecommendationMlClient.TrainingOutcome mlOutcome = recommendationMl.trainRelatedCourses(
                UUID.randomUUID(),
                requestedModelVersion,
                limitPerCourse,
                trackingEvents.trainingInteractions(since, recommendationMl.maxTrainingEvents()));
        if (mlOutcome.active()) {
            int generatedCount = materializeMlRecommendations(mlOutcome.response());
            return new RecommendationBatchResponseDto(
                    mlOutcome.response().modelVersion(),
                    since,
                    mlOutcome.response().pairCount(),
                    generatedCount,
                    Instant.now(),
                    "ML",
                    null);
        }

        pairStats.deleteAllInBatch();
        int pairCount = pairStats.recomputeFromTrackingEvents(since, fallbackModelVersion);
        relatedCourses.deleteGeneratedReadModel();
        int generatedCount = relatedCourses.refreshGeneratedReadModel(limitPerCourse);
        return new RecommendationBatchResponseDto(
                fallbackModelVersion,
                since,
                pairCount,
                generatedCount,
                Instant.now(),
                "BEHAVIORAL_FALLBACK",
                mlOutcome.fallbackReason());
    }

    @Transactional
    public RecommendationMlTrainingJobResponseDto enqueueMlRelatedCourseTraining(RecommendationBatchRequestDto request) {
        int lookbackDays = normalizeLookbackDays(request == null ? null : request.lookbackDays());
        int limitPerCourse = normalizeLimitPerCourse(request == null ? null : request.limitPerCourse());
        String requestedModelVersion = normalizeRequestedModelVersion(request == null ? null : request.modelVersion());
        Instant since = Instant.now().minus(lookbackDays, ChronoUnit.DAYS);
        UUID trainingRunId = UUID.randomUUID();
        Instant submittedAt = Instant.now();

        RecommendationMlClient.TrainingOutcome outcome = recommendationMl.enqueueRelatedCourses(
                trainingRunId,
                requestedModelVersion,
                limitPerCourse,
                trackingEvents.trainingInteractions(since, recommendationMl.maxTrainingEvents()));
        RecommendationMlTrainingJob tracked = new RecommendationMlTrainingJob(
                trainingRunId,
                requestedModelVersion,
                outcome.accepted() ? outcome.response().status() : RecommendationMlTrainingJob.STATUS_FAILED_TO_ENQUEUE,
                since,
                limitPerCourse,
                submittedAt);
        if (!outcome.accepted()) {
            tracked.markEnqueueFailed(outcome.fallbackReason(), Instant.now());
            mlTrainingJobs.save(tracked);
            return new RecommendationMlTrainingJobResponseDto(
                    trainingRunId,
                    requestedModelVersion,
                    "FAILED_TO_ENQUEUE",
                    since,
                    0,
                    0,
                    Instant.now(),
                    "ML_ASYNC",
                    outcome.fallbackReason());
        }
        RecommendationMlTrainingJobResponseDto response = jobResponse(outcome.response(), since, "ML_ASYNC", null, 0);
        tracked.recordCheck(
                response.modelVersion(),
                response.status(),
                response.pairCount(),
                response.generatedRelatedRows(),
                response.fallbackReason(),
                Instant.now());
        mlTrainingJobs.save(tracked);
        return response;
    }

    @Transactional
    public RecommendationMlTrainingJobResponseDto materializeMlTrainingRun(UUID trainingRunId) {
        return materializeMlTrainingRun(trainingRunId, false, "ML_ASYNC");
    }

    @Transactional
    public RecommendationMlTrainingJobResponseDto syncActiveMlModelReadModel() {
        RecommendationMlClient.ActiveModelOutcome activeOutcome = recommendationMl.activeModel();
        Instant checkedAt = Instant.now();
        if (!activeOutcome.available()) {
            return new RecommendationMlTrainingJobResponseDto(
                    null,
                    null,
                    RecommendationMlTrainingJob.STATUS_UNAVAILABLE,
                    null,
                    0,
                    0,
                    checkedAt,
                    "ML_ACTIVE_MODEL_SYNC",
                    activeOutcome.fallbackReason());
        }
        RecommendationMlClient.ActiveModelResponse activeModel = activeOutcome.response();
        if (relatedCourses.existsBySourceAndModelVersion("ML", activeModel.modelVersion())) {
            return new RecommendationMlTrainingJobResponseDto(
                    activeModel.trainingRunId(),
                    activeModel.modelVersion(),
                    activeModel.status(),
                    null,
                    activeModel.pairCount(),
                    0,
                    activeModel.activatedAt() == null ? checkedAt : activeModel.activatedAt(),
                    "ML_ACTIVE_MODEL_SYNC",
                    null);
        }
        return materializeMlTrainingRun(activeModel.trainingRunId(), true, "ML_ACTIVE_MODEL_SYNC");
    }

    @Transactional
    public RecommendationMlTrainingJobResponseDto materializeRecommendationArtifact(
            MaterializeRecommendationArtifactRequestDto request) {
        if (request == null || request.artifact() == null) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_REQUIRED",
                    "Recommendation artifact is required");
        }
        RecommendationArtifactDto artifact = request.artifact();
        validateArtifact(artifact);
        Instant generatedAt = artifact.generatedAt();
        boolean forceReplace = Boolean.TRUE.equals(request.forceReplace());
        if (!forceReplace && relatedCourses.existsMlReadModelNewerThan(generatedAt)) {
            return new RecommendationMlTrainingJobResponseDto(
                    null,
                    artifact.modelVersion(),
                    artifact.status(),
                    null,
                    artifact.recommendations().size(),
                    0,
                    generatedAt,
                    "DP_AI_ARTIFACT",
                    "ML_READ_MODEL_NEWER_THAN_ARTIFACT");
        }
        relatedCourses.deleteGeneratedReadModel();
        List<RelatedCourse> rows = toRelatedCourseRows(artifact, generatedAt);
        if (!rows.isEmpty()) {
            relatedCourses.saveAll(rows);
        }
        return new RecommendationMlTrainingJobResponseDto(
                null,
                artifact.modelVersion(),
                artifact.status(),
                null,
                artifact.recommendations().size(),
                rows.size(),
                generatedAt,
                "DP_AI_ARTIFACT",
                null);
    }

    private RecommendationMlTrainingJobResponseDto materializeMlTrainingRun(UUID trainingRunId,
                                                                            boolean forceReplace,
                                                                            String engine) {
        RecommendationMlTrainingJob tracked = mlTrainingJobs.findById(trainingRunId).orElse(null);
        Instant since = tracked == null ? null : tracked.getSince();
        Instant checkedAt = Instant.now();
        RecommendationMlClient.TrainingOutcome outcome = recommendationMl.trainingRun(trainingRunId);
        if (!outcome.accepted()) {
            RecommendationMlTrainingJob job = tracked == null
                    ? new RecommendationMlTrainingJob(
                            trainingRunId,
                            null,
                            RecommendationMlTrainingJob.STATUS_UNAVAILABLE,
                            null,
                            DEFAULT_LIMIT_PER_COURSE,
                            checkedAt)
                    : tracked;
            job.recordCheck(
                    null,
                    RecommendationMlTrainingJob.STATUS_UNAVAILABLE,
                    0,
                    0,
                    outcome.fallbackReason(),
                    checkedAt);
            mlTrainingJobs.save(job);
            return new RecommendationMlTrainingJobResponseDto(
                    trainingRunId,
                    null,
                    "UNAVAILABLE",
                    since,
                    0,
                    0,
                    checkedAt,
                    engine,
                    outcome.fallbackReason());
        }
        RecommendationMlClient.TrainingResponse response = outcome.response();
        int generatedCount = 0;
        if (outcome.active()) {
            generatedCount = materializeMlRecommendations(response, forceReplace);
        }
        RecommendationMlTrainingJobResponseDto materialized = jobResponse(
                response,
                since,
                engine,
                null,
                generatedCount);
        RecommendationMlTrainingJob job = tracked == null
                ? new RecommendationMlTrainingJob(
                        response.trainingRunId(),
                        response.modelVersion(),
                        response.status(),
                        since,
                        DEFAULT_LIMIT_PER_COURSE,
                        checkedAt)
                : tracked;
        job.recordCheck(
                materialized.modelVersion(),
                materialized.status(),
                materialized.pairCount(),
                materialized.generatedRelatedRows(),
                materialized.fallbackReason(),
                checkedAt);
        mlTrainingJobs.save(job);
        return materialized;
    }

    @Transactional(readOnly = true)
    public List<UUID> pendingMlTrainingRunIdsForMaterialization(int batchSize, long minCheckIntervalMs) {
        int safeBatchSize = Math.max(1, Math.min(batchSize, 100));
        long safeIntervalMs = Math.max(1000, minCheckIntervalMs);
        Instant eligibleBefore = Instant.now().minus(safeIntervalMs, ChronoUnit.MILLIS);
        return mlTrainingJobs.findPendingTrainingRunIds(
                ML_MATERIALIZATION_PENDING_STATUSES,
                eligibleBefore,
                PageRequest.of(0, safeBatchSize));
    }

    @Transactional
    public List<UUID> claimPendingMlTrainingRunIdsForMaterialization(int batchSize,
                                                                     long minCheckIntervalMs,
                                                                     String workerId,
                                                                     long lockLeaseMs) {
        int safeBatchSize = Math.max(1, Math.min(batchSize, 100));
        long safeIntervalMs = Math.max(1000, minCheckIntervalMs);
        long safeLockLeaseMs = Math.max(10_000, lockLeaseMs);
        String safeWorkerId = normalizeText(workerId, 120);
        if (safeWorkerId == null) {
            safeWorkerId = "analytics-materializer";
        }
        Instant now = Instant.now();
        Instant eligibleBefore = now.minus(safeIntervalMs, ChronoUnit.MILLIS);
        Instant staleLockBefore = now.minus(safeLockLeaseMs, ChronoUnit.MILLIS);
        List<UUID> candidates = mlTrainingJobs.findClaimableTrainingRunIds(
                ML_MATERIALIZATION_PENDING_STATUSES,
                eligibleBefore,
                staleLockBefore,
                PageRequest.of(0, safeBatchSize));
        List<UUID> claimed = new ArrayList<>();
        for (UUID candidate : candidates) {
            int updated = mlTrainingJobs.claimTrainingRunForMaterialization(
                    candidate,
                    ML_MATERIALIZATION_PENDING_STATUSES,
                    safeWorkerId,
                    now,
                    eligibleBefore,
                    staleLockBefore);
            if (updated == 1) {
                claimed.add(candidate);
            }
        }
        return claimed;
    }

    private int materializeMlRecommendations(RecommendationMlClient.TrainingResponse response) {
        return materializeMlRecommendations(response, false);
    }

    private int materializeMlRecommendations(RecommendationMlClient.TrainingResponse response, boolean forceReplace) {
        Instant generatedAt = response.generatedAt() == null ? Instant.now() : response.generatedAt();
        if (!forceReplace && relatedCourses.existsMlReadModelNewerThan(generatedAt)) {
            return 0;
        }
        relatedCourses.deleteGeneratedReadModel();
        List<RelatedCourse> rows = response.recommendations().stream()
                .map(row -> {
                    RelatedCourse related = new RelatedCourse(UUID.randomUUID(), row.courseId(), row.relatedCourseId());
                    related.updateScore(
                            BigDecimal.valueOf(row.score()).setScale(3, RoundingMode.HALF_UP),
                            "ML",
                            mlReason(row.reasonCode(), row.supportCount()),
                            row.reasonCode(),
                            row.modelVersion() == null ? response.modelVersion() : row.modelVersion(),
                            generatedAt);
                    return related;
                })
                .toList();
        relatedCourses.saveAll(rows);
        return rows.size();
    }

    private List<RelatedCourse> toRelatedCourseRows(RecommendationArtifactDto artifact, Instant generatedAt) {
        Set<CoursePairKey> manuallyCuratedPairs = manuallyCuratedPairs(artifact.recommendations());
        return artifact.recommendations().stream()
                .filter(row -> !manuallyCuratedPairs.contains(new CoursePairKey(row.courseId(), row.relatedCourseId())))
                .map(row -> toRelatedCourse(row, artifact, generatedAt))
                .toList();
    }

    private RelatedCourse toRelatedCourse(RecommendationArtifactRowDto row,
                                          RecommendationArtifactDto artifact,
                                          Instant generatedAt) {
        ensureNotSelf(row.courseId(), row.relatedCourseId());
        RelatedCourse related = new RelatedCourse(UUID.randomUUID(), row.courseId(), row.relatedCourseId());
        related.updateScore(
                normalizeArtifactScore(row.score()),
                "ML",
                mlReason(row.reasonCode(), row.supportCount()),
                normalizeText(row.reasonCode(), 80),
                normalizeText(artifact.modelVersion(), 80),
                generatedAt);
        return related;
    }

    private void validateArtifact(RecommendationArtifactDto artifact) {
        if (!Integer.valueOf(SUPPORTED_DP_AI_ARTIFACT_VERSION).equals(artifact.artifactVersion())) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_VERSION_UNSUPPORTED",
                    "Recommendation artifactVersion is not supported");
        }
        if (!DP_AI_ARTIFACT_TYPE.equals(artifact.artifactType())) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_TYPE_UNSUPPORTED",
                    "Recommendation artifactType is not supported");
        }
        if (!"ACTIVE".equalsIgnoreCase(artifact.status())) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_NOT_ACTIVE",
                    "Only ACTIVE recommendation artifacts can be materialized");
        }
        if (artifact.modelVersion() == null || artifact.modelVersion().isBlank()) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_MODEL_VERSION_REQUIRED",
                    "Recommendation artifact modelVersion is required");
        }
        if (artifact.generatedAt() == null) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_GENERATED_AT_REQUIRED",
                    "Recommendation artifact generatedAt is required");
        }
        if (artifact.recommendations() == null || artifact.recommendations().isEmpty()) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_EMPTY",
                    "Recommendation artifact must contain at least one recommendation");
        }
        String modelVersion = normalizeText(artifact.modelVersion(), 80);
        Set<CoursePairKey> seenPairs = new HashSet<>();
        for (RecommendationArtifactRowDto row : artifact.recommendations()) {
            if (row == null) {
                throw BadRequestException.coded(
                        "ANALYTICS_RECOMMENDATION_ARTIFACT_ROW_INVALID",
                        "Recommendation artifact rows must not be null");
            }
            if (row.courseId() == null || row.relatedCourseId() == null) {
                throw BadRequestException.coded(
                        "ANALYTICS_RECOMMENDATION_ARTIFACT_ROW_INVALID",
                        "Recommendation artifact row must include courseId and relatedCourseId");
            }
            ensureNotSelf(row.courseId(), row.relatedCourseId());
            if (!seenPairs.add(new CoursePairKey(row.courseId(), row.relatedCourseId()))) {
                throw BadRequestException.coded(
                        "ANALYTICS_RECOMMENDATION_ARTIFACT_DUPLICATE_PAIR",
                        "Recommendation artifact contains duplicate course pairs");
            }
            if (row.rank() != null && row.rank() <= 0) {
                throw BadRequestException.coded(
                        "ANALYTICS_RECOMMENDATION_ARTIFACT_RANK_INVALID",
                        "Recommendation artifact row rank must be positive");
            }
            if (row.supportCount() < 0) {
                throw BadRequestException.coded(
                        "ANALYTICS_RECOMMENDATION_ARTIFACT_SUPPORT_INVALID",
                        "Recommendation artifact row supportCount must not be negative");
            }
            validateArtifactScore(row.score());
            validateUnitInterval("similarity", row.similarity());
            normalizeText(row.reasonCode(), 80);
            String rowModelVersion = normalizeText(row.modelVersion(), 80);
            if (rowModelVersion != null && !rowModelVersion.equals(modelVersion)) {
                throw BadRequestException.coded(
                        "ANALYTICS_RECOMMENDATION_ARTIFACT_MODEL_VERSION_MISMATCH",
                        "Recommendation artifact row modelVersion must match artifact modelVersion");
            }
        }
    }

    private Set<CoursePairKey> manuallyCuratedPairs(List<RecommendationArtifactRowDto> recommendations) {
        Map<UUID, List<UUID>> relatedIdsByCourse = new HashMap<>();
        for (RecommendationArtifactRowDto row : recommendations) {
            relatedIdsByCourse
                    .computeIfAbsent(row.courseId(), ignored -> new ArrayList<>())
                    .add(row.relatedCourseId());
        }
        Set<CoursePairKey> pairs = new HashSet<>();
        for (Map.Entry<UUID, List<UUID>> entry : relatedIdsByCourse.entrySet()) {
            manualRelatedCourses.findByCourseIdAndPlacementAndRelatedCourseIdIn(
                            entry.getKey(),
                            ManualRelatedCourse.DEFAULT_PLACEMENT,
                            entry.getValue())
                    .stream()
                    .filter(row -> ManualRelatedCourse.STATUS_ACTIVE.equals(row.getStatus())
                            || ManualRelatedCourse.STATUS_ARCHIVED.equals(row.getStatus()))
                    .map(row -> new CoursePairKey(row.getCourseId(), row.getRelatedCourseId()))
                    .forEach(pairs::add);
        }
        return pairs;
    }

    private static BigDecimal normalizeArtifactScore(double score) {
        validateArtifactScore(score);
        return BigDecimal.valueOf(score).setScale(3, RoundingMode.HALF_UP);
    }

    private static void validateArtifactScore(double score) {
        if (!Double.isFinite(score) || score <= 0.0 || score > 1.0) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_SCORE_INVALID",
                    "Recommendation artifact row score must be finite and between 0 and 1");
        }
    }

    private static void validateUnitInterval(String field, double value) {
        if (!Double.isFinite(value) || value < 0.0 || value > 1.0) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ARTIFACT_FIELD_INVALID",
                    "Recommendation artifact row " + field + " must be finite and between 0 and 1");
        }
    }

    private RecommendationMlTrainingJobResponseDto jobResponse(RecommendationMlClient.TrainingResponse response,
                                                               Instant since,
                                                               String engine,
                                                               String fallbackReason,
                                                               int generatedRows) {
        return new RecommendationMlTrainingJobResponseDto(
                response.trainingRunId(),
                response.modelVersion(),
                response.status(),
                since,
                response.pairCount(),
                generatedRows,
                response.generatedAt() == null ? Instant.now() : response.generatedAt(),
                engine,
                fallbackReason);
    }

    private String mlReason(String reasonCode, int supportCount) {
        String code = reasonCode == null ? "" : reasonCode;
        if ("ML_CO_ENROLLMENT".equalsIgnoreCase(code)) {
            return "ML model found strong co-enrollment patterns across similar learners.";
        }
        if (supportCount > 0) {
            return "ML model found overlapping learner behavior for this course pair.";
        }
        return "ML model ranked this course as a related next step.";
    }

    private ManualRelatedCourse findManual(UUID courseId, UUID relatedCourseId) {
        return manualRelatedCourses
                .findByCourseIdAndRelatedCourseIdAndPlacement(
                        courseId,
                        relatedCourseId,
                        ManualRelatedCourse.DEFAULT_PLACEMENT)
                .orElseThrow(() -> NotFoundException.coded(
                        "ANALYTICS_MANUAL_RELATED_NOT_FOUND",
                        "Manual related course was not found for course " + courseId));
    }

    private NormalizedRecommendationEvent normalizeTrackingEvent(RecordRecommendationEventRequestDto request,
                                                                 String trustedStudentId,
                                                                 String actorId) {
        UUID eventId = request.eventId();
        String eventType = normalizeEventType(request.eventType());
        UUID courseId = request.courseId();
        UUID relatedCourseId = request.relatedCourseId();
        if ((RecommendationTrackingEvent.TYPE_IMPRESSION.equals(eventType)
                || RecommendationTrackingEvent.TYPE_CLICK.equals(eventType))
                && (courseId == null || relatedCourseId == null)) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_EVENT_TARGET_REQUIRED",
                    "Recommendation impression and click events require courseId and relatedCourseId");
        }
        if (courseId != null && courseId.equals(relatedCourseId)) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_SELF_RELATED",
                    "A course cannot be related to itself");
        }
        if (RecommendationTrackingEvent.TYPE_ENROLLMENT.equals(eventType)
                && relatedCourseId == null
                && courseId == null) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_ENROLLMENT_TARGET_REQUIRED",
                    "Recommendation enrollment events require courseId or relatedCourseId");
        }
        String studentId = normalizeText(trustedStudentId == null ? request.studentId() : trustedStudentId, 64);
        String sessionId = normalizeText(request.sessionId(), 120);
        if (studentId == null && sessionId == null && actorId == null) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_EVENT_IDENTITY_REQUIRED",
                    "Recommendation tracking requires a student, session or trusted service actor");
        }
        String source = actorId == null
                ? "PUBLIC"
                : actorId.startsWith("service") ? "SERVICE" : "USER";
        Instant occurredAt = request.occurredAt() == null ? Instant.now() : request.occurredAt();
        String placement = normalizeText(request.placement(), 60);
        if (placement == null) {
            placement = ManualRelatedCourse.DEFAULT_PLACEMENT;
        }
        String reasonCode = normalizeText(request.reasonCode(), 80);
        String recommendationSource = normalizeText(request.recommendationSource(), 60);
        String modelVersion = normalizeText(request.modelVersion(), 80);
        String attributionId = normalizeText(request.attributionId(), 120);
        String metadataJson = normalizeMetadataJson(request.metadataJson());
        String requestHash = requestHash(
                eventId,
                eventType,
                source,
                courseId,
                relatedCourseId,
                studentId,
                sessionId,
                placement,
                reasonCode,
                recommendationSource,
                modelVersion,
                attributionId,
                occurredAt,
                metadataJson);
        return new NormalizedRecommendationEvent(
                eventId,
                eventType,
                source,
                courseId,
                relatedCourseId,
                studentId,
                sessionId,
                placement,
                reasonCode,
                recommendationSource,
                modelVersion,
                attributionId,
                occurredAt,
                metadataJson,
                requestHash,
                actorId);
    }

    private RecommendationTrackingEvent toEntity(NormalizedRecommendationEvent event) {
        return new RecommendationTrackingEvent(
                event.eventId(),
                event.eventType(),
                event.source(),
                event.courseId(),
                event.relatedCourseId(),
                event.studentId(),
                event.sessionId(),
                event.placement(),
                event.reasonCode(),
                event.recommendationSource(),
                event.modelVersion(),
                event.attributionId(),
                event.occurredAt(),
                event.metadataJson(),
                event.requestHash(),
                event.actorId());
    }

    private ManualRelatedCourseDto toDto(ManualRelatedCourse row) {
        return new ManualRelatedCourseDto(
                row.getId(),
                row.getCourseId(),
                row.getRelatedCourseId(),
                row.getPlacement(),
                row.getPosition(),
                row.getWeight(),
                row.getReason(),
                row.getStatus(),
                row.getEffectiveFrom(),
                row.getEffectiveTo(),
                row.getCreatedBy(),
                row.getUpdatedBy(),
                row.getCreatedAt(),
                row.getUpdatedAt());
    }

    private static UUID requireRelatedCourseId(UUID relatedCourseId) {
        if (relatedCourseId == null) {
            throw BadRequestException.coded(
                    "ANALYTICS_MANUAL_RELATED_TARGET_REQUIRED",
                    "relatedCourseId is required");
        }
        return relatedCourseId;
    }

    private static void ensureNotSelf(UUID courseId, UUID relatedCourseId) {
        if (courseId.equals(relatedCourseId)) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_SELF_RELATED",
                    "A course cannot be related to itself");
        }
    }

    private static void ensureNoDuplicates(List<UUID> orderedIds) {
        Set<UUID> unique = new HashSet<>(orderedIds);
        if (unique.size() != orderedIds.size()) {
            throw BadRequestException.coded(
                    "ANALYTICS_MANUAL_RELATED_DUPLICATE_REORDER",
                    "Manual related course reorder payload contains duplicates");
        }
    }

    private static void ensureEffectiveRange(Instant effectiveFrom, Instant effectiveTo) {
        if (effectiveFrom != null && effectiveTo != null && !effectiveTo.isAfter(effectiveFrom)) {
            throw BadRequestException.coded(
                    "ANALYTICS_MANUAL_RELATED_INVALID_EFFECTIVE_RANGE",
                    "effectiveTo must be after effectiveFrom");
        }
    }

    private static BigDecimal normalizeWeight(BigDecimal requested, BigDecimal fallback) {
        BigDecimal weight = requested == null ? fallback : requested;
        if (weight == null) {
            weight = DEFAULT_MANUAL_WEIGHT;
        }
        if (weight.compareTo(BigDecimal.ZERO) < 0 || weight.compareTo(MAX_WEIGHT) > 0) {
            throw BadRequestException.coded(
                    "ANALYTICS_MANUAL_RELATED_INVALID_WEIGHT",
                    "Manual related course weight must be between 0 and 999.999");
        }
        return weight.setScale(3, RoundingMode.HALF_UP);
    }

    private static Integer normalizePosition(Integer position) {
        if (position == null) {
            return null;
        }
        if (position < 0) {
            throw BadRequestException.coded(
                    "ANALYTICS_MANUAL_RELATED_INVALID_POSITION",
                    "Manual related course position must not be negative");
        }
        return position;
    }

    private static String normalizeStatus(String requested, String fallback) {
        String status = normalizeText(requested, 30);
        if (status == null) {
            return fallback;
        }
        status = status.toUpperCase();
        if (!ManualRelatedCourse.STATUS_ACTIVE.equals(status)
                && !ManualRelatedCourse.STATUS_ARCHIVED.equals(status)) {
            throw BadRequestException.coded(
                    "ANALYTICS_MANUAL_RELATED_INVALID_STATUS",
                    "Manual related course status must be ACTIVE or ARCHIVED");
        }
        return status;
    }

    private static String normalizeEventType(String value) {
        String eventType = normalizeText(value, 60);
        if (eventType == null) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_EVENT_TYPE_REQUIRED",
                    "Recommendation eventType is required");
        }
        eventType = eventType.toUpperCase().replace('-', '_');
        if (!RecommendationTrackingEvent.TYPE_IMPRESSION.equals(eventType)
                && !RecommendationTrackingEvent.TYPE_CLICK.equals(eventType)
                && !RecommendationTrackingEvent.TYPE_ENROLLMENT.equals(eventType)) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_EVENT_TYPE_UNSUPPORTED",
                    "Recommendation eventType is not supported: " + value);
        }
        return eventType;
    }

    private static int normalizeLookbackDays(Integer requested) {
        int value = requested == null ? DEFAULT_LOOKBACK_DAYS : requested;
        if (value <= 0) {
            return DEFAULT_LOOKBACK_DAYS;
        }
        return Math.min(value, MAX_LOOKBACK_DAYS);
    }

    private static int normalizeLimitPerCourse(Integer requested) {
        int value = requested == null ? DEFAULT_LIMIT_PER_COURSE : requested;
        if (value <= 0) {
            return DEFAULT_LIMIT_PER_COURSE;
        }
        return Math.min(value, MAX_LIMIT_PER_COURSE);
    }

    private static String normalizeRequestedModelVersion(String requested) {
        return normalizeText(requested, 80);
    }

    private static String normalizeText(String value, int maxLength) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String normalized = value.trim();
        if (normalized.length() > maxLength) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_FIELD_TOO_LONG",
                    "Recommendation field exceeds max length " + maxLength);
        }
        return normalized;
    }

    private static String normalizeMetadataJson(String value) {
        String metadata = normalizeText(value, 4_000);
        if (metadata == null) {
            return null;
        }
        String lower = metadata.toLowerCase();
        if (metadata.contains("@")
                || lower.contains("password")
                || lower.contains("authorization")
                || lower.contains("token")
                || lower.contains("email")
                || lower.contains("phone")) {
            throw BadRequestException.coded(
                    "ANALYTICS_RECOMMENDATION_METADATA_UNSAFE",
                    "Recommendation tracking metadata must not contain PII or credentials");
        }
        return metadata;
    }

    private static void ensureSameEvent(RecommendationTrackingEvent event, String requestHash) {
        if (!requestHash.equals(event.getRequestHash())) {
            throw ConflictException.coded(
                    "ANALYTICS_RECOMMENDATION_EVENT_IDEMPOTENCY_CONFLICT",
                    "Recommendation event id was already used with a different payload");
        }
    }

    private static String requestHash(Object... parts) {
        StringBuilder canonical = new StringBuilder();
        for (Object part : parts) {
            if (canonical.length() > 0) {
                canonical.append('|');
            }
            canonical.append(part == null ? "" : part);
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of()
                    .formatHex(digest.digest(canonical.toString().getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private record NormalizedRecommendationEvent(
            UUID eventId,
            String eventType,
            String source,
            UUID courseId,
            UUID relatedCourseId,
            String studentId,
            String sessionId,
            String placement,
            String reasonCode,
            String recommendationSource,
            String modelVersion,
            String attributionId,
            Instant occurredAt,
            String metadataJson,
            String requestHash,
            String actorId
    ) {
    }

    private record CoursePairKey(UUID courseId, UUID relatedCourseId) {
    }
}
