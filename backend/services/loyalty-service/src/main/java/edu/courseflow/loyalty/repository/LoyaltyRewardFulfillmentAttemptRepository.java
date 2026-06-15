package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyRewardFulfillmentAttempt;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LoyaltyRewardFulfillmentAttemptRepository
        extends JpaRepository<LoyaltyRewardFulfillmentAttempt, UUID> {

    List<LoyaltyRewardFulfillmentAttempt> findByRedemptionIdOrderByAttemptNumberDesc(UUID redemptionId);
}
