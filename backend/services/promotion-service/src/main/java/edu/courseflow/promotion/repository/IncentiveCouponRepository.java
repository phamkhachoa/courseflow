package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCoupon;
import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveCouponRepository extends JpaRepository<IncentiveCoupon, UUID> {
    Optional<IncentiveCoupon> findByCampaignIdAndNormalizedCode(UUID campaignId, String normalizedCode);

    List<IncentiveCoupon> findByCampaignIdAndNormalizedCodeIn(UUID campaignId, Collection<String> normalizedCodes);

    interface CouponStorageFormatCount {
        String getStorageFormat();

        long getCouponCount();
    }

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select c from IncentiveCoupon c where c.id = :id")
    Optional<IncentiveCoupon> lockById(@Param("id") UUID id);

    @Query("""
            select c from IncentiveCoupon c
            join IncentiveCampaign campaign on campaign.id = c.campaignId
            where (:tenantId is null or campaign.tenantId = :tenantId)
              and (:applicationId is null or campaign.applicationId = :applicationId)
              and (:campaignId is null or c.campaignId = :campaignId)
              and (:status is null or c.status = :status)
              and (:holderProfileId is null or c.holderProfileId = :holderProfileId)
              and (
                    :codeLookupEnabled = false
                    or c.normalizedCode in :codeLookups
                    or lower(c.codeMask) like lower(concat('%', :codeMaskQuery, '%'))
                  )
            order by c.createdAt desc, c.id desc
            """)
    List<IncentiveCoupon> listFiltered(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignId") UUID campaignId,
            @Param("status") String status,
            @Param("holderProfileId") String holderProfileId,
            @Param("codeLookupEnabled") boolean codeLookupEnabled,
            @Param("codeLookups") Collection<String> codeLookups,
            @Param("codeMaskQuery") String codeMaskQuery,
            Pageable pageable);

    @Query(value = """
            select classified.storage_format as storageFormat,
                   count(*) as couponCount
            from (
                select case
                    when c.normalized_code is null or btrim(c.normalized_code) = '' then 'malformed'
                    when c.normalized_code like concat(:currentHmacPrefix, '%')
                        and substring(c.normalized_code from length(:currentHmacPrefix) + 1) ~ '^[0-9a-f]{64}$'
                        then 'current_hmac'
                    when c.normalized_code ~ '^hmac-sha256:[A-Za-z0-9._-]+:[0-9a-f]{64}$' then 'previous_hmac'
                    when c.normalized_code like 'hmac-sha256:%' then 'malformed'
                    when c.normalized_code ~ '^[0-9a-f]{64}$' then 'legacy_sha'
                    else 'legacy_raw'
                end as storage_format
                from incentive_coupons c
                join incentive_campaigns campaign on campaign.id = c.campaign_id
                where (:tenantId is null or campaign.tenant_id = :tenantId)
                  and (:applicationId is null or campaign.application_id = :applicationId)
                  and (:campaignId is null or c.campaign_id = :campaignId)
                  and (:activeOnly = false or c.status = 'ACTIVE')
            ) classified
            group by classified.storage_format
            order by case classified.storage_format
                when 'current_hmac' then 1
                when 'previous_hmac' then 2
                when 'legacy_sha' then 3
                when 'legacy_raw' then 4
                when 'malformed' then 5
                else 99
            end
            """, nativeQuery = true)
    List<CouponStorageFormatCount> countByStorageFormat(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignId") UUID campaignId,
            @Param("activeOnly") boolean activeOnly,
            @Param("currentHmacPrefix") String currentHmacPrefix);
}
