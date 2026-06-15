package edu.courseflow.analytics.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public final class ReportingDtos {

    private ReportingDtos() {
    }

    public record CourseCompletionDto(
            String courseId,
            int enrolledCount,
            int completedCount,
            double completionRate,
            Double avgDaysToComplete,
            Instant updatedAt
    ) {
    }

    public record TimeSpentDto(
            String studentId,
            String courseId,
            int minutesSpent,
            Instant lastActivityAt
    ) {
    }

    public record OrgDashboardDto(
            String orgId,
            int activeLearners,
            int totalEnrollments,
            double avgCompletionRate,
            Instant updatedAt
    ) {
    }

    public record RecommendationDto(
            String studentId,
            String courseId,
            double score,
            String reason
    ) {
    }

    public record RelatedCourseDto(
            String courseId,
            String relatedCourseId,
            double score,
            String source,
            String reason,
            String reasonCode,
            String placement,
            String modelVersion,
            Instant generatedAt
    ) {
    }

    public record MarketingFunnelStageDto(
            String stage,
            long count,
            Double stepConversionRate,
            Double overallConversionRate
    ) {
    }

    public record MarketingFunnelRowDto(
            LocalDate bucketDate,
            String campaignCode,
            String source,
            String stage,
            long count
    ) {
    }

    public record MarketingFunnelDto(
            String tenantId,
            String applicationId,
            String campaignCode,
            String source,
            LocalDate from,
            LocalDate to,
            List<MarketingFunnelStageDto> stages,
            List<MarketingFunnelRowDto> rows,
            Instant generatedAt
    ) {
    }

    public record RecordMarketingFunnelEventRequestDto(
            @NotNull UUID eventId,
            @NotBlank String tenantId,
            @NotBlank String applicationId,
            String campaignCode,
            String source,
            @NotBlank String stage,
            LocalDate bucketDate,
            Instant occurredAt,
            Long eventCount
    ) {
    }

    public record MarketingFunnelIngestResponseDto(
            UUID eventId,
            boolean accepted,
            boolean duplicate,
            String stage,
            LocalDate bucketDate,
            long eventCount
    ) {
    }

    public record WarehouseExportRequestDto(
            @NotBlank String dataset,
            String format,
            String tenantId,
            String applicationId,
            String campaignCode,
            String source,
            LocalDate from,
            LocalDate to,
            Integer limit
    ) {
    }

    public record WarehouseExportColumnDto(
            String name,
            String type,
            boolean nullable,
            String description
    ) {
    }

    public record WarehouseExportResponseDto(
            String exportId,
            String dataset,
            int schemaVersion,
            String format,
            String contentType,
            String filename,
            int rowCount,
            boolean truncated,
            LocalDate from,
            LocalDate to,
            List<WarehouseExportColumnDto> columns,
            String contentSha256,
            String content,
            Instant generatedAt
    ) {
    }
}
