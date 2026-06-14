package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.OutboxEvent;
import java.time.Instant;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OutboxEventRepository extends JpaRepository<OutboxEvent, UUID> {
    @Query(value = """
            select count(*)
            from outbox_events
            where published_at is null
              and aggregate_type in ('loyalty-points-entry', 'loyalty-reward-redemption')
            """, nativeQuery = true)
    long countUnpublishedLoyaltyEvents();

    @Query(value = """
            select coalesce(extract(epoch from (now() - min(created_at))), 0)
            from outbox_events
            where published_at is null
              and aggregate_type in ('loyalty-points-entry', 'loyalty-reward-redemption')
            """, nativeQuery = true)
    double oldestUnpublishedLoyaltyAgeSeconds();

    @Query(value = """
            select count(*)
            from outbox_events
            where aggregate_type = 'loyalty-points-entry'
              and aggregate_id = :aggregateId
            """, nativeQuery = true)
    long countLoyaltyPointEvents(@Param("aggregateId") String aggregateId);

    @Query(value = """
            select count(*)
            from outbox_events
            where aggregate_type = 'loyalty-points-entry'
              and aggregate_id = :aggregateId
              and published_at is not null
            """, nativeQuery = true)
    long countPublishedLoyaltyPointEvents(@Param("aggregateId") String aggregateId);

    @Query(value = """
            select count(*)
            from loyalty_points_entries e
            join outbox_events o
              on o.aggregate_type = 'loyalty-points-entry'
             and o.aggregate_id = cast(e.id as text)
            where e.tenant_id = :tenantId
              and e.application_id = :applicationId
              and (:programId is null or e.program_id = :programId)
              and e.created_at >= :fromCreatedAt
              and e.created_at < :toCreatedAt
              and o.published_at is null
            """, nativeQuery = true)
    long countPendingLoyaltyPointEntries(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("fromCreatedAt") Instant from,
            @Param("toCreatedAt") Instant to);

    @Query(value = """
            select count(*)
            from loyalty_points_entries e
            left join outbox_events o
              on o.aggregate_type = 'loyalty-points-entry'
             and o.aggregate_id = cast(e.id as text)
            where e.tenant_id = :tenantId
              and e.application_id = :applicationId
              and (:programId is null or e.program_id = :programId)
              and e.created_at >= :fromCreatedAt
              and e.created_at < :toCreatedAt
              and o.id is null
            """, nativeQuery = true)
    long countMissingLoyaltyPointEntries(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("programId") String programId,
            @Param("fromCreatedAt") Instant from,
            @Param("toCreatedAt") Instant to);
}
