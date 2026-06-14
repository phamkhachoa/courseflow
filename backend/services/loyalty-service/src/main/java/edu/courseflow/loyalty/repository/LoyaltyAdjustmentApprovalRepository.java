package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyAdjustmentApproval;
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

public interface LoyaltyAdjustmentApprovalRepository extends JpaRepository<LoyaltyAdjustmentApproval, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select approval from LoyaltyAdjustmentApproval approval where approval.id = :id")
    Optional<LoyaltyAdjustmentApproval> findByIdForUpdate(@Param("id") UUID id);

    @Query("""
            select approval from LoyaltyAdjustmentApproval approval
            where approval.tenantId = :tenantId
              and approval.applicationId = :applicationId
              and (:programId is null or approval.programId = :programId)
              and (:profileId is null or approval.profileId = :profileId)
              and (:status is null or approval.status = :status)
              and (:fromRequestedAt is null or approval.requestedAt >= :fromRequestedAt)
              and (:toRequestedAt is null or approval.requestedAt < :toRequestedAt)
            order by approval.requestedAt desc
            """)
    List<LoyaltyAdjustmentApproval> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId,
            @Param("status") String status,
            @Param("fromRequestedAt") Instant from,
            @Param("toRequestedAt") Instant to,
            Pageable pageable);
}
