package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(
        name = "loyalty_promotion_point_effects",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_loyalty_promotion_point_effect",
                columnNames = {"source_event_type", "event_id", "effect_id", "expected_entry_type"}))
public class LoyaltyPromotionPointEffect {

    @Id
    private UUID id;

    @Column(name = "source_topic", nullable = false, length = 240)
    private String sourceTopic;

    @Column(name = "source_event_type", nullable = false, length = 160)
    private String sourceEventType;

    @Column(name = "event_id", nullable = false, length = 180)
    private String eventId;

    @Column(name = "redemption_id", nullable = false, length = 180)
    private String redemptionId;

    @Column(name = "effect_id", nullable = false, length = 240)
    private String effectId;

    @Column(name = "expected_entry_type", nullable = false, length = 40)
    private String expectedEntryType;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(name = "profile_id", nullable = false, length = 160)
    private String profileId;

    @Column(name = "points_delta", nullable = false)
    private long pointsDelta;

    @Column(name = "original_source_reference", nullable = false, length = 180)
    private String originalSourceReference;

    @Column(name = "expected_idempotency_key", nullable = false, length = 180)
    private String expectedIdempotencyKey;

    @Column(name = "correlation_id", length = 160)
    private String correlationId;

    @Column(name = "payload_hash", nullable = false, length = 80)
    private String payloadHash;

    @Column(name = "event_occurred_at")
    private Instant eventOccurredAt;

    @Column(name = "observed_at", nullable = false)
    private Instant observedAt = Instant.now();

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyPromotionPointEffect() {
    }

    public LoyaltyPromotionPointEffect(
            String sourceTopic,
            String sourceEventType,
            String eventId,
            String redemptionId,
            String effectId,
            String expectedEntryType,
            String tenantId,
            String applicationId,
            String programId,
            String profileId,
            long pointsDelta,
            String originalSourceReference,
            String expectedIdempotencyKey,
            String correlationId,
            String payloadHash,
            Instant eventOccurredAt) {
        this.id = UUID.randomUUID();
        this.sourceTopic = sourceTopic;
        this.sourceEventType = sourceEventType;
        this.eventId = eventId;
        this.redemptionId = redemptionId;
        this.effectId = effectId;
        this.expectedEntryType = expectedEntryType;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.programId = programId;
        this.profileId = profileId;
        this.pointsDelta = pointsDelta;
        this.originalSourceReference = originalSourceReference;
        this.expectedIdempotencyKey = expectedIdempotencyKey;
        this.correlationId = correlationId;
        this.payloadHash = payloadHash;
        this.eventOccurredAt = eventOccurredAt;
    }

    @PreUpdate
    void preUpdate() {
        this.updatedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public String getSourceTopic() { return sourceTopic; }
    public String getSourceEventType() { return sourceEventType; }
    public String getEventId() { return eventId; }
    public String getRedemptionId() { return redemptionId; }
    public String getEffectId() { return effectId; }
    public String getExpectedEntryType() { return expectedEntryType; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public long getPointsDelta() { return pointsDelta; }
    public String getOriginalSourceReference() { return originalSourceReference; }
    public String getExpectedIdempotencyKey() { return expectedIdempotencyKey; }
    public String getCorrelationId() { return correlationId; }
    public String getPayloadHash() { return payloadHash; }
    public Instant getEventOccurredAt() { return eventOccurredAt; }
    public Instant getObservedAt() { return observedAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
