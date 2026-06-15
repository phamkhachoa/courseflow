package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionActionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponDistributionRecipientInputDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCouponDistributionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.PreviewCouponDistributionRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveCouponDistribution;
import edu.courseflow.promotion.model.IncentiveCouponDistributionRecipient;
import edu.courseflow.promotion.model.OutboxEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCouponDistributionRecipientRepository;
import edu.courseflow.promotion.repository.IncentiveCouponDistributionRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
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

@ExtendWith(MockitoExtension.class)
class CouponDistributionServiceTest {

    @Mock
    IncentiveCampaignRepository campaigns;
    @Mock
    IncentiveCouponRepository coupons;
    @Mock
    IncentiveCouponDistributionRepository distributions;
    @Mock
    IncentiveCouponDistributionRecipientRepository recipients;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    OutboxEventRepository outboxEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final CouponCodeFingerprintService couponFingerprints =
            new CouponCodeFingerprintService("test", "test-coupon-pepper", "", true);
    private CouponDistributionService service;

    @BeforeEach
    void setUp() {
        service = new CouponDistributionService(
                campaigns,
                coupons,
                distributions,
                recipients,
                auditEvents,
                outboxEvents,
                access,
                couponFingerprints,
                new CouponStorageCutoverGuard(coupons, couponFingerprints),
                AdminOperationRateGuard.disabled(metrics),
                objectMapper);
    }

    @Test
    void previewCreateApproveIssueAndRevokeDistribution() {
        CurrentUser admin = adminUser();
        IncentiveCampaign campaign = campaignEntity();
        AtomicReference<IncentiveCouponDistribution> distributionRef = new AtomicReference<>();
        AtomicReference<List<IncentiveCouponDistributionRecipient>> recipientRows =
                new AtomicReference<>(new ArrayList<>());
        Map<UUID, IncentiveCoupon> savedCoupons = new LinkedHashMap<>();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(distributions.save(any())).thenAnswer(invocation -> {
            IncentiveCouponDistribution distribution = invocation.getArgument(0);
            distributionRef.set(distribution);
            return distribution;
        });
        when(distributions.lockById(any())).thenAnswer(invocation -> Optional.of(distributionRef.get()));
        when(recipients.saveAll(any())).thenAnswer(invocation -> {
            List<IncentiveCouponDistributionRecipient> rows = new ArrayList<>();
            for (IncentiveCouponDistributionRecipient row : invocation.<Iterable<IncentiveCouponDistributionRecipient>>getArgument(0)) {
                rows.add(row);
            }
            recipientRows.set(rows);
            return rows;
        });
        when(recipients.findByDistributionIdOrderByCreatedAtAsc(any())).thenAnswer(invocation -> recipientRows.get());
        when(coupons.findByCampaignIdAndNormalizedCode(eq(campaign.getId()), any())).thenReturn(Optional.empty());
        when(coupons.save(any())).thenAnswer(invocation -> {
            IncentiveCoupon coupon = invocation.getArgument(0);
            savedCoupons.put(coupon.getId(), coupon);
            return coupon;
        });
        when(coupons.lockById(any())).thenAnswer(invocation -> Optional.of(savedCoupons.get(invocation.getArgument(0))));
        when(auditEvents.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(outboxEvents.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var previewRequest = new PreviewCouponDistributionRequestDto(
                campaign.getId(),
                "cohort",
                "spring-2026",
                true,
                Instant.now(),
                Instant.now().plusSeconds(86_400),
                1,
                1,
                Map.of("campaignRun", "launch"),
                List.of(
                        new CouponDistributionRecipientInputDto("learner-1", Map.of("email", "one@example.com")),
                        new CouponDistributionRecipientInputDto("learner-2", Map.of()),
                        new CouponDistributionRecipientInputDto("learner-1", Map.of("duplicate", true))));

        var preview = service.preview(previewRequest, admin, "corr-preview");

        assertThat(preview.uniqueRecipients()).isEqualTo(2);
        assertThat(preview.duplicateRecipients()).isEqualTo(1);
        assertThat(preview.previewHash()).startsWith("sha256:");

        var created = service.create(new CreateCouponDistributionRequestDto(
                campaign.getId(),
                "Spring launch cohort",
                "COHORT",
                "spring-2026",
                true,
                previewRequest.startsAt(),
                previewRequest.expiresAt(),
                previewRequest.maxRedemptions(),
                previewRequest.maxRedemptionsPerProfile(),
                previewRequest.metadata(),
                preview.previewHash(),
                "approved recipient preview",
                previewRequest.recipients()), admin, "corr-create");

        assertThat(created.status()).isEqualTo("PENDING_APPROVAL");
        assertThat(created.recipientCount()).isEqualTo(2);
        assertThat(created.recipients()).hasSize(2);

        var approved = service.approve(created.id(), new CouponDistributionActionRequestDto("looks good"),
                admin, "corr-approve");
        assertThat(approved.status()).isEqualTo("APPROVED");
        assertThat(approved.approvedBy()).isEqualTo("1");

        var issued = service.issue(created.id(), new CouponDistributionActionRequestDto("release now"),
                admin, "corr-issue");
        assertThat(issued.status()).isEqualTo("ISSUED");
        assertThat(issued.issuedCount()).isEqualTo(2);
        assertThat(savedCoupons).hasSize(2);
        assertThat(issued.recipients())
                .allSatisfy(row -> {
                    assertThat(row.status()).isEqualTo("ISSUED");
                    assertThat(row.couponId()).isNotNull();
                    assertThat(row.notificationStatus()).isEqualTo("QUEUED");
                });

        var revoked = service.revoke(created.id(), new CouponDistributionActionRequestDto("cohort recalled"),
                admin, "corr-revoke");
        assertThat(revoked.status()).isEqualTo("REVOKED");
        assertThat(revoked.revokedCount()).isEqualTo(2);
        assertThat(savedCoupons.values()).allSatisfy(coupon -> assertThat(coupon.getStatus()).isEqualTo("VOID"));

        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents, atLeastOnce()).save(auditCaptor.capture());
        assertThat(auditCaptor.getAllValues())
                .extracting(IncentiveAuditEvent::getAction)
                .contains(
                        "coupon.distribution_previewed",
                        "coupon.distribution_created",
                        "coupon.distribution_approved",
                        "coupon.distribution_issued",
                        "coupon.distribution_revoked");
        ArgumentCaptor<OutboxEvent> outboxCaptor = ArgumentCaptor.forClass(OutboxEvent.class);
        verify(outboxEvents, atLeastOnce()).save(outboxCaptor.capture());
        assertThat(outboxCaptor.getAllValues()).hasSize(3);
    }

    private IncentiveCampaign campaignEntity() {
        return new IncentiveCampaign(
                "courseflow",
                "lms",
                "WELCOME10",
                "Welcome 10",
                "Welcome coupon campaign",
                "PROMOTION",
                null,
                null,
                100,
                false,
                true,
                true,
                "ALL",
                "USD",
                "[]",
                "[]",
                null,
                null,
                "1");
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

    private static String fakeInternalToken(String clientId, String actorType) {
        String payload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(("{\"azp\":\"" + clientId + "\",\"actor_type\":\"" + actorType + "\"}")
                        .getBytes(StandardCharsets.UTF_8));
        return "test." + payload + ".signature";
    }
}
