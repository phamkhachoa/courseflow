package edu.courseflow.enrollment.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.enrollment.service.CoursePricingClient.CoursePricingSnapshot;
import edu.courseflow.enrollment.service.CoursePricingClient.CoursePricingUnavailableException;
import edu.courseflow.enrollment.dto.EnrollmentDtos.LearnerCouponWalletDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionEffectDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.PromotionPreviewDto;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class PromotionEnrollmentClient {

    private static final BigDecimal ZERO = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);

    private final RestClient promotionClient;
    private final InternalJwtService internalJwt;
    private final CoursePricingClient coursePricing;
    private final String tenantId;
    private final String applicationId;
    private final String currency;
    private final BigDecimal defaultListPrice;
    private final String priceSource;
    private final boolean enabled;
    private final boolean allowConfigDefaultPrice;

    public PromotionEnrollmentClient(
            RestClient.Builder restClientBuilder,
            InternalJwtService internalJwt,
            CoursePricingClient coursePricing,
            @Value("${courseflow.enrollment.promotion-service-url:http://promotion-service:8080}") String promotionServiceUrl,
            @Value("${courseflow.enrollment.incentives.tenant-id:courseflow}") String tenantId,
            @Value("${courseflow.enrollment.incentives.application-id:lms}") String applicationId,
            @Value("${courseflow.enrollment.incentives.currency:USD}") String currency,
            @Value("${courseflow.enrollment.incentives.default-list-price:100.00}") BigDecimal defaultListPrice,
            @Value("${courseflow.enrollment.incentives.price-source:CONFIG_DEFAULT}") String priceSource,
            @Value("${courseflow.enrollment.incentives.allow-config-default-price:false}") boolean allowConfigDefaultPrice,
            @Value("${courseflow.enrollment.incentives.enabled:true}") boolean enabled) {
        this.promotionClient = restClientBuilder.baseUrl(promotionServiceUrl).build();
        this.internalJwt = internalJwt;
        this.coursePricing = coursePricing;
        this.tenantId = normalize(tenantId, "courseflow");
        this.applicationId = normalize(applicationId, "lms");
        this.currency = normalize(currency, "USD").toUpperCase();
        this.defaultListPrice = money(defaultListPrice == null ? BigDecimal.ZERO : defaultListPrice);
        this.priceSource = normalize(priceSource, "CONFIG_DEFAULT");
        this.allowConfigDefaultPrice = allowConfigDefaultPrice;
        this.enabled = enabled;
    }

    public PromotionPreviewDto preview(UUID courseId, String profileId, String couponCode, String couponId) {
        String normalizedCoupon = normalizeCoupon(couponCode);
        UUID normalizedCouponId = normalizeCouponId(couponId);
        if (!enabled) {
            return unavailablePreview(courseId, normalizedCoupon, normalizedCouponId, "Promotion checks are disabled");
        }
        if (normalizedCoupon == null && normalizedCouponId == null) {
            return preview(courseId, null, null, fallbackPricing(), false, List.of("COUPON_REQUIRED"), List.of(), false);
        }
        PricingSnapshot pricing = pricing(courseId);
        if (pricing.unavailable()) {
            return unavailablePreview(courseId, normalizedCoupon, normalizedCouponId,
                    pricing.message());
        }
        try {
            EvaluateIncentivesResponse response = promotionClient.post()
                    .uri("/internal/incentives/evaluate")
                    .headers(headers -> internalJwt.applyServiceToken(headers, List.of(InternalScopes.PROMOTION_EVALUATE)))
                    .body(context(courseId, profileId, normalizedCoupon, normalizedCouponId, "enrollment-preview", pricing))
                    .retrieve()
                    .body(EvaluateIncentivesResponse.class);
            if (response == null) {
                return unavailablePreview(courseId, normalizedCoupon, normalizedCouponId,
                        "Promotion service returned an empty decision");
            }
            return preview(courseId, normalizedCoupon, normalizedCouponId, pricing, response.eligible(),
                    safeReasons(response.reasonCodes()), toEffects(response.effects()), false);
        } catch (RestClientResponseException ex) {
            return preview(courseId, normalizedCoupon, normalizedCouponId, pricing, false,
                    List.of("PROMOTION_REJECTED"), List.of(), false);
        } catch (RestClientException ex) {
            return unavailablePreview(courseId, normalizedCoupon, normalizedCouponId, "Promotion service is unavailable");
        }
    }

    public LearnerCouponWalletDto learnerCoupons(String profileId) {
        if (!enabled) {
            return emptyWallet(profileId);
        }
        try {
            LearnerCouponWalletDto response = promotionClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .path("/internal/incentives/learner/coupons")
                            .queryParam("tenantId", tenantId)
                            .queryParam("applicationId", applicationId)
                            .queryParam("profileId", profileId)
                            .queryParam("limit", 50)
                            .build())
                    .headers(headers -> internalJwt.applyServiceToken(
                            headers, List.of(InternalScopes.PROMOTION_EVALUATE)))
                    .retrieve()
                    .body(LearnerCouponWalletDto.class);
            return response == null ? emptyWallet(profileId) : response;
        } catch (RestClientException ex) {
            return emptyWallet(profileId);
        }
    }

    public ReservationResult reserve(UUID courseId,
                                     String profileId,
                                     String couponCode,
                                     String couponId,
                                     String idempotencyKey) {
        String normalizedCoupon = normalizeCoupon(couponCode);
        UUID normalizedCouponId = normalizeCouponId(couponId);
        if (!enabled || (normalizedCoupon == null && normalizedCouponId == null)) {
            return ReservationResult.skipped(normalizedCoupon, normalizedCouponId);
        }
        PricingSnapshot pricing = pricing(courseId);
        if (pricing.unavailable()) {
            throw new PromotionUnavailableException(pricing.message());
        }
        String key = normalize(idempotencyKey, null);
        if (key == null) {
            key = "enrollment-reserve-" + UUID.randomUUID();
        }
        String requestKey = key;
        try {
            ReserveIncentiveResponse response = promotionClient.post()
                    .uri("/internal/incentives/reservations")
                    .headers(headers -> {
                        internalJwt.applyServiceToken(headers, List.of(InternalScopes.PROMOTION_RESERVE));
                        headers.set("Idempotency-Key", requestKey);
                    })
                    .body(new ReserveIncentiveRequest(requestKey, context(courseId, profileId, normalizedCoupon,
                            normalizedCouponId, "enrollment-confirm", pricing)))
                    .retrieve()
                    .body(ReserveIncentiveResponse.class);
            if (response == null) {
                throw new PromotionUnavailableException("Promotion service returned an empty reservation");
            }
            return new ReservationResult(
                    response.reserved(),
                    response.reservationId(),
                    normalizedCoupon,
                    normalizedCouponId == null ? null : normalizedCouponId.toString(),
                    safeReasons(response.reasonCodes()),
                    toEffects(response.effects()),
                    false);
        } catch (RestClientResponseException ex) {
            return new ReservationResult(false, null, normalizedCoupon,
                    normalizedCouponId == null ? null : normalizedCouponId.toString(),
                    List.of("PROMOTION_REJECTED"), List.of(), false);
        } catch (RestClientException ex) {
            throw new PromotionUnavailableException("Promotion reserve is unavailable", ex);
        }
    }

    public CommitResult commit(UUID reservationId, String externalReference, String idempotencyKey) {
        if (reservationId == null) {
            return CommitResult.skipped();
        }
        String key = normalize(idempotencyKey, null);
        if (key == null) {
            key = "enrollment-commit-" + UUID.randomUUID();
        }
        String requestKey = key;
        try {
            CommitReservationResponse response = promotionClient.post()
                    .uri("/internal/incentives/reservations/{reservationId}/commit", reservationId)
                    .headers(headers -> {
                        internalJwt.applyServiceToken(headers, List.of(InternalScopes.PROMOTION_COMMIT));
                        headers.set("Idempotency-Key", requestKey);
                    })
                    .body(new CommitReservationRequest(requestKey, externalReference))
                    .retrieve()
                    .body(CommitReservationResponse.class);
            if (response == null) {
                throw new PromotionUnavailableException("Promotion service returned an empty commit");
            }
            return new CommitResult(
                    response.committed(),
                    response.redemptionId(),
                    safeReasons(response.reasonCodes()),
                    toEffects(response.effects()));
        } catch (RestClientException ex) {
            throw new PromotionUnavailableException("Promotion commit is unavailable", ex);
        }
    }

    public void cancel(UUID reservationId, String reason, String idempotencyKey) {
        try {
            cancelReservation(reservationId, reason, idempotencyKey);
        } catch (PromotionUnavailableException ignored) {
            // Enrollment failure remains the caller-visible error. Reservation expiry job is the fallback.
        }
    }

    public CancelResult cancelStrict(UUID reservationId, String reason, String idempotencyKey) {
        return cancelReservation(reservationId, reason, idempotencyKey);
    }

    private CancelResult cancelReservation(UUID reservationId, String reason, String idempotencyKey) {
        if (reservationId == null) {
            return CancelResult.skipped();
        }
        String key = normalize(idempotencyKey, null);
        if (key == null) {
            key = "enrollment-cancel-" + UUID.randomUUID();
        }
        String requestKey = key;
        try {
            CancelReservationResponse response = promotionClient.post()
                    .uri("/internal/incentives/reservations/{reservationId}/cancel", reservationId)
                    .headers(headers -> {
                        internalJwt.applyServiceToken(headers, List.of(InternalScopes.PROMOTION_CANCEL));
                        headers.set("Idempotency-Key", requestKey);
                    })
                    .body(new CancelReservationRequest(requestKey, reason))
                    .retrieve()
                    .body(CancelReservationResponse.class);
            if (response == null) {
                throw new PromotionUnavailableException("Promotion service returned an empty cancel response");
            }
            return new CancelResult(response.cancelled(), response.status(), safeReasons(response.reasonCodes()));
        } catch (RestClientException ex) {
            throw new PromotionUnavailableException("Promotion cancel is unavailable", ex);
        }
    }

    public ReverseResult reverse(UUID redemptionId, String reason, String idempotencyKey) {
        if (redemptionId == null) {
            return ReverseResult.skipped();
        }
        String key = normalize(idempotencyKey, null);
        if (key == null) {
            key = "enrollment-reverse-" + UUID.randomUUID();
        }
        String requestKey = key;
        try {
            ReverseRedemptionResponse response = promotionClient.post()
                    .uri("/internal/incentives/redemptions/{redemptionId}/reverse", redemptionId)
                    .headers(headers -> {
                        internalJwt.applyServiceToken(headers, List.of(InternalScopes.PROMOTION_REVERSE));
                        headers.set("Idempotency-Key", requestKey);
                    })
                    .body(new ReverseRedemptionRequest(requestKey, normalize(reason, "Enrollment dropped")))
                    .retrieve()
                    .body(ReverseRedemptionResponse.class);
            if (response == null) {
                throw new PromotionUnavailableException("Promotion service returned an empty reversal");
            }
            return new ReverseResult(response.reversed(), response.redemptionId(), response.status(),
                    safeReasons(response.reasonCodes()), toEffects(response.effects()));
        } catch (RestClientException ex) {
            throw new PromotionUnavailableException("Promotion reversal is unavailable", ex);
        }
    }

    private EvaluateIncentivesRequest context(UUID courseId,
                                             String profileId,
                                             String couponCode,
                                             UUID couponId,
                                             String source,
                                             PricingSnapshot pricing) {
        BigDecimal price = pricing.listPrice();
        return new EvaluateIncentivesRequest(
                tenantId,
                applicationId,
                profileId,
                "course-enrollment:" + courseId,
                "web-learn",
                pricing.currency(),
                couponCode == null ? List.of() : List.of(couponCode),
                couponId == null ? List.of() : List.of(couponId),
                new TransactionContext(price, ZERO),
                List.of(new IncentiveItem(
                        courseId.toString(),
                        "COURSE",
                        1,
                        price,
                        Map.of(
                                "courseId", courseId.toString(),
                                "category", "COURSE",
                                "source", source,
                                "priceSource", pricing.priceSource(),
                                "priceStatus", pricing.priceStatus()))),
                Map.of(
                        "courseId", courseId.toString(),
                        "source", source,
                        "priceSource", pricing.priceSource(),
                        "priceStatus", pricing.priceStatus()));
    }

    private PromotionPreviewDto preview(UUID courseId,
                                        String couponCode,
                                        UUID couponId,
                                        PricingSnapshot pricing,
                                        boolean eligible,
                                        List<String> reasonCodes,
                                        List<PromotionEffectDto> effects,
                                        boolean unavailable) {
        BigDecimal discount = discountAmount(effects, pricing);
        BigDecimal finalAmount = pricing.listPrice().subtract(discount).max(BigDecimal.ZERO);
        String status = unavailable ? "UNAVAILABLE" : eligible ? "PREVIEWED" : "INVALID";
        return new PromotionPreviewDto(
                previewId(courseId, couponCode, couponId, pricing, reasonCodes, effects),
                courseId.toString(),
                couponCode,
                couponId == null ? null : couponId.toString(),
                status,
                eligible,
                reasonCodes,
                message(status, reasonCodes),
                pricing.listPrice(),
                discount,
                finalAmount,
                pricing.currency(),
                pricing.priceSource(),
                effects,
                unavailable);
    }

    private PromotionPreviewDto unavailablePreview(UUID courseId, String couponCode, UUID couponId, String message) {
        PricingSnapshot pricing = fallbackPricing();
        return new PromotionPreviewDto(
                previewId(courseId, couponCode, couponId, pricing, List.of("PROMOTION_UNAVAILABLE"), List.of()),
                courseId.toString(),
                couponCode,
                couponId == null ? null : couponId.toString(),
                "UNAVAILABLE",
                false,
                List.of("PROMOTION_UNAVAILABLE"),
                message,
                pricing.listPrice(),
                ZERO,
                pricing.listPrice(),
                pricing.currency(),
                pricing.priceSource(),
                List.of(),
                true);
    }

    private LearnerCouponWalletDto emptyWallet(String profileId) {
        return new LearnerCouponWalletDto(
                tenantId,
                applicationId,
                profileId,
                Instant.now(),
                0,
                0,
                0,
                0,
                List.of());
    }

    private List<PromotionEffectDto> toEffects(List<IncentiveEffect> effects) {
        if (effects == null || effects.isEmpty()) {
            return List.of();
        }
        return effects.stream()
                .filter(Objects::nonNull)
                .map(effect -> new PromotionEffectDto(
                        effect.type(),
                        effect.benefitType(),
                        effect.actionType(),
                        effect.targetType(),
                        effect.targetId(),
                        effect.amount(),
                        effect.currency(),
                        effect.unit(),
                        effect.quantity(),
                        effect.metadata()))
                .toList();
    }

    private BigDecimal discountAmount(List<PromotionEffectDto> effects, PricingSnapshot pricing) {
        if (effects == null || effects.isEmpty()) {
            return ZERO;
        }
        BigDecimal total = effects.stream()
                .filter(effect -> "DISCOUNT".equalsIgnoreCase(nullToEmpty(effect.benefitType())))
                .map(PromotionEffectDto::amount)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        return money(total.min(pricing.listPrice()).max(BigDecimal.ZERO));
    }

    private PricingSnapshot pricing(UUID courseId) {
        try {
            CoursePricingSnapshot snapshot = coursePricing.pricing(courseId.toString());
            return new PricingSnapshot(
                    money(snapshot.listPrice()),
                    snapshot.currency().trim().toUpperCase(),
                    snapshot.priceStatus(),
                    snapshot.priceSource(),
                    false,
                    null);
        } catch (CoursePricingUnavailableException ex) {
            if (allowConfigDefaultPrice) {
                return fallbackPricing();
            }
            return new PricingSnapshot(
                    defaultListPrice,
                    currency,
                    "UNAVAILABLE",
                    "UNAVAILABLE",
                    true,
                    "Enrollment coupon pricing requires an authoritative course price source");
        }
    }

    private PricingSnapshot fallbackPricing() {
        return new PricingSnapshot(defaultListPrice, currency, "CONFIG_DEFAULT", priceSource, false, null);
    }

    private List<String> safeReasons(List<String> reasonCodes) {
        return reasonCodes == null ? List.of() : reasonCodes;
    }

    private String message(String status, List<String> reasonCodes) {
        if ("PREVIEWED".equals(status)) {
            return "Coupon can be applied to this enrollment";
        }
        if ("UNAVAILABLE".equals(status)) {
            return "Promotion service is unavailable";
        }
        if (reasonCodes == null || reasonCodes.isEmpty()) {
            return "Coupon is not applicable";
        }
        return "Coupon is not applicable: " + String.join(", ", reasonCodes);
    }

    private String previewId(UUID courseId,
                             String couponCode,
                             UUID couponId,
                             PricingSnapshot pricing,
                             List<String> reasonCodes,
                             List<PromotionEffectDto> effects) {
        return "preview-" + sha256Hex(String.join("|",
                courseId.toString(),
                normalize(couponCode, ""),
                couponId == null ? "" : couponId.toString(),
                pricing.listPrice().toPlainString(),
                pricing.currency(),
                pricing.priceSource(),
                pricing.priceStatus(),
                String.join(",", reasonCodes == null ? List.of() : reasonCodes),
                effectSignature(effects))).substring(0, 24);
    }

    private String effectSignature(List<PromotionEffectDto> effects) {
        if (effects == null || effects.isEmpty()) {
            return "";
        }
        return effects.stream()
                .map(effect -> String.join(":",
                        normalize(effect.type(), ""),
                        normalize(effect.benefitType(), ""),
                        normalize(effect.actionType(), ""),
                        normalize(effect.targetType(), ""),
                        normalize(effect.targetId(), ""),
                        effect.amount() == null ? "" : money(effect.amount()).toPlainString(),
                        normalize(effect.currency(), ""),
                        normalize(effect.unit(), ""),
                        effect.quantity() == null ? "" : effect.quantity().stripTrailingZeros().toPlainString()))
                .sorted()
                .toList()
                .toString();
    }

    private String normalizeCoupon(String couponCode) {
        String value = normalize(couponCode, null);
        return value == null ? null : value.toUpperCase();
    }

    private UUID normalizeCouponId(String couponId) {
        String value = normalize(couponId, null);
        if (value == null) {
            return null;
        }
        try {
            return UUID.fromString(value);
        } catch (RuntimeException ex) {
            throw new BadRequestException("Invalid couponId: " + couponId);
        }
    }

    private String normalize(String value, String fallback) {
        if (value == null || value.isBlank()) {
            return fallback;
        }
        return value.trim();
    }

    private String nullToEmpty(String value) {
        return value == null ? "" : value;
    }

    private BigDecimal money(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }

    private String sha256Hex(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("Unable to hash promotion preview", ex);
        }
    }

    public record ReservationResult(
            boolean reserved,
            UUID reservationId,
            String couponCode,
            String couponId,
            List<String> reasonCodes,
            List<PromotionEffectDto> effects,
            boolean skipped
    ) {
        static ReservationResult skipped(String couponCode, UUID couponId) {
            return new ReservationResult(false, null, couponCode, couponId == null ? null : couponId.toString(),
                    List.of("COUPON_NOT_SUPPLIED"),
                    List.of(), true);
        }

        static ReservationResult skipped(String couponCode, String couponId) {
            return new ReservationResult(false, null, couponCode, couponId, List.of("COUPON_NOT_SUPPLIED"),
                    List.of(), true);
        }
    }

    public record CommitResult(
            boolean committed,
            UUID redemptionId,
            List<String> reasonCodes,
            List<PromotionEffectDto> effects
    ) {
        static CommitResult skipped() {
            return new CommitResult(false, null, List.of("PROMOTION_SKIPPED"), List.of());
        }
    }

    public record ReverseResult(
            boolean reversed,
            UUID redemptionId,
            String status,
            List<String> reasonCodes,
            List<PromotionEffectDto> effects
    ) {
        static ReverseResult skipped() {
            return new ReverseResult(false, null, "SKIPPED", List.of("PROMOTION_SKIPPED"), List.of());
        }
    }

    public record CancelResult(
            boolean cancelled,
            String status,
            List<String> reasonCodes
    ) {
        static CancelResult skipped() {
            return new CancelResult(false, "SKIPPED", List.of("PROMOTION_SKIPPED"));
        }
    }

    public static class PromotionUnavailableException extends RuntimeException {
        PromotionUnavailableException(String message) {
            super(message);
        }

        PromotionUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    private record EvaluateIncentivesRequest(
            String tenantId,
            String applicationId,
            String profileId,
            String externalReference,
            String channel,
            String currency,
            List<String> couponCodes,
            List<UUID> couponIds,
            TransactionContext transaction,
            List<IncentiveItem> items,
            Map<String, Object> attributes
    ) {
    }

    private record TransactionContext(BigDecimal subtotal, BigDecimal shippingAmount) {
    }

    private record IncentiveItem(
            String id,
            String type,
            int quantity,
            BigDecimal unitPrice,
            Map<String, Object> attributes
    ) {
    }

    private record PricingSnapshot(
            BigDecimal listPrice,
            String currency,
            String priceStatus,
            String priceSource,
            boolean unavailable,
            String message
    ) {
    }

    private record EvaluateIncentivesResponse(
            boolean eligible,
            UUID campaignId,
            Integer campaignVersion,
            String campaignCode,
            UUID couponId,
            List<IncentiveEffect> effects,
            List<String> reasonCodes
    ) {
    }

    private record ReserveIncentiveRequest(String idempotencyKey, EvaluateIncentivesRequest context) {
    }

    private record ReserveIncentiveResponse(
            boolean reserved,
            UUID reservationId,
            UUID campaignId,
            Integer campaignVersion,
            UUID couponId,
            String expiresAt,
            List<IncentiveEffect> effects,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }

    private record CommitReservationRequest(String idempotencyKey, String externalReference) {
    }

    private record CommitReservationResponse(
            boolean committed,
            UUID reservationId,
            UUID redemptionId,
            UUID campaignId,
            Integer campaignVersion,
            String status,
            List<IncentiveEffect> effects,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }

    private record CancelReservationRequest(String idempotencyKey, String reason) {
    }

    private record CancelReservationResponse(
            boolean cancelled,
            UUID reservationId,
            String status,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }

    private record ReverseRedemptionRequest(String idempotencyKey, String reason) {
    }

    private record ReverseRedemptionResponse(
            boolean reversed,
            UUID redemptionId,
            String status,
            List<IncentiveEffect> effects,
            List<String> reasonCodes,
            boolean idempotencyReplay
    ) {
    }

    private record IncentiveEffect(
            String type,
            String benefitType,
            String actionType,
            String targetType,
            String targetId,
            BigDecimal amount,
            String currency,
            String unit,
            BigDecimal quantity,
            Map<String, Object> metadata,
            String effectId,
            Integer campaignVersion
    ) {
    }
}
