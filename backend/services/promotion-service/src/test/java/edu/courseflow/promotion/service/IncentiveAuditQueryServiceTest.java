package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveApplicationRepository;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class IncentiveAuditQueryServiceTest {

    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveCampaignRepository campaigns;
    @Mock
    IncentiveApplicationRepository applications;
    @Mock
    IncentiveRedemptionRepository redemptions;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private IncentiveAuditQueryService service;

    @BeforeEach
    void setUp() {
        service = new IncentiveAuditQueryService(
                auditEvents,
                campaigns,
                applications,
                redemptions,
                access,
                new ObjectMapper().findAndRegisterModules(),
                metrics);
    }

    @Test
    void queryPassesTraceFiltersAndMapsTraceFields() {
        IncentiveAuditEvent event = new IncentiveAuditEvent(
                "courseflow",
                "lms",
                "coupon-1",
                "coupon",
                "coupon.created",
                "admin@example.com",
                "created",
                "{\"maskedCode\":\"WE****ME\"}",
                "corr-1",
                "api-gateway");
        when(auditEvents.search(
                eq("courseflow"),
                eq("lms"),
                eq("coupon"),
                eq("coupon-1"),
                eq("coupon.created"),
                eq("admin@example.com"),
                eq("corr-1"),
                eq("api-gateway"),
                eq(Instant.parse("2026-01-01T00:00:00Z")),
                eq(Instant.parse("2026-01-31T23:59:59Z")),
                any(Pageable.class)))
                .thenReturn(List.of(event));

        var response = service.query(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.of("coupon"),
                Optional.of("coupon-1"),
                Optional.of("coupon.created"),
                Optional.of("admin@example.com"),
                Optional.of("corr-1"),
                Optional.of("api-gateway"),
                Optional.of(Instant.parse("2026-01-01T00:00:00Z")),
                Optional.of(Instant.parse("2026-01-31T23:59:59Z")),
                Optional.of(25),
                user());

        assertThat(response.limit()).isEqualTo(25);
        assertThat(response.hasMore()).isFalse();
        assertThat(response.items()).hasSize(1);
        assertThat(response.items().getFirst().correlationId()).isEqualTo("corr-1");
        assertThat(response.items().getFirst().sourceClientId()).isEqualTo("api-gateway");
        assertThat(response.items().getFirst().payload()).containsEntry("maskedCode", "WE****ME");
        verify(access).requireReviewAccess("courseflow", "lms", user());
        verify(metrics).auditQuery(eq("explorer"), any());
    }

    @Test
    void blankTraceFiltersAreIgnoredAndLimitIsBounded() {
        when(auditEvents.search(
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(Instant.EPOCH),
                eq(Instant.parse("9999-12-31T23:59:59Z")),
                any(Pageable.class)))
                .thenReturn(List.of());

        var response = service.query(
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(" "),
                Optional.of(" "),
                Optional.empty(),
                Optional.empty(),
                Optional.of(500),
                user());

        assertThat(response.limit()).isEqualTo(200);
        assertThat(response.items()).isEmpty();
        verify(access).requirePlatformAdmin(user());
    }

    private CurrentUser user() {
        return new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of());
    }
}
