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
import edu.courseflow.assignment.dto.AssignmentDtos.AttachmentRef;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmitAssignmentRequestDto;
import edu.courseflow.assignment.model.AttachmentUploadGrant;
import edu.courseflow.assignment.repository.AssignmentRepository;
import edu.courseflow.assignment.repository.AttachmentUploadGrantJpaRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient.PresignedUrl;
import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AssignmentServiceAttachmentGrantTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID ASSIGNMENT_ID = UUID.fromString("50000000-0000-0000-0000-000000000001");
    private static final UUID SUBMISSION_ID = UUID.fromString("50000000-0000-0000-0000-000000000101");
    private static final String STUDENT_ID = "4";
    private static final String STORAGE_KEY = "submissions/50000000-0000-0000-0000-000000000001/4/upload.pdf";

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
    void presignUploadStoresGrantForAuthenticatedStudent() {
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignment()));
        when(storage.buildKey("submissions/" + ASSIGNMENT_ID + "/" + STUDENT_ID, "answer.pdf"))
                .thenReturn(STORAGE_KEY);
        when(storage.presignPut(STORAGE_KEY, "application/pdf"))
                .thenReturn(new PresignedUrl(STORAGE_KEY, "https://storage/upload", Instant.now().plusSeconds(3600)));

        service.presignUpload(ASSIGNMENT_ID, STUDENT_ID,
                new edu.courseflow.assignment.dto.AssignmentDtos.RequestUploadUrlDto("answer.pdf", "application/pdf"));

        ArgumentCaptor<AttachmentUploadGrant> captor = ArgumentCaptor.forClass(AttachmentUploadGrant.class);
        verify(learningAccess).requireSourceAccess(COURSE_ID, STUDENT_ID, "ASSIGNMENT", ASSIGNMENT_ID);
        verify(uploadGrants).save(captor.capture());
        assertThat(captor.getValue().getAssignmentId()).isEqualTo(ASSIGNMENT_ID);
        assertThat(captor.getValue().getStudentId()).isEqualTo(STUDENT_ID);
        assertThat(captor.getValue().getStorageKey()).isEqualTo(STORAGE_KEY);
        assertThat(captor.getValue().getFileName()).isEqualTo("answer.pdf");
    }

    @Test
    void submitRejectsAttachmentWithoutOwnedGrant() {
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignment()));

        assertThrows(BadRequestException.class,
                () -> service.submit(ASSIGNMENT_ID, STUDENT_ID, submitWithAttachment()));

        verify(assignments, never()).insertSubmission(any(), any(), anyInt(), any(), any(), anyBoolean(),
                anyInt(), any());
    }

    @Test
    void submitUsesGrantMetadataAndConsumesGrant() {
        AttachmentUploadGrant grant = new AttachmentUploadGrant(
                ASSIGNMENT_ID,
                STUDENT_ID,
                STORAGE_KEY,
                "trusted-name.pdf",
                "application/pdf",
                2048L,
                Instant.now().plusSeconds(3600));
        when(assignments.find(ASSIGNMENT_ID)).thenReturn(Optional.of(assignment()));
        when(assignments.nextAttemptNo(ASSIGNMENT_ID, STUDENT_ID)).thenReturn(1);
        when(uploadGrants.findByAssignmentIdAndStudentIdAndStorageKey(ASSIGNMENT_ID, STUDENT_ID, STORAGE_KEY))
                .thenReturn(Optional.of(grant));
        when(storage.exists(STORAGE_KEY)).thenReturn(true);
        when(assignments.insertSubmission(any(), any(), anyInt(), any(), any(), anyBoolean(),
                anyInt(), any())).thenReturn(submission());

        service.submit(ASSIGNMENT_ID, STUDENT_ID, submitWithAttachment());

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<AttachmentRef>> attachmentsCaptor = ArgumentCaptor.forClass(List.class);
        verify(learningAccess).requireSourceAccess(COURSE_ID, STUDENT_ID, "ASSIGNMENT", ASSIGNMENT_ID);
        verify(assignments).insertSubmission(
                any(),
                any(),
                anyInt(),
                any(),
                any(),
                anyBoolean(),
                anyInt(),
                attachmentsCaptor.capture());
        assertThat(attachmentsCaptor.getValue()).singleElement().satisfies(ref -> {
            assertThat(ref.fileName()).isEqualTo("trusted-name.pdf");
            assertThat(ref.storageKey()).isEqualTo(STORAGE_KEY);
            assertThat(ref.contentType()).isEqualTo("application/pdf");
            assertThat(ref.sizeBytes()).isEqualTo(2048L);
        });
        assertThat(grant.isConsumed()).isTrue();
        verify(uploadGrants).save(grant);
    }

    private static AssignmentDto assignment() {
        return new AssignmentDto(
                ASSIGNMENT_ID.toString(),
                COURSE_ID.toString(),
                "Capstone",
                "PROJECT",
                "Submit your final project",
                null,
                Instant.now().plus(Duration.ofDays(10)),
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

    private static SubmitAssignmentRequestDto submitWithAttachment() {
        return new SubmitAssignmentRequestDto(
                null,
                null,
                List.of(new AttachmentRef(
                        null,
                        "client-name.pdf",
                        STORAGE_KEY,
                        "text/plain",
                        999L)));
    }

    private static SubmissionDto submission() {
        return new SubmissionDto(
                SUBMISSION_ID.toString(),
                ASSIGNMENT_ID.toString(),
                STUDENT_ID,
                1,
                Instant.now(),
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
