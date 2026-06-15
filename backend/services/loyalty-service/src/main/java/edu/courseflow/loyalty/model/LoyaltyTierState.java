package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "loyalty_tier_states")
public class LoyaltyTierState {

    @Id
    private UUID id;

    @Column(name = "account_id", nullable = false)
    private UUID accountId;

    @Column(name = "program_uuid", nullable = false)
    private UUID programUuid;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(name = "profile_id", nullable = false, length = 160)
    private String profileId;

    @Column(name = "tier_policy_id")
    private UUID tierPolicyId;

    @Column(name = "tier_code", nullable = false, length = 80)
    private String tierCode = "BASE";

    @Column(name = "tier_name", nullable = false, length = 160)
    private String tierName = "Base";

    @Column(name = "tier_rank", nullable = false)
    private int tierRank;

    @Column(name = "qualification_points", nullable = false)
    private long qualificationPoints;

    @Column(name = "qualification_window_days")
    private Integer qualificationWindowDays;

    @Column(name = "qualification_window_started_at")
    private Instant qualificationWindowStartedAt;

    @Column(name = "qualification_window_ends_at")
    private Instant qualificationWindowEndsAt;

    @Column(name = "current_period_started_at", nullable = false)
    private Instant currentPeriodStartedAt = Instant.now();

    @Column(name = "qualified_at")
    private Instant qualifiedAt;

    @Column(name = "grace_until")
    private Instant graceUntil;

    @Column(name = "next_tier_policy_id")
    private UUID nextTierPolicyId;

    @Column(name = "next_tier_code", length = 80)
    private String nextTierCode;

    @Column(name = "next_tier_name", length = 160)
    private String nextTierName;

    @Column(name = "next_tier_rank")
    private Integer nextTierRank;

    @Column(name = "next_tier_points_required")
    private Long nextTierPointsRequired;

    @Column(name = "points_to_next")
    private Long pointsToNext;

    @Column(name = "evaluated_at", nullable = false)
    private Instant evaluatedAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyTierState() {
    }

    public LoyaltyTierState(LoyaltyAccount account, Instant now) {
        this.id = UUID.randomUUID();
        this.accountId = account.getId();
        this.programUuid = account.getProgramUuid();
        this.tenantId = account.getTenantId();
        this.applicationId = account.getApplicationId();
        this.programId = account.getProgramId();
        this.profileId = account.getProfileId();
        this.currentPeriodStartedAt = now == null ? Instant.now() : now;
        this.evaluatedAt = this.currentPeriodStartedAt;
        this.updatedAt = this.currentPeriodStartedAt;
    }

    public boolean applyTier(
            LoyaltyTierPolicy currentTier,
            long qualificationPoints,
            Integer qualificationWindowDays,
            Instant windowStartedAt,
            Instant windowEndsAt,
            Instant graceUntil,
            Instant now) {
        String previousTierCode = this.tierCode;
        int previousTierRank = this.tierRank;
        if (currentTier == null) {
            this.tierPolicyId = null;
            this.tierCode = "BASE";
            this.tierName = "Base";
            this.tierRank = 0;
            this.qualifiedAt = null;
        } else {
            this.tierPolicyId = currentTier.getId();
            this.tierCode = currentTier.getTierCode();
            this.tierName = currentTier.getName();
            this.tierRank = currentTier.getRank();
            if (!this.tierCode.equals(previousTierCode)) {
                this.qualifiedAt = now;
            } else if (this.qualifiedAt == null) {
                this.qualifiedAt = now;
            }
        }
        if (!this.tierCode.equals(previousTierCode) || this.tierRank != previousTierRank) {
            this.currentPeriodStartedAt = now;
        }
        this.qualificationPoints = Math.max(0L, qualificationPoints);
        this.qualificationWindowDays = qualificationWindowDays;
        this.qualificationWindowStartedAt = windowStartedAt;
        this.qualificationWindowEndsAt = windowEndsAt;
        this.graceUntil = graceUntil;
        this.evaluatedAt = now;
        this.updatedAt = now;
        return !this.tierCode.equals(previousTierCode) || this.tierRank != previousTierRank;
    }

    public void applyNextTier(
            LoyaltyTierPolicy nextTier,
            long nextTierQualificationPoints,
            Long pointsToNext) {
        if (nextTier == null) {
            this.nextTierPolicyId = null;
            this.nextTierCode = null;
            this.nextTierName = null;
            this.nextTierRank = null;
            this.nextTierPointsRequired = null;
            this.pointsToNext = null;
            return;
        }
        this.nextTierPolicyId = nextTier.getId();
        this.nextTierCode = nextTier.getTierCode();
        this.nextTierName = nextTier.getName();
        this.nextTierRank = nextTier.getRank();
        this.nextTierPointsRequired = nextTier.getQualificationPoints();
        this.pointsToNext = pointsToNext == null
                ? Math.max(0L, nextTier.getQualificationPoints() - nextTierQualificationPoints)
                : Math.max(0L, pointsToNext);
    }

    public UUID getId() { return id; }
    public UUID getAccountId() { return accountId; }
    public UUID getProgramUuid() { return programUuid; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public UUID getTierPolicyId() { return tierPolicyId; }
    public String getTierCode() { return tierCode; }
    public String getTierName() { return tierName; }
    public int getTierRank() { return tierRank; }
    public long getQualificationPoints() { return qualificationPoints; }
    public Integer getQualificationWindowDays() { return qualificationWindowDays; }
    public Instant getQualificationWindowStartedAt() { return qualificationWindowStartedAt; }
    public Instant getQualificationWindowEndsAt() { return qualificationWindowEndsAt; }
    public Instant getCurrentPeriodStartedAt() { return currentPeriodStartedAt; }
    public Instant getQualifiedAt() { return qualifiedAt; }
    public Instant getGraceUntil() { return graceUntil; }
    public UUID getNextTierPolicyId() { return nextTierPolicyId; }
    public String getNextTierCode() { return nextTierCode; }
    public String getNextTierName() { return nextTierName; }
    public Integer getNextTierRank() { return nextTierRank; }
    public Long getNextTierPointsRequired() { return nextTierPointsRequired; }
    public Long getPointsToNext() { return pointsToNext; }
    public Instant getEvaluatedAt() { return evaluatedAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
