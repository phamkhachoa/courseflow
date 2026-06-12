package edu.courseflow.gradebook.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

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
            BigDecimal latePenaltyPercent) {
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
            Integer minutesLate) {
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
            String status,
            String finalizedBy,
            Instant finalizedAt) {
    }

    public record FinalizeRequestDto(String finalizedBy) {
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
