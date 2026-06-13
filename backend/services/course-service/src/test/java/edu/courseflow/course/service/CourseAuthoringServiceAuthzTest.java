package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.ReviewDecisionRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.Course;
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
class CourseAuthoringServiceAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID OTHER_COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000999");
    private static final UUID DEPARTMENT_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");
    private static final UUID OTHER_DEPARTMENT_ID = UUID.fromString("20000000-0000-0000-0000-000000000999");

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
        service = new CourseAuthoringService(
                courses,
                modules,
                items,
                versions,
                new ObjectMapper(),
                mapper,
                readinessClient);
    }

    @Test
    void departmentOrgAdminCanApproveCourseInOwnDepartment() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CourseDraftDto approved = draftDto(course, "APPROVED");
        CurrentUser orgAdmin = userWithScope(9L, "org-admin@courseflow.local", "ORG_ADMIN", "DEPARTMENT", DEPARTMENT_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of());
        when(mapper.toDraftDto(course, List.of())).thenReturn(approved);

        CourseDraftDto result = service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok"), orgAdmin);

        assertThat(result).isSameAs(approved);
        assertThat(course.getReviewState()).isEqualTo("APPROVED");
    }

    @Test
    void orgAdminCannotApproveCourseOutsideDepartment() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CurrentUser orgAdmin = userWithScope(
                9L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                OTHER_DEPARTMENT_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class,
                () -> service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok"), orgAdmin));
    }

    @Test
    void courseScopedInstructorCanApproveSameCourseWhenNotOwner() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CourseDraftDto approved = draftDto(course, "APPROVED");
        CurrentUser instructor = userWithScope(9L, "reviewer@courseflow.local", "INSTRUCTOR", "COURSE", COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of());
        when(mapper.toDraftDto(course, List.of())).thenReturn(approved);

        CourseDraftDto result = service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok"), instructor);

        assertThat(result).isSameAs(approved);
        assertThat(course.getReviewState()).isEqualTo("APPROVED");
    }

    @Test
    void courseScopedInstructorCannotApproveAnotherCourse() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CurrentUser instructor = userWithScope(
                9L,
                "reviewer@courseflow.local",
                "INSTRUCTOR",
                "COURSE",
                OTHER_COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class,
                () -> service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok"), instructor));
    }

    @Test
    void ownerCannotApproveOwnCourseEvenWithScopedInstructorRole() {
        Course course = inReviewCourse("9", DEPARTMENT_ID);
        CurrentUser owner = userWithScope(9L, "owner@courseflow.local", "INSTRUCTOR", "COURSE", COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class,
                () -> service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok"), owner));
    }

    private static Course inReviewCourse(String ownerId, UUID departmentId) {
        Course course = new Course(
                COURSE_ID,
                "SA-101",
                "System Architecture",
                "system-architecture",
                "Architecture foundations",
                departmentId,
                ownerId,
                "BEGINNER");
        course.setReviewState("IN_REVIEW");
        return course;
    }

    private static CourseDraftDto draftDto(Course course, String reviewState) {
        return new CourseDraftDto(
                course.getId().toString(),
                course.getTitle(),
                course.getSlug(),
                course.getSummary(),
                course.getStatus(),
                reviewState,
                course.getCurrentVersionNo(),
                course.getLastAuthoredBy(),
                List.of());
    }

    private static CurrentUser userWithScope(
            Long id,
            String email,
            String role,
            String scopeType,
            UUID scopeId) {
        return new CurrentUser(
                id,
                email,
                role,
                Set.of(role),
                Set.of(new CurrentUser.RoleAssignment(role, scopeType, scopeId == null ? null : scopeId.toString())));
    }
}
