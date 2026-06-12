package edu.courseflow.announcement.config;

import edu.courseflow.announcement.model.OutboxEvent;
import edu.courseflow.announcement.repository.OutboxEventRepository;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Polls the local {@code outbox_events} table and relays unpublished rows to Kafka. The event_type
 * column doubles as the Kafka topic ("announcement.published"). Each row is published at-least-once:
 * we only mark {@code published_at} after the broker acks, so a crash between send and mark replays
 * the event — which is why every consumer must dedup on {@code eventId}.
 *
 * <p>For training simplicity the relay lives inside the producing service and reads that service's
 * own database. In production each service relays its own outbox (or Debezium does it via CDC).
 */
@Component
public class OutboxRelay {

    private static final Logger log = LoggerFactory.getLogger(OutboxRelay.class);

    private final OutboxEventRepository outboxEvents;
    private final KafkaTemplate<String, String> kafka;

    public OutboxRelay(OutboxEventRepository outboxEvents, KafkaTemplate<String, String> kafka) {
        this.outboxEvents = outboxEvents;
        this.kafka = kafka;
    }

    @Scheduled(fixedDelayString = "${courseflow.outbox.poll-interval-ms:1000}")
    @Transactional
    public void relay() {
        List<OutboxEvent> rows = outboxEvents.findTop100ByPublishedAtIsNullOrderByCreatedAtAsc();

        for (OutboxEvent row : rows) {
            String topic = row.getEventType();
            String key = row.getAggregateId();
            String payload = row.getPayload();
            try {
                kafka.send(topic, key, payload).join();
            } catch (Exception ex) {
                // Stop this batch; the row stays unpublished and is retried on the next poll.
                log.warn("Outbox relay failed to publish event {} to topic {}, will retry", row.getId(), topic, ex);
                throw ex;
            }
            row.markPublished();
            outboxEvents.save(row);
        }
    }
}
