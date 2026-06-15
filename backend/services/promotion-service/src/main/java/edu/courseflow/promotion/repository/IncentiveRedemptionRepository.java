package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveRedemption;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import jakarta.persistence.LockModeType;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveRedemptionRepository extends JpaRepository<IncentiveRedemption, UUID> {
    Optional<IncentiveRedemption> findByReservationId(UUID reservationId);

    long countByTenantIdAndApplicationIdAndProfileIdAndRedeemedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            String profileId,
            Instant since);

    long countByTenantIdAndApplicationIdAndProfileIdAndStatusAndReversedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            String profileId,
            String status,
            Instant since);

    long countByTenantIdAndApplicationIdAndCouponIdInAndRedeemedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            List<UUID> couponIds,
            Instant since);

    long countByTenantIdAndApplicationIdAndExternalReferenceAndRedeemedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            String externalReference,
            Instant since);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select r from IncentiveRedemption r
            where r.id = :redemptionId
            """)
    Optional<IncentiveRedemption> lockById(@Param("redemptionId") UUID redemptionId);

    @Query("""
            select r from IncentiveRedemption r
            where (:tenantId is null or r.tenantId = :tenantId)
              and (:applicationId is null or r.applicationId = :applicationId)
              and (:profileId is null or r.profileId = :profileId)
              and (:externalReference is null or r.externalReference = :externalReference)
              and (:campaignId is null or r.campaignId = :campaignId)
              and (:couponId is null or r.couponId = :couponId)
            order by r.redeemedAt desc
            """)
    List<IncentiveRedemption> listFiltered(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("profileId") String profileId,
            @Param("externalReference") String externalReference,
            @Param("campaignId") UUID campaignId,
            @Param("couponId") UUID couponId,
            Pageable pageable);
}
