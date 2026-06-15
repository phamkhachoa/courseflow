package edu.courseflow.gradebook.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

public final class GradebookDtos {

    private GradebookDtos() {
    }

    public record GradeItemDto(
            String id,
            String courseId,
            String categoryName,
            String sourceType,
            String sourceId,
            String title,
            BigDecimal maxScore,
            BigDecimal itemWeightPercent,
            BigDecimal categoryWeightPercent,
            String aggregationMethod,
            int dropLowest,
            BigDecimal latePenaltyPercent,
            boolean published) {
    }

    public record UpsertGradeItemRequestDto(
            @NotBlank String categoryId,
            @NotBlank String sourceType,
            @NotBlank String sourceId,
            @NotBlank String title,
            @NotNull @DecimalMin("0.01") BigDecimal maxScore,
            @NotNull @DecimalMin("0.00") BigDecimal weightPercent,
            @NotNull @DecimalMin("0.00") BigDecimal latePenaltyPercent,
            Boolean published) {
    }

    public record GradeEntryDto(
            String id,
            String gradeItemId,
            String title,
            String categoryName,
            BigDecimal rawScore,
            BigDecimal adjustedScore,
            BigDecimal maxScore,
            BigDecimal latePenaltyApplied,
            boolean isLate,
            int minutesLate,
            String letter,
            String status,
            Instant gradedAt) {
    }

    public record CategorySummaryDto(
            String name,
            String aggregationMethod,
            int dropLowest,
            BigDecimal weightPercent,
            BigDecimal contribution,
            int itemCount,
            int droppedCount) {
    }

    public record StudentGradebookDto(
            String courseId,
            String studentId,
            BigDecimal finalScore,
            String finalLetter,
            String gradingSchemeName,
            List<CategorySummaryDto> categories,
            List<GradeEntryDto> entries) {
    }

    public record UpsertGradeEntryRequestDto(
            @NotBlank String gradeItemId,
            @NotBlank String studentId,
            @NotNull BigDecimal rawScore,
            Boolean isLate,
            Integer minutesLate,
            String reason) {
    }

    public record GradeOverrideDto(
            String id,
            String gradeEntryId,
            BigDecimal oldScore,
            BigDecimal newScore,
            String reason,
            String actorId,
            Instant createdAt) {
    }

    // ---- Grading schemes ----

    public record GradingSchemeEntryDto(
            String id,
            @NotBlank String letter,
            @NotNull @DecimalMin("0.00") BigDecimal minPercent,
            BigDecimal gpaPoints) {
    }

    public record GradingSchemeDto(
            String id,
            String courseId,
            String name,
            boolean isDefault,
            List<GradingSchemeEntryDto> entries) {
    }

    public record CreateGradingSchemeRequestDto(
            @NotBlank String name,
            Boolean isDefault,
            @NotEmpty @Valid List<GradingSchemeEntryDto> entries) {
    }

    // ---- Final grades ----

    public record FinalGradeDto(
            String id,
            String courseId,
            String studentId,
            BigDecimal finalScore,
            String letter,
            boolean passed,
            BigDecimal passThreshold,
            String status,
            String finalizedBy,
            Instant finalizedAt) {
    }

    public record FinalizeRequestDto(String finalizedBy) {
    }

    // ---- Grade publish/finalize audit ----

    public record GradePublishAuditDto(
            String id,
            String action,
            String courseId,
            String studentId,
            String gradeItemId,
            String gradeEntryId,
            String finalGradeId,
            String actorId,
            List<String> reasonCodes,
            Map<String, Object> payload,
            Instant createdAt
    ) {
    }

    public record GradingQueueItemDto(
            String queueKey,
            String courseId,
            String studentId,
            String status,
            List<String> reasonCodes,
            String gradeItemId,
            String gradeEntryId,
            String finalGradeId,
            String title,
            String categoryName,
            String sourceType,
            String sourceId,
            BigDecimal rawScore,
            BigDecimal adjustedScore,
            BigDecimal maxScore,
            String finalGradeStatus,
            Instant gradedAt,
            Instant finalizedAt
    ) {
    }

    // ---- Categories + weights (P0-4: weights must be set so final scores aren't always 0) ----

    public record GradeCategoryDto(
            String id,
            String courseId,
            String name,
            BigDecimal weightPercent,
            int position,
            String aggregationMethod,
            int dropLowest) {
    }

    public record UpsertCategoryRequestDto(
            @NotBlank String name,
            @NotNull @DecimalMin("0.00") BigDecimal weightPercent,
            String aggregationMethod,
            Integer dropLowest) {
    }
}
