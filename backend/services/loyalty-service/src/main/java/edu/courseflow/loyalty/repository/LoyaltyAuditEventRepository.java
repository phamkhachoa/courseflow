package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyAuditEvent;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LoyaltyAuditEventRepository extends JpaRepository<LoyaltyAuditEvent, UUID> {
    @Query("""
            select event
            from LoyaltyAuditEvent event
            where (:tenantId is null or event.tenantId = :tenantId)
              and (:applicationId is null or event.applicationId = :applicationId)
              and (:aggregateType is null or event.aggregateType = :aggregateType)
              and (:aggregateId is null or event.aggregateId = :aggregateId)
              and (:action is null or event.action = :action)
              and (:actorId is null or event.actorId = :actorId)
              and (:correlationId is null or event.correlationId = :correlationId)
              and event.createdAt >= :from
              and event.createdAt <= :to
            order by event.createdAt desc
            """)
    List<LoyaltyAuditEvent> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("aggregateType") String aggregateType,
            @Param("aggregateId") String aggregateId,
            @Param("action") String action,
            @Param("actorId") String actorId,
            @Param("correlationId") String correlationId,
            @Param("from") Instant from,
            @Param("to") Instant to,
            Pageable pageable);

    @Query("""
            select event
            from LoyaltyAuditEvent event
            where event.tenantId = :tenantId
              and event.applicationId = :applicationId
              and event.aggregateId in :aggregateIds
            order by event.createdAt desc
            """)
    List<LoyaltyAuditEvent> timeline(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("aggregateIds") List<String> aggregateIds,
            Pageable pageable);
}
