package edu.courseflow.analytics.controller;

import edu.courseflow.analytics.dto.ReportingDtos.CourseCompletionDto;
import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
import edu.courseflow.analytics.dto.ReportingDtos.RelatedCourseDto;
import edu.courseflow.analytics.dto.ReportingDtos.TimeSpentDto;
import edu.courseflow.analytics.service.ReportingService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class ReportingController {

    private final ReportingService reporting;

    public ReportingController(ReportingService reporting) {
        this.reporting = reporting;
    }

    // ---- reporting ----

    @GetMapping("/internal/analytics/courses/{courseId}/completion")
    public CourseCompletionDto completion(@PathVariable UUID courseId, CurrentUser user) {
        requireStaff(user);
        return reporting.courseCompletion(courseId);
    }

    @GetMapping("/internal/analytics/students/{studentId}/time-spent")
    public List<TimeSpentDto> timeSpent(@PathVariable String studentId, CurrentUser user) {
        requireSelfOrStaff(user, studentId);
        return reporting.timeSpent(studentId);
    }

    @GetMapping("/internal/analytics/orgs/{orgId}/dashboard")
    public OrgDashboardDto orgDashboard(@PathVariable String orgId, CurrentUser user) {
        requireStaff(user);
        return reporting.orgDashboard(orgId);
    }

    // ---- recommendation ----

    @GetMapping("/internal/analytics/students/{studentId}/recommendations")
    public List<RecommendationDto> recommendations(@PathVariable String studentId,
                                                   @RequestParam(defaultValue = "10") int limit,
                                                   CurrentUser user) {
        requireSelfOrStaff(user, studentId);
        return reporting.recommendations(studentId, limit);
    }

    @GetMapping("/public/courses/{courseId}/related")
    public List<RelatedCourseDto> related(@PathVariable UUID courseId,
                                          @RequestParam(defaultValue = "6") int limit) {
        return reporting.relatedCourses(courseId, limit);
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Authentication required");
        }
        return String.valueOf(user.id());
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("ADMIN", "INSTRUCTOR");
    }

    private void requireStaff(CurrentUser user) {
        callerId(user);
        if (!isStaff(user)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires ADMIN or INSTRUCTOR role");
        }
    }

    private void requireSelfOrStaff(CurrentUser user, String studentId) {
        if (isStaff(user)) {
            return;
        }
        if (!callerId(user).equals(studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed to access another student");
        }
    }
}
