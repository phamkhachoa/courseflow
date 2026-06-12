package edu.courseflow.gradebook.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for the pure weighted-aggregation math ({@link GradebookService#categoryContribution}).
 * These guard P0-4: a perfect category must contribute exactly its weight (never more), so the
 * course total stays within 100 and a real (non-zero) weight produces a non-zero final score.
 */
class GradebookAggregationTest {

    private static final BigDecimal WEIGHT_40 = new BigDecimal("40");
    private static final BigDecimal ONE = BigDecimal.ONE;
    private static final BigDecimal HALF = new BigDecimal("0.5");

    @Test
    void sumPerfectCategoryContributesExactlyItsWeight() {
        // Three items all at 100% with weight 40 must yield 40, not 120 (the old SUM bug).
        BigDecimal result = GradebookService.categoryContribution(
                "SUM",
                List.of(ONE, ONE, ONE),
                List.of(new BigDecimal("10"), new BigDecimal("20"), new BigDecimal("70")),
                List.of(ONE, ONE, ONE),
                WEIGHT_40);
        assertThat(result).isEqualByComparingTo("40");
    }

    @Test
    void sumIsPointsWeightedNotItemCountWeighted() {
        // 10/10 + 0/90 = 10 earned of 100 possible = 10% of the category -> 0.10 * 40 = 4.
        BigDecimal result = GradebookService.categoryContribution(
                "SUM",
                List.of(ONE, BigDecimal.ZERO),
                List.of(new BigDecimal("10"), new BigDecimal("90")),
                List.of(ONE, ONE),
                WEIGHT_40);
        assertThat(result).isEqualByComparingTo("4.00");
    }

    @Test
    void meanAveragesPercentagesThenScalesByWeight() {
        // mean(100%, 50%) = 75% -> 0.75 * 40 = 30.
        BigDecimal result = GradebookService.categoryContribution(
                "MEAN",
                List.of(ONE, HALF),
                List.of(new BigDecimal("100"), new BigDecimal("100")),
                List.of(ONE, ONE),
                WEIGHT_40);
        assertThat(result).isEqualByComparingTo("30.0000");
    }

    @Test
    void weightedMeanUsesItemWeights() {
        // (100%*3 + 0%*1) / 4 = 0.75 -> 0.75 * 40 = 30.
        BigDecimal result = GradebookService.categoryContribution(
                "WEIGHTED_MEAN",
                List.of(ONE, BigDecimal.ZERO),
                List.of(new BigDecimal("100"), new BigDecimal("100")),
                List.of(new BigDecimal("3"), ONE),
                WEIGHT_40);
        assertThat(result).isEqualByComparingTo("30.0000");
    }

    @Test
    void weightedMeanPerfectCategoryContributesFullWeight() {
        BigDecimal result = GradebookService.categoryContribution(
                "WEIGHTED_MEAN",
                List.of(ONE, ONE),
                List.of(new BigDecimal("100"), new BigDecimal("50")),
                List.of(ONE, new BigDecimal("2")),
                WEIGHT_40);
        assertThat(result).isEqualByComparingTo("40.0000");
    }

    @Test
    void nullMethodDefaultsToWeightedMean() {
        BigDecimal result = GradebookService.categoryContribution(
                null,
                List.of(ONE),
                List.of(new BigDecimal("100")),
                List.of(ONE),
                WEIGHT_40);
        assertThat(result).isEqualByComparingTo("40.0000");
    }

    @Test
    void emptyCategoryContributesZero() {
        BigDecimal result = GradebookService.categoryContribution(
                "SUM", List.of(), List.of(), List.of(), WEIGHT_40);
        assertThat(result).isEqualByComparingTo("0");
    }

    @Test
    void zeroWeightContributesZeroEvenWhenPerfect() {
        // Mirrors the consumer-seeded weight=0 category: contributes nothing until the weight is set.
        BigDecimal result = GradebookService.categoryContribution(
                "WEIGHTED_MEAN",
                List.of(ONE),
                List.of(new BigDecimal("100")),
                List.of(ONE),
                BigDecimal.ZERO);
        assertThat(result).isEqualByComparingTo("0");
    }
}
