package edu.courseflow.events.assignment;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record SubmissionCreatedEvent(
        String eventId,
        String submissionId,
        String assignmentId,
        String courseId,
        String studentId,
        Instant submittedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "submission.created";
    }

    @Override
    public String aggregateId() {
        return submissionId;
    }

    @Override
    public String aggregateType() {
        return "submission";
    }

    @Override
    public Instant occurredAt() {
        return submittedAt;
    }
}
