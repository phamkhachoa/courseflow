package edu.courseflow.analytics.controller;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
import edu.courseflow.analytics.dto.ReportingDtos.TimeSpentDto;
import edu.courseflow.analytics.service.ReportingService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class ReportingControllerAuthzTest {

    private static final String ORG_ID = "20000000-0000-0000-0000-000000000001";
    private static final String OTHER_ORG_ID = "20000000-0000-0000-0000-000000000999";

    @Mock
    private ReportingService reporting;
    @Mock
    private CourseAccessClient courseAccess;

    private ReportingController controller;

    @BeforeEach
    void setUp() {
        controller = new ReportingController(reporting, courseAccess);
    }

    @Test
    void platformAdminCanViewOrgDashboard() {
        CurrentUser admin = userWithScope(1L, "admin@courseflow.local", "ADMIN", "PLATFORM", null);
        OrgDashboardDto dashboard = new OrgDashboardDto(ORG_ID, 5, 8, 62.5, Instant.now());
        when(reporting.orgDashboard(ORG_ID)).thenReturn(dashboard);

        controller.orgDashboard(ORG_ID, admin);

        verify(reporting).orgDashboard(ORG_ID);
    }

    @Test
    void orgAdminCanOnlyViewOwnDepartmentDashboard() {
        CurrentUser orgAdmin = userWithScope(
                2L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                ORG_ID);
        OrgDashboardDto dashboard = new OrgDashboardDto(ORG_ID, 5, 8, 62.5, Instant.now());
        when(reporting.orgDashboard(ORG_ID)).thenReturn(dashboard);

        controller.orgDashboard(ORG_ID, orgAdmin);

        verify(reporting).orgDashboard(ORG_ID);
    }

    @Test
    void orgAdminCannotViewAnotherDepartmentDashboard() {
        CurrentUser orgAdmin = userWithScope(
                2L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                OTHER_ORG_ID);

        assertThrows(ResponseStatusException.class, () -> controller.orgDashboard(ORG_ID, orgAdmin));
        verifyNoInteractions(reporting);
    }

    @Test
    void courseScopedInstructorCannotViewWholeOrgDashboard() {
        CurrentUser instructor = userWithScope(
                3L,
                "instructor@courseflow.local",
                "INSTRUCTOR",
                "COURSE",
                "30000000-0000-0000-0000-000000000001");

        assertThrows(ResponseStatusException.class, () -> controller.orgDashboard(ORG_ID, instructor));
        verifyNoInteractions(reporting);
    }

    @Test
    void learnerCanViewOwnTimeSpent() {
        CurrentUser learner = userWithScope(4L, "learner@courseflow.local", "STUDENT", "PLATFORM", null);
        when(reporting.timeSpent("4")).thenReturn(List.of(
                new TimeSpentDto("4", "30000000-0000-0000-0000-000000000001", 45, Instant.now())));

        controller.timeSpent("4", learner);

        verify(reporting).timeSpent("4");
    }

    @Test
    void platformAdminCanViewStudentRecommendations() {
        CurrentUser admin = userWithScope(1L, "admin@courseflow.local", "ADMIN", "PLATFORM", null);
        when(reporting.recommendations("4", 10)).thenReturn(List.of(
                new RecommendationDto("4", "30000000-0000-0000-0000-000000000001", 0.95, "similar-course")));

        controller.recommendations("4", 10, admin);

        verify(reporting).recommendations("4", 10);
    }

    @Test
    void courseScopedInstructorCannotViewStudentWideAnalyticsWithoutCourseScope() {
        CurrentUser instructor = userWithScope(
                3L,
                "instructor@courseflow.local",
                "INSTRUCTOR",
                "COURSE",
                "30000000-0000-0000-0000-000000000001");

        assertThrows(ResponseStatusException.class, () -> controller.timeSpent("4", instructor));
        assertThrows(ResponseStatusException.class, () -> controller.recommendations("4", 10, instructor));
        verifyNoInteractions(reporting);
    }

    private static CurrentUser userWithScope(
            Long id,
            String email,
            String role,
            String scopeType,
            String scopeId) {
        return new CurrentUser(
                id,
                email,
                role,
                Set.of(role),
                Set.of(new CurrentUser.RoleAssignment(role, scopeType, scopeId)));
    }
}
