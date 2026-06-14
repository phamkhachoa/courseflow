package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveOperationApproval;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveOperationApprovalRepository extends JpaRepository<IncentiveOperationApproval, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select approval from IncentiveOperationApproval approval where approval.id = :id")
    Optional<IncentiveOperationApproval> lockById(@Param("id") UUID id);

    @Query("""
            select approval from IncentiveOperationApproval approval
             where approval.operationType = :operationType
               and approval.targetType = :targetType
               and approval.targetId = :targetId
               and approval.subjectHash = :subjectHash
               and approval.status in ('PENDING_APPROVAL', 'APPROVED')
            """)
    Optional<IncentiveOperationApproval> findActiveForSubject(
            @Param("operationType") String operationType,
            @Param("targetType") String targetType,
            @Param("targetId") UUID targetId,
            @Param("subjectHash") String subjectHash);

    @Query("""
            select approval from IncentiveOperationApproval approval
             where approval.operationType = :operationType
               and approval.tenantId = :tenantId
               and approval.applicationId = :applicationId
               and (:campaignId is null or approval.campaignId = :campaignId)
               and (:status is null or approval.status = :status)
             order by approval.createdAt desc
            """)
    List<IncentiveOperationApproval> search(
            @Param("operationType") String operationType,
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignId") UUID campaignId,
            @Param("status") String status,
            Pageable pageable);
}
