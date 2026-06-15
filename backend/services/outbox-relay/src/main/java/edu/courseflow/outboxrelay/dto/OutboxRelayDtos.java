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
            String topic,
            Integer kafkaPartition,
            Long kafkaOffset,
            String aggregateId,
            String status,
            int attempts,
            int replayAttempts,
            String payloadHash,
            String errorClass,
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
            String topic,
            Integer kafkaPartition,
            Long kafkaOffset,
            String aggregateId,
            String status,
            int attempts,
            int replayAttempts,
            String payloadHash,
            long payloadSizeBytes,
            String errorClass,
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
            Boolean dryRun,
            UUID approvalId) {
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

    public record DeadLetterApprovalRequestDto(
            String action,
            String reason,
            String evidenceReference) {
    }

    public record DeadLetterApprovalReviewRequestDto(
            String note) {
    }

    public record DeadLetterApprovalDto(
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

    public record DeadLetterApprovalQueryResponseDto(
            List<DeadLetterApprovalDto> items,
            int limit,
            boolean hasMore) {
    }
}
