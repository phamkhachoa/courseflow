package edu.courseflow.outboxrelay.relay;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterActionRequestDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterActionResponseDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterDetailDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterQueryResponseDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterSummaryDto;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class DeadLetterService {

    private static final int MAX_LIMIT = 200;

    private final DeadLetterRepository deadLetters;
    private final KafkaTemplate<String, String> kafka;
    private final ObjectMapper objectMapper;
    private final OutboxRelayMetrics metrics;
    private final String workerId;
    private final int replayLeaseSeconds;

    public DeadLetterService(DeadLetterRepository deadLetters,
                             KafkaTemplate<String, String> kafka,
                             ObjectMapper objectMapper,
                             OutboxRelayMetrics metrics,
                             @Value("${courseflow.outbox.worker-id:${spring.application.name:outbox-relay}-${random.uuid}}")
                             String workerId,
                             @Value("${courseflow.outbox.replay-lease-seconds:300}") int replayLeaseSeconds) {
        this.deadLetters = deadLetters;
        this.kafka = kafka;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
        this.workerId = workerId;
        this.replayLeaseSeconds = replayLeaseSeconds;
    }

    public DeadLetterQueryResponseDto search(String status,
                                             String serviceName,
                                             String eventType,
                                             String aggregateId,
                                             Integer requestedLimit) {
        int limit = Math.max(1, Math.min(requestedLimit == null ? 50 : requestedLimit, MAX_LIMIT));
        List<DeadLetterRecord> records = deadLetters.search(status, serviceName, eventType, aggregateId, limit + 1);
        boolean hasMore = records.size() > limit;
        return new DeadLetterQueryResponseDto(
                records.stream().limit(limit).map(this::summary).toList(),
                limit,
                hasMore);
    }

    public DeadLetterDetailDto get(UUID id) {
        return detail(record(id));
    }

    public DeadLetterActionResponseDto replay(UUID id, DeadLetterActionRequestDto request,
                                              String actorId, String correlationId) {
        DeadLetterRecord current = record(id);
        if (Boolean.TRUE.equals(request == null ? null : request.dryRun())) {
            return actionResponse(current, "REPLAY", "DRY_RUN", true, false, false,
                    replayable(current) ? "WOULD_REPLAY" : "NOT_REPLAYABLE");
        }

        String idempotencyKey = required(request == null ? null : request.idempotencyKey(), "idempotencyKey");
        String reason = required(request == null ? null : request.reason(), "reason");
        String requestHash = hash("REPLAY:" + id + ":" + reason);
        DeadLetterActionResponseDto replayed = existingCompletedResponse(idempotencyKey, "REPLAY", id, requestHash);
        if (replayed != null) {
            return replayed;
        }
        if (!replayable(current)) {
            return actionResponse(current, "REPLAY", "FAILED", false, false, false, "NOT_REPLAYABLE");
        }
        if (!deadLetters.insertOperatorAction(idempotencyKey, "REPLAY", id, requestHash, actorId, correlationId)) {
            throw new ConflictException("Replay action is already in progress");
        }

        DeadLetterRecord claimed = deadLetters.claimForReplay(id, workerId, replayLeaseSeconds).orElse(null);
        if (claimed == null) {
            DeadLetterActionResponseDto response = actionResponse(
                    current, "REPLAY", "FAILED", false, false, false, "NOT_REPLAYABLE");
            deadLetters.completeOperatorAction(idempotencyKey, "REPLAY", id, "COMPLETED", toJson(response));
            return response;
        }
        DeadLetterActionResponseDto response;
        try {
            kafka.send(claimed.eventType(), claimed.aggregateId(), claimed.payload()).join();
            if (!deadLetters.markReplayed(id, actorId, reason, workerId)) {
                DeadLetterRecord changed = record(id);
                metrics.replay("state_conflict", changed.serviceName(), changed.eventType());
                response = actionResponse(
                        changed,
                        "REPLAY",
                        "FAILED",
                        false,
                        false,
                        false,
                        "STATE_CHANGED_AFTER_PUBLISH");
                deadLetters.completeOperatorAction(idempotencyKey, "REPLAY", id, "COMPLETED", toJson(response));
                return response;
            }
            DeadLetterRecord updated = record(id);
            metrics.replay("success", updated.serviceName(), updated.eventType());
            response = actionResponse(updated, "REPLAY", "REPLAYED", false, true, false, "REPLAYED");
            deadLetters.completeOperatorAction(idempotencyKey, "REPLAY", id, "COMPLETED", toJson(response));
            return response;
        } catch (RuntimeException ex) {
            boolean markedFailed = deadLetters.markReplayFailed(id, rootMessage(ex), workerId);
            DeadLetterRecord failed = record(id);
            metrics.replay("error", failed.serviceName(), failed.eventType());
            response = actionResponse(
                    failed,
                    "REPLAY",
                    "FAILED",
                    false,
                    false,
                    false,
                    markedFailed ? "PUBLISH_FAILED" : "STATE_CHANGED_AFTER_PUBLISH_FAILURE");
            deadLetters.completeOperatorAction(idempotencyKey, "REPLAY", id, "COMPLETED", toJson(response));
            return response;
        }
    }

    public DeadLetterActionResponseDto discard(UUID id, DeadLetterActionRequestDto request,
                                               String actorId, String correlationId) {
        DeadLetterRecord current = record(id);
        if (Boolean.TRUE.equals(request == null ? null : request.dryRun())) {
            return actionResponse(current, "DISCARD", "DRY_RUN", true, false, false,
                    discardable(current) ? "WOULD_DISCARD" : "NOT_DISCARDABLE");
        }

        String idempotencyKey = required(request == null ? null : request.idempotencyKey(), "idempotencyKey");
        String reason = required(request == null ? null : request.reason(), "reason");
        String requestHash = hash("DISCARD:" + id + ":" + reason);
        DeadLetterActionResponseDto discarded = existingCompletedResponse(idempotencyKey, "DISCARD", id, requestHash);
        if (discarded != null) {
            return discarded;
        }
        if (!discardable(current)) {
            return actionResponse(current, "DISCARD", "FAILED", false, false, false, "NOT_DISCARDABLE");
        }
        if (!deadLetters.insertOperatorAction(idempotencyKey, "DISCARD", id, requestHash, actorId, correlationId)) {
            throw new ConflictException("Discard action is already in progress");
        }
        if (!deadLetters.discard(id, actorId, reason)) {
            DeadLetterActionResponseDto response = actionResponse(
                    current, "DISCARD", "FAILED", false, false, false, "NOT_DISCARDABLE");
            deadLetters.completeOperatorAction(idempotencyKey, "DISCARD", id, "COMPLETED", toJson(response));
            return response;
        }
        DeadLetterRecord updated = record(id);
        DeadLetterActionResponseDto response = actionResponse(
                updated, "DISCARD", "DISCARDED", false, false, true, "DISCARDED");
        deadLetters.completeOperatorAction(idempotencyKey, "DISCARD", id, "COMPLETED", toJson(response));
        return response;
    }

    public static String payloadHash(String payload) {
        return hash(payload == null ? "" : payload);
    }

    private DeadLetterRecord record(UUID id) {
        return deadLetters.findById(id)
                .orElseThrow(() -> new NotFoundException("Outbox dead letter not found: " + id));
    }

    private DeadLetterActionResponseDto existingCompletedResponse(String idempotencyKey,
                                                                 String action,
                                                                 UUID id,
                                                                 String requestHash) {
        OperatorActionRecord existing = deadLetters.findOperatorAction(idempotencyKey, action, id).orElse(null);
        if (existing == null) {
            return null;
        }
        if (existing.requestHash() != null && !existing.requestHash().equals(requestHash)) {
            throw new ConflictException("Idempotency key was already used with a different request");
        }
        if ("COMPLETED".equals(existing.status())) {
            return fromJson(existing.responseJson(), DeadLetterActionResponseDto.class);
        }
        throw new ConflictException("Outbox dead-letter action is already in progress");
    }

    private DeadLetterSummaryDto summary(DeadLetterRecord record) {
        return new DeadLetterSummaryDto(
                record.id(),
                record.serviceName(),
                record.sourceEventId(),
                record.eventType(),
                record.aggregateId(),
                record.status(),
                record.attempts(),
                record.replayAttempts(),
                payloadHash(record),
                record.lastError(),
                record.createdAt(),
                record.updatedAt(),
                record.lastReplayAt(),
                record.replayedAt(),
                record.discardedAt());
    }

    private DeadLetterDetailDto detail(DeadLetterRecord record) {
        return new DeadLetterDetailDto(
                record.id(),
                record.serviceName(),
                record.sourceEventId(),
                record.eventType(),
                record.aggregateId(),
                record.status(),
                record.attempts(),
                record.replayAttempts(),
                payloadHash(record),
                record.payload() == null ? 0 : record.payload().getBytes(StandardCharsets.UTF_8).length,
                record.lastError(),
                record.lastReplayError(),
                record.resolvedBy(),
                record.resolutionNote(),
                record.createdAt(),
                record.updatedAt(),
                record.lastReplayAt(),
                record.replayedAt(),
                record.discardedAt());
    }

    private DeadLetterActionResponseDto actionResponse(DeadLetterRecord record,
                                                       String action,
                                                       String status,
                                                       boolean dryRun,
                                                       boolean replayed,
                                                       boolean discarded,
                                                       String reasonCode) {
        return new DeadLetterActionResponseDto(
                record.id(),
                action,
                status,
                dryRun,
                replayed,
                discarded,
                reasonCode,
                payloadHash(record),
                Instant.now());
    }

    private String payloadHash(DeadLetterRecord record) {
        return record.payloadHash() == null || record.payloadHash().isBlank()
                ? payloadHash(record.payload())
                : record.payloadHash();
    }

    private boolean replayable(DeadLetterRecord record) {
        return "OPEN".equals(record.status()) || "FAILED".equals(record.status())
                || ("REPLAYING".equals(record.status())
                && (record.lockedUntil() == null || record.lockedUntil().isBefore(Instant.now())));
    }

    private boolean discardable(DeadLetterRecord record) {
        return "OPEN".equals(record.status()) || "FAILED".equals(record.status());
    }

    private String required(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new BadRequestException(field + " is required");
        }
        return value.trim();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new BadRequestException("Could not serialize outbox action response");
        }
    }

    private <T> T fromJson(String json, Class<T> type) {
        try {
            return objectMapper.readValue(json, type);
        } catch (JsonProcessingException ex) {
            throw new BadRequestException("Could not read outbox action response");
        }
    }

    private static String hash(String value) {
        try {
            return "sha256:" + HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private String rootMessage(Throwable ex) {
        Throwable root = ex;
        while (root.getCause() != null) {
            root = root.getCause();
        }
        return root.getMessage() == null ? root.getClass().getSimpleName() : root.getMessage();
    }
}
