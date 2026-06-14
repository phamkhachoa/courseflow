package edu.courseflow.outboxrelay.relay;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterActionRequestDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterActionResponseDto;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.core.KafkaTemplate;

class DeadLetterServiceTest {

    private final DeadLetterRepository repository = mock(DeadLetterRepository.class);
    @SuppressWarnings("unchecked")
    private final KafkaTemplate<String, String> kafka = mock(KafkaTemplate.class);
    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final OutboxRelayMetrics metrics = new OutboxRelayMetrics(
            new SimpleMeterRegistry(),
            repository);
    private final DeadLetterService service = new DeadLetterService(
            repository,
            kafka,
            objectMapper,
            metrics,
            "test-relay",
            300);

    @Test
    void replayPublishesStoredPayloadAndMarksDeadLetterReplayed() {
        UUID id = UUID.randomUUID();
        DeadLetterRecord open = record(id, "OPEN");
        DeadLetterRecord replayed = record(id, "REPLAYED");
        when(repository.findById(id)).thenReturn(Optional.of(open), Optional.of(replayed));
        when(repository.findOperatorAction("idem-1", "REPLAY", id)).thenReturn(Optional.empty());
        when(repository.insertOperatorAction(
                eq("idem-1"), eq("REPLAY"), eq(id), anyString(), eq("1"), eq("corr-1")))
                .thenReturn(true);
        when(repository.claimForReplay(id, "test-relay", 300)).thenReturn(Optional.of(open));
        when(kafka.send(open.eventType(), open.aggregateId(), open.payload()))
                .thenReturn(CompletableFuture.completedFuture(null));
        when(repository.markReplayed(id, "1", "broker fixed", "test-relay")).thenReturn(true);

        DeadLetterActionResponseDto response = service.replay(
                id,
                new DeadLetterActionRequestDto("idem-1", "broker fixed", false),
                "1",
                "corr-1");

        assertThat(response.replayed()).isTrue();
        assertThat(response.status()).isEqualTo("REPLAYED");
        assertThat(response.reasonCode()).isEqualTo("REPLAYED");
        verify(kafka).send(open.eventType(), open.aggregateId(), open.payload());
        verify(repository).markReplayed(id, "1", "broker fixed", "test-relay");
    }

    @Test
    void replayWithCompletedIdempotencyKeyDoesNotPublishAgain() throws Exception {
        UUID id = UUID.randomUUID();
        DeadLetterActionResponseDto completed = new DeadLetterActionResponseDto(
                id,
                "REPLAY",
                "REPLAYED",
                false,
                true,
                false,
                "REPLAYED",
                "sha256:abc",
                Instant.now());
        when(repository.findById(id)).thenReturn(Optional.of(record(id, "REPLAYED")));
        when(repository.findOperatorAction("idem-1", "REPLAY", id))
                .thenReturn(Optional.of(new OperatorActionRecord(
                        "COMPLETED",
                        null,
                        objectMapper.writeValueAsString(completed))));

        DeadLetterActionResponseDto response = service.replay(
                id,
                new DeadLetterActionRequestDto("idem-1", "retry", false),
                "1",
                "corr-1");

        assertThat(response.replayed()).isTrue();
        verify(kafka, never()).send(anyString(), anyString(), anyString());
    }

    @Test
    void detailDoesNotExposeRawPayload() {
        UUID id = UUID.randomUUID();
        when(repository.findById(id)).thenReturn(Optional.of(record(id, "OPEN")));

        var detail = service.get(id);

        assertThat(detail.payloadHash()).isEqualTo("sha256:payload");
        assertThat(detail.payloadSizeBytes()).isPositive();
        assertThat(detail.toString()).doesNotContain("secret-code");
    }

    @Test
    void searchFetchesLimitPlusOneAndReportsHasMore() {
        UUID first = UUID.randomUUID();
        UUID second = UUID.randomUUID();
        when(repository.search(null, "promotion", null, null, 2))
                .thenReturn(List.of(record(first, "OPEN"), record(second, "OPEN")));

        var response = service.search(null, "promotion", null, null, 1);

        assertThat(response.items()).hasSize(1);
        assertThat(response.hasMore()).isTrue();
        assertThat(response.items().getFirst().id()).isEqualTo(first);
    }

    @Test
    void replayRejectsIdempotencyKeyReusedForDifferentRequest() throws Exception {
        UUID id = UUID.randomUUID();
        DeadLetterActionResponseDto completed = new DeadLetterActionResponseDto(
                id,
                "REPLAY",
                "REPLAYED",
                false,
                true,
                false,
                "REPLAYED",
                "sha256:abc",
                Instant.now());
        when(repository.findById(id)).thenReturn(Optional.of(record(id, "OPEN")));
        when(repository.findOperatorAction("idem-1", "REPLAY", id))
                .thenReturn(Optional.of(new OperatorActionRecord(
                        "COMPLETED",
                        sha256("REPLAY:" + id + ":old reason"),
                        objectMapper.writeValueAsString(completed))));

        assertThatThrownBy(() -> service.replay(
                id,
                new DeadLetterActionRequestDto("idem-1", "new reason", false),
                "1",
                "corr-1"))
                .isInstanceOf(ConflictException.class);
        verify(kafka, never()).send(anyString(), anyString(), anyString());
    }

    @Test
    void replayCompletesOperatorActionWhenClaimLosesRace() {
        UUID id = UUID.randomUUID();
        DeadLetterRecord open = record(id, "OPEN");
        when(repository.findById(id)).thenReturn(Optional.of(open));
        when(repository.findOperatorAction("idem-1", "REPLAY", id)).thenReturn(Optional.empty());
        when(repository.insertOperatorAction(
                eq("idem-1"), eq("REPLAY"), eq(id), anyString(), eq("1"), eq("corr-1")))
                .thenReturn(true);
        when(repository.claimForReplay(id, "test-relay", 300)).thenReturn(Optional.empty());

        DeadLetterActionResponseDto response = service.replay(
                id,
                new DeadLetterActionRequestDto("idem-1", "operator retry", false),
                "1",
                "corr-1");

        assertThat(response.status()).isEqualTo("FAILED");
        assertThat(response.reasonCode()).isEqualTo("NOT_REPLAYABLE");
        verify(repository).completeOperatorAction(eq("idem-1"), eq("REPLAY"), eq(id), eq("COMPLETED"), anyString());
        verify(kafka, never()).send(anyString(), anyString(), anyString());
    }

    @Test
    void replayDoesNotOverwriteStateWhenClaimOwnershipChangedAfterPublish() {
        UUID id = UUID.randomUUID();
        DeadLetterRecord open = record(id, "OPEN");
        DeadLetterRecord discarded = record(id, "DISCARDED");
        when(repository.findById(id)).thenReturn(Optional.of(open), Optional.of(discarded));
        when(repository.findOperatorAction("idem-1", "REPLAY", id)).thenReturn(Optional.empty());
        when(repository.insertOperatorAction(
                eq("idem-1"), eq("REPLAY"), eq(id), anyString(), eq("1"), eq("corr-1")))
                .thenReturn(true);
        when(repository.claimForReplay(id, "test-relay", 300)).thenReturn(Optional.of(open));
        when(kafka.send(open.eventType(), open.aggregateId(), open.payload()))
                .thenReturn(CompletableFuture.completedFuture(null));
        when(repository.markReplayed(id, "1", "broker fixed", "test-relay")).thenReturn(false);

        DeadLetterActionResponseDto response = service.replay(
                id,
                new DeadLetterActionRequestDto("idem-1", "broker fixed", false),
                "1",
                "corr-1");

        assertThat(response.status()).isEqualTo("FAILED");
        assertThat(response.reasonCode()).isEqualTo("STATE_CHANGED_AFTER_PUBLISH");
        verify(repository).completeOperatorAction(eq("idem-1"), eq("REPLAY"), eq(id), eq("COMPLETED"), anyString());
    }

    @Test
    void discardDoesNotRunWhileReplayIsInProgress() {
        UUID id = UUID.randomUUID();
        DeadLetterRecord replaying = record(id, "REPLAYING");
        when(repository.findById(id)).thenReturn(Optional.of(replaying));

        DeadLetterActionResponseDto response = service.discard(
                id,
                new DeadLetterActionRequestDto("idem-1", "operator reviewed", false),
                "1",
                "corr-1");

        assertThat(response.status()).isEqualTo("FAILED");
        assertThat(response.reasonCode()).isEqualTo("NOT_DISCARDABLE");
        verify(repository, never()).insertOperatorAction(anyString(), anyString(), eq(id), anyString(), anyString(), anyString());
        verify(repository, never()).discard(eq(id), anyString(), anyString());
    }

    @Test
    void detailComputesPayloadHashForLegacyDeadLetterRows() {
        UUID id = UUID.randomUUID();
        DeadLetterRecord legacy = new DeadLetterRecord(
                id,
                "promotion",
                UUID.randomUUID(),
                "incentive.redemption.committed",
                "reservation-1",
                "{\"coupon\":\"secret-code\"}",
                5,
                "send failed",
                Instant.now().minusSeconds(60),
                "OPEN",
                0,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                Instant.now(),
                null);
        when(repository.findById(id)).thenReturn(Optional.of(legacy));

        var detail = service.get(id);

        assertThat(detail.payloadHash()).startsWith("sha256:");
    }

    private DeadLetterRecord record(UUID id, String status) {
        return new DeadLetterRecord(
                id,
                "promotion",
                UUID.randomUUID(),
                "incentive.redemption.committed",
                "reservation-1",
                "{\"coupon\":\"secret-code\"}",
                5,
                "send failed",
                Instant.now().minusSeconds(60),
                status,
                "REPLAYED".equals(status) ? 1 : 0,
                null,
                null,
                "REPLAYED".equals(status) ? Instant.now() : null,
                null,
                "1",
                "broker fixed",
                null,
                null,
                Instant.now(),
                "sha256:payload");
    }

    private static String sha256(String value) throws Exception {
        return "sha256:" + HexFormat.of().formatHex(
                MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    }
}
