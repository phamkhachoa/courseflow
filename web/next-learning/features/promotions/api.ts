import { clientFetch } from "@/shared/api/client";

export type LearnerCoupon = {
  couponId: string;
  campaignId: string;
  campaignCode: string;
  campaignName: string;
  codeMask: string;
  status: string;
  walletStatus: string;
  startsAt?: string | null;
  expiresAt?: string | null;
  redemptionId?: string | null;
  redeemedAt?: string | null;
  message?: string | null;
};

export type LearnerCouponWallet = {
  tenantId: string;
  applicationId: string;
  profileId: string;
  generatedAt: string;
  availableCount: number;
  expiringSoonCount: number;
  usedCount: number;
  expiredCount: number;
  items: LearnerCoupon[];
};

export async function getLearnerCouponWallet(): Promise<LearnerCouponWallet> {
  return clientFetch<LearnerCouponWallet>("/v1/enrollments/coupons");
}
