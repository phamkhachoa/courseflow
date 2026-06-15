import { describe, expect, it } from "vitest";
import { buildLearnerIncentiveHub } from "./incentive-hub";
import type { LearnerLoyaltyWalletResponse } from "./api";
import type { LearnerCouponWallet } from "@/features/promotions/api";

const wallet: LearnerLoyaltyWalletResponse = {
  profileId: "learner-1",
  generatedAt: "2026-06-15T02:00:00Z",
  totals: {
    ledgerBalance: 320,
    activePoints: 300,
    expiredPoints: 0,
    expiringSoonPoints: 40,
    accountCount: 1,
    activeAccountCount: 1,
    nextExpiryAt: "2026-07-01T00:00:00Z"
  },
  accounts: [
    {
      balance: {
        accountId: "account-1",
        tenantId: "tenant-1",
        applicationId: "learn",
        programId: "main",
        pointUnit: "POINT",
        accountStatus: "ACTIVE",
        programStatus: "ACTIVE",
        ledgerBalance: 320,
        activePoints: 300,
        expiredPoints: 0,
        expiringSoonPoints: 40,
        nextExpiryAt: "2026-07-01T00:00:00Z",
        warnings: []
      },
      buckets: [],
      recentEntries: [
        {
          id: "entry-1",
          accountId: "account-1",
          tenantId: "tenant-1",
          applicationId: "learn",
          programId: "main",
          profileId: "learner-1",
          entryType: "EARN",
          pointsDelta: 120,
          sourceReference: "course:course-1",
          reason: "Course completed",
          correlationId: "corr-1",
          occurredAt: "2026-06-14T10:00:00Z",
          createdAt: "2026-06-14T10:00:00Z"
        }
      ]
    }
  ],
  availableRewards: [
    {
      id: "reward-1",
      tenantId: "tenant-1",
      applicationId: "learn",
      programId: "main",
      rewardCode: "COACH",
      name: "Mentor session",
      pointsCost: 500,
      pointUnit: "POINT",
      ledgerBalance: 320,
      spendableBalance: 300,
      eligible: false,
      ineligibleReasons: ["INSUFFICIENT_BALANCE"],
      fulfillmentType: "MANUAL"
    },
    {
      id: "reward-2",
      tenantId: "tenant-1",
      applicationId: "learn",
      programId: "main",
      rewardCode: "BADGE",
      name: "Skill badge",
      pointsCost: 100,
      pointUnit: "POINT",
      ledgerBalance: 320,
      spendableBalance: 300,
      eligible: true,
      ineligibleReasons: [],
      fulfillmentType: "AUTO_ISSUE"
    }
  ],
  recentRedemptions: [
    {
      id: "redemption-1",
      rewardId: "reward-2",
      accountId: "account-1",
      burnEntryId: "burn-1",
      tenantId: "tenant-1",
      applicationId: "learn",
      programId: "main",
      profileId: "learner-1",
      rewardCode: "BADGE",
      pointsCost: 100,
      sourceReference: "reward:BADGE",
      status: "COMMITTED",
      fulfillmentStatus: "MANUAL_REQUIRED",
      fulfillmentNote: "Provider needs manual approval",
      fulfillmentSlaDueAt: "2026-06-16T00:00:00Z",
      rewardSnapshot: { name: "Skill badge" },
      redeemedAt: "2026-06-15T01:00:00Z",
      idempotencyReplay: false
    }
  ],
  warnings: ["Ledger balance differs from active lots"]
};

const couponWallet: LearnerCouponWallet = {
  tenantId: "tenant-1",
  applicationId: "learn",
  profileId: "learner-1",
  generatedAt: "2026-06-15T02:00:00Z",
  availableCount: 1,
  expiringSoonCount: 1,
  usedCount: 0,
  expiredCount: 0,
  items: [
    {
      couponId: "coupon-1",
      campaignId: "campaign-1",
      campaignCode: "WELCOME",
      campaignName: "Welcome coupon",
      codeMask: "WEL***",
      status: "ACTIVE",
      walletStatus: "UPCOMING",
      startsAt: "2026-06-20T00:00:00Z"
    },
    {
      couponId: "coupon-2",
      campaignId: "campaign-2",
      campaignCode: "OPS",
      campaignName: "Ops coupon",
      codeMask: "OPS***",
      status: "VOID",
      walletStatus: "VOID",
      message: "Coupon was revoked"
    }
  ]
};

describe("buildLearnerIncentiveHub", () => {
  it("derives learner pending benefits, eligibility gaps, support refs and activity", () => {
    const hub = buildLearnerIncentiveHub(wallet, couponWallet);

    expect(hub.summary.activePoints).toBe(300);
    expect(hub.summary.availableCoupons).toBe(1);
    expect(hub.summary.eligibleRewards).toBe(1);
    expect(hub.summary.ineligibleRewards).toBe(1);
    expect(hub.summary.pendingBenefits).toBe(2);
    expect(hub.summary.supportRefs).toBe(3);

    expect(hub.pendingBenefits.map((item) => item.ref)).toEqual([
      "coupon:coupon-1",
      "reward-redemption:redemption-1"
    ]);
    expect(hub.eligibilityGaps).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "reward-gap:reward-1",
          missingPoints: 200,
          reasons: ["Chưa đủ điểm"]
        }),
        expect.objectContaining({
          id: "coupon-gap:coupon-2",
          reasons: ["Coupon was revoked"]
        })
      ])
    );
    expect(hub.supportItems).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          caseRef: "reward-redemption:redemption-1",
          severity: "warning"
        }),
        expect.objectContaining({
          caseRef: "coupon:coupon-2",
          severity: "critical"
        })
      ])
    );
    expect(hub.activity.map((item) => item.id)).toEqual(
      expect.arrayContaining(["ledger:entry-1", "redemption:redemption-1", "coupon:coupon-1"])
    );
  });
});
