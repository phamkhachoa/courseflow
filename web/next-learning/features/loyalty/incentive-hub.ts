import type {
  LearnerLoyaltyReward,
  LearnerLoyaltyWalletResponse,
  LoyaltyLedgerEntry,
  LoyaltyRewardRedemption
} from "@/features/loyalty/api";
import type {
  LearnerCoupon,
  LearnerCouponWallet
} from "@/features/promotions/api";

export type IncentiveHubSource = "COUPON" | "LOYALTY" | "REWARD" | "WALLET";

export type IncentiveHubSummary = {
  availableCoupons: number;
  expiringSoonCoupons: number;
  eligibleRewards: number;
  ineligibleRewards: number;
  pendingBenefits: number;
  supportRefs: number;
  activePoints: number;
};

export type IncentivePendingBenefit = {
  id: string;
  source: IncentiveHubSource;
  title: string;
  status: string;
  detail: string;
  dueAt?: string | null;
  ref: string;
};

export type IncentiveEligibilityGap = {
  id: string;
  source: IncentiveHubSource;
  title: string;
  reasons: string[];
  missingPoints?: number;
  actionLabel: string;
};

export type IncentiveSupportItem = {
  id: string;
  source: IncentiveHubSource;
  title: string;
  status: string;
  severity: "warning" | "critical";
  caseRef: string;
  detail: string;
  createdAt?: string | null;
  dueAt?: string | null;
};

export type IncentiveTimelineItem = {
  id: string;
  source: IncentiveHubSource;
  title: string;
  status: string;
  occurredAt?: string | null;
  pointsDelta?: number;
  detail?: string;
};

export type LearnerIncentiveHub = {
  summary: IncentiveHubSummary;
  pendingBenefits: IncentivePendingBenefit[];
  eligibilityGaps: IncentiveEligibilityGap[];
  supportItems: IncentiveSupportItem[];
  activity: IncentiveTimelineItem[];
};

const pendingFulfillmentStatuses = new Set(["PENDING", "FAILED", "MANUAL_REQUIRED"]);
const supportFulfillmentStatuses = new Set(["FAILED", "MANUAL_REQUIRED"]);

const reasonLabels: Record<string, string> = {
  PROGRAM_NOT_ACTIVE: "Chương trình chưa hoạt động",
  REWARD_NOT_ACTIVE: "Reward chưa mở",
  NO_LOYALTY_ACCOUNT: "Chưa có ví điểm",
  INSUFFICIENT_BALANCE: "Chưa đủ điểm",
  OUT_OF_STOCK: "Đã hết lượt",
  PROFILE_LIMIT_REACHED: "Đã đạt giới hạn đổi"
};

function sortByTimeDesc<T extends { occurredAt?: string | null; createdAt?: string | null; dueAt?: string | null }>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const left = new Date(a.occurredAt ?? a.createdAt ?? a.dueAt ?? 0).getTime();
    const right = new Date(b.occurredAt ?? b.createdAt ?? b.dueAt ?? 0).getTime();
    return right - left;
  });
}

function rewardDisplayName(redemption: LoyaltyRewardRedemption): string {
  const snapshotName = redemption.rewardSnapshot?.name;
  return typeof snapshotName === "string" && snapshotName.trim()
    ? snapshotName
    : redemption.rewardCode;
}

function rewardMissingPoints(reward: LearnerLoyaltyReward): number {
  const spendableBalance = reward.spendableBalance ?? reward.ledgerBalance;
  return Math.max(0, reward.pointsCost - spendableBalance);
}

function rewardGap(reward: LearnerLoyaltyReward): IncentiveEligibilityGap {
  return {
    id: `reward-gap:${reward.id}`,
    source: "REWARD",
    title: reward.name,
    reasons: reward.ineligibleReasons.map((reason) => reasonLabels[reason] ?? reason),
    missingPoints: rewardMissingPoints(reward),
    actionLabel: reward.ineligibleReasons.includes("INSUFFICIENT_BALANCE")
      ? "Tích thêm điểm"
      : "Theo dõi điều kiện"
  };
}

function couponGap(coupon: LearnerCoupon): IncentiveEligibilityGap | null {
  if (!["PAUSED", "VOID", "UNAVAILABLE", "EXPIRED"].includes(coupon.walletStatus)) return null;
  return {
    id: `coupon-gap:${coupon.couponId}`,
    source: "COUPON",
    title: coupon.campaignName,
    reasons: [coupon.message || `Coupon ${coupon.walletStatus}`],
    actionLabel: coupon.walletStatus === "EXPIRED" ? "Tìm ưu đãi khác" : "Liên hệ support"
  };
}

function redemptionPending(redemption: LoyaltyRewardRedemption): IncentivePendingBenefit | null {
  if (redemption.status === "REVERSED" || !pendingFulfillmentStatuses.has(redemption.fulfillmentStatus)) {
    return null;
  }
  return {
    id: `reward-pending:${redemption.id}`,
    source: "REWARD",
    title: rewardDisplayName(redemption),
    status: redemption.fulfillmentStatus,
    detail: redemption.fulfillmentNote || redemption.fulfillmentErrorMessage || `${redemption.pointsCost} điểm đã được ghi nhận cho redemption này.`,
    dueAt: redemption.fulfillmentSlaDueAt ?? redemption.fulfillmentNextAttemptAt,
    ref: `reward-redemption:${redemption.id}`
  };
}

function couponPending(coupon: LearnerCoupon): IncentivePendingBenefit | null {
  if (coupon.walletStatus !== "UPCOMING") return null;
  return {
    id: `coupon-pending:${coupon.couponId}`,
    source: "COUPON",
    title: coupon.campaignName,
    status: coupon.walletStatus,
    detail: coupon.message || "Coupon đã được cấp và sẽ khả dụng khi tới thời gian bắt đầu.",
    dueAt: coupon.startsAt,
    ref: `coupon:${coupon.couponId}`
  };
}

function redemptionSupport(redemption: LoyaltyRewardRedemption): IncentiveSupportItem | null {
  if (!supportFulfillmentStatuses.has(redemption.fulfillmentStatus)) return null;
  return {
    id: `reward-support:${redemption.id}`,
    source: "REWARD",
    title: rewardDisplayName(redemption),
    status: redemption.fulfillmentStatus,
    severity: redemption.fulfillmentStatus === "FAILED" ? "critical" : "warning",
    caseRef: `reward-redemption:${redemption.id}`,
    detail: redemption.fulfillmentErrorMessage || redemption.fulfillmentNote || "Reward đang cần support kiểm tra fulfillment.",
    createdAt: redemption.redeemedAt,
    dueAt: redemption.fulfillmentSlaDueAt
  };
}

function couponSupport(coupon: LearnerCoupon): IncentiveSupportItem | null {
  if (!["VOID", "UNAVAILABLE"].includes(coupon.walletStatus)) return null;
  return {
    id: `coupon-support:${coupon.couponId}`,
    source: "COUPON",
    title: coupon.campaignName,
    status: coupon.walletStatus,
    severity: coupon.walletStatus === "VOID" ? "critical" : "warning",
    caseRef: `coupon:${coupon.couponId}`,
    detail: coupon.message || "Coupon không khả dụng và có thể cần support đối chiếu.",
    createdAt: coupon.redeemedAt,
    dueAt: coupon.expiresAt
  };
}

function walletWarningSupport(warning: string, index: number, generatedAt?: string): IncentiveSupportItem {
  return {
    id: `wallet-warning:${index}`,
    source: "WALLET",
    title: "Cảnh báo ví điểm",
    status: "WARNING",
    severity: "warning",
    caseRef: `wallet-warning:${index + 1}`,
    detail: warning,
    createdAt: generatedAt
  };
}

function ledgerActivity(entry: LoyaltyLedgerEntry): IncentiveTimelineItem {
  return {
    id: `ledger:${entry.id}`,
    source: "LOYALTY",
    title: entry.reason || entry.sourceReference,
    status: entry.entryType,
    occurredAt: entry.occurredAt || entry.createdAt,
    pointsDelta: entry.pointsDelta,
    detail: entry.programId
  };
}

function redemptionActivity(redemption: LoyaltyRewardRedemption): IncentiveTimelineItem {
  return {
    id: `redemption:${redemption.id}`,
    source: "REWARD",
    title: rewardDisplayName(redemption),
    status: redemption.fulfillmentStatus || redemption.status,
    occurredAt: redemption.redeemedAt,
    pointsDelta: -Math.abs(redemption.pointsCost),
    detail: redemption.rewardCode
  };
}

function couponActivity(coupon: LearnerCoupon): IncentiveTimelineItem {
  return {
    id: `coupon:${coupon.couponId}`,
    source: "COUPON",
    title: coupon.campaignName,
    status: coupon.walletStatus,
    occurredAt: coupon.redeemedAt ?? coupon.startsAt ?? coupon.expiresAt,
    detail: coupon.codeMask || coupon.campaignCode
  };
}

export function buildLearnerIncentiveHub(
  wallet?: LearnerLoyaltyWalletResponse,
  couponWallet?: LearnerCouponWallet
): LearnerIncentiveHub {
  const rewards = wallet?.availableRewards ?? [];
  const redemptions = wallet?.recentRedemptions ?? [];
  const coupons = couponWallet?.items ?? [];
  const ledgerEntries = wallet?.accounts.flatMap((account) => account.recentEntries) ?? [];

  const pendingBenefits = sortByTimeDesc([
    ...redemptions.map(redemptionPending).filter(Boolean),
    ...coupons.map(couponPending).filter(Boolean)
  ] as IncentivePendingBenefit[]).slice(0, 8);

  const eligibilityGaps = [
    ...rewards.filter((reward) => !reward.eligible).map(rewardGap),
    ...coupons.map(couponGap).filter(Boolean),
    ...(wallet?.warnings ?? []).map((warning, index) => ({
      id: `wallet-gap:${index}`,
      source: "WALLET" as const,
      title: "Cảnh báo ví điểm",
      reasons: [warning],
      actionLabel: "Liên hệ support"
    }))
  ].filter(Boolean) as IncentiveEligibilityGap[];

  const supportItems = sortByTimeDesc([
    ...redemptions.map(redemptionSupport).filter(Boolean),
    ...coupons.map(couponSupport).filter(Boolean),
    ...(wallet?.warnings ?? []).map((warning, index) => walletWarningSupport(warning, index, wallet?.generatedAt))
  ] as IncentiveSupportItem[]).slice(0, 8);

  const activity = sortByTimeDesc([
    ...ledgerEntries.map(ledgerActivity),
    ...redemptions.map(redemptionActivity),
    ...coupons.map(couponActivity)
  ]).slice(0, 12);

  return {
    summary: {
      availableCoupons: couponWallet?.availableCount ?? coupons.filter((coupon) => coupon.walletStatus === "AVAILABLE").length,
      expiringSoonCoupons: couponWallet?.expiringSoonCount ?? 0,
      eligibleRewards: rewards.filter((reward) => reward.eligible).length,
      ineligibleRewards: rewards.filter((reward) => !reward.eligible).length,
      pendingBenefits: pendingBenefits.length,
      supportRefs: supportItems.length,
      activePoints: wallet?.totals.activePoints ?? 0
    },
    pendingBenefits,
    eligibilityGaps: eligibilityGaps.slice(0, 8),
    supportItems,
    activity
  };
}
