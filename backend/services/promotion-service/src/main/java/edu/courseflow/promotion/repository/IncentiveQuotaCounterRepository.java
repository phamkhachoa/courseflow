package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveQuotaCounter;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveQuotaCounterRepository extends JpaRepository<IncentiveQuotaCounter, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select q from IncentiveQuotaCounter q
            where q.tenantId = :tenantId
              and q.applicationId = :applicationId
              and q.scopeType = :scopeType
              and q.scopeId = :scopeId
              and q.profileId = :profileId
            """)
    Optional<IncentiveQuotaCounter> lockByScope(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("scopeType") String scopeType,
            @Param("scopeId") String scopeId,
            @Param("profileId") String profileId);

    Optional<IncentiveQuotaCounter> findByTenantIdAndApplicationIdAndScopeTypeAndScopeIdAndProfileId(
            String tenantId,
            String applicationId,
            String scopeType,
            String scopeId,
            String profileId);

    @Modifying
    @Query(value = """
            insert into incentive_quota_counters (
                id, tenant_id, application_id, scope_type, scope_id, profile_id,
                limit_count, used_count, created_at, updated_at, version
            ) values (
                :id, :tenantId, :applicationId, :scopeType, :scopeId, :profileId,
                :limitCount, 0, now(), now(), 0
            )
            on conflict (tenant_id, application_id, scope_type, scope_id, profile_id) do nothing
            """, nativeQuery = true)
    int insertIfAbsent(
            @Param("id") UUID id,
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("scopeType") String scopeType,
            @Param("scopeId") String scopeId,
            @Param("profileId") String profileId,
            @Param("limitCount") int limitCount);

    @Modifying
    @Query(value = """
            update incentive_quota_counters
            set used_count = used_count + 1,
                limit_count = :limitCount,
                updated_at = now(),
                version = version + 1
            where tenant_id = :tenantId
              and application_id = :applicationId
              and scope_type = :scopeType
              and scope_id = :scopeId
              and profile_id = :profileId
              and :limitCount > 0
              and used_count < :limitCount
            """, nativeQuery = true)
    int tryConsumeIfAvailable(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("scopeType") String scopeType,
            @Param("scopeId") String scopeId,
            @Param("profileId") String profileId,
            @Param("limitCount") int limitCount);
}
