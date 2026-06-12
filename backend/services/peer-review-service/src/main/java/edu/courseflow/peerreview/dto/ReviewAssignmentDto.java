package edu.courseflow.peerreview.dto;

import java.time.Instant;

public record ReviewAssignmentDto(
        String id,
        String courseId,
        String assignmentId,
        String submissionId,
        String reviewerId,
        String revieweeId,
        String status,
        Instant assignedAt
) {
}
