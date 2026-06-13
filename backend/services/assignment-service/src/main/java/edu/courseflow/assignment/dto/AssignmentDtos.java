package edu.courseflow.assignment.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public final class AssignmentDtos {

        private AssignmentDtos() {
        }

        public record AssignmentDto(
                        String id,
                        String courseId,
                        String title,
                        String assignmentType,
                        String instructions,
                        Instant availableAt,
                        Instant dueAt,
                        Instant lockAt,
                        BigDecimal maxScore,
                        String status,
                        String submissionTypes,
                        int maxAttempts,
                        boolean allowResubmission,
                        BigDecimal latePenaltyPercent,
                        String latePenaltyInterval,
                        BigDecimal latePenaltyMaxPercent,
                        String rubricId) {
        }

        public record AssignmentReadinessDto(
                        String id,
                        String courseId,
                        String status) {
        }

        public record SubmissionAttachmentDto(
                        String id,
                        String mediaAssetId,
                        String fileName,
                        String storageKey,
                        String contentType,
                        Long sizeBytes,
                        Instant createdAt) {
        }

        public record SubmissionDto(
                        String id,
                        String assignmentId,
                        String studentId,
                        int attemptNo,
                        Instant submittedAt,
                        String status,
                        String submissionText,
                        String submissionUrl,
                        boolean isLate,
                        int minutesLate,
                        BigDecimal rawScore,
                        BigDecimal latePenaltyApplied,
                        BigDecimal finalScore,
                        String graderId,
                        Instant gradedAt,
                        String feedback,
                        List<SubmissionAttachmentDto> attachments) {
        }

        public record CreateAssignmentRequestDto(
                        @NotBlank String courseId,
                        @NotBlank String title,
                        @NotBlank String assignmentType,
                        String instructions,
                        Instant availableAt,
                        @NotNull Instant dueAt,
                        Instant lockAt,
                        @NotNull @DecimalMin("0.01") BigDecimal maxScore,
                        String submissionTypes,
                        @Min(1) Integer maxAttempts,
                        Boolean allowResubmission,
                        BigDecimal latePenaltyPercent,
                        String latePenaltyInterval,
                        BigDecimal latePenaltyMaxPercent) {
        }

        /**
         * Pointer to a file already stored in object storage (uploaded via this service
         * or media-service).
         */
        public record AttachmentRef(
                        String mediaAssetId,
                        @NotBlank String fileName,
                        @NotBlank String storageKey,
                        String contentType,
                        Long sizeBytes) {
        }

        // studentId is taken from the authenticated caller, never from the request body.
        public record SubmitAssignmentRequestDto(
                        String submissionText,
                        String submissionUrl,
                        @Valid List<AttachmentRef> attachments) {
        }

        public record PresignedUploadDto(
                        String storageKey,
                        String uploadUrl,
                        Instant expiresAt) {
        }

        public record PresignedDownloadDto(
                        String storageKey,
                        String downloadUrl,
                        Instant expiresAt) {
        }

        public record RequestUploadUrlDto(
                        @NotBlank String fileName,
                        String contentType) {
        }

        // ---- Rubric ----

        public record RubricCriterionDto(
                        String id,
                        @NotBlank String name,
                        String description,
                        @NotNull @DecimalMin("0.01") BigDecimal maxPoints,
                        int position) {
        }

        public record RubricDto(
                        String id,
                        String assignmentId,
                        String title,
                        BigDecimal maxScore,
                        List<RubricCriterionDto> criteria) {
        }

        public record UpsertRubricRequestDto(
                        @NotBlank String title,
                        @NotNull @DecimalMin("0.01") BigDecimal maxScore,
                        @Valid List<RubricCriterionDto> criteria) {
        }

        // ---- Grading ----

        public record RubricScoreDto(
                        @NotBlank String criterionId,
                        @NotNull @DecimalMin("0") BigDecimal points,
                        String comment) {
        }

        // graderId is taken from the authenticated instructor/admin, never from the request body.
        public record GradeSubmissionRequestDto(
                        BigDecimal rawScore,
                        String feedback,
                        @Valid List<RubricScoreDto> rubricScores) {
        }
}
