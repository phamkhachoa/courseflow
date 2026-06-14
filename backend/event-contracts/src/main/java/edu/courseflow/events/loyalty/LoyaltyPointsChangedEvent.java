package edu.courseflow.events.loyalty;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;
import java.time.Instant;

public record LoyaltyPointsChangedEvent(
        String eventId,
        int schemaVersion,
        String tenantId,
        String applicationId,
        String programId,
        String accountId,
        String entryId,
        String profileId,
        String entryType,
        long pointsDelta,
        String sourceReference,
        String correlationId,
        Instant occurredAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return switch (entryType) {
            case "EARN" -> "loyalty.points.earned";
            case "BURN" -> "loyalty.points.burned";
            case "REVERSE" -> "loyalty.points.reversed";
            case "ADJUST" -> "loyalty.points.adjusted";
            case "EXPIRE" -> "loyalty.points.expired";
            default -> "loyalty.points.changed";
        };
    }

    @Override
    public String aggregateId() {
        return entryId;
    }

    @Override
    public String aggregateType() {
        return "loyalty-points-entry";
    }
}
