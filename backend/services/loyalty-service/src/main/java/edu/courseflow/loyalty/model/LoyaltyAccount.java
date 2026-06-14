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
@Table(name = "loyalty_accounts")
public class LoyaltyAccount {

    private static final Set<String> STATUSES = Set.of("ACTIVE", "SUSPENDED", "CLOSED");

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

    @Column(name = "profile_id", nullable = false, length = 160)
    private String profileId;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @Column(name = "opened_at", nullable = false)
    private Instant openedAt = Instant.now();

    @Column(name = "closed_at")
    private Instant closedAt;

    @Version
    private long version;

    protected LoyaltyAccount() {
    }

    public LoyaltyAccount(LoyaltyProgram program, String profileId) {
        this.id = UUID.randomUUID();
        this.programUuid = program.getId();
        this.tenantId = program.getTenantId();
        this.applicationId = program.getApplicationId();
        this.programId = program.getProgramId();
        this.profileId = profileId;
    }

    public void changeStatus(String status) {
        String nextStatus = status == null || status.isBlank() ? "" : status.trim().toUpperCase();
        if (!STATUSES.contains(nextStatus)) {
            throw new IllegalArgumentException("Unsupported loyalty account status: " + status);
        }
        this.status = nextStatus;
        this.closedAt = "CLOSED".equals(nextStatus) ? Instant.now() : null;
    }

    public UUID getId() { return id; }
    public UUID getProgramUuid() { return programUuid; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getProgramId() { return programId; }
    public String getProfileId() { return profileId; }
    public String getStatus() { return status; }
    public Instant getOpenedAt() { return openedAt; }
    public Instant getClosedAt() { return closedAt; }
}
