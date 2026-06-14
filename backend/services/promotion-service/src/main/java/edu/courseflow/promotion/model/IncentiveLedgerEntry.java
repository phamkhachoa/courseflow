package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "incentive_ledger_entries")
public class IncentiveLedgerEntry {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "entry_type", nullable = false, length = 40)
    private String entryType;

    @Column(name = "reservation_id")
    private UUID reservationId;

    @Column(name = "redemption_id")
    private UUID redemptionId;

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

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "effect_json", nullable = false, columnDefinition = "jsonb")
    private String effectJson;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected IncentiveLedgerEntry() {
    }

    public IncentiveLedgerEntry(String entryType, IncentiveReservation reservation, UUID redemptionId,
                                String effectJson) {
        this.id = UUID.randomUUID();
        this.tenantId = reservation.getTenantId();
        this.applicationId = reservation.getApplicationId();
        this.entryType = entryType;
        this.reservationId = reservation.getId();
        this.redemptionId = redemptionId;
        this.campaignId = reservation.getCampaignId();
        this.campaignVersion = reservation.getCampaignVersion();
        this.couponId = reservation.getCouponId();
        this.profileId = reservation.getProfileId();
        this.externalReference = reservation.getExternalReference();
        this.effectJson = effectJson;
    }
}
