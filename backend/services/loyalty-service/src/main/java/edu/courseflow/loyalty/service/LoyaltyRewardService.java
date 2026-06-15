package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_INACTIVE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_ALREADY_EXISTS;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_IDEMPOTENCY_KEY_REUSED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_INACTIVE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_FULFILLMENT_APPROVAL_REQUIRED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_INVALID_REQUEST;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_OUT_OF_STOCK;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_PROFILE_LIMIT_REACHED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_REVERSAL_APPROVAL_MISMATCH;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_REVERSAL_APPROVAL_REQUIRED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerRewardCatalogResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerRewardDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyAdjustmentApprovalDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardRedemptionDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardRedemptionQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RedeemRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RetryRewardFulfillmentRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RewardFulfillmentCallbackRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RewardFulfillmentRunItemDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RewardFulfillmentRunResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitRewardFulfillmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitRewardRedemptionReversalApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardFulfillmentStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardStatusRequestDto;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyAdjustmentApproval;
import edu.courseflow.loyalty.model.LoyaltyAuditEvent;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyReward;
import edu.courseflow.loyalty.model.LoyaltyRewardFulfillmentAttempt;
import edu.courseflow.loyalty.model.LoyaltyRewardRedemption;
import edu.courseflow.loyalty.model.OutboxEvent;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyAdjustmentApprovalRepository;
import edu.courseflow.loyalty.repository.LoyaltyAuditEventRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointLotRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardFulfillmentAttemptRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRedemptionRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRepository;
import edu.courseflow.loyalty.repository.OutboxEventRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Service
public class LoyaltyRewardService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };
    private static final String REWARD_REVERSAL_APPROVAL_OPERATION = "REWARD_REDEMPTION_REVERSE";
    private static final String REWARD_REVERSAL_THRESHOLD_POLICY =
            "ALL_REWARD_REDEMPTION_REVERSALS_REQUIRE_MAKER_CHECKER_APPROVAL";
    private static final String REWARD_FULFILLMENT_APPROVAL_OPERATION = "REWARD_FULFILLMENT_OVERRIDE";
    private static final String REWARD_FULFILLMENT_THRESHOLD_POLICY =
            "ALL_MANUAL_REWARD_FULFILLMENT_OVERRIDES_REQUIRE_MAKER_CHECKER_APPROVAL";
    private static final Set<String> FULFILLMENT_STATUSES = Set.of(
            "PENDING", "ISSUED", "MANUAL_REQUIRED", "FAILED");
    private static final int DEFAULT_MAX_FULFILLMENT_ATTEMPTS = 5;
    private static final long DEFAULT_FULFILLMENT_BASE_BACKOFF_SECONDS = 60;
    private static final long DEFAULT_FULFILLMENT_MAX_BACKOFF_SECONDS = 3600;
    private static final long DEFAULT_FULFILLMENT_SLA_HOURS = 48;

    private final LoyaltyRewardRepository rewards;
    private final LoyaltyRewardRedemptionRepository redemptions;
    private final LoyaltyProgramRepository programs;
    private final LoyaltyAccountRepository accounts;
    private final LoyaltyPointsEntryRepository pointsEntries;
    private final LoyaltyPointLotRepository pointLots;
    private final LoyaltyAdjustmentApprovalRepository adjustmentApprovals;
    private final LoyaltyAuditEventRepository auditEvents;
    private final LoyaltyRewardFulfillmentAttemptRepository fulfillmentAttempts;
    private final OutboxEventRepository outboxEvents;
    private final LoyaltyAccessService access;
    private final LoyaltyService loyaltyService;
    private final RestClient.Builder restClientBuilder;
    private final ObjectMapper objectMapper;
    private final int maxFulfillmentAttempts;
    private final long fulfillmentBaseBackoffSeconds;
    private final long fulfillmentMaxBackoffSeconds;
    private final long defaultFulfillmentSlaHours;

    public LoyaltyRewardService(
            LoyaltyRewardRepository rewards,
            LoyaltyRewardRedemptionRepository redemptions,
            LoyaltyProgramRepository programs,
            LoyaltyAccountRepository accounts,
            LoyaltyPointsEntryRepository pointsEntries,
            LoyaltyPointLotRepository pointLots,
            LoyaltyAdjustmentApprovalRepository adjustmentApprovals,
            LoyaltyAuditEventRepository auditEvents,
            LoyaltyRewardFulfillmentAttemptRepository fulfillmentAttempts,
            OutboxEventRepository outboxEvents,
            LoyaltyAccessService access,
            LoyaltyService loyaltyService,
            RestClient.Builder restClientBuilder,
            ObjectMapper objectMapper,
            @Value("${courseflow.loyalty.reward-fulfillment.max-attempts:5}") int maxFulfillmentAttempts,
            @Value("${courseflow.loyalty.reward-fulfillment.base-backoff-seconds:60}") long fulfillmentBaseBackoffSeconds,
            @Value("${courseflow.loyalty.reward-fulfillment.max-backoff-seconds:3600}") long fulfillmentMaxBackoffSeconds,
            @Value("${courseflow.loyalty.reward-fulfillment.default-sla-hours:48}") long defaultFulfillmentSlaHours) {
        this.rewards = rewards;
        this.redemptions = redemptions;
        this.programs = programs;
        this.accounts = accounts;
        this.pointsEntries = pointsEntries;
        this.pointLots = pointLots;
        this.adjustmentApprovals = adjustmentApprovals;
        this.auditEvents = auditEvents;
        this.fulfillmentAttempts = fulfillmentAttempts;
        this.outboxEvents = outboxEvents;
        this.access = access;
        this.loyaltyService = loyaltyService;
        this.restClientBuilder = restClientBuilder;
        this.objectMapper = objectMapper;
        this.maxFulfillmentAttempts = maxFulfillmentAttempts <= 0
                ? DEFAULT_MAX_FULFILLMENT_ATTEMPTS
                : maxFulfillmentAttempts;
        this.fulfillmentBaseBackoffSeconds = fulfillmentBaseBackoffSeconds <= 0
                ? DEFAULT_FULFILLMENT_BASE_BACKOFF_SECONDS
                : fulfillmentBaseBackoffSeconds;
        this.fulfillmentMaxBackoffSeconds = fulfillmentMaxBackoffSeconds <= 0
                ? DEFAULT_FULFILLMENT_MAX_BACKOFF_SECONDS
                : fulfillmentMaxBackoffSeconds;
        this.defaultFulfillmentSlaHours = defaultFulfillmentSlaHours <= 0
                ? DEFAULT_FULFILLMENT_SLA_HOURS
                : defaultFulfillmentSlaHours;
    }

    @Transactional(readOnly = true)
    public List<LoyaltyRewardDto> listRewards(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> status,
            Optional<Boolean> activeOnly,
            Optional<Integer> limit,
            CurrentUser user) {
        requireReadForScope(tenantId, applicationId, user);
        return rewards.search(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(programId.orElse(null)),
                        normalized(status.orElse(null)),
                        Boolean.TRUE.equals(activeOnly.orElse(false)) ? Instant.now() : null,
                        PageRequest.of(0, boundedLimit(limit.orElse(50))))
                .stream()
                .map(this::rewardDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public LoyaltyRewardDto reward(UUID rewardId, CurrentUser user) {
        LoyaltyReward reward = rewardById(rewardId);
        access.requireReadAccess(reward.getTenantId(), reward.getApplicationId(), user);
        return rewardDto(reward);
    }

    @Transactional
    public LoyaltyRewardDto createReward(CreateRewardRequestDto request, CurrentUser user) {
        LoyaltyProgram program = programByScope(request.tenantId(), request.applicationId(), request.programId());
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        String rewardCode = normalize(request.rewardCode());
        if (rewardCode.isBlank()) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, "rewardCode is required");
        }
        if (request.pointsCost() == null || request.pointsCost() <= 0) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, "pointsCost must be positive");
        }
        validateWindow(request.startsAt(), request.endsAt());
        if (rewards.existsByTenantIdAndApplicationIdAndProgramIdAndRewardCode(
                program.getTenantId(), program.getApplicationId(), program.getProgramId(), rewardCode)) {
            throw ConflictException.coded(LOYALTY_REWARD_ALREADY_EXISTS, "Loyalty reward already exists");
        }
        LoyaltyReward reward = rewards.save(new LoyaltyReward(
                program,
                rewardCode,
                request.name().trim(),
                blankToNull(request.description()),
                request.pointsCost(),
                request.status(),
                request.startsAt(),
                request.endsAt(),
                request.inventoryLimit(),
                request.perProfileLimit(),
                request.fulfillmentType(),
                json(request.fulfillmentConfig()),
                actor(user)));
        audit(reward.getTenantId(), reward.getApplicationId(), reward.getId().toString(), "loyalty-reward",
                "loyalty.reward.created", actor(user), null, null, Map.of(
                        "programId", reward.getProgramId(),
                        "rewardCode", reward.getRewardCode(),
                        "pointsCost", reward.getPointsCost()));
        return rewardDto(reward);
    }

    @Transactional
    public LoyaltyRewardDto updateReward(UUID rewardId, UpdateRewardRequestDto request, CurrentUser user) {
        LoyaltyReward reward = rewardById(rewardId);
        access.requireAdminAccess(reward.getTenantId(), reward.getApplicationId(), user);
        validateWindow(
                request.startsAt() == null ? reward.getStartsAt() : request.startsAt(),
                request.endsAt() == null ? reward.getEndsAt() : request.endsAt());
        try {
            reward.update(
                    request.name(),
                    request.description(),
                    request.pointsCost(),
                    request.startsAt(),
                    request.endsAt(),
                    request.inventoryLimit(),
                    request.perProfileLimit(),
                    request.fulfillmentType(),
                    request.fulfillmentConfig() == null ? null : json(request.fulfillmentConfig()));
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, ex.getMessage());
        }
        LoyaltyReward saved = rewards.save(reward);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-reward",
                "loyalty.reward.updated", actor(user), null, null, Map.of(
                        "rewardCode", saved.getRewardCode(),
                        "pointsCost", saved.getPointsCost(),
                        "status", saved.getStatus()));
        return rewardDto(saved);
    }

    @Transactional
    public LoyaltyRewardDto updateRewardStatus(
            UUID rewardId,
            UpdateRewardStatusRequestDto request,
            String correlationId,
            CurrentUser user) {
        LoyaltyReward reward = rewardById(rewardId);
        access.requireAdminAccess(reward.getTenantId(), reward.getApplicationId(), user);
        try {
            reward.changeStatus(request.status());
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, ex.getMessage());
        }
        LoyaltyReward saved = rewards.save(reward);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-reward",
                "loyalty.reward.status_changed", actor(user), request.note(), correlationId, Map.of(
                        "rewardCode", saved.getRewardCode(),
                        "status", saved.getStatus()));
        return rewardDto(saved);
    }

    @Transactional(readOnly = true)
    public LearnerRewardCatalogResponseDto learnerRewards(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            CurrentUser user) {
        requireAuthenticated(user);
        String scopedTenantId = blankToNull(tenantId.orElse(null));
        String scopedApplicationId = blankToNull(applicationId.orElse(null));
        if (scopedTenantId == null || scopedApplicationId == null) {
            throw BadRequestException.coded(
                    LOYALTY_REWARD_INVALID_REQUEST,
                    "tenantId and applicationId are required for learner reward catalog");
        }
        String profileId = String.valueOf(user.id());
        Instant now = Instant.now();
        List<LearnerRewardDto> items = rewards.search(
                        scopedTenantId,
                        scopedApplicationId,
                        blankToNull(programId.orElse(null)),
                        null,
                        now,
                        PageRequest.of(0, 100))
                .stream()
                .map(reward -> learnerRewardDto(reward, profileId, now))
                .toList();
        return new LearnerRewardCatalogResponseDto(profileId, now, items);
    }

    @Transactional
    public LoyaltyRewardRedemptionDto redeemReward(
            UUID rewardId,
            RedeemRewardRequestDto request,
            CurrentUser user) {
        requireAuthenticated(user);
        LoyaltyReward reward = rewards.findByIdForUpdate(rewardId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_REWARD_NOT_FOUND, "Loyalty reward not found"));
        LoyaltyProgram program = programById(reward.getProgramUuid());
        String profileId = String.valueOf(user.id());
        String idempotencyKey = blankToNull(request.idempotencyKey());
        if (idempotencyKey == null) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, "idempotencyKey is required");
        }
        String requestHash = rewardRequestHash(reward, profileId, request);
        LoyaltyRewardRedemption existing = redemptions
                .findByTenantIdAndApplicationIdAndIdempotencyKey(
                        reward.getTenantId(), reward.getApplicationId(), idempotencyKey)
                .orElse(null);
        if (existing != null) {
            if (!existing.getRequestHash().equals(requestHash)) {
                throw ConflictException.coded(
                        LOYALTY_REWARD_IDEMPOTENCY_KEY_REUSED,
                        "Reward redemption idempotency key was reused with a different request");
            }
            return redemptionDto(existing, true);
        }

        requireActiveProgram(program);
        requireRewardRedeemable(reward, profileId, Instant.now());
        String sourceReference = rewardSourceReference(reward.getId(), idempotencyKey);
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("source", "loyalty-reward");
        metadata.put("rewardId", reward.getId().toString());
        metadata.put("rewardCode", reward.getRewardCode());
        metadata.put("fulfillmentType", reward.getFulfillmentType());
        if (request.metadata() != null && !request.metadata().isEmpty()) {
            metadata.put("requestMetadata", request.metadata());
        }
        PointsMutationResponseDto burn = loyaltyService.redeemRewardBurn(new PointsMutationRequestDto(
                reward.getTenantId(),
                reward.getApplicationId(),
                reward.getProgramId(),
                profileId,
                reward.getPointsCost(),
                sourceReference,
                idempotencyKey,
                "Reward redemption: " + reward.getRewardCode(),
                request.correlationId(),
                Instant.now(),
                null,
                metadata), user);
        LoyaltyRewardRedemption redemption = new LoyaltyRewardRedemption(
                reward,
                burn.accountId(),
                burn.entryId(),
                profileId,
                sourceReference,
                idempotencyKey,
                requestHash,
                json(rewardSnapshot(reward, program)),
                request.correlationId(),
                request.note(),
                json(request.metadata()));
        try {
            LoyaltyRewardRedemption saved = redemptions.save(redemption);
            audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                    "loyalty-reward-redemption", "loyalty.reward.redeemed", actor(user),
                    request.note(), request.correlationId(), Map.of(
                            "rewardId", saved.getRewardId().toString(),
                            "rewardCode", saved.getRewardCode(),
                            "burnEntryId", saved.getBurnEntryId().toString(),
                            "pointsCost", saved.getPointsCost()));
            emitRewardEvent(saved, "loyalty.reward.redeemed", actor(user), request.note(), request.correlationId(),
                    Map.of("idempotencyReplay", false));
            dispatchFulfillment(saved, reward, actor(user), request.note(), request.correlationId(), false);
            return redemptionDto(saved, false);
        } catch (DataIntegrityViolationException ex) {
            LoyaltyRewardRedemption replay = redemptions
                    .findByTenantIdAndApplicationIdAndIdempotencyKey(
                            reward.getTenantId(), reward.getApplicationId(), idempotencyKey)
                    .orElseThrow(() -> ex);
            if (!replay.getRequestHash().equals(requestHash)) {
                throw ConflictException.coded(
                        LOYALTY_REWARD_IDEMPOTENCY_KEY_REUSED,
                        "Reward redemption idempotency key was reused with a different request");
            }
            return redemptionDto(replay, true);
        }
    }

    @Transactional(readOnly = true)
    public LoyaltyRewardRedemptionQueryResponseDto redemptions(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> profileId,
            Optional<UUID> rewardId,
            Optional<String> status,
            Optional<String> fulfillmentStatus,
            Optional<Instant> from,
            Optional<Instant> to,
            Optional<Integer> limit,
            CurrentUser user) {
        requireReadForScope(tenantId, applicationId, user);
        int pageSize = boundedLimit(limit.orElse(50));
        List<LoyaltyRewardRedemption> rows = redemptions.search(
                blankToNull(tenantId.orElse(null)),
                blankToNull(applicationId.orElse(null)),
                blankToNull(programId.orElse(null)),
                blankToNull(profileId.orElse(null)),
                rewardId.orElse(null),
                normalized(status.orElse(null)),
                normalized(fulfillmentStatus.orElse(null)),
                from.orElse(null),
                to.orElse(null),
                PageRequest.of(0, pageSize + 1));
        boolean hasMore = rows.size() > pageSize;
        return new LoyaltyRewardRedemptionQueryResponseDto(
                rows.stream().limit(pageSize).map(row -> redemptionDto(row, false)).toList(),
                pageSize,
                hasMore);
    }

    @Transactional(readOnly = true)
    public LoyaltyRewardRedemptionDto redemption(UUID redemptionId, CurrentUser user) {
        LoyaltyRewardRedemption redemption = redemptions.findById(redemptionId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Loyalty reward redemption not found"));
        access.requireReadAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        return redemptionDto(redemption, false);
    }

    @Transactional
    public LoyaltyAdjustmentApprovalDto submitReversalApproval(
            UUID redemptionId,
            SubmitRewardRedemptionReversalApprovalRequestDto request,
            CurrentUser user) {
        LoyaltyRewardRedemption redemption = redemptions.findById(redemptionId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Loyalty reward redemption not found"));
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        if ("REVERSED".equals(redemption.getStatus())) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_INVALID_REQUEST,
                    "Reward redemption is already reversed");
        }
        Map<String, Object> metadata = rewardReversalApprovalMetadata(redemption, request);
        LoyaltyAdjustmentApproval approval = adjustmentApprovals.save(new LoyaltyAdjustmentApproval(
                redemption.getTenantId(),
                redemption.getApplicationId(),
                redemption.getProgramId(),
                redemption.getProfileId(),
                redemption.getPointsCost(),
                rewardReversalSourceReference(redemption),
                normalize(request.idempotencyKey()),
                request.reason(),
                request.correlationId(),
                Instant.now(),
                null,
                json(metadata),
                rewardReversalApprovalHash(redemption, request),
                actor(user)));
        audit(redemption.getTenantId(), redemption.getApplicationId(), approval.getId().toString(),
                "loyalty-reward-reversal-approval", "loyalty.reward_reversal_approval.requested",
                actor(user), request.reason(), request.correlationId(), Map.of(
                        "redemptionId", redemption.getId().toString(),
                        "rewardId", redemption.getRewardId().toString(),
                        "rewardCode", redemption.getRewardCode(),
                        "pointsToRestore", redemption.getPointsCost(),
                        "thresholdPolicy", REWARD_REVERSAL_THRESHOLD_POLICY));
        return approvalDto(approval);
    }

    @Transactional
    public LoyaltyRewardRedemptionDto reverseRedemption(
            UUID redemptionId,
            ReversePointsRequestDto request,
            CurrentUser user) {
        LoyaltyRewardRedemption redemption = redemptions.findByIdForUpdate(redemptionId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Loyalty reward redemption not found"));
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        LoyaltyAdjustmentApproval approval = requireApprovedReversalApproval(redemption, request);
        if ("REVERSED".equals(redemption.getStatus())) {
            return redemptionDto(redemption, true);
        }
        if ("EXECUTED".equals(approval.getStatus())) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_REVERSAL_APPROVAL_MISMATCH,
                    "Reward reversal approval has already been executed");
        }
        PointsMutationResponseDto reversal = loyaltyService.reverseRewardBurn(redemption.getBurnEntryId(), request, user);
        redemption.markReversed(reversal.entryId());
        try {
            approval.markExecuted(reversal.entryId());
        } catch (IllegalStateException ex) {
            throw ConflictException.coded(LOYALTY_REWARD_REVERSAL_APPROVAL_MISMATCH, ex.getMessage());
        }
        LoyaltyRewardRedemption saved = redemptions.save(redemption);
        audit(saved.getTenantId(), saved.getApplicationId(), approval.getId().toString(),
                "loyalty-reward-reversal-approval", "loyalty.reward_reversal_approval.executed",
                actor(user), request.reason(), request.correlationId(), Map.of(
                        "redemptionId", saved.getId().toString(),
                        "rewardId", saved.getRewardId().toString(),
                        "rewardCode", saved.getRewardCode(),
                        "burnEntryId", saved.getBurnEntryId().toString(),
                        "reversalEntryId", reversal.entryId().toString(),
                        "pointsRestored", saved.getPointsCost(),
                        "thresholdPolicy", REWARD_REVERSAL_THRESHOLD_POLICY));
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                "loyalty-reward-redemption", "loyalty.reward.reversed", actor(user),
                request.reason(), request.correlationId(), Map.of(
                        "rewardId", saved.getRewardId().toString(),
                        "rewardCode", saved.getRewardCode(),
                        "approvalId", approval.getId().toString(),
                        "approvalReviewedBy", approval.getReviewedBy(),
                        "burnEntryId", saved.getBurnEntryId().toString(),
                        "reversalEntryId", reversal.entryId().toString(),
                        "pointsCost", saved.getPointsCost()));
        emitRewardEvent(saved, "loyalty.reward.reversed", actor(user), request.reason(), request.correlationId(),
                Map.of(
                        "approvalId", approval.getId().toString(),
                        "reversalEntryId", reversal.entryId().toString(),
                        "idempotencyReplay", reversal.idempotencyReplay()));
        return redemptionDto(saved, reversal.idempotencyReplay());
    }

    @Transactional
    public LoyaltyAdjustmentApprovalDto submitFulfillmentApproval(
            UUID redemptionId,
            SubmitRewardFulfillmentApprovalRequestDto request,
            CurrentUser user) {
        LoyaltyRewardRedemption redemption = redemptions.findById(redemptionId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Loyalty reward redemption not found"));
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        validateFulfillmentStatus(request.status());
        Map<String, Object> metadata = rewardFulfillmentApprovalMetadata(redemption, request);
        LoyaltyAdjustmentApproval approval = adjustmentApprovals.save(new LoyaltyAdjustmentApproval(
                redemption.getTenantId(),
                redemption.getApplicationId(),
                redemption.getProgramId(),
                redemption.getProfileId(),
                0L,
                rewardFulfillmentSourceReference(redemption),
                normalize(request.idempotencyKey()),
                request.reason(),
                request.correlationId(),
                Instant.now(),
                null,
                json(metadata),
                rewardFulfillmentApprovalHash(redemption, request),
                actor(user)));
        audit(redemption.getTenantId(), redemption.getApplicationId(), approval.getId().toString(),
                "loyalty-reward-fulfillment-approval", "loyalty.reward_fulfillment_approval.requested",
                actor(user), request.reason(), request.correlationId(), Map.of(
                        "redemptionId", redemption.getId().toString(),
                        "rewardId", redemption.getRewardId().toString(),
                        "rewardCode", redemption.getRewardCode(),
                        "currentFulfillmentStatus", redemption.getFulfillmentStatus(),
                        "targetFulfillmentStatus", normalizeFulfillmentStatus(request.status()),
                        "thresholdPolicy", REWARD_FULFILLMENT_THRESHOLD_POLICY));
        return approvalDto(approval);
    }

    @Transactional
    public LoyaltyRewardRedemptionDto updateFulfillment(
            UUID redemptionId,
            UpdateRewardFulfillmentStatusRequestDto request,
            CurrentUser user) {
        LoyaltyRewardRedemption redemption = redemptions.findByIdForUpdate(redemptionId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Loyalty reward redemption not found"));
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        LoyaltyAdjustmentApproval approval = requireApprovedFulfillmentApproval(redemption, request, user);
        if ("EXECUTED".equals(approval.getStatus())) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH,
                    "Reward fulfillment approval has already been executed");
        }
        try {
            redemption.updateFulfillment(request.status(), request.fulfillmentRef(), request.note());
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, ex.getMessage());
        }
        try {
            approval.markExecuted(null);
        } catch (IllegalStateException ex) {
            throw ConflictException.coded(LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH, ex.getMessage());
        }
        LoyaltyRewardRedemption saved = redemptions.save(redemption);
        audit(saved.getTenantId(), saved.getApplicationId(), approval.getId().toString(),
                "loyalty-reward-fulfillment-approval", "loyalty.reward_fulfillment_approval.executed",
                actor(user), request.reason(), request.correlationId(), Map.of(
                        "redemptionId", saved.getId().toString(),
                        "rewardId", saved.getRewardId().toString(),
                        "rewardCode", saved.getRewardCode(),
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "fulfillmentRef", saved.getFulfillmentRef() == null ? "" : saved.getFulfillmentRef(),
                        "approvalReviewedBy", approval.getReviewedBy(),
                        "thresholdPolicy", REWARD_FULFILLMENT_THRESHOLD_POLICY));
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                "loyalty-reward-redemption", "loyalty.reward.fulfillment_status_changed", actor(user),
                request.reason(), request.correlationId(), Map.of(
                        "rewardId", saved.getRewardId().toString(),
                        "rewardCode", saved.getRewardCode(),
                        "approvalId", approval.getId().toString(),
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "fulfillmentRef", saved.getFulfillmentRef() == null ? "" : saved.getFulfillmentRef()));
        emitRewardEvent(saved, "loyalty.reward.fulfillment_status_changed", actor(user), request.reason(),
                request.correlationId(), Map.of(
                        "approvalId", approval.getId().toString(),
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "fulfillmentRef", saved.getFulfillmentRef() == null ? "" : saved.getFulfillmentRef()));
        return redemptionDto(saved, false);
    }

    @Transactional
    public LoyaltyRewardRedemptionDto retryFulfillment(
            UUID redemptionId,
            RetryRewardFulfillmentRequestDto request,
            CurrentUser user) {
        LoyaltyRewardRedemption redemption = redemptions.findByIdForUpdate(redemptionId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Loyalty reward redemption not found"));
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        LoyaltyReward reward = rewardById(redemption.getRewardId());
        dispatchFulfillment(
                redemption,
                reward,
                actor(user),
                request == null ? null : request.reason(),
                request == null ? redemption.getCorrelationId() : request.correlationId(),
                true);
        return redemptionDto(redemption, false);
    }

    @Transactional
    public LoyaltyRewardRedemptionDto applyFulfillmentCallback(
            String provider,
            RewardFulfillmentCallbackRequestDto request,
            CurrentUser user) {
        LoyaltyRewardRedemption redemption = callbackRedemption(provider, request);
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        String callbackHash = hash(Map.of(
                "provider", normalizedProvider(provider),
                "redemptionId", redemption.getId().toString(),
                "externalRef", blankToNull(request.externalRef()) == null ? "" : request.externalRef().trim(),
                "status", normalized(request.status()),
                "fulfillmentRef", blankToNull(request.fulfillmentRef()) == null ? "" : request.fulfillmentRef().trim(),
                "metadata", request.metadata() == null ? Map.of() : request.metadata()));
        try {
            redemption.updateFulfillment(
                    request.status(),
                    blankToNull(request.fulfillmentRef()) == null ? request.externalRef() : request.fulfillmentRef(),
                    request.note(),
                    request.errorClass(),
                    request.errorMessage(),
                    callbackHash,
                    request.occurredAt() == null ? Instant.now() : request.occurredAt());
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, ex.getMessage());
        }
        LoyaltyRewardRedemption saved = redemptions.save(redemption);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                "loyalty-reward-redemption", "loyalty.reward.fulfillment_callback_received", actor(user),
                request.note(), saved.getCorrelationId(), Map.of(
                        "provider", normalizedProvider(provider),
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "fulfillmentRef", saved.getFulfillmentRef() == null ? "" : saved.getFulfillmentRef(),
                        "callbackPayloadHash", callbackHash));
        emitRewardEvent(saved, "loyalty.reward.fulfillment_callback_received", actor(user), request.note(),
                saved.getCorrelationId(), Map.of(
                        "provider", normalizedProvider(provider),
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "callbackPayloadHash", callbackHash));
        return redemptionDto(saved, false);
    }

    @Transactional
    public RewardFulfillmentRunResponseDto runDueFulfillments(Optional<Integer> limit, CurrentUser user) {
        access.requirePlatformAdmin(user);
        return runDueFulfillmentsInternal(boundedLimit(limit.orElse(50)), actor(user));
    }

    @Transactional
    public RewardFulfillmentRunResponseDto runDueFulfillmentsForScheduler() {
        return runDueFulfillmentsInternal(50, "loyalty-fulfillment-job");
    }

    private RewardFulfillmentRunResponseDto runDueFulfillmentsInternal(int limit, String actorId) {
        Instant runAt = Instant.now();
        List<LoyaltyRewardRedemption> due = redemptions.findDueFulfillmentsForUpdate(
                runAt,
                PageRequest.of(0, boundedLimit(limit)));
        List<RewardFulfillmentRunItemDto> items = new ArrayList<>();
        int issued = 0;
        int pending = 0;
        int failed = 0;
        int manualRequired = 0;
        for (LoyaltyRewardRedemption redemption : due) {
            LoyaltyReward reward = rewardById(redemption.getRewardId());
            dispatchFulfillment(redemption, reward, actorId, "Scheduled reward fulfillment retry",
                    redemption.getCorrelationId(), false);
            items.add(runItem(redemption));
            switch (redemption.getFulfillmentStatus()) {
                case "ISSUED" -> issued++;
                case "PENDING" -> pending++;
                case "FAILED" -> failed++;
                case "MANUAL_REQUIRED" -> manualRequired++;
                default -> {
                }
            }
        }
        return new RewardFulfillmentRunResponseDto(
                runAt,
                due.size(),
                items.size(),
                issued,
                pending,
                failed,
                manualRequired,
                items);
    }

    private void dispatchFulfillment(
            LoyaltyRewardRedemption redemption,
            LoyaltyReward reward,
            String actorId,
            String note,
            String correlationId,
            boolean force) {
        if ("REVERSED".equals(redemption.getStatus())) {
            return;
        }
        if (!force && ("ISSUED".equals(redemption.getFulfillmentStatus())
                || "MANUAL_REQUIRED".equals(redemption.getFulfillmentStatus()))) {
            return;
        }
        Map<String, Object> config = readMap(reward.getFulfillmentConfigJson());
        String provider = normalizedProvider(blankToNull(redemption.getFulfillmentProvider()) == null
                ? reward.getFulfillmentType()
                : redemption.getFulfillmentProvider());
        Instant now = Instant.now();
        redemption.initializeFulfillment(provider, fulfillmentSlaDueAt(redemption, config), now);
        if (!force && redemption.getFulfillmentNextAttemptAt() != null
                && redemption.getFulfillmentNextAttemptAt().isAfter(now)) {
            return;
        }
        redemption.markFulfillmentAttemptStarted(now);
        FulfillmentOutcome outcome;
        try {
            outcome = dispatchProvider(provider, redemption, reward, config);
        } catch (RestClientResponseException ex) {
            outcome = FulfillmentOutcome.failed(
                    ex.getClass().getSimpleName(),
                    "HTTP " + ex.getStatusCode().value() + " from reward fulfillment provider",
                    true,
                    Map.of("statusCode", ex.getStatusCode().value(), "responseBody", ex.getResponseBodyAsString()));
        } catch (RestClientException ex) {
            outcome = FulfillmentOutcome.failed(ex.getClass().getSimpleName(), ex.getMessage(), true, Map.of());
        } catch (RuntimeException ex) {
            outcome = FulfillmentOutcome.failed(ex.getClass().getSimpleName(), ex.getMessage(), false, Map.of());
        }
        applyFulfillmentOutcome(redemption, outcome);
        LoyaltyRewardRedemption saved = redemptions.save(redemption);
        fulfillmentAttempts.save(new LoyaltyRewardFulfillmentAttempt(
                saved,
                provider,
                saved.getFulfillmentAttemptCount(),
                saved.getFulfillmentStatus(),
                saved.getFulfillmentRef(),
                saved.getFulfillmentErrorClass(),
                saved.getFulfillmentErrorMessage(),
                now,
                Instant.now(),
                saved.getFulfillmentNextAttemptAt(),
                correlationId,
                json(outcome.payload())));
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                "loyalty-reward-redemption", "loyalty.reward.fulfillment_dispatched", actorId,
                note, correlationId, Map.of(
                        "provider", provider,
                        "attempt", saved.getFulfillmentAttemptCount(),
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "fulfillmentRef", saved.getFulfillmentRef() == null ? "" : saved.getFulfillmentRef(),
                        "nextAttemptAt", saved.getFulfillmentNextAttemptAt() == null
                                ? ""
                                : saved.getFulfillmentNextAttemptAt().toString(),
                        "errorClass", saved.getFulfillmentErrorClass() == null
                                ? ""
                                : saved.getFulfillmentErrorClass()));
        emitRewardEvent(saved, "loyalty.reward.fulfillment_dispatched", actorId, note, correlationId, Map.of(
                "provider", provider,
                "attempt", saved.getFulfillmentAttemptCount(),
                "fulfillmentStatus", saved.getFulfillmentStatus(),
                "nextAttemptAt", saved.getFulfillmentNextAttemptAt() == null
                        ? ""
                        : saved.getFulfillmentNextAttemptAt().toString()));
    }

    private FulfillmentOutcome dispatchProvider(
            String provider,
            LoyaltyRewardRedemption redemption,
            LoyaltyReward reward,
            Map<String, Object> config) {
        return switch (provider) {
            case "AUTO_ISSUE" -> FulfillmentOutcome.success(
                    "ISSUED",
                    "auto-issue:" + redemption.getId(),
                    "Reward auto-issued",
                    Map.of("adapter", "AUTO_ISSUE"));
            case "WEBHOOK", "PROVIDER_CALLBACK" -> FulfillmentOutcome.success(
                    "PENDING",
                    externalReference(provider, redemption, config),
                    "Waiting for reward fulfillment provider callback",
                    Map.of("adapter", provider));
            case "HTTP_POST" -> dispatchHttpProvider(redemption, reward, config);
            case "MANUAL" -> FulfillmentOutcome.success(
                    "MANUAL_REQUIRED",
                    redemption.getFulfillmentRef(),
                    "Manual reward fulfillment required",
                    Map.of("adapter", "MANUAL"));
            default -> FulfillmentOutcome.success(
                    "MANUAL_REQUIRED",
                    redemption.getFulfillmentRef(),
                    "Unsupported provider " + provider + "; manual fulfillment required",
                    Map.of("adapter", provider, "unsupported", true));
        };
    }

    private FulfillmentOutcome dispatchHttpProvider(
            LoyaltyRewardRedemption redemption,
            LoyaltyReward reward,
            Map<String, Object> config) {
        String endpointUrl = stringValue(config.get("endpointUrl"));
        if (endpointUrl == null || endpointUrl.isBlank()) {
            return FulfillmentOutcome.success(
                    "MANUAL_REQUIRED",
                    redemption.getFulfillmentRef(),
                    "HTTP_POST fulfillment is missing endpointUrl",
                    Map.of("adapter", "HTTP_POST", "missingEndpointUrl", true));
        }
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("redemptionId", redemption.getId().toString());
        request.put("rewardId", redemption.getRewardId().toString());
        request.put("rewardCode", redemption.getRewardCode());
        request.put("tenantId", redemption.getTenantId());
        request.put("applicationId", redemption.getApplicationId());
        request.put("programId", redemption.getProgramId());
        request.put("profileId", redemption.getProfileId());
        request.put("pointsCost", redemption.getPointsCost());
        request.put("sourceReference", redemption.getSourceReference());
        request.put("externalRef", externalReference("HTTP_POST", redemption, config));
        request.put("rewardSnapshot", readMap(redemption.getRewardSnapshotJson()));
        request.put("metadata", readMap(redemption.getMetadataJson()));
        @SuppressWarnings("unchecked")
        Map<String, Object> response = restClientBuilder.build()
                .post()
                .uri(endpointUrl)
                .body(request)
                .retrieve()
                .body(Map.class);
        Map<String, Object> responsePayload = response == null ? Map.of() : response;
        String status = normalized(stringValue(responsePayload.get("status")));
        if (status == null || status.isBlank()) {
            status = "PENDING";
        }
        String fulfillmentRef = firstPresent(
                stringValue(responsePayload.get("fulfillmentRef")),
                stringValue(responsePayload.get("externalRef")),
                stringValue(request.get("externalRef")));
        String note = firstPresent(stringValue(responsePayload.get("note")), "HTTP fulfillment dispatched");
        return FulfillmentOutcome.success(status, fulfillmentRef, note, Map.of(
                "adapter", "HTTP_POST",
                "endpointUrl", endpointUrl,
                "response", responsePayload));
    }

    private void applyFulfillmentOutcome(LoyaltyRewardRedemption redemption, FulfillmentOutcome outcome) {
        String status = normalized(outcome.status());
        if ("FAILED".equals(status)) {
            Instant nextAttemptAt = outcome.retryable()
                    && redemption.getFulfillmentAttemptCount() < maxFulfillmentAttempts
                            ? nextFulfillmentAttemptAt(redemption.getFulfillmentAttemptCount())
                            : null;
            redemption.markFulfillmentFailure(
                    outcome.errorClass(),
                    outcome.errorMessage(),
                    nextAttemptAt,
                    nextAttemptAt == null
                            ? "Reward fulfillment failed; manual intervention required"
                            : "Reward fulfillment failed; retry scheduled");
            return;
        }
        try {
            redemption.updateFulfillment(status, outcome.fulfillmentRef(), outcome.note());
            if ("PENDING".equals(status)) {
                redemption.scheduleNextFulfillmentAttempt(null);
            }
        } catch (IllegalArgumentException ex) {
            redemption.updateFulfillment(
                    "MANUAL_REQUIRED",
                    outcome.fulfillmentRef(),
                    "Provider returned unsupported status " + outcome.status());
        }
    }

    private Instant fulfillmentSlaDueAt(LoyaltyRewardRedemption redemption, Map<String, Object> config) {
        long slaHours = longConfig(config, "slaHours", defaultFulfillmentSlaHours);
        long slaMinutes = longConfig(config, "slaMinutes", 0);
        Instant base = redemption.getRedeemedAt() == null ? Instant.now() : redemption.getRedeemedAt();
        return base.plusSeconds((slaHours * 3600) + (slaMinutes * 60));
    }

    private Instant nextFulfillmentAttemptAt(int attemptNumber) {
        int exponent = Math.max(0, Math.min(10, attemptNumber - 1));
        long delay = Math.min(
                fulfillmentMaxBackoffSeconds,
                fulfillmentBaseBackoffSeconds * (1L << exponent));
        return Instant.now().plusSeconds(delay);
    }

    private LoyaltyRewardRedemption callbackRedemption(String provider, RewardFulfillmentCallbackRequestDto request) {
        if (request.redemptionId() != null) {
            return redemptions.findByIdForUpdate(request.redemptionId())
                    .orElseThrow(() -> NotFoundException.coded(
                            LOYALTY_REWARD_NOT_FOUND,
                            "Loyalty reward redemption not found"));
        }
        String externalRef = blankToNull(request.externalRef());
        if (externalRef == null) {
            throw BadRequestException.coded(
                    LOYALTY_REWARD_INVALID_REQUEST,
                    "redemptionId or externalRef is required for fulfillment callback");
        }
        LoyaltyRewardRedemption matched = redemptions
                .findByFulfillmentProviderAndFulfillmentRef(normalizedProvider(provider), externalRef)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Reward fulfillment callback did not match a redemption"));
        return redemptions.findByIdForUpdate(matched.getId()).orElse(matched);
    }

    private RewardFulfillmentRunItemDto runItem(LoyaltyRewardRedemption redemption) {
        return new RewardFulfillmentRunItemDto(
                redemption.getId(),
                redemption.getRewardCode(),
                redemption.getFulfillmentProvider(),
                redemption.getFulfillmentStatus(),
                redemption.getFulfillmentRef(),
                redemption.getFulfillmentAttemptCount(),
                redemption.getFulfillmentNextAttemptAt(),
                redemption.getFulfillmentErrorClass(),
                redemption.getFulfillmentErrorMessage());
    }

    private String externalReference(String provider, LoyaltyRewardRedemption redemption, Map<String, Object> config) {
        String configured = firstPresent(
                stringValue(config.get("externalReference")),
                stringValue(config.get("externalRef")));
        if (configured != null) {
            return configured + ":" + redemption.getId();
        }
        String prefix = firstPresent(stringValue(config.get("externalReferencePrefix")), provider.toLowerCase());
        return prefix + ":" + redemption.getRewardCode() + ":" + redemption.getId();
    }

    private String normalizedProvider(String provider) {
        return provider == null || provider.isBlank() ? "MANUAL" : provider.trim().toUpperCase();
    }

    private long longConfig(Map<String, Object> config, String key, long fallback) {
        Object value = config == null ? null : config.get(key);
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Long.parseLong(text.trim());
            } catch (NumberFormatException ignored) {
                return fallback;
            }
        }
        return fallback;
    }

    private void requireRewardRedeemable(LoyaltyReward reward, String profileId, Instant now) {
        if (!reward.activeAt(now)) {
            throw ConflictException.coded(LOYALTY_REWARD_INACTIVE, "Loyalty reward is not currently redeemable");
        }
        if (reward.getInventoryLimit() != null
                && redemptions.countByRewardIdAndStatus(reward.getId(), "COMMITTED") >= reward.getInventoryLimit()) {
            throw ConflictException.coded(LOYALTY_REWARD_OUT_OF_STOCK, "Loyalty reward inventory is exhausted");
        }
        if (reward.getPerProfileLimit() != null
                && redemptions.countByRewardIdAndProfileIdAndStatus(reward.getId(), profileId, "COMMITTED")
                >= reward.getPerProfileLimit()) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_PROFILE_LIMIT_REACHED,
                    "Learner has reached the per-profile redemption limit");
        }
    }

    private LoyaltyAdjustmentApproval requireApprovedReversalApproval(
            LoyaltyRewardRedemption redemption,
            ReversePointsRequestDto request) {
        if (request.approvalId() == null) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_REVERSAL_APPROVAL_REQUIRED,
                    "Reward redemption reversal requires an approved approvalId");
        }
        LoyaltyAdjustmentApproval approval = adjustmentApprovals.findByIdForUpdate(request.approvalId())
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_REVERSAL_APPROVAL_REQUIRED,
                        "Reward redemption reversal approval not found"));
        Map<String, Object> metadata = readMap(approval.getMetadataJson());
        if (!REWARD_REVERSAL_APPROVAL_OPERATION.equalsIgnoreCase(approvalOperationType(metadata))) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_REVERSAL_APPROVAL_MISMATCH,
                    "Approval is not for reward redemption reversal");
        }
        if (!redemption.getTenantId().equals(approval.getTenantId())
                || !redemption.getApplicationId().equals(approval.getApplicationId())
                || !redemption.getProgramId().equals(approval.getProgramId())
                || !redemption.getProfileId().equals(approval.getProfileId())
                || redemption.getPointsCost() != approval.getPointsDelta()
                || !rewardReversalSourceReference(redemption).equals(approval.getSourceReference())
                || !redemption.getId().toString().equals(stringValue(metadata.get("redemptionId")))
                || !redemption.getBurnEntryId().toString().equals(stringValue(metadata.get("burnEntryId")))) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_REVERSAL_APPROVAL_MISMATCH,
                    "Reward reversal approval scope does not match the redemption");
        }
        if (!normalize(request.idempotencyKey()).equals(approval.getIdempotencyKey())
                || !rewardReversalApprovalHash(redemption, request).equals(approval.getRequestHash())) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_REVERSAL_APPROVAL_MISMATCH,
                    "Reward reversal approval evidence no longer matches execution request");
        }
        if (!"APPROVED".equals(approval.getStatus()) && !"EXECUTED".equals(approval.getStatus())) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_REVERSAL_APPROVAL_REQUIRED,
                    "Reward redemption reversal requires an approved approval");
        }
        return approval;
    }

    private Map<String, Object> rewardReversalApprovalMetadata(
            LoyaltyRewardRedemption redemption,
            SubmitRewardRedemptionReversalApprovalRequestDto request) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("operationType", REWARD_REVERSAL_APPROVAL_OPERATION);
        metadata.put("thresholdPolicy", REWARD_REVERSAL_THRESHOLD_POLICY);
        metadata.put("redemptionId", redemption.getId().toString());
        metadata.put("rewardId", redemption.getRewardId().toString());
        metadata.put("rewardCode", redemption.getRewardCode());
        metadata.put("burnEntryId", redemption.getBurnEntryId().toString());
        metadata.put("pointsToRestore", redemption.getPointsCost());
        metadata.put("redemptionStatus", redemption.getStatus());
        metadata.put("fulfillmentStatus", redemption.getFulfillmentStatus());
        metadata.put("idempotencyKey", normalize(request.idempotencyKey()));
        metadata.put("requestMetadata", request.metadata() == null ? Map.of() : request.metadata());
        return metadata;
    }

    private String rewardReversalApprovalHash(
            LoyaltyRewardRedemption redemption,
            SubmitRewardRedemptionReversalApprovalRequestDto request) {
        return rewardReversalApprovalHash(
                redemption,
                request.idempotencyKey(),
                request.reason(),
                request.correlationId(),
                request.metadata());
    }

    private String rewardReversalApprovalHash(
            LoyaltyRewardRedemption redemption,
            ReversePointsRequestDto request) {
        return rewardReversalApprovalHash(
                redemption,
                request.idempotencyKey(),
                request.reason(),
                request.correlationId(),
                request.metadata());
    }

    private String rewardReversalApprovalHash(
            LoyaltyRewardRedemption redemption,
            String idempotencyKey,
            String reason,
            String correlationId,
            Map<String, Object> metadata) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("operation", REWARD_REVERSAL_APPROVAL_OPERATION);
        payload.put("tenantId", redemption.getTenantId());
        payload.put("applicationId", redemption.getApplicationId());
        payload.put("programId", redemption.getProgramId());
        payload.put("profileId", redemption.getProfileId());
        payload.put("redemptionId", redemption.getId().toString());
        payload.put("rewardId", redemption.getRewardId().toString());
        payload.put("burnEntryId", redemption.getBurnEntryId().toString());
        payload.put("pointsToRestore", redemption.getPointsCost());
        payload.put("idempotencyKey", normalize(idempotencyKey));
        payload.put("reason", reason);
        payload.put("correlationId", correlationId);
        payload.put("metadata", metadata == null ? Map.of() : metadata);
        return hash(payload);
    }

    private String rewardReversalSourceReference(LoyaltyRewardRedemption redemption) {
        return "reward-reversal:" + redemption.getId();
    }

    private LoyaltyAdjustmentApproval requireApprovedFulfillmentApproval(
            LoyaltyRewardRedemption redemption,
            UpdateRewardFulfillmentStatusRequestDto request,
            CurrentUser user) {
        if (request.approvalId() == null) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_FULFILLMENT_APPROVAL_REQUIRED,
                    "Reward fulfillment override requires an approved approvalId");
        }
        validateFulfillmentStatus(request.status());
        LoyaltyAdjustmentApproval approval = adjustmentApprovals.findByIdForUpdate(request.approvalId())
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_FULFILLMENT_APPROVAL_REQUIRED,
                        "Reward fulfillment approval not found"));
        Map<String, Object> metadata = readMap(approval.getMetadataJson());
        if (!REWARD_FULFILLMENT_APPROVAL_OPERATION.equalsIgnoreCase(approvalOperationType(metadata))) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH,
                    "Approval is not for reward fulfillment override");
        }
        if (!redemption.getTenantId().equals(approval.getTenantId())
                || !redemption.getApplicationId().equals(approval.getApplicationId())
                || !redemption.getProgramId().equals(approval.getProgramId())
                || !redemption.getProfileId().equals(approval.getProfileId())
                || !rewardFulfillmentSourceReference(redemption).equals(approval.getSourceReference())
                || !redemption.getId().toString().equals(stringValue(metadata.get("redemptionId")))
                || !redemption.getRewardId().toString().equals(stringValue(metadata.get("rewardId")))) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH,
                    "Reward fulfillment approval scope does not match the redemption");
        }
        if (!normalize(request.idempotencyKey()).equals(approval.getIdempotencyKey())
                || !rewardFulfillmentApprovalHash(redemption, request).equals(approval.getRequestHash())) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH,
                    "Reward fulfillment approval evidence no longer matches execution request");
        }
        if (!"APPROVED".equals(approval.getStatus()) && !"EXECUTED".equals(approval.getStatus())) {
            throw ConflictException.coded(
                    LOYALTY_REWARD_FULFILLMENT_APPROVAL_REQUIRED,
                    "Reward fulfillment override requires an approved approval");
        }
        String executor = actor(user);
        if (executor != null
                && approval.getReviewedBy() != null
                && executor.equalsIgnoreCase(approval.getReviewedBy())) {
            throw ForbiddenException.coded(
                    LOYALTY_REWARD_FULFILLMENT_APPROVAL_MISMATCH,
                    "Reviewer cannot execute their own reward fulfillment approval");
        }
        return approval;
    }

    private Map<String, Object> rewardFulfillmentApprovalMetadata(
            LoyaltyRewardRedemption redemption,
            SubmitRewardFulfillmentApprovalRequestDto request) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("operationType", REWARD_FULFILLMENT_APPROVAL_OPERATION);
        metadata.put("thresholdPolicy", REWARD_FULFILLMENT_THRESHOLD_POLICY);
        metadata.put("redemptionId", redemption.getId().toString());
        metadata.put("rewardId", redemption.getRewardId().toString());
        metadata.put("rewardCode", redemption.getRewardCode());
        metadata.put("currentFulfillmentStatus", redemption.getFulfillmentStatus());
        metadata.put("currentFulfillmentRef", blankToNull(redemption.getFulfillmentRef()));
        metadata.put("targetFulfillmentStatus", normalizeFulfillmentStatus(request.status()));
        metadata.put("targetFulfillmentRef", blankToNull(request.fulfillmentRef()));
        metadata.put("targetFulfillmentNote", blankToNull(request.note()));
        metadata.put("idempotencyKey", normalize(request.idempotencyKey()));
        metadata.put("requestMetadata", request.metadata() == null ? Map.of() : request.metadata());
        return metadata;
    }

    private String rewardFulfillmentApprovalHash(
            LoyaltyRewardRedemption redemption,
            SubmitRewardFulfillmentApprovalRequestDto request) {
        return rewardFulfillmentApprovalHash(
                redemption,
                request.status(),
                request.fulfillmentRef(),
                request.note(),
                request.idempotencyKey(),
                request.reason(),
                request.correlationId(),
                request.metadata());
    }

    private String rewardFulfillmentApprovalHash(
            LoyaltyRewardRedemption redemption,
            UpdateRewardFulfillmentStatusRequestDto request) {
        return rewardFulfillmentApprovalHash(
                redemption,
                request.status(),
                request.fulfillmentRef(),
                request.note(),
                request.idempotencyKey(),
                request.reason(),
                request.correlationId(),
                request.metadata());
    }

    private String rewardFulfillmentApprovalHash(
            LoyaltyRewardRedemption redemption,
            String status,
            String fulfillmentRef,
            String note,
            String idempotencyKey,
            String reason,
            String correlationId,
            Map<String, Object> metadata) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("operation", REWARD_FULFILLMENT_APPROVAL_OPERATION);
        payload.put("tenantId", redemption.getTenantId());
        payload.put("applicationId", redemption.getApplicationId());
        payload.put("programId", redemption.getProgramId());
        payload.put("profileId", redemption.getProfileId());
        payload.put("redemptionId", redemption.getId().toString());
        payload.put("rewardId", redemption.getRewardId().toString());
        payload.put("currentFulfillmentStatus", redemption.getFulfillmentStatus());
        payload.put("currentFulfillmentRef", blankToNull(redemption.getFulfillmentRef()));
        payload.put("targetFulfillmentStatus", normalizeFulfillmentStatus(status));
        payload.put("targetFulfillmentRef", blankToNull(fulfillmentRef));
        payload.put("targetFulfillmentNote", blankToNull(note));
        payload.put("idempotencyKey", normalize(idempotencyKey));
        payload.put("reason", reason);
        payload.put("correlationId", correlationId);
        payload.put("metadata", metadata == null ? Map.of() : metadata);
        return hash(payload);
    }

    private String rewardFulfillmentSourceReference(LoyaltyRewardRedemption redemption) {
        return "reward-fulfillment:" + redemption.getId();
    }

    private String validateFulfillmentStatus(String status) {
        String normalized = normalizeFulfillmentStatus(status);
        if (!FULFILLMENT_STATUSES.contains(normalized)) {
            throw BadRequestException.coded(
                    LOYALTY_REWARD_INVALID_REQUEST,
                    "Unsupported reward fulfillment status: " + status);
        }
        return normalized;
    }

    private String normalizeFulfillmentStatus(String status) {
        return status == null || status.isBlank() ? "" : status.trim().toUpperCase();
    }

    private LearnerRewardDto learnerRewardDto(LoyaltyReward reward, String profileId, Instant now) {
        LoyaltyProgram program = programById(reward.getProgramUuid());
        Optional<LoyaltyAccount> account = accounts.findByTenantIdAndApplicationIdAndProgramIdAndProfileId(
                reward.getTenantId(), reward.getApplicationId(), reward.getProgramId(), profileId);
        long ledgerBalance = account.map(value -> pointsEntries.balance(value.getId())).orElse(0L);
        long spendableBalance = account
                .map(value -> pointLots.activeRemainingPoints(value.getId(), now))
                .orElse(0L);
        long redeemed = redemptions.countByRewardIdAndStatus(reward.getId(), "COMMITTED");
        long profileRedeemed = redemptions.countByRewardIdAndProfileIdAndStatus(reward.getId(), profileId, "COMMITTED");
        List<String> reasons = new ArrayList<>();
        if (!"ACTIVE".equals(program.getStatus())) {
            reasons.add("PROGRAM_NOT_ACTIVE");
        }
        if (!reward.activeAt(now)) {
            reasons.add("REWARD_NOT_ACTIVE");
        }
        if (account.isEmpty()) {
            reasons.add("NO_LOYALTY_ACCOUNT");
        }
        if (spendableBalance < reward.getPointsCost()) {
            reasons.add("INSUFFICIENT_BALANCE");
        }
        Long inventoryRemaining = null;
        if (reward.getInventoryLimit() != null) {
            inventoryRemaining = Math.max(0L, reward.getInventoryLimit() - redeemed);
            if (inventoryRemaining == 0L) {
                reasons.add("OUT_OF_STOCK");
            }
        }
        Integer perProfileRemaining = null;
        if (reward.getPerProfileLimit() != null) {
            perProfileRemaining = (int) Math.max(0L, reward.getPerProfileLimit() - profileRedeemed);
            if (perProfileRemaining == 0) {
                reasons.add("PROFILE_LIMIT_REACHED");
            }
        }
        return new LearnerRewardDto(
                reward.getId(),
                reward.getTenantId(),
                reward.getApplicationId(),
                reward.getProgramId(),
                reward.getRewardCode(),
                reward.getName(),
                reward.getDescription(),
                reward.getPointsCost(),
                program.getPointUnit(),
                ledgerBalance,
                spendableBalance,
                reasons.isEmpty(),
                reasons,
                inventoryRemaining,
                perProfileRemaining,
                reward.getStartsAt(),
                reward.getEndsAt(),
                reward.getFulfillmentType());
    }

    private LoyaltyRewardDto rewardDto(LoyaltyReward reward) {
        return new LoyaltyRewardDto(
                reward.getId(),
                reward.getProgramUuid(),
                reward.getTenantId(),
                reward.getApplicationId(),
                reward.getProgramId(),
                reward.getRewardCode(),
                reward.getName(),
                reward.getDescription(),
                reward.getPointsCost(),
                reward.getStatus(),
                reward.getStartsAt(),
                reward.getEndsAt(),
                reward.getInventoryLimit(),
                reward.getPerProfileLimit(),
                reward.getFulfillmentType(),
                readMap(reward.getFulfillmentConfigJson()),
                redemptions.countByRewardIdAndStatus(reward.getId(), "COMMITTED"),
                reward.getCreatedBy(),
                reward.getCreatedAt(),
                reward.getUpdatedAt());
    }

    private LoyaltyAdjustmentApprovalDto approvalDto(LoyaltyAdjustmentApproval approval) {
        Map<String, Object> metadata = readMap(approval.getMetadataJson());
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
                approvalOperationType(metadata),
                metadata);
    }

    private LoyaltyRewardRedemptionDto redemptionDto(LoyaltyRewardRedemption redemption, boolean idempotencyReplay) {
        return new LoyaltyRewardRedemptionDto(
                redemption.getId(),
                redemption.getRewardId(),
                redemption.getAccountId(),
                redemption.getBurnEntryId(),
                redemption.getReversalEntryId(),
                redemption.getTenantId(),
                redemption.getApplicationId(),
                redemption.getProgramId(),
                redemption.getProfileId(),
                redemption.getRewardCode(),
                redemption.getPointsCost(),
                redemption.getSourceReference(),
                redemption.getStatus(),
                redemption.getFulfillmentStatus(),
                redemption.getFulfillmentRef(),
                redemption.getFulfillmentNote(),
                redemption.getFulfillmentProvider(),
                redemption.getFulfillmentAttemptCount(),
                redemption.getFulfillmentLastAttemptAt(),
                redemption.getFulfillmentNextAttemptAt(),
                redemption.getFulfillmentSlaDueAt(),
                redemption.getFulfillmentErrorClass(),
                redemption.getFulfillmentErrorMessage(),
                redemption.getFulfillmentCallbackReceivedAt(),
                redemption.getFulfillmentCallbackPayloadHash(),
                readMap(redemption.getRewardSnapshotJson()),
                redemption.getCorrelationId(),
                redemption.getNote(),
                readMap(redemption.getMetadataJson()),
                redemption.getRedeemedAt(),
                redemption.getFulfilledAt(),
                redemption.getReversedAt(),
                idempotencyReplay);
    }

    private void emitRewardEvent(
            LoyaltyRewardRedemption redemption,
            String eventType,
            String actorId,
            String note,
            String correlationId,
            Map<String, Object> extra) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("eventId", UUID.randomUUID().toString());
        payload.put("schemaVersion", 1);
        payload.put("eventType", eventType);
        payload.put("tenantId", redemption.getTenantId());
        payload.put("applicationId", redemption.getApplicationId());
        payload.put("programId", redemption.getProgramId());
        payload.put("rewardId", redemption.getRewardId().toString());
        payload.put("redemptionId", redemption.getId().toString());
        payload.put("accountId", redemption.getAccountId().toString());
        payload.put("burnEntryId", redemption.getBurnEntryId().toString());
        payload.put("reversalEntryId", redemption.getReversalEntryId() == null
                ? null
                : redemption.getReversalEntryId().toString());
        payload.put("profileId", redemption.getProfileId());
        payload.put("rewardCode", redemption.getRewardCode());
        payload.put("pointsCost", redemption.getPointsCost());
        payload.put("status", redemption.getStatus());
        payload.put("fulfillmentStatus", redemption.getFulfillmentStatus());
        payload.put("fulfillmentRef", redemption.getFulfillmentRef());
        payload.put("fulfillmentProvider", redemption.getFulfillmentProvider());
        payload.put("fulfillmentAttemptCount", redemption.getFulfillmentAttemptCount());
        payload.put("fulfillmentNextAttemptAt", redemption.getFulfillmentNextAttemptAt());
        payload.put("fulfillmentSlaDueAt", redemption.getFulfillmentSlaDueAt());
        payload.put("fulfillmentErrorClass", redemption.getFulfillmentErrorClass());
        payload.put("sourceReference", redemption.getSourceReference());
        payload.put("correlationId", correlationId);
        payload.put("actorId", actorId);
        payload.put("note", note);
        payload.put("redeemedAt", redemption.getRedeemedAt());
        payload.put("fulfilledAt", redemption.getFulfilledAt());
        payload.put("reversedAt", redemption.getReversedAt());
        payload.put("metadata", extra == null ? Map.of() : extra);
        outboxEvents.save(new OutboxEvent(
                redemption.getId(),
                "loyalty-reward-redemption",
                eventType,
                json(payload)));
    }

    private LoyaltyProgram programByScope(String tenantId, String applicationId, String programId) {
        return programs.findByTenantIdAndApplicationIdAndProgramId(
                        normalize(tenantId), normalize(applicationId), normalize(programId))
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_PROGRAM_NOT_FOUND, "Loyalty program not found"));
    }

    private LoyaltyProgram programById(UUID programId) {
        return programs.findById(programId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_PROGRAM_NOT_FOUND, "Loyalty program not found"));
    }

    private LoyaltyReward rewardById(UUID rewardId) {
        return rewards.findById(rewardId)
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_REWARD_NOT_FOUND, "Loyalty reward not found"));
    }

    private void requireActiveProgram(LoyaltyProgram program) {
        if (!"ACTIVE".equals(program.getStatus())) {
            throw ForbiddenException.coded(LOYALTY_PROGRAM_INACTIVE, "Loyalty program is not active");
        }
    }

    private void requireReadForScope(Optional<String> tenantId, Optional<String> applicationId, CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant != null && application != null) {
            access.requireReadAccess(tenant, application, user);
            return;
        }
        access.requirePlatformAdmin(user);
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw ForbiddenException.coded(
                    LOYALTY_REWARD_INVALID_REQUEST,
                    "Authenticated learner is required for reward redemption");
        }
    }

    private void validateWindow(Instant startsAt, Instant endsAt) {
        if (startsAt != null && endsAt != null && !endsAt.isAfter(startsAt)) {
            throw BadRequestException.coded(
                    LOYALTY_REWARD_INVALID_REQUEST,
                    "Reward endsAt must be after startsAt");
        }
    }

    private String rewardRequestHash(LoyaltyReward reward, String profileId, RedeemRewardRequestDto request) {
        return hash(Map.of(
                "operation", "REWARD_REDEEM",
                "rewardId", reward.getId().toString(),
                "profileId", profileId,
                "idempotencyKey", normalize(request.idempotencyKey()),
                "metadata", request.metadata() == null ? Map.of() : request.metadata()));
    }

    private Map<String, Object> rewardSnapshot(LoyaltyReward reward, LoyaltyProgram program) {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("rewardId", reward.getId().toString());
        snapshot.put("programUuid", reward.getProgramUuid().toString());
        snapshot.put("tenantId", reward.getTenantId());
        snapshot.put("applicationId", reward.getApplicationId());
        snapshot.put("programId", reward.getProgramId());
        snapshot.put("rewardCode", reward.getRewardCode());
        snapshot.put("name", reward.getName());
        snapshot.put("description", reward.getDescription());
        snapshot.put("pointsCost", reward.getPointsCost());
        snapshot.put("pointUnit", program.getPointUnit());
        snapshot.put("status", reward.getStatus());
        snapshot.put("startsAt", reward.getStartsAt());
        snapshot.put("endsAt", reward.getEndsAt());
        snapshot.put("inventoryLimit", reward.getInventoryLimit());
        snapshot.put("perProfileLimit", reward.getPerProfileLimit());
        snapshot.put("fulfillmentType", reward.getFulfillmentType());
        return snapshot;
    }

    private String rewardSourceReference(UUID rewardId, String idempotencyKey) {
        return "reward:" + rewardId + ":" + sha256Hex(idempotencyKey).substring(0, 24);
    }

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, String correlationId, Map<String, Object> payload) {
        auditEvents.save(new LoyaltyAuditEvent(
                tenantId, applicationId, aggregateId, aggregateType, action, actorId, note, correlationId,
                json(payload)));
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

    private String approvalOperationType(Map<String, Object> metadata) {
        String operationType = stringValue(metadata.get("operationType"));
        return operationType == null ? "ADJUSTMENT" : operationType;
    }

    private String stringValue(Object value) {
        return value == null || value.toString().isBlank() ? null : value.toString().trim();
    }

    private String firstPresent(String... values) {
        if (values == null) {
            return null;
        }
        for (String value : values) {
            String normalized = blankToNull(value);
            if (normalized != null) {
                return normalized;
            }
        }
        return null;
    }

    private String json(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, "Unable to serialize loyalty reward payload");
        }
    }

    private String hash(Object value) {
        return "sha256:" + sha256Hex(json(value));
    }

    private String sha256Hex(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
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

    private int boundedLimit(int requested) {
        return Math.max(1, Math.min(requested, 200));
    }

    private String normalized(String value) {
        String normalized = blankToNull(value);
        return normalized == null ? null : normalized.toUpperCase();
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim();
    }

    private String blankToNull(String value) {
        String normalized = normalize(value);
        return normalized.isBlank() ? null : normalized;
    }

    private record FulfillmentOutcome(
            String status,
            String fulfillmentRef,
            String note,
            String errorClass,
            String errorMessage,
            boolean retryable,
            Map<String, Object> payload) {

        static FulfillmentOutcome success(
                String status,
                String fulfillmentRef,
                String note,
                Map<String, Object> payload) {
            return new FulfillmentOutcome(status, fulfillmentRef, note, null, null, false,
                    payload == null ? Map.of() : payload);
        }

        static FulfillmentOutcome failed(
                String errorClass,
                String errorMessage,
                boolean retryable,
                Map<String, Object> payload) {
            return new FulfillmentOutcome("FAILED", null, null, errorClass, errorMessage, retryable,
                    payload == null ? Map.of() : payload);
        }
    }
}
