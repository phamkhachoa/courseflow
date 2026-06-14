package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.OutboxEvent;
import java.time.Instant;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OutboxEventRepository extends JpaRepository<OutboxEvent, UUID> {
    long countByAggregateIdAndEventType(String aggregateId, String eventType);

    @Query(value = """
            select count(*)
            from outbox_events
            where aggregate_type = 'incentive-redemption'
              and published_at is null
            """, nativeQuery = true)
    long countUnpublishedIncentiveEvents();

    @Query(value = """
            select coalesce(extract(epoch from (now() - min(created_at))), 0)
            from outbox_events
            where aggregate_type = 'incentive-redemption'
              and published_at is null
            """, nativeQuery = true)
    double oldestUnpublishedIncentiveAgeSeconds();

    @Query(value = """
            select count(*) filter (
                       where published_at is not null
                         and published_at <= :cutoff
                   ) as eligibleCount,
                   count(*) filter (
                       where published_at is null
                          or published_at > :cutoff
                   ) as blockedCount,
                   min(published_at) filter (
                       where published_at is not null
                         and published_at <= :cutoff
                   ) as oldestCandidateAt,
                   max(published_at) filter (
                       where published_at is not null
                         and published_at <= :cutoff
                   ) as newestCandidateAt
            from outbox_events
            where aggregate_type like 'incentive-%'
            """, nativeQuery = true)
    RetentionDryRunStats dryRunPublishedEvents(@Param("cutoff") Instant cutoff);
}
