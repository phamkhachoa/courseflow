package edu.courseflow.promotion.service;

import jakarta.annotation.PostConstruct;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "courseflow.promotion.admin-operation-guard")
public class AdminOperationRateGuardProperties {

    public enum Mode {
        DISABLED,
        SHADOW,
        ENFORCED
    }

    public enum FailPolicy {
        ALLOW_WITH_ALERT,
        DENY
    }

    private Mode mode = Mode.DISABLED;
    private String keyId = "local";
    private String pepper = "courseflow-local-admin-operation-rate-guard-pepper-change-me";
    private long windowSeconds = 60;
    private int actorCapacity = 30;
    private int sourceClientCapacity = 120;
    private int applicationCapacity = 500;
    private int campaignCapacity = 120;
    private int contentCapacity = 10;
    private int missingIdentityCapacity = 5;
    private FailPolicy failPolicy = FailPolicy.DENY;

    @PostConstruct
    void validate() {
        if (mode == null) {
            mode = Mode.DISABLED;
        }
        if (failPolicy == null) {
            failPolicy = FailPolicy.DENY;
        }
        keyId = normalizeKeyId(keyId);
        if (mode != Mode.DISABLED && (pepper == null || pepper.isBlank())) {
            throw new IllegalStateException("Admin operation rate guard pepper must not be blank when guard is enabled");
        }
        pepper = pepper == null ? "" : pepper.trim();
        windowSeconds = Math.max(1, windowSeconds);
        actorCapacity = positive(actorCapacity, 30);
        sourceClientCapacity = positive(sourceClientCapacity, 120);
        applicationCapacity = positive(applicationCapacity, 500);
        campaignCapacity = positive(campaignCapacity, 120);
        contentCapacity = positive(contentCapacity, 10);
        missingIdentityCapacity = positive(missingIdentityCapacity, 5);
    }

    boolean enabled() {
        return mode != Mode.DISABLED;
    }

    Duration window() {
        return Duration.ofSeconds(windowSeconds);
    }

    int capacity(AdminOperationRateGuard.Scope scope) {
        return switch (scope) {
            case ACTOR -> actorCapacity;
            case SOURCE_CLIENT -> sourceClientCapacity;
            case APPLICATION -> applicationCapacity;
            case CAMPAIGN -> campaignCapacity;
            case CONTENT -> contentCapacity;
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
            throw new IllegalStateException("Admin operation rate guard key id contains unsupported characters");
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

    public int getActorCapacity() {
        return actorCapacity;
    }

    public void setActorCapacity(int actorCapacity) {
        this.actorCapacity = actorCapacity;
    }

    public int getSourceClientCapacity() {
        return sourceClientCapacity;
    }

    public void setSourceClientCapacity(int sourceClientCapacity) {
        this.sourceClientCapacity = sourceClientCapacity;
    }

    public int getApplicationCapacity() {
        return applicationCapacity;
    }

    public void setApplicationCapacity(int applicationCapacity) {
        this.applicationCapacity = applicationCapacity;
    }

    public int getCampaignCapacity() {
        return campaignCapacity;
    }

    public void setCampaignCapacity(int campaignCapacity) {
        this.campaignCapacity = campaignCapacity;
    }

    public int getContentCapacity() {
        return contentCapacity;
    }

    public void setContentCapacity(int contentCapacity) {
        this.contentCapacity = contentCapacity;
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
