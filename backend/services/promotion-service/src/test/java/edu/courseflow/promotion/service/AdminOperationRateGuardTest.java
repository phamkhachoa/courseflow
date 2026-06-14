package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

import edu.courseflow.commonlibrary.exception.CodedResponseStatusException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class AdminOperationRateGuardTest {

    @Test
    void enforcedModeBlocksBurstWithoutRawActorClientOrContentInKeys() {
        RecordingStore store = new RecordingStore();
        AdminOperationRateGuard guard = guard(store, properties(AdminOperationRateGuardProperties.Mode.ENFORCED, 1), registry());
        UUID campaignId = UUID.randomUUID();
        CurrentUser admin = user(42L);

        assertThat(guard.check("coupon_import_dry_run", "courseflow", "lms", campaignId,
                admin, "api-gateway-secret-client", "raw-csv-content-hash").blocked()).isFalse();
        AdminOperationRateGuard.Decision blocked = guard.check("coupon_import_dry_run", "courseflow", "lms", campaignId,
                admin, "api-gateway-secret-client", "raw-csv-content-hash");

        assertThat(blocked.blocked()).isTrue();
        assertThat(String.join(" ", store.keys()))
                .doesNotContain(":actor:42")
                .doesNotContain("api-gateway-secret-client")
                .doesNotContain("raw-csv-content-hash");
    }

    @Test
    void requireAllowedThrowsStableErrorCodeWhenRateLimited() {
        AdminOperationRateGuard guard = guard(
                new RecordingStore(),
                properties(AdminOperationRateGuardProperties.Mode.ENFORCED, 1),
                registry());
        UUID campaignId = UUID.randomUUID();
        CurrentUser admin = user(42L);

        guard.requireAllowed("coupon_import_dry_run", "courseflow", "lms", campaignId,
                admin, "api-gateway", "content-hash");

        assertThatThrownBy(() -> guard.requireAllowed("coupon_import_dry_run", "courseflow", "lms", campaignId,
                admin, "api-gateway", "content-hash"))
                .isInstanceOf(CodedResponseStatusException.class)
                .satisfies(error -> {
                    CodedResponseStatusException exception = (CodedResponseStatusException) error;
                    assertThat(exception.getStatusCode().value()).isEqualTo(429);
                    assertThat(exception.errorCode()).isEqualTo(PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED);
                });
    }

    @Test
    void shadowModeRecordsLimitButAllowsRequest() {
        SimpleMeterRegistry registry = registry();
        RecordingStore store = new RecordingStore();
        AdminOperationRateGuard guard = guard(store, properties(AdminOperationRateGuardProperties.Mode.SHADOW, 1), registry);
        UUID campaignId = UUID.randomUUID();
        CurrentUser admin = user(42L);

        guard.check("coupon_import_issue_export", "courseflow", "lms", campaignId, admin, "api-gateway", "dry-run-1");
        AdminOperationRateGuard.Decision second =
                guard.check("coupon_import_issue_export", "courseflow", "lms", campaignId, admin, "api-gateway", "dry-run-1");

        assertThat(second.blocked()).isFalse();
        assertThat(registry.get("promotion.admin_operation.rate_guard")
                .tag("operation", "coupon_import_issue_export")
                .tag("mode", "shadow")
                .tag("scope", "actor")
                .tag("result", "shadow_limited")
                .counter()
                .count()).isEqualTo(1.0);
    }

    @Test
    void storeFailurePolicyCanFailOpenOrClosed() {
        AdminOperationRateGuardProperties allow = properties(AdminOperationRateGuardProperties.Mode.ENFORCED, 1);
        allow.setFailPolicy(AdminOperationRateGuardProperties.FailPolicy.ALLOW_WITH_ALERT);
        allow.validate();
        AdminOperationRateGuard allowGuard = guard(new ThrowingStore(), allow, registry());

        assertThat(allowGuard.check("coupon_generate", "courseflow", "lms", UUID.randomUUID(),
                user(1L), "api-gateway", null).blocked()).isFalse();

        AdminOperationRateGuardProperties deny = properties(AdminOperationRateGuardProperties.Mode.ENFORCED, 1);
        deny.setFailPolicy(AdminOperationRateGuardProperties.FailPolicy.DENY);
        deny.validate();
        AdminOperationRateGuard denyGuard = guard(new ThrowingStore(), deny, registry());

        assertThat(denyGuard.check("coupon_generate", "courseflow", "lms", UUID.randomUUID(),
                user(1L), "api-gateway", null).blocked()).isTrue();
    }

    @Test
    void disabledModeDoesNotTouchStore() {
        RecordingStore store = new RecordingStore();
        AdminOperationRateGuard guard = guard(store, properties(AdminOperationRateGuardProperties.Mode.DISABLED, 1), registry());

        assertThat(guard.check("coupon_import_commit", "courseflow", "lms", UUID.randomUUID(),
                user(1L), "api-gateway", null).blocked()).isFalse();

        assertThat(store.keys()).isEmpty();
    }

    private AdminOperationRateGuard guard(CouponAbuseRateLimitStore store,
                                          AdminOperationRateGuardProperties properties,
                                          SimpleMeterRegistry registry) {
        return new AdminOperationRateGuard(properties, store, metrics(registry));
    }

    private AdminOperationRateGuardProperties properties(AdminOperationRateGuardProperties.Mode mode, int actorCapacity) {
        AdminOperationRateGuardProperties properties = new AdminOperationRateGuardProperties();
        properties.setMode(mode);
        properties.setKeyId("test");
        properties.setPepper("test-admin-operation-rate-pepper-32-byte-value");
        properties.setWindowSeconds(60);
        properties.setActorCapacity(actorCapacity);
        properties.setSourceClientCapacity(100);
        properties.setApplicationCapacity(100);
        properties.setCampaignCapacity(100);
        properties.setContentCapacity(100);
        properties.setMissingIdentityCapacity(1);
        properties.validate();
        return properties;
    }

    private IncentiveMetrics metrics(SimpleMeterRegistry registry) {
        return new IncentiveMetrics(
                registry,
                mock(OutboxEventRepository.class),
                mock(IncentiveReservationRepository.class),
                mock(IncentiveRetentionOperationRepository.class));
    }

    private SimpleMeterRegistry registry() {
        return new SimpleMeterRegistry();
    }

    private CurrentUser user(long id) {
        return new CurrentUser(id, "admin@example.com", "ADMIN", Set.of("ADMIN"), Set.of(), null);
    }

    private static final class RecordingStore implements CouponAbuseRateLimitStore {
        private final Map<String, Long> counts = new LinkedHashMap<>();
        private final List<String> keys = new ArrayList<>();

        @Override
        public Hit hit(String key, int capacity, Duration window) {
            keys.add(key);
            long count = counts.merge(key, 1L, Long::sum);
            return new Hit(count, count <= capacity);
        }

        List<String> keys() {
            return keys;
        }
    }

    private static final class ThrowingStore implements CouponAbuseRateLimitStore {
        @Override
        public Hit hit(String key, int capacity, Duration window) {
            throw new IllegalStateException("redis unavailable");
        }
    }
}
