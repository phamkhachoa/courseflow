package edu.courseflow.loyalty.service;

import edu.courseflow.loyalty.repository.LoyaltyInboundDeadLetterRepository;
import edu.courseflow.loyalty.repository.OutboxEventRepository;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;
import java.time.Duration;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class LoyaltyMetrics {

    private final MeterRegistry registry;
    private final OutboxEventRepository outboxEvents;
    private final LoyaltyInboundDeadLetterRepository inboundDeadLetters;
    private final AtomicLong unpublishedOutboxCount = new AtomicLong();
    private final AtomicLong oldestUnpublishedOutboxAgeSeconds = new AtomicLong();
    private final AtomicLong openInboundDeadLetterCount = new AtomicLong();
    private final AtomicLong unresolvedInboundDeadLetterCount = new AtomicLong();

    public LoyaltyMetrics(
            MeterRegistry registry,
            OutboxEventRepository outboxEvents,
            LoyaltyInboundDeadLetterRepository inboundDeadLetters) {
        this.registry = registry;
        this.outboxEvents = outboxEvents;
        this.inboundDeadLetters = inboundDeadLetters;
        registerOutboxGauges();
        registerInboundDeadLetterGauges();
        refreshOutboxGauges();
    }

    public void mutation(String operation, String result, String reason, Duration duration) {
        Tags tags = Tags.of(
                "operation", safe(operation),
                "result", safe(result),
                "reason", safe(reason));
        registry.counter("loyalty.points.mutation", tags).increment();
        registry.timer("loyalty.points.mutation.duration", tags).record(duration);
    }

    public void idempotency(String operation, String result) {
        registry.counter("loyalty.idempotency",
                Tags.of("operation", safe(operation), "result", safe(result))).increment();
    }

    public void sourceReference(String operation, String result) {
        registry.counter("loyalty.source_reference",
                Tags.of("operation", safe(operation), "result", safe(result))).increment();
    }

    public void outboxEnqueued(String eventType) {
        registry.counter("loyalty.outbox.enqueued",
                Tags.of("event_type", safe(eventType))).increment();
    }

    public void inboundDeadLetter(String action, String result, String topic) {
        registry.counter("loyalty.inbound_dead_letter",
                Tags.of("action", safe(action), "result", safe(result), "topic", safe(topic))).increment();
    }

    public void inboundEvent(String sourceEventType, String result) {
        registry.counter("loyalty.inbound_event",
                Tags.of("source_event_type", safe(sourceEventType), "result", safe(result))).increment();
    }

    private void registerOutboxGauges() {
        Gauge.builder("loyalty.outbox.unpublished", unpublishedOutboxCount, AtomicLong::get)
                .tag("aggregate_type", "loyalty-points-entry")
                .description("Unpublished loyalty outbox events awaiting relay")
                .register(registry);
        Gauge.builder("loyalty.outbox.oldest.unpublished.age.seconds",
                        oldestUnpublishedOutboxAgeSeconds, AtomicLong::get)
                .tag("aggregate_type", "loyalty-points-entry")
                .description("Age in seconds of the oldest unpublished loyalty outbox event")
                .register(registry);
    }

    private void registerInboundDeadLetterGauges() {
        Gauge.builder("loyalty.inbound_dead_letter.open", openInboundDeadLetterCount, AtomicLong::get)
                .description("Open loyalty inbound Kafka dead-letter records awaiting operator action")
                .register(registry);
        Gauge.builder("loyalty.inbound_dead_letter.unresolved", unresolvedInboundDeadLetterCount, AtomicLong::get)
                .description("Open or failed loyalty inbound Kafka dead-letter records awaiting operator action")
                .register(registry);
    }

    @Scheduled(fixedDelayString = "${courseflow.loyalty.metrics.outbox-refresh-ms:30000}")
    public void refreshOutboxGauges() {
        try {
            unpublishedOutboxCount.set(outboxEvents.countUnpublishedLoyaltyEvents());
            oldestUnpublishedOutboxAgeSeconds.set(Math.max(
                    0L,
                    Math.round(outboxEvents.oldestUnpublishedLoyaltyAgeSeconds())));
            long openDeadLetters = inboundDeadLetters.countByStatus("OPEN");
            long failedDeadLetters = inboundDeadLetters.countByStatus("FAILED");
            openInboundDeadLetterCount.set(openDeadLetters);
            unresolvedInboundDeadLetterCount.set(openDeadLetters + failedDeadLetters);
            registry.counter("loyalty.metrics.refresh", Tags.of("result", "success")).increment();
        } catch (RuntimeException ex) {
            registry.counter("loyalty.metrics.refresh", Tags.of("result", "error")).increment();
        }
    }

    private String safe(String value) {
        if (value == null || value.isBlank()) {
            return "unknown";
        }
        return value.trim().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_\\-]", "_");
    }
}
