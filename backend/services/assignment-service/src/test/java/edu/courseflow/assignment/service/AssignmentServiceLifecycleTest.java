package edu.courseflow.assignment.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RequestUploadUrlDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmitAssignmentRequestDto;
import edu.courseflow.assignment.repository.AssignmentRepository;
import edu.courseflow.assignment.repository.AttachmentUploadGrantJpaRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
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
    private static final String STUDENT_ID = "4";

    @Mock
    private AssignmentRepository assignments;
    @Mock
    private ObjectStorageClient storage;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private AttachmentUploadGrantJpaRepository uploadGrants;

    private AssignmentService service;

    @BeforeEach
    void setUp() {
        service = new AssignmentService(assignments, storage, new ObjectMapper(), courseAccess, uploadGrants);
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
        verify(assignments).insertSubmission(ASSIGNMENT_ID, STUDENT_ID, 1, "Completed work", null, false, 0, List.of());
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
