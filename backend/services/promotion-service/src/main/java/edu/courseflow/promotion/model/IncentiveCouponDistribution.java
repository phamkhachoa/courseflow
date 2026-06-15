package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "incentive_coupon_distributions")
public class IncentiveCouponDistribution {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    @Column(nullable = false)
    private String name;

    @Column(name = "source_type", nullable = false, length = 40)
    private String sourceType;

    @Column(name = "source_reference", length = 160)
    private String sourceReference;

    @Column(nullable = false, length = 40)
    private String status = "PENDING_APPROVAL";

    @Column(name = "notify_learners", nullable = false)
    private boolean notifyLearners;

    @Column(name = "starts_at")
    private Instant startsAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "max_redemptions")
    private Integer maxRedemptions;

    @Column(name = "max_redemptions_per_profile")
    private Integer maxRedemptionsPerProfile;

    @Column(name = "recipient_count", nullable = false)
    private int recipientCount;

    @Column(name = "issued_count", nullable = false)
    private int issuedCount;

    @Column(name = "revoked_count", nullable = false)
    private int revokedCount;

    @Column(name = "preview_hash", nullable = false, length = 160)
    private String previewHash;

    @Column(length = 500)
    private String reason;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false, columnDefinition = "jsonb")
    private String metadataJson = "{}";

    @Column(name = "created_by", length = 80)
    private String createdBy;

    @Column(name = "approved_by", length = 80)
    private String approvedBy;

    @Column(name = "issued_by", length = 80)
    private String issuedBy;

    @Column(name = "revoked_by", length = 80)
    private String revokedBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "approved_at")
    private Instant approvedAt;

    @Column(name = "issued_at")
    private Instant issuedAt;

    @Column(name = "revoked_at")
    private Instant revokedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private Long version;

    protected IncentiveCouponDistribution() {
    }

    public IncentiveCouponDistribution(String tenantId,
                                       String applicationId,
                                       UUID campaignId,
                                       String name,
                                       String sourceType,
                                       String sourceReference,
                                       boolean notifyLearners,
                                       Instant startsAt,
                                       Instant expiresAt,
                                       Integer maxRedemptions,
                                       Integer maxRedemptionsPerProfile,
                                       int recipientCount,
                                       String previewHash,
                                       String reason,
                                       String metadataJson,
                                       String createdBy) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignId = campaignId;
        this.name = name;
        this.sourceType = sourceType;
        this.sourceReference = sourceReference;
        this.notifyLearners = notifyLearners;
        this.startsAt = startsAt;
        this.expiresAt = expiresAt;
        this.maxRedemptions = maxRedemptions;
        this.maxRedemptionsPerProfile = maxRedemptionsPerProfile;
        this.recipientCount = recipientCount;
        this.previewHash = previewHash;
        this.reason = reason;
        this.metadataJson = metadataJson == null || metadataJson.isBlank() ? "{}" : metadataJson;
        this.createdBy = createdBy;
    }

    @PreUpdate
    void touch() {
        this.updatedAt = Instant.now();
    }

    public void approve(String actorId) {
        requireStatus("PENDING_APPROVAL");
        this.status = "APPROVED";
        this.approvedBy = actorId;
        this.approvedAt = Instant.now();
    }

    public void markIssued(String actorId, int issuedCount) {
        requireStatus("APPROVED");
        this.status = "ISSUED";
        this.issuedBy = actorId;
        this.issuedCount = issuedCount;
        this.issuedAt = Instant.now();
    }

    public void revoke(String actorId, int revokedCount) {
        if ("REVOKED".equals(this.status)) {
            return;
        }
        if (!"PENDING_APPROVAL".equals(this.status) && !"APPROVED".equals(this.status) && !"ISSUED".equals(this.status)) {
            throw new IllegalStateException("Only pending, approved or issued coupon distributions can be revoked");
        }
        this.status = "REVOKED";
        this.revokedBy = actorId;
        this.revokedAt = Instant.now();
        this.revokedCount = revokedCount;
    }

    private void requireStatus(String expected) {
        if (!expected.equals(this.status)) {
            throw new IllegalStateException("Coupon distribution is not " + expected + ": " + this.status);
        }
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getCampaignId() { return campaignId; }
    public String getName() { return name; }
    public String getSourceType() { return sourceType; }
    public String getSourceReference() { return sourceReference; }
    public String getStatus() { return status; }
    public boolean isNotifyLearners() { return notifyLearners; }
    public Instant getStartsAt() { return startsAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public Integer getMaxRedemptions() { return maxRedemptions; }
    public Integer getMaxRedemptionsPerProfile() { return maxRedemptionsPerProfile; }
    public int getRecipientCount() { return recipientCount; }
    public int getIssuedCount() { return issuedCount; }
    public int getRevokedCount() { return revokedCount; }
    public String getPreviewHash() { return previewHash; }
    public String getReason() { return reason; }
    public String getMetadataJson() { return metadataJson; }
    public String getCreatedBy() { return createdBy; }
    public String getApprovedBy() { return approvedBy; }
    public String getIssuedBy() { return issuedBy; }
    public String getRevokedBy() { return revokedBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getApprovedAt() { return approvedAt; }
    public Instant getIssuedAt() { return issuedAt; }
    public Instant getRevokedAt() { return revokedAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
