package edu.courseflow.analytics.mapper;

import edu.courseflow.analytics.dto.AnalyticsDtos.AtRiskStudentDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.CourseMetricDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.EngagementDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.GradeDistributionDto;
import edu.courseflow.analytics.dto.ReportingDtos.CourseCompletionDto;
import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
import edu.courseflow.analytics.dto.ReportingDtos.RelatedCourseDto;
import edu.courseflow.analytics.dto.ReportingDtos.TimeSpentDto;
import edu.courseflow.analytics.model.CourseCompletionMetric;
import edu.courseflow.analytics.model.CourseMetric;
import edu.courseflow.analytics.model.CourseRecommendation;
import edu.courseflow.analytics.model.GradeDistribution;
import edu.courseflow.analytics.model.OrgDashboardMetric;
import edu.courseflow.analytics.model.RelatedCourse;
import edu.courseflow.analytics.model.StudentEngagement;
import edu.courseflow.analytics.model.StudentTimeSpent;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface AnalyticsMapper {

    CourseMetricDto toDto(CourseMetric metric);

    EngagementDto toDto(StudentEngagement row);

    @Mapping(target = "daysSinceActivity", expression = "java(daysSince(now, row.getLastActivityAt()))")
    @Mapping(target = "riskReasons", expression = "java(riskReasons(row, now))")
    AtRiskStudentDto toAtRiskDto(StudentEngagement row, Instant now);

    GradeDistributionDto.GradeBandDto toDto(GradeDistribution row);

    CourseCompletionDto toDto(CourseCompletionMetric row);

    TimeSpentDto toDto(StudentTimeSpent row);

    OrgDashboardDto toDto(OrgDashboardMetric row);

    RecommendationDto toDto(CourseRecommendation row);

    RelatedCourseDto toDto(RelatedCourse row);

    default int daysSince(Instant now, Instant lastActivity) {
        Instant baseline = lastActivity == null ? now.minus(999, ChronoUnit.DAYS) : lastActivity;
        return (int) ChronoUnit.DAYS.between(baseline, now);
    }

    default List<String> riskReasons(StudentEngagement row, Instant now) {
        List<String> reasons = new ArrayList<>();
        if ("HIGH".equalsIgnoreCase(row.getRiskLevel()) || "MEDIUM".equalsIgnoreCase(row.getRiskLevel())) {
            reasons.add("ENGAGEMENT_SCORE_LOW");
        }
        if (daysSince(now, row.getLastActivityAt()) >= 7) {
            reasons.add("NO_ACTIVITY_7D");
        }
        if (row.getSubmissions7d() == 0) {
            reasons.add("NO_SUBMISSIONS_7D");
        }
        if (row.getTimeSpent7d() < 30) {
            reasons.add("LOW_TIME_SPENT_7D");
        }
        if (row.getPosts7d() == 0) {
            reasons.add("NO_DISCUSSION_POSTS_7D");
        }
        return reasons;
    }
}
