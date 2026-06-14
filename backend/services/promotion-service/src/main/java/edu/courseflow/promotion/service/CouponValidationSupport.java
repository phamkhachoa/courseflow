package edu.courseflow.promotion.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import java.time.Instant;

final class CouponValidationSupport {

    private CouponValidationSupport() {
    }

    static void validateWindowAndLimits(Instant startsAt, Instant expiresAt,
                                        Integer maxRedemptions,
                                        Integer maxRedemptionsPerProfile) {
        if (startsAt != null && expiresAt != null && !startsAt.isBefore(expiresAt)) {
            throw new BadRequestException("Coupon startsAt must be before expiresAt");
        }
        if (maxRedemptions != null && maxRedemptions < 0) {
            throw new BadRequestException("Coupon maxRedemptions must not be negative");
        }
        if (maxRedemptionsPerProfile != null && maxRedemptionsPerProfile < 0) {
            throw new BadRequestException("Coupon maxRedemptionsPerProfile must not be negative");
        }
    }

    static String normalizeStatusOrThrow(String status) {
        String normalized = blankToNull(status);
        if (normalized == null) {
            throw new BadRequestException("Coupon status is required");
        }
        normalized = normalized.toUpperCase();
        if ("ACTIVE".equals(normalized) || "PAUSED".equals(normalized)
                || "EXPIRED".equals(normalized) || "VOID".equals(normalized)) {
            return normalized;
        }
        throw new BadRequestException("Unsupported incentive coupon status: " + status);
    }

    static String normalizeStatusOrNull(String status) {
        String normalized = blankToNull(status);
        return normalized == null ? null : normalizeStatusOrThrow(normalized);
    }

    private static String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
