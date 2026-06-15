package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.AdminPreviewIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCouponRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.GenerateCouponsRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RuleSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCampaignVersion;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import edu.courseflow.promotion.model.IncentiveQuotaCounter;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignVersionRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import edu.courseflow.promotion.repository.IncentiveLedgerEntryRepository;
import edu.courseflow.promotion.repository.IncentiveQuotaCounterRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class PromotionServiceTest {

    @Mock
    IncentiveCampaignRepository campaigns;
    @Mock
    IncentiveCampaignVersionRepository campaignVersions;
    @Mock
    IncentiveCouponRepository coupons;
    @Mock
    IncentiveQuotaCounterRepository quotaCounters;
    @Mock
    IncentiveReservationRepository reservations;
    @Mock
    IncentiveRedemptionRepository redemptions;
    @Mock
    IncentiveLedgerEntryRepository ledgerEntries;
    @Mock
    IncentiveIdempotencyKeyRepository idempotencyKeys;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    OutboxEventRepository outboxEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    CampaignVersionService campaignVersionService;
    @Mock
    RedemptionReversalApprovalService reversalApprovals;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private PromotionService service;

    @BeforeEach
    void setUp() {
        service = serviceWithFingerprints(couponFingerprints());
    }

    private PromotionService serviceWithFingerprints(CouponCodeFingerprintService couponFingerprints) {
        return serviceWithFingerprints(couponFingerprints, AdminOperationRateGuard.disabled(metrics));
    }

    private PromotionService serviceWithFingerprints(CouponCodeFingerprintService couponFingerprints,
                                                     AdminOperationRateGuard adminOperationRateGuard) {
        return new PromotionService(
                campaigns,
                campaignVersions,
                coupons,
                quotaCounters,
                reservations,
                redemptions,
                ledgerEntries,
                idempotencyKeys,
                auditEvents,
                outboxEvents,
                new IncentiveDecisionEngine(objectMapper),
                access,
                campaignVersionService,
                reversalApprovals,
                objectMapper,
                metrics,
                couponFingerprints,
                new CouponStorageCutoverGuard(coupons, couponFingerprints),
                CouponAbuseGuard.disabled(metrics),
                adminOperationRateGuard,
                requestSnapshotSanitizer());
    }

    private static ReservationRequestSnapshotSanitizer requestSnapshotSanitizer() {
        return new ReservationRequestSnapshotSanitizer("test-request-snapshot-secret-32-byte-value");
    }

    @Test
    void adminPreviewEvaluatesPublishedSnapshotWithoutLedgerImpact() {
        CurrentUser admin = new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of(),
                fakeInternalToken("api-gateway", "user"));
        EvaluateIncentivesRequestDto context = request(List.of("WELCOME-SECRET"));
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(campaign()));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "support preview"),
                admin,
                "corr-preview-1");

        assertThat(response.preview()).isTrue();
        assertThat(response.ledgerImpact()).isFalse();
        assertThat(response.contextHash()).isNotBlank();
        assertThat(response.decision().eligible()).isTrue();
        assertThat(response.decision().campaignCode()).isEqualTo("WELCOME10");
        assertThat(response.winningCampaignId()).isEqualTo(response.decision().campaignId());
        assertThat(response.totals().totalDiscount()).isEqualByComparingTo("10.00");
        assertThat(response.totals().finalAmount()).isEqualByComparingTo("120.00");
        assertThat(response.candidates()).hasSize(1);
        assertThat(response.candidates().getFirst().selected()).isTrue();
        verifyNoInteractions(reservations, redemptions, ledgerEntries, idempotencyKeys, outboxEvents);
        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        IncentiveAuditEvent audit = auditCaptor.getValue();
        assertThat(audit.getAction()).isEqualTo("incentive.previewed");
        assertThat(audit.getAggregateType()).isEqualTo("incentive-preview");
        assertThat(audit.getAggregateId()).isEqualTo(response.contextHash());
        assertThat(audit.getCorrelationId()).isEqualTo("corr-preview-1");
        assertThat(audit.getSourceClientId()).isEqualTo("api-gateway");
        assertThat(audit.getPayloadJson()).contains("\"ledgerImpact\":false");
        assertThat(audit.getPayloadJson()).contains("\"candidateCount\":1");
        assertThat(audit.getPayloadJson()).contains("\"totalDiscount\":10.00");
        assertThat(audit.getPayloadJson()).contains("\"masks\":[\"WE****ET\"]");
        assertThat(audit.getPayloadJson()).contains("\"profileHash\":\"hmac-sha256:");
        assertThat(audit.getPayloadJson())
                .doesNotContain("WELCOME-SECRET")
                .doesNotContain("profile-1")
                .doesNotContain("cart-1");
    }

    @Test
    void adminPreviewReturnsQuotaExposureWithoutConsumingQuota() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of());
        IncentiveCampaignVersion version = campaign(false, 5);
        IncentiveQuotaCounter counter = new IncentiveQuotaCounter(
                "courseflow",
                "lms",
                "CAMPAIGN",
                version.getCampaignId().toString(),
                IncentiveQuotaCounter.WILDCARD_PROFILE,
                5);
        counter.consume();
        counter.consume();
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(quotaCounters.findByTenantIdAndApplicationIdAndScopeTypeAndScopeIdAndProfileId(
                eq("courseflow"),
                eq("lms"),
                eq("CAMPAIGN"),
                eq(version.getCampaignId().toString()),
                eq(IncentiveQuotaCounter.WILDCARD_PROFILE)))
                .thenReturn(Optional.of(counter));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "quota simulation"),
                admin,
                "corr-quota-simulation");

        assertThat(response.decision().eligible()).isTrue();
        assertThat(response.quotaExposure()).hasSize(1);
        assertThat(response.quotaExposure().getFirst().limit()).isEqualTo(5);
        assertThat(response.quotaExposure().getFirst().used()).isEqualTo(2);
        assertThat(response.quotaExposure().getFirst().remaining()).isEqualTo(3);
        assertThat(response.quotaExposure().getFirst().available()).isTrue();
        assertThat(response.quotaExposure().getFirst().wouldConsume()).isTrue();
        assertThat(response.candidates()).hasSize(1);
        assertThat(response.candidates().getFirst().quotaExposure().getFirst().remaining()).isEqualTo(3);
        assertThat(counter.getUsedCount()).isEqualTo(2);
        verifyNoInteractions(reservations, redemptions, ledgerEntries, idempotencyKeys, outboxEvents);
    }

    @Test
    void adminPreviewMarksStackingCompatibleCandidatesWithoutChangingRuntimeWinner() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of());
        IncentiveCampaignVersion primary = campaign("WELCOME10", 100, false, true, false, 10, null);
        IncentiveCampaignVersion secondary = campaign("SPRING5", 90, false, true, false, 5, null);
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(primary, secondary));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "stacking simulation"),
                admin,
                "corr-stacking-simulation");

        assertThat(response.decision().campaignId()).isEqualTo(primary.getCampaignId());
        assertThat(response.decision().effects()).hasSize(1);
        assertThat(response.totals().totalDiscount()).isEqualByComparingTo("10.00");
        assertThat(response.candidates()).hasSize(2);
        assertThat(response.candidates().get(0).selected()).isTrue();
        assertThat(response.candidates().get(0).stackingStatus()).isEqualTo("SELECTED_PRIMARY");
        assertThat(response.candidates().get(0).stackingReasonCodes()).contains("RUNTIME_SINGLE_WINNER");
        assertThat(response.candidates().get(1).selected()).isFalse();
        assertThat(response.candidates().get(1).stackingStatus()).isEqualTo("WOULD_STACK");
        assertThat(response.candidates().get(1).stackingReasonCodes())
                .containsExactly("STACKING_COMPATIBLE", "SIMULATION_ONLY");
        assertThat(response.candidates().get(1).exclusive()).isFalse();
        assertThat(response.candidates().get(1).stackable()).isTrue();
        verifyNoInteractions(reservations, redemptions, ledgerEntries, idempotencyKeys, outboxEvents);
    }

    @Test
    void adminPreviewMarksPolicyBlockedStackingCandidate() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of());
        IncentiveCampaignVersion primary = campaign("WELCOME10", 100, false, false, false, 10, null);
        IncentiveCampaignVersion secondary = campaign("SPRING5", 90, false, true, false, 5, null);
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(primary, secondary));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "blocked stacking simulation"),
                admin,
                "corr-blocked-stacking-simulation");

        assertThat(response.candidates()).hasSize(2);
        assertThat(response.candidates().get(0).stackable()).isFalse();
        assertThat(response.candidates().get(0).stackingStatus()).isEqualTo("SELECTED_PRIMARY");
        assertThat(response.candidates().get(1).stackingStatus()).isEqualTo("BLOCKED_BY_PRIMARY_NON_STACKABLE");
        assertThat(response.candidates().get(1).stackingReasonCodes()).containsExactly("WINNER_NOT_STACKABLE");
        assertThat(response.candidates().get(1).selected()).isFalse();
        verifyNoInteractions(reservations, redemptions, ledgerEntries, idempotencyKeys, outboxEvents);
    }

    @Test
    void adminPreviewRateLimitStopsBeforeDecisionOrAudit() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("WELCOME-SECRET"));
        PromotionService guardedService = serviceWithFingerprints(couponFingerprints(), blockingGuard());
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        assertThatThrownBy(() -> guardedService.preview(
                new AdminPreviewIncentivesRequestDto(context, "support preview"),
                admin,
                "corr-preview-rate-limit"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(metrics).adminOperationRateGuard("admin_preview", "enforced", "application", "limited");
        verifyNoInteractions(campaignVersions, coupons, reservations, redemptions, ledgerEntries,
                idempotencyKeys, outboxEvents, auditEvents);
    }

    @Test
    void adminPreviewRecordsExpiredCouponMatchMetricOnce() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("SAVE10"));
        IncentiveCampaignVersion version = campaign(true);
        IncentiveCoupon expiredCoupon = coupon(
                version.getCampaignId(),
                "SAVE10",
                null,
                null,
                Instant.now().minusSeconds(60));
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(coupons.findByCampaignIdAndNormalizedCode(
                eq(version.getCampaignId()),
                eq(couponFingerprints().primaryFingerprint("SAVE10"))))
                .thenReturn(Optional.of(expiredCoupon));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "expired coupon debug"),
                admin,
                "corr-expired-coupon");

        assertThat(response.decision().eligible()).isFalse();
        assertThat(response.decision().reasonCodes()).containsExactly("NO_ELIGIBLE_INCENTIVE");
        verify(metrics).couponMatch("preview", "expired", true, true);
        verify(metrics).couponLookup("preview", "current_hmac", true, true);
    }

    @Test
    void adminPreviewRecordsHolderMismatchCouponMatchMetric() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("VIP10"));
        IncentiveCampaignVersion version = campaign(true);
        IncentiveCoupon heldCoupon = coupon(
                version.getCampaignId(),
                "VIP10",
                "another-profile",
                null,
                Instant.now().plusSeconds(3600));
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(coupons.findByCampaignIdAndNormalizedCode(
                eq(version.getCampaignId()),
                eq(couponFingerprints().primaryFingerprint("VIP10"))))
                .thenReturn(Optional.of(heldCoupon));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "holder mismatch debug"),
                admin,
                "corr-holder-coupon");

        assertThat(response.decision().eligible()).isFalse();
        assertThat(response.decision().reasonCodes()).containsExactly("NO_ELIGIBLE_INCENTIVE");
        verify(metrics).couponMatch("preview", "holder_mismatch", true, true);
        verify(metrics).couponLookup("preview", "current_hmac", true, true);
    }

    @Test
    void quotaRecheckRecordsCouponMatchMetricOnlyOnce() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("SAVE10"));
        IncentiveCampaignVersion version = campaign(true, 1);
        IncentiveCoupon validCoupon = coupon(
                version.getCampaignId(),
                "SAVE10",
                null,
                null,
                Instant.now().plusSeconds(3600));
        IncentiveQuotaCounter exhaustedCounter = new IncentiveQuotaCounter(
                "courseflow",
                "lms",
                "CAMPAIGN",
                version.getCampaignId().toString(),
                IncentiveQuotaCounter.WILDCARD_PROFILE,
                1);
        exhaustedCounter.consume();
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(coupons.findByCampaignIdAndNormalizedCode(
                eq(version.getCampaignId()),
                eq(couponFingerprints().primaryFingerprint("SAVE10"))))
                .thenReturn(Optional.of(validCoupon));
        when(quotaCounters.findByTenantIdAndApplicationIdAndScopeTypeAndScopeIdAndProfileId(
                eq("courseflow"),
                eq("lms"),
                eq("CAMPAIGN"),
                eq(version.getCampaignId().toString()),
                eq(IncentiveQuotaCounter.WILDCARD_PROFILE)))
                .thenReturn(Optional.of(exhaustedCounter));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "quota debug"),
                admin,
                "corr-quota-coupon");

        assertThat(response.decision().eligible()).isFalse();
        assertThat(response.decision().reasonCodes()).containsExactly("QUOTA_EXHAUSTED");
        verify(metrics).couponMatch("preview", "matched", true, true);
        verify(metrics).couponLookup("preview", "current_hmac", true, true);
    }

    @Test
    void adminPreviewRecordsLegacyRawCouponLookupPath() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("SAVE10"));
        IncentiveCampaignVersion version = campaign(true);
        IncentiveCoupon legacyCoupon = new IncentiveCoupon(
                version.getCampaignId(),
                "SAVE10",
                "SAVE10",
                "SA****10",
                null,
                null,
                Instant.now().plusSeconds(3600),
                null,
                null,
                "{}");
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(coupons.findByCampaignIdAndNormalizedCode(eq(version.getCampaignId()), any()))
                .thenReturn(Optional.empty());
        when(coupons.findByCampaignIdAndNormalizedCode(version.getCampaignId(), "SAVE10"))
                .thenReturn(Optional.of(legacyCoupon));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "legacy coupon debug"),
                admin,
                "corr-legacy-coupon");

        assertThat(response.decision().eligible()).isTrue();
        verify(metrics).couponMatch("preview", "matched", true, true);
        verify(metrics).couponLookup("preview", "legacy_raw", true, true);
    }

    @Test
    void adminPreviewRecordsPreviousHmacCouponLookupPath() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("SAVE10"));
        IncentiveCampaignVersion version = campaign(true);
        String previousFingerprint = new CouponCodeFingerprintService("old", "old-coupon-pepper", "", true)
                .primaryFingerprint("SAVE10");
        IncentiveCoupon previousKeyCoupon = new IncentiveCoupon(
                version.getCampaignId(),
                "SA****10",
                previousFingerprint,
                "SA****10",
                null,
                null,
                Instant.now().plusSeconds(3600),
                null,
                null,
                "{}");
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(coupons.findByCampaignIdAndNormalizedCode(eq(version.getCampaignId()), any()))
                .thenReturn(Optional.empty());
        when(coupons.findByCampaignIdAndNormalizedCode(version.getCampaignId(), previousFingerprint))
                .thenReturn(Optional.of(previousKeyCoupon));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "previous key coupon debug"),
                admin,
                "corr-previous-coupon");

        assertThat(response.decision().eligible()).isTrue();
        verify(metrics).couponLookup("preview", "previous_hmac", true, true);
    }

    @Test
    void adminPreviewRecordsLegacyShaCouponLookupPath() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("SAVE10"));
        IncentiveCampaignVersion version = campaign(true);
        String legacySha = CouponCodeNormalizer.legacySha256Fingerprint("SAVE10");
        IncentiveCoupon legacyShaCoupon = new IncentiveCoupon(
                version.getCampaignId(),
                "SA****10",
                legacySha,
                "SA****10",
                null,
                null,
                Instant.now().plusSeconds(3600),
                null,
                null,
                "{}");
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(coupons.findByCampaignIdAndNormalizedCode(eq(version.getCampaignId()), any()))
                .thenReturn(Optional.empty());
        when(coupons.findByCampaignIdAndNormalizedCode(version.getCampaignId(), legacySha))
                .thenReturn(Optional.of(legacyShaCoupon));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "legacy sha coupon debug"),
                admin,
                "corr-legacy-sha-coupon");

        assertThat(response.decision().eligible()).isTrue();
        verify(metrics).couponLookup("preview", "legacy_sha", true, true);
    }

    @Test
    void adminPreviewRecordsCouponLookupMissPath() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("MISSING10"));
        IncentiveCampaignVersion version = campaign(true);
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(version));
        when(coupons.findByCampaignIdAndNormalizedCode(eq(version.getCampaignId()), any()))
                .thenReturn(Optional.empty());
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "missing coupon debug"),
                admin,
                "corr-missing-coupon");

        assertThat(response.decision().eligible()).isFalse();
        verify(metrics).couponLookup("preview", "miss", true, true);
    }

    @Test
    void adminPreviewRecordsNoActiveCampaignCouponLookupPath() {
        CurrentUser admin = adminUser();
        EvaluateIncentivesRequestDto context = request(List.of("SAVE10"));
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of());
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.preview(
                new AdminPreviewIncentivesRequestDto(context, "no campaign debug"),
                admin,
                "corr-no-campaign");

        assertThat(response.decision().eligible()).isFalse();
        verify(metrics).couponLookup("preview", "no_active_campaign", true, false);
    }

    @Test
    void createCouponStoresVersionedHmacFingerprintInsteadOfRawOrLegacySha() {
        CurrentUser admin = adminUser();
        IncentiveCampaign campaign = campaignEntity();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(coupons.findByCampaignIdAndNormalizedCode(eq(campaign.getId()), any()))
                .thenReturn(Optional.empty());
        when(coupons.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var response = service.createCoupon(new CreateCouponRequestDto(
                campaign.getId(),
                " Save10 ",
                null,
                null,
                Instant.now().plusSeconds(3600),
                null,
                null,
                Map.of()), admin, "corr-create-coupon");

        ArgumentCaptor<IncentiveCoupon> couponCaptor = ArgumentCaptor.forClass(IncentiveCoupon.class);
        verify(coupons).save(couponCaptor.capture());
        IncentiveCoupon saved = couponCaptor.getValue();
        assertThat(saved.getNormalizedCode())
                .startsWith("hmac-sha256:test:")
                .doesNotContain("SAVE10")
                .isNotEqualTo(CouponCodeNormalizer.legacySha256Fingerprint("SAVE10"));
        assertThat(saved.getCode()).isEqualTo("SA****10");
        assertThat(response.code()).isEqualTo("SA****10");
        assertThat(response.normalizedCode()).isNull();
    }

    @Test
    void createCouponRejectsDuplicateLegacyRawCodeBeforeWritingHmacFingerprint() {
        CurrentUser admin = adminUser();
        IncentiveCampaign campaign = campaignEntity();
        IncentiveCoupon legacyCoupon = new IncentiveCoupon(
                campaign.getId(),
                "SAVE10",
                "SAVE10",
                "SA****10",
                null,
                null,
                null,
                null,
                null,
                "{}");
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(coupons.findByCampaignIdAndNormalizedCode(eq(campaign.getId()), any()))
                .thenReturn(Optional.empty());
        when(coupons.findByCampaignIdAndNormalizedCode(campaign.getId(), "SAVE10"))
                .thenReturn(Optional.of(legacyCoupon));

        assertThatThrownBy(() -> service.createCoupon(new CreateCouponRequestDto(
                campaign.getId(),
                "SAVE10",
                null,
                null,
                null,
                null,
                null,
                Map.of()), admin, "corr-duplicate-coupon"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("Coupon code already exists");
    }

    @Test
    void createCouponFailsClosedWhenFallbackDisabledAndLegacyInventoryRemains() {
        CurrentUser admin = adminUser();
        IncentiveCampaign campaign = campaignEntity();
        CouponCodeFingerprintService strictFingerprints =
                new CouponCodeFingerprintService("test", "test-coupon-pepper", "", false);
        PromotionService strictService = serviceWithFingerprints(strictFingerprints);
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(coupons.countByStorageFormat(
                "courseflow",
                "lms",
                campaign.getId(),
                true,
                strictFingerprints.currentStoragePrefix()))
                .thenReturn(List.of(storageCount("legacy_raw", 1)));

        assertThatThrownBy(() -> strictService.createCoupon(new CreateCouponRequestDto(
                campaign.getId(),
                "SAVE10",
                null,
                null,
                null,
                null,
                null,
                Map.of()), admin, "corr-fallback-off"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("Coupon storage cutover is not ready");
        verify(coupons, never()).findByCampaignIdAndNormalizedCode(eq(campaign.getId()), any());
        verify(coupons, never()).save(any());
    }

    @Test
    void generateCouponsFailsClosedWhenFallbackDisabledAndLegacyInventoryRemains() {
        CurrentUser admin = adminUser();
        IncentiveCampaign campaign = campaignEntity();
        CouponCodeFingerprintService strictFingerprints =
                new CouponCodeFingerprintService("test", "test-coupon-pepper", "", false);
        PromotionService strictService = serviceWithFingerprints(strictFingerprints);
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(coupons.countByStorageFormat(
                "courseflow",
                "lms",
                campaign.getId(),
                true,
                strictFingerprints.currentStoragePrefix()))
                .thenReturn(List.of(storageCount("legacy_sha", 1)));

        assertThatThrownBy(() -> strictService.generateCoupons(new GenerateCouponsRequestDto(
                campaign.getId(),
                "SAVE",
                2,
                8,
                null,
                null,
                null,
                null,
                null,
                Map.of()), admin, "corr-generate-fallback-off"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("Coupon storage cutover is not ready");
        verify(coupons, never()).findByCampaignIdAndNormalizedCode(eq(campaign.getId()), any());
        verify(coupons, never()).save(any());
    }

    @Test
    void generateCouponsRateLimitStopsBeforeDuplicateLookupOrSave() {
        CurrentUser admin = adminUser();
        IncentiveCampaign campaign = campaignEntity();
        PromotionService guardedService = serviceWithFingerprints(couponFingerprints(), blockingGuard());
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        assertThatThrownBy(() -> guardedService.generateCoupons(new GenerateCouponsRequestDto(
                campaign.getId(),
                "SAVE",
                2,
                8,
                null,
                null,
                null,
                null,
                null,
                Map.of()), admin, "corr-generate-rate-limit"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(coupons, never()).findByCampaignIdAndNormalizedCode(eq(campaign.getId()), any());
        verify(coupons, never()).save(any());
    }

    @Test
    void couponStorageInventoryReturnsSafeOrderedCountsAndDisableReadiness() {
        CurrentUser admin = adminUser();
        when(coupons.countByStorageFormat(
                eq("courseflow"),
                eq("lms"),
                isNull(),
                eq(true),
                eq(couponFingerprints().currentStoragePrefix())))
                .thenReturn(List.of(
                        storageCount("current_hmac", 10),
                        storageCount("legacy_sha", 2),
                        storageCount("legacy_raw", 1)));

        var response = service.couponStorageInventory(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.empty(),
                Optional.empty(),
                admin);

        assertThat(response.tenantId()).isEqualTo("courseflow");
        assertThat(response.applicationId()).isEqualTo("lms");
        assertThat(response.activeOnly()).isTrue();
        assertThat(response.legacyFallbackEnabled()).isTrue();
        assertThat(response.fallbackDisableReady()).isFalse();
        assertThat(response.totalCoupons()).isEqualTo(13);
        assertThat(response.legacyCoupons()).isEqualTo(3);
        assertThat(response.malformedCoupons()).isZero();
        assertThat(response.items())
                .extracting(item -> item.storageFormat() + "=" + item.count())
                .containsExactly(
                        "current_hmac=10",
                        "previous_hmac=0",
                        "legacy_sha=2",
                        "legacy_raw=1",
                        "malformed=0");
        verify(access).requireAdminAccess("courseflow", "lms", admin);
    }

    @Test
    void couponStorageInventoryUsesCampaignScopeForAdminAccess() {
        CurrentUser admin = adminUser();
        IncentiveCampaign campaign = campaignEntity();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(coupons.countByStorageFormat(
                eq("courseflow"),
                eq("lms"),
                eq(campaign.getId()),
                eq(false),
                eq(couponFingerprints().currentStoragePrefix())))
                .thenReturn(List.of(storageCount("current_hmac", 5)));

        var response = service.couponStorageInventory(
                Optional.empty(),
                Optional.empty(),
                Optional.of(campaign.getId()),
                Optional.of(false),
                admin);

        assertThat(response.campaignId()).isEqualTo(campaign.getId());
        assertThat(response.activeOnly()).isFalse();
        assertThat(response.totalCoupons()).isEqualTo(5);
        assertThat(response.fallbackDisableReady()).isTrue();
        verify(access).requireAdminAccess("courseflow", "lms", admin);
    }

    @Test
    void couponStorageInventoryRequiresPlatformAdminForGlobalReport() {
        CurrentUser admin = adminUser();
        when(coupons.countByStorageFormat(
                isNull(),
                isNull(),
                isNull(),
                eq(true),
                eq(couponFingerprints().currentStoragePrefix())))
                .thenReturn(List.of(storageCount("malformed", 1)));

        var response = service.couponStorageInventory(
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                admin);

        assertThat(response.tenantId()).isNull();
        assertThat(response.applicationId()).isNull();
        assertThat(response.malformedCoupons()).isEqualTo(1);
        assertThat(response.fallbackDisableReady()).isFalse();
        verify(access).requirePlatformAdmin(admin);
    }

    @Test
    void reserveFallsBackToNextCandidateWhenQuotaConsumeRaces() {
        CurrentUser admin = adminUser();
        IncentiveCampaignVersion exhaustedVersion = campaign(false, 1);
        IncentiveCampaignVersion fallbackVersion = campaign(false, 1);
        ReserveIncentiveRequestDto reserveRequest = new ReserveIncentiveRequestDto(
                "reserve-fallback-1",
                request(List.of()));
        AtomicReference<IncentiveIdempotencyKey> idempotencyKey = new AtomicReference<>();
        when(idempotencyKeys.insertInProgressIfAbsent(any(), eq("courseflow"), eq("lms"), eq("RESERVE"),
                eq("reserve-fallback-1"), any(), any()))
                .thenAnswer(invocation -> {
                    idempotencyKey.set(inProgressKey(invocation.getArgument(5)));
                    return 1;
                });
        when(idempotencyKeys.lockByScope("courseflow", "lms", "RESERVE", "reserve-fallback-1"))
                .thenAnswer(invocation -> Optional.of(idempotencyKey.get()));
        when(campaignVersions.findActivePublished(eq("courseflow"), eq("lms"), any()))
                .thenReturn(List.of(exhaustedVersion, fallbackVersion));
        when(quotaCounters.insertIfAbsent(
                any(),
                eq("courseflow"),
                eq("lms"),
                eq("CAMPAIGN"),
                any(),
                eq(IncentiveQuotaCounter.WILDCARD_PROFILE),
                eq(1)))
                .thenReturn(1);
        when(quotaCounters.tryConsumeIfAvailable(
                "courseflow",
                "lms",
                "CAMPAIGN",
                exhaustedVersion.getCampaignId().toString(),
                IncentiveQuotaCounter.WILDCARD_PROFILE,
                1))
                .thenReturn(0);
        when(quotaCounters.tryConsumeIfAvailable(
                "courseflow",
                "lms",
                "CAMPAIGN",
                fallbackVersion.getCampaignId().toString(),
                IncentiveQuotaCounter.WILDCARD_PROFILE,
                1))
                .thenReturn(1);

        var response = service.reserve(reserveRequest, admin, "corr-reserve-fallback");

        assertThat(response.reserved()).isTrue();
        assertThat(response.campaignId()).isEqualTo(fallbackVersion.getCampaignId());
        assertThat(response.reasonCodes()).containsExactly("ELIGIBLE");
        verify(metrics).quotaReserveFallback("candidate_conflict");
        verify(metrics).quotaReserveFallback("success");
    }

    private IncentiveCampaignVersion campaign() {
        return campaign(false);
    }

    private IncentiveCampaignVersion campaign(boolean couponRequired) {
        return campaign(couponRequired, null);
    }

    private IncentiveCampaignVersion campaign(boolean couponRequired, Integer maxRedemptions) {
        return campaign("WELCOME10", 100, false, true, couponRequired, 10, maxRedemptions);
    }

    private IncentiveCampaignVersion campaign(String code,
                                              int priority,
                                              boolean exclusive,
                                              boolean stackable,
                                              boolean couponRequired,
                                              int discountAmount,
                                              Integer maxRedemptions) {
        IncentiveDecisionEngine engine = new IncentiveDecisionEngine(objectMapper);
        IncentiveCampaign campaign = new IncentiveCampaign(
                "courseflow",
                "lms",
                code,
                code,
                null,
                "PROMOTION",
                Instant.now().minusSeconds(60),
                Instant.now().plusSeconds(3600),
                priority,
                exclusive,
                stackable,
                couponRequired,
                "ALL",
                "USD",
                engine.toRulesJson(List.of(new RuleSpecDto(
                        "MIN_ORDER_AMOUNT",
                        1,
                        Map.of("amount", 100, "currency", "USD")))),
                engine.toActionsJson(List.of(new ActionSpecDto(
                        "ORDER_FIXED_OFF",
                        1,
                        Map.of("amount", discountAmount)))),
                maxRedemptions,
                null,
                "test");
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "test");
        version.submit("test", "ready");
        version.approve("reviewer", "approved");
        version.publish("publisher");
        return version;
    }

    private IncentiveCampaign campaignEntity() {
        IncentiveDecisionEngine engine = new IncentiveDecisionEngine(objectMapper);
        return new IncentiveCampaign(
                "courseflow",
                "lms",
                "WELCOME10",
                "Welcome",
                null,
                "PROMOTION",
                Instant.now().minusSeconds(60),
                Instant.now().plusSeconds(3600),
                100,
                false,
                true,
                false,
                "ALL",
                "USD",
                engine.toRulesJson(List.of()),
                engine.toActionsJson(List.of(new ActionSpecDto(
                        "ORDER_FIXED_OFF",
                        1,
                        Map.of("amount", 10)))),
                null,
                null,
                "test");
    }

    private IncentiveCoupon coupon(UUID campaignId,
                                   String code,
                                   String holderProfileId,
                                   Instant startsAt,
                                   Instant expiresAt) {
        String normalized = CouponCodeNormalizer.normalize(code);
        return new IncentiveCoupon(
                campaignId,
                CouponCodeNormalizer.mask(normalized),
                couponFingerprints().primaryFingerprint(normalized),
                CouponCodeNormalizer.mask(normalized),
                holderProfileId,
                startsAt,
                expiresAt,
                null,
                null,
                "{}");
    }

    private CurrentUser adminUser() {
        return new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of(),
                fakeInternalToken("api-gateway", "user"));
    }

    private AdminOperationRateGuard blockingGuard() {
        AdminOperationRateGuardProperties properties = new AdminOperationRateGuardProperties();
        properties.setMode(AdminOperationRateGuardProperties.Mode.ENFORCED);
        properties.setKeyId("test");
        properties.setPepper("test-admin-operation-rate-pepper-32-byte-value");
        properties.validate();
        return new AdminOperationRateGuard(properties, (key, capacity, window) ->
                new CouponAbuseRateLimitStore.Hit(capacity + 1L, false), metrics);
    }

    private static IncentiveCouponRepository.CouponStorageFormatCount storageCount(String storageFormat, long count) {
        return new IncentiveCouponRepository.CouponStorageFormatCount() {
            @Override
            public String getStorageFormat() {
                return storageFormat;
            }

            @Override
            public long getCouponCount() {
                return count;
            }
        };
    }

    private EvaluateIncentivesRequestDto request(List<String> couponCodes) {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                "profile-1",
                "cart-1",
                "WEB",
                "USD",
                couponCodes,
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.TEN),
                List.of(new IncentiveItemDto(
                        "item-1",
                        "COURSE",
                        1,
                        BigDecimal.valueOf(120),
                        Map.of("category", "spring"))),
                Map.of("segment", "NEW"));
    }

    private static String fakeInternalToken(String clientId, String actorType) {
        String payload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(("{\"azp\":\"" + clientId + "\",\"actor_type\":\"" + actorType + "\"}")
                        .getBytes(StandardCharsets.UTF_8));
        return "test." + payload + ".signature";
    }

    private static CouponCodeFingerprintService couponFingerprints() {
        return new CouponCodeFingerprintService("test", "test-coupon-pepper", "old:old-coupon-pepper", true);
    }

    private static IncentiveIdempotencyKey inProgressKey(String requestHash) {
        IncentiveIdempotencyKey key = new IncentiveIdempotencyKey(
                "courseflow",
                "lms",
                "RESERVE",
                "reserve-fallback-1",
                requestHash,
                "{}",
                Instant.now().plusSeconds(3600));
        ReflectionTestUtils.setField(key, "status", "IN_PROGRESS");
        return key;
    }
}
