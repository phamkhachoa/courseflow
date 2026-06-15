package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyRewardRedemption;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyRewardRedemptionRepository extends JpaRepository<LoyaltyRewardRedemption, UUID> {

    Optional<LoyaltyRewardRedemption> findByTenantIdAndApplicationIdAndIdempotencyKey(
            String tenantId,
            String applicationId,
            String idempotencyKey);

    Optional<LoyaltyRewardRedemption> findByFulfillmentProviderAndFulfillmentRef(
            String fulfillmentProvider,
            String fulfillmentRef);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select redemption from LoyaltyRewardRedemption redemption where redemption.id = :id")
    Optional<LoyaltyRewardRedemption> findByIdForUpdate(@Param("id") UUID id);

    long countByRewardIdAndStatus(UUID rewardId, String status);

    long countByRewardIdAndProfileIdAndStatus(UUID rewardId, String profileId, String status);

    @Query("""
            select redemption
            from LoyaltyRewardRedemption redemption
            where (:tenantId is null or redemption.tenantId = :tenantId)
              and (:applicationId is null or redemption.applicationId = :applicationId)
              and (:programId is null or redemption.programId = :programId)
              and (:profileId is null or redemption.profileId = :profileId)
              and (:rewardId is null or redemption.rewardId = :rewardId)
              and (:status is null or redemption.status = :status)
              and (:fulfillmentStatus is null or redemption.fulfillmentStatus = :fulfillmentStatus)
              and (:fromRedeemedAt is null or redemption.redeemedAt >= :fromRedeemedAt)
              and (:toRedeemedAt is null or redemption.redeemedAt < :toRedeemedAt)
            order by redemption.redeemedAt desc
            """)
    List<LoyaltyRewardRedemption> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId,
            @Param("rewardId") UUID rewardId,
            @Param("status") String status,
            @Param("fulfillmentStatus") String fulfillmentStatus,
            @Param("fromRedeemedAt") Instant from,
            @Param("toRedeemedAt") Instant to,
            Pageable pageable);

    @Query("""
            select redemption
            from LoyaltyRewardRedemption redemption
            where redemption.status = 'REVERSED'
              and redemption.tenantId = :tenantId
              and redemption.applicationId = :applicationId
              and (:programId is null or redemption.programId = :programId)
              and (:profileId is null or redemption.profileId = :profileId)
              and (:fromReversedAt is null or redemption.reversedAt >= :fromReversedAt)
              and (:toReversedAt is null or redemption.reversedAt < :toReversedAt)
            order by redemption.reversedAt desc
            """)
    List<LoyaltyRewardRedemption> searchReversedForReconciliation(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId,
            @Param("fromReversedAt") Instant from,
            @Param("toReversedAt") Instant to,
            Pageable pageable);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select redemption
            from LoyaltyRewardRedemption redemption
            where redemption.status = 'COMMITTED'
              and redemption.fulfillmentStatus in ('PENDING', 'FAILED')
              and redemption.fulfillmentNextAttemptAt is not null
              and redemption.fulfillmentNextAttemptAt <= :now
            order by redemption.fulfillmentNextAttemptAt asc, redemption.redeemedAt asc
            """)
    List<LoyaltyRewardRedemption> findDueFulfillmentsForUpdate(@Param("now") Instant now, Pageable pageable);
}
