package edu.courseflow.peerreview.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record ReviewSubmissionDto(
        String id,
        String reviewAssignmentId,
        BigDecimal score,
        String comment,
        String status,
        Instant submittedAt
) {
}
