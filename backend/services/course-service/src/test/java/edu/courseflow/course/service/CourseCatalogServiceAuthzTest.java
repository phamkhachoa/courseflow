package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.repository.CourseCatalogRepository;
import java.time.Instant;
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
class CourseCatalogServiceAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID DEPARTMENT_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");
    private static final UUID OTHER_DEPARTMENT_ID = UUID.fromString("20000000-0000-0000-0000-000000000999");

    @Mock
    private CourseCatalogRepository courses;
    @Mock
    private CourseAuthoringService authoring;

    private CourseCatalogService service;

    @BeforeEach
    void setUp() {
        service = new CourseCatalogService(courses, authoring, new ObjectMapper().findAndRegisterModules());
    }

    @Test
    void orgAdminListsOnlyCoursesFromScopedDepartment() {
        CurrentUser orgAdmin = userWithScope(9L, "org-admin@courseflow.local", "ORG_ADMIN", "DEPARTMENT", DEPARTMENT_ID);
        CourseDto course = courseDto(DEPARTMENT_ID, "owner-2");
        when(courses.listByDepartmentIds(List.of(DEPARTMENT_ID), Optional.of("DRAFT"))).thenReturn(List.of(course));

        List<CourseDto> result = service.list(Optional.of("DRAFT"), orgAdmin);

        assertThat(result).containsExactly(course);
        verify(courses).listByDepartmentIds(List.of(DEPARTMENT_ID), Optional.of("DRAFT"));
    }

    @Test
    void orgAdminCanArchiveCourseInOwnDepartment() {
        CurrentUser orgAdmin = userWithScope(9L, "org-admin@courseflow.local", "ORG_ADMIN", "DEPARTMENT", DEPARTMENT_ID);
        CourseDto course = courseDto(DEPARTMENT_ID, "owner-2");
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        CourseDto result = service.archive(COURSE_ID, orgAdmin);

        assertThat(result).isSameAs(course);
        verify(courses).updateStatus(COURSE_ID, "ARCHIVED");
    }

    @Test
    void orgAdminCannotPublishCourseOutsideDepartment() {
        CurrentUser orgAdmin = userWithScope(
                9L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                OTHER_DEPARTMENT_ID);
        CourseDto course = courseDto(DEPARTMENT_ID, "owner-2");
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class, () -> service.publish(COURSE_ID, orgAdmin));
        verifyNoInteractions(authoring);
    }

    private static CourseDto courseDto(UUID departmentId, String ownerId) {
        return new CourseDto(
                COURSE_ID.toString(),
                "SA-101",
                "System Architecture",
                "system-architecture",
                "Architecture foundations",
                departmentId.toString(),
                ownerId,
                "BEGINNER",
                "DRAFT",
                Instant.now(),
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
