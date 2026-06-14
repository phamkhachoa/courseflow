package edu.courseflow.events.incentive;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;
import java.time.Instant;
import java.util.List;

public record IncentiveRedemptionReversedEvent(
        String eventId,
        int schemaVersion,
        String tenantId,
        String applicationId,
        String reservationId,
        String redemptionId,
        String campaignId,
        Integer campaignVersion,
        String couponId,
        String profileId,
        String externalReference,
        String correlationId,
        String sourceClientId,
        String reason,
        boolean quotaReleased,
        List<IncentiveEffectPayload> effects,
        Instant reversedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "incentive.redemption.reversed";
    }

    @Override
    public String aggregateId() {
        return redemptionId;
    }

    @Override
    public String aggregateType() {
        return "incentive-redemption";
    }

    @Override
    public Instant occurredAt() {
        return reversedAt;
    }
}
