package edu.courseflow.events.loyalty;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;
import java.time.Instant;
import java.util.Map;

public record LoyaltyRewardRedemptionEvent(
        String eventId,
        int schemaVersion,
        String eventType,
        String tenantId,
        String applicationId,
        String programId,
        String rewardId,
        String redemptionId,
        String accountId,
        String burnEntryId,
        String reversalEntryId,
        String profileId,
        String rewardCode,
        long pointsCost,
        String status,
        String fulfillmentStatus,
        String fulfillmentRef,
        String sourceReference,
        String correlationId,
        String actorId,
        String note,
        Instant redeemedAt,
        Instant fulfilledAt,
        Instant reversedAt,
        Map<String, Object> rewardMetadata,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String aggregateId() {
        return redemptionId;
    }

    @Override
    public String aggregateType() {
        return "loyalty-reward-redemption";
    }

    @Override
    public Instant occurredAt() {
        if ("loyalty.reward.reversed".equals(eventType) && reversedAt != null) {
            return reversedAt;
        }
        if ("loyalty.reward.fulfillment_status_changed".equals(eventType) && fulfilledAt != null) {
            return fulfilledAt;
        }
        return redeemedAt;
    }
}
