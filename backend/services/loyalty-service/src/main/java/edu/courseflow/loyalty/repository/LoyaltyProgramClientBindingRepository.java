package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyProgramClientBinding;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LoyaltyProgramClientBindingRepository extends JpaRepository<LoyaltyProgramClientBinding, UUID> {
    List<LoyaltyProgramClientBinding> findByTenantIdAndApplicationIdAndProgramId(
            String tenantId, String applicationId, String programId);

    Optional<LoyaltyProgramClientBinding> findByTenantIdAndApplicationIdAndProgramIdAndClientId(
            String tenantId, String applicationId, String programId, String clientId);
}
