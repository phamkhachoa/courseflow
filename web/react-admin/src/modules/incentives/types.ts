export type JsonRecord = Record<string, unknown>;

export type RuleSpec = {
  type: string;
  schemaVersion?: number | null;
  parameters?: JsonRecord | null;
};

export type ActionSpec = {
  type: string;
  schemaVersion?: number | null;
  parameters?: JsonRecord | null;
};

export type IncentiveEffect = {
  type?: string | null;
  targetType?: string | null;
  targetId?: string | null;
  amount?: number | string | null;
  currency?: string | null;
  metadata?: JsonRecord | null;
  effectId?: string | null;
  benefitType?: string | null;
  actionType?: string | null;
  unit?: string | null;
  quantity?: number | string | null;
  campaignVersion?: number | null;
};

export type IncentiveItem = {
  id: string;
  type: string;
  quantity: number;
  unitPrice: number | string;
  attributes?: JsonRecord | null;
};

export type TransactionContext = {
  subtotal: number | string;
  shippingAmount?: number | string | null;
};

export type EvaluateIncentivesRequest = {
  tenantId: string;
  applicationId: string;
  profileId: string;
  externalReference?: string | null;
  channel?: string | null;
  currency: string;
  couponCodes?: string[];
  couponIds?: string[];
  transaction: TransactionContext;
  items?: IncentiveItem[];
  attributes?: JsonRecord | null;
};

export type EvaluateIncentivesResponse = {
  eligible: boolean;
  campaignId?: string | null;
  campaignVersion?: number | null;
  campaignCode?: string | null;
  couponId?: string | null;
  effects: IncentiveEffect[];
  reasonCodes: string[];
};

export type AdminPreviewIncentivesRequest = {
  context: EvaluateIncentivesRequest;
  note?: string;
};

export type AdminSimulationTotals = {
  subtotal: number | string;
  totalDiscount: number | string;
  finalAmount: number | string;
  currency?: string | null;
  totalPoints: number | string;
};

export type AdminSimulationQuotaExposure = {
  scopeType: string;
  scopeId: string;
  profileId: string;
  limit: number;
  used: number;
  remaining: number;
  available: boolean;
  wouldConsume: boolean;
};

export type AdminSimulationCandidate = {
  campaignId: string;
  campaignVersion?: number | null;
  campaignCode?: string | null;
  couponId?: string | null;
  matched: boolean;
  selected: boolean;
  exclusive?: boolean;
  stackable?: boolean;
  stackingStatus?: string | null;
  stackingReasonCodes?: string[];
  effects: IncentiveEffect[];
  reasonCodes: string[];
  quotaExposure: AdminSimulationQuotaExposure[];
};

export type AdminPreviewIncentivesResponse = {
  preview: boolean;
  ledgerImpact: boolean;
  contextHash: string;
  decision: EvaluateIncentivesResponse;
  winningCampaignId?: string | null;
  winningCampaignVersion?: number | null;
  winningCampaignCode?: string | null;
  couponId?: string | null;
  totals?: AdminSimulationTotals | null;
  quotaExposure?: AdminSimulationQuotaExposure[];
  candidates?: AdminSimulationCandidate[];
  generatedAt?: string | null;
};

export type IncentiveApplication = {
  id: string;
  tenantId: string;
  applicationId: string;
  name: string;
  status: string;
  clientBindings?: ApplicationClientBinding[];
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type ApplicationClientBinding = {
  id: string;
  tenantId: string;
  applicationId: string;
  clientId: string;
  status: string;
  allowedOperations?: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type Campaign = {
  id: string;
  tenantId: string;
  applicationId: string;
  code: string;
  name: string;
  description?: string | null;
  incentiveType?: string | null;
  status?: string | null;
  startsAt?: string | null;
  endsAt?: string | null;
  priority: number;
  exclusive: boolean;
  stackable: boolean;
  couponRequired: boolean;
  matchPolicy?: string | null;
  currency?: string | null;
  rules?: RuleSpec[];
  actions?: ActionSpec[];
  maxRedemptions?: number | null;
  maxRedemptionsPerProfile?: number | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  publishedAt?: string | null;
  draftVersion?: number | null;
  publishedVersion?: number | null;
};

export type CampaignVersion = {
  id: string;
  campaignId: string;
  versionNumber: number;
  versionStatus: string;
  activeSnapshot: boolean;
  createdBy?: string | null;
  submittedBy?: string | null;
  reviewedBy?: string | null;
  publishedBy?: string | null;
  reviewNote?: string | null;
  createdAt?: string | null;
  submittedAt?: string | null;
  reviewedAt?: string | null;
  publishedAt?: string | null;
};

export type CampaignVersionReviewQueueItem = {
  version: CampaignVersion;
  tenantId: string;
  applicationId: string;
  campaignCode: string;
  campaignName: string;
  blockerCount: number;
  warningCount: number;
  publishable: boolean;
};

export type CampaignVersionReviewQueueResponse = {
  items: CampaignVersionReviewQueueItem[];
  limit: number;
  hasMore: boolean;
};

export type CampaignVersionDetail = CampaignVersion & {
  tenantId: string;
  applicationId: string;
  code: string;
  name: string;
  description?: string | null;
  incentiveType?: string | null;
  startsAt?: string | null;
  endsAt?: string | null;
  priority: number;
  exclusive: boolean;
  stackable: boolean;
  couponRequired: boolean;
  matchPolicy?: string | null;
  currency?: string | null;
  rules?: RuleSpec[];
  actions?: ActionSpec[];
  maxRedemptions?: number | null;
  maxRedemptionsPerProfile?: number | null;
  rollbackSourceVersion?: number | null;
};

export type ValidationMessage = {
  severity: string;
  code: string;
  field?: string | null;
  message: string;
};

export type CampaignVersionValidation = {
  campaignId: string;
  versionNumber: number;
  publishable: boolean;
  blockers: ValidationMessage[];
  warnings: ValidationMessage[];
};

export type CampaignVersionDiffEntry = {
  field: string;
  leftValue: unknown;
  rightValue: unknown;
};

export type CampaignVersionDiff = {
  campaignId: string;
  leftVersion: number;
  rightVersion: number;
  changes: CampaignVersionDiffEntry[];
};

export type AuditEvent = {
  id: string;
  tenantId?: string | null;
  applicationId?: string | null;
  aggregateId?: string | null;
  aggregateType?: string | null;
  action?: string | null;
  actorId?: string | null;
  note?: string | null;
  payload?: JsonRecord | null;
  correlationId?: string | null;
  sourceClientId?: string | null;
  createdAt?: string | null;
};

export type AuditQueryResponse = {
  items: AuditEvent[];
  limit: number;
  hasMore: boolean;
};

export type LoyaltyClientBinding = {
  id: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  clientId: string;
  status: string;
  allowedOperations?: string[];
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type LoyaltyProgram = {
  id: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  name: string;
  pointUnit: string;
  status: string;
  allowNegativeBalance: boolean;
  defaultPointsExpiryDays?: number | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  clientBindings?: LoyaltyClientBinding[];
};

export type LoyaltyAccount = {
  id: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  status: string;
  balance: number;
  openedAt?: string | null;
};

export type LoyaltyTierPolicy = {
  id: string;
  programUuid: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  tierCode: string;
  name: string;
  rank: number;
  status: string;
  qualificationPoints: number;
  qualificationWindowDays: number;
  downgradeGraceDays: number;
  benefits?: JsonRecord | null;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type CreateLoyaltyTierPolicyRequest = {
  tenantId: string;
  applicationId: string;
  programId: string;
  tierCode: string;
  name: string;
  rank: number;
  qualificationPoints: number;
  qualificationWindowDays: number;
  downgradeGraceDays: number;
  benefits?: JsonRecord;
};

export type UpdateLoyaltyTierPolicyRequest = Partial<Omit<CreateLoyaltyTierPolicyRequest, "tenantId" | "applicationId" | "programId" | "tierCode">>;

export type UpdateLoyaltyTierPolicyStatusRequest = {
  status: string;
  note?: string;
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

export type LoyaltyTierState = {
  id: string;
  accountId: string;
  programUuid: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  progress: LoyaltyTierProgress;
  updatedAt?: string | null;
};

export type LoyaltyTierStateQueryResponse = {
  items: LoyaltyTierState[];
  limit: number;
  hasMore: boolean;
};

export type LoyaltyTierFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  status?: string;
  profileId?: string;
  tierCode?: string;
  limit?: number;
};

export type RecalculateLoyaltyTiersRequest = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  profileId?: string;
  accountId?: string;
  limit?: number;
  reason?: string;
  correlationId?: string;
};

export type LoyaltyTierRecalculateResponse = {
  runAt: string;
  scanned: number;
  changed: number;
  items: LoyaltyTierState[];
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
  occurredAt?: string | null;
  expiresAt?: string | null;
  createdAt?: string | null;
};

export type LoyaltyLedgerQueryResponse = {
  accountId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  balance: number;
  items: LoyaltyLedgerEntry[];
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
  occurredAt?: string | null;
  expiresAt?: string | null;
  status: string;
};

export type LoyaltyBalanceBucketResponse = {
  accountId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  ledgerBalance: number;
  activePoints: number;
  expiredPoints: number;
  unallocatedDebitPoints: number;
  projectionMode: string;
  asOf: string;
  items: LoyaltyBalanceBucket[];
  warnings: string[];
};

export type PointLotBackfillRequest = {
  tenantId: string;
  applicationId: string;
  programId?: string;
  profileId?: string;
  accountId?: string;
  dryRun?: boolean;
  limit?: number;
  expectedResultHash?: string;
  reason?: string;
  correlationId?: string;
};

export type PointLotBackfillAccountResult = {
  accountId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  ledgerBalance: number;
  projectedRemainingPoints: number;
  projectedExpiredPoints: number;
  unallocatedDebitPoints: number;
  positiveEntryCount: number;
  debitEntryCount: number;
  existingLotCount: number;
  missingLotCount: number;
  resetLotCount: number;
  warnings: string[];
};

export type PointLotBackfillResponse = {
  tenantId: string;
  applicationId: string;
  programId?: string | null;
  profileId?: string | null;
  accountId?: string | null;
  dryRun: boolean;
  scannedAccountCount: number;
  affectedAccountCount: number;
  missingLotCount: number;
  resetLotCount: number;
  unallocatedDebitPoints: number;
  hasMore: boolean;
  resultHash: string;
  generatedAt: string;
  items: PointLotBackfillAccountResult[];
  warnings: string[];
};

export type LoyaltyPointsMutationResponse = {
  entryId: string;
  accountId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  entryType: string;
  pointsDelta: number;
  balance: number;
  idempotencyReplay: boolean;
};

export type AdjustLoyaltyPointsRequest = {
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  pointsDelta: number;
  sourceReference: string;
  idempotencyKey: string;
  reason: string;
  correlationId: string;
  occurredAt?: string;
  expiresAt?: string;
  metadata?: JsonRecord;
};

export type LoyaltyExpiryDryRunRequest = {
  tenantId: string;
  applicationId: string;
  programId: string;
  asOf: string;
  limit?: number;
};

export type LoyaltyExpiryCandidate = {
  entryId: string;
  accountId: string;
  profileId: string;
  pointsDelta: number;
  sourceReference: string;
  occurredAt?: string | null;
  expiresAt?: string | null;
};

export type LoyaltyExpiryDryRunResponse = {
  tenantId: string;
  applicationId: string;
  programId: string;
  asOf: string;
  candidateEntryCount: number;
  affectedAccountCount: number;
  expiringPoints: number;
  resultHash: string;
  samples: LoyaltyExpiryCandidate[];
  warnings: string[];
};

export type LoyaltyExpiryExecutionRequest = {
  tenantId: string;
  applicationId: string;
  programId: string;
  asOf: string;
  idempotencyKey: string;
  reason: string;
  correlationId: string;
  limit?: number;
  approvalId?: string;
};

export type SubmitLoyaltyExpiryApprovalRequest = {
  tenantId: string;
  applicationId: string;
  programId: string;
  asOf: string;
  resultHash: string;
  idempotencyKey: string;
  reason: string;
  correlationId: string;
  limit?: number;
};

export type LoyaltyExpiryExecutionItem = {
  entryId: string;
  accountId: string;
  sourceLotId: string;
  sourceEntryId: string;
  profileId: string;
  expiredPoints: number;
  sourceReference: string;
  expiresAt?: string | null;
};

export type LoyaltyExpiryExecutionResponse = {
  tenantId: string;
  applicationId: string;
  programId: string;
  asOf: string;
  expiredLotCount: number;
  affectedAccountCount: number;
  expiredPoints: number;
  idempotencyReplay: boolean;
  items: LoyaltyExpiryExecutionItem[];
  warnings: string[];
};

export type LoyaltyAdjustmentApproval = {
  id: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  pointsDelta: number;
  sourceReference: string;
  reason: string;
  correlationId: string;
  occurredAt?: string | null;
  expiresAt?: string | null;
  status: string;
  requestedBy: string;
  reviewedBy?: string | null;
  reviewNote?: string | null;
  requestedAt?: string | null;
  reviewedAt?: string | null;
  executedAt?: string | null;
  executedEntryId?: string | null;
  operationType: string;
  metadata: JsonRecord;
};

export type LoyaltyApprovalEvidencePack = {
  approvalId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  operationType: string;
  generatedAt: string;
  approval: LoyaltyAdjustmentApproval;
  auditEvents: AuditEvent[];
  ledgerEntries: LoyaltyReconciliationEntry[];
  evidenceSummary: JsonRecord;
  warnings: string[];
};

export type LoyaltyAdjustmentApprovalFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  profileId?: string;
  status?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type SubmitLoyaltyAdjustmentApprovalRequest = AdjustLoyaltyPointsRequest;

export type ReviewLoyaltyAdjustmentApprovalRequest = {
  note: string;
};

export type LoyaltyAdjustmentApprovalQueryResponse = {
  items: LoyaltyAdjustmentApproval[];
  limit: number;
  hasMore: boolean;
};

export type LoyaltyReconciliationFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  profileId?: string;
  accountId?: string;
  entryType?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type LoyaltyReconciliationEntry = {
  ledgerEntryId: string;
  reconciliationKey: string;
  reconciliationStatus: string;
  reasonCodes: string[];
  direction: string;
  entryType: string;
  accountId: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  pointsDelta: number;
  sourceReference: string;
  reversalOfEntryId?: string | null;
  outboxStatus: string;
  correlationId?: string | null;
  occurredAt?: string | null;
  expiresAt?: string | null;
  ledgerCreatedAt?: string | null;
};

export type LoyaltyReconciliationQueryResponse = {
  items: LoyaltyReconciliationEntry[];
  limit: number;
  hasMore: boolean;
  generatedAt: string;
};

export type LoyaltyBenefitReconciliationFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  profileId?: string;
  redemptionId?: string;
  itemType?: string;
  status?: string;
  includeMatched?: boolean;
  from?: string;
  to?: string;
  limit?: number;
};

export type LoyaltyBenefitReconciliationEntry = {
  reconciliationKey: string;
  reconciliationStatus: string;
  reasonCodes: string[];
  itemType: string;
  severity: string;
  tenantId: string;
  applicationId: string;
  programId?: string | null;
  profileId?: string | null;
  redemptionId?: string | null;
  effectId?: string | null;
  expectedEntryType?: string | null;
  expectedPointsDelta: number;
  expectedSourceReference?: string | null;
  expectedIdempotencyKey?: string | null;
  ledgerEntryId?: string | null;
  reversalOfEntryId?: string | null;
  rewardRedemptionId?: string | null;
  rewardBurnEntryId?: string | null;
  rewardReversalEntryId?: string | null;
  rewardCode?: string | null;
  rewardStatus?: string | null;
  rewardPointsCost: number;
  sourceEventType?: string | null;
  sourceEventId?: string | null;
  payloadHash?: string | null;
  correlationId?: string | null;
  observedAt?: string | null;
  ledgerCreatedAt?: string | null;
  rewardReversedAt?: string | null;
};

export type LoyaltyBenefitReconciliationQueryResponse = {
  items: LoyaltyBenefitReconciliationEntry[];
  limit: number;
  hasMore: boolean;
  generatedAt: string;
};

export type LoyaltyFinanceCloseoutFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  from?: string;
  to?: string;
  limit?: number;
  cursor?: string;
};

export type LoyaltyFinanceCloseoutTotals = {
  earnedPoints: number;
  burnedPoints: number;
  reversedPoints: number;
  adjustedPoints: number;
  expiredPoints: number;
  netPoints: number;
  entryCount: number;
  pendingOutboxCount: number;
  missingOutboxCount: number;
};

export type LoyaltyFinanceCloseoutExport = {
  closeoutId: string;
  tenantId: string;
  applicationId: string;
  programId?: string | null;
  from: string;
  to: string;
  resultHash: string;
  certifiable: boolean;
  generatedAt: string;
  totals: LoyaltyFinanceCloseoutTotals;
  items: LoyaltyReconciliationEntry[];
  limit: number;
  hasMore: boolean;
  nextCursor?: string | null;
  warnings: string[];
};

export type LoyaltyReward = {
  id: string;
  programUuid: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  rewardCode: string;
  name: string;
  description?: string | null;
  pointsCost: number;
  status: string;
  startsAt?: string | null;
  endsAt?: string | null;
  inventoryLimit?: number | null;
  perProfileLimit?: number | null;
  fulfillmentType: string;
  fulfillmentConfig?: JsonRecord | null;
  redeemedCount: number;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type LoyaltyRewardFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  status?: string;
  activeOnly?: boolean;
  limit?: number;
};

export type CreateLoyaltyRewardRequest = {
  tenantId: string;
  applicationId: string;
  programId: string;
  rewardCode: string;
  name: string;
  description?: string;
  pointsCost: number;
  status?: string;
  startsAt?: string;
  endsAt?: string;
  inventoryLimit?: number;
  perProfileLimit?: number;
  fulfillmentType?: string;
  fulfillmentConfig?: JsonRecord;
};

export type UpdateLoyaltyRewardRequest = Partial<
  Pick<
    CreateLoyaltyRewardRequest,
    | "name"
    | "description"
    | "pointsCost"
    | "startsAt"
    | "endsAt"
    | "inventoryLimit"
    | "perProfileLimit"
    | "fulfillmentType"
    | "fulfillmentConfig"
  >
>;

export type UpdateLoyaltyRewardStatusRequest = {
  status: string;
  note?: string;
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
  rewardSnapshot?: JsonRecord | null;
  correlationId?: string | null;
  note?: string | null;
  metadata?: JsonRecord | null;
  redeemedAt?: string | null;
  fulfilledAt?: string | null;
  reversedAt?: string | null;
  idempotencyReplay: boolean;
};

export type LoyaltyRewardRedemptionFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  profileId?: string;
  rewardId?: string;
  status?: string;
  fulfillmentStatus?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type LoyaltyRewardRedemptionQueryResponse = {
  items: LoyaltyRewardRedemption[];
  limit: number;
  hasMore: boolean;
};

export type ReverseLoyaltyRewardRedemptionRequest = {
  idempotencyKey: string;
  reason: string;
  correlationId?: string;
  metadata?: JsonRecord;
};

export type UpdateLoyaltyRewardFulfillmentRequest = {
  status: string;
  fulfillmentRef?: string;
  note?: string;
  idempotencyKey: string;
  reason: string;
  correlationId: string;
  metadata?: JsonRecord;
  approvalId: string;
};

export type SubmitLoyaltyRewardFulfillmentApprovalRequest = {
  status: string;
  fulfillmentRef?: string;
  note?: string;
  idempotencyKey: string;
  reason: string;
  correlationId: string;
  metadata?: JsonRecord;
};

export type RetryLoyaltyRewardFulfillmentRequest = {
  reason?: string;
  correlationId?: string;
};

export type RewardFulfillmentRunItem = {
  redemptionId: string;
  rewardCode: string;
  fulfillmentProvider: string;
  fulfillmentStatus: string;
  fulfillmentRef?: string | null;
  fulfillmentAttemptCount: number;
  nextAttemptAt?: string | null;
  errorClass?: string | null;
  errorMessage?: string | null;
};

export type RewardFulfillmentRunResponse = {
  runAt: string;
  scanned: number;
  dispatched: number;
  issued: number;
  pending: number;
  failed: number;
  manualRequired: number;
  items: RewardFulfillmentRunItem[];
};

export type RedeemLoyaltyRewardRequest = {
  idempotencyKey: string;
  correlationId?: string;
  note?: string;
  metadata?: JsonRecord;
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

export type LearnerLoyaltyRewardCatalogResponse = {
  profileId: string;
  generatedAt: string;
  items: LearnerLoyaltyReward[];
};

export type LoyaltyInboundDeadLetter = {
  id: string;
  sourceTopic: string;
  dltTopic: string;
  consumerGroup?: string | null;
  kafkaPartition: number;
  kafkaOffset: number;
  originalPartition?: number | null;
  originalOffset?: number | null;
  recordKey?: string | null;
  status: string;
  replayAttempts: number;
  payloadHash: string;
  exceptionClass?: string | null;
  exceptionMessage?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  lastReplayAt?: string | null;
  replayedAt?: string | null;
  discardedAt?: string | null;
};

export type LoyaltyInboundDeadLetterDetail = LoyaltyInboundDeadLetter & {
  payloadSizeBytes: number;
  stacktrace?: string | null;
  lastReplayError?: string | null;
  resolvedBy?: string | null;
  resolutionNote?: string | null;
  headers?: JsonRecord | null;
};

export type LoyaltyInboundDeadLetterFilters = {
  status?: string;
  sourceTopic?: string;
  dltTopic?: string;
  payloadHash?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type LoyaltyInboundDeadLetterQueryResponse = {
  items: LoyaltyInboundDeadLetter[];
  limit: number;
  hasMore: boolean;
};

export type LoyaltyInboundDeadLetterActionRequest = {
  reason: string;
  dryRun?: boolean;
  approvalId?: string;
};

export type LoyaltyInboundDeadLetterActionResponse = {
  deadLetterId: string;
  action: string;
  status: string;
  dryRun: boolean;
  replayed: boolean;
  discarded: boolean;
  reasonCode: string;
  payloadHash: string;
  completedAt: string;
};

export type LoyaltyInboundDeadLetterApprovalRequest = {
  action: "REPLAY" | "DISCARD";
  reason: string;
  evidenceReference: string;
};

export type LoyaltyInboundDeadLetterApprovalReviewRequest = {
  note: string;
};

export type LoyaltyInboundDeadLetterApproval = {
  id: string;
  deadLetterId: string;
  action: string;
  status: string;
  reason: string;
  evidenceReference: string;
  thresholdPolicy: string;
  payloadHash: string;
  requestHash: string;
  requestedBy: string;
  reviewedBy?: string | null;
  reviewNote?: string | null;
  executedBy?: string | null;
  requestedAt: string;
  reviewedAt?: string | null;
  executedAt?: string | null;
};

export type LoyaltyInboundDeadLetterApprovalQueryResponse = {
  items: LoyaltyInboundDeadLetterApproval[];
  limit: number;
  hasMore: boolean;
};

export type OutboxDeadLetterSummary = {
  id: string;
  serviceName: string;
  sourceEventId: string;
  eventType: string;
  topic?: string | null;
  kafkaPartition?: number | null;
  kafkaOffset?: number | null;
  aggregateId?: string | null;
  status: string;
  attempts: number;
  replayAttempts: number;
  payloadHash: string;
  errorClass?: string | null;
  lastError?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  lastReplayAt?: string | null;
  replayedAt?: string | null;
  discardedAt?: string | null;
};

export type OutboxDeadLetterFilters = {
  status?: string;
  service?: string;
  eventType?: string;
  aggregateId?: string;
  payloadHash?: string;
  limit?: number;
};

export type OutboxDeadLetterQueryResponse = {
  items: OutboxDeadLetterSummary[];
  limit: number;
  hasMore: boolean;
};

export type OutboxDeadLetterActionRequest = {
  idempotencyKey: string;
  reason: string;
  dryRun?: boolean;
  approvalId?: string;
  correlationId?: string;
};

export type OutboxDeadLetterActionResponse = {
  deadLetterId: string;
  action: string;
  status: string;
  dryRun: boolean;
  replayed: boolean;
  discarded: boolean;
  reasonCode: string;
  payloadHash: string;
  completedAt: string;
};

export type OutboxDeadLetterApprovalRequest = {
  action: "REPLAY" | "DISCARD";
  reason: string;
  evidenceReference: string;
  correlationId?: string;
};

export type OutboxDeadLetterApprovalReviewRequest = {
  note: string;
};

export type OutboxDeadLetterApproval = {
  id: string;
  deadLetterId: string;
  action: string;
  status: string;
  reason: string;
  evidenceReference: string;
  thresholdPolicy: string;
  payloadHash: string;
  requestHash: string;
  requestedBy: string;
  reviewedBy?: string | null;
  reviewNote?: string | null;
  executedBy?: string | null;
  executionIdempotencyKey?: string | null;
  correlationId?: string | null;
  requestedAt: string;
  reviewedAt?: string | null;
  executedAt?: string | null;
};

export type OutboxDeadLetterApprovalQueryResponse = {
  items: OutboxDeadLetterApproval[];
  limit: number;
  hasMore: boolean;
};

export type CreateLoyaltyProgramClientBindingRequest = {
  clientId: string;
  allowedOperations: string[];
};

export type CreateLoyaltyProgramRequest = {
  tenantId: string;
  applicationId: string;
  programId: string;
  name: string;
  pointUnit?: string;
  allowNegativeBalance?: boolean;
  defaultPointsExpiryDays?: number;
  clientBindings?: CreateLoyaltyProgramClientBindingRequest[];
};

export type UpdateLoyaltyProgramRequest = {
  name?: string;
  pointUnit?: string;
  allowNegativeBalance?: boolean;
  defaultPointsExpiryDays?: number;
};

export type Coupon = {
  id: string;
  campaignId: string;
  code?: string | null;
  normalizedCode?: string | null;
  codeMask?: string | null;
  status: string;
  holderProfileId?: string | null;
  startsAt?: string | null;
  expiresAt?: string | null;
  maxRedemptions?: number | null;
  maxRedemptionsPerProfile?: number | null;
  metadata?: JsonRecord | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type CouponStorageInventoryItem = {
  storageFormat: string;
  count: number;
};

export type CouponStorageInventory = {
  tenantId?: string | null;
  applicationId?: string | null;
  campaignId?: string | null;
  activeOnly: boolean;
  legacyFallbackEnabled: boolean;
  fallbackDisableReady: boolean;
  totalCoupons: number;
  legacyCoupons: number;
  malformedCoupons: number;
  generatedAt?: string | null;
  items: CouponStorageInventoryItem[];
};

export type Redemption = {
  id: string;
  reservationId?: string | null;
  tenantId: string;
  applicationId: string;
  campaignId: string;
  campaignVersion?: number | null;
  couponId?: string | null;
  profileId: string;
  externalReference?: string | null;
  status: string;
  effects?: IncentiveEffect[];
  redeemedAt?: string | null;
  reversedAt?: string | null;
};

export type ReservationQuotaSnapshot = {
  scopeType: string;
  scopeId: string;
  profileId: string;
  limit: number;
};

export type Reservation = {
  id: string;
  tenantId: string;
  applicationId: string;
  campaignId: string;
  campaignVersion?: number | null;
  couponId?: string | null;
  profileId: string;
  externalReference?: string | null;
  status: string;
  effects?: IncentiveEffect[];
  quotaSnapshot?: ReservationQuotaSnapshot[];
  requestHash?: string | null;
  reservedAt?: string | null;
  expiresAt?: string | null;
  committedAt?: string | null;
  cancelledAt?: string | null;
  failureReason?: string | null;
  expired?: boolean;
};

export type CreateApplicationRequest = {
  tenantId: string;
  applicationId: string;
  name: string;
  status?: string;
  allowedClientIds?: string[];
};

export type UpdateApplicationStatusRequest = {
  status: string;
  note?: string;
};

export type CreateApplicationClientBindingRequest = {
  clientId: string;
  status?: string;
  allowedOperations?: string[];
};

export type CreateCampaignRequest = {
  tenantId: string;
  applicationId: string;
  code: string;
  name: string;
  description?: string;
  incentiveType?: string;
  startsAt?: string;
  endsAt?: string;
  priority?: number;
  exclusive?: boolean;
  stackable?: boolean;
  couponRequired?: boolean;
  matchPolicy?: string;
  currency?: string;
  rules?: RuleSpec[];
  actions: ActionSpec[];
  maxRedemptions?: number;
  maxRedemptionsPerProfile?: number;
};

export type UpdateCampaignVersionDraftRequest = Partial<Omit<CreateCampaignRequest, "tenantId" | "applicationId">>;

export type CampaignVersionTransitionRequest = {
  note?: string;
};

export type RollbackCampaignVersionRequest = {
  note?: string;
};

export type CreateCouponRequest = {
  campaignId: string;
  code: string;
  holderProfileId?: string;
  startsAt?: string;
  expiresAt?: string;
  maxRedemptions?: number;
  maxRedemptionsPerProfile?: number;
  metadata?: JsonRecord;
};

export type UpdateCouponStatusRequest = {
  status: string;
  reason?: string;
};

export type GenerateCouponsRequest = {
  campaignId: string;
  prefix?: string;
  quantity: number;
  codeLength?: number;
  holderProfileId?: string;
  startsAt?: string;
  expiresAt?: string;
  maxRedemptions?: number;
  maxRedemptionsPerProfile?: number;
  metadata?: JsonRecord;
};

export type GenerateCouponsResponse = {
  campaignId: string;
  requested: number;
  created: number;
  duplicateRetries: number;
  coupons: Coupon[];
};

export type CouponDistributionRecipientInput = {
  profileId: string;
  metadata?: JsonRecord;
};

export type PreviewCouponDistributionRequest = {
  campaignId: string;
  sourceType: string;
  sourceReference?: string;
  notifyLearners?: boolean;
  startsAt?: string;
  expiresAt?: string;
  maxRedemptions?: number;
  maxRedemptionsPerProfile?: number;
  metadata?: JsonRecord;
  recipients: CouponDistributionRecipientInput[];
};

export type CouponDistributionPreviewRecipient = {
  profileId: string;
  status: string;
  reason?: string | null;
  metadata?: JsonRecord | null;
};

export type CouponDistributionPreviewResponse = {
  campaignId: string;
  sourceType: string;
  sourceReference?: string | null;
  notifyLearners: boolean;
  requestedRecipients: number;
  uniqueRecipients: number;
  duplicateRecipients: number;
  previewHash: string;
  sampleRecipients: CouponDistributionPreviewRecipient[];
};

export type CreateCouponDistributionRequest = PreviewCouponDistributionRequest & {
  name: string;
  previewHash: string;
  reason?: string;
};

export type CouponDistributionActionRequest = {
  reason?: string;
};

export type CouponDistributionRecipient = {
  id: string;
  distributionId: string;
  profileId: string;
  status: string;
  couponId?: string | null;
  notificationStatus?: string | null;
  failureReason?: string | null;
  metadata?: JsonRecord | null;
  createdAt?: string | null;
  issuedAt?: string | null;
  revokedAt?: string | null;
};

export type CouponDistribution = {
  id: string;
  tenantId: string;
  applicationId: string;
  campaignId: string;
  name: string;
  sourceType: string;
  sourceReference?: string | null;
  status: string;
  notifyLearners: boolean;
  startsAt?: string | null;
  expiresAt?: string | null;
  maxRedemptions?: number | null;
  maxRedemptionsPerProfile?: number | null;
  recipientCount: number;
  issuedCount: number;
  revokedCount: number;
  previewHash: string;
  reason?: string | null;
  metadata?: JsonRecord | null;
  createdBy?: string | null;
  approvedBy?: string | null;
  issuedBy?: string | null;
  revokedBy?: string | null;
  createdAt?: string | null;
  approvedAt?: string | null;
  issuedAt?: string | null;
  revokedAt?: string | null;
  updatedAt?: string | null;
  recipients?: CouponDistributionRecipient[];
};

export type CouponDistributionFilters = {
  tenantId?: string;
  applicationId?: string;
  campaignId?: string;
  status?: string;
  limit?: number;
};

export type CouponDistributionQueryResponse = {
  items: CouponDistribution[];
  limit: number;
};

export type CouponImportDryRunIssue = {
  rowNumber: number;
  codeMask?: string | null;
  field?: string | null;
  reasonCode: string;
  message: string;
};

export type CouponImportDryRunRow = {
  rowNumber: number;
  codeMask?: string | null;
  status: string;
  issueCodes?: string[];
};

export type CouponImportDryRunRequest = {
  campaignId: string;
  file: File;
  maxRows?: number;
  holderProfileId?: string;
  startsAt?: string;
  expiresAt?: string;
  maxRedemptions?: number;
  maxRedemptionsPerProfile?: number;
  metadataJson?: string;
  idempotencyKey?: string;
};

export type CouponImportDryRunResponse = {
  dryRunId: string;
  campaignId: string;
  dryRun: boolean;
  requestedRows: number;
  validRows: number;
  invalidRows: number;
  duplicateInFileRows: number;
  duplicateExistingRows: number;
  storageInventoryReady: boolean;
  commitReady: boolean;
  resultHash: string;
  generatedAt: string;
  warnings: string[];
  issues: CouponImportDryRunIssue[];
  sampleRows: CouponImportDryRunRow[];
};

export type CouponImportDryRunListItem = {
  dryRunId: string;
  tenantId: string;
  applicationId: string;
  campaignId: string;
  status: string;
  requestedRows: number;
  validRows: number;
  invalidRows: number;
  duplicateInFileRows: number;
  duplicateExistingRows: number;
  storageInventoryReady: boolean;
  commitReady: boolean;
  resultHash: string;
  createdBy?: string | null;
  correlationId?: string | null;
  sourceClientId?: string | null;
  createdAt?: string | null;
  expiresAt?: string | null;
  committedAt?: string | null;
  committedBy?: string | null;
  committedOperationId?: string | null;
  committedRows: number;
  failureReason?: string | null;
};

export type CouponImportDryRunHistoryFilters = {
  tenantId?: string;
  applicationId?: string;
  campaignId?: string;
  status?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type CouponImportDryRunQueryResponse = {
  items: CouponImportDryRunListItem[];
  limit: number;
  hasMore: boolean;
  generatedAt: string;
};

export type CouponImportApproval = {
  approvalId: string;
  status: string;
  dryRunId: string;
  campaignId: string;
  approvedResultHash: string;
  requestedRows: number;
  validRows: number;
  invalidRows: number;
  duplicateInFileRows: number;
  duplicateExistingRows: number;
  storageInventoryReady: boolean;
  commitReady: boolean;
  reason?: string | null;
  changeTicket?: string | null;
  requestedBy?: string | null;
  approvedBy?: string | null;
  rejectedBy?: string | null;
  committedBy?: string | null;
  expiresAt?: string | null;
  createdAt?: string | null;
  approvedAt?: string | null;
  rejectedAt?: string | null;
  committedAt?: string | null;
};

export type CouponImportApprovalFilters = {
  tenantId?: string;
  applicationId?: string;
  campaignId?: string;
  status?: string;
  limit?: number;
};

export type CouponImportApprovalDecisionRequest = {
  note?: string;
};

export type CouponImportApprovalRequest = {
  dryRunId: string;
  campaignId: string;
  file: File;
  approvedResultHash: string;
  reason: string;
  changeTicket: string;
  maxRows?: number;
  holderProfileId?: string;
  startsAt?: string;
  expiresAt?: string;
  maxRedemptions?: number;
  maxRedemptionsPerProfile?: number;
  metadataJson?: string;
};

export type CouponImportCommitRequest = CouponImportApprovalRequest & {
  approvalId: string;
  idempotencyKey: string;
  confirm: boolean;
};

export type CouponImportCommitResponse = {
  importId: string;
  approvalId: string;
  dryRunId: string;
  campaignId: string;
  status: string;
  requestedRows: number;
  importedRows: number;
  resultHash: string;
  idempotencyReplay: boolean;
  committedAt?: string | null;
  warnings: string[];
};

export type CouponImportOperation = {
  importId: string;
  approvalId?: string | null;
  dryRunId: string;
  tenantId: string;
  applicationId: string;
  campaignId: string;
  status: string;
  requestedRows: number;
  importedRows: number;
  resultHash: string;
  reason: string;
  changeTicket: string;
  createdBy?: string | null;
  correlationId?: string | null;
  sourceClientId?: string | null;
  createdAt?: string | null;
};

export type CouponImportOperationFilters = {
  tenantId?: string;
  applicationId?: string;
  campaignId?: string;
  approvalId?: string;
  dryRunId?: string;
  status?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type CouponImportOperationQueryResponse = {
  items: CouponImportOperation[];
  limit: number;
  hasMore: boolean;
  generatedAt: string;
};

export type CouponImportOperationExport = {
  importId: string;
  approvalId?: string | null;
  dryRunId: string;
  campaignId: string;
  tenantId: string;
  applicationId: string;
  filename: string;
  contentType: string;
  content: string;
  generatedAt: string;
};

export type IncentiveReconciliationEffect = {
  effectId?: string | null;
  type?: string | null;
  benefitType?: string | null;
  actionType?: string | null;
  targetType?: string | null;
  targetId?: string | null;
  amount?: number | string | null;
  currency?: string | null;
  unit?: string | null;
  quantity?: number | string | null;
  campaignVersion?: number | null;
  metadata?: JsonRecord | null;
};

export type IncentiveReconciliationEntry = {
  ledgerEntryId: string;
  reconciliationKey: string;
  reconciliationStatus: string;
  reasonCodes: string[];
  direction: string;
  entryType: string;
  redemptionId?: string | null;
  reservationId?: string | null;
  tenantId: string;
  applicationId: string;
  campaignId: string;
  campaignVersion: number;
  couponId?: string | null;
  profileId: string;
  externalReference?: string | null;
  redemptionStatus?: string | null;
  quotaPolicy: string;
  quotaReleased?: boolean | null;
  outboxStatus: string;
  outboxEventType?: string | null;
  outboxPublishedAt?: string | null;
  correlationId?: string | null;
  sourceClientId?: string | null;
  ledgerCreatedAt: string;
  redeemedAt?: string | null;
  reversedAt?: string | null;
  effect?: IncentiveReconciliationEffect | null;
};

export type IncentiveReconciliationFilters = {
  tenantId?: string;
  applicationId?: string;
  profileId?: string;
  externalReference?: string;
  campaignId?: string;
  couponId?: string;
  redemptionId?: string;
  reservationId?: string;
  entryType?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type IncentiveReconciliationQueryResponse = {
  items: IncentiveReconciliationEntry[];
  limit: number;
  hasMore: boolean;
  generatedAt: string;
};

export type ReverseRedemptionRequest = {
  idempotencyKey: string;
  reason: string;
  approvalId?: string;
  changeTicket?: string;
};

export type RedemptionReversalApproval = {
  approvalId: string;
  status: string;
  redemptionId: string;
  reservationId?: string | null;
  tenantId: string;
  applicationId: string;
  campaignId: string;
  campaignVersion?: number | null;
  couponId?: string | null;
  profileId?: string | null;
  externalReference?: string | null;
  idempotencyKey?: string | null;
  requestHash: string;
  resultHash: string;
  subjectHash: string;
  reason: string;
  changeTicket: string;
  requestedBy?: string | null;
  approvedBy?: string | null;
  rejectedBy?: string | null;
  executedBy?: string | null;
  expiresAt?: string | null;
  createdAt?: string | null;
  approvedAt?: string | null;
  rejectedAt?: string | null;
  executedAt?: string | null;
  subject?: Record<string, unknown> | null;
};

export type RedemptionReversalApprovalRequest = {
  idempotencyKey: string;
  reason: string;
  changeTicket: string;
  metadata?: Record<string, unknown>;
};

export type RedemptionReversalApprovalDecisionRequest = {
  note?: string;
};

export type RedemptionReversalApprovalFilters = {
  tenantId?: string;
  applicationId?: string;
  campaignId?: string;
  status?: string;
  limit?: number;
};

export type ApplicationFilters = {
  tenantId?: string;
  applicationId?: string;
  status?: string;
};

export type CampaignFilters = {
  tenantId?: string;
  applicationId?: string;
};

export type ReviewQueueFilters = CampaignFilters & {
  status?: string;
  limit?: number;
};

export type CouponFilters = {
  tenantId?: string;
  applicationId?: string;
  campaignId?: string;
  status?: string;
  holderProfileId?: string;
  code?: string;
  limit?: number;
};

export type RedemptionFilters = {
  tenantId?: string;
  applicationId?: string;
  profileId?: string;
  externalReference?: string;
  campaignId?: string;
  couponId?: string;
  limit?: number;
};

export type ReservationFilters = RedemptionFilters & {
  status?: string;
  expiredOnly?: boolean;
};

export type AuditFilters = {
  tenantId?: string;
  applicationId?: string;
  aggregateType?: string;
  aggregateId?: string;
  action?: string;
  actorId?: string;
  correlationId?: string;
  sourceClientId?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export type LoyaltyProgramFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  status?: string;
  limit?: number;
};

export type LoyaltyAccountFilters = {
  tenantId?: string;
  applicationId?: string;
  programId?: string;
  profileId?: string;
  status?: string;
  limit?: number;
};

export type LoyaltyLedgerFilters = {
  accountId?: string;
};

export type UpdateLoyaltyProgramStatusRequest = {
  status: string;
  note?: string;
};

export type UpdateLoyaltyAccountStatusRequest = {
  status: string;
  note?: string;
};

export type UpsertLoyaltyClientBindingRequest = {
  clientId: string;
  status: string;
  allowedOperations: string[];
};

export type SubmittedCampaignVersion = CampaignVersionReviewQueueItem;

export type RetentionPolicy = {
  policyId: string;
  policyVersion: string;
  targetDataset: string;
  actionType: string;
  defaultRetentionDays: number;
  minimumRetentionDays: number;
  defaultBatchLimit: number;
  destructiveExecutionSupported: boolean;
  scopeTypes: string[];
  eligibleWhen?: string | null;
  blockerRules: string[];
};

export type RetentionPolicyRegistry = {
  policies: RetentionPolicy[];
};

export type RetentionDryRunRequest = {
  tenantId?: string;
  applicationId?: string;
  policyIds?: string[];
  asOf?: string;
  retentionDaysOverride?: Record<string, number>;
  batchLimit?: number;
  reason?: string;
};

export type RetentionDryRunResult = {
  policyId: string;
  policyVersion: string;
  targetDataset: string;
  actionType: string;
  cutoff: string;
  retentionDays: number;
  eligibleCount: number;
  blockedCount: number;
  blockedReason?: string | null;
  oldestCandidateAt?: string | null;
  newestCandidateAt?: string | null;
  batchLimit: number;
  destructiveExecutionSupported: boolean;
  resultHash: string;
};

export type RetentionDryRunResponse = {
  dryRunId: string;
  resultHash: string;
  dryRun: boolean;
  nonDestructive: boolean;
  tenantId?: string | null;
  applicationId?: string | null;
  generatedAt: string;
  results: RetentionDryRunResult[];
  warnings: string[];
};

export type RetentionRestoreDrillRequest = {
  restoreDrillRef: string;
  databaseName: string;
  backupPath: string;
  artifactHash: string;
  status: string;
  checkedAt?: string;
  expiresAt?: string;
  note?: string;
};

export type RetentionRestoreDrill = {
  id: string;
  restoreDrillRef: string;
  databaseName: string;
  backupPath: string;
  artifactHash: string;
  status: string;
  checkedAt: string;
  expiresAt: string;
  createdBy: string;
  createdAt: string;
};

export type RetentionApprovalRequest = {
  tenantId?: string;
  applicationId?: string;
  policyId: string;
  asOf: string;
  retentionDaysOverride?: Record<string, number>;
  batchLimit?: number;
  approvedDryRunId: string;
  approvedResultHash: string;
  reason: string;
  changeTicket: string;
  restoreDrillRef: string;
};

export type RetentionApprovalDecisionRequest = {
  note?: string;
};

export type RetentionApproval = {
  approvalId: string;
  status: string;
  policyId: string;
  policyVersion: string;
  targetDataset: string;
  tenantId?: string | null;
  applicationId?: string | null;
  asOf: string;
  cutoff: string;
  retentionDays: number;
  dryRunId: string;
  approvedResultHash: string;
  eligibleCount: number;
  batchLimit: number;
  restoreDrillRef: string;
  changeTicket: string;
  reason: string;
  note?: string | null;
  requestedBy?: string | null;
  approvedBy?: string | null;
  rejectedBy?: string | null;
  executedBy?: string | null;
  correlationId?: string | null;
  sourceClientId?: string | null;
  expiresAt: string;
  createdAt: string;
  approvedAt?: string | null;
  rejectedAt?: string | null;
  failedAt?: string | null;
  executedAt?: string | null;
};

export type RetentionApprovalFilters = {
  scopeType?: "APPLICATION" | "GLOBAL";
  tenantId?: string;
  applicationId?: string;
  approvalId?: string;
  dryRunId?: string;
  status?: string;
  policyId?: string;
  changeTicket?: string;
  requestedBy?: string;
  approvedBy?: string;
  executedBy?: string;
  expired?: boolean;
  from?: string;
  to?: string;
  limit?: number;
};

export type RetentionApprovalQueryResponse = {
  items: RetentionApproval[];
  limit: number;
  hasMore: boolean;
  generatedAt: string;
};

export type RetentionRestoreDrillEvidence = {
  id: string;
  restoreDrillRef: string;
  databaseName: string;
  backupPath: string;
  artifactHash: string;
  status: string;
  checkedAt: string;
  expiresAt: string;
  createdBy: string;
  note?: string | null;
  correlationId?: string | null;
  sourceClientId?: string | null;
  createdAt: string;
};

export type RetentionExecutionEvidence = {
  executionId: string;
  approvalId: string;
  status: string;
  policyId: string;
  policyVersion: string;
  targetDataset: string;
  tenantId?: string | null;
  applicationId?: string | null;
  dryRunId: string;
  approvedResultHash: string;
  cutoff: string;
  expectedEligibleCount: number;
  redactedCount: number;
  batchLimit: number;
  hasMore?: boolean | null;
  idempotencyKeyHash: string;
  changeTicket: string;
  restoreDrillRef: string;
  approvedBy?: string | null;
  executedBy?: string | null;
  correlationId?: string | null;
  lastError?: string | null;
  createdAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
};

export type RetentionAuditEvidenceEvent = {
  eventId: string;
  action: string;
  aggregateType: string;
  aggregateId: string;
  actorId?: string | null;
  note?: string | null;
  correlationId?: string | null;
  sourceClientId?: string | null;
  createdAt: string;
  payloadSummary: JsonRecord;
};

export type RetentionEvidencePack = {
  schemaVersion: string;
  artifactType: string;
  approvalId: string;
  generatedAt: string;
  approval: RetentionApproval;
  restoreDrill?: RetentionRestoreDrillEvidence | null;
  execution?: RetentionExecutionEvidence | null;
  auditTrail: RetentionAuditEvidenceEvent[];
  warnings: string[];
};

export type RetentionEvidencePackExport = {
  approvalId: string;
  filename: string;
  contentType: string;
  content: string;
  contentSha256: string;
  generatedAt: string;
};

export type RetentionExecutionRequest = {
  approvalId: string;
  idempotencyKey: string;
  confirm: boolean;
};

export type RetentionExecutionResponse = {
  executionId: string;
  status: string;
  policyId: string;
  policyVersion: string;
  targetDataset: string;
  tenantId?: string | null;
  applicationId?: string | null;
  cutoff: string;
  dryRunId: string;
  approvedResultHash: string;
  eligibleBefore: number;
  redactedCount: number;
  batchLimit: number;
  hasMore: boolean;
  idempotencyReplay: boolean;
  executedAt: string;
};
