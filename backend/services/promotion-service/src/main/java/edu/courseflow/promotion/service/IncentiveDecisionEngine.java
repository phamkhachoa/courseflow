package edu.courseflow.promotion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveEffectDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.RuleSpecDto;
import edu.courseflow.promotion.model.CampaignDefinitionSnapshot;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class IncentiveDecisionEngine {

    private static final TypeReference<List<RuleSpecDto>> RULE_LIST = new TypeReference<>() {
    };
    private static final TypeReference<List<ActionSpecDto>> ACTION_LIST = new TypeReference<>() {
    };
    private static final Set<String> RULE_TYPES = Set.of(
            "MIN_ORDER_AMOUNT",
            "PROFILE_SEGMENT",
            "ITEM_CATEGORY_INCLUDE",
            "CHANNEL_MATCH");
    private static final Set<String> ACTION_TYPES = Set.of(
            "ORDER_PERCENT_OFF",
            "ORDER_FIXED_OFF",
            "LINE_FIXED_OFF",
            "FREE_SHIPPING",
            "LOYALTY_POINTS_EARN");

    private final ObjectMapper objectMapper;

    public IncentiveDecisionEngine(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void validateRules(List<RuleSpecDto> rules) {
        for (RuleSpecDto rule : safeRules(rules)) {
            String type = normalize(rule.type());
            if (!RULE_TYPES.contains(type)) {
                throw new IllegalArgumentException("Unsupported incentive rule type: " + rule.type());
            }
            switch (type) {
                case "MIN_ORDER_AMOUNT" -> requirePositiveAmount(rule.parameters(), "amount");
                case "PROFILE_SEGMENT" -> requireAny(rule.parameters(), "segment", "segments");
                case "ITEM_CATEGORY_INCLUDE" -> requireAny(rule.parameters(), "category", "categories");
                case "CHANNEL_MATCH" -> requireAny(rule.parameters(), "channel", "channels");
                default -> throw new IllegalArgumentException("Unsupported incentive rule type: " + rule.type());
            }
        }
    }

    public void validateActions(List<ActionSpecDto> actions) {
        if (actions == null || actions.isEmpty()) {
            throw new IllegalArgumentException("At least one incentive action is required");
        }
        for (ActionSpecDto action : actions) {
            String type = normalize(action.type());
            if (!ACTION_TYPES.contains(type)) {
                throw new IllegalArgumentException("Unsupported incentive action type: " + action.type());
            }
            switch (type) {
                case "ORDER_PERCENT_OFF" -> {
                    requirePercent(action.parameters(), "percent");
                    if (safeMap(action.parameters()).containsKey("maxAmount")) {
                        requirePositiveAmount(action.parameters(), "maxAmount");
                    }
                }
                case "ORDER_FIXED_OFF", "LINE_FIXED_OFF" -> requirePositiveAmount(action.parameters(), "amount");
                case "FREE_SHIPPING" -> {
                }
                case "LOYALTY_POINTS_EARN" -> {
                    requirePositiveAmount(action.parameters(), "points");
                    requireProgramId(action.parameters());
                }
                default -> throw new IllegalArgumentException("Unsupported incentive action type: " + action.type());
            }
        }
    }

    public Decision decide(CampaignDefinitionSnapshot campaign, EvaluateIncentivesRequestDto request) {
        if (campaign.getCurrency() != null && !campaign.getCurrency().isBlank()
                && !campaign.getCurrency().equalsIgnoreCase(request.currency())) {
            return new Decision(false, List.of(), List.of("CURRENCY_NOT_MATCHED"));
        }
        List<RuleSpecDto> rules = rules(campaign.getRulesJson());
        validateRules(rules);
        List<String> reasons = new ArrayList<>();
        boolean matched = matches(rules, campaign.getMatchPolicy(), request, reasons);
        if (!matched) {
            return new Decision(false, List.of(), reasons.isEmpty() ? List.of("RULES_NOT_MATCHED") : List.copyOf(reasons));
        }
        List<ActionSpecDto> actions = actions(campaign.getActionsJson());
        validateActions(actions);
        List<IncentiveEffectDto> effects = resolveEffects(campaign, actions, request);
        if (effects.isEmpty()) {
            return new Decision(false, List.of(), List.of("NO_EFFECTS"));
        }
        return new Decision(true, effects, List.of("ELIGIBLE"));
    }

    public List<RuleSpecDto> rules(String json) {
        return readList(json, RULE_LIST);
    }

    public List<ActionSpecDto> actions(String json) {
        return readList(json, ACTION_LIST);
    }

    public String toRulesJson(List<RuleSpecDto> rules) {
        validateRules(rules);
        return write(safeRules(rules));
    }

    public String toActionsJson(List<ActionSpecDto> actions) {
        validateActions(actions);
        return write(actions);
    }

    private boolean matches(List<RuleSpecDto> rules, String matchPolicy, EvaluateIncentivesRequestDto request,
                            List<String> reasons) {
        if (rules == null || rules.isEmpty()) {
            return true;
        }
        boolean any = false;
        for (RuleSpecDto rule : rules) {
            boolean matched = matches(rule, request);
            if (matched) {
                any = true;
            } else {
                reasons.add("RULE_" + normalize(rule.type()) + "_NOT_MATCHED");
            }
            if (!matched && !"ANY".equalsIgnoreCase(matchPolicy)) {
                return false;
            }
        }
        return "ANY".equalsIgnoreCase(matchPolicy) ? any : true;
    }

    private boolean matches(RuleSpecDto rule, EvaluateIncentivesRequestDto request) {
        Map<String, Object> parameters = safeMap(rule.parameters());
        return switch (normalize(rule.type())) {
            case "MIN_ORDER_AMOUNT" -> subtotal(request).compareTo(amount(parameters, "amount")) >= 0
                    && currencyMatches(parameters, request.currency());
            case "PROFILE_SEGMENT" -> containsParameter(parameters, "segment", "segments", attribute(request, "segment"));
            case "ITEM_CATEGORY_INCLUDE" -> items(request).stream()
                    .map(item -> attr(item.attributes(), "category"))
                    .anyMatch(category -> containsParameter(parameters, "category", "categories", category));
            case "CHANNEL_MATCH" -> containsParameter(parameters, "channel", "channels", request.channel());
            default -> false;
        };
    }

    private List<IncentiveEffectDto> resolveEffects(CampaignDefinitionSnapshot campaign, List<ActionSpecDto> actions,
                                                    EvaluateIncentivesRequestDto request) {
        List<IncentiveEffectDto> effects = new ArrayList<>();
        BigDecimal remainingOrderDiscount = subtotal(request);
        for (ActionSpecDto action : actions) {
            Map<String, Object> parameters = safeMap(action.parameters());
            String type = normalize(action.type());
            switch (type) {
                case "ORDER_PERCENT_OFF" -> {
                    BigDecimal percent = amount(parameters, "percent");
                    BigDecimal amount = subtotal(request)
                            .multiply(percent)
                            .divide(BigDecimal.valueOf(100), 8, RoundingMode.HALF_UP);
                    BigDecimal maxAmount = optionalAmount(parameters, "maxAmount");
                    if (maxAmount != null && amount.compareTo(maxAmount) > 0) {
                        amount = maxAmount;
                    }
                    amount = cap(amount, remainingOrderDiscount);
                    remainingOrderDiscount = remainingOrderDiscount.subtract(amount).max(BigDecimal.ZERO);
                    addMoneyEffect(effects, type, "ORDER", null, amount, request.currency(), campaign);
                }
                case "ORDER_FIXED_OFF" -> {
                    BigDecimal amount = cap(amount(parameters, "amount"), remainingOrderDiscount);
                    remainingOrderDiscount = remainingOrderDiscount.subtract(amount).max(BigDecimal.ZERO);
                    addMoneyEffect(effects, type, "ORDER", null, amount, request.currency(), campaign);
                }
                case "LINE_FIXED_OFF" -> {
                    BigDecimal amount = amount(parameters, "amount");
                    for (IncentiveItemDto item : items(request)) {
                        if (!parameters.containsKey("category")
                                || containsParameter(parameters, "category", "categories", attr(item.attributes(), "category"))) {
                            BigDecimal lineTotal = item.unitPrice().multiply(BigDecimal.valueOf(item.quantity()));
                            addMoneyEffect(effects, type, "ITEM", item.id(), cap(amount, lineTotal), request.currency(),
                                    campaign);
                            break;
                        }
                    }
                }
                case "FREE_SHIPPING" -> {
                    BigDecimal shipping = request.transaction().shippingAmount();
                    if (shipping != null && shipping.compareTo(BigDecimal.ZERO) > 0) {
                        addMoneyEffect(effects, type, "SHIPPING", null, shipping, request.currency(),
                                campaign);
                    }
                }
                case "LOYALTY_POINTS_EARN" -> addPointsEarnIntent(effects, parameters, request, campaign);
                default -> throw new IllegalArgumentException("Unsupported incentive action type: " + action.type());
            }
        }
        return effects.stream()
                .filter(effect -> effect.amount() != null && effect.amount().compareTo(BigDecimal.ZERO) > 0)
                .map(effect -> {
                    BigDecimal roundedAmount = effect.amount().setScale(2, RoundingMode.HALF_UP);
                    BigDecimal roundedQuantity = effect.quantity() == null
                            ? roundedAmount
                            : effect.quantity().setScale(2, RoundingMode.HALF_UP);
                    return new IncentiveEffectDto(
                            effect.type(),
                            effect.targetType(),
                            effect.targetId(),
                            roundedAmount,
                            effect.currency(),
                            effect.metadata(),
                            effect.effectId(),
                            effect.benefitType(),
                            effect.actionType(),
                            effect.unit(),
                            roundedQuantity,
                            effect.campaignVersion());
                })
                .toList();
    }

    private void addMoneyEffect(List<IncentiveEffectDto> effects, String type, String targetType, String targetId,
                                BigDecimal amount, String currency, CampaignDefinitionSnapshot campaign) {
        Integer campaignVersion = campaign.getCampaignVersion();
        String effectId = String.join(":",
                campaign.getCampaignId().toString(),
                String.valueOf(campaignVersion),
                type,
                targetType,
                targetId == null ? "order" : targetId);
        effects.add(new IncentiveEffectDto(
                type,
                targetType,
                targetId,
                amount,
                currency,
                Map.of(
                        "campaignId", campaign.getCampaignId().toString(),
                        "campaignVersion", campaignVersion),
                effectId,
                "DISCOUNT",
                type,
                "MONEY",
                amount,
                campaignVersion));
    }

    private void addPointsEarnIntent(List<IncentiveEffectDto> effects,
                                     Map<String, Object> parameters,
                                     EvaluateIncentivesRequestDto request,
                                     CampaignDefinitionSnapshot campaign) {
        BigDecimal points = amount(parameters, "points");
        String programId = String.valueOf(parameters.get("programId")).trim();
        Integer campaignVersion = campaign.getCampaignVersion();
        String effectId = String.join(":",
                campaign.getCampaignId().toString(),
                String.valueOf(campaignVersion),
                "LOYALTY_POINTS_EARN",
                programId,
                request.profileId());
        effects.add(new IncentiveEffectDto(
                "LOYALTY_POINTS_EARN",
                "LOYALTY_ACCOUNT",
                request.profileId(),
                points,
                null,
                Map.of(
                        "campaignId", campaign.getCampaignId().toString(),
                        "campaignVersion", campaignVersion,
                        "programId", programId,
                        "idempotencyKeyTemplate", "promotion:{redemptionId}:" + effectId),
                effectId,
                "POINTS_EARN_INTENT",
                "LOYALTY_POINTS_EARN",
                "POINT",
                points,
                campaignVersion));
    }

    private BigDecimal subtotal(EvaluateIncentivesRequestDto request) {
        return request.transaction() == null || request.transaction().subtotal() == null
                ? BigDecimal.ZERO
                : request.transaction().subtotal();
    }

    private List<IncentiveItemDto> items(EvaluateIncentivesRequestDto request) {
        return request.items() == null ? List.of() : request.items();
    }

    private String attribute(EvaluateIncentivesRequestDto request, String key) {
        return attr(request.attributes(), key);
    }

    private String attr(Map<String, Object> attributes, String key) {
        Object value = safeMap(attributes).get(key);
        return value == null ? null : String.valueOf(value);
    }

    private boolean currencyMatches(Map<String, Object> parameters, String requestCurrency) {
        Object currency = parameters.get("currency");
        return currency == null || String.valueOf(currency).equalsIgnoreCase(requestCurrency);
    }

    private void requireAmount(Map<String, Object> parameters, String key) {
        amount(safeMap(parameters), key);
    }

    private void requirePositiveAmount(Map<String, Object> parameters, String key) {
        BigDecimal value = amount(safeMap(parameters), key);
        if (value.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Amount parameter must be positive: " + key);
        }
    }

    private void requirePercent(Map<String, Object> parameters, String key) {
        BigDecimal value = amount(safeMap(parameters), key);
        if (value.compareTo(BigDecimal.ZERO) <= 0 || value.compareTo(BigDecimal.valueOf(100)) > 0) {
            throw new IllegalArgumentException("Percent parameter must be between 0 and 100: " + key);
        }
    }

    private void requireAny(Map<String, Object> parameters, String singleKey, String listKey) {
        Map<String, Object> safe = safeMap(parameters);
        if (!safe.containsKey(singleKey) && !safe.containsKey(listKey)) {
            throw new IllegalArgumentException("Missing parameter: " + singleKey + " or " + listKey);
        }
    }

    private void requireProgramId(Map<String, Object> parameters) {
        Map<String, Object> safe = safeMap(parameters);
        if (safe.containsKey("programIds")) {
            throw new IllegalArgumentException("Unsupported parameter for LOYALTY_POINTS_EARN: programIds");
        }
        Object programId = safe.get("programId");
        if (programId == null || String.valueOf(programId).isBlank()) {
            throw new IllegalArgumentException("Missing parameter: programId");
        }
    }

    private BigDecimal amount(Map<String, Object> parameters, String key) {
        Object value = safeMap(parameters).get(key);
        if (value == null) {
            throw new IllegalArgumentException("Missing amount parameter: " + key);
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ex) {
            throw new IllegalArgumentException("Invalid amount parameter: " + key, ex);
        }
    }

    private BigDecimal optionalAmount(Map<String, Object> parameters, String key) {
        return safeMap(parameters).containsKey(key) ? amount(parameters, key) : null;
    }

    private BigDecimal cap(BigDecimal amount, BigDecimal max) {
        if (amount == null) {
            return BigDecimal.ZERO;
        }
        if (max == null || max.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO;
        }
        return amount.compareTo(max) > 0 ? max : amount;
    }

    private boolean containsParameter(Map<String, Object> parameters, String singleKey, String listKey, String value) {
        if (value == null || value.isBlank()) {
            return false;
        }
        Object single = parameters.get(singleKey);
        if (single != null && value.equalsIgnoreCase(String.valueOf(single))) {
            return true;
        }
        Object list = parameters.get(listKey);
        if (list instanceof Collection<?> values) {
            return values.stream().anyMatch(candidate -> value.equalsIgnoreCase(String.valueOf(candidate)));
        }
        return false;
    }

    private List<RuleSpecDto> safeRules(List<RuleSpecDto> rules) {
        return rules == null ? List.of() : rules;
    }

    private Map<String, Object> safeMap(Map<String, Object> value) {
        return value == null ? Map.of() : value;
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toUpperCase();
    }

    private <T> List<T> readList(String json, TypeReference<List<T>> type) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<T> result = objectMapper.readValue(json, type);
            return result == null ? List.of() : result;
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("Invalid incentive JSON config", ex);
        }
    }

    private String write(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("Invalid incentive JSON config", ex);
        }
    }

    public record Decision(boolean eligible, List<IncentiveEffectDto> effects, List<String> reasonCodes) {
    }
}
