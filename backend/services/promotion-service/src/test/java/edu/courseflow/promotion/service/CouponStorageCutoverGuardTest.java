package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CouponStorageCutoverGuardTest {

    @Mock
    IncentiveCouponRepository coupons;

    @Test
    void fallbackEnabledDoesNotBlockWritesOrQueryInventory() {
        CouponStorageCutoverGuard guard = new CouponStorageCutoverGuard(coupons, fingerprints(true));

        guard.requireCouponWriteAllowed("courseflow", "lms", UUID.randomUUID());

        verify(coupons, never()).countByStorageFormat(
                eq("courseflow"),
                eq("lms"),
                org.mockito.ArgumentMatchers.any(),
                eq(true),
                eq(fingerprints(true).currentStoragePrefix()));
    }

    @Test
    void fallbackDisabledBlocksWritesWhenLegacyOrMalformedActiveInventoryRemains() {
        UUID campaignId = UUID.randomUUID();
        CouponCodeFingerprintService fingerprints = fingerprints(false);
        CouponStorageCutoverGuard guard = new CouponStorageCutoverGuard(coupons, fingerprints);
        when(coupons.countByStorageFormat("courseflow", "lms", campaignId, true,
                fingerprints.currentStoragePrefix()))
                .thenReturn(List.of(
                        storageCount("current_hmac", 4),
                        storageCount("legacy_sha", 1),
                        storageCount("malformed", 1)));

        assertThatThrownBy(() -> guard.requireCouponWriteAllowed("courseflow", "lms", campaignId))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("Coupon storage cutover is not ready");
    }

    @Test
    void fallbackDisabledAllowsWritesWhenOnlyCurrentOrPreviousHmacRemain() {
        UUID campaignId = UUID.randomUUID();
        CouponCodeFingerprintService fingerprints = fingerprints(false);
        CouponStorageCutoverGuard guard = new CouponStorageCutoverGuard(coupons, fingerprints);
        when(coupons.countByStorageFormat("courseflow", "lms", campaignId, true,
                fingerprints.currentStoragePrefix()))
                .thenReturn(List.of(
                        storageCount("current_hmac", 4),
                        storageCount("previous_hmac", 2)));

        guard.requireCouponWriteAllowed("courseflow", "lms", campaignId);
    }

    private static CouponCodeFingerprintService fingerprints(boolean legacyFallbackEnabled) {
        return new CouponCodeFingerprintService("test", "test-coupon-pepper", "", legacyFallbackEnabled);
    }

    private static IncentiveCouponRepository.CouponStorageFormatCount storageCount(String storageFormat, long count) {
        return new IncentiveCouponRepository.CouponStorageFormatCount() {
            @Override
            public String getStorageFormat() {
                return storageFormat;
            }

            @Override
            public long getCouponCount() {
                return count;
            }
        };
    }
}
