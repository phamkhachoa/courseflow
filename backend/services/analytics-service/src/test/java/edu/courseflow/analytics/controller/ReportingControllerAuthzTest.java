package edu.courseflow.analytics.controller;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelDto;
import edu.courseflow.analytics.dto.ReportingDtos.MarketingFunnelIngestResponseDto;
import edu.courseflow.analytics.dto.ReportingDtos.OrgDashboardDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecordMarketingFunnelEventRequestDto;
import edu.courseflow.analytics.dto.ReportingDtos.RecommendationDto;
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
import io.jsonwebtoken.Jwts;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class ReportingControllerAuthzTest {

    private static final String ORG_ID = "20000000-0000-0000-0000-000000000001";
    private static final String OTHER_ORG_ID = "20000000-0000-0000-0000-000000000999";

    @Mock
    private ReportingService reporting;
    @Mock
    private WarehouseExportService warehouseExports;
    @Mock
    private CourseAccessClient courseAccess;
    @Mock
    private InternalJwtService internalJwtService;

    private ReportingController controller;

    @BeforeEach
    void setUp() {
        controller = new ReportingController(reporting, warehouseExports, courseAccess, internalJwtService);
    }

    @Test
    void platformAdminCanViewOrgDashboard() {
        CurrentUser admin = userWithScope(1L, "admin@courseflow.local", "ADMIN", "PLATFORM", null);
        OrgDashboardDto dashboard = new OrgDashboardDto(ORG_ID, 5, 8, 62.5, Instant.now());
        when(reporting.orgDashboard(ORG_ID)).thenReturn(dashboard);

        controller.orgDashboard(ORG_ID, admin);

        verify(reporting).orgDashboard(ORG_ID);
    }

    @Test
    void orgAdminCanOnlyViewOwnDepartmentDashboard() {
        CurrentUser orgAdmin = userWithScope(
                2L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                ORG_ID);
        OrgDashboardDto dashboard = new OrgDashboardDto(ORG_ID, 5, 8, 62.5, Instant.now());
        when(reporting.orgDashboard(ORG_ID)).thenReturn(dashboard);

        controller.orgDashboard(ORG_ID, orgAdmin);

        verify(reporting).orgDashboard(ORG_ID);
    }

    @Test
    void orgAdminCannotViewAnotherDepartmentDashboard() {
        CurrentUser orgAdmin = userWithScope(
                2L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                OTHER_ORG_ID);

        assertThrows(ResponseStatusException.class, () -> controller.orgDashboard(ORG_ID, orgAdmin));
        verifyNoInteractions(reporting);
    }

    @Test
    void courseScopedInstructorCannotViewWholeOrgDashboard() {
        CurrentUser instructor = userWithScope(
                3L,
                "instructor@courseflow.local",
                "INSTRUCTOR",
                "COURSE",
                "30000000-0000-0000-0000-000000000001");

        assertThrows(ResponseStatusException.class, () -> controller.orgDashboard(ORG_ID, instructor));
        verifyNoInteractions(reporting);
    }

    @Test
    void learnerCanViewOwnTimeSpent() {
        CurrentUser learner = userWithScope(4L, "learner@courseflow.local", "STUDENT", "PLATFORM", null);
        when(reporting.timeSpent("4")).thenReturn(List.of(
                new TimeSpentDto("4", "30000000-0000-0000-0000-000000000001", 45, Instant.now())));

        controller.timeSpent("4", learner);

        verify(reporting).timeSpent("4");
    }

    @Test
    void platformAdminCanViewStudentRecommendations() {
        CurrentUser admin = userWithScope(1L, "admin@courseflow.local", "ADMIN", "PLATFORM", null);
        when(reporting.recommendations("4", 10)).thenReturn(List.of(
                new RecommendationDto("4", "30000000-0000-0000-0000-000000000001", 0.95, "similar-course")));

        controller.recommendations("4", 10, admin);

        verify(reporting).recommendations("4", 10);
    }

    @Test
    void platformAdminCanViewMarketingFunnel() {
        CurrentUser admin = userWithScope(1L, "admin@courseflow.local", "ADMIN", "PLATFORM", null);
        when(reporting.marketingFunnel("courseflow", "lms", null, null, null, null, 500))
                .thenReturn(new MarketingFunnelDto(
                        "courseflow",
                        "lms",
                        null,
                        null,
                        null,
                        null,
                        List.of(),
                        List.of(),
                        Instant.now()));

        controller.marketingFunnel("courseflow", "lms", null, null, null, null, 500, admin);

        verify(reporting).marketingFunnel("courseflow", "lms", null, null, null, null, 500);
    }

    @Test
    void nonPlatformAdminCannotViewMarketingFunnel() {
        CurrentUser orgAdmin = userWithScope(
                2L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                ORG_ID);

        assertThrows(ResponseStatusException.class,
                () -> controller.marketingFunnel("courseflow", "lms", null, null, null, null, 500, orgAdmin));
        verifyNoInteractions(reporting);
    }

    @Test
    void serviceActorCanRecordMarketingFunnelEvent() {
        String token = "service.token.signature";
        CurrentUser service = new CurrentUser(null, null, null, Set.of(), Set.of(), token);
        UUID eventId = UUID.randomUUID();
        RecordMarketingFunnelEventRequestDto request = new RecordMarketingFunnelEventRequestDto(
                eventId,
                "courseflow",
                "lms",
                "SUMMER",
                "email",
                "IMPRESSION",
                LocalDate.of(2026, 6, 15),
                null,
                1L);
        when(internalJwtService.verify(token)).thenReturn(serviceClaims(InternalScopes.ANALYTICS_FUNNEL_WRITE));
        when(reporting.recordMarketingFunnelEvent(request, service)).thenReturn(
                new MarketingFunnelIngestResponseDto(
                        eventId,
                        true,
                        false,
                        "IMPRESSION",
                        LocalDate.of(2026, 6, 15),
                        1L));

        controller.recordMarketingFunnelEvent(request, service);

        verify(reporting).recordMarketingFunnelEvent(request, service);
    }

    @Test
    void serviceActorWithoutFunnelWriteScopeCannotRecordMarketingFunnelEvent() {
        String token = "service.token.signature";
        CurrentUser service = new CurrentUser(null, null, null, Set.of(), Set.of(), token);
        RecordMarketingFunnelEventRequestDto request = new RecordMarketingFunnelEventRequestDto(
                UUID.randomUUID(),
                "courseflow",
                "lms",
                null,
                null,
                "IMPRESSION",
                null,
                null,
                null);
        when(internalJwtService.verify(token)).thenReturn(serviceClaims(InternalScopes.SERVICE));

        assertThrows(ResponseStatusException.class, () -> controller.recordMarketingFunnelEvent(request, service));
        verifyNoInteractions(reporting);
    }

    @Test
    void platformAdminCanExportWarehouseDataset() {
        CurrentUser admin = userWithScope(1L, "admin@courseflow.local", "ADMIN", "PLATFORM", null);
        WarehouseExportRequestDto request = new WarehouseExportRequestDto(
                "COURSE_COMPLETION_SNAPSHOT",
                "CSV",
                null,
                null,
                null,
                null,
                null,
                null,
                100);
        when(warehouseExports.export(request)).thenReturn(exportResponse("COURSE_COMPLETION_SNAPSHOT"));

        controller.warehouseExport(request, admin);

        verify(warehouseExports).export(request);
    }

    @Test
    void serviceActorCanExportWarehouseDatasetWithExportReadScope() {
        String token = "service.token.signature";
        CurrentUser service = new CurrentUser(null, null, null, Set.of(), Set.of(), token);
        WarehouseExportRequestDto request = new WarehouseExportRequestDto(
                "MARKETING_FUNNEL_DAILY",
                "CSV",
                "courseflow",
                "lms",
                null,
                null,
                LocalDate.of(2026, 6, 1),
                LocalDate.of(2026, 6, 15),
                100);
        when(internalJwtService.verify(token)).thenReturn(serviceClaims(InternalScopes.ANALYTICS_EXPORT_READ));
        when(warehouseExports.export(request)).thenReturn(exportResponse("MARKETING_FUNNEL_DAILY"));

        controller.warehouseExport(request, service);

        verify(warehouseExports).export(request);
    }

    @Test
    void serviceActorWithoutExportReadScopeCannotExportWarehouseDataset() {
        String token = "service.token.signature";
        CurrentUser service = new CurrentUser(null, null, null, Set.of(), Set.of(), token);
        WarehouseExportRequestDto request = new WarehouseExportRequestDto(
                "COURSE_COMPLETION_SNAPSHOT",
                "CSV",
                null,
                null,
                null,
                null,
                null,
                null,
                100);
        when(internalJwtService.verify(token)).thenReturn(serviceClaims(InternalScopes.SERVICE));

        assertThrows(ResponseStatusException.class, () -> controller.warehouseExport(request, service));
        verifyNoInteractions(warehouseExports);
    }

    @Test
    void learnerCannotRecordMarketingFunnelEvent() {
        CurrentUser learner = userWithScope(4L, "learner@courseflow.local", "STUDENT", "PLATFORM", null);
        RecordMarketingFunnelEventRequestDto request = new RecordMarketingFunnelEventRequestDto(
                UUID.randomUUID(),
                "courseflow",
                "lms",
                null,
                null,
                "IMPRESSION",
                null,
                null,
                null);

        assertThrows(ResponseStatusException.class, () -> controller.recordMarketingFunnelEvent(request, learner));
        verifyNoInteractions(reporting);
    }

    @Test
    void courseScopedInstructorCannotViewStudentWideAnalyticsWithoutCourseScope() {
        CurrentUser instructor = userWithScope(
                3L,
                "instructor@courseflow.local",
                "INSTRUCTOR",
                "COURSE",
                "30000000-0000-0000-0000-000000000001");

        assertThrows(ResponseStatusException.class, () -> controller.timeSpent("4", instructor));
        assertThrows(ResponseStatusException.class, () -> controller.recommendations("4", 10, instructor));
        verifyNoInteractions(reporting);
    }

    private static CurrentUser userWithScope(
            Long id,
            String email,
            String role,
            String scopeType,
            String scopeId) {
        return new CurrentUser(
                id,
                email,
                role,
                Set.of(role),
                Set.of(new CurrentUser.RoleAssignment(role, scopeType, scopeId)));
    }

    private static Claims serviceClaims(String... scopes) {
        return Jwts.claims()
                .add("actor_type", "service")
                .add("scope", String.join(" ", scopes))
                .add("scp", List.of(scopes))
                .build();
    }

    private static WarehouseExportResponseDto exportResponse(String dataset) {
        return new WarehouseExportResponseDto(
                "sha256:test",
                dataset,
                1,
                "CSV",
                "text/csv",
                "export.csv",
                0,
                false,
                null,
                null,
                List.of(),
                "sha256:content",
                "",
                Instant.now());
    }
}
