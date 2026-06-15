package edu.courseflow.analytics.controller;

import edu.courseflow.analytics.dto.ReportingDtos.CourseCompletionDto;
import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelDto;
import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelIngestResponseDto;
import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecordMarketingFunnelEventRequestDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
import edu.courseflow.analytics.dto.ReportingDtos.RelatedCourseDto;
import edu.courseflow.analytics.dto.ReportingDtos.TimeSpentDto;
import edu.courseflow.analytics.dto.ReportingDtos.WarehouseExportRequestDto;
import edu.courseflow.analytics.dto.ReportingDtos.WarehouseExportResponseDto;
import edu.courseflow.analytics.service.ReportingService;
import edu.courseflow.analytics.service.WarehouseExportService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class ReportingController {

    private final ReportingService reporting;
    private final WarehouseExportService warehouseExports;
    private final CourseAccessClient courseAccess;
    private final InternalJwtService internalJwtService;

    public ReportingController(
            ReportingService reporting,
            WarehouseExportService warehouseExports,
            CourseAccessClient courseAccess,
            InternalJwtService internalJwtService) {
        this.reporting = reporting;
        this.warehouseExports = warehouseExports;
        this.courseAccess = courseAccess;
        this.internalJwtService = internalJwtService;
    }

    // ---- reporting ----

    @GetMapping("/internal/analytics/courses/{courseId}/completion")
    public CourseCompletionDto completion(@PathVariable UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return reporting.courseCompletion(courseId);
    }

    @GetMapping("/internal/analytics/students/{studentId}/time-spent")
    public List<TimeSpentDto> timeSpent(@PathVariable String studentId, CurrentUser user) {
        requireSelfOrPlatformAdmin(user, studentId);
        return reporting.timeSpent(studentId);
    }

    @GetMapping("/internal/analytics/orgs/{orgId}/dashboard")
    public OrgDashboardDto orgDashboard(@PathVariable String orgId, CurrentUser user) {
        requireOrgDashboardAccess(user, orgId);
        return reporting.orgDashboard(orgId);
    }

    @GetMapping("/internal/analytics/marketing/funnel")
    public MarketingFunnelDto marketingFunnel(@RequestParam String tenantId,
                                              @RequestParam String applicationId,
                                              @RequestParam(required = false) String campaignCode,
                                              @RequestParam(required = false) String source,
                                              @RequestParam(required = false) LocalDate from,
                                              @RequestParam(required = false) LocalDate to,
                                              @RequestParam(defaultValue = "500") int limit,
                                              CurrentUser user) {
        requirePlatformAdmin(user);
        return reporting.marketingFunnel(tenantId, applicationId, campaignCode, source, from, to, limit);
    }

    @PostMapping("/internal/analytics/marketing/funnel/events")
    public MarketingFunnelIngestResponseDto recordMarketingFunnelEvent(
            @Valid @RequestBody RecordMarketingFunnelEventRequestDto request,
            CurrentUser user) {
        requirePlatformAdminOrServiceActor(user);
        return reporting.recordMarketingFunnelEvent(request, user);
    }

    @PostMapping("/internal/analytics/warehouse/exports")
    public WarehouseExportResponseDto warehouseExport(
            @Valid @RequestBody WarehouseExportRequestDto request,
            CurrentUser user) {
        requirePlatformAdminOrServiceScope(
                user,
                InternalScopes.ANALYTICS_EXPORT_READ,
                "Requires platform admin or analytics export service access");
        return warehouseExports.export(request);
    }

    // ---- recommendation ----

    @GetMapping("/internal/analytics/students/{studentId}/recommendations")
    public List<RecommendationDto> recommendations(@PathVariable String studentId,
                                                   @RequestParam(defaultValue = "10") int limit,
                                                   CurrentUser user) {
        requireSelfOrPlatformAdmin(user, studentId);
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

    private void requireOrgDashboardAccess(CurrentUser user, String orgId) {
        callerId(user);
        if (user.hasPlatformRole("ADMIN")) {
            return;
        }
        if (user.hasDepartmentRole("ORG_ADMIN", orgId)) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires scoped organization access");
    }

    private void requireSelfOrPlatformAdmin(CurrentUser user, String studentId) {
        if (user != null && user.hasPlatformRole("ADMIN")) {
            return;
        }
        if (!callerId(user).equals(studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed to access another student");
        }
    }

    private void requirePlatformAdmin(CurrentUser user) {
        if (user != null && user.hasPlatformRole("ADMIN")) {
            return;
        }
        callerId(user);
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires platform admin access");
    }

    private void requirePlatformAdminOrServiceActor(CurrentUser user) {
        if (user != null && user.hasPlatformRole("ADMIN")) {
            return;
        }
        if (hasVerifiedServiceScope(user, InternalScopes.ANALYTICS_FUNNEL_WRITE)) {
            return;
        }
        callerId(user);
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires platform admin or service actor access");
    }

    private void requirePlatformAdminOrServiceScope(CurrentUser user, String scope, String message) {
        if (user != null && user.hasPlatformRole("ADMIN")) {
            return;
        }
        if (hasVerifiedServiceScope(user, scope)) {
            return;
        }
        callerId(user);
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, message);
    }

    private boolean hasVerifiedServiceScope(CurrentUser user, String requiredScope) {
        if (user == null || user.id() != null || user.internalToken() == null) {
            return false;
        }
        try {
            Claims claims = internalJwtService.verify(user.internalToken());
            if (!"service".equals(claims.get("actor_type", String.class))) {
                return false;
            }
            Set<String> scopes = extractScopes(claims);
            return scopes.contains("*") || scopes.contains(requiredScope);
        } catch (JwtException | IllegalArgumentException | IllegalStateException ex) {
            return false;
        }
    }

    @SuppressWarnings("unchecked")
    private Set<String> extractScopes(Claims claims) {
        Set<String> scopes = new LinkedHashSet<>();
        Object rawScope = claims.get("scope");
        if (rawScope != null) {
            Arrays.stream(rawScope.toString().split("\\s+"))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(scopes::add);
        }
        Object rawScp = claims.get("scp");
        if (rawScp instanceof List<?> list) {
            for (Object scope : list) {
                if (scope != null && !scope.toString().isBlank()) {
                    scopes.add(scope.toString().trim());
                }
            }
        }
        return scopes;
    }
}
