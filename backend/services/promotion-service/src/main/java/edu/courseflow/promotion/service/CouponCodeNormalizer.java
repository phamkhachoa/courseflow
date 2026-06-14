package edu.courseflow.promotion.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.text.Normalizer;
import java.util.HexFormat;
import java.util.Locale;

final class CouponCodeNormalizer {

    private CouponCodeNormalizer() {
    }

    static String normalize(String code) {
        if (code == null) {
            return "";
        }
        return Normalizer.normalize(code.trim(), Normalizer.Form.NFKC)
                .toUpperCase(Locale.ROOT);
    }

    static String mask(String normalizedCode) {
        if (normalizedCode == null || normalizedCode.isBlank()) {
            return "";
        }
        if (normalizedCode.length() <= 4) {
            return "****";
        }
        int suffixStart = Math.max(2, normalizedCode.length() - 2);
        return normalizedCode.substring(0, 2) + "****" + normalizedCode.substring(suffixStart);
    }

    static String legacySha256Fingerprint(String normalizedCode) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(normalizedCode.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }
}
