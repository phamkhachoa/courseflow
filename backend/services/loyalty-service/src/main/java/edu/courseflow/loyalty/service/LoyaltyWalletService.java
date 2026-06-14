package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_REWARD_INVALID_REQUEST;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyBalanceDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyWalletAccountDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyWalletResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerLoyaltyWalletTotalsDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LearnerRewardDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyBalanceBucketDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyRewardRedemptionDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsEntryDto;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyPointLot;
import edu.courseflow.loyalty.model.LoyaltyPointsEntry;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyReward;
import edu.courseflow.loyalty.model.LoyaltyRewardRedemption;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointLotRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRedemptionRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyWalletService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final LoyaltyAccountRepository accounts;
    private final LoyaltyProgramRepository programs;
    private final LoyaltyPointsEntryRepository pointsEntries;
    private final LoyaltyPointLotRepository pointLots;
    private final LoyaltyRewardRepository rewards;
    private final LoyaltyRewardRedemptionRepository redemptions;
    private final ObjectMapper objectMapper;

    public LoyaltyWalletService(
            LoyaltyAccountRepository accounts,
            LoyaltyProgramRepository programs,
            LoyaltyPointsEntryRepository pointsEntries,
            LoyaltyPointLotRepository pointLots,
            LoyaltyRewardRepository rewards,
            LoyaltyRewardRedemptionRepository redemptions,
            ObjectMapper objectMapper) {
        this.accounts = accounts;
        this.programs = programs;
        this.pointsEntries = pointsEntries;
        this.pointLots = pointLots;
        this.rewards = rewards;
        this.redemptions = redemptions;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public LearnerLoyaltyWalletResponseDto learnerWallet(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<Integer> limit,
            CurrentUser user) {
        requireAuthenticated(user);
        String profileId = String.valueOf(user.id());
        Instant generatedAt = Instant.now();
        int pageSize = boundedLimit(limit.orElse(20));
        List<String> warnings = new ArrayList<>();
        List<LoyaltyAccount> scopedAccounts = accounts.search(
                blankToNull(tenantId.orElse(null)),
                blankToNull(applicationId.orElse(null)),
                blankToNull(programId.orElse(null)),
                profileId,
                null,
                PageRequest.of(0, Math.min(pageSize, 50)));
        if (scopedAccounts.isEmpty()) {
            warnings.add("NO_LOYALTY_ACCOUNTS_FOR_LEARNER");
        }

        List<LearnerLoyaltyWalletAccountDto> walletAccounts = scopedAccounts.stream()
                .map(account -> walletAccount(account, generatedAt, pageSize))
                .toList();
        walletAccounts.stream()
                .flatMap(account -> account.balance().warnings().stream())
                .distinct()
                .forEach(warnings::add);

        List<LearnerRewardDto> availableRewards = learnerRewards(scopedAccounts, profileId, generatedAt, pageSize);
        List<LoyaltyRewardRedemptionDto> recentRedemptions = redemptions.search(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(programId.orElse(null)),
                        profileId,
                        null,
                        null,
                        null,
                        null,
                        null,
                        PageRequest.of(0, pageSize))
                .stream()
                .map(redemption -> redemptionDto(redemption, false))
                .toList();

        return new LearnerLoyaltyWalletResponseDto(
                profileId,
                generatedAt,
                totals(walletAccounts),
                walletAccounts,
                availableRewards,
                recentRedemptions,
                warnings.stream().distinct().toList());
    }

    private LearnerLoyaltyWalletAccountDto walletAccount(LoyaltyAccount account, Instant now, int limit) {
        return new LearnerLoyaltyWalletAccountDto(
                learnerBalance(account, now),
                buckets(account, now, limit),
                pointsEntries.findTop100ByAccountIdOrderByCreatedAtDesc(account.getId())
                        .stream()
                        .limit(limit)
                        .map(this::entryDto)
                        .toList());
    }

    private LearnerLoyaltyWalletTotalsDto totals(List<LearnerLoyaltyWalletAccountDto> accounts) {
        List<LearnerLoyaltyBalanceDto> balances = accounts.stream().map(LearnerLoyaltyWalletAccountDto::balance).toList();
        Instant nextExpiryAt = balances.stream()
                .map(LearnerLoyaltyBalanceDto::nextExpiryAt)
                .filter(value -> value != null)
                .min(Comparator.naturalOrder())
                .orElse(null);
        return new LearnerLoyaltyWalletTotalsDto(
                balances.stream().mapToLong(LearnerLoyaltyBalanceDto::ledgerBalance).sum(),
                balances.stream().mapToLong(LearnerLoyaltyBalanceDto::activePoints).sum(),
                balances.stream().mapToLong(LearnerLoyaltyBalanceDto::expiredPoints).sum(),
                balances.stream().mapToLong(LearnerLoyaltyBalanceDto::expiringSoonPoints).sum(),
                balances.size(),
                (int) balances.stream()
                        .filter(balance -> "ACTIVE".equalsIgnoreCase(balance.accountStatus())
                                && "ACTIVE".equalsIgnoreCase(balance.programStatus()))
                        .count(),
                nextExpiryAt);
    }

    private List<LearnerRewardDto> learnerRewards(
            List<LoyaltyAccount> scopedAccounts,
            String profileId,
            Instant now,
            int limit) {
        Map<UUID, LearnerRewardDto> results = new LinkedHashMap<>();
        for (LoyaltyAccount account : scopedAccounts) {
            rewards.search(
                            account.getTenantId(),
                            account.getApplicationId(),
                            account.getProgramId(),
                            null,
                            now,
                            PageRequest.of(0, limit))
                    .forEach(reward -> results.putIfAbsent(reward.getId(), learnerRewardDto(reward, profileId, now)));
        }
        return results.values().stream().limit(limit).toList();
    }

    private LearnerLoyaltyBalanceDto learnerBalance(LoyaltyAccount account, Instant now) {
        LoyaltyProgram program = programFor(account);
        long ledgerBalance = pointsEntries.balance(account.getId());
        List<LoyaltyPointLot> lots = pointLots.findByAccountIdOrderByExpiresAtAscOccurredAtAsc(account.getId())
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
                warnings);
    }

    private List<LoyaltyBalanceBucketDto> buckets(LoyaltyAccount account, Instant now, int limit) {
        return pointLots.findByAccountIdOrderByExpiresAtAscOccurredAtAsc(account.getId())
                .stream()
                .filter(lot -> lot.getRemainingPoints() > 0)
                .limit(limit)
                .map(lot -> bucketDto(lot, now))
                .toList();
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

    private LoyaltyBalanceBucketDto bucketDto(LoyaltyPointLot lot, Instant now) {
        String status = isExpired(lot, now) ? "EXPIRED" : "ACTIVE";
        return new LoyaltyBalanceBucketDto(
                lot.getSourceEntryId(),
                lot.getAccountId(),
                lot.getProfileId(),
                lot.getEntryType(),
                lot.getOriginalPoints(),
                lot.getConsumedPoints(),
                lot.getRemainingPoints(),
                lot.getSourceReference(),
                lot.getOccurredAt(),
                lot.getExpiresAt(),
                status);
    }

    private PointsEntryDto entryDto(LoyaltyPointsEntry entry) {
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

    private LoyaltyProgram programFor(LoyaltyAccount account) {
        return programById(account.getProgramUuid());
    }

    private LoyaltyProgram programById(UUID programId) {
        return programs.findById(programId)
                .orElseThrow(() -> ForbiddenException.coded(
                        LOYALTY_REWARD_INVALID_REQUEST,
                        "Loyalty program is unavailable for learner wallet"));
    }

    private boolean isExpired(LoyaltyPointLot lot, Instant now) {
        return lot.getExpiresAt() != null && !lot.getExpiresAt().isAfter(now);
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw ForbiddenException.coded(
                    LOYALTY_REWARD_INVALID_REQUEST,
                    "Authenticated learner is required for loyalty wallet");
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

    private int boundedLimit(int requested) {
        return Math.max(1, Math.min(requested, 50));
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
