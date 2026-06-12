package edu.courseflow.events.livesession;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record LiveSessionScheduledEvent(
        String eventId,
        String sessionId,
        String courseId,
        String hostId,
        Instant scheduledStart,
        Instant occurredAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "live.session.scheduled";
    }

    @Override
    public String aggregateId() {
        return sessionId;
    }

    @Override
    public String aggregateType() {
        return "live-session";
    }
}
