package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveIdempotencyKeyRepository extends JpaRepository<IncentiveIdempotencyKey, UUID> {
    Optional<IncentiveIdempotencyKey> findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
            String tenantId,
            String applicationId,
            String operation,
            String idempotencyKey);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select k from IncentiveIdempotencyKey k
            where k.tenantId = :tenantId
              and k.applicationId = :applicationId
              and k.operation = :operation
              and k.idempotencyKey = :idempotencyKey
            """)
    Optional<IncentiveIdempotencyKey> lockByScope(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("operation") String operation,
            @Param("idempotencyKey") String idempotencyKey);

    @Modifying
    @Query(value = """
            insert into incentive_idempotency_keys (
                id, tenant_id, application_id, operation, idempotency_key,
                request_hash, response_json, status, created_at, expires_at
            ) values (
                :id, :tenantId, :applicationId, :operation, :idempotencyKey,
                :requestHash, '{}'::jsonb, 'IN_PROGRESS', now(), :expiresAt
            )
            on conflict (tenant_id, application_id, operation, idempotency_key) do nothing
            """, nativeQuery = true)
    int insertInProgressIfAbsent(
            @Param("id") UUID id,
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("operation") String operation,
            @Param("idempotencyKey") String idempotencyKey,
            @Param("requestHash") String requestHash,
            @Param("expiresAt") Instant expiresAt);

    @Query(value = """
            select count(*) filter (
                       where expires_at <= :cutoff
                         and status <> 'IN_PROGRESS'
                   ) as eligibleCount,
                   count(*) filter (
                       where expires_at > :cutoff
                          or status = 'IN_PROGRESS'
                   ) as blockedCount,
                   min(expires_at) filter (
                       where expires_at <= :cutoff
                         and status <> 'IN_PROGRESS'
                   ) as oldestCandidateAt,
                   max(expires_at) filter (
                       where expires_at <= :cutoff
                         and status <> 'IN_PROGRESS'
                   ) as newestCandidateAt
            from incentive_idempotency_keys
            where (:tenantId is null or tenant_id = :tenantId)
              and (:applicationId is null or application_id = :applicationId)
            """, nativeQuery = true)
    RetentionDryRunStats dryRunExpiredKeys(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("cutoff") Instant cutoff);
}
