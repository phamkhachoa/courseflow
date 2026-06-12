package edu.courseflow.events.peerreview;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record PeerReviewAssignedEvent(
        String eventId,
        String reviewAssignmentId,
        String assignmentId,
        String submissionId,
        String reviewerId,
        Instant assignedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "peer_review.assigned";
    }

    @Override
    public String aggregateId() {
        return reviewAssignmentId;
    }

    @Override
    public String aggregateType() {
        return "peer-review-assignment";
    }

    @Override
    public Instant occurredAt() {
        return assignedAt;
    }
}
