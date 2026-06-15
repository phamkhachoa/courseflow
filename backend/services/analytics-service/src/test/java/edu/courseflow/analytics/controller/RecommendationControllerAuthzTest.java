package edu.courseflow.analytics.controller;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import edu.courseflow.analytics.dto.RecommendationDtos.ManualRelatedCourseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationBatchRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationBatchResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationEventIngestResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationMlTrainingJobResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecordRecommendationEventRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.UpsertManualRelatedCourseRequestDto;
import edu.courseflow.analytics.model.ManualRelatedCourse;
import edu.courseflow.analytics.service.RecommendationService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class RecommendationControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID RELATED_ID = UUID.fromString("30000000-0000-0000-0000-000000000002");

    @Mock
    private RecommendationService recommendations;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private InternalJwtService internalJwtService;

    private RecommendationController controller;

    @BeforeEach
    void setUp() {
        controller = new RecommendationController(recommendations, courseAccess, internalJwtService);
    }

    @Test
    void platformAdminCanCreateManualRelatedCourse() {
        CurrentUser admin = user(1L, "ADMIN");
        UpsertManualRelatedCourseRequestDto request = new UpsertManualRelatedCourseRequestDto(
                RELATED_ID,
                BigDecimal.ONE,
                "Manual pick",
                0,
                null,
                null,
                null);
        ManualRelatedCourseDto dto = new ManualRelatedCourseDto(
                UUID.randomUUID(),
                COURSE_ID,
                RELATED_ID,
                ManualRelatedCourse.DEFAULT_PLACEMENT,
                0,
                BigDecimal.ONE,
                "Manual pick",
                ManualRelatedCourse.STATUS_ACTIVE,
                null,
                null,
                "user:1",
                "user:1",
                Instant.now(),
                Instant.now());
        when(recommendations.createManualRelatedCourse(COURSE_ID, request, "user:1")).thenReturn(dto);

        controller.createManualRelatedCourse(COURSE_ID, request, admin);

        verify(courseAccess).requirePublishedCourse(RELATED_ID);
        verify(recommendations).createManualRelatedCourse(COURSE_ID, request, "user:1");
    }

    @Test
    void learnerCannotCreateManualRelatedCourse() {
        CurrentUser learner = user(4L, "STUDENT");
        UpsertManualRelatedCourseRequestDto request = new UpsertManualRelatedCourseRequestDto(
                RELATED_ID,
                null,
                null,
                null,
                null,
                null,
                null);

        assertThrows(ResponseStatusException.class,
                () -> controller.createManualRelatedCourse(COURSE_ID, request, learner));
        verifyNoInteractions(recommendations);
    }

    @Test
    void publicAnonymousTrackingCannotSetStudentId() {
        RecordRecommendationEventRequestDto request = new RecordRecommendationEventRequestDto(
                UUID.randomUUID(),
                "IMPRESSION",
                COURSE_ID,
                RELATED_ID,
                "4",
                "session-1",
                null,
                null,
                "MANUAL",
                null,
                null,
                Instant.now(),
                null);

        assertThrows(ResponseStatusException.class,
                () -> controller.recordPublicRecommendationEvent(request, null));
        verifyNoInteractions(recommendations);
    }

    @Test
    void publicAnonymousTrackingCanUseSessionId() {
        RecordRecommendationEventRequestDto request = new RecordRecommendationEventRequestDto(
                UUID.randomUUID(),
                "IMPRESSION",
                COURSE_ID,
                RELATED_ID,
                null,
                "session-1",
                null,
                null,
                "MANUAL",
                null,
                null,
                Instant.now(),
                null);
        when(recommendations.recordRecommendationEvent(request, null, null))
                .thenReturn(new RecommendationEventIngestResponseDto(
                        request.eventId(),
                        true,
                        false,
                        "IMPRESSION",
                        request.occurredAt()));

        controller.recordPublicRecommendationEvent(request, null);

        verify(recommendations).recordRecommendationEvent(request, null, null);
    }

    @Test
    void serviceActorCanRecordInternalTrackingWithEventScope() {
        String token = "service.token.signature";
        CurrentUser service = new CurrentUser(null, null, null, Set.of(), Set.of(), token);
        RecordRecommendationEventRequestDto request = new RecordRecommendationEventRequestDto(
                UUID.randomUUID(),
                "CLICK",
                COURSE_ID,
                RELATED_ID,
                "4",
                null,
                null,
                "CO_ENROLLMENT",
                "BEHAVIORAL",
                null,
                "attr-1",
                Instant.now(),
                null);
        when(internalJwtService.verify(token)).thenReturn(serviceClaims(InternalScopes.ANALYTICS_EVENT_WRITE));
        when(recommendations.recordRecommendationEvent(request, "4", "service"))
                .thenReturn(new RecommendationEventIngestResponseDto(
                        request.eventId(),
                        true,
                        false,
                        "CLICK",
                        request.occurredAt()));

        controller.recordInternalRecommendationEvent(request, service);

        verify(recommendations).recordRecommendationEvent(request, "4", "service");
    }

    @Test
    void serviceActorCanRunBatchWithModelScope() {
        String token = "service.token.signature";
        CurrentUser service = new CurrentUser(null, null, null, Set.of(), Set.of(), token);
        RecommendationBatchRequestDto request = new RecommendationBatchRequestDto(30, 10, "model-v1");
        when(internalJwtService.verify(token)).thenReturn(serviceClaims(InternalScopes.ANALYTICS_MODEL_WRITE));
        when(recommendations.recomputeRelatedCoursePairs(request)).thenReturn(
                new RecommendationBatchResponseDto("model-v1", Instant.now(), 2, 3, Instant.now(), "ML", null));

        controller.recomputeRelatedCoursePairs(request, service);

        verify(recommendations).recomputeRelatedCoursePairs(request);
    }

    @Test
    void serviceActorCanRunAsyncMlTrainingWithModelScope() {
        String token = "service.token.signature";
        CurrentUser service = new CurrentUser(null, null, null, Set.of(), Set.of(), token);
        UUID trainingRunId = UUID.randomUUID();
        RecommendationBatchRequestDto request = new RecommendationBatchRequestDto(30, 10, "model-v1");
        when(internalJwtService.verify(token)).thenReturn(serviceClaims(InternalScopes.ANALYTICS_MODEL_WRITE));
        when(recommendations.enqueueMlRelatedCourseTraining(request)).thenReturn(
                new RecommendationMlTrainingJobResponseDto(
                        trainingRunId,
                        "model-v1",
                        "QUEUED",
                        Instant.now(),
                        0,
                        0,
                        Instant.now(),
                        "ML_ASYNC",
                        null));
        when(recommendations.materializeMlTrainingRun(trainingRunId)).thenReturn(
                new RecommendationMlTrainingJobResponseDto(
                        trainingRunId,
                        "model-v1",
                        "ACTIVE",
                        null,
                        2,
                        2,
                        Instant.now(),
                        "ML_ASYNC",
                        null));
        when(recommendations.syncActiveMlModelReadModel()).thenReturn(
                new RecommendationMlTrainingJobResponseDto(
                        trainingRunId,
                        "model-v1",
                        "ACTIVE",
                        null,
                        2,
                        0,
                        Instant.now(),
                        "ML_ACTIVE_MODEL_SYNC",
                        null));

        controller.enqueueMlRelatedCourseTraining(request, service);
        controller.materializeMlTrainingRun(trainingRunId, service);
        controller.materializeActiveMlModel(service);

        verify(recommendations).enqueueMlRelatedCourseTraining(request);
        verify(recommendations).materializeMlTrainingRun(trainingRunId);
        verify(recommendations).syncActiveMlModelReadModel();
    }

    private static CurrentUser user(Long id, String role) {
        return new CurrentUser(id, role.toLowerCase() + "@courseflow.local", role, Set.of(role));
    }

    private static Claims serviceClaims(String... scopes) {
        return Jwts.claims()
                .add("actor_type", "service")
                .add("scope", String.join(" ", scopes))
                .add("scp", List.of(scopes))
                .build();
    }
}
