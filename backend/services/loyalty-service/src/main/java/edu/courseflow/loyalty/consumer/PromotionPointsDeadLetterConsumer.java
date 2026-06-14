package edu.courseflow.loyalty.consumer;

import edu.courseflow.loyalty.service.LoyaltyInboundDeadLetterService;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class PromotionPointsDeadLetterConsumer {

    private static final Logger log = LoggerFactory.getLogger(PromotionPointsDeadLetterConsumer.class);

    private final LoyaltyInboundDeadLetterService deadLetters;

    public PromotionPointsDeadLetterConsumer(LoyaltyInboundDeadLetterService deadLetters) {
        this.deadLetters = deadLetters;
    }

    @KafkaListener(
            topics = {
                    "${courseflow.loyalty.promotion-points-dlt-topic:incentive.redemption.committed.DLT}",
                    "${courseflow.loyalty.promotion-points-reversal-dlt-topic:incentive.redemption.reversed.DLT}"
            },
            groupId = "${courseflow.loyalty.promotion-points-dlt-group:loyalty-service-dlt-ops}",
            containerFactory = "dltOpsKafkaListenerContainerFactory")
    public void onDeadLetter(ConsumerRecord<String, String> record) {
        deadLetters.record(record);
        log.warn(
                "loyalty: persisted inbound dead letter topic={} partition={} offset={}",
                record.topic(),
                record.partition(),
                record.offset());
    }
}
