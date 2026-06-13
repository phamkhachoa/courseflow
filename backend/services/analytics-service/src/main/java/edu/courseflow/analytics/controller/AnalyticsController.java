package edu.courseflow.analytics.controller;

import edu.courseflow.analytics.dto.AnalyticsDtos.AtRiskStudentDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.CourseMetricDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.EngagementDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.GradeDistributionDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.RecordActivityRequestDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.RecordTimeSpentRequestDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.UpdateCourseMetricRequestDto;
import edu.courseflow.analytics.dto.AnalyticsDtos.UpdateGradeDistributionRequestDto;
import edu.courseflow.analytics.service.AnalyticsService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AnalyticsController {

    private final AnalyticsService analytics;
    private final CourseAccessClient courseAccess;

    public AnalyticsController(AnalyticsService analytics, CourseAccessClient courseAccess) {
        this.analytics = analytics;
        this.courseAccess = courseAccess;
    }

    @GetMapping("/internal/analytics/courses/{courseId}/metrics")
    public CourseMetricDto courseMetric(@PathVariable UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return analytics.courseMetric(courseId);
    }

    @PostMapping("/internal/analytics/courses/metrics")
    public CourseMetricDto update(@Valid @RequestBody UpdateCourseMetricRequestDto request, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(request.courseId()));
        return analytics.update(request);
    }

    @PostMapping("/internal/analytics/activity")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void recordActivity(@Valid @RequestBody RecordActivityRequestDto req, CurrentUser user) {
        courseAccess.requireCourseAccess(user, UUID.fromString(req.courseId()));
        RecordActivityRequestDto trusted = new RecordActivityRequestDto(
                callerId(user),
                req.courseId(),
                req.activityType(),
                req.durationMinutes());
        analytics.recordActivity(trusted);
    }

    @PostMapping("/internal/analytics/time-spent")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void recordTimeSpent(@Valid @RequestBody RecordTimeSpentRequestDto req, CurrentUser user) {
        courseAccess.requireCourseAccess(user, UUID.fromString(req.courseId()));
        RecordTimeSpentRequestDto trusted = new RecordTimeSpentRequestDto(
                callerId(user),
                req.courseId(),
                req.minutes());
        analytics.recordTimeSpent(trusted);
    }

    @GetMapping("/internal/analytics/students/{studentId}/engagement")
    public List<EngagementDto> engagement(@PathVariable String studentId,
                                          @RequestParam(required = false) String courseId,
                                          CurrentUser user) {
        requireSelfOrScopedCourseStaff(user, studentId, courseId);
        return analytics.engagement(studentId, courseId);
    }

    @GetMapping("/internal/analytics/courses/{courseId}/at-risk")
    public List<AtRiskStudentDto> atRisk(@PathVariable UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return analytics.atRiskStudents(courseId);
    }

    @GetMapping("/internal/analytics/courses/{courseId}/grade-distribution")
    public GradeDistributionDto gradeDistribution(@PathVariable UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return analytics.gradeDistribution(courseId);
    }

    @PostMapping("/internal/analytics/grade-distribution")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void updateGradeDistribution(@Valid @RequestBody UpdateGradeDistributionRequestDto req, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(req.courseId()));
        analytics.updateGradeDistribution(req);
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Authentication required");
        }
        return String.valueOf(user.id());
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("ADMIN", "ORG_ADMIN", "TA", "INSTRUCTOR", "PROFESSOR");
    }

    private void requireSelfOrScopedCourseStaff(CurrentUser user, String studentId, String courseId) {
        if (isStaff(user)) {
            if (courseId != null && !courseId.isBlank()) {
                courseAccess.requireCourseStaffAccess(user, UUID.fromString(courseId));
                return;
            }
            if (user.hasPlatformRole("ADMIN")) {
                return;
            }
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "A course scope is required for staff access");
        }
        if (!callerId(user).equals(studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed to access another student");
        }
        if (courseId != null && !courseId.isBlank()) {
            courseAccess.requireCourseAccess(user, UUID.fromString(courseId));
        }
    }
}
