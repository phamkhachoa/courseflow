package edu.courseflow.peerreview.dto;

import jakarta.validation.constraints.NotBlank;

public record AssignReviewRequestDto(
        String courseId,
        @NotBlank String assignmentId,
        @NotBlank String submissionId,
        @NotBlank String reviewerId,
        @NotBlank String revieweeId
) {
}
