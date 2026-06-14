package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;

@Entity
@Table(name = "loyalty_programs")
public class LoyaltyProgram {

    private static final Set<String> STATUSES = Set.of("DRAFT", "ACTIVE", "SUSPENDED", "ARCHIVED");

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(nullable = false)
    private String name;

    @Column(name = "point_unit", nullable = false, length = 40)
    private String pointUnit = "POINT";

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @Column(name = "allow_negative_balance", nullable = false)
    private boolean allowNegativeBalance;

    @Column(name = "default_points_expiry_days")
    private Integer defaultPointsExpiryDays;

    @Column(name = "created_by", length = 160)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyProgram() {
    }

    public LoyaltyProgram(String tenantId, String applicationId, String programId, String name,
                          String pointUnit, boolean allowNegativeBalance, Integer defaultPointsExpiryDays,
                          String createdBy) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.programId = programId;
        this.name = name;
        this.pointUnit = pointUnit == null || pointUnit.isBlank() ? "POINT" : pointUnit.trim();
        this.allowNegativeBalance = allowNegativeBalance;
        if (defaultPointsExpiryDays != null) {
            this.defaultPointsExpiryDays = defaultPointsExpiryDays;
        }
        this.createdBy = createdBy;
    }

    public void update(String name, String pointUnit, Boolean allowNegativeBalance, Integer defaultPointsExpiryDays) {
        if (name != null && !name.isBlank()) {
            this.name = name.trim();
        }
        if (pointUnit != null && !pointUnit.isBlank()) {
            this.pointUnit = pointUnit.trim();
        }
        if (allowNegativeBalance != null) {
            this.allowNegativeBalance = allowNegativeBalance;
        }
        this.defaultPointsExpiryDays = defaultPointsExpiryDays;
        this.updatedAt = Instant.now();
    }

    public void changeStatus(String status) {
        String nextStatus = status == null || status.isBlank() ? "" : status.trim().toUpperCase();
        if (!STATUSES.contains(nextStatus)) {
            throw new IllegalArgumentException("Unsupported loyalty program status: " + status);
        }
        this.status = nextStatus;
        this.updatedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getName() { return name; }
    public String getPointUnit() { return pointUnit; }
    public String getStatus() { return status; }
    public boolean isAllowNegativeBalance() { return allowNegativeBalance; }
    public Integer getDefaultPointsExpiryDays() { return defaultPointsExpiryDays; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
