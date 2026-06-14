package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.RetentionDryRunRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveIdempotencyKeyRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import edu.courseflow.promotion.repository.RetentionDryRunStats;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RetentionDryRunServiceTest {

    @Mock
    IncentiveIdempotencyKeyRepository idempotencyKeys;
    @Mock
    OutboxEventRepository outboxEvents;
    @Mock
    IncentiveReservationRepository reservations;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveMetrics metrics;

    private RetentionDryRunService service;
    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @BeforeEach
    void setUp() {
        service = new RetentionDryRunService(
                new RetentionPolicyRegistry(),
                idempotencyKeys,
                outboxEvents,
                reservations,
                access,
                auditEvents,
                objectMapper,
                metrics,
                true);
    }

    @Test
    void scopedDryRunReturnsAggregateOnlyResultsAndAudit() throws Exception {
        CurrentUser admin = admin();
        Instant asOf = Instant.parse("2026-06-14T10:00:00Z");
        when(idempotencyKeys.dryRunExpiredKeys(
                eq("courseflow"),
                eq("lms"),
                eq(Instant.parse("2026-06-13T10:00:00Z"))))
                .thenReturn(stats(3, 2, "2026-06-01T10:00:00Z", "2026-06-10T10:00:00Z"));
        when(reservations.dryRunTerminalRequestSnapshots(
                eq("courseflow"),
                eq("lms"),
                eq(Instant.parse("2026-05-15T10:00:00Z"))))
                .thenReturn(stats(5, 4, "2026-04-01T10:00:00Z", "2026-05-01T10:00:00Z"));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");

        var response = service.dryRun(new RetentionDryRunRequestDto(
                "courseflow",
                "lms",
                List.of("expired-idempotency-keys", "terminal-reservation-request-snapshots"),
                asOf,
                Map.of(),
                100,
                "monthly review"), admin, "corr-retention");

        assertThat(response.dryRun()).isTrue();
        assertThat(response.nonDestructive()).isTrue();
        assertThat(response.tenantId()).isEqualTo("courseflow");
        assertThat(response.applicationId()).isEqualTo("lms");
        assertThat(response.resultHash()).startsWith("sha256:");
        assertThat(response.results())
                .extracting(result -> result.policyId() + "=" + result.eligibleCount() + "/" + result.blockedCount())
                .containsExactly(
                        "expired-idempotency-keys=3/2",
                        "terminal-reservation-request-snapshots=5/4");
        assertThat(response.results())
                .filteredOn(result -> "terminal-reservation-request-snapshots".equals(result.policyId()))
                .singleElement()
                .satisfies(result -> assertThat(result.destructiveExecutionSupported()).isTrue());
        assertThat(objectMapper.writeValueAsString(response))
                .doesNotContain("request_json")
                .doesNotContain("response_json")
                .doesNotContain("payload")
                .doesNotContain("profileId")
                .doesNotContain("externalReference")
                .doesNotContain("normalizedCode")
                .doesNotContain("fingerprint");
        verify(access).requireAdminAccess("courseflow", "lms", admin);

        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        IncentiveAuditEvent audit = auditCaptor.getValue();
        assertThat(audit.getAction()).isEqualTo("retention.dry_run_requested");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-retention");
        assertThat(audit.getPayloadJson()).contains("expired-idempotency-keys");
        assertThat(audit.getPayloadJson()).doesNotContain("request_json");
        assertThat(audit.getPayloadJson()).doesNotContain("profileId");
        assertThat(audit.getPayloadJson()).doesNotContain("externalReference");
    }

    @Test
    void globalOutboxDryRunRequiresPlatformAdmin() {
        CurrentUser admin = admin();
        Instant asOf = Instant.parse("2026-06-14T10:00:00Z");
        when(outboxEvents.dryRunPublishedEvents(eq(Instant.parse("2026-05-31T10:00:00Z"))))
                .thenReturn(stats(7, 1, "2026-05-01T10:00:00Z", "2026-05-15T10:00:00Z"));

        var response = service.dryRun(new RetentionDryRunRequestDto(
                null,
                null,
                List.of("published-outbox-events"),
                asOf,
                Map.of(),
                null,
                null), admin, null);

        assertThat(response.results()).singleElement()
                .satisfies(result -> {
                    assertThat(result.policyId()).isEqualTo("published-outbox-events");
                    assertThat(result.eligibleCount()).isEqualTo(7);
                    assertThat(result.blockedCount()).isEqualTo(1);
                    assertThat(result.blockedReason()).isNull();
                });
        verify(access).requirePlatformAdmin(admin);
    }

    @Test
    void scopedOutboxDryRunIsBlockedBecauseOutboxRowsAreGlobal() {
        CurrentUser admin = admin();

        var response = service.dryRun(new RetentionDryRunRequestDto(
                "courseflow",
                "lms",
                List.of("published-outbox-events"),
                Instant.parse("2026-06-14T10:00:00Z"),
                Map.of(),
                null,
                null), admin, null);

        assertThat(response.results()).singleElement()
                .satisfies(result -> {
                    assertThat(result.eligibleCount()).isZero();
                    assertThat(result.blockedReason()).isEqualTo("GLOBAL_ONLY_POLICY");
                });
        assertThat(response.warnings()).contains("published-outbox-events is global because outbox_events does not carry tenant/application columns");
        verifyNoInteractions(outboxEvents);
    }

    @Test
    void partialScopeIsRejected() {
        assertThatThrownBy(() -> service.dryRun(new RetentionDryRunRequestDto(
                "courseflow",
                null,
                List.of("expired-idempotency-keys"),
                Instant.parse("2026-06-14T10:00:00Z"),
                Map.of(),
                null,
                null), admin(), null))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("tenantId and applicationId");
    }

    @Test
    void retentionOverrideBelowMinimumIsRejected() {
        assertThatThrownBy(() -> service.dryRun(new RetentionDryRunRequestDto(
                null,
                null,
                List.of("published-outbox-events"),
                Instant.parse("2026-06-14T10:00:00Z"),
                Map.of("published-outbox-events", 1),
                null,
                null), admin(), null))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("below minimum");
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
                return oldest == null ? null : Instant.parse(oldest);
            }

            @Override
            public Instant getNewestCandidateAt() {
                return newest == null ? null : Instant.parse(newest);
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
}
