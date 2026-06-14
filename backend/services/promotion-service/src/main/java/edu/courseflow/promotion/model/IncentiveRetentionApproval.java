package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "incentive_retention_approvals")
public class IncentiveRetentionApproval {

    public static final String STATUS_PENDING = "PENDING_APPROVAL";
    public static final String STATUS_APPROVED = "APPROVED";
    public static final String STATUS_REJECTED = "REJECTED";
    public static final String STATUS_EXECUTED = "EXECUTED";
    public static final String STATUS_EXECUTION_FAILED = "EXECUTION_FAILED";

    @Id
    private UUID id;

    @Column(nullable = false, length = 40)
    private String status = STATUS_PENDING;

    @Column(name = "policy_id", nullable = false, length = 120)
    private String policyId;

    @Column(name = "policy_version", nullable = false, length = 40)
    private String policyVersion;

    @Column(name = "target_dataset", nullable = false, length = 120)
    private String targetDataset;

    @Column(name = "scope_key", nullable = false, length = 180)
    private String scopeKey;

    @Column(name = "tenant_id", length = 80)
    private String tenantId;

    @Column(name = "application_id", length = 80)
    private String applicationId;

    @Column(name = "as_of", nullable = false)
    private Instant asOf;

    @Column(name = "cutoff_at", nullable = false)
    private Instant cutoffAt;

    @Column(name = "retention_days", nullable = false)
    private int retentionDays;

    @Column(name = "dry_run_id", nullable = false)
    private UUID dryRunId;

    @Column(name = "dry_run_result_hash", nullable = false, length = 128)
    private String dryRunResultHash;

    @Column(name = "eligible_count", nullable = false)
    private long eligibleCount;

    @Column(name = "batch_limit", nullable = false)
    private int batchLimit;

    @Column(name = "reason", nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Column(name = "change_ticket", nullable = false, length = 160)
    private String changeTicket;

    @Column(name = "restore_drill_ref", nullable = false, length = 160)
    private String restoreDrillRef;

    @Column(name = "requested_by", nullable = false, length = 160)
    private String requestedBy;

    @Column(name = "approved_by", length = 160)
    private String approvedBy;

    @Column(name = "rejected_by", length = 160)
    private String rejectedBy;

    @Column(name = "executed_by", length = 160)
    private String executedBy;

    @Column(columnDefinition = "TEXT")
    private String note;

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

    @Column(name = "failed_at")
    private Instant failedAt;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    protected IncentiveRetentionApproval() {
    }

    public IncentiveRetentionApproval(String policyId,
                                      String policyVersion,
                                      String targetDataset,
                                      String scopeKey,
                                      String tenantId,
                                      String applicationId,
                                      Instant asOf,
                                      Instant cutoffAt,
                                      int retentionDays,
                                      UUID dryRunId,
                                      String dryRunResultHash,
                                      long eligibleCount,
                                      int batchLimit,
                                      String reason,
                                      String changeTicket,
                                      String restoreDrillRef,
                                      String requestedBy,
                                      String correlationId,
                                      String sourceClientId,
                                      Instant expiresAt) {
        this.id = UUID.randomUUID();
        this.policyId = policyId;
        this.policyVersion = policyVersion;
        this.targetDataset = targetDataset;
        this.scopeKey = scopeKey;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.asOf = asOf;
        this.cutoffAt = cutoffAt;
        this.retentionDays = retentionDays;
        this.dryRunId = dryRunId;
        this.dryRunResultHash = dryRunResultHash;
        this.eligibleCount = eligibleCount;
        this.batchLimit = batchLimit;
        this.reason = reason;
        this.changeTicket = changeTicket;
        this.restoreDrillRef = restoreDrillRef;
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

    public boolean expired(Instant now) {
        return expiresAt != null && !expiresAt.isAfter(now);
    }

    public void approve(String actorId, String note, Instant now) {
        this.status = STATUS_APPROVED;
        this.approvedBy = actorId;
        this.note = note;
        this.approvedAt = now;
    }

    public void reject(String actorId, String note, Instant now) {
        this.status = STATUS_REJECTED;
        this.rejectedBy = actorId;
        this.note = note;
        this.rejectedAt = now;
    }

    public void markExecuted(String actorId, Instant now) {
        this.status = STATUS_EXECUTED;
        this.executedBy = actorId;
        this.executedAt = now;
    }

    public void markExecutionFailed(Instant now) {
        this.status = STATUS_EXECUTION_FAILED;
        this.failedAt = now;
    }

    public UUID getId() { return id; }
    public String getStatus() { return status; }
    public String getPolicyId() { return policyId; }
    public String getPolicyVersion() { return policyVersion; }
    public String getTargetDataset() { return targetDataset; }
    public String getScopeKey() { return scopeKey; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public Instant getAsOf() { return asOf; }
    public Instant getCutoffAt() { return cutoffAt; }
    public int getRetentionDays() { return retentionDays; }
    public UUID getDryRunId() { return dryRunId; }
    public String getDryRunResultHash() { return dryRunResultHash; }
    public long getEligibleCount() { return eligibleCount; }
    public int getBatchLimit() { return batchLimit; }
    public String getReason() { return reason; }
    public String getChangeTicket() { return changeTicket; }
    public String getRestoreDrillRef() { return restoreDrillRef; }
    public String getRequestedBy() { return requestedBy; }
    public String getApprovedBy() { return approvedBy; }
    public String getRejectedBy() { return rejectedBy; }
    public String getExecutedBy() { return executedBy; }
    public String getNote() { return note; }
    public String getCorrelationId() { return correlationId; }
    public String getSourceClientId() { return sourceClientId; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getApprovedAt() { return approvedAt; }
    public Instant getRejectedAt() { return rejectedAt; }
    public Instant getExecutedAt() { return executedAt; }
    public Instant getFailedAt() { return failedAt; }
    public Instant getExpiresAt() { return expiresAt; }
}
