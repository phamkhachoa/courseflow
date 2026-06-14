package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCouponImportOperation;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveCouponImportOperationRepository extends JpaRepository<IncentiveCouponImportOperation, UUID> {

    Optional<IncentiveCouponImportOperation> findByApprovalId(UUID approvalId);

    Optional<IncentiveCouponImportOperation> findByDryRunId(UUID dryRunId);

    @Query("""
            select operation from IncentiveCouponImportOperation operation
             where operation.tenantId = :tenantId
               and operation.applicationId = :applicationId
               and (:campaignId is null or operation.campaignId = :campaignId)
               and (:approvalId is null or operation.approvalId = :approvalId)
               and (:dryRunId is null or operation.dryRunId = :dryRunId)
               and (:status is null or operation.status = :status)
               and (:from is null or operation.createdAt >= :from)
               and (:to is null or operation.createdAt <= :to)
             order by operation.createdAt desc
            """)
    List<IncentiveCouponImportOperation> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignId") UUID campaignId,
            @Param("approvalId") UUID approvalId,
            @Param("dryRunId") UUID dryRunId,
            @Param("status") String status,
            @Param("from") Instant from,
            @Param("to") Instant to,
            Pageable pageable);
}
