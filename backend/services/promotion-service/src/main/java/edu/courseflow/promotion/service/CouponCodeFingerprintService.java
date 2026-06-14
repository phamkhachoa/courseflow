package edu.courseflow.promotion.service;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class CouponCodeFingerprintService {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String HMAC_PREFIX = "hmac-sha256:";

    private final String currentKeyId;
    private final String currentPepper;
    private final List<KeyMaterial> previousKeys;
    private final boolean legacyFallbackEnabled;

    public CouponCodeFingerprintService(
            @Value("${courseflow.promotion.coupon.fingerprint-key-id:local}")
            String currentKeyId,
            @Value("${courseflow.promotion.coupon.fingerprint-pepper:courseflow-local-coupon-fingerprint-pepper-change-me}")
            String currentPepper,
            @Value("${courseflow.promotion.coupon.previous-fingerprint-keys:}") String previousKeys,
            @Value("${courseflow.promotion.coupon.legacy-fallback-enabled:true}") boolean legacyFallbackEnabled) {
        this.currentKeyId = requireKeyId(currentKeyId);
        this.currentPepper = requirePepper(currentPepper);
        this.previousKeys = parsePreviousKeys(previousKeys);
        this.legacyFallbackEnabled = legacyFallbackEnabled;
    }

    public String primaryFingerprint(String normalizedCode) {
        return hmacFingerprint(normalizedCode, currentKeyId, currentPepper);
    }

    public String integrityHash(String purpose, String value) {
        String normalizedPurpose = purpose == null || purpose.isBlank() ? "coupon" : purpose.trim();
        String normalizedValue = value == null ? "" : value;
        return hmacFingerprint(normalizedPurpose + "\n" + normalizedValue, currentKeyId, currentPepper);
    }

    public String currentStoragePrefix() {
        return HMAC_PREFIX + currentKeyId + ":";
    }

    public boolean legacyFallbackEnabled() {
        return legacyFallbackEnabled;
    }

    public List<String> lookupFingerprints(String normalizedCode) {
        return lookupCandidates(normalizedCode).stream()
                .map(CouponLookupCandidate::fingerprint)
                .toList();
    }

    public List<CouponLookupCandidate> lookupCandidates(String normalizedCode) {
        if (normalizedCode == null || normalizedCode.isBlank()) {
            return List.of();
        }
        Set<CouponLookupCandidate> lookups = new LinkedHashSet<>();
        lookups.add(new CouponLookupCandidate(primaryFingerprint(normalizedCode), "current_hmac"));
        for (KeyMaterial previousKey : previousKeys) {
            lookups.add(new CouponLookupCandidate(
                    hmacFingerprint(normalizedCode, previousKey.keyId(), previousKey.pepper()),
                    "previous_hmac"));
        }
        if (legacyFallbackEnabled) {
            lookups.add(new CouponLookupCandidate(
                    CouponCodeNormalizer.legacySha256Fingerprint(normalizedCode),
                    "legacy_sha"));
            lookups.add(new CouponLookupCandidate(normalizedCode, "legacy_raw"));
        }
        return List.copyOf(lookups);
    }

    private String hmacFingerprint(String normalizedCode, String keyId, String pepper) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(pepper.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM));
            return HMAC_PREFIX + keyId + ":" + HexFormat.of().formatHex(
                    mac.doFinal(normalizedCode.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to fingerprint coupon code", ex);
        }
    }

    private String requireKeyId(String keyId) {
        if (keyId == null || keyId.isBlank()) {
            throw new IllegalStateException("Coupon fingerprint key id must not be blank");
        }
        String normalized = keyId.trim();
        if (!normalized.matches("[A-Za-z0-9._-]{1,40}")) {
            throw new IllegalStateException("Coupon fingerprint key id contains unsupported characters");
        }
        return normalized;
    }

    private String requirePepper(String pepper) {
        if (pepper == null || pepper.isBlank()) {
            throw new IllegalStateException("Coupon fingerprint pepper must not be blank");
        }
        return pepper.trim();
    }

    private List<KeyMaterial> parsePreviousKeys(String keys) {
        if (keys == null || keys.isBlank()) {
            return List.of();
        }
        List<KeyMaterial> parsed = new ArrayList<>();
        for (String entry : keys.split(",")) {
            String normalized = entry.trim();
            if (normalized.isBlank()) {
                continue;
            }
            String[] parts = normalized.split(":", 2);
            if (parts.length != 2) {
                throw new IllegalStateException(
                        "Previous coupon fingerprint keys must use keyId:secret entries");
            }
            String keyId = requireKeyId(parts[0]);
            String pepper = requirePepper(parts[1]);
            if (!keyId.equals(currentKeyId)) {
                parsed.add(new KeyMaterial(keyId, pepper));
            }
        }
        return List.copyOf(parsed);
    }

    private record KeyMaterial(String keyId, String pepper) {
    }

    public record CouponLookupCandidate(String fingerprint, String storagePath) {
    }
}
