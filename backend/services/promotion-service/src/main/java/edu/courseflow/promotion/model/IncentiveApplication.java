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
@Table(name = "incentive_applications")
public class IncentiveApplication {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "created_by", length = 80)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private Long version;

    protected IncentiveApplication() {
    }

    public IncentiveApplication(String tenantId, String applicationId, String name, String status, String createdBy) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.name = name == null || name.isBlank() ? applicationId : name.trim();
        changeStatus(status == null || status.isBlank() ? "DRAFT" : status);
        this.createdBy = createdBy;
    }

    @PreUpdate
    void touch() {
        this.updatedAt = Instant.now();
    }

    public void rename(String nextName) {
        if (nextName != null && !nextName.isBlank()) {
            this.name = nextName.trim();
        }
    }

    public void changeStatus(String nextStatus) {
        String normalized = nextStatus == null ? "" : nextStatus.trim().toUpperCase();
        if ("DRAFT".equals(normalized) || "ACTIVE".equals(normalized)
                || "SUSPENDED".equals(normalized) || "ARCHIVED".equals(normalized)) {
            this.status = normalized;
            return;
        }
        throw new IllegalArgumentException("Unsupported incentive application status: " + nextStatus);
    }

    public boolean active() {
        return "ACTIVE".equals(status);
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getName() { return name; }
    public String getStatus() { return status; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
