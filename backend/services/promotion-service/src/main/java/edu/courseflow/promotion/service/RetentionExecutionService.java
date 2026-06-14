package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_APPROVAL_CONSUMED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_APPROVAL_NOT_REPLAYABLE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_ACQUIRE_FAILED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_DISABLED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_IDEMPOTENCY_IN_PROGRESS;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_IDEMPOTENCY_NOT_REPLAYABLE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_IDEMPOTENCY_REUSED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_NOT_IN_PROGRESS;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_NOT_STARTED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_EXECUTION_RESPONSE_NOT_REPLAYABLE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_DRY_RUN_STALE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_OPERATOR_REQUIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_RESULT_HASH_MISMATCH;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveRetentionApproval;
import edu.courseflow.promotion.model.IncentiveRetentionOperation;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import edu.courseflow.promotion.repository.RetentionDryRunStats;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@Service
public class RetentionExecutionService {

    private static final int MAX_BATCH_LIMIT = 10_000;

    private final RetentionPolicyRegistry registry;
    private final IncentiveReservationRepository reservations;
    private final IncentiveRetentionOperationRepository operations;
    private final RetentionApprovalService approvals;
    private final RetentionExecutionFailureRecorder failureRecorder;
    private final IncentiveAccessService access;
    private final IncentiveAuditEventRepository auditEvents;
    private final ObjectMapper objectMapper;
    private final IncentiveMetrics metrics;
    private final TransactionTemplate transactions;
    private final boolean enabled;
    private final Duration dryRunTtl;

    public RetentionExecutionService(RetentionPolicyRegistry registry,
                                     IncentiveReservationRepository reservations,
                                     IncentiveRetentionOperationRepository operations,
                                     RetentionApprovalService approvals,
                                     RetentionExecutionFailureRecorder failureRecorder,
                                     IncentiveAccessService access,
                                     IncentiveAuditEventRepository auditEvents,
                                     ObjectMapper objectMapper,
                                     IncentiveMetrics metrics,
                                     PlatformTransactionManager transactionManager,
                                     @Value("${courseflow.promotion.retention.execution.enabled:false}")
                                     boolean enabled,
                                     @Value("${courseflow.promotion.retention.execution.dry-run-ttl-minutes:60}")
                                     long dryRunTtlMinutes) {
        this.registry = registry;
        this.reservations = reservations;
        this.operations = operations;
        this.approvals = approvals;
        this.failureRecorder = failureRecorder;
        this.access = access;
        this.auditEvents = auditEvents;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
        this.transactions = new TransactionTemplate(transactionManager);
        this.enabled = enabled;
        this.dryRunTtl = Duration.ofMinutes(Math.max(1, dryRunTtlMinutes));
    }

    public RetentionExecutionResponseDto execute(RetentionExecutionRequestDto request,
                                                 CurrentUser user,
                                                 String correlationId) {
        Instant startedAt = Instant.now();
        if (!enabled) {
            throw ForbiddenException.coded(
                    RETENTION_EXECUTION_DISABLED,
                    "Promotion retention execution is disabled");
        }
        requireOperatorActor(user);
        requireRequest(request);
        String correlation = requireText(correlationId, "correlationId");

        IncentiveRetentionApproval approval = approvals.requireApprovedForExecution(request.approvalId(), user);
        RetentionScope scope = new RetentionScope(approval.getTenantId(), approval.getApplicationId());
        RetentionPolicyRegistry.RetentionPolicy policy = requireExecutionPolicy(approval.getPolicyId());
        Instant asOf = approval.getAsOf();
        int batchLimit = approval.getBatchLimit();
        int retentionDays = approval.getRetentionDays();
        Instant cutoff = approval.getCutoffAt();

        String actorId = actorId(user);
        String requestHash = executionRequestHash(request, approval, scope, policy, cutoff, batchLimit);
        OperationStart start = null;
        try {
            start = transactions.execute(status -> startOperation(
                    request,
                    user,
                    correlation,
                    approval,
                    scope,
                    policy,
                    asOf,
                    retentionDays,
                    cutoff,
                    batchLimit,
                    requestHash,
                    actorId));
            if (start == null) {
                throw ConflictException.coded(
                        RETENTION_EXECUTION_ACQUIRE_FAILED,
                        "Could not start retention execution operation");
            }
            if (start.replayResponse() != null) {
                metrics.retentionExecution(policy.policyId(), policy.targetDataset(), "replay",
                        start.replayResponse().redactedCount(), Duration.between(startedAt, Instant.now()));
                return withReplay(start.replayResponse());
            }
            UUID operationId = start.operationId();
            RetentionDryRunStats approvedStats = start.stats();
            UUID startedDryRunId = start.approvedDryRunId();
            String startedResultHash = start.approvedResultHash();
            return transactions.execute(status -> executeStartedOperation(
                    operationId,
                    approval,
                    user,
                    scope,
                    policy,
                    approvedStats,
                    startedDryRunId,
                    startedResultHash,
                    cutoff,
                    batchLimit,
                    actorId,
                    startedAt));
        } catch (RuntimeException ex) {
            if (start != null && start.operationId() != null) {
                failureRecorder.recordFailure(
                        approval,
                        user,
                        correlation,
                        ex,
                        Duration.between(startedAt, Instant.now()));
            }
            throw ex;
        }
    }

    private OperationStart startOperation(RetentionExecutionRequestDto request,
                                          CurrentUser user,
                                          String correlation,
                                          IncentiveRetentionApproval approval,
                                          RetentionScope scope,
                                          RetentionPolicyRegistry.RetentionPolicy policy,
                                          Instant asOf,
                                          int retentionDays,
                                          Instant cutoff,
                                          int batchLimit,
        String requestHash,
        String actorId) {
        IncentiveRetentionApproval currentApproval = approvals.requireApprovedForExecution(approval.getId(), user);
        var existingForApproval = operations.lockByApprovalId(approval.getId());
        if (existingForApproval.isPresent()) {
            IncentiveRetentionOperation existing = existingForApproval.get();
            if (!existing.getIdempotencyKey().equals(request.idempotencyKey().trim())) {
                throw ConflictException.coded(
                        RETENTION_APPROVAL_CONSUMED,
                        "Retention approval already has an execution operation");
            }
            if (!existing.getRequestHash().equals(requestHash)) {
                throw ConflictException.coded(
                        RETENTION_EXECUTION_IDEMPOTENCY_REUSED,
                        "Retention execution idempotency key was reused with a different payload");
            }
            if (existing.succeeded()) {
                return OperationStart.replay(readResponse(existing.getResponseJson()));
            }
            if (existing.inProgress()) {
                throw ConflictException.coded(
                        RETENTION_EXECUTION_IDEMPOTENCY_IN_PROGRESS,
                        "Retention execution idempotency key is already in progress");
            }
            throw ConflictException.coded(
                    RETENTION_APPROVAL_NOT_REPLAYABLE,
                    "Retention execution approval is not replayable");
        }
        if (!currentApproval.approved()) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_CONSUMED,
                    "Retention approval is already executed");
        }

        RetentionDryRunStats stats = reservations.dryRunTerminalRequestSnapshots(
                scope.tenantId(), scope.applicationId(), cutoff);
        String policyResultHash = policyResultHash(policy, cutoff, retentionDays, stats, batchLimit);
        String approvedResultHash = responseResultHash(scope, asOf, List.of(policyResultHash));
        UUID approvedDryRunId = UUID.nameUUIDFromBytes(approvedResultHash.getBytes(StandardCharsets.UTF_8));
        if (!approvedResultHash.equals(approval.getDryRunResultHash())
                || !approvedDryRunId.equals(approval.getDryRunId())) {
            throw ConflictException.coded(
                    RETENTION_RESULT_HASH_MISMATCH,
                    "Approved retention dry-run no longer matches current candidates");
        }

        UUID executionId = UUID.randomUUID();
        int inserted = operations.insertInProgressIfAbsent(
                executionId,
                policy.policyId(),
                policy.policyVersion(),
                policy.targetDataset(),
                scope.operationScopeKey(),
                approval.getId(),
                scope.tenantId(),
                scope.applicationId(),
                approvedDryRunId,
                approvedResultHash,
                cutoff,
                stats.getEligibleCount(),
                batchLimit,
                request.idempotencyKey().trim(),
                requestHash,
                approval.getReason(),
                approval.getChangeTicket(),
                approval.getRestoreDrillRef(),
                approval.getApprovedBy(),
                actorId,
                correlation);

        IncentiveRetentionOperation operation = operations
                .lockByIdempotencyKey(policy.policyId(), scope.operationScopeKey(), request.idempotencyKey().trim())
                .orElseThrow(() -> ConflictException.coded(
                        RETENTION_EXECUTION_ACQUIRE_FAILED,
                        "Could not acquire retention execution operation"));
        if (!operation.getRequestHash().equals(requestHash)) {
            throw ConflictException.coded(
                    RETENTION_EXECUTION_IDEMPOTENCY_REUSED,
                    "Retention execution idempotency key was reused with a different payload");
        }
        if (inserted == 0) {
            if (operation.succeeded()) {
                return OperationStart.replay(readResponse(operation.getResponseJson()));
            }
            if (operation.inProgress()) {
                throw ConflictException.coded(
                        RETENTION_EXECUTION_IDEMPOTENCY_IN_PROGRESS,
                        "Retention execution idempotency key is already in progress");
            }
            throw ConflictException.coded(
                    RETENTION_EXECUTION_IDEMPOTENCY_NOT_REPLAYABLE,
                    "Retention execution idempotency key is not replayable");
        }
        if (!operation.inProgress()) {
            throw ConflictException.coded(
                    RETENTION_EXECUTION_IDEMPOTENCY_NOT_REPLAYABLE,
                    "Retention execution idempotency key is not replayable");
        }
        return OperationStart.started(operation.getId(), stats, approvedDryRunId, approvedResultHash);
    }

    private RetentionExecutionResponseDto executeStartedOperation(UUID operationId,
                                                                  IncentiveRetentionApproval approval,
                                                                  CurrentUser user,
                                                                  RetentionScope scope,
                                                                  RetentionPolicyRegistry.RetentionPolicy policy,
                                                                  RetentionDryRunStats stats,
                                                                  UUID approvedDryRunId,
                                                                  String approvedResultHash,
                                                                  Instant cutoff,
                                                                  int batchLimit,
                                                                  String actorId,
                                                                  Instant startedAt) {
        IncentiveRetentionApproval currentApproval = approvals.requireApprovedForExecution(approval.getId(), user);
        if (!currentApproval.approved()) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_CONSUMED,
                    "Retention approval is already executed");
        }
        IncentiveRetentionOperation operation = operations.lockById(operationId)
                .orElseThrow(() -> ConflictException.coded(
                        RETENTION_EXECUTION_NOT_STARTED,
                        "Retention execution operation was not started"));
        if (!operation.inProgress()) {
            throw ConflictException.coded(
                    RETENTION_EXECUTION_NOT_IN_PROGRESS,
                    "Retention execution operation is not in progress");
        }
        String sourceClientId = access.sourceClientId(user);
        auditOperation("retention.execution_requested", operation, 0, stats.getEligibleCount(), false, sourceClientId);
        Instant redactedAt = Instant.now();
        String redactedSnapshot = redactedSnapshot(policy, operation, redactedAt);
        int redacted = reservations.redactTerminalRequestSnapshots(
                scope.tenantId(),
                scope.applicationId(),
                cutoff,
                batchLimit,
                redactedSnapshot);
        RetentionExecutionResponseDto response = new RetentionExecutionResponseDto(
                operation.getId(),
                IncentiveRetentionOperation.STATUS_SUCCEEDED,
                policy.policyId(),
                policy.policyVersion(),
                policy.targetDataset(),
                scope.tenantId(),
                scope.applicationId(),
                cutoff,
                approvedDryRunId,
                approvedResultHash,
                stats.getEligibleCount(),
                redacted,
                batchLimit,
                stats.getEligibleCount() > redacted,
                false,
                redactedAt);
        operation.complete(redacted, toJson(response), redactedAt);
        currentApproval.markExecuted(actorId, redactedAt);
        auditOperation("retention.execution_completed", operation, redacted, stats.getEligibleCount(),
                stats.getEligibleCount() > redacted, sourceClientId);
        metrics.retentionExecution(policy.policyId(), policy.targetDataset(), "success",
                redacted, Duration.between(startedAt, Instant.now()));
        return response;
    }

    private void requireRequest(RetentionExecutionRequestDto request) {
        if (request == null) {
            throw new BadRequestException("Retention execution request is required");
        }
        if (request.approvalId() == null) {
            throw new BadRequestException("approvalId is required");
        }
        requireText(request.idempotencyKey(), "idempotencyKey");
        if (!Boolean.TRUE.equals(request.confirm())) {
            throw new BadRequestException("Retention execution requires confirm=true");
        }
    }

    private RetentionPolicyRegistry.RetentionPolicy requireExecutionPolicy(String policyId) {
        RetentionPolicyRegistry.RetentionPolicy policy = registry.select(List.of(policyId)).getFirst();
        if (!RetentionPolicyRegistry.TERMINAL_RESERVATION_REQUEST_SNAPSHOTS.equals(policy.policyId())) {
            throw new BadRequestException("Unsupported destructive retention execution policy: " + policy.policyId());
        }
        return policy;
    }

    private void validateFreshDryRun(Instant asOf) {
        Instant now = Instant.now();
        if (asOf.isBefore(now.minus(dryRunTtl))) {
            throw ConflictException.coded(
                    RETENTION_DRY_RUN_STALE,
                    "Approved retention dry-run is stale; run a fresh dry-run");
        }
        if (asOf.isAfter(now.plus(Duration.ofMinutes(5)))) {
            throw new BadRequestException("asOf cannot be in the future");
        }
    }

    private int retentionDays(RetentionPolicyRegistry.RetentionPolicy policy, Map<String, Integer> overrides) {
        Integer requested = overrides.get(policy.policyId());
        int value = requested == null ? policy.defaultRetentionDays() : requested;
        if (value < policy.minimumRetentionDays()) {
            throw new BadRequestException("Retention override is below minimum for policy: " + policy.policyId());
        }
        return value;
    }

    private int sanitizeBatchLimit(Integer requested, Integer defaultValue) {
        int fallback = defaultValue == null ? 1_000 : defaultValue;
        int value = requested == null || requested <= 0 ? fallback : requested;
        return Math.min(value, MAX_BATCH_LIMIT);
    }

    private RetentionScope scope(String tenantId, String applicationId) {
        String tenant = blankToNull(tenantId);
        String application = blankToNull(applicationId);
        if ((tenant == null) != (application == null)) {
            throw new BadRequestException("tenantId and applicationId must be provided together");
        }
        return new RetentionScope(tenant, application);
    }

    private String policyResultHash(RetentionPolicyRegistry.RetentionPolicy policy,
                                    Instant cutoff,
                                    int retentionDays,
                                    RetentionDryRunStats stats,
                                    int batchLimit) {
        return hash(String.join("|",
                policy.policyId(),
                policy.policyVersion(),
                cutoff.toString(),
                Long.toString(stats.getEligibleCount()),
                Long.toString(stats.getBlockedCount()),
                "",
                Objects.toString(stats.getOldestCandidateAt(), ""),
                Objects.toString(stats.getNewestCandidateAt(), ""),
                Integer.toString(batchLimit)));
    }

    private String responseResultHash(RetentionScope scope, Instant asOf, List<String> policyResultHashes) {
        return hash(policyResultHashes.stream()
                .reduce(scope.scopeHashSeed() + "|" + asOf, (left, right) -> left + "|" + right));
    }

    private String executionRequestHash(RetentionExecutionRequestDto request,
                                        IncentiveRetentionApproval approval,
                                        RetentionScope scope,
                                        RetentionPolicyRegistry.RetentionPolicy policy,
                                        Instant cutoff,
                                        int batchLimit) {
        return hash(String.join("|",
                "retention-execution",
                approval.getId().toString(),
                policy.policyId(),
                policy.policyVersion(),
                scope.scopeHashSeed(),
                approval.getAsOf().toString(),
                cutoff.toString(),
                approval.getDryRunId().toString(),
                approval.getDryRunResultHash(),
                Integer.toString(batchLimit),
                approval.getReason(),
                approval.getChangeTicket(),
                approval.getRestoreDrillRef(),
                request.idempotencyKey().trim()));
    }

    private String redactedSnapshot(RetentionPolicyRegistry.RetentionPolicy policy,
                                    IncentiveRetentionOperation operation,
                                    Instant redactedAt) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("snapshotVersion", "reservation-request-snapshot.redacted.v1");
        payload.put("policyId", policy.policyId());
        payload.put("policyVersion", policy.policyVersion());
        payload.put("retentionRedacted", true);
        payload.put("requestSnapshotMinimized", true);
        payload.put("rawSnapshotRemoved", true);
        payload.put("redactedAt", redactedAt.toString());
        payload.put("operationId", operation.getId().toString());
        payload.put("approvalId", operation.getApprovalId().toString());
        payload.put("dryRunId", operation.getDryRunId().toString());
        payload.put("approvedResultHash", operation.getDryRunResultHash());
        return toJson(payload);
    }

    private void auditOperation(String action,
                                IncentiveRetentionOperation operation,
                                long redacted,
                                long eligibleBefore,
                                boolean hasMore,
                                String sourceClientId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("operationId", operation.getId().toString());
        payload.put("approvalId", operation.getApprovalId() == null ? "" : operation.getApprovalId().toString());
        payload.put("policyId", operation.getPolicyId());
        payload.put("policyVersion", operation.getPolicyVersion());
        payload.put("targetDataset", operation.getTargetDataset());
        payload.put("tenantId", Objects.toString(operation.getTenantId(), ""));
        payload.put("applicationId", Objects.toString(operation.getApplicationId(), ""));
        payload.put("dryRunId", operation.getDryRunId().toString());
        payload.put("approvedResultHash", operation.getDryRunResultHash());
        payload.put("cutoff", operation.getCutoffAt().toString());
        payload.put("eligibleBefore", eligibleBefore);
        payload.put("redactedCount", redacted);
        payload.put("batchLimit", operation.getBatchLimit());
        payload.put("hasMore", hasMore);
        payload.put("changeTicket", operation.getChangeTicket());
        payload.put("restoreDrillRef", operation.getRestoreDrillRef());
        payload.put("idempotencyKeyHash", hash(operation.getIdempotencyKey()));
        auditEvents.save(new IncentiveAuditEvent(
                operation.getTenantId(),
                operation.getApplicationId(),
                operation.getId().toString(),
                "retention-execution",
                action,
                operation.getExecutedBy(),
                operation.getReason(),
                toJson(payload),
                operation.getCorrelationId(),
                sourceClientId));
    }

    private RetentionExecutionResponseDto readResponse(String responseJson) {
        try {
            return objectMapper.readValue(responseJson, RetentionExecutionResponseDto.class);
        } catch (JsonProcessingException ex) {
            throw ConflictException.coded(
                    RETENTION_EXECUTION_RESPONSE_NOT_REPLAYABLE,
                    "Stored retention execution response is not replayable");
        }
    }

    private RetentionExecutionResponseDto withReplay(RetentionExecutionResponseDto response) {
        return new RetentionExecutionResponseDto(
                response.executionId(),
                response.status(),
                response.policyId(),
                response.policyVersion(),
                response.targetDataset(),
                response.tenantId(),
                response.applicationId(),
                response.cutoff(),
                response.dryRunId(),
                response.approvedResultHash(),
                response.eligibleBefore(),
                response.redactedCount(),
                response.batchLimit(),
                response.hasMore(),
                true,
                response.executedAt());
    }

    private void requireOperatorActor(CurrentUser user) {
        if (user == null) {
            throw ForbiddenException.coded(
                    RETENTION_OPERATOR_REQUIRED,
                    "Promotion retention access requires an authenticated operator");
        }
        if ("service".equalsIgnoreCase(access.actorType(user))) {
            throw ForbiddenException.coded(
                    RETENTION_OPERATOR_REQUIRED,
                    "Promotion retention access is not available to runtime service actors");
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Could not serialize retention execution payload", ex);
        }
    }

    private String hash(String raw) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(digest.digest(raw.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 not available", ex);
        }
    }

    private String actorId(CurrentUser user) {
        if (user == null) {
            return "unknown";
        }
        if (user.email() != null && !user.email().isBlank()) {
            return user.email();
        }
        return user.id() == null ? "unknown" : user.id().toString();
    }

    private String requireText(String value, String field) {
        String clean = blankToNull(value);
        if (clean == null) {
            throw new BadRequestException(field + " is required");
        }
        return clean;
    }

    private String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private record OperationStart(UUID operationId,
                                  RetentionExecutionResponseDto replayResponse,
                                  RetentionDryRunStats stats,
                                  UUID approvedDryRunId,
                                  String approvedResultHash) {
        static OperationStart started(UUID operationId,
                                      RetentionDryRunStats stats,
                                      UUID approvedDryRunId,
                                      String approvedResultHash) {
            return new OperationStart(operationId, null, stats, approvedDryRunId, approvedResultHash);
        }

        static OperationStart replay(RetentionExecutionResponseDto replayResponse) {
            return new OperationStart(null, replayResponse, null, null, null);
        }
    }

    private record RetentionScope(String tenantId, String applicationId) {
        boolean applicationScoped() {
            return tenantId != null && applicationId != null;
        }

        String scopeHashSeed() {
            return Objects.toString(tenantId, "GLOBAL") + "/" + Objects.toString(applicationId, "GLOBAL");
        }

        String operationScopeKey() {
            if (!applicationScoped()) {
                return "GLOBAL:0:|APP:0:";
            }
            return "TENANT:" + tenantId.length() + ":" + tenantId
                    + "|APP:" + applicationId.length() + ":" + applicationId;
        }
    }
}
