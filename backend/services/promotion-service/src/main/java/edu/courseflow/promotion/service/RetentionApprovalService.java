package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_ADMIN_FORBIDDEN;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_APPROVAL_ALREADY_EXISTS;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_APPROVAL_EXPIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_APPROVAL_NOT_APPROVED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_APPROVAL_NOT_FOUND;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_APPROVAL_NOT_PENDING;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_DRY_RUN_STALE;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_OPERATOR_REQUIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_PLATFORM_ADMIN_REQUIRED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_RESTORE_DRILL_ALREADY_EXISTS;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_RESTORE_DRILL_INVALID;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_REVIEW_FORBIDDEN;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_RESULT_HASH_MISMATCH;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_SELF_APPROVAL_BLOCKED;
import static edu.courseflow.promotion.service.PromotionErrorCodes.RETENTION_SELF_EXECUTION_BLOCKED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionAuditEvidenceEventDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionEvidencePackDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionEvidencePackExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionEvidenceDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionRestoreDrillEvidenceDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionRestoreDrillRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionRestoreDrillResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveRestoreDrill;
import edu.courseflow.promotion.model.IncentiveRetentionApproval;
import edu.courseflow.promotion.model.IncentiveRetentionOperation;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRestoreDrillRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionApprovalRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import edu.courseflow.promotion.repository.RetentionDryRunStats;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.data.domain.PageRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RetentionApprovalService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };
    private static final DateTimeFormatter EVIDENCE_FILENAME_TIME =
            DateTimeFormatter.ofPattern("yyyyMMddHHmmss").withZone(ZoneOffset.UTC);
    private static final int MAX_BATCH_LIMIT = 10_000;
    private static final int MAX_QUEUE_LIMIT = 200;
    private static final int MAX_EVIDENCE_AUDIT_EVENTS = 100;
    private static final String RETENTION_SCOPE_APPLICATION = "APPLICATION";
    private static final String RETENTION_SCOPE_GLOBAL = "GLOBAL";
    private static final Pattern SHA256_HASH = Pattern.compile("sha256:[0-9a-f]{64}");
    private static final Duration RESTORE_DRILL_CLOCK_SKEW = Duration.ofMinutes(5);

    private final RetentionPolicyRegistry registry;
    private final IncentiveReservationRepository reservations;
    private final IncentiveRestoreDrillRepository restoreDrills;
    private final IncentiveRetentionApprovalRepository approvals;
    private final IncentiveRetentionOperationRepository operations;
    private final IncentiveAccessService access;
    private final IncentiveAuditEventRepository auditEvents;
    private final ObjectMapper objectMapper;
    private final Duration approvalTtl;

    public RetentionApprovalService(RetentionPolicyRegistry registry,
                                    IncentiveReservationRepository reservations,
                                    IncentiveRestoreDrillRepository restoreDrills,
                                    IncentiveRetentionApprovalRepository approvals,
                                    IncentiveRetentionOperationRepository operations,
                                    IncentiveAccessService access,
                                    IncentiveAuditEventRepository auditEvents,
                                    ObjectMapper objectMapper,
                                    @Value("${courseflow.promotion.retention.execution.dry-run-ttl-minutes:60}")
                                    long approvalTtlMinutes) {
        this.registry = registry;
        this.reservations = reservations;
        this.restoreDrills = restoreDrills;
        this.approvals = approvals;
        this.operations = operations;
        this.access = access;
        this.auditEvents = auditEvents;
        this.objectMapper = objectMapper;
        this.approvalTtl = Duration.ofMinutes(Math.max(1, approvalTtlMinutes));
    }

    @Transactional
    public RetentionRestoreDrillResponseDto registerRestoreDrill(RetentionRestoreDrillRequestDto request,
                                                                 CurrentUser user,
                                                                 String correlationId) {
        requireOperatorActor(user);
        requirePlatformAdmin(user);
        if (request == null) {
            throw new BadRequestException("Restore drill request is required");
        }
        String ref = requireText(request.restoreDrillRef(), "restoreDrillRef");
        String databaseName = requireText(request.databaseName(), "databaseName");
        if (!IncentiveRestoreDrill.PROMOTION_DATABASE.equals(databaseName)) {
            throw new BadRequestException("Restore drill databaseName must be " + IncentiveRestoreDrill.PROMOTION_DATABASE);
        }
        String backupPath = requireText(request.backupPath(), "backupPath");
        String artifactHash = requireText(request.artifactHash(), "artifactHash").toLowerCase(java.util.Locale.ROOT);
        if (!SHA256_HASH.matcher(artifactHash).matches()) {
            throw new BadRequestException("Restore drill artifactHash must use sha256:<64-hex>");
        }
        String status = normalizeRestoreStatus(request.status());
        Instant now = Instant.now();
        Instant checkedAt = request.checkedAt() == null ? now : request.checkedAt();
        if (checkedAt.isAfter(now.plus(RESTORE_DRILL_CLOCK_SKEW))) {
            throw new BadRequestException("restore drill checkedAt cannot be in the future");
        }
        Instant expiresAt = request.expiresAt() == null ? checkedAt.plus(approvalTtl) : request.expiresAt();
        if (!expiresAt.isAfter(checkedAt)) {
            throw new BadRequestException("restore drill expiresAt must be after checkedAt");
        }
        if (restoreDrills.findByRestoreDrillRef(ref).isPresent()) {
            throw ConflictException.coded(
                    RETENTION_RESTORE_DRILL_ALREADY_EXISTS,
                    "Restore drill reference already exists");
        }
        String actorId = actorId(user);
        IncentiveRestoreDrill drill = new IncentiveRestoreDrill(
                ref,
                databaseName,
                backupPath,
                artifactHash,
                status,
                checkedAt,
                expiresAt,
                actorId,
                request.note(),
                requireText(correlationId, "correlationId"),
                access.sourceClientId(user));
        restoreDrills.save(drill);
        audit("retention.restore_drill_registered", null, null, ref, "retention-restore-drill",
                actorId, request.note(), Map.of(
                        "restoreDrillRef", ref,
                        "databaseName", databaseName,
                        "status", status,
                        "checkedAt", checkedAt.toString(),
                        "expiresAt", expiresAt.toString(),
                        "artifactHash", artifactHash), correlationId, access.sourceClientId(user));
        return drillDto(drill);
    }

    @Transactional(readOnly = true)
    public RetentionRestoreDrillResponseDto restoreDrill(String restoreDrillRef, CurrentUser user) {
        requireOperatorActor(user);
        requirePlatformAdmin(user);
        IncentiveRestoreDrill drill = restoreDrills.findByRestoreDrillRef(
                        requireText(restoreDrillRef, "restoreDrillRef"))
                .orElseThrow(() -> new BadRequestException("Restore drill not found"));
        return drillDto(drill);
    }

    @Transactional
    public RetentionApprovalResponseDto requestApproval(RetentionApprovalRequestDto request,
                                                        CurrentUser user,
                                                        String correlationId) {
        requireOperatorActor(user);
        requireApprovalRequest(request);
        RetentionScope scope = scope(request.tenantId(), request.applicationId());
        requireAdmin(scope, user);
        RetentionPolicyRegistry.RetentionPolicy policy = requireExecutionPolicy(request.policyId());
        Instant asOf = request.asOf();
        validateFreshDryRun(asOf);
        int batchLimit = sanitizeBatchLimit(request.batchLimit(), policy.defaultBatchLimit());
        int retentionDays = retentionDays(policy, request.retentionDaysOverride() == null
                ? Map.of()
                : request.retentionDaysOverride());
        Instant cutoff = asOf.minus(Duration.ofDays(retentionDays));
        RetentionDryRunStats stats = reservations.dryRunTerminalRequestSnapshots(
                scope.tenantId(), scope.applicationId(), cutoff);
        String policyResultHash = policyResultHash(policy, cutoff, retentionDays, stats, batchLimit);
        String resultHash = responseResultHash(scope, asOf, List.of(policyResultHash));
        UUID dryRunId = UUID.nameUUIDFromBytes(resultHash.getBytes(StandardCharsets.UTF_8));
        if (!resultHash.equals(request.approvedResultHash()) || !dryRunId.equals(request.approvedDryRunId())) {
            throw ConflictException.coded(
                    RETENTION_RESULT_HASH_MISMATCH,
                    "Retention approval dry-run no longer matches current candidates");
        }
        IncentiveRestoreDrill drill = requireValidRestoreDrill(request.restoreDrillRef());
        if (!drill.getExpiresAt().isAfter(asOf)) {
            throw ConflictException.coded(
                    RETENTION_RESTORE_DRILL_INVALID,
                    "Restore drill expires before the approved dry-run timestamp");
        }
        Instant expiresAt = min(asOf.plus(approvalTtl), drill.getExpiresAt());
        if (!expiresAt.isAfter(Instant.now())) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_EXPIRED,
                    "Retention approval already expired");
        }
        approvals.findActiveForDryRun(policy.policyId(), scope.operationScopeKey(), dryRunId, resultHash, batchLimit)
                .ifPresent(existing -> {
                    throw ConflictException.coded(
                            RETENTION_APPROVAL_ALREADY_EXISTS,
                            "An active retention approval already exists for this dry-run");
                });

        String actorId = actorId(user);
        IncentiveRetentionApproval approval = new IncentiveRetentionApproval(
                policy.policyId(),
                policy.policyVersion(),
                policy.targetDataset(),
                scope.operationScopeKey(),
                scope.tenantId(),
                scope.applicationId(),
                asOf,
                cutoff,
                retentionDays,
                dryRunId,
                resultHash,
                stats.getEligibleCount(),
                batchLimit,
                request.reason().trim(),
                request.changeTicket().trim(),
                request.restoreDrillRef().trim(),
                actorId,
                requireText(correlationId, "correlationId"),
                access.sourceClientId(user),
                expiresAt);
        approvals.save(approval);
        auditApproval("retention.request_created", approval, actorId, null, correlationId, access.sourceClientId(user));
        return approvalDto(approval);
    }

    @Transactional
    public RetentionApprovalResponseDto approve(UUID approvalId,
                                                RetentionApprovalDecisionRequestDto request,
                                                CurrentUser user,
                                                String correlationId) {
        requireOperatorActor(user);
        IncentiveRetentionApproval approval = lockApproval(approvalId);
        requireReviewer(approval, user);
        String actorId = actorId(user);
        if (actorId.equals(approval.getRequestedBy())) {
            throw ForbiddenException.coded(
                    RETENTION_SELF_APPROVAL_BLOCKED,
                    "Retention approval must be reviewed by a different operator");
        }
        if (!approval.pending()) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_NOT_PENDING,
                    "Retention approval is not pending");
        }
        requireApprovalDecisionWindow(approval);
        validateApprovalStillCurrent(approval);
        requireValidRestoreDrill(approval.getRestoreDrillRef());
        approval.approve(actorId, request == null ? null : request.note(), Instant.now());
        auditApproval("retention.request_approved", approval, actorId,
                request == null ? null : request.note(), correlationId, access.sourceClientId(user));
        return approvalDto(approval);
    }

    @Transactional
    public RetentionApprovalResponseDto reject(UUID approvalId,
                                               RetentionApprovalDecisionRequestDto request,
                                               CurrentUser user,
                                               String correlationId) {
        requireOperatorActor(user);
        IncentiveRetentionApproval approval = lockApproval(approvalId);
        requireReviewer(approval, user);
        if (!approval.pending()) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_NOT_PENDING,
                    "Retention approval is not pending");
        }
        requireApprovalDecisionWindow(approval);
        String actorId = actorId(user);
        approval.reject(actorId, request == null ? null : request.note(), Instant.now());
        auditApproval("retention.request_rejected", approval, actorId,
                request == null ? null : request.note(), correlationId, access.sourceClientId(user));
        return approvalDto(approval);
    }

    @Transactional(readOnly = true)
    public RetentionApprovalResponseDto approval(UUID approvalId, CurrentUser user) {
        requireOperatorActor(user);
        IncentiveRetentionApproval approval = approvals.findById(approvalId)
                .orElseThrow(() -> BadRequestException.coded(
                        RETENTION_APPROVAL_NOT_FOUND,
                        "Retention approval not found"));
        requireReviewer(approval, user);
        return approvalDto(approval);
    }

    @Transactional(readOnly = true)
    public RetentionApprovalQueryResponseDto queue(String scopeType,
                                                   String tenantId,
                                                   String applicationId,
                                                   UUID approvalId,
                                                   UUID dryRunId,
                                                   String status,
                                                   String policyId,
                                                   String changeTicket,
                                                   String requestedBy,
                                                   String approvedBy,
                                                   String executedBy,
                                                   Boolean expired,
                                                   Instant from,
                                                   Instant to,
                                                   Integer limit,
                                                   CurrentUser user) {
        requireOperatorActor(user);
        String scope = normalizeRetentionScope(scopeType, tenantId, applicationId);
        String tenant = null;
        String application = null;
        if (RETENTION_SCOPE_GLOBAL.equals(scope)) {
            access.requirePlatformAdmin(user);
        } else {
            tenant = requireText(tenantId, "tenantId");
            application = requireText(applicationId, "applicationId");
            access.requireReviewAccess(tenant, application, user);
        }
        String normalizedStatus = normalizeApprovalStatus(status);
        int pageSize = Math.min(MAX_QUEUE_LIMIT, Math.max(1, limit == null ? 50 : limit));
        Instant now = Instant.now();
        List<IncentiveRetentionApproval> rows = approvals.search(
                tenant,
                application,
                approvalId,
                dryRunId,
                normalizedStatus,
                blankToNull(policyId),
                containsFilter(changeTicket),
                exactFilter(requestedBy),
                exactFilter(approvedBy),
                exactFilter(executedBy),
                expired,
                now,
                from,
                to,
                PageRequest.of(0, pageSize + 1));
        boolean hasMore = rows.size() > pageSize;
        return new RetentionApprovalQueryResponseDto(
                rows.stream().limit(pageSize).map(this::approvalDto).toList(),
                pageSize,
                hasMore,
                now);
    }

    @Transactional
    public RetentionEvidencePackDto evidencePack(UUID approvalId, CurrentUser user, String correlationId) {
        requireOperatorActor(user);
        EvidenceContext context = evidenceContext(approvalId, user);
        Instant generatedAt = Instant.now();
        auditEvidenceAccess("retention.evidence_pack_viewed", context.approval(), context.operation(),
                generatedAt, user, correlationId, "view", null, null);
        return buildEvidencePack(context, generatedAt);
    }

    @Transactional
    public RetentionEvidencePackExportDto evidencePackExport(UUID approvalId,
                                                             String format,
                                                             CurrentUser user,
                                                             String correlationId) {
        requireOperatorActor(user);
        EvidenceContext context = evidenceContext(approvalId, user);
        Instant generatedAt = Instant.now();
        RetentionEvidencePackDto pack = buildEvidencePack(context, generatedAt);
        String normalizedFormat = normalizeEvidenceFormat(format);
        String content = "csv".equals(normalizedFormat) ? evidenceCsv(pack) : evidenceJson(pack);
        String contentSha256 = hash(content);
        auditEvidenceAccess("retention.evidence_pack_exported", context.approval(), context.operation(),
                generatedAt, user, correlationId, normalizedFormat, contentSha256, pack.auditTrail().size());
        String extension = "csv".equals(normalizedFormat) ? "csv" : "json";
        String contentType = "csv".equals(normalizedFormat) ? "text/csv" : "application/json";
        return new RetentionEvidencePackExportDto(
                context.approval().getId(),
                "retention-evidence-pack-" + context.approval().getId() + "-"
                        + EVIDENCE_FILENAME_TIME.format(generatedAt) + "." + extension,
                contentType,
                content,
                contentSha256,
                generatedAt);
    }

    private EvidenceContext evidenceContext(UUID approvalId, CurrentUser user) {
        if (approvalId == null) {
            throw new BadRequestException("approvalId is required");
        }
        IncentiveRetentionApproval approval = approvals.findById(approvalId)
                .orElseThrow(() -> BadRequestException.coded(
                        RETENTION_APPROVAL_NOT_FOUND,
                        "Retention approval not found"));
        requireReviewer(approval, user);
        IncentiveRestoreDrill drill = restoreDrills.findByRestoreDrillRef(approval.getRestoreDrillRef()).orElse(null);
        IncentiveRetentionOperation operation = operations.findByApprovalId(approval.getId()).orElse(null);
        List<String> warnings = new ArrayList<>();
        if (drill == null) {
            warnings.add("Restore drill evidence is no longer registered.");
        }
        if (operation == null) {
            warnings.add("No retention execution operation has been recorded for this approval.");
        }
        return new EvidenceContext(approval, drill, operation, warnings);
    }

    private RetentionEvidencePackDto buildEvidencePack(EvidenceContext context, Instant generatedAt) {
        List<String> aggregateIds = new ArrayList<>();
        aggregateIds.add(context.approval().getId().toString());
        aggregateIds.add(context.approval().getDryRunId().toString());
        aggregateIds.add(context.approval().getRestoreDrillRef());
        if (context.operation() != null) {
            aggregateIds.add(context.operation().getId().toString());
        }
        List<IncentiveAuditEvent> auditRows = auditEvents.timelineByAggregateIds(
                context.approval().getTenantId(),
                context.approval().getApplicationId(),
                aggregateIds,
                PageRequest.of(0, MAX_EVIDENCE_AUDIT_EVENTS + 1));
        List<String> warnings = new ArrayList<>(context.warnings());
        if (auditRows.size() > MAX_EVIDENCE_AUDIT_EVENTS) {
            warnings.add("Audit timeline was truncated at " + MAX_EVIDENCE_AUDIT_EVENTS + " events.");
        }
        return new RetentionEvidencePackDto(
                "retention-evidence-pack.v1",
                "retention_compliance_evidence_pack",
                context.approval().getId(),
                generatedAt,
                approvalDto(context.approval()),
                context.drill() == null ? null : restoreDrillEvidenceDto(context.drill()),
                context.operation() == null ? null : executionEvidenceDto(context.operation()),
                auditRows.stream().limit(MAX_EVIDENCE_AUDIT_EVENTS).map(this::auditEvidenceEventDto).toList(),
                warnings);
    }

    @Transactional
    public IncentiveRetentionApproval requireApprovedForExecution(UUID approvalId, CurrentUser user) {
        requireOperatorActor(user);
        if (approvalId == null) {
            throw new BadRequestException("approvalId is required");
        }
        IncentiveRetentionApproval approval = lockApproval(approvalId);
        requireAdmin(new RetentionScope(approval.getTenantId(), approval.getApplicationId()), user);
        String actorId = actorId(user);
        if (actorId.equals(approval.getApprovedBy())) {
            throw ForbiddenException.coded(
                    RETENTION_SELF_EXECUTION_BLOCKED,
                    "Retention execution must be run by a different operator from approver");
        }
        if (!approval.approved() && !IncentiveRetentionApproval.STATUS_EXECUTED.equals(approval.getStatus())) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_NOT_APPROVED,
                    "Retention approval is not approved");
        }
        if (approval.approved() && approval.expired(Instant.now())) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_EXPIRED,
                    "Retention approval is expired");
        }
        if (approval.approved()) {
            requireValidRestoreDrill(approval.getRestoreDrillRef());
            validateApprovalStillCurrent(approval);
        }
        return approval;
    }

    public RetentionApprovalResponseDto approvalDto(IncentiveRetentionApproval approval) {
        return new RetentionApprovalResponseDto(
                approval.getId(),
                approval.getStatus(),
                approval.getPolicyId(),
                approval.getPolicyVersion(),
                approval.getTargetDataset(),
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getAsOf(),
                approval.getCutoffAt(),
                approval.getRetentionDays(),
                approval.getDryRunId(),
                approval.getDryRunResultHash(),
                approval.getEligibleCount(),
                approval.getBatchLimit(),
                approval.getRestoreDrillRef(),
                approval.getChangeTicket(),
                approval.getReason(),
                approval.getNote(),
                approval.getRequestedBy(),
                approval.getApprovedBy(),
                approval.getRejectedBy(),
                approval.getExecutedBy(),
                approval.getCorrelationId(),
                approval.getSourceClientId(),
                approval.getExpiresAt(),
                approval.getCreatedAt(),
                approval.getApprovedAt(),
                approval.getRejectedAt(),
                approval.getFailedAt(),
                approval.getExecutedAt());
    }

    public RetentionRestoreDrillResponseDto drillDto(IncentiveRestoreDrill drill) {
        return new RetentionRestoreDrillResponseDto(
                drill.getId(),
                drill.getRestoreDrillRef(),
                drill.getDatabaseName(),
                drill.getBackupPath(),
                drill.getArtifactHash(),
                drill.getStatus(),
                drill.getCheckedAt(),
                drill.getExpiresAt(),
                drill.getCreatedBy(),
                drill.getCreatedAt());
    }

    private RetentionRestoreDrillEvidenceDto restoreDrillEvidenceDto(IncentiveRestoreDrill drill) {
        return new RetentionRestoreDrillEvidenceDto(
                drill.getId(),
                drill.getRestoreDrillRef(),
                drill.getDatabaseName(),
                drill.getBackupPath(),
                drill.getArtifactHash(),
                drill.getStatus(),
                drill.getCheckedAt(),
                drill.getExpiresAt(),
                drill.getCreatedBy(),
                drill.getNote(),
                drill.getCorrelationId(),
                drill.getSourceClientId(),
                drill.getCreatedAt());
    }

    private RetentionExecutionEvidenceDto executionEvidenceDto(IncentiveRetentionOperation operation) {
        return new RetentionExecutionEvidenceDto(
                operation.getId(),
                operation.getApprovalId(),
                operation.getStatus(),
                operation.getPolicyId(),
                operation.getPolicyVersion(),
                operation.getTargetDataset(),
                operation.getTenantId(),
                operation.getApplicationId(),
                operation.getDryRunId(),
                operation.getDryRunResultHash(),
                operation.getCutoffAt(),
                operation.getExpectedEligibleCount(),
                operation.getRowsRedacted(),
                operation.getBatchLimit(),
                executionHasMore(operation),
                hash(operation.getIdempotencyKey()),
                operation.getChangeTicket(),
                operation.getRestoreDrillRef(),
                operation.getApprovedBy(),
                operation.getExecutedBy(),
                operation.getCorrelationId(),
                operation.getLastError(),
                operation.getCreatedAt(),
                operation.getStartedAt(),
                operation.getCompletedAt());
    }

    private RetentionAuditEvidenceEventDto auditEvidenceEventDto(IncentiveAuditEvent event) {
        return new RetentionAuditEvidenceEventDto(
                event.getId(),
                event.getAction(),
                event.getAggregateType(),
                event.getAggregateId(),
                event.getActorId(),
                event.getNote(),
                event.getCorrelationId(),
                event.getSourceClientId(),
                event.getCreatedAt(),
                payloadSummary(event.getPayloadJson()));
    }

    private Boolean executionHasMore(IncentiveRetentionOperation operation) {
        Object hasMore = readMap(operation.getResponseJson()).get("hasMore");
        return hasMore instanceof Boolean value ? value : null;
    }

    private String evidenceJson(RetentionEvidencePackDto pack) {
        return toJson(pack);
    }

    private String evidenceCsv(RetentionEvidencePackDto pack) {
        StringBuilder csv = new StringBuilder();
        csv.append("approvalId,status,tenantId,applicationId,policyId,policyVersion,dryRunId,approvedResultHash,executionId,executionStatus,changeTicket,restoreDrillRef,auditAction,auditActor,correlationId,createdAt,payloadSummary\n");
        for (RetentionAuditEvidenceEventDto event : pack.auditTrail()) {
            csv.append(csv(pack.approvalId())).append(',')
                    .append(csv(pack.approval().status())).append(',')
                    .append(csv(pack.approval().tenantId())).append(',')
                    .append(csv(pack.approval().applicationId())).append(',')
                    .append(csv(pack.approval().policyId())).append(',')
                    .append(csv(pack.approval().policyVersion())).append(',')
                    .append(csv(pack.approval().dryRunId())).append(',')
                    .append(csv(pack.approval().approvedResultHash())).append(',')
                    .append(csv(pack.execution() == null ? null : pack.execution().executionId())).append(',')
                    .append(csv(pack.execution() == null ? null : pack.execution().status())).append(',')
                    .append(csv(pack.approval().changeTicket())).append(',')
                    .append(csv(pack.approval().restoreDrillRef())).append(',')
                    .append(csv(event.action())).append(',')
                    .append(csv(event.actorId())).append(',')
                    .append(csv(event.correlationId())).append(',')
                    .append(csv(event.createdAt())).append(',')
                    .append(csv(toJson(event.payloadSummary())))
                    .append('\n');
        }
        return csv.toString();
    }

    private String csv(Object value) {
        String text = value == null ? "" : String.valueOf(value);
        return "\"" + text.replace("\"", "\"\"") + "\"";
    }

    private String normalizeEvidenceFormat(String format) {
        String clean = blankToNull(format);
        if (clean == null) {
            return "json";
        }
        clean = clean.toLowerCase(Locale.ROOT);
        if (!List.of("json", "csv").contains(clean)) {
            throw new BadRequestException("Unsupported retention evidence export format: " + format);
        }
        return clean;
    }

    private void auditEvidenceAccess(String action,
                                     IncentiveRetentionApproval approval,
                                     IncentiveRetentionOperation operation,
                                     Instant generatedAt,
                                     CurrentUser user,
                                     String correlationId,
                                     String format,
                                     String contentSha256,
                                     Integer includedAuditEventCount) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("approvalId", approval.getId().toString());
        payload.put("status", approval.getStatus());
        payload.put("policyId", approval.getPolicyId());
        payload.put("dryRunId", approval.getDryRunId().toString());
        payload.put("approvedResultHash", approval.getDryRunResultHash());
        payload.put("executionId", operation == null ? "" : operation.getId().toString());
        payload.put("format", format);
        payload.put("contentSha256", contentSha256 == null ? "" : contentSha256);
        payload.put("includedAuditEventCount", includedAuditEventCount == null ? "" : includedAuditEventCount);
        payload.put("changeTicket", approval.getChangeTicket());
        payload.put("restoreDrillRef", approval.getRestoreDrillRef());
        payload.put("generatedAt", generatedAt.toString());
        audit(action,
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getId().toString(),
                "retention-approval",
                actorId(user),
                approval.getReason(),
                payload,
                correlationId,
                access.sourceClientId(user));
    }

    private Map<String, Object> payloadSummary(String payloadJson) {
        Map<String, Object> payload = readMap(payloadJson);
        List<String> allowed = List.of(
                "approvalId",
                "operationId",
                "dryRunId",
                "resultHash",
                "approvedResultHash",
                "policyId",
                "policyVersion",
                "targetDataset",
                "tenantId",
                "applicationId",
                "eligibleCount",
                "eligibleCounts",
                "eligibleBefore",
                "redactedCount",
                "batchLimit",
                "hasMore",
                "changeTicket",
                "restoreDrillRef",
                "databaseName",
                "artifactHash",
                "status",
                "checkedAt",
                "expiresAt",
                "errorType",
                "error",
                "format",
                "contentSha256",
                "includedAuditEventCount",
                "filename",
                "idempotencyKeyHash");
        Map<String, Object> summary = new LinkedHashMap<>();
        for (String key : allowed) {
            if (payload.containsKey(key)) {
                summary.put(key, payload.get(key));
            }
        }
        return summary;
    }

    private Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> result = objectMapper.readValue(json, MAP_TYPE);
            return result == null ? Map.of() : result;
        } catch (JsonProcessingException ex) {
            return Map.of();
        }
    }

    private record EvidenceContext(IncentiveRetentionApproval approval,
                                   IncentiveRestoreDrill drill,
                                   IncentiveRetentionOperation operation,
                                   List<String> warnings) {
    }

    private void requireApprovalRequest(RetentionApprovalRequestDto request) {
        if (request == null) {
            throw new BadRequestException("Retention approval request is required");
        }
        requireText(request.policyId(), "policyId");
        if (request.asOf() == null) {
            throw new BadRequestException("asOf is required");
        }
        if (request.approvedDryRunId() == null) {
            throw new BadRequestException("approvedDryRunId is required");
        }
        requireText(request.approvedResultHash(), "approvedResultHash");
        requireText(request.reason(), "reason");
        requireText(request.changeTicket(), "changeTicket");
        requireText(request.restoreDrillRef(), "restoreDrillRef");
    }

    private IncentiveRetentionApproval lockApproval(UUID approvalId) {
        return approvals.lockById(approvalId)
                .orElseThrow(() -> BadRequestException.coded(
                        RETENTION_APPROVAL_NOT_FOUND,
                        "Retention approval not found"));
    }

    private IncentiveRestoreDrill requireValidRestoreDrill(String restoreDrillRef) {
        IncentiveRestoreDrill drill = restoreDrills.findByRestoreDrillRef(requireText(restoreDrillRef, "restoreDrillRef"))
                .orElseThrow(() -> ConflictException.coded(
                        RETENTION_RESTORE_DRILL_INVALID,
                        "Restore drill is not registered"));
        if (!drill.validForPromotionExecution(Instant.now())) {
            throw ConflictException.coded(
                    RETENTION_RESTORE_DRILL_INVALID,
                    "Restore drill is not valid for promotion execution");
        }
        return drill;
    }

    private void requireApprovalDecisionWindow(IncentiveRetentionApproval approval) {
        if (approval.expired(Instant.now())) {
            throw ConflictException.coded(
                    RETENTION_APPROVAL_EXPIRED,
                    "Retention approval is expired");
        }
    }

    private void validateApprovalStillCurrent(IncentiveRetentionApproval approval) {
        RetentionScope scope = new RetentionScope(approval.getTenantId(), approval.getApplicationId());
        RetentionPolicyRegistry.RetentionPolicy policy = requireExecutionPolicy(approval.getPolicyId());
        RetentionDryRunStats stats = reservations.dryRunTerminalRequestSnapshots(
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getCutoffAt());
        String policyResultHash = policyResultHash(
                policy,
                approval.getCutoffAt(),
                approval.getRetentionDays(),
                stats,
                approval.getBatchLimit());
        String resultHash = responseResultHash(scope, approval.getAsOf(), List.of(policyResultHash));
        UUID dryRunId = UUID.nameUUIDFromBytes(resultHash.getBytes(StandardCharsets.UTF_8));
        if (!resultHash.equals(approval.getDryRunResultHash()) || !dryRunId.equals(approval.getDryRunId())) {
            throw ConflictException.coded(
                    RETENTION_RESULT_HASH_MISMATCH,
                    "Retention approval dry-run no longer matches current candidates");
        }
    }

    private RetentionPolicyRegistry.RetentionPolicy requireExecutionPolicy(String policyId) {
        RetentionPolicyRegistry.RetentionPolicy policy = registry.select(List.of(policyId)).getFirst();
        if (!RetentionPolicyRegistry.TERMINAL_RESERVATION_REQUEST_SNAPSHOTS.equals(policy.policyId())) {
            throw new BadRequestException("Unsupported destructive retention execution policy: " + policy.policyId());
        }
        return policy;
    }

    private void requireAdmin(RetentionScope scope, CurrentUser user) {
        if (scope.applicationScoped()) {
            if (!isPlatformAdmin(user) && !access.canAdminAccess(scope.tenantId(), scope.applicationId(), user)) {
                throw ForbiddenException.coded(
                        RETENTION_ADMIN_FORBIDDEN,
                        "Not allowed to manage retention operation: " + scope.tenantId() + "/" + scope.applicationId());
            }
            access.requireAdminAccess(scope.tenantId(), scope.applicationId(), user);
        } else {
            requirePlatformAdmin(user);
        }
    }

    private void requireReviewer(IncentiveRetentionApproval approval, CurrentUser user) {
        if (approval.getTenantId() == null) {
            requirePlatformAdmin(user);
        } else {
            if (!isPlatformAdmin(user) && !access.canReviewAccess(approval.getTenantId(), approval.getApplicationId(), user)) {
                throw ForbiddenException.coded(
                        RETENTION_REVIEW_FORBIDDEN,
                        "Not allowed to review retention approval: "
                                + approval.getTenantId() + "/" + approval.getApplicationId());
            }
            access.requireReviewAccess(approval.getTenantId(), approval.getApplicationId(), user);
        }
    }

    private void requirePlatformAdmin(CurrentUser user) {
        if (!isPlatformAdmin(user)) {
            throw ForbiddenException.coded(
                    RETENTION_PLATFORM_ADMIN_REQUIRED,
                    "Retention global operation requires platform ADMIN role");
        }
        access.requirePlatformAdmin(user);
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasPlatformRole("ADMIN");
    }

    private void validateFreshDryRun(Instant asOf) {
        Instant now = Instant.now();
        if (asOf.isBefore(now.minus(approvalTtl))) {
            throw ConflictException.coded(
                    RETENTION_DRY_RUN_STALE,
                    "Retention dry-run is stale; run a fresh dry-run");
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

    private void auditApproval(String action,
                               IncentiveRetentionApproval approval,
                               String actorId,
                               String note,
                               String correlationId,
                               String sourceClientId) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("approvalId", approval.getId().toString());
        payload.put("status", approval.getStatus());
        payload.put("policyId", approval.getPolicyId());
        payload.put("policyVersion", approval.getPolicyVersion());
        payload.put("targetDataset", approval.getTargetDataset());
        payload.put("tenantId", Objects.toString(approval.getTenantId(), ""));
        payload.put("applicationId", Objects.toString(approval.getApplicationId(), ""));
        payload.put("dryRunId", approval.getDryRunId().toString());
        payload.put("resultHash", approval.getDryRunResultHash());
        payload.put("eligibleCount", approval.getEligibleCount());
        payload.put("batchLimit", approval.getBatchLimit());
        payload.put("restoreDrillRef", approval.getRestoreDrillRef());
        payload.put("changeTicket", approval.getChangeTicket());
        payload.put("expiresAt", approval.getExpiresAt().toString());
        audit(action, approval.getTenantId(), approval.getApplicationId(), approval.getId().toString(),
                "retention-approval", actorId, note == null ? approval.getReason() : note,
                payload, correlationId, sourceClientId);
    }

    private void audit(String action,
                       String tenantId,
                       String applicationId,
                       String aggregateId,
                       String aggregateType,
                       String actorId,
                       String note,
                       Map<String, Object> payload,
                       String correlationId,
                       String sourceClientId) {
        auditEvents.save(new IncentiveAuditEvent(
                tenantId,
                applicationId,
                aggregateId,
                aggregateType,
                action,
                actorId,
                note,
                toJson(payload),
                correlationId,
                sourceClientId));
    }

    private String normalizeRestoreStatus(String value) {
        String status = requireText(value, "status").toUpperCase(java.util.Locale.ROOT);
        if (!IncentiveRestoreDrill.STATUS_PASSED.equals(status)
                && !IncentiveRestoreDrill.STATUS_FAILED.equals(status)) {
            throw new BadRequestException("Unsupported restore drill status: " + value);
        }
        return status;
    }

    private String normalizeApprovalStatus(String value) {
        String status = blankToNull(value);
        if (status == null) {
            return null;
        }
        status = status.toUpperCase(Locale.ROOT);
        if (!List.of(
                IncentiveRetentionApproval.STATUS_PENDING,
                IncentiveRetentionApproval.STATUS_APPROVED,
                IncentiveRetentionApproval.STATUS_REJECTED,
                IncentiveRetentionApproval.STATUS_EXECUTED,
                IncentiveRetentionApproval.STATUS_EXECUTION_FAILED).contains(status)) {
            throw new BadRequestException("Unsupported retention approval status: " + value);
        }
        return status;
    }

    private String normalizeRetentionScope(String value, String tenantId, String applicationId) {
        String scope = blankToNull(value);
        if (scope == null) {
            return blankToNull(tenantId) == null && blankToNull(applicationId) == null
                    ? RETENTION_SCOPE_GLOBAL
                    : RETENTION_SCOPE_APPLICATION;
        }
        scope = scope.toUpperCase(Locale.ROOT);
        if (!RETENTION_SCOPE_APPLICATION.equals(scope) && !RETENTION_SCOPE_GLOBAL.equals(scope)) {
            throw new BadRequestException("Unsupported retention approval scopeType: " + value);
        }
        if (RETENTION_SCOPE_GLOBAL.equals(scope)
                && (blankToNull(tenantId) != null || blankToNull(applicationId) != null)) {
            throw new BadRequestException("GLOBAL retention approval queue does not accept tenantId/applicationId");
        }
        return scope;
    }

    private String containsFilter(String value) {
        String clean = blankToNull(value);
        return clean == null ? null : "%" + clean.toLowerCase(Locale.ROOT) + "%";
    }

    private String exactFilter(String value) {
        String clean = blankToNull(value);
        return clean == null ? null : clean.toLowerCase(Locale.ROOT);
    }

    private Instant min(Instant left, Instant right) {
        return left.isBefore(right) ? left : right;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Could not serialize retention approval audit payload", ex);
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
