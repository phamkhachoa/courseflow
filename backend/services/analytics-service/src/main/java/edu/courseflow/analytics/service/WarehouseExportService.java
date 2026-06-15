package edu.courseflow.analytics.service;

import edu.courseflow.analytics.dto.ReportingDtos.WarehouseExportColumnDto;
import edu.courseflow.analytics.dto.ReportingDtos.WarehouseExportRequestDto;
import edu.courseflow.analytics.dto.ReportingDtos.WarehouseExportResponseDto;
import edu.courseflow.analytics.model.CourseCompletionMetric;
import edu.courseflow.analytics.model.MarketingFunnelMetric;
import edu.courseflow.analytics.model.OrgDashboardMetric;
import edu.courseflow.analytics.repository.CourseCompletionMetricRepository;
import edu.courseflow.analytics.repository.MarketingFunnelMetricRepository;
import edu.courseflow.analytics.repository.OrgDashboardMetricRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class WarehouseExportService {

    private static final int SCHEMA_VERSION = 1;
    private static final int DEFAULT_LIMIT = 5_000;
    private static final int MAX_LIMIT = 10_000;

    private final MarketingFunnelMetricRepository marketingFunnels;
    private final CourseCompletionMetricRepository courseCompletions;
    private final OrgDashboardMetricRepository orgDashboards;

    public WarehouseExportService(MarketingFunnelMetricRepository marketingFunnels,
                                  CourseCompletionMetricRepository courseCompletions,
                                  OrgDashboardMetricRepository orgDashboards) {
        this.marketingFunnels = marketingFunnels;
        this.courseCompletions = courseCompletions;
        this.orgDashboards = orgDashboards;
    }

    @Transactional(readOnly = true)
    public WarehouseExportResponseDto export(WarehouseExportRequestDto request) {
        Dataset dataset = Dataset.from(request == null ? null : request.dataset());
        String format = normalizeFormat(request == null ? null : request.format());
        int requestedLimit = normalizeLimit(request == null ? null : request.limit());
        int fetchLimit = requestedLimit + 1;
        List<WarehouseExportColumnDto> columns = columns(dataset);
        List<List<String>> rows = rows(dataset, request, fetchLimit);
        boolean truncated = rows.size() > requestedLimit;
        List<List<String>> boundedRows = truncated ? rows.subList(0, requestedLimit) : rows;
        String content = csv(columns, boundedRows);
        String contentSha = sha256(content);
        Instant generatedAt = Instant.now();
        String exportId = sha256(String.join("|",
                dataset.name(),
                String.valueOf(SCHEMA_VERSION),
                String.valueOf(request == null ? null : request.tenantId()),
                String.valueOf(request == null ? null : request.applicationId()),
                String.valueOf(request == null ? null : request.campaignCode()),
                String.valueOf(request == null ? null : request.source()),
                String.valueOf(request == null ? null : request.from()),
                String.valueOf(request == null ? null : request.to()),
                String.valueOf(requestedLimit),
                contentSha));
        return new WarehouseExportResponseDto(
                exportId,
                dataset.name(),
                SCHEMA_VERSION,
                format,
                "text/csv",
                filename(dataset, generatedAt),
                boundedRows.size(),
                truncated,
                request == null ? null : request.from(),
                request == null ? null : request.to(),
                columns,
                contentSha,
                content,
                generatedAt);
    }

    private List<List<String>> rows(Dataset dataset, WarehouseExportRequestDto request, int limit) {
        return switch (dataset) {
            case MARKETING_FUNNEL_DAILY -> marketingFunnelRows(request, limit);
            case COURSE_COMPLETION_SNAPSHOT -> courseCompletionRows(limit);
            case ORG_DASHBOARD_SNAPSHOT -> orgDashboardRows(limit);
        };
    }

    private List<List<String>> marketingFunnelRows(WarehouseExportRequestDto request, int limit) {
        String tenantId = required(request == null ? null : request.tenantId(), "tenantId");
        String applicationId = required(request == null ? null : request.applicationId(), "applicationId");
        return marketingFunnels.exportFunnel(
                        tenantId,
                        applicationId,
                        blankToNull(request.campaignCode()),
                        blankToNull(request.source()),
                        request.from(),
                        request.to(),
                        PageRequest.of(0, limit))
                .stream()
                .map(this::marketingFunnelRow)
                .toList();
    }

    private List<String> marketingFunnelRow(MarketingFunnelMetric metric) {
        return List.of(
                value(metric.getTenantId()),
                value(metric.getApplicationId()),
                value(metric.getCampaignCode()),
                value(metric.getSource()),
                value(metric.getStage()),
                value(metric.getBucketDate()),
                value(metric.getEventCount()),
                value(metric.getUpdatedAt()));
    }

    private List<List<String>> courseCompletionRows(int limit) {
        return courseCompletions.exportSnapshot(PageRequest.of(0, limit))
                .stream()
                .map(this::courseCompletionRow)
                .toList();
    }

    private List<String> courseCompletionRow(CourseCompletionMetric metric) {
        return List.of(
                value(metric.getCourseId()),
                value(metric.getEnrolledCount()),
                value(metric.getCompletedCount()),
                value(metric.getCompletionRate()),
                value(metric.getAvgDaysToComplete()),
                value(metric.getUpdatedAt()));
    }

    private List<List<String>> orgDashboardRows(int limit) {
        return orgDashboards.exportSnapshot(PageRequest.of(0, limit))
                .stream()
                .map(this::orgDashboardRow)
                .toList();
    }

    private List<String> orgDashboardRow(OrgDashboardMetric metric) {
        return List.of(
                value(metric.getOrgId()),
                value(metric.getActiveLearners()),
                value(metric.getTotalEnrollments()),
                value(metric.getAvgCompletionRate()),
                value(metric.getUpdatedAt()));
    }

    private List<WarehouseExportColumnDto> columns(Dataset dataset) {
        return switch (dataset) {
            case MARKETING_FUNNEL_DAILY -> List.of(
                    column("tenant_id", "string", false, "Tenant code."),
                    column("application_id", "string", false, "Application code."),
                    column("campaign_code", "string", true, "Campaign code dimension."),
                    column("source", "string", true, "Marketing source dimension."),
                    column("stage", "string", false, "Standard funnel stage."),
                    column("bucket_date", "date", false, "UTC reporting date."),
                    column("event_count", "integer", false, "Aggregated event count."),
                    column("updated_at", "timestamp", false, "Read-model update time."));
            case COURSE_COMPLETION_SNAPSHOT -> List.of(
                    column("course_id", "uuid", false, "Course id."),
                    column("enrolled_count", "integer", false, "Learners enrolled."),
                    column("completed_count", "integer", false, "Learners completed."),
                    column("completion_rate", "decimal", false, "Completion percentage."),
                    column("avg_days_to_complete", "decimal", true, "Average days to complete."),
                    column("updated_at", "timestamp", false, "Read-model update time."));
            case ORG_DASHBOARD_SNAPSHOT -> List.of(
                    column("org_id", "string", false, "Organization id."),
                    column("active_learners", "integer", false, "Active learner count."),
                    column("total_enrollments", "integer", false, "Total enrollment count."),
                    column("avg_completion_rate", "decimal", false, "Average completion percentage."),
                    column("updated_at", "timestamp", false, "Read-model update time."));
        };
    }

    private WarehouseExportColumnDto column(String name, String type, boolean nullable, String description) {
        return new WarehouseExportColumnDto(name, type, nullable, description);
    }

    private String csv(List<WarehouseExportColumnDto> columns, List<List<String>> rows) {
        List<String> lines = new ArrayList<>();
        lines.add(joinCsv(columns.stream().map(WarehouseExportColumnDto::name).toList()));
        rows.stream().map(this::joinCsv).forEach(lines::add);
        return String.join("\n", lines) + "\n";
    }

    private String joinCsv(List<String> values) {
        return values.stream().map(this::csvValue).collect(java.util.stream.Collectors.joining(","));
    }

    private String csvValue(String value) {
        String normalized = value == null ? "" : value;
        boolean quote = normalized.contains(",") || normalized.contains("\"")
                || normalized.contains("\n") || normalized.contains("\r");
        String escaped = normalized.replace("\"", "\"\"");
        return quote ? "\"" + escaped + "\"" : escaped;
    }

    private String filename(Dataset dataset, Instant generatedAt) {
        return "courseflow-analytics-"
                + dataset.name().toLowerCase(Locale.ROOT).replace('_', '-')
                + "-"
                + generatedAt.toString().replace(":", "").replace(".", "-")
                + ".csv";
    }

    private String normalizeFormat(String requested) {
        String format = requested == null || requested.isBlank()
                ? "CSV"
                : requested.trim().toUpperCase(Locale.ROOT);
        if (!"CSV".equals(format)) {
            throw BadRequestException.coded(
                    "ANALYTICS_WAREHOUSE_EXPORT_FORMAT_UNSUPPORTED",
                    "Analytics warehouse export currently supports CSV only");
        }
        return format;
    }

    private int normalizeLimit(Integer requested) {
        if (requested == null || requested <= 0) {
            return DEFAULT_LIMIT;
        }
        return Math.min(requested, MAX_LIMIT);
    }

    private String required(String value, String field) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            throw BadRequestException.coded(
                    "ANALYTICS_WAREHOUSE_EXPORT_REQUIRED_FILTER",
                    field + " is required for this analytics warehouse dataset");
        }
        return normalized;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String value(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(
                    digest.digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private enum Dataset {
        MARKETING_FUNNEL_DAILY,
        COURSE_COMPLETION_SNAPSHOT,
        ORG_DASHBOARD_SNAPSHOT;

        static Dataset from(String raw) {
            String normalized = raw == null ? "" : raw.trim().toUpperCase(Locale.ROOT).replace('-', '_');
            try {
                return Dataset.valueOf(normalized);
            } catch (IllegalArgumentException ex) {
                throw BadRequestException.coded(
                        "ANALYTICS_WAREHOUSE_EXPORT_DATASET_UNSUPPORTED",
                        "Unsupported analytics warehouse export dataset: " + raw);
            }
        }
    }
}
