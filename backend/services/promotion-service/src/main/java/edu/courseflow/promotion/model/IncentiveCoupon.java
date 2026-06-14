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
@Table(name = "incentive_coupons")
public class IncentiveCoupon {

    @Id
    private UUID id;

    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    @Column(nullable = false, length = 160)
    private String code;

    @Column(name = "normalized_code", nullable = false, length = 160)
    private String normalizedCode;

    @Column(name = "code_mask", length = 80)
    private String codeMask;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @Column(name = "holder_profile_id", length = 120)
    private String holderProfileId;

    @Column(name = "starts_at")
    private Instant startsAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "max_redemptions")
    private Integer maxRedemptions;

    @Column(name = "max_redemptions_per_profile")
    private Integer maxRedemptionsPerProfile;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false, columnDefinition = "jsonb")
    private String metadataJson = "{}";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private Long version;

    protected IncentiveCoupon() {
    }

    public IncentiveCoupon(UUID campaignId, String code, String normalizedCode, String codeMask,
                           String holderProfileId, Instant startsAt, Instant expiresAt,
                           Integer maxRedemptions, Integer maxRedemptionsPerProfile, String metadataJson) {
        this.id = UUID.randomUUID();
        this.campaignId = campaignId;
        this.code = code;
        this.normalizedCode = normalizedCode;
        this.codeMask = codeMask;
        this.holderProfileId = holderProfileId;
        this.startsAt = startsAt;
        this.expiresAt = expiresAt;
        this.maxRedemptions = maxRedemptions;
        this.maxRedemptionsPerProfile = maxRedemptionsPerProfile;
        this.metadataJson = metadataJson == null || metadataJson.isBlank() ? "{}" : metadataJson;
    }

    @PreUpdate
    void touch() {
        this.updatedAt = Instant.now();
    }

    public void changeStatus(String nextStatus) {
        String normalized = nextStatus == null ? "" : nextStatus.trim().toUpperCase();
        if ("ACTIVE".equals(normalized) || "PAUSED".equals(normalized)
                || "EXPIRED".equals(normalized) || "VOID".equals(normalized)) {
            this.status = normalized;
            return;
        }
        throw new IllegalArgumentException("Unsupported incentive coupon status: " + nextStatus);
    }

    public UUID getId() { return id; }
    public UUID getCampaignId() { return campaignId; }
    public String getCode() { return code; }
    public String getNormalizedCode() { return normalizedCode; }
    public String getCodeMask() { return codeMask; }
    public String getStatus() { return status; }
    public String getHolderProfileId() { return holderProfileId; }
    public Instant getStartsAt() { return startsAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public Integer getMaxRedemptions() { return maxRedemptions; }
    public Integer getMaxRedemptionsPerProfile() { return maxRedemptionsPerProfile; }
    public String getMetadataJson() { return metadataJson; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
