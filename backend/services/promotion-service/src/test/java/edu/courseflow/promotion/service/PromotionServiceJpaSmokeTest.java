package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionTransitionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CommitReservationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportCommitResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.CouponImportDryRunRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateCampaignRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReserveIncentiveResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReverseRedemptionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RuleSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.model.IncentiveReservation;
import edu.courseflow.promotion.repository.IncentiveLedgerEntryRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.function.IntFunction;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest(properties = {
        "courseflow.promotion.reservation-expiry.enabled=false",
        "eureka.client.enabled=false"
})
@Testcontainers(disabledWithoutDocker = true)
class PromotionServiceJpaSmokeTest {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("cf_promotion")
            .withUsername("courseflow")
            .withPassword("courseflow");

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.liquibase.contexts", () -> "prod");
        registry.add("courseflow.security.internal-jwt.secret",
                () -> "test-internal-jwt-secret-32-byte-value-001");
    }

    @Autowired
    PromotionService promotions;

    @Autowired
    CampaignVersionService campaignVersions;

    @Autowired
    IncentiveReconciliationService reconciliation;

    @Autowired
    IncentiveReservationRepository reservations;

    @Autowired
    IncentiveLedgerEntryRepository ledgerEntries;

    @Autowired
    OutboxEventRepository outboxEvents;

    @Autowired
    CouponCodeFingerprintService couponFingerprints;

    @Autowired
    CouponImportDryRunService couponImportDryRuns;

    @Autowired
    CouponImportApprovalService couponImportApprovals;

    @Autowired
    CouponImportCommitService couponImportCommits;

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    PlatformTransactionManager txManager;

    private final CurrentUser admin = new CurrentUser(
            1L, "admin@example.com", "ADMIN", Set.of("ADMIN"), Set.of(), fakeInternalToken("api-gateway", "user"));
    private final CurrentUser reviewer = new CurrentUser(
            2L, "reviewer@example.com", "ADMIN", Set.of("ADMIN"), Set.of(), fakeInternalToken("api-gateway", "user"));
    private final CurrentUser runtimeService = new CurrentUser(
            null, null, null, Set.of(), Set.of(), fakeInternalToken(
            "checkout-service",
            "service",
            "internal:promotion:evaluate",
            "internal:promotion:reserve",
            "internal:promotion:commit",
            "internal:promotion:cancel",
            "internal:promotion:reverse"));

    @Test
    void duplicateCommitDoesNotCreateDuplicateLedgerOrOutboxEvents() {
        String suffix = UUID.randomUUID().toString();
        publishCampaign("COMMIT-" + suffix, 1);

        var reserve = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-" + suffix,
                request("profile-commit", "cart-" + suffix)), runtimeService);
        assertThat(reserve.reserved()).isTrue();

        var reserveReplay = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-" + suffix,
                request("profile-commit", "cart-" + suffix)), runtimeService);
        assertThat(reserveReplay.idempotencyReplay()).isTrue();
        assertThat(reserveReplay.reservationId()).isEqualTo(reserve.reservationId());

        var firstCommit = promotions.commit(reserve.reservationId(),
                new CommitReservationRequestDto("commit-1-" + suffix, "order-" + suffix), runtimeService);
        var secondCommit = promotions.commit(reserve.reservationId(),
                new CommitReservationRequestDto("commit-2-" + suffix, "order-" + suffix), runtimeService);

        assertThat(firstCommit.committed()).isTrue();
        assertThat(secondCommit.committed()).isTrue();
        assertThat(secondCommit.redemptionId()).isEqualTo(firstCommit.redemptionId());
        assertThat(secondCommit.reasonCodes()).containsExactly("ALREADY_COMMITTED");
        assertThat(ledgerEntries.countByReservationIdAndEntryType(reserve.reservationId(), "COMMIT")).isEqualTo(1);
        assertThat(outboxEvents.countByAggregateIdAndEventType(
                firstCommit.redemptionId().toString(), "incentive.redemption.committed")).isEqualTo(1);
    }

    @Test
    void reconciliationQueryReadsCommittedLedgerEffectsAndOutboxState() {
        String suffix = UUID.randomUUID().toString();
        publishCampaign("RECON-" + suffix, 1);

        var reserve = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-recon-" + suffix,
                request("profile-recon", "cart-recon-" + suffix)), runtimeService);
        var commit = promotions.commit(reserve.reservationId(),
                new CommitReservationRequestDto("commit-recon-" + suffix, "order-recon-" + suffix), runtimeService);

        var response = reconciliation.query(
                java.util.Optional.of("courseflow"),
                java.util.Optional.of("lms"),
                java.util.Optional.of("profile-recon"),
                java.util.Optional.of("order-recon-" + suffix),
                java.util.Optional.empty(),
                java.util.Optional.empty(),
                java.util.Optional.of(commit.redemptionId()),
                java.util.Optional.empty(),
                java.util.Optional.of("COMMIT"),
                java.util.Optional.empty(),
                java.util.Optional.empty(),
                java.util.Optional.of(25),
                admin);

        assertThat(response.items()).hasSize(1);
        var item = response.items().getFirst();
        assertThat(item.reconciliationStatus()).isEqualTo("MATCHED");
        assertThat(item.direction()).isEqualTo("APPLY");
        assertThat(item.quotaPolicy()).isEqualTo("NO_QUOTA_CHANGE");
        assertThat(item.redemptionId()).isEqualTo(commit.redemptionId());
        assertThat(item.reservationId()).isEqualTo(reserve.reservationId());
        assertThat(item.externalReference()).isEqualTo("order-recon-" + suffix);
        assertThat(item.outboxStatus()).isEqualTo("PENDING");
        assertThat(item.outboxEventType()).isEqualTo("incentive.redemption.committed");
        assertThat(item.effect()).isNotNull();
        assertThat(item.effect().currency()).isEqualTo("USD");
        assertThat(item.effect().effectId()).contains(item.campaignId().toString());
    }

    @Test
    void expiredReservationReleasesQuotaAndAllowsFutureEvaluation() {
        String suffix = UUID.randomUUID().toString();
        CampaignDto campaign = publishCampaign("EXPIRE-" + suffix, 1);

        var reserve = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-expire-" + suffix,
                request("profile-expire", "cart-expire-" + suffix)), runtimeService);
        assertThat(reserve.reserved()).isTrue();
        assertThat(promotions.evaluate(request("profile-other", "cart-blocked-" + suffix), runtimeService).eligible()).isFalse();

        jdbc.update("update incentive_reservations set expires_at = ? where id = ?",
                java.sql.Timestamp.from(Instant.now().minusSeconds(5)),
                reserve.reservationId());

        assertThat(promotions.expireReservedReservations(10)).isGreaterThanOrEqualTo(1);

        assertThat(reservations.findById(reserve.reservationId()).orElseThrow().getStatus()).isEqualTo("EXPIRED");
        assertThat(ledgerEntries.countByReservationIdAndEntryType(reserve.reservationId(), "EXPIRE")).isEqualTo(1);
        assertThat(jdbc.queryForObject("""
                        select coalesce(sum(used_count), 0)
                        from incentive_quota_counters
                        where scope_id = ?
                        """,
                Integer.class,
                campaign.id().toString())).isZero();
        assertThat(promotions.evaluate(request("profile-after-expire", "cart-after-" + suffix), runtimeService).eligible()).isTrue();
    }

    @Test
    void reservationExpiryBatchSizeDrainsExpiredRowsWithoutDuplicateExpireLedger() {
        String suffix = UUID.randomUUID().toString();
        publishCampaign("EXPIRE-BATCH-" + suffix, 2);

        var first = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-expire-batch-1-" + suffix,
                request("profile-expire-batch-1", "cart-expire-batch-1-" + suffix)), runtimeService);
        var second = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-expire-batch-2-" + suffix,
                request("profile-expire-batch-2", "cart-expire-batch-2-" + suffix)), runtimeService);
        assertThat(first.reserved()).isTrue();
        assertThat(second.reserved()).isTrue();

        expireRows(first.reservationId(), second.reservationId());

        assertThat(promotions.expireReservedReservations(1)).isEqualTo(1);
        assertThat(promotions.expireReservedReservations(1)).isEqualTo(1);
        assertThat(promotions.expireReservedReservations(1)).isZero();

        assertThat(reservations.findById(first.reservationId()).orElseThrow().getStatus()).isEqualTo("EXPIRED");
        assertThat(reservations.findById(second.reservationId()).orElseThrow().getStatus()).isEqualTo("EXPIRED");
        assertThat(ledgerEntries.countByReservationIdAndEntryType(first.reservationId(), "EXPIRE")).isEqualTo(1);
        assertThat(ledgerEntries.countByReservationIdAndEntryType(second.reservationId(), "EXPIRE")).isEqualTo(1);
    }

    @Test
    void expiryClaimSkipsRowsLockedByAnotherTransaction() {
        String suffix = UUID.randomUUID().toString();
        publishCampaign("EXPIRE-SKIP-" + suffix, 2);

        var locked = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-skip-locked-" + suffix,
                request("profile-skip-locked", "cart-skip-locked-" + suffix)), runtimeService);
        var available = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-skip-available-" + suffix,
                request("profile-skip-available", "cart-skip-available-" + suffix)), runtimeService);
        expireRows(locked.reservationId(), available.reservationId());

        TransactionTemplate outer = new TransactionTemplate(txManager);
        outer.executeWithoutResult(status -> {
            reservations.lockById(locked.reservationId()).orElseThrow();

            TransactionTemplate contender = new TransactionTemplate(txManager);
            contender.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
            List<IncentiveReservation> claimed = contender.execute(inner ->
                    reservations.lockExpiredReservedForExpiry(Instant.now(), 10));

            assertThat(claimed).isNotNull();
            assertThat(claimed).extracting(IncentiveReservation::getId)
                    .containsExactly(available.reservationId());
        });
    }

    @Test
    void concurrentReserveDoesNotOversellCampaignQuota() throws Exception {
        String suffix = UUID.randomUUID().toString();
        String applicationId = "lms-hot-campaign-" + suffix.substring(0, 8);
        CampaignDto campaign = publishCampaign("HOT-CAMPAIGN-" + suffix, 1, null, applicationId);

        List<ReserveIncentiveResponseDto> responses = runConcurrentReserves(12, attempt -> new ReserveIncentiveRequestDto(
                "reserve-hot-campaign-" + suffix + "-" + attempt,
                request(
                        "profile-hot-campaign-" + suffix + "-" + attempt,
                        "cart-hot-campaign-" + suffix + "-" + attempt,
                        applicationId)));

        assertThat(responses).filteredOn(response -> response.reserved()).hasSize(1);
        assertThat(responses).filteredOn(response -> !response.reserved())
                .allSatisfy(response -> assertThat(response.reasonCodes()).contains("QUOTA_EXHAUSTED"));
        assertReservationEvidence(campaign.id(), applicationId, "CAMPAIGN", campaign.id().toString(), "*", 1);
    }

    @Test
    void concurrentReserveDoesNotOversellCampaignPerProfileCap() throws Exception {
        String suffix = UUID.randomUUID().toString();
        String applicationId = "lms-hot-profile-" + suffix.substring(0, 8);
        String profileId = "profile-hot-profile-" + suffix;
        CampaignDto campaign = publishCampaign("HOT-PROFILE-" + suffix, 20, 1, applicationId);

        List<ReserveIncentiveResponseDto> responses = runConcurrentReserves(10, attempt -> new ReserveIncentiveRequestDto(
                "reserve-hot-profile-" + suffix + "-" + attempt,
                request(
                        profileId,
                        "cart-hot-profile-" + suffix + "-" + attempt,
                        applicationId)));

        assertThat(responses).filteredOn(response -> response.reserved()).hasSize(1);
        assertThat(responses).filteredOn(response -> !response.reserved())
                .allSatisfy(response -> assertThat(response.reasonCodes()).contains("QUOTA_EXHAUSTED"));
        assertReservationEvidence(campaign.id(), applicationId, "CAMPAIGN_PROFILE", campaign.id().toString(), profileId, 1);
        assertQuotaCounter(applicationId, "CAMPAIGN", campaign.id().toString(), "*", 1, 20);
    }

    @Test
    void concurrentReserveDoesNotOversellCouponQuota() throws Exception {
        String suffix = UUID.randomUUID().toString();
        String applicationId = "lms-hot-coupon-" + suffix.substring(0, 8);
        CampaignDto campaign = publishCampaign("HOT-COUPON-" + suffix, 20, null, applicationId, true);
        String couponCode = "HOT-COUPON-" + suffix.substring(0, 8);
        UUID couponId = insertRuntimeCoupon(campaign.id(), couponCode, 1, null);

        List<ReserveIncentiveResponseDto> responses = runConcurrentReserves(10, attempt -> new ReserveIncentiveRequestDto(
                "reserve-hot-coupon-" + suffix + "-" + attempt,
                request(
                        "profile-hot-coupon-" + suffix + "-" + attempt,
                        "cart-hot-coupon-" + suffix + "-" + attempt,
                        applicationId,
                        List.of(couponCode))));

        assertThat(responses).filteredOn(response -> response.reserved()).hasSize(1);
        assertThat(responses).filteredOn(response -> !response.reserved())
                .allSatisfy(response -> assertThat(response.reasonCodes()).contains("QUOTA_EXHAUSTED"));
        assertReservationEvidence(campaign.id(), applicationId, "COUPON", couponId.toString(), "*", 1);
        assertQuotaCounter(applicationId, "CAMPAIGN", campaign.id().toString(), "*", 1, 20);
    }

    @Test
    void concurrentReserveDoesNotOversellCouponPerProfileCap() throws Exception {
        String suffix = UUID.randomUUID().toString();
        String applicationId = "lms-hot-coupon-profile-" + suffix.substring(0, 8);
        String profileId = "profile-hot-coupon-profile-" + suffix;
        CampaignDto campaign = publishCampaign("HOT-COUPON-PROFILE-" + suffix, 20, null, applicationId, true);
        String couponCode = "HOT-CP-" + suffix.substring(0, 8);
        UUID couponId = insertRuntimeCoupon(campaign.id(), couponCode, 20, 1);

        List<ReserveIncentiveResponseDto> responses = runConcurrentReserves(10, attempt -> new ReserveIncentiveRequestDto(
                "reserve-hot-coupon-profile-" + suffix + "-" + attempt,
                request(
                        profileId,
                        "cart-hot-coupon-profile-" + suffix + "-" + attempt,
                        applicationId,
                        List.of(couponCode))));

        assertThat(responses).filteredOn(response -> response.reserved()).hasSize(1);
        assertThat(responses).filteredOn(response -> !response.reserved())
                .allSatisfy(response -> assertThat(response.reasonCodes()).contains("QUOTA_EXHAUSTED"));
        assertReservationEvidence(campaign.id(), applicationId, "COUPON_PROFILE", couponId.toString(), profileId, 1);
        assertQuotaCounter(applicationId, "CAMPAIGN", campaign.id().toString(), "*", 1, 20);
        assertQuotaCounter(applicationId, "COUPON", couponId.toString(), "*", 1, 20);
    }

    @Test
    void concurrentCouponImportCommitReplaysWithoutDuplicateCouponsOrOperations() throws Exception {
        String suffix = UUID.randomUUID().toString();
        String applicationId = "lms-import-" + suffix.substring(0, 8);
        CampaignDto campaign = publishCampaign("IMPORT-COMMIT-" + suffix, 20, null, applicationId, true);
        String csv = "code\nJPA-" + suffix.substring(0, 12) + "\n";
        String idempotencyKey = "coupon-import-commit-" + suffix;

        var dryRun = couponImportDryRuns.dryRun(
                couponDryRunRequest(campaign.id(), csv),
                admin,
                "corr-import-dry-" + suffix);
        assertThat(dryRun.commitReady()).isTrue();

        var approvalRequest = couponCommitRequest(
                null,
                dryRun.dryRunId(),
                campaign.id(),
                csv,
                dryRun.resultHash(),
                idempotencyKey);
        var approval = couponImportApprovals.requestApproval(
                dryRun.dryRunId(),
                approvalRequest,
                admin,
                "corr-import-approval-request-" + suffix);
        couponImportApprovals.approve(
                approval.approvalId(),
                new CouponImportApprovalDecisionRequestDto("approved"),
                reviewer,
                "corr-import-approval-decision-" + suffix);

        var commitRequest = couponCommitRequest(
                approval.approvalId(),
                dryRun.dryRunId(),
                campaign.id(),
                csv,
                dryRun.resultHash(),
                idempotencyKey);
        List<CouponImportCommitResponseDto> responses = runConcurrentCouponImportCommits(
                2,
                commitRequest,
                "corr-import-commit-" + suffix);

        assertThat(responses).hasSize(2);
        assertThat(responses).allSatisfy(response -> {
            assertThat(response.status()).isEqualTo("SUCCEEDED");
            assertThat(response.approvalId()).isEqualTo(approval.approvalId());
            assertThat(response.dryRunId()).isEqualTo(dryRun.dryRunId());
            assertThat(response.campaignId()).isEqualTo(campaign.id());
            assertThat(response.resultHash()).isEqualTo(dryRun.resultHash());
            assertThat(response.requestedRows()).isEqualTo(1);
            assertThat(response.importedRows()).isEqualTo(1);
        });
        UUID importId = responses.getFirst().importId();
        assertThat(responses).extracting(CouponImportCommitResponseDto::importId).containsOnly(importId);
        assertThat(responses.stream().filter(CouponImportCommitResponseDto::idempotencyReplay).count()).isEqualTo(1);
        assertThat(responses.stream().filter(response -> !response.idempotencyReplay()).count()).isEqualTo(1);

        assertCouponImportCommittedOnce(
                dryRun.dryRunId(),
                approval.approvalId(),
                campaign.id(),
                applicationId,
                importId);

        jdbc.update("""
                        update incentive_idempotency_keys
                        set status = 'IN_PROGRESS',
                            response_json = '{}'::jsonb
                        where tenant_id = 'courseflow'
                          and application_id = ?
                          and operation = 'COUPON_IMPORT_COMMIT'
                          and idempotency_key = ?
                        """,
                applicationId,
                idempotencyKey);

        var healedReplay = couponImportCommits.commit(
                commitRequest,
                admin,
                "corr-import-commit-heal-" + suffix);
        assertThat(healedReplay.idempotencyReplay()).isTrue();
        assertThat(healedReplay.importId()).isEqualTo(importId);
        assertCouponImportCommittedOnce(
                dryRun.dryRunId(),
                approval.approvalId(),
                campaign.id(),
                applicationId,
                importId);
    }

    @Test
    void concurrentCouponImportCommitWithDifferentIdempotencyKeysImportsOnceAndRejectsSecondSubmit()
            throws Exception {
        String suffix = UUID.randomUUID().toString();
        String applicationId = "lms-import-diff-" + suffix.substring(0, 8);
        CampaignDto campaign = publishCampaign("IMPORT-DIFF-" + suffix, 20, null, applicationId, true);
        String csv = "code\nJPA-DIFF-" + suffix.substring(0, 10) + "\n";

        var dryRun = couponImportDryRuns.dryRun(
                couponDryRunRequest(campaign.id(), csv),
                admin,
                "corr-import-diff-dry-" + suffix);
        assertThat(dryRun.commitReady()).isTrue();

        var approvalRequest = couponCommitRequest(
                null,
                dryRun.dryRunId(),
                campaign.id(),
                csv,
                dryRun.resultHash(),
                "coupon-import-commit-request-" + suffix);
        var approval = couponImportApprovals.requestApproval(
                dryRun.dryRunId(),
                approvalRequest,
                admin,
                "corr-import-diff-approval-request-" + suffix);
        couponImportApprovals.approve(
                approval.approvalId(),
                new CouponImportApprovalDecisionRequestDto("approved"),
                reviewer,
                "corr-import-diff-approval-decision-" + suffix);

        List<CouponImportCommitAttempt> attempts = runConcurrentCouponImportCommitAttempts(
                2,
                attempt -> couponCommitRequest(
                        approval.approvalId(),
                        dryRun.dryRunId(),
                        campaign.id(),
                        csv,
                        dryRun.resultHash(),
                        "coupon-import-commit-diff-" + suffix + "-" + attempt),
                "corr-import-diff-commit-" + suffix);

        List<CouponImportCommitResponseDto> successes = attempts.stream()
                .map(CouponImportCommitAttempt::response)
                .filter(response -> response != null)
                .toList();
        List<Throwable> failures = attempts.stream()
                .map(CouponImportCommitAttempt::failure)
                .filter(failure -> failure != null)
                .toList();

        assertThat(successes).hasSize(1);
        CouponImportCommitResponseDto success = successes.getFirst();
        assertThat(success.status()).isEqualTo("SUCCEEDED");
        assertThat(success.idempotencyReplay()).isFalse();
        assertThat(success.approvalId()).isEqualTo(approval.approvalId());
        assertThat(success.dryRunId()).isEqualTo(dryRun.dryRunId());
        assertThat(success.campaignId()).isEqualTo(campaign.id());
        assertThat(success.requestedRows()).isEqualTo(1);
        assertThat(success.importedRows()).isEqualTo(1);
        assertThat(failures).hasSize(1);
        assertThat(failures.getFirst())
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("already been committed");

        assertCouponImportCommittedOnce(
                dryRun.dryRunId(),
                approval.approvalId(),
                campaign.id(),
                applicationId,
                success.importId());
    }

    @Test
    void retentionRedactionCteSkipsLockedRowsAndOnlyTouchesLegacyTerminalSnapshots() {
        String suffix = UUID.randomUUID().toString();
        publishCampaign("REDACT-SKIP-" + suffix, 4);
        Instant cutoff = Instant.now().minusSeconds(30L * 24 * 60 * 60);
        Instant oldTerminal = cutoff.minusSeconds(60);
        Instant recentTerminal = cutoff.plusSeconds(60);

        var locked = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-redact-locked-" + suffix,
                request("profile-redact-locked", "cart-redact-locked-" + suffix)), runtimeService);
        var available = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-redact-available-" + suffix,
                request("profile-redact-available", "cart-redact-available-" + suffix)), runtimeService);
        var minimized = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-redact-minimized-" + suffix,
                request("profile-redact-minimized", "cart-redact-minimized-" + suffix)), runtimeService);
        var recent = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-redact-recent-" + suffix,
                request("profile-redact-recent", "cart-redact-recent-" + suffix)), runtimeService);

        markTerminalSnapshot(locked.reservationId(), "EXPIRED", oldTerminal,
                "{\"profileId\":\"raw-locked\",\"couponFingerprint\":\"raw-fp\"}");
        markTerminalSnapshot(available.reservationId(), "CANCELLED", oldTerminal,
                "{\"profileId\":\"raw-available\",\"externalReference\":\"raw-ext\"}");
        markTerminalSnapshot(minimized.reservationId(), "EXPIRED", oldTerminal,
                "{\"requestSnapshotMinimized\":true,\"snapshotVersion\":\"reservation-request-snapshot.v2\"}");
        markTerminalSnapshot(recent.reservationId(), "EXPIRED", recentTerminal,
                "{\"profileId\":\"raw-recent\"}");

        String redactedSnapshot = """
                {"retentionRedacted":true,"requestSnapshotMinimized":true,"rawSnapshotRemoved":true}
                """;
        TransactionTemplate outer = new TransactionTemplate(txManager);
        outer.executeWithoutResult(status -> {
            jdbc.queryForObject(
                    "select id from incentive_reservations where id = ? for update",
                    UUID.class,
                    locked.reservationId());

            TransactionTemplate contender = new TransactionTemplate(txManager);
            contender.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
            Integer redacted = contender.execute(inner -> reservations.redactTerminalRequestSnapshots(
                    "courseflow",
                    "lms",
                    cutoff,
                    10,
                    redactedSnapshot));

            assertThat(redacted).isEqualTo(1);
            assertThat(requestJson(available.reservationId()))
                    .contains("\"retentionRedacted\": true")
                    .doesNotContain("raw-available")
                    .doesNotContain("raw-ext");
            assertThat(requestJson(locked.reservationId())).contains("raw-locked");
        });

        TransactionTemplate afterLockReleased = new TransactionTemplate(txManager);
        Integer redactedAfterLockReleased = afterLockReleased.execute(status -> reservations.redactTerminalRequestSnapshots(
                "courseflow",
                "lms",
                cutoff,
                10,
                redactedSnapshot));
        assertThat(redactedAfterLockReleased).isEqualTo(1);
        assertThat(requestJson(locked.reservationId()))
                .contains("\"retentionRedacted\": true")
                .doesNotContain("raw-locked")
                .doesNotContain("raw-fp");
        assertThat(requestJson(minimized.reservationId()))
                .contains("\"requestSnapshotMinimized\": true")
                .doesNotContain("retentionRedacted");
        assertThat(requestJson(recent.reservationId())).contains("raw-recent");
    }

    @Test
    void reverseRedemptionIsIdempotentAndDoesNotReleaseCommittedQuota() {
        String suffix = UUID.randomUUID().toString();
        publishCampaign("REVERSE-" + suffix, 1);

        var reserve = promotions.reserve(new ReserveIncentiveRequestDto(
                "reserve-reverse-" + suffix,
                request("profile-reverse", "cart-reverse-" + suffix)), runtimeService);
        assertThat(reserve.reserved()).isTrue();

        var commit = promotions.commit(reserve.reservationId(),
                new CommitReservationRequestDto("commit-reverse-" + suffix, "order-reverse-" + suffix), runtimeService);
        assertThat(commit.committed()).isTrue();

        var firstReverse = promotions.reverse(commit.redemptionId(),
                new ReverseRedemptionRequestDto("reverse-" + suffix, "source refund"), runtimeService);
        var replayReverse = promotions.reverse(commit.redemptionId(),
                new ReverseRedemptionRequestDto("reverse-" + suffix, "source refund"), runtimeService);

        assertThat(firstReverse.reversed()).isTrue();
        assertThat(replayReverse.idempotencyReplay()).isTrue();
        assertThat(ledgerEntries.countByReservationIdAndEntryType(reserve.reservationId(), "REVERSE")).isEqualTo(1);
        assertThat(outboxEvents.countByAggregateIdAndEventType(
                commit.redemptionId().toString(), "incentive.redemption.reversed")).isEqualTo(1);
        assertThat(promotions.evaluate(request("profile-after-reverse", "cart-after-reverse-" + suffix), runtimeService)
                .eligible()).isFalse();
    }

    @Test
    void couponStorageInventoryClassifiesStorageFormatsAndActiveOnlyRows() {
        ensureApplication();
        String suffix = UUID.randomUUID().toString();
        UUID campaignId = UUID.randomUUID();
        jdbc.update("""
                insert into incentive_campaigns (
                    id, tenant_id, application_id, code, name, incentive_type, status,
                    starts_at, ends_at, priority, exclusive, stackable, coupon_required, match_policy,
                    currency, rules_json, actions_json, created_by, created_at, updated_at, version
                ) values (?, 'courseflow', 'lms', ?, 'Inventory Smoke', 'PROMOTION', 'PUBLISHED',
                    now() - interval '1 minute', now() + interval '1 hour', 0, false, true, true, 'ALL',
                    'USD', '[]'::jsonb, '[]'::jsonb, 'test', now(), now(), 0)
                """, campaignId, "INV-" + suffix);
        insertCoupon(campaignId, "current", "hmac-sha256:local:" + "a".repeat(64), "ACTIVE");
        insertCoupon(campaignId, "previous", "hmac-sha256:old:" + "b".repeat(64), "ACTIVE");
        insertCoupon(campaignId, "legacy-sha", "c".repeat(64), "ACTIVE");
        insertCoupon(campaignId, "legacy-raw", "SAVE10", "ACTIVE");
        insertCoupon(campaignId, "malformed-hmac", "hmac-sha256:old:bad", "ACTIVE");
        insertCoupon(campaignId, "malformed-blank", "", "ACTIVE");
        insertCoupon(campaignId, "paused-legacy", "PAUSED10", "PAUSED");

        var activeOnly = promotions.couponStorageInventory(
                java.util.Optional.of("courseflow"),
                java.util.Optional.of("lms"),
                java.util.Optional.of(campaignId),
                java.util.Optional.empty(),
                admin);

        assertThat(activeOnly.totalCoupons()).isEqualTo(6);
        assertThat(activeOnly.legacyCoupons()).isEqualTo(2);
        assertThat(activeOnly.malformedCoupons()).isEqualTo(2);
        assertThat(activeOnly.fallbackDisableReady()).isFalse();
        assertThat(activeOnly.items())
                .extracting(item -> item.storageFormat() + "=" + item.count())
                .containsExactly(
                        "current_hmac=1",
                        "previous_hmac=1",
                        "legacy_sha=1",
                        "legacy_raw=1",
                        "malformed=2");

        var allRows = promotions.couponStorageInventory(
                java.util.Optional.of("courseflow"),
                java.util.Optional.of("lms"),
                java.util.Optional.of(campaignId),
                java.util.Optional.of(false),
                admin);

        assertThat(allRows.totalCoupons()).isEqualTo(7);
        assertThat(allRows.legacyCoupons()).isEqualTo(3);
    }

    private List<ReserveIncentiveResponseDto> runConcurrentReserves(
            int attempts,
            IntFunction<ReserveIncentiveRequestDto> requestFactory) throws Exception {
        ExecutorService executor = Executors.newFixedThreadPool(attempts);
        CountDownLatch ready = new CountDownLatch(attempts);
        CountDownLatch start = new CountDownLatch(1);
        try {
            List<Future<ReserveIncentiveResponseDto>> futures = IntStream.range(0, attempts)
                    .mapToObj(attempt -> executor.submit(() -> {
                        ready.countDown();
                        if (!start.await(10, TimeUnit.SECONDS)) {
                            throw new IllegalStateException("Timed out waiting for concurrent reserve start");
                        }
                        return promotions.reserve(requestFactory.apply(attempt), runtimeService);
                    }))
                    .toList();

            assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
            start.countDown();

            return futures.stream()
                    .map(future -> {
                        try {
                            return future.get(30, TimeUnit.SECONDS);
                        } catch (Exception ex) {
                            throw new IllegalStateException("Concurrent reserve attempt failed", ex);
                        }
                    })
                    .toList();
        } finally {
            executor.shutdownNow();
            assertThat(executor.awaitTermination(10, TimeUnit.SECONDS)).isTrue();
        }
    }

    private List<CouponImportCommitResponseDto> runConcurrentCouponImportCommits(
            int attempts,
            CouponImportCommitRequestDto request,
            String correlationPrefix) throws Exception {
        return runConcurrentCouponImportCommitAttempts(
                attempts,
                ignored -> request,
                correlationPrefix).stream()
                .map(attempt -> {
                    if (attempt.failure() != null) {
                        throw new IllegalStateException("Concurrent coupon import commit failed", attempt.failure());
                    }
                    return attempt.response();
                })
                .toList();
    }

    private List<CouponImportCommitAttempt> runConcurrentCouponImportCommitAttempts(
            int attempts,
            IntFunction<CouponImportCommitRequestDto> requestFactory,
            String correlationPrefix) throws Exception {
        ExecutorService executor = Executors.newFixedThreadPool(attempts);
        CountDownLatch ready = new CountDownLatch(attempts);
        CountDownLatch start = new CountDownLatch(1);
        try {
            List<Future<CouponImportCommitAttempt>> futures = IntStream.range(0, attempts)
                    .mapToObj(attempt -> executor.submit(() -> {
                        ready.countDown();
                        if (!start.await(10, TimeUnit.SECONDS)) {
                            throw new IllegalStateException("Timed out waiting for concurrent coupon import commit");
                        }
                        try {
                            return new CouponImportCommitAttempt(
                                    couponImportCommits.commit(
                                            requestFactory.apply(attempt),
                                            admin,
                                            correlationPrefix + "-" + attempt),
                                    null);
                        } catch (Throwable failure) {
                            return new CouponImportCommitAttempt(null, failure);
                        }
                    }))
                    .toList();

            assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
            start.countDown();

            return futures.stream()
                    .map(future -> {
                        try {
                            return future.get(30, TimeUnit.SECONDS);
                        } catch (Exception ex) {
                            throw new IllegalStateException("Concurrent coupon import commit failed", ex);
                        }
                    })
                    .toList();
        } finally {
            executor.shutdownNow();
            assertThat(executor.awaitTermination(10, TimeUnit.SECONDS)).isTrue();
        }
    }

    private void assertCouponImportCommittedOnce(UUID dryRunId,
                                                 UUID approvalId,
                                                 UUID campaignId,
                                                 String applicationId,
                                                 UUID importId) {
        assertThat(jdbc.queryForObject("""
                        select count(*)
                        from incentive_coupon_import_operations
                        where dry_run_id = ?
                        """,
                Long.class,
                dryRunId)).isEqualTo(1L);
        assertThat(jdbc.queryForObject("""
                        select count(*)
                        from incentive_coupon_import_operations
                        where approval_id = ?
                        """,
                Long.class,
                approvalId)).isEqualTo(1L);
        assertThat(jdbc.queryForObject("""
                        select count(*)
                        from incentive_coupons
                        where campaign_id = ?
                        """,
                Long.class,
                campaignId)).isEqualTo(1L);

        Map<String, Object> batch = jdbc.queryForMap("""
                        select committed_operation_id, committed_rows, committed_by, committed_at, expires_at
                        from incentive_coupon_import_batches
                        where id = ?
                        """,
                dryRunId);
        assertThat(batch.get("committed_operation_id")).isEqualTo(importId);
        assertThat(batch.get("committed_rows")).isEqualTo(1);
        assertThat(batch.get("committed_by")).isEqualTo("1");
        assertThat(batch.get("committed_at")).isNotNull();
        assertThat(batch.get("expires_at")).isNull();

        Map<String, Object> approvalRow = jdbc.queryForMap("""
                        select status, executed_by, executed_at
                        from incentive_operation_approvals
                        where id = ?
                        """,
                approvalId);
        assertThat(approvalRow.get("status")).isEqualTo("EXECUTED");
        assertThat(approvalRow.get("executed_by")).isEqualTo("1");
        assertThat(approvalRow.get("executed_at")).isNotNull();

        assertThat(jdbc.queryForObject("""
                        select count(*)
                        from incentive_idempotency_keys
                        where tenant_id = 'courseflow'
                          and application_id = ?
                          and operation = 'COUPON_IMPORT_COMMIT'
                        """,
                Long.class,
                applicationId)).isEqualTo(1L);
        Map<String, Object> idempotency = jdbc.queryForMap("""
                        select status, response_json::text as response_json
                        from incentive_idempotency_keys
                        where tenant_id = 'courseflow'
                          and application_id = ?
                          and operation = 'COUPON_IMPORT_COMMIT'
                        """,
                applicationId);
        assertThat(idempotency.get("status")).isEqualTo("SUCCEEDED");
        assertThat((String) idempotency.get("response_json")).contains(importId.toString());
    }

    private void assertReservationEvidence(UUID campaignId, String applicationId, String scopeType, String scopeId,
                                           String profileId, int expectedReserved) {
        assertThat(jdbc.queryForObject("""
                        select count(*)
                        from incentive_reservations
                        where tenant_id = 'courseflow'
                          and application_id = ?
                          and campaign_id = ?
                          and status = 'RESERVED'
                        """,
                Long.class,
                applicationId,
                campaignId)).isEqualTo((long) expectedReserved);
        assertThat(jdbc.queryForObject("""
                        select count(*)
                        from incentive_ledger_entries
                        where tenant_id = 'courseflow'
                          and application_id = ?
                          and campaign_id = ?
                          and entry_type = 'RESERVE'
                        """,
                Long.class,
                applicationId,
                campaignId)).isEqualTo((long) expectedReserved);
        assertQuotaCounter(applicationId, scopeType, scopeId, profileId, expectedReserved, expectedReserved);
        assertNoQuotaInvariantViolations(applicationId);
    }

    private void assertQuotaCounter(String applicationId, String scopeType, String scopeId, String profileId,
                                    int expectedUsed, int expectedLimit) {
        String counter = jdbc.queryForObject("""
                        select used_count || '|' || limit_count
                        from incentive_quota_counters
                        where tenant_id = 'courseflow'
                          and application_id = ?
                          and scope_type = ?
                          and scope_id = ?
                          and profile_id = ?
                        """,
                String.class,
                applicationId,
                scopeType,
                scopeId,
                profileId);
        assertThat(counter).isEqualTo(expectedUsed + "|" + expectedLimit);
        assertNoQuotaInvariantViolations(applicationId);
    }

    private void assertNoQuotaInvariantViolations(String applicationId) {
        assertThat(jdbc.queryForObject("""
                        select count(*)
                        from incentive_quota_counters
                        where tenant_id = 'courseflow'
                          and application_id = ?
                          and (used_count < 0 or used_count > limit_count)
                        """,
                Long.class,
                applicationId)).isZero();
    }

    private CampaignDto publishCampaign(String code, Integer maxRedemptions) {
        return publishCampaign(code, maxRedemptions, null, "lms");
    }

    private CampaignDto publishCampaign(String code, Integer maxRedemptions, Integer maxRedemptionsPerProfile,
                                        String applicationId) {
        return publishCampaign(code, maxRedemptions, maxRedemptionsPerProfile, applicationId, false);
    }

    private CampaignDto publishCampaign(String code, Integer maxRedemptions, Integer maxRedemptionsPerProfile,
                                        String applicationId, boolean couponRequired) {
        ensureApplication(applicationId);
        var campaign = promotions.createCampaign(new CreateCampaignRequestDto(
                "courseflow",
                applicationId,
                code,
                "Test " + code,
                null,
                "PROMOTION",
                Instant.now().minusSeconds(60),
                Instant.now().plusSeconds(3600),
                100,
                false,
                true,
                couponRequired,
                "ALL",
                "USD",
                List.of(new RuleSpecDto("MIN_ORDER_AMOUNT", 1, Map.of("amount", 100, "currency", "USD"))),
                List.of(new ActionSpecDto("ORDER_FIXED_OFF", 1, Map.of("amount", 10))),
                maxRedemptions,
                maxRedemptionsPerProfile),
                admin);
        int version = campaign.draftVersion();
        campaignVersions.submit(campaign.id(), version, new CampaignVersionTransitionRequestDto("ready"), admin);
        campaignVersions.approve(campaign.id(), version, new CampaignVersionTransitionRequestDto("approved"), reviewer);
        campaignVersions.publish(campaign.id(), version, new CampaignVersionTransitionRequestDto("publish"), admin);
        return promotions.campaignDetail(campaign.id(), admin);
    }

    private void ensureApplication() {
        ensureApplication("lms");
    }

    private void ensureApplication(String applicationId) {
        jdbc.update("""
                insert into incentive_applications (
                    id, tenant_id, application_id, name, status, created_by, created_at, updated_at, version
                ) values (?, 'courseflow', ?, 'LMS', 'ACTIVE', 'test', now(), now(), 0)
                on conflict (tenant_id, application_id)
                do update set status = 'ACTIVE', updated_at = now()
                """, UUID.randomUUID(), applicationId);
        jdbc.update("""
                insert into incentive_application_client_bindings (
                    id, tenant_id, application_id, client_id, status, allowed_operations, created_by,
                    created_at, updated_at, version
                ) values (?, 'courseflow', ?, 'api-gateway', 'ACTIVE',
                    '["admin","reverse"]'::jsonb, 'test', now(), now(), 0)
                on conflict (tenant_id, application_id, client_id)
                do update set status = 'ACTIVE', allowed_operations = excluded.allowed_operations, updated_at = now()
                """, UUID.randomUUID(), applicationId);
        jdbc.update("""
                insert into incentive_application_client_bindings (
                    id, tenant_id, application_id, client_id, status, allowed_operations, created_by,
                    created_at, updated_at, version
                ) values (?, 'courseflow', ?, 'checkout-service', 'ACTIVE',
                    '["evaluate","reserve","commit","cancel","reverse"]'::jsonb, 'test', now(), now(), 0)
                on conflict (tenant_id, application_id, client_id)
                do update set status = 'ACTIVE', allowed_operations = excluded.allowed_operations, updated_at = now()
                """, UUID.randomUUID(), applicationId);
    }

    private void insertCoupon(UUID campaignId, String code, String normalizedCode, String status) {
        jdbc.update("""
                insert into incentive_coupons (
                    id, campaign_id, code, normalized_code, code_mask, status, created_at, updated_at, version
                ) values (?, ?, ?, ?, ?, ?, now(), now(), 0)
                """, UUID.randomUUID(), campaignId, code, normalizedCode, code, status);
    }

    private UUID insertRuntimeCoupon(UUID campaignId, String rawCode, Integer maxRedemptions,
                                     Integer maxRedemptionsPerProfile) {
        String normalizedCode = CouponCodeNormalizer.normalize(rawCode);
        UUID couponId = UUID.randomUUID();
        jdbc.update("""
                insert into incentive_coupons (
                    id, campaign_id, code, normalized_code, code_mask, status, max_redemptions,
                    max_redemptions_per_profile, created_at, updated_at, version
                ) values (?, ?, ?, ?, ?, 'ACTIVE', ?, ?, now(), now(), 0)
                """,
                couponId,
                campaignId,
                CouponCodeNormalizer.mask(normalizedCode),
                couponFingerprints.primaryFingerprint(normalizedCode),
                CouponCodeNormalizer.mask(normalizedCode),
                maxRedemptions,
                maxRedemptionsPerProfile);
        return couponId;
    }

    private void expireRows(UUID... reservationIds) {
        for (UUID reservationId : reservationIds) {
            jdbc.update("update incentive_reservations set expires_at = ? where id = ?",
                    java.sql.Timestamp.from(Instant.now().minusSeconds(5)),
                    reservationId);
        }
    }

    private void markTerminalSnapshot(UUID reservationId, String status, Instant terminalAt, String requestJson) {
        jdbc.update("""
                update incentive_reservations
                set status = ?,
                    expires_at = ?,
                    cancelled_at = case when ? = 'CANCELLED' then ? else cancelled_at end,
                    request_json = ?::jsonb
                where id = ?
                """,
                status,
                java.sql.Timestamp.from(terminalAt),
                status,
                java.sql.Timestamp.from(terminalAt),
                requestJson,
                reservationId);
    }

    private String requestJson(UUID reservationId) {
        return jdbc.queryForObject(
                "select request_json::text from incentive_reservations where id = ?",
                String.class,
                reservationId);
    }

    private static String fakeInternalToken(String clientId, String actorType, String... scopes) {
        String scopeClaim = scopes == null || scopes.length == 0
                ? ""
                : ",\"scope\":\"" + String.join(" ", scopes) + "\"";
        String payload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(("{\"azp\":\"" + clientId + "\",\"actor_type\":\"" + actorType + "\"" + scopeClaim + "}")
                        .getBytes(StandardCharsets.UTF_8));
        return "test." + payload + ".signature";
    }

    private EvaluateIncentivesRequestDto request(String profileId, String externalReference) {
        return request(profileId, externalReference, "lms");
    }

    private EvaluateIncentivesRequestDto request(String profileId, String externalReference, String applicationId) {
        return request(profileId, externalReference, applicationId, List.of());
    }

    private EvaluateIncentivesRequestDto request(String profileId, String externalReference, String applicationId,
                                                List<String> couponCodes) {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                applicationId,
                profileId,
                externalReference,
                "WEB",
                "USD",
                couponCodes,
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.TEN),
                List.of(new IncentiveItemDto(
                        "item-1",
                        "COURSE",
                        1,
                        BigDecimal.valueOf(120),
                        Map.of("category", "spring"))),
                Map.of("segment", "NEW"));
    }

    private CouponImportDryRunRequestDto couponDryRunRequest(UUID campaignId, String csv) {
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

    private CouponImportCommitRequestDto couponCommitRequest(UUID approvalId,
                                                             UUID dryRunId,
                                                             UUID campaignId,
                                                             String csv,
                                                             String resultHash,
                                                             String idempotencyKey) {
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
                "CHG-JPA",
                resultHash,
                idempotencyKey,
                true);
    }

    private record CouponImportCommitAttempt(CouponImportCommitResponseDto response, Throwable failure) {
    }
}
