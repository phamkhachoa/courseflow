package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class CouponCodeFingerprintServiceTest {

    @Test
    void primaryFingerprintUsesVersionedHmacAndDoesNotExposeRawCode() {
        CouponCodeFingerprintService fingerprints =
                new CouponCodeFingerprintService("current", "current-pepper", "", true);

        String fingerprint = fingerprints.primaryFingerprint("WELCOME10");

        assertThat(fingerprint)
                .startsWith("hmac-sha256:current:")
                .hasSize("hmac-sha256:current:".length() + 64)
                .doesNotContain("WELCOME10");
        assertThat(fingerprint)
                .isNotEqualTo(CouponCodeNormalizer.legacySha256Fingerprint("WELCOME10"));
    }

    @Test
    void lookupFingerprintsIncludeCurrentPreviousLegacyShaAndRawFallbacks() {
        CouponCodeFingerprintService fingerprints =
                new CouponCodeFingerprintService(
                        "current",
                        "current-pepper",
                        "previous:previous-pepper,current:ignored",
                        true);

        assertThat(fingerprints.lookupFingerprints("WELCOME10"))
                .containsExactly(
                        new CouponCodeFingerprintService("current", "current-pepper", "", true)
                                .primaryFingerprint("WELCOME10"),
                        new CouponCodeFingerprintService("previous", "previous-pepper", "", true)
                                .primaryFingerprint("WELCOME10"),
                        CouponCodeNormalizer.legacySha256Fingerprint("WELCOME10"),
                        "WELCOME10");
        assertThat(fingerprints.lookupCandidates("WELCOME10"))
                .extracting(CouponCodeFingerprintService.CouponLookupCandidate::storagePath)
                .containsExactly("current_hmac", "previous_hmac", "legacy_sha", "legacy_raw");
    }

    @Test
    void lookupCandidatesCanDisableLegacyFallbacksAfterMigration() {
        CouponCodeFingerprintService fingerprints =
                new CouponCodeFingerprintService("current", "current-pepper", "previous:previous-pepper", false);

        assertThat(fingerprints.lookupCandidates("WELCOME10"))
                .extracting(CouponCodeFingerprintService.CouponLookupCandidate::storagePath)
                .containsExactly("current_hmac", "previous_hmac");
    }
}
