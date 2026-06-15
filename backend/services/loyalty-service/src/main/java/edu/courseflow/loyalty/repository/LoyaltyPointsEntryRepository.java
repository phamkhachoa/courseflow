package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyPointsEntry;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyPointsEntryRepository extends JpaRepository<LoyaltyPointsEntry, UUID> {
    interface FinanceTotalsProjection {
        Long getEarnedPoints();
        Long getBurnedPoints();
        Long getReversedPoints();
        Long getAdjustedPoints();
        Long getExpiredPoints();
        Long getNetPoints();
        Long getEntryCount();
    }

    Optional<LoyaltyPointsEntry> findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
            UUID programUuid, String entryType, String sourceReference);

    Optional<LoyaltyPointsEntry> findFirstByTenantIdAndApplicationIdAndProgramIdAndEntryTypeAndSourceReference(
            String tenantId,
            String applicationId,
            String programId,
            String entryType,
            String sourceReference);

    Optional<LoyaltyPointsEntry> findFirstByReversalOfEntryId(UUID reversalOfEntryId);

    List<LoyaltyPointsEntry> findTop100ByAccountIdOrderByCreatedAtDesc(UUID accountId);

    List<LoyaltyPointsEntry> findByAccountIdOrderByOccurredAtAscCreatedAtAsc(UUID accountId);

    @Query("""
            select e from LoyaltyPointsEntry e
            where e.tenantId = :tenantId
              and e.applicationId = :applicationId
              and (:programId is null or e.programId = :programId)
              and (:correlationId is null or e.correlationId = :correlationId)
              and (:sourceReference is null or e.sourceReference = :sourceReference)
            order by e.createdAt desc, e.occurredAt desc
            """)
    List<LoyaltyPointsEntry> findEvidenceEntries(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("correlationId") String correlationId,
            @Param("sourceReference") String sourceReference,
            Pageable pageable);

    @Query("""
            select e from LoyaltyPointsEntry e
            where e.tenantId = :tenantId
              and e.applicationId = :applicationId
              and (:programId is null or e.programId = :programId)
              and (:profileId is null or e.profileId = :profileId)
              and (:accountId is null or e.accountId = :accountId)
              and (:entryType is null or e.entryType = :entryType)
              and (:fromCreatedAt is null or e.createdAt >= :fromCreatedAt)
              and (:toCreatedAt is null or e.createdAt < :toCreatedAt)
            order by e.createdAt desc, e.occurredAt desc
            """)
    List<LoyaltyPointsEntry> searchReconciliationEntries(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("profileId") String profileId,
            @Param("accountId") UUID accountId,
            @Param("entryType") String entryType,
            @Param("fromCreatedAt") Instant from,
            @Param("toCreatedAt") Instant to,
            Pageable pageable);

    @Query("""
            select
              coalesce(sum(case when e.entryType = 'EARN' then e.pointsDelta else 0 end), 0) as earnedPoints,
              coalesce(sum(case when e.entryType = 'BURN' then abs(e.pointsDelta) else 0 end), 0) as burnedPoints,
              coalesce(sum(case when e.entryType = 'REVERSE' then e.pointsDelta else 0 end), 0) as reversedPoints,
              coalesce(sum(case when e.entryType = 'ADJUST' then e.pointsDelta else 0 end), 0) as adjustedPoints,
              coalesce(sum(case when e.entryType = 'EXPIRE' then abs(e.pointsDelta) else 0 end), 0) as expiredPoints,
              coalesce(sum(e.pointsDelta), 0) as netPoints,
              count(e) as entryCount
            from LoyaltyPointsEntry e
            where e.tenantId = :tenantId
              and e.applicationId = :applicationId
              and (:programId is null or e.programId = :programId)
              and e.createdAt >= :fromCreatedAt
              and e.createdAt < :toCreatedAt
            """)
    FinanceTotalsProjection financeTotals(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("fromCreatedAt") Instant from,
            @Param("toCreatedAt") Instant to);

    @Query("""
            select e from LoyaltyPointsEntry e
            where e.programUuid = :programUuid
              and e.pointsDelta > 0
              and e.expiresAt is not null
              and e.expiresAt <= :asOf
            order by e.expiresAt asc, e.createdAt asc, e.id asc
            """)
    List<LoyaltyPointsEntry> expiryCandidates(
            @Param("programUuid") UUID programUuid,
            @Param("asOf") Instant asOf,
            Pageable pageable);

    @Query("select coalesce(sum(e.pointsDelta), 0) from LoyaltyPointsEntry e where e.accountId = :accountId")
    long balance(@Param("accountId") UUID accountId);

    @Query("""
            select coalesce(sum(e.pointsDelta), 0)
            from LoyaltyPointsEntry e
            where e.accountId = :accountId
              and e.entryType in ('EARN', 'ADJUST')
              and e.pointsDelta > 0
              and e.occurredAt >= :from
              and e.occurredAt <= :to
            """)
    long qualifyingPositivePoints(
            @Param("accountId") UUID accountId,
            @Param("from") Instant from,
            @Param("to") Instant to);
}
