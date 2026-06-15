package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "loyalty_tier_policies")
public class LoyaltyTierPolicy {

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

    @Column(name = "tier_code", nullable = false, length = 80)
    private String tierCode;

    @Column(nullable = false, length = 160)
    private String name;

    @Column(nullable = false)
    private int rank;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @Column(name = "qualification_points", nullable = false)
    private long qualificationPoints;

    @Column(name = "qualification_window_days", nullable = false)
    private int qualificationWindowDays = 365;

    @Column(name = "downgrade_grace_days", nullable = false)
    private int downgradeGraceDays = 30;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "benefits_json", nullable = false, columnDefinition = "jsonb")
    private String benefitsJson = "{}";

    @Column(name = "created_by", length = 160)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected LoyaltyTierPolicy() {
    }

    public LoyaltyTierPolicy(
            LoyaltyProgram program,
            String tierCode,
            String name,
            int rank,
            long qualificationPoints,
            int qualificationWindowDays,
            int downgradeGraceDays,
            String benefitsJson,
            String createdBy) {
        this.id = UUID.randomUUID();
        this.programUuid = program.getId();
        this.tenantId = program.getTenantId();
        this.applicationId = program.getApplicationId();
        this.programId = program.getProgramId();
        this.tierCode = normalize(tierCode);
        this.name = name == null || name.isBlank() ? this.tierCode : name.trim();
        this.rank = rank;
        this.qualificationPoints = qualificationPoints;
        this.qualificationWindowDays = qualificationWindowDays;
        this.downgradeGraceDays = downgradeGraceDays;
        this.benefitsJson = benefitsJson == null || benefitsJson.isBlank() ? "{}" : benefitsJson;
        this.createdBy = createdBy;
    }

    public void update(
            String name,
            Integer rank,
            Long qualificationPoints,
            Integer qualificationWindowDays,
            Integer downgradeGraceDays,
            String benefitsJson) {
        if (name != null && !name.isBlank()) {
            this.name = name.trim();
        }
        if (rank != null) {
            this.rank = rank;
        }
        if (qualificationPoints != null) {
            this.qualificationPoints = qualificationPoints;
        }
        if (qualificationWindowDays != null) {
            this.qualificationWindowDays = qualificationWindowDays;
        }
        if (downgradeGraceDays != null) {
            this.downgradeGraceDays = downgradeGraceDays;
        }
        if (benefitsJson != null) {
            this.benefitsJson = benefitsJson.isBlank() ? "{}" : benefitsJson;
        }
        this.updatedAt = Instant.now();
    }

    public void changeStatus(String status) {
        String nextStatus = status == null || status.isBlank() ? "" : status.trim().toUpperCase();
        if (!STATUSES.contains(nextStatus)) {
            throw new IllegalArgumentException("Unsupported loyalty tier policy status: " + status);
        }
        this.status = nextStatus;
        this.updatedAt = Instant.now();
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toUpperCase();
    }

    public UUID getId() { return id; }
    public UUID getProgramUuid() { return programUuid; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getTierCode() { return tierCode; }
    public String getName() { return name; }
    public int getRank() { return rank; }
    public String getStatus() { return status; }
    public long getQualificationPoints() { return qualificationPoints; }
    public int getQualificationWindowDays() { return qualificationWindowDays; }
    public int getDowngradeGraceDays() { return downgradeGraceDays; }
    public String getBenefitsJson() { return benefitsJson; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
