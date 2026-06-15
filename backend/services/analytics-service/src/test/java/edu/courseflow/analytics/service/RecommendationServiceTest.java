package edu.courseflow.analytics.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationBatchRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecordRecommendationEventRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.UpsertManualRelatedCourseRequestDto;
import edu.courseflow.analytics.model.ManualRelatedCourse;
import edu.courseflow.analytics.model.RecommendationMlTrainingJob;
import edu.courseflow.analytics.model.RecommendationTrackingEvent;
import edu.courseflow.analytics.repository.CoursePairStatRepository;
import edu.courseflow.analytics.repository.ManualRelatedCourseRepository;
import edu.courseflow.analytics.repository.RecommendationMlTrainingJobRepository;
import edu.courseflow.analytics.repository.RecommendationTrackingEventRepository;
import edu.courseflow.analytics.repository.RelatedCourseRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class RecommendationServiceTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID RELATED_ID = UUID.fromString("30000000-0000-0000-0000-000000000002");

    @Mock
    private ManualRelatedCourseRepository manualRelatedCourses;
    @Mock
    private RecommendationTrackingEventRepository trackingEvents;
    @Mock
    private CoursePairStatRepository pairStats;
    @Mock
    private RelatedCourseRepository relatedCourses;
    @Mock
    private RecommendationMlTrainingJobRepository mlTrainingJobs;
    @Mock
    private RecommendationMlClient recommendationMl;

    private RecommendationService service;

    @BeforeEach
    void setUp() {
        service = new RecommendationService(
                manualRelatedCourses,
                trackingEvents,
                pairStats,
                relatedCourses,
                mlTrainingJobs,
                recommendationMl);
    }

    @Test
    void createManualRelatedCourseNormalizesWeightAndAppendsPosition() {
        when(manualRelatedCourses.findByCourseIdAndRelatedCourseIdAndPlacement(
                COURSE_ID,
                RELATED_ID,
                ManualRelatedCourse.DEFAULT_PLACEMENT))
                .thenReturn(Optional.empty());
        when(manualRelatedCourses.countByCourseIdAndPlacement(COURSE_ID, ManualRelatedCourse.DEFAULT_PLACEMENT))
                .thenReturn(2L);
        when(manualRelatedCourses.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var dto = service.createManualRelatedCourse(
                COURSE_ID,
                new UpsertManualRelatedCourseRequestDto(
                        RELATED_ID,
                        new BigDecimal("2.4567"),
                        " Because it fits ",
                        null,
                        null,
                        null,
                        null),
                "user:1");

        assertThat(dto.position()).isEqualTo(2);
        assertThat(dto.weight()).isEqualByComparingTo("2.457");
        assertThat(dto.reason()).isEqualTo("Because it fits");
        assertThat(dto.status()).isEqualTo(ManualRelatedCourse.STATUS_ACTIVE);
    }

    @Test
    void createManualRelatedCourseRejectsSelfRelation() {
        assertThatThrownBy(() -> service.createManualRelatedCourse(
                COURSE_ID,
                new UpsertManualRelatedCourseRequestDto(COURSE_ID, null, null, null, null, null, null),
                "user:1"))
                .isInstanceOf(BadRequestException.class);
    }

    @Test
    void trackingEventIsIdempotentAndUsesTrustedStudentId() {
        UUID eventId = UUID.randomUUID();
        Instant occurredAt = Instant.parse("2026-06-15T01:00:00Z");
        AtomicReference<RecommendationTrackingEvent> stored = new AtomicReference<>();
        when(trackingEvents.findById(eventId)).thenAnswer(invocation -> Optional.ofNullable(stored.get()));
        doAnswer(invocation -> {
            RecommendationTrackingEvent event = invocation.getArgument(0);
            stored.set(event);
            return event;
        }).when(trackingEvents).saveAndFlush(any());

        var request = new RecordRecommendationEventRequestDto(
                eventId,
                "click",
                COURSE_ID,
                RELATED_ID,
                "999",
                "session-1",
                null,
                "CO_ENROLLMENT",
                "BEHAVIORAL",
                "model-v1",
                "attr-1",
                occurredAt,
                "{\"surface\":\"course\"}");

        var first = service.recordRecommendationEvent(request, "4", "user:4");
        var second = service.recordRecommendationEvent(request, "4", "user:4");

        assertThat(first.accepted()).isTrue();
        assertThat(second.duplicate()).isTrue();
        assertThat(stored.get().getStudentId()).isEqualTo("4");
        assertThat(stored.get().getSource()).isEqualTo("USER");
        assertThat(stored.get().getAttributionId()).isEqualTo("attr-1");
    }

    @Test
    void recomputeRelatedCoursePairsRefreshesGeneratedReadModel() {
        when(recommendationMl.maxTrainingEvents()).thenReturn(1000);
        when(trackingEvents.trainingInteractions(any(), eq(1000))).thenReturn(List.of());
        when(recommendationMl.trainRelatedCourses(any(), eq("model-v2"), eq(5), eq(List.of())))
                .thenReturn(RecommendationMlClient.TrainingOutcome.fallback("RECOMMENDATION_ML_NO_TRAINING_EVENTS"));
        when(pairStats.recomputeFromTrackingEvents(any(), eq("model-v2"))).thenReturn(3);
        when(relatedCourses.refreshGeneratedReadModel(5)).thenReturn(7);

        var response = service.recomputeRelatedCoursePairs(
                new RecommendationBatchRequestDto(90, 5, "model-v2"));

        assertThat(response.modelVersion()).isEqualTo("model-v2");
        assertThat(response.pairStatsComputed()).isEqualTo(3);
        assertThat(response.generatedRelatedRows()).isEqualTo(7);
        assertThat(response.engine()).isEqualTo("BEHAVIORAL_FALLBACK");
        assertThat(response.fallbackReason()).isEqualTo("RECOMMENDATION_ML_NO_TRAINING_EVENTS");
        verify(pairStats).deleteAllInBatch();
        verify(relatedCourses).deleteGeneratedReadModel();
    }

    @Test
    void enqueueMlRelatedCourseTrainingReturnsQueuedJob() {
        when(recommendationMl.maxTrainingEvents()).thenReturn(1000);
        when(trackingEvents.trainingInteractions(any(), eq(1000))).thenReturn(List.of());
        when(recommendationMl.enqueueRelatedCourses(any(), eq("model-v3"), eq(5), eq(List.of())))
                .thenAnswer(invocation -> RecommendationMlClient.TrainingOutcome.accepted(
                        new RecommendationMlClient.TrainingResponse(
                                invocation.getArgument(0),
                                "model-v3",
                                "QUEUED",
                                "IMPLICIT_ITEM_CF_V1",
                                0,
                                0,
                                0,
                                0,
                                0.0,
                                Instant.now(),
                                null,
                                List.of())));

        var response = service.enqueueMlRelatedCourseTraining(
                new RecommendationBatchRequestDto(90, 5, "model-v3"));

        assertThat(response.status()).isEqualTo("QUEUED");
        assertThat(response.engine()).isEqualTo("ML_ASYNC");
        ArgumentCaptor<RecommendationMlTrainingJob> captor = ArgumentCaptor.forClass(RecommendationMlTrainingJob.class);
        verify(mlTrainingJobs).save(captor.capture());
        assertThat(captor.getValue().getTrainingRunId()).isEqualTo(response.trainingRunId());
        assertThat(captor.getValue().getStatus()).isEqualTo("QUEUED");
        assertThat(captor.getValue().getCheckCount()).isEqualTo(1);
    }

    @Test
    void materializeMlTrainingRunRefreshesGeneratedReadModelWhenActive() {
        UUID trainingRunId = UUID.randomUUID();
        RecommendationMlClient.TrainingResponse mlResponse = new RecommendationMlClient.TrainingResponse(
                trainingRunId,
                "ml-active-v1",
                "ACTIVE",
                "IMPLICIT_ITEM_CF_V1",
                2,
                1,
                2,
                1,
                0.8,
                Instant.now(),
                null,
                List.of(new RecommendationMlClient.ScoredRecommendation(
                        COURSE_ID,
                        RELATED_ID,
                        1,
                        0.9,
                        0.9,
                        2,
                        "ML_CO_ENROLLMENT",
                        "ml-active-v1")));
        when(recommendationMl.trainingRun(trainingRunId))
                .thenReturn(RecommendationMlClient.TrainingOutcome.active(mlResponse));
        when(relatedCourses.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(mlTrainingJobs.findById(trainingRunId))
                .thenReturn(Optional.of(new RecommendationMlTrainingJob(
                        trainingRunId,
                        "ml-active-v1",
                        "QUEUED",
                        Instant.now().minusSeconds(60),
                        5,
                        Instant.now().minusSeconds(30))));

        var response = service.materializeMlTrainingRun(trainingRunId);

        assertThat(response.status()).isEqualTo("ACTIVE");
        assertThat(response.generatedRelatedRows()).isEqualTo(1);
        verify(relatedCourses).deleteGeneratedReadModel();
        verify(relatedCourses).saveAll(any());
        ArgumentCaptor<RecommendationMlTrainingJob> captor = ArgumentCaptor.forClass(RecommendationMlTrainingJob.class);
        verify(mlTrainingJobs).save(captor.capture());
        assertThat(captor.getValue().getMaterializedAt()).isNotNull();
    }

    @Test
    void materializeMlTrainingRunDoesNotOverwriteNewerMlReadModel() {
        UUID trainingRunId = UUID.randomUUID();
        RecommendationMlClient.TrainingResponse mlResponse = new RecommendationMlClient.TrainingResponse(
                trainingRunId,
                "ml-old-v1",
                "ACTIVE",
                "IMPLICIT_ITEM_CF_V1",
                2,
                1,
                2,
                1,
                0.8,
                Instant.now().minusSeconds(600),
                null,
                List.of(new RecommendationMlClient.ScoredRecommendation(
                        COURSE_ID,
                        RELATED_ID,
                        1,
                        0.9,
                        0.9,
                        2,
                        "ML_CO_ENROLLMENT",
                        "ml-old-v1")));
        when(recommendationMl.trainingRun(trainingRunId))
                .thenReturn(RecommendationMlClient.TrainingOutcome.active(mlResponse));
        when(relatedCourses.existsMlReadModelNewerThan(mlResponse.generatedAt())).thenReturn(true);

        var response = service.materializeMlTrainingRun(trainingRunId);

        assertThat(response.generatedRelatedRows()).isZero();
        verify(relatedCourses).existsMlReadModelNewerThan(mlResponse.generatedAt());
    }

    @Test
    void syncActiveMlModelReadModelForcesApprovedRollbackIntoReadModel() {
        UUID trainingRunId = UUID.randomUUID();
        Instant olderGeneratedAt = Instant.now().minusSeconds(600);
        RecommendationMlClient.ActiveModelResponse activeModel = new RecommendationMlClient.ActiveModelResponse(
                trainingRunId,
                "ml-old-v1",
                "IMPLICIT_ITEM_CF_V1",
                "ACTIVE",
                2,
                1,
                2,
                1,
                0.8,
                olderGeneratedAt,
                olderGeneratedAt.plusSeconds(60));
        RecommendationMlClient.TrainingResponse mlResponse = new RecommendationMlClient.TrainingResponse(
                trainingRunId,
                "ml-old-v1",
                "ACTIVE",
                "IMPLICIT_ITEM_CF_V1",
                2,
                1,
                2,
                1,
                0.8,
                olderGeneratedAt,
                null,
                List.of(new RecommendationMlClient.ScoredRecommendation(
                        COURSE_ID,
                        RELATED_ID,
                        1,
                        0.9,
                        0.9,
                        2,
                        "ML_CO_ENROLLMENT",
                        "ml-old-v1")));
        when(recommendationMl.activeModel())
                .thenReturn(RecommendationMlClient.ActiveModelOutcome.available(activeModel));
        when(relatedCourses.existsBySourceAndModelVersion("ML", "ml-old-v1")).thenReturn(false);
        when(recommendationMl.trainingRun(trainingRunId))
                .thenReturn(RecommendationMlClient.TrainingOutcome.active(mlResponse));
        when(relatedCourses.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var response = service.syncActiveMlModelReadModel();

        assertThat(response.status()).isEqualTo("ACTIVE");
        assertThat(response.engine()).isEqualTo("ML_ACTIVE_MODEL_SYNC");
        assertThat(response.generatedRelatedRows()).isEqualTo(1);
        verify(relatedCourses, never()).existsMlReadModelNewerThan(olderGeneratedAt);
        verify(relatedCourses).deleteGeneratedReadModel();
        verify(relatedCourses).saveAll(any());
    }

    @Test
    void syncActiveMlModelReadModelSkipsWhenReadModelAlreadyMatchesActiveModel() {
        UUID trainingRunId = UUID.randomUUID();
        RecommendationMlClient.ActiveModelResponse activeModel = new RecommendationMlClient.ActiveModelResponse(
                trainingRunId,
                "ml-active-v1",
                "IMPLICIT_ITEM_CF_V1",
                "ACTIVE",
                20,
                10,
                4,
                8,
                0.8,
                Instant.now().minusSeconds(120),
                Instant.now().minusSeconds(60));
        when(recommendationMl.activeModel())
                .thenReturn(RecommendationMlClient.ActiveModelOutcome.available(activeModel));
        when(relatedCourses.existsBySourceAndModelVersion("ML", "ml-active-v1")).thenReturn(true);

        var response = service.syncActiveMlModelReadModel();

        assertThat(response.trainingRunId()).isEqualTo(trainingRunId);
        assertThat(response.modelVersion()).isEqualTo("ml-active-v1");
        assertThat(response.engine()).isEqualTo("ML_ACTIVE_MODEL_SYNC");
        assertThat(response.generatedRelatedRows()).isZero();
        verify(recommendationMl, never()).trainingRun(trainingRunId);
        verify(relatedCourses, never()).deleteGeneratedReadModel();
        verify(relatedCourses, never()).saveAll(any());
    }

    @Test
    void materializeMlTrainingRunRecordsQualityGateFailureAsTerminal() {
        UUID trainingRunId = UUID.randomUUID();
        RecommendationMlClient.TrainingResponse mlResponse = new RecommendationMlClient.TrainingResponse(
                trainingRunId,
                null,
                RecommendationMlTrainingJob.STATUS_QUALITY_GATE_FAILED,
                "IMPLICIT_ITEM_CF_V1",
                2,
                1,
                2,
                2,
                0.5,
                Instant.now(),
                "Recommendation ML model did not pass activation quality gates",
                List.of());
        when(recommendationMl.trainingRun(trainingRunId))
                .thenReturn(RecommendationMlClient.TrainingOutcome.accepted(mlResponse));
        when(mlTrainingJobs.findById(trainingRunId))
                .thenReturn(Optional.of(new RecommendationMlTrainingJob(
                        trainingRunId,
                        null,
                        "QUEUED",
                        Instant.now().minusSeconds(60),
                        5,
                        Instant.now().minusSeconds(30))));

        var response = service.materializeMlTrainingRun(trainingRunId);

        assertThat(response.status()).isEqualTo(RecommendationMlTrainingJob.STATUS_QUALITY_GATE_FAILED);
        assertThat(response.generatedRelatedRows()).isZero();
        ArgumentCaptor<RecommendationMlTrainingJob> captor = ArgumentCaptor.forClass(RecommendationMlTrainingJob.class);
        verify(mlTrainingJobs).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(RecommendationMlTrainingJob.STATUS_QUALITY_GATE_FAILED);
        assertThat(captor.getValue().getCheckCount()).isEqualTo(1);
    }

    @Test
    void materializeMlTrainingRunRecordsCancelledAsTerminal() {
        UUID trainingRunId = UUID.randomUUID();
        RecommendationMlClient.TrainingResponse mlResponse = new RecommendationMlClient.TrainingResponse(
                trainingRunId,
                null,
                RecommendationMlTrainingJob.STATUS_CANCELLED,
                "IMPLICIT_ITEM_CF_V1",
                0,
                0,
                0,
                0,
                0.0,
                Instant.now(),
                "Operator cancelled duplicated batch",
                List.of());
        when(recommendationMl.trainingRun(trainingRunId))
                .thenReturn(RecommendationMlClient.TrainingOutcome.accepted(mlResponse));
        when(mlTrainingJobs.findById(trainingRunId))
                .thenReturn(Optional.of(new RecommendationMlTrainingJob(
                        trainingRunId,
                        null,
                        "QUEUED",
                        Instant.now().minusSeconds(60),
                        5,
                        Instant.now().minusSeconds(30))));

        var response = service.materializeMlTrainingRun(trainingRunId);

        assertThat(response.status()).isEqualTo(RecommendationMlTrainingJob.STATUS_CANCELLED);
        assertThat(response.generatedRelatedRows()).isZero();
        ArgumentCaptor<RecommendationMlTrainingJob> captor = ArgumentCaptor.forClass(RecommendationMlTrainingJob.class);
        verify(mlTrainingJobs).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(RecommendationMlTrainingJob.STATUS_CANCELLED);
    }

    @Test
    void materializeMlTrainingRunKeepsPendingActivationClaimable() {
        UUID trainingRunId = UUID.randomUUID();
        RecommendationMlClient.TrainingResponse mlResponse = new RecommendationMlClient.TrainingResponse(
                trainingRunId,
                "ml-candidate-v1",
                RecommendationMlTrainingJob.STATUS_PENDING_ACTIVATION,
                "IMPLICIT_ITEM_CF_V1",
                20,
                5,
                10,
                8,
                0.7,
                Instant.now(),
                "Model passed quality gates and is waiting for activation approval",
                List.of(new RecommendationMlClient.ScoredRecommendation(
                        COURSE_ID,
                        RELATED_ID,
                        1,
                        0.9,
                        0.9,
                        2,
                        "ML_CO_ENROLLMENT",
                        "ml-candidate-v1")));
        when(recommendationMl.trainingRun(trainingRunId))
                .thenReturn(RecommendationMlClient.TrainingOutcome.accepted(mlResponse));
        when(mlTrainingJobs.findById(trainingRunId))
                .thenReturn(Optional.of(new RecommendationMlTrainingJob(
                        trainingRunId,
                        "ml-candidate-v1",
                        "QUEUED",
                        Instant.now().minusSeconds(60),
                        5,
                        Instant.now().minusSeconds(30))));

        var response = service.materializeMlTrainingRun(trainingRunId);

        assertThat(response.status()).isEqualTo(RecommendationMlTrainingJob.STATUS_PENDING_ACTIVATION);
        assertThat(response.generatedRelatedRows()).isZero();
        verify(relatedCourses, never()).deleteGeneratedReadModel();
        verify(relatedCourses, never()).saveAll(any());
        ArgumentCaptor<RecommendationMlTrainingJob> captor = ArgumentCaptor.forClass(RecommendationMlTrainingJob.class);
        verify(mlTrainingJobs).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(RecommendationMlTrainingJob.STATUS_PENDING_ACTIVATION);
        assertThat(captor.getValue().getMaterializedAt()).isNull();
    }

    @Test
    void materializeMlTrainingRunRecordsActivationRejectedAsTerminal() {
        UUID trainingRunId = UUID.randomUUID();
        RecommendationMlClient.TrainingResponse mlResponse = new RecommendationMlClient.TrainingResponse(
                trainingRunId,
                "ml-candidate-rejected-v1",
                RecommendationMlTrainingJob.STATUS_ACTIVATION_REJECTED,
                "IMPLICIT_ITEM_CF_V1",
                20,
                5,
                10,
                8,
                0.7,
                Instant.now(),
                "Offline validation did not meet expected lift",
                List.of());
        when(recommendationMl.trainingRun(trainingRunId))
                .thenReturn(RecommendationMlClient.TrainingOutcome.accepted(mlResponse));
        when(mlTrainingJobs.findById(trainingRunId))
                .thenReturn(Optional.of(new RecommendationMlTrainingJob(
                        trainingRunId,
                        "ml-candidate-rejected-v1",
                        RecommendationMlTrainingJob.STATUS_PENDING_ACTIVATION,
                        Instant.now().minusSeconds(60),
                        5,
                        Instant.now().minusSeconds(30))));

        var response = service.materializeMlTrainingRun(trainingRunId);

        assertThat(response.status()).isEqualTo(RecommendationMlTrainingJob.STATUS_ACTIVATION_REJECTED);
        assertThat(response.generatedRelatedRows()).isZero();
        verify(relatedCourses, never()).deleteGeneratedReadModel();
        verify(relatedCourses, never()).saveAll(any());
        ArgumentCaptor<RecommendationMlTrainingJob> captor = ArgumentCaptor.forClass(RecommendationMlTrainingJob.class);
        verify(mlTrainingJobs).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(
                RecommendationMlTrainingJob.STATUS_ACTIVATION_REJECTED);
    }

    @Test
    void pendingMlTrainingRunIdsUsesTrackerRepository() {
        UUID first = UUID.randomUUID();
        when(mlTrainingJobs.findPendingTrainingRunIds(any(), any(), any(Pageable.class)))
                .thenReturn(List.of(first));

        var ids = service.pendingMlTrainingRunIdsForMaterialization(25, 30_000);

        assertThat(ids).containsExactly(first);
        verify(mlTrainingJobs).findPendingTrainingRunIds(eq(mlPendingStatuses()), any(), any(Pageable.class));
    }

    @Test
    void claimPendingMlTrainingRunIdsOnlyReturnsRowsWonByThisWorker() {
        UUID first = UUID.randomUUID();
        UUID second = UUID.randomUUID();
        when(mlTrainingJobs.findClaimableTrainingRunIds(any(), any(), any(), any(Pageable.class)))
                .thenReturn(List.of(first, second));
        when(mlTrainingJobs.claimTrainingRunForMaterialization(eq(first), any(), eq("worker-1"), any(), any(), any()))
                .thenReturn(1);
        when(mlTrainingJobs.claimTrainingRunForMaterialization(eq(second), any(), eq("worker-1"), any(), any(), any()))
                .thenReturn(0);

        var ids = service.claimPendingMlTrainingRunIdsForMaterialization(25, 30_000, "worker-1", 300_000);

        assertThat(ids).containsExactly(first);
        verify(mlTrainingJobs).findClaimableTrainingRunIds(
                eq(mlPendingStatuses()),
                any(),
                any(),
                any(Pageable.class));
        verify(mlTrainingJobs).claimTrainingRunForMaterialization(
                eq(first),
                eq(mlPendingStatuses()),
                eq("worker-1"),
                any(),
                any(),
                any());
        verify(mlTrainingJobs).claimTrainingRunForMaterialization(
                eq(second),
                eq(mlPendingStatuses()),
                eq("worker-1"),
                any(),
                any(),
                any());
    }

    private static List<String> mlPendingStatuses() {
        return List.of(
                "QUEUED",
                "RUNNING",
                "STARTED",
                RecommendationMlTrainingJob.STATUS_PENDING_ACTIVATION,
                RecommendationMlTrainingJob.STATUS_UNAVAILABLE);
    }
}
