package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunResultDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionPolicyRegistryDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import edu.courseflow.promotion.repository.RetentionDryRunStats;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RetentionDryRunService {

    private static final int MAX_BATCH_LIMIT = 10_000;

    private final RetentionPolicyRegistry registry;
    private final IncentiveIdempotencyKeyRepository idempotencyKeys;
    private final OutboxEventRepository outboxEvents;
    private final IncentiveReservationRepository reservations;
    private final IncentiveAccessService access;
    private final IncentiveAuditEventRepository auditEvents;
    private final ObjectMapper objectMapper;
    private final IncentiveMetrics metrics;
    private final boolean enabled;

    public RetentionDryRunService(RetentionPolicyRegistry registry,
                                  IncentiveIdempotencyKeyRepository idempotencyKeys,
                                  OutboxEventRepository outboxEvents,
                                  IncentiveReservationRepository reservations,
                                  IncentiveAccessService access,
                                  IncentiveAuditEventRepository auditEvents,
                                  ObjectMapper objectMapper,
                                  IncentiveMetrics metrics,
                                  @Value("${courseflow.promotion.retention.dry-run.enabled:true}")
                                  boolean enabled) {
        this.registry = registry;
        this.idempotencyKeys = idempotencyKeys;
        this.outboxEvents = outboxEvents;
        this.reservations = reservations;
        this.access = access;
        this.auditEvents = auditEvents;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
        this.enabled = enabled;
    }

    @Transactional(readOnly = true)
    public RetentionPolicyRegistryDto policies(CurrentUser user) {
        requireOperatorActor(user);
        return registry.listPolicies();
    }

    @Transactional
    public RetentionDryRunResponseDto dryRun(RetentionDryRunRequestDto request,
                                             CurrentUser user,
                                             String correlationId) {
        if (!enabled) {
            throw new ForbiddenException("Promotion retention dry-run is disabled");
        }
        requireOperatorActor(user);
        RetentionScope scope = scope(request);
        if (scope.applicationScoped()) {
            access.requireAdminAccess(scope.tenantId(), scope.applicationId(), user);
        } else {
            access.requirePlatformAdmin(user);
        }

        Instant generatedAt = request == null || request.asOf() == null ? Instant.now() : request.asOf();
        int requestBatchLimit = sanitizeBatchLimit(request == null ? null : request.batchLimit(), null);
        Map<String, Integer> overrides = request == null || request.retentionDaysOverride() == null
                ? Map.of()
                : request.retentionDaysOverride();
        List<String> warnings = new ArrayList<>();
        List<RetentionDryRunResultDto> results = new ArrayList<>();

        for (RetentionPolicyRegistry.RetentionPolicy policy : registry.select(request == null ? null : request.policyIds())) {
            Instant startedAt = Instant.now();
            RetentionDryRunResultDto result = evaluatePolicy(policy, scope, generatedAt, requestBatchLimit, overrides);
            metrics.retentionDryRun(policy.policyId(), policy.targetDataset(),
                    result.blockedReason() == null ? "success" : "blocked",
                    result.eligibleCount(),
                    Duration.between(startedAt, Instant.now()));
            results.add(result);
            if (scope.applicationScoped()
                    && RetentionPolicyRegistry.PUBLISHED_OUTBOX_EVENTS.equals(policy.policyId())) {
                warnings.add("published-outbox-events is global because outbox_events does not carry tenant/application columns");
            }
        }

        String resultHash = hash(results.stream()
                .map(RetentionDryRunResultDto::resultHash)
                .reduce(scope.scopeHashSeed() + "|" + generatedAt, (left, right) -> left + "|" + right));
        UUID dryRunId = UUID.nameUUIDFromBytes(resultHash.getBytes(StandardCharsets.UTF_8));
        RetentionDryRunResponseDto response = new RetentionDryRunResponseDto(
                dryRunId,
                resultHash,
                true,
                true,
                scope.tenantId(),
                scope.applicationId(),
                generatedAt,
                results,
                warnings);
        auditDryRun(response, request == null ? null : request.reason(), user, correlationId);
        return response;
    }

    private RetentionDryRunResultDto evaluatePolicy(RetentionPolicyRegistry.RetentionPolicy policy,
                                                   RetentionScope scope,
                                                   Instant asOf,
                                                   int requestBatchLimit,
                                                   Map<String, Integer> overrides) {
        int retentionDays = retentionDays(policy, overrides);
        Instant cutoff = asOf.minus(Duration.ofDays(retentionDays));
        int batchLimit = sanitizeBatchLimit(requestBatchLimit, policy.defaultBatchLimit());
        if (!policy.dryRunSupported()) {
            return result(policy, cutoff, retentionDays, 0, 0, "NEVER_PURGE_POLICY", null, null, batchLimit);
        }
        if (scope.applicationScoped() && RetentionPolicyRegistry.PUBLISHED_OUTBOX_EVENTS.equals(policy.policyId())) {
            return result(policy, cutoff, retentionDays, 0, 0, "GLOBAL_ONLY_POLICY", null, null, batchLimit);
        }

        RetentionDryRunStats stats = switch (policy.policyId()) {
            case RetentionPolicyRegistry.EXPIRED_IDEMPOTENCY_KEYS -> idempotencyKeys.dryRunExpiredKeys(
                    scope.tenantId(), scope.applicationId(), cutoff);
            case RetentionPolicyRegistry.PUBLISHED_OUTBOX_EVENTS -> outboxEvents.dryRunPublishedEvents(cutoff);
            case RetentionPolicyRegistry.TERMINAL_RESERVATION_REQUEST_SNAPSHOTS ->
                    reservations.dryRunTerminalRequestSnapshots(scope.tenantId(), scope.applicationId(), cutoff);
            default -> throw new BadRequestException("Unsupported retention dry-run policy: " + policy.policyId());
        };
        return result(policy, cutoff, retentionDays, stats.getEligibleCount(), stats.getBlockedCount(),
                null, stats.getOldestCandidateAt(), stats.getNewestCandidateAt(), batchLimit);
    }

    private RetentionDryRunResultDto result(RetentionPolicyRegistry.RetentionPolicy policy,
                                           Instant cutoff,
                                           int retentionDays,
                                           long eligibleCount,
                                           long blockedCount,
                                           String blockedReason,
                                           Instant oldestCandidateAt,
                                           Instant newestCandidateAt,
                                           int batchLimit) {
        String resultHash = hash(String.join("|",
                policy.policyId(),
                policy.policyVersion(),
                cutoff.toString(),
                Long.toString(eligibleCount),
                Long.toString(blockedCount),
                Objects.toString(blockedReason, ""),
                Objects.toString(oldestCandidateAt, ""),
                Objects.toString(newestCandidateAt, ""),
                Integer.toString(batchLimit)));
        return new RetentionDryRunResultDto(
                policy.policyId(),
                policy.policyVersion(),
                policy.targetDataset(),
                policy.actionType(),
                cutoff,
                retentionDays,
                eligibleCount,
                blockedCount,
                blockedReason,
                oldestCandidateAt,
                newestCandidateAt,
                batchLimit,
                RetentionPolicyRegistry.TERMINAL_RESERVATION_REQUEST_SNAPSHOTS.equals(policy.policyId()),
                resultHash);
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

    private RetentionScope scope(RetentionDryRunRequestDto request) {
        String tenant = blankToNull(request == null ? null : request.tenantId());
        String application = blankToNull(request == null ? null : request.applicationId());
        if ((tenant == null) != (application == null)) {
            throw new BadRequestException("tenantId and applicationId must be provided together");
        }
        return new RetentionScope(tenant, application);
    }

    private void requireOperatorActor(CurrentUser user) {
        if (user == null) {
            throw new ForbiddenException("Promotion retention access requires an authenticated operator");
        }
        if ("service".equalsIgnoreCase(access.actorType(user))) {
            throw new ForbiddenException("Promotion retention access is not available to runtime service actors");
        }
    }

    private void auditDryRun(RetentionDryRunResponseDto response,
                             String reason,
                             CurrentUser user,
                             String correlationId) {
        Map<String, Object> payload = Map.of(
                "dryRunId", response.dryRunId().toString(),
                "resultHash", response.resultHash(),
                "tenantId", Objects.toString(response.tenantId(), ""),
                "applicationId", Objects.toString(response.applicationId(), ""),
                "policyIds", response.results().stream().map(RetentionDryRunResultDto::policyId).toList(),
                "eligibleCounts", response.results().stream()
                        .collect(java.util.stream.Collectors.toMap(
                                RetentionDryRunResultDto::policyId,
                                RetentionDryRunResultDto::eligibleCount)),
                "nonDestructive", response.nonDestructive());
        auditEvents.save(new IncentiveAuditEvent(
                response.tenantId(),
                response.applicationId(),
                response.dryRunId().toString(),
                "retention-dry-run",
                "retention.dry_run_requested",
                actorId(user),
                reason,
                toJson(payload),
                correlationId,
                access.sourceClientId(user)));
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Could not serialize retention dry-run audit payload", ex);
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

    private String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private record RetentionScope(String tenantId, String applicationId) {
        boolean applicationScoped() {
            return tenantId != null && applicationId != null;
        }

        String scopeHashSeed() {
            return Objects.toString(tenantId, "GLOBAL") + "/" + Objects.toString(applicationId, "GLOBAL");
        }
    }
}
