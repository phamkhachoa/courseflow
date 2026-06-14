package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_INACTIVE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_ALREADY_EXISTS;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_IDEMPOTENCY_KEY_REUSED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_INACTIVE;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_INVALID_REQUEST;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_OUT_OF_STOCK;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_PROFILE_LIMIT_REACHED;

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
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardRedemptionDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardRedemptionQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RedeemRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardFulfillmentStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateRewardStatusRequestDto;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyAuditEvent;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyReward;
import edu.courseflow.loyalty.model.LoyaltyRewardRedemption;
import edu.courseflow.loyalty.model.OutboxEvent;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyAuditEventRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointLotRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
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
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyRewardService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final LoyaltyRewardRepository rewards;
    private final LoyaltyRewardRedemptionRepository redemptions;
    private final LoyaltyProgramRepository programs;
    private final LoyaltyAccountRepository accounts;
    private final LoyaltyPointsEntryRepository pointsEntries;
    private final LoyaltyPointLotRepository pointLots;
    private final LoyaltyAuditEventRepository auditEvents;
    private final OutboxEventRepository outboxEvents;
    private final LoyaltyAccessService access;
    private final LoyaltyService loyaltyService;
    private final ObjectMapper objectMapper;

    public LoyaltyRewardService(
            LoyaltyRewardRepository rewards,
            LoyaltyRewardRedemptionRepository redemptions,
            LoyaltyProgramRepository programs,
            LoyaltyAccountRepository accounts,
            LoyaltyPointsEntryRepository pointsEntries,
            LoyaltyPointLotRepository pointLots,
            LoyaltyAuditEventRepository auditEvents,
            OutboxEventRepository outboxEvents,
            LoyaltyAccessService access,
            LoyaltyService loyaltyService,
            ObjectMapper objectMapper) {
        this.rewards = rewards;
        this.redemptions = redemptions;
        this.programs = programs;
        this.accounts = accounts;
        this.pointsEntries = pointsEntries;
        this.pointLots = pointLots;
        this.auditEvents = auditEvents;
        this.outboxEvents = outboxEvents;
        this.access = access;
        this.loyaltyService = loyaltyService;
        this.objectMapper = objectMapper;
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
    public LoyaltyRewardRedemptionDto reverseRedemption(
            UUID redemptionId,
            ReversePointsRequestDto request,
            CurrentUser user) {
        LoyaltyRewardRedemption redemption = redemptions.findByIdForUpdate(redemptionId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_REWARD_NOT_FOUND,
                        "Loyalty reward redemption not found"));
        access.requireAdminAccess(redemption.getTenantId(), redemption.getApplicationId(), user);
        if ("REVERSED".equals(redemption.getStatus())) {
            return redemptionDto(redemption, true);
        }
        PointsMutationResponseDto reversal = loyaltyService.reverseRewardBurn(redemption.getBurnEntryId(), request, user);
        redemption.markReversed(reversal.entryId());
        LoyaltyRewardRedemption saved = redemptions.save(redemption);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                "loyalty-reward-redemption", "loyalty.reward.reversed", actor(user),
                request.reason(), request.correlationId(), Map.of(
                        "rewardId", saved.getRewardId().toString(),
                        "rewardCode", saved.getRewardCode(),
                        "burnEntryId", saved.getBurnEntryId().toString(),
                        "reversalEntryId", reversal.entryId().toString(),
                        "pointsCost", saved.getPointsCost()));
        emitRewardEvent(saved, "loyalty.reward.reversed", actor(user), request.reason(), request.correlationId(),
                Map.of(
                        "reversalEntryId", reversal.entryId().toString(),
                        "idempotencyReplay", reversal.idempotencyReplay()));
        return redemptionDto(saved, reversal.idempotencyReplay());
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
        try {
            redemption.updateFulfillment(request.status(), request.fulfillmentRef(), request.note());
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_REWARD_INVALID_REQUEST, ex.getMessage());
        }
        LoyaltyRewardRedemption saved = redemptions.save(redemption);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(),
                "loyalty-reward-redemption", "loyalty.reward.fulfillment_status_changed", actor(user),
                request.note(), saved.getCorrelationId(), Map.of(
                        "rewardId", saved.getRewardId().toString(),
                        "rewardCode", saved.getRewardCode(),
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "fulfillmentRef", saved.getFulfillmentRef() == null ? "" : saved.getFulfillmentRef()));
        emitRewardEvent(saved, "loyalty.reward.fulfillment_status_changed", actor(user), request.note(),
                saved.getCorrelationId(), Map.of(
                        "fulfillmentStatus", saved.getFulfillmentStatus(),
                        "fulfillmentRef", saved.getFulfillmentRef() == null ? "" : saved.getFulfillmentRef()));
        return redemptionDto(saved, false);
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
}
