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
@Table(name = "incentive_coupon_import_rows")
public class IncentiveCouponImportRow {

    @Id
    private UUID id;

    @Column(name = "batch_id", nullable = false)
    private UUID batchId;

    @Column(name = "row_number", nullable = false)
    private int rowNumber;

    @Column(name = "code_mask", length = 80)
    private String codeMask;

    @Column(name = "row_status", nullable = false, length = 40)
    private String rowStatus;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "issue_codes_json", nullable = false, columnDefinition = "jsonb")
    private String issueCodesJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "issues_json", nullable = false, columnDefinition = "jsonb")
    private String issuesJson;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected IncentiveCouponImportRow() {
    }

    public IncentiveCouponImportRow(UUID batchId,
                                    int rowNumber,
                                    String codeMask,
                                    String rowStatus,
                                    String issueCodesJson,
                                    String issuesJson) {
        this.id = UUID.randomUUID();
        this.batchId = batchId;
        this.rowNumber = rowNumber;
        this.codeMask = codeMask;
        this.rowStatus = rowStatus;
        this.issueCodesJson = issueCodesJson == null || issueCodesJson.isBlank() ? "[]" : issueCodesJson;
        this.issuesJson = issuesJson == null || issuesJson.isBlank() ? "[]" : issuesJson;
    }

    public UUID getId() { return id; }
    public UUID getBatchId() { return batchId; }
    public int getRowNumber() { return rowNumber; }
    public String getCodeMask() { return codeMask; }
    public String getRowStatus() { return rowStatus; }
    public String getIssueCodesJson() { return issueCodesJson; }
    public String getIssuesJson() { return issuesJson; }
    public Instant getCreatedAt() { return createdAt; }
}
