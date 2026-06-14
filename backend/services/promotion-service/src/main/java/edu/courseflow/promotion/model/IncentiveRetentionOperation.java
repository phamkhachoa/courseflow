package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "incentive_retention_operations")
public class IncentiveRetentionOperation {

    public static final String STATUS_IN_PROGRESS = "IN_PROGRESS";
    public static final String STATUS_SUCCEEDED = "SUCCEEDED";
    public static final String STATUS_FAILED = "FAILED";

    @Id
    private UUID id;

    @Column(name = "policy_id", nullable = false, length = 120)
    private String policyId;

    @Column(name = "policy_version", nullable = false, length = 40)
    private String policyVersion;

    @Column(name = "target_dataset", nullable = false, length = 120)
    private String targetDataset;

    @Column(name = "scope_key", nullable = false, length = 180)
    private String scopeKey;

    @Column(name = "approval_id")
    private UUID approvalId;

    @Column(name = "tenant_id", length = 80)
    private String tenantId;

    @Column(name = "application_id", length = 80)
    private String applicationId;

    @Column(name = "dry_run_id", nullable = false)
    private UUID dryRunId;

    @Column(name = "dry_run_result_hash", nullable = false, length = 128)
    private String dryRunResultHash;

    @Column(name = "cutoff_at", nullable = false)
    private Instant cutoffAt;

    @Column(name = "expected_eligible_count", nullable = false)
    private long expectedEligibleCount;

    @Column(name = "batch_limit", nullable = false)
    private int batchLimit;

    @Column(nullable = false, length = 40)
    private String status = STATUS_IN_PROGRESS;

    @Column(name = "idempotency_key", nullable = false, length = 160)
    private String idempotencyKey;

    @Column(name = "request_hash", nullable = false, length = 128)
    private String requestHash;

    @Column(name = "reason", nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Column(name = "change_ticket", nullable = false, length = 160)
    private String changeTicket;

    @Column(name = "restore_drill_ref", nullable = false, length = 255)
    private String restoreDrillRef;

    @Column(name = "approved_by", length = 160)
    private String approvedBy;

    @Column(name = "executed_by", length = 160)
    private String executedBy;

    @Column(name = "correlation_id", nullable = false, length = 160)
    private String correlationId;

    @Column(name = "rows_redacted", nullable = false)
    private long rowsRedacted;

    @Column(name = "last_error", columnDefinition = "TEXT")
    private String lastError;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "response_json", nullable = false, columnDefinition = "jsonb")
    private String responseJson = "{}";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "started_at")
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    protected IncentiveRetentionOperation() {
    }

    public IncentiveRetentionOperation(UUID id,
                                       String policyId,
                                       String policyVersion,
                                       String targetDataset,
                                       String scopeKey,
                                       UUID approvalId,
                                       String tenantId,
                                       String applicationId,
                                       UUID dryRunId,
                                       String dryRunResultHash,
                                       Instant cutoffAt,
                                       long expectedEligibleCount,
                                       int batchLimit,
                                       String idempotencyKey,
                                       String requestHash,
                                       String reason,
                                       String changeTicket,
                                       String restoreDrillRef,
                                       String approvedBy,
                                       String executedBy,
                                       String correlationId) {
        this.id = id;
        this.policyId = policyId;
        this.policyVersion = policyVersion;
        this.targetDataset = targetDataset;
        this.scopeKey = scopeKey;
        this.approvalId = approvalId;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.dryRunId = dryRunId;
        this.dryRunResultHash = dryRunResultHash;
        this.cutoffAt = cutoffAt;
        this.expectedEligibleCount = expectedEligibleCount;
        this.batchLimit = batchLimit;
        this.idempotencyKey = idempotencyKey;
        this.requestHash = requestHash;
        this.reason = reason;
        this.changeTicket = changeTicket;
        this.restoreDrillRef = restoreDrillRef;
        this.approvedBy = approvedBy;
        this.executedBy = executedBy;
        this.correlationId = correlationId;
        this.startedAt = Instant.now();
    }

    public boolean succeeded() {
        return STATUS_SUCCEEDED.equals(status);
    }

    public boolean inProgress() {
        return STATUS_IN_PROGRESS.equals(status);
    }

    public void complete(long rowsRedacted, String responseJson, Instant completedAt) {
        this.rowsRedacted = rowsRedacted;
        this.responseJson = responseJson == null || responseJson.isBlank() ? "{}" : responseJson;
        this.completedAt = completedAt;
        this.status = STATUS_SUCCEEDED;
        this.lastError = null;
    }

    public void fail(String error, Instant completedAt) {
        this.lastError = error;
        this.completedAt = completedAt;
        this.status = STATUS_FAILED;
    }

    public UUID getId() { return id; }
    public String getPolicyId() { return policyId; }
    public String getPolicyVersion() { return policyVersion; }
    public String getTargetDataset() { return targetDataset; }
    public String getScopeKey() { return scopeKey; }
    public UUID getApprovalId() { return approvalId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getDryRunId() { return dryRunId; }
    public String getDryRunResultHash() { return dryRunResultHash; }
    public Instant getCutoffAt() { return cutoffAt; }
    public long getExpectedEligibleCount() { return expectedEligibleCount; }
    public int getBatchLimit() { return batchLimit; }
    public String getStatus() { return status; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getRequestHash() { return requestHash; }
    public String getReason() { return reason; }
    public String getChangeTicket() { return changeTicket; }
    public String getRestoreDrillRef() { return restoreDrillRef; }
    public String getApprovedBy() { return approvedBy; }
    public String getExecutedBy() { return executedBy; }
    public String getCorrelationId() { return correlationId; }
    public long getRowsRedacted() { return rowsRedacted; }
    public String getLastError() { return lastError; }
    public String getResponseJson() { return responseJson; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getStartedAt() { return startedAt; }
    public Instant getCompletedAt() { return completedAt; }
}
