package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "loyalty_adjustment_approvals")
public class LoyaltyAdjustmentApproval {

    private static final Set<String> TERMINAL_STATUSES = Set.of("APPROVED", "REJECTED", "EXECUTED");

    @Id
    private UUID id;

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

    @Column(name = "source_reference", nullable = false, length = 180)
    private String sourceReference;

    @Column(name = "idempotency_key", nullable = false, length = 180)
    private String idempotencyKey;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Column(name = "correlation_id", nullable = false, length = 160)
    private String correlationId;

    @Column(name = "occurred_at")
    private Instant occurredAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false, columnDefinition = "jsonb")
    private String metadataJson = "{}";

    @Column(name = "request_hash", nullable = false, length = 128)
    private String requestHash;

    @Column(nullable = false, length = 40)
    private String status = "PENDING";

    @Column(name = "requested_by", nullable = false, length = 160)
    private String requestedBy;

    @Column(name = "reviewed_by", length = 160)
    private String reviewedBy;

    @Column(name = "review_note", columnDefinition = "TEXT")
    private String reviewNote;

    @Column(name = "requested_at", nullable = false)
    private Instant requestedAt = Instant.now();

    @Column(name = "reviewed_at")
    private Instant reviewedAt;

    @Column(name = "executed_at")
    private Instant executedAt;

    @Column(name = "executed_entry_id")
    private UUID executedEntryId;

    @Version
    private long version;

    protected LoyaltyAdjustmentApproval() {
    }

    public LoyaltyAdjustmentApproval(String tenantId, String applicationId, String programId, String profileId,
                                     long pointsDelta, String sourceReference, String idempotencyKey,
                                     String reason, String correlationId, Instant occurredAt, Instant expiresAt,
                                     String metadataJson, String requestHash, String requestedBy) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.programId = programId;
        this.profileId = profileId;
        this.pointsDelta = pointsDelta;
        this.sourceReference = sourceReference;
        this.idempotencyKey = idempotencyKey;
        this.reason = reason;
        this.correlationId = correlationId;
        this.occurredAt = occurredAt;
        this.expiresAt = expiresAt;
        this.metadataJson = metadataJson == null || metadataJson.isBlank() ? "{}" : metadataJson;
        this.requestHash = requestHash;
        this.requestedBy = requestedBy;
    }

    public void approve(String reviewer, String note) {
        requireReviewable();
        this.status = "APPROVED";
        this.reviewedBy = reviewer;
        this.reviewNote = note;
        this.reviewedAt = Instant.now();
    }

    public void reject(String reviewer, String note) {
        requireReviewable();
        this.status = "REJECTED";
        this.reviewedBy = reviewer;
        this.reviewNote = note;
        this.reviewedAt = Instant.now();
    }

    public void markExecuted(UUID entryId) {
        if (!"APPROVED".equals(status)) {
            throw new IllegalStateException("Only approved loyalty operations can be executed");
        }
        this.status = "EXECUTED";
        this.executedEntryId = entryId;
        this.executedAt = Instant.now();
    }

    private void requireReviewable() {
        if (TERMINAL_STATUSES.contains(status)) {
            throw new IllegalStateException("Loyalty operation approval has already been reviewed");
        }
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public long getPointsDelta() { return pointsDelta; }
    public String getSourceReference() { return sourceReference; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getReason() { return reason; }
    public String getCorrelationId() { return correlationId; }
    public Instant getOccurredAt() { return occurredAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public String getMetadataJson() { return metadataJson; }
    public String getRequestHash() { return requestHash; }
    public String getStatus() { return status; }
    public String getRequestedBy() { return requestedBy; }
    public String getReviewedBy() { return reviewedBy; }
    public String getReviewNote() { return reviewNote; }
    public Instant getRequestedAt() { return requestedAt; }
    public Instant getReviewedAt() { return reviewedAt; }
    public Instant getExecutedAt() { return executedAt; }
    public UUID getExecutedEntryId() { return executedEntryId; }
}
