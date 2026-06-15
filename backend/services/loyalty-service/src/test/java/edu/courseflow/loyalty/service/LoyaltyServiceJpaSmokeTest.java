package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ClientBindingRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateProgramRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsAdjustmentRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RedeemRewardRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReviewLoyaltyAdjustmentApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.SubmitRewardRedemptionReversalApprovalRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateAccountStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateProgramStatusRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpsertClientBindingRequestDto;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest(properties = {
        "eureka.client.enabled=false",
        "courseflow.security.internal-jwt.secret=test-internal-jwt-secret-32-byte-value-001"
})
@Testcontainers(disabledWithoutDocker = true)
class LoyaltyServiceJpaSmokeTest {

    private static final CurrentUser LOYALTY_ADMIN = serviceUser(
            "loyalty-service",
            InternalScopes.LOYALTY_ADMIN,
            InternalScopes.LOYALTY_READ);
    private static final CurrentUser LOYALTY_REVIEWER = serviceUser(
            "loyalty-risk-reviewer",
            InternalScopes.LOYALTY_ADMIN,
            InternalScopes.LOYALTY_READ);
    private static final CurrentUser CHECKOUT = serviceUser(
            "checkout-service",
            InternalScopes.LOYALTY_EARN,
            InternalScopes.LOYALTY_BURN,
            InternalScopes.LOYALTY_REVERSE,
            InternalScopes.LOYALTY_READ);

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("cf_loyalty")
            .withUsername("courseflow")
            .withPassword("courseflow");

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.liquibase.contexts", () -> "prod");
    }

    @Autowired
    private LoyaltyService loyalty;

    @Autowired
    private LoyaltyAdminService admin;

    @Autowired
    private LoyaltyRewardService rewards;

    @Autowired
    private LoyaltyPointsEntryRepository pointsEntries;

    @Autowired
    private JdbcTemplate jdbc;

    @Test
    void concurrentBurnsSerializeOnAccountAndCannotOverdraw() throws Exception {
        String programId = "burn-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);
        var earn = loyalty.earn(points(programId, "learner-1", 100, "earn-source", "earn-idem"), CHECKOUT);

        List<Object> results = runConcurrently(2, index ->
                () -> {
                    try {
                        return loyalty.burn(points(
                                programId,
                                "learner-1",
                                80,
                                "burn-source-" + index,
                                "burn-idem-" + index), CHECKOUT);
                    } catch (ConflictException ex) {
                        return ex;
                    }
                });

        assertThat(results).filteredOn(result -> !(result instanceof ConflictException)).hasSize(1);
        assertThat(results).filteredOn(ConflictException.class::isInstance).hasSize(1);
        assertThat(pointsEntries.balance(earn.accountId())).isEqualTo(20);
        assertThat(pointsEntries.findTop100ByAccountIdOrderByCreatedAtDesc(earn.accountId()))
                .filteredOn(entry -> "BURN".equals(entry.getEntryType()))
                .hasSize(1);
    }

    @Test
    void concurrentReverseCreatesOnlyOneCompensatingEntry() throws Exception {
        String programId = "reverse-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);
        var earn = loyalty.earn(points(programId, "learner-2", 100, "earn-reverse-source", "earn-reverse-idem"), CHECKOUT);

        List<Object> results = runConcurrently(2, index ->
                () -> loyalty.reverse(
                        earn.entryId(),
                        new ReversePointsRequestDto(
                                "reverse-idem-" + index,
                                "refund",
                                "corr-reverse-" + index,
                                Map.of("index", index)),
                        CHECKOUT));

        assertThat(results).hasSize(2);
        assertThat(results).allSatisfy(result -> assertThat(result).isNotInstanceOf(Exception.class));
        assertThat(pointsEntries.balance(earn.accountId())).isEqualTo(0);
        assertThat(pointsEntries.findTop100ByAccountIdOrderByCreatedAtDesc(earn.accountId()))
                .filteredOn(entry -> "REVERSE".equals(entry.getEntryType()))
                .hasSize(1);
    }

    @Test
    void unboundServiceClientCannotMutateProgramEvenWithLoyaltyScope() {
        String programId = "binding-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);
        CurrentUser unboundClient = serviceUser("promotion-service", InternalScopes.LOYALTY_EARN);

        assertThatThrownBy(() -> loyalty.earn(
                        points(programId, "learner-3", 10, "unbound-source", "unbound-idem"),
                        unboundClient))
                .isInstanceOf(ForbiddenException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_CLIENT_NOT_BOUND));
    }

    @Test
    void adminControlPlaneManagesBindingStatusAccountsAndAuditTimeline() {
        String programId = "control-plane-" + UUID.randomUUID();
        var program = loyalty.createProgram(program(programId), LOYALTY_ADMIN);

        var listed = admin.listPrograms(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.of(programId),
                Optional.empty(),
                Optional.of(10),
                LOYALTY_ADMIN);
        assertThat(listed).hasSize(1);
        assertThat(listed.getFirst().clientBindings())
                .extracting("clientId")
                .contains("checkout-service");

        admin.upsertClientBinding(
                program.id(),
                new UpsertClientBindingRequestDto("support-service", "ACTIVE", List.of("earn", "read")),
                "corr-binding",
                LOYALTY_ADMIN);
        var supportEarn = loyalty.earn(
                points(programId, "learner-admin", 15, "control-plane-support", "control-plane-support-idem"),
                serviceUser("support-service", InternalScopes.LOYALTY_EARN, InternalScopes.LOYALTY_READ));

        var accounts = admin.listAccounts(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.of(programId),
                Optional.of("learner-admin"),
                Optional.of("ACTIVE"),
                Optional.of(10),
                LOYALTY_ADMIN);
        assertThat(accounts).hasSize(1);
        assertThat(accounts.getFirst().balance()).isEqualTo(15);

        var suspendedAccount = admin.updateAccountStatus(
                supportEarn.accountId(),
                new UpdateAccountStatusRequestDto("SUSPENDED", "support hold"),
                "corr-account",
                LOYALTY_ADMIN);
        assertThat(suspendedAccount.status()).isEqualTo("SUSPENDED");

        var suspendedProgram = admin.updateProgramStatus(
                program.id(),
                new UpdateProgramStatusRequestDto("SUSPENDED", "incident hold"),
                "corr-program",
                LOYALTY_ADMIN);
        assertThat(suspendedProgram.status()).isEqualTo("SUSPENDED");

        var ledger = admin.ledger(supportEarn.accountId(), LOYALTY_ADMIN);
        assertThat(ledger.balance()).isEqualTo(15);
        assertThat(ledger.items())
                .extracting("entryType")
                .contains("EARN");

        var audit = admin.audit(
                Optional.of("courseflow"),
                Optional.of("lms"),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                Optional.of(20),
                LOYALTY_ADMIN);
        assertThat(audit.items())
                .extracting("action")
                .contains(
                        "loyalty.program_client_binding.upserted",
                        "loyalty.account.status_changed",
                        "loyalty.program.status_changed");
        assertThat(admin.programTimeline(program.id(), Optional.of(10), LOYALTY_ADMIN).items())
                .extracting("action")
                .contains(
                        "loyalty.program_client_binding.upserted",
                        "loyalty.program.status_changed");
        assertThat(admin.accountTimeline(supportEarn.accountId(), Optional.of(10), LOYALTY_ADMIN).items())
                .extracting("action")
                .contains("loyalty.account.status_changed");
    }

    @Test
    void adminManualAdjustmentIsIdempotentAuditedAndCannotOverdraw() {
        String programId = "adjust-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);

        PointsAdjustmentRequestDto creditRequest = adjustment(
                programId, "learner-adjust", 40, "adjust-ticket-credit", "adjust-idem-credit");
        var credit = loyalty.adjust(creditRequest, LOYALTY_ADMIN);
        assertThat(credit.entryType()).isEqualTo("ADJUST");
        assertThat(credit.pointsDelta()).isEqualTo(40);
        assertThat(credit.balance()).isEqualTo(40);

        var replay = loyalty.adjust(creditRequest, LOYALTY_ADMIN);
        assertThat(replay.entryId()).isEqualTo(credit.entryId());
        assertThat(replay.idempotencyReplay()).isTrue();

        assertThatThrownBy(() -> loyalty.adjust(
                        adjustment(programId, "learner-adjust", 45, "adjust-ticket-credit", "adjust-idem-conflict"),
                        LOYALTY_ADMIN))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_SOURCE_REFERENCE_REUSED));

        var debit = loyalty.adjust(
                adjustment(programId, "learner-adjust", -15, "adjust-ticket-debit", "adjust-idem-debit"),
                LOYALTY_ADMIN);
        assertThat(debit.balance()).isEqualTo(25);

        assertThatThrownBy(() -> loyalty.adjust(
                        adjustment(programId, "learner-adjust", -50, "adjust-ticket-overdraw", "adjust-idem-overdraw"),
                        LOYALTY_ADMIN))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_INSUFFICIENT_BALANCE));

        assertThat(admin.ledger(credit.accountId(), LOYALTY_ADMIN).items())
                .extracting("entryType")
                .containsOnly("ADJUST", "ADJUST");
        assertThat(admin.audit(
                        Optional.of("courseflow"),
                        Optional.of("lms"),
                        Optional.of("loyalty-points-entry"),
                        Optional.empty(),
                        Optional.of("loyalty.points.adjusted"),
                        Optional.empty(),
                        Optional.empty(),
                        Optional.empty(),
                        Optional.empty(),
                        Optional.of(10),
                        LOYALTY_ADMIN).items())
                .extracting("action")
                .contains("loyalty.points.adjusted");
        assertThat(outboxEventCount("loyalty.points.adjusted")).isGreaterThanOrEqualTo(2);
    }

    @Test
    void rewardRedemptionReverseRequiresApprovedMakerCheckerApproval() {
        String programId = "reward-reverse-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);
        CurrentUser learner = new CurrentUser(42L, "learner42@example.com", "STUDENT", Set.of("STUDENT"));
        var earn = loyalty.earn(points(programId, "42", 100, "reward-reverse-earn", "reward-reverse-earn-idem"),
                CHECKOUT);
        var reward = rewards.createReward(new CreateRewardRequestDto(
                "courseflow",
                "lms",
                programId,
                "voucher-" + UUID.randomUUID(),
                "Voucher",
                "Manual voucher",
                60L,
                "ACTIVE",
                Instant.now().minusSeconds(60),
                null,
                null,
                null,
                "MANUAL",
                Map.of("provider", "manual")), LOYALTY_ADMIN);
        var redemption = rewards.redeemReward(
                reward.id(),
                new RedeemRewardRequestDto(
                        "reward-redemption-idem-" + UUID.randomUUID(),
                        "corr-reward-redemption",
                        "learner redemption",
                        Map.of("cartId", "cart-42")),
                learner);
        assertThat(pointsEntries.balance(earn.accountId())).isEqualTo(40);

        var reverseWithoutApproval = new ReversePointsRequestDto(
                "reward-reverse-idem-" + UUID.randomUUID(),
                "customer support refund",
                "corr-reward-reverse",
                Map.of("ticketId", "T-42"));
        assertThatThrownBy(() -> rewards.reverseRedemption(redemption.id(), reverseWithoutApproval, LOYALTY_ADMIN))
                .isInstanceOf(ConflictException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_REWARD_REVERSAL_APPROVAL_REQUIRED));

        var approvalRequest = new SubmitRewardRedemptionReversalApprovalRequestDto(
                "reward-reverse-idem-approved-" + UUID.randomUUID(),
                "customer support refund",
                "corr-reward-reverse-approved",
                Map.of("ticketId", "T-42", "evidence", "support-case"));
        var approval = rewards.submitReversalApproval(redemption.id(), approvalRequest, LOYALTY_ADMIN);
        assertThat(approval.status()).isEqualTo("PENDING");
        assertThat(approval.operationType()).isEqualTo("REWARD_REDEMPTION_REVERSE");
        assertThat(approval.metadata())
                .containsEntry("thresholdPolicy", "ALL_REWARD_REDEMPTION_REVERSALS_REQUIRE_MAKER_CHECKER_APPROVAL");

        assertThatThrownBy(() -> loyalty.approveAdjustmentApproval(
                        approval.id(),
                        new ReviewLoyaltyAdjustmentApprovalRequestDto("maker cannot approve own request"),
                        LOYALTY_ADMIN))
                .isInstanceOf(ForbiddenException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_ADJUSTMENT_SELF_APPROVAL_DENIED));

        var approved = loyalty.approveAdjustmentApproval(
                approval.id(),
                new ReviewLoyaltyAdjustmentApprovalRequestDto("approved by risk checker"),
                LOYALTY_REVIEWER);
        assertThat(approved.status()).isEqualTo("APPROVED");
        assertThat(pointsEntries.balance(earn.accountId())).isEqualTo(40);

        var reversed = rewards.reverseRedemption(
                redemption.id(),
                new ReversePointsRequestDto(
                        approvalRequest.idempotencyKey(),
                        approvalRequest.reason(),
                        approvalRequest.correlationId(),
                        approvalRequest.metadata(),
                        approval.id()),
                LOYALTY_ADMIN);
        assertThat(reversed.status()).isEqualTo("REVERSED");
        assertThat(reversed.reversalEntryId()).isNotNull();
        assertThat(pointsEntries.balance(earn.accountId())).isEqualTo(100);

        var evidence = admin.approvalEvidencePack(approval.id(), LOYALTY_ADMIN);
        assertThat(evidence.operationType()).isEqualTo("REWARD_REDEMPTION_REVERSE");
        assertThat(evidence.approval().status()).isEqualTo("EXECUTED");
        assertThat(evidence.ledgerEntries())
                .extracting("entryType")
                .contains("REVERSE");
        assertThat(evidence.auditEvents())
                .extracting("action")
                .contains(
                        "loyalty.reward_reversal_approval.requested",
                        "loyalty.reward_reversal_approval.approved",
                        "loyalty.reward_reversal_approval.executed");
    }

    @Test
    void inactiveProgramCannotMutateAndDoesNotWriteLedgerEntry() {
        String programId = "inactive-program-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);
        jdbc.update("update loyalty_programs set status = 'SUSPENDED' where program_id = ?", programId);

        assertThatThrownBy(() -> loyalty.earn(
                        points(programId, "learner-4", 10, "inactive-program-source", "inactive-program-idem"),
                        CHECKOUT))
                .isInstanceOf(ForbiddenException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_PROGRAM_INACTIVE));
        assertThat(ledgerEntryCount(programId)).isZero();
    }

    @Test
    void inactiveAccountCannotMutateAndDoesNotWriteAdditionalLedgerEntry() {
        String programId = "inactive-account-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);
        var earn = loyalty.earn(points(programId, "learner-5", 100, "inactive-account-earn", "inactive-account-earn-idem"),
                CHECKOUT);
        jdbc.update("update loyalty_accounts set status = 'SUSPENDED' where id = ?", earn.accountId());

        assertThatThrownBy(() -> loyalty.burn(
                        points(programId, "learner-5", 10, "inactive-account-burn", "inactive-account-burn-idem"),
                        CHECKOUT))
                .isInstanceOf(ForbiddenException.class)
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(LoyaltyErrorCodes.LOYALTY_ACCOUNT_INACTIVE));
        assertThat(ledgerEntryCount(programId)).isEqualTo(1);
    }

    @Test
    void idempotencyReplaySurvivesSuspendedProgramAndAccount() {
        String programId = "replay-after-suspend-" + UUID.randomUUID();
        loyalty.createProgram(program(programId), LOYALTY_ADMIN);
        PointsMutationRequestDto request = points(
                programId,
                "learner-6",
                100,
                "replay-after-suspend-source",
                "replay-after-suspend-idem");
        var first = loyalty.earn(request, CHECKOUT);
        jdbc.update("update loyalty_accounts set status = 'SUSPENDED' where id = ?", first.accountId());
        jdbc.update("update loyalty_programs set status = 'SUSPENDED' where program_id = ?", programId);

        var replay = loyalty.earn(request, CHECKOUT);

        assertThat(replay.entryId()).isEqualTo(first.entryId());
        assertThat(replay.accountId()).isEqualTo(first.accountId());
        assertThat(replay.idempotencyReplay()).isTrue();
        assertThat(ledgerEntryCount(programId)).isEqualTo(1);
    }

    private CreateProgramRequestDto program(String programId) {
        return new CreateProgramRequestDto(
                "courseflow",
                "lms",
                programId,
                "Concurrency program",
                "POINT",
                false,
                365,
                List.of(new ClientBindingRequestDto(
                        "checkout-service",
                        List.of("earn", "burn", "reverse", "read"))));
    }

    private PointsMutationRequestDto points(
            String programId, String profileId, long points, String sourceReference, String idempotencyKey) {
        return new PointsMutationRequestDto(
                "courseflow",
                "lms",
                programId,
                profileId,
                points,
                sourceReference,
                idempotencyKey,
                "smoke",
                "corr-" + sourceReference,
                Instant.now(),
                null,
                Map.of("source", sourceReference));
    }

    private PointsAdjustmentRequestDto adjustment(
            String programId, String profileId, long pointsDelta, String sourceReference, String idempotencyKey) {
        return new PointsAdjustmentRequestDto(
                "courseflow",
                "lms",
                programId,
                profileId,
                pointsDelta,
                sourceReference,
                idempotencyKey,
                "manual correction",
                "corr-" + idempotencyKey,
                Instant.now(),
                null,
                Map.of("source", "jpa-smoke"));
    }

    private List<Object> runConcurrently(int workers, java.util.function.IntFunction<Callable<Object>> taskFactory)
            throws Exception {
        ExecutorService executor = Executors.newFixedThreadPool(workers);
        CountDownLatch ready = new CountDownLatch(workers);
        CountDownLatch start = new CountDownLatch(1);
        try {
            List<Future<Object>> futures = IntStream.range(0, workers)
                    .mapToObj(index -> executor.submit(() -> {
                        ready.countDown();
                        if (!start.await(10, TimeUnit.SECONDS)) {
                            throw new IllegalStateException("Workers did not start together");
                        }
                        return taskFactory.apply(index).call();
                    }))
                    .toList();
            assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            return futures.stream()
                    .map(future -> {
                        try {
                            return future.get(30, TimeUnit.SECONDS);
                        } catch (Exception ex) {
                            return ex;
                        }
                    })
                    .toList();
        } finally {
            executor.shutdownNow();
        }
    }

    private long ledgerEntryCount(String programId) {
        Long count = jdbc.queryForObject(
                "select count(*) from loyalty_points_entries where program_id = ?",
                Long.class,
                programId);
        return count == null ? 0 : count;
    }

    private long outboxEventCount(String eventType) {
        Long count = jdbc.queryForObject(
                "select count(*) from outbox_events where event_type = ?",
                Long.class,
                eventType);
        return count == null ? 0 : count;
    }

    private static CurrentUser serviceUser(String clientId, String... scopes) {
        String scope = String.join(" ", scopes);
        String payload = Base64.getUrlEncoder().withoutPadding().encodeToString(
                ("{\"actor_type\":\"service\",\"azp\":\"" + clientId + "\",\"scope\":\"" + scope + "\"}")
                        .getBytes(StandardCharsets.UTF_8));
        return new CurrentUser(null, null, null, Set.of(), Set.of(), "header." + payload + ".signature");
    }
}
