package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "incentive_coupon_import_batches")
public class IncentiveCouponImportBatch {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    @Column(name = "request_hash", nullable = false, length = 160)
    private String requestHash;

    @Column(name = "idempotency_key", length = 160)
    private String idempotencyKey;

    @Column(nullable = false, length = 40)
    private String mode = "DRY_RUN";

    @Column(nullable = false, length = 40)
    private String status = "COMPLETED";

    @Column(name = "content_hash", nullable = false, length = 160)
    private String contentHash;

    @Column(name = "result_hash", nullable = false, length = 160)
    private String resultHash;

    @Column(name = "requested_rows", nullable = false)
    private int requestedRows;

    @Column(name = "valid_rows", nullable = false)
    private int validRows;

    @Column(name = "invalid_rows", nullable = false)
    private int invalidRows;

    @Column(name = "duplicate_in_file_rows", nullable = false)
    private int duplicateInFileRows;

    @Column(name = "duplicate_existing_rows", nullable = false)
    private int duplicateExistingRows;

    @Column(name = "storage_inventory_ready", nullable = false)
    private boolean storageInventoryReady;

    @Column(name = "commit_ready", nullable = false)
    private boolean commitReady;

    @Column(name = "committed_at")
    private Instant committedAt;

    @Column(name = "committed_by", length = 80)
    private String committedBy;

    @Column(name = "committed_operation_id")
    private UUID committedOperationId;

    @Column(name = "committed_rows", nullable = false)
    private int committedRows;

    @Column(name = "failure_reason", length = 255)
    private String failureReason;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "result_json", nullable = false, columnDefinition = "jsonb")
    private String resultJson;

    @Column(name = "created_by", length = 80)
    private String createdBy;

    @Column(name = "correlation_id", length = 120)
    private String correlationId;

    @Column(name = "source_client_id", length = 160)
    private String sourceClientId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Version
    private Long version;

    protected IncentiveCouponImportBatch() {
    }

    public IncentiveCouponImportBatch(UUID id,
                                      String tenantId,
                                      String applicationId,
                                      UUID campaignId,
                                      String requestHash,
                                      String idempotencyKey,
                                      String contentHash,
                                      String resultHash,
                                      int requestedRows,
                                      int validRows,
                                      int invalidRows,
                                      int duplicateInFileRows,
                                      int duplicateExistingRows,
                                      boolean storageInventoryReady,
                                      boolean commitReady,
                                      String resultJson,
                                      String createdBy,
                                      String correlationId,
                                      String sourceClientId,
                                      Instant expiresAt) {
        this.id = id == null ? UUID.randomUUID() : id;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignId = campaignId;
        this.requestHash = requestHash;
        this.idempotencyKey = idempotencyKey;
        this.contentHash = contentHash;
        this.resultHash = resultHash;
        this.requestedRows = requestedRows;
        this.validRows = validRows;
        this.invalidRows = invalidRows;
        this.duplicateInFileRows = duplicateInFileRows;
        this.duplicateExistingRows = duplicateExistingRows;
        this.storageInventoryReady = storageInventoryReady;
        this.commitReady = commitReady;
        this.resultJson = resultJson;
        this.createdBy = createdBy;
        this.correlationId = correlationId;
        this.sourceClientId = sourceClientId;
        this.expiresAt = expiresAt;
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getCampaignId() { return campaignId; }
    public String getStatus() { return status; }
    public String getRequestHash() { return requestHash; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getResultHash() { return resultHash; }
    public String getContentHash() { return contentHash; }
    public int getRequestedRows() { return requestedRows; }
    public int getValidRows() { return validRows; }
    public int getInvalidRows() { return invalidRows; }
    public int getDuplicateInFileRows() { return duplicateInFileRows; }
    public int getDuplicateExistingRows() { return duplicateExistingRows; }
    public boolean isStorageInventoryReady() { return storageInventoryReady; }
    public boolean isCommitReady() { return commitReady; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public Instant getCommittedAt() { return committedAt; }
    public String getCommittedBy() { return committedBy; }
    public UUID getCommittedOperationId() { return committedOperationId; }
    public int getCommittedRows() { return committedRows; }
    public String getFailureReason() { return failureReason; }
    public String getResultJson() { return resultJson; }
    public String getCreatedBy() { return createdBy; }
    public String getCorrelationId() { return correlationId; }
    public String getSourceClientId() { return sourceClientId; }

    public void markCommitted(UUID operationId, int committedRows, String actorId, Instant committedAt) {
        this.committedOperationId = operationId;
        this.committedRows = committedRows;
        this.committedBy = actorId;
        this.committedAt = committedAt == null ? Instant.now() : committedAt;
        this.expiresAt = null;
        this.failureReason = null;
    }
}
