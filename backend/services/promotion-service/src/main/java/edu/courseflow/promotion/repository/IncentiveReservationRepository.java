package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveReservation;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveReservationRepository extends JpaRepository<IncentiveReservation, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from IncentiveReservation r where r.id = :id")
    Optional<IncentiveReservation> lockById(@Param("id") UUID id);

    @Query("""
            select r from IncentiveReservation r
            where (:tenantId is null or r.tenantId = :tenantId)
              and (:applicationId is null or r.applicationId = :applicationId)
              and (:profileId is null or r.profileId = :profileId)
              and (:externalReference is null or r.externalReference = :externalReference)
              and (:campaignId is null or r.campaignId = :campaignId)
              and (:couponId is null or r.couponId = :couponId)
              and (:status is null or r.status = :status)
              and (:expiredOnly = false or (r.status = 'RESERVED' and r.expiresAt <= :now))
            order by r.reservedAt desc, r.id desc
            """)
    List<IncentiveReservation> listFiltered(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("profileId") String profileId,
            @Param("externalReference") String externalReference,
            @Param("campaignId") UUID campaignId,
            @Param("couponId") UUID couponId,
            @Param("status") String status,
            @Param("expiredOnly") boolean expiredOnly,
            @Param("now") Instant now,
            Pageable pageable);

    @Query(value = """
            select *
            from incentive_reservations
            where status = 'RESERVED'
              and expires_at <= :now
            order by expires_at asc, id asc
            for update skip locked
            limit :limit
            """, nativeQuery = true)
    List<IncentiveReservation> lockExpiredReservedForExpiry(
            @Param("now") Instant now,
            @Param("limit") int limit);

    @Query(value = """
            select count(*)
            from incentive_reservations
            where status = 'RESERVED'
              and expires_at <= now()
            """, nativeQuery = true)
    long countExpiredReservedBacklog();

    @Query(value = """
            select coalesce(extract(epoch from (now() - min(expires_at))), 0)
            from incentive_reservations
            where status = 'RESERVED'
              and expires_at <= now()
            """, nativeQuery = true)
    double oldestExpiredReservedAgeSeconds();

    long countByTenantIdAndApplicationIdAndProfileIdAndReservedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            String profileId,
            Instant since);

    long countByTenantIdAndApplicationIdAndProfileIdAndStatusAndReservedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            String profileId,
            String status,
            Instant since);

    long countByTenantIdAndApplicationIdAndCouponIdInAndReservedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            List<UUID> couponIds,
            Instant since);

    long countByTenantIdAndApplicationIdAndExternalReferenceAndReservedAtGreaterThanEqual(
            String tenantId,
            String applicationId,
            String externalReference,
            Instant since);

    @Query(value = """
            select count(*) filter (
                       where status in ('EXPIRED', 'CANCELLED')
                         and coalesce(cancelled_at, expires_at) <= :cutoff
                         and request_json <> '{}'::jsonb
                         and coalesce(request_json ->> 'requestSnapshotMinimized', 'false') <> 'true'
                         and coalesce(request_json ->> 'retentionRedacted', 'false') <> 'true'
                   ) as eligibleCount,
                   count(*) filter (
                       where status in ('RESERVED', 'REDEEMED')
                          or status not in ('EXPIRED', 'CANCELLED')
                          or coalesce(cancelled_at, expires_at) > :cutoff
                          or request_json = '{}'::jsonb
                          or coalesce(request_json ->> 'requestSnapshotMinimized', 'false') = 'true'
                          or coalesce(request_json ->> 'retentionRedacted', 'false') = 'true'
                   ) as blockedCount,
                   min(coalesce(cancelled_at, expires_at)) filter (
                       where status in ('EXPIRED', 'CANCELLED')
                         and coalesce(cancelled_at, expires_at) <= :cutoff
                         and request_json <> '{}'::jsonb
                         and coalesce(request_json ->> 'requestSnapshotMinimized', 'false') <> 'true'
                         and coalesce(request_json ->> 'retentionRedacted', 'false') <> 'true'
                   ) as oldestCandidateAt,
                   max(coalesce(cancelled_at, expires_at)) filter (
                       where status in ('EXPIRED', 'CANCELLED')
                         and coalesce(cancelled_at, expires_at) <= :cutoff
                         and request_json <> '{}'::jsonb
                         and coalesce(request_json ->> 'requestSnapshotMinimized', 'false') <> 'true'
                         and coalesce(request_json ->> 'retentionRedacted', 'false') <> 'true'
                   ) as newestCandidateAt
            from incentive_reservations
            where (:tenantId is null or tenant_id = :tenantId)
              and (:applicationId is null or application_id = :applicationId)
            """, nativeQuery = true)
    RetentionDryRunStats dryRunTerminalRequestSnapshots(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("cutoff") Instant cutoff);

    @Modifying
    @Query(value = """
            with candidates as (
                select id
                from incentive_reservations
                where (:tenantId is null or tenant_id = :tenantId)
                  and (:applicationId is null or application_id = :applicationId)
                  and status in ('EXPIRED', 'CANCELLED')
                  and coalesce(cancelled_at, expires_at) <= :cutoff
                  and request_json <> '{}'::jsonb
                  and coalesce(request_json ->> 'requestSnapshotMinimized', 'false') <> 'true'
                  and coalesce(request_json ->> 'retentionRedacted', 'false') <> 'true'
                order by coalesce(cancelled_at, expires_at) asc, id asc
                for update skip locked
                limit :limit
            )
            update incentive_reservations reservation
            set request_json = cast(:redactedSnapshot as jsonb)
            from candidates
            where reservation.id = candidates.id
            """, nativeQuery = true)
    int redactTerminalRequestSnapshots(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("cutoff") Instant cutoff,
            @Param("limit") int limit,
            @Param("redactedSnapshot") String redactedSnapshot);
}
