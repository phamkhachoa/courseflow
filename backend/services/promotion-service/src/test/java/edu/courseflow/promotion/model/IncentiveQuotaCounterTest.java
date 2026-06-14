package edu.courseflow.promotion.model;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class IncentiveQuotaCounterTest {

    @Test
    void effectiveLimitCanTightenAnExistingCounter() {
        IncentiveQuotaCounter counter = new IncentiveQuotaCounter(
                "courseflow", "lms", "CAMPAIGN", "campaign-1",
                IncentiveQuotaCounter.WILDCARD_PROFILE, 10000);
        counter.consumeAgainstLimit(1);

        assertThat(counter.hasAvailableCapacity(1)).isFalse();
        assertThatThrownBy(() -> counter.consumeAgainstLimit(1))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Quota exhausted");
    }
}
