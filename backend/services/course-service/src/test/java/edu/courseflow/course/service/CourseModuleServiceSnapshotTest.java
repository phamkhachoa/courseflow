package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.startsWith;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModulePrerequisiteOutlineDto;
import edu.courseflow.course.dto.CourseDtos.PresignedDownloadDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.dto.LearningDtos.CertificateEligibilityDto;
import edu.courseflow.course.dto.LearningDtos.CertificateMissingRequirementDto;
import edu.courseflow.course.dto.LearningDtos.LearnerCoursePlayerDto;
import edu.courseflow.course.dto.LearningDtos.LearnerLearningPathDto;
import edu.courseflow.course.dto.LearningDtos.LearningAccessCheckDto;
import edu.courseflow.course.dto.LearningDtos.LearningAccessCheckRequestDto;
import edu.courseflow.course.dto.LearningDtos.LearningSourceStatusDto;
import edu.courseflow.course.service.LearningSourceStatusClient.SourceKey;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseJpaRepository;
import edu.courseflow.course.repository.CourseVersionJpaRepository;
import edu.courseflow.course.repository.LearnerItemProgressJpaRepository;
import edu.courseflow.course.repository.LearnerModuleProgressJpaRepository;
import edu.courseflow.course.repository.ModuleItemJpaRepository;
import edu.courseflow.course.repository.ModulePrerequisiteJpaRepository;
import edu.courseflow.course.repository.OutboxEventJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

@ExtendWith(MockitoExtension.class)
class CourseModuleServiceSnapshotTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID MODULE_ID = UUID.fromString("30000000-0000-0000-0000-000000001001");
    private static final UUID MODULE_2_ID = UUID.fromString("30000000-0000-0000-0000-000000001002");
    private static final UUID SNAPSHOT_ITEM_ID = UUID.fromString("30000000-0000-0000-0000-000000002001");
    private static final UUID SNAPSHOT_ITEM_2_ID = UUID.fromString("30000000-0000-0000-0000-000000002002");
    private static final UUID DOCUMENT_MEDIA_ID = UUID.fromString("91000000-0000-0000-0000-000000000301");
    private static final UUID OUTSIDE_MEDIA_ID = UUID.fromString("91000000-0000-0000-0000-000000000999");
    private static final CurrentUser LEARNER = new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));

    @Mock
    private CourseModuleJpaRepository modules;
    @Mock
    private ModuleItemJpaRepository items;
    @Mock
    private CourseJpaRepository courses;
    @Mock
    private CourseVersionJpaRepository versions;
    @Mock
    private ModulePrerequisiteJpaRepository prerequisites;
    @Mock
    private LearnerModuleProgressJpaRepository progressRepository;
    @Mock
    private LearnerItemProgressJpaRepository itemProgressRepository;
    @Mock
    private OutboxEventJpaRepository outbox;
    @Mock
    private CourseMapper mapper;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private CertificateEligibilityClient certificateEligibilityClient;
    @Mock
    private LearningSourceStatusClient sourceStatusClient;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private RestClient.Builder restClientBuilder;
    private MockRestServiceServer mediaServer;
    private CourseModuleService service;

    @BeforeEach
    void setUp() {
        restClientBuilder = RestClient.builder();
        mediaServer = MockRestServiceServer.bindTo(restClientBuilder).build();
        service = new CourseModuleService(
                modules,
                items,
                courses,
                versions,
                prerequisites,
                progressRepository,
                itemProgressRepository,
                outbox,
                objectMapper,
                mapper,
                courseAccess,
                certificateEligibilityClient,
                sourceStatusClient,
                restClientBuilder,
                "http://media.test",
                internalJwt());
        lenient().when(courses.findById(COURSE_ID)).thenReturn(Optional.of(publishedCourse()));
        lenient().when(certificateEligibilityClient.loadEligibility(eq(COURSE_ID), eq(LEARNER)))
                .thenReturn(certificateNotEligible());
    }

    @Test
    void listModulesReadsPublishedSnapshotInsteadOfMutableLiveTables() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithOneItem()));

        List<CourseModuleDto> result = service.listModules(COURSE_ID, LEARNER);

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().id()).isEqualTo(MODULE_ID.toString());
        assertThat(result.getFirst().items()).hasSize(1);
        assertThat(result.getFirst().items().getFirst().id()).isEqualTo(SNAPSHOT_ITEM_ID.toString());
        assertThat(result.getFirst().items().getFirst().title()).isEqualTo("Read architecture overview");
        verifyNoInteractions(modules, items);
    }

    @Test
    void listModulesRejectsPublishedCourseWithMissingSnapshot() {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "PUBLISHED", "2", "approved")));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.listModules(COURSE_ID, LEARNER));

        assertThat(ex.getMessage()).contains("empty curriculum snapshot");
        verifyNoInteractions(modules, items);
    }

    @Test
    void listModulesReadsExplicitPublishedVersionPointerInsteadOfLatestPublishedSnapshot() throws Exception {
        Course course = publishedCourse();
        course.publishVersion(1);
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 1)).thenReturn(Optional.of(publishedVersion(
                1,
                "Stable live lesson",
                SNAPSHOT_ITEM_ID)));

        List<CourseModuleDto> result = service.listModules(COURSE_ID, LEARNER);

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().items().getFirst().title()).isEqualTo("Stable live lesson");
        verifyNoInteractions(modules, items);
    }

    @Test
    void progressCountsOnlyItemsFrozenInPublishedSnapshot() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithOneItem()));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());

        CourseProgressDto progress = service.progress(COURSE_ID, LEARNER);

        assertThat(progress.totalModules()).isEqualTo(1);
        assertThat(progress.totalItems()).isEqualTo(1);
        assertThat(progress.totalRequiredItems()).isEqualTo(1);
        assertThat(progress.missingRequirements()).extracting(CourseProgressDto.MissingRequirementDto::itemId)
                .containsExactly(SNAPSHOT_ITEM_ID.toString());
        verifyNoInteractions(modules, items);
    }

    @Test
    void playerAndProgressExposePublishedVersionNumber() throws Exception {
        Course course = publishedCourse();
        course.publishVersion(7);
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 7))
                .thenReturn(Optional.of(publishedVersion(7, "Pinned lesson", SNAPSHOT_ITEM_ID)));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());

        LearnerCoursePlayerDto player = service.player(COURSE_ID, LEARNER);
        CourseProgressDto progress = service.progress(COURSE_ID, LEARNER);

        assertThat(player.publishedVersionNo()).isEqualTo(7);
        assertThat(player.progress().publishedVersionNo()).isEqualTo(7);
        assertThat(progress.publishedVersionNo()).isEqualTo(7);
        verifyNoInteractions(modules, items);
    }

    @Test
    void playerExposesPrerequisiteLockStateBeforeLearnerClicksLockedModule() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithPrerequisiteChain()));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());

        LearnerCoursePlayerDto player = service.player(COURSE_ID, LEARNER);

        assertThat(player.modules()).hasSize(2);
        assertThat(player.progress().totalRequiredItems()).isEqualTo(2);
        assertThat(player.moduleStates())
                .filteredOn(state -> state.moduleId().equals(MODULE_2_ID.toString()))
                .singleElement()
                .satisfies(state -> {
                    assertThat(state.locked()).isTrue();
                    assertThat(state.lockedReasonCode()).isEqualTo("PREREQUISITE_MODULE_INCOMPLETE");
                    assertThat(state.unmetPrerequisites()).extracting("moduleId").containsExactly(MODULE_ID.toString());
                });
        assertThat(player.itemStates())
                .filteredOn(state -> state.itemId().equals(SNAPSHOT_ITEM_2_ID.toString()))
                .singleElement()
                .satisfies(state -> {
                    assertThat(state.locked()).isTrue();
                    assertThat(state.completionMode()).isEqualTo("SELF");
                });
        assertThat(player.nextAction().itemId()).isEqualTo(SNAPSHOT_ITEM_ID.toString());
        assertThat(player.certificateEligibility().status()).isEqualTo("REQUIRED_ITEMS_INCOMPLETE");
        assertThat(player.certificateEligibility().missingRequirements())
                .extracting(CertificateMissingRequirementDto::label)
                .contains("Read architecture overview");
        verifyNoInteractions(modules, items);
    }

    @Test
    void learningPathProjectsPublishedSnapshotWithCohortContextAndLocks() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithPrerequisiteChain()));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());

        LearnerLearningPathDto path = service.learningPath(COURSE_ID, LEARNER, "cohort-2026-a", "section-01");

        assertThat(path.courseId()).isEqualTo(COURSE_ID.toString());
        assertThat(path.publishedVersionNo()).isEqualTo(3);
        assertThat(path.studentId()).isEqualTo("4");
        assertThat(path.cohortId()).isEqualTo("cohort-2026-a");
        assertThat(path.sectionId()).isEqualTo("section-01");
        assertThat(path.progress().totalRequiredItems()).isEqualTo(2);
        assertThat(path.nextAction().itemId()).isEqualTo(SNAPSHOT_ITEM_ID.toString());
        assertThat(path.modules()).hasSize(2);
        assertThat(path.modules().getFirst().items())
                .singleElement()
                .satisfies(item -> {
                    assertThat(item.itemId()).isEqualTo(SNAPSHOT_ITEM_ID.toString());
                    assertThat(item.progressStatus()).isEqualTo("NOT_STARTED");
                    assertThat(item.sourceStatus()).isEqualTo("READY");
                });
        assertThat(path.modules().getLast()).satisfies(module -> {
            assertThat(module.locked()).isTrue();
            assertThat(module.lockedReasonCode()).isEqualTo("PREREQUISITE_MODULE_INCOMPLETE");
            assertThat(module.unmetPrerequisites()).extracting("moduleId").containsExactly(MODULE_ID.toString());
            assertThat(module.items()).singleElement().satisfies(item -> {
                assertThat(item.locked()).isTrue();
                assertThat(item.lockedReasonCode()).isEqualTo("PREREQUISITE_MODULE_INCOMPLETE");
            });
        });
        verifyNoInteractions(modules, items);
    }

    @Test
    void playerSkipsSourceCompletedAssessmentsAndPrioritizesOverdueRequiredItem() throws Exception {
        UUID assignmentId = UUID.fromString("50000000-0000-0000-0000-000000000201");
        UUID quizId = UUID.fromString("60000000-0000-0000-0000-000000000201");
        Instant dueAt = Instant.parse("2026-06-12T10:00:00Z");
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithAssessmentItems(assignmentId, quizId)));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());
        when(sourceStatusClient.loadStatuses(eq(COURSE_ID), eq("4"), anyList())).thenReturn(Map.of(
                new SourceKey("ASSIGNMENT", assignmentId.toString()),
                new LearningSourceStatusDto(
                        "ASSIGNMENT",
                        assignmentId.toString(),
                        COURSE_ID.toString(),
                        "Submit release plan",
                        "COMPLETED",
                        null,
                        dueAt,
                        null,
                        "GRADED",
                        "50000000-0000-0000-0000-000000000301",
                        1,
                        1,
                        true,
                        false),
                new SourceKey("QUIZ", quizId.toString()),
                new LearningSourceStatusDto(
                        "QUIZ",
                        quizId.toString(),
                        COURSE_ID.toString(),
                        "Release readiness quiz",
                        "OVERDUE",
                        null,
                        dueAt,
                        dueAt,
                        null,
                        null,
                        0,
                        1,
                        false,
                        true)));

        LearnerCoursePlayerDto player = service.player(COURSE_ID, LEARNER);

        assertThat(player.nextAction().kind()).isEqualTo("OVERDUE_ITEM");
        assertThat(player.nextAction().itemId()).isEqualTo(SNAPSHOT_ITEM_2_ID.toString());
        assertThat(player.itemStates())
                .filteredOn(state -> state.itemId().equals(SNAPSHOT_ITEM_ID.toString()))
                .singleElement()
                .satisfies(state -> {
                    assertThat(state.sourceStatus()).isEqualTo("COMPLETED");
                    assertThat(state.sourceDueAt()).isEqualTo(dueAt);
                });
        assertThat(player.itemStates())
                .filteredOn(state -> state.itemId().equals(SNAPSHOT_ITEM_2_ID.toString()))
                .singleElement()
                .satisfies(state -> {
                    assertThat(state.sourceStatus()).isEqualTo("OVERDUE");
                    assertThat(state.sourceDueAt()).isEqualTo(dueAt);
        });
        verifyNoInteractions(modules, items);
    }

    @Test
    void playerMarksCertificateEligibleWhenRequiredItemsAndCertificateChecksPass() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithOneItem()));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4"))
                .thenReturn(List.of(completedProgress(SNAPSHOT_ITEM_ID)));
        when(certificateEligibilityClient.loadEligibility(eq(COURSE_ID), eq(LEARNER)))
                .thenReturn(certificateEligible());

        LearnerCoursePlayerDto player = service.player(COURSE_ID, LEARNER);

        assertThat(player.progress().completed()).isTrue();
        assertThat(player.certificateEligibility().eligible()).isTrue();
        assertThat(player.certificateEligibility().status()).isEqualTo("ELIGIBLE");
        assertThat(player.certificateEligibility().requiredItemsEligible()).isTrue();
        assertThat(player.certificateEligibility().gradeThreshold()).isEqualByComparingTo("60.00");
    }

    @Test
    void playerShowsProgressSyncPendingWhenSourcesCompletedButEnrollmentNotSynced() throws Exception {
        UUID assignmentId = UUID.fromString("50000000-0000-0000-0000-000000000201");
        UUID quizId = UUID.fromString("60000000-0000-0000-0000-000000000201");
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithAssessmentItems(assignmentId, quizId)));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());
        when(sourceStatusClient.loadStatuses(eq(COURSE_ID), eq("4"), anyList())).thenReturn(Map.of(
                new SourceKey("ASSIGNMENT", assignmentId.toString()),
                completedSourceStatus("ASSIGNMENT", assignmentId),
                new SourceKey("QUIZ", quizId.toString()),
                completedSourceStatus("QUIZ", quizId)));
        when(certificateEligibilityClient.loadEligibility(eq(COURSE_ID), eq(LEARNER)))
                .thenReturn(certificateNotEligible());

        LearnerCoursePlayerDto player = service.player(COURSE_ID, LEARNER);

        assertThat(player.nextAction().kind()).isEqualTo("SOURCE_SYNC_PENDING");
        assertThat(player.certificateEligibility().status()).isEqualTo("PROGRESS_SYNC_PENDING");
        assertThat(player.certificateEligibility().requiredItemsEligible()).isTrue();
        assertThat(player.certificateEligibility().missingRequirements())
                .extracting(CertificateMissingRequirementDto::code)
                .contains("COURSE_COMPLETION_SYNC")
                .doesNotContain("REQUIRED_ITEM_INCOMPLETE");
    }

    @Test
    void playerBlocksVerifiedActivityWhenSourceStatusIsUnavailable() throws Exception {
        UUID assignmentId = UUID.fromString("50000000-0000-0000-0000-000000000201");
        UUID quizId = UUID.fromString("60000000-0000-0000-0000-000000000201");
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithAssessmentItems(assignmentId, quizId)));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());
        when(sourceStatusClient.loadStatuses(eq(COURSE_ID), eq("4"), anyList())).thenReturn(Map.of(
                new SourceKey("ASSIGNMENT", assignmentId.toString()),
                new LearningSourceStatusDto(
                        "ASSIGNMENT",
                        assignmentId.toString(),
                        COURSE_ID.toString(),
                        null,
                        "SOURCE_STATUS_UNAVAILABLE",
                        null,
                        null,
                        null,
                        null,
                        null,
                        0,
                        null,
                        false,
                        false),
                new SourceKey("QUIZ", quizId.toString()),
                new LearningSourceStatusDto(
                        "QUIZ",
                        quizId.toString(),
                        COURSE_ID.toString(),
                        null,
                        "SOURCE_STATUS_UNAVAILABLE",
                        null,
                        null,
                        null,
                        null,
                        null,
                        0,
                        null,
                        false,
                        false)));

        LearnerCoursePlayerDto player = service.player(COURSE_ID, LEARNER);

        assertThat(player.nextAction().kind()).isEqualTo("SOURCE_STATUS_UNAVAILABLE");
        assertThat(player.nextAction().locked()).isTrue();
        assertThat(player.itemStates())
                .filteredOn(state -> state.itemId().equals(SNAPSHOT_ITEM_ID.toString()))
                .singleElement()
                .satisfies(state -> assertThat(state.sourceStatus()).isEqualTo("SOURCE_STATUS_UNAVAILABLE"));
        verifyNoInteractions(modules, items);
    }

    @Test
    void learnerCannotSelfCompleteVerifiedActivityItems() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithVideoItem()));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.completeItem(COURSE_ID, MODULE_ID, SNAPSHOT_ITEM_ID, null, LEARNER));

        assertThat(ex.getMessage()).contains("requires verified completion");
        verifyNoInteractions(modules, items, itemProgressRepository, outbox);
    }

    @Test
    void learnerCanDownloadDocumentMediaFromPublishedSnapshot() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithDocumentItem()));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());
        mediaServer.expect(requestTo("http://media.test/internal/media/assets/" + DOCUMENT_MEDIA_ID + "/download-url/trusted"))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header(HttpHeaders.AUTHORIZATION, startsWith("Bearer ")))
                .andExpect(header(GatewayHeaders.INTERNAL_AUTHORIZATION, startsWith("Bearer ")))
                .andRespond(withSuccess("""
                        {"storageKey":"demo/docs/se401.pdf","downloadUrl":"https://download.test/se401.pdf","expiresAt":"2026-06-13T00:05:00Z"}
                        """, MediaType.APPLICATION_JSON));

        PresignedDownloadDto grant = service.downloadPublishedMedia(COURSE_ID, DOCUMENT_MEDIA_ID, LEARNER);

        assertThat(grant.downloadUrl()).isEqualTo("https://download.test/se401.pdf");
        mediaServer.verify();
        verifyNoInteractions(modules, items);
    }

    private InternalJwtService internalJwt() {
        return new InternalJwtService(new InternalJwtProperties(
                "internal-jwt-secret-that-is-at-least-32-bytes",
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "course-service"));
    }

    private static Course publishedCourse() {
        Course course = new Course(
                COURSE_ID,
                "SE401",
                "Production Architecture",
                "production-architecture",
                "Production readiness",
                UUID.fromString("20000000-0000-0000-0000-000000000001"),
                "2",
                "ADVANCED");
        course.setStatus("PUBLISHED");
        return course;
    }

    @Test
    void learnerCannotDownloadDocumentMediaFromLockedModule() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithLockedDocumentItem()));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());

        assertThrows(edu.courseflow.course.exception.ForbiddenException.class,
                () -> service.downloadPublishedMedia(COURSE_ID, DOCUMENT_MEDIA_ID, LEARNER));

        mediaServer.verify();
        verifyNoInteractions(modules, items);
    }

    @Test
    void learningAccessDeniesPublishedSourceInLockedModule() throws Exception {
        UUID quizId = UUID.fromString("60000000-0000-0000-0000-000000000201");
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithLockedQuizItem(quizId)));
        when(itemProgressRepository.findByCourseIdAndStudentId(COURSE_ID, "4")).thenReturn(List.of());

        LearningAccessCheckDto access = service.checkLearningAccess(
                COURSE_ID,
                new LearningAccessCheckRequestDto("4", "QUIZ", quizId.toString()));

        assertThat(access.allowed()).isFalse();
        assertThat(access.reasonCode()).isEqualTo("PREREQUISITE_MODULE_INCOMPLETE");
        assertThat(access.moduleId()).isEqualTo(MODULE_2_ID.toString());
        assertThat(access.itemId()).isEqualTo(SNAPSHOT_ITEM_2_ID.toString());
        verifyNoInteractions(modules, items);
    }

    @Test
    void learningAccessDeniesStudentWithoutCourseEnrollment() {
        UUID quizId = UUID.fromString("60000000-0000-0000-0000-000000000201");
        doThrow(new edu.courseflow.commonlibrary.exception.ForbiddenException("not enrolled"))
                .when(courseAccess).requireStudentCourseAccess("4", COURSE_ID);

        LearningAccessCheckDto access = service.checkLearningAccess(
                COURSE_ID,
                new LearningAccessCheckRequestDto("4", "QUIZ", quizId.toString()));

        assertThat(access.allowed()).isFalse();
        assertThat(access.reasonCode()).isEqualTo("COURSE_ACCESS_DENIED");
        verifyNoInteractions(modules, items);
    }

    @Test
    void learningAccessDeniesSourceOutsidePublishedSnapshot() throws Exception {
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithOneItem()));

        LearningAccessCheckDto access = service.checkLearningAccess(
                COURSE_ID,
                new LearningAccessCheckRequestDto("4", "QUIZ", "60000000-0000-0000-0000-000000000999"));

        assertThat(access.allowed()).isFalse();
        assertThat(access.reasonCode()).isEqualTo("SOURCE_NOT_IN_PUBLISHED_CURRICULUM");
        assertThat(access.moduleId()).isNull();
        assertThat(access.itemId()).isNull();
        verifyNoInteractions(modules, items);
    }

    @Test
    void learnerCannotDownloadMediaOutsidePublishedSnapshot() throws Exception {
        doNothing().when(courseAccess).requireCourseAccess(LEARNER, COURSE_ID);
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED"))
                .thenReturn(List.of(publishedVersionWithDocumentItem()));

        assertThrows(edu.courseflow.course.exception.ForbiddenException.class,
                () -> service.downloadPublishedMedia(COURSE_ID, OUTSIDE_MEDIA_ID, LEARNER));

        mediaServer.verify();
        verifyNoInteractions(modules, items);
    }

    private CourseVersion publishedVersionWithOneItem() throws JsonProcessingException {
        return publishedVersion(3, "Read architecture overview", SNAPSHOT_ITEM_ID);
    }

    private CourseVersion publishedVersion(int versionNo, String itemTitle, UUID itemId) throws JsonProcessingException {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, versionNo, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(new ModuleOutlineDto(
                MODULE_ID.toString(),
                "Module 1 - Architecture foundation",
                "Learn service ownership, API boundaries and local infra.",
                1,
                "PUBLISHED",
                List.of(new ItemOutlineDto(
                        itemId.toString(),
                        "LESSON",
                        "30000000-0000-0000-0000-000000000101",
                        itemTitle,
                        "Review architecture guide.",
                        null,
                        List.of(),
                        null,
                        25,
                        1,
                        true))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
    }

    private edu.courseflow.course.model.LearnerItemProgress completedProgress(UUID itemId) {
        edu.courseflow.course.model.LearnerItemProgress progress =
                new edu.courseflow.course.model.LearnerItemProgress(UUID.randomUUID(), COURSE_ID, MODULE_ID, itemId, "4");
        progress.complete("LESSON_CONFIRMED", Instant.parse("2026-06-13T00:00:00Z"));
        return progress;
    }

    private LearningSourceStatusDto completedSourceStatus(String sourceType, UUID sourceId) {
        return new LearningSourceStatusDto(
                sourceType,
                sourceId.toString(),
                COURSE_ID.toString(),
                sourceType + " completed",
                "COMPLETED",
                null,
                null,
                null,
                "COMPLETED",
                UUID.randomUUID().toString(),
                1,
                1,
                true,
                false);
    }

    private CertificateEligibilityDto certificateNotEligible() {
        return new CertificateEligibilityDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                "4",
                false,
                "COURSE_NOT_COMPLETED",
                false,
                true,
                false,
                false,
                new java.math.BigDecimal("91.50"),
                new java.math.BigDecimal("60.00"),
                "FINALIZED",
                null,
                null,
                null,
                List.of(new CertificateMissingRequirementDto(
                        "COURSE_COMPLETION",
                        "Hoàn thành khóa học",
                        "Enrollment phải ở trạng thái COMPLETED trước khi cấp chứng chỉ.")));
    }

    private CertificateEligibilityDto certificateEligible() {
        return new CertificateEligibilityDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                "4",
                true,
                "ELIGIBLE",
                true,
                true,
                true,
                false,
                new java.math.BigDecimal("91.50"),
                new java.math.BigDecimal("60.00"),
                "FINALIZED",
                null,
                null,
                null,
                List.of());
    }

    private CourseVersion publishedVersionWithVideoItem() throws JsonProcessingException {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(new ModuleOutlineDto(
                MODULE_ID.toString(),
                "Module 1 - Architecture foundation",
                "Learn service ownership, API boundaries and local infra.",
                1,
                "PUBLISHED",
                List.of(new ItemOutlineDto(
                        SNAPSHOT_ITEM_ID.toString(),
                        "VIDEO",
                        "83000000-0000-0000-0000-000000000001",
                        "Watch architecture walkthrough",
                        "Watch the service boundary walkthrough.",
                        "83000000-0000-0000-0000-000000000001",
                        List.of(),
                        null,
                        25,
                        1,
                        true))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
    }

    private CourseVersion publishedVersionWithDocumentItem() throws JsonProcessingException {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(new ModuleOutlineDto(
                MODULE_ID.toString(),
                "Module 1 - Architecture foundation",
                "Learn service ownership, API boundaries and local infra.",
                1,
                "PUBLISHED",
                List.of(new ItemOutlineDto(
                        SNAPSHOT_ITEM_ID.toString(),
                        "MATERIAL",
                        "32000000-0000-0000-0000-000000000103",
                        "Read architecture workbook",
                        "Review architecture workbook.",
                        null,
                        List.of(DOCUMENT_MEDIA_ID.toString()),
                        null,
                        25,
                        1,
                        true))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
    }

    private CourseVersion publishedVersionWithAssessmentItems(UUID assignmentId, UUID quizId) throws JsonProcessingException {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(new ModuleOutlineDto(
                MODULE_ID.toString(),
                "Module 1 - Architecture foundation",
                "Learn service ownership, API boundaries and local infra.",
                1,
                "PUBLISHED",
                List.of(
                        new ItemOutlineDto(
                                SNAPSHOT_ITEM_ID.toString(),
                                "ASSIGNMENT",
                                assignmentId.toString(),
                                "Submit release plan",
                                "Submit the release plan.",
                                null,
                                List.of(),
                                null,
                                30,
                                1,
                                true),
                        new ItemOutlineDto(
                                SNAPSHOT_ITEM_2_ID.toString(),
                                "QUIZ",
                                quizId.toString(),
                                "Release readiness quiz",
                                "Pass the readiness quiz.",
                                null,
                                List.of(),
                                null,
                                20,
                                2,
                                true))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
    }

    private CourseVersion publishedVersionWithPrerequisiteChain() throws JsonProcessingException {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(
                new ModuleOutlineDto(
                        MODULE_ID.toString(),
                        "Module 1 - Architecture foundation",
                        "Learn service ownership, API boundaries and local infra.",
                        1,
                        "PUBLISHED",
                        List.of(new ItemOutlineDto(
                                SNAPSHOT_ITEM_ID.toString(),
                                "LESSON",
                                "30000000-0000-0000-0000-000000000101",
                                "Read architecture overview",
                                "Review architecture guide.",
                                null,
                                List.of(),
                                null,
                                25,
                                1,
                                true)),
                        List.of()),
                new ModuleOutlineDto(
                        MODULE_2_ID.toString(),
                        "Module 2 - Release readiness",
                        "Practice launch-readiness checks.",
                        2,
                        "PUBLISHED",
                        List.of(new ItemOutlineDto(
                                SNAPSHOT_ITEM_2_ID.toString(),
                                "LESSON",
                                "30000000-0000-0000-0000-000000000102",
                                "Run release checklist",
                                "Complete the release checklist.",
                                null,
                                List.of(),
                                null,
                                20,
                                1,
                                true)),
                        List.of(new ModulePrerequisiteOutlineDto(MODULE_ID.toString(), "MODULE_COMPLETED"))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
    }

    private CourseVersion publishedVersionWithLockedDocumentItem() throws JsonProcessingException {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(
                new ModuleOutlineDto(
                        MODULE_ID.toString(),
                        "Module 1 - Architecture foundation",
                        "Learn service ownership, API boundaries and local infra.",
                        1,
                        "PUBLISHED",
                        List.of(new ItemOutlineDto(
                                SNAPSHOT_ITEM_ID.toString(),
                                "LESSON",
                                "30000000-0000-0000-0000-000000000101",
                                "Read architecture overview",
                                "Review architecture guide.",
                                null,
                                List.of(),
                                null,
                                25,
                                1,
                                true)),
                        List.of()),
                new ModuleOutlineDto(
                        MODULE_2_ID.toString(),
                        "Module 2 - Release readiness",
                        "Practice launch-readiness checks.",
                        2,
                        "PUBLISHED",
                        List.of(new ItemOutlineDto(
                                SNAPSHOT_ITEM_2_ID.toString(),
                                "MATERIAL",
                                "30000000-0000-0000-0000-000000000102",
                                "Download release workbook",
                                "Review the release workbook.",
                                null,
                                List.of(DOCUMENT_MEDIA_ID.toString()),
                                null,
                                20,
                                1,
                                true)),
                        List.of(new ModulePrerequisiteOutlineDto(MODULE_ID.toString(), "MODULE_COMPLETED"))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
    }

    private CourseVersion publishedVersionWithLockedQuizItem(UUID quizId) throws JsonProcessingException {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(
                new ModuleOutlineDto(
                        MODULE_ID.toString(),
                        "Module 1 - Architecture foundation",
                        "Learn service ownership, API boundaries and local infra.",
                        1,
                        "PUBLISHED",
                        List.of(new ItemOutlineDto(
                                SNAPSHOT_ITEM_ID.toString(),
                                "LESSON",
                                "30000000-0000-0000-0000-000000000101",
                                "Read architecture overview",
                                "Review architecture guide.",
                                null,
                                List.of(),
                                null,
                                25,
                                1,
                                true)),
                        List.of()),
                new ModuleOutlineDto(
                        MODULE_2_ID.toString(),
                        "Module 2 - Release readiness",
                        "Practice launch-readiness checks.",
                        2,
                        "PUBLISHED",
                        List.of(new ItemOutlineDto(
                                SNAPSHOT_ITEM_2_ID.toString(),
                                "QUIZ",
                                quizId.toString(),
                                "Release readiness quiz",
                                "Pass the readiness quiz.",
                                null,
                                List.of(),
                                null,
                                20,
                                1,
                                true)),
                        List.of(new ModulePrerequisiteOutlineDto(MODULE_ID.toString(), "MODULE_COMPLETED"))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
    }
}
