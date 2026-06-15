package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ACCOUNT_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ACCESS_DENIED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ACCOUNT_INACTIVE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ADJUSTMENT_APPROVAL_INVALID_STATE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ADJUSTMENT_APPROVAL_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ADJUSTMENT_APPROVAL_REQUIRED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ADJUSTMENT_SELF_APPROVAL_DENIED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ENTRY_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ENTRY_NOT_REVERSIBLE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_EXPIRY_APPROVAL_MISMATCH;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_EXPIRY_APPROVAL_REQUIRED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_IDEMPOTENCY_KEY_REUSED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_IDEMPOTENCY_NOT_REPLAYABLE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_INSUFFICIENT_BALANCE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_INVALID_POINTS_DELTA;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_ALREADY_EXISTS;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_INACTIVE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_RESPONSE_NOT_REPLAYABLE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REVERSAL_WOULD_OVERDRAW;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_SOURCE_REFERENCE_REUSED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.events.common.EventMetadata;
import edu.courseflow.events.loyalty.LoyaltyPointsChangedEvent;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateAccountRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateProgramRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LedgerQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyBalanceDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyBalanceResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAccountDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAdjustmentApprovalDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyProgramDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsAdjustmentRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsEntryDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryCandidateDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryDryRunRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryDryRunResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryExecutionItemDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryExecutionRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsExpiryExecutionResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReviewLoyaltyAdjustmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitPointsAdjustmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitPointsExpiryApprovalRequestDto;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyAdjustmentApproval;
import edu.courseflow.loyalty.model.LoyaltyAuditEvent;
import edu.courseflow.loyalty.model.LoyaltyIdempotencyKey;
import edu.courseflow.loyalty.model.LoyaltyPointLot;
import edu.courseflow.loyalty.model.LoyaltyPointsEntry;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.OutboxEvent;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyAdjustmentApprovalRepository;
import edu.courseflow.loyalty.repository.LoyaltyAuditEventRepository;
import edu.courseflow.loyalty.repository.LoyaltyIdempotencyKeyRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointLotRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
import edu.courseflow.loyalty.repository.OutboxEventRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyService {

    private static final String EXPIRY_APPROVAL_OPERATION = "EXPIRY";
    private static final String REWARD_REVERSAL_APPROVAL_OPERATION = "REWARD_REDEMPTION_REVERSE";
    private static final String REWARD_FULFILLMENT_APPROVAL_OPERATION = "REWARD_FULFILLMENT_OVERRIDE";
    private static final String LOT_ALLOCATIONS_METADATA_KEY = "lotAllocations";
    private static final int IDEMPOTENCY_TTL_DAYS = 30;
    private static final long MANUAL_ADJUSTMENT_APPROVAL_THRESHOLD_POINTS = 1_000L;
    private static final Instant NO_EXPIRY = Instant.parse("9999-12-31T23:59:59Z");
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final LoyaltyProgramRepository programRepository;
    private final LoyaltyAccountRepository accountRepository;
    private final LoyaltyPointsEntryRepository pointsEntryRepository;
    private final LoyaltyPointLotRepository pointLotRepository;
    private final LoyaltyAdjustmentApprovalRepository adjustmentApprovalRepository;
    private final LoyaltyIdempotencyKeyRepository idempotencyKeyRepository;
    private final LoyaltyAuditEventRepository auditEventRepository;
    private final OutboxEventRepository outboxEventRepository;
    private final ObjectMapper objectMapper;
    private final LoyaltyMetrics metrics;
    private final LoyaltyAccessService access;
    private final LoyaltyTierService tierService;

    public LoyaltyService(
            LoyaltyProgramRepository programRepository,
            LoyaltyAccountRepository accountRepository,
            LoyaltyPointsEntryRepository pointsEntryRepository,
            LoyaltyPointLotRepository pointLotRepository,
            LoyaltyAdjustmentApprovalRepository adjustmentApprovalRepository,
            LoyaltyIdempotencyKeyRepository idempotencyKeyRepository,
            LoyaltyAuditEventRepository auditEventRepository,
            OutboxEventRepository outboxEventRepository,
            ObjectMapper objectMapper,
            LoyaltyMetrics metrics,
            LoyaltyAccessService access,
            LoyaltyTierService tierService) {
        this.programRepository = programRepository;
        this.accountRepository = accountRepository;
        this.pointsEntryRepository = pointsEntryRepository;
        this.pointLotRepository = pointLotRepository;
        this.adjustmentApprovalRepository = adjustmentApprovalRepository;
        this.idempotencyKeyRepository = idempotencyKeyRepository;
        this.auditEventRepository = auditEventRepository;
        this.outboxEventRepository = outboxEventRepository;
        this.objectMapper = objectMapper;
        this.metrics = metrics;
        this.access = access;
        this.tierService = tierService;
    }

    @Transactional
    public LoyaltyProgramDto createProgram(CreateProgramRequestDto request, CurrentUser user) {
        String tenantId = normalize(request.tenantId());
        String applicationId = normalize(request.applicationId());
        String programId = normalize(request.programId());
        access.requireAdminAccess(tenantId, applicationId, user);
        if (programRepository.existsByTenantIdAndApplicationIdAndProgramId(tenantId, applicationId, programId)) {
            throw ConflictException.coded(LOYALTY_PROGRAM_ALREADY_EXISTS, "Loyalty program already exists");
        }
        LoyaltyProgram program = programRepository.save(new LoyaltyProgram(
                tenantId,
                applicationId,
                programId,
                request.name().trim(),
                request.pointUnit(),
                Boolean.TRUE.equals(request.allowNegativeBalance()),
                request.defaultPointsExpiryDays(),
                actor(user)));
        access.replaceClientBindings(program, request.clientBindings(), user);
        audit(program.getTenantId(), program.getApplicationId(), program.getId().toString(), "loyalty-program",
                "loyalty.program.created", actor(user), null, null, json(Map.of(
                        "programId", program.getProgramId(),
                        "pointUnit", program.getPointUnit())));
        return toProgramDto(program);
    }

    @Transactional
    public LoyaltyAccountDto createAccount(CreateAccountRequestDto request, CurrentUser user) {
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        requireActiveProgram(program);
        access.requireAdjustmentAccess(program.getTenantId(), program.getApplicationId(), user);
        LoyaltyAccount account = accountRepository
                .findByTenantIdAndApplicationIdAndProgramIdAndProfileId(
                        program.getTenantId(), program.getApplicationId(), program.getProgramId(), normalize(request.profileId()))
                .orElseGet(() -> accountRepository.save(new LoyaltyAccount(program, normalize(request.profileId()))));
        tierService.evaluateAfterPointsMutation(account, actor(user), "Loyalty account opened", null);
        return toAccountDto(account);
    }

    @Transactional(readOnly = true)
    public LoyaltyAccountDto account(UUID accountId, CurrentUser user) {
        LoyaltyAccount account = accountRepository.findById(accountId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        LoyaltyProgram program = programFor(account);
        requireActiveProgram(program);
        requireActiveAccount(account);
        access.requireProgramReadAccess(program, user);
        return toAccountDto(account);
    }

    @Transactional(readOnly = true)
    public LoyaltyAccountDto account(
            String tenantId, String applicationId, String programId, String profileId, CurrentUser user) {
        LoyaltyProgram program = requireProgram(tenantId, applicationId, programId);
        requireActiveProgram(program);
        access.requireProgramReadAccess(program, user);
        LoyaltyAccount account = accountRepository.findByTenantIdAndApplicationIdAndProgramIdAndProfileId(
                        normalize(tenantId), normalize(applicationId), normalize(programId), normalize(profileId))
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        requireActiveAccount(account);
        return toAccountDto(account);
    }

    @Transactional
    public PointsMutationResponseDto earn(PointsMutationRequestDto request, CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            PointsMutationResponseDto response = mutate("EARN", request, Math.abs(request.points()), true, user);
            metrics.mutation("earn", response.idempotencyReplay() ? "replay" : "success", "ok", elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.mutation("earn", "error", errorReason(ex), elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public PointsMutationResponseDto burn(PointsMutationRequestDto request, CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            PointsMutationResponseDto response = mutate("BURN", request, -Math.abs(request.points()), false, user);
            metrics.mutation("burn", response.idempotencyReplay() ? "replay" : "success", "ok", elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.mutation("burn", "error", errorReason(ex), elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public PointsMutationResponseDto redeemRewardBurn(PointsMutationRequestDto request, CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            PointsMutationResponseDto response = mutateLearnerRewardBurn(request, user);
            metrics.mutation(
                    "reward_redeem",
                    response.idempotencyReplay() ? "replay" : "success",
                    "ok",
                    elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.mutation("reward_redeem", "error", errorReason(ex), elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public PointsMutationResponseDto reverse(UUID entryId, ReversePointsRequestDto request, CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            PointsMutationResponseDto response = reverseInternal(entryId, request, user, false);
            metrics.mutation("reverse", response.idempotencyReplay() ? "replay" : "success", "ok", elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.mutation("reverse", "error", errorReason(ex), elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public PointsMutationResponseDto reverseRewardBurn(UUID entryId, ReversePointsRequestDto request, CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            PointsMutationResponseDto response = reverseInternal(entryId, request, user, true);
            metrics.mutation(
                    "reward_redeem_reverse",
                    response.idempotencyReplay() ? "replay" : "success",
                    "ok",
                    elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.mutation("reward_redeem_reverse", "error", errorReason(ex), elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public PointsMutationResponseDto reverseBySourceReference(
            String tenantId,
            String applicationId,
            String programId,
            String sourceReference,
            ReversePointsRequestDto request,
            CurrentUser user) {
        LoyaltyProgram program = requireProgram(tenantId, applicationId, programId);
        LoyaltyPointsEntry original = pointsEntryRepository
                .findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
                        program.getId(), "EARN", normalize(sourceReference))
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_ENTRY_NOT_FOUND,
                        "Original loyalty earn entry was not found for source reference"));
        return reverse(original.getId(), request, user);
    }

    @Transactional
    public PointsMutationResponseDto adjust(PointsAdjustmentRequestDto request, CurrentUser user) {
        long startedNanos = System.nanoTime();
        try {
            PointsMutationResponseDto response = adjustInternal(request, user, false);
            metrics.mutation("adjust", response.idempotencyReplay() ? "replay" : "success", "ok", elapsed(startedNanos));
            return response;
        } catch (RuntimeException ex) {
            metrics.mutation("adjust", "error", errorReason(ex), elapsed(startedNanos));
            throw ex;
        }
    }

    @Transactional
    public LoyaltyAdjustmentApprovalDto submitAdjustmentApproval(
            SubmitPointsAdjustmentApprovalRequestDto request,
            CurrentUser user) {
        long pointsDelta = request.pointsDelta() == null ? 0L : request.pointsDelta();
        if (pointsDelta == 0L) {
            throw BadRequestException.coded(LOYALTY_INVALID_POINTS_DELTA, "Adjustment pointsDelta must not be zero");
        }
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        requireActiveProgram(program);
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        Map<String, Object> hashPayload = new LinkedHashMap<>();
        hashPayload.put("operation", "ADJUSTMENT_APPROVAL");
        hashPayload.put("tenantId", program.getTenantId());
        hashPayload.put("applicationId", program.getApplicationId());
        hashPayload.put("programId", program.getProgramId());
        hashPayload.put("profileId", normalize(request.profileId()));
        hashPayload.put("pointsDelta", pointsDelta);
        hashPayload.put("sourceReference", normalize(request.sourceReference()));
        hashPayload.put("idempotencyKey", normalize(request.idempotencyKey()));
        hashPayload.put("reason", request.reason());
        hashPayload.put("correlationId", request.correlationId());
        hashPayload.put("occurredAt", request.occurredAt());
        hashPayload.put("expiresAt", request.expiresAt());
        hashPayload.put("metadata", request.metadata());
        LoyaltyAdjustmentApproval approval = adjustmentApprovalRepository.save(new LoyaltyAdjustmentApproval(
                program.getTenantId(),
                program.getApplicationId(),
                program.getProgramId(),
                normalize(request.profileId()),
                pointsDelta,
                normalize(request.sourceReference()),
                normalize(request.idempotencyKey()),
                request.reason(),
                normalize(request.correlationId()),
                request.occurredAt(),
                request.expiresAt(),
                json(request.metadata()),
                hash(hashPayload),
                actor(user)));
        audit(program.getTenantId(), program.getApplicationId(), approval.getId().toString(),
                "loyalty-adjustment-approval", "loyalty.adjustment_approval.requested",
                actor(user), request.reason(), request.correlationId(), json(Map.of(
                        "programId", program.getProgramId(),
                        "profileId", approval.getProfileId(),
                        "pointsDelta", pointsDelta,
                        "threshold", MANUAL_ADJUSTMENT_APPROVAL_THRESHOLD_POINTS)));
        return toApprovalDto(approval);
    }

    @Transactional
    public LoyaltyAdjustmentApprovalDto submitExpiryApproval(
            SubmitPointsExpiryApprovalRequestDto request,
            CurrentUser user) {
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        requireActiveProgram(program);
        int pageSize = expiryPageSize(request.limit());
        PointsExpiryDryRunResponseDto dryRun = expiryDryRunInternal(
                program,
                new PointsExpiryDryRunRequestDto(
                        program.getTenantId(),
                        program.getApplicationId(),
                        program.getProgramId(),
                        request.asOf(),
                        pageSize));
        if (!request.resultHash().equals(dryRun.resultHash())) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_MISMATCH,
                    "Expiry approval dry-run result hash no longer matches current candidates");
        }
        if (dryRun.expiringPoints() <= 0 || dryRun.candidateEntryCount() == 0) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_REQUIRED,
                    "Expiry approval requires at least one expiring point lot");
        }
        if (dryRun.warnings().contains("DRY_RUN_FALLBACK_GROSS_LEDGER_CANDIDATES_NO_MATERIALIZED_LOTS")) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_REQUIRED,
                    "Backfill point lots before submitting expiry approval");
        }
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("operationType", EXPIRY_APPROVAL_OPERATION);
        metadata.put("asOf", request.asOf().toString());
        metadata.put("limit", pageSize);
        metadata.put("resultHash", dryRun.resultHash());
        metadata.put("candidateEntryCount", dryRun.candidateEntryCount());
        metadata.put("affectedAccountCount", dryRun.affectedAccountCount());
        metadata.put("expiringPoints", dryRun.expiringPoints());
        metadata.put("warnings", dryRun.warnings());
        String sourceReference = "expiry:" + program.getProgramId() + ":" + dryRun.resultHash().substring(0, 24);
        LoyaltyAdjustmentApproval approval = adjustmentApprovalRepository.save(new LoyaltyAdjustmentApproval(
                program.getTenantId(),
                program.getApplicationId(),
                program.getProgramId(),
                "*",
                -dryRun.expiringPoints(),
                sourceReference,
                request.idempotencyKey(),
                request.reason(),
                request.correlationId(),
                request.asOf(),
                null,
                json(metadata),
                expiryApprovalHash(program, request.asOf(), pageSize, dryRun.resultHash()),
                actor(user)));
        audit(program.getTenantId(), program.getApplicationId(), approval.getId().toString(),
                "loyalty-expiry-approval", "loyalty.expiry_approval.requested",
                actor(user), request.reason(), request.correlationId(), json(metadata));
        return toApprovalDto(approval);
    }

    @Transactional
    public LoyaltyAdjustmentApprovalDto approveAdjustmentApproval(
            UUID approvalId,
            ReviewLoyaltyAdjustmentApprovalRequestDto request,
            CurrentUser user) {
        LoyaltyAdjustmentApproval approval = adjustmentApprovalRepository.findByIdForUpdate(approvalId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_ADJUSTMENT_APPROVAL_NOT_FOUND,
                        "Loyalty adjustment approval not found"));
        access.requireAdjustmentReviewAccess(approval.getTenantId(), approval.getApplicationId(), user);
        String reviewer = actor(user);
        if (reviewer != null && reviewer.equalsIgnoreCase(approval.getRequestedBy())) {
            throw ForbiddenException.coded(
                    LOYALTY_ADJUSTMENT_SELF_APPROVAL_DENIED,
                    "Requester cannot approve their own loyalty operation");
        }
        try {
            approval.approve(reviewer, request.note());
            if (isExpiryApproval(approval)) {
                audit(approval.getTenantId(), approval.getApplicationId(), approval.getId().toString(),
                        "loyalty-expiry-approval", "loyalty.expiry_approval.approved",
                        reviewer, request.note(), approval.getCorrelationId(), json(approvalMetadata(approval)));
                return toApprovalDto(approval);
            }
            if (isRewardReversalApproval(approval)) {
                audit(approval.getTenantId(), approval.getApplicationId(), approval.getId().toString(),
                        "loyalty-reward-reversal-approval", "loyalty.reward_reversal_approval.approved",
                        reviewer, request.note(), approval.getCorrelationId(), json(approvalMetadata(approval)));
                return toApprovalDto(approval);
            }
            if (isRewardFulfillmentApproval(approval)) {
                audit(approval.getTenantId(), approval.getApplicationId(), approval.getId().toString(),
                        "loyalty-reward-fulfillment-approval", "loyalty.reward_fulfillment_approval.approved",
                        reviewer, request.note(), approval.getCorrelationId(), json(approvalMetadata(approval)));
                return toApprovalDto(approval);
            }
            PointsMutationResponseDto response = adjustInternal(approvalRequest(approval), user, true);
            approval.markExecuted(response.entryId());
        } catch (IllegalStateException ex) {
            throw ConflictException.coded(LOYALTY_ADJUSTMENT_APPROVAL_INVALID_STATE, ex.getMessage());
        }
        audit(approval.getTenantId(), approval.getApplicationId(), approval.getId().toString(),
                "loyalty-adjustment-approval", "loyalty.adjustment_approval.executed",
                reviewer, request.note(), approval.getCorrelationId(), json(Map.of(
                        "programId", approval.getProgramId(),
                        "profileId", approval.getProfileId(),
                        "pointsDelta", approval.getPointsDelta(),
                        "executedEntryId", String.valueOf(approval.getExecutedEntryId()))));
        return toApprovalDto(approval);
    }

    @Transactional
    public LoyaltyAdjustmentApprovalDto rejectAdjustmentApproval(
            UUID approvalId,
            ReviewLoyaltyAdjustmentApprovalRequestDto request,
            CurrentUser user) {
        LoyaltyAdjustmentApproval approval = adjustmentApprovalRepository.findByIdForUpdate(approvalId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_ADJUSTMENT_APPROVAL_NOT_FOUND,
                        "Loyalty adjustment approval not found"));
        access.requireAdjustmentReviewAccess(approval.getTenantId(), approval.getApplicationId(), user);
        try {
            approval.reject(actor(user), request.note());
        } catch (IllegalStateException ex) {
            throw ConflictException.coded(LOYALTY_ADJUSTMENT_APPROVAL_INVALID_STATE, ex.getMessage());
        }
        String aggregateType = approvalAggregateType(approval);
        String action = approvalRejectedAction(approval);
        audit(approval.getTenantId(), approval.getApplicationId(), approval.getId().toString(),
                aggregateType, action,
                actor(user), request.note(), approval.getCorrelationId(), json(Map.of(
                        "programId", approval.getProgramId(),
                        "profileId", approval.getProfileId(),
                        "pointsDelta", approval.getPointsDelta())));
        return toApprovalDto(approval);
    }

    @Transactional(readOnly = true)
    public PointsExpiryDryRunResponseDto expiryDryRun(PointsExpiryDryRunRequestDto request, CurrentUser user) {
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        return expiryDryRunInternal(program, request);
    }

    private PointsExpiryDryRunResponseDto expiryDryRunInternal(
            LoyaltyProgram program,
            PointsExpiryDryRunRequestDto request) {
        int pageSize = expiryPageSize(request.limit());
        List<LoyaltyPointLot> lotCandidates = pointLotRepository.expiryCandidates(
                program.getId(), request.asOf(), PageRequest.of(0, pageSize + 1));
        if (!lotCandidates.isEmpty()) {
            boolean limited = lotCandidates.size() > pageSize;
            List<LoyaltyPointLot> page = lotCandidates.stream().limit(pageSize).toList();
            long expiringPoints = page.stream().mapToLong(LoyaltyPointLot::getRemainingPoints).sum();
            int affectedAccounts = page.stream()
                    .map(LoyaltyPointLot::getAccountId)
                    .collect(java.util.stream.Collectors.toSet())
                    .size();
            List<PointsExpiryCandidateDto> samples = page.stream()
                    .limit(50)
                    .map(lot -> new PointsExpiryCandidateDto(
                            lot.getSourceEntryId(),
                            lot.getAccountId(),
                            lot.getProfileId(),
                            lot.getRemainingPoints(),
                            lot.getSourceReference(),
                            lot.getOccurredAt(),
                            lot.getExpiresAt()))
                    .toList();
            List<String> warnings = limited
                    ? List.of("RESULT_LIMIT_REACHED", "DRY_RUN_USES_MATERIALIZED_REMAINING_LOTS")
                    : List.of("DRY_RUN_USES_MATERIALIZED_REMAINING_LOTS");
            return new PointsExpiryDryRunResponseDto(
                    program.getTenantId(),
                    program.getApplicationId(),
                    program.getProgramId(),
                    request.asOf(),
                    page.size(),
                    affectedAccounts,
                    expiringPoints,
                    expiryLotResultHash(program, request.asOf(), page, expiringPoints),
                    samples,
                    warnings);
        }
        List<LoyaltyPointsEntry> candidates = pointsEntryRepository.expiryCandidates(
                program.getId(), request.asOf(), PageRequest.of(0, pageSize + 1));
        boolean limited = candidates.size() > pageSize;
        List<LoyaltyPointsEntry> page = candidates.stream().limit(pageSize).toList();
        long expiringPoints = page.stream().mapToLong(LoyaltyPointsEntry::getPointsDelta).sum();
        int affectedAccounts = page.stream().map(LoyaltyPointsEntry::getAccountId).collect(java.util.stream.Collectors.toSet()).size();
        List<PointsExpiryCandidateDto> samples = page.stream()
                .limit(50)
                .map(entry -> new PointsExpiryCandidateDto(
                        entry.getId(),
                        entry.getAccountId(),
                        entry.getProfileId(),
                        entry.getPointsDelta(),
                        entry.getSourceReference(),
                        entry.getOccurredAt(),
                        entry.getExpiresAt()))
                .toList();
        List<String> warnings = limited
                ? List.of("RESULT_LIMIT_REACHED", "DRY_RUN_FALLBACK_GROSS_LEDGER_CANDIDATES_NO_MATERIALIZED_LOTS")
                : List.of("DRY_RUN_FALLBACK_GROSS_LEDGER_CANDIDATES_NO_MATERIALIZED_LOTS");
        return new PointsExpiryDryRunResponseDto(
                program.getTenantId(),
                program.getApplicationId(),
                program.getProgramId(),
                request.asOf(),
                page.size(),
                affectedAccounts,
                expiringPoints,
                expiryEntryResultHash(program, request.asOf(), page, expiringPoints),
                samples,
                warnings);
    }

    @Transactional
    public PointsExpiryExecutionResponseDto executeExpiry(PointsExpiryExecutionRequestDto request, CurrentUser user) {
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        requireActiveProgram(program);
        int pageSize = expiryPageSize(request.limit());
        LoyaltyAdjustmentApproval approval = requireApprovedExpiryApproval(request, program);
        String requestHash = hash(Map.of(
                "operation", "EXPIRE",
                "tenantId", program.getTenantId(),
                "applicationId", program.getApplicationId(),
                "programId", program.getProgramId(),
                "asOf", request.asOf(),
                "limit", pageSize,
                "approvalId", approval.getId().toString(),
                "reason", request.reason(),
                "correlationId", request.correlationId()));
        PointsExpiryExecutionResponseDto replay = replayExpiryFromIdempotency(
                program.getTenantId(), program.getApplicationId(), request.idempotencyKey(), requestHash);
        if (replay != null) {
            return replay;
        }
        if ("EXECUTED".equals(approval.getStatus())) {
            throw ConflictException.coded(
                    LOYALTY_ADJUSTMENT_APPROVAL_INVALID_STATE,
                    "Expiry approval has already been executed");
        }
        List<LoyaltyPointLot> candidates = pointLotRepository.expiryCandidates(
                program.getId(), request.asOf(), PageRequest.of(0, pageSize + 1));
        boolean limited = candidates.size() > pageSize;
        List<LoyaltyPointLot> candidatePage = candidates.stream().limit(pageSize).toList();
        Map<UUID, LoyaltyAccount> lockedAccounts = new LinkedHashMap<>();
        candidatePage.stream()
                .map(LoyaltyPointLot::getAccountId)
                .distinct()
                .sorted(Comparator.comparing(UUID::toString))
                .forEach(accountId -> {
                    LoyaltyAccount account = accountRepository.findByIdForUpdate(accountId)
                            .orElseThrow(() -> NotFoundException.coded(
                                    LOYALTY_ACCOUNT_NOT_FOUND,
                                    "Loyalty account not found"));
                    requireActiveAccount(account);
                    lockedAccounts.put(account.getId(), account);
                });
        List<UUID> candidateLotIds = candidatePage.stream().map(LoyaltyPointLot::getId).toList();
        List<LoyaltyPointLot> page = candidateLotIds.isEmpty()
                ? List.of()
                : pointLotRepository.findByIdsForUpdate(candidateLotIds)
                .stream()
                .filter(lot -> program.getId().equals(lot.getProgramUuid()))
                .filter(lot -> lot.getRemainingPoints() > 0)
                .filter(lot -> lot.getExpiresAt() != null && !lot.getExpiresAt().isAfter(request.asOf()))
                .sorted(pointLotComparator())
                .toList();
        long candidatePoints = page.stream().mapToLong(LoyaltyPointLot::getRemainingPoints).sum();
        String approvedResultHash = requiredString(approvalMetadata(approval), "resultHash");
        String currentResultHash = expiryLotResultHash(program, request.asOf(), page, candidatePoints);
        if (!approvedResultHash.equals(currentResultHash)) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_MISMATCH,
                    "Approved expiry candidate set no longer matches current remaining lots");
        }
        List<PointsExpiryExecutionItemDto> items = new ArrayList<>();
        for (LoyaltyPointLot lot : page) {
            long remaining = lot.getRemainingPoints();
            if (remaining <= 0) {
                continue;
            }
            LoyaltyAccount account = lockedAccounts.get(lot.getAccountId());
            if (account == null) {
                throw NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found");
            }
            String sourceReference = "expire:" + lot.getSourceEntryId() + ":" + request.asOf();
            String entryHash = hash(Map.of(
                    "operation", "EXPIRE_LOT",
                    "lotId", lot.getId().toString(),
                    "sourceEntryId", lot.getSourceEntryId().toString(),
                    "asOf", request.asOf(),
                    "points", remaining));
            LoyaltyPointsEntry entry = pointsEntryRepository.save(new LoyaltyPointsEntry(
                    account,
                    "EXPIRE",
                    -remaining,
                    sourceReference,
                    entryHash,
                    null,
                    request.reason(),
                    request.correlationId(),
                    json(Map.of(
                            "sourceLotId", lot.getId().toString(),
                            "sourceEntryId", lot.getSourceEntryId().toString(),
                            "expiryAsOf", request.asOf().toString(),
                            LOT_ALLOCATIONS_METADATA_KEY, List.of(lotAllocationMap(lot, remaining)))),
                    Instant.now(),
                    null));
            lot.consume(remaining);
            writeSideEffects(entry, program.getPointUnit(), actor(user), request.reason(), request.correlationId());
            tierService.evaluateAfterPointsMutation(account, actor(user), request.reason(), request.correlationId());
            items.add(new PointsExpiryExecutionItemDto(
                    entry.getId(),
                    account.getId(),
                    lot.getId(),
                    lot.getSourceEntryId(),
                    account.getProfileId(),
                    remaining,
                    lot.getSourceReference(),
                    lot.getExpiresAt()));
        }
        List<String> warnings = limited ? List.of("RESULT_LIMIT_REACHED") : List.of();
        PointsExpiryExecutionResponseDto response = new PointsExpiryExecutionResponseDto(
                program.getTenantId(),
                program.getApplicationId(),
                program.getProgramId(),
                request.asOf(),
                items.size(),
                items.stream().map(PointsExpiryExecutionItemDto::accountId).collect(java.util.stream.Collectors.toSet()).size(),
                items.stream().mapToLong(PointsExpiryExecutionItemDto::expiredPoints).sum(),
                false,
                items,
                warnings);
        rememberExpiryIdempotency(program.getTenantId(), program.getApplicationId(),
                request.idempotencyKey(), requestHash, response);
        try {
            UUID firstEntryId = items.isEmpty() ? null : items.get(0).entryId();
            approval.markExecuted(firstEntryId);
        } catch (IllegalStateException ex) {
            throw ConflictException.coded(LOYALTY_ADJUSTMENT_APPROVAL_INVALID_STATE, ex.getMessage());
        }
        audit(program.getTenantId(), program.getApplicationId(), approval.getId().toString(),
                "loyalty-expiry-approval", "loyalty.expiry_approval.executed",
                actor(user), request.reason(), request.correlationId(), json(Map.of(
                        "programId", program.getProgramId(),
                        "asOf", request.asOf().toString(),
                        "expiredLotCount", response.expiredLotCount(),
                        "expiredPoints", response.expiredPoints())));
        return response;
    }

    private LoyaltyAdjustmentApproval requireApprovedExpiryApproval(
            PointsExpiryExecutionRequestDto request,
            LoyaltyProgram program) {
        if (request.approvalId() == null) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_REQUIRED,
                    "Expiry execution requires an approved approvalId");
        }
        LoyaltyAdjustmentApproval approval = adjustmentApprovalRepository.findByIdForUpdate(request.approvalId())
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_ADJUSTMENT_APPROVAL_NOT_FOUND,
                        "Loyalty expiry approval not found"));
        if (!isExpiryApproval(approval)) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_MISMATCH,
                    "Approval is not for loyalty expiry execution");
        }
        if (!program.getTenantId().equals(approval.getTenantId())
                || !program.getApplicationId().equals(approval.getApplicationId())
                || !program.getProgramId().equals(approval.getProgramId())) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_MISMATCH,
                    "Expiry approval scope does not match execution request");
        }
        Map<String, Object> metadata = approvalMetadata(approval);
        int pageSize = expiryPageSize(request.limit());
        String expectedHash = expiryApprovalHash(program, request.asOf(), pageSize, requiredString(metadata, "resultHash"));
        if (!expectedHash.equals(approval.getRequestHash())
                || !request.asOf().toString().equals(requiredString(metadata, "asOf"))
                || pageSize != requiredInt(metadata, "limit")
                || !request.idempotencyKey().equals(approval.getIdempotencyKey())) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_MISMATCH,
                    "Expiry approval request no longer matches execution request");
        }
        if (!"APPROVED".equals(approval.getStatus()) && !"EXECUTED".equals(approval.getStatus())) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_REQUIRED,
                    "Expiry execution requires an approved approval");
        }
        return approval;
    }

    private int expiryPageSize(Integer requestedLimit) {
        return Math.max(1, Math.min(requestedLimit == null ? 100 : requestedLimit, 500));
    }

    private String expiryLotResultHash(
            LoyaltyProgram program,
            Instant asOf,
            List<LoyaltyPointLot> page,
            long expiringPoints) {
        Map<String, Object> hashPayload = new LinkedHashMap<>();
        hashPayload.put("tenantId", program.getTenantId());
        hashPayload.put("applicationId", program.getApplicationId());
        hashPayload.put("programId", program.getProgramId());
        hashPayload.put("asOf", asOf);
        hashPayload.put("sourceLotIds", page.stream().map(lot -> lot.getId().toString()).toList());
        hashPayload.put("expiringPoints", expiringPoints);
        return hash(hashPayload);
    }

    private String expiryEntryResultHash(
            LoyaltyProgram program,
            Instant asOf,
            List<LoyaltyPointsEntry> page,
            long expiringPoints) {
        Map<String, Object> hashPayload = new LinkedHashMap<>();
        hashPayload.put("tenantId", program.getTenantId());
        hashPayload.put("applicationId", program.getApplicationId());
        hashPayload.put("programId", program.getProgramId());
        hashPayload.put("asOf", asOf);
        hashPayload.put("candidateEntryIds", page.stream().map(entry -> entry.getId().toString()).toList());
        hashPayload.put("expiringPoints", expiringPoints);
        return hash(hashPayload);
    }

    private String expiryApprovalHash(
            LoyaltyProgram program,
            Instant asOf,
            int pageSize,
            String resultHash) {
        return hash(Map.of(
                "operation", EXPIRY_APPROVAL_OPERATION,
                "tenantId", program.getTenantId(),
                "applicationId", program.getApplicationId(),
                "programId", program.getProgramId(),
                "asOf", asOf,
                "limit", pageSize,
                "resultHash", resultHash));
    }

    private PointsMutationResponseDto reverseInternal(
            UUID entryId,
            ReversePointsRequestDto request,
            CurrentUser user,
            boolean allowAdminReverse) {
        LoyaltyPointsEntry original = pointsEntryRepository.findById(entryId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ENTRY_NOT_FOUND, "Loyalty points entry not found"));
        LoyaltyProgram program = programRepository.findById(original.getProgramUuid())
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_PROGRAM_NOT_FOUND, "Loyalty program not found"));
        if (allowAdminReverse && !"BURN".equals(original.getEntryType())) {
            throw ConflictException.coded(
                    LOYALTY_ENTRY_NOT_REVERSIBLE,
                    "Reward redemption support can only reverse loyalty burn entries");
        }
        if (allowAdminReverse) {
            access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        } else {
            access.requireRuntimeOperation(program, user, "reverse");
        }
        String operationType = allowAdminReverse ? "REWARD_REDEEM_REVERSE" : "REVERSE";
        String requestHash = hash(Map.of("operation", operationType, "entryId", entryId.toString(), "request", request));
        PointsMutationResponseDto replay = replayFromIdempotency(
                original.getTenantId(), original.getApplicationId(), operationType, request.idempotencyKey(), requestHash);
        if (replay != null) {
            return replay;
        }
        requireActiveProgram(program);
        LoyaltyAccount account = accountRepository.findByIdForUpdate(original.getAccountId())
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        requireActiveAccount(account);
        if ("REVERSE".equals(original.getEntryType())) {
            throw ConflictException.coded(LOYALTY_ENTRY_NOT_REVERSIBLE, "Reversal entries cannot be reversed");
        }

        LoyaltyPointsEntry existingReverse = pointsEntryRepository.findFirstByReversalOfEntryId(entryId).orElse(null);
        if (existingReverse != null) {
            PointsMutationResponseDto response = toMutationResponse(existingReverse,
                    pointsEntryRepository.balance(existingReverse.getAccountId()), true);
            rememberIdempotency(original.getTenantId(), original.getApplicationId(), operationType,
                    request.idempotencyKey(), requestHash, response);
            return response;
        }

        long balanceBefore = pointsEntryRepository.balance(account.getId());
        long spendableBefore = spendablePoints(account.getId(), Instant.now());
        long reverseDelta = -original.getPointsDelta();
        if (original.getPointsDelta() > 0
                && !program.isAllowNegativeBalance()
                && spendableBefore < original.getPointsDelta()) {
            throw ConflictException.coded(LOYALTY_REVERSAL_WOULD_OVERDRAW,
                    "Reversing the earn entry would overdraw active loyalty points");
        }

        LoyaltyPointsEntry reversal = pointsEntryRepository.save(new LoyaltyPointsEntry(
                account,
                "REVERSE",
                reverseDelta,
                "reverse:" + entryId,
                requestHash,
                entryId,
                request.reason(),
                request.correlationId(),
                json(request.metadata()),
                Instant.now(),
                null));
        if (original.getPointsDelta() < 0 && hasLotAllocations(original)) {
            restoreLotAllocations(original);
        } else {
            applyLotMutation(reversal, !program.isAllowNegativeBalance());
        }
        long balanceAfter = balanceBefore + reverseDelta;
        writeSideEffects(reversal, program.getPointUnit(), actor(user), request.reason(), request.correlationId());
        tierService.evaluateAfterPointsMutation(account, actor(user), request.reason(), request.correlationId());
        PointsMutationResponseDto response = toMutationResponse(reversal, balanceAfter, false);
        rememberIdempotency(original.getTenantId(), original.getApplicationId(), operationType,
                request.idempotencyKey(), requestHash, response);
        return response;
    }

    private PointsMutationResponseDto adjustInternal(
            PointsAdjustmentRequestDto request,
            CurrentUser user,
            boolean bypassApprovalGate) {
        long pointsDelta = request.pointsDelta() == null ? 0L : request.pointsDelta();
        if (pointsDelta == 0L) {
            throw BadRequestException.coded(LOYALTY_INVALID_POINTS_DELTA, "Adjustment pointsDelta must not be zero");
        }
        if (!bypassApprovalGate && Math.abs(pointsDelta) >= MANUAL_ADJUSTMENT_APPROVAL_THRESHOLD_POINTS) {
            throw ConflictException.coded(
                    LOYALTY_ADJUSTMENT_APPROVAL_REQUIRED,
                    "Manual loyalty adjustments at or above "
                            + MANUAL_ADJUSTMENT_APPROVAL_THRESHOLD_POINTS
                            + " points require maker-checker approval");
        }
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        String requestHash = hash(Map.of(
                "operation", "ADJUST",
                "pointsDelta", pointsDelta,
                "request", request));
        PointsMutationResponseDto replay = replayFromIdempotency(
                program.getTenantId(), program.getApplicationId(), "ADJUST", request.idempotencyKey(), requestHash);
        if (replay != null) {
            return replay;
        }
        requireActiveProgram(program);
        String normalizedProfileId = normalize(request.profileId());
        Optional<LoyaltyAccount> existingAccount = accountRepository.findByScopeForUpdate(
                program.getTenantId(), program.getApplicationId(), program.getProgramId(), normalizedProfileId);
        existingAccount.ifPresent(this::requireActiveAccount);

        LoyaltyPointsEntry existingSource = pointsEntryRepository
                .findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
                        program.getId(), "ADJUST", normalize(request.sourceReference()))
                .orElse(null);
        if (existingSource != null) {
            if (!existingSource.getSourceRequestHash().equals(requestHash)) {
                metrics.sourceReference("ADJUST", "payload_conflict");
                throw ConflictException.coded(LOYALTY_SOURCE_REFERENCE_REUSED,
                        "Loyalty source reference was reused with a different adjustment");
            }
            PointsMutationResponseDto response = toMutationResponse(
                    existingSource, pointsEntryRepository.balance(existingSource.getAccountId()), true);
            rememberIdempotency(program.getTenantId(), program.getApplicationId(), "ADJUST",
                    request.idempotencyKey(), requestHash, response);
            metrics.sourceReference("ADJUST", "replay");
            return response;
        }

        LoyaltyAccount account = existingAccount
                .orElseGet(() -> createOrRefetchMutationAccount(program, normalizedProfileId, pointsDelta > 0));
        requireActiveAccount(account);
        long balanceBefore = pointsEntryRepository.balance(account.getId());
        long spendableBefore = spendablePoints(account.getId(), Instant.now());
        if (pointsDelta < 0 && !program.isAllowNegativeBalance() && spendableBefore < Math.abs(pointsDelta)) {
            throw ConflictException.coded(
                    LOYALTY_INSUFFICIENT_BALANCE,
                    "Loyalty account has insufficient active points");
        }

        LoyaltyPointsEntry entry = pointsEntryRepository.save(new LoyaltyPointsEntry(
                account,
                "ADJUST",
                pointsDelta,
                normalize(request.sourceReference()),
                requestHash,
                null,
                request.reason(),
                request.correlationId(),
                json(request.metadata()),
                request.occurredAt(),
                effectiveExpiry(program, request.occurredAt(), request.expiresAt(), pointsDelta)));
        applyLotMutation(entry, !program.isAllowNegativeBalance());
        long balanceAfter = balanceBefore + pointsDelta;
        writeSideEffects(entry, program.getPointUnit(), actor(user), request.reason(), request.correlationId());
        tierService.evaluateAfterPointsMutation(account, actor(user), request.reason(), request.correlationId());
        PointsMutationResponseDto response = toMutationResponse(entry, balanceAfter, false);
        rememberIdempotency(program.getTenantId(), program.getApplicationId(), "ADJUST",
                request.idempotencyKey(), requestHash, response);
        return response;
    }

    @Transactional(readOnly = true)
    public LedgerQueryResponseDto ledger(UUID accountId, CurrentUser user) {
        LoyaltyAccount account = accountRepository.findById(accountId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        LoyaltyProgram program = programFor(account);
        requireActiveProgram(program);
        requireActiveAccount(account);
        access.requireProgramReadAccess(program, user);
        List<PointsEntryDto> items = pointsEntryRepository.findTop100ByAccountIdOrderByCreatedAtDesc(accountId)
                .stream()
                .map(this::toEntryDto)
                .toList();
        return new LedgerQueryResponseDto(
                account.getId(),
                account.getTenantId(),
                account.getApplicationId(),
                account.getProgramId(),
                account.getProfileId(),
                pointsEntryRepository.balance(account.getId()),
                items);
    }

    @Transactional(readOnly = true)
    public LearnerLoyaltyBalanceResponseDto learnerBalances(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            CurrentUser user) {
        requireAuthenticated(user);
        String profileId = String.valueOf(user.id());
        Instant generatedAt = Instant.now();
        List<LearnerLoyaltyBalanceDto> items = accountRepository.search(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(programId.orElse(null)),
                        profileId,
                        null,
                        PageRequest.of(0, 50))
                .stream()
                .map(account -> learnerBalance(account, generatedAt))
                .toList();
        return new LearnerLoyaltyBalanceResponseDto(profileId, generatedAt, items);
    }

    private PointsMutationResponseDto mutate(String entryType, PointsMutationRequestDto request, long pointsDelta,
                                             boolean createMissingAccount, CurrentUser user) {
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        access.requireRuntimeOperation(program, user, operationName(entryType));
        String requestHash = hash(Map.of("operation", entryType, "request", request));
        PointsMutationResponseDto replay = replayFromIdempotency(
                program.getTenantId(), program.getApplicationId(), entryType, request.idempotencyKey(), requestHash);
        if (replay != null) {
            return replay;
        }
        requireActiveProgram(program);
        String normalizedProfileId = normalize(request.profileId());
        Optional<LoyaltyAccount> existingAccount = accountRepository.findByScopeForUpdate(
                program.getTenantId(), program.getApplicationId(), program.getProgramId(), normalizedProfileId);
        existingAccount.ifPresent(this::requireActiveAccount);

        LoyaltyPointsEntry existingSource = pointsEntryRepository
                .findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
                        program.getId(), entryType, normalize(request.sourceReference()))
                .orElse(null);
        if (existingSource != null) {
            if (!existingSource.getSourceRequestHash().equals(requestHash)) {
                metrics.sourceReference(entryType, "payload_conflict");
                throw ConflictException.coded(LOYALTY_SOURCE_REFERENCE_REUSED,
                        "Loyalty source reference was reused with a different request");
            }
            PointsMutationResponseDto response = toMutationResponse(
                    existingSource, pointsEntryRepository.balance(existingSource.getAccountId()), true);
            rememberIdempotency(program.getTenantId(), program.getApplicationId(), entryType,
                    request.idempotencyKey(), requestHash, response);
            metrics.sourceReference(entryType, "replay");
            return response;
        }

        LoyaltyAccount account = existingAccount
                .orElseGet(() -> createOrRefetchMutationAccount(program, normalizedProfileId, createMissingAccount));
        requireActiveAccount(account);
        long balanceBefore = pointsEntryRepository.balance(account.getId());
        long spendableBefore = spendablePoints(account.getId(), Instant.now());
        if (pointsDelta < 0 && !program.isAllowNegativeBalance() && spendableBefore < Math.abs(pointsDelta)) {
            throw ConflictException.coded(
                    LOYALTY_INSUFFICIENT_BALANCE,
                    "Loyalty account has insufficient active points");
        }

        LoyaltyPointsEntry entry = pointsEntryRepository.save(new LoyaltyPointsEntry(
                account,
                entryType,
                pointsDelta,
                normalize(request.sourceReference()),
                requestHash,
                null,
                request.reason(),
                request.correlationId(),
                json(request.metadata()),
                request.occurredAt(),
                effectiveExpiry(program, request, pointsDelta)));
        applyLotMutation(entry, !program.isAllowNegativeBalance());
        long balanceAfter = balanceBefore + pointsDelta;
        writeSideEffects(entry, program.getPointUnit(), actor(user), request.reason(), request.correlationId());
        tierService.evaluateAfterPointsMutation(account, actor(user), request.reason(), request.correlationId());
        PointsMutationResponseDto response = toMutationResponse(entry, balanceAfter, false);
        rememberIdempotency(program.getTenantId(), program.getApplicationId(), entryType,
                request.idempotencyKey(), requestHash, response);
        return response;
    }

    private PointsMutationResponseDto mutateLearnerRewardBurn(PointsMutationRequestDto request, CurrentUser user) {
        requireAuthenticated(user);
        String learnerProfileId = String.valueOf(user.id());
        if (!learnerProfileId.equals(normalize(request.profileId()))) {
            throw ForbiddenException.coded(
                    LOYALTY_ACCESS_DENIED,
                    "Learners may only redeem rewards for their own loyalty profile");
        }
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        requireActiveProgram(program);
        String requestHash = hash(Map.of("operation", "REWARD_REDEEM", "request", request));
        PointsMutationResponseDto replay = replayFromIdempotency(
                program.getTenantId(), program.getApplicationId(), "REWARD_REDEEM",
                request.idempotencyKey(), requestHash);
        if (replay != null) {
            return replay;
        }

        LoyaltyAccount account = accountRepository.findByScopeForUpdate(
                        program.getTenantId(), program.getApplicationId(), program.getProgramId(), learnerProfileId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        requireActiveAccount(account);

        LoyaltyPointsEntry existingSource = pointsEntryRepository
                .findFirstByProgramUuidAndEntryTypeAndSourceReferenceAndReversalOfEntryIdIsNull(
                        program.getId(), "BURN", normalize(request.sourceReference()))
                .orElse(null);
        if (existingSource != null) {
            if (!existingSource.getSourceRequestHash().equals(requestHash)) {
                metrics.sourceReference("REWARD_REDEEM", "payload_conflict");
                throw ConflictException.coded(LOYALTY_SOURCE_REFERENCE_REUSED,
                        "Reward redemption source reference was reused with a different request");
            }
            PointsMutationResponseDto response = toMutationResponse(
                    existingSource, pointsEntryRepository.balance(existingSource.getAccountId()), true);
            rememberIdempotency(program.getTenantId(), program.getApplicationId(), "REWARD_REDEEM",
                    request.idempotencyKey(), requestHash, response);
            metrics.sourceReference("REWARD_REDEEM", "replay");
            return response;
        }

        long pointsDelta = -Math.abs(request.points());
        long balanceBefore = pointsEntryRepository.balance(account.getId());
        long spendableBefore = spendablePoints(account.getId(), Instant.now());
        if (!program.isAllowNegativeBalance() && spendableBefore < Math.abs(pointsDelta)) {
            throw ConflictException.coded(
                    LOYALTY_INSUFFICIENT_BALANCE,
                    "Loyalty account has insufficient active points for reward redemption");
        }

        LoyaltyPointsEntry entry = pointsEntryRepository.save(new LoyaltyPointsEntry(
                account,
                "BURN",
                pointsDelta,
                normalize(request.sourceReference()),
                requestHash,
                null,
                request.reason(),
                request.correlationId(),
                json(request.metadata()),
                request.occurredAt(),
                null));
        applyLotMutation(entry, !program.isAllowNegativeBalance());
        long balanceAfter = balanceBefore + pointsDelta;
        writeSideEffects(entry, program.getPointUnit(), actor(user), request.reason(), request.correlationId());
        tierService.evaluateAfterPointsMutation(account, actor(user), request.reason(), request.correlationId());
        PointsMutationResponseDto response = toMutationResponse(entry, balanceAfter, false);
        rememberIdempotency(program.getTenantId(), program.getApplicationId(), "REWARD_REDEEM",
                request.idempotencyKey(), requestHash, response);
        return response;
    }

    private LoyaltyProgram requireProgram(String tenantId, String applicationId, String programId) {
        return programRepository.findByTenantIdAndApplicationIdAndProgramId(
                        normalize(tenantId), normalize(applicationId), normalize(programId))
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_PROGRAM_NOT_FOUND, "Loyalty program not found"));
    }

    private void requireActiveProgram(LoyaltyProgram program) {
        if (!"ACTIVE".equalsIgnoreCase(program.getStatus())) {
            throw ForbiddenException.coded(
                    LOYALTY_PROGRAM_INACTIVE,
                    "Loyalty program is not active");
        }
    }

    private void requireActiveAccount(LoyaltyAccount account) {
        if (!"ACTIVE".equalsIgnoreCase(account.getStatus())) {
            throw ForbiddenException.coded(
                    LOYALTY_ACCOUNT_INACTIVE,
                    "Loyalty account is not active");
        }
    }

    private LoyaltyProgram programFor(LoyaltyAccount account) {
        return programRepository.findById(account.getProgramUuid())
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_PROGRAM_NOT_FOUND, "Loyalty program not found"));
    }

    private LearnerLoyaltyBalanceDto learnerBalance(LoyaltyAccount account, Instant now) {
        LoyaltyProgram program = programFor(account);
        long ledgerBalance = pointsEntryRepository.balance(account.getId());
        List<LoyaltyPointLot> lots = pointLotRepository.findByAccountIdOrderByExpiresAtAscOccurredAtAsc(account.getId())
                .stream()
                .filter(lot -> lot.getRemainingPoints() > 0)
                .toList();
        List<String> warnings = new ArrayList<>();
        long activePoints;
        long expiredPoints;
        long expiringSoonPoints;
        Instant nextExpiryAt;
        if (lots.isEmpty()) {
            activePoints = 0L;
            expiredPoints = 0L;
            expiringSoonPoints = 0L;
            nextExpiryAt = null;
            if (ledgerBalance != 0L) {
                warnings.add("BALANCE_BUCKETS_NOT_MATERIALIZED_FOR_ACCOUNT");
                warnings.add("POINT_LOTS_BACKFILL_REQUIRED_FOR_SPENDABLE_BALANCE");
            }
        } else {
            activePoints = lots.stream()
                    .filter(lot -> !isExpired(lot, now))
                    .mapToLong(LoyaltyPointLot::getRemainingPoints)
                    .sum();
            expiredPoints = lots.stream()
                    .filter(lot -> isExpired(lot, now))
                    .mapToLong(LoyaltyPointLot::getRemainingPoints)
                    .sum();
            Instant expiringSoonCutoff = now.plus(30, ChronoUnit.DAYS);
            expiringSoonPoints = lots.stream()
                    .filter(lot -> lot.getExpiresAt() != null)
                    .filter(lot -> lot.getExpiresAt().isAfter(now) && !lot.getExpiresAt().isAfter(expiringSoonCutoff))
                    .mapToLong(LoyaltyPointLot::getRemainingPoints)
                    .sum();
            nextExpiryAt = lots.stream()
                    .map(LoyaltyPointLot::getExpiresAt)
                    .filter(expiresAt -> expiresAt != null && expiresAt.isAfter(now))
                    .min(Comparator.naturalOrder())
                    .orElse(null);
            if (ledgerBalance != activePoints + expiredPoints) {
                warnings.add("POINT_LOT_BALANCE_MISMATCH");
            }
        }
        if (!"ACTIVE".equalsIgnoreCase(program.getStatus())) {
            warnings.add("PROGRAM_NOT_ACTIVE");
        }
        if (!"ACTIVE".equalsIgnoreCase(account.getStatus())) {
            warnings.add("ACCOUNT_NOT_ACTIVE");
        }
        return new LearnerLoyaltyBalanceDto(
                account.getId(),
                account.getTenantId(),
                account.getApplicationId(),
                account.getProgramId(),
                program.getPointUnit(),
                account.getStatus(),
                program.getStatus(),
                ledgerBalance,
                activePoints,
                expiredPoints,
                expiringSoonPoints,
                nextExpiryAt,
                tierService.progressForAccount(account, now),
                warnings);
    }

    private boolean isExpired(LoyaltyPointLot lot, Instant now) {
        return lot.getExpiresAt() != null && !lot.getExpiresAt().isAfter(now);
    }

    private String operationName(String entryType) {
        return switch (entryType) {
            case "EARN" -> "earn";
            case "BURN" -> "burn";
            case "REVERSE" -> "reverse";
            case "ADJUST" -> "adjust";
            case "EXPIRE" -> "expire";
            default -> "admin";
        };
    }

    private LoyaltyAccount createOrRefetchMutationAccount(
            LoyaltyProgram program, String profileId, boolean createMissingAccount) {
        if (!createMissingAccount) {
            throw NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found");
        }
        try {
            return accountRepository.saveAndFlush(new LoyaltyAccount(program, profileId));
        } catch (DataIntegrityViolationException ex) {
            return accountRepository.findByScopeForUpdate(
                            program.getTenantId(), program.getApplicationId(), program.getProgramId(), profileId)
                    .orElseThrow(() -> NotFoundException.coded(LOYALTY_ACCOUNT_NOT_FOUND, "Loyalty account not found"));
        }
    }

    private void applyLotMutation(LoyaltyPointsEntry entry, boolean requireDebitCoverage) {
        if (entry.getPointsDelta() > 0) {
            pointLotRepository.findBySourceEntryId(entry.getId())
                    .orElseGet(() -> pointLotRepository.save(new LoyaltyPointLot(entry)));
            return;
        }
        List<LotAllocation> allocations = consumeActiveLots(
                entry.getAccountId(),
                Math.abs(entry.getPointsDelta()),
                requireDebitCoverage);
        if (!allocations.isEmpty()) {
            Map<String, Object> metadata = new LinkedHashMap<>(readMap(entry.getMetadataJson()));
            metadata.put(LOT_ALLOCATIONS_METADATA_KEY, allocations.stream()
                    .map(LoyaltyService::lotAllocationMap)
                    .toList());
            entry.replaceMetadataJson(json(metadata));
        }
    }

    private List<LotAllocation> consumeActiveLots(UUID accountId, long points, boolean requireDebitCoverage) {
        long remainingDebit = points;
        List<LotAllocation> allocations = new ArrayList<>();
        List<LoyaltyPointLot> lots = pointLotRepository.activeRemainingLotsForUpdate(accountId, Instant.now())
                .stream()
                .sorted(pointLotComparator())
                .toList();
        for (LoyaltyPointLot lot : lots) {
            if (remainingDebit == 0) {
                return allocations;
            }
            long consumed = lot.consume(remainingDebit);
            if (consumed > 0) {
                allocations.add(new LotAllocation(lot.getId(), lot.getSourceEntryId(), consumed));
            }
            remainingDebit -= consumed;
        }
        if (remainingDebit > 0 && requireDebitCoverage) {
            throw ConflictException.coded(
                    LOYALTY_INSUFFICIENT_BALANCE,
                    "Loyalty account has insufficient active point lots");
        }
        return allocations;
    }

    private long spendablePoints(UUID accountId, Instant asOf) {
        return pointLotRepository.activeRemainingPoints(accountId, asOf == null ? Instant.now() : asOf);
    }

    private boolean hasLotAllocations(LoyaltyPointsEntry entry) {
        return !lotAllocations(entry).isEmpty();
    }

    private void restoreLotAllocations(LoyaltyPointsEntry original) {
        List<LotAllocation> allocations = lotAllocations(original);
        List<UUID> lotIds = allocations.stream().map(LotAllocation::lotId).distinct().toList();
        Map<UUID, LoyaltyPointLot> lotsById = new LinkedHashMap<>();
        if (!lotIds.isEmpty()) {
            pointLotRepository.findByIdsForUpdate(lotIds)
                    .forEach(lot -> lotsById.put(lot.getId(), lot));
        }
        long remainingRestore = Math.abs(original.getPointsDelta());
        for (LotAllocation allocation : allocations) {
            LoyaltyPointLot lot = lotsById.get(allocation.lotId());
            if (lot == null) {
                throw ConflictException.coded(
                        LOYALTY_ENTRY_NOT_REVERSIBLE,
                        "Original point lot allocation is no longer available for reversal");
            }
            long expectedRestore = Math.min(allocation.points(), remainingRestore);
            long restored = lot.restore(expectedRestore);
            if (restored != expectedRestore) {
                throw ConflictException.coded(
                        LOYALTY_ENTRY_NOT_REVERSIBLE,
                        "Original point lot allocation cannot be fully restored");
            }
            remainingRestore -= restored;
        }
        if (remainingRestore > 0) {
            throw ConflictException.coded(
                    LOYALTY_ENTRY_NOT_REVERSIBLE,
                    "Original debit entry does not contain enough point-lot allocation metadata");
        }
    }

    private List<LotAllocation> lotAllocations(LoyaltyPointsEntry entry) {
        Object raw = readMap(entry.getMetadataJson()).get(LOT_ALLOCATIONS_METADATA_KEY);
        if (!(raw instanceof List<?> rows)) {
            return List.of();
        }
        List<LotAllocation> allocations = new ArrayList<>();
        for (Object row : rows) {
            if (!(row instanceof Map<?, ?> map)) {
                continue;
            }
            UUID lotId = uuidValue(map.get("lotId"));
            long points = longValue(map.get("points"));
            if (lotId == null || points <= 0) {
                continue;
            }
            allocations.add(new LotAllocation(lotId, uuidValue(map.get("sourceEntryId")), points));
        }
        return allocations;
    }

    private static Map<String, Object> lotAllocationMap(LotAllocation allocation) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("lotId", allocation.lotId().toString());
        row.put("sourceEntryId", allocation.sourceEntryId() == null ? "" : allocation.sourceEntryId().toString());
        row.put("points", allocation.points());
        return row;
    }

    private static Map<String, Object> lotAllocationMap(LoyaltyPointLot lot, long points) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("lotId", lot.getId().toString());
        row.put("sourceEntryId", lot.getSourceEntryId().toString());
        row.put("sourceReference", lot.getSourceReference());
        row.put("expiresAt", lot.getExpiresAt() == null ? "" : lot.getExpiresAt().toString());
        row.put("points", points);
        return row;
    }

    private UUID uuidValue(Object value) {
        if (value == null || String.valueOf(value).isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(String.valueOf(value));
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private long longValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value == null || String.valueOf(value).isBlank()) {
            return 0L;
        }
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return 0L;
        }
    }

    private Comparator<LoyaltyPointLot> pointLotComparator() {
        return Comparator
                .comparing((LoyaltyPointLot lot) -> lot.getExpiresAt() == null ? NO_EXPIRY : lot.getExpiresAt())
                .thenComparing(LoyaltyPointLot::getOccurredAt)
                .thenComparing(LoyaltyPointLot::getCreatedAt);
    }

    private Instant effectiveExpiry(LoyaltyProgram program, PointsMutationRequestDto request, long pointsDelta) {
        return effectiveExpiry(program, request.occurredAt(), request.expiresAt(), pointsDelta);
    }

    private Instant effectiveExpiry(LoyaltyProgram program, Instant occurredAt, Instant requestedExpiresAt, long pointsDelta) {
        if (requestedExpiresAt != null || pointsDelta <= 0) {
            return requestedExpiresAt;
        }
        Integer days = program.getDefaultPointsExpiryDays();
        return days == null ? null : (occurredAt == null ? Instant.now() : occurredAt).plus(days, ChronoUnit.DAYS);
    }

    private PointsMutationResponseDto replayFromIdempotency(
            String tenantId, String applicationId, String operation, String idempotencyKey, String requestHash) {
        LoyaltyIdempotencyKey existing = idempotencyKeyRepository
                .findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
                        tenantId, applicationId, operation, normalize(idempotencyKey))
                .orElse(null);
        if (existing == null) {
            return null;
        }
        if (!existing.getRequestHash().equals(requestHash)) {
            metrics.idempotency(operation, "payload_conflict");
            throw ConflictException.coded(LOYALTY_IDEMPOTENCY_KEY_REUSED,
                    "Idempotency key was reused with a different loyalty request");
        }
        if (!"SUCCEEDED".equals(existing.getStatus())) {
            metrics.idempotency(operation, "not_replayable");
            throw ConflictException.coded(LOYALTY_IDEMPOTENCY_NOT_REPLAYABLE,
                    "Idempotency key is not replayable");
        }
        try {
            PointsMutationResponseDto response = objectMapper.readValue(
                    existing.getResponseJson(), PointsMutationResponseDto.class);
            metrics.idempotency(operation, "replay");
            return withReplay(response, true);
        } catch (JsonProcessingException ex) {
            metrics.idempotency(operation, "response_not_replayable");
            throw ConflictException.coded(LOYALTY_RESPONSE_NOT_REPLAYABLE,
                    "Stored loyalty idempotency response is not replayable");
        }
    }

    private void rememberIdempotency(String tenantId, String applicationId, String operation, String idempotencyKey,
                                     String requestHash, PointsMutationResponseDto response) {
        idempotencyKeyRepository.save(new LoyaltyIdempotencyKey(
                tenantId,
                applicationId,
                operation,
                normalize(idempotencyKey),
                requestHash,
                json(withReplay(response, false)),
                Instant.now().plus(IDEMPOTENCY_TTL_DAYS, ChronoUnit.DAYS)));
        metrics.idempotency(operation, "remembered");
    }

    private PointsExpiryExecutionResponseDto replayExpiryFromIdempotency(
            String tenantId, String applicationId, String idempotencyKey, String requestHash) {
        LoyaltyIdempotencyKey existing = idempotencyKeyRepository
                .findByTenantIdAndApplicationIdAndOperationAndIdempotencyKey(
                        tenantId, applicationId, "EXPIRE", normalize(idempotencyKey))
                .orElse(null);
        if (existing == null) {
            return null;
        }
        if (!existing.getRequestHash().equals(requestHash)) {
            metrics.idempotency("EXPIRE", "payload_conflict");
            throw ConflictException.coded(LOYALTY_IDEMPOTENCY_KEY_REUSED,
                    "Idempotency key was reused with a different loyalty expiry request");
        }
        try {
            PointsExpiryExecutionResponseDto response = objectMapper.readValue(
                    existing.getResponseJson(), PointsExpiryExecutionResponseDto.class);
            metrics.idempotency("EXPIRE", "replay");
            return new PointsExpiryExecutionResponseDto(
                    response.tenantId(),
                    response.applicationId(),
                    response.programId(),
                    response.asOf(),
                    response.expiredLotCount(),
                    response.affectedAccountCount(),
                    response.expiredPoints(),
                    true,
                    response.items(),
                    response.warnings());
        } catch (JsonProcessingException ex) {
            metrics.idempotency("EXPIRE", "response_not_replayable");
            throw ConflictException.coded(LOYALTY_RESPONSE_NOT_REPLAYABLE,
                    "Stored loyalty expiry idempotency response is not replayable");
        }
    }

    private void rememberExpiryIdempotency(
            String tenantId,
            String applicationId,
            String idempotencyKey,
            String requestHash,
            PointsExpiryExecutionResponseDto response) {
        idempotencyKeyRepository.save(new LoyaltyIdempotencyKey(
                tenantId,
                applicationId,
                "EXPIRE",
                normalize(idempotencyKey),
                requestHash,
                json(new PointsExpiryExecutionResponseDto(
                        response.tenantId(),
                        response.applicationId(),
                        response.programId(),
                        response.asOf(),
                        response.expiredLotCount(),
                        response.affectedAccountCount(),
                        response.expiredPoints(),
                        false,
                        response.items(),
                        response.warnings())),
                Instant.now().plus(IDEMPOTENCY_TTL_DAYS, ChronoUnit.DAYS)));
        metrics.idempotency("EXPIRE", "remembered");
    }

    private void writeSideEffects(
            LoyaltyPointsEntry entry, String pointUnit, String actorId, String reason, String correlationId) {
        LoyaltyPointsChangedEvent event = new LoyaltyPointsChangedEvent(
                UUID.randomUUID().toString(),
                1,
                entry.getTenantId(),
                entry.getApplicationId(),
                entry.getProgramId(),
                entry.getAccountId().toString(),
                entry.getId().toString(),
                entry.getProfileId(),
                entry.getEntryType(),
                entry.getPointsDelta(),
                entry.getSourceReference(),
                correlationId,
                entry.getOccurredAt(),
                new EventMetadata(
                        correlationId,
                        entry.getReversalOfEntryId() == null ? null : entry.getReversalOfEntryId().toString(),
                        actorId,
                        Map.of("pointUnit", pointUnit == null || pointUnit.isBlank() ? "POINT" : pointUnit)));
        String eventType = event.eventType();
        String payload = json(event);
        audit(entry.getTenantId(), entry.getApplicationId(), entry.getId().toString(), "loyalty-points-entry",
                eventType, actorId, reason, correlationId, payload);
        outboxEventRepository.save(new OutboxEvent(entry.getId(), "loyalty-points-entry", eventType, payload));
        metrics.outboxEnqueued(eventType);
    }

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, String correlationId, String payloadJson) {
        auditEventRepository.save(new LoyaltyAuditEvent(
                tenantId, applicationId, aggregateId, aggregateType, action, actorId, note, correlationId, payloadJson));
    }

    private LoyaltyProgramDto toProgramDto(LoyaltyProgram program) {
        return new LoyaltyProgramDto(
                program.getId(),
                program.getTenantId(),
                program.getApplicationId(),
                program.getProgramId(),
                program.getName(),
                program.getPointUnit(),
                program.getStatus(),
                program.isAllowNegativeBalance(),
                program.getDefaultPointsExpiryDays(),
                program.getCreatedAt());
    }

    private LoyaltyAccountDto toAccountDto(LoyaltyAccount account) {
        return new LoyaltyAccountDto(
                account.getId(),
                account.getTenantId(),
                account.getApplicationId(),
                account.getProgramId(),
                account.getProfileId(),
                account.getStatus(),
                pointsEntryRepository.balance(account.getId()),
                account.getOpenedAt());
    }

    private PointsEntryDto toEntryDto(LoyaltyPointsEntry entry) {
        return new PointsEntryDto(
                entry.getId(),
                entry.getAccountId(),
                entry.getTenantId(),
                entry.getApplicationId(),
                entry.getProgramId(),
                entry.getProfileId(),
                entry.getEntryType(),
                entry.getPointsDelta(),
                entry.getSourceReference(),
                entry.getReversalOfEntryId(),
                entry.getReason(),
                entry.getCorrelationId(),
                entry.getOccurredAt(),
                entry.getExpiresAt(),
                entry.getCreatedAt());
    }

    private PointsMutationResponseDto toMutationResponse(LoyaltyPointsEntry entry, long balance, boolean replay) {
        return new PointsMutationResponseDto(
                entry.getId(),
                entry.getAccountId(),
                entry.getTenantId(),
                entry.getApplicationId(),
                entry.getProgramId(),
                entry.getProfileId(),
                entry.getEntryType(),
                entry.getPointsDelta(),
                balance,
                replay);
    }

    private PointsMutationResponseDto withReplay(PointsMutationResponseDto response, boolean replay) {
        return new PointsMutationResponseDto(
                response.entryId(),
                response.accountId(),
                response.tenantId(),
                response.applicationId(),
                response.programId(),
                response.profileId(),
                response.entryType(),
                response.pointsDelta(),
                response.balance(),
                replay);
    }

    private PointsAdjustmentRequestDto approvalRequest(LoyaltyAdjustmentApproval approval) {
        Map<String, Object> metadata = Map.of(
                "approvalId", approval.getId().toString(),
                "approvalRequestedBy", approval.getRequestedBy(),
                "approvalReviewedBy", approval.getReviewedBy() == null ? "" : approval.getReviewedBy());
        return new PointsAdjustmentRequestDto(
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getProgramId(),
                approval.getProfileId(),
                approval.getPointsDelta(),
                approval.getSourceReference(),
                approval.getIdempotencyKey(),
                approval.getReason(),
                approval.getCorrelationId(),
                approval.getOccurredAt(),
                approval.getExpiresAt(),
                metadata);
    }

    private boolean isExpiryApproval(LoyaltyAdjustmentApproval approval) {
        return EXPIRY_APPROVAL_OPERATION.equalsIgnoreCase(approvalOperationType(approval));
    }

    private boolean isRewardReversalApproval(LoyaltyAdjustmentApproval approval) {
        return REWARD_REVERSAL_APPROVAL_OPERATION.equalsIgnoreCase(approvalOperationType(approval));
    }

    private boolean isRewardFulfillmentApproval(LoyaltyAdjustmentApproval approval) {
        return REWARD_FULFILLMENT_APPROVAL_OPERATION.equalsIgnoreCase(approvalOperationType(approval));
    }

    private String approvalAggregateType(LoyaltyAdjustmentApproval approval) {
        if (isExpiryApproval(approval)) {
            return "loyalty-expiry-approval";
        }
        if (isRewardReversalApproval(approval)) {
            return "loyalty-reward-reversal-approval";
        }
        if (isRewardFulfillmentApproval(approval)) {
            return "loyalty-reward-fulfillment-approval";
        }
        return "loyalty-adjustment-approval";
    }

    private String approvalRejectedAction(LoyaltyAdjustmentApproval approval) {
        if (isExpiryApproval(approval)) {
            return "loyalty.expiry_approval.rejected";
        }
        if (isRewardReversalApproval(approval)) {
            return "loyalty.reward_reversal_approval.rejected";
        }
        if (isRewardFulfillmentApproval(approval)) {
            return "loyalty.reward_fulfillment_approval.rejected";
        }
        return "loyalty.adjustment_approval.rejected";
    }

    private String approvalOperationType(LoyaltyAdjustmentApproval approval) {
        String operationType = stringValue(approvalMetadata(approval).get("operationType"));
        return operationType == null ? "ADJUSTMENT" : operationType;
    }

    private Map<String, Object> approvalMetadata(LoyaltyAdjustmentApproval approval) {
        if (approval.getMetadataJson() == null || approval.getMetadataJson().isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> metadata = objectMapper.readValue(approval.getMetadataJson(), MAP_TYPE);
            return metadata == null ? Map.of() : metadata;
        } catch (JsonProcessingException ex) {
            return Map.of();
        }
    }

    private String requiredString(Map<String, Object> metadata, String key) {
        String value = stringValue(metadata.get(key));
        if (value == null) {
            throw ConflictException.coded(
                    LOYALTY_EXPIRY_APPROVAL_MISMATCH,
                    "Expiry approval metadata is missing: " + key);
        }
        return value;
    }

    private int requiredInt(Map<String, Object> metadata, String key) {
        Object raw = metadata.get(key);
        if (raw instanceof Number number) {
            return number.intValue();
        }
        String value = stringValue(raw);
        if (value != null) {
            try {
                return Integer.parseInt(value);
            } catch (NumberFormatException ignored) {
                // handled below
            }
        }
        throw ConflictException.coded(
                LOYALTY_EXPIRY_APPROVAL_MISMATCH,
                "Expiry approval metadata is invalid: " + key);
    }

    private String stringValue(Object raw) {
        return raw == null || raw.toString().isBlank() ? null : raw.toString().trim();
    }

    private LoyaltyAdjustmentApprovalDto toApprovalDto(LoyaltyAdjustmentApproval approval) {
        Map<String, Object> metadata = approvalMetadata(approval);
        return new LoyaltyAdjustmentApprovalDto(
                approval.getId(),
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getProgramId(),
                approval.getProfileId(),
                approval.getPointsDelta(),
                approval.getSourceReference(),
                approval.getReason(),
                approval.getCorrelationId(),
                approval.getOccurredAt(),
                approval.getExpiresAt(),
                approval.getStatus(),
                approval.getRequestedBy(),
                approval.getReviewedBy(),
                approval.getReviewNote(),
                approval.getRequestedAt(),
                approval.getReviewedAt(),
                approval.getExecutedAt(),
                approval.getExecutedEntryId(),
                approvalOperationType(approval),
                metadata);
    }

    private String actor(CurrentUser user) {
        if ("service".equalsIgnoreCase(access.actorType(user))) {
            String sourceClientId = access.sourceClientId(user);
            if (sourceClientId != null && !sourceClientId.isBlank()) {
                return sourceClientId;
            }
        }
        if (user == null) {
            return null;
        }
        if (user.email() != null && !user.email().isBlank()) {
            return user.email();
        }
        return user.id() == null ? null : String.valueOf(user.id());
    }

    private Duration elapsed(long startedNanos) {
        return Duration.ofNanos(Math.max(0L, System.nanoTime() - startedNanos));
    }

    private String errorReason(RuntimeException ex) {
        if (ex instanceof ErrorCodeCarrier carrier) {
            return carrier.errorCode();
        }
        return ex.getClass().getSimpleName();
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim();
    }

    private String blankToNull(String value) {
        String normalized = normalize(value);
        return normalized.isBlank() ? null : normalized;
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw ForbiddenException.coded(
                    LOYALTY_ACCESS_DENIED,
                    "Authenticated learner is required");
        }
    }

    private String json(Object value) {
        try {
            Object safe = value == null ? Map.of() : value;
            return objectMapper.writeValueAsString(safe);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("Unable to serialize loyalty payload", ex);
        }
    }

    private Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            Map<String, Object> result = objectMapper.readValue(json, MAP_TYPE);
            return result == null ? Map.of() : result;
        } catch (JsonProcessingException ex) {
            return Map.of("raw", json);
        }
    }

    private String hash(Object value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(digest.digest(json(value).getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private record LotAllocation(UUID lotId, UUID sourceEntryId, long points) {
    }
}
