package edu.courseflow.events.incentive;

import java.math.BigDecimal;
import java.util.Map;

public record IncentiveEffectPayload(
        String effectId,
        String type,
        String benefitType,
        String actionType,
        String targetType,
        String targetId,
        BigDecimal amount,
        String currency,
        String unit,
        BigDecimal quantity,
        Integer campaignVersion,
        Map<String, Object> metadata
) {
}
