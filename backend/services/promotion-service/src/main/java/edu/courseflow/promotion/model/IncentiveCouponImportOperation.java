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
@Table(name = "incentive_coupon_import_operations")
public class IncentiveCouponImportOperation {

    public static final String STATUS_SUCCEEDED = "SUCCEEDED";

    @Id
    private UUID id;

    @Column(name = "dry_run_id", nullable = false)
    private UUID dryRunId;

    @Column(name = "approval_id")
    private UUID approvalId;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    @Column(name = "result_hash", nullable = false, length = 160)
    private String resultHash;

    @Column(name = "request_hash", nullable = false, length = 160)
    private String requestHash;

    @Column(name = "idempotency_key_hash", nullable = false, length = 160)
    private String idempotencyKeyHash;

    @Column(nullable = false, length = 40)
    private String status = STATUS_SUCCEEDED;

    @Column(name = "requested_rows", nullable = false)
    private int requestedRows;

    @Column(name = "imported_rows", nullable = false)
    private int importedRows;

    @Column(name = "reason", nullable = false, length = 500)
    private String reason;

    @Column(name = "change_ticket", nullable = false, length = 160)
    private String changeTicket;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "response_json", nullable = false, columnDefinition = "jsonb")
    private String responseJson;

    @Column(name = "created_by", length = 80)
    private String createdBy;

    @Column(name = "correlation_id", length = 120)
    private String correlationId;

    @Column(name = "source_client_id", length = 160)
    private String sourceClientId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Version
    private Long version;

    protected IncentiveCouponImportOperation() {
    }

    public IncentiveCouponImportOperation(UUID id,
                                          UUID dryRunId,
                                          UUID approvalId,
                                          String tenantId,
                                          String applicationId,
                                          UUID campaignId,
                                          String resultHash,
                                          String requestHash,
                                          String idempotencyKeyHash,
                                          int requestedRows,
                                          int importedRows,
                                          String reason,
                                          String changeTicket,
                                          String responseJson,
                                          String createdBy,
                                          String correlationId,
                                          String sourceClientId) {
        this.id = id == null ? UUID.randomUUID() : id;
        this.dryRunId = dryRunId;
        this.approvalId = approvalId;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignId = campaignId;
        this.resultHash = resultHash;
        this.requestHash = requestHash;
        this.idempotencyKeyHash = idempotencyKeyHash;
        this.requestedRows = requestedRows;
        this.importedRows = importedRows;
        this.reason = reason;
        this.changeTicket = changeTicket;
        this.responseJson = responseJson == null || responseJson.isBlank() ? "{}" : responseJson;
        this.createdBy = createdBy;
        this.correlationId = correlationId;
        this.sourceClientId = sourceClientId;
    }

    public UUID getId() { return id; }
    public UUID getDryRunId() { return dryRunId; }
    public UUID getApprovalId() { return approvalId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getCampaignId() { return campaignId; }
    public String getResultHash() { return resultHash; }
    public String getRequestHash() { return requestHash; }
    public String getIdempotencyKeyHash() { return idempotencyKeyHash; }
    public String getStatus() { return status; }
    public int getRequestedRows() { return requestedRows; }
    public int getImportedRows() { return importedRows; }
    public String getReason() { return reason; }
    public String getChangeTicket() { return changeTicket; }
    public String getResponseJson() { return responseJson; }
    public String getCreatedBy() { return createdBy; }
    public String getCorrelationId() { return correlationId; }
    public String getSourceClientId() { return sourceClientId; }
    public Instant getCreatedAt() { return createdAt; }
}
