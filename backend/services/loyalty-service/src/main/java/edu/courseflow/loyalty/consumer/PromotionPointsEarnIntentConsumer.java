package edu.courseflow.loyalty.consumer;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROMOTION_POINTS_INTENT_INVALID;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.events.incentive.IncentiveEffectPayload;
import edu.courseflow.events.incentive.IncentiveRedemptionCommittedEvent;
import edu.courseflow.events.incentive.IncentiveRedemptionReversedEvent;
import edu.courseflow.loyalty.dto.LoyaltyDtos.PointsMutationRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ReversePointsRequestDto;
import edu.courseflow.loyalty.model.LoyaltyPromotionPointEffect;
import edu.courseflow.loyalty.security.PromotionServiceActorFactory;
import edu.courseflow.loyalty.service.LoyaltyProcessedInboundEventService;
import edu.courseflow.loyalty.service.LoyaltyPromotionPointEffectService;
import edu.courseflow.loyalty.service.LoyaltyService;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class PromotionPointsEarnIntentConsumer {

    private static final String BENEFIT_TYPE = "POINTS_EARN_INTENT";
    private static final String ACTION_TYPE = "LOYALTY_POINTS_EARN";

    private final LoyaltyService loyaltyService;
    private final ObjectMapper objectMapper;
    private final PromotionServiceActorFactory promotionServiceActorFactory;
    private final LoyaltyProcessedInboundEventService processedEvents;
    private final LoyaltyPromotionPointEffectService expectedEffects;

    public PromotionPointsEarnIntentConsumer(
            LoyaltyService loyaltyService,
            ObjectMapper objectMapper,
            PromotionServiceActorFactory promotionServiceActorFactory,
            LoyaltyProcessedInboundEventService processedEvents,
            LoyaltyPromotionPointEffectService expectedEffects) {
        this.loyaltyService = loyaltyService;
        this.objectMapper = objectMapper;
        this.promotionServiceActorFactory = promotionServiceActorFactory;
        this.processedEvents = processedEvents;
        this.expectedEffects = expectedEffects;
    }

    @KafkaListener(
            topics = "${courseflow.loyalty.promotion-points-topic:incentive.redemption.committed}",
            groupId = "${courseflow.loyalty.promotion-points-group:loyalty-service}")
    public void onRedemptionCommitted(ConsumerRecord<String, String> record) throws Exception {
        String payload = record.value();
        String payloadHash = sha256Hex(payload == null ? "" : payload);
        IncentiveRedemptionCommittedEvent event = objectMapper.readValue(
                payload, IncentiveRedemptionCommittedEvent.class);
        handleInboundEvent(
                record.topic(),
                "incentive.redemption.committed",
                event.eventId(),
                event.redemptionId(),
                payloadHash,
                payload,
                () -> {
                    if (event.effects() == null || event.effects().isEmpty()) {
                        return;
                    }
                    for (IncentiveEffectPayload effect : event.effects()) {
                        if (!isPointsEarnIntent(effect)) {
                            continue;
                        }
                        earnPoints(record.topic(), payloadHash, event, effect);
                    }
                }
        );
    }

    @KafkaListener(
            topics = "${courseflow.loyalty.promotion-points-reversal-topic:incentive.redemption.reversed}",
            groupId = "${courseflow.loyalty.promotion-points-group:loyalty-service}")
    public void onRedemptionReversed(ConsumerRecord<String, String> record) throws Exception {
        String payload = record.value();
        String payloadHash = sha256Hex(payload == null ? "" : payload);
        IncentiveRedemptionReversedEvent event = objectMapper.readValue(
                payload, IncentiveRedemptionReversedEvent.class);
        handleInboundEvent(
                record.topic(),
                "incentive.redemption.reversed",
                event.eventId(),
                event.redemptionId(),
                payloadHash,
                payload,
                () -> {
                    if (event.effects() == null || event.effects().isEmpty()) {
                        return;
                    }
                    for (IncentiveEffectPayload effect : event.effects()) {
                        if (!isPointsEarnIntent(effect)) {
                            continue;
                        }
                        reversePoints(record.topic(), payloadHash, event, effect);
                    }
                }
        );
    }

    private void handleInboundEvent(
            String sourceTopic,
            String sourceEventType,
            String eventId,
            String aggregateId,
            String payloadHash,
            String payload,
            ThrowingRunnable handler) throws Exception {
        String processedEventId = inboundEventId(eventId, payloadHash);
        if (!processedEvents.shouldProcess(sourceEventType, processedEventId, payloadHash)) {
            return;
        }
        handler.run();
        processedEvents.recordProcessed(
                sourceTopic,
                sourceEventType,
                processedEventId,
                blankToNull(aggregateId),
                payloadHash);
    }

    private void earnPoints(
            String sourceTopic,
            String payloadHash,
            IncentiveRedemptionCommittedEvent event,
            IncentiveEffectPayload effect) {
        String programId = metadataText(effect, "programId");
        String profileId = firstNonBlank(effect.targetId(), event.profileId());
        Long points = points(effect);
        if (event.tenantId() == null || event.tenantId().isBlank()
                || event.applicationId() == null || event.applicationId().isBlank()
                || event.redemptionId() == null || event.redemptionId().isBlank()
                || effect.effectId() == null || effect.effectId().isBlank()
                || programId == null || profileId == null || points == null || points <= 0) {
            throw BadRequestException.coded(
                    LOYALTY_PROMOTION_POINTS_INTENT_INVALID,
                    "Malformed POINTS_EARN_INTENT in incentive redemption committed event");
        }

        String operationKey = promotionOperationKey(event, effect);
        expectedEffects.recordExpectedEffect(new LoyaltyPromotionPointEffect(
                sourceTopic,
                "incentive.redemption.committed",
                inboundEventId(event.eventId(), payloadHash),
                event.redemptionId().trim(),
                effect.effectId().trim(),
                "EARN",
                event.tenantId().trim(),
                event.applicationId().trim(),
                programId,
                profileId,
                points,
                operationKey,
                operationKey,
                event.correlationId(),
                payloadHash,
                occurredAt(event)));
        loyaltyService.earn(new PointsMutationRequestDto(
                event.tenantId(),
                event.applicationId(),
                programId,
                profileId,
                points,
                operationKey,
                operationKey,
                "Promotion points earn intent",
                event.correlationId(),
                occurredAt(event),
                null,
                metadata(event, effect)
        ), promotionServiceActorFactory.currentUser());
    }

    private void reversePoints(
            String sourceTopic,
            String payloadHash,
            IncentiveRedemptionReversedEvent event,
            IncentiveEffectPayload effect) {
        String programId = metadataText(effect, "programId");
        if (event.tenantId() == null || event.tenantId().isBlank()
                || event.applicationId() == null || event.applicationId().isBlank()
                || event.redemptionId() == null || event.redemptionId().isBlank()
                || effect.effectId() == null || effect.effectId().isBlank()
                || programId == null) {
            throw BadRequestException.coded(
                    LOYALTY_PROMOTION_POINTS_INTENT_INVALID,
                    "Malformed POINTS_EARN_INTENT in incentive redemption reversed event");
        }

        String originalOperationKey = promotionOperationKey(event.redemptionId(), effect.effectId());
        String reversalKey = promotionReversalOperationKey(event.redemptionId(), effect.effectId());
        Long points = points(effect);
        expectedEffects.recordExpectedEffect(new LoyaltyPromotionPointEffect(
                sourceTopic,
                "incentive.redemption.reversed",
                inboundEventId(event.eventId(), payloadHash),
                event.redemptionId().trim(),
                effect.effectId().trim(),
                "REVERSE",
                event.tenantId().trim(),
                event.applicationId().trim(),
                programId,
                firstNonBlank(firstNonBlank(effect.targetId(), event.profileId()), "unknown"),
                points == null ? 0L : points,
                originalOperationKey,
                reversalKey,
                event.correlationId(),
                payloadHash,
                Instant.now()));
        loyaltyService.reverseBySourceReference(
                event.tenantId(),
                event.applicationId(),
                programId,
                originalOperationKey,
                new ReversePointsRequestDto(
                        reversalKey,
                        firstNonBlank(event.reason(), "Promotion redemption reversed"),
                        event.correlationId(),
                        reversalMetadata(event, effect, originalOperationKey)),
                promotionServiceActorFactory.currentUser());
    }

    private static boolean isPointsEarnIntent(IncentiveEffectPayload effect) {
        return effect != null
                && BENEFIT_TYPE.equalsIgnoreCase(effect.benefitType())
                && ACTION_TYPE.equalsIgnoreCase(effect.actionType());
    }

    private static Long points(IncentiveEffectPayload effect) {
        BigDecimal raw = effect.quantity() != null ? effect.quantity() : effect.amount();
        if (raw == null || raw.signum() <= 0) {
            return null;
        }
        try {
            return raw.setScale(0, RoundingMode.UNNECESSARY).longValueExact();
        } catch (ArithmeticException ex) {
            return null;
        }
    }

    private static String metadataText(IncentiveEffectPayload effect, String key) {
        if (effect.metadata() == null) {
            return null;
        }
        Object value = effect.metadata().get(key);
        if (value == null || String.valueOf(value).isBlank()) {
            return null;
        }
        return String.valueOf(value).trim();
    }

    private static String promotionOperationKey(IncentiveRedemptionCommittedEvent event, IncentiveEffectPayload effect) {
        return promotionOperationKey(event.redemptionId(), effect.effectId());
    }

    private static String promotionOperationKey(String redemptionId, String effectId) {
        return "promotion:" + redemptionId.trim() + ":" + sha256Hex(effectId.trim()).substring(0, 32);
    }

    private static String promotionReversalOperationKey(String redemptionId, String effectId) {
        return "promotion-reversal:" + redemptionId.trim() + ":" + sha256Hex(effectId.trim()).substring(0, 32);
    }

    private static Map<String, Object> metadata(IncentiveRedemptionCommittedEvent event, IncentiveEffectPayload effect) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("source", "promotion-service");
        metadata.put("sourceEventId", event.eventId());
        metadata.put("redemptionId", event.redemptionId());
        metadata.put("reservationId", event.reservationId());
        metadata.put("campaignId", event.campaignId());
        metadata.put("campaignVersion", event.campaignVersion());
        metadata.put("couponId", event.couponId());
        metadata.put("externalReference", event.externalReference());
        metadata.put("effectId", effect.effectId());
        metadata.put("effectType", effect.type());
        metadata.put("benefitType", effect.benefitType());
        metadata.put("actionType", effect.actionType());
        if (effect.metadata() != null && !effect.metadata().isEmpty()) {
            metadata.put("effectMetadata", effect.metadata());
        }
        return metadata;
    }

    private static Map<String, Object> reversalMetadata(
            IncentiveRedemptionReversedEvent event,
            IncentiveEffectPayload effect,
            String originalOperationKey) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("source", "promotion-service");
        metadata.put("sourceEventId", event.eventId());
        metadata.put("redemptionId", event.redemptionId());
        metadata.put("reservationId", event.reservationId());
        metadata.put("campaignId", event.campaignId());
        metadata.put("campaignVersion", event.campaignVersion());
        metadata.put("couponId", event.couponId());
        metadata.put("externalReference", event.externalReference());
        metadata.put("effectId", effect.effectId());
        metadata.put("effectType", effect.type());
        metadata.put("benefitType", effect.benefitType());
        metadata.put("actionType", effect.actionType());
        metadata.put("originalSourceReference", originalOperationKey);
        metadata.put("quotaReleased", event.quotaReleased());
        if (effect.metadata() != null && !effect.metadata().isEmpty()) {
            metadata.put("effectMetadata", effect.metadata());
        }
        return metadata;
    }

    private static Instant occurredAt(IncentiveRedemptionCommittedEvent event) {
        return event.committedAt() == null ? Instant.now() : event.committedAt();
    }

    private static String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first.trim();
        }
        if (second != null && !second.isBlank()) {
            return second.trim();
        }
        return null;
    }

    private static String inboundEventId(String eventId, String payloadHash) {
        String normalized = blankToNull(eventId);
        return normalized == null ? "payload:" + payloadHash : normalized;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private static String sha256Hex(String value) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is required", ex);
        }
    }

    @FunctionalInterface
    private interface ThrowingRunnable {
        void run() throws Exception;
    }

}
