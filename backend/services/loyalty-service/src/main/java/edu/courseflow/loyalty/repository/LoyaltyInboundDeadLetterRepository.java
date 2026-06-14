package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyInboundDeadLetter;
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

public interface LoyaltyInboundDeadLetterRepository extends JpaRepository<LoyaltyInboundDeadLetter, UUID> {

    Optional<LoyaltyInboundDeadLetter> findByDltTopicAndKafkaPartitionAndKafkaOffset(
            String dltTopic,
            int kafkaPartition,
            long kafkaOffset);

    long countByStatus(String status);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select dlt
            from LoyaltyInboundDeadLetter dlt
            where dlt.id = :id
            """)
    Optional<LoyaltyInboundDeadLetter> findByIdForUpdate(@Param("id") UUID id);

    @Query("""
            select dlt
            from LoyaltyInboundDeadLetter dlt
            where (:status is null or dlt.status = :status)
              and (:sourceTopic is null or dlt.sourceTopic = :sourceTopic)
              and (:dltTopic is null or dlt.dltTopic = :dltTopic)
              and (:payloadHash is null or dlt.payloadHash = :payloadHash)
              and dlt.createdAt >= :from
              and dlt.createdAt <= :to
            order by dlt.createdAt desc
            """)
    List<LoyaltyInboundDeadLetter> search(
            @Param("status") String status,
            @Param("sourceTopic") String sourceTopic,
            @Param("dltTopic") String dltTopic,
            @Param("payloadHash") String payloadHash,
            @Param("from") Instant from,
            @Param("to") Instant to,
            Pageable pageable);
}
