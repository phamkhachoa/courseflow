package edu.courseflow.outboxrelay.relay;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.MultiGauge;
import io.micrometer.core.instrument.Tags;
import java.util.List;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class OutboxRelayMetrics {

    private final MeterRegistry registry;
    private final DeadLetterRepository deadLetters;
    private final MultiGauge openDeadLetters;
    private final MultiGauge oldestDeadLetterAge;

    public OutboxRelayMetrics(MeterRegistry registry, DeadLetterRepository deadLetters) {
        this.registry = registry;
        this.deadLetters = deadLetters;
        this.openDeadLetters = MultiGauge.builder("outbox.relay.dead.letters.open")
                .description("Open outbox relay dead letters by service and event type")
                .register(registry);
        this.oldestDeadLetterAge = MultiGauge.builder("outbox.relay.dead.letter.oldest.age.seconds")
                .description("Oldest open outbox relay dead-letter age by service and event type")
                .register(registry);
    }

    public void publishFailure(String serviceName, String eventType, String errorClass, boolean retryable) {
        counter("outbox.relay.publish.failures",
                "service", tag(serviceName),
                "event_type", tag(eventType),
                "error_class", tag(errorClass),
                "retryable", Boolean.toString(retryable))
                .increment();
    }

    public void deadLetterCreated(String serviceName, String eventType) {
        counter("outbox.relay.dead.letters.created",
                "service", tag(serviceName),
                "event_type", tag(eventType))
                .increment();
    }

    public void replay(String result, String serviceName, String eventType) {
        counter("outbox.relay.replay",
                "result", tag(result),
                "service", tag(serviceName),
                "event_type", tag(eventType))
                .increment();
    }

    @Scheduled(fixedDelayString = "${courseflow.outbox.metrics-refresh-ms:30000}")
    public void refreshDeadLetterGauges() {
        List<DeadLetterCount> counts = deadLetters.openCounts();
        List<MultiGauge.Row<?>> openRows = counts.stream()
                .<MultiGauge.Row<?>>map(count -> MultiGauge.Row.of(
                        Tags.of("service", tag(count.serviceName()), "event_type", tag(count.eventType())),
                        count.count()))
                .toList();
        List<MultiGauge.Row<?>> ageRows = counts.stream()
                .<MultiGauge.Row<?>>map(count -> MultiGauge.Row.of(
                        Tags.of("service", tag(count.serviceName()), "event_type", tag(count.eventType())),
                        count.oldestAgeSeconds()))
                .toList();
        openDeadLetters.register(openRows, true);
        oldestDeadLetterAge.register(ageRows, true);
    }

    private Counter counter(String name, String... tags) {
        return registry.counter(name, tags);
    }

    private String tag(String value) {
        return value == null || value.isBlank() ? "unknown" : value.trim();
    }
}
