package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.dto.AnalyticsDtos.AtRiskStudentDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.CourseMetricDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.EngagementDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.GradeDistributionDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.UpdateCourseMetricRequestDto;
import edu.courseflow.analytics.mapper.AnalyticsMapper;
import edu.courseflow.analytics.model.CourseMetric;
import edu.courseflow.analytics.model.GradeDistribution;
import edu.courseflow.analytics.model.GradeDistributionId;
import edu.courseflow.analytics.model.StudentActivityLog;
import edu.courseflow.analytics.model.StudentEngagement;
import edu.courseflow.analytics.model.StudentTimeSpent;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class AnalyticsRepository {

    private final CourseMetricRepository courseMetrics;
    private final StudentTimeSpentRepository timeSpent;
    private final StudentActivityLogRepository activityLogs;
    private final StudentEngagementRepository engagement;
    private final GradeDistributionRepository gradeDistributions;
    private final AnalyticsMapper mapper;

    public AnalyticsRepository(CourseMetricRepository courseMetrics,
            StudentTimeSpentRepository timeSpent,
            StudentActivityLogRepository activityLogs,
            StudentEngagementRepository engagement,
            GradeDistributionRepository gradeDistributions,
            AnalyticsMapper mapper) {
        this.courseMetrics = courseMetrics;
        this.timeSpent = timeSpent;
        this.activityLogs = activityLogs;
        this.engagement = engagement;
        this.gradeDistributions = gradeDistributions;
        this.mapper = mapper;
    }

    public Optional<CourseMetricDto> findCourseMetric(UUID courseId) {
        return courseMetrics.findById(courseId).map(mapper::toDto);
    }

    public CourseMetricDto update(UpdateCourseMetricRequestDto request) {
        UUID courseId = UUID.fromString(request.courseId());
        CourseMetric metric = courseMetrics.findById(courseId).orElseGet(() -> new CourseMetric(courseId));
        metric.applyDelta(request.enrolledDelta(), request.submittedDelta(),
                request.discussionDelta(), request.latestScore());
        return mapper.toDto(courseMetrics.save(metric));
    }

    public void addTimeSpent(String studentId, UUID courseId, int minutes, Instant lastActivity) {
        StudentTimeSpent row = timeSpent.findByStudentIdAndCourseId(studentId, courseId)
                .orElseGet(() -> new StudentTimeSpent(studentId, courseId));
        row.addMinutes(minutes, lastActivity);
        timeSpent.save(row);
    }

    public void recordActivity(String studentId, UUID courseId, String activityType, int durationMinutes) {
        activityLogs.save(new StudentActivityLog(studentId, courseId, activityType, durationMinutes));
        recomputeEngagement(studentId, courseId);
        if (durationMinutes > 0) {
            addTimeSpent(studentId, courseId, durationMinutes, Instant.now());
        }
    }

    private void recomputeEngagement(String studentId, UUID courseId) {
        List<StudentActivityLog> logs = activityLogs.findByStudentIdAndCourseId(studentId, courseId);
        Instant cutoff = Instant.now().minus(7, ChronoUnit.DAYS);
        int logins = count(logs, "LOGIN", null);
        int time7d = logs.stream()
                .filter(log -> log.getOccurredAt().isAfter(cutoff))
                .mapToInt(StudentActivityLog::getDurationMinutes)
                .sum();
        int submissions7d = count(logs, "SUBMISSION", cutoff);
        int posts7d = count(logs, "DISCUSSION_POST", cutoff);
        Instant lastActivity = logs.stream()
                .map(StudentActivityLog::getOccurredAt)
                .max(Instant::compareTo)
                .orElse(null);

        double score = Math.min(100.0,
                logins * 10.0 + time7d * 0.3 + submissions7d * 15.0 + posts7d * 10.0);

        boolean stale = lastActivity == null || lastActivity.isBefore(cutoff);
        String risk = score < 30 && stale ? "HIGH" : score < 50 ? "MEDIUM" : "LOW";

        StudentEngagement row = engagement.findByStudentIdAndCourseId(studentId, courseId)
                .orElseGet(() -> new StudentEngagement(studentId, courseId));
        row.update(score, logins, time7d, submissions7d, posts7d, lastActivity, risk);
        engagement.save(row);
    }

    public List<EngagementDto> getEngagement(String studentId, String courseId) {
        List<StudentEngagement> rows = courseId == null
                ? engagement.findByStudentIdOrderByUpdatedAtDesc(studentId)
                : engagement.findByStudentIdAndCourseIdOrderByUpdatedAtDesc(studentId, UUID.fromString(courseId));
        return rows.stream().map(mapper::toDto).toList();
    }

    public List<AtRiskStudentDto> atRiskStudents(UUID courseId) {
        Instant now = Instant.now();
        return engagement.findByCourseIdAndRiskLevelInOrderByEngagementScoreAsc(courseId, List.of("MEDIUM", "HIGH"))
                .stream()
                .map(row -> mapper.toAtRiskDto(row, now))
                .toList();
    }

    public void upsertGradeDistribution(UUID courseId, String gradeBand, int studentCount) {
        GradeDistribution row = gradeDistributions.findById(new GradeDistributionId(courseId, gradeBand))
                .orElseGet(() -> new GradeDistribution(courseId, gradeBand));
        row.setStudentCount(studentCount);
        gradeDistributions.save(row);
    }

    public GradeDistributionDto gradeDistribution(UUID courseId) {
        List<GradeDistributionDto.GradeBandDto> bands = gradeDistributions
                .findByCourseIdOrderByGradeBandAsc(courseId)
                .stream()
                .map(mapper::toDto)
                .toList();
        return new GradeDistributionDto(courseId.toString(), bands);
    }

    private int count(List<StudentActivityLog> logs, String activityType, Instant cutoff) {
        return (int) logs.stream()
                .filter(log -> activityType.equals(log.getActivityType()))
                .filter(log -> cutoff == null || log.getOccurredAt().isAfter(cutoff))
                .count();
    }

}
