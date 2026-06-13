package edu.courseflow.events.identity;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;
import java.time.Instant;

public record UserEmailVerificationRequestedEvent(
        String eventId,
        String userId,
        String email,
        String fullName,
        String verificationUrl,
        Instant expiresAt,
        Instant requestedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "user.email_verification_requested";
    }

    @Override
    public String aggregateId() {
        return userId;
    }

    @Override
    public String aggregateType() {
        return "user";
    }

    @Override
    public Instant occurredAt() {
        return requestedAt;
    }
}
