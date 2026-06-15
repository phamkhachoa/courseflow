package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyPointsEntry;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyPromotionPointEffect;
import edu.courseflow.loyalty.model.LoyaltyReward;
import edu.courseflow.loyalty.model.LoyaltyRewardRedemption;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyPromotionPointEffectRepository;
import edu.courseflow.loyalty.repository.LoyaltyRewardRedemptionRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class LoyaltyBenefitReconciliationServiceTest {

    @Mock
    private LoyaltyPromotionPointEffectRepository expectedEffects;
    @Mock
    private LoyaltyPointsEntryRepository pointsEntries;
    @Mock
    private LoyaltyRewardRedemptionRepository rewardRedemptions;
    @Mock
    private LoyaltyAccessService access;

    private LoyaltyBenefitReconciliationService service;
    private CurrentUser reviewer;

    @BeforeEach
    void setUp() {
        service = new LoyaltyBenefitReconciliationService(expectedEffects, pointsEntries, rewardRedemptions, access);
        reviewer = new CurrentUser(7L, "reviewer@example.com", "LOYALTY_REVIEWER", Set.of("LOYALTY_REVIEWER"));
    }

    @Test
    void flagsPromotionEarnIntentWithoutEarnLedger() {
        LoyaltyPromotionPointEffect expected = expectedEarnEffect();
        when(expectedEffects.search(
                eq("courseflow"),
                eq("lms"),
                eq("default"),
                eq("profile-1"),
                eq("redemption-1"),
                eq(null),
                eq(null),
                eq(null),
                any(Pageable.class))).thenReturn(List.of(expected));
        when(rewardRedemptions.searchReversedForReconciliation(
                eq("courseflow"),
                eq("lms"),
                eq("default"),
                eq("profile-1"),
                eq(null),
                eq(null),
                any(Pageable.class))).thenReturn(List.of());
        when(pointsEntries.findFirstByTenantIdAndApplicationIdAndProgramIdAndEntryTypeAndSourceReference(
                "courseflow",
                "lms",
                "default",
                "EARN",
                expected.getOriginalSourceReference())).thenReturn(Optional.empty());

        var result = service.query(
                "courseflow",
                "lms",
                Optional.of("default"),
                Optional.of("profile-1"),
                Optional.of("redemption-1"),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(25),
                reviewer);

        assertThat(result.items()).hasSize(1);
        assertThat(result.items().get(0).reconciliationStatus()).isEqualTo("PROMOTION_EARN_MISSING");
        assertThat(result.items().get(0).itemType()).isEqualTo("PROMOTION_POINTS");
        assertThat(result.items().get(0).expectedPointsDelta()).isEqualTo(50);
        verify(access).requireReadAccess("courseflow", "lms", reviewer);
    }

    @Test
    void flagsRewardReversedWithoutPointRestoration() {
        LoyaltyRewardRedemption redemption = reversedRewardWithoutLedger();
        when(expectedEffects.search(
                eq("courseflow"),
                eq("lms"),
                eq(null),
                eq("profile-1"),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                any(Pageable.class))).thenReturn(List.of());
        when(rewardRedemptions.searchReversedForReconciliation(
                eq("courseflow"),
                eq("lms"),
                eq(null),
                eq("profile-1"),
                eq(null),
                eq(null),
                any(Pageable.class))).thenReturn(List.of(redemption));

        var result = service.query(
                "courseflow",
                "lms",
                Optional.empty(),
                Optional.of("profile-1"),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(25),
                reviewer);

        assertThat(result.items()).hasSize(1);
        assertThat(result.items().get(0).reconciliationStatus()).isEqualTo("REWARD_REVERSE_POINTS_MISSING");
        assertThat(result.items().get(0).rewardRedemptionId()).isEqualTo(redemption.getId());
        assertThat(result.items().get(0).rewardPointsCost()).isEqualTo(40);
    }

    @Test
    void flagsPromotionReverseWithoutPointRestoration() {
        LoyaltyPromotionPointEffect expected = expectedReverseEffect();
        LoyaltyPointsEntry originalEarn = earnEntry("promotion:redemption-1:effecthash", 50);
        when(expectedEffects.search(
                eq("courseflow"),
                eq("lms"),
                eq("default"),
                eq("profile-1"),
                eq("redemption-1"),
                eq(null),
                eq(null),
                eq(null),
                any(Pageable.class))).thenReturn(List.of(expected));
        when(pointsEntries.findFirstByTenantIdAndApplicationIdAndProgramIdAndEntryTypeAndSourceReference(
                "courseflow",
                "lms",
                "default",
                "EARN",
                expected.getOriginalSourceReference())).thenReturn(Optional.of(originalEarn));
        when(pointsEntries.findFirstByReversalOfEntryId(originalEarn.getId())).thenReturn(Optional.empty());

        var result = service.query(
                "courseflow",
                "lms",
                Optional.of("default"),
                Optional.of("profile-1"),
                Optional.of("redemption-1"),
                Optional.of("PROMOTION_POINTS"),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(25),
                reviewer);

        assertThat(result.items()).hasSize(1);
        assertThat(result.items().get(0).reconciliationStatus()).isEqualTo("PROMOTION_REVERSE_MISSING");
        assertThat(result.items().get(0).reversalOfEntryId()).isEqualTo(originalEarn.getId());
    }

    @Test
    void flagsPromotionReverseLedgerMismatch() {
        LoyaltyPromotionPointEffect expected = expectedReverseEffect();
        LoyaltyPointsEntry originalEarn = earnEntry("promotion:redemption-1:effecthash", 50);
        LoyaltyPointsEntry wrongReversal = reverseEntry(originalEarn, 40);
        when(expectedEffects.search(
                eq("courseflow"),
                eq("lms"),
                eq("default"),
                eq("profile-1"),
                eq("redemption-1"),
                eq(null),
                eq(null),
                eq(null),
                any(Pageable.class))).thenReturn(List.of(expected));
        when(pointsEntries.findFirstByTenantIdAndApplicationIdAndProgramIdAndEntryTypeAndSourceReference(
                "courseflow",
                "lms",
                "default",
                "EARN",
                expected.getOriginalSourceReference())).thenReturn(Optional.of(originalEarn));
        when(pointsEntries.findFirstByReversalOfEntryId(originalEarn.getId())).thenReturn(Optional.of(wrongReversal));

        var result = service.query(
                "courseflow",
                "lms",
                Optional.of("default"),
                Optional.of("profile-1"),
                Optional.of("redemption-1"),
                Optional.of("PROMOTION_POINTS"),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(25),
                reviewer);

        assertThat(result.items()).hasSize(1);
        assertThat(result.items().get(0).reconciliationStatus()).isEqualTo("PROMOTION_REVERSE_LEDGER_MISMATCH");
        assertThat(result.items().get(0).ledgerEntryId()).isEqualTo(wrongReversal.getId());
        assertThat(result.items().get(0).reversalOfEntryId()).isEqualTo(originalEarn.getId());
    }

    private LoyaltyPromotionPointEffect expectedEarnEffect() {
        return new LoyaltyPromotionPointEffect(
                "incentive.redemption.committed",
                "incentive.redemption.committed",
                "event-1",
                "redemption-1",
                "effect-1",
                "EARN",
                "courseflow",
                "lms",
                "default",
                "profile-1",
                50,
                "promotion:redemption-1:effecthash",
                "promotion:redemption-1:effecthash",
                "corr-1",
                "hash-1",
                Instant.parse("2026-01-01T00:00:00Z"));
    }

    private LoyaltyPromotionPointEffect expectedReverseEffect() {
        return new LoyaltyPromotionPointEffect(
                "incentive.redemption.reversed",
                "incentive.redemption.reversed",
                "event-reverse-1",
                "redemption-1",
                "effect-1",
                "REVERSE",
                "courseflow",
                "lms",
                "default",
                "profile-1",
                50,
                "promotion:redemption-1:effecthash",
                "promotion:redemption-1:effecthash:reverse",
                "corr-reverse",
                "hash-reverse",
                Instant.parse("2026-01-02T00:00:00Z"));
    }

    private LoyaltyPointsEntry earnEntry(String sourceReference, long points) {
        return new LoyaltyPointsEntry(
                loyaltyAccount(),
                "EARN",
                points,
                sourceReference,
                sourceReference,
                null,
                "Promotion points earn intent",
                "corr-earn",
                "{}",
                Instant.parse("2026-01-01T00:00:00Z"),
                null);
    }

    private LoyaltyPointsEntry reverseEntry(LoyaltyPointsEntry originalEarn, long points) {
        return new LoyaltyPointsEntry(
                loyaltyAccount(),
                "REVERSE",
                points,
                originalEarn.getSourceReference() + ":reverse",
                originalEarn.getSourceReference() + ":reverse",
                originalEarn.getId(),
                "Promotion redemption reversed",
                "corr-reverse",
                "{}",
                Instant.parse("2026-01-02T00:00:00Z"),
                null);
    }

    private LoyaltyAccount loyaltyAccount() {
        return new LoyaltyAccount(loyaltyProgram(), "profile-1");
    }

    private LoyaltyProgram loyaltyProgram() {
        return new LoyaltyProgram(
                "courseflow",
                "lms",
                "default",
                "Default points",
                "POINT",
                false,
                365,
                "test");
    }

    private LoyaltyRewardRedemption reversedRewardWithoutLedger() {
        LoyaltyReward reward = new LoyaltyReward(
                loyaltyProgram(),
                "CERT",
                "Certificate",
                "Certificate reward",
                40,
                "ACTIVE",
                null,
                null,
                null,
                null,
                "MANUAL",
                "{}",
                "test");
        LoyaltyRewardRedemption redemption = new LoyaltyRewardRedemption(
                reward,
                UUID.randomUUID(),
                UUID.randomUUID(),
                "profile-1",
                "reward:CERT:profile-1",
                "reward-idem",
                "hash",
                "{}",
                "corr-reward",
                "redeemed",
                "{}");
        redemption.markReversed(null);
        return redemption;
    }
}
