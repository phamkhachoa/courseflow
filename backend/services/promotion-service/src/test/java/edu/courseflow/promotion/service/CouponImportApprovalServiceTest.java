package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveOperationApproval;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportRowRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import edu.courseflow.promotion.repository.IncentiveOperationApprovalRepository;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class CouponImportApprovalServiceTest {

    @Mock
    IncentiveCampaignRepository campaigns;
    @Mock
    IncentiveCouponRepository coupons;
    @Mock
    IncentiveCouponImportBatchRepository importBatches;
    @Mock
    IncentiveCouponImportRowRepository importRows;
    @Mock
    IncentiveIdempotencyKeyRepository idempotencyKeys;
    @Mock
    IncentiveOperationApprovalRepository approvals;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final CouponCodeFingerprintService fingerprints =
            new CouponCodeFingerprintService("test", "test-coupon-pepper", "", true);
    private CouponImportDryRunService dryRuns;
    private CouponImportApprovalService service;

    @BeforeEach
    void setUp() {
        dryRuns = new CouponImportDryRunService(
                campaigns,
                coupons,
                importBatches,
                importRows,
                idempotencyKeys,
                auditEvents,
                access,
                fingerprints,
                AdminOperationRateGuard.disabled(metrics),
                metrics,
                objectMapper,
                true,
                30);
        service = new CouponImportApprovalService(
                dryRuns,
                importBatches,
                approvals,
                auditEvents,
                fingerprints,
                AdminOperationRateGuard.disabled(metrics),
                access,
                objectMapper,
                60);
    }

    @Test
    void requestApprovalPersistsPendingAggregateWithoutRawCouponCodes() {
        CurrentUser admin = user(1L);
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(coupons.findByCampaignIdAndNormalizedCodeIn(eq(campaign.getId()), any())).thenReturn(List.of());
        when(coupons.countByStorageFormat(
                eq("courseflow"),
                eq("lms"),
                eq(campaign.getId()),
                eq(true),
                eq(fingerprints.currentStoragePrefix())))
                .thenReturn(List.of(storageCount("current_hmac", 0)));
        when(importBatches.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(importRows.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(approvals.findActiveForSubject(any(), any(), any(), any())).thenReturn(Optional.empty());
        when(approvals.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        CouponImportDryRunResponseDto dryRun = dryRuns.dryRun(dryRunRequest(campaign.getId(), csv), admin, "corr-dry");
        IncentiveCouponImportBatch batch = batch(campaign, dryRun);
        when(importBatches.lockById(dryRun.dryRunId())).thenReturn(Optional.of(batch));

        CouponImportApprovalResponseDto response = service.requestApproval(
                dryRun.dryRunId(),
                approvalRequest(dryRun.dryRunId(), campaign.getId(), csv, dryRun.resultHash()),
                admin,
                "corr-approval");

        assertThat(response.status()).isEqualTo(IncentiveOperationApproval.STATUS_PENDING);
        assertThat(response.dryRunId()).isEqualTo(dryRun.dryRunId());
        assertThat(response.approvedResultHash()).isEqualTo(dryRun.resultHash());
        assertThat(response.requestedBy()).isEqualTo("1");
        assertThat(response.reason()).isEqualTo("approved import");

        ArgumentCaptor<IncentiveOperationApproval> approvalCaptor =
                ArgumentCaptor.forClass(IncentiveOperationApproval.class);
        verify(approvals).save(approvalCaptor.capture());
        assertThat(approvalCaptor.getValue().getSubjectJson())
                .contains("\"requestedRows\":1")
                .doesNotContain("SAVE10")
                .doesNotContain("normalizedCode")
                .doesNotContain("fingerprint");

        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents, org.mockito.Mockito.atLeastOnce()).save(auditCaptor.capture());
        IncentiveAuditEvent approvalAudit = auditCaptor.getAllValues().stream()
                .filter(event -> "coupon.import_approval_requested".equals(event.getAction()))
                .findFirst()
                .orElseThrow();
        assertThat(approvalAudit.getPayloadJson())
                .contains("\"reason\":\"approved import\"")
                .doesNotContain("SAVE10")
                .doesNotContain("normalizedCode")
                .doesNotContain("fingerprint");
    }

    @Test
    void requestApprovalRejectsDuplicateActiveApproval() {
        CurrentUser admin = user(1L);
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(coupons.findByCampaignIdAndNormalizedCodeIn(eq(campaign.getId()), any())).thenReturn(List.of());
        when(coupons.countByStorageFormat(
                eq("courseflow"),
                eq("lms"),
                eq(campaign.getId()),
                eq(true),
                eq(fingerprints.currentStoragePrefix())))
                .thenReturn(List.of(storageCount("current_hmac", 0)));
        when(importBatches.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(importRows.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));
        CouponImportDryRunResponseDto dryRun = dryRuns.dryRun(dryRunRequest(campaign.getId(), csv), admin, "corr-dry");
        IncentiveCouponImportBatch batch = batch(campaign, dryRun);
        when(importBatches.lockById(dryRun.dryRunId())).thenReturn(Optional.of(batch));
        when(approvals.findActiveForSubject(any(), any(), any(), any()))
                .thenReturn(Optional.of(approval(campaign, batch, "2")));

        assertThatThrownBy(() -> service.requestApproval(
                dryRun.dryRunId(),
                approvalRequest(dryRun.dryRunId(), campaign.getId(), csv, dryRun.resultHash()),
                admin,
                "corr-approval"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("active coupon import approval")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.COUPON_IMPORT_APPROVAL_ALREADY_EXISTS));
    }

    @Test
    void requestApprovalRateLimitStopsBeforeReevaluationActiveApprovalMutationOrAudit() {
        CurrentUser admin = user(1L);
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        UUID dryRunId = UUID.randomUUID();
        IncentiveCouponImportBatch batch = batch(campaign, dryRunId, "hmac-sha256:test:result", true);
        CouponImportApprovalService guardedService = serviceWithGuard(blockingGuard());
        when(importBatches.lockById(dryRunId)).thenReturn(Optional.of(batch));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        assertThatThrownBy(() -> guardedService.requestApproval(
                dryRunId,
                approvalRequest(dryRunId, campaign.getId(), csv, batch.getResultHash()),
                admin,
                "corr-approval-rate-limit"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(metrics).adminOperationRateGuard(
                "coupon_import_approval_request", "enforced", "application", "limited");
        verify(campaigns, never()).findById(any());
        verify(approvals, never()).findActiveForSubject(any(), any(), any(), any());
        verify(approvals, never()).save(any());
        verify(auditEvents, never()).save(any());
    }

    @Test
    void approveRejectsRequesterAsReviewer() {
        IncentiveCampaign campaign = campaign();
        IncentiveCouponImportBatch batch = batch(campaign, UUID.randomUUID(), "hmac-sha256:test:result", true);
        IncentiveOperationApproval approval = approval(campaign, batch, "1");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));

        assertThatThrownBy(() -> service.approve(
                approval.getId(),
                new CouponImportApprovalDecisionRequestDto("looks good"),
                user(1L),
                "corr-approval"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("different operator");
    }

    @Test
    void approveTransitionsPendingApprovalAfterBatchValidation() {
        IncentiveCampaign campaign = campaign();
        IncentiveCouponImportBatch batch = batch(campaign, UUID.randomUUID(), "hmac-sha256:test:result", true);
        IncentiveOperationApproval approval = approval(campaign, batch, "1");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        when(importBatches.lockById(batch.getId())).thenReturn(Optional.of(batch));

        CouponImportApprovalResponseDto response = service.approve(
                approval.getId(),
                new CouponImportApprovalDecisionRequestDto("looks good"),
                user(2L),
                "corr-approval");

        assertThat(response.status()).isEqualTo(IncentiveOperationApproval.STATUS_APPROVED);
        assertThat(response.approvedBy()).isEqualTo("2");
        assertThat(response.approvedAt()).isNotNull();
    }

    @Test
    void approveRateLimitStopsBeforeBatchValidationMutationOrAudit() {
        IncentiveCampaign campaign = campaign();
        IncentiveCouponImportBatch batch = batch(campaign, UUID.randomUUID(), "hmac-sha256:test:result", true);
        IncentiveOperationApproval approval = approval(campaign, batch, "1");
        CurrentUser reviewer = user(2L);
        CouponImportApprovalService guardedService = serviceWithGuard(blockingGuard());
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        when(access.sourceClientId(reviewer)).thenReturn("api-gateway");

        assertThatThrownBy(() -> guardedService.approve(
                approval.getId(),
                new CouponImportApprovalDecisionRequestDto("looks good"),
                reviewer,
                "corr-approval-rate-limit"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(metrics).adminOperationRateGuard(
                "coupon_import_approval_decision", "enforced", "application", "limited");
        assertThat(approval.pending()).isTrue();
        assertThat(approval.getApprovedBy()).isNull();
        verify(importBatches, never()).lockById(batch.getId());
        verify(auditEvents, never()).save(any());
    }

    @Test
    void rejectRateLimitStopsBeforeMutationOrAudit() {
        IncentiveCampaign campaign = campaign();
        IncentiveCouponImportBatch batch = batch(campaign, UUID.randomUUID(), "hmac-sha256:test:result", true);
        IncentiveOperationApproval approval = approval(campaign, batch, "1");
        CurrentUser reviewer = user(2L);
        CouponImportApprovalService guardedService = serviceWithGuard(blockingGuard());
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        when(access.sourceClientId(reviewer)).thenReturn("api-gateway");

        assertThatThrownBy(() -> guardedService.reject(
                approval.getId(),
                new CouponImportApprovalDecisionRequestDto("reject for now"),
                reviewer,
                "corr-reject-rate-limit"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(metrics).adminOperationRateGuard(
                "coupon_import_approval_decision", "enforced", "application", "limited");
        assertThat(approval.pending()).isTrue();
        assertThat(approval.getRejectedBy()).isNull();
        verify(auditEvents, never()).save(any());
    }

    @Test
    void rejectTransitionsPendingApprovalWithAudit() {
        IncentiveCampaign campaign = campaign();
        IncentiveCouponImportBatch batch = batch(campaign, UUID.randomUUID(), "hmac-sha256:test:result", true);
        IncentiveOperationApproval approval = approval(campaign, batch, "1");
        CurrentUser reviewer = user(2L);
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));
        when(access.sourceClientId(reviewer)).thenReturn("api-gateway");

        CouponImportApprovalResponseDto response = service.reject(
                approval.getId(),
                new CouponImportApprovalDecisionRequestDto("reject for now"),
                reviewer,
                "corr-reject");

        assertThat(response.status()).isEqualTo(IncentiveOperationApproval.STATUS_REJECTED);
        assertThat(response.rejectedBy()).isEqualTo("2");
        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        assertThat(auditCaptor.getValue().getAction()).isEqualTo("coupon.import_approval_rejected");
        assertThat(auditCaptor.getValue().getSourceClientId()).isEqualTo("api-gateway");
    }

    @Test
    void approverCannotCommitApprovedImport() {
        IncentiveCampaign campaign = campaign();
        IncentiveCouponImportBatch batch = batch(campaign, UUID.randomUUID(), "hmac-sha256:test:result", true);
        IncentiveOperationApproval approval = approval(campaign, batch, "1");
        approval.approve("2", "looks good", Instant.parse("2026-06-14T10:00:00Z"));
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));

        assertThatThrownBy(() -> service.requireApprovedForCommit(approval.getId(), user(2L)))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("different operator from approver");
    }

    private CouponImportDryRunRequestDto dryRunRequest(UUID campaignId, String csv) {
        return new CouponImportDryRunRequestDto(
                campaignId,
                csv,
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                null);
    }

    private CouponImportCommitRequestDto approvalRequest(UUID dryRunId, UUID campaignId, String csv, String resultHash) {
        return new CouponImportCommitRequestDto(
                null,
                dryRunId,
                campaignId,
                csv,
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                "approved import",
                "CHG-100",
                resultHash,
                null,
                true);
    }

    private IncentiveOperationApproval approval(IncentiveCampaign campaign,
                                                IncentiveCouponImportBatch batch,
                                                String requestedBy) {
        String subjectHash = fingerprints.integrityHash("coupon-import-approval-subject", String.join("|",
                batch.getId().toString(),
                batch.getCampaignId().toString(),
                batch.getRequestHash(),
                batch.getContentHash(),
                batch.getResultHash(),
                Integer.toString(batch.getRequestedRows()),
                Integer.toString(batch.getValidRows()),
                Integer.toString(batch.getInvalidRows()),
                Integer.toString(batch.getDuplicateInFileRows()),
                Integer.toString(batch.getDuplicateExistingRows()),
                Boolean.toString(batch.isStorageInventoryReady()),
                Boolean.toString(batch.isCommitReady())));
        return new IncentiveOperationApproval(
                IncentiveOperationApproval.OPERATION_COUPON_IMPORT_COMMIT,
                IncentiveOperationApproval.TARGET_COUPON_IMPORT_DRY_RUN,
                batch.getId(),
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                campaign.getTenantId() + "/" + campaign.getApplicationId(),
                batch.getRequestHash(),
                batch.getResultHash(),
                subjectHash,
                batch.getRequestedRows(),
                batch.getValidRows(),
                batch.getInvalidRows(),
                batch.getDuplicateInFileRows(),
                batch.getDuplicateExistingRows(),
                batch.isStorageInventoryReady(),
                batch.isCommitReady(),
                "{}",
                "approved import",
                "CHG-100",
                requestedBy,
                "corr-approval",
                "api-gateway",
                Instant.parse("2026-07-14T10:00:00Z"));
    }

    private IncentiveCouponImportBatch batch(IncentiveCampaign campaign, CouponImportDryRunResponseDto dryRun) {
        return batch(campaign, dryRun.dryRunId(), dryRun.resultHash(), dryRun.commitReady());
    }

    private IncentiveCouponImportBatch batch(IncentiveCampaign campaign,
                                             UUID dryRunId,
                                             String resultHash,
                                             boolean commitReady) {
        return new IncentiveCouponImportBatch(
                dryRunId,
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                "hmac-sha256:test:request",
                null,
                "hmac-sha256:test:content",
                resultHash,
                1,
                1,
                0,
                0,
                0,
                true,
                commitReady,
                "{}",
                "1",
                "corr-dry",
                "api-gateway",
                Instant.parse("2026-07-14T10:00:00Z"));
    }

    private static IncentiveCouponRepository.CouponStorageFormatCount storageCount(String storageFormat, long count) {
        return new IncentiveCouponRepository.CouponStorageFormatCount() {
            @Override
            public String getStorageFormat() {
                return storageFormat;
            }

            @Override
            public long getCouponCount() {
                return count;
            }
        };
    }

    private IncentiveCampaign campaign() {
        return new IncentiveCampaign(
                "courseflow",
                "lms",
                "WELCOME",
                "Welcome Campaign",
                null,
                "PROMOTION",
                null,
                null,
                10,
                false,
                true,
                true,
                "ALL",
                "USD",
                "[]",
                "[]",
                null,
                null,
                "1");
    }

    private CurrentUser user(Long id) {
        return new CurrentUser(id, "operator@example.com", "ADMIN", Set.of("ADMIN"), Set.of());
    }

    private CouponImportApprovalService serviceWithGuard(AdminOperationRateGuard guard) {
        return new CouponImportApprovalService(
                dryRuns,
                importBatches,
                approvals,
                auditEvents,
                fingerprints,
                guard,
                access,
                objectMapper,
                60);
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
