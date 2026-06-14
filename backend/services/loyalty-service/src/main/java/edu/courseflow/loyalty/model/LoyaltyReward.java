package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(
        name = "loyalty_rewards",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_loyalty_reward_code",
                columnNames = {"tenant_id", "application_id", "program_id", "reward_code"}))
public class LoyaltyReward {

    private static final Set<String> STATUSES = Set.of("DRAFT", "ACTIVE", "SUSPENDED", "ARCHIVED");

    @Id
    private UUID id;

    @Column(name = "program_uuid", nullable = false)
    private UUID programUuid;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(name = "reward_code", nullable = false, length = 120)
    private String rewardCode;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "points_cost", nullable = false)
    private long pointsCost;

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "starts_at")
    private Instant startsAt;

    @Column(name = "ends_at")
    private Instant endsAt;

    @Column(name = "inventory_limit")
    private Long inventoryLimit;

    @Column(name = "per_profile_limit")
    private Integer perProfileLimit;

    @Column(name = "fulfillment_type", nullable = false, length = 60)
    private String fulfillmentType = "MANUAL";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "fulfillment_config_json", nullable = false, columnDefinition = "jsonb")
    private String fulfillmentConfigJson = "{}";

    @Column(name = "created_by", length = 160)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyReward() {
    }

    public LoyaltyReward(
            LoyaltyProgram program,
            String rewardCode,
            String name,
            String description,
            long pointsCost,
            String status,
            Instant startsAt,
            Instant endsAt,
            Long inventoryLimit,
            Integer perProfileLimit,
            String fulfillmentType,
            String fulfillmentConfigJson,
            String createdBy) {
        this.id = UUID.randomUUID();
        this.programUuid = program.getId();
        this.tenantId = program.getTenantId();
        this.applicationId = program.getApplicationId();
        this.programId = program.getProgramId();
        this.rewardCode = rewardCode;
        this.name = name;
        this.description = description;
        this.pointsCost = pointsCost;
        if (startsAt != null) {
            this.startsAt = startsAt;
        }
        if (endsAt != null) {
            this.endsAt = endsAt;
        }
        if (inventoryLimit != null) {
            this.inventoryLimit = inventoryLimit;
        }
        if (perProfileLimit != null) {
            this.perProfileLimit = perProfileLimit;
        }
        this.fulfillmentType = fulfillmentType == null || fulfillmentType.isBlank()
                ? "MANUAL"
                : fulfillmentType.trim().toUpperCase();
        this.fulfillmentConfigJson = fulfillmentConfigJson == null || fulfillmentConfigJson.isBlank()
                ? "{}"
                : fulfillmentConfigJson;
        this.createdBy = createdBy;
        changeStatus(status == null || status.isBlank() ? "DRAFT" : status);
    }

    public void update(
            String name,
            String description,
            Long pointsCost,
            Instant startsAt,
            Instant endsAt,
            Long inventoryLimit,
            Integer perProfileLimit,
            String fulfillmentType,
            String fulfillmentConfigJson) {
        if (name != null && !name.isBlank()) {
            this.name = name.trim();
        }
        if (description != null) {
            this.description = description.isBlank() ? null : description.trim();
        }
        if (pointsCost != null) {
            if (pointsCost <= 0) {
                throw new IllegalArgumentException("Reward pointsCost must be positive");
            }
            this.pointsCost = pointsCost;
        }
        this.startsAt = startsAt;
        this.endsAt = endsAt;
        this.inventoryLimit = inventoryLimit;
        this.perProfileLimit = perProfileLimit;
        if (fulfillmentType != null && !fulfillmentType.isBlank()) {
            this.fulfillmentType = fulfillmentType.trim().toUpperCase();
        }
        if (fulfillmentConfigJson != null && !fulfillmentConfigJson.isBlank()) {
            this.fulfillmentConfigJson = fulfillmentConfigJson;
        }
        this.updatedAt = Instant.now();
    }

    public void changeStatus(String status) {
        String nextStatus = status == null || status.isBlank() ? "" : status.trim().toUpperCase();
        if (!STATUSES.contains(nextStatus)) {
            throw new IllegalArgumentException("Unsupported loyalty reward status: " + status);
        }
        this.status = nextStatus;
        this.updatedAt = Instant.now();
    }

    public boolean activeAt(Instant now) {
        return "ACTIVE".equals(status)
                && (startsAt == null || !startsAt.isAfter(now))
                && (endsAt == null || endsAt.isAfter(now));
    }

    @PreUpdate
    void preUpdate() {
        this.updatedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public UUID getProgramUuid() { return programUuid; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getRewardCode() { return rewardCode; }
    public String getName() { return name; }
    public String getDescription() { return description; }
    public long getPointsCost() { return pointsCost; }
    public String getStatus() { return status; }
    public Instant getStartsAt() { return startsAt; }
    public Instant getEndsAt() { return endsAt; }
    public Long getInventoryLimit() { return inventoryLimit; }
    public Integer getPerProfileLimit() { return perProfileLimit; }
    public String getFulfillmentType() { return fulfillmentType; }
    public String getFulfillmentConfigJson() { return fulfillmentConfigJson; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
