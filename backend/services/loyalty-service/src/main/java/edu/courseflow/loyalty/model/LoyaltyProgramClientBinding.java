package edu.courseflow.loyalty.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "loyalty_program_client_bindings")
public class LoyaltyProgramClientBinding {

    private static final Set<String> STATUSES = Set.of("ACTIVE", "SUSPENDED");

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "program_id", nullable = false, length = 120)
    private String programId;

    @Column(name = "client_id", nullable = false, length = 120)
    private String clientId;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "allowed_operations", nullable = false, columnDefinition = "jsonb")
    private String allowedOperations = "[]";

    @Column(name = "created_by", length = 160)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected LoyaltyProgramClientBinding() {
    }

    public LoyaltyProgramClientBinding(
            LoyaltyProgram program,
            String clientId,
            String allowedOperations,
            String createdBy) {
        this.id = UUID.randomUUID();
        this.tenantId = program.getTenantId();
        this.applicationId = program.getApplicationId();
        this.programId = program.getProgramId();
        this.clientId = clientId;
        this.allowedOperations = allowedOperations == null || allowedOperations.isBlank()
                ? "[]"
                : allowedOperations;
        this.createdBy = createdBy;
    }

    public void replace(String status, String allowedOperations) {
        String nextStatus = status == null || status.isBlank() ? "ACTIVE" : status.trim().toUpperCase();
        if (!STATUSES.contains(nextStatus)) {
            throw new IllegalArgumentException("Unsupported loyalty client binding status: " + status);
        }
        this.status = nextStatus;
        this.allowedOperations = allowedOperations == null || allowedOperations.isBlank() ? "[]" : allowedOperations;
        this.updatedAt = Instant.now();
    }

    public void suspend() {
        this.status = "SUSPENDED";
        this.updatedAt = Instant.now();
    }

    public boolean active() {
        return "ACTIVE".equalsIgnoreCase(status);
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getClientId() { return clientId; }
    public String getStatus() { return status; }
    public String getAllowedOperations() { return allowedOperations; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
