package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "incentive_quota_counters")
public class IncentiveQuotaCounter {

    public static final String WILDCARD_PROFILE = "*";

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "scope_type", nullable = false, length = 40)
    private String scopeType;

    @Column(name = "scope_id", nullable = false, length = 120)
    private String scopeId;

    @Column(name = "profile_id", nullable = false, length = 120)
    private String profileId = WILDCARD_PROFILE;

    @Column(name = "limit_count", nullable = false)
    private int limitCount;

    @Column(name = "used_count", nullable = false)
    private int usedCount;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private Long version;

    protected IncentiveQuotaCounter() {
    }

    public IncentiveQuotaCounter(String tenantId, String applicationId, String scopeType, String scopeId,
                                 String profileId, int limitCount) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.scopeType = scopeType;
        this.scopeId = scopeId;
        this.profileId = profileId == null || profileId.isBlank() ? WILDCARD_PROFILE : profileId;
        this.limitCount = limitCount;
    }

    @PreUpdate
    void touch() {
        this.updatedAt = Instant.now();
    }

    public void consume() {
        if (usedCount >= limitCount) {
            throw new IllegalStateException("Quota exhausted");
        }
        usedCount += 1;
    }

    public void consumeAgainstLimit(int effectiveLimit) {
        if (effectiveLimit <= 0 || usedCount >= effectiveLimit) {
            throw new IllegalStateException("Quota exhausted");
        }
        usedCount += 1;
        if (limitCount != effectiveLimit) {
            limitCount = effectiveLimit;
        }
    }

    public void release() {
        if (usedCount > 0) {
            usedCount -= 1;
        }
    }

    public boolean hasAvailableCapacity() {
        return usedCount < limitCount;
    }

    public boolean hasAvailableCapacity(int effectiveLimit) {
        return effectiveLimit > 0 && usedCount < effectiveLimit;
    }

    public UUID getId() { return id; }
    public int getUsedCount() { return usedCount; }
    public int getLimitCount() { return limitCount; }
}
