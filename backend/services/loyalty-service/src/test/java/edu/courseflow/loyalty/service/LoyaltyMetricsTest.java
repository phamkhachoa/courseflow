package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import edu.courseflow.loyalty.repository.LoyaltyInboundDeadLetterRepository;
import edu.courseflow.loyalty.repository.OutboxEventRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LoyaltyMetricsTest {

    @Mock
    private OutboxEventRepository outboxEvents;
    @Mock
    private LoyaltyInboundDeadLetterRepository inboundDeadLetters;

    @Test
    void recordsMutationCountersAndOutboxBacklogGauges() {
        when(outboxEvents.countUnpublishedLoyaltyEvents()).thenReturn(3L);
        when(outboxEvents.oldestUnpublishedLoyaltyAgeSeconds()).thenReturn(42.4);
        when(inboundDeadLetters.countByStatus("OPEN")).thenReturn(2L);
        when(inboundDeadLetters.countByStatus("FAILED")).thenReturn(1L);
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        LoyaltyMetrics metrics = new LoyaltyMetrics(registry, outboxEvents, inboundDeadLetters);

        metrics.mutation("EARN", "success", "ok", Duration.ofMillis(12));
        metrics.idempotency("EARN", "remembered");
        metrics.outboxEnqueued("loyalty.points.earned");
        metrics.refreshOutboxGauges();

        assertThat(registry.counter("loyalty.points.mutation",
                        "operation", "earn",
                        "result", "success",
                        "reason", "ok")
                .count()).isEqualTo(1);
        assertThat(registry.counter("loyalty.idempotency",
                        "operation", "earn",
                        "result", "remembered")
                .count()).isEqualTo(1);
        assertThat(registry.counter("loyalty.outbox.enqueued",
                        "event_type", "loyalty_points_earned")
                .count()).isEqualTo(1);
        assertThat(registry.get("loyalty.outbox.unpublished")
                .tag("aggregate_type", "loyalty-points-entry")
                .gauge()
                .value()).isEqualTo(3);
        assertThat(registry.get("loyalty.outbox.oldest.unpublished.age.seconds")
                .tag("aggregate_type", "loyalty-points-entry")
                .gauge()
                .value()).isEqualTo(42);
        assertThat(registry.get("loyalty.inbound_dead_letter.open").gauge().value()).isEqualTo(2);
        assertThat(registry.get("loyalty.inbound_dead_letter.unresolved").gauge().value()).isEqualTo(3);
    }
}
