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
@Table(name = "incentive_coupon_distribution_recipients")
public class IncentiveCouponDistributionRecipient {

    @Id
    private UUID id;

    @Column(name = "distribution_id", nullable = false)
    private UUID distributionId;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    @Column(name = "profile_id", nullable = false, length = 120)
    private String profileId;

    @Column(nullable = false, length = 40)
    private String status = "PENDING";

    @Column(name = "coupon_id")
    private UUID couponId;

    @Column(name = "notification_status", nullable = false, length = 40)
    private String notificationStatus = "SUPPRESSED";

    @Column(name = "failure_reason", length = 500)
    private String failureReason;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false, columnDefinition = "jsonb")
    private String metadataJson = "{}";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "issued_at")
    private Instant issuedAt;

    @Column(name = "revoked_at")
    private Instant revokedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private Long version;

    protected IncentiveCouponDistributionRecipient() {
    }

    public IncentiveCouponDistributionRecipient(UUID distributionId,
                                                String tenantId,
                                                String applicationId,
                                                UUID campaignId,
                                                String profileId,
                                                String metadataJson) {
        this.id = UUID.randomUUID();
        this.distributionId = distributionId;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignId = campaignId;
        this.profileId = profileId;
        this.metadataJson = metadataJson == null || metadataJson.isBlank() ? "{}" : metadataJson;
    }

    @PreUpdate
    void touch() {
        this.updatedAt = Instant.now();
    }

    public void issue(UUID couponId, boolean notifyLearner) {
        if (!"PENDING".equals(this.status)) {
            throw new IllegalStateException("Coupon distribution recipient is not pending: " + this.status);
        }
        this.status = "ISSUED";
        this.couponId = couponId;
        this.notificationStatus = notifyLearner ? "QUEUED" : "SUPPRESSED";
        this.issuedAt = Instant.now();
        this.failureReason = null;
    }

    public void revoke(String reason) {
        if ("REVOKED".equals(this.status)) {
            return;
        }
        if (!"ISSUED".equals(this.status) && !"PENDING".equals(this.status)) {
            throw new IllegalStateException("Coupon distribution recipient cannot be revoked: " + this.status);
        }
        this.status = "REVOKED";
        this.revokedAt = Instant.now();
        this.failureReason = reason;
    }

    public UUID getId() { return id; }
    public UUID getDistributionId() { return distributionId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getCampaignId() { return campaignId; }
    public String getProfileId() { return profileId; }
    public String getStatus() { return status; }
    public UUID getCouponId() { return couponId; }
    public String getNotificationStatus() { return notificationStatus; }
    public String getFailureReason() { return failureReason; }
    public String getMetadataJson() { return metadataJson; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getIssuedAt() { return issuedAt; }
    public Instant getRevokedAt() { return revokedAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
