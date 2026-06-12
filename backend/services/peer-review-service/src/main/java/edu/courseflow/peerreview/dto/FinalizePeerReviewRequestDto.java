package edu.courseflow.peerreview.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * Finalize a submission's peer-review score. Only the submission identifier is accepted from the
 * client: the assignment, the reviewee (studentId) and the final score are all derived server-side
 * from {@code review_assignments} / {@code review_submissions}, and the finalizer is the
 * authenticated instructor/admin. This closes the P0 where a caller could post any score for any
 * student.
 */
public record FinalizePeerReviewRequestDto(
        @NotBlank String submissionId
) {
}
