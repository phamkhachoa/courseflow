package edu.courseflow.analytics.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public final class AnalyticsDtos {

    private AnalyticsDtos() {
    }

    public record CourseMetricDto(
            String courseId,
            int enrolledCount,
            int submittedCount,
            BigDecimal averageScore,
            int discussionCount,
            Instant updatedAt
    ) {
    }

    public record UpdateCourseMetricRequestDto(
            @NotBlank String courseId,
            @NotNull Integer enrolledDelta,
            @NotNull Integer submittedDelta,
            @NotNull Integer discussionDelta,
            BigDecimal latestScore
    ) {
    }

    public record RecordActivityRequestDto(
        String studentId,
        @NotBlank String courseId,
        @NotBlank String activityType,
        int durationMinutes
    ) {}

    public record RecordTimeSpentRequestDto(
        String studentId,
        @NotBlank String courseId,
        int minutes
    ) {}

    public record EngagementDto(
        String studentId, String courseId,
        double engagementScore,
        int loginCount7d, int timeSpent7d, int submissions7d, int posts7d,
        Instant lastActivityAt, String riskLevel, Instant updatedAt
    ) {}

    public record AtRiskStudentDto(
        String studentId, String courseId,
        double engagementScore, String riskLevel, Instant lastActivityAt, int daysSinceActivity,
        List<String> riskReasons
    ) {}

    public record GradeDistributionDto(
        String courseId, List<GradeBandDto> bands
    ) {
        public record GradeBandDto(String gradeBand, int studentCount) {}
    }

    public record UpdateGradeDistributionRequestDto(
        @NotBlank String courseId,
        @NotBlank String gradeBand,
        int studentCount
    ) {}
}
