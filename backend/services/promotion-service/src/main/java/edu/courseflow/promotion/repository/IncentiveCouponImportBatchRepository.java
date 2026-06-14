package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import jakarta.persistence.LockModeType;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveCouponImportBatchRepository extends JpaRepository<IncentiveCouponImportBatch, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select batch from IncentiveCouponImportBatch batch where batch.id = :id")
    Optional<IncentiveCouponImportBatch> lockById(@Param("id") UUID id);

    @Query("""
            select batch from IncentiveCouponImportBatch batch
             where batch.tenantId = :tenantId
               and batch.applicationId = :applicationId
               and (:campaignId is null or batch.campaignId = :campaignId)
               and (:status is null or batch.status = :status)
               and (:from is null or batch.createdAt >= :from)
               and (:to is null or batch.createdAt <= :to)
             order by batch.createdAt desc
            """)
    List<IncentiveCouponImportBatch> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignId") UUID campaignId,
            @Param("status") String status,
            @Param("from") Instant from,
            @Param("to") Instant to,
            Pageable pageable);

    @Modifying
    @Query("""
            delete from IncentiveCouponImportBatch batch
             where batch.expiresAt is not null
               and batch.expiresAt < :cutoff
               and batch.committedAt is null
            """)
    int deleteExpiredUncommitted(@Param("cutoff") Instant cutoff);
}
