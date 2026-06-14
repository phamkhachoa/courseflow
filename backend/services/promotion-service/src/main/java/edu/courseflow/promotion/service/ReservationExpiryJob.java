package edu.courseflow.promotion.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
        name = "courseflow.promotion.reservation-expiry.enabled",
        havingValue = "true",
        matchIfMissing = true)
public class ReservationExpiryJob {

    private static final Logger log = LoggerFactory.getLogger(ReservationExpiryJob.class);

    private final PromotionService promotions;
    private final int batchSize;

    public ReservationExpiryJob(PromotionService promotions,
                                @Value("${courseflow.promotion.reservation-expiry.batch-size:100}") int batchSize) {
        this.promotions = promotions;
        this.batchSize = batchSize;
    }

    @Scheduled(fixedDelayString = "${courseflow.promotion.reservation-expiry.fixed-delay-ms:60000}")
    public void expireReservations() {
        int expired = promotions.expireReservedReservations(batchSize);
        if (expired > 0) {
            log.info("Expired {} incentive reservation(s)", expired);
        }
    }
}
