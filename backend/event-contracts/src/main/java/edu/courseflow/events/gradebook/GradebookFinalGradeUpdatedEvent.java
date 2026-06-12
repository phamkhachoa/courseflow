package edu.courseflow.events.gradebook;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.math.BigDecimal;
import java.time.Instant;

public record GradebookFinalGradeUpdatedEvent(
        String eventId,
        String finalGradeId,
        String courseId,
        String studentId,
        BigDecimal finalScore,
        String status,
        Instant updatedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "gradebook.final_grade.updated";
    }

    @Override
    public String aggregateId() {
        return finalGradeId;
    }

    @Override
    public String aggregateType() {
        return "final-grade";
    }

    @Override
    public Instant occurredAt() {
        return updatedAt;
    }
}
