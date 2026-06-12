package edu.courseflow.peerreview.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record PeerReviewResultDto(
        String id,
        String submissionId,
        BigDecimal finalScore,
        String finalizedBy,
        Instant finalizedAt
) {
}
