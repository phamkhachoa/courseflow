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
@Table(name = "incentive_redemptions")
public class IncentiveRedemption {

    @Id
    private UUID id;

    @Column(name = "reservation_id")
    private UUID reservationId;

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
    private String status = "REDEEMED";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "effects_json", nullable = false, columnDefinition = "jsonb")
    private String effectsJson;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "request_json", nullable = false, columnDefinition = "jsonb")
    private String requestJson;

    @Column(name = "request_hash", nullable = false, length = 128)
    private String requestHash;

    @Column(name = "redeemed_at", nullable = false)
    private Instant redeemedAt = Instant.now();

    @Column(name = "reversed_at")
    private Instant reversedAt;

    @Column(name = "reversed_by", length = 80)
    private String reversedBy;

    @Version
    private Long version;

    protected IncentiveRedemption() {
    }

    public IncentiveRedemption(IncentiveReservation reservation) {
        this.id = UUID.randomUUID();
        this.reservationId = reservation.getId();
        this.tenantId = reservation.getTenantId();
        this.applicationId = reservation.getApplicationId();
        this.campaignId = reservation.getCampaignId();
        this.campaignVersion = reservation.getCampaignVersion();
        this.couponId = reservation.getCouponId();
        this.profileId = reservation.getProfileId();
        this.externalReference = reservation.getExternalReference();
        this.effectsJson = reservation.getEffectsJson();
        this.requestJson = reservation.getRequestJson();
        this.requestHash = reservation.getRequestHash();
    }

    public void reverse(String actorId) {
        if ("REVERSED".equals(status)) {
            return;
        }
        if (!"REDEEMED".equals(status)) {
            throw new IllegalStateException("Only redeemed incentives can be reversed");
        }
        this.status = "REVERSED";
        this.reversedAt = Instant.now();
        this.reversedBy = actorId;
    }

    public UUID getId() { return id; }
    public UUID getReservationId() { return reservationId; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public UUID getCampaignId() { return campaignId; }
    public Integer getCampaignVersion() { return campaignVersion; }
    public UUID getCouponId() { return couponId; }
    public String getProfileId() { return profileId; }
    public String getExternalReference() { return externalReference; }
    public String getStatus() { return status; }
    public String getEffectsJson() { return effectsJson; }
    public String getRequestHash() { return requestHash; }
    public Instant getRedeemedAt() { return redeemedAt; }
    public Instant getReversedAt() { return reversedAt; }
    public String getReversedBy() { return reversedBy; }
}
