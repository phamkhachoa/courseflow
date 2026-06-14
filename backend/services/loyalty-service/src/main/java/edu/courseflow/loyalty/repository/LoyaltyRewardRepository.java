package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyReward;
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

public interface LoyaltyRewardRepository extends JpaRepository<LoyaltyReward, UUID> {

    boolean existsByTenantIdAndApplicationIdAndProgramIdAndRewardCode(
            String tenantId,
            String applicationId,
            String programId,
            String rewardCode);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select reward from LoyaltyReward reward where reward.id = :id")
    Optional<LoyaltyReward> findByIdForUpdate(@Param("id") UUID id);

    @Query("""
            select reward
            from LoyaltyReward reward
            where (:tenantId is null or reward.tenantId = :tenantId)
              and (:applicationId is null or reward.applicationId = :applicationId)
              and (:programId is null or reward.programId = :programId)
              and (:status is null or reward.status = :status)
              and (:activeAt is null
                   or (reward.status = 'ACTIVE'
                       and (reward.startsAt is null or reward.startsAt <= :activeAt)
                       and (reward.endsAt is null or reward.endsAt > :activeAt)))
            order by reward.createdAt desc
            """)
    List<LoyaltyReward> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("status") String status,
            @Param("activeAt") Instant activeAt,
            Pageable pageable);
}
