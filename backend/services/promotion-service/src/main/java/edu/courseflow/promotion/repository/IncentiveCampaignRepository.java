package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCampaign;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveCampaignRepository extends JpaRepository<IncentiveCampaign, UUID> {

    @Query("""
            select c from IncentiveCampaign c
            where c.tenantId = :tenantId
              and c.applicationId = :applicationId
              and c.status = 'PUBLISHED'
              and (c.startsAt is null or c.startsAt <= :now)
              and (c.endsAt is null or c.endsAt >= :now)
            order by c.priority desc, c.createdAt asc
            """)
    List<IncentiveCampaign> findActive(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("now") Instant now);

    @Query("""
            select c from IncentiveCampaign c
            where (:tenantId is null or c.tenantId = :tenantId)
              and (:applicationId is null or c.applicationId = :applicationId)
            order by c.updatedAt desc, c.createdAt desc
            """)
    List<IncentiveCampaign> listFiltered(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId);
}
