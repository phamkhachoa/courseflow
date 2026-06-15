package edu.courseflow.assignment.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradeSubmissionRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradingQueueItemDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RequestUploadUrlDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricCriterionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricScoreDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmitAssignmentRequestDto;
import edu.courseflow.assignment.repository.AssignmentRepository;
import edu.courseflow.assignment.repository.AttachmentUploadGrantJpaRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient;
import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AssignmentServiceLifecycleTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID ASSIGNMENT_ID = UUID.fromString("50000000-0000-0000-0000-000000000001");
    private static final UUID SUBMISSION_ID = UUID.fromString("50000000-0000-0000-0000-000000000101");
    private static final UUID RUBRIC_ID = UUID.fromString("60000000-0000-0000-0000-000000000001");
    private static final UUID CRITERION_ID = UUID.fromString("60000000-0000-0000-0000-000000000101");
    private static final String STUDENT_ID = "4";

    @Mock
    private AssignmentRepository assignments;
    @Mock
    private ObjectStorageClient storage;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private LearningAccessClient learningAccess;
    @Mock
    private AttachmentUploadGrantJpaRepository uploadGrants;

    private AssignmentService service;

    @BeforeEach
    void setUp() {
        service = new AssignmentService(assignments, storage, new ObjectMapper(), courseAccess, learningAccess, uploadGrants);
    }

    @Test
    void learnerListHidesDraftFutureAndLockedAssignments() {
        Instant now = Instant.now();
        AssignmentDto open = assignment(ASSIGNMENT_ID, "Open", "PUBLISHED",
                now.minus(Duration.ofDays(1)), now.plus(Duration.ofDays(7)), null, "TEXT");
        AssignmentDto draft = assignment(UUID.randomUUID(), "Draft", "DRAFT",
                null, now.plus(Duration.ofDays(7)), null, "TEXT");
        AssignmentDto future = assignment(UUID.randomUUID(), "Future", "PUBLISHED",
                now.plus(Duration.ofDays(1)), now.plus(Duration.ofDays(7)), null, "TEXT");
        AssignmentDto locked = assignment(UUID.randomUUID(), "Locked", "PUBLISHED",
                now.minus(Duration.ofDays(7)), now.minus(Duration.ofDays(2)), now.minus(Duration.ofDays(1)), "TEXT");
        when(assignments.listByCourse(COURSE_ID)).thenReturn(List.of(open, draft, future, locked));

        List<AssignmentDto> result = service.listVisibleByCourse(COURSE_ID);

        assertThat(result).extracting(AssignmentDto::title).containsExactly("Open");
    }

    @Test
    void learnerStatusesMarkMissingPastDueAssignmentOverdue() {
        AssignmentDto overdue = assignment(ASSIGNMENT_ID, "Past due", "PUBLISHED",
                null, Instant.parse("2000-01-01T00:00:00Z"), null, "TEXT");
        when(assignments.listByCourse(COURSE_ID)).thenReturn(List.of(overdue));
        when(assignments.listSubmissionAttemptsForStudent(List.of(ASSIGNMENT_ID), STUDENT_ID))
                .thenReturn(List.of());

        var result = service.learnerStatuses(COURSE_ID, STUDENT_ID, List.of(ASSIGNMENT_ID));

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().sourceStatus()).isEqualTo("OVERDUE");
        assertThat(result.getFirst().dueAt()).isEqualTo(overdue.dueAt());
        assertThat(result.getFirst().completed()).isFalse();
        assertThat(result.getFirst().overdue()).isTrue();
    }

    @Test
    void learnerStatusesExposeSubmittedAssignmentWithoutMarkingItOverdue() {
        AssignmentDto overdue = assignment(ASSIGNMENT_ID, "Submitted", "PUBLISHED",
                null, Instant.parse("2000-01-01T00:00:00Z"), null, "TEXT");
        when(assignments.listByCourse(COURSE_ID)).thenReturn(List.of(overdue));
        when(assignments.listSubmissionAttemptsForStudent(List.of(ASSIGNMENT_ID), STUDENT_ID))
                .thenReturn(List.of(submission()));

        var result = service.learnerStatuses(COURSE_ID, STUDENT_ID, List.of(ASSIGNMENT_ID));

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().sourceStatus()).isEqualTo("SUBMITTED");
        assertThat(result.getFirst().latestProgressStatus()).isEqualTo("SUBMITTED");
        assertThat(result.getFirst().attemptsUsed()).isEqualTo(1);
        assertThat(result.getFirst().overdue()).isFalse();
    }

    @Test
    void gradingQueueDefaultsToSubmittedAndResubmittedStatuses() {
        AssignmentDto assignment = assignment(ASSIGNMENT_ID, "Queue item", "PUBLISHED",
                null, Instant.now().plus(Duration.ofDays(7)), null, "FILE");
        GradingQueueItemDto queueItem = new GradingQueueItemDto(
                SUBMISSION_ID.toString(),
                ASSIGNMENT_ID.toString(),
                "Queue item",
                COURSE_ID.toString(),
                STUDENT_ID,
                1,
                Instant.now(),
                "SUBMITTED",
                false,
                0,
                new BigDecimal("100"),
                null,
                1);
        when(assignments.listByCourse(COURSE_ID)).thenReturn(List.of(assignment));
        when(assignments.listGradingQueue(List.of(assignment), List.of("SUBMITTED", "RESUBMITTED"), 50))
                .thenReturn(List.of(queueItem));

        List<GradingQueueItemDto> result = service.gradingQueue(COURSE_ID, null, null, 50);

        assertThat(result).containsExactly(queueItem);
    }

    @Test
    void gradingQueueRejectsAssignmentOutsideCourse() {
        when(assignments.listByCourse(COURSE_ID)).thenReturn(List.of());

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.gradingQueue(COURSE_ID, ASSIGNMENT_ID, null, 50));

        assertThat(ex.getMessage()).contains("ASSIGNMENT_NOT_IN_COURSE");
    }

    @Test
    void submitRejectsDraftAssignment() {
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignment(
                ASSIGNMENT_ID, "Draft", "DRAFT", null, Instant.now().plus(Duration.ofDays(7)), null, "TEXT")));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.submit(ASSIGNMENT_ID, STUDENT_ID, textSubmission()));

        assertThat(ex.getMessage()).contains("ASSIGNMENT_NOT_PUBLISHED");
        verify(courseAccess).requireStudentCourseAccess(STUDENT_ID, COURSE_ID);
        verify(assignments, never()).insertSubmission(any(), any(), anyInt(), any(), any(), anyBoolean(), anyInt(), any());
    }

    @Test
    void learnerVisibleGuardRejectsDraftAssignment() {
        AssignmentDto draft = assignment(
                ASSIGNMENT_ID, "Draft", "DRAFT", null, Instant.now().plus(Duration.ofDays(7)), null, "TEXT");

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.requireLearnerVisible(draft));

        assertThat(ex.getMessage()).contains("ASSIGNMENT_NOT_AVAILABLE");
    }

    @Test
    void presignUploadRejectsDraftAssignment() {
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignment(
                ASSIGNMENT_ID, "Draft", "DRAFT", null, Instant.now().plus(Duration.ofDays(7)), null, "FILE")));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.presignUpload(ASSIGNMENT_ID, STUDENT_ID,
                        new RequestUploadUrlDto("answer.pdf", "application/pdf")));

        assertThat(ex.getMessage()).contains("ASSIGNMENT_NOT_PUBLISHED");
        verify(storage, never()).presignPut(any(), any());
    }

    @Test
    void submitAllowsPublishedAssignment() {
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignment(
                ASSIGNMENT_ID, "Open", "PUBLISHED", null, Instant.now().plus(Duration.ofDays(7)), null, "TEXT")));
        when(assignments.nextAttemptNo(ASSIGNMENT_ID, STUDENT_ID)).thenReturn(1);
        when(assignments.insertSubmission(any(), any(), anyInt(), any(), any(), anyBoolean(), anyInt(), any()))
                .thenReturn(submission());

        SubmissionDto result = service.submit(ASSIGNMENT_ID, STUDENT_ID, textSubmission());

        assertThat(result.id()).isEqualTo(SUBMISSION_ID.toString());
        verify(learningAccess).requireSourceAccess(COURSE_ID, STUDENT_ID, "ASSIGNMENT", ASSIGNMENT_ID);
        verify(assignments).insertSubmission(ASSIGNMENT_ID, STUDENT_ID, 1, "Completed work", null, false, 0, List.of());
    }

    @Test
    void submitRejectsWhenLearningAccessPolicyDeniesAssignment() {
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignment(
                ASSIGNMENT_ID, "Open", "PUBLISHED", null, Instant.now().plus(Duration.ofDays(7)), null, "TEXT")));
        doThrow(new ForbiddenException("PREREQUISITE_MODULE_INCOMPLETE"))
                .when(learningAccess).requireSourceAccess(COURSE_ID, STUDENT_ID, "ASSIGNMENT", ASSIGNMENT_ID);

        ForbiddenException ex = assertThrows(ForbiddenException.class,
                () -> service.submit(ASSIGNMENT_ID, STUDENT_ID, textSubmission()));

        assertThat(ex.getMessage()).contains("PREREQUISITE_MODULE_INCOMPLETE");
        verify(assignments, never()).insertSubmission(any(), any(), anyInt(), any(), any(), anyBoolean(), anyInt(), any());
    }

    @Test
    void gradeRejectsRubricScoreForCriterionOutsideAssignmentRubric() {
        UUID otherCriterionId = UUID.fromString("60000000-0000-0000-0000-000000000999");
        when(assignments.findSubmissionById(SUBMISSION_ID)).thenReturn(Optional.of(submission()));
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignmentWithRubric()));
        when(assignments.findRubricByAssignment(ASSIGNMENT_ID)).thenReturn(Optional.of(rubric()));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.grade(SUBMISSION_ID, "9", new GradeSubmissionRequestDto(
                        null,
                        "Needs another pass",
                        List.of(new RubricScoreDto(otherCriterionId.toString(), new BigDecimal("4"), null)))));

        assertThat(ex.getMessage()).contains("RUBRIC_CRITERION_NOT_ON_ASSIGNMENT");
        verify(assignments, never()).replaceRubricScores(any(), any());
        verify(assignments, never()).recordGrade(any(), any(), any(), any(), any(), any());
    }

    @Test
    void gradeRejectsRubricScoreAboveCriterionMax() {
        when(assignments.findSubmissionById(SUBMISSION_ID)).thenReturn(Optional.of(submission()));
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignmentWithRubric()));
        when(assignments.findRubricByAssignment(ASSIGNMENT_ID)).thenReturn(Optional.of(rubric()));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.grade(SUBMISSION_ID, "9", new GradeSubmissionRequestDto(
                        null,
                        "Too generous",
                        List.of(new RubricScoreDto(CRITERION_ID.toString(), new BigDecimal("11"), null)))));

        assertThat(ex.getMessage()).contains("RUBRIC_SCORE_EXCEEDS_CRITERION_MAX");
        verify(assignments, never()).replaceRubricScores(any(), any());
        verify(assignments, never()).recordGrade(any(), any(), any(), any(), any(), any());
    }

    @Test
    void gradeRejectsDuplicateRubricCriterionScores() {
        when(assignments.findSubmissionById(SUBMISSION_ID)).thenReturn(Optional.of(submission()));
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignmentWithRubric()));
        when(assignments.findRubricByAssignment(ASSIGNMENT_ID)).thenReturn(Optional.of(rubric()));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.grade(SUBMISSION_ID, "9", new GradeSubmissionRequestDto(
                        null,
                        "Duplicated criterion",
                        List.of(
                                new RubricScoreDto(CRITERION_ID.toString(), new BigDecimal("4"), null),
                                new RubricScoreDto(CRITERION_ID.toString(), new BigDecimal("5"), null)))));

        assertThat(ex.getMessage()).contains("DUPLICATE_RUBRIC_CRITERION_SCORE");
        verify(assignments, never()).replaceRubricScores(any(), any());
        verify(assignments, never()).recordGrade(any(), any(), any(), any(), any(), any());
    }

    @Test
    void gradeAcceptsRubricScoreWithinCriterionMax() {
        List<RubricScoreDto> scores = List.of(
                new RubricScoreDto(CRITERION_ID.toString(), new BigDecimal("8.50"), "Solid"));
        when(assignments.findSubmissionById(SUBMISSION_ID)).thenReturn(Optional.of(submission()));
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignmentWithRubric()));
        when(assignments.findRubricByAssignment(ASSIGNMENT_ID)).thenReturn(Optional.of(rubric()));

        SubmissionDto result = service.grade(SUBMISSION_ID, "9",
                new GradeSubmissionRequestDto(null, "Good work", scores));

        assertThat(result.id()).isEqualTo(SUBMISSION_ID.toString());
        verify(assignments).replaceRubricScores(SUBMISSION_ID, scores);
        verify(assignments).recordGrade(
                eq(SUBMISSION_ID),
                eq("9"),
                eq(new BigDecimal("8.50")),
                eq(BigDecimal.ZERO),
                eq(new BigDecimal("8.50")),
                eq("Good work"));
    }

    private static SubmitAssignmentRequestDto textSubmission() {
        return new SubmitAssignmentRequestDto("Completed work", null, List.of());
    }

    private static AssignmentDto assignment(UUID id, String title, String status,
            Instant availableAt, Instant dueAt, Instant lockAt, String submissionTypes) {
        return new AssignmentDto(
                id.toString(),
                COURSE_ID.toString(),
                title,
                "PROJECT",
                "Instructions",
                availableAt,
                dueAt,
                lockAt,
                new BigDecimal("100"),
                status,
                submissionTypes,
                1,
                false,
                BigDecimal.ZERO,
                "DAY",
                new BigDecimal("100"),
                null);
    }

    private static AssignmentDto assignmentWithRubric() {
        AssignmentDto base = assignment(
                ASSIGNMENT_ID, "Open", "PUBLISHED", null, Instant.now().plus(Duration.ofDays(7)), null, "TEXT");
        return new AssignmentDto(
                base.id(),
                base.courseId(),
                base.title(),
                base.assignmentType(),
                base.instructions(),
                base.availableAt(),
                base.dueAt(),
                base.lockAt(),
                base.maxScore(),
                base.status(),
                base.submissionTypes(),
                base.maxAttempts(),
                base.allowResubmission(),
                base.latePenaltyPercent(),
                base.latePenaltyInterval(),
                base.latePenaltyMaxPercent(),
                RUBRIC_ID.toString());
    }

    private static RubricDto rubric() {
        return new RubricDto(
                RUBRIC_ID.toString(),
                ASSIGNMENT_ID.toString(),
                "Project rubric",
                new BigDecimal("10"),
                List.of(new RubricCriterionDto(
                        CRITERION_ID.toString(),
                        "Correctness",
                        "Meets the requirements",
                        new BigDecimal("10"),
                        1)));
    }

    private static SubmissionDto submission() {
        return new SubmissionDto(
                SUBMISSION_ID.toString(),
                ASSIGNMENT_ID.toString(),
                STUDENT_ID,
                1,
                Instant.now(),
                "SUBMITTED",
                "Completed work",
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
