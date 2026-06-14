package edu.courseflow.promotion.service;

import jakarta.annotation.PostConstruct;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "courseflow.promotion.coupon.abuse-guard")
public class CouponAbuseGuardProperties {

    public enum Mode {
        DISABLED,
        SHADOW,
        ENFORCED
    }

    public enum FailPolicy {
        ALLOW_WITH_ALERT,
        DENY_COUPON_REQUIRED
    }

    private Mode mode = Mode.DISABLED;
    private String keyId = "local";
    private String pepper = "courseflow-local-coupon-abuse-guard-pepper-change-me";
    private long windowSeconds = 60;
    private int profileCapacity = 5;
    private int clientCapacity = 100;
    private int applicationCapacity = 500;
    private int couponCapacity = 20;
    private int missingIdentityCapacity = 3;
    private FailPolicy failPolicy = FailPolicy.ALLOW_WITH_ALERT;

    @PostConstruct
    void validate() {
        if (mode == null) {
            mode = Mode.DISABLED;
        }
        if (failPolicy == null) {
            failPolicy = FailPolicy.ALLOW_WITH_ALERT;
        }
        keyId = normalizeKeyId(keyId);
        if (mode != Mode.DISABLED && (pepper == null || pepper.isBlank())) {
            throw new IllegalStateException("Coupon abuse guard pepper must not be blank when guard is enabled");
        }
        pepper = pepper == null ? "" : pepper.trim();
        windowSeconds = Math.max(1, windowSeconds);
        profileCapacity = positive(profileCapacity, 5);
        clientCapacity = positive(clientCapacity, 100);
        applicationCapacity = positive(applicationCapacity, 500);
        couponCapacity = positive(couponCapacity, 20);
        missingIdentityCapacity = positive(missingIdentityCapacity, 3);
    }

    boolean enabled() {
        return mode != Mode.DISABLED;
    }

    Duration window() {
        return Duration.ofSeconds(windowSeconds);
    }

    int capacity(CouponAbuseGuard.Scope scope) {
        return switch (scope) {
            case PROFILE -> profileCapacity;
            case CLIENT -> clientCapacity;
            case APPLICATION -> applicationCapacity;
            case COUPON -> couponCapacity;
            case MISSING_IDENTITY -> missingIdentityCapacity;
            case STORE -> 1;
        };
    }

    private int positive(int value, int fallback) {
        return value > 0 ? value : fallback;
    }

    private String normalizeKeyId(String value) {
        String normalized = value == null || value.isBlank() ? "local" : value.trim();
        if (!normalized.matches("[A-Za-z0-9._-]{1,40}")) {
            throw new IllegalStateException("Coupon abuse guard key id contains unsupported characters");
        }
        return normalized;
    }

    public Mode getMode() {
        return mode;
    }

    public void setMode(Mode mode) {
        this.mode = mode;
    }

    public String getKeyId() {
        return keyId;
    }

    public void setKeyId(String keyId) {
        this.keyId = keyId;
    }

    public String getPepper() {
        return pepper;
    }

    public void setPepper(String pepper) {
        this.pepper = pepper;
    }

    public long getWindowSeconds() {
        return windowSeconds;
    }

    public void setWindowSeconds(long windowSeconds) {
        this.windowSeconds = windowSeconds;
    }

    public int getProfileCapacity() {
        return profileCapacity;
    }

    public void setProfileCapacity(int profileCapacity) {
        this.profileCapacity = profileCapacity;
    }

    public int getClientCapacity() {
        return clientCapacity;
    }

    public void setClientCapacity(int clientCapacity) {
        this.clientCapacity = clientCapacity;
    }

    public int getApplicationCapacity() {
        return applicationCapacity;
    }

    public void setApplicationCapacity(int applicationCapacity) {
        this.applicationCapacity = applicationCapacity;
    }

    public int getCouponCapacity() {
        return couponCapacity;
    }

    public void setCouponCapacity(int couponCapacity) {
        this.couponCapacity = couponCapacity;
    }

    public int getMissingIdentityCapacity() {
        return missingIdentityCapacity;
    }

    public void setMissingIdentityCapacity(int missingIdentityCapacity) {
        this.missingIdentityCapacity = missingIdentityCapacity;
    }

    public FailPolicy getFailPolicy() {
        return failPolicy;
    }

    public void setFailPolicy(FailPolicy failPolicy) {
        this.failPolicy = failPolicy;
    }
}
