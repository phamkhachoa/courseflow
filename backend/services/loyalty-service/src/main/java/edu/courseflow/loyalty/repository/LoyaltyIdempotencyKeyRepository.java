package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyIdempotencyKey;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LoyaltyIdempotencyKeyRepository extends JpaRepository<LoyaltyIdempotencyKey, UUID> {
    Optional<LoyaltyIdempotencyKey> findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
            String tenantId, String applicationId, String operation, String idempotencyKey);
}
