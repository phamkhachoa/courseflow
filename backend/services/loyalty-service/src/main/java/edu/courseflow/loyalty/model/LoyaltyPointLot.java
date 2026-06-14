package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "loyalty_point_lots")
public class LoyaltyPointLot {

    @Id
    private UUID id;

    @Column(name = "program_uuid", nullable = false)
    private UUID programUuid;

    @Column(name = "account_id", nullable = false)
    private UUID accountId;

    @Column(name = "source_entry_id", nullable = false)
    private UUID sourceEntryId;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(name = "profile_id", nullable = false, length = 160)
    private String profileId;

    @Column(name = "entry_type", nullable = false, length = 40)
    private String entryType;

    @Column(name = "original_points", nullable = false)
    private long originalPoints;

    @Column(name = "consumed_points", nullable = false)
    private long consumedPoints;

    @Column(name = "remaining_points", nullable = false)
    private long remainingPoints;

    @Column(name = "source_reference", nullable = false, length = 180)
    private String sourceReference;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyPointLot() {
    }

    public LoyaltyPointLot(LoyaltyPointsEntry entry) {
        this.id = UUID.randomUUID();
        this.programUuid = entry.getProgramUuid();
        this.accountId = entry.getAccountId();
        this.sourceEntryId = entry.getId();
        this.tenantId = entry.getTenantId();
        this.applicationId = entry.getApplicationId();
        this.programId = entry.getProgramId();
        this.profileId = entry.getProfileId();
        this.entryType = entry.getEntryType();
        this.originalPoints = entry.getPointsDelta();
        this.remainingPoints = entry.getPointsDelta();
        this.sourceReference = entry.getSourceReference();
        this.occurredAt = entry.getOccurredAt();
        this.expiresAt = entry.getExpiresAt();
    }

    public long consume(long points) {
        long consumed = Math.min(Math.max(points, 0L), remainingPoints);
        this.remainingPoints -= consumed;
        this.consumedPoints += consumed;
        this.updatedAt = Instant.now();
        return consumed;
    }

    public long restore(long points) {
        long restored = Math.min(Math.max(points, 0L), consumedPoints);
        this.remainingPoints += restored;
        this.consumedPoints -= restored;
        this.updatedAt = Instant.now();
        return restored;
    }

    public void resetConsumption() {
        this.consumedPoints = 0L;
        this.remainingPoints = originalPoints;
        this.updatedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public UUID getProgramUuid() { return programUuid; }
    public UUID getAccountId() { return accountId; }
    public UUID getSourceEntryId() { return sourceEntryId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public String getEntryType() { return entryType; }
    public long getOriginalPoints() { return originalPoints; }
    public long getConsumedPoints() { return consumedPoints; }
    public long getRemainingPoints() { return remainingPoints; }
    public String getSourceReference() { return sourceReference; }
    public Instant getOccurredAt() { return occurredAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
