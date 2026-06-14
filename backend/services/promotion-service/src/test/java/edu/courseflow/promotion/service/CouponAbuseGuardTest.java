package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import edu.courseflow.promotion.repository.IncentiveRetentionOperationRepository;
import edu.courseflow.promotion.repository.OutboxEventRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class CouponAbuseGuardTest {

    @Test
    void enforcedModeBlocksSuspiciousCouponBurstWithoutRawValuesInKeys() {
        RecordingStore store = new RecordingStore();
        CouponAbuseGuard guard = guard(store, properties(CouponAbuseGuardProperties.Mode.ENFORCED, 1), registry());
        EvaluateIncentivesRequestDto request = request("profile-secret-1", List.of("SAVE-SECRET-10"));

        assertThat(guard.check("evaluate", request, "checkout-service", "not_found", true).blocked())
                .isFalse();
        CouponAbuseGuard.Decision blocked =
                guard.check("evaluate", request, "checkout-service", "not_found", true);

        assertThat(blocked.blocked()).isTrue();
        assertThat(blocked.reasonCode()).isEqualTo("RATE_LIMITED");
        assertThat(String.join(" ", store.keys()))
                .doesNotContain("SAVE-SECRET-10")
                .doesNotContain("PROFILE-SECRET-1")
                .doesNotContain("profile-secret-1");
    }

    @Test
    void shadowModeRecordsLimitButAllowsBusinessDecline() {
        SimpleMeterRegistry registry = registry();
        RecordingStore store = new RecordingStore();
        CouponAbuseGuard guard = guard(store, properties(CouponAbuseGuardProperties.Mode.SHADOW, 1), registry);
        EvaluateIncentivesRequestDto request = request("profile-1", List.of("MISS-1"));

        guard.check("evaluate", request, "checkout-service", "not_found", true);
        CouponAbuseGuard.Decision second =
                guard.check("evaluate", request, "checkout-service", "not_found", true);

        assertThat(second.blocked()).isFalse();
        assertThat(registry.get("promotion.coupon.abuse_guard")
                .tag("operation", "evaluate")
                .tag("mode", "shadow")
                .tag("scope", "profile")
                .tag("result", "shadow_limited")
                .counter()
                .count()).isEqualTo(1.0);
    }

    @Test
    void storeFailurePolicyCanFailOpenOrDenyCouponRequiredTraffic() {
        CouponAbuseGuardProperties allow = properties(CouponAbuseGuardProperties.Mode.ENFORCED, 1);
        allow.setFailPolicy(CouponAbuseGuardProperties.FailPolicy.ALLOW_WITH_ALERT);
        allow.validate();
        CouponAbuseGuard allowGuard = guard(new ThrowingStore(), allow, registry());

        assertThat(allowGuard.check(
                "reserve",
                request("profile-1", List.of("MISS-1")),
                "checkout-service",
                "not_found",
                true).blocked()).isFalse();

        CouponAbuseGuardProperties deny = properties(CouponAbuseGuardProperties.Mode.ENFORCED, 1);
        deny.setFailPolicy(CouponAbuseGuardProperties.FailPolicy.DENY_COUPON_REQUIRED);
        deny.validate();
        CouponAbuseGuard denyGuard = guard(new ThrowingStore(), deny, registry());

        assertThat(denyGuard.check(
                "reserve",
                request("profile-1", List.of("MISS-1")),
                "checkout-service",
                "not_found",
                true).blocked()).isTrue();
    }

    @Test
    void disabledModeDoesNotTouchStore() {
        RecordingStore store = new RecordingStore();
        CouponAbuseGuard guard = guard(store, properties(CouponAbuseGuardProperties.Mode.DISABLED, 1), registry());

        CouponAbuseGuard.Decision decision = guard.check(
                "evaluate",
                request("profile-1", List.of("MISS-1")),
                "checkout-service",
                "not_found",
                true);

        assertThat(decision.blocked()).isFalse();
        assertThat(store.keys()).isEmpty();
    }

    private CouponAbuseGuard guard(CouponAbuseRateLimitStore store,
                                   CouponAbuseGuardProperties properties,
                                   SimpleMeterRegistry registry) {
        return new CouponAbuseGuard(properties, store, metrics(registry));
    }

    private CouponAbuseGuardProperties properties(CouponAbuseGuardProperties.Mode mode, int profileCapacity) {
        CouponAbuseGuardProperties properties = new CouponAbuseGuardProperties();
        properties.setMode(mode);
        properties.setKeyId("test");
        properties.setPepper("test-abuse-guard-pepper-32-byte-value");
        properties.setWindowSeconds(60);
        properties.setProfileCapacity(profileCapacity);
        properties.setClientCapacity(100);
        properties.setApplicationCapacity(100);
        properties.setCouponCapacity(100);
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

    private EvaluateIncentivesRequestDto request(String profileId, List<String> couponCodes) {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                profileId,
                "cart-1",
                "WEB",
                "USD",
                couponCodes,
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.ZERO),
                List.of(new IncentiveItemDto("item-1", "COURSE", 1, BigDecimal.valueOf(120), Map.of())),
                Map.of());
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
