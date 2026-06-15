package edu.courseflow.outboxrelay.relay;

import java.time.Instant;
import java.util.UUID;

public record DeadLetterApprovalRecord(
        UUID id,
        UUID deadLetterId,
        String action,
        String status,
        String reason,
        String evidenceReference,
        String thresholdPolicy,
        String payloadHash,
        String requestHash,
        String requestedBy,
        String reviewedBy,
        String reviewNote,
        String executedBy,
        String executionIdempotencyKey,
        String correlationId,
        Instant requestedAt,
        Instant reviewedAt,
        Instant executedAt) {
}
