package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.CancelReservationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CommitReservationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCampaignRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.GenerateCouponsRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import edu.courseflow.promotion.model.IncentiveRedemption;
import edu.courseflow.promotion.model.IncentiveReservation;
import edu.courseflow.promotion.model.OutboxEvent;
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
import java.time.Duration;
import java.time.Instant;
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

@ExtendWith(MockitoExtension.class)
class PromotionServiceTraceabilityTest {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };
    private static final UUID COUPON_ID = UUID.fromString("00000000-0000-0000-0000-000000000777");

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
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private PromotionService service;

    @BeforeEach
    void setUp() {
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
    void createCampaignPersistsAuditTraceMetadata() {
        CurrentUser admin = admin();
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(campaigns.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.createCampaign(new CreateCampaignRequestDto(
                "courseflow",
                "lms",
                "WELCOME10",
                "Welcome campaign",
                null,
                "PROMOTION",
                Instant.now().minusSeconds(60),
                Instant.now().plusSeconds(3600),
                10,
                false,
                true,
                false,
                "ALL",
                "USD",
                List.of(),
                List.of(new ActionSpecDto("ORDER_FIXED_OFF", 1, Map.of("amount", 10))),
                100,
                1), admin, "corr-campaign");

        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("campaign.created");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-campaign");
        assertThat(audit.getSourceClientId()).isEqualTo("api-gateway");
        assertThat(audit.getActorId()).isEqualTo("1");
    }

    @Test
    void generateCouponsPersistsAuditTraceMetadata() {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(coupons.findByCampaignIdAndNormalizedCode(eq(campaign.getId()), any()))
                .thenReturn(Optional.empty());
        when(coupons.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.generateCoupons(new GenerateCouponsRequestDto(
                campaign.getId(),
                "VIP",
                2,
                8,
                null,
                Instant.now().minusSeconds(60),
                Instant.now().plusSeconds(3600),
                1,
                1,
                Map.of("batch", "spring")), admin, "corr-coupons");

        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("coupon.batch_generated");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-coupons");
        assertThat(audit.getSourceClientId()).isEqualTo("api-gateway");
        assertThat(audit.getPayloadJson()).contains("\"created\":2");
    }

    @Test
    void reversePersistsAuditAndOutboxTraceMetadata() throws Exception {
        CurrentUser admin = admin();
        IncentiveReservation reservation = reservation(Instant.now().plusSeconds(600));
        reservation.commit("order-1");
        IncentiveRedemption redemption = new IncentiveRedemption(reservation);
        AtomicReference<String> requestHash = inProgressIdempotency("REVERSE", "reverse-key-1");
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(redemptions.lockById(redemption.getId())).thenReturn(Optional.of(redemption));
        when(reservations.findById(reservation.getId())).thenReturn(Optional.of(reservation));
        when(redemptions.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.reverse(redemption.getId(), new ReverseRedemptionRequestDto(
                "reverse-key-1",
                "customer refund"), admin, "corr-reverse");

        assertThat(requestHash).hasValueSatisfying(value -> assertThat(value).isNotBlank());
        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("redemption.reversed");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-reverse");
        assertThat(audit.getSourceClientId()).isEqualTo("api-gateway");
        assertThat(audit.getPayloadJson())
                .contains("\"quotaPolicy\":\"NO_RELEASE_ON_COMMITTED_REVERSAL\"")
                .contains("\"quotaReleased\":false");

        ArgumentCaptor<OutboxEvent> outboxCaptor = ArgumentCaptor.forClass(OutboxEvent.class);
        verify(outboxEvents).save(outboxCaptor.capture());
        Map<String, Object> payload = readMap((String) ReflectionTestUtils.getField(outboxCaptor.getValue(), "payload"));
        assertThat(payload).containsEntry("correlationId", "corr-reverse");
        assertThat(payload).containsEntry("sourceClientId", "api-gateway");
        assertThat(payload).containsEntry("couponId", COUPON_ID.toString());
        assertThat((List<?>) payload.get("effects"))
                .first()
                .satisfies(this::assertEffectId);
        verify(metrics).reversal("success", "REVERSED");
        verify(metrics).runtimeOperation(eq("reverse"), eq("success"), eq("reversed"), any(Duration.class));
    }

    @Test
    void commitPersistsAuditAndOutboxTraceMetadata() throws Exception {
        CurrentUser serviceActor = serviceActor();
        IncentiveReservation reservation = reservation(Instant.now().plusSeconds(600));
        AtomicReference<String> requestHash = inProgressIdempotency("COMMIT", "commit-key-1");
        when(access.sourceClientId(serviceActor)).thenReturn("checkout-service");
        when(reservations.lockById(reservation.getId())).thenReturn(Optional.of(reservation));
        when(reservations.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(redemptions.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.commit(reservation.getId(), new CommitReservationRequestDto(
                "commit-key-1",
                "order-1"), serviceActor, "corr-commit");

        assertThat(requestHash).hasValueSatisfying(value -> assertThat(value).isNotBlank());
        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("redemption.committed");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-commit");
        assertThat(audit.getSourceClientId()).isEqualTo("checkout-service");

        ArgumentCaptor<OutboxEvent> outboxCaptor = ArgumentCaptor.forClass(OutboxEvent.class);
        verify(outboxEvents).save(outboxCaptor.capture());
        Map<String, Object> payload = readMap((String) ReflectionTestUtils.getField(outboxCaptor.getValue(), "payload"));
        assertThat(payload).containsEntry("correlationId", "corr-commit");
        assertThat(payload).containsEntry("sourceClientId", "checkout-service");
        assertThat(payload).containsEntry("couponId", COUPON_ID.toString());
        assertThat((List<?>) payload.get("effects"))
                .first()
                .satisfies(this::assertEffectId);
        verify(metrics).runtimeOperation(eq("commit"), eq("success"), eq("committed"), any(Duration.class));
    }

    @Test
    void cancelPersistsAuditTraceMetadata() {
        CurrentUser serviceActor = serviceActor();
        IncentiveCampaign campaign = campaign();
        IncentiveReservation reservation = reservation(campaign.getId(), Instant.now().plusSeconds(600));
        inProgressIdempotency("CANCEL", "cancel-key-1");
        when(access.sourceClientId(serviceActor)).thenReturn("checkout-service");
        when(reservations.lockById(reservation.getId())).thenReturn(Optional.of(reservation));
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(reservations.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.cancel(reservation.getId(), new CancelReservationRequestDto(
                "cancel-key-1",
                "user abandoned checkout"), serviceActor, "corr-cancel");

        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("reservation.cancelled");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-cancel");
        assertThat(audit.getSourceClientId()).isEqualTo("checkout-service");
        assertThat(audit.getNote()).isEqualTo("user abandoned checkout");
        verify(metrics).runtimeOperation(eq("cancel"), eq("success"), eq("cancelled"), any(Duration.class));
    }

    @Test
    void reservationExpiryPersistsSyntheticSystemTraceMetadata() {
        IncentiveCampaign campaign = campaign();
        IncentiveReservation reservation = reservation(campaign.getId(), Instant.now().minusSeconds(60));
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(reservations.lockExpiredReservedForExpiry(any(), eq(100)))
                .thenReturn(List.of(reservation));

        int expired = service.expireReservedReservations(100);

        assertThat(expired).isEqualTo(1);
        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("reservation.expired");
        assertThat(audit.getActorId()).isNull();
        assertThat(audit.getCorrelationId()).startsWith("reservation-expiry-");
        assertThat(audit.getSourceClientId()).isEqualTo("promotion-service/reservation-expiry");
        verify(metrics).reservationExpiry(eq("success"), eq(1), any(Duration.class));
        verify(metrics).runtimeOperation(eq("reservation_expiry"), eq("success"), eq("success"), any(Duration.class));
    }

    private AtomicReference<String> inProgressIdempotency(String operation, String idempotencyKey) {
        AtomicReference<String> requestHash = new AtomicReference<>();
        when(idempotencyKeys.insertInProgressIfAbsent(
                any(UUID.class),
                eq("courseflow"),
                eq("lms"),
                eq(operation),
                eq(idempotencyKey),
                any(),
                any()))
                .thenAnswer(invocation -> {
                    requestHash.set(invocation.getArgument(5));
                    return 1;
                });
        when(idempotencyKeys.lockByScope("courseflow", "lms", operation, idempotencyKey))
                .thenAnswer(invocation -> Optional.of(inProgressKey(
                        operation,
                        idempotencyKey,
                        requestHash.get())));
        return requestHash;
    }

    private IncentiveIdempotencyKey inProgressKey(String operation, String idempotencyKey, String requestHash) {
        IncentiveIdempotencyKey key = new IncentiveIdempotencyKey(
                "courseflow",
                "lms",
                operation,
                idempotencyKey,
                requestHash,
                "{}",
                Instant.now().plusSeconds(3600));
        ReflectionTestUtils.setField(key, "status", "IN_PROGRESS");
        return key;
    }

    private IncentiveAuditEvent capturedAudit() {
        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        return auditCaptor.getValue();
    }

    private Map<String, Object> readMap(String json) throws Exception {
        return objectMapper.readValue(json, MAP_TYPE);
    }

    @SuppressWarnings("unchecked")
    private void assertEffectId(Object effect) {
        assertThat((Map<String, Object>) effect).containsEntry("effectId", "effect-1");
    }

    private IncentiveReservation reservation(Instant expiresAt) {
        return reservation(UUID.randomUUID(), expiresAt);
    }

    private IncentiveReservation reservation(UUID campaignId, Instant expiresAt) {
        return new IncentiveReservation(
                "courseflow",
                "lms",
                campaignId,
                1,
                COUPON_ID,
                "profile-1",
                "order-1",
                """
                        [{
                          "effectId": "effect-1",
                          "type": "ORDER_FIXED_OFF",
                          "benefitType": "DISCOUNT",
                          "actionType": "ORDER_FIXED_OFF",
                          "targetType": "ORDER",
                          "amount": 5.00,
                          "currency": "USD",
                          "unit": "MONEY",
                          "quantity": 5.00,
                          "campaignVersion": 1,
                          "metadata": {}
                        }]
                        """,
                "{}",
                "request-hash",
                "[]",
                expiresAt);
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

    private CurrentUser admin() {
        return new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of());
    }

    private CurrentUser serviceActor() {
        return new CurrentUser(
                null,
                null,
                null,
                Set.of(),
                Set.of());
    }
}
