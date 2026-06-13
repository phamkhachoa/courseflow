package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.CourseDtos.PresignedDownloadDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.CourseProgressDto;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseVersionJpaRepository;
import edu.courseflow.course.repository.LearnerItemProgressJpaRepository;
import edu.courseflow.course.repository.LearnerModuleProgressJpaRepository;
import edu.courseflow.course.repository.ModuleItemJpaRepository;
import edu.courseflow.course.repository.ModulePrerequisiteJpaRepository;
import edu.courseflow.course.repository.OutboxEventJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
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
    private static final UUID SNAPSHOT_ITEM_ID = UUID.fromString("30000000-0000-0000-0000-000000002001");
    private static final UUID DOCUMENT_MEDIA_ID = UUID.fromString("91000000-0000-0000-0000-000000000301");
    private static final UUID OUTSIDE_MEDIA_ID = UUID.fromString("91000000-0000-0000-0000-000000000999");
    private static final CurrentUser LEARNER = new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));

    @Mock
    private CourseModuleJpaRepository modules;
    @Mock
    private ModuleItemJpaRepository items;
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
                versions,
                prerequisites,
                progressRepository,
                itemProgressRepository,
                outbox,
                objectMapper,
                mapper,
                courseAccess,
                restClientBuilder,
                "http://media.test",
                "service-token");
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
        mediaServer.expect(requestTo("http://media.test/internal/media/assets/" + DOCUMENT_MEDIA_ID + "/download-url/trusted"))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header(CourseAccessClient.SERVICE_TOKEN_HEADER, "service-token"))
                .andRespond(withSuccess("""
                        {"storageKey":"demo/docs/se401.pdf","downloadUrl":"https://download.test/se401.pdf","expiresAt":"2026-06-13T00:05:00Z"}
                        """, MediaType.APPLICATION_JSON));

        PresignedDownloadDto grant = service.downloadPublishedMedia(COURSE_ID, DOCUMENT_MEDIA_ID, LEARNER);

        assertThat(grant.downloadUrl()).isEqualTo("https://download.test/se401.pdf");
        mediaServer.verify();
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
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 3, "DRAFT", "2", "approved");
        version.publish(objectMapper.writeValueAsString(List.of(new ModuleOutlineDto(
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
                        true))))), Instant.parse("2026-06-13T00:00:00Z"));
        return version;
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
}
