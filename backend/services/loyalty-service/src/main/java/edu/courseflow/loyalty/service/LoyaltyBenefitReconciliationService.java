package edu.courseflow.loyalty.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyBenefitReconciliationEntryDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyBenefitReconciliationQueryResponseDto;
import edu.courseflow.loyalty.model.LoyaltyPointsEntry;
import edu.courseflow.loyalty.model.LoyaltyPromotionPointEffect;
import edu.courseflow.loyalty.model.LoyaltyRewardRedemption;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyPromotionPointEffectRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRedemptionRepository;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyBenefitReconciliationService {

    private static final int DEFAULT_LIMIT = 50;
    private static final int MAX_LIMIT = 200;

    private final LoyaltyPromotionPointEffectRepository expectedEffects;
    private final LoyaltyPointsEntryRepository pointsEntries;
    private final LoyaltyRewardRedemptionRepository rewardRedemptions;
    private final LoyaltyAccessService access;

    public LoyaltyBenefitReconciliationService(
            LoyaltyPromotionPointEffectRepository expectedEffects,
            LoyaltyPointsEntryRepository pointsEntries,
            LoyaltyRewardRedemptionRepository rewardRedemptions,
            LoyaltyAccessService access) {
        this.expectedEffects = expectedEffects;
        this.pointsEntries = pointsEntries;
        this.rewardRedemptions = rewardRedemptions;
        this.access = access;
    }

    @Transactional(readOnly = true)
    public LoyaltyBenefitReconciliationQueryResponseDto query(
            String tenantId,
            String applicationId,
            Optional<String> programId,
            Optional<String> profileId,
            Optional<String> redemptionId,
            Optional<String> itemType,
            Optional<String> status,
            Optional<Boolean> includeMatched,
            Optional<Instant> from,
            Optional<Instant> to,
            Optional<Integer> limit,
            CurrentUser user) {
        String tenant = requiredText(tenantId, "tenantId");
        String application = requiredText(applicationId, "applicationId");
        access.requireReadAccess(tenant, application, user);
        String normalizedItemType = itemType.map(this::normalizeItemType).orElse(null);
        String normalizedStatus = status.map(this::normalizeStatus).orElse(null);
        Instant fromValue = from.orElse(null);
        Instant toValue = to.orElse(null);
        if (fromValue != null && toValue != null && !fromValue.isBefore(toValue)) {
            throw new BadRequestException("Benefit reconciliation from timestamp must be before to timestamp");
        }
        int pageSize = Math.max(1, Math.min(limit.orElse(DEFAULT_LIMIT), MAX_LIMIT));
        boolean showMatched = includeMatched.orElse(false) || "MATCHED".equals(normalizedStatus);
        List<LoyaltyBenefitReconciliationEntryDto> rows = new ArrayList<>();
        if (normalizedItemType == null || "PROMOTION_POINTS".equals(normalizedItemType)) {
            expectedEffects.search(
                            tenant,
                            application,
                            blankToNull(programId.orElse(null)),
                            blankToNull(profileId.orElse(null)),
                            blankToNull(redemptionId.orElse(null)),
                            null,
                            fromValue,
                            toValue,
                            PageRequest.of(0, pageSize + 1))
                    .stream()
                    .map(this::promotionEffectEntry)
                    .forEach(rows::add);
        }
        if (normalizedItemType == null || "REWARD_REVERSE".equals(normalizedItemType)) {
            rewardRedemptions.searchReversedForReconciliation(
                            tenant,
                            application,
                            blankToNull(programId.orElse(null)),
                            blankToNull(profileId.orElse(null)),
                            fromValue,
                            toValue,
                            PageRequest.of(0, pageSize + 1))
                    .stream()
                    .map(this::rewardReverseEntry)
                    .forEach(rows::add);
        }
        List<LoyaltyBenefitReconciliationEntryDto> filtered = rows.stream()
                .filter(row -> normalizedStatus == null || normalizedStatus.equals(row.reconciliationStatus()))
                .filter(row -> showMatched || !"MATCHED".equals(row.reconciliationStatus()))
                .limit(pageSize + 1L)
                .toList();
        boolean hasMore = filtered.size() > pageSize || rows.size() > pageSize;
        return new LoyaltyBenefitReconciliationQueryResponseDto(
                filtered.stream().limit(pageSize).toList(),
                pageSize,
                hasMore,
                Instant.now());
    }

    private LoyaltyBenefitReconciliationEntryDto promotionEffectEntry(LoyaltyPromotionPointEffect effect) {
        if ("EARN".equals(effect.getExpectedEntryType())) {
            LoyaltyPointsEntry ledgerEntry = findEntry(effect, "EARN", effect.getOriginalSourceReference()).orElse(null);
            return effectDto(
                    effect,
                    ledgerEntry == null ? "PROMOTION_EARN_MISSING" : "MATCHED",
                    ledgerEntry == null
                            ? List.of("PROMOTION_EARN_MISSING", "Promotion committed a points earn intent but no loyalty EARN ledger entry exists")
                            : List.of(),
                    ledgerEntry == null ? "HIGH" : "LOW",
                    ledgerEntry,
                    null);
        }
        LoyaltyPointsEntry originalEarn = findEntry(effect, "EARN", effect.getOriginalSourceReference()).orElse(null);
        if (originalEarn == null) {
            return effectDto(
                    effect,
                    "PROMOTION_REVERSE_ORIGINAL_EARN_MISSING",
                    List.of("PROMOTION_REVERSE_ORIGINAL_EARN_MISSING",
                            "Promotion reversed a points intent but the original loyalty EARN ledger entry is missing"),
                    "HIGH",
                    null,
                    null);
        }
        LoyaltyPointsEntry reversal = pointsEntries.findFirstByReversalOfEntryId(originalEarn.getId()).orElse(null);
        if (reversal != null && !validPromotionReversal(originalEarn, reversal)) {
            return effectDto(
                    effect,
                    "PROMOTION_REVERSE_LEDGER_MISMATCH",
                    List.of("PROMOTION_REVERSE_LEDGER_MISMATCH",
                            "Promotion reversal ledger entry exists but entry type, restored points or account do not match the original earn"),
                    "HIGH",
                    reversal,
                    originalEarn.getId());
        }
        return effectDto(
                effect,
                reversal == null ? "PROMOTION_REVERSE_MISSING" : "MATCHED",
                reversal == null
                        ? List.of("PROMOTION_REVERSE_MISSING", "Promotion reversed a points intent but loyalty points were not reversed")
                        : List.of(),
                reversal == null ? "HIGH" : "LOW",
                reversal,
                originalEarn.getId());
    }

    private LoyaltyBenefitReconciliationEntryDto rewardReverseEntry(LoyaltyRewardRedemption redemption) {
        LoyaltyPointsEntry reversal = redemption.getReversalEntryId() == null
                ? null
                : pointsEntries.findById(redemption.getReversalEntryId()).orElse(null);
        String status = "MATCHED";
        List<String> reasons = List.of();
        String severity = "LOW";
        if (redemption.getReversalEntryId() == null) {
            status = "REWARD_REVERSE_POINTS_MISSING";
            reasons = List.of("REWARD_REVERSE_POINTS_MISSING",
                    "Reward redemption is REVERSED but has no reversal ledger entry id");
            severity = "HIGH";
        } else if (reversal == null) {
            status = "REWARD_REVERSE_LEDGER_MISSING";
            reasons = List.of("REWARD_REVERSE_LEDGER_MISSING",
                    "Reward redemption references a reversal ledger entry that does not exist");
            severity = "HIGH";
        } else if (!"REVERSE".equals(reversal.getEntryType()) || reversal.getPointsDelta() != redemption.getPointsCost()) {
            status = "REWARD_REVERSE_LEDGER_MISMATCH";
            reasons = List.of("REWARD_REVERSE_LEDGER_MISMATCH",
                    "Reward reversal ledger entry exists but entry type or restored points do not match redemption cost");
            severity = "HIGH";
        }
        return new LoyaltyBenefitReconciliationEntryDto(
                "reward:" + redemption.getId(),
                status,
                reasons,
                "REWARD_REVERSE",
                severity,
                redemption.getTenantId(),
                redemption.getApplicationId(),
                redemption.getProgramId(),
                redemption.getProfileId(),
                null,
                null,
                "REVERSE",
                redemption.getPointsCost(),
                redemption.getSourceReference(),
                redemption.getIdempotencyKey(),
                reversal == null ? null : reversal.getId(),
                redemption.getBurnEntryId(),
                redemption.getId(),
                redemption.getBurnEntryId(),
                redemption.getReversalEntryId(),
                redemption.getRewardCode(),
                redemption.getStatus(),
                redemption.getPointsCost(),
                null,
                null,
                null,
                redemption.getCorrelationId(),
                redemption.getUpdatedAt(),
                reversal == null ? null : reversal.getCreatedAt(),
                redemption.getReversedAt());
    }

    private boolean validPromotionReversal(LoyaltyPointsEntry originalEarn, LoyaltyPointsEntry reversal) {
        return "REVERSE".equals(reversal.getEntryType())
                && reversal.getPointsDelta() == originalEarn.getPointsDelta()
                && reversal.getAccountId().equals(originalEarn.getAccountId());
    }

    private LoyaltyBenefitReconciliationEntryDto effectDto(
            LoyaltyPromotionPointEffect effect,
            String status,
            List<String> reasons,
            String severity,
            LoyaltyPointsEntry ledgerEntry,
            UUID reversalOfEntryId) {
        return new LoyaltyBenefitReconciliationEntryDto(
                "promotion:" + effect.getRedemptionId() + ":" + effect.getExpectedEntryType() + ":" + effect.getEffectId(),
                status,
                reasons,
                "PROMOTION_POINTS",
                severity,
                effect.getTenantId(),
                effect.getApplicationId(),
                effect.getProgramId(),
                effect.getProfileId(),
                effect.getRedemptionId(),
                effect.getEffectId(),
                effect.getExpectedEntryType(),
                effect.getPointsDelta(),
                effect.getOriginalSourceReference(),
                effect.getExpectedIdempotencyKey(),
                ledgerEntry == null ? null : ledgerEntry.getId(),
                reversalOfEntryId,
                null,
                null,
                null,
                null,
                null,
                0L,
                effect.getSourceEventType(),
                effect.getEventId(),
                effect.getPayloadHash(),
                effect.getCorrelationId(),
                effect.getObservedAt(),
                ledgerEntry == null ? null : ledgerEntry.getCreatedAt(),
                null);
    }

    private Optional<LoyaltyPointsEntry> findEntry(
            LoyaltyPromotionPointEffect effect,
            String entryType,
            String sourceReference) {
        return pointsEntries.findFirstByTenantIdAndApplicationIdAndProgramIdAndEntryTypeAndSourceReference(
                effect.getTenantId(),
                effect.getApplicationId(),
                effect.getProgramId(),
                entryType,
                sourceReference);
    }

    private String normalizeItemType(String value) {
        String normalized = requiredText(value, "itemType").toUpperCase();
        if (!Set.of("PROMOTION_POINTS", "REWARD_REVERSE").contains(normalized)) {
            throw new BadRequestException("Invalid loyalty benefit reconciliation itemType: " + value);
        }
        return normalized;
    }

    private String normalizeStatus(String value) {
        String normalized = requiredText(value, "status").toUpperCase();
        if (!Set.of(
                "MATCHED",
                "PROMOTION_EARN_MISSING",
                "PROMOTION_REVERSE_ORIGINAL_EARN_MISSING",
                "PROMOTION_REVERSE_MISSING",
                "PROMOTION_REVERSE_LEDGER_MISMATCH",
                "REWARD_REVERSE_POINTS_MISSING",
                "REWARD_REVERSE_LEDGER_MISSING",
                "REWARD_REVERSE_LEDGER_MISMATCH").contains(normalized)) {
            throw new BadRequestException("Invalid loyalty benefit reconciliation status: " + value);
        }
        return normalized;
    }

    private String requiredText(String value, String field) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            throw new BadRequestException(field + " is required");
        }
        return normalized;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
