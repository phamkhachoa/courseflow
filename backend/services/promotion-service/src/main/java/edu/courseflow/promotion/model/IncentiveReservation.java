package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "incentive_reservations")
public class IncentiveReservation {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    @Column(name = "campaign_version", nullable = false)
    private Integer campaignVersion;

    @Column(name = "coupon_id")
    private UUID couponId;

    @Column(name = "profile_id", nullable = false, length = 120)
    private String profileId;

    @Column(name = "external_reference", length = 160)
    private String externalReference;

    @Column(nullable = false, length = 40)
    private String status = "RESERVED";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "effects_json", nullable = false, columnDefinition = "jsonb")
    private String effectsJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "request_json", nullable = false, columnDefinition = "jsonb")
    private String requestJson;

    @Column(name = "request_hash", nullable = false, length = 128)
    private String requestHash;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "quota_snapshot_json", nullable = false, columnDefinition = "jsonb")
    private String quotaSnapshotJson = "[]";

    @Column(name = "reserved_at", nullable = false)
    private Instant reservedAt = Instant.now();

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "committed_at")
    private Instant committedAt;

    @Column(name = "cancelled_at")
    private Instant cancelledAt;

    @Column(name = "failure_reason", length = 120)
    private String failureReason;

    @Version
    private Long version;

    protected IncentiveReservation() {
    }

    public IncentiveReservation(String tenantId, String applicationId, UUID campaignId, Integer campaignVersion,
                                UUID couponId,
                                String profileId, String externalReference, String effectsJson,
                                String requestJson, String requestHash, String quotaSnapshotJson,
                                Instant expiresAt) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignId = campaignId;
        this.campaignVersion = campaignVersion;
        this.couponId = couponId;
        this.profileId = profileId;
        this.externalReference = externalReference;
        this.effectsJson = effectsJson;
        this.requestJson = requestJson;
        this.requestHash = requestHash;
        this.quotaSnapshotJson = quotaSnapshotJson == null || quotaSnapshotJson.isBlank() ? "[]" : quotaSnapshotJson;
        this.expiresAt = expiresAt;
    }

    public void commit(String externalReference) {
        if ("REDEEMED".equals(status)) {
            return;
        }
        if (!"RESERVED".equals(status)) {
            throw new IllegalStateException("Reservation is not committable");
        }
        this.status = "REDEEMED";
        this.externalReference = externalReference == null || externalReference.isBlank()
                ? this.externalReference
                : externalReference;
        this.committedAt = Instant.now();
    }

    public void cancel(String reason) {
        if (!"RESERVED".equals(status)) {
            throw new IllegalStateException("Reservation is not cancellable");
        }
        this.status = "CANCELLED";
        this.cancelledAt = Instant.now();
        this.failureReason = reason;
    }

    public void expire(String reason) {
        if (!"RESERVED".equals(status)) {
            return;
        }
        this.status = "EXPIRED";
        this.failureReason = reason;
    }

    public boolean isExpired(Instant now) {
        return expiresAt != null && now.isAfter(expiresAt);
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getCampaignId() { return campaignId; }
    public Integer getCampaignVersion() { return campaignVersion; }
    public UUID getCouponId() { return couponId; }
    public String getProfileId() { return profileId; }
    public String getExternalReference() { return externalReference; }
    public String getStatus() { return status; }
    public String getEffectsJson() { return effectsJson; }
    public String getRequestJson() { return requestJson; }
    public String getRequestHash() { return requestHash; }
    public String getQuotaSnapshotJson() { return quotaSnapshotJson; }
    public Instant getReservedAt() { return reservedAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public Instant getCommittedAt() { return committedAt; }
    public Instant getCancelledAt() { return cancelledAt; }
    public String getFailureReason() { return failureReason; }
}
