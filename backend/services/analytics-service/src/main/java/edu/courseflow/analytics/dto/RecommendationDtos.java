package edu.courseflow.analytics.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class RecommendationDtos {

    private RecommendationDtos() {
    }

    public record ManualRelatedCourseDto(
            UUID id,
            UUID courseId,
            UUID relatedCourseId,
            String placement,
            int position,
            BigDecimal weight,
            String reason,
            String status,
            Instant effectiveFrom,
            Instant effectiveTo,
            String createdBy,
            String updatedBy,
            Instant createdAt,
            Instant updatedAt
    ) {
    }

    public record UpsertManualRelatedCourseRequestDto(
            @NotNull UUID relatedCourseId,
            BigDecimal weight,
            String reason,
            Integer position,
            String status,
            Instant effectiveFrom,
            Instant effectiveTo
    ) {
    }

    public record UpdateManualRelatedCourseRequestDto(
            BigDecimal weight,
            String reason,
            Integer position,
            String status,
            Instant effectiveFrom,
            Instant effectiveTo
    ) {
    }

    public record ReorderManualRelatedCoursesRequestDto(
            @NotEmpty List<UUID> relatedCourseIds
    ) {
    }

    public record RecordRecommendationEventRequestDto(
            @NotNull UUID eventId,
            @NotBlank String eventType,
            UUID courseId,
            UUID relatedCourseId,
            String studentId,
            String sessionId,
            String placement,
            String reasonCode,
            String recommendationSource,
            String modelVersion,
            String attributionId,
            Instant occurredAt,
            String metadataJson
    ) {
    }

    public record RecommendationEventIngestResponseDto(
            UUID eventId,
            boolean accepted,
            boolean duplicate,
            String eventType,
            Instant occurredAt
    ) {
    }

    public record RecommendationBatchRequestDto(
            Integer lookbackDays,
            Integer limitPerCourse,
            String modelVersion
    ) {
    }

    public record RecommendationBatchResponseDto(
            String modelVersion,
            Instant since,
            int pairStatsComputed,
            int generatedRelatedRows,
            Instant generatedAt,
            String engine,
            String fallbackReason
    ) {
    }

    public record RecommendationMlTrainingJobResponseDto(
            UUID trainingRunId,
            String modelVersion,
            String status,
            Instant since,
            int pairCount,
            int generatedRelatedRows,
            Instant generatedAt,
            String engine,
            String fallbackReason
    ) {
    }
}
