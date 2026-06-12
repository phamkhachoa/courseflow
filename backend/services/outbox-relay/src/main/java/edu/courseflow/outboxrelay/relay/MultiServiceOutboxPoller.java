package edu.courseflow.outboxrelay.relay;

import com.zaxxer.hikari.HikariDataSource;
import edu.courseflow.outboxrelay.config.OutboxRelayProperties;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Polls each configured service's {@code outbox_events} table and relays unpublished rows to Kafka.
 *
 * <p>Design notes:
 * <ul>
 *   <li>One JdbcClient is created per service at startup from the configured JDBC URL.</li>
 *   <li>Rows are published at-least-once: {@code published_at} is set only after the broker acks,
 *       so a crash between send and mark causes a replay — consumers must dedup on {@code eventId}.</li>
 *   <li>After each batch, {@code relay_checkpoints} (in the relay's own DB) is updated with the
 *       last event UUID for observability.</li>
 *   <li><b>Poison-row handling:</b> a single row that repeatedly fails to publish used to abort the
 *       whole batch forever, freezing the entire stream behind it. We now keep an in-memory attempt
 *       counter per {@code (service, rowId)}. While a row is under budget we stop the batch and retry
 *       on the next poll (preserving ordering). Once a row exhausts {@code maxAttempts} we copy it to
 *       {@code relay_dead_letters} (in the relay's OWN DB — the relay must not migrate other services'
 *       tables) and mark its source row {@code published_at = NOW()} so the stream advances.</li>
 * </ul>
 *
 * <p>Trade-off: the attempt counter is in-memory, so a relay restart resets budgets and a poison row
 * may be retried a few more times before being dead-lettered again — acceptable since dead-lettering
 * is idempotent (UNIQUE on service+event id) and the alternative (migrating per-service schemas to add
 * an {@code attempts} column) violates table ownership. Dead-lettering a row also weakens strict
 * ordering for that one aggregate, but only after the broker has rejected it {@code maxAttempts} times,
 * which is preferable to blocking every other aggregate indefinitely.
 */
@Component
public class MultiServiceOutboxPoller {

    private static final Logger log = LoggerFactory.getLogger(MultiServiceOutboxPoller.class);

    private record OutboxRow(UUID id, String aggregateId, String eventType, String payload) {}
    private record ServiceRelay(String name, JdbcClient client, TransactionTemplate tx) {}

    private final List<ServiceRelay> relays;
    private final JdbcClient checkpointClient;
    private final KafkaTemplate<String, String> kafka;
    private final int maxAttempts;
    private final int retentionDays;

    /** In-memory failure budget keyed by "service:rowId". Reset on success or after dead-lettering. */
    private final ConcurrentHashMap<String, Integer> attempts = new ConcurrentHashMap<>();

    public MultiServiceOutboxPoller(OutboxRelayProperties props,
                                    JdbcClient checkpointClient,
                                    KafkaTemplate<String, String> kafka,
                                    @Value("${courseflow.outbox.max-attempts:5}") int maxAttempts,
                                    @Value("${courseflow.outbox.retention-days:7}") int retentionDays) {
        this.checkpointClient = checkpointClient;
        this.kafka = kafka;
        this.maxAttempts = maxAttempts;
        this.retentionDays = retentionDays;
        this.relays = props.getServices().stream().map(svc -> {
            HikariDataSource ds = DataSourceBuilder.create()
                    .type(HikariDataSource.class)
                    .url(svc.getJdbcUrl())
                    .username(svc.getUsername())
                    .password(svc.getPassword())
                    .build();
            ds.setPoolName("relay-" + svc.getName());
            ds.setMaximumPoolSize(2);
            log.info("Outbox relay configured for service '{}'", svc.getName());
            return new ServiceRelay(
                    svc.getName(),
                    JdbcClient.create(ds),
                    new TransactionTemplate(new DataSourceTransactionManager(ds)));
        }).toList();
    }

    @Scheduled(fixedDelayString = "${courseflow.outbox.poll-interval-ms:1000}")
    public void poll() {
        for (ServiceRelay relay : relays) {
            pollService(relay);
        }
    }

    private void pollService(ServiceRelay relay) {
        relay.tx().executeWithoutResult(status -> pollServiceLocked(relay));
    }

    private void pollServiceLocked(ServiceRelay relay) {
        List<OutboxRow> rows;
        try {
            rows = relay.client().sql("""
                            SELECT id, aggregate_id, event_type, payload::text AS payload
                            FROM outbox_events
                            WHERE published_at IS NULL
                            ORDER BY created_at, id
                            LIMIT 100
                            FOR UPDATE SKIP LOCKED
                            """)
                    .query((rs, rowNum) -> new OutboxRow(
                            rs.getObject("id", UUID.class),
                            rs.getString("aggregate_id"),
                            rs.getString("event_type"),
                            rs.getString("payload")))
                    .list();
        } catch (Exception ex) {
            log.warn("outbox-relay: failed to query outbox_events for service '{}', will retry", relay.name(), ex);
            return;
        }

        for (OutboxRow row : rows) {
            String key = relay.name() + ":" + row.id();
            try {
                kafka.send(row.eventType(), row.aggregateId(), row.payload()).join();
            } catch (Exception ex) {
                int failures = attempts.merge(key, 1, Integer::sum);
                if (failures < maxAttempts) {
                    log.warn("outbox-relay: failed to publish event {} → topic '{}' for service '{}' "
                                    + "(attempt {}/{}), stopping batch and will retry",
                            row.id(), row.eventType(), relay.name(), failures, maxAttempts, ex);
                    // Stop the batch to preserve ordering; the row is retried on the next poll.
                    return;
                }
                // Budget exhausted: dead-letter the row and advance past it so the stream is not frozen.
                log.error("outbox-relay: event {} → topic '{}' for service '{}' failed {} times; "
                                + "dead-lettering and skipping to unblock the stream",
                        row.id(), row.eventType(), relay.name(), failures, ex);
                if (!deadLetter(relay, row, failures, ex)) {
                    return;
                }
                markPublished(relay, row.id());
                attempts.remove(key);
                continue;
            }
            attempts.remove(key);
            markPublished(relay, row.id());
            updateCheckpoint(relay.name(), row.id());
        }

        if (!rows.isEmpty()) {
            log.debug("outbox-relay: relayed {} event(s) for service '{}'", rows.size(), relay.name());
        }
    }

    @Scheduled(fixedDelayString = "${courseflow.outbox.purge-interval-ms:3600000}")
    public void purgePublished() {
        if (retentionDays <= 0) {
            return;
        }
        for (ServiceRelay relay : relays) {
            try {
                int deleted = relay.client().sql("""
                                DELETE FROM outbox_events
                                WHERE published_at IS NOT NULL
                                  AND published_at < NOW() - (:retentionDays * INTERVAL '1 day')
                                """)
                        .param("retentionDays", retentionDays)
                        .update();
                if (deleted > 0) {
                    log.info("outbox-relay: purged {} published outbox row(s) for service '{}'",
                            deleted, relay.name());
                }
            } catch (Exception ex) {
                log.warn("outbox-relay: failed to purge published rows for service '{}'", relay.name(), ex);
            }
        }
    }

    private void markPublished(ServiceRelay relay, UUID rowId) {
        relay.client()
                .sql("UPDATE outbox_events SET published_at = NOW() WHERE id = :id")
                .param("id", rowId)
                .update();
    }

    /** Persist a poison row to the relay's own dead-letter table for later inspection/replay. */
    private boolean deadLetter(ServiceRelay relay, OutboxRow row, int attemptCount, Exception ex) {
        try {
            checkpointClient.sql("""
                            INSERT INTO relay_dead_letters
                                (service_name, source_event_id, event_type, aggregate_id, payload, attempts, last_error)
                            VALUES (:service, :eventId, :eventType, :aggregateId, :payload, :attempts, :lastError)
                            ON CONFLICT (service_name, source_event_id) DO UPDATE
                              SET attempts = EXCLUDED.attempts, last_error = EXCLUDED.last_error
                            """)
                    .param("service", relay.name())
                    .param("eventId", row.id())
                    .param("eventType", row.eventType())
                    .param("aggregateId", row.aggregateId())
                    .param("payload", row.payload())
                    .param("attempts", attemptCount)
                    .param("lastError", ex.getMessage())
                    .update();
            return true;
        } catch (Exception dlEx) {
            log.error("outbox-relay: FAILED to dead-letter event {} for service '{}'; leaving it unpublished",
                    row.id(), relay.name(), dlEx);
            return false;
        }
    }

    private void updateCheckpoint(String serviceName, UUID lastEventId) {
        checkpointClient.sql("""
                        INSERT INTO relay_checkpoints (service_name, last_event_id, updated_at)
                        VALUES (:service, :eventId, NOW())
                        ON CONFLICT (service_name) DO UPDATE
                          SET last_event_id = :eventId, updated_at = NOW()
                        """)
                .param("service", serviceName)
                .param("eventId", lastEventId)
                .update();
    }
}
