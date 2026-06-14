package edu.courseflow.promotion.service;

import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.promotion.repository.IncentiveCouponRepository;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class CouponStorageCutoverGuard {

    private final IncentiveCouponRepository coupons;
    private final CouponCodeFingerprintService couponFingerprints;

    public CouponStorageCutoverGuard(IncentiveCouponRepository coupons,
                                     CouponCodeFingerprintService couponFingerprints) {
        this.coupons = coupons;
        this.couponFingerprints = couponFingerprints;
    }

    public void requireCouponWriteAllowed(String tenantId, String applicationId, UUID campaignId) {
        if (couponFingerprints.legacyFallbackEnabled()) {
            return;
        }
        StorageDebt debt = storageDebt(tenantId, applicationId, campaignId);
        if (debt.legacyCoupons() > 0 || debt.malformedCoupons() > 0) {
            throw new ConflictException(
                    "Coupon storage cutover is not ready; active legacy or malformed coupon inventory remains");
        }
    }

    private StorageDebt storageDebt(String tenantId, String applicationId, UUID campaignId) {
        long legacy = 0;
        long malformed = 0;
        for (IncentiveCouponRepository.CouponStorageFormatCount row : coupons.countByStorageFormat(
                tenantId,
                applicationId,
                campaignId,
                true,
                couponFingerprints.currentStoragePrefix())) {
            if ("legacy_sha".equals(row.getStorageFormat()) || "legacy_raw".equals(row.getStorageFormat())) {
                legacy += row.getCouponCount();
            } else if ("malformed".equals(row.getStorageFormat())) {
                malformed += row.getCouponCount();
            }
        }
        return new StorageDebt(legacy, malformed);
    }

    private record StorageDebt(long legacyCoupons, long malformedCoupons) {
    }
}
