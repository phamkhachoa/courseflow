package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(
        name = "loyalty_reward_redemptions",
        uniqueConstraints = {
                @UniqueConstraint(
                        name = "uk_loyalty_reward_redemption_idempotency",
                        columnNames = {"tenant_id", "application_id", "idempotency_key"}),
                @UniqueConstraint(
                        name = "uk_loyalty_reward_redemption_source",
                        columnNames = {"program_uuid", "source_reference"})
        })
public class LoyaltyRewardRedemption {

    private static final Set<String> FULFILLMENT_STATUSES = Set.of("PENDING", "ISSUED", "MANUAL_REQUIRED", "FAILED");

    @Id
    private UUID id;

    @Column(name = "reward_id", nullable = false)
    private UUID rewardId;

    @Column(name = "program_uuid", nullable = false)
    private UUID programUuid;

    @Column(name = "account_id", nullable = false)
    private UUID accountId;

    @Column(name = "burn_entry_id", nullable = false)
    private UUID burnEntryId;

    @Column(name = "reversal_entry_id")
    private UUID reversalEntryId;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(name = "profile_id", nullable = false, length = 160)
    private String profileId;

    @Column(name = "reward_code", nullable = false, length = 120)
    private String rewardCode;

    @Column(name = "points_cost", nullable = false)
    private long pointsCost;

    @Column(name = "source_reference", nullable = false, length = 180)
    private String sourceReference;

    @Column(name = "idempotency_key", nullable = false, length = 180)
    private String idempotencyKey;

    @Column(name = "request_hash", nullable = false, length = 128)
    private String requestHash;

    @Column(nullable = false, length = 40)
    private String status = "COMMITTED";

    @Column(name = "fulfillment_status", nullable = false, length = 40)
    private String fulfillmentStatus = "PENDING";

    @Column(name = "fulfillment_ref", length = 180)
    private String fulfillmentRef;

    @Column(name = "fulfillment_note", columnDefinition = "TEXT")
    private String fulfillmentNote;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "reward_snapshot_json", nullable = false, columnDefinition = "jsonb")
    private String rewardSnapshotJson = "{}";

    @Column(name = "correlation_id", length = 160)
    private String correlationId;

    @Column(columnDefinition = "TEXT")
    private String note;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false, columnDefinition = "jsonb")
    private String metadataJson = "{}";

    @Column(name = "redeemed_at", nullable = false)
    private Instant redeemedAt = Instant.now();

    @Column(name = "fulfilled_at")
    private Instant fulfilledAt;

    @Column(name = "reversed_at")
    private Instant reversedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyRewardRedemption() {
    }

    public LoyaltyRewardRedemption(
            LoyaltyReward reward,
            UUID accountId,
            UUID burnEntryId,
            String profileId,
            String sourceReference,
            String idempotencyKey,
            String requestHash,
            String rewardSnapshotJson,
            String correlationId,
            String note,
            String metadataJson) {
        this.id = UUID.randomUUID();
        this.rewardId = reward.getId();
        this.programUuid = reward.getProgramUuid();
        this.accountId = accountId;
        this.burnEntryId = burnEntryId;
        this.tenantId = reward.getTenantId();
        this.applicationId = reward.getApplicationId();
        this.programId = reward.getProgramId();
        this.profileId = profileId;
        this.rewardCode = reward.getRewardCode();
        this.pointsCost = reward.getPointsCost();
        this.sourceReference = sourceReference;
        this.idempotencyKey = idempotencyKey;
        this.requestHash = requestHash;
        this.rewardSnapshotJson = rewardSnapshotJson == null || rewardSnapshotJson.isBlank()
                ? "{}"
                : rewardSnapshotJson;
        this.correlationId = correlationId;
        this.note = note;
        this.metadataJson = metadataJson == null || metadataJson.isBlank() ? "{}" : metadataJson;
        if ("AUTO_ISSUE".equalsIgnoreCase(reward.getFulfillmentType())) {
            this.fulfillmentStatus = "ISSUED";
            this.fulfillmentRef = sourceReference;
            this.fulfilledAt = Instant.now();
        }
    }

    public void updateFulfillment(String status, String fulfillmentRef, String note) {
        String nextStatus = status == null || status.isBlank() ? "" : status.trim().toUpperCase();
        if (!FULFILLMENT_STATUSES.contains(nextStatus)) {
            throw new IllegalArgumentException("Unsupported reward fulfillment status: " + status);
        }
        this.fulfillmentStatus = nextStatus;
        if (fulfillmentRef != null) {
            this.fulfillmentRef = fulfillmentRef.isBlank() ? null : fulfillmentRef.trim();
        }
        if (note != null) {
            this.fulfillmentNote = note.isBlank() ? null : note.trim();
        }
        if ("ISSUED".equals(nextStatus)) {
            this.fulfilledAt = Instant.now();
        }
        this.updatedAt = Instant.now();
    }

    public void markReversed(UUID reversalEntryId) {
        this.status = "REVERSED";
        this.reversalEntryId = reversalEntryId;
        this.reversedAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    @PreUpdate
    void preUpdate() {
        this.updatedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public UUID getRewardId() { return rewardId; }
    public UUID getProgramUuid() { return programUuid; }
    public UUID getAccountId() { return accountId; }
    public UUID getBurnEntryId() { return burnEntryId; }
    public UUID getReversalEntryId() { return reversalEntryId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public String getRewardCode() { return rewardCode; }
    public long getPointsCost() { return pointsCost; }
    public String getSourceReference() { return sourceReference; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getRequestHash() { return requestHash; }
    public String getStatus() { return status; }
    public String getFulfillmentStatus() { return fulfillmentStatus; }
    public String getFulfillmentRef() { return fulfillmentRef; }
    public String getFulfillmentNote() { return fulfillmentNote; }
    public String getRewardSnapshotJson() { return rewardSnapshotJson; }
    public String getCorrelationId() { return correlationId; }
    public String getNote() { return note; }
    public String getMetadataJson() { return metadataJson; }
    public Instant getRedeemedAt() { return redeemedAt; }
    public Instant getFulfilledAt() { return fulfilledAt; }
    public Instant getReversedAt() { return reversedAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
