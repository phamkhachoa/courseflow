package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyTierPolicy;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyTierPolicyRepository extends JpaRepository<LoyaltyTierPolicy, UUID> {
    Optional<LoyaltyTierPolicy> findByProgramUuidAndTierCode(UUID programUuid, String tierCode);

    @Query("""
            select policy
            from LoyaltyTierPolicy policy
            where policy.programUuid = :programUuid
              and policy.status = 'ACTIVE'
            order by policy.rank asc
            """)
    List<LoyaltyTierPolicy> findActiveByProgram(@Param("programUuid") UUID programUuid);

    @Query("""
            select policy
            from LoyaltyTierPolicy policy
            where (:tenantId is null or policy.tenantId = :tenantId)
              and (:applicationId is null or policy.applicationId = :applicationId)
              and (:programId is null or policy.programId = :programId)
              and (:status is null or policy.status = :status)
            order by policy.tenantId asc, policy.applicationId asc, policy.programId asc, policy.rank asc
            """)
    List<LoyaltyTierPolicy> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("status") String status,
            Pageable pageable);
}
