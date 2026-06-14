package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveLedgerEntry;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveLedgerEntryRepository extends JpaRepository<IncentiveLedgerEntry, UUID> {
    long countByReservationIdAndEntryType(UUID reservationId, String entryType);

    long countByRedemptionIdAndEntryType(UUID redemptionId, String entryType);

    @Query(value = """
            select l.id as ledgerEntryId,
                   l.tenant_id as tenantId,
                   l.application_id as applicationId,
                   l.entry_type as entryType,
                   l.reservation_id as reservationId,
                   coalesce(l.redemption_id, r.id) as redemptionId,
                   l.campaign_id as campaignId,
                   l.campaign_version as campaignVersion,
                   l.coupon_id as couponId,
                   l.profile_id as profileId,
                   l.external_reference as externalReference,
                   l.effect_json as effectJson,
                   l.created_at as ledgerCreatedAt,
                   r.status as redemptionStatus,
                   r.redeemed_at as redeemedAt,
                   r.reversed_at as reversedAt,
                   o.event_type as outboxEventType,
                   o.published_at as outboxPublishedAt,
                   o.payload ->> 'correlationId' as correlationId,
                   o.payload ->> 'sourceClientId' as sourceClientId
            from incentive_ledger_entries l
            left join incentive_redemptions r
              on r.id = l.redemption_id
              or (l.redemption_id is null and r.reservation_id = l.reservation_id)
            left join outbox_events o
              on o.aggregate_type = 'incentive-redemption'
             and o.aggregate_id = cast(coalesce(l.redemption_id, r.id) as text)
             and (
                    (l.entry_type = 'COMMIT' and o.event_type = 'incentive.redemption.committed')
                 or (l.entry_type = 'REVERSE' and o.event_type = 'incentive.redemption.reversed')
             )
            where (:tenantId is null or l.tenant_id = :tenantId)
              and (:applicationId is null or l.application_id = :applicationId)
              and (:profileId is null or l.profile_id = :profileId)
              and (:externalReference is null or l.external_reference = :externalReference)
              and (:campaignId is null or l.campaign_id = :campaignId)
              and (:couponId is null or l.coupon_id = :couponId)
              and (:redemptionId is null or coalesce(l.redemption_id, r.id) = :redemptionId)
              and (:reservationId is null or l.reservation_id = :reservationId)
              and (:entryType is null or l.entry_type = :entryType)
              and (cast(:fromCreatedAt as timestamptz) is null or l.created_at >= :fromCreatedAt)
              and (cast(:toCreatedAt as timestamptz) is null or l.created_at < :toCreatedAt)
            order by l.created_at desc, l.id desc
            limit :limit
            """, nativeQuery = true)
    List<ReconciliationLedgerRow> searchReconciliationRows(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("profileId") String profileId,
            @Param("externalReference") String externalReference,
            @Param("campaignId") UUID campaignId,
            @Param("couponId") UUID couponId,
            @Param("redemptionId") UUID redemptionId,
            @Param("reservationId") UUID reservationId,
            @Param("entryType") String entryType,
            @Param("fromCreatedAt") Instant fromCreatedAt,
            @Param("toCreatedAt") Instant toCreatedAt,
            @Param("limit") int limit);

    interface ReconciliationLedgerRow {
        UUID getLedgerEntryId();
        String getTenantId();
        String getApplicationId();
        String getEntryType();
        UUID getReservationId();
        UUID getRedemptionId();
        UUID getCampaignId();
        Integer getCampaignVersion();
        UUID getCouponId();
        String getProfileId();
        String getExternalReference();
        String getEffectJson();
        Instant getLedgerCreatedAt();
        String getRedemptionStatus();
        Instant getRedeemedAt();
        Instant getReversedAt();
        String getOutboxEventType();
        Instant getOutboxPublishedAt();
        String getCorrelationId();
        String getSourceClientId();
    }
}
