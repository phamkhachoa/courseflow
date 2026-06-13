package edu.courseflow.deadline.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.deadline.dto.DeadlineDtos.CreateReminderPolicyRequestDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderPolicyDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ScheduleReminderRequestDto;
import edu.courseflow.deadline.service.DeadlineService;
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
class DeadlineControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID POLICY_ID = UUID.fromString("84000000-0000-0000-0000-000000000001");

    @Mock
    private DeadlineService deadlines;
    @Mock
    private CourseAccessClient courseAccess;

    private DeadlineController controller;

    @BeforeEach
    void setUp() {
        controller = new DeadlineController(deadlines, courseAccess);
    }

    @Test
    void coursePoliciesRequireScopedCourseStaffAccessForStaff() {
        CurrentUser instructor = instructor();
        when(deadlines.listPolicies(Optional.of(COURSE_ID))).thenReturn(List.of());

        controller.policies(Optional.of(COURSE_ID), instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void createPolicyRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        CreateReminderPolicyRequestDto request = new CreateReminderPolicyRequestDto(
                COURSE_ID.toString(), "One day before", 1440, "INBOX");
        when(deadlines.createPolicy(request)).thenReturn(new ReminderPolicyDto(
                POLICY_ID.toString(), COURSE_ID.toString(), "One day before", 1440, "INBOX", true));

        controller.createPolicy(request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void schedulingReminderRequiresPolicyCourseStaffAccess() {
        CurrentUser instructor = instructor();
        ScheduleReminderRequestDto request = new ScheduleReminderRequestDto(
                "50000000-0000-0000-0000-000000000001",
                "4",
                POLICY_ID.toString(),
                Instant.parse("2026-07-01T00:00:00Z"));
        when(deadlines.courseIdForPolicy(POLICY_ID)).thenReturn(COURSE_ID);

        controller.schedule(request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }
}
