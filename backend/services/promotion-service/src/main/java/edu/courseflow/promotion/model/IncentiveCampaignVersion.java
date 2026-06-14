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
@Table(name = "incentive_campaign_versions")
public class IncentiveCampaignVersion implements CampaignDefinitionSnapshot {

    @Id
    private UUID id;

    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

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

    @Column(name = "version_number", nullable = false)
    private int versionNumber;

    @Column(name = "version_status", nullable = false, length = 40)
    private String versionStatus = "DRAFT";

    @Column(name = "active_snapshot", nullable = false)
    private boolean activeSnapshot;

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

    @Column(name = "rollback_source_version")
    private Integer rollbackSourceVersion;

    @Column(name = "created_by", length = 80)
    private String createdBy;

    @Column(name = "submitted_by", length = 80)
    private String submittedBy;

    @Column(name = "reviewed_by", length = 80)
    private String reviewedBy;

    @Column(name = "published_by", length = 80)
    private String publishedBy;

    @Column(name = "review_note", columnDefinition = "TEXT")
    private String reviewNote;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "submitted_at")
    private Instant submittedAt;

    @Column(name = "reviewed_at")
    private Instant reviewedAt;

    @Column(name = "published_at")
    private Instant publishedAt;

    @Version
    private Long version;

    protected IncentiveCampaignVersion() {
    }

    public IncentiveCampaignVersion(IncentiveCampaign campaign, int versionNumber, String createdBy) {
        this.id = UUID.randomUUID();
        this.campaignId = campaign.getId();
        this.tenantId = campaign.getTenantId();
        this.applicationId = campaign.getApplicationId();
        this.code = campaign.getCode();
        this.name = campaign.getName();
        this.description = campaign.getDescription();
        this.incentiveType = campaign.getIncentiveType();
        this.versionNumber = versionNumber;
        this.startsAt = campaign.getStartsAt();
        this.endsAt = campaign.getEndsAt();
        this.priority = campaign.getPriority();
        this.exclusive = campaign.isExclusive();
        this.stackable = campaign.isStackable();
        this.couponRequired = campaign.isCouponRequired();
        this.matchPolicy = campaign.getMatchPolicy();
        this.currency = campaign.getCurrency();
        this.rulesJson = campaign.getRulesJson();
        this.actionsJson = campaign.getActionsJson();
        this.maxRedemptions = campaign.getMaxRedemptions();
        this.maxRedemptionsPerProfile = campaign.getMaxRedemptionsPerProfile();
        this.createdBy = createdBy;
    }

    public IncentiveCampaignVersion(IncentiveCampaignVersion source, int versionNumber, String createdBy) {
        this.id = UUID.randomUUID();
        this.campaignId = source.getCampaignId();
        this.tenantId = source.getTenantId();
        this.applicationId = source.getApplicationId();
        this.code = source.getCode();
        this.name = source.getName();
        this.description = source.getDescription();
        this.incentiveType = source.getIncentiveType();
        this.versionNumber = versionNumber;
        this.startsAt = source.getStartsAt();
        this.endsAt = source.getEndsAt();
        this.priority = source.getPriority();
        this.exclusive = source.isExclusive();
        this.stackable = source.isStackable();
        this.couponRequired = source.isCouponRequired();
        this.matchPolicy = source.getMatchPolicy();
        this.currency = source.getCurrency();
        this.rulesJson = source.getRulesJson();
        this.actionsJson = source.getActionsJson();
        this.maxRedemptions = source.getMaxRedemptions();
        this.maxRedemptionsPerProfile = source.getMaxRedemptionsPerProfile();
        this.rollbackSourceVersion = source.getVersionNumber();
        this.createdBy = createdBy;
    }

    @PreUpdate
    void touch() {
        if ("PUBLISHED".equals(versionStatus) && publishedAt == null) {
            publishedAt = Instant.now();
        }
    }

    public void submit(String actorId, String note) {
        if (!"DRAFT".equals(versionStatus) && !"REJECTED".equals(versionStatus)) {
            throw new IllegalStateException("Only draft or rejected campaign versions can be submitted");
        }
        this.versionStatus = "SUBMITTED";
        this.submittedBy = actorId;
        this.submittedAt = Instant.now();
        this.reviewNote = note;
    }

    public void approve(String actorId, String note) {
        if (!"SUBMITTED".equals(versionStatus)) {
            throw new IllegalStateException("Only submitted campaign versions can be approved");
        }
        if (actorId != null && actorId.equals(createdBy)) {
            throw new IllegalStateException("Campaign version creator cannot approve their own version");
        }
        this.versionStatus = "APPROVED";
        this.reviewedBy = actorId;
        this.reviewedAt = Instant.now();
        this.reviewNote = note;
    }

    public void reject(String actorId, String note) {
        if (!"SUBMITTED".equals(versionStatus)) {
            throw new IllegalStateException("Only submitted campaign versions can be rejected");
        }
        this.versionStatus = "REJECTED";
        this.reviewedBy = actorId;
        this.reviewedAt = Instant.now();
        this.reviewNote = note;
    }

    public void publish(String actorId) {
        if (!"APPROVED".equals(versionStatus)) {
            throw new IllegalStateException("Only approved campaign versions can be published");
        }
        this.versionStatus = "PUBLISHED";
        this.activeSnapshot = true;
        this.publishedBy = actorId;
        this.publishedAt = Instant.now();
    }

    public void supersede() {
        if ("PUBLISHED".equals(versionStatus)) {
            this.versionStatus = "SUPERSEDED";
        }
        this.activeSnapshot = false;
    }

    public void deactivate() {
        this.activeSnapshot = false;
    }

    public void updateDraft(String code,
                            String name,
                            String description,
                            String incentiveType,
                            Instant startsAt,
                            Instant endsAt,
                            Integer priority,
                            Boolean exclusive,
                            Boolean stackable,
                            Boolean couponRequired,
                            String matchPolicy,
                            String currency,
                            String rulesJson,
                            String actionsJson,
                            Integer maxRedemptions,
                            Integer maxRedemptionsPerProfile) {
        if (!"DRAFT".equals(versionStatus) && !"REJECTED".equals(versionStatus)) {
            throw new IllegalStateException("Only draft or rejected campaign versions can be edited");
        }
        if (code != null) {
            this.code = code;
        }
        if (name != null) {
            this.name = name;
        }
        if (description != null) {
            this.description = description;
        }
        if (incentiveType != null) {
            this.incentiveType = incentiveType;
        }
        if (startsAt != null) {
            this.startsAt = startsAt;
        }
        if (endsAt != null) {
            this.endsAt = endsAt;
        }
        if (priority != null) {
            this.priority = priority;
        }
        if (exclusive != null) {
            this.exclusive = exclusive;
        }
        if (stackable != null) {
            this.stackable = stackable;
        }
        if (couponRequired != null) {
            this.couponRequired = couponRequired;
        }
        if (matchPolicy != null) {
            this.matchPolicy = matchPolicy;
        }
        if (currency != null) {
            this.currency = currency;
        }
        if (rulesJson != null) {
            this.rulesJson = rulesJson;
        }
        if (actionsJson != null) {
            this.actionsJson = actionsJson;
        }
        if (maxRedemptions != null) {
            this.maxRedemptions = maxRedemptions;
        }
        if (maxRedemptionsPerProfile != null) {
            this.maxRedemptionsPerProfile = maxRedemptionsPerProfile;
        }
        if ("REJECTED".equals(versionStatus)) {
            this.versionStatus = "DRAFT";
            this.reviewedBy = null;
            this.reviewedAt = null;
            this.reviewNote = null;
        }
    }

    public UUID getId() { return id; }
    @Override public UUID getCampaignId() { return campaignId; }
    @Override public int getCampaignVersion() { return versionNumber; }
    @Override public String getTenantId() { return tenantId; }
    @Override public String getApplicationId() { return applicationId; }
    @Override public String getCode() { return code; }
    @Override public String getName() { return name; }
    @Override public String getDescription() { return description; }
    @Override public String getIncentiveType() { return incentiveType; }
    public int getVersionNumber() { return versionNumber; }
    public String getVersionStatus() { return versionStatus; }
    public boolean isActiveSnapshot() { return activeSnapshot; }
    @Override public Instant getStartsAt() { return startsAt; }
    @Override public Instant getEndsAt() { return endsAt; }
    @Override public int getPriority() { return priority; }
    @Override public boolean isExclusive() { return exclusive; }
    @Override public boolean isStackable() { return stackable; }
    @Override public boolean isCouponRequired() { return couponRequired; }
    @Override public String getMatchPolicy() { return matchPolicy; }
    @Override public String getCurrency() { return currency; }
    @Override public String getRulesJson() { return rulesJson; }
    @Override public String getActionsJson() { return actionsJson; }
    @Override public Integer getMaxRedemptions() { return maxRedemptions; }
    @Override public Integer getMaxRedemptionsPerProfile() { return maxRedemptionsPerProfile; }
    public Integer getRollbackSourceVersion() { return rollbackSourceVersion; }
    public String getCreatedBy() { return createdBy; }
    public String getSubmittedBy() { return submittedBy; }
    public String getReviewedBy() { return reviewedBy; }
    public String getPublishedBy() { return publishedBy; }
    public String getReviewNote() { return reviewNote; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getSubmittedAt() { return submittedAt; }
    public Instant getReviewedAt() { return reviewedAt; }
    public Instant getPublishedAt() { return publishedAt; }
}
