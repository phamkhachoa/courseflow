package edu.courseflow.loyalty.service;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class LoyaltyRewardFulfillmentRetryJob {

    private final LoyaltyRewardService rewards;

    public LoyaltyRewardFulfillmentRetryJob(LoyaltyRewardService rewards) {
        this.rewards = rewards;
    }

    @Scheduled(fixedDelayString = "${courseflow.loyalty.reward-fulfillment.retry.fixed-delay-ms:60000}")
    void retryDueFulfillments() {
        rewards.runDueFulfillmentsForScheduler();
    }
}
