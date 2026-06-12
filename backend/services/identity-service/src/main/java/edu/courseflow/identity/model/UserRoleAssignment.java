package edu.courseflow.identity.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * A scoped, time-bound role grant. We never hard-delete: revoking sets
 * {@code revokedAt} so the
 * grant remains auditable. The unique-live constraint at the DB level lets the
 * same role be
 * re-granted later.
 */
@Entity
@Table(name = "user_role_assignments")
public class UserRoleAssignment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "role_id", nullable = false)
    private Role role;

    @Column(name = "scope_type", nullable = false, length = 40)
    private String scopeType = "PLATFORM";

    @Column(name = "scope_id")
    private String scopeId;

    @Column(name = "granted_by", length = 64)
    private String grantedBy;

    @Column(name = "granted_at", nullable = false)
    private Instant grantedAt = Instant.now();

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "revoked_at")
    private Instant revokedAt;

    @Column(name = "revoked_by", length = 64)
    private String revokedBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected UserRoleAssignment() {
    }

    public UserRoleAssignment(Long userId, Role role, String scopeType, String scopeId,
            String grantedBy, Instant expiresAt) {
        this.userId = userId;
        this.role = role;
        this.scopeType = scopeType;
        this.scopeId = scopeId;
        this.grantedBy = grantedBy;
        this.grantedAt = Instant.now();
        this.expiresAt = expiresAt;
        this.createdAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public Role getRole() {
        return role;
    }

    public String getScopeType() {
        return scopeType;
    }

    public String getScopeId() {
        return scopeId;
    }

    public String getGrantedBy() {
        return grantedBy;
    }

    public Instant getGrantedAt() {
        return grantedAt;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }

    public Instant getRevokedAt() {
        return revokedAt;
    }

    public String getRevokedBy() {
        return revokedBy;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public boolean isActive(Instant now) {
        if (revokedAt != null)
            return false;
        return expiresAt == null || expiresAt.isAfter(now);
    }

    public void updateGrant(String grantedBy, Instant expiresAt) {
        this.grantedBy = grantedBy;
        this.expiresAt = expiresAt;
        this.revokedAt = null;
        this.revokedBy = null;
        this.grantedAt = Instant.now();
    }

    public void revoke(String revokedBy) {
        this.revokedAt = Instant.now();
        this.revokedBy = revokedBy;
    }
}
