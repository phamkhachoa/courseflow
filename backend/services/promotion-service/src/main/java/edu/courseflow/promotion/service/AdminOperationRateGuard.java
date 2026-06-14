package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.ADMIN_OPERATION_RATE_LIMITED;

import edu.courseflow.commonlibrary.exception.CodedResponseStatusException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
public class AdminOperationRateGuard {

    private static final String HMAC_ALGORITHM = "HmacSHA256";

    private final AdminOperationRateGuardProperties properties;
    private final CouponAbuseRateLimitStore store;
    private final IncentiveMetrics metrics;

    public AdminOperationRateGuard(AdminOperationRateGuardProperties properties,
                                   CouponAbuseRateLimitStore store,
                                   IncentiveMetrics metrics) {
        this.properties = properties;
        this.store = store;
        this.metrics = metrics;
    }

    static AdminOperationRateGuard disabled(IncentiveMetrics metrics) {
        AdminOperationRateGuardProperties properties = new AdminOperationRateGuardProperties();
        properties.setMode(AdminOperationRateGuardProperties.Mode.DISABLED);
        properties.validate();
        return new AdminOperationRateGuard(properties, (key, capacity, window) ->
                new CouponAbuseRateLimitStore.Hit(0, true), metrics);
    }

    public void requireAllowed(String operation,
                               String tenantId,
                               String applicationId,
                               UUID campaignId,
                               CurrentUser user,
                               String sourceClientId,
                               String contentHash) {
        Decision decision = check(operation, tenantId, applicationId, campaignId, user, sourceClientId, contentHash);
        if (decision.blocked()) {
            throw new CodedResponseStatusException(
                    HttpStatus.TOO_MANY_REQUESTS,
                    ADMIN_OPERATION_RATE_LIMITED,
                    "Promotion admin operation rate limit exceeded");
        }
    }

    Decision check(String operation,
                   String tenantId,
                   String applicationId,
                   UUID campaignId,
                   CurrentUser user,
                   String sourceClientId,
                   String contentHash) {
        if (!properties.enabled()) {
            return Decision.allowed();
        }
        List<Bucket> buckets = buckets(operation, tenantId, applicationId, campaignId, user, sourceClientId, contentHash);
        if (buckets.stream().anyMatch(bucket -> bucket.scope() == Scope.MISSING_IDENTITY)) {
            metrics.adminOperationRateGuard(operation, mode(), Scope.MISSING_IDENTITY.tag(), "missing_identity");
        }
        try {
            boolean limited = false;
            for (Bucket bucket : buckets) {
                CouponAbuseRateLimitStore.Hit hit = store.hit(
                        key(bucket),
                        properties.capacity(bucket.scope()),
                        properties.window());
                if (hit.allowed()) {
                    metrics.adminOperationRateGuard(operation, mode(), bucket.scope().tag(), "allowed");
                } else {
                    limited = true;
                    metrics.adminOperationRateGuard(
                            operation,
                            mode(),
                            bucket.scope().tag(),
                            shadowMode() ? "shadow_limited" : "limited");
                }
            }
            if (limited && !shadowMode()) {
                return Decision.denied();
            }
            return Decision.allowed();
        } catch (RuntimeException ex) {
            boolean deny = properties.getMode() == AdminOperationRateGuardProperties.Mode.ENFORCED
                    && properties.getFailPolicy() == AdminOperationRateGuardProperties.FailPolicy.DENY;
            metrics.adminOperationRateGuard(operation, mode(), Scope.STORE.tag(), deny ? "error_denied" : "error_allowed");
            return deny ? Decision.denied() : Decision.allowed();
        }
    }

    private List<Bucket> buckets(String operation,
                                 String tenantId,
                                 String applicationId,
                                 UUID campaignId,
                                 CurrentUser user,
                                 String sourceClientId,
                                 String contentHash) {
        String normalizedOperation = normalizeOperation(operation);
        String tenant = blankToUnknown(tenantId);
        String application = blankToUnknown(applicationId);
        String actor = user == null || user.id() == null ? null : String.valueOf(user.id());
        String client = blankToNull(sourceClientId);
        List<Bucket> buckets = new ArrayList<>();
        buckets.add(new Bucket(Scope.APPLICATION, List.of(tenant, application, normalizedOperation)));
        if (campaignId != null) {
            buckets.add(new Bucket(Scope.CAMPAIGN, List.of(tenant, application, normalizedOperation, "campaign", campaignId.toString())));
        }
        if (actor == null) {
            buckets.add(new Bucket(Scope.MISSING_IDENTITY, List.of(tenant, application, normalizedOperation, "actor:missing")));
        } else {
            buckets.add(new Bucket(Scope.ACTOR, List.of(tenant, application, normalizedOperation, "actor", hash("actor", actor))));
        }
        if (client == null) {
            buckets.add(new Bucket(Scope.MISSING_IDENTITY, List.of(tenant, application, normalizedOperation, "source-client:missing")));
        } else {
            buckets.add(new Bucket(Scope.SOURCE_CLIENT, List.of(tenant, application, normalizedOperation, "source-client", hash("source-client", client))));
        }
        String content = blankToNull(contentHash);
        if (content != null) {
            buckets.add(new Bucket(Scope.CONTENT, List.of(tenant, application, normalizedOperation, "content", hash("content", content))));
        }
        return List.copyOf(buckets);
    }

    private String key(Bucket bucket) {
        return "promotion:admin-operation-rate:"
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
            throw new IllegalStateException("Unable to compute admin operation rate guard hash", ex);
        }
    }

    private boolean shadowMode() {
        return properties.getMode() == AdminOperationRateGuardProperties.Mode.SHADOW;
    }

    private String mode() {
        return properties.getMode().name().toLowerCase(Locale.ROOT);
    }

    private String normalizeOperation(String value) {
        if (value == null || value.isBlank()) {
            return "unknown";
        }
        return value.trim().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_\\-]", "_");
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String blankToUnknown(String value) {
        String normalized = blankToNull(value);
        return normalized == null ? "unknown" : normalized;
    }

    enum Scope {
        ACTOR("actor"),
        SOURCE_CLIENT("source_client"),
        APPLICATION("application"),
        CAMPAIGN("campaign"),
        CONTENT("content"),
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

    record Decision(boolean blocked) {
        static Decision allowed() {
            return new Decision(false);
        }

        static Decision denied() {
            return new Decision(true);
        }
    }

    private record Bucket(Scope scope, List<String> parts) {
    }
}
