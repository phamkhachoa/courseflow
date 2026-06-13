package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.model.ModuleItem;
import edu.courseflow.course.repository.CourseJpaRepository;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseVersionJpaRepository;
import edu.courseflow.course.repository.ModuleItemJpaRepository;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CourseAuthoringServiceReviewabilityTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID DEPARTMENT_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");
    private static final UUID MODULE_ID = UUID.fromString("30000000-0000-0000-0000-000000001001");
    private static final UUID ITEM_ID = UUID.fromString("30000000-0000-0000-0000-000000002001");
    private static final UUID VIDEO_ID = UUID.fromString("83000000-0000-0000-0000-000000000001");
    private static final UUID QUIZ_ID = UUID.fromString("b3000000-0000-0000-0000-000000000001");
    private static final UUID ASSIGNMENT_ID = UUID.fromString("50000000-0000-0000-0000-000000000001");
    private static final CurrentUser OWNER = new CurrentUser(2L, "owner@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));

    @Mock
    private CourseJpaRepository courses;
    @Mock
    private CourseModuleJpaRepository modules;
    @Mock
    private ModuleItemJpaRepository items;
    @Mock
    private CourseVersionJpaRepository versions;
    @Mock
    private CourseMapper mapper;
    @Mock
    private CourseContentReadinessClient readinessClient;

    private CourseAuthoringService service;

    @BeforeEach
    void setUp() {
        service = new CourseAuthoringService(courses, modules, items, versions, new ObjectMapper(), mapper,
                readinessClient);
    }

    @Test
    void submitForReviewRejectsVideoItemWithoutMedia() {
        Course course = course();
        CourseModule module = module();
        ModuleItem video = item("VIDEO", ITEM_ID.toString(), null, null, null, null);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(video));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.submitForReview(COURSE_ID, OWNER));

        assertThat(ex.getMessage()).contains("video item without video media");
    }

    @Test
    void submitForReviewRejectsVideoItemThatIsNotReady() {
        Course course = course();
        CourseModule module = module();
        ModuleItem video = item("VIDEO", VIDEO_ID.toString(), null, VIDEO_ID, null, null);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(video));
        when(readinessClient.videoIssue(VIDEO_ID, COURSE_ID)).thenReturn(Optional.of("video asset is not READY"));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.submitForReview(COURSE_ID, OWNER));

        assertThat(ex.getMessage()).contains("video asset is not READY");
    }

    @Test
    void submitForReviewRejectsAssessmentPlaceholderReference() {
        Course course = course();
        CourseModule module = module();
        ModuleItem quiz = item("QUIZ", ITEM_ID.toString(), "Quiz", null, null, null);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(quiz));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.submitForReview(COURSE_ID, OWNER));

        assertThat(ex.getMessage()).contains("without a linked quiz");
    }

    @Test
    void submitForReviewRejectsDraftQuizReference() {
        Course course = course();
        CourseModule module = module();
        ModuleItem quiz = item("QUIZ", QUIZ_ID.toString(), "Quiz", null, null, null);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(quiz));
        when(readinessClient.quizIssue(QUIZ_ID, COURSE_ID)).thenReturn(Optional.of("linked quiz is not published"));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.submitForReview(COURSE_ID, OWNER));

        assertThat(ex.getMessage()).contains("linked quiz is not published");
    }

    @Test
    void submitForReviewRejectsDraftAssignmentReference() {
        Course course = course();
        CourseModule module = module();
        ModuleItem assignment = item("ASSIGNMENT", ASSIGNMENT_ID.toString(), "Assignment", null, null, null);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(assignment));
        when(readinessClient.assignmentIssue(ASSIGNMENT_ID, COURSE_ID))
                .thenReturn(Optional.of("linked assignment is not published"));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.submitForReview(COURSE_ID, OWNER));

        assertThat(ex.getMessage()).contains("linked assignment is not published");
    }

    @Test
    void submitForReviewAcceptsReadyTextLesson() {
        Course course = course();
        CourseModule module = module();
        ModuleItem lesson = item("LESSON", ITEM_ID.toString(), "Read the notes", null, null, null);
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 1, "DRAFT", "2", "Initial draft");
        ModuleOutlineDto moduleDto = new ModuleOutlineDto(MODULE_ID.toString(), "Module 1", null, 1, "DRAFT", List.of());
        CourseDraftDto draft = new CourseDraftDto(
                COURSE_ID.toString(),
                course.getTitle(),
                course.getSlug(),
                course.getSummary(),
                course.getStatus(),
                "IN_REVIEW",
                1,
                "2",
                List.of(moduleDto));
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(lesson));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 1)).thenReturn(Optional.of(version));
        when(mapper.toOutlineDto(lesson)).thenReturn(new ItemOutlineDto(
                ITEM_ID.toString(), "LESSON", ITEM_ID.toString(), "Item", "Read the notes",
                null, List.of(), null, 10, 1, true));
        when(mapper.toOutlineDto(module, List.of(mapper.toOutlineDto(lesson)))).thenReturn(moduleDto);
        when(mapper.toDraftDto(course, List.of(moduleDto))).thenReturn(draft);

        CourseDraftDto result = service.submitForReview(COURSE_ID, OWNER);

        assertThat(result).isSameAs(draft);
        assertThat(course.getReviewState()).isEqualTo("IN_REVIEW");
    }

    private static Course course() {
        return new Course(
                COURSE_ID,
                "SA-101",
                "System Architecture",
                "system-architecture",
                "Architecture foundations",
                DEPARTMENT_ID,
                "2",
                "BEGINNER");
    }

    private static CourseModule module() {
        return new CourseModule(MODULE_ID, COURSE_ID, "Module 1", null, 1, "DRAFT");
    }

    private static ModuleItem item(String itemType, String refId, String description,
                                   UUID videoMediaId, List<String> documentMediaIds, String contentUrl) {
        return new ModuleItem(
                ITEM_ID,
                MODULE_ID,
                itemType,
                refId,
                "Item",
                description,
                videoMediaId,
                documentMediaIds,
                contentUrl,
                10,
                1,
                true);
    }
}
