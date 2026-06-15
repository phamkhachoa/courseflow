package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCouponDistribution;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveCouponDistributionRepository extends JpaRepository<IncentiveCouponDistribution, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select d from IncentiveCouponDistribution d where d.id = :id")
    Optional<IncentiveCouponDistribution> lockById(@Param("id") UUID id);

    @Query("""
            select d from IncentiveCouponDistribution d
            where (:tenantId is null or d.tenantId = :tenantId)
              and (:applicationId is null or d.applicationId = :applicationId)
              and (:campaignId is null or d.campaignId = :campaignId)
              and (:status is null or d.status = :status)
            order by d.createdAt desc, d.id desc
            """)
    List<IncentiveCouponDistribution> search(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignId") UUID campaignId,
            @Param("status") String status,
            Pageable pageable);
}
