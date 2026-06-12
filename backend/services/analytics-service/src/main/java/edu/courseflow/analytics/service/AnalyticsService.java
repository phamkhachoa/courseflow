package edu.courseflow.analytics.service;

import edu.courseflow.analytics.dto.AnalyticsDtos.AtRiskStudentDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.CourseMetricDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.EngagementDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.GradeDistributionDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.RecordActivityRequestDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.RecordTimeSpentRequestDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.UpdateCourseMetricRequestDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.UpdateGradeDistributionRequestDto;
import edu.courseflow.analytics.repository.AnalyticsRepository;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnalyticsService {

    private final AnalyticsRepository analytics;

    public AnalyticsService(AnalyticsRepository analytics) {
        this.analytics = analytics;
    }

    public CourseMetricDto courseMetric(UUID courseId) {
        return analytics.findCourseMetric(courseId)
                .orElseThrow(() -> new NotFoundException("Course metric not found: " + courseId));
    }

    @Transactional
    public CourseMetricDto update(UpdateCourseMetricRequestDto request) {
        return analytics.update(request);
    }

    @Transactional
    public void recordActivity(RecordActivityRequestDto req) {
        analytics.recordActivity(req.studentId(), UUID.fromString(req.courseId()), req.activityType(), req.durationMinutes());
    }

    @Transactional
    public void recordTimeSpent(RecordTimeSpentRequestDto req) {
        analytics.addTimeSpent(req.studentId(), UUID.fromString(req.courseId()), req.minutes(), Instant.now());
    }

    public List<EngagementDto> engagement(String studentId, String courseId) {
        return analytics.getEngagement(studentId, courseId);
    }

    public List<AtRiskStudentDto> atRiskStudents(UUID courseId) {
        return analytics.atRiskStudents(courseId);
    }

    public GradeDistributionDto gradeDistribution(UUID courseId) {
        return analytics.gradeDistribution(courseId);
    }

    @Transactional
    public void updateGradeDistribution(UpdateGradeDistributionRequestDto req) {
        analytics.upsertGradeDistribution(UUID.fromString(req.courseId()), req.gradeBand(), req.studentCount());
    }
}
