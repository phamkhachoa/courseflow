package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.FraudScorePreviewRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class IncentiveFraudScoringServiceTest {

    @Mock
    private IncentiveAccessService access;
    @Mock
    private IncentiveReservationRepository reservations;
    @Mock
    private IncentiveRedemptionRepository redemptions;
    @Mock
    private IncentiveAuditEventRepository auditEvents;

    @Test
    void previewScoresRiskWithExplainableSignalsAndSanitizedAudit() {
        IncentiveFraudScoringService service = new IncentiveFraudScoringService(
                access,
                reservations,
                redemptions,
                auditEvents,
                new ObjectMapper().findAndRegisterModules());
        CurrentUser admin = new CurrentUser(7L, "admin@courseflow.local", "ADMIN", Set.of("ADMIN"));
        UUID couponId = UUID.randomUUID();
        UUID otherCouponId = UUID.randomUUID();
        EvaluateIncentivesRequestDto context = new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                "profile-1",
                "order-123",
                "WEB",
                "USD",
                List.of(
                        "SECRET-001", "SECRET-002", "SECRET-003", "SECRET-004", "SECRET-005",
                        "SECRET-006", "SECRET-007", "SECRET-008", "SECRET-009", "SECRET-010"),
                List.of(couponId, otherCouponId),
                new TransactionContextDto(BigDecimal.valueOf(1_250), BigDecimal.ZERO),
                List.of(),
                Map.of());
        when(reservations.countByTenantIdAndApplicationIdAndProfileIdAndReservedAtGreaterThanEqual(
                eq("courseflow"), eq("lms"), eq("profile-1"), org.mockito.ArgumentMatchers.any(Instant.class)))
                .thenReturn(12L);
        when(redemptions.countByTenantIdAndApplicationIdAndProfileIdAndRedeemedAtGreaterThanEqual(
                eq("courseflow"), eq("lms"), eq("profile-1"), org.mockito.ArgumentMatchers.any(Instant.class)))
                .thenReturn(6L);
        when(redemptions.countByTenantIdAndApplicationIdAndProfileIdAndStatusAndReversedAtGreaterThanEqual(
                eq("courseflow"), eq("lms"), eq("profile-1"), eq("REVERSED"),
                org.mockito.ArgumentMatchers.any(Instant.class)))
                .thenReturn(2L);
        when(redemptions.countByTenantIdAndApplicationIdAndCouponIdInAndRedeemedAtGreaterThanEqual(
                eq("courseflow"), eq("lms"), eq(List.of(couponId, otherCouponId)),
                org.mockito.ArgumentMatchers.any(Instant.class)))
                .thenReturn(25L);

        var response = service.preview(
                new FraudScorePreviewRequestDto(context, 60, "checkout-service", "support risk review"),
                admin,
                "corr-fraud");

        assertThat(response.score()).isEqualTo(100);
        assertThat(response.severity()).isEqualTo("CRITICAL");
        assertThat(response.recommendedAction()).isEqualTo("BLOCK");
        assertThat(response.signals()).extracting("code")
                .contains(
                        "COUPON_SELECTOR_BURST",
                        "MULTIPLE_COUPON_IDS",
                        "HIGH_VALUE_TRANSACTION",
                        "RECENT_RESERVATION_VELOCITY",
                        "RECENT_REDEMPTION_VELOCITY",
                        "RECENT_REVERSAL_HISTORY",
                        "COUPON_ID_SHARED_VELOCITY");
        verify(access).requireAdminAccess("courseflow", "lms", admin);
        verify(access).requireActiveApplication("courseflow", "lms", admin, "fraud-score");
        ArgumentCaptor<IncentiveAuditEvent> audit = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(audit.capture());
        assertThat(audit.getValue().getAction()).isEqualTo("fraud_score.previewed");
        assertThat(audit.getValue().getCorrelationId()).isEqualTo("corr-fraud");
        assertThat(audit.getValue().getPayloadJson())
                .contains("RECENT_REVERSAL_HISTORY")
                .doesNotContain("SECRET-001")
                .doesNotContain("SECRET-010");
    }
}
