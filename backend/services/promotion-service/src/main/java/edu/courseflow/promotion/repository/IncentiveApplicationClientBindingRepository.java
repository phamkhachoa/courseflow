package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveApplicationClientBinding;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncentiveApplicationClientBindingRepository
        extends JpaRepository<IncentiveApplicationClientBinding, UUID> {

    List<IncentiveApplicationClientBinding> findByTenantIdAndApplicationId(String tenantId, String applicationId);

    Optional<IncentiveApplicationClientBinding> findByTenantIdAndApplicationIdAndClientId(
            String tenantId,
            String applicationId,
            String clientId);

    boolean existsByTenantIdAndApplicationId(String tenantId, String applicationId);
}
