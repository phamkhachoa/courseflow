package edu.courseflow.outboxrelay.dto;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class OutboxRelayDtos {

    private OutboxRelayDtos() {
    }

    public record DeadLetterSummaryDto(
            UUID id,
            String serviceName,
            UUID sourceEventId,
            String eventType,
            String aggregateId,
            String status,
            int attempts,
            int replayAttempts,
            String payloadHash,
            String lastError,
            Instant createdAt,
            Instant updatedAt,
            Instant lastReplayAt,
            Instant replayedAt,
            Instant discardedAt) {
    }

    public record DeadLetterDetailDto(
            UUID id,
            String serviceName,
            UUID sourceEventId,
            String eventType,
            String aggregateId,
            String status,
            int attempts,
            int replayAttempts,
            String payloadHash,
            long payloadSizeBytes,
            String lastError,
            String lastReplayError,
            String resolvedBy,
            String resolutionNote,
            Instant createdAt,
            Instant updatedAt,
            Instant lastReplayAt,
            Instant replayedAt,
            Instant discardedAt) {
    }

    public record DeadLetterQueryResponseDto(
            List<DeadLetterSummaryDto> items,
            int limit,
            boolean hasMore) {
    }

    public record DeadLetterActionRequestDto(
            String idempotencyKey,
            String reason,
            Boolean dryRun) {
    }

    public record DeadLetterActionResponseDto(
            UUID deadLetterId,
            String action,
            String status,
            boolean dryRun,
            boolean replayed,
            boolean discarded,
            String reasonCode,
            String payloadHash,
            Instant completedAt) {
    }
}
