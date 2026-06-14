package edu.courseflow.promotion.service;

import edu.courseflow.promotion.repository.OutboxEventRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Tags;
import java.time.Duration;
import java.time.Instant;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class IncentiveMetrics {

    private final MeterRegistry registry;
    private final OutboxEventRepository outboxEvents;
    private final IncentiveReservationRepository reservations;
    private final IncentiveRetentionOperationRepository retentionOperations;
    private final AtomicLong unpublishedOutboxCount = new AtomicLong();
    private final AtomicLong oldestUnpublishedOutboxAgeSeconds = new AtomicLong();
    private final AtomicLong expiredReservationBacklog = new AtomicLong();
    private final AtomicLong oldestExpiredReservationAgeSeconds = new AtomicLong();
    private final AtomicLong staleRetentionExecutionInProgress = new AtomicLong();

    public IncentiveMetrics(MeterRegistry registry,
                            OutboxEventRepository outboxEvents,
                            IncentiveReservationRepository reservations,
                            IncentiveRetentionOperationRepository retentionOperations) {
        this.registry = registry;
        this.outboxEvents = outboxEvents;
        this.reservations = reservations;
        this.retentionOperations = retentionOperations;
        registerOutboxGauges();
        registerReservationExpiryGauges();
        registerRetentionExecutionGauges();
        refreshOutboxGauges();
    }

    public void versionTransition(String action, String result) {
        registry.counter("promotion.version.transition",
                Tags.of("action", safe(action), "result", safe(result))).increment();
    }

    public void reversal(String result, String reason) {
        registry.counter("promotion.reversal",
                Tags.of("result", safe(result), "reason", reason(reason))).increment();
    }

    public void auditQuery(String view, Duration duration) {
        registry.timer("promotion.audit.query.duration", Tags.of("view", safe(view))).record(duration);
    }

    public void reconciliationQuery(String result, Duration duration) {
        Tags tags = Tags.of("result", safe(result));
        registry.counter("promotion.reconciliation.query.requests", tags).increment();
        registry.timer("promotion.reconciliation.query.duration", tags).record(duration);
    }

    public void runtimeOperation(String operation, String result, String reason, Duration duration) {
        Tags tags = Tags.of("operation", safe(operation), "result", safe(result), "reason", reason(reason));
        registry.counter("promotion.runtime.operation", tags).increment();
        registry.timer("promotion.runtime.operation.duration", tags).record(duration);
    }

    public void idempotency(String operation, String result) {
        registry.counter("promotion.idempotency",
                Tags.of("operation", safe(operation), "result", safe(result))).increment();
    }

    public void quota(String result, String scopeType) {
        registry.counter("promotion.quota",
                Tags.of("result", safe(result), "scope_type", safe(scopeType))).increment();
    }

    public void quotaReserveFallback(String result) {
        registry.counter("promotion.quota.reserve.fallback",
                Tags.of("result", safe(result))).increment();
    }

    public void couponMatch(String operation, String result, boolean couponSupplied, boolean couponRequired) {
        registry.counter("promotion.coupon.match",
                Tags.of(
                        "operation", safe(operation),
                        "result", safe(result),
                        "coupon_supplied", Boolean.toString(couponSupplied),
                        "coupon_required", Boolean.toString(couponRequired))).increment();
    }

    public void couponLookup(String operation, String storagePath, boolean couponSupplied, boolean couponRequired) {
        registry.counter("promotion.coupon.lookup",
                Tags.of(
                        "operation", safe(operation),
                        "storage_path", safe(storagePath),
                        "coupon_supplied", Boolean.toString(couponSupplied),
                        "coupon_required", Boolean.toString(couponRequired))).increment();
    }

    public void couponAbuseGuard(String operation, String mode, String scope, String result) {
        registry.counter("promotion.coupon.abuse_guard",
                Tags.of(
                        "operation", safe(operation),
                        "mode", safe(mode),
                        "scope", safe(scope),
                        "result", safe(result))).increment();
    }

    public void adminOperationRateGuard(String operation, String mode, String scope, String result) {
        registry.counter("promotion.admin_operation.rate_guard",
                Tags.of(
                        "operation", safe(operation),
                        "mode", safe(mode),
                        "scope", safe(scope),
                        "result", safe(result))).increment();
    }

    public void couponImportDryRun(String result, long rows, Duration duration) {
        Tags tags = Tags.of("result", safe(result));
        registry.counter("promotion.coupon.import.dry_run.requests", tags).increment();
        registry.summary("promotion.coupon.import.dry_run.rows", tags).record(Math.max(0, rows));
        registry.timer("promotion.coupon.import.dry_run.duration", tags).record(duration);
    }

    public void couponImportDryRunCleanup(String result, long deleted, Duration duration) {
        Tags tags = Tags.of("result", safe(result));
        registry.counter("promotion.coupon.import.dry_run.cleanup.runs", tags).increment();
        registry.summary("promotion.coupon.import.dry_run.cleanup.deleted", tags).record(Math.max(0, deleted));
        registry.timer("promotion.coupon.import.dry_run.cleanup.duration", tags).record(duration);
    }

    public void couponImportCommit(String result, long rows, Duration duration) {
        Tags tags = Tags.of("result", safe(result));
        registry.counter("promotion.coupon.import.commit.requests", tags).increment();
        registry.summary("promotion.coupon.import.commit.rows", tags).record(Math.max(0, rows));
        registry.timer("promotion.coupon.import.commit.duration", tags).record(duration);
    }

    public void couponImportQuery(String view, String result, Duration duration) {
        Tags tags = Tags.of("view", safe(view), "result", safe(result));
        registry.counter("promotion.coupon.import.query.requests", tags).increment();
        registry.timer("promotion.coupon.import.query.duration", tags).record(duration);
    }

    public void reservationExpiry(String result, int expiredCount, Duration duration) {
        Tags tags = Tags.of("result", safe(result));
        registry.counter("promotion.reservation.expiry.runs", tags).increment();
        registry.counter("promotion.reservation.expiry.expired", tags).increment(Math.max(0, expiredCount));
        registry.timer("promotion.reservation.expiry.duration", tags).record(duration);
    }

    public void retentionDryRun(String policyId, String targetDataset, String result, long candidates,
                                Duration duration) {
        Tags tags = Tags.of(
                "policy_id", safe(policyId),
                "target_dataset", safe(targetDataset),
                "result", safe(result));
        registry.counter("promotion.retention.dry_run.requests", tags).increment();
        registry.summary("promotion.retention.dry_run.candidates", tags).record(Math.max(0, candidates));
        registry.timer("promotion.retention.dry_run.duration", tags).record(duration);
    }

    public void retentionExecution(String policyId, String targetDataset, String result, long redacted,
                                   Duration duration) {
        Tags tags = Tags.of(
                "policy_id", safe(policyId),
                "target_dataset", safe(targetDataset),
                "result", safe(result));
        registry.counter("promotion.retention.execution.requests", tags).increment();
        registry.summary("promotion.retention.execution.redacted", tags).record(Math.max(0, redacted));
        registry.timer("promotion.retention.execution.duration", tags).record(duration);
    }

    private void registerOutboxGauges() {
        Gauge.builder("promotion.outbox.unpublished", unpublishedOutboxCount, AtomicLong::get)
                .tag("aggregate_type", "incentive-redemption")
                .description("Unpublished promotion outbox events awaiting relay")
                .register(registry);
        Gauge.builder("promotion.outbox.oldest.unpublished.age.seconds",
                        oldestUnpublishedOutboxAgeSeconds, AtomicLong::get)
                .tag("aggregate_type", "incentive-redemption")
                .description("Age in seconds of the oldest unpublished promotion outbox event")
                .register(registry);
    }

    private void registerReservationExpiryGauges() {
        Gauge.builder("promotion.reservation.expiry.backlog", expiredReservationBacklog, AtomicLong::get)
                .description("Expired reserved incentive reservations awaiting expiry processing")
                .register(registry);
        Gauge.builder("promotion.reservation.expiry.oldest.age.seconds",
                        oldestExpiredReservationAgeSeconds, AtomicLong::get)
                .description("Age in seconds of the oldest expired reserved incentive reservation")
                .register(registry);
    }

    private void registerRetentionExecutionGauges() {
        Gauge.builder("promotion.retention.execution.stale.in_progress",
                        staleRetentionExecutionInProgress, AtomicLong::get)
                .description("Retention execution operations still in progress after the safety window")
                .register(registry);
    }

    @Scheduled(fixedDelayString = "${courseflow.promotion.metrics.outbox-refresh-ms:30000}")
    public void refreshOutboxGauges() {
        try {
            unpublishedOutboxCount.set(outboxEvents.countUnpublishedIncentiveEvents());
            oldestUnpublishedOutboxAgeSeconds.set(Math.max(
                    0L,
                    Math.round(outboxEvents.oldestUnpublishedIncentiveAgeSeconds())));
            expiredReservationBacklog.set(reservations.countExpiredReservedBacklog());
            oldestExpiredReservationAgeSeconds.set(Math.max(
                    0L,
                    Math.round(reservations.oldestExpiredReservedAgeSeconds())));
            staleRetentionExecutionInProgress.set(retentionOperations.countByStatusAndStartedAtBefore(
                    "IN_PROGRESS",
                    Instant.now().minus(Duration.ofMinutes(15))));
            registry.counter("promotion.metrics.refresh", Tags.of("result", "success")).increment();
        } catch (RuntimeException ex) {
            registry.counter("promotion.metrics.refresh", Tags.of("result", "error")).increment();
        }
    }

    private String safe(String value) {
        if (value == null || value.isBlank()) {
            return "unknown";
        }
        return value.trim().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_\\-]", "_");
    }

    private String reason(String value) {
        return safe(value == null || value.isBlank() ? "none" : value);
    }
}
