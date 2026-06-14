package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveRetentionApproval;
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

public interface IncentiveRetentionApprovalRepository extends JpaRepository<IncentiveRetentionApproval, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select approval from IncentiveRetentionApproval approval where approval.id = :id")
    Optional<IncentiveRetentionApproval> lockById(@Param("id") UUID id);

    @Query("""
            select approval from IncentiveRetentionApproval approval
            where approval.policyId = :policyId
              and approval.scopeKey = :scopeKey
              and approval.dryRunId = :dryRunId
              and approval.dryRunResultHash = :dryRunResultHash
              and approval.batchLimit = :batchLimit
              and approval.status in ('PENDING_APPROVAL', 'APPROVED')
            """)
    Optional<IncentiveRetentionApproval> findActiveForDryRun(
            @Param("policyId") String policyId,
            @Param("scopeKey") String scopeKey,
            @Param("dryRunId") UUID dryRunId,
            @Param("dryRunResultHash") String dryRunResultHash,
            @Param("batchLimit") int batchLimit);

    @Query("""
            select approval from IncentiveRetentionApproval approval
             where ((:tenantId is null and approval.tenantId is null) or approval.tenantId = :tenantId)
               and ((:applicationId is null and approval.applicationId is null) or approval.applicationId = :applicationId)
               and (:approvalId is null or approval.id = :approvalId)
               and (:dryRunId is null or approval.dryRunId = :dryRunId)
               and (:status is null or approval.status = :status)
               and (:policyId is null or approval.policyId = :policyId)
               and (:changeTicket is null or lower(approval.changeTicket) like :changeTicket)
               and (:requestedBy is null or lower(approval.requestedBy) = :requestedBy)
               and (:approvedBy is null or lower(approval.approvedBy) = :approvedBy)
               and (:executedBy is null or lower(approval.executedBy) = :executedBy)
               and (:expired is null
                    or (:expired = true and approval.expiresAt <= :now)
                    or (:expired = false and approval.expiresAt > :now))
               and (:from is null or approval.createdAt >= :from)
               and (:to is null or approval.createdAt <= :to)
             order by approval.createdAt desc
            """)
    List<IncentiveRetentionApproval> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("approvalId") UUID approvalId,
            @Param("dryRunId") UUID dryRunId,
            @Param("status") String status,
            @Param("policyId") String policyId,
            @Param("changeTicket") String changeTicket,
            @Param("requestedBy") String requestedBy,
            @Param("approvedBy") String approvedBy,
            @Param("executedBy") String executedBy,
            @Param("expired") Boolean expired,
            @Param("now") Instant now,
            @Param("from") Instant from,
            @Param("to") Instant to,
            Pageable pageable);
}
