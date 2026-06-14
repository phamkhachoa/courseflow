package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(
        name = "loyalty_processed_inbound_events",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_loyalty_processed_inbound_event",
                columnNames = {"source_event_type", "event_id"}))
public class LoyaltyProcessedInboundEvent {

    @Id
    private UUID id;

    @Column(name = "source_topic", nullable = false, length = 240)
    private String sourceTopic;

    @Column(name = "source_event_type", nullable = false, length = 160)
    private String sourceEventType;

    @Column(name = "event_id", nullable = false, length = 180)
    private String eventId;

    @Column(name = "aggregate_id", length = 180)
    private String aggregateId;

    @Column(name = "payload_hash", nullable = false, length = 80)
    private String payloadHash;

    @Column(nullable = false, length = 40)
    private String status = "PROCESSED";

    @Column(name = "processed_at", nullable = false)
    private Instant processedAt = Instant.now();

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyProcessedInboundEvent() {
    }

    public LoyaltyProcessedInboundEvent(
            String sourceTopic,
            String sourceEventType,
            String eventId,
            String aggregateId,
            String payloadHash) {
        this.id = UUID.randomUUID();
        this.sourceTopic = sourceTopic;
        this.sourceEventType = sourceEventType;
        this.eventId = eventId;
        this.aggregateId = aggregateId;
        this.payloadHash = payloadHash;
    }

    public UUID getId() { return id; }
    public String getSourceTopic() { return sourceTopic; }
    public String getSourceEventType() { return sourceEventType; }
    public String getEventId() { return eventId; }
    public String getAggregateId() { return aggregateId; }
    public String getPayloadHash() { return payloadHash; }
    public String getStatus() { return status; }
    public Instant getProcessedAt() { return processedAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
