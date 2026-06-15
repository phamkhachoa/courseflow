package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyPromotionPointEffect;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyPromotionPointEffectRepository extends JpaRepository<LoyaltyPromotionPointEffect, UUID> {

    Optional<LoyaltyPromotionPointEffect> findBySourceEventTypeAndEventIdAndEffectIdAndExpectedEntryType(
            String sourceEventType,
            String eventId,
            String effectId,
            String expectedEntryType);

    @Query("""
            select effect
            from LoyaltyPromotionPointEffect effect
            where effect.tenantId = :tenantId
              and effect.applicationId = :applicationId
              and (:programId is null or effect.programId = :programId)
              and (:profileId is null or effect.profileId = :profileId)
              and (:redemptionId is null or effect.redemptionId = :redemptionId)
              and (:expectedEntryType is null or effect.expectedEntryType = :expectedEntryType)
              and (:fromObservedAt is null or effect.observedAt >= :fromObservedAt)
              and (:toObservedAt is null or effect.observedAt < :toObservedAt)
            order by effect.observedAt desc
            """)
    List<LoyaltyPromotionPointEffect> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId,
            @Param("redemptionId") String redemptionId,
            @Param("expectedEntryType") String expectedEntryType,
            @Param("fromObservedAt") Instant from,
            @Param("toObservedAt") Instant to,
            Pageable pageable);
}
