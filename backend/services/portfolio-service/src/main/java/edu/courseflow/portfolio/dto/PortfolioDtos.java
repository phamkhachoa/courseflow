package edu.courseflow.portfolio.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

public final class PortfolioDtos {

    private PortfolioDtos() {
    }

    public record LearningEvidenceDto(
            String id,
            String studentId,
            String courseId,
            String title,
            String evidenceType,
            String sourceType,
            String sourceId,
            String reflection,
            Instant createdAt
    ) {
    }

    public record AddLearningEvidenceRequestDto(
            @NotBlank String courseId,
            @NotBlank String title,
            @NotBlank String evidenceType,
            @NotBlank String sourceType,
            @NotBlank String sourceId,
            String reflection
    ) {
    }

    public record LearningEvidenceDetailDto(
            String id,
            String studentId,
            String courseId,
            String title,
            String evidenceType,
            String sourceType,
            String sourceId,
            String reflection,
            List<String> tags,
            String visibility,
            List<String> mediaUrls,
            List<EvaluationDto> evaluations,
            Instant createdAt,
            Instant updatedAt
    ) {
        public record EvaluationDto(
                String evaluatorId,
                String evaluatorRole,
                BigDecimal score,
                String comment,
                Instant evaluatedAt
        ) {
        }
    }

    public record UpdateEvidenceRequestDto(
            String title,
            String reflection,
            String visibility,
            List<String> tags,
            List<String> mediaUrls
    ) {
    }

    public record AddEvaluationRequestDto(
            String evaluatorId,
            String evaluatorRole,
            @NotNull BigDecimal score,
            String comment
    ) {
    }

    public record PortfolioSummaryDto(
            String studentId,
            int totalEvidence,
            Map<String, Integer> countByType,
            Map<String, Integer> countByCourse,
            BigDecimal avgEvaluationScore,
            int evaluationCount
    ) {
    }
}
