package edu.courseflow.analytics.service;

import edu.courseflow.analytics.dto.ReportingDtos.CourseCompletionDto;
import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
import edu.courseflow.analytics.dto.ReportingDtos.RelatedCourseDto;
import edu.courseflow.analytics.dto.ReportingDtos.TimeSpentDto;
import edu.courseflow.analytics.repository.ReportingRepository;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class ReportingService {

    private final ReportingRepository reporting;

    public ReportingService(ReportingRepository reporting) {
        this.reporting = reporting;
    }

    public CourseCompletionDto courseCompletion(UUID courseId) {
        return reporting.courseCompletion(courseId)
                .orElse(new CourseCompletionDto(courseId.toString(), 0, 0, 0.0, null, Instant.now()));
    }

    public List<TimeSpentDto> timeSpent(String studentId) {
        return reporting.timeSpentByStudent(studentId);
    }

    public OrgDashboardDto orgDashboard(String orgId) {
        return reporting.orgDashboard(orgId)
                .orElse(new OrgDashboardDto(orgId, 0, 0, 0.0, Instant.now()));
    }

    public List<RecommendationDto> recommendations(String studentId, int limit) {
        return reporting.recommendations(studentId, limit <= 0 ? 10 : limit);
    }

    public List<RelatedCourseDto> relatedCourses(UUID courseId, int limit) {
        return reporting.relatedCourses(courseId, limit <= 0 ? 6 : limit);
    }
}
