package edu.courseflow.events.incentive;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;
import java.time.Instant;
import java.util.List;

public record IncentiveRedemptionCommittedEvent(
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
        List<IncentiveEffectPayload> effects,
        Instant committedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "incentive.redemption.committed";
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
        return committedAt;
    }
}
