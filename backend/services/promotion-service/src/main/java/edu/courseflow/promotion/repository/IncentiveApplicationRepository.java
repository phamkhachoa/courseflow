package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveApplication;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveApplicationRepository extends JpaRepository<IncentiveApplication, UUID> {

    Optional<IncentiveApplication> findByTenantIdAndApplicationId(String tenantId, String applicationId);

    @Query("""
            select a from IncentiveApplication a
            where (:tenantId is null or a.tenantId = :tenantId)
              and (:applicationId is null or a.applicationId = :applicationId)
              and (:status is null or a.status = :status)
            order by a.updatedAt desc, a.createdAt desc
            """)
    List<IncentiveApplication> listFiltered(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("status") String status);
}
