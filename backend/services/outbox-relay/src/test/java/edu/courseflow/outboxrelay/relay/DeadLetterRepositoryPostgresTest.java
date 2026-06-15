package edu.courseflow.outboxrelay.relay;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.UUID;
import javax.sql.DataSource;
import liquibase.integration.spring.SpringLiquibase;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@Testcontainers(disabledWithoutDocker = true)
class DeadLetterRepositoryPostgresTest {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("cf_outbox")
            .withUsername("courseflow")
            .withPassword("courseflow");

    static DataSource dataSource;

    DeadLetterRepository repository;
    JdbcClient jdbc;

    @BeforeAll
    static void migrate() throws Exception {
        DriverManagerDataSource ds = new DriverManagerDataSource(
                postgres.getJdbcUrl(),
                postgres.getUsername(),
                postgres.getPassword());
        SpringLiquibase liquibase = new SpringLiquibase();
        liquibase.setDataSource(ds);
        liquibase.setChangeLog("classpath:db/changelog/db.changelog.xml");
        liquibase.afterPropertiesSet();
        dataSource = ds;
    }

    @BeforeEach
    void setUp() {
        jdbc = JdbcClient.create(dataSource);
        repository = new DeadLetterRepository(jdbc);
        jdbc.sql("""
                        TRUNCATE relay_operator_actions,
                                 relay_dead_letter_approvals,
                                 relay_delivery_states,
                                 relay_dead_letters,
                                 relay_checkpoints
                        """)
                .update();
    }

    @Test
    void replayStateTransitionsAreGuardedByStatusAndWorkerLease() {
        UUID sourceEventId = UUID.randomUUID();
        repository.recordDeadLetter(
                "promotion",
                sourceEventId,
                "incentive.redemption.committed",
                "reservation-1",
                "{\"coupon\":\"secret\"}",
                5,
                "SerializationException",
                "serialization failed",
                "sha256:payload");

        DeadLetterRecord open = repository.search("OPEN", "promotion", null, null, "payload", 10).getFirst();
        assertThat(open.topic()).isEqualTo("incentive.redemption.committed");
        assertThat(open.errorClass()).isEqualTo("SerializationException");

        DeadLetterRecord claimed = repository.claimForReplay(open.id(), "worker-a", 300).orElseThrow();
        assertThat(claimed.status()).isEqualTo("REPLAYING");

        assertThat(repository.discard(open.id(), "admin-1", "do not race active replay")).isFalse();
        assertThat(repository.markReplayed(open.id(), "admin-1", "wrong worker", "worker-b")).isFalse();

        assertThat(repository.markReplayed(open.id(), "admin-1", "broker fixed", "worker-a")).isTrue();
        DeadLetterRecord replayed = repository.findById(open.id()).orElseThrow();
        assertThat(replayed.status()).isEqualTo("REPLAYED");
        assertThat(replayed.lockedBy()).isNull();
        assertThat(replayed.replayedAt()).isNotNull();
        assertThat(replayed.resolvedBy()).isEqualTo("admin-1");
    }

    @Test
    void deliveryFailureBudgetAndOperatorActionAreDurable() {
        UUID sourceEventId = UUID.randomUUID();

        assertThat(repository.recordDeliveryFailure("promotion", sourceEventId, "timeout")).isEqualTo(1);
        assertThat(repository.recordDeliveryFailure("promotion", sourceEventId, "timeout again")).isEqualTo(2);

        repository.recordDeadLetter(
                "promotion",
                sourceEventId,
                "incentive.redemption.committed",
                "reservation-1",
                "{}",
                2,
                "TimeoutException",
                "poison",
                "sha256:payload");
        DeadLetterRecord deadLetter = repository.search("OPEN", "promotion", null, null, null, 10).getFirst();

        assertThat(repository.insertOperatorAction(
                "idem-1",
                "REPLAY",
                deadLetter.id(),
                "sha256:request",
                "admin-1",
                "corr-1")).isTrue();
        assertThat(repository.insertOperatorAction(
                "idem-1",
                "REPLAY",
                deadLetter.id(),
                "sha256:request",
                "admin-1",
                "corr-1")).isFalse();

        OperatorActionRecord action = repository.findOperatorAction("idem-1", "REPLAY", deadLetter.id()).orElseThrow();
        assertThat(action.status()).isEqualTo("IN_PROGRESS");
        assertThat(action.requestHash()).isEqualTo("sha256:request");

        repository.completeOperatorAction("idem-1", "REPLAY", deadLetter.id(), "COMPLETED", "{\"ok\":true}");

        OperatorActionRecord completed = repository.findOperatorAction("idem-1", "REPLAY", deadLetter.id())
                .orElseThrow();
        assertThat(completed.status()).isEqualTo("COMPLETED");
        assertThat(completed.responseJson()).contains("\"ok\":true");
    }
}
