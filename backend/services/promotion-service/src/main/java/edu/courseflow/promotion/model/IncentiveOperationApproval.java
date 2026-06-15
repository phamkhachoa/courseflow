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
@Table(name = "incentive_operation_approvals")
public class IncentiveOperationApproval {

    public static final String OPERATION_COUPON_IMPORT_COMMIT = "COUPON_IMPORT_COMMIT";
    public static final String OPERATION_REDEMPTION_REVERSE = "PROMOTION_REDEMPTION_REVERSE";
    public static final String TARGET_COUPON_IMPORT_DRY_RUN = "COUPON_IMPORT_DRY_RUN";
    public static final String TARGET_REDEMPTION = "PROMOTION_REDEMPTION";

    public static final String STATUS_PENDING = "PENDING_APPROVAL";
    public static final String STATUS_APPROVED = "APPROVED";
    public static final String STATUS_REJECTED = "REJECTED";
    public static final String STATUS_EXECUTED = "EXECUTED";

    @Id
    private UUID id;

    @Column(name = "operation_type", nullable = false, length = 80)
    private String operationType;

    @Column(name = "target_type", nullable = false, length = 80)
    private String targetType;

    @Column(name = "target_id", nullable = false)
    private UUID targetId;

    @Column(nullable = false, length = 40)
    private String status = STATUS_PENDING;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "campaign_id")
    private UUID campaignId;

    @Column(name = "scope_key", nullable = false, length = 220)
    private String scopeKey;

    @Column(name = "request_hash", nullable = false, length = 160)
    private String requestHash;

    @Column(name = "result_hash", nullable = false, length = 160)
    private String resultHash;

    @Column(name = "subject_hash", nullable = false, length = 160)
    private String subjectHash;

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

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "subject_json", nullable = false, columnDefinition = "jsonb")
    private String subjectJson;

    @Column(name = "reason", nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Column(name = "change_ticket", nullable = false, length = 160)
    private String changeTicket;

    @Column(columnDefinition = "TEXT")
    private String note;

    @Column(name = "requested_by", nullable = false, length = 160)
    private String requestedBy;

    @Column(name = "approved_by", length = 160)
    private String approvedBy;

    @Column(name = "rejected_by", length = 160)
    private String rejectedBy;

    @Column(name = "executed_by", length = 160)
    private String executedBy;

    @Column(name = "correlation_id", nullable = false, length = 160)
    private String correlationId;

    @Column(name = "source_client_id", length = 160)
    private String sourceClientId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "approved_at")
    private Instant approvedAt;

    @Column(name = "rejected_at")
    private Instant rejectedAt;

    @Column(name = "executed_at")
    private Instant executedAt;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Version
    private Long version;

    protected IncentiveOperationApproval() {
    }

    public IncentiveOperationApproval(String operationType,
                                      String targetType,
                                      UUID targetId,
                                      String tenantId,
                                      String applicationId,
                                      UUID campaignId,
                                      String scopeKey,
                                      String requestHash,
                                      String resultHash,
                                      String subjectHash,
                                      int requestedRows,
                                      int validRows,
                                      int invalidRows,
                                      int duplicateInFileRows,
                                      int duplicateExistingRows,
                                      boolean storageInventoryReady,
                                      boolean commitReady,
                                      String subjectJson,
                                      String reason,
                                      String changeTicket,
                                      String requestedBy,
                                      String correlationId,
                                      String sourceClientId,
                                      Instant expiresAt) {
        this.id = UUID.randomUUID();
        this.operationType = operationType;
        this.targetType = targetType;
        this.targetId = targetId;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignId = campaignId;
        this.scopeKey = scopeKey;
        this.requestHash = requestHash;
        this.resultHash = resultHash;
        this.subjectHash = subjectHash;
        this.requestedRows = requestedRows;
        this.validRows = validRows;
        this.invalidRows = invalidRows;
        this.duplicateInFileRows = duplicateInFileRows;
        this.duplicateExistingRows = duplicateExistingRows;
        this.storageInventoryReady = storageInventoryReady;
        this.commitReady = commitReady;
        this.subjectJson = subjectJson == null || subjectJson.isBlank() ? "{}" : subjectJson;
        this.reason = reason;
        this.changeTicket = changeTicket;
        this.requestedBy = requestedBy;
        this.correlationId = correlationId;
        this.sourceClientId = sourceClientId;
        this.expiresAt = expiresAt;
    }

    public boolean pending() {
        return STATUS_PENDING.equals(status);
    }

    public boolean approved() {
        return STATUS_APPROVED.equals(status);
    }

    public boolean executed() {
        return STATUS_EXECUTED.equals(status);
    }

    public boolean expired(Instant now) {
        return expiresAt != null && !expiresAt.isAfter(now);
    }

    public void approve(String actorId, String note, Instant now) {
        this.status = STATUS_APPROVED;
        this.approvedBy = actorId;
        this.note = note;
        this.approvedAt = now == null ? Instant.now() : now;
    }

    public void reject(String actorId, String note, Instant now) {
        this.status = STATUS_REJECTED;
        this.rejectedBy = actorId;
        this.note = note;
        this.rejectedAt = now == null ? Instant.now() : now;
    }

    public void markExecuted(String actorId, Instant now) {
        this.status = STATUS_EXECUTED;
        this.executedBy = actorId;
        this.executedAt = now == null ? Instant.now() : now;
    }

    public UUID getId() { return id; }
    public String getOperationType() { return operationType; }
    public String getTargetType() { return targetType; }
    public UUID getTargetId() { return targetId; }
    public String getStatus() { return status; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getCampaignId() { return campaignId; }
    public String getScopeKey() { return scopeKey; }
    public String getRequestHash() { return requestHash; }
    public String getResultHash() { return resultHash; }
    public String getSubjectHash() { return subjectHash; }
    public int getRequestedRows() { return requestedRows; }
    public int getValidRows() { return validRows; }
    public int getInvalidRows() { return invalidRows; }
    public int getDuplicateInFileRows() { return duplicateInFileRows; }
    public int getDuplicateExistingRows() { return duplicateExistingRows; }
    public boolean isStorageInventoryReady() { return storageInventoryReady; }
    public boolean isCommitReady() { return commitReady; }
    public String getSubjectJson() { return subjectJson; }
    public String getReason() { return reason; }
    public String getChangeTicket() { return changeTicket; }
    public String getNote() { return note; }
    public String getRequestedBy() { return requestedBy; }
    public String getApprovedBy() { return approvedBy; }
    public String getRejectedBy() { return rejectedBy; }
    public String getExecutedBy() { return executedBy; }
    public String getCorrelationId() { return correlationId; }
    public String getSourceClientId() { return sourceClientId; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getApprovedAt() { return approvedAt; }
    public Instant getRejectedAt() { return rejectedAt; }
    public Instant getExecutedAt() { return executedAt; }
    public Instant getExpiresAt() { return expiresAt; }
}
