package edu.courseflow.peerreview.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for the server-side peer-review aggregate ({@link PeerReviewService#mean}). This guards
 * the P0 fix: the finalized score must be computed from the actual submitted review scores, not taken
 * from the client.
 */
class PeerReviewAggregateTest {

    @Test
    void meanOfSeveralScores() {
        BigDecimal result = PeerReviewService.mean(List.of(
                new BigDecimal("80"), new BigDecimal("90"), new BigDecimal("70")));
        assertThat(result).isEqualByComparingTo("80.00");
    }

    @Test
    void meanRoundsHalfUpToTwoDecimals() {
        // (80 + 85 + 81) / 3 = 82.0; (80 + 81) / 2 = 80.5
        assertThat(PeerReviewService.mean(List.of(new BigDecimal("80"), new BigDecimal("81"))))
                .isEqualByComparingTo("80.50");
        // (10 + 20 + 25) / 3 = 18.3333 -> 18.33
        assertThat(PeerReviewService.mean(List.of(
                new BigDecimal("10"), new BigDecimal("20"), new BigDecimal("25"))))
                .isEqualByComparingTo("18.33");
    }

    @Test
    void meanOfSingleScoreIsThatScore() {
        assertThat(PeerReviewService.mean(List.of(new BigDecimal("73.5"))))
                .isEqualByComparingTo("73.50");
    }
}
