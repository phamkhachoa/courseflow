package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveRetentionOperation;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveRetentionOperationRepository extends JpaRepository<IncentiveRetentionOperation, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select op from IncentiveRetentionOperation op where op.id = :id")
    Optional<IncentiveRetentionOperation> lockById(@Param("id") UUID id);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select op from IncentiveRetentionOperation op
            where op.policyId = :policyId
              and op.scopeKey = :scopeKey
              and op.idempotencyKey = :idempotencyKey
            """)
    Optional<IncentiveRetentionOperation> lockByIdempotencyKey(
            @Param("policyId") String policyId,
            @Param("scopeKey") String scopeKey,
            @Param("idempotencyKey") String idempotencyKey);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select op from IncentiveRetentionOperation op where op.approvalId = :approvalId")
    Optional<IncentiveRetentionOperation> lockByApprovalId(@Param("approvalId") UUID approvalId);

    Optional<IncentiveRetentionOperation> findByApprovalId(UUID approvalId);

    @Modifying
    @Query(value = """
            insert into incentive_retention_operations (
                id, policy_id, policy_version, target_dataset, scope_key, approval_id, tenant_id, application_id,
                dry_run_id, dry_run_result_hash, cutoff_at, expected_eligible_count,
                batch_limit, status, idempotency_key, request_hash, reason, change_ticket,
                restore_drill_ref, approved_by, executed_by, correlation_id, rows_redacted,
                response_json, created_at, started_at
            ) values (
                :id, :policyId, :policyVersion, :targetDataset, :scopeKey, :approvalId, :tenantId, :applicationId,
                :dryRunId, :dryRunResultHash, :cutoffAt, :expectedEligibleCount,
                :batchLimit, 'IN_PROGRESS', :idempotencyKey, :requestHash, :reason, :changeTicket,
                :restoreDrillRef, :approvedBy, :executedBy, :correlationId, 0,
                '{}'::jsonb, now(), now()
            )
            on conflict (policy_id, scope_key, idempotency_key) do nothing
            """, nativeQuery = true)
    int insertInProgressIfAbsent(
            @Param("id") UUID id,
            @Param("policyId") String policyId,
            @Param("policyVersion") String policyVersion,
            @Param("targetDataset") String targetDataset,
            @Param("scopeKey") String scopeKey,
            @Param("approvalId") UUID approvalId,
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("dryRunId") UUID dryRunId,
            @Param("dryRunResultHash") String dryRunResultHash,
            @Param("cutoffAt") Instant cutoffAt,
            @Param("expectedEligibleCount") long expectedEligibleCount,
            @Param("batchLimit") int batchLimit,
            @Param("idempotencyKey") String idempotencyKey,
            @Param("requestHash") String requestHash,
            @Param("reason") String reason,
            @Param("changeTicket") String changeTicket,
            @Param("restoreDrillRef") String restoreDrillRef,
            @Param("approvedBy") String approvedBy,
            @Param("executedBy") String executedBy,
            @Param("correlationId") String correlationId);

    long countByStatusAndStartedAtBefore(String status, Instant startedAt);
}
