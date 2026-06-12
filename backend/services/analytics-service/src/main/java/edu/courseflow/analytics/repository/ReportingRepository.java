package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.dto.ReportingDtos.CourseCompletionDto;
import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
import edu.courseflow.analytics.dto.ReportingDtos.RelatedCourseDto;
import edu.courseflow.analytics.dto.ReportingDtos.TimeSpentDto;
import edu.courseflow.analytics.mapper.AnalyticsMapper;
import edu.courseflow.analytics.model.CourseCompletionMetric;
import edu.courseflow.analytics.model.CourseRecommendation;
import edu.courseflow.analytics.model.OrgDashboardMetric;
import edu.courseflow.analytics.model.RelatedCourse;
import edu.courseflow.analytics.model.StudentTimeSpent;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;

@Repository
public class ReportingRepository {

    private final CourseCompletionMetricRepository completions;
    private final StudentTimeSpentRepository timeSpent;
    private final OrgDashboardMetricRepository dashboards;
    private final CourseRecommendationRepository recommendations;
    private final RelatedCourseRepository relatedCourses;
    private final AnalyticsMapper mapper;

    public ReportingRepository(CourseCompletionMetricRepository completions,
            StudentTimeSpentRepository timeSpent,
            OrgDashboardMetricRepository dashboards,
            CourseRecommendationRepository recommendations,
            RelatedCourseRepository relatedCourses,
            AnalyticsMapper mapper) {
        this.completions = completions;
        this.timeSpent = timeSpent;
        this.dashboards = dashboards;
        this.recommendations = recommendations;
        this.relatedCourses = relatedCourses;
        this.mapper = mapper;
    }

    public Optional<CourseCompletionDto> courseCompletion(UUID courseId) {
        return completions.findById(courseId).map(mapper::toDto);
    }

    public List<TimeSpentDto> timeSpentByStudent(String studentId) {
        return timeSpent.findByStudentIdOrderByMinutesSpentDesc(studentId).stream()
                .map(mapper::toDto)
                .toList();
    }

    public Optional<OrgDashboardDto> orgDashboard(String orgId) {
        return dashboards.findById(orgId).map(mapper::toDto);
    }

    public List<RecommendationDto> recommendations(String studentId, int limit) {
        return recommendations.findByStudentIdOrderByScoreDesc(studentId, PageRequest.of(0, limit)).stream()
                .map(mapper::toDto)
                .toList();
    }

    public List<RelatedCourseDto> relatedCourses(UUID courseId, int limit) {
        return relatedCourses.findByCourseIdOrderByScoreDesc(courseId, PageRequest.of(0, limit)).stream()
                .map(mapper::toDto)
                .toList();
    }

    public void addTimeSpent(String studentId, UUID courseId, int minutes, Instant lastActivity) {
        StudentTimeSpent row = timeSpent.findByStudentIdAndCourseId(studentId, courseId)
                .orElseGet(() -> new StudentTimeSpent(studentId, courseId));
        row.addMinutes(minutes, lastActivity);
        timeSpent.save(row);
    }

    public void upsertCompletionEnrolled(UUID courseId) {
        CourseCompletionMetric row = completions.findById(courseId)
                .orElseGet(() -> new CourseCompletionMetric(courseId));
        row.incrementEnrolled();
        completions.save(row);
    }

}
