import { clientFetch } from "@/shared/api/client";

export type LearnerLoyaltyBalance = {
  accountId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  pointUnit: string;
  accountStatus: string;
  programStatus: string;
  ledgerBalance: number;
  activePoints: number;
  expiredPoints: number;
  expiringSoonPoints: number;
  nextExpiryAt?: string | null;
  tierProgress?: LoyaltyTierProgress | null;
  warnings: string[];
};

export type LoyaltyTierProgress = {
  stateId?: string | null;
  accountId: string;
  currentTierPolicyId?: string | null;
  currentTierCode: string;
  currentTierName: string;
  currentTierRank: number;
  qualificationPoints: number;
  qualificationWindowDays?: number | null;
  qualificationWindowStartedAt?: string | null;
  qualificationWindowEndsAt?: string | null;
  currentPeriodStartedAt?: string | null;
  qualifiedAt?: string | null;
  graceUntil?: string | null;
  nextTierPolicyId?: string | null;
  nextTierCode?: string | null;
  nextTierName?: string | null;
  nextTierRank?: number | null;
  nextTierPointsRequired?: number | null;
  pointsToNext?: number | null;
  evaluatedAt?: string | null;
};

export type LearnerLoyaltyBalanceResponse = {
  profileId: string;
  generatedAt: string;
  items: LearnerLoyaltyBalance[];
};

export type LoyaltyBalanceBucket = {
  entryId: string;
  accountId: string;
  profileId: string;
  entryType: string;
  originalPoints: number;
  consumedPoints: number;
  remainingPoints: number;
  sourceReference: string;
  occurredAt: string;
  expiresAt?: string | null;
  status: string;
};

export type LoyaltyLedgerEntry = {
  id: string;
  accountId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  entryType: string;
  pointsDelta: number;
  sourceReference: string;
  reversalOfEntryId?: string | null;
  reason?: string | null;
  correlationId?: string | null;
  occurredAt: string;
  expiresAt?: string | null;
  createdAt: string;
};

export type LearnerLoyaltyWalletTotals = {
  ledgerBalance: number;
  activePoints: number;
  expiredPoints: number;
  expiringSoonPoints: number;
  accountCount: number;
  activeAccountCount: number;
  nextExpiryAt?: string | null;
};

export type LearnerLoyaltyWalletAccount = {
  balance: LearnerLoyaltyBalance;
  buckets: LoyaltyBalanceBucket[];
  recentEntries: LoyaltyLedgerEntry[];
};

export type LearnerLoyaltyReward = {
  id: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  rewardCode: string;
  name: string;
  description?: string | null;
  pointsCost: number;
  pointUnit: string;
  ledgerBalance: number;
  spendableBalance: number;
  eligible: boolean;
  ineligibleReasons: string[];
  inventoryRemaining?: number | null;
  perProfileRemaining?: number | null;
  startsAt?: string | null;
  endsAt?: string | null;
  fulfillmentType: string;
};

export type LoyaltyRewardRedemption = {
  id: string;
  rewardId: string;
  accountId: string;
  burnEntryId: string;
  reversalEntryId?: string | null;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  rewardCode: string;
  pointsCost: number;
  sourceReference: string;
  status: string;
  fulfillmentStatus: string;
  fulfillmentRef?: string | null;
  fulfillmentNote?: string | null;
  fulfillmentProvider?: string | null;
  fulfillmentAttemptCount?: number;
  fulfillmentLastAttemptAt?: string | null;
  fulfillmentNextAttemptAt?: string | null;
  fulfillmentSlaDueAt?: string | null;
  fulfillmentErrorClass?: string | null;
  fulfillmentErrorMessage?: string | null;
  fulfillmentCallbackReceivedAt?: string | null;
  fulfillmentCallbackPayloadHash?: string | null;
  rewardSnapshot?: Record<string, unknown> | null;
  correlationId?: string | null;
  note?: string | null;
  metadata?: Record<string, unknown> | null;
  redeemedAt?: string | null;
  fulfilledAt?: string | null;
  reversedAt?: string | null;
  idempotencyReplay: boolean;
};

export type LearnerLoyaltyWalletResponse = {
  profileId: string;
  generatedAt: string;
  totals: LearnerLoyaltyWalletTotals;
  accounts: LearnerLoyaltyWalletAccount[];
  availableRewards: LearnerLoyaltyReward[];
  recentRedemptions: LoyaltyRewardRedemption[];
  warnings: string[];
};

export async function getLearnerLoyaltyBalances(): Promise<LearnerLoyaltyBalanceResponse> {
  return clientFetch<LearnerLoyaltyBalanceResponse>("/v1/loyalty/balances");
}

export async function getLearnerLoyaltyWallet(): Promise<LearnerLoyaltyWalletResponse> {
  return clientFetch<LearnerLoyaltyWalletResponse>("/v1/loyalty/wallet");
}

export async function redeemLearnerLoyaltyReward(
  rewardId: string,
  input: {
    idempotencyKey: string;
    correlationId?: string;
    note?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<LoyaltyRewardRedemption> {
  return clientFetch<LoyaltyRewardRedemption>(`/v1/loyalty/rewards/${rewardId}:redeem`, {
    method: "POST",
    body: input
  });
}
