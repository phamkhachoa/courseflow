package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyAccount;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyAccountRepository extends JpaRepository<LoyaltyAccount, UUID> {
    Optional<LoyaltyAccount> findByTenantIdAndApplicationIdAndProgramIdAndProfileId(
            String tenantId, String applicationId, String programId, String profileId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select account from LoyaltyAccount account where account.id = :id")
    Optional<LoyaltyAccount> findByIdForUpdate(@Param("id") UUID id);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select account
            from LoyaltyAccount account
            where account.tenantId = :tenantId
              and account.applicationId = :applicationId
              and account.programId = :programId
              and account.profileId = :profileId
            """)
    Optional<LoyaltyAccount> findByScopeForUpdate(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId);

    @Query("""
            select account
            from LoyaltyAccount account
            where (:tenantId is null or account.tenantId = :tenantId)
              and (:applicationId is null or account.applicationId = :applicationId)
              and (:programId is null or account.programId = :programId)
              and (:profileId is null or account.profileId = :profileId)
              and (:status is null or account.status = :status)
            order by account.openedAt desc
            """)
    List<LoyaltyAccount> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId,
            @Param("status") String status,
            Pageable pageable);
}
