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
@Table(name = "incentive_campaigns")
public class IncentiveCampaign {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(nullable = false, length = 120)
    private String code;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "incentive_type", nullable = false, length = 40)
    private String incentiveType = "PROMOTION";

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "starts_at")
    private Instant startsAt;

    @Column(name = "ends_at")
    private Instant endsAt;

    @Column(nullable = false)
    private int priority;

    @Column(nullable = false)
    private boolean exclusive;

    @Column(nullable = false)
    private boolean stackable = true;

    @Column(name = "coupon_required", nullable = false)
    private boolean couponRequired;

    @Column(name = "match_policy", nullable = false, length = 20)
    private String matchPolicy = "ALL";

    @Column(length = 8)
    private String currency;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "rules_json", nullable = false, columnDefinition = "jsonb")
    private String rulesJson = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "actions_json", nullable = false, columnDefinition = "jsonb")
    private String actionsJson = "[]";

    @Column(name = "max_redemptions")
    private Integer maxRedemptions;

    @Column(name = "max_redemptions_per_profile")
    private Integer maxRedemptionsPerProfile;

    @Column(name = "created_by", length = 80)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Column(name = "published_at")
    private Instant publishedAt;

    @Version
    private Long version;

    protected IncentiveCampaign() {
    }

    public IncentiveCampaign(String tenantId, String applicationId, String code, String name, String description,
                             String incentiveType, Instant startsAt, Instant endsAt, int priority, boolean exclusive,
                             boolean stackable, boolean couponRequired, String matchPolicy, String currency,
                             String rulesJson, String actionsJson, Integer maxRedemptions,
                             Integer maxRedemptionsPerProfile, String createdBy) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.code = code;
        this.name = name;
        this.description = description;
        this.incentiveType = incentiveType == null || incentiveType.isBlank() ? "PROMOTION" : incentiveType;
        this.startsAt = startsAt;
        this.endsAt = endsAt;
        this.priority = priority;
        this.exclusive = exclusive;
        this.stackable = stackable;
        this.couponRequired = couponRequired;
        this.matchPolicy = matchPolicy == null || matchPolicy.isBlank() ? "ALL" : matchPolicy;
        this.currency = currency;
        this.rulesJson = rulesJson;
        this.actionsJson = actionsJson;
        this.maxRedemptions = maxRedemptions;
        this.maxRedemptionsPerProfile = maxRedemptionsPerProfile;
        this.createdBy = createdBy;
    }

    @PreUpdate
    void touch() {
        this.updatedAt = Instant.now();
    }

    public void changeStatus(String nextStatus) {
        String normalized = nextStatus == null ? "" : nextStatus.trim().toUpperCase();
        if ("PUBLISHED".equals(normalized)) {
            this.status = "PUBLISHED";
            this.publishedAt = this.publishedAt == null ? Instant.now() : this.publishedAt;
            return;
        }
        if ("PAUSED".equals(normalized) || "ARCHIVED".equals(normalized) || "DRAFT".equals(normalized)) {
            this.status = normalized;
            return;
        }
        throw new IllegalArgumentException("Unsupported campaign status: " + nextStatus);
    }

    public void publishFrom(IncentiveCampaignVersion version) {
        this.code = version.getCode();
        this.name = version.getName();
        this.description = version.getDescription();
        this.incentiveType = version.getIncentiveType();
        this.startsAt = version.getStartsAt();
        this.endsAt = version.getEndsAt();
        this.priority = version.getPriority();
        this.exclusive = version.isExclusive();
        this.stackable = version.isStackable();
        this.couponRequired = version.isCouponRequired();
        this.matchPolicy = version.getMatchPolicy();
        this.currency = version.getCurrency();
        this.rulesJson = version.getRulesJson();
        this.actionsJson = version.getActionsJson();
        this.maxRedemptions = version.getMaxRedemptions();
        this.maxRedemptionsPerProfile = version.getMaxRedemptionsPerProfile();
        this.status = "PUBLISHED";
        this.publishedAt = version.getPublishedAt() == null ? Instant.now() : version.getPublishedAt();
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getCode() { return code; }
    public String getName() { return name; }
    public String getDescription() { return description; }
    public String getIncentiveType() { return incentiveType; }
    public String getStatus() { return status; }
    public Instant getStartsAt() { return startsAt; }
    public Instant getEndsAt() { return endsAt; }
    public int getPriority() { return priority; }
    public boolean isExclusive() { return exclusive; }
    public boolean isStackable() { return stackable; }
    public boolean isCouponRequired() { return couponRequired; }
    public String getMatchPolicy() { return matchPolicy; }
    public String getCurrency() { return currency; }
    public String getRulesJson() { return rulesJson; }
    public String getActionsJson() { return actionsJson; }
    public Integer getMaxRedemptions() { return maxRedemptions; }
    public Integer getMaxRedemptionsPerProfile() { return maxRedemptionsPerProfile; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public Instant getPublishedAt() { return publishedAt; }
}
