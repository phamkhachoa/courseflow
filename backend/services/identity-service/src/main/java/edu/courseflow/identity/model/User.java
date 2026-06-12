package edu.courseflow.identity.model;

import edu.courseflow.commonlibrary.model.AbstractAuditEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Duration;
import java.time.Instant;

@Entity
@Table(name = "users")
public class User extends AbstractAuditEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String email;

    @Column(name = "email_verified", nullable = false)
    private boolean emailVerified = false;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    @Column(name = "password_changed_at", nullable = false)
    private Instant passwordChangedAt = Instant.now();

    @Column(name = "must_change_password", nullable = false)
    private boolean mustChangePassword = false;

    @Column(name = "full_name", nullable = false)
    private String fullName;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 40)
    private UserStatus status = UserStatus.ACTIVE;

    @Column(name = "failed_login_count", nullable = false)
    private int failedLoginCount = 0;

    @Column(name = "locked_until")
    private Instant lockedUntil;

    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    @Column(name = "access_tokens_valid_after")
    private Instant accessTokensValidAfter;

    @Column(name = "mfa_enabled", nullable = false)
    private boolean mfaEnabled = false;

    @Column(name = "mfa_secret")
    private String mfaSecret;

    @Version
    @Column(nullable = false)
    private long version;

    protected User() {
    }

    public User(String email, String passwordHash, String fullName) {
        this.email = email;
        this.passwordHash = passwordHash;
        this.fullName = fullName;
        this.passwordChangedAt = Instant.now();
        this.status = UserStatus.ACTIVE;
    }

    public Long getId() {
        return id;
    }

    public String getEmail() {
        return email;
    }

    public boolean isEmailVerified() {
        return emailVerified;
    }

    public void markEmailVerified() {
        this.emailVerified = true;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public void updatePassword(String newHash) {
        this.passwordHash = newHash;
        this.passwordChangedAt = Instant.now();
        this.mustChangePassword = false;
    }

    public Instant getPasswordChangedAt() {
        return passwordChangedAt;
    }

    public boolean isMustChangePassword() {
        return mustChangePassword;
    }

    public void requirePasswordChange() {
        this.mustChangePassword = true;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public UserStatus getStatus() {
        return status;
    }

    public void setStatus(UserStatus status) {
        this.status = status;
    }

    public boolean isActive() {
        return status == UserStatus.ACTIVE && !isLockedOut();
    }

    public int getFailedLoginCount() {
        return failedLoginCount;
    }

    public Instant getLockedUntil() {
        return lockedUntil;
    }

    public boolean isLockedOut() {
        return lockedUntil != null && lockedUntil.isAfter(Instant.now());
    }

    public void recordFailedLogin(int lockoutThreshold, Duration lockoutDuration) {
        this.failedLoginCount += 1;
        if (this.failedLoginCount >= lockoutThreshold) {
            this.lockedUntil = Instant.now().plus(lockoutDuration);
        }
    }

    public void recordSuccessfulLogin() {
        this.failedLoginCount = 0;
        this.lockedUntil = null;
        this.lastLoginAt = Instant.now();
    }

    public Instant getLastLoginAt() {
        return lastLoginAt;
    }

    public Instant getAccessTokensValidAfter() {
        return accessTokensValidAfter;
    }

    public void revokeAccessTokens() {
        this.accessTokensValidAfter = Instant.now();
    }

    public boolean isMfaEnabled() {
        return mfaEnabled;
    }

    public String getMfaSecret() {
        return mfaSecret;
    }

    public void enableMfa(String secret) {
        this.mfaEnabled = true;
        this.mfaSecret = secret;
    }

    public void disableMfa() {
        this.mfaEnabled = false;
        this.mfaSecret = null;
    }
}
