package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveAuditEvent;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveAuditEventRepository extends JpaRepository<IncentiveAuditEvent, UUID> {

    @Query("""
            select a from IncentiveAuditEvent a
            where (:tenantId is null or a.tenantId = :tenantId)
              and (:applicationId is null or a.applicationId = :applicationId)
              and (:aggregateType is null or a.aggregateType = :aggregateType)
              and (:aggregateId is null or a.aggregateId = :aggregateId)
              and (:action is null or a.action = :action)
              and (:actorId is null or a.actorId = :actorId)
              and (:correlationId is null or a.correlationId = :correlationId)
              and (:sourceClientId is null or a.sourceClientId = :sourceClientId)
              and a.createdAt >= :from
              and a.createdAt <= :to
            order by a.createdAt desc, a.id desc
            """)
    List<IncentiveAuditEvent> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("aggregateType") String aggregateType,
            @Param("aggregateId") String aggregateId,
            @Param("action") String action,
            @Param("actorId") String actorId,
            @Param("correlationId") String correlationId,
            @Param("sourceClientId") String sourceClientId,
            @Param("from") Instant from,
            @Param("to") Instant to,
            Pageable pageable);

    @Query("""
            select a from IncentiveAuditEvent a
            where a.tenantId = :tenantId
              and a.applicationId = :applicationId
              and a.aggregateId in :aggregateIds
            order by a.createdAt asc, a.id asc
            """)
    List<IncentiveAuditEvent> timeline(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("aggregateIds") List<String> aggregateIds,
            Pageable pageable);

    @Query("""
            select a from IncentiveAuditEvent a
            where ((:tenantId is null and a.tenantId is null) or a.tenantId = :tenantId)
              and ((:applicationId is null and a.applicationId is null) or a.applicationId = :applicationId)
              and a.aggregateId in :aggregateIds
            order by a.createdAt asc, a.id asc
            """)
    List<IncentiveAuditEvent> timelineByAggregateIds(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("aggregateIds") List<String> aggregateIds,
            Pageable pageable);
}
