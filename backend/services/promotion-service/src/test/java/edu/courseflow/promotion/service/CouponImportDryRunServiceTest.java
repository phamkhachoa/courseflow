package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCoupon;
import edu.courseflow.promotion.model.IncentiveCouponImportBatch;
import edu.courseflow.promotion.model.IncentiveCouponImportRow;
import edu.courseflow.promotion.model.IncentiveIdempotencyKey;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportBatchRepository;
import edu.courseflow.promotion.repository.IncentiveCouponImportRowRepository;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import java.time.Instant;
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
class CouponImportDryRunServiceTest {

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
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final CouponCodeFingerprintService fingerprints =
            new CouponCodeFingerprintService("test", "test-coupon-pepper", "", true);
    private CouponImportDryRunService service;

    @BeforeEach
    void setUp() {
        service = new CouponImportDryRunService(
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
    }

    @Test
    void dryRunPersistsMaskedReportWithoutWritingCoupons() throws Exception {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        String existingFingerprint = fingerprints.primaryFingerprint("EXISTS20");
        IncentiveCoupon existingCoupon = new IncentiveCoupon(
                campaign.getId(),
                "EX****20",
                existingFingerprint,
                "EX****20",
                null,
                null,
                null,
                null,
                null,
                "{}");
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(coupons.findByCampaignIdAndNormalizedCodeIn(eq(campaign.getId()), any()))
                .thenAnswer(invocation -> {
                    @SuppressWarnings("unchecked")
                    Collection<String> lookups = invocation.getArgument(1, Collection.class);
                    return lookups.contains(existingFingerprint) ? List.of(existingCoupon) : List.of();
                });
        when(coupons.countByStorageFormat(
                eq("courseflow"),
                eq("lms"),
                eq(campaign.getId()),
                eq(true),
                eq(fingerprints.currentStoragePrefix())))
                .thenReturn(List.of(storageCount("legacy_raw", 1)));
        when(importBatches.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(importRows.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        CouponImportDryRunResponseDto response = service.dryRun(new CouponImportDryRunRequestDto(
                campaign.getId(),
                """
                        code,holderProfileId,maxRedemptions,startsAt,expiresAt,metadata.channel
                        SAVE10,profile-1,1,2026-01-01T00:00:00Z,2026-12-31T00:00:00Z,web
                        save10,profile-1,1,2026-01-01T00:00:00Z,2026-12-31T00:00:00Z,web
                        EXISTS20,profile-2,1,2026-01-01T00:00:00Z,2026-12-31T00:00:00Z,partner
                        BADWINDOW,,0,2026-12-31T00:00:00Z,2026-01-01T00:00:00Z,ops
                        """,
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                null), admin, "corr-import");

        assertThat(response.dryRun()).isTrue();
        assertThat(response.requestedRows()).isEqualTo(4);
        assertThat(response.validRows()).isEqualTo(1);
        assertThat(response.invalidRows()).isEqualTo(3);
        assertThat(response.duplicateInFileRows()).isEqualTo(1);
        assertThat(response.duplicateExistingRows()).isEqualTo(1);
        assertThat(response.storageInventoryReady()).isFalse();
        assertThat(response.commitReady()).isFalse();
        assertThat(response.resultHash()).startsWith("hmac-sha256:");
        assertThat(response.warnings()).contains("COUPON_STORAGE_MIGRATION_NOT_READY");
        assertThat(response.issues())
                .extracting(issue -> issue.codeMask() + ":" + issue.reasonCode())
                .contains(
                        "SA****10:DUPLICATE_IN_FILE",
                        "EX****20:DUPLICATE_EXISTING",
                        "BA****OW:INVALID_WINDOW_OR_LIMIT");
        assertThat(objectMapper.writeValueAsString(response))
                .doesNotContain("SAVE10")
                .doesNotContain("EXISTS20")
                .doesNotContain(existingFingerprint)
                .doesNotContain("normalizedCode")
                .doesNotContain("fingerprint");

        verify(coupons, never()).save(any());
        verify(access).requireCouponImportManageAccess("courseflow", "lms", admin);
        verify(access).requireActiveApplication("courseflow", "lms", admin, "admin");

        ArgumentCaptor<IncentiveCouponImportBatch> batchCaptor =
                ArgumentCaptor.forClass(IncentiveCouponImportBatch.class);
        verify(importBatches).save(batchCaptor.capture());
        assertThat(batchCaptor.getValue().getResultJson())
                .doesNotContain("SAVE10")
                .doesNotContain("EXISTS20")
                .contains("SA****10")
                .contains("EX****20");

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Iterable<IncentiveCouponImportRow>> rowsCaptor = ArgumentCaptor.forClass(Iterable.class);
        verify(importRows).saveAll(rowsCaptor.capture());
        assertThat(rowsCaptor.getValue()).hasSize(4);

        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        assertThat(auditCaptor.getValue().getAction()).isEqualTo("coupon.import_dry_run_created");
        assertThat(auditCaptor.getValue().getCorrelationId()).isEqualTo("corr-import");
        assertThat(auditCaptor.getValue().getSourceClientId()).isEqualTo("api-gateway");
        assertThat(auditCaptor.getValue().getPayloadJson())
                .contains("\"requestedRows\":4")
                .doesNotContain("SAVE10")
                .doesNotContain("EXISTS20")
                .doesNotContain(existingFingerprint);
    }

    @Test
    void readBackDryRunRequiresReviewAccessAndReturnsPersistedReport() throws Exception {
        UUID dryRunId = UUID.randomUUID();
        UUID campaignId = UUID.randomUUID();
        CouponImportDryRunResponseDto report = new CouponImportDryRunResponseDto(
                dryRunId,
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
                List.of());
        IncentiveCouponImportBatch batch = new IncentiveCouponImportBatch(
                dryRunId,
                "courseflow",
                "lms",
                campaignId,
                "sha256:request",
                null,
                "sha256:content",
                report.resultHash(),
                report.requestedRows(),
                report.validRows(),
                report.invalidRows(),
                report.duplicateInFileRows(),
                report.duplicateExistingRows(),
                report.storageInventoryReady(),
                report.commitReady(),
                objectMapper.writeValueAsString(report),
                "1",
                "corr-import",
                "api-gateway",
                Instant.parse("2026-07-14T10:00:00Z"));
        CurrentUser admin = admin();
        when(importBatches.findById(dryRunId)).thenReturn(Optional.of(batch));

        CouponImportDryRunResponseDto response = service.dryRun(dryRunId, admin);

        assertThat(response.dryRunId()).isEqualTo(dryRunId);
        assertThat(response.resultHash()).isEqualTo("sha256:result");
        verify(access).requireCouponImportReadAccess("courseflow", "lms", admin);
    }

    @Test
    void purgeExpiredDryRunsDeletesExpiredBatchesAndRecordsMetric() {
        when(importBatches.deleteExpiredUncommitted(any())).thenReturn(3);

        service.purgeExpiredDryRuns();

        verify(importBatches).deleteExpiredUncommitted(any());
        verify(metrics).couponImportDryRunCleanup(eq("success"), eq(3L), any());
    }

    @Test
    void resultHashUsesContentIdentityNotOnlyVisibleCodeMask() {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
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

        CouponImportDryRunResponseDto first = service.dryRun(new CouponImportDryRunRequestDto(
                campaign.getId(),
                "code\nSAVE10\n",
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                null), admin, "corr-a");
        CouponImportDryRunResponseDto second = service.dryRun(new CouponImportDryRunRequestDto(
                campaign.getId(),
                "code\nSAFE10\n",
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                null), admin, "corr-b");

        assertThat(first.sampleRows().getFirst().codeMask()).isEqualTo(second.sampleRows().getFirst().codeMask());
        assertThat(first.resultHash()).startsWith("hmac-sha256:");
        assertThat(first.resultHash()).isNotEqualTo(second.resultHash());
        verifyNoInteractions(idempotencyKeys);
    }

    @Test
    void idempotencyKeyReplaysStoredReportWithoutWritingNewBatch() throws Exception {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        UUID dryRunId = UUID.randomUUID();
        CouponImportDryRunResponseDto stored = new CouponImportDryRunResponseDto(
                dryRunId,
                campaign.getId(),
                true,
                1,
                1,
                0,
                0,
                0,
                true,
                true,
                "sha256:stored",
                Instant.parse("2026-06-14T10:00:00Z"),
                List.of(),
                List.of(),
                List.of());
        AtomicReference<String> capturedRequestHash = new AtomicReference<>();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(idempotencyKeys.insertInProgressIfAbsent(
                any(),
                eq("courseflow"),
                eq("lms"),
                eq("COUPON_IMPORT_DRY_RUN"),
                eq("import-1"),
                any(),
                any()))
                .thenAnswer(invocation -> {
                    capturedRequestHash.set(invocation.getArgument(5, String.class));
                    return 0;
                });
        when(idempotencyKeys.lockByScope("courseflow", "lms", "COUPON_IMPORT_DRY_RUN", "import-1"))
                .thenAnswer(invocation -> Optional.of(new IncentiveIdempotencyKey(
                        "courseflow",
                        "lms",
                        "COUPON_IMPORT_DRY_RUN",
                        "import-1",
                        capturedRequestHash.get(),
                        objectMapper.writeValueAsString(stored),
                        Instant.parse("2026-06-21T10:00:00Z"))));

        CouponImportDryRunResponseDto response = service.dryRun(new CouponImportDryRunRequestDto(
                campaign.getId(),
                "code\nSAVE10\n",
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                "import-1"), admin, "corr-import");

        assertThat(response.dryRunId()).isEqualTo(dryRunId);
        assertThat(response.resultHash()).isEqualTo("sha256:stored");
        verify(coupons, never()).findByCampaignIdAndNormalizedCodeIn(any(), any());
        verify(importBatches, never()).save(any());
        verify(importRows, never()).saveAll(any());
        verify(auditEvents, never()).save(any());
    }

    @Test
    void idempotencyKeyRejectsDifferentPayload() {
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(idempotencyKeys.lockByScope("courseflow", "lms", "COUPON_IMPORT_DRY_RUN", "import-1"))
                .thenReturn(Optional.of(new IncentiveIdempotencyKey(
                        "courseflow",
                        "lms",
                        "COUPON_IMPORT_DRY_RUN",
                        "import-1",
                        "sha256:different",
                        "{}",
                        Instant.parse("2026-06-21T10:00:00Z"))));

        assertThatThrownBy(() -> service.dryRun(new CouponImportDryRunRequestDto(
                campaign.getId(),
                "code\nSAVE10\n",
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                "import-1"), admin, "corr-import"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("different payload")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.IDEMPOTENCY_KEY_REUSED));

        verify(importBatches, never()).save(any());
    }

    @Test
    void rateLimitedDryRunStopsBeforeIdempotencyLookupOrWrites() {
        service = new CouponImportDryRunService(
                campaigns,
                coupons,
                importBatches,
                importRows,
                idempotencyKeys,
                auditEvents,
                access,
                fingerprints,
                blockingGuard(),
                metrics,
                objectMapper,
                true,
                30);
        CurrentUser admin = admin();
        IncentiveCampaign campaign = campaign();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        assertThatThrownBy(() -> service.dryRun(new CouponImportDryRunRequestDto(
                campaign.getId(),
                "code\nSAVE10\n",
                100,
                null,
                null,
                null,
                null,
                null,
                Map.of(),
                "import-1"), admin, "corr-import"))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED));

        verify(idempotencyKeys, never()).insertInProgressIfAbsent(any(), any(), any(), any(), any(), any(), any());
        verify(idempotencyKeys, never()).lockByScope(any(), any(), any(), any());
        verify(coupons, never()).findByCampaignIdAndNormalizedCodeIn(any(), any());
        verify(importBatches, never()).save(any());
        verify(importRows, never()).saveAll(any());
        verify(auditEvents, never()).save(any());
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
