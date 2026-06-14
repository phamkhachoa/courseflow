package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class IncentiveCatalogServiceTest {

    private final IncentiveCatalogService service = new IncentiveCatalogService();

    @Test
    void catalogDescribesSupportedRulesActionsEffectsAndIdempotency() {
        var catalog = service.catalog();

        assertThat(catalog.catalogVersion()).isEqualTo("incentive-contract-v1");
        assertThat(catalog.factContractVersion()).isEqualTo("generic-commerce-facts-v1");
        assertThat(catalog.rules()).extracting("type")
                .containsExactly("MIN_ORDER_AMOUNT", "PROFILE_SEGMENT", "ITEM_CATEGORY_INCLUDE", "CHANNEL_MATCH");
        assertThat(catalog.actions()).extracting("type")
                .containsExactly("ORDER_PERCENT_OFF", "ORDER_FIXED_OFF", "LINE_FIXED_OFF", "FREE_SHIPPING");
        assertThat(catalog.effects()).extracting("benefitType")
                .contains("DISCOUNT", "CREDIT", "ENTITLEMENT", "POINTS_EARN_INTENT");
        assertThat(catalog.reasonCodes()).extracting("code")
                .contains(
                        "ELIGIBLE",
                        "NO_ELIGIBLE_INCENTIVE",
                        "RULES_NOT_MATCHED",
                        "NO_EFFECTS",
                        "QUOTA_EXHAUSTED",
                        "RESERVED",
                        "RESERVATION_EXPIRED",
                        "COMMITTED",
                        "CANCELLED",
                        "REVERSED");
        assertThat(catalog.reasonCodes()).extracting("code")
                .doesNotContain("RULE_*_NOT_MATCHED");
        assertThat(catalog.idempotency().preferredLocation()).isEqualTo("body-or-header");
        assertThat(catalog.idempotency().headerName()).isEqualTo("Idempotency-Key");
        assertThat(catalog.idempotency().bodyFields())
                .contains("CouponImportDryRunRequestDto.idempotencyKey");
        assertThat(catalog.portabilityNotes()).allSatisfy(note -> assertThat(note).doesNotContain("courseId", "enrollmentId", "studentId"));
    }
}
