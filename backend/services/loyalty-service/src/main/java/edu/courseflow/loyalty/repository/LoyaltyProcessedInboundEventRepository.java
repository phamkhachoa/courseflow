package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyProcessedInboundEvent;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LoyaltyProcessedInboundEventRepository extends JpaRepository<LoyaltyProcessedInboundEvent, UUID> {
    Optional<LoyaltyProcessedInboundEvent> findBySourceEventTypeAndEventId(String sourceEventType, String eventId);
}
