package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.EvaluateIncentivesRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.RuleSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.TransactionContextDto;
import edu.courseflow.promotion.model.CampaignDefinitionSnapshot;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCampaignVersion;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class IncentiveDecisionEngineTest {

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final IncentiveDecisionEngine engine = new IncentiveDecisionEngine(objectMapper);

    @Test
    void percentOffRespectsMinOrderAndMaxDiscountCap() {
        CampaignDefinitionSnapshot campaign = campaign(
                List.of(new RuleSpecDto("MIN_ORDER_AMOUNT", 1, Map.of("amount", 100, "currency", "USD"))),
                List.of(new ActionSpecDto("ORDER_PERCENT_OFF", 1, Map.of("percent", 10, "maxAmount", 15))));

        IncentiveDecisionEngine.Decision decision = engine.decide(campaign, request("NEW", "spring"));

        assertThat(decision.eligible()).isTrue();
        assertThat(decision.effects()).hasSize(1);
        assertThat(decision.effects().getFirst().amount()).isEqualByComparingTo("12.00");
        assertThat(decision.effects().getFirst().benefitType()).isEqualTo("DISCOUNT");
        assertThat(decision.effects().getFirst().unit()).isEqualTo("MONEY");
        assertThat(decision.effects().getFirst().actionType()).isEqualTo("ORDER_PERCENT_OFF");
        assertThat(decision.effects().getFirst().effectId()).contains("ORDER_PERCENT_OFF");
        assertThat(decision.effects().getFirst().campaignVersion()).isEqualTo(1);
    }

    @Test
    void missingRequiredAttributeFailsClosed() {
        CampaignDefinitionSnapshot campaign = campaign(
                List.of(new RuleSpecDto("PROFILE_SEGMENT", 1, Map.of("segment", "VIP"))),
                List.of(new ActionSpecDto("ORDER_FIXED_OFF", 1, Map.of("amount", 5))));

        IncentiveDecisionEngine.Decision decision = engine.decide(campaign, request("NEW", "spring"));

        assertThat(decision.eligible()).isFalse();
        assertThat(decision.reasonCodes()).contains("RULE_PROFILE_SEGMENT_NOT_MATCHED");
    }

    @Test
    void unknownRuleTypeIsRejected() {
        assertThatThrownBy(() -> engine.toRulesJson(List.of(
                new RuleSpecDto("SCRIPT", 1, Map.of("expression", "true")))))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unsupported incentive rule type");
    }

    @Test
    void lineFixedOffTargetsFirstEligibleCategory() {
        CampaignDefinitionSnapshot campaign = campaign(
                List.of(new RuleSpecDto("ITEM_CATEGORY_INCLUDE", 1, Map.of("category", "spring"))),
                List.of(new ActionSpecDto("LINE_FIXED_OFF", 1, Map.of("amount", 20, "category", "spring"))));

        IncentiveDecisionEngine.Decision decision = engine.decide(campaign, request("NEW", "spring"));

        assertThat(decision.eligible()).isTrue();
        assertThat(decision.effects().getFirst().targetType()).isEqualTo("ITEM");
        assertThat(decision.effects().getFirst().targetId()).isEqualTo("item-1");
    }

    @Test
    void campaignCurrencyMismatchFailsClosed() {
        CampaignDefinitionSnapshot campaign = campaign(
                List.of(),
                List.of(new ActionSpecDto("ORDER_FIXED_OFF", 1, Map.of("amount", 5))));

        IncentiveDecisionEngine.Decision decision = engine.decide(campaign, request("NEW", "spring", "EUR"));

        assertThat(decision.eligible()).isFalse();
        assertThat(decision.reasonCodes()).containsExactly("CURRENCY_NOT_MATCHED");
    }

    @Test
    void orderFixedOffCannotExceedSubtotal() {
        CampaignDefinitionSnapshot campaign = campaign(
                List.of(),
                List.of(new ActionSpecDto("ORDER_FIXED_OFF", 1, Map.of("amount", 500))));

        IncentiveDecisionEngine.Decision decision = engine.decide(campaign, request("NEW", "spring"));

        assertThat(decision.eligible()).isTrue();
        assertThat(decision.effects().getFirst().amount()).isEqualByComparingTo("120.00");
    }

    @Test
    void percentOffAboveOneHundredIsRejected() {
        assertThatThrownBy(() -> engine.toActionsJson(List.of(
                new ActionSpecDto("ORDER_PERCENT_OFF", 1, Map.of("percent", 101)))))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Percent parameter must be between 0 and 100");
    }

    private CampaignDefinitionSnapshot campaign(List<RuleSpecDto> rules, List<ActionSpecDto> actions) {
        IncentiveCampaign campaign = new IncentiveCampaign(
                "courseflow",
                "lms",
                "WELCOME10",
                "Welcome",
                null,
                "PROMOTION",
                Instant.now().minusSeconds(60),
                Instant.now().plusSeconds(3600),
                100,
                false,
                true,
                false,
                "ALL",
                "USD",
                engine.toRulesJson(rules),
                engine.toActionsJson(actions),
                100,
                1,
                "test");
        return new IncentiveCampaignVersion(campaign, 1, "test");
    }

    private EvaluateIncentivesRequestDto request(String segment, String category) {
        return request(segment, category, "USD");
    }

    private EvaluateIncentivesRequestDto request(String segment, String category, String currency) {
        return new EvaluateIncentivesRequestDto(
                "courseflow",
                "lms",
                "profile-1",
                "order-1",
                "WEB",
                currency,
                List.of("WELCOME10"),
                new TransactionContextDto(BigDecimal.valueOf(120), BigDecimal.TEN),
                List.of(new IncentiveItemDto(
                        "item-1",
                        "COURSE",
                        1,
                        BigDecimal.valueOf(120),
                        Map.of("category", category))),
                Map.of("segment", segment));
    }
}
