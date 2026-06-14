package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_INBOUND_EVENT_PAYLOAD_CONFLICT;

import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.loyalty.model.LoyaltyProcessedInboundEvent;
import edu.courseflow.loyalty.repository.LoyaltyProcessedInboundEventRepository;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyProcessedInboundEventService {

    private final LoyaltyProcessedInboundEventRepository processedEvents;
    private final LoyaltyMetrics metrics;

    public LoyaltyProcessedInboundEventService(
            LoyaltyProcessedInboundEventRepository processedEvents,
            LoyaltyMetrics metrics) {
        this.processedEvents = processedEvents;
        this.metrics = metrics;
    }

    @Transactional(readOnly = true)
    public boolean shouldProcess(String sourceEventType, String eventId, String payloadHash) {
        LoyaltyProcessedInboundEvent existing = processedEvents
                .findBySourceEventTypeAndEventId(sourceEventType, eventId)
                .orElse(null);
        if (existing == null) {
            metrics.inboundEvent(sourceEventType, "new");
            return true;
        }
        requireSamePayload(existing, payloadHash);
        metrics.inboundEvent(sourceEventType, "duplicate_skip");
        return false;
    }

    @Transactional
    public void recordProcessed(
            String sourceTopic,
            String sourceEventType,
            String eventId,
            String aggregateId,
            String payloadHash) {
        try {
            processedEvents.save(new LoyaltyProcessedInboundEvent(
                    sourceTopic,
                    sourceEventType,
                    eventId,
                    aggregateId,
                    payloadHash));
            metrics.inboundEvent(sourceEventType, "processed");
        } catch (DataIntegrityViolationException ex) {
            LoyaltyProcessedInboundEvent existing = processedEvents
                    .findBySourceEventTypeAndEventId(sourceEventType, eventId)
                    .orElseThrow(() -> ex);
            requireSamePayload(existing, payloadHash);
            metrics.inboundEvent(sourceEventType, "record_race_duplicate");
        }
    }

    private void requireSamePayload(LoyaltyProcessedInboundEvent existing, String payloadHash) {
        if (!existing.getPayloadHash().equals(payloadHash)) {
            metrics.inboundEvent(existing.getSourceEventType(), "payload_conflict");
            throw ConflictException.coded(
                    LOYALTY_INBOUND_EVENT_PAYLOAD_CONFLICT,
                    "Inbound loyalty event id was reused with a different payload");
        }
    }
}
