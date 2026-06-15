package edu.courseflow.analytics.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.analytics.dto.ReportingDtos.RecordMarketingFunnelEventRequestDto;
import edu.courseflow.analytics.model.MarketingFunnelEventReceipt;
import edu.courseflow.analytics.model.MarketingFunnelMetric;
import edu.courseflow.analytics.repository.ReportingRepository;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ReportingServiceTest {

    @Mock
    private ReportingRepository reporting;

    @Test
    void marketingFunnelAggregatesStageCountsAndConversionRates() {
        ReportingService service = new ReportingService(reporting);
        LocalDate from = LocalDate.of(2026, 6, 1);
        LocalDate to = LocalDate.of(2026, 6, 7);
        when(reporting.marketingFunnel(
                eq("courseflow"),
                eq("lms"),
                eq("SUMMER"),
                eq("email"),
                eq(from),
                eq(to),
                eq(500)))
                .thenReturn(List.of(
                        metric("IMPRESSION", from, 100),
                        metric("COURSE_VIEW", from, 40),
                        metric("COURSE_VIEW", to, 20),
                        metric("CHECKOUT_STARTED", to, 30),
                        metric("PAYMENT_SUCCESS", to, 18),
                        metric("ENROLLED", to, 15)));

        var response = service.marketingFunnel(" courseflow ", " lms ", " SUMMER ", " email ", from, to, 500);

        assertThat(response.stages()).extracting("stage")
                .containsExactly("IMPRESSION", "COURSE_VIEW", "CHECKOUT_STARTED", "PAYMENT_SUCCESS", "ENROLLED");
        assertThat(response.stages()).extracting("count")
                .containsExactly(100L, 60L, 30L, 18L, 15L);
        assertThat(response.stages().get(1).stepConversionRate()).isEqualTo(60.0);
        assertThat(response.stages().get(2).stepConversionRate()).isEqualTo(50.0);
        assertThat(response.stages().get(4).overallConversionRate()).isEqualTo(15.0);
        assertThat(response.rows()).hasSize(6);
        verify(reporting).marketingFunnel("courseflow", "lms", "SUMMER", "email", from, to, 500);
    }

    @Test
    void marketingFunnelNormalizesDefaultAndMaxLimit() {
        ReportingService service = new ReportingService(reporting);
        when(reporting.marketingFunnel(
                eq("courseflow"),
                eq("lms"),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(5000)))
                .thenReturn(List.of());

        var response = service.marketingFunnel("courseflow", "lms", null, null, null, null, 50_000);

        assertThat(response.stages()).hasSize(5);
        assertThat(response.stages()).allSatisfy(stage -> assertThat(stage.count()).isZero());
        verify(reporting).marketingFunnel("courseflow", "lms", null, null, null, null, 5000);
    }

    @Test
    void recordMarketingFunnelEventIsIdempotentByEventIdAndRequestHash() {
        ReportingService service = new ReportingService(reporting);
        UUID eventId = UUID.randomUUID();
        LocalDate bucketDate = LocalDate.of(2026, 6, 15);
        AtomicReference<MarketingFunnelEventReceipt> receipt = new AtomicReference<>();
        when(reporting.findMarketingFunnelReceipt(eventId)).thenAnswer(invocation -> Optional.ofNullable(receipt.get()));
        doAnswer(invocation -> {
            receipt.set(invocation.getArgument(0));
            return null;
        }).when(reporting).saveMarketingFunnelReceipt(org.mockito.ArgumentMatchers.any());

        RecordMarketingFunnelEventRequestDto request = new RecordMarketingFunnelEventRequestDto(
                eventId,
                "courseflow",
                "lms",
                "SUMMER",
                "email",
                "course-view",
                bucketDate,
                Instant.parse("2026-06-15T01:00:00Z"),
                3L);
        CurrentUser admin = new CurrentUser(1L, "admin@courseflow.local", "ADMIN", Set.of("ADMIN"));

        var first = service.recordMarketingFunnelEvent(request, admin);
        var second = service.recordMarketingFunnelEvent(request, admin);

        assertThat(first.accepted()).isTrue();
        assertThat(first.duplicate()).isFalse();
        assertThat(second.accepted()).isFalse();
        assertThat(second.duplicate()).isTrue();
        assertThat(second.stage()).isEqualTo("COURSE_VIEW");
        verify(reporting, times(1)).incrementMarketingFunnelMetric(
                "courseflow",
                "lms",
                "SUMMER",
                "email",
                "COURSE_VIEW",
                bucketDate,
                3L);
    }

    private static MarketingFunnelMetric metric(String stage, LocalDate bucketDate, long count) {
        return new MarketingFunnelMetric("courseflow", "lms", "SUMMER", "email", stage, bucketDate, count);
    }
}
