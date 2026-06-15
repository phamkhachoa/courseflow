package edu.courseflow.analytics.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import edu.courseflow.analytics.dto.ReportingDtos.WarehouseExportRequestDto;
import edu.courseflow.analytics.model.MarketingFunnelMetric;
import edu.courseflow.analytics.repository.CourseCompletionMetricRepository;
import edu.courseflow.analytics.repository.MarketingFunnelMetricRepository;
import edu.courseflow.analytics.repository.OrgDashboardMetricRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageRequest;

@ExtendWith(MockitoExtension.class)
class WarehouseExportServiceTest {

    @Mock
    private MarketingFunnelMetricRepository marketingFunnels;
    @Mock
    private CourseCompletionMetricRepository courseCompletions;
    @Mock
    private OrgDashboardMetricRepository orgDashboards;

    @Test
    void exportsMarketingFunnelDatasetWithManifestChecksumAndTruncation() {
        WarehouseExportService service = service();
        LocalDate from = LocalDate.of(2026, 6, 1);
        LocalDate to = LocalDate.of(2026, 6, 15);
        when(marketingFunnels.exportFunnel(
                eq("courseflow"),
                eq("lms"),
                eq(null),
                eq(null),
                eq(from),
                eq(to),
                eq(PageRequest.of(0, 2))))
                .thenReturn(List.of(
                        new MarketingFunnelMetric(
                                "courseflow", "lms", null, "email", "IMPRESSION", from, 10),
                        new MarketingFunnelMetric(
                                "courseflow", "lms", null, "email", "COURSE_VIEW", from, 4)));

        var response = service.export(new WarehouseExportRequestDto(
                "marketing-funnel-daily",
                null,
                "courseflow",
                "lms",
                null,
                null,
                from,
                to,
                1));

        assertThat(response.dataset()).isEqualTo("MARKETING_FUNNEL_DAILY");
        assertThat(response.schemaVersion()).isEqualTo(1);
        assertThat(response.format()).isEqualTo("CSV");
        assertThat(response.rowCount()).isEqualTo(1);
        assertThat(response.truncated()).isTrue();
        assertThat(response.columns()).extracting("name")
                .containsExactly(
                        "tenant_id",
                        "application_id",
                        "campaign_code",
                        "source",
                        "stage",
                        "bucket_date",
                        "event_count",
                        "updated_at");
        assertThat(response.content()).startsWith("tenant_id,application_id,campaign_code,source,stage");
        assertThat(response.content()).contains("courseflow,lms,,email,IMPRESSION,2026-06-01,10,");
        assertThat(response.contentSha256()).startsWith("sha256:");
        assertThat(response.exportId()).startsWith("sha256:");
    }

    @Test
    void marketingFunnelDatasetRequiresTenantAndApplicationFilters() {
        WarehouseExportService service = service();

        assertThatThrownBy(() -> service.export(new WarehouseExportRequestDto(
                "MARKETING_FUNNEL_DAILY",
                "CSV",
                null,
                "lms",
                null,
                null,
                null,
                null,
                null)))
                .isInstanceOf(BadRequestException.class);
    }

    @Test
    void rejectsUnsupportedExportFormat() {
        WarehouseExportService service = service();

        assertThatThrownBy(() -> service.export(new WarehouseExportRequestDto(
                "COURSE_COMPLETION_SNAPSHOT",
                "PARQUET",
                null,
                null,
                null,
                null,
                null,
                null,
                null)))
                .isInstanceOf(BadRequestException.class);
    }

    private WarehouseExportService service() {
        return new WarehouseExportService(marketingFunnels, courseCompletions, orgDashboards);
    }
}
