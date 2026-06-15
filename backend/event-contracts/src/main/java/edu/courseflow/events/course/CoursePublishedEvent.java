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
        Integer publishedVersionNo,
        Instant publishedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    public CoursePublishedEvent(
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
    ) {
        this(eventId, courseId, code, title, slug, summary, departmentId, ownerId, level, status, null,
                publishedAt, metadata);
    }

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
