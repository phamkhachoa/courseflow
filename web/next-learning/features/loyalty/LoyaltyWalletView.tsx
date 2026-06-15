"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Coins,
  Gift,
  LifeBuoy,
  ListChecks,
  RefreshCw,
  Sparkles,
  Ticket,
  WalletCards
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import {
  getLearnerLoyaltyWallet,
  redeemLearnerLoyaltyReward,
  type LearnerLoyaltyReward,
  type LearnerLoyaltyWalletAccount,
  type LoyaltyLedgerEntry,
  type LoyaltyRewardRedemption
} from "@/features/loyalty/api";
import {
  getLearnerCouponWallet,
  type LearnerCoupon,
  type LearnerCouponWallet
} from "@/features/promotions/api";
import {
  buildLearnerIncentiveHub,
  type IncentiveEligibilityGap,
  type IncentivePendingBenefit,
  type IncentiveSupportItem,
  type IncentiveTimelineItem
} from "./incentive-hub";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  LinkButton,
  MetricCard,
  SectionHeader,
  cn
} from "@/shared/ui";

const reasonLabels: Record<string, string> = {
  PROGRAM_NOT_ACTIVE: "Chương trình chưa hoạt động",
  REWARD_NOT_ACTIVE: "Reward chưa mở",
  NO_LOYALTY_ACCOUNT: "Chưa có ví điểm",
  INSUFFICIENT_BALANCE: "Chưa đủ điểm",
  OUT_OF_STOCK: "Đã hết lượt",
  PROFILE_LIMIT_REACHED: "Đã đạt giới hạn đổi"
};

const entryLabels: Record<string, string> = {
  EARN: "Cộng điểm",
  BURN: "Đổi thưởng",
  REVERSE: "Hoàn điểm",
  ADJUST: "Điều chỉnh",
  EXPIRE: "Hết hạn"
};

const statusLabels: Record<string, string> = {
  ACTIVE: "Đang hoạt động",
  EXPIRED: "Đã hết hạn",
  COMMITTED: "Đã ghi nhận",
  REVERSED: "Đã hoàn",
  PENDING: "Đang chờ",
  ISSUED: "Đã cấp",
  MANUAL_REQUIRED: "Cần xử lý",
  FAILED: "Thất bại",
  AVAILABLE: "Dùng được",
  UPCOMING: "Sắp mở",
  VOID: "Đã hủy",
  UNAVAILABLE: "Chưa khả dụng",
  WARNING: "Cảnh báo"
};

const couponStatusLabels: Record<string, string> = {
  AVAILABLE: "Dùng được",
  UPCOMING: "Sắp mở",
  USED: "Đã dùng",
  EXPIRED: "Hết hạn",
  PAUSED: "Tạm dừng",
  VOID: "Đã hủy",
  UNAVAILABLE: "Chưa khả dụng"
};

function operationId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.max(0, Math.round(value)));
}

function signedPoints(value: number): string {
  const abs = formatNumber(Math.abs(value));
  return value > 0 ? `+${abs}` : value < 0 ? `-${abs}` : abs;
}

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(date);
}

function statusLabel(value?: string | null) {
  return statusLabels[value ?? ""] ?? value ?? "-";
}

function couponStatusLabel(value?: string | null) {
  return couponStatusLabels[value ?? ""] ?? value ?? "-";
}

function couponTone(status?: string | null): "neutral" | "brand" | "amber" | "sky" | "coral" {
  switch (status) {
    case "AVAILABLE":
      return "sky";
    case "UPCOMING":
      return "amber";
    case "USED":
      return "brand";
    case "EXPIRED":
    case "VOID":
      return "coral";
    default:
      return "neutral";
  }
}

function entryLabel(value?: string | null) {
  return entryLabels[value ?? ""] ?? value ?? "-";
}

function sourceLabel(value: string) {
  const labels: Record<string, string> = {
    COUPON: "Coupon",
    LOYALTY: "Điểm",
    REWARD: "Reward",
    WALLET: "Ví"
  };
  return labels[value] ?? value;
}

function sourceTone(value: string): "neutral" | "brand" | "amber" | "sky" | "coral" {
  switch (value) {
    case "COUPON":
      return "brand";
    case "REWARD":
      return "sky";
    case "WALLET":
      return "amber";
    case "LOYALTY":
      return "neutral";
    default:
      return "neutral";
  }
}

function rewardTitle(redemption: LoyaltyRewardRedemption) {
  const snapshot = redemption.rewardSnapshot ?? {};
  const name = snapshot.name;
  return typeof name === "string" && name.trim() ? name : redemption.rewardCode;
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <Card className="border-coral-100 bg-coral-50/70">
      <div className="flex gap-3">
        <AlertTriangle className="mt-1 size-5 shrink-0 text-coral-600" />
        <div>
          <p className="font-bold text-coral-700">Không tải được dữ liệu</p>
          <p className="mt-1 text-sm leading-6 text-coral-700/80">{message}</p>
        </div>
      </div>
    </Card>
  );
}

function WalletAccountCard({ account }: { account: LearnerLoyaltyWalletAccount }) {
  const balance = account.balance;
  const tier = balance.tierProgress;
  const activeBuckets = account.buckets.filter((bucket) => bucket.status === "ACTIVE");
  const expiredBuckets = account.buckets.filter((bucket) => bucket.status === "EXPIRED");
  const pointsToNext = tier?.pointsToNext ?? 0;
  const nextRequirement = tier?.nextTierPointsRequired ?? 0;
  const progressValue = nextRequirement > 0
    ? Math.max(0, Math.min(100, ((nextRequirement - pointsToNext) / nextRequirement) * 100))
    : 100;

  return (
    <Card className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">{balance.programId}</p>
          <h3 className="mt-1 text-2xl font-bold text-ink-900">
            {formatNumber(balance.activePoints)} {balance.pointUnit}
          </h3>
          <p className="mt-1 text-sm text-ink-500">
            Ledger {formatNumber(balance.ledgerBalance)} · {statusLabel(balance.accountStatus)}
          </p>
        </div>
        <Badge tone={balance.programStatus === "ACTIVE" ? "sky" : "amber"}>
          {statusLabel(balance.programStatus)}
        </Badge>
      </div>

      {tier && (
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-xs font-bold uppercase text-ink-500">Tier hiện tại</p>
              <p className="mt-1 text-lg font-bold text-ink-900">{tier.currentTierName}</p>
            </div>
            <Badge tone={tier.graceUntil ? "amber" : "sky"}>{tier.currentTierCode}</Badge>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-brand-600" style={{ width: `${progressValue}%` }} />
          </div>
          <div className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-ink-500">
            <span>{formatNumber(tier.qualificationPoints)} điểm trong window</span>
            {tier.nextTierCode ? (
              <span>{formatNumber(pointsToNext)} điểm tới {tier.nextTierCode}</span>
            ) : (
              <span>Top tier</span>
            )}
          </div>
          {tier.graceUntil && (
            <p className="mt-2 text-xs font-semibold text-amber-700">Grace đến {formatDate(tier.graceUntil)}</p>
          )}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-bold uppercase text-ink-500">Sắp hết hạn</p>
          <p className="mt-1 text-lg font-bold text-ink-900">{formatNumber(balance.expiringSoonPoints)}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-bold uppercase text-ink-500">Đã hết hạn</p>
          <p className="mt-1 text-lg font-bold text-ink-900">{formatNumber(balance.expiredPoints)}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-bold uppercase text-ink-500">Hạn gần nhất</p>
          <p className="mt-1 text-lg font-bold text-ink-900">{formatDate(balance.nextExpiryAt)}</p>
        </div>
      </div>

      {account.buckets.length > 0 ? (
        <div>
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="font-bold text-ink-900">Expiry buckets</p>
            <Badge tone="neutral">
              {activeBuckets.length} active · {expiredBuckets.length} expired
            </Badge>
          </div>
          <div className="grid gap-2">
            {account.buckets.slice(0, 8).map((bucket) => (
              <div key={bucket.entryId} className="grid gap-2 rounded-lg border border-slate-200 p-3 sm:grid-cols-[1fr_auto]">
                <div>
                  <p className="font-semibold text-ink-900">{formatNumber(bucket.remainingPoints)} điểm còn lại</p>
                  <p className="mt-1 text-xs text-ink-500">
                    {entryLabel(bucket.entryType)} · dùng {formatNumber(bucket.consumedPoints)} / {formatNumber(bucket.originalPoints)}
                  </p>
                </div>
                <div className="text-left sm:text-right">
                  <Badge tone={bucket.status === "ACTIVE" ? "sky" : "amber"}>{statusLabel(bucket.status)}</Badge>
                  <p className="mt-1 text-xs text-ink-500">Hạn {formatDate(bucket.expiresAt)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm leading-6 text-ink-500">
          Chưa có bucket expiry được materialize cho ví này.
        </div>
      )}
    </Card>
  );
}

function LedgerList({ entries }: { entries: LoyaltyLedgerEntry[] }) {
  if (entries.length === 0) {
    return (
      <EmptyState
        title="Chưa có giao dịch điểm"
        description="Khi bạn nhận điểm, đổi thưởng hoặc điểm hết hạn, lịch sử sẽ xuất hiện ở đây."
      />
    );
  }
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="divide-y divide-slate-100">
        {entries.slice(0, 20).map((entry) => (
          <div key={entry.id} className="grid gap-3 p-4 sm:grid-cols-[1fr_auto]">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={entry.pointsDelta >= 0 ? "sky" : "coral"}>{entryLabel(entry.entryType)}</Badge>
                <span className="text-sm font-semibold text-ink-900">{entry.reason || entry.sourceReference}</span>
              </div>
              <p className="mt-1 text-xs text-ink-500">
                {entry.programId} · {formatDateTime(entry.occurredAt)}
              </p>
            </div>
            <p className={cn("text-lg font-bold", entry.pointsDelta >= 0 ? "text-signal-600" : "text-coral-600")}>
              {signedPoints(entry.pointsDelta)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function RewardCard({
  reward,
  onRedeem,
  isPending
}: {
  reward: LearnerLoyaltyReward;
  onRedeem: (reward: LearnerLoyaltyReward) => void;
  isPending?: boolean;
}) {
  const reasons = reward.ineligibleReasons.map((reason) => reasonLabels[reason] ?? reason);
  const spendableBalance = reward.spendableBalance ?? reward.ledgerBalance;
  const missing = Math.max(0, reward.pointsCost - spendableBalance);

  return (
    <Card className="flex min-h-[260px] flex-col">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">{reward.rewardCode}</p>
          <h3 className="mt-1 text-lg font-bold leading-6 text-ink-900">{reward.name}</h3>
        </div>
        <span className={cn("grid size-10 shrink-0 place-items-center rounded-md", reward.eligible ? "bg-signal-50 text-signal-600" : "bg-accent-50 text-accent-600")}>
          <Gift className="size-5" />
        </span>
      </div>
      {reward.description && <p className="mt-3 line-clamp-3 text-sm leading-6 text-ink-500">{reward.description}</p>}
      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-bold uppercase text-ink-500">Cost</p>
          <p className="mt-1 font-bold text-ink-900">{formatNumber(reward.pointsCost)} {reward.pointUnit}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-bold uppercase text-ink-500">Khả dụng</p>
          <p className="mt-1 font-bold text-ink-900">{formatNumber(spendableBalance)}</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Badge tone={reward.eligible ? "sky" : "amber"}>{reward.eligible ? "Đủ điều kiện" : `Thiếu ${formatNumber(missing)}`}</Badge>
        {reward.inventoryRemaining !== undefined && reward.inventoryRemaining !== null && (
          <Badge tone="neutral">Còn {formatNumber(reward.inventoryRemaining)} lượt</Badge>
        )}
        {reward.perProfileRemaining !== undefined && reward.perProfileRemaining !== null && (
          <Badge tone="neutral">Bạn còn {reward.perProfileRemaining} lượt</Badge>
        )}
      </div>
      {!reward.eligible && reasons.length > 0 && (
        <p className="mt-3 text-sm leading-6 text-ink-500">{reasons.join(", ")}</p>
      )}
      <Button className="mt-auto w-full" disabled={!reward.eligible || isPending} onClick={() => onRedeem(reward)}>
        {isPending ? <RefreshCw className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
        Đổi reward
      </Button>
    </Card>
  );
}

function RedemptionList({ redemptions }: { redemptions: LoyaltyRewardRedemption[] }) {
  if (redemptions.length === 0) {
    return (
      <EmptyState
        title="Chưa có lịch sử đổi thưởng"
        description="Các reward đã đổi và trạng thái fulfillment sẽ xuất hiện tại đây."
      />
    );
  }
  return (
    <div className="grid gap-3">
      {redemptions.slice(0, 10).map((redemption) => (
        <Card key={redemption.id} className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={redemption.status === "REVERSED" ? "coral" : "sky"}>{statusLabel(redemption.status)}</Badge>
              <Badge tone="neutral">{statusLabel(redemption.fulfillmentStatus)}</Badge>
            </div>
            <h3 className="mt-2 font-bold text-ink-900">{rewardTitle(redemption)}</h3>
            <p className="mt-1 text-sm text-ink-500">{redemption.rewardCode} · {formatDateTime(redemption.redeemedAt)}</p>
          </div>
          <div className="text-left sm:text-right">
            <p className="text-lg font-bold text-coral-600">-{formatNumber(redemption.pointsCost)}</p>
            {redemption.reversedAt && <p className="mt-1 text-xs text-coral-600">Hoàn {formatDateTime(redemption.reversedAt)}</p>}
          </div>
        </Card>
      ))}
    </div>
  );
}

function CouponRow({ coupon }: { coupon: LearnerCoupon }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-bold text-ink-900">{coupon.codeMask || coupon.campaignCode}</p>
          <p className="mt-1 text-sm leading-5 text-ink-500">{coupon.campaignName}</p>
        </div>
        <Badge tone={couponTone(coupon.walletStatus)}>{couponStatusLabel(coupon.walletStatus)}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-500">
        <span>Bắt đầu {formatDate(coupon.startsAt)}</span>
        <span>Hết hạn {formatDate(coupon.expiresAt)}</span>
      </div>
      {coupon.message && <p className="mt-2 text-xs leading-5 text-ink-500">{coupon.message}</p>}
    </div>
  );
}

function CouponWalletPanel({
  wallet,
  isLoading,
  isError
}: {
  wallet?: LearnerCouponWallet;
  isLoading?: boolean;
  isError?: boolean;
}) {
  if (isLoading) {
    return (
      <Card className="grid min-h-36 place-items-center text-center">
        <RefreshCw className="size-7 animate-spin text-brand-600" />
        <p className="mt-3 text-sm font-bold text-ink-900">Đang tải ưu đãi</p>
      </Card>
    );
  }
  if (isError) {
    return (
      <Card className="border-accent-100 bg-accent-50/60">
        <p className="font-bold text-ink-900">Chưa tải được ưu đãi</p>
        <p className="mt-1 text-sm leading-6 text-ink-500">Ví điểm vẫn dùng được, bạn có thể thử lại sau.</p>
      </Card>
    );
  }
  if (!wallet || wallet.items.length === 0) {
    return (
      <EmptyState
        title="Chưa có coupon"
        description="Coupon được cấp riêng cho tài khoản sẽ xuất hiện tại đây."
      />
    );
  }
  return (
    <Card className="space-y-4">
      <div className="grid grid-cols-4 gap-2 text-center text-xs">
        <div className="rounded-md bg-signal-50 p-2 text-signal-700">
          <p className="font-bold">{wallet.availableCount}</p>
          <p>Dùng được</p>
        </div>
        <div className="rounded-md bg-accent-50 p-2 text-accent-700">
          <p className="font-bold">{wallet.expiringSoonCount}</p>
          <p>Sắp hết</p>
        </div>
        <div className="rounded-md bg-brand-50 p-2 text-brand-700">
          <p className="font-bold">{wallet.usedCount}</p>
          <p>Đã dùng</p>
        </div>
        <div className="rounded-md bg-coral-50 p-2 text-coral-700">
          <p className="font-bold">{wallet.expiredCount}</p>
          <p>Hết hạn</p>
        </div>
      </div>
      <div className="grid gap-3">
        {wallet.items.slice(0, 6).map((coupon) => (
          <CouponRow key={coupon.couponId} coupon={coupon} />
        ))}
      </div>
    </Card>
  );
}

function PendingBenefitsPanel({ items }: { items: IncentivePendingBenefit[] }) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Không có benefit pending"
        description="Reward, coupon hoặc benefit đang chờ xử lý sẽ xuất hiện tại đây."
      />
    );
  }
  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Pending</p>
          <h3 className="text-xl font-bold text-ink-900">Benefit đang chờ</h3>
        </div>
        <Clock3 className="size-6 text-accent-600" />
      </div>
      <div className="grid gap-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-bold text-ink-900">{item.title}</p>
                <p className="mt-1 text-sm leading-5 text-ink-500">{item.detail}</p>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <Badge tone={sourceTone(item.source)}>{sourceLabel(item.source)}</Badge>
                <Badge tone={item.status === "FAILED" ? "coral" : item.status === "MANUAL_REQUIRED" ? "amber" : "sky"}>
                  {statusLabel(item.status)}
                </Badge>
              </div>
            </div>
            <p className="mt-3 text-xs font-semibold text-ink-500">
              Ref {item.ref}{item.dueAt ? ` · SLA ${formatDateTime(item.dueAt)}` : ""}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function EligibilityGapPanel({ items }: { items: IncentiveEligibilityGap[] }) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Không có vướng mắc điều kiện"
        description="Bạn đang đủ điều kiện với các reward/coupon đang mở cho tài khoản."
      />
    );
  }
  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Eligibility</p>
          <h3 className="text-xl font-bold text-ink-900">Lý do chưa đủ điều kiện</h3>
        </div>
        <ListChecks className="size-6 text-brand-600" />
      </div>
      <div className="grid gap-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-bold text-ink-900">{item.title}</p>
                <p className="mt-1 text-sm leading-5 text-ink-500">{item.reasons.join(", ")}</p>
              </div>
              <Badge tone={sourceTone(item.source)}>{sourceLabel(item.source)}</Badge>
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
              {typeof item.missingPoints === "number" && item.missingPoints > 0 ? (
                <span className="font-semibold text-accent-700">Thiếu {formatNumber(item.missingPoints)} điểm</span>
              ) : (
                <span className="font-semibold text-ink-500">Cần kiểm tra điều kiện</span>
              )}
              <span className="font-bold text-brand-700">{item.actionLabel}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function SupportCasesPanel({ items }: { items: IncentiveSupportItem[] }) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Không có support case"
        description="Các reward/coupon cần support hoặc cảnh báo ví sẽ được ghim tại đây."
      />
    );
  }
  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Support</p>
          <h3 className="text-xl font-bold text-ink-900">Case cần theo dõi</h3>
        </div>
        <LifeBuoy className="size-6 text-coral-600" />
      </div>
      <div className="grid gap-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="font-bold text-ink-900">{item.title}</p>
                <p className="mt-1 text-sm leading-5 text-ink-500">{item.detail}</p>
              </div>
              <Badge tone={item.severity === "critical" ? "coral" : "amber"}>{statusLabel(item.status)}</Badge>
            </div>
            <p className="mt-3 text-xs font-semibold text-ink-500">
              Case ref {item.caseRef}{item.dueAt ? ` · SLA ${formatDateTime(item.dueAt)}` : ""}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ActivityTimelinePanel({ items }: { items: IncentiveTimelineItem[] }) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="Chưa có lịch sử ưu đãi"
        description="Coupon, điểm và reward gần đây sẽ được gom vào timeline này."
      />
    );
  }
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="divide-y divide-slate-100">
        {items.map((item) => (
          <div key={item.id} className="grid gap-3 p-4 sm:grid-cols-[1fr_auto]">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={sourceTone(item.source)}>{sourceLabel(item.source)}</Badge>
                <Badge tone={item.status === "FAILED" || item.status === "VOID" ? "coral" : "neutral"}>
                  {statusLabel(item.status) || item.status}
                </Badge>
              </div>
              <p className="mt-2 font-bold text-ink-900">{item.title}</p>
              <p className="mt-1 text-xs text-ink-500">
                {item.detail ? `${item.detail} · ` : ""}{formatDateTime(item.occurredAt)}
              </p>
            </div>
            {typeof item.pointsDelta === "number" && (
              <p className={cn("text-lg font-bold", item.pointsDelta >= 0 ? "text-signal-600" : "text-coral-600")}>
                {signedPoints(item.pointsDelta)}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function LoyaltyWalletView() {
  const { session } = useLearnerSession();
  const queryClient = useQueryClient();
  const [redeemError, setRedeemError] = useState<string | null>(null);

  const walletQuery = useQuery({
    queryKey: ["learner", "loyalty", "wallet"],
    queryFn: getLearnerLoyaltyWallet,
    enabled: Boolean(session),
    retry: 1
  });

  const couponWalletQuery = useQuery({
    queryKey: ["learner", "promotions", "coupons"],
    queryFn: getLearnerCouponWallet,
    enabled: Boolean(session),
    retry: 1
  });

  const redeemMutation = useMutation({
    mutationFn: (reward: LearnerLoyaltyReward) => {
      const id = operationId("learner-reward");
      return redeemLearnerLoyaltyReward(reward.id, {
        idempotencyKey: id,
        correlationId: id,
        note: `Redeem ${reward.rewardCode}`,
        metadata: { source: "web-learn", rewardCode: reward.rewardCode }
      });
    },
    onMutate: () => setRedeemError(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["learner", "loyalty", "wallet"] });
    },
    onError: (error) => {
      setRedeemError(error instanceof Error ? error.message : "Không đổi được reward");
    }
  });

  const wallet = walletQuery.data;
  const couponWallet = couponWalletQuery.data;
  const hub = useMemo(() => buildLearnerIncentiveHub(wallet, couponWallet), [wallet, couponWallet]);
  const hasWalletAccounts = Boolean(wallet?.accounts.length);
  const recentEntries = useMemo(
    () => wallet?.accounts.flatMap((account) => account.recentEntries).sort((a, b) => b.createdAt.localeCompare(a.createdAt)) ?? [],
    [wallet]
  );

  if (!session) {
    return (
      <EmptyState
        title="Đăng nhập để xem ưu đãi"
        description="Điểm, coupon, reward và benefit pending được gắn với tài khoản học tập của bạn."
        action={<LinkButton href="/login">Đăng nhập</LinkButton>}
      />
    );
  }

  if (walletQuery.isLoading && couponWalletQuery.isLoading) {
    return (
      <Card className="grid min-h-[360px] place-items-center text-center">
        <RefreshCw className="size-10 animate-spin text-brand-600" />
        <p className="mt-4 font-bold text-ink-900">Đang tải hub ưu đãi</p>
      </Card>
    );
  }

  if (walletQuery.isError && couponWalletQuery.isError) {
    return <ErrorPanel message={walletQuery.error instanceof Error ? walletQuery.error.message : "Không tải được hub ưu đãi"} />;
  }

  if (!hasWalletAccounts && !couponWalletQuery.isLoading && (!couponWallet || couponWallet.items.length === 0)) {
    return (
      <EmptyState
        title="Chưa có ưu đãi"
        description="Khi bạn nhận điểm, coupon, reward hoặc benefit pending, hub ưu đãi sẽ xuất hiện tại đây."
        action={<LinkButton href="/search" variant="secondary">Tìm khóa học</LinkButton>}
      />
    );
  }

  return (
    <div className="space-y-7">
      {walletQuery.isError && (
        <Card className="border-accent-100 bg-accent-50/50">
          <div className="flex gap-3">
            <AlertTriangle className="mt-1 size-5 shrink-0 text-accent-600" />
            <div>
              <p className="font-bold text-ink-900">Chưa tải được ví điểm</p>
              <p className="mt-1 text-sm leading-6 text-ink-500">
                {walletQuery.error instanceof Error ? walletQuery.error.message : "Bạn vẫn có thể xem coupon nếu dữ liệu coupon đã tải được."}
              </p>
            </div>
          </div>
        </Card>
      )}

      {(wallet?.warnings.length ?? 0) > 0 && (
        <Card className="border-accent-100 bg-accent-50/50">
          <div className="flex gap-3">
            <AlertTriangle className="mt-1 size-5 shrink-0 text-accent-600" />
            <div>
              <p className="font-bold text-ink-900">Ví có cảnh báo</p>
              <p className="mt-1 text-sm leading-6 text-ink-500">{wallet?.warnings.join(", ")}</p>
            </div>
          </div>
        </Card>
      )}

      {redeemError && <ErrorPanel message={redeemError} />}

      <section className="grid gap-3 md:grid-cols-4">
        <MetricCard
          label="Điểm khả dụng"
          value={formatNumber(hub.summary.activePoints)}
          tone="brand"
          stateLabel={`${wallet?.totals.activeAccountCount ?? 0} ví active`}
          icon={<Coins className="size-5" />}
        />
        <MetricCard
          label="Coupon dùng được"
          value={formatNumber(hub.summary.availableCoupons)}
          tone="amber"
          stateLabel={`${hub.summary.expiringSoonCoupons} sắp hết hạn`}
          icon={<Ticket className="size-5" />}
        />
        <MetricCard
          label="Reward khả dụng"
          value={String(hub.summary.eligibleRewards)}
          tone="sky"
          stateLabel={`${hub.summary.ineligibleRewards} chưa đủ điều kiện`}
          icon={<Gift className="size-5" />}
        />
        <MetricCard
          label="Benefit pending"
          value={String(hub.summary.pendingBenefits)}
          tone="coral"
          stateLabel={`${hub.summary.supportRefs} support refs`}
          icon={<Clock3 className="size-5" />}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <PendingBenefitsPanel items={hub.pendingBenefits} />
        <EligibilityGapPanel items={hub.eligibilityGaps} />
        <SupportCasesPanel items={hub.supportItems} />
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <SectionHeader
            eyebrow="Ví điểm"
            title="Balance và expiry"
            description="Điểm khả dụng, bucket hết hạn và giao dịch gần đây theo từng chương trình."
          />
          {hasWalletAccounts && wallet ? (
            <div className="grid gap-4">
              {wallet.accounts.map((account) => (
                <WalletAccountCard key={account.balance.accountId} account={account} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="Chưa có ví điểm"
              description="Điểm sẽ xuất hiện sau khi bạn hoàn tất hoạt động đủ điều kiện hoặc promotion earn được commit."
              action={<LinkButton href="/search" variant="secondary">Tìm khóa học tích điểm</LinkButton>}
            />
          )}

          <SectionHeader eyebrow="Ledger" title="Giao dịch gần đây" />
          <LedgerList entries={recentEntries} />

          <SectionHeader eyebrow="Timeline" title="Lịch sử ưu đãi" />
          <ActivityTimelinePanel items={hub.activity} />
        </div>

        <aside className="space-y-6">
          <Card className="bg-ink-900 text-white">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-signal-200">Incentive health</p>
                <h3 className="mt-2 text-2xl font-bold">
                  {formatNumber(wallet?.totals.ledgerBalance ?? 0)} ledger points
                </h3>
              </div>
              <WalletCards className="size-8 text-signal-200" />
            </div>
            <p className="mt-3 text-sm leading-6 text-white/70">
              {wallet && wallet.totals.expiredPoints > 0
                ? `${formatNumber(wallet.totals.expiredPoints)} điểm đã hết hạn trong ví.`
                : hub.summary.pendingBenefits > 0
                  ? `${hub.summary.pendingBenefits} benefit đang chờ hoàn tất.`
                  : "Không có benefit pending đang chờ xử lý."}
            </p>
            <Button asChild variant="inverse" className="mt-5 w-full">
              <Link href="/search">
                Tìm khóa học tích điểm
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </Card>

          <SectionHeader eyebrow="Coupons" title="Ưu đãi của tôi" />
          <CouponWalletPanel
            wallet={couponWalletQuery.data}
            isLoading={couponWalletQuery.isLoading}
            isError={couponWalletQuery.isError}
          />

          <SectionHeader eyebrow="Rewards" title="Đổi thưởng" />
          {wallet && wallet.availableRewards.length > 0 ? (
            <div className="grid gap-4">
              {wallet.availableRewards.map((reward) => (
                <RewardCard
                  key={reward.id}
                  reward={reward}
                  onRedeem={(item) => redeemMutation.mutate(item)}
                  isPending={redeemMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              title="Chưa có reward khả dụng"
              description="Reward active trong các chương trình điểm của bạn sẽ xuất hiện tại đây."
            />
          )}
        </aside>
      </section>

      <section>
        <SectionHeader eyebrow="Redemptions" title="Lịch sử đổi thưởng" className="mb-4" />
        <RedemptionList redemptions={wallet?.recentRedemptions ?? []} />
      </section>

      {redeemMutation.isSuccess && (
        <Card className="border-signal-100 bg-signal-50/60">
          <div className="flex gap-3">
            <CheckCircle2 className="mt-1 size-5 shrink-0 text-signal-600" />
            <p className="text-sm font-semibold leading-6 text-signal-700">Reward đã được ghi nhận và ví điểm đang cập nhật.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
