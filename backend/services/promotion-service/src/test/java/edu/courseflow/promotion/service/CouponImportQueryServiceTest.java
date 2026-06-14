package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveCouponImportOperation;
import edu.courseflow.promotion.model.IncentiveCouponImportRow;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportOperationRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportRowRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class CouponImportQueryServiceTest {

    @Mock
    IncentiveCouponImportBatchRepository batches;
    @Mock
    IncentiveCouponImportOperationRepository operations;
    @Mock
    IncentiveCouponImportRowRepository rows;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private CouponImportQueryService service;

    @BeforeEach
    void setUp() {
        service = new CouponImportQueryService(batches, operations, rows, auditEvents, access,
                AdminOperationRateGuard.disabled(metrics), metrics, objectMapper, 10_000);
    }

    @Test
    void dryRunsRequireTenantAndApplicationScope() {
        assertThatThrownBy(() -> service.dryRuns(
                Optional.of("courseflow"),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(25),
                user()))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("applicationId");
    }

    @Test
    void dryRunsReturnSafeHistoryRows() {
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        IncentiveCouponImportBatch batch = new IncentiveCouponImportBatch(
                dryRunId,
                "courseflow",
                "lms",
                campaignId,
                "request-hash-secret",
                "idem-key-secret",
                "content-hash-secret",
                "hmac-sha256:test:result",
                2,
                2,
                0,
                0,
                0,
                true,
                true,
                "{\"safe\":true}",
                "1",
                "corr-1",
                "admin-web",
                Instant.now().plus(Duration.ofDays(30)));
        when(batches.search(eq("courseflow"), eq("lms"), eq(campaignId), eq("COMPLETED"),
                any(), any(), any(Pageable.class))).thenReturn(List.of(batch));

        var response = service.dryRuns(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.of(campaignId),
                Optional.of("completed"),
                Optional.empty(),
                Optional.empty(),
                Optional.of(25),
                user());

        assertThat(response.items()).hasSize(1);
        var item = response.items().getFirst();
        assertThat(item.dryRunId()).isEqualTo(dryRunId);
        assertThat(item.resultHash()).isEqualTo("hmac-sha256:test:result");
        assertThat(item.correlationId()).isEqualTo("corr-1");
        assertThat(response.limit()).isEqualTo(25);
        assertThat(response.hasMore()).isFalse();
        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(metrics).couponImportQuery(eq("dry_runs"), eq("success"), any());
    }

    @Test
    void operationsReturnSafeHistoryRowsAndDetectHasMore() {
        UUID importId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        IncentiveCouponImportOperation operation = new IncentiveCouponImportOperation(
                importId,
                dryRunId,
                approvalId,
                "courseflow",
                "lms",
                campaignId,
                "hmac-sha256:test:result",
                "request-hash-secret",
                "idempotency-hash-secret",
                2,
                2,
                "approved import",
                "CHG-100",
                "{\"importId\":\"safe\"}",
                "3",
                "corr-commit",
                "admin-web");
        when(operations.search(eq("courseflow"), eq("lms"), eq(campaignId), eq(approvalId),
                eq(dryRunId), eq("SUCCEEDED"), any(), any(), any(Pageable.class)))
                .thenReturn(List.of(operation, operation));

        var response = service.operations(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.of(campaignId),
                Optional.of(approvalId),
                Optional.of(dryRunId),
                Optional.of("succeeded"),
                Optional.empty(),
                Optional.empty(),
                Optional.of(1),
                user());

        assertThat(response.items()).hasSize(1);
        assertThat(response.hasMore()).isTrue();
        var item = response.items().getFirst();
        assertThat(item.importId()).isEqualTo(importId);
        assertThat(item.resultHash()).isEqualTo("hmac-sha256:test:result");
        assertThat(item.reason()).isEqualTo("approved import");
        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(metrics).couponImportQuery(eq("operations"), eq("success"), any());
    }

    @Test
    void operationDetailRequiresReviewAccess() {
        UUID importId = UUID.randomUUID();
        IncentiveCouponImportOperation operation = new IncentiveCouponImportOperation(
                importId,
                UUID.randomUUID(),
                UUID.randomUUID(),
                "courseflow",
                "lms",
                UUID.randomUUID(),
                "hmac-sha256:test:result",
                "request-hash-secret",
                "idempotency-hash-secret",
                1,
                1,
                "approved import",
                "CHG-100",
                "{}",
                "3",
                "corr-commit",
                "admin-web");
        when(operations.findById(importId)).thenReturn(Optional.of(operation));

        var response = service.operation(importId, user());

        assertThat(response.importId()).isEqualTo(importId);
        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
    }

    @Test
    void operationExportReturnsSafeCsvAndAuditsDownload() {
        UUID importId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        UUID approvalId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        IncentiveCouponImportOperation operation = new IncentiveCouponImportOperation(
                importId,
                dryRunId,
                approvalId,
                "courseflow",
                "lms",
                campaignId,
                "hmac-sha256:test:result",
                "request-hash-secret",
                "idempotency-hash-secret",
                2,
                2,
                "=approved import",
                "@CHG-100",
                "{\"raw\":\"SAVE10\",\"csvContent\":\"code\\\\nSAVE10\",\"normalizedCode\":\"SAVE10\","
                        + "\"fingerprint\":\"hmac-sha256:test:fingerprint\","
                        + "\"metadata\":{\"profileId\":\"profile-secret\"},\"secret\":\"response-secret\"}",
                "3",
                "corr-commit",
                "admin-web");
        when(operations.findById(importId)).thenReturn(Optional.of(operation));
        when(access.sourceClientId(any())).thenReturn("api-gateway");

        var response = service.operationExport(importId, user(), "corr-export");

        assertThat(response.importId()).isEqualTo(importId);
        assertThat(response.approvalId()).isEqualTo(approvalId);
        assertThat(response.dryRunId()).isEqualTo(dryRunId);
        assertThat(response.campaignId()).isEqualTo(campaignId);
        assertThat(response.filename()).contains(importId.toString()).endsWith(".csv");
        assertThat(response.contentType()).isEqualTo("text/csv");
        assertThat(response.content())
                .contains("importId,approvalId,dryRunId,tenantId,applicationId,campaignId,status")
                .contains(importId.toString())
                .contains("hmac-sha256:test:result")
                .contains("'=approved import")
                .contains("'@CHG-100")
                .doesNotContain("request-hash-secret")
                .doesNotContain("idempotency-hash-secret")
                .doesNotContain("csvContent")
                .doesNotContain("normalizedCode")
                .doesNotContain("fingerprint")
                .doesNotContain("profile-secret")
                .doesNotContain("response-secret")
                .doesNotContain("SAVE10");
        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(metrics).couponImportQuery(eq("operation_export"), eq("success"), any());
        org.mockito.ArgumentCaptor<IncentiveAuditEvent> auditCaptor =
                org.mockito.ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        assertThat(auditCaptor.getValue().getAction()).isEqualTo("coupon.import_operation_downloaded");
        assertThat(auditCaptor.getValue().getCorrelationId()).isEqualTo("corr-export");
        assertThat(auditCaptor.getValue().getPayloadJson())
                .contains(importId.toString())
                .contains("\"importedRows\":2")
                .doesNotContain("hmac-sha256")
                .doesNotContain("csvContent")
                .doesNotContain("normalizedCode")
                .doesNotContain("fingerprint")
                .doesNotContain("profile-secret")
                .doesNotContain("request-hash-secret")
                .doesNotContain("idempotency-hash-secret")
                .doesNotContain("response-secret")
                .doesNotContain("SAVE10");
    }

    @Test
    void operationExportRateLimitStopsBeforeAudit() {
        service = new CouponImportQueryService(batches, operations, rows, auditEvents, access,
                blockingGuard(), metrics, objectMapper, 10_000);
        UUID importId = UUID.randomUUID();
        IncentiveCouponImportOperation operation = new IncentiveCouponImportOperation(
                importId,
                UUID.randomUUID(),
                UUID.randomUUID(),
                "courseflow",
                "lms",
                UUID.randomUUID(),
                "hmac-sha256:test:result",
                "request-hash-secret",
                "idempotency-hash-secret",
                1,
                1,
                "approved import",
                "CHG-100",
                "{}",
                "3",
                "corr-commit",
                "admin-web");
        when(operations.findById(importId)).thenReturn(Optional.of(operation));
        when(access.sourceClientId(any())).thenReturn("api-gateway");

        assertThatThrownBy(() -> service.operationExport(importId, user(), "corr-export"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(auditEvents, never()).save(any());
        verify(metrics).couponImportQuery(eq("operation_export"), eq("error"), any());
    }

    @Test
    void issueExportReturnsMaskedCsvAndAuditsDownload() {
        UUID dryRunId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        IncentiveCouponImportBatch batch = new IncentiveCouponImportBatch(
                dryRunId,
                "courseflow",
                "lms",
                campaignId,
                "request-hash-secret",
                "idem-key-secret",
                "content-hash-secret",
                "hmac-sha256:test:result",
                2,
                0,
                2,
                1,
                1,
                true,
                false,
                "{\"safe\":true}",
                "1",
                "corr-dry",
                "admin-web",
                Instant.now().plus(Duration.ofDays(30)));
        when(batches.findById(dryRunId)).thenReturn(Optional.of(batch));
        when(rows.countByBatchIdAndRowStatus(dryRunId, "INVALID")).thenReturn(2L);
        when(rows.findByBatchIdAndRowStatusOrderByRowNumber(dryRunId, "INVALID"))
                .thenReturn(List.of(
                        new IncentiveCouponImportRow(
                                dryRunId,
                                2,
                                "=A****10",
                                "INVALID",
                                "[\"DUPLICATE_IN_FILE\"]",
                                "[{\"rowNumber\":2,\"codeMask\":\"=A****10\",\"field\":\"code\",\"reasonCode\":\"DUPLICATE_IN_FILE\",\"message\":\"Coupon code is duplicated in the CSV file\"}]"),
                        new IncentiveCouponImportRow(
                                dryRunId,
                                3,
                                "EX****20",
                                "INVALID",
                                "[\"DUPLICATE_EXISTING\"]",
                                "[{\"rowNumber\":3,\"codeMask\":\"EX****20\",\"field\":\"code\",\"reasonCode\":\"DUPLICATE_EXISTING\",\"message\":\"Coupon code already exists for campaign\"}]")));
        when(access.sourceClientId(any())).thenReturn("api-gateway");

        var response = service.dryRunIssueExport(dryRunId, Optional.empty(), user(), "corr-export");

        assertThat(response.dryRunId()).isEqualTo(dryRunId);
        assertThat(response.campaignId()).isEqualTo(campaignId);
        assertThat(response.rowStatus()).isEqualTo("INVALID");
        assertThat(response.rowCount()).isEqualTo(2);
        assertThat(response.filename()).contains(dryRunId.toString()).endsWith("-invalid.csv");
        assertThat(response.contentType()).isEqualTo("text/csv");
        assertThat(response.content())
                .contains("rowNumber,codeMask,rowStatus,issueCodes")
                .contains("'=A****10")
                .contains("DUPLICATE_IN_FILE")
                .contains("EX****20")
                .contains("DUPLICATE_EXISTING")
                .doesNotContain("SAVE10")
                .doesNotContain("EXISTS20")
                .doesNotContain("hmac-sha256")
                .doesNotContain("idem-key-secret");
        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(metrics).couponImportQuery(eq("issue_export"), eq("success"), any());
        org.mockito.ArgumentCaptor<IncentiveAuditEvent> auditCaptor =
                org.mockito.ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        assertThat(auditCaptor.getValue().getAction()).isEqualTo("coupon.import_issue_export_downloaded");
        assertThat(auditCaptor.getValue().getCorrelationId()).isEqualTo("corr-export");
        assertThat(auditCaptor.getValue().getPayloadJson())
                .contains("\"rowCount\":2")
                .doesNotContain("=A****10")
                .doesNotContain("SAVE10")
                .doesNotContain("hmac-sha256");
    }

    @Test
    void issueExportDefaultsBlankRowStatusToInvalid() {
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        IncentiveCouponImportBatch batch = new IncentiveCouponImportBatch(
                dryRunId,
                "courseflow",
                "lms",
                campaignId,
                "request-hash-secret",
                "idem-key-secret",
                "content-hash-secret",
                "hmac-sha256:test:result",
                1,
                0,
                1,
                0,
                0,
                true,
                false,
                "{\"safe\":true}",
                "1",
                "corr-dry",
                "admin-web",
                Instant.now().plus(Duration.ofDays(30)));
        when(batches.findById(dryRunId)).thenReturn(Optional.of(batch));
        when(rows.countByBatchIdAndRowStatus(dryRunId, "INVALID")).thenReturn(0L);
        when(rows.findByBatchIdAndRowStatusOrderByRowNumber(dryRunId, "INVALID")).thenReturn(List.of());

        var response = service.dryRunIssueExport(dryRunId, Optional.of(" "), user(), "corr-export");

        assertThat(response.rowStatus()).isEqualTo("INVALID");
        assertThat(response.filename()).endsWith("-invalid.csv");
        verify(rows).findByBatchIdAndRowStatusOrderByRowNumber(dryRunId, "INVALID");
    }

    @Test
    void issueExportRejectsUnsupportedRowStatus() {
        assertThatThrownBy(() -> service.dryRunIssueExport(UUID.randomUUID(), Optional.of("PENDING"), user(), "corr-export"))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("Unsupported coupon import issue export row status");
        verify(metrics).couponImportQuery(eq("issue_export"), eq("error"), any());
    }

    @Test
    void issueExportRejectsWhenSelectedRowsExceedConfiguredMax() {
        service = new CouponImportQueryService(batches, operations, rows, auditEvents, access,
                AdminOperationRateGuard.disabled(metrics), metrics, objectMapper, 1);
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        IncentiveCouponImportBatch batch = new IncentiveCouponImportBatch(
                dryRunId,
                "courseflow",
                "lms",
                campaignId,
                "request-hash-secret",
                "idem-key-secret",
                "content-hash-secret",
                "hmac-sha256:test:result",
                2,
                0,
                2,
                0,
                0,
                true,
                false,
                "{\"safe\":true}",
                "1",
                "corr-dry",
                "admin-web",
                Instant.now().plus(Duration.ofDays(30)));
        when(batches.findById(dryRunId)).thenReturn(Optional.of(batch));
        when(rows.countByBatchIdAndRowStatus(dryRunId, "INVALID")).thenReturn(2L);

        assertThatThrownBy(() -> service.dryRunIssueExport(dryRunId, Optional.of("INVALID"), user(), "corr-export"))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("EXPORT_TOO_LARGE")
                .hasMessageContaining("exceeds max rows 1");

        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(rows, never()).findByBatchIdAndRowStatusOrderByRowNumber(dryRunId, "INVALID");
        verify(auditEvents, never()).save(any());
        verify(metrics).couponImportQuery(eq("issue_export"), eq("error"), any());
    }

    @Test
    void issueExportRateLimitStopsBeforeCountFetchOrAudit() {
        service = new CouponImportQueryService(batches, operations, rows, auditEvents, access,
                blockingGuard(), metrics, objectMapper, 10_000);
        UUID campaignId = UUID.randomUUID();
        UUID dryRunId = UUID.randomUUID();
        IncentiveCouponImportBatch batch = new IncentiveCouponImportBatch(
                dryRunId,
                "courseflow",
                "lms",
                campaignId,
                "request-hash-secret",
                "idem-key-secret",
                "content-hash-secret",
                "hmac-sha256:test:result",
                1,
                0,
                1,
                0,
                0,
                true,
                false,
                "{\"safe\":true}",
                "1",
                "corr-dry",
                "admin-web",
                Instant.now().plus(Duration.ofDays(30)));
        when(batches.findById(dryRunId)).thenReturn(Optional.of(batch));
        when(access.sourceClientId(any())).thenReturn("api-gateway");

        assertThatThrownBy(() -> service.dryRunIssueExport(dryRunId, Optional.of("INVALID"), user(), "corr-export"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(access).requireCouponImportReadAccess(eq("courseflow"), eq("lms"), any(CurrentUser.class));
        verify(rows, never()).countByBatchIdAndRowStatus(dryRunId, "INVALID");
        verify(rows, never()).findByBatchIdAndRowStatusOrderByRowNumber(dryRunId, "INVALID");
        verify(auditEvents, never()).save(any());
        verify(metrics).couponImportQuery(eq("issue_export"), eq("error"), any());
    }

    private static CurrentUser user() {
        return new CurrentUser(1L, "admin@example.com", "ADMIN", Set.of("ADMIN"), Set.of(), null);
    }

    private AdminOperationRateGuard blockingGuard() {
        AdminOperationRateGuardProperties properties = new AdminOperationRateGuardProperties();
        properties.setMode(AdminOperationRateGuardProperties.Mode.ENFORCED);
        properties.setKeyId("test");
        properties.setPepper("test-admin-operation-rate-pepper-32-byte-value");
        properties.validate();
        return new AdminOperationRateGuard(properties, (key, capacity, window) ->
                new CouponAbuseRateLimitStore.Hit(capacity + 1L, false), metrics);
    }
}
