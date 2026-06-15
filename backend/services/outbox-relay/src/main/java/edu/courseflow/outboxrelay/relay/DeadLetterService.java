package edu.courseflow.outboxrelay.relay;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalQueryResponseDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalRequestDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalReviewRequestDto;
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
import java.util.Locale;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class DeadLetterService {

    private static final int MAX_LIMIT = 200;
    private static final String DLT_THRESHOLD_POLICY = "OUTBOX_DLT_DUAL_CONTROL_V1";

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
                                             String payloadHash,
                                             Integer requestedLimit) {
        int limit = Math.max(1, Math.min(requestedLimit == null ? 50 : requestedLimit, MAX_LIMIT));
        List<DeadLetterRecord> records = deadLetters.search(
                status,
                serviceName,
                eventType,
                aggregateId,
                payloadHash,
                limit + 1);
        boolean hasMore = records.size() > limit;
        return new DeadLetterQueryResponseDto(
                records.stream().limit(limit).map(this::summary).toList(),
                limit,
                hasMore);
    }

    public DeadLetterDetailDto get(UUID id) {
        return detail(record(id));
    }

    public DeadLetterApprovalQueryResponseDto approvals(UUID deadLetterId, String status, Integer requestedLimit) {
        record(deadLetterId);
        int limit = Math.max(1, Math.min(requestedLimit == null ? 50 : requestedLimit, MAX_LIMIT));
        List<DeadLetterApprovalRecord> approvals = deadLetters.approvals(deadLetterId, status, limit + 1);
        boolean hasMore = approvals.size() > limit;
        return new DeadLetterApprovalQueryResponseDto(
                approvals.stream().limit(limit).map(this::approvalDto).toList(),
                limit,
                hasMore);
    }

    public DeadLetterApprovalDto requestApproval(UUID id,
                                                 DeadLetterApprovalRequestDto request,
                                                 String actorId,
                                                 String correlationId) {
        DeadLetterRecord current = record(id);
        String action = approvalAction(request == null ? null : request.action());
        if ("REPLAY".equals(action) && !replayable(current)) {
            throw new ConflictException("Dead letter is not currently replayable");
        }
        if ("DISCARD".equals(action) && !discardable(current)) {
            throw new ConflictException("Dead letter is not currently discardable");
        }
        String reason = required(request == null ? null : request.reason(), "reason");
        String evidenceReference = required(
                request == null ? null : request.evidenceReference(),
                "evidenceReference");
        String actor = required(actorId, "actorId");
        String payloadHash = payloadHash(current);
        String requestHash = approvalRequestHash(current, action, reason, evidenceReference);
        DeadLetterApprovalRecord existing = deadLetters
                .findEquivalentActiveApproval(id, action, requestHash)
                .orElse(null);
        if (existing != null) {
            return approvalDto(existing);
        }
        return approvalDto(deadLetters.insertApproval(
                id,
                action,
                reason,
                evidenceReference,
                DLT_THRESHOLD_POLICY,
                payloadHash,
                requestHash,
                actor,
                correlationId));
    }

    public DeadLetterApprovalDto approveApproval(UUID approvalId,
                                                 DeadLetterApprovalReviewRequestDto request,
                                                 String actorId) {
        DeadLetterApprovalRecord approval = deadLetters.findApprovalById(approvalId)
                .orElseThrow(() -> new NotFoundException("Outbox dead-letter approval not found: " + approvalId));
        String reviewer = required(actorId, "actorId");
        if (reviewer.equalsIgnoreCase(approval.requestedBy())) {
            throw new ForbiddenException("Requester cannot approve their own outbox dead-letter action");
        }
        return approvalDto(deadLetters.approveApproval(approvalId, reviewer, reviewNote(request))
                .orElseThrow(() -> new ConflictException("Outbox dead-letter approval has already been reviewed")));
    }

    public DeadLetterApprovalDto rejectApproval(UUID approvalId,
                                                DeadLetterApprovalReviewRequestDto request,
                                                String actorId) {
        DeadLetterApprovalRecord approval = deadLetters.findApprovalById(approvalId)
                .orElseThrow(() -> new NotFoundException("Outbox dead-letter approval not found: " + approvalId));
        String reviewer = required(actorId, "actorId");
        return approvalDto(deadLetters.rejectApproval(approval.id(), reviewer, reviewNote(request))
                .orElseThrow(() -> new ConflictException("Outbox dead-letter approval has already been reviewed")));
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
        String requestHash = actionRequestHash("REPLAY", id, reason, request.approvalId());
        DeadLetterActionResponseDto replayed = existingCompletedResponse(idempotencyKey, "REPLAY", id, requestHash);
        if (replayed != null) {
            return replayed;
        }
        if (!replayable(current)) {
            return actionResponse(current, "REPLAY", "FAILED", false, false, false, "NOT_REPLAYABLE");
        }
        DeadLetterApprovalRecord approval = requireApprovedApproval(current, "REPLAY", request);
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
        markApprovalExecuted(approval, actorId, idempotencyKey);
        deadLetters.completeOperatorAction(idempotencyKey, "REPLAY", id, "COMPLETED", toJson(response));
        return response;
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
        String requestHash = actionRequestHash("DISCARD", id, reason, request.approvalId());
        DeadLetterActionResponseDto discarded = existingCompletedResponse(idempotencyKey, "DISCARD", id, requestHash);
        if (discarded != null) {
            return discarded;
        }
        if (!discardable(current)) {
            return actionResponse(current, "DISCARD", "FAILED", false, false, false, "NOT_DISCARDABLE");
        }
        DeadLetterApprovalRecord approval = requireApprovedApproval(current, "DISCARD", request);
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
        markApprovalExecuted(approval, actorId, idempotencyKey);
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

    private DeadLetterApprovalRecord requireApprovedApproval(DeadLetterRecord current,
                                                            String action,
                                                            DeadLetterActionRequestDto request) {
        if (request == null || request.approvalId() == null) {
            throw new ConflictException("Outbox dead-letter " + action.toLowerCase(Locale.ROOT)
                    + " requires an approved approvalId");
        }
        DeadLetterApprovalRecord approval = deadLetters.findApprovalById(request.approvalId())
                .orElseThrow(() -> new NotFoundException(
                        "Outbox dead-letter approval not found: " + request.approvalId()));
        if (!current.id().equals(approval.deadLetterId()) || !action.equals(approval.action())) {
            throw new ConflictException("Outbox dead-letter approval scope does not match the action");
        }
        if (!"APPROVED".equals(approval.status())) {
            throw new ConflictException("Outbox dead-letter action requires an approved approval");
        }
        String expectedHash = approvalRequestHash(
                current,
                action,
                required(request.reason(), "reason"),
                approval.evidenceReference());
        if (!expectedHash.equals(approval.requestHash())
                || !payloadHash(current).equals(approval.payloadHash())
                || !DLT_THRESHOLD_POLICY.equals(approval.thresholdPolicy())) {
            throw new ConflictException("Outbox dead-letter approval evidence no longer matches the action");
        }
        return approval;
    }

    private void markApprovalExecuted(DeadLetterApprovalRecord approval, String actorId, String idempotencyKey) {
        deadLetters.markApprovalExecuted(approval.id(), actorId, idempotencyKey)
                .orElseThrow(() -> new ConflictException("Outbox dead-letter approval has already been executed"));
    }

    private DeadLetterSummaryDto summary(DeadLetterRecord record) {
        return new DeadLetterSummaryDto(
                record.id(),
                record.serviceName(),
                record.sourceEventId(),
                record.eventType(),
                topic(record),
                record.kafkaPartition(),
                record.kafkaOffset(),
                record.aggregateId(),
                record.status(),
                record.attempts(),
                record.replayAttempts(),
                payloadHash(record),
                record.errorClass(),
                record.lastError(),
                record.createdAt(),
                record.updatedAt(),
                record.lastReplayAt(),
                record.replayedAt(),
                record.discardedAt());
    }

    private DeadLetterApprovalDto approvalDto(DeadLetterApprovalRecord approval) {
        return new DeadLetterApprovalDto(
                approval.id(),
                approval.deadLetterId(),
                approval.action(),
                approval.status(),
                approval.reason(),
                approval.evidenceReference(),
                approval.thresholdPolicy(),
                approval.payloadHash(),
                approval.requestHash(),
                approval.requestedBy(),
                approval.reviewedBy(),
                approval.reviewNote(),
                approval.executedBy(),
                approval.executionIdempotencyKey(),
                approval.correlationId(),
                approval.requestedAt(),
                approval.reviewedAt(),
                approval.executedAt());
    }

    private DeadLetterDetailDto detail(DeadLetterRecord record) {
        return new DeadLetterDetailDto(
                record.id(),
                record.serviceName(),
                record.sourceEventId(),
                record.eventType(),
                topic(record),
                record.kafkaPartition(),
                record.kafkaOffset(),
                record.aggregateId(),
                record.status(),
                record.attempts(),
                record.replayAttempts(),
                payloadHash(record),
                record.payload() == null ? 0 : record.payload().getBytes(StandardCharsets.UTF_8).length,
                record.errorClass(),
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

    private String topic(DeadLetterRecord record) {
        return record.topic() == null || record.topic().isBlank()
                ? record.eventType()
                : record.topic();
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

    private String approvalAction(String value) {
        String normalized = required(value, "action").toUpperCase(Locale.ROOT);
        if (!"REPLAY".equals(normalized) && !"DISCARD".equals(normalized)) {
            throw new BadRequestException("action must be REPLAY or DISCARD");
        }
        return normalized;
    }

    private String required(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new BadRequestException(field + " is required");
        }
        return value.trim();
    }

    private String reviewNote(DeadLetterApprovalReviewRequestDto request) {
        return required(request == null ? null : request.note(), "note");
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

    private String actionRequestHash(String action, UUID id, String reason, UUID approvalId) {
        if (approvalId == null) {
            throw new ConflictException("Outbox dead-letter " + action.toLowerCase(Locale.ROOT)
                    + " requires an approved approvalId");
        }
        return hash(action + ":" + id + ":" + reason + ":" + approvalId);
    }

    private String approvalRequestHash(DeadLetterRecord record,
                                       String action,
                                       String reason,
                                       String evidenceReference) {
        return hash(String.join(":",
                "DLT_APPROVAL",
                action,
                record.id().toString(),
                nullToEmpty(record.serviceName()),
                record.sourceEventId() == null ? "" : record.sourceEventId().toString(),
                nullToEmpty(record.eventType()),
                nullToEmpty(topic(record)),
                nullToEmpty(record.aggregateId()),
                nullToEmpty(record.status()),
                Integer.toString(record.attempts()),
                Integer.toString(record.replayAttempts()),
                nullToEmpty(record.errorClass()),
                payloadHash(record),
                reason,
                evidenceReference,
                DLT_THRESHOLD_POLICY));
    }

    private String nullToEmpty(String value) {
        return value == null ? "" : value;
    }

    private String rootMessage(Throwable ex) {
        Throwable root = ex;
        while (root.getCause() != null) {
            root = root.getCause();
        }
        return root.getMessage() == null ? root.getClass().getSimpleName() : root.getMessage();
    }
}
