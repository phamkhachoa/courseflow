package edu.courseflow.analytics.dto;

import java.time.Instant;

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
            double score
    ) {
    }
}
