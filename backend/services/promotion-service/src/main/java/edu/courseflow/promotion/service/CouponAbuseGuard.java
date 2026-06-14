package edu.courseflow.promotion.service;

import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.stereotype.Component;

@Component
public class CouponAbuseGuard {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String RATE_LIMITED = "RATE_LIMITED";
    private static final Set<String> SUSPICIOUS_RESULTS = Set.of(
            "not_supplied",
            "not_found",
            "inactive",
            "not_started",
            "expired",
            "holder_mismatch");

    private final CouponAbuseGuardProperties properties;
    private final CouponAbuseRateLimitStore store;
    private final IncentiveMetrics metrics;

    public CouponAbuseGuard(CouponAbuseGuardProperties properties,
                            CouponAbuseRateLimitStore store,
                            IncentiveMetrics metrics) {
        this.properties = properties;
        this.store = store;
        this.metrics = metrics;
    }

    static CouponAbuseGuard disabled(IncentiveMetrics metrics) {
        CouponAbuseGuardProperties properties = new CouponAbuseGuardProperties();
        properties.setMode(CouponAbuseGuardProperties.Mode.DISABLED);
        properties.validate();
        return new CouponAbuseGuard(properties, (key, capacity, window) ->
                new CouponAbuseRateLimitStore.Hit(0, true), metrics);
    }

    Decision check(String operation,
                   EvaluateIncentivesRequestDto request,
                   String sourceClientId,
                   String couponMatchResult,
                   boolean couponRequired) {
        if (!properties.enabled() || !couponRequired || !suspicious(couponMatchResult)) {
            return Decision.allowed();
        }
        List<Bucket> buckets = buckets(operation, request, sourceClientId);
        if (buckets.stream().anyMatch(bucket -> bucket.scope() == Scope.MISSING_IDENTITY)) {
            metrics.couponAbuseGuard(operation, mode(), "missing_identity", "missing_identity");
        }
        try {
            boolean limited = false;
            for (Bucket bucket : buckets) {
                CouponAbuseRateLimitStore.Hit hit = store.hit(
                        key(bucket),
                        properties.capacity(bucket.scope()),
                        properties.window());
                if (hit.allowed()) {
                    metrics.couponAbuseGuard(operation, mode(), bucket.scope().tag(), "allowed");
                } else {
                    limited = true;
                    metrics.couponAbuseGuard(
                            operation,
                            mode(),
                            bucket.scope().tag(),
                            shadowMode() ? "shadow_limited" : "limited");
                }
            }
            if (limited && !shadowMode()) {
                return Decision.blocked(RATE_LIMITED);
            }
            return Decision.allowed();
        } catch (RuntimeException ex) {
            boolean deny = properties.getMode() == CouponAbuseGuardProperties.Mode.ENFORCED
                    && properties.getFailPolicy() == CouponAbuseGuardProperties.FailPolicy.DENY_COUPON_REQUIRED;
            metrics.couponAbuseGuard(operation, mode(), Scope.STORE.tag(), deny ? "error_denied" : "error_allowed");
            return deny ? Decision.blocked(RATE_LIMITED) : Decision.allowed();
        }
    }

    private boolean suspicious(String couponMatchResult) {
        return SUSPICIOUS_RESULTS.contains(normalize(couponMatchResult));
    }

    private List<Bucket> buckets(String operation, EvaluateIncentivesRequestDto request, String sourceClientId) {
        String tenantId = blankToUnknown(request == null ? null : request.tenantId());
        String applicationId = blankToUnknown(request == null ? null : request.applicationId());
        String normalizedOperation = blankToUnknown(operation);
        String client = blankToNull(sourceClientId);
        String profile = blankToNull(request == null ? null : request.profileId());
        List<Bucket> buckets = new ArrayList<>();
        buckets.add(new Bucket(
                Scope.APPLICATION,
                List.of(tenantId, applicationId, normalizedOperation)));
        if (client == null) {
            buckets.add(new Bucket(
                    Scope.MISSING_IDENTITY,
                    List.of(tenantId, applicationId, normalizedOperation, "client:missing")));
        } else {
            buckets.add(new Bucket(
                    Scope.CLIENT,
                    List.of(tenantId, applicationId, normalizedOperation, "client", hash("client", client))));
        }
        if (profile == null) {
            buckets.add(new Bucket(
                    Scope.MISSING_IDENTITY,
                    List.of(tenantId, applicationId, normalizedOperation, "profile:missing")));
        } else {
            buckets.add(new Bucket(
                    Scope.PROFILE,
                    List.of(tenantId, applicationId, normalizedOperation, "profile", hash("profile", profile))));
        }
        for (String couponHash : couponHashes(request)) {
            buckets.add(new Bucket(
                    Scope.COUPON,
                    List.of(tenantId, applicationId, normalizedOperation, "coupon", couponHash)));
        }
        return List.copyOf(buckets);
    }

    private List<String> couponHashes(EvaluateIncentivesRequestDto request) {
        if (request == null || request.couponCodes() == null) {
            return List.of();
        }
        Set<String> hashes = new LinkedHashSet<>();
        for (String raw : request.couponCodes()) {
            String normalized = CouponCodeNormalizer.normalize(raw);
            if (!normalized.isBlank()) {
                hashes.add(hash("coupon", normalized));
            }
        }
        return List.copyOf(hashes);
    }

    private String key(Bucket bucket) {
        return "promotion:coupon-abuse:"
                + properties.getKeyId()
                + ":"
                + bucket.scope().tag()
                + ":"
                + hash("bucket", String.join("|", bucket.parts()));
    }

    private String hash(String purpose, String value) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(properties.getPepper().getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM));
            String body = purpose + "\n" + (value == null ? "" : value);
            return HexFormat.of().formatHex(mac.doFinal(body.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to compute coupon abuse guard hash", ex);
        }
    }

    private boolean shadowMode() {
        return properties.getMode() == CouponAbuseGuardProperties.Mode.SHADOW;
    }

    private String mode() {
        return properties.getMode().name().toLowerCase();
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase();
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String blankToUnknown(String value) {
        String normalized = blankToNull(value);
        return normalized == null ? "unknown" : normalized;
    }

    enum Scope {
        PROFILE("profile"),
        CLIENT("client"),
        APPLICATION("application"),
        COUPON("coupon"),
        MISSING_IDENTITY("missing_identity"),
        STORE("store");

        private final String tag;

        Scope(String tag) {
            this.tag = tag;
        }

        String tag() {
            return tag;
        }
    }

    record Decision(boolean blocked, String reasonCode) {
        static Decision allowed() {
            return new Decision(false, null);
        }

        static Decision blocked(String reasonCode) {
            return new Decision(true, reasonCode);
        }
    }

    private record Bucket(Scope scope, List<String> parts) {
    }
}
