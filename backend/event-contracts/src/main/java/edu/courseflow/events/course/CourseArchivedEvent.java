package edu.courseflow.events.course;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record CourseArchivedEvent(
        String eventId,
        String courseId,
        String code,
        String title,
        String slug,
        String summary,
        String departmentId,
        String ownerId,
        String level,
        String status,
        Instant archivedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "course.archived";
    }

    @Override
    public String aggregateId() {
        return courseId;
    }

    @Override
    public String aggregateType() {
        return "course";
    }

    @Override
    public Instant occurredAt() {
        return archivedAt;
    }
}
