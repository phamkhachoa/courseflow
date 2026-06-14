package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import org.junit.jupiter.api.Test;

class IncentiveMetricsTest {

    private final OutboxEventRepository outboxEvents = org.mockito.Mockito.mock(OutboxEventRepository.class);
    private final IncentiveReservationRepository reservations =
            org.mockito.Mockito.mock(IncentiveReservationRepository.class);
    private final IncentiveRetentionOperationRepository retentionOperations =
            org.mockito.Mockito.mock(IncentiveRetentionOperationRepository.class);
    private final SimpleMeterRegistry registry = new SimpleMeterRegistry();

    @Test
    void recordsRuntimeIdempotencyQuotaAndExpiryMetricsWithBoundedTags() {
        IncentiveMetrics metrics = new IncentiveMetrics(registry, outboxEvents, reservations, retentionOperations);

        metrics.runtimeOperation("reserve", "success", "RESERVED", Duration.ofMillis(25));
        metrics.idempotency("reserve", "payload_conflict");
        metrics.quota("exhausted", "CAMPAIGN_PROFILE");
        metrics.couponMatch("preview", "holder_mismatch", true, true);
        metrics.couponLookup("preview", "legacy_raw", true, true);
        metrics.couponAbuseGuard("evaluate", "enforced", "profile", "limited");
        metrics.adminOperationRateGuard("coupon_import_dry_run", "enforced", "actor", "limited");
        metrics.couponImportDryRun("commit_ready", 2, Duration.ofMillis(11));
        metrics.couponImportDryRunCleanup("success", 1, Duration.ofMillis(9));
        metrics.couponImportCommit("success", 2, Duration.ofMillis(14));
        metrics.reservationExpiry("success", 3, Duration.ofMillis(10));
        metrics.retentionDryRun("expired-idempotency-keys", "incentive_idempotency_keys",
                "success", 5, Duration.ofMillis(12));
        metrics.retentionExecution("terminal-reservation-request-snapshots",
                "incentive_reservation_request_snapshots", "success", 4, Duration.ofMillis(13));

        assertThat(registry.get("promotion.runtime.operation")
                .tag("operation", "reserve")
                .tag("result", "success")
                .tag("reason", "reserved")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.runtime.operation.duration")
                .tag("operation", "reserve")
                .tag("result", "success")
                .tag("reason", "reserved")
                .timer()
                .count()).isEqualTo(1);
        assertThat(registry.get("promotion.idempotency")
                .tag("operation", "reserve")
                .tag("result", "payload_conflict")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.quota")
                .tag("result", "exhausted")
                .tag("scope_type", "campaign_profile")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.match")
                .tag("operation", "preview")
                .tag("result", "holder_mismatch")
                .tag("coupon_supplied", "true")
                .tag("coupon_required", "true")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.lookup")
                .tag("operation", "preview")
                .tag("storage_path", "legacy_raw")
                .tag("coupon_supplied", "true")
                .tag("coupon_required", "true")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.abuse_guard")
                .tag("operation", "evaluate")
                .tag("mode", "enforced")
                .tag("scope", "profile")
                .tag("result", "limited")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.admin_operation.rate_guard")
                .tag("operation", "coupon_import_dry_run")
                .tag("mode", "enforced")
                .tag("scope", "actor")
                .tag("result", "limited")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.import.dry_run.requests")
                .tag("result", "commit_ready")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.import.dry_run.rows")
                .tag("result", "commit_ready")
                .summary()
                .totalAmount()).isEqualTo(2.0);
        assertThat(registry.get("promotion.coupon.import.dry_run.cleanup.runs")
                .tag("result", "success")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.import.dry_run.cleanup.deleted")
                .tag("result", "success")
                .summary()
                .totalAmount()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.import.commit.requests")
                .tag("result", "success")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.coupon.import.commit.rows")
                .tag("result", "success")
                .summary()
                .totalAmount()).isEqualTo(2.0);
        assertThat(registry.get("promotion.reservation.expiry.runs")
                .tag("result", "success")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.reservation.expiry.expired")
                .tag("result", "success")
                .counter()
                .count()).isEqualTo(3.0);
        assertThat(registry.get("promotion.retention.dry_run.requests")
                .tag("policy_id", "expired-idempotency-keys")
                .tag("target_dataset", "incentive_idempotency_keys")
                .tag("result", "success")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.retention.dry_run.candidates")
                .tag("policy_id", "expired-idempotency-keys")
                .tag("target_dataset", "incentive_idempotency_keys")
                .tag("result", "success")
                .summary()
                .totalAmount()).isEqualTo(5.0);
        assertThat(registry.get("promotion.retention.execution.requests")
                .tag("policy_id", "terminal-reservation-request-snapshots")
                .tag("target_dataset", "incentive_reservation_request_snapshots")
                .tag("result", "success")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.retention.execution.redacted")
                .tag("policy_id", "terminal-reservation-request-snapshots")
                .tag("target_dataset", "incentive_reservation_request_snapshots")
                .tag("result", "success")
                .summary()
                .totalAmount()).isEqualTo(4.0);
    }

    @Test
    void refreshesOutboxAndReservationBacklogGaugeCache() {
        when(outboxEvents.countUnpublishedIncentiveEvents()).thenReturn(7L);
        when(outboxEvents.oldestUnpublishedIncentiveAgeSeconds()).thenReturn(42.4);
        when(reservations.countExpiredReservedBacklog()).thenReturn(2L);
        when(reservations.oldestExpiredReservedAgeSeconds()).thenReturn(60.2);

        when(retentionOperations.countByStatusAndStartedAtBefore(org.mockito.Mockito.eq("IN_PROGRESS"),
                org.mockito.Mockito.any())).thenReturn(1L);

        IncentiveMetrics metrics = new IncentiveMetrics(registry, outboxEvents, reservations, retentionOperations);
        metrics.refreshOutboxGauges();

        assertThat(registry.get("promotion.outbox.unpublished")
                .tag("aggregate_type", "incentive-redemption")
                .gauge()
                .value()).isEqualTo(7.0);
        assertThat(registry.get("promotion.outbox.oldest.unpublished.age.seconds")
                .tag("aggregate_type", "incentive-redemption")
                .gauge()
                .value()).isEqualTo(42.0);
        assertThat(registry.get("promotion.reservation.expiry.backlog")
                .gauge()
                .value()).isEqualTo(2.0);
        assertThat(registry.get("promotion.reservation.expiry.oldest.age.seconds")
                .gauge()
                .value()).isEqualTo(60.0);
        assertThat(registry.get("promotion.retention.execution.stale.in_progress")
                .gauge()
                .value()).isEqualTo(1.0);
    }

    @Test
    void refreshFailurePreservesLastKnownGaugeValuesAndRecordsError() {
        when(outboxEvents.countUnpublishedIncentiveEvents())
                .thenReturn(7L)
                .thenThrow(new IllegalStateException("database unavailable"));
        when(outboxEvents.oldestUnpublishedIncentiveAgeSeconds()).thenReturn(42.4);
        when(reservations.countExpiredReservedBacklog()).thenReturn(2L);
        when(reservations.oldestExpiredReservedAgeSeconds()).thenReturn(60.2);

        IncentiveMetrics metrics = new IncentiveMetrics(registry, outboxEvents, reservations, retentionOperations);
        metrics.refreshOutboxGauges();

        assertThat(registry.get("promotion.outbox.unpublished")
                .tag("aggregate_type", "incentive-redemption")
                .gauge()
                .value()).isEqualTo(7.0);
        assertThat(registry.get("promotion.reservation.expiry.backlog")
                .gauge()
                .value()).isEqualTo(2.0);
        assertThat(registry.get("promotion.metrics.refresh")
                .tag("result", "success")
                .counter()
                .count()).isEqualTo(1.0);
        assertThat(registry.get("promotion.metrics.refresh")
                .tag("result", "error")
                .counter()
                .count()).isEqualTo(1.0);
    }
}
