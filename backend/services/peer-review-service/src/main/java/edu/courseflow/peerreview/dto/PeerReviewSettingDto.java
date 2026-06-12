package edu.courseflow.peerreview.dto;

import java.time.Instant;

public record PeerReviewSettingDto(
        String id,
        String assignmentId,
        int reviewersPerSubmission,
        boolean anonymous,
        Instant reviewDueAt,
        String status
) {
}
