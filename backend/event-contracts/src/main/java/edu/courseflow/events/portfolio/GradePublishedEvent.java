package edu.courseflow.events.portfolio;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.math.BigDecimal;
import java.time.Instant;

public record GradePublishedEvent(
        String eventId,
        String gradeId,
        String submissionId,
        String assignmentId,
        String studentId,
        BigDecimal score,
        BigDecimal maxScore,
        Instant publishedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "grade.published";
    }

    @Override
    public String aggregateId() {
        return gradeId;
    }

    @Override
    public String aggregateType() {
        return "grade";
    }

    @Override
    public Instant occurredAt() {
        return publishedAt;
    }
}
