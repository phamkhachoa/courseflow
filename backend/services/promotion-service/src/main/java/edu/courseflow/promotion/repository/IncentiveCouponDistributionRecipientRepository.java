package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCouponDistributionRecipient;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncentiveCouponDistributionRecipientRepository
        extends JpaRepository<IncentiveCouponDistributionRecipient, UUID> {

    List<IncentiveCouponDistributionRecipient> findByDistributionIdOrderByCreatedAtAsc(UUID distributionId);
}
