package edu.courseflow.promotion.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.exception.ApiExceptionHandler;
import edu.courseflow.commonlibrary.exception.CodedResponseStatusException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.commonlibrary.web.CurrentUserArgumentResolver;
import edu.courseflow.commonlibrary.web.TrustedGatewayHeaderFilter;
import edu.courseflow.promotion.dto.PromotionDtos.AdminPreviewIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.AdminPreviewIncentivesResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ApplicationDto;
import edu.courseflow.promotion.dto.PromotionDtos.AuditQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunListItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRowDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportIssueExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportOperationQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponStorageInventoryDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponStorageInventoryItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateApplicationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveCatalogDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationEffectDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationEntryDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveReconciliationQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalQueryResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionEvidencePackDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionEvidencePackExportDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunResultDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionPolicyDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionPolicyRegistryDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.service.CampaignVersionService;
import edu.courseflow.promotion.service.CouponImportApprovalService;
import edu.courseflow.promotion.service.CouponImportCommitService;
import edu.courseflow.promotion.service.CouponImportDryRunService;
import edu.courseflow.promotion.service.CouponImportQueryService;
import edu.courseflow.promotion.service.IncentiveAccessService;
import edu.courseflow.promotion.service.IncentiveAuditQueryService;
import edu.courseflow.promotion.service.IncentiveCatalogService;
import edu.courseflow.promotion.service.IncentiveReconciliationService;
import edu.courseflow.promotion.service.PromotionService;
import edu.courseflow.promotion.service.PromotionErrorCodes;
import edu.courseflow.promotion.service.RetentionApprovalService;
import edu.courseflow.promotion.service.RetentionDryRunService;
import edu.courseflow.promotion.service.RetentionExecutionService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class PromotionControllerSecurityTest {

    private static final String INTERNAL_SECRET = "test-internal-jwt-secret-32-byte-value-001";

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final PromotionService promotions = org.mockito.Mockito.mock(PromotionService.class);
    private final IncentiveAccessService access = org.mockito.Mockito.mock(IncentiveAccessService.class);
    private final CampaignVersionService campaignVersions = org.mockito.Mockito.mock(CampaignVersionService.class);
    private final IncentiveAuditQueryService auditQueries = org.mockito.Mockito.mock(IncentiveAuditQueryService.class);
    private final IncentiveReconciliationService reconciliation =
            org.mockito.Mockito.mock(IncentiveReconciliationService.class);
    private final IncentiveCatalogService catalog = org.mockito.Mockito.mock(IncentiveCatalogService.class);
    private final RetentionDryRunService retention = org.mockito.Mockito.mock(RetentionDryRunService.class);
    private final RetentionExecutionService retentionExecutions = org.mockito.Mockito.mock(RetentionExecutionService.class);
    private final RetentionApprovalService retentionApprovals = org.mockito.Mockito.mock(RetentionApprovalService.class);
    private final CouponImportDryRunService couponImports = org.mockito.Mockito.mock(CouponImportDryRunService.class);
    private final CouponImportApprovalService couponImportApprovals =
            org.mockito.Mockito.mock(CouponImportApprovalService.class);
    private final CouponImportCommitService couponImportCommits =
            org.mockito.Mockito.mock(CouponImportCommitService.class);
    private final CouponImportQueryService couponImportQueries =
            org.mockito.Mockito.mock(CouponImportQueryService.class);
    private final InternalJwtService internalJwtService = new InternalJwtService(new InternalJwtProperties(
            INTERNAL_SECRET,
            "courseflow-token-converter",
            "courseflow-services",
            180,
            30,
            "api-gateway"));
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders
                .standaloneSetup(new PromotionController(
                        promotions, access, campaignVersions, auditQueries,
                        reconciliation, catalog, retention, retentionExecutions, retentionApprovals, couponImports,
                        couponImportApprovals, couponImportCommits, couponImportQueries))
                .setControllerAdvice(new ApiExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .addFilters(new TrustedGatewayHeaderFilter(internalJwtService))
                .build();
    }

    @Test
    void catalogIsExposedForAuthenticatedOperators() throws Exception {
        when(catalog.catalog()).thenReturn(new IncentiveCatalogDto(
                "incentive-contract-v1",
                "generic-commerce-facts-v1",
                List.of(),
                List.of(),
                List.of(),
                List.of(),
                null,
                List.of("portable")));

        mvc.perform(get("/internal/incentives/catalog").headers(userHeaders()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.catalogVersion").value("incentive-contract-v1"));

        verify(catalog).catalog();
    }

    @Test
    void internalRuntimeEndpointRequiresInternalJwt() throws Exception {
        mvc.perform(post("/internal/incentives/evaluate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request())))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(promotions);
    }

    @Test
    void adminPreviewForwardsCorrelationIdAndCurrentUser() throws Exception {
        when(promotions.preview(any(), any(), eq("corr-preview")))
                .thenReturn(new AdminPreviewIncentivesResponseDto(
                        true,
                        false,
                        "context-hash",
                        new EvaluateIncentivesResponseDto(
                                false, null, null, null, null, List.of(), List.of("NO_ELIGIBLE_INCENTIVE"))));

        mvc.perform(post("/internal/incentives/admin/preview")
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-preview")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(
                                new AdminPreviewIncentivesRequestDto(request(), "support preview"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.preview").value(true))
                .andExpect(jsonPath("$.ledgerImpact").value(false))
                .andExpect(jsonPath("$.contextHash").value("context-hash"));

        verify(promotions).preview(any(), any(CurrentUser.class), eq("corr-preview"));
    }

    @Test
    void applicationMutationForwardsCorrelationIdAndCurrentUser() throws Exception {
        when(access.createApplication(any(), any(), eq("corr-app")))
                .thenReturn(new ApplicationDto(
                        UUID.randomUUID(),
                        "courseflow",
                        "lms",
                        "CourseFlow LMS",
                        "ACTIVE",
                        List.of(),
                        Instant.now(),
                        Instant.now()));

        mvc.perform(post("/internal/incentives/applications")
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-app")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(new CreateApplicationRequestDto(
                                "courseflow",
                                "lms",
                                "CourseFlow LMS",
                                "ACTIVE",
                                List.of("api-gateway")))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.tenantId").value("courseflow"));

        verify(access).createApplication(any(), any(CurrentUser.class), eq("corr-app"));
    }

    @Test
    void runtimeMutationForwardsCorrelationIdAndCurrentUser() throws Exception {
        UUID reservationId = UUID.randomUUID();
        when(promotions.reserve(any(), any(), eq("corr-reserve")))
                .thenReturn(new ReserveIncentiveResponseDto(
                        true,
                        reservationId,
                        UUID.randomUUID(),
                        1,
                        null,
                        Instant.now().plusSeconds(900),
                        List.of(),
                        List.of("RESERVED"),
                        false));

        mvc.perform(post("/internal/incentives/reservations")
                        .headers(serviceHeaders(InternalScopes.PROMOTION_RESERVE))
                        .header(GatewayHeaders.CORRELATION_ID, "corr-reserve")
                        .header("Idempotency-Key", "reserve-header-1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(new ReserveIncentiveRequestDto(
                                "reserve-body-1",
                                request()))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.reserved").value(true));

        ArgumentCaptor<ReserveIncentiveRequestDto> requestCaptor =
                ArgumentCaptor.forClass(ReserveIncentiveRequestDto.class);
        verify(promotions).reserve(requestCaptor.capture(), any(CurrentUser.class), eq("corr-reserve"));
        assertThat(requestCaptor.getValue().idempotencyKey()).isEqualTo("reserve-header-1");
    }

    @Test
    void auditExplorerForwardsCorrelationAndSourceClientFilters() throws Exception {
        when(auditQueries.query(
                any(), any(), any(), any(), any(), any(), any(), any(), any(), any(), any(), any()))
                .thenReturn(new AuditQueryResponseDto(List.of(), 50, false));

        mvc.perform(get("/internal/incentives/audit")
                        .headers(userHeaders())
                        .queryParam("tenantId", "courseflow")
                        .queryParam("applicationId", "lms")
                        .queryParam("correlationId", "corr-1")
                        .queryParam("sourceClientId", "checkout-service"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.limit").value(50));

        verify(auditQueries).query(
                eq(Optional.of("courseflow")),
                eq(Optional.of("lms")),
                eq(Optional.empty()),
                eq(Optional.empty()),
                eq(Optional.empty()),
                eq(Optional.empty()),
                eq(Optional.of("corr-1")),
                eq(Optional.of("checkout-service")),
                eq(Optional.empty()),
                eq(Optional.empty()),
                eq(Optional.empty()),
                any(CurrentUser.class));
    }

    @Test
    void reconciliationEntriesForwardScopedFiltersAndReturnSafeEffectRows() throws Exception {
        UUID ledgerEntryId = UUID.randomUUID();
        UUID redemptionId = UUID.randomUUID();
        UUID reservationId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        UUID couponId = UUID.randomUUID();
        Instant now = Instant.parse("2026-06-14T10:00:00Z");
        when(reconciliation.query(
                any(), any(), any(), any(), any(), any(), any(), any(), any(), any(), any(), any(), any()))
                .thenReturn(new IncentiveReconciliationQueryResponseDto(
                        List.of(new IncentiveReconciliationEntryDto(
                                ledgerEntryId,
                                redemptionId + ":COMMIT:effect-1",
                                "MATCHED",
                                List.of(),
                                "APPLY",
                                "COMMIT",
                                redemptionId,
                                reservationId,
                                "courseflow",
                                "lms",
                                campaignId,
                                1,
                                couponId,
                                "profile-1",
                                "order-1",
                                "REDEEMED",
                                "NO_QUOTA_CHANGE",
                                null,
                                "PUBLISHED",
                                "incentive.redemption.committed",
                                now,
                                "corr-reconcile",
                                "checkout-service",
                                now,
                                now,
                                null,
                                new IncentiveReconciliationEffectDto(
                                        "effect-1",
                                        "ORDER_FIXED_OFF",
                                        "DISCOUNT",
                                        "ORDER_FIXED_OFF",
                                        "ORDER",
                                        null,
                                        BigDecimal.TEN,
                                        "USD",
                                        "MONEY",
                                        BigDecimal.TEN,
                                        1,
                                        Map.of("campaignId", campaignId.toString())))),
                        25,
                        false,
                        now));

        mvc.perform(get("/internal/incentives/reconciliation/entries")
                        .headers(userHeaders())
                        .queryParam("tenantId", "courseflow")
                        .queryParam("applicationId", "lms")
                        .queryParam("profileId", "profile-1")
                        .queryParam("externalReference", "order-1")
                        .queryParam("campaignId", campaignId.toString())
                        .queryParam("couponId", couponId.toString())
                        .queryParam("redemptionId", redemptionId.toString())
                        .queryParam("reservationId", reservationId.toString())
                        .queryParam("entryType", "COMMIT")
                        .queryParam("from", "2026-06-14T00:00:00Z")
                        .queryParam("to", "2026-06-15T00:00:00Z")
                        .queryParam("limit", "25"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].reconciliationStatus").value("MATCHED"))
                .andExpect(jsonPath("$.items[0].direction").value("APPLY"))
                .andExpect(jsonPath("$.items[0].quotaPolicy").value("NO_QUOTA_CHANGE"))
                .andExpect(jsonPath("$.items[0].outboxStatus").value("PUBLISHED"))
                .andExpect(jsonPath("$.items[0].effect.effectId").value("effect-1"))
                .andExpect(jsonPath("$.items[0].effect.amount").value(10))
                .andExpect(jsonPath("$.items[0].effect.currency").value("USD"))
                .andExpect(jsonPath("$.limit").value(25))
                .andExpect(jsonPath("$.hasMore").value(false))
                .andExpect(jsonPath("$.items[0].code").doesNotExist())
                .andExpect(jsonPath("$.items[0].normalizedCode").doesNotExist())
                .andExpect(jsonPath("$.items[0].fingerprint").doesNotExist());

        verify(reconciliation).query(
                eq(Optional.of("courseflow")),
                eq(Optional.of("lms")),
                eq(Optional.of("profile-1")),
                eq(Optional.of("order-1")),
                eq(Optional.of(campaignId)),
                eq(Optional.of(couponId)),
                eq(Optional.of(redemptionId)),
                eq(Optional.of(reservationId)),
                eq(Optional.of("COMMIT")),
                eq(Optional.of(Instant.parse("2026-06-14T00:00:00Z"))),
                eq(Optional.of(Instant.parse("2026-06-15T00:00:00Z"))),
                eq(Optional.of(25)),
                any(CurrentUser.class));
    }

    @Test
    void couponStorageInventoryForwardsScopedFiltersAndReturnsAggregateOnly() throws Exception {
        UUID campaignId = UUID.randomUUID();
        when(promotions.couponStorageInventory(any(), any(), any(), any(), any()))
                .thenReturn(new CouponStorageInventoryDto(
                        "courseflow",
                        "lms",
                        campaignId,
                        false,
                        true,
                        false,
                        13,
                        3,
                        1,
                        Instant.parse("2026-06-14T10:00:00Z"),
                        List.of(
                                new CouponStorageInventoryItemDto("current_hmac", 10),
                                new CouponStorageInventoryItemDto("previous_hmac", 0),
                                new CouponStorageInventoryItemDto("legacy_sha", 2),
                                new CouponStorageInventoryItemDto("legacy_raw", 1),
                                new CouponStorageInventoryItemDto("malformed", 1))));

        mvc.perform(get("/internal/incentives/coupons/storage-inventory")
                        .headers(userHeaders())
                        .queryParam("tenantId", "courseflow")
                        .queryParam("applicationId", "lms")
                        .queryParam("campaignId", campaignId.toString())
                        .queryParam("activeOnly", "false"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.tenantId").value("courseflow"))
                .andExpect(jsonPath("$.applicationId").value("lms"))
                .andExpect(jsonPath("$.campaignId").value(campaignId.toString()))
                .andExpect(jsonPath("$.activeOnly").value(false))
                .andExpect(jsonPath("$.legacyFallbackEnabled").value(true))
                .andExpect(jsonPath("$.fallbackDisableReady").value(false))
                .andExpect(jsonPath("$.totalCoupons").value(13))
                .andExpect(jsonPath("$.legacyCoupons").value(3))
                .andExpect(jsonPath("$.malformedCoupons").value(1))
                .andExpect(jsonPath("$.items[0].storageFormat").value("current_hmac"))
                .andExpect(jsonPath("$.items[0].count").value(10))
                .andExpect(jsonPath("$.code").doesNotExist())
                .andExpect(jsonPath("$.normalizedCode").doesNotExist())
                .andExpect(jsonPath("$.fingerprint").doesNotExist())
                .andExpect(jsonPath("$.couponId").doesNotExist())
                .andExpect(jsonPath("$.holderProfileId").doesNotExist());

        verify(promotions).couponStorageInventory(
                eq(Optional.of("courseflow")),
                eq(Optional.of("lms")),
                eq(Optional.of(campaignId)),
                eq(Optional.of(false)),
                any(CurrentUser.class));
    }

    @Test
    void couponImportDryRunForwardsMultipartCsvAndCorrelationId() throws Exception {
        UUID campaignId = UUID.randomUUID();
        when(couponImports.dryRun(any(), any(), eq("corr-import")))
                .thenReturn(new CouponImportDryRunResponseDto(
                        UUID.randomUUID(),
                        campaignId,
                        true,
                        1,
                        1,
                        0,
                        0,
                        0,
                        true,
                        true,
                        "sha256:result",
                        Instant.parse("2026-06-14T10:00:00Z"),
                        List.of(),
                        List.of(),
                        List.of(new CouponImportDryRunRowDto(2, "SA****10", "VALID", List.of()))));
        MockMultipartFile csv = new MockMultipartFile(
                "file",
                "coupons.csv",
                "text/csv",
                "code\nSAVE10\n".getBytes());

        mvc.perform(multipart("/internal/incentives/coupons:import-dry-run")
                        .file(csv)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-import")
                        .header("Idempotency-Key", "import-1")
                        .param("campaignId", campaignId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dryRun").value(true))
                .andExpect(jsonPath("$.sampleRows[0].codeMask").value("SA****10"))
                .andExpect(jsonPath("$.sampleRows[0].status").value("VALID"))
                .andExpect(jsonPath("$.code").doesNotExist())
                .andExpect(jsonPath("$.normalizedCode").doesNotExist())
                .andExpect(jsonPath("$.fingerprint").doesNotExist());

        ArgumentCaptor<CouponImportDryRunRequestDto> requestCaptor =
                ArgumentCaptor.forClass(CouponImportDryRunRequestDto.class);
        verify(couponImports).dryRun(requestCaptor.capture(), any(CurrentUser.class), eq("corr-import"));
        assertThat(requestCaptor.getValue().idempotencyKey()).isEqualTo("import-1");
    }

    @Test
    void couponImportDryRunReturnsCodedRateLimitErrorBody() throws Exception {
        UUID campaignId = UUID.randomUUID();
        when(couponImports.dryRun(any(), any(), eq("corr-import")))
                .thenThrow(new CodedResponseStatusException(
                        HttpStatus.TOO_MANY_REQUESTS,
                        PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED,
                        "Promotion admin operation rate limit exceeded"));
        MockMultipartFile csv = new MockMultipartFile(
                "file",
                "coupons.csv",
                "text/csv",
                "code\nSAVE10\n".getBytes());

        mvc.perform(multipart("/internal/incentives/coupons:import-dry-run")
                        .file(csv)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-import")
                        .header("Idempotency-Key", "import-1")
                        .param("campaignId", campaignId.toString()))
                .andExpect(status().isTooManyRequests())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.statusCode").value("429 TOO_MANY_REQUESTS"))
                .andExpect(jsonPath("$.title").value("Too Many Requests"))
                .andExpect(jsonPath("$.detail").value("Promotion admin operation rate limit exceeded"))
                .andExpect(jsonPath("$.errorCode").value(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED))
                .andExpect(jsonPath("$.fieldErrors").isEmpty());
    }

    @Test
    void couponImportApprovalRequestForwardsMultipartCsvAndCorrelationId() throws Exception {
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        when(couponImportApprovals.requestApproval(eq(dryRunId), any(), any(), eq("corr-approval")))
                .thenReturn(new CouponImportApprovalResponseDto(
                        approvalId,
                        "PENDING_APPROVAL",
                        dryRunId,
                        campaignId,
                        "hmac-sha256:test:result",
                        1,
                        1,
                        0,
                        0,
                        0,
                        true,
                        true,
                        "approved import",
                        "CHG-100",
                        "1",
                        null,
                        null,
                        null,
                        Instant.parse("2026-07-14T10:00:00Z"),
                        Instant.parse("2026-06-14T10:00:00Z"),
                        null,
                        null,
                        null));
        MockMultipartFile csv = new MockMultipartFile(
                "file",
                "coupons.csv",
                "text/csv",
                "code\nSAVE10\n".getBytes());

        mvc.perform(multipart("/internal/incentives/coupons/import-dry-runs/{dryRunId}/approvals", dryRunId)
                        .file(csv)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-approval")
                        .param("campaignId", campaignId.toString())
                        .param("approvedResultHash", "hmac-sha256:test:result")
                        .param("reason", "approved import")
                        .param("changeTicket", "CHG-100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.approvalId").value(approvalId.toString()))
                .andExpect(jsonPath("$.status").value("PENDING_APPROVAL"));

        ArgumentCaptor<CouponImportCommitRequestDto> requestCaptor =
                ArgumentCaptor.forClass(CouponImportCommitRequestDto.class);
        verify(couponImportApprovals)
                .requestApproval(eq(dryRunId), requestCaptor.capture(), any(CurrentUser.class), eq("corr-approval"));
        assertThat(requestCaptor.getValue().dryRunId()).isEqualTo(dryRunId);
        assertThat(requestCaptor.getValue().campaignId()).isEqualTo(campaignId);
        assertThat(requestCaptor.getValue().csvContent()).contains("SAVE10");
    }

    @Test
    void couponImportApprovalDecisionForwardsCorrelationId() throws Exception {
        UUID approvalId = UUID.randomUUID();
        when(couponImportApprovals.approve(eq(approvalId), any(), any(), eq("corr-approval")))
                .thenReturn(new CouponImportApprovalResponseDto(
                        approvalId,
                        "APPROVED",
                        UUID.randomUUID(),
                        UUID.randomUUID(),
                        "hmac-sha256:test:result",
                        1,
                        1,
                        0,
                        0,
                        0,
                        true,
                        true,
                        "approved import",
                        "CHG-100",
                        "1",
                        "2",
                        null,
                        null,
                        Instant.parse("2026-07-14T10:00:00Z"),
                        Instant.parse("2026-06-14T10:00:00Z"),
                        Instant.parse("2026-06-14T10:05:00Z"),
                        null,
                        null));

        mvc.perform(post("/internal/incentives/coupons/import-approvals/{approvalId}:approve", approvalId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-approval")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(
                                new CouponImportApprovalDecisionRequestDto("looks good"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("APPROVED"));

        verify(couponImportApprovals)
                .approve(eq(approvalId), any(CouponImportApprovalDecisionRequestDto.class),
                        any(CurrentUser.class), eq("corr-approval"));
    }

    @Test
    void couponImportApprovalRequestReturnsCodedConflictErrorBody() throws Exception {
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        when(couponImportApprovals.requestApproval(eq(dryRunId), any(), any(), eq("corr-approval")))
                .thenThrow(ConflictException.coded(
                        PromotionErrorCodes.COUPON_IMPORT_RESULT_HASH_MISMATCH,
                        "Coupon import approval result hash no longer matches"));
        MockMultipartFile csv = new MockMultipartFile(
                "file",
                "coupons.csv",
                "text/csv",
                "code\nSAVE10\n".getBytes());

        mvc.perform(multipart("/internal/incentives/coupons/import-dry-runs/{dryRunId}/approvals", dryRunId)
                        .file(csv)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-approval")
                        .param("campaignId", campaignId.toString())
                        .param("approvedResultHash", "hmac-sha256:test:result")
                        .param("reason", "approved import")
                        .param("changeTicket", "CHG-100"))
                .andExpect(status().isConflict())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.statusCode").value("409 CONFLICT"))
                .andExpect(jsonPath("$.title").value("Conflict"))
                .andExpect(jsonPath("$.detail").value("Coupon import approval result hash no longer matches"))
                .andExpect(jsonPath("$.errorCode").value(PromotionErrorCodes.COUPON_IMPORT_RESULT_HASH_MISMATCH))
                .andExpect(jsonPath("$.fieldErrors").isEmpty());
    }

    @Test
    void couponImportApprovalDecisionReturnsCodedForbiddenErrorBody() throws Exception {
        UUID approvalId = UUID.randomUUID();
        when(couponImportApprovals.approve(eq(approvalId), any(), any(), eq("corr-approval")))
                .thenThrow(ForbiddenException.coded(
                        PromotionErrorCodes.COUPON_IMPORT_REVIEW_FORBIDDEN,
                        "Not allowed to review coupon import approval: courseflow/lms"));

        mvc.perform(post("/internal/incentives/coupons/import-approvals/{approvalId}:approve", approvalId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-approval")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(
                                new CouponImportApprovalDecisionRequestDto("looks good"))))
                .andExpect(status().isForbidden())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.statusCode").value("403 FORBIDDEN"))
                .andExpect(jsonPath("$.title").value("Forbidden"))
                .andExpect(jsonPath("$.detail").value("Not allowed to review coupon import approval: courseflow/lms"))
                .andExpect(jsonPath("$.errorCode").value(PromotionErrorCodes.COUPON_IMPORT_REVIEW_FORBIDDEN))
                .andExpect(jsonPath("$.fieldErrors").isEmpty());
    }

    @Test
    void couponImportApprovalDecisionReturnsCodedNotPendingErrorBody() throws Exception {
        UUID approvalId = UUID.randomUUID();
        when(couponImportApprovals.approve(eq(approvalId), any(), any(), eq("corr-approval")))
                .thenThrow(ConflictException.coded(
                        PromotionErrorCodes.COUPON_IMPORT_APPROVAL_NOT_PENDING,
                        "Coupon import approval is not pending"));

        mvc.perform(post("/internal/incentives/coupons/import-approvals/{approvalId}:approve", approvalId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-approval")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(
                                new CouponImportApprovalDecisionRequestDto("looks good"))))
                .andExpect(status().isConflict())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.statusCode").value("409 CONFLICT"))
                .andExpect(jsonPath("$.title").value("Conflict"))
                .andExpect(jsonPath("$.detail").value("Coupon import approval is not pending"))
                .andExpect(jsonPath("$.errorCode").value(PromotionErrorCodes.COUPON_IMPORT_APPROVAL_NOT_PENDING))
                .andExpect(jsonPath("$.fieldErrors").isEmpty());
    }

    @Test
    void couponImportDryRunHistoryForwardsScopedFiltersAndSafeRows() throws Exception {
        UUID dryRunId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        when(couponImportQueries.dryRuns(any(), any(), any(), any(), any(), any(), any(), any()))
                .thenReturn(new CouponImportDryRunQueryResponseDto(
                        List.of(new CouponImportDryRunListItemDto(
                                dryRunId,
                                "courseflow",
                                "lms",
                                campaignId,
                                "COMPLETED",
                                2,
                                2,
                                0,
                                0,
                                0,
                                true,
                                true,
                                "hmac-sha256:test:result",
                                "1",
                                "corr-import",
                                "admin-web",
                                Instant.parse("2026-06-14T10:00:00Z"),
                                Instant.parse("2026-07-14T10:00:00Z"),
                                null,
                                null,
                                null,
                                0,
                                null)),
                        25,
                        false,
                        Instant.parse("2026-06-14T10:01:00Z")));

        mvc.perform(get("/internal/incentives/coupons/import-dry-runs")
                        .headers(userHeaders())
                        .param("tenantId", "courseflow")
                        .param("applicationId", "lms")
                        .param("campaignId", campaignId.toString())
                        .param("status", "COMPLETED")
                        .param("limit", "25"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].dryRunId").value(dryRunId.toString()))
                .andExpect(jsonPath("$.items[0].resultHash").value("hmac-sha256:test:result"))
                .andExpect(jsonPath("$.items[0].contentHash").doesNotExist())
                .andExpect(jsonPath("$.items[0].requestHash").doesNotExist())
                .andExpect(jsonPath("$.items[0].code").doesNotExist())
                .andExpect(jsonPath("$.items[0].fingerprint").doesNotExist());

        verify(couponImportQueries).dryRuns(
                eq(Optional.of("courseflow")),
                eq(Optional.of("lms")),
                eq(Optional.of(campaignId)),
                eq(Optional.of("COMPLETED")),
                eq(Optional.empty()),
                eq(Optional.empty()),
                eq(Optional.of(25)),
                any(CurrentUser.class));
    }

    @Test
    void couponImportIssueExportReturnsMaskedCsvAndForwardsCorrelationId() throws Exception {
        UUID dryRunId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        when(couponImportQueries.dryRunIssueExport(eq(dryRunId), any(), any(), eq("corr-export")))
                .thenReturn(new CouponImportIssueExportDto(
                        dryRunId,
                        campaignId,
                        "courseflow",
                        "lms",
                        "INVALID",
                        1,
                        "coupon-import-" + dryRunId + "-invalid.csv",
                        "text/csv",
                        "rowNumber,codeMask,rowStatus,issueCodes\r\n2,SA****10,INVALID,DUPLICATE_IN_FILE\r\n",
                        Instant.parse("2026-06-14T10:02:00Z")));

        mvc.perform(get("/internal/incentives/coupons/import-dry-runs/{dryRunId}/issue-export", dryRunId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-export")
                        .param("rowStatus", "INVALID"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dryRunId").value(dryRunId.toString()))
                .andExpect(jsonPath("$.rowStatus").value("INVALID"))
                .andExpect(jsonPath("$.rowCount").value(1))
                .andExpect(jsonPath("$.content").value(org.hamcrest.Matchers.containsString("SA****10")))
                .andExpect(jsonPath("$.content").value(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("SAVE10"))))
                .andExpect(jsonPath("$.content").value(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("hmac-sha256"))))
                .andExpect(jsonPath("$.fingerprint").doesNotExist())
                .andExpect(jsonPath("$.normalizedCode").doesNotExist());

        verify(couponImportQueries).dryRunIssueExport(
                eq(dryRunId),
                eq(Optional.of("INVALID")),
                any(CurrentUser.class),
                eq("corr-export"));
    }

    @Test
    void couponImportIssueExportReturnsCodedReadForbiddenErrorBody() throws Exception {
        UUID dryRunId = UUID.randomUUID();
        when(couponImportQueries.dryRunIssueExport(eq(dryRunId), any(), any(), eq("corr-export")))
                .thenThrow(ForbiddenException.coded(
                        PromotionErrorCodes.COUPON_IMPORT_READ_FORBIDDEN,
                        "Not allowed to view coupon import operations: courseflow/lms"));

        mvc.perform(get("/internal/incentives/coupons/import-dry-runs/{dryRunId}/issue-export", dryRunId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-export")
                        .param("rowStatus", "INVALID"))
                .andExpect(status().isForbidden())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.statusCode").value("403 FORBIDDEN"))
                .andExpect(jsonPath("$.title").value("Forbidden"))
                .andExpect(jsonPath("$.detail").value("Not allowed to view coupon import operations: courseflow/lms"))
                .andExpect(jsonPath("$.errorCode").value(PromotionErrorCodes.COUPON_IMPORT_READ_FORBIDDEN))
                .andExpect(jsonPath("$.fieldErrors").isEmpty());
    }

    @Test
    void couponImportOperationHistoryAndDetailReturnSafeOperationRows() throws Exception {
        UUID importId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        CouponImportOperationDto operation = new CouponImportOperationDto(
                importId,
                approvalId,
                dryRunId,
                "courseflow",
                "lms",
                campaignId,
                "SUCCEEDED",
                2,
                2,
                "hmac-sha256:test:result",
                "approved import",
                "CHG-100",
                "3",
                "corr-commit",
                "admin-web",
                Instant.parse("2026-06-14T10:10:00Z"));
        when(couponImportQueries.operations(any(), any(), any(), any(), any(), any(), any(), any(), any(), any()))
                .thenReturn(new CouponImportOperationQueryResponseDto(
                        List.of(operation),
                        25,
                        false,
                        Instant.parse("2026-06-14T10:11:00Z")));
        when(couponImportQueries.operation(eq(importId), any(CurrentUser.class))).thenReturn(operation);

        mvc.perform(get("/internal/incentives/coupons/import-operations")
                        .headers(userHeaders())
                        .param("tenantId", "courseflow")
                        .param("applicationId", "lms")
                        .param("campaignId", campaignId.toString())
                        .param("approvalId", approvalId.toString())
                        .param("dryRunId", dryRunId.toString())
                        .param("status", "SUCCEEDED")
                        .param("limit", "25"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].importId").value(importId.toString()))
                .andExpect(jsonPath("$.items[0].idempotencyKeyHash").doesNotExist())
                .andExpect(jsonPath("$.items[0].requestHash").doesNotExist())
                .andExpect(jsonPath("$.items[0].responseJson").doesNotExist())
                .andExpect(jsonPath("$.items[0].fingerprint").doesNotExist());

        mvc.perform(get("/internal/incentives/coupons/import-operations/{importId}", importId)
                        .headers(userHeaders()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.importId").value(importId.toString()))
                .andExpect(jsonPath("$.resultHash").value("hmac-sha256:test:result"))
                .andExpect(jsonPath("$.idempotencyKeyHash").doesNotExist())
                .andExpect(jsonPath("$.requestHash").doesNotExist())
                .andExpect(jsonPath("$.responseJson").doesNotExist());
    }

    @Test
    void couponImportOperationExportReturnsSafeCsvAndForwardsCorrelationId() throws Exception {
        UUID importId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        when(couponImportQueries.operationExport(eq(importId), any(CurrentUser.class), eq("corr-export")))
                .thenReturn(new CouponImportOperationExportDto(
                        importId,
                        approvalId,
                        dryRunId,
                        campaignId,
                        "courseflow",
                        "lms",
                        "coupon-import-operation-" + importId + ".csv",
                        "text/csv",
                        "importId,approvalId,dryRunId,resultHash\r\n" + importId + "," + approvalId + "," + dryRunId + ",hmac-sha256:test:result\r\n",
                        Instant.parse("2026-06-14T10:12:00Z")));

        mvc.perform(get("/internal/incentives/coupons/import-operations/{importId}/export", importId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-export"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.importId").value(importId.toString()))
                .andExpect(jsonPath("$.filename").value("coupon-import-operation-" + importId + ".csv"))
                .andExpect(jsonPath("$.contentType").value("text/csv"))
                .andExpect(jsonPath("$.content").value(org.hamcrest.Matchers.containsString(importId.toString())))
                .andExpect(jsonPath("$.content").value(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("SAVE10"))))
                .andExpect(jsonPath("$.content").value(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("idempotency"))))
                .andExpect(jsonPath("$.idempotencyKeyHash").doesNotExist())
                .andExpect(jsonPath("$.requestHash").doesNotExist())
                .andExpect(jsonPath("$.responseJson").doesNotExist());

        verify(couponImportQueries).operationExport(eq(importId), any(CurrentUser.class), eq("corr-export"));
    }

    @Test
    void couponImportCommitForwardsMultipartCsvHashAndIdempotency() throws Exception {
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        when(couponImportCommits.commit(any(), any(), eq("corr-import")))
                .thenReturn(new CouponImportCommitResponseDto(
                        UUID.randomUUID(),
                        approvalId,
                        dryRunId,
                        campaignId,
                        "SUCCEEDED",
                        1,
                        1,
                        "hmac-sha256:test:result",
                        false,
                        Instant.parse("2026-06-14T10:00:00Z"),
                        List.of()));
        MockMultipartFile csv = new MockMultipartFile(
                "file",
                "coupons.csv",
                "text/csv",
                "code\nSAVE10\n".getBytes());

        mvc.perform(multipart("/internal/incentives/coupons/import-dry-runs/{dryRunId}:commit", dryRunId)
                        .file(csv)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-import")
                        .header("Idempotency-Key", "commit-1")
                        .param("approvalId", approvalId.toString())
                        .param("campaignId", campaignId.toString())
                        .param("approvedResultHash", "hmac-sha256:test:result")
                        .param("reason", "approved import")
                        .param("changeTicket", "CHG-100")
                        .param("confirm", "true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("SUCCEEDED"))
                .andExpect(jsonPath("$.importedRows").value(1))
                .andExpect(jsonPath("$.idempotencyReplay").value(false))
                .andExpect(jsonPath("$.code").doesNotExist())
                .andExpect(jsonPath("$.normalizedCode").doesNotExist())
                .andExpect(jsonPath("$.fingerprint").doesNotExist());

        ArgumentCaptor<CouponImportCommitRequestDto> requestCaptor =
                ArgumentCaptor.forClass(CouponImportCommitRequestDto.class);
        verify(couponImportCommits).commit(requestCaptor.capture(), any(CurrentUser.class), eq("corr-import"));
        assertThat(requestCaptor.getValue().approvalId()).isEqualTo(approvalId);
        assertThat(requestCaptor.getValue().dryRunId()).isEqualTo(dryRunId);
        assertThat(requestCaptor.getValue().idempotencyKey()).isEqualTo("commit-1");
        assertThat(requestCaptor.getValue().confirm()).isTrue();
        assertThat(requestCaptor.getValue().csvContent()).contains("SAVE10");
    }

    @Test
    void couponImportCommitReturnsCodedRateLimitErrorBody() throws Exception {
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        when(couponImportCommits.commit(any(), any(), eq("corr-import")))
                .thenThrow(new CodedResponseStatusException(
                        HttpStatus.TOO_MANY_REQUESTS,
                        PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED,
                        "Promotion admin operation rate limit exceeded"));
        MockMultipartFile csv = new MockMultipartFile(
                "file",
                "coupons.csv",
                "text/csv",
                "code\nSAVE10\n".getBytes());

        mvc.perform(multipart("/internal/incentives/coupons/import-dry-runs/{dryRunId}:commit", dryRunId)
                        .file(csv)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-import")
                        .header("Idempotency-Key", "commit-1")
                        .param("approvalId", approvalId.toString())
                        .param("campaignId", campaignId.toString())
                        .param("approvedResultHash", "hmac-sha256:test:result")
                        .param("reason", "approved import")
                        .param("changeTicket", "CHG-100")
                        .param("confirm", "true"))
                .andExpect(status().isTooManyRequests())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.statusCode").value("429 TOO_MANY_REQUESTS"))
                .andExpect(jsonPath("$.title").value("Too Many Requests"))
                .andExpect(jsonPath("$.detail").value("Promotion admin operation rate limit exceeded"))
                .andExpect(jsonPath("$.errorCode").value(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED))
                .andExpect(jsonPath("$.fieldErrors").isEmpty());
    }

    @Test
    void couponImportApprovalCommitForwardsMultipartCsvHashAndIdempotency() throws Exception {
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        when(couponImportCommits.commit(any(), any(), eq("corr-approval-import")))
                .thenReturn(new CouponImportCommitResponseDto(
                        UUID.randomUUID(),
                        approvalId,
                        dryRunId,
                        campaignId,
                        "SUCCEEDED",
                        2,
                        2,
                        "hmac-sha256:test:approval-result",
                        false,
                        Instant.parse("2026-06-14T10:10:00Z"),
                        List.of()));
        MockMultipartFile csv = new MockMultipartFile(
                "file",
                "coupons.csv",
                "text/csv",
                "code\nSAVE10\nSAVE20\n".getBytes());

        mvc.perform(multipart("/internal/incentives/coupons/import-approvals/{approvalId}:commit", approvalId)
                        .file(csv)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-approval-import")
                        .header("Idempotency-Key", "commit-approval-1")
                        .param("dryRunId", dryRunId.toString())
                        .param("campaignId", campaignId.toString())
                        .param("approvedResultHash", "hmac-sha256:test:approval-result")
                        .param("reason", "approved import")
                        .param("changeTicket", "CHG-200")
                        .param("confirm", "true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("SUCCEEDED"))
                .andExpect(jsonPath("$.importedRows").value(2))
                .andExpect(jsonPath("$.idempotencyReplay").value(false))
                .andExpect(jsonPath("$.code").doesNotExist())
                .andExpect(jsonPath("$.normalizedCode").doesNotExist())
                .andExpect(jsonPath("$.fingerprint").doesNotExist());

        ArgumentCaptor<CouponImportCommitRequestDto> requestCaptor =
                ArgumentCaptor.forClass(CouponImportCommitRequestDto.class);
        verify(couponImportCommits).commit(requestCaptor.capture(), any(CurrentUser.class), eq("corr-approval-import"));
        assertThat(requestCaptor.getValue().approvalId()).isEqualTo(approvalId);
        assertThat(requestCaptor.getValue().dryRunId()).isEqualTo(dryRunId);
        assertThat(requestCaptor.getValue().campaignId()).isEqualTo(campaignId);
        assertThat(requestCaptor.getValue().approvedResultHash()).isEqualTo("hmac-sha256:test:approval-result");
        assertThat(requestCaptor.getValue().idempotencyKey()).isEqualTo("commit-approval-1");
        assertThat(requestCaptor.getValue().confirm()).isTrue();
        assertThat(requestCaptor.getValue().csvContent()).contains("SAVE20");
    }

    @Test
    void retentionPolicyRegistryForwardsCurrentUser() throws Exception {
        when(retention.policies(any()))
                .thenReturn(new RetentionPolicyRegistryDto(List.of(new RetentionPolicyDto(
                        "expired-idempotency-keys",
                        "v1",
                        "incentive_idempotency_keys",
                        "PURGE_CANDIDATE",
                        1,
                        0,
                        1000,
                        false,
                        List.of("GLOBAL", "APPLICATION"),
                        "expires_at <= cutoff",
                        List.of("unexpired rows")))));

        mvc.perform(get("/internal/incentives/retention/policies")
                        .headers(userHeaders()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.policies[0].policyId").value("expired-idempotency-keys"))
                .andExpect(jsonPath("$.policies[0].destructiveExecutionSupported").value(false));

        verify(retention).policies(any(CurrentUser.class));
    }

    @Test
    void retentionDryRunForwardsCorrelationAndReturnsAggregateOnly() throws Exception {
        UUID dryRunId = UUID.randomUUID();
        when(retention.dryRun(any(), any(), eq("corr-retention")))
                .thenReturn(new RetentionDryRunResponseDto(
                        dryRunId,
                        "sha256:abc",
                        true,
                        true,
                        "courseflow",
                        "lms",
                        Instant.parse("2026-06-14T10:00:00Z"),
                        List.of(new RetentionDryRunResultDto(
                                "expired-idempotency-keys",
                                "v1",
                                "incentive_idempotency_keys",
                                "PURGE_CANDIDATE",
                                Instant.parse("2026-06-13T10:00:00Z"),
                                1,
                                3,
                                2,
                                null,
                                Instant.parse("2026-06-01T10:00:00Z"),
                                Instant.parse("2026-06-10T10:00:00Z"),
                                1000,
                                false,
                                "sha256:policy")),
                        List.of()));

        mvc.perform(post("/internal/incentives/retention/dry-runs")
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-retention")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "tenantId": "courseflow",
                                  "applicationId": "lms",
                                  "policyIds": ["expired-idempotency-keys"],
                                  "asOf": "2026-06-14T10:00:00Z",
                                  "reason": "monthly review"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dryRunId").value(dryRunId.toString()))
                .andExpect(jsonPath("$.dryRun").value(true))
                .andExpect(jsonPath("$.nonDestructive").value(true))
                .andExpect(jsonPath("$.results[0].eligibleCount").value(3))
                .andExpect(jsonPath("$.results[0].blockedCount").value(2))
                .andExpect(jsonPath("$.requestJson").doesNotExist())
                .andExpect(jsonPath("$.responseJson").doesNotExist())
                .andExpect(jsonPath("$.payload").doesNotExist())
                .andExpect(jsonPath("$.profileId").doesNotExist())
                .andExpect(jsonPath("$.externalReference").doesNotExist());

        verify(retention).dryRun(any(), any(CurrentUser.class), eq("corr-retention"));
    }

    @Test
    void retentionApprovalQueueForwardsFiltersAndReturnsEvidenceOnly() throws Exception {
        UUID approvalId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        Instant from = Instant.parse("2026-06-14T00:00:00Z");
        Instant to = Instant.parse("2026-06-15T00:00:00Z");
        when(retentionApprovals.queue(
                eq("APPLICATION"),
                eq("courseflow"),
                eq("lms"),
                eq(approvalId),
                eq(dryRunId),
                eq("PENDING_APPROVAL"),
                eq("terminal-reservation-request-snapshots"),
                eq("CHG-42"),
                eq("requester@example.com"),
                eq("reviewer@example.com"),
                eq("ops@example.com"),
                eq(false),
                eq(from),
                eq(to),
                eq(25),
                any(CurrentUser.class)))
                .thenReturn(new RetentionApprovalQueryResponseDto(
                        List.of(new RetentionApprovalResponseDto(
                                approvalId,
                                "PENDING_APPROVAL",
                                "terminal-reservation-request-snapshots",
                                "v1",
                                "incentive_reservation_request_snapshots",
                                "courseflow",
                                "lms",
                                Instant.parse("2026-06-14T10:00:00Z"),
                                Instant.parse("2026-05-15T10:00:00Z"),
                                30,
                                dryRunId,
                                "sha256:abc",
                                8,
                                500,
                                "restore-drill-cf_promotion-20260614",
                                "CHG-42",
                                "privacy redaction",
                                "review note",
                                "requester@example.com",
                                "reviewer@example.com",
                                null,
                                null,
                                "corr-approval",
                                "api-gateway",
                                Instant.parse("2026-06-14T11:00:00Z"),
                                Instant.parse("2026-06-14T10:05:00Z"),
                                null,
                                null,
                                null,
                                null)),
                        25,
                        false,
                        Instant.parse("2026-06-14T10:10:00Z")));

        mvc.perform(get("/internal/incentives/retention/approvals")
                        .headers(userHeaders())
                        .param("scopeType", "APPLICATION")
                        .param("tenantId", "courseflow")
                        .param("applicationId", "lms")
                        .param("approvalId", approvalId.toString())
                        .param("dryRunId", dryRunId.toString())
                        .param("status", "PENDING_APPROVAL")
                        .param("policyId", "terminal-reservation-request-snapshots")
                        .param("changeTicket", "CHG-42")
                        .param("requestedBy", "requester@example.com")
                        .param("approvedBy", "reviewer@example.com")
                        .param("executedBy", "ops@example.com")
                        .param("expired", "false")
                        .param("from", from.toString())
                        .param("to", to.toString())
                        .param("limit", "25"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].approvalId").value(approvalId.toString()))
                .andExpect(jsonPath("$.items[0].dryRunId").value(dryRunId.toString()))
                .andExpect(jsonPath("$.items[0].eligibleCount").value(8))
                .andExpect(jsonPath("$.items[0].approvedResultHash").value("sha256:abc"))
                .andExpect(jsonPath("$.items[0].reason").value("privacy redaction"))
                .andExpect(jsonPath("$.items[0].correlationId").value("corr-approval"))
                .andExpect(jsonPath("$.limit").value(25))
                .andExpect(jsonPath("$.hasMore").value(false))
                .andExpect(jsonPath("$.items[0].requestJson").doesNotExist())
                .andExpect(jsonPath("$.items[0].responseJson").doesNotExist())
                .andExpect(jsonPath("$.items[0].payload").doesNotExist())
                .andExpect(jsonPath("$.items[0].profileId").doesNotExist())
                .andExpect(jsonPath("$.items[0].externalReference").doesNotExist());

        verify(retentionApprovals).queue(
                eq("APPLICATION"),
                eq("courseflow"),
                eq("lms"),
                eq(approvalId),
                eq(dryRunId),
                eq("PENDING_APPROVAL"),
                eq("terminal-reservation-request-snapshots"),
                eq("CHG-42"),
                eq("requester@example.com"),
                eq("reviewer@example.com"),
                eq("ops@example.com"),
                eq(false),
                eq(from),
                eq(to),
                eq(25),
                any(CurrentUser.class));
    }

    @Test
    void retentionEvidencePackViewAndExportForwardCorrelationAndRemainAuditSafe() throws Exception {
        UUID approvalId = UUID.randomUUID();
        when(retentionApprovals.evidencePack(eq(approvalId), any(CurrentUser.class), eq("corr-view")))
                .thenReturn(new RetentionEvidencePackDto(
                        "retention-evidence-pack.v1",
                        "retention_compliance_evidence_pack",
                        approvalId,
                        Instant.parse("2026-06-14T10:20:00Z"),
                        null,
                        null,
                        null,
                        List.of(),
                        List.of("No retention execution operation has been recorded for this approval.")));
        when(retentionApprovals.evidencePackExport(eq(approvalId), eq("json"), any(CurrentUser.class), eq("corr-export")))
                .thenReturn(new RetentionEvidencePackExportDto(
                        approvalId,
                        "retention-evidence-pack-%s-20260614102000.json".formatted(approvalId),
                        "application/json",
                        "{\"schemaVersion\":\"retention-evidence-pack.v1\"}",
                        "sha256:" + "a".repeat(64),
                        Instant.parse("2026-06-14T10:20:00Z")));

        mvc.perform(get("/internal/incentives/retention/approvals/{approvalId}/evidence-pack", approvalId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-view"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.schemaVersion").value("retention-evidence-pack.v1"))
                .andExpect(jsonPath("$.warnings[0]").value("No retention execution operation has been recorded for this approval."))
                .andExpect(jsonPath("$.requestJson").doesNotExist())
                .andExpect(jsonPath("$.responseJson").doesNotExist())
                .andExpect(jsonPath("$.profileId").doesNotExist())
                .andExpect(jsonPath("$.idempotencyKey").doesNotExist());

        mvc.perform(get("/internal/incentives/retention/approvals/{approvalId}/evidence-pack/export", approvalId)
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-export")
                        .param("format", "json"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.approvalId").value(approvalId.toString()))
                .andExpect(jsonPath("$.contentType").value("application/json"))
                .andExpect(jsonPath("$.contentSha256").value("sha256:" + "a".repeat(64)))
                .andExpect(jsonPath("$.requestHash").doesNotExist())
                .andExpect(jsonPath("$.responseJson").doesNotExist())
                .andExpect(jsonPath("$.profileId").doesNotExist())
                .andExpect(jsonPath("$.idempotencyKey").doesNotExist());

        verify(retentionApprovals).evidencePack(eq(approvalId), any(CurrentUser.class), eq("corr-view"));
        verify(retentionApprovals).evidencePackExport(eq(approvalId), eq("json"), any(CurrentUser.class), eq("corr-export"));
    }

    @Test
    void retentionExecutionForwardsCorrelationAndReturnsAggregateOnly() throws Exception {
        UUID dryRunId = UUID.randomUUID();
        UUID executionId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        when(retentionExecutions.execute(any(), any(), eq("corr-redaction")))
                .thenReturn(new RetentionExecutionResponseDto(
                        executionId,
                        "SUCCEEDED",
                        "terminal-reservation-request-snapshots",
                        "v1",
                        "incentive_reservation_request_snapshots",
                        "courseflow",
                        "lms",
                        Instant.parse("2026-05-15T10:00:00Z"),
                        dryRunId,
                        "sha256:abc",
                        8,
                        5,
                        500,
                        true,
                        false,
                        Instant.parse("2026-06-14T10:00:00Z")));

        mvc.perform(post("/internal/incentives/retention/executions")
                        .headers(userHeaders())
                        .header(GatewayHeaders.CORRELATION_ID, "corr-redaction")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "approvalId": "%s",
                                  "idempotencyKey": "retention-2026-06",
                                  "confirm": true
                                }
                                """.formatted(approvalId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.executionId").value(executionId.toString()))
                .andExpect(jsonPath("$.status").value("SUCCEEDED"))
                .andExpect(jsonPath("$.eligibleBefore").value(8))
                .andExpect(jsonPath("$.redactedCount").value(5))
                .andExpect(jsonPath("$.hasMore").value(true))
                .andExpect(jsonPath("$.requestJson").doesNotExist())
                .andExpect(jsonPath("$.responseJson").doesNotExist())
                .andExpect(jsonPath("$.payload").doesNotExist())
                .andExpect(jsonPath("$.profileId").doesNotExist())
                .andExpect(jsonPath("$.externalReference").doesNotExist());

        verify(retentionExecutions).execute(any(), any(CurrentUser.class), eq("corr-redaction"));
    }

    @Test
    void runtimeEvaluateAllowsServiceActorThroughControllerBoundary() throws Exception {
        when(promotions.evaluate(any(), any()))
                .thenReturn(new EvaluateIncentivesResponseDto(
                        true, null, null, "WELCOME10", null, List.of(), List.of("ELIGIBLE")));

        mvc.perform(post("/internal/incentives/evaluate")
                        .headers(serviceHeaders(InternalScopes.PROMOTION_EVALUATE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.eligible").value(true))
                .andExpect(jsonPath("$.campaignCode").value("WELCOME10"));

        verify(promotions).evaluate(any(), any(CurrentUser.class));
    }

    @Test
    void runtimeEvaluateRejectsGenericServiceScopeBeforeController() throws Exception {
        mvc.perform(post("/internal/incentives/evaluate")
                        .headers(serviceHeaders(InternalScopes.SERVICE))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request())))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(promotions);
    }

    private HttpHeaders userHeaders() {
        HttpHeaders headers = new HttpHeaders();
        internalJwtService.applyUserToken(headers, new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of()));
        return headers;
    }

    private HttpHeaders serviceHeaders(String scope) {
        HttpHeaders headers = new HttpHeaders();
        internalJwtService.applyServiceToken(headers, Set.of(scope));
        return headers;
    }

    private EvaluateIncentivesRequestDto request() {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                "profile-1",
                "cart-1",
                "WEB",
                "USD",
                List.of(),
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.ZERO),
                List.of(),
                java.util.Map.of("segment", "NEW"));
    }
}
