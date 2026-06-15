package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.MarketingFunnelEventReceipt;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MarketingFunnelEventReceiptRepository extends JpaRepository<MarketingFunnelEventReceipt, UUID> {

    Optional<MarketingFunnelEventReceipt> findBySourceEventId(UUID sourceEventId);
}
