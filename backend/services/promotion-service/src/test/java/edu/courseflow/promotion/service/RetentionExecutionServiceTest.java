package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionExecutionResponseDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveRetentionApproval;
import edu.courseflow.promotion.model.IncentiveRetentionOperation;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import edu.courseflow.promotion.repository.RetentionDryRunStats;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
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
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.SimpleTransactionStatus;

@ExtendWith(MockitoExtension.class)
class RetentionExecutionServiceTest {

    @Mock
    IncentiveReservationRepository reservations;
    @Mock
    IncentiveRetentionOperationRepository operations;
    @Mock
    RetentionApprovalService approvals;
    @Mock
    RetentionExecutionFailureRecorder failureRecorder;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveMetrics metrics;

    private RetentionExecutionService service;
    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final PlatformTransactionManager transactionManager = new PlatformTransactionManager() {
        @Override
        public TransactionStatus getTransaction(TransactionDefinition definition) {
            return new SimpleTransactionStatus();
        }

        @Override
        public void commit(TransactionStatus status) {
        }

        @Override
        public void rollback(TransactionStatus status) {
        }
    };

    @BeforeEach
    void setUp() {
        service = new RetentionExecutionService(
                new RetentionPolicyRegistry(),
                reservations,
                operations,
                approvals,
                failureRecorder,
                access,
                auditEvents,
                objectMapper,
                metrics,
                transactionManager,
                true,
                60);
    }

    @Test
    void executesLegacySnapshotRedactionAfterFreshDryRunApproval() throws Exception {
        CurrentUser admin = admin();
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats stats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        ApprovedDryRun approved = approved(asOf, cutoff, stats, 500);
        IncentiveRetentionApproval approval = approval(asOf, cutoff, approved, 8, 500);
        approval.approve("reviewer@example.com", "approved", Instant.now());
        when(approvals.requireApprovedForExecution(approval.getId(), admin)).thenReturn(approval);
        when(reservations.dryRunTerminalRequestSnapshots("courseflow", "lms", cutoff)).thenReturn(stats);
        when(reservations.redactTerminalRequestSnapshots(eq("courseflow"), eq("lms"), eq(cutoff), eq(500), anyString()))
                .thenReturn(5);
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(operations.lockByApprovalId(approval.getId())).thenReturn(Optional.empty());

        AtomicReference<IncentiveRetentionOperation> operationRef = new AtomicReference<>();
        when(operations.insertInProgressIfAbsent(
                any(UUID.class), eq("terminal-reservation-request-snapshots"), eq("v1"),
                eq("incentive_reservation_request_snapshots"), eq("TENANT:10:courseflow|APP:3:lms"),
                eq(approval.getId()),
                eq("courseflow"), eq("lms"),
                eq(approved.dryRunId()), eq(approved.resultHash()), eq(cutoff), eq(8L),
                eq(500), eq("retention-2026-06"), anyString(), eq("privacy monthly redaction"),
                eq("CHG-42"), eq("restore-drill-2026-06"), eq("reviewer@example.com"),
                eq("admin@example.com"), eq("corr-retention")))
                .thenAnswer(invocation -> {
                    operationRef.set(new IncentiveRetentionOperation(
                            invocation.getArgument(0),
                            invocation.getArgument(1),
                            invocation.getArgument(2),
                            invocation.getArgument(3),
                            invocation.getArgument(4),
                            invocation.getArgument(5),
                            invocation.getArgument(6),
                            invocation.getArgument(7),
                            invocation.getArgument(8),
                            invocation.getArgument(9),
                            invocation.getArgument(10),
                            invocation.getArgument(11),
                            invocation.getArgument(12),
                            invocation.getArgument(13),
                            invocation.getArgument(14),
                            invocation.getArgument(15),
                            invocation.getArgument(16),
                            invocation.getArgument(17),
                            invocation.getArgument(18),
                            invocation.getArgument(19),
                            invocation.getArgument(20)));
                    return 1;
                });
        when(operations.lockByIdempotencyKey("terminal-reservation-request-snapshots",
                "TENANT:10:courseflow|APP:3:lms", "retention-2026-06"))
                .thenAnswer(invocation -> Optional.of(operationRef.get()));
        when(operations.lockById(any(UUID.class))).thenAnswer(invocation -> Optional.of(operationRef.get()));

        var response = service.execute(new RetentionExecutionRequestDto(
                approval.getId(),
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                approved.dryRunId(),
                approved.resultHash(),
                "retention-2026-06",
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                true), admin, "corr-retention");

        assertThat(response.status()).isEqualTo("SUCCEEDED");
        assertThat(response.eligibleBefore()).isEqualTo(8);
        assertThat(response.redactedCount()).isEqualTo(5);
        assertThat(response.hasMore()).isTrue();
        assertThat(objectMapper.writeValueAsString(response))
                .doesNotContain("request_json")
                .doesNotContain("profileId")
                .doesNotContain("externalReference")
                .doesNotContain("fingerprint");

        ArgumentCaptor<String> redactedSnapshotCaptor = ArgumentCaptor.forClass(String.class);
        verify(reservations).redactTerminalRequestSnapshots(
                eq("courseflow"), eq("lms"), eq(cutoff), eq(500), redactedSnapshotCaptor.capture());
        assertThat(redactedSnapshotCaptor.getValue())
                .contains("\"retentionRedacted\":true")
                .contains("\"requestSnapshotMinimized\":true")
                .contains("\"rawSnapshotRemoved\":true")
                .doesNotContain("profileId")
                .doesNotContain("externalReference")
                .doesNotContain("coupon")
                .doesNotContain("fingerprint");

        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents, org.mockito.Mockito.times(2)).save(auditCaptor.capture());
        assertThat(auditCaptor.getAllValues())
                .extracting(IncentiveAuditEvent::getAction)
                .containsExactly("retention.execution_requested", "retention.execution_completed");
        assertThat(auditCaptor.getAllValues().getLast().getPayloadJson())
                .contains("CHG-42")
                .contains("restore-drill-2026-06")
                .doesNotContain("profileId")
                .doesNotContain("externalReference");
        verify(metrics).retentionExecution(
                eq("terminal-reservation-request-snapshots"),
                eq("incentive_reservation_request_snapshots"),
                eq("success"),
                eq(5L),
                org.mockito.ArgumentMatchers.any());
    }

    @Test
    void rejectsExecutionWithoutApprovalId() {
        assertThatThrownBy(() -> service.execute(new RetentionExecutionRequestDto(
                null,
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                Instant.now(),
                Map.of(),
                500,
                UUID.randomUUID(),
                "sha256:abc",
                "retention-2026-06",
                "privacy monthly redaction",
                "CHG-42",
                " ",
                true), admin(), "corr-retention"))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("approvalId");
    }

    @Test
    void rejectsStaleOrMismatchedApprovedDryRun() {
        CurrentUser admin = admin();
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats stats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        IncentiveRetentionApproval approval = approval(asOf, cutoff, new ApprovedDryRun(UUID.randomUUID(), "sha256:not-current"),
                8, 500);
        approval.approve("reviewer@example.com", "approved", Instant.now());
        when(approvals.requireApprovedForExecution(approval.getId(), admin)).thenReturn(approval);
        when(reservations.dryRunTerminalRequestSnapshots("courseflow", "lms", cutoff)).thenReturn(stats);

        assertThatThrownBy(() -> service.execute(new RetentionExecutionRequestDto(
                approval.getId(),
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                UUID.randomUUID(),
                "sha256:not-current",
                "retention-2026-06",
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                true), admin, "corr-retention"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("no longer matches")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.RETENTION_RESULT_HASH_MISMATCH));
    }

    @Test
    void wrongRetryKeyForCompletedApprovalDoesNotRecordFailure() {
        CurrentUser admin = admin();
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats stats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        ApprovedDryRun approved = approved(asOf, cutoff, stats, 500);
        IncentiveRetentionApproval approval = approval(asOf, cutoff, approved, 8, 500);
        approval.approve("reviewer@example.com", "approved", Instant.now());
        IncentiveRetentionOperation completed = operation(approval, approved, cutoff, "retention-2026-06");
        completed.complete(5, "{}", Instant.now());
        approval.markExecuted("admin@example.com", Instant.now());
        when(approvals.requireApprovedForExecution(approval.getId(), admin)).thenReturn(approval);
        when(operations.lockByApprovalId(approval.getId())).thenReturn(Optional.of(completed));

        assertThatThrownBy(() -> service.execute(new RetentionExecutionRequestDto(
                approval.getId(),
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                approved.dryRunId(),
                approved.resultHash(),
                "different-key",
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                true), admin, "corr-retention"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("already has an execution operation")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.RETENTION_APPROVAL_CONSUMED));

        verify(failureRecorder, never()).recordFailure(any(), any(), anyString(), any(), any());
        assertThat(completed.getStatus()).isEqualTo(IncentiveRetentionOperation.STATUS_SUCCEEDED);
    }

    @Test
    void completedOperationReplaysWithoutRecomputingChangedDryRun() throws Exception {
        CurrentUser admin = admin();
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats originalStats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        ApprovedDryRun approved = approved(asOf, cutoff, originalStats, 500);
        IncentiveRetentionApproval approval = approval(asOf, cutoff, approved, 8, 500);
        approval.approve("reviewer@example.com", "approved", Instant.now());
        IncentiveRetentionOperation completed = operation(approval, approved, cutoff, "retention-2026-06");
        RetentionExecutionResponseDto stored = new RetentionExecutionResponseDto(
                completed.getId(),
                IncentiveRetentionOperation.STATUS_SUCCEEDED,
                "terminal-reservation-request-snapshots",
                "v1",
                "incentive_reservation_request_snapshots",
                "courseflow",
                "lms",
                cutoff,
                approved.dryRunId(),
                approved.resultHash(),
                8,
                5,
                500,
                true,
                false,
                Instant.now());
        completed.complete(5, objectMapper.writeValueAsString(stored), Instant.now());
        approval.markExecuted("admin@example.com", Instant.now());
        when(approvals.requireApprovedForExecution(approval.getId(), admin)).thenReturn(approval);
        when(operations.lockByApprovalId(approval.getId())).thenReturn(Optional.of(completed));

        var response = service.execute(new RetentionExecutionRequestDto(
                approval.getId(),
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                approved.dryRunId(),
                approved.resultHash(),
                "retention-2026-06",
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                true), admin, "corr-retention");

        assertThat(response.idempotencyReplay()).isTrue();
        assertThat(response.redactedCount()).isEqualTo(5);
        org.mockito.Mockito.verifyNoInteractions(reservations);
    }

    @Test
    void failureAfterOperationStartIsRecorded() {
        CurrentUser admin = admin();
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats stats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        ApprovedDryRun approved = approved(asOf, cutoff, stats, 500);
        IncentiveRetentionApproval approval = approval(asOf, cutoff, approved, 8, 500);
        approval.approve("reviewer@example.com", "approved", Instant.now());
        when(approvals.requireApprovedForExecution(approval.getId(), admin)).thenReturn(approval);
        when(reservations.dryRunTerminalRequestSnapshots("courseflow", "lms", cutoff)).thenReturn(stats);
        when(reservations.redactTerminalRequestSnapshots(eq("courseflow"), eq("lms"), eq(cutoff), eq(500), anyString()))
                .thenThrow(new IllegalStateException("database unavailable"));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(operations.lockByApprovalId(approval.getId())).thenReturn(Optional.empty());

        AtomicReference<IncentiveRetentionOperation> operationRef = new AtomicReference<>();
        when(operations.insertInProgressIfAbsent(
                any(UUID.class), eq("terminal-reservation-request-snapshots"), eq("v1"),
                eq("incentive_reservation_request_snapshots"), eq("TENANT:10:courseflow|APP:3:lms"),
                eq(approval.getId()),
                eq("courseflow"), eq("lms"),
                eq(approved.dryRunId()), eq(approved.resultHash()), eq(cutoff), eq(8L),
                eq(500), eq("retention-2026-06"), anyString(), eq("privacy monthly redaction"),
                eq("CHG-42"), eq("restore-drill-2026-06"), eq("reviewer@example.com"),
                eq("admin@example.com"), eq("corr-retention")))
                .thenAnswer(invocation -> {
                    operationRef.set(new IncentiveRetentionOperation(
                            invocation.getArgument(0),
                            invocation.getArgument(1),
                            invocation.getArgument(2),
                            invocation.getArgument(3),
                            invocation.getArgument(4),
                            invocation.getArgument(5),
                            invocation.getArgument(6),
                            invocation.getArgument(7),
                            invocation.getArgument(8),
                            invocation.getArgument(9),
                            invocation.getArgument(10),
                            invocation.getArgument(11),
                            invocation.getArgument(12),
                            invocation.getArgument(13),
                            invocation.getArgument(14),
                            invocation.getArgument(15),
                            invocation.getArgument(16),
                            invocation.getArgument(17),
                            invocation.getArgument(18),
                            invocation.getArgument(19),
                            invocation.getArgument(20)));
                    return 1;
                });
        when(operations.lockByIdempotencyKey("terminal-reservation-request-snapshots",
                "TENANT:10:courseflow|APP:3:lms", "retention-2026-06"))
                .thenAnswer(invocation -> Optional.of(operationRef.get()));
        when(operations.lockById(any(UUID.class))).thenAnswer(invocation -> Optional.of(operationRef.get()));

        assertThatThrownBy(() -> service.execute(new RetentionExecutionRequestDto(
                approval.getId(),
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                approved.dryRunId(),
                approved.resultHash(),
                "retention-2026-06",
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                true), admin, "corr-retention"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("database unavailable");

        verify(failureRecorder).recordFailure(eq(approval), eq(admin), eq("corr-retention"),
                any(IllegalStateException.class), any());
    }

    private static ApprovedDryRun approved(Instant asOf,
                                           Instant cutoff,
                                           RetentionDryRunStats stats,
                                           int batchLimit) {
        String policyResultHash = hash(String.join("|",
                "terminal-reservation-request-snapshots",
                "v1",
                cutoff.toString(),
                Long.toString(stats.getEligibleCount()),
                Long.toString(stats.getBlockedCount()),
                "",
                stats.getOldestCandidateAt().toString(),
                stats.getNewestCandidateAt().toString(),
                Integer.toString(batchLimit)));
        String resultHash = hash("courseflow/lms|" + asOf + "|" + policyResultHash);
        UUID dryRunId = UUID.nameUUIDFromBytes(resultHash.getBytes(StandardCharsets.UTF_8));
        return new ApprovedDryRun(dryRunId, resultHash);
    }

    private static RetentionDryRunStats stats(long eligibleCount,
                                              long blockedCount,
                                              String oldest,
                                              String newest) {
        return new RetentionDryRunStats() {
            @Override
            public long getEligibleCount() {
                return eligibleCount;
            }

            @Override
            public long getBlockedCount() {
                return blockedCount;
            }

            @Override
            public Instant getOldestCandidateAt() {
                return Instant.parse(oldest);
            }

            @Override
            public Instant getNewestCandidateAt() {
                return Instant.parse(newest);
            }
        };
    }

    private static String hash(String raw) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(digest.digest(raw.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 not available", ex);
        }
    }

    private static CurrentUser admin() {
        return new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of());
    }

    private static IncentiveRetentionApproval approval(Instant asOf,
                                                       Instant cutoff,
                                                       ApprovedDryRun approved,
                                                       long eligibleCount,
                                                       int batchLimit) {
        return new IncentiveRetentionApproval(
                "terminal-reservation-request-snapshots",
                "v1",
                "incentive_reservation_request_snapshots",
                "TENANT:10:courseflow|APP:3:lms",
                "courseflow",
                "lms",
                asOf,
                cutoff,
                30,
                approved.dryRunId(),
                approved.resultHash(),
                eligibleCount,
                batchLimit,
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                "requester@example.com",
                "corr-retention",
                "api-gateway",
                asOf.plus(java.time.Duration.ofMinutes(60)));
    }

    private static IncentiveRetentionOperation operation(IncentiveRetentionApproval approval,
                                                        ApprovedDryRun approved,
                                                        Instant cutoff,
                                                        String idempotencyKey) {
        return new IncentiveRetentionOperation(
                UUID.randomUUID(),
                "terminal-reservation-request-snapshots",
                "v1",
                "incentive_reservation_request_snapshots",
                "TENANT:10:courseflow|APP:3:lms",
                approval.getId(),
                "courseflow",
                "lms",
                approved.dryRunId(),
                approved.resultHash(),
                cutoff,
                approval.getEligibleCount(),
                approval.getBatchLimit(),
                idempotencyKey,
                hash(String.join("|",
                        "retention-execution",
                        approval.getId().toString(),
                        "terminal-reservation-request-snapshots",
                        "v1",
                        "courseflow/lms",
                        approval.getAsOf().toString(),
                        cutoff.toString(),
                        approval.getDryRunId().toString(),
                        approval.getDryRunResultHash(),
                        Integer.toString(approval.getBatchLimit()),
                        "privacy monthly redaction",
                        "CHG-42",
                        "restore-drill-2026-06",
                        idempotencyKey)),
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                "reviewer@example.com",
                "admin@example.com",
                "corr-retention");
    }

    private record ApprovedDryRun(UUID dryRunId, String resultHash) {
    }
}
