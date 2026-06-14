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
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveCouponImportOperation;
import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import edu.courseflow.promotion.model.IncentiveOperationApproval;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportOperationRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportRowRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class CouponImportCommitServiceTest {

    @Mock
    IncentiveCampaignRepository campaigns;
    @Mock
    IncentiveCouponRepository coupons;
    @Mock
    IncentiveCouponImportBatchRepository importBatches;
    @Mock
    IncentiveCouponImportRowRepository importRows;
    @Mock
    IncentiveCouponImportOperationRepository operations;
    @Mock
    IncentiveIdempotencyKeyRepository idempotencyKeys;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;
    @Mock
    CouponImportApprovalService importApprovals;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final CouponCodeFingerprintService fingerprints =
            new CouponCodeFingerprintService("test", "test-coupon-pepper", "", true);
    private CouponImportDryRunService dryRuns;
    private CouponImportCommitService commits;

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
        commits = new CouponImportCommitService(
                dryRuns,
                importApprovals,
                importBatches,
                operations,
                coupons,
                idempotencyKeys,
                auditEvents,
                fingerprints,
                new CouponStorageCutoverGuard(coupons, fingerprints),
                AdminOperationRateGuard.disabled(metrics),
                access,
                metrics,
                objectMapper);
    }

    @Test
    void commitRevalidatesDryRunAndCreatesMaskedCouponsAtomically() throws Exception {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String csv = """
                code,holderProfileId,maxRedemptions,startsAt,expiresAt,metadata.channel
                SAVE10,profile-1,2,2026-01-01T00:00:00Z,2026-12-31T00:00:00Z,web
                """;
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
        when(coupons.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(operations.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        CouponImportDryRunResponseDto dryRun = dryRuns.dryRun(dryRunRequest(campaign.getId(), csv), admin, "corr-dry");
        IncentiveOperationApproval approval = approval(campaign, dryRun.dryRunId(), dryRun.resultHash());
        stubApproval(approval);
        IncentiveCouponImportBatch batch = batch(campaign, dryRun);
        when(importBatches.lockById(dryRun.dryRunId())).thenReturn(Optional.of(batch));
        var inProgress = org.mockito.Mockito.mock(IncentiveIdempotencyKey.class);
        AtomicReference<String> requestHash = new AtomicReference<>();
        when(idempotencyKeys.insertInProgressIfAbsent(
                any(), eq("courseflow"), eq("lms"), eq("COUPON_IMPORT_COMMIT"), eq("commit-1"), any(), any()))
                .thenAnswer(invocation -> {
                    requestHash.set(invocation.getArgument(5, String.class));
                    return 1;
                });
        when(idempotencyKeys.lockByScope("courseflow", "lms", "COUPON_IMPORT_COMMIT", "commit-1"))
                .thenReturn(Optional.of(inProgress));
        when(inProgress.getRequestHash()).thenAnswer(invocation -> requestHash.get());
        when(inProgress.expired(any())).thenReturn(false);
        when(inProgress.succeeded()).thenReturn(false);
        when(inProgress.inProgress()).thenReturn(true);

        CouponImportCommitResponseDto response = commits.commit(commitRequest(
                approval.getId(),
                dryRun.dryRunId(),
                campaign.getId(),
                csv,
                dryRun.resultHash(),
                "commit-1",
                true), admin, "corr-commit");

        assertThat(response.status()).isEqualTo("SUCCEEDED");
        assertThat(response.approvalId()).isEqualTo(approval.getId());
        assertThat(response.requestedRows()).isEqualTo(1);
        assertThat(response.importedRows()).isEqualTo(1);
        assertThat(response.resultHash()).isEqualTo(dryRun.resultHash());
        assertThat(response.idempotencyReplay()).isFalse();
        assertThat(batch.getCommittedAt()).isNotNull();
        assertThat(batch.getExpiresAt()).isNull();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Iterable<IncentiveCoupon>> couponsCaptor = ArgumentCaptor.forClass(Iterable.class);
        verify(coupons).saveAll(couponsCaptor.capture());
        List<IncentiveCoupon> savedCoupons = ((Collection<IncentiveCoupon>) couponsCaptor.getValue())
                .stream()
                .toList();
        assertThat(savedCoupons).hasSize(1);
        IncentiveCoupon saved = savedCoupons.getFirst();
        assertThat(saved.getCode()).isEqualTo("SA****10");
        assertThat(saved.getNormalizedCode()).startsWith("hmac-sha256:test:");
        assertThat(saved.getHolderProfileId()).isEqualTo("profile-1");
        assertThat(saved.getStartsAt()).isEqualTo(Instant.parse("2026-01-01T00:00:00Z"));
        assertThat(saved.getExpiresAt()).isEqualTo(Instant.parse("2026-12-31T00:00:00Z"));
        assertThat(saved.getMaxRedemptions()).isEqualTo(2);
        assertThat(saved.getMetadataJson()).contains("\"channel\":\"web\"");

        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents, org.mockito.Mockito.atLeastOnce()).save(auditCaptor.capture());
        IncentiveAuditEvent commitAudit = auditCaptor.getAllValues().stream()
                .filter(event -> "coupon.import_committed".equals(event.getAction()))
                .findFirst()
                .orElseThrow();
        assertThat(commitAudit.getPayloadJson())
                .contains("\"importedRows\":1")
                .contains("\"reason\":\"approved import\"")
                .contains("\"changeTicket\":\"CHG-100\"")
                .contains("idempotencyKeyHash")
                .doesNotContain("SAVE10")
                .doesNotContain(fingerprints.primaryFingerprint("SAVE10"));
        assertThat(commitAudit.getNote()).isEqualTo("approved import");

        ArgumentCaptor<IncentiveCouponImportOperation> operationCaptor =
                ArgumentCaptor.forClass(IncentiveCouponImportOperation.class);
        verify(operations).save(operationCaptor.capture());
        assertThat(operationCaptor.getValue().getApprovalId()).isEqualTo(approval.getId());
        assertThat(operationCaptor.getValue().getReason()).isEqualTo("approved import");
        assertThat(operationCaptor.getValue().getChangeTicket()).isEqualTo("CHG-100");
        assertThat(operationCaptor.getValue().getIdempotencyKeyHash()).startsWith("hmac-sha256:test:");
        assertThat(operationCaptor.getValue().getResponseJson())
                .doesNotContain("SAVE10")
                .doesNotContain("normalizedCode")
                .doesNotContain("fingerprint");
        verify(idempotencyKeys).save(inProgress);
        verify(importApprovals).markCommitted(eq(approval), eq("1"), any(), eq("corr-commit"), eq("api-gateway"));
    }

    @Test
    void commitRejectsHashMismatchWithoutWritingCoupons() {
        CurrentUser admin = admin();
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
        IncentiveOperationApproval approval = approval(campaign, dryRun.dryRunId(), dryRun.resultHash());
        stubApproval(approval);
        IncentiveCouponImportBatch batch = batch(campaign, dryRun);
        when(importBatches.lockById(dryRun.dryRunId())).thenReturn(Optional.of(batch));

        assertThatThrownBy(() -> commits.commit(commitRequest(
                approval.getId(),
                dryRun.dryRunId(),
                campaign.getId(),
                csv,
                "hmac-sha256:test:different",
                "commit-1",
                true), admin, "corr-commit"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("result hash");

        verify(coupons, never()).saveAll(any());
    }

    @Test
    void commitRequiresConfirmTrue() {
        assertThatThrownBy(() -> commits.commit(new CouponImportCommitRequestDto(
                UUID.randomUUID(),
                UUID.randomUUID(),
                UUID.randomUUID(),
                "code\nSAVE10\n",
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                "reason",
                "CHG-1",
                "hmac-sha256:test:result",
                "commit-1",
                false), admin(), "corr-commit"))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("confirm");
    }

    @Test
    void commitRequiresApprovalId() {
        assertThatThrownBy(() -> commits.commit(new CouponImportCommitRequestDto(
                null,
                UUID.randomUUID(),
                UUID.randomUUID(),
                "code\nSAVE10\n",
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                "reason",
                "CHG-1",
                "hmac-sha256:test:result",
                "commit-1",
                true), admin(), "corr-commit"))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("approvalId");
    }

    @Test
    void commitReplaysSuccessfulImportWithSameIdempotencyKey() throws Exception {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        UUID dryRunId = UUID.randomUUID();
        IncentiveOperationApproval approval = approval(campaign, dryRunId, "hmac-sha256:test:result");
        stubApproval(approval);
        CouponImportCommitResponseDto stored = new CouponImportCommitResponseDto(
                UUID.randomUUID(),
                approval.getId(),
                dryRunId,
                campaign.getId(),
                "SUCCEEDED",
                1,
                1,
                "hmac-sha256:test:result",
                false,
                Instant.parse("2026-06-14T10:00:00Z"),
                List.of());
        IncentiveCouponImportBatch batch = batch(campaign, stored.dryRunId(), stored.resultHash(), true);
        batch.markCommitted(stored.importId(), stored.importedRows(), "1", stored.committedAt());
        when(importBatches.lockById(stored.dryRunId())).thenReturn(Optional.of(batch));
        var replayKey = org.mockito.Mockito.mock(IncentiveIdempotencyKey.class);
        when(idempotencyKeys.lockByScope("courseflow", "lms", "COUPON_IMPORT_COMMIT", "commit-1"))
                .thenReturn(Optional.of(replayKey));
        when(replayKey.getRequestHash()).thenReturn(commitRequestHash(commitRequest(
                approval.getId(),
                stored.dryRunId(),
                campaign.getId(),
                csv,
                stored.resultHash(),
                "commit-1",
                true)));
        when(replayKey.expired(any())).thenReturn(false);
        when(replayKey.succeeded()).thenReturn(true);
        when(replayKey.getResponseJson()).thenReturn(objectMapper.writeValueAsString(stored));

        CouponImportCommitResponseDto response = commits.commit(commitRequest(
                approval.getId(),
                stored.dryRunId(),
                campaign.getId(),
                csv,
                stored.resultHash(),
                "commit-1",
                true), admin, "corr-commit");

        assertThat(response.idempotencyReplay()).isTrue();
        assertThat(response.importId()).isEqualTo(stored.importId());
        verify(coupons, never()).saveAll(any());
    }

    @Test
    void commitReplaysCommittedOperationAndHealsInProgressIdempotencyKey() throws Exception {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        UUID dryRunId = UUID.randomUUID();
        IncentiveOperationApproval approval = approval(campaign, dryRunId, "hmac-sha256:test:result");
        stubApproval(approval);
        CouponImportCommitRequestDto request = commitRequest(
                approval.getId(),
                dryRunId,
                campaign.getId(),
                csv,
                approval.getResultHash(),
                "commit-1",
                true);
        String requestHash = commitRequestHash(request);
        String idempotencyKeyHash = fingerprints.integrityHash("coupon-import-idempotency-key", "commit-1");
        CouponImportCommitResponseDto stored = new CouponImportCommitResponseDto(
                UUID.randomUUID(),
                approval.getId(),
                dryRunId,
                campaign.getId(),
                "SUCCEEDED",
                1,
                1,
                approval.getResultHash(),
                false,
                Instant.parse("2026-06-14T10:00:00Z"),
                List.of());
        IncentiveCouponImportBatch batch = batch(campaign, dryRunId, stored.resultHash(), true);
        batch.markCommitted(stored.importId(), stored.importedRows(), "1", stored.committedAt());
        IncentiveCouponImportOperation operation = operation(stored, campaign, requestHash, idempotencyKeyHash);
        when(importBatches.lockById(dryRunId)).thenReturn(Optional.of(batch));
        when(operations.findByDryRunId(dryRunId)).thenReturn(Optional.of(operation));
        var inProgressKey = org.mockito.Mockito.mock(IncentiveIdempotencyKey.class);
        when(idempotencyKeys.lockByScope("courseflow", "lms", "COUPON_IMPORT_COMMIT", "commit-1"))
                .thenReturn(Optional.of(inProgressKey));
        when(inProgressKey.getRequestHash()).thenReturn(requestHash);
        when(inProgressKey.expired(any())).thenReturn(false);
        when(inProgressKey.succeeded()).thenReturn(false);
        when(inProgressKey.inProgress()).thenReturn(true);

        CouponImportCommitResponseDto response = commits.commit(request, admin, "corr-commit-replay");

        assertThat(response.idempotencyReplay()).isTrue();
        assertThat(response.importId()).isEqualTo(stored.importId());
        verify(coupons, never()).saveAll(any());
        verify(inProgressKey).complete(any(), any());
        verify(idempotencyKeys).save(inProgressKey);
    }

    @Test
    void commitReplaysCommittedOperationWhenIdempotencyKeyIsMissing() throws Exception {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        UUID dryRunId = UUID.randomUUID();
        IncentiveOperationApproval approval = approval(campaign, dryRunId, "hmac-sha256:test:result");
        stubApproval(approval);
        CouponImportCommitRequestDto request = commitRequest(
                approval.getId(),
                dryRunId,
                campaign.getId(),
                csv,
                approval.getResultHash(),
                "commit-1",
                true);
        String requestHash = commitRequestHash(request);
        CouponImportCommitResponseDto stored = new CouponImportCommitResponseDto(
                UUID.randomUUID(),
                approval.getId(),
                dryRunId,
                campaign.getId(),
                "SUCCEEDED",
                1,
                1,
                approval.getResultHash(),
                false,
                Instant.parse("2026-06-14T10:00:00Z"),
                List.of());
        IncentiveCouponImportBatch batch = batch(campaign, dryRunId, stored.resultHash(), true);
        batch.markCommitted(stored.importId(), stored.importedRows(), "1", stored.committedAt());
        when(importBatches.lockById(dryRunId)).thenReturn(Optional.of(batch));
        when(idempotencyKeys.lockByScope("courseflow", "lms", "COUPON_IMPORT_COMMIT", "commit-1"))
                .thenReturn(Optional.empty());
        when(operations.findById(stored.importId())).thenReturn(Optional.of(operation(
                stored,
                campaign,
                requestHash,
                fingerprints.integrityHash("coupon-import-idempotency-key", "commit-1"))));

        CouponImportCommitResponseDto response = commits.commit(request, admin, "corr-commit-replay");

        assertThat(response.idempotencyReplay()).isTrue();
        assertThat(response.importId()).isEqualTo(stored.importId());
        verify(coupons, never()).saveAll(any());
        verify(idempotencyKeys, never()).save(any());
    }

    @Test
    void commitRejectsCommittedOperationReplayWhenRequestOrKeyDoesNotMatch() throws Exception {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        UUID dryRunId = UUID.randomUUID();
        IncentiveOperationApproval approval = approval(campaign, dryRunId, "hmac-sha256:test:result");
        stubApproval(approval);
        CouponImportCommitRequestDto request = commitRequest(
                approval.getId(),
                dryRunId,
                campaign.getId(),
                csv,
                approval.getResultHash(),
                "commit-1",
                true);
        CouponImportCommitResponseDto stored = new CouponImportCommitResponseDto(
                UUID.randomUUID(),
                approval.getId(),
                dryRunId,
                campaign.getId(),
                "SUCCEEDED",
                1,
                1,
                approval.getResultHash(),
                false,
                Instant.parse("2026-06-14T10:00:00Z"),
                List.of());
        IncentiveCouponImportBatch batch = batch(campaign, dryRunId, stored.resultHash(), true);
        batch.markCommitted(stored.importId(), stored.importedRows(), "1", stored.committedAt());
        when(importBatches.lockById(dryRunId)).thenReturn(Optional.of(batch));
        when(idempotencyKeys.lockByScope("courseflow", "lms", "COUPON_IMPORT_COMMIT", "commit-1"))
                .thenReturn(Optional.empty());
        when(operations.findById(stored.importId())).thenReturn(Optional.of(operation(
                stored,
                campaign,
                "hmac-sha256:test:different-request",
                fingerprints.integrityHash("coupon-import-idempotency-key", "commit-1"))));

        assertThatThrownBy(() -> commits.commit(request, admin, "corr-commit-replay"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("already been committed")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.COUPON_IMPORT_ALREADY_COMMITTED));

        verify(coupons, never()).saveAll(any());
        verify(idempotencyKeys, never()).save(any());
    }

    @Test
    void rateLimitedCommitStopsBeforeIdempotencyCouponWriteOperationOrAudit() {
        commits = new CouponImportCommitService(
                dryRuns,
                importApprovals,
                importBatches,
                operations,
                coupons,
                idempotencyKeys,
                auditEvents,
                fingerprints,
                new CouponStorageCutoverGuard(coupons, fingerprints),
                blockingGuard(),
                access,
                metrics,
                objectMapper);
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        UUID dryRunId = UUID.randomUUID();
        IncentiveOperationApproval approval = approval(campaign, dryRunId, "hmac-sha256:test:result");
        stubApproval(approval);
        when(importBatches.lockById(dryRunId)).thenReturn(Optional.of(batch(campaign, dryRunId, approval.getResultHash(), true)));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        assertThatThrownBy(() -> commits.commit(commitRequest(
                approval.getId(),
                dryRunId,
                campaign.getId(),
                csv,
                approval.getResultHash(),
                "commit-1",
                true), admin, "corr-commit"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(idempotencyKeys, never()).insertInProgressIfAbsent(any(), any(), any(), any(), any(), any(), any());
        verify(coupons, never()).saveAll(any());
        verify(operations, never()).save(any());
        verify(auditEvents, never()).save(any());
    }

    @Test
    void commitFailsClosedWhenFallbackDisabledAndLegacyInventoryAppearsAfterDryRun() {
        CouponCodeFingerprintService fallbackOffFingerprints =
                new CouponCodeFingerprintService("test", "test-coupon-pepper", "", false);
        commits = new CouponImportCommitService(
                dryRuns,
                importApprovals,
                importBatches,
                operations,
                coupons,
                idempotencyKeys,
                auditEvents,
                fallbackOffFingerprints,
                new CouponStorageCutoverGuard(coupons, fallbackOffFingerprints),
                AdminOperationRateGuard.disabled(metrics),
                access,
                metrics,
                objectMapper);
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String csv = "code\nSAVE10\n";
        UUID dryRunId = UUID.randomUUID();
        IncentiveOperationApproval approval = approval(campaign, dryRunId, "hmac-sha256:test:result");
        stubApproval(approval);
        when(importBatches.lockById(dryRunId)).thenReturn(Optional.of(batch(campaign, dryRunId, approval.getResultHash(), true)));
        when(coupons.countByStorageFormat(
                eq("courseflow"),
                eq("lms"),
                eq(campaign.getId()),
                eq(true),
                eq(fallbackOffFingerprints.currentStoragePrefix())))
                .thenReturn(List.of(storageCount("legacy_raw", 1)));

        assertThatThrownBy(() -> commits.commit(commitRequest(
                approval.getId(),
                dryRunId,
                campaign.getId(),
                csv,
                approval.getResultHash(),
                "commit-1",
                true), admin, "corr-commit"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("Coupon storage cutover is not ready");

        verify(coupons, never()).findByCampaignIdAndNormalizedCodeIn(any(), any());
        verify(idempotencyKeys, never()).insertInProgressIfAbsent(any(), any(), any(), any(), any(), any(), any());
        verify(coupons, never()).saveAll(any());
        verify(operations, never()).save(any());
        verify(importBatches, never()).save(any());
        verify(importApprovals, never()).markCommitted(any(), any(), any(), any(), any());
        verify(auditEvents, never()).save(any());
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

    private CouponImportCommitRequestDto commitRequest(UUID dryRunId,
                                                       UUID campaignId,
                                                       String csv,
                                                       String resultHash,
                                                       String idempotencyKey,
                                                       boolean confirm) {
        return commitRequest(UUID.randomUUID(), dryRunId, campaignId, csv, resultHash, idempotencyKey, confirm);
    }

    private CouponImportCommitRequestDto commitRequest(UUID approvalId,
                                                       UUID dryRunId,
                                                       UUID campaignId,
                                                       String csv,
                                                       String resultHash,
                                                       String idempotencyKey,
                                                       boolean confirm) {
        return new CouponImportCommitRequestDto(
                approvalId,
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
                idempotencyKey,
                confirm);
    }

    private String commitRequestHash(CouponImportCommitRequestDto request) throws Exception {
        Map<String, Object> identity = new LinkedHashMap<>();
        identity.put("approvalId", request.approvalId() == null ? null : request.approvalId().toString());
        identity.put("dryRunId", request.dryRunId().toString());
        identity.put("campaignId", request.campaignId().toString());
        identity.put("approvedResultHash", request.approvedResultHash());
        identity.put("csvContent", request.csvContent() == null ? "" : request.csvContent());
        identity.put("maxRows", request.maxRows());
        identity.put("holderProfileId", request.holderProfileId());
        identity.put("startsAt", request.startsAt() == null ? null : request.startsAt().toString());
        identity.put("expiresAt", request.expiresAt() == null ? null : request.expiresAt().toString());
        identity.put("maxRedemptions", request.maxRedemptions());
        identity.put("maxRedemptionsPerProfile", request.maxRedemptionsPerProfile());
        identity.put("metadata", request.metadata() == null ? Map.of() : request.metadata());
        identity.put("reason", request.reason());
        identity.put("changeTicket", request.changeTicket());
        identity.put("confirm", request.confirm());
        return fingerprints.integrityHash("coupon-import-commit", objectMapper.writeValueAsString(identity));
    }

    private IncentiveCouponImportBatch batch(IncentiveCampaign campaign, CouponImportDryRunResponseDto dryRun) {
        return batch(campaign, dryRun.dryRunId(), dryRun.resultHash(), dryRun.commitReady());
    }

    private void stubApproval(IncentiveOperationApproval approval) {
        when(importApprovals.requireApprovedForCommit(eq(approval.getId()), any())).thenReturn(approval);
        when(importApprovals.effectiveCommitRequest(any(), eq(approval)))
                .thenAnswer(invocation -> invocation.getArgument(0));
    }

    private IncentiveOperationApproval approval(IncentiveCampaign campaign, UUID dryRunId, String resultHash) {
        return new IncentiveOperationApproval(
                IncentiveOperationApproval.OPERATION_COUPON_IMPORT_COMMIT,
                IncentiveOperationApproval.TARGET_COUPON_IMPORT_DRY_RUN,
                dryRunId,
                campaign.getTenantId(),
                campaign.getApplicationId(),
                campaign.getId(),
                campaign.getTenantId() + "/" + campaign.getApplicationId(),
                "hmac-sha256:test:request",
                resultHash,
                "hmac-sha256:test:subject",
                1,
                1,
                0,
                0,
                0,
                true,
                true,
                "{}",
                "approved import",
                "CHG-100",
                "1",
                "corr-approval",
                "api-gateway",
                Instant.parse("2026-07-14T10:00:00Z"));
    }

    private IncentiveCouponImportOperation operation(CouponImportCommitResponseDto response,
                                                     IncentiveCampaign campaign,
                                                     String requestHash,
                                                     String idempotencyKeyHash) throws Exception {
        return new IncentiveCouponImportOperation(
                response.importId(),
                response.dryRunId(),
                response.approvalId(),
                "courseflow",
                "lms",
                campaign.getId(),
                response.resultHash(),
                requestHash,
                idempotencyKeyHash,
                response.requestedRows(),
                response.importedRows(),
                "approved import",
                "CHG-100",
                objectMapper.writeValueAsString(response),
                "1",
                "corr-commit",
                "api-gateway");
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

    private CurrentUser admin() {
        return new CurrentUser(1L, "admin@example.com", "ADMIN", Set.of("ADMIN"), Set.of());
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
