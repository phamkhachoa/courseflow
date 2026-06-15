package edu.courseflow.assignment.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.when;

import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.CreateAssignmentRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradeSubmissionRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradingQueueItemDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmitAssignmentRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.service.AssignmentService;
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

@ExtendWith(MockitoExtension.class)
class AssignmentControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID ASSIGNMENT_ID = UUID.fromString("50000000-0000-0000-0000-000000000001");
    private static final UUID SUBMISSION_ID = UUID.fromString("50000000-0000-0000-0000-000000000101");

    @Mock
    private AssignmentService assignments;
    @Mock
    private CourseAccessClient courseAccess;

    private AssignmentController controller;

    @BeforeEach
    void setUp() {
        controller = new AssignmentController(assignments, courseAccess);
    }

    @Test
    void createRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        CreateAssignmentRequestDto request = new CreateAssignmentRequestDto(
                COURSE_ID.toString(),
                "Capstone",
                "PROJECT",
                "Build the final project",
                null,
                Instant.parse("2026-07-01T00:00:00Z"),
                null,
                new BigDecimal("100"),
                "FILE",
                1,
                false,
                BigDecimal.ZERO,
                "DAY",
                new BigDecimal("100"));
        when(assignments.create(request)).thenReturn(assignment());

        controller.create(request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments).create(request);
    }

    @Test
    void gradingRequiresScopedCourseStaffAccessForSubmissionCourse() {
        CurrentUser instructor = instructor();
        GradeSubmissionRequestDto request = new GradeSubmissionRequestDto(new BigDecimal("88"), "Good work", List.of());
        when(assignments.getSubmission(SUBMISSION_ID)).thenReturn(submission("4"));
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment());
        when(assignments.grade(SUBMISSION_ID, "9", request)).thenReturn(submission("4"));

        controller.grade(SUBMISSION_ID, request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments).grade(SUBMISSION_ID, "9", request);
    }

    @Test
    void staffListingSubmissionsRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment());
        when(assignments.listSubmissions(ASSIGNMENT_ID, "4")).thenReturn(List.of(submission("4")));

        controller.listSubmissions(ASSIGNMENT_ID, "4", instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments).listSubmissions(ASSIGNMENT_ID, "4");
    }

    @Test
    void gradingQueueRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        GradingQueueItemDto item = new GradingQueueItemDto(
                SUBMISSION_ID.toString(),
                ASSIGNMENT_ID.toString(),
                "Capstone",
                COURSE_ID.toString(),
                "4",
                1,
                Instant.parse("2026-06-20T00:00:00Z"),
                "SUBMITTED",
                false,
                0,
                new BigDecimal("100"),
                null,
                0);
        when(assignments.gradingQueue(COURSE_ID, ASSIGNMENT_ID, "SUBMITTED", 25)).thenReturn(List.of(item));

        controller.gradingQueue(COURSE_ID, ASSIGNMENT_ID, "SUBMITTED", 25, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments).gradingQueue(COURSE_ID, ASSIGNMENT_ID, "SUBMITTED", 25);
    }

    @Test
    void learnerSubmitRequiresCourseAccessBeforeServiceSubmit() {
        CurrentUser student = student();
        SubmitAssignmentRequestDto request = new SubmitAssignmentRequestDto("Done", null, List.of());
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment());
        when(assignments.submit(ASSIGNMENT_ID, "4", request)).thenReturn(submission("4"));

        controller.submit(ASSIGNMENT_ID, request, student);

        verify(courseAccess).requireCourseAccess(student, COURSE_ID);
        verify(assignments).submit(ASSIGNMENT_ID, "4", request);
    }

    @Test
    void publishRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment());
        when(assignments.publish(ASSIGNMENT_ID)).thenReturn(assignment());

        controller.publish(ASSIGNMENT_ID, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments).publish(ASSIGNMENT_ID);
    }

    @Test
    void draftRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment());
        when(assignments.draft(ASSIGNMENT_ID)).thenReturn(assignment());

        controller.draft(ASSIGNMENT_ID, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments).draft(ASSIGNMENT_ID);
    }

    @Test
    void archiveRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment());
        when(assignments.archive(ASSIGNMENT_ID)).thenReturn(assignment());

        controller.archive(ASSIGNMENT_ID, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments).archive(ASSIGNMENT_ID);
    }

    @Test
    void learnerDetailRequiresCourseAccessAndVisibleAssignment() {
        CurrentUser student = student();
        AssignmentDto assignment = assignment();
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment);

        controller.get(ASSIGNMENT_ID, student);

        verify(courseAccess).requireCourseAccess(student, COURSE_ID);
        verify(assignments).requireLearnerVisible(assignment);
    }

    @Test
    void staffDetailUsesStaffScopeWithoutLearnerVisibilityGuard() {
        CurrentUser instructor = instructor();
        AssignmentDto assignment = assignment();
        when(assignments.get(ASSIGNMENT_ID)).thenReturn(assignment);

        controller.get(ASSIGNMENT_ID, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
        verify(assignments, never()).requireLearnerVisible(assignment);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static CurrentUser student() {
        return new CurrentUser(4L, "student@courseflow.local", "STUDENT", Set.of("STUDENT"));
    }

    private static AssignmentDto assignment() {
        return new AssignmentDto(
                ASSIGNMENT_ID.toString(),
                COURSE_ID.toString(),
                "Capstone",
                "PROJECT",
                "Build the final project",
                null,
                Instant.parse("2026-07-01T00:00:00Z"),
                null,
                new BigDecimal("100"),
                "PUBLISHED",
                "FILE",
                1,
                false,
                BigDecimal.ZERO,
                "DAY",
                new BigDecimal("100"),
                null);
    }

    private static SubmissionDto submission(String studentId) {
        return new SubmissionDto(
                SUBMISSION_ID.toString(),
                ASSIGNMENT_ID.toString(),
                studentId,
                1,
                Instant.parse("2026-06-20T00:00:00Z"),
                "SUBMITTED",
                null,
                null,
                false,
                0,
                null,
                null,
                null,
                null,
                null,
                null,
                List.of());
    }
}
