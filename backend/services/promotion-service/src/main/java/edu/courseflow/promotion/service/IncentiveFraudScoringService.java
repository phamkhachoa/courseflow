package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.FraudScorePreviewRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.FraudScorePreviewResponseDto;
import edu.courseflow.promotion.dto.PromotionDtos.FraudScoreSignalDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveRedemptionRepository;
import edu.courseflow.promotion.repository.IncentiveReservationRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IncentiveFraudScoringService {

    private static final String POLICY_VERSION = "promotion-fraud-score-v1";
    private static final int DEFAULT_LOOKBACK_MINUTES = 60;
    private static final int MAX_LOOKBACK_MINUTES = 10_080;

    private final IncentiveAccessService access;
    private final IncentiveReservationRepository reservations;
    private final IncentiveRedemptionRepository redemptions;
    private final IncentiveAuditEventRepository auditEvents;
    private final ObjectMapper objectMapper;

    public IncentiveFraudScoringService(IncentiveAccessService access,
                                        IncentiveReservationRepository reservations,
                                        IncentiveRedemptionRepository redemptions,
                                        IncentiveAuditEventRepository auditEvents,
                                        ObjectMapper objectMapper) {
        this.access = access;
        this.reservations = reservations;
        this.redemptions = redemptions;
        this.auditEvents = auditEvents;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public FraudScorePreviewResponseDto preview(FraudScorePreviewRequestDto request,
                                                CurrentUser user,
                                                String correlationId) {
        if (request == null || request.context() == null) {
            throw new BadRequestException("Fraud score context is required");
        }
        EvaluateIncentivesRequestDto context = request.context();
        String tenantId = required(context.tenantId(), "tenantId");
        String applicationId = required(context.applicationId(), "applicationId");
        String profileId = required(context.profileId(), "profileId");
        access.requireAdminAccess(tenantId, applicationId, user);
        access.requireActiveApplication(tenantId, applicationId, user, "fraud-score");

        int lookbackMinutes = normalizeLookback(request.lookbackMinutes());
        Instant since = Instant.now().minusSeconds(lookbackMinutes * 60L);
        String sourceClientId = firstNonBlank(request.sourceClientId(), access.sourceClientId(user));
        List<FraudScoreSignalDto> signals = new ArrayList<>();
        addContextSignals(signals, context, sourceClientId);
        addVelocitySignals(signals, tenantId, applicationId, profileId, context, since, lookbackMinutes);

        int score = Math.min(100, signals.stream().mapToInt(FraudScoreSignalDto::points).sum());
        String severity = severity(score);
        String action = recommendedAction(score);
        FraudScorePreviewResponseDto response = new FraudScorePreviewResponseDto(
                true,
                false,
                POLICY_VERSION,
                tenantId,
                applicationId,
                profileId,
                lookbackMinutes,
                score,
                severity,
                action,
                List.copyOf(signals),
                Instant.now());
        audit(response, request.note(), correlationId, sourceClientId, user);
        return response;
    }

    private void addContextSignals(List<FraudScoreSignalDto> signals,
                                   EvaluateIncentivesRequestDto context,
                                   String sourceClientId) {
        int couponCodeCount = nonBlankCouponCodes(context).size();
        int couponIdCount = couponIds(context).size();
        int selectorCount = couponCodeCount + couponIdCount;
        if (couponCodeCount >= 10) {
            add(signals, "COUPON_SELECTOR_BURST", 30,
                    "Many coupon codes were supplied in one incentive context",
                    evidence(
                            "couponCodeCount", couponCodeCount,
                            "couponIdCount", couponIdCount));
        } else if (couponCodeCount >= 4) {
            add(signals, "COUPON_SELECTOR_BURST", 15,
                    "Multiple coupon codes were supplied in one incentive context",
                    evidence(
                            "couponCodeCount", couponCodeCount,
                            "couponIdCount", couponIdCount));
        }
        if (selectorCount > 0 && sourceClientId == null) {
            add(signals, "MISSING_SOURCE_CLIENT", 10,
                    "Coupon-bearing context has no source client for runtime attribution",
                    evidence("couponSelectorCount", selectorCount));
        }
        if (couponIdCount > 1) {
            add(signals, "MULTIPLE_COUPON_IDS", 10,
                    "Multiple coupon ids were supplied for a single checkout context",
                    evidence("couponIdCount", couponIdCount));
        }
        BigDecimal subtotal = context.transaction() == null ? BigDecimal.ZERO : context.transaction().subtotal();
        if (subtotal != null && subtotal.compareTo(BigDecimal.valueOf(1_000)) >= 0) {
            add(signals, "HIGH_VALUE_TRANSACTION", 25,
                    "High-value transaction increases benefit abuse exposure",
                    evidence("subtotalBand", ">=1000"));
        } else if (subtotal != null && subtotal.compareTo(BigDecimal.valueOf(500)) >= 0) {
            add(signals, "HIGH_VALUE_TRANSACTION", 15,
                    "Medium-high transaction value increases benefit abuse exposure",
                    evidence("subtotalBand", ">=500"));
        }
    }

    private void addVelocitySignals(List<FraudScoreSignalDto> signals,
                                    String tenantId,
                                    String applicationId,
                                    String profileId,
                                    EvaluateIncentivesRequestDto context,
                                    Instant since,
                                    int lookbackMinutes) {
        long reservationCount = reservations.countByTenantIdAndApplicationIdAndProfileIdAndReservedAtGreaterThanEqual(
                tenantId, applicationId, profileId, since);
        long cancelledCount = reservations
                .countByTenantIdAndApplicationIdAndProfileIdAndStatusAndReservedAtGreaterThanEqual(
                        tenantId, applicationId, profileId, "CANCELLED", since);
        long expiredCount = reservations
                .countByTenantIdAndApplicationIdAndProfileIdAndStatusAndReservedAtGreaterThanEqual(
                        tenantId, applicationId, profileId, "EXPIRED", since);
        long redemptionCount = redemptions.countByTenantIdAndApplicationIdAndProfileIdAndRedeemedAtGreaterThanEqual(
                tenantId, applicationId, profileId, since);
        long reversedCount = redemptions
                .countByTenantIdAndApplicationIdAndProfileIdAndStatusAndReversedAtGreaterThanEqual(
                        tenantId, applicationId, profileId, "REVERSED", since);

        addThresholdSignal(signals,
                "RECENT_RESERVATION_VELOCITY",
                reservationCount,
                5,
                10,
                20,
                "Profile has high recent incentive reservation velocity",
                lookbackMinutes);
        addThresholdSignal(signals,
                "RECENT_REDEMPTION_VELOCITY",
                redemptionCount,
                3,
                6,
                12,
                "Profile has high recent incentive redemption velocity",
                lookbackMinutes);
        addThresholdSignal(signals,
                "ABANDONED_RESERVATION_VELOCITY",
                cancelledCount + expiredCount,
                3,
                6,
                10,
                "Profile has repeated cancelled or expired reservations",
                lookbackMinutes);
        if (reversedCount >= 2) {
            add(signals,
                    "RECENT_REVERSAL_HISTORY",
                    reversedCount >= 5 ? 35 : 25,
                    "Profile has recent reversed incentive redemptions",
                    evidence(
                            "count", reversedCount,
                            "lookbackMinutes", lookbackMinutes));
        }

        List<UUID> couponIds = couponIds(context);
        if (!couponIds.isEmpty()) {
            long couponReservationCount = reservations
                    .countByTenantIdAndApplicationIdAndCouponIdInAndReservedAtGreaterThanEqual(
                            tenantId, applicationId, couponIds, since);
            long couponRedemptionCount = redemptions
                    .countByTenantIdAndApplicationIdAndCouponIdInAndRedeemedAtGreaterThanEqual(
                            tenantId, applicationId, couponIds, since);
            addThresholdSignal(signals,
                    "COUPON_ID_SHARED_VELOCITY",
                    couponReservationCount + couponRedemptionCount,
                    10,
                    25,
                    50,
                    "Selected coupon ids have high recent cross-profile usage velocity",
                    lookbackMinutes);
        }

        String externalReference = blankToNull(context.externalReference());
        if (externalReference != null) {
            long externalReferenceUses = reservations
                    .countByTenantIdAndApplicationIdAndExternalReferenceAndReservedAtGreaterThanEqual(
                            tenantId, applicationId, externalReference, since)
                    + redemptions.countByTenantIdAndApplicationIdAndExternalReferenceAndRedeemedAtGreaterThanEqual(
                            tenantId, applicationId, externalReference, since);
            if (externalReferenceUses > 1) {
                add(signals,
                        "EXTERNAL_REFERENCE_REUSE",
                        externalReferenceUses >= 5 ? 35 : 20,
                        "External reference has been used repeatedly in the lookback window",
                        evidence(
                                "count", externalReferenceUses,
                                "lookbackMinutes", lookbackMinutes));
            }
        }
    }

    private void addThresholdSignal(List<FraudScoreSignalDto> signals,
                                    String code,
                                    long count,
                                    long lowThreshold,
                                    long mediumThreshold,
                                    long highThreshold,
                                    String message,
                                    int lookbackMinutes) {
        if (count >= highThreshold) {
            add(signals, code, 35, message, evidence("count", count, "lookbackMinutes", lookbackMinutes));
        } else if (count >= mediumThreshold) {
            add(signals, code, 25, message, evidence("count", count, "lookbackMinutes", lookbackMinutes));
        } else if (count >= lowThreshold) {
            add(signals, code, 15, message, evidence("count", count, "lookbackMinutes", lookbackMinutes));
        }
    }

    private void add(List<FraudScoreSignalDto> signals,
                     String code,
                     int points,
                     String message,
                     Map<String, Object> evidence) {
        signals.add(new FraudScoreSignalDto(code, signalSeverity(points), points, message, evidence));
    }

    private void audit(FraudScorePreviewResponseDto response,
                       String note,
                       String correlationId,
                       String sourceClientId,
                       CurrentUser user) {
        auditEvents.save(new IncentiveAuditEvent(
                response.tenantId(),
                response.applicationId(),
                response.profileId(),
                "fraud-score",
                "fraud_score.previewed",
                actorId(user),
                note,
                toJson(Map.of(
                        "policyVersion", response.policyVersion(),
                        "score", response.score(),
                        "severity", response.severity(),
                        "recommendedAction", response.recommendedAction(),
                        "lookbackMinutes", response.lookbackMinutes(),
                        "signals", response.signals().stream().map(FraudScoreSignalDto::code).toList())),
                correlationId,
                sourceClientId));
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize fraud score audit payload", ex);
        }
    }

    private List<String> nonBlankCouponCodes(EvaluateIncentivesRequestDto context) {
        if (context.couponCodes() == null) {
            return List.of();
        }
        return context.couponCodes().stream()
                .map(this::blankToNull)
                .filter(value -> value != null)
                .distinct()
                .toList();
    }

    private List<UUID> couponIds(EvaluateIncentivesRequestDto context) {
        if (context.couponIds() == null) {
            return List.of();
        }
        return context.couponIds().stream()
                .filter(value -> value != null)
                .collect(java.util.stream.Collectors.collectingAndThen(
                        java.util.stream.Collectors.toCollection(LinkedHashSet::new),
                        List::copyOf));
    }

    private int normalizeLookback(Integer requested) {
        if (requested == null || requested <= 0) {
            return DEFAULT_LOOKBACK_MINUTES;
        }
        return Math.min(requested, MAX_LOOKBACK_MINUTES);
    }

    private String required(String value, String field) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            throw new BadRequestException(field + " is required");
        }
        return normalized;
    }

    private String firstNonBlank(String first, String second) {
        String normalized = blankToNull(first);
        return normalized == null ? blankToNull(second) : normalized;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private Map<String, Object> evidence(Object... pairs) {
        Map<String, Object> values = new LinkedHashMap<>();
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            Object key = pairs[i];
            Object value = pairs[i + 1];
            if (key != null && value != null) {
                values.put(String.valueOf(key), value);
            }
        }
        return values;
    }

    private String severity(int score) {
        if (score >= 75) {
            return "CRITICAL";
        }
        if (score >= 50) {
            return "HIGH";
        }
        if (score >= 25) {
            return "MEDIUM";
        }
        return "LOW";
    }

    private String signalSeverity(int points) {
        if (points >= 30) {
            return "HIGH";
        }
        if (points >= 15) {
            return "MEDIUM";
        }
        return "LOW";
    }

    private String recommendedAction(int score) {
        if (score >= 75) {
            return "BLOCK";
        }
        if (score >= 50) {
            return "REVIEW";
        }
        if (score >= 25) {
            return "CHALLENGE";
        }
        return "ALLOW";
    }

    private String actorId(CurrentUser user) {
        if (user == null || user.id() == null) {
            return "system";
        }
        return user.id().toString();
    }
}
