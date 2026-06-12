package edu.courseflow.events.announcement;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record AnnouncementPublishedEvent(
        String eventId,
        String announcementId,
        String courseId,
        String title,
        String audience,
        Instant publishedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "announcement.published";
    }

    @Override
    public String aggregateId() {
        return announcementId;
    }

    @Override
    public String aggregateType() {
        return "announcement";
    }

    @Override
    public Instant occurredAt() {
        return publishedAt;
    }
}
