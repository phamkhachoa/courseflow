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
@Table(name = "incentive_application_client_bindings")
public class IncentiveApplicationClientBinding {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "client_id", nullable = false, length = 160)
    private String clientId;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "allowed_operations", nullable = false, columnDefinition = "jsonb")
    private String allowedOperations = "[]";

    @Column(name = "created_by", length = 80)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private Long version;

    protected IncentiveApplicationClientBinding() {
    }

    public IncentiveApplicationClientBinding(String tenantId, String applicationId, String clientId,
                                             String status, String allowedOperations, String createdBy) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.clientId = clientId;
        changeStatus(status == null || status.isBlank() ? "ACTIVE" : status);
        this.allowedOperations = allowedOperations == null || allowedOperations.isBlank() ? "[]" : allowedOperations;
        this.createdBy = createdBy;
    }

    @PreUpdate
    void touch() {
        this.updatedAt = Instant.now();
    }

    public void replace(String status, String allowedOperations) {
        if (status != null && !status.isBlank()) {
            changeStatus(status);
        }
        if (allowedOperations != null && !allowedOperations.isBlank()) {
            this.allowedOperations = allowedOperations;
        }
    }

    public void changeStatus(String nextStatus) {
        String normalized = nextStatus == null ? "" : nextStatus.trim().toUpperCase();
        if ("ACTIVE".equals(normalized) || "SUSPENDED".equals(normalized)) {
            this.status = normalized;
            return;
        }
        throw new IllegalArgumentException("Unsupported application client binding status: " + nextStatus);
    }

    public void suspend() {
        this.status = "SUSPENDED";
    }

    public boolean active() {
        return "ACTIVE".equals(status);
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getClientId() { return clientId; }
    public String getStatus() { return status; }
    public String getAllowedOperations() { return allowedOperations; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
