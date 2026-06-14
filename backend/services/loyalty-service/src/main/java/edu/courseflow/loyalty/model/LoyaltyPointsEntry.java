package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "loyalty_points_entries")
public class LoyaltyPointsEntry {

    @Id
    private UUID id;

    @Column(name = "program_uuid", nullable = false)
    private UUID programUuid;

    @Column(name = "account_id", nullable = false)
    private UUID accountId;

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

    @Column(name = "points_delta", nullable = false)
    private long pointsDelta;

    @Column(name = "source_reference", nullable = false, length = 180)
    private String sourceReference;

    @Column(name = "source_request_hash", nullable = false, length = 128)
    private String sourceRequestHash;

    @Column(name = "reversal_of_entry_id")
    private UUID reversalOfEntryId;

    @Column(columnDefinition = "TEXT")
    private String reason;

    @Column(name = "correlation_id", length = 160)
    private String correlationId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false, columnDefinition = "jsonb")
    private String metadataJson = "{}";

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected LoyaltyPointsEntry() {
    }

    public LoyaltyPointsEntry(LoyaltyAccount account, String entryType, long pointsDelta,
                              String sourceReference, String sourceRequestHash, UUID reversalOfEntryId,
                              String reason, String correlationId, String metadataJson,
                              Instant occurredAt, Instant expiresAt) {
        this.id = UUID.randomUUID();
        this.programUuid = account.getProgramUuid();
        this.accountId = account.getId();
        this.tenantId = account.getTenantId();
        this.applicationId = account.getApplicationId();
        this.programId = account.getProgramId();
        this.profileId = account.getProfileId();
        this.entryType = entryType;
        this.pointsDelta = pointsDelta;
        this.sourceReference = sourceReference;
        this.sourceRequestHash = sourceRequestHash;
        this.reversalOfEntryId = reversalOfEntryId;
        this.reason = reason;
        this.correlationId = correlationId;
        this.metadataJson = metadataJson == null || metadataJson.isBlank() ? "{}" : metadataJson;
        this.occurredAt = occurredAt == null ? Instant.now() : occurredAt;
        this.expiresAt = expiresAt;
    }

    public void replaceMetadataJson(String metadataJson) {
        this.metadataJson = metadataJson == null || metadataJson.isBlank() ? "{}" : metadataJson;
    }

    public UUID getId() { return id; }
    public UUID getProgramUuid() { return programUuid; }
    public UUID getAccountId() { return accountId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public String getEntryType() { return entryType; }
    public long getPointsDelta() { return pointsDelta; }
    public String getSourceReference() { return sourceReference; }
    public String getSourceRequestHash() { return sourceRequestHash; }
    public UUID getReversalOfEntryId() { return reversalOfEntryId; }
    public String getReason() { return reason; }
    public String getCorrelationId() { return correlationId; }
    public String getMetadataJson() { return metadataJson; }
    public Instant getOccurredAt() { return occurredAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public Instant getCreatedAt() { return createdAt; }
}
