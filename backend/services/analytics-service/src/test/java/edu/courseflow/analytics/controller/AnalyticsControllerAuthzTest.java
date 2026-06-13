package edu.courseflow.analytics.controller;

import static org.mockito.ArgumentMatchers.argThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import edu.courseflow.analytics.dto.AnalyticsDtos.CourseMetricDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.RecordActivityRequestDto;
import edu.courseflow.analytics.service.AnalyticsService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
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
class AnalyticsControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");

    @Mock
    private AnalyticsService analytics;
    @Mock
    private CourseAccessClient courseAccess;

    private AnalyticsController controller;

    @BeforeEach
    void setUp() {
        controller = new AnalyticsController(analytics, courseAccess);
    }

    @Test
    void courseMetricsRequireScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(analytics.courseMetric(COURSE_ID)).thenReturn(new CourseMetricDto(
                COURSE_ID.toString(), 10, 5, new BigDecimal("82.50"), 3, Instant.now()));

        controller.courseMetric(COURSE_ID, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void learnerActivityRequiresCourseAccessAndUsesCallerStudentId() {
        CurrentUser learner = learner();
        RecordActivityRequestDto request = new RecordActivityRequestDto(
                "999", COURSE_ID.toString(), "VIDEO_WATCHED", 12);

        controller.recordActivity(request, learner);

        verify(courseAccess).requireCourseAccess(learner, COURSE_ID);
        verify(analytics).recordActivity(argThat(trusted ->
                "4".equals(trusted.studentId())
                        && COURSE_ID.toString().equals(trusted.courseId())
                        && "VIDEO_WATCHED".equals(trusted.activityType())));
    }

    @Test
    void staffEngagementWithCourseFilterRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(analytics.engagement("4", COURSE_ID.toString())).thenReturn(List.of());

        controller.engagement("4", COURSE_ID.toString(), instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void staffEngagementWithoutCourseFilterRequiresPlatformAdmin() {
        CurrentUser instructor = instructor();

        assertThrows(ResponseStatusException.class, () -> controller.engagement("4", null, instructor));
        verifyNoInteractions(analytics);
    }

    @Test
    void platformAdminCanReadUnscopedStudentEngagement() {
        CurrentUser admin = scopedUser(1L, "admin@courseflow.local", "ADMIN", "PLATFORM", null);
        when(analytics.engagement("4", null)).thenReturn(List.of());

        controller.engagement("4", null, admin);

        verify(analytics).engagement("4", null);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static CurrentUser learner() {
        return new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));
    }

    private static CurrentUser scopedUser(Long id, String email, String role, String scopeType, String scopeId) {
        return new CurrentUser(
                id,
                email,
                role,
                Set.of(role),
                Set.of(new CurrentUser.RoleAssignment(role, scopeType, scopeId)));
    }
}
