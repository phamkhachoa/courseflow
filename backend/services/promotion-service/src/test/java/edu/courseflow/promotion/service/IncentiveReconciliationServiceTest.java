package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveEffectDto;
import edu.courseflow.promotion.repository.IncentiveLedgerEntryRepository;
import edu.courseflow.promotion.repository.IncentiveLedgerEntryRepository.ReconciliationLedgerRow;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class IncentiveReconciliationServiceTest {

    @Mock
    IncentiveLedgerEntryRepository ledgerEntries;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private IncentiveReconciliationService service;

    @BeforeEach
    void setUp() {
        service = new IncentiveReconciliationService(ledgerEntries, access, objectMapper, metrics);
    }

    @Test
    void queryMapsLedgerEffectsToReadOnlyReconciliationRows() throws Exception {
        UUID ledgerEntryId = UUID.randomUUID();
        UUID redemptionId = UUID.randomUUID();
        UUID reservationId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        UUID couponId = UUID.randomUUID();
        Instant now = Instant.parse("2026-06-14T10:00:00Z");
        String effectJson = objectMapper.writeValueAsString(List.of(new IncentiveEffectDto(
                "ORDER_FIXED_OFF",
                "ORDER",
                null,
                BigDecimal.TEN,
                "USD",
                Map.of("campaignId", campaignId.toString(), "campaignVersion", 2),
                "effect-1",
                "DISCOUNT",
                "ORDER_FIXED_OFF",
                "MONEY",
                BigDecimal.TEN,
                2)));
        when(ledgerEntries.searchReconciliationRows(
                eq("courseflow"),
                eq("lms"),
                eq("profile-1"),
                eq("order-1"),
                eq(campaignId),
                eq(couponId),
                eq(redemptionId),
                eq(reservationId),
                eq("COMMIT"),
                eq(Instant.parse("2026-06-14T00:00:00Z")),
                eq(Instant.parse("2026-06-15T00:00:00Z")),
                eq(26)))
                .thenReturn(List.of(new TestRow(
                        ledgerEntryId,
                        "courseflow",
                        "lms",
                        "COMMIT",
                        reservationId,
                        redemptionId,
                        campaignId,
                        2,
                        couponId,
                        "profile-1",
                        "order-1",
                        effectJson,
                        now,
                        "REDEEMED",
                        now,
                        null,
                        "incentive.redemption.committed",
                        now.plusSeconds(5),
                        "corr-1",
                        "checkout-service")));
        when(ledgerEntries.countByRedemptionIdAndEntryType(redemptionId, "COMMIT")).thenReturn(1L);

        var response = service.query(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.of("profile-1"),
                Optional.of("order-1"),
                Optional.of(campaignId),
                Optional.of(couponId),
                Optional.of(redemptionId),
                Optional.of(reservationId),
                Optional.of("commit"),
                Optional.of(Instant.parse("2026-06-14T00:00:00Z")),
                Optional.of(Instant.parse("2026-06-15T00:00:00Z")),
                Optional.of(25),
                adminUser());

        assertThat(response.items()).hasSize(1);
        var item = response.items().getFirst();
        assertThat(item.reconciliationStatus()).isEqualTo("MATCHED");
        assertThat(item.direction()).isEqualTo("APPLY");
        assertThat(item.quotaPolicy()).isEqualTo("NO_QUOTA_CHANGE");
        assertThat(item.quotaReleased()).isNull();
        assertThat(item.outboxStatus()).isEqualTo("PUBLISHED");
        assertThat(item.reconciliationKey()).isEqualTo(redemptionId + ":COMMIT:effect-1");
        assertThat(item.effect().effectId()).isEqualTo("effect-1");
        assertThat(item.effect().amount()).isEqualByComparingTo(BigDecimal.TEN);
        assertThat(item.effect().currency()).isEqualTo("USD");
        assertThat(response.limit()).isEqualTo(25);
        assertThat(response.hasMore()).isFalse();
        verify(access).requireAdminAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(metrics).reconciliationQuery(eq("success"), any());
    }

    @Test
    void queryRequiresTenantAndApplicationScope() {
        assertThatThrownBy(() -> service.query(
                Optional.of("courseflow"),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(25),
                adminUser()))
                .hasMessageContaining("tenantId and applicationId");
    }

    private static CurrentUser adminUser() {
        return new CurrentUser(1L, "admin@example.com", "ADMIN", Set.of("ADMIN"), Set.of(), null);
    }

    private record TestRow(
            UUID ledgerEntryId,
            String tenantId,
            String applicationId,
            String entryType,
            UUID reservationId,
            UUID redemptionId,
            UUID campaignId,
            Integer campaignVersion,
            UUID couponId,
            String profileId,
            String externalReference,
            String effectJson,
            Instant ledgerCreatedAt,
            String redemptionStatus,
            Instant redeemedAt,
            Instant reversedAt,
            String outboxEventType,
            Instant outboxPublishedAt,
            String correlationId,
            String sourceClientId
    ) implements ReconciliationLedgerRow {
        @Override
        public UUID getLedgerEntryId() { return ledgerEntryId; }
        @Override
        public String getTenantId() { return tenantId; }
        @Override
        public String getApplicationId() { return applicationId; }
        @Override
        public String getEntryType() { return entryType; }
        @Override
        public UUID getReservationId() { return reservationId; }
        @Override
        public UUID getRedemptionId() { return redemptionId; }
        @Override
        public UUID getCampaignId() { return campaignId; }
        @Override
        public Integer getCampaignVersion() { return campaignVersion; }
        @Override
        public UUID getCouponId() { return couponId; }
        @Override
        public String getProfileId() { return profileId; }
        @Override
        public String getExternalReference() { return externalReference; }
        @Override
        public String getEffectJson() { return effectJson; }
        @Override
        public Instant getLedgerCreatedAt() { return ledgerCreatedAt; }
        @Override
        public String getRedemptionStatus() { return redemptionStatus; }
        @Override
        public Instant getRedeemedAt() { return redeemedAt; }
        @Override
        public Instant getReversedAt() { return reversedAt; }
        @Override
        public String getOutboxEventType() { return outboxEventType; }
        @Override
        public Instant getOutboxPublishedAt() { return outboxPublishedAt; }
        @Override
        public String getCorrelationId() { return correlationId; }
        @Override
        public String getSourceClientId() { return sourceClientId; }
    }
}
