package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalDecisionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionApprovalRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveRetentionApproval;
import edu.courseflow.promotion.model.IncentiveRetentionOperation;
import edu.courseflow.promotion.model.IncentiveRestoreDrill;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRestoreDrillRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionApprovalRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import edu.courseflow.promotion.repository.RetentionDryRunStats;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RetentionApprovalServiceTest {

    @Mock
    IncentiveReservationRepository reservations;
    @Mock
    IncentiveRestoreDrillRepository restoreDrills;
    @Mock
    IncentiveRetentionApprovalRepository approvals;
    @Mock
    IncentiveRetentionOperationRepository operations;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveAuditEventRepository auditEvents;

    private RetentionApprovalService service;
    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @BeforeEach
    void setUp() {
        service = new RetentionApprovalService(
                new RetentionPolicyRegistry(),
                reservations,
                restoreDrills,
                approvals,
                operations,
                access,
                auditEvents,
                objectMapper,
                60);
    }

    @Test
    void requestApprovalPersistsAggregateApprovalAfterRestoreDrillValidation() {
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats stats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        ApprovedDryRun dryRun = approved(asOf, cutoff, stats, 500);
        when(reservations.dryRunTerminalRequestSnapshots("courseflow", "lms", cutoff)).thenReturn(stats);
        when(restoreDrills.findByRestoreDrillRef("restore-drill-2026-06"))
                .thenReturn(Optional.of(passedDrill()));
        when(approvals.findActiveForDryRun(eq("terminal-reservation-request-snapshots"),
                eq("TENANT:10:courseflow|APP:3:lms"), eq(dryRun.dryRunId()),
                eq(dryRun.resultHash()), eq(500))).thenReturn(Optional.empty());
        when(access.sourceClientId(admin())).thenReturn("api-gateway");

        var response = service.requestApproval(new RetentionApprovalRequestDto(
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                dryRun.dryRunId(),
                dryRun.resultHash(),
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06"), admin(), "corr-approval");

        assertThat(response.status()).isEqualTo("PENDING_APPROVAL");
        assertThat(response.eligibleCount()).isEqualTo(8);
        assertThat(response.restoreDrillRef()).isEqualTo("restore-drill-2026-06");
        ArgumentCaptor<IncentiveRetentionApproval> captor =
                ArgumentCaptor.forClass(IncentiveRetentionApproval.class);
        verify(approvals).save(captor.capture());
        assertThat(captor.getValue().getRequestedBy()).isEqualTo("admin@example.com");
        assertThat(captor.getValue().getDryRunResultHash()).isEqualTo(dryRun.resultHash());
    }

    @Test
    void missingRestoreDrillBlocksApprovalRequest() {
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats stats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        ApprovedDryRun dryRun = approved(asOf, cutoff, stats, 500);
        when(reservations.dryRunTerminalRequestSnapshots("courseflow", "lms", cutoff)).thenReturn(stats);
        when(restoreDrills.findByRestoreDrillRef("restore-drill-2026-06")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.requestApproval(new RetentionApprovalRequestDto(
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                dryRun.dryRunId(),
                dryRun.resultHash(),
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06"), admin(), "corr-approval"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("Restore drill")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.RETENTION_RESTORE_DRILL_INVALID));
    }

    @Test
    void activeApprovalForSameDryRunBlocksDuplicateRequest() {
        Instant asOf = Instant.now();
        Instant cutoff = asOf.minus(java.time.Duration.ofDays(30));
        RetentionDryRunStats stats = stats(8, 2, "2026-05-01T10:00:00Z", "2026-05-10T10:00:00Z");
        ApprovedDryRun dryRun = approved(asOf, cutoff, stats, 500);
        when(reservations.dryRunTerminalRequestSnapshots("courseflow", "lms", cutoff)).thenReturn(stats);
        when(restoreDrills.findByRestoreDrillRef("restore-drill-2026-06"))
                .thenReturn(Optional.of(passedDrill()));
        when(approvals.findActiveForDryRun(eq("terminal-reservation-request-snapshots"),
                eq("TENANT:10:courseflow|APP:3:lms"), eq(dryRun.dryRunId()),
                eq(dryRun.resultHash()), eq(500))).thenReturn(Optional.of(approval("other@example.com")));

        assertThatThrownBy(() -> service.requestApproval(new RetentionApprovalRequestDto(
                "courseflow",
                "lms",
                "terminal-reservation-request-snapshots",
                asOf,
                Map.of(),
                500,
                dryRun.dryRunId(),
                dryRun.resultHash(),
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06"), admin(), "corr-approval"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("active retention approval")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.RETENTION_APPROVAL_ALREADY_EXISTS));
    }

    @Test
    void requesterCannotApproveOwnRetentionRequest() {
        IncentiveRetentionApproval approval = approval("admin@example.com");
        when(approvals.lockById(approval.getId())).thenReturn(Optional.of(approval));

        assertThatThrownBy(() -> service.approve(
                approval.getId(),
                new RetentionApprovalDecisionRequestDto("looks good"),
                admin(),
                "corr-approval"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("different operator")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.RETENTION_SELF_APPROVAL_BLOCKED));
    }

    @Test
    void expiredPendingApprovalCannotBeApprovedOrRejected() {
        IncentiveRetentionApproval approveTarget =
                approval("requester@example.com", Instant.now().minusSeconds(30));
        when(approvals.lockById(approveTarget.getId())).thenReturn(Optional.of(approveTarget));

        assertThatThrownBy(() -> service.approve(
                approveTarget.getId(),
                new RetentionApprovalDecisionRequestDto("looks good"),
                admin(),
                "corr-approval"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("expired")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.RETENTION_APPROVAL_EXPIRED));

        IncentiveRetentionApproval rejectTarget =
                approval("requester@example.com", Instant.now().minusSeconds(30));
        when(approvals.lockById(rejectTarget.getId())).thenReturn(Optional.of(rejectTarget));

        assertThatThrownBy(() -> service.reject(
                rejectTarget.getId(),
                new RetentionApprovalDecisionRequestDto("too old"),
                admin(),
                "corr-approval"))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("expired")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.RETENTION_APPROVAL_EXPIRED));
    }

    @Test
    void queueReturnsLimitedRetentionApprovalsWithNormalizedFilters() {
        Instant from = Instant.now().minusSeconds(3600);
        Instant to = Instant.now();
        IncentiveRetentionApproval first = approval("requester@example.com");
        IncentiveRetentionApproval second = approval("requester@example.com");
        IncentiveRetentionApproval overflow = approval("requester@example.com");
        when(approvals.search(
                eq("courseflow"),
                eq("lms"),
                eq(null),
                eq(null),
                eq(IncentiveRetentionApproval.STATUS_PENDING),
                eq("terminal-reservation-request-snapshots"),
                eq("%chg-42%"),
                eq("requester@example.com"),
                eq("reviewer@example.com"),
                eq("ops@example.com"),
                eq(true),
                any(Instant.class),
                eq(from),
                eq(to),
                any(Pageable.class)))
                .thenReturn(java.util.List.of(first, second, overflow));

        var response = service.queue(
                "APPLICATION",
                "courseflow",
                "lms",
                null,
                null,
                "pending_approval",
                "terminal-reservation-request-snapshots",
                "CHG-42",
                "Requester@Example.com",
                "Reviewer@Example.com",
                "Ops@Example.com",
                true,
                from,
                to,
                2,
                admin());

        assertThat(response.items()).extracting("approvalId")
                .containsExactly(first.getId(), second.getId());
        assertThat(response.limit()).isEqualTo(2);
        assertThat(response.hasMore()).isTrue();
        assertThat(response.generatedAt()).isNotNull();
        ArgumentCaptor<Pageable> pageable = ArgumentCaptor.forClass(Pageable.class);
        verify(approvals).search(
                eq("courseflow"),
                eq("lms"),
                eq(null),
                eq(null),
                eq(IncentiveRetentionApproval.STATUS_PENDING),
                eq("terminal-reservation-request-snapshots"),
                eq("%chg-42%"),
                eq("requester@example.com"),
                eq("reviewer@example.com"),
                eq("ops@example.com"),
                eq(true),
                any(Instant.class),
                eq(from),
                eq(to),
                pageable.capture());
        assertThat(pageable.getValue().getPageSize()).isEqualTo(3);
    }

    @Test
    void queueSupportsGlobalRetentionApprovalsForPlatformAdmins() {
        IncentiveRetentionApproval global = globalApproval("platform-admin@example.com");
        when(approvals.search(
                eq(null),
                eq(null),
                eq(global.getId()),
                eq(global.getDryRunId()),
                eq(IncentiveRetentionApproval.STATUS_APPROVED),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(null),
                eq(false),
                any(Instant.class),
                eq(null),
                eq(null),
                any(Pageable.class)))
                .thenReturn(java.util.List.of(global));

        var response = service.queue(
                "GLOBAL",
                null,
                null,
                global.getId(),
                global.getDryRunId(),
                "APPROVED",
                null,
                null,
                null,
                null,
                null,
                false,
                null,
                null,
                50,
                admin());

        assertThat(response.items()).hasSize(1);
        assertThat(response.items().getFirst().tenantId()).isNull();
        assertThat(response.items().getFirst().applicationId()).isNull();
        assertThat(response.items().getFirst().reason()).isEqualTo("privacy monthly redaction");
        assertThat(response.items().getFirst().correlationId()).isEqualTo("corr-approval");
    }

    @Test
    void queueRejectsUnsupportedRetentionStatus() {
        assertThatThrownBy(() -> service.queue(
                "APPLICATION",
                "courseflow",
                "lms",
                null,
                null,
                "NOT_A_STATUS",
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                50,
                admin()))
                .isInstanceOf(edu.courseflow.commonlibrary.exception.BadRequestException.class)
                .hasMessageContaining("Unsupported retention approval status");
    }

    @Test
    void globalQueueRejectsTenantScopeParams() {
        assertThatThrownBy(() -> service.queue(
                "GLOBAL",
                "courseflow",
                "lms",
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                50,
                admin()))
                .isInstanceOf(edu.courseflow.commonlibrary.exception.BadRequestException.class)
                .hasMessageContaining("GLOBAL");
    }

    @Test
    void evidencePackIncludesSafeApprovalRestoreExecutionAndAuditSummary() {
        IncentiveRetentionApproval approval = approval("requester@example.com");
        IncentiveRestoreDrill drill = passedDrill();
        IncentiveRetentionOperation operation = operation(approval);
        operation.complete(5, """
                {"executionId":"%s","status":"SUCCEEDED","hasMore":true}
                """.formatted(operation.getId()), Instant.now());
        when(approvals.findById(approval.getId())).thenReturn(Optional.of(approval));
        when(restoreDrills.findByRestoreDrillRef(approval.getRestoreDrillRef())).thenReturn(Optional.of(drill));
        when(operations.findByApprovalId(approval.getId())).thenReturn(Optional.of(operation));
        when(access.sourceClientId(admin())).thenReturn("api-gateway");
        when(auditEvents.timelineByAggregateIds(
                eq("courseflow"),
                eq("lms"),
                any(),
                any(Pageable.class)))
                .thenReturn(java.util.List.of(new IncentiveAuditEvent(
                        "courseflow",
                        "lms",
                        approval.getId().toString(),
                        "retention-approval",
                        "retention.request_created",
                        "requester@example.com",
                        "privacy",
                        """
                                {"approvalId":"%s","dryRunId":"%s","approvedResultHash":"%s","eligibleCount":8,"profileId":"secret-profile","requestJson":{"raw":true},"responseJson":{"raw":true},"requestHash":"secret-hash"}
                                """.formatted(approval.getId(), approval.getDryRunId(), approval.getDryRunResultHash()),
                        "corr-approval",
                        "api-gateway")));

        var pack = service.evidencePack(approval.getId(), admin(), "corr-evidence");

        assertThat(pack.schemaVersion()).isEqualTo("retention-evidence-pack.v1");
        assertThat(pack.approval().approvalId()).isEqualTo(approval.getId());
        assertThat(pack.restoreDrill().restoreDrillRef()).isEqualTo(drill.getRestoreDrillRef());
        assertThat(pack.execution().executionId()).isEqualTo(operation.getId());
        assertThat(pack.execution().hasMore()).isTrue();
        assertThat(pack.auditTrail()).hasSize(1);
        assertThat(pack.auditTrail().getFirst().payloadSummary())
                .containsKeys("approvalId", "dryRunId", "approvedResultHash", "eligibleCount")
                .doesNotContainKeys("profileId", "requestJson", "responseJson", "requestHash");
        verify(auditEvents).save(any(IncentiveAuditEvent.class));
    }

    @Test
    void evidencePackExportReturnsHashedContentWithoutRawRequestMaterial() {
        IncentiveRetentionApproval approval = approval("requester@example.com");
        IncentiveRestoreDrill drill = passedDrill();
        IncentiveRetentionOperation operation = operation(approval);
        when(approvals.findById(approval.getId())).thenReturn(Optional.of(approval));
        when(restoreDrills.findByRestoreDrillRef(approval.getRestoreDrillRef())).thenReturn(Optional.of(drill));
        when(operations.findByApprovalId(approval.getId())).thenReturn(Optional.of(operation));
        when(access.sourceClientId(admin())).thenReturn("api-gateway");
        when(auditEvents.timelineByAggregateIds(eq("courseflow"), eq("lms"), any(), any(Pageable.class)))
                .thenReturn(java.util.List.of());

        var export = service.evidencePackExport(approval.getId(), "json", admin(), "corr-export");

        assertThat(export.filename()).startsWith("retention-evidence-pack-" + approval.getId());
        assertThat(export.contentType()).isEqualTo("application/json");
        assertThat(export.contentSha256()).startsWith("sha256:");
        assertThat(export.content()).contains("retention-evidence-pack.v1", approval.getId().toString());
        assertThat(export.content()).doesNotContain("requestHash", "responseJson", "secret-profile", "raw-idempotency-key");
        verify(auditEvents).save(any(IncentiveAuditEvent.class));
    }

    private static IncentiveRestoreDrill passedDrill() {
        Instant now = Instant.now();
        return new IncentiveRestoreDrill(
                "restore-drill-2026-06",
                "cf_promotion",
                "backups/postgres/codex/cf_promotion.dump",
                "sha256:" + "a".repeat(64),
                "PASSED",
                now.minusSeconds(60),
                now.plusSeconds(3600),
                "platform-admin@example.com",
                "restore checked",
                "corr-drill",
                "api-gateway");
    }

    private static IncentiveRetentionApproval approval(String requestedBy) {
        return approval(requestedBy, Instant.now().plus(java.time.Duration.ofMinutes(60)));
    }

    private static IncentiveRetentionApproval approval(String requestedBy, Instant expiresAt) {
        Instant asOf = Instant.now();
        return new IncentiveRetentionApproval(
                "terminal-reservation-request-snapshots",
                "v1",
                "incentive_reservation_request_snapshots",
                "TENANT:10:courseflow|APP:3:lms",
                "courseflow",
                "lms",
                asOf,
                asOf.minus(java.time.Duration.ofDays(30)),
                30,
                UUID.randomUUID(),
                "sha256:abc",
                8,
                500,
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                requestedBy,
                "corr-approval",
                "api-gateway",
                expiresAt);
    }

    private static IncentiveRetentionOperation operation(IncentiveRetentionApproval approval) {
        return new IncentiveRetentionOperation(
                UUID.randomUUID(),
                approval.getPolicyId(),
                approval.getPolicyVersion(),
                approval.getTargetDataset(),
                approval.getScopeKey(),
                approval.getId(),
                approval.getTenantId(),
                approval.getApplicationId(),
                approval.getDryRunId(),
                approval.getDryRunResultHash(),
                approval.getCutoffAt(),
                approval.getEligibleCount(),
                approval.getBatchLimit(),
                "raw-idempotency-key",
                "request-hash-that-must-not-leak",
                approval.getReason(),
                approval.getChangeTicket(),
                approval.getRestoreDrillRef(),
                "reviewer@example.com",
                "ops@example.com",
                "corr-exec");
    }

    private static IncentiveRetentionApproval globalApproval(String requestedBy) {
        Instant asOf = Instant.now();
        return new IncentiveRetentionApproval(
                "terminal-reservation-request-snapshots",
                "v1",
                "incentive_reservation_request_snapshots",
                "GLOBAL",
                null,
                null,
                asOf,
                asOf.minus(java.time.Duration.ofDays(30)),
                30,
                UUID.randomUUID(),
                "sha256:abc",
                8,
                500,
                "privacy monthly redaction",
                "CHG-42",
                "restore-drill-2026-06",
                requestedBy,
                "corr-approval",
                "api-gateway",
                asOf.plus(java.time.Duration.ofMinutes(60)));
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

    private static CurrentUser admin() {
        return new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of());
    }

    private static String hash(String raw) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return "sha256:" + HexFormat.of().formatHex(digest.digest(raw.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 not available", ex);
        }
    }

    private record ApprovedDryRun(UUID dryRunId, String resultHash) {
    }
}
