package edu.courseflow.promotion.model;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class IncentiveRedemptionTest {

    @Test
    void reverseIsIdempotentForRedeemedRedemption() {
        IncentiveRedemption redemption = new IncentiveRedemption(reservation());

        redemption.reverse("operator-1");
        redemption.reverse("operator-1");

        assertThat(redemption.getStatus()).isEqualTo("REVERSED");
        assertThat(redemption.getReversedAt()).isNotNull();
        assertThat(redemption.getReversedBy()).isEqualTo("operator-1");
    }

    @Test
    void alreadyReversedRedemptionCanBeSafelyReplayed() {
        IncentiveRedemption redemption = new IncentiveRedemption(reservation());
        redemption.reverse("operator-1");

        assertThatCode(() -> redemption.reverse("operator-2")).doesNotThrowAnyException();
        assertThat(redemption.getStatus()).isEqualTo("REVERSED");
    }

    private IncentiveReservation reservation() {
        return new IncentiveReservation(
                "courseflow",
                "lms",
                UUID.randomUUID(),
                1,
                null,
                "profile-1",
                "cart-1",
                "[]",
                "{}",
                "hash",
                "[]",
                Instant.now().plusSeconds(900));
    }
}
