package edu.courseflow.events.course;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record CoursePublishedEvent(
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
        Instant publishedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "course.published";
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
        return publishedAt;
    }
}
