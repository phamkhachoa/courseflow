package edu.courseflow.outboxrelay.relay;

import java.time.Instant;
import java.util.UUID;

public record DeadLetterRecord(
        UUID id,
        String serviceName,
        UUID sourceEventId,
        String eventType,
        String aggregateId,
        String payload,
        int attempts,
        String lastError,
        Instant createdAt,
        String status,
        int replayAttempts,
        String lastReplayError,
        Instant lastReplayAt,
        Instant replayedAt,
        Instant discardedAt,
        String resolvedBy,
        String resolutionNote,
        String lockedBy,
        Instant lockedUntil,
        Instant updatedAt,
        String payloadHash) {
}
