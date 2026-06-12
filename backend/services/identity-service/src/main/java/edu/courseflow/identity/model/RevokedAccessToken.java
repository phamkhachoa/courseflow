package edu.courseflow.identity.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "revoked_access_tokens")
public class RevokedAccessToken {

    @Id
    @Column(length = 80)
    private String jti;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "revoked_at", nullable = false)
    private Instant revokedAt = Instant.now();

    @Column(nullable = false, length = 80)
    private String reason;

    protected RevokedAccessToken() {
    }

    public RevokedAccessToken(String jti, Long userId, Instant expiresAt, String reason) {
        this.jti = jti;
        this.userId = userId;
        this.expiresAt = expiresAt;
        this.reason = reason;
        this.revokedAt = Instant.now();
    }

    public String getJti() {
        return jti;
    }

    public Long getUserId() {
        return userId;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }

    public Instant getRevokedAt() {
        return revokedAt;
    }

    public String getReason() {
        return reason;
    }
}
