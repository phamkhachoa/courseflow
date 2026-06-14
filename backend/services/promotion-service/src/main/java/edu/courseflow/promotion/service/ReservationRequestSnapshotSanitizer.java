package edu.courseflow.promotion.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveItemDto;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ReservationRequestSnapshotSanitizer {

    static final String SNAPSHOT_VERSION = "reservation-request-snapshot.v2";
    static final String POLICY_ID = "reservation-request-snapshot-minimization";
    static final String POLICY_VERSION = "v1";

    private final byte[] hashSecret;

    public ReservationRequestSnapshotSanitizer(
            @Value("${courseflow.promotion.request-snapshot.hash-secret:"
                    + "${courseflow.security.internal-jwt.secret:local-request-snapshot-secret-change-me-32}}")
            String hashSecret) {
        String normalized = hashSecret == null || hashSecret.isBlank()
                ? "local-request-snapshot-secret-change-me-32"
                : hashSecret.trim();
        this.hashSecret = normalized.getBytes(StandardCharsets.UTF_8);
    }

    public Map<String, Object> storageSnapshot(EvaluateIncentivesRequestDto request) {
        Map<String, Object> snapshot = sanitizedFacts(request);
        snapshot.put("generatedAt", Instant.now().toString());
        return snapshot;
    }

    public Map<String, Object> auditFacts(EvaluateIncentivesRequestDto request) {
        return sanitizedFacts(request);
    }

    private Map<String, Object> sanitizedFacts(EvaluateIncentivesRequestDto request) {
        if (request == null) {
            throw new BadRequestException("Incentive request context is required");
        }
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("snapshotVersion", SNAPSHOT_VERSION);
        snapshot.put("policyId", POLICY_ID);
        snapshot.put("policyVersion", POLICY_VERSION);
        snapshot.put("requestSnapshotMinimized", true);
        snapshot.put("tenantId", safeString(request.tenantId()));
        snapshot.put("applicationId", safeString(request.applicationId()));
        snapshot.put("subject", subject(request));
        snapshot.put("context", context(request));
        snapshot.put("transaction", transaction(request));
        snapshot.put("items", items(request.items()));
        snapshot.put("attributes", attributes(request.attributes()));
        snapshot.put("coupons", coupons(request.couponCodes(), request.couponIds()));
        return snapshot;
    }

    private Map<String, Object> subject(EvaluateIncentivesRequestDto request) {
        Map<String, Object> subject = new LinkedHashMap<>();
        subject.put("profileHash", fingerprint("profile", request.profileId()));
        subject.put("externalReferenceHash", fingerprint("external-reference", request.externalReference()));
        return subject;
    }

    private Map<String, Object> context(EvaluateIncentivesRequestDto request) {
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("channel", safeString(request.channel()));
        context.put("currency", safeString(request.currency()));
        return context;
    }

    private Map<String, Object> transaction(EvaluateIncentivesRequestDto request) {
        Map<String, Object> transaction = new LinkedHashMap<>();
        if (request.transaction() == null) {
            transaction.put("subtotal", "");
            transaction.put("shippingAmount", "");
            return transaction;
        }
        transaction.put("subtotal", decimal(request.transaction().subtotal()));
        transaction.put("shippingAmount", decimal(request.transaction().shippingAmount()));
        return transaction;
    }

    private Map<String, Object> items(List<IncentiveItemDto> items) {
        Map<String, Object> result = new LinkedHashMap<>();
        List<IncentiveItemDto> safeItems = items == null ? List.of() : items;
        result.put("count", safeItems.size());
        result.put("totalQuantity", safeItems.stream().mapToInt(IncentiveItemDto::quantity).sum());
        result.put("types", safeItems.stream()
                .map(IncentiveItemDto::type)
                .filter(value -> value != null && !value.isBlank())
                .map(String::trim)
                .distinct()
                .sorted()
                .toList());
        result.put("attributeKeys", safeItems.stream()
                .filter(item -> item.attributes() != null)
                .flatMap(item -> item.attributes().keySet().stream())
                .filter(value -> value != null && !value.isBlank())
                .map(String::trim)
                .distinct()
                .sorted()
                .toList());
        return result;
    }

    private Map<String, Object> attributes(Map<String, Object> attributes) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", attributes == null ? 0 : attributes.size());
        result.put("keys", attributes == null
                ? List.of()
                : attributes.keySet().stream()
                .filter(value -> value != null && !value.isBlank())
                .map(String::trim)
                .distinct()
                .sorted()
                .toList());
        return result;
    }

    private Map<String, Object> coupons(List<String> couponCodes, List<UUID> couponIds) {
        List<String> normalizedCodes = couponCodes == null ? List.of() : couponCodes.stream()
                .map(CouponCodeNormalizer::normalize)
                .filter(code -> !code.isBlank())
                .distinct()
                .toList();
        List<String> ids = couponIds == null ? List.of() : couponIds.stream()
                .filter(Objects::nonNull)
                .map(UUID::toString)
                .distinct()
                .sorted()
                .toList();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", normalizedCodes.size());
        result.put("masks", normalizedCodes.stream().map(CouponCodeNormalizer::mask).toList());
        result.put("couponIdCount", ids.size());
        result.put("couponIds", ids);
        return result;
    }

    private String fingerprint(String namespace, String value) {
        String normalized = safeString(value);
        if (normalized.isBlank()) {
            return "";
        }
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(hashSecret, "HmacSHA256"));
            byte[] digest = mac.doFinal((namespace + ":" + normalized).getBytes(StandardCharsets.UTF_8));
            return "hmac-sha256:" + java.util.HexFormat.of().formatHex(digest);
        } catch (Exception ex) {
            throw new IllegalStateException("HmacSHA256 is not available", ex);
        }
    }

    private String decimal(BigDecimal value) {
        return value == null ? "" : value.toPlainString();
    }

    private String safeString(Object value) {
        return Objects.toString(value, "").trim();
    }
}
