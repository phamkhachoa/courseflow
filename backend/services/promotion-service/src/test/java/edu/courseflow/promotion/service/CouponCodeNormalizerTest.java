package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class CouponCodeNormalizerTest {

    @Test
    void normalizesCaseAndWhitespace() {
        assertThat(CouponCodeNormalizer.normalize("  welcome10  ")).isEqualTo("WELCOME10");
    }

    @Test
    void masksWithoutLeakingFullCode() {
        assertThat(CouponCodeNormalizer.mask("WELCOME10")).isEqualTo("WE****10");
    }

    @Test
    void legacySha256FingerprintDoesNotRetainRawValue() {
        assertThat(CouponCodeNormalizer.legacySha256Fingerprint("WELCOME10"))
                .hasSize(64)
                .doesNotContain("WELCOME10");
    }
}
