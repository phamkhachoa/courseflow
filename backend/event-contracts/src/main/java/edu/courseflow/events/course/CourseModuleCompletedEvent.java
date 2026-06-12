package edu.courseflow.events.course;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record CourseModuleCompletedEvent(
        String eventId,
        String progressId,
        String courseId,
        String moduleId,
        String studentId,
        Instant completedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "course.module.completed";
    }

    @Override
    public String aggregateId() {
        return progressId;
    }

    @Override
    public String aggregateType() {
        return "learner-module-progress";
    }

    @Override
    public Instant occurredAt() {
        return completedAt;
    }
}
