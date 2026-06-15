package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyTierState;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyTierStateRepository extends JpaRepository<LoyaltyTierState, UUID> {
    Optional<LoyaltyTierState> findByAccountId(UUID accountId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select state from LoyaltyTierState state where state.accountId = :accountId")
    Optional<LoyaltyTierState> findByAccountIdForUpdate(@Param("accountId") UUID accountId);

    @Query("""
            select state
            from LoyaltyTierState state
            where (:tenantId is null or state.tenantId = :tenantId)
              and (:applicationId is null or state.applicationId = :applicationId)
              and (:programId is null or state.programId = :programId)
              and (:profileId is null or state.profileId = :profileId)
              and (:tierCode is null or state.tierCode = :tierCode)
            order by state.evaluatedAt desc
            """)
    List<LoyaltyTierState> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId,
            @Param("tierCode") String tierCode,
            Pageable pageable);
}
