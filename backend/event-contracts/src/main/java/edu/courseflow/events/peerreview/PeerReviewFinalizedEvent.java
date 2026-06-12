package edu.courseflow.events.peerreview;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.math.BigDecimal;
import java.time.Instant;

public record PeerReviewFinalizedEvent(
        String eventId,
        String resultId,
        String assignmentId,
        String submissionId,
        String studentId,
        BigDecimal finalScore,
        Instant finalizedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "peer_review.finalized";
    }

    @Override
    public String aggregateId() {
        return resultId;
    }

    @Override
    public String aggregateType() {
        return "peer-review-result";
    }

    @Override
    public Instant occurredAt() {
        return finalizedAt;
    }
}
