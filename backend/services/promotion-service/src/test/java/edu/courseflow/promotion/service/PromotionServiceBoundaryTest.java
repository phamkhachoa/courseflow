package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.commonlibrary.web.CurrentUser.RoleAssignment;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCampaignStatusRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCouponStatusRequestDto;
import edu.courseflow.promotion.model.IncentiveApplication;
import edu.courseflow.promotion.model.IncentiveApplicationClientBinding;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.repository.IncentiveApplicationClientBindingRepository;
import edu.courseflow.promotion.repository.IncentiveApplicationRepository;
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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.junit.jupiter.api.extension.ExtendWith;

@ExtendWith(MockitoExtension.class)
class PromotionServiceBoundaryTest {

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
    IncentiveApplicationRepository applications;
    @Mock
    IncentiveApplicationClientBindingRepository clientBindings;
    @Mock
    CampaignVersionService campaignVersionService;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private PromotionService service;

    @BeforeEach
    void setUp() {
        IncentiveAccessService access = new IncentiveAccessService(
                applications,
                clientBindings,
                auditEvents,
                objectMapper);
        service = new PromotionService(
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
                objectMapper,
                metrics,
                couponFingerprints(),
                new CouponStorageCutoverGuard(coupons, couponFingerprints()),
                CouponAbuseGuard.disabled(metrics),
                AdminOperationRateGuard.disabled(metrics),
                requestSnapshotSanitizer());
    }

    private static CouponCodeFingerprintService couponFingerprints() {
        return new CouponCodeFingerprintService("test", "test-coupon-pepper", "", true);
    }

    private static ReservationRequestSnapshotSanitizer requestSnapshotSanitizer() {
        return new ReservationRequestSnapshotSanitizer("test-request-snapshot-secret-32-byte-value");
    }

    @Test
    void userActorCannotCallRuntimeReserveEvenWhenClientBindingAllowsOperation() {
        IncentiveApplication application = activeApplication();
        when(applications.findByTenantIdAndApplicationId("courseflow", "lms"))
                .thenReturn(Optional.of(application));
        when(clientBindings.findByTenantIdAndApplicationIdAndClientId("courseflow", "lms", "api-gateway"))
                .thenReturn(Optional.of(new IncentiveApplicationClientBinding(
                        "courseflow",
                        "lms",
                        "api-gateway",
                        "ACTIVE",
                        "[\"reserve\"]",
                        "admin")));

        assertThatThrownBy(() -> service.reserve(
                new ReserveIncentiveRequestDto("idem-1", context()),
                new CurrentUser(
                        1L,
                        "learner@example.com",
                        "STUDENT",
                        Set.of("STUDENT"),
                        Set.of(),
                        fakeInternalToken("api-gateway", "user")),
                "corr-user"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("trusted application service");
    }

    @Test
    void unboundServiceClientCannotCallRuntimeReserve() {
        when(applications.findByTenantIdAndApplicationId("courseflow", "lms"))
                .thenReturn(Optional.of(activeApplication()));
        when(clientBindings.findByTenantIdAndApplicationIdAndClientId("courseflow", "lms", "checkout-service"))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.reserve(
                new ReserveIncentiveRequestDto("idem-2", context()),
                new CurrentUser(
                        null,
                        null,
                        null,
                        Set.of(),
                        Set.of(),
                        fakeInternalToken("checkout-service", "service", InternalScopes.PROMOTION_RESERVE)),
                "corr-service"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("not bound");
    }

    @Test
    void scopedReviewerCannotViewCouponStorageInventoryReport() {
        CurrentUser reviewer = new CurrentUser(
                2L,
                "reviewer@example.com",
                "INCENTIVE_REVIEWER",
                Set.of(),
                Set.of(new RoleAssignment("INCENTIVE_REVIEWER", "APPLICATION", "courseflow:lms")),
                fakeInternalToken("api-gateway", "user"));

        assertThatThrownBy(() -> service.couponStorageInventory(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.empty(),
                Optional.empty(),
                reviewer))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("manage incentive application");
    }

    @Test
    void emptyAdminBindingCannotChangeCampaignStatus() {
        IncentiveCampaign campaign = campaign();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        stubClientBinding("api-gateway", "[]");

        assertThatThrownBy(() -> service.updateCampaignStatus(
                campaign.getId(),
                new UpdateCampaignStatusRequestDto("PAUSED", "pause rollout"),
                adminUser(),
                "corr-campaign-status"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("no allowed operations");
    }

    @Test
    void emptyAdminBindingCannotChangeCouponStatus() {
        IncentiveCampaign campaign = campaign();
        IncentiveCoupon coupon = new IncentiveCoupon(
                campaign.getId(),
                "SA****10",
                couponFingerprints().primaryFingerprint("SAVE10"),
                "SA****10",
                null,
                null,
                Instant.now().plusSeconds(3600),
                null,
                null,
                "{}");
        when(coupons.lockById(coupon.getId())).thenReturn(Optional.of(coupon));
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        stubClientBinding("api-gateway", "[]");

        assertThatThrownBy(() -> service.updateCouponStatus(
                coupon.getId(),
                new UpdateCouponStatusRequestDto("VOID", "bad distribution"),
                adminUser(),
                "corr-coupon-status"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("no allowed operations");
    }

    private void stubClientBinding(String clientId, String allowedOperations) {
        when(applications.findByTenantIdAndApplicationId("courseflow", "lms"))
                .thenReturn(Optional.of(activeApplication()));
        when(clientBindings.findByTenantIdAndApplicationIdAndClientId("courseflow", "lms", clientId))
                .thenReturn(Optional.of(new IncentiveApplicationClientBinding(
                        "courseflow",
                        "lms",
                        clientId,
                        "ACTIVE",
                        allowedOperations,
                        "admin")));
    }

    private IncentiveApplication activeApplication() {
        return new IncentiveApplication("courseflow", "lms", "CourseFlow LMS", "ACTIVE", "admin");
    }

    private IncentiveCampaign campaign() {
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
                        Map.of("amount", BigDecimal.TEN)))),
                100,
                1,
                "admin@example.com");
    }

    private EvaluateIncentivesRequestDto context() {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                "1",
                "order-1",
                "WEB",
                "USD",
                List.of(),
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.ZERO),
                List.of(),
                Map.of());
    }

    private static String fakeInternalToken(String clientId, String actorType) {
        return fakeInternalToken(clientId, actorType, new String[0]);
    }

    private static String fakeInternalToken(String clientId, String actorType, String... scopes) {
        String scopeClaim = scopes == null || scopes.length == 0
                ? ""
                : ",\"scope\":\"" + String.join(" ", scopes) + "\",\"scp\":[\""
                + String.join("\",\"", scopes) + "\"]";
        String payload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(("{\"azp\":\"" + clientId + "\",\"actor_type\":\"" + actorType + "\""
                        + scopeClaim + "}")
                        .getBytes(StandardCharsets.UTF_8));
        return "test." + payload + ".signature";
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
}
