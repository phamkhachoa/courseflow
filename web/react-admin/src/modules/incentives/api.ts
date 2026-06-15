import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";
import type {
  ApplicationClientBinding,
  ApplicationFilters,
  AuditFilters,
  AuditQueryResponse,
  AdminPreviewIncentivesRequest,
  AdminPreviewIncentivesResponse,
  Campaign,
  CampaignFilters,
  CampaignVersion,
  CampaignVersionDetail,
  CampaignVersionDiff,
  CampaignVersionReviewQueueResponse,
  CampaignVersionTransitionRequest,
  CampaignVersionValidation,
  Coupon,
  CouponDistribution,
  CouponDistributionActionRequest,
  CouponDistributionFilters,
  CouponDistributionPreviewResponse,
  CouponDistributionQueryResponse,
  CouponFilters,
  CouponStorageInventory,
  CouponImportApproval,
  CouponImportApprovalDecisionRequest,
  CouponImportApprovalFilters,
  CouponImportApprovalRequest,
  CouponImportCommitRequest,
  CouponImportCommitResponse,
  CouponImportDryRunHistoryFilters,
  CouponImportDryRunRequest,
  CouponImportDryRunQueryResponse,
  CouponImportDryRunResponse,
  CouponImportOperation,
  CouponImportOperationExport,
  CouponImportOperationFilters,
  CouponImportOperationQueryResponse,
  AdjustLoyaltyPointsRequest,
  CreateLoyaltyRewardRequest,
  CreateLoyaltyProgramRequest,
  CreateApplicationClientBindingRequest,
  CreateApplicationRequest,
  CreateCampaignRequest,
  CreateCouponDistributionRequest,
  CreateCouponRequest,
  GenerateCouponsRequest,
  GenerateCouponsResponse,
  IncentiveApplication,
  IncentiveReconciliationFilters,
  IncentiveReconciliationQueryResponse,
  LearnerLoyaltyRewardCatalogResponse,
  LoyaltyAccount,
  LoyaltyAccountFilters,
  LoyaltyAdjustmentApproval,
  LoyaltyAdjustmentApprovalFilters,
  LoyaltyAdjustmentApprovalQueryResponse,
  LoyaltyApprovalEvidencePack,
  LoyaltyBalanceBucketResponse,
  LoyaltyBenefitReconciliationFilters,
  LoyaltyBenefitReconciliationQueryResponse,
  LoyaltyClientBinding,
  LoyaltyFinanceCloseoutExport,
  LoyaltyFinanceCloseoutFilters,
  LoyaltyInboundDeadLetterActionRequest,
  LoyaltyInboundDeadLetterActionResponse,
  LoyaltyInboundDeadLetterApproval,
  LoyaltyInboundDeadLetterApprovalQueryResponse,
  LoyaltyInboundDeadLetterApprovalRequest,
  LoyaltyInboundDeadLetterApprovalReviewRequest,
  LoyaltyInboundDeadLetterDetail,
  LoyaltyInboundDeadLetterFilters,
  LoyaltyInboundDeadLetterQueryResponse,
  LoyaltyLedgerFilters,
  LoyaltyLedgerQueryResponse,
  LoyaltyExpiryDryRunRequest,
  LoyaltyExpiryDryRunResponse,
  LoyaltyExpiryExecutionRequest,
  LoyaltyExpiryExecutionResponse,
  CreateLoyaltyTierPolicyRequest,
  LoyaltyPointsMutationResponse,
  LoyaltyProgram,
  LoyaltyProgramFilters,
  LoyaltyReconciliationFilters,
  LoyaltyReconciliationQueryResponse,
  LoyaltyReward,
  LoyaltyRewardFilters,
  LoyaltyRewardRedemption,
  LoyaltyRewardRedemptionFilters,
  LoyaltyRewardRedemptionQueryResponse,
  LoyaltyTierFilters,
  LoyaltyTierPolicy,
  LoyaltyTierRecalculateResponse,
  LoyaltyTierStateQueryResponse,
  OutboxDeadLetterApproval,
  OutboxDeadLetterApprovalQueryResponse,
  OutboxDeadLetterApprovalRequest,
  OutboxDeadLetterApprovalReviewRequest,
  OutboxDeadLetterActionRequest,
  OutboxDeadLetterActionResponse,
  OutboxDeadLetterFilters,
  OutboxDeadLetterQueryResponse,
  PointLotBackfillRequest,
  PointLotBackfillResponse,
  PreviewCouponDistributionRequest,
  RedeemLoyaltyRewardRequest,
  RecalculateLoyaltyTiersRequest,
  RetryLoyaltyRewardFulfillmentRequest,
  RewardFulfillmentRunResponse,
  ReverseLoyaltyRewardRedemptionRequest,
  Reservation,
  ReservationFilters,
  ReviewLoyaltyAdjustmentApprovalRequest,
  Redemption,
  RedemptionFilters,
  RedemptionReversalApproval,
  RedemptionReversalApprovalDecisionRequest,
  RedemptionReversalApprovalFilters,
  RedemptionReversalApprovalRequest,
  ReviewQueueFilters,
  ReverseRedemptionRequest,
  RollbackCampaignVersionRequest,
  RetentionApproval,
  RetentionApprovalDecisionRequest,
  RetentionApprovalFilters,
  RetentionApprovalQueryResponse,
  RetentionApprovalRequest,
  RetentionDryRunRequest,
  RetentionDryRunResponse,
  RetentionEvidencePack,
  RetentionEvidencePackExport,
  RetentionExecutionRequest,
  RetentionExecutionResponse,
  RetentionPolicyRegistry,
  RetentionRestoreDrill,
  RetentionRestoreDrillRequest,
  SubmittedCampaignVersion,
  SubmitLoyaltyAdjustmentApprovalRequest,
  SubmitLoyaltyExpiryApprovalRequest,
  SubmitLoyaltyRewardFulfillmentApprovalRequest,
  UpdateApplicationStatusRequest,
  UpdateCampaignVersionDraftRequest,
  UpdateCouponStatusRequest,
  UpdateLoyaltyProgramRequest,
  UpdateLoyaltyAccountStatusRequest,
  UpdateLoyaltyTierPolicyRequest,
  UpdateLoyaltyTierPolicyStatusRequest,
  UpdateLoyaltyRewardFulfillmentRequest,
  UpdateLoyaltyProgramStatusRequest,
  UpdateLoyaltyRewardRequest,
  UpdateLoyaltyRewardStatusRequest,
  UpsertLoyaltyClientBindingRequest
} from "./types";

const basePath = "/admin/v1/incentives";
const loyaltyBasePath = "/admin/v1/loyalty";
const outboxBasePath = "/admin/v1/outbox";

function cleanParams<T extends Record<string, unknown>>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== "")
  ) as Partial<T>;
}

function randomId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

export function retentionOperationId(prefix: string) {
  return `${prefix}-${randomId()}`;
}

function correlationHeaders(prefix: string, correlationId?: string) {
  return { "X-Correlation-Id": correlationId?.trim() || retentionOperationId(prefix) };
}

function appendOptional(form: FormData, key: string, value: unknown) {
  if (value === undefined || value === null || value === "") return;
  form.append(key, String(value));
}

function appendCouponImportFields(
  form: FormData,
  input: Pick<
    CouponImportApprovalRequest,
    | "campaignId"
    | "file"
    | "maxRows"
    | "holderProfileId"
    | "startsAt"
    | "expiresAt"
    | "maxRedemptions"
    | "maxRedemptionsPerProfile"
  >
) {
  appendOptional(form, "campaignId", input.campaignId);
  appendOptional(form, "maxRows", input.maxRows);
  appendOptional(form, "holderProfileId", input.holderProfileId);
  appendOptional(form, "startsAt", input.startsAt);
  appendOptional(form, "expiresAt", input.expiresAt);
  appendOptional(form, "maxRedemptions", input.maxRedemptions);
  appendOptional(form, "maxRedemptionsPerProfile", input.maxRedemptionsPerProfile);
  form.append("file", input.file);
}

export async function listApplications(filters: ApplicationFilters = {}): Promise<IncentiveApplication[]> {
  const { data } = await apiClient.get(`${basePath}/applications`, { params: cleanParams(filters) });
  return unwrapList<IncentiveApplication>(data);
}

export async function createApplication(input: CreateApplicationRequest): Promise<IncentiveApplication> {
  const { data } = await apiClient.post(`${basePath}/applications`, input);
  return unwrap<IncentiveApplication>(data);
}

export async function updateApplicationStatus(
  applicationUuid: string,
  input: UpdateApplicationStatusRequest
): Promise<IncentiveApplication> {
  const { data } = await apiClient.patch(`${basePath}/applications/${applicationUuid}/status`, input);
  return unwrap<IncentiveApplication>(data);
}

export async function upsertApplicationClientBinding(
  applicationUuid: string,
  input: CreateApplicationClientBindingRequest
): Promise<ApplicationClientBinding> {
  const { data } = await apiClient.post(`${basePath}/applications/${applicationUuid}/client-bindings`, input);
  return unwrap<ApplicationClientBinding>(data);
}

export async function listCampaigns(filters: CampaignFilters = {}): Promise<Campaign[]> {
  const { data } = await apiClient.get(`${basePath}/campaigns`, { params: cleanParams(filters) });
  return unwrapList<Campaign>(data);
}

export async function getCampaign(campaignId: string): Promise<Campaign> {
  const { data } = await apiClient.get(`${basePath}/campaigns/${campaignId}`);
  return unwrap<Campaign>(data);
}

export async function createCampaign(input: CreateCampaignRequest): Promise<Campaign> {
  const { data } = await apiClient.post(`${basePath}/campaigns`, input);
  return unwrap<Campaign>(data);
}

export async function listCampaignVersions(campaignId: string): Promise<CampaignVersion[]> {
  const { data } = await apiClient.get(`${basePath}/campaigns/${campaignId}/versions`);
  return unwrapList<CampaignVersion>(data);
}

export async function createCampaignVersion(campaignId: string): Promise<CampaignVersion> {
  const { data } = await apiClient.post(`${basePath}/campaigns/${campaignId}/versions`, {});
  return unwrap<CampaignVersion>(data);
}

export async function getCampaignVersion(campaignId: string, versionNumber: number): Promise<CampaignVersionDetail> {
  const { data } = await apiClient.get(`${basePath}/campaigns/${campaignId}/versions/${versionNumber}`);
  return unwrap<CampaignVersionDetail>(data);
}

export async function updateCampaignVersionDraft(
  campaignId: string,
  versionNumber: number,
  input: UpdateCampaignVersionDraftRequest
): Promise<CampaignVersionDetail> {
  const { data } = await apiClient.patch(`${basePath}/campaigns/${campaignId}/versions/${versionNumber}/draft`, input);
  return unwrap<CampaignVersionDetail>(data);
}

export async function getCampaignVersionValidation(
  campaignId: string,
  versionNumber: number
): Promise<CampaignVersionValidation> {
  const { data } = await apiClient.get(`${basePath}/campaigns/${campaignId}/versions/${versionNumber}/validation`);
  return unwrap<CampaignVersionValidation>(data);
}

export async function getCampaignVersionDiff(
  campaignId: string,
  leftVersion: number,
  rightVersion: number
): Promise<CampaignVersionDiff> {
  const { data } = await apiClient.get(`${basePath}/campaigns/${campaignId}/versions/${leftVersion}/diff`, {
    params: { rightVersion }
  });
  return unwrap<CampaignVersionDiff>(data);
}

export async function rollbackCampaignVersion(
  campaignId: string,
  versionNumber: number,
  input: RollbackCampaignVersionRequest = {}
): Promise<CampaignVersionDetail> {
  const { data } = await apiClient.post(`${basePath}/campaigns/${campaignId}/versions/${versionNumber}/rollback`, input);
  return unwrap<CampaignVersionDetail>(data);
}

async function transitionCampaignVersion(
  campaignId: string,
  versionNumber: number,
  action: "submit" | "approve" | "reject" | "publish",
  input: CampaignVersionTransitionRequest = {}
): Promise<CampaignVersion> {
  const { data } = await apiClient.post(`${basePath}/campaigns/${campaignId}/versions/${versionNumber}/${action}`, input);
  return unwrap<CampaignVersion>(data);
}

export function submitCampaignVersion(
  campaignId: string,
  versionNumber: number,
  input?: CampaignVersionTransitionRequest
) {
  return transitionCampaignVersion(campaignId, versionNumber, "submit", input);
}

export function approveCampaignVersion(
  campaignId: string,
  versionNumber: number,
  input?: CampaignVersionTransitionRequest
) {
  return transitionCampaignVersion(campaignId, versionNumber, "approve", input);
}

export function rejectCampaignVersion(
  campaignId: string,
  versionNumber: number,
  input?: CampaignVersionTransitionRequest
) {
  return transitionCampaignVersion(campaignId, versionNumber, "reject", input);
}

export function publishCampaignVersion(
  campaignId: string,
  versionNumber: number,
  input?: CampaignVersionTransitionRequest
) {
  return transitionCampaignVersion(campaignId, versionNumber, "publish", input);
}

export async function previewIncentives(
  input: AdminPreviewIncentivesRequest,
  correlationId?: string
): Promise<AdminPreviewIncentivesResponse> {
  const { data } = await apiClient.post(`${basePath}/admin/preview`, input, {
    headers: correlationHeaders("admin-incentive-simulation", correlationId)
  });
  return unwrap<AdminPreviewIncentivesResponse>(data);
}

export async function createCoupon(input: CreateCouponRequest): Promise<Coupon> {
  const { data } = await apiClient.post(`${basePath}/coupons`, input);
  return unwrap<Coupon>(data);
}

export async function listCoupons(filters: CouponFilters = {}): Promise<Coupon[]> {
  const { data } = await apiClient.get(`${basePath}/coupons`, { params: cleanParams(filters) });
  return unwrapList<Coupon>(data);
}

export async function couponStorageInventory(
  filters: Pick<CouponFilters, "tenantId" | "applicationId" | "campaignId"> & { activeOnly?: boolean } = {}
): Promise<CouponStorageInventory> {
  const { data } = await apiClient.get(`${basePath}/coupons/storage-inventory`, {
    params: cleanParams(filters)
  });
  return unwrap<CouponStorageInventory>(data);
}

export async function getCoupon(couponId: string): Promise<Coupon> {
  const { data } = await apiClient.get(`${basePath}/coupons/${couponId}`);
  return unwrap<Coupon>(data);
}

export async function updateCouponStatus(couponId: string, input: UpdateCouponStatusRequest): Promise<Coupon> {
  const { data } = await apiClient.patch(`${basePath}/coupons/${couponId}/status`, input);
  return unwrap<Coupon>(data);
}

export async function generateCoupons(input: GenerateCouponsRequest): Promise<GenerateCouponsResponse> {
  const { data } = await apiClient.post(`${basePath}/coupons:generate`, input);
  return unwrap<GenerateCouponsResponse>(data);
}

export async function previewCouponDistribution(
  input: PreviewCouponDistributionRequest,
  correlationId?: string
): Promise<CouponDistributionPreviewResponse> {
  const { data } = await apiClient.post(`${basePath}/coupon-distributions:preview`, input, {
    headers: correlationHeaders("admin-coupon-distribution-preview", correlationId)
  });
  return unwrap<CouponDistributionPreviewResponse>(data);
}

export async function createCouponDistribution(
  input: CreateCouponDistributionRequest,
  correlationId?: string
): Promise<CouponDistribution> {
  const { data } = await apiClient.post(`${basePath}/coupon-distributions`, input, {
    headers: correlationHeaders("admin-coupon-distribution-create", correlationId)
  });
  return unwrap<CouponDistribution>(data);
}

export async function listCouponDistributions(
  filters: CouponDistributionFilters = {}
): Promise<CouponDistributionQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/coupon-distributions`, { params: cleanParams(filters) });
  return unwrap<CouponDistributionQueryResponse>(data);
}

export async function approveCouponDistribution(
  distributionId: string,
  input: CouponDistributionActionRequest = {},
  correlationId?: string
): Promise<CouponDistribution> {
  const { data } = await apiClient.post(`${basePath}/coupon-distributions/${distributionId}:approve`, input, {
    headers: correlationHeaders("admin-coupon-distribution-approve", correlationId)
  });
  return unwrap<CouponDistribution>(data);
}

export async function issueCouponDistribution(
  distributionId: string,
  input: CouponDistributionActionRequest = {},
  correlationId?: string
): Promise<CouponDistribution> {
  const { data } = await apiClient.post(`${basePath}/coupon-distributions/${distributionId}:issue`, input, {
    headers: correlationHeaders("admin-coupon-distribution-issue", correlationId)
  });
  return unwrap<CouponDistribution>(data);
}

export async function revokeCouponDistribution(
  distributionId: string,
  input: CouponDistributionActionRequest = {},
  correlationId?: string
): Promise<CouponDistribution> {
  const { data } = await apiClient.post(`${basePath}/coupon-distributions/${distributionId}:revoke`, input, {
    headers: correlationHeaders("admin-coupon-distribution-revoke", correlationId)
  });
  return unwrap<CouponDistribution>(data);
}

export async function runCouponImportDryRun(
  input: CouponImportDryRunRequest,
  correlationId?: string
): Promise<CouponImportDryRunResponse> {
  const form = new FormData();
  appendCouponImportFields(form, input);
  appendOptional(form, "idempotencyKey", input.idempotencyKey);
  const headers = {
    ...correlationHeaders("admin-coupon-import-dry-run", correlationId),
    ...(input.idempotencyKey?.trim() ? { "Idempotency-Key": input.idempotencyKey.trim() } : {})
  };
  const { data } = await apiClient.post(`${basePath}/coupons:import-dry-run`, form, { headers });
  return unwrap<CouponImportDryRunResponse>(data);
}

export async function getCouponImportDryRun(dryRunId: string): Promise<CouponImportDryRunResponse> {
  const { data } = await apiClient.get(`${basePath}/coupons/import-dry-runs/${dryRunId}`);
  return unwrap<CouponImportDryRunResponse>(data);
}

export async function listCouponImportDryRuns(
  filters: CouponImportDryRunHistoryFilters
): Promise<CouponImportDryRunQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/coupons/import-dry-runs`, {
    params: cleanParams(filters)
  });
  return unwrap<CouponImportDryRunQueryResponse>(data);
}

export async function listCouponImportApprovals(
  filters: CouponImportApprovalFilters
): Promise<CouponImportApproval[]> {
  const { data } = await apiClient.get(`${basePath}/coupons/import-approvals`, {
    params: cleanParams(filters)
  });
  return unwrapList<CouponImportApproval>(data);
}

export async function getCouponImportApproval(approvalId: string): Promise<CouponImportApproval> {
  const { data } = await apiClient.get(`${basePath}/coupons/import-approvals/${approvalId}`);
  return unwrap<CouponImportApproval>(data);
}

export async function listCouponImportOperations(
  filters: CouponImportOperationFilters
): Promise<CouponImportOperationQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/coupons/import-operations`, {
    params: cleanParams(filters)
  });
  return unwrap<CouponImportOperationQueryResponse>(data);
}

export async function getCouponImportOperation(importId: string): Promise<CouponImportOperation> {
  const { data } = await apiClient.get(`${basePath}/coupons/import-operations/${importId}`);
  return unwrap<CouponImportOperation>(data);
}

export async function exportCouponImportOperation(
  importId: string,
  correlationId?: string
): Promise<CouponImportOperationExport> {
  const { data } = await apiClient.get(`${basePath}/coupons/import-operations/${importId}/export`, {
    headers: correlationHeaders("admin-coupon-import-operation-export", correlationId)
  });
  return unwrap<CouponImportOperationExport>(data);
}

export async function requestCouponImportApproval(
  input: CouponImportApprovalRequest,
  correlationId?: string
): Promise<CouponImportApproval> {
  const form = new FormData();
  appendCouponImportFields(form, input);
  appendOptional(form, "approvedResultHash", input.approvedResultHash);
  appendOptional(form, "reason", input.reason);
  appendOptional(form, "changeTicket", input.changeTicket);
  const { data } = await apiClient.post(`${basePath}/coupons/import-dry-runs/${input.dryRunId}/approvals`, form, {
    headers: correlationHeaders("admin-coupon-import-approval", correlationId)
  });
  return unwrap<CouponImportApproval>(data);
}

export async function approveCouponImportApproval(
  approvalId: string,
  input: CouponImportApprovalDecisionRequest = {},
  correlationId?: string
): Promise<CouponImportApproval> {
  const { data } = await apiClient.post(`${basePath}/coupons/import-approvals/${approvalId}:approve`, input, {
    headers: correlationHeaders("admin-coupon-import-approve", correlationId)
  });
  return unwrap<CouponImportApproval>(data);
}

export async function rejectCouponImportApproval(
  approvalId: string,
  input: CouponImportApprovalDecisionRequest = {},
  correlationId?: string
): Promise<CouponImportApproval> {
  const { data } = await apiClient.post(`${basePath}/coupons/import-approvals/${approvalId}:reject`, input, {
    headers: correlationHeaders("admin-coupon-import-reject", correlationId)
  });
  return unwrap<CouponImportApproval>(data);
}

export async function commitCouponImportApproval(
  input: CouponImportCommitRequest,
  correlationId?: string
): Promise<CouponImportCommitResponse> {
  const form = new FormData();
  appendCouponImportFields(form, input);
  appendOptional(form, "dryRunId", input.dryRunId);
  appendOptional(form, "approvedResultHash", input.approvedResultHash);
  appendOptional(form, "reason", input.reason);
  appendOptional(form, "changeTicket", input.changeTicket);
  appendOptional(form, "idempotencyKey", input.idempotencyKey);
  appendOptional(form, "confirm", input.confirm);
  const headers = {
    ...correlationHeaders("admin-coupon-import-commit", correlationId),
    "Idempotency-Key": input.idempotencyKey.trim()
  };
  const { data } = await apiClient.post(`${basePath}/coupons/import-approvals/${input.approvalId}:commit`, form, {
    headers
  });
  return unwrap<CouponImportCommitResponse>(data);
}

export async function listRedemptions(filters: RedemptionFilters = {}): Promise<Redemption[]> {
  const { data } = await apiClient.get(`${basePath}/redemptions`, { params: cleanParams(filters) });
  return unwrapList<Redemption>(data);
}

export async function listReservations(filters: ReservationFilters = {}): Promise<Reservation[]> {
  const { data } = await apiClient.get(`${basePath}/reservations`, { params: cleanParams(filters) });
  return unwrapList<Reservation>(data);
}

export async function getReservation(reservationId: string): Promise<Reservation> {
  const { data } = await apiClient.get(`${basePath}/reservations/${reservationId}`);
  return unwrap<Reservation>(data);
}

export async function getRedemption(redemptionId: string): Promise<Redemption> {
  const { data } = await apiClient.get(`${basePath}/redemptions/${redemptionId}`);
  return unwrap<Redemption>(data);
}

export async function submitRedemptionReversalApproval(
  redemptionId: string,
  input: RedemptionReversalApprovalRequest,
  correlationId?: string
): Promise<RedemptionReversalApproval> {
  const { data } = await apiClient.post(`${basePath}/redemptions/${redemptionId}/reversal-approvals`, input, {
    headers: correlationHeaders("admin-redemption-reversal-approval", correlationId)
  });
  return unwrap<RedemptionReversalApproval>(data);
}

export async function listRedemptionReversalApprovals(
  filters: RedemptionReversalApprovalFilters = {}
): Promise<RedemptionReversalApproval[]> {
  const { data } = await apiClient.get(`${basePath}/redemptions/reversal-approvals`, {
    params: cleanParams(filters)
  });
  return unwrapList<RedemptionReversalApproval>(data);
}

export async function approveRedemptionReversalApproval(
  approvalId: string,
  input: RedemptionReversalApprovalDecisionRequest = {},
  correlationId?: string
): Promise<RedemptionReversalApproval> {
  const { data } = await apiClient.post(`${basePath}/redemptions/reversal-approvals/${approvalId}:approve`, input, {
    headers: correlationHeaders("admin-redemption-reversal-approve", correlationId)
  });
  return unwrap<RedemptionReversalApproval>(data);
}

export async function rejectRedemptionReversalApproval(
  approvalId: string,
  input: RedemptionReversalApprovalDecisionRequest = {},
  correlationId?: string
): Promise<RedemptionReversalApproval> {
  const { data } = await apiClient.post(`${basePath}/redemptions/reversal-approvals/${approvalId}:reject`, input, {
    headers: correlationHeaders("admin-redemption-reversal-reject", correlationId)
  });
  return unwrap<RedemptionReversalApproval>(data);
}

export async function queryReconciliation(
  filters: IncentiveReconciliationFilters = {}
): Promise<IncentiveReconciliationQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/reconciliation/entries`, { params: cleanParams(filters) });
  return unwrap<IncentiveReconciliationQueryResponse>(data);
}

export async function reverseRedemption(
  redemptionId: string,
  input: ReverseRedemptionRequest
): Promise<{ reversed: boolean; redemptionId: string; status: string; idempotencyReplay: boolean }> {
  const { data } = await apiClient.post(`${basePath}/redemptions/${redemptionId}/reverse`, input, {
    headers: {
      ...correlationHeaders("admin-redemption-reversal-execute"),
      "Idempotency-Key": input.idempotencyKey
    }
  });
  return unwrap(data);
}

export async function queryAudit(filters: AuditFilters = {}): Promise<AuditQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/audit`, { params: cleanParams(filters) });
  return unwrap<AuditQueryResponse>(data);
}

export async function campaignTimeline(campaignId: string, limit = 25): Promise<AuditQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/campaigns/${campaignId}/timeline`, { params: { limit } });
  return unwrap<AuditQueryResponse>(data);
}

export async function applicationTimeline(applicationUuid: string, limit = 25): Promise<AuditQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/applications/${applicationUuid}/timeline`, { params: { limit } });
  return unwrap<AuditQueryResponse>(data);
}

export async function redemptionTimeline(redemptionId: string, limit = 25): Promise<AuditQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/redemptions/${redemptionId}/timeline`, { params: { limit } });
  return unwrap<AuditQueryResponse>(data);
}

export async function listLoyaltyPrograms(filters: LoyaltyProgramFilters = {}): Promise<LoyaltyProgram[]> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/programs`, { params: cleanParams(filters) });
  return unwrapList<LoyaltyProgram>(data);
}

export async function getLoyaltyProgram(programId: string): Promise<LoyaltyProgram> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/programs/${programId}`);
  return unwrap<LoyaltyProgram>(data);
}

export async function createLoyaltyProgram(input: CreateLoyaltyProgramRequest): Promise<LoyaltyProgram> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/programs`, input);
  return unwrap<LoyaltyProgram>(data);
}

export async function updateLoyaltyProgram(
  programId: string,
  input: UpdateLoyaltyProgramRequest,
  correlationId?: string
): Promise<LoyaltyProgram> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/programs/${programId}`, input, {
    headers: correlationHeaders("loyalty-program-update", correlationId)
  });
  return unwrap<LoyaltyProgram>(data);
}

export async function updateLoyaltyProgramStatus(
  programId: string,
  input: UpdateLoyaltyProgramStatusRequest,
  correlationId?: string
): Promise<LoyaltyProgram> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/programs/${programId}/status`, input, {
    headers: correlationHeaders("loyalty-program-status", correlationId)
  });
  return unwrap<LoyaltyProgram>(data);
}

export async function listLoyaltyTierPolicies(filters: LoyaltyTierFilters = {}): Promise<LoyaltyTierPolicy[]> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/tier-policies`, { params: cleanParams(filters) });
  return unwrapList<LoyaltyTierPolicy>(data);
}

export async function createLoyaltyTierPolicy(input: CreateLoyaltyTierPolicyRequest): Promise<LoyaltyTierPolicy> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/tier-policies`, input);
  return unwrap<LoyaltyTierPolicy>(data);
}

export async function updateLoyaltyTierPolicy(
  policyId: string,
  input: UpdateLoyaltyTierPolicyRequest,
  correlationId?: string
): Promise<LoyaltyTierPolicy> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/tier-policies/${policyId}`, input, {
    headers: correlationHeaders("loyalty-tier-policy-update", correlationId)
  });
  return unwrap<LoyaltyTierPolicy>(data);
}

export async function updateLoyaltyTierPolicyStatus(
  policyId: string,
  input: UpdateLoyaltyTierPolicyStatusRequest,
  correlationId?: string
): Promise<LoyaltyTierPolicy> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/tier-policies/${policyId}/status`, input, {
    headers: correlationHeaders("loyalty-tier-policy-status", correlationId)
  });
  return unwrap<LoyaltyTierPolicy>(data);
}

export async function queryLoyaltyTierStates(filters: LoyaltyTierFilters = {}): Promise<LoyaltyTierStateQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/tier-states`, { params: cleanParams(filters) });
  return unwrap<LoyaltyTierStateQueryResponse>(data);
}

export async function recalculateLoyaltyTiers(
  input: RecalculateLoyaltyTiersRequest
): Promise<LoyaltyTierRecalculateResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/tier-states:recalculate`, input, {
    headers: correlationHeaders("loyalty-tier-recalculate", input.correlationId)
  });
  return unwrap<LoyaltyTierRecalculateResponse>(data);
}

export async function upsertLoyaltyClientBinding(
  programId: string,
  input: UpsertLoyaltyClientBindingRequest,
  correlationId?: string
): Promise<LoyaltyClientBinding> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/programs/${programId}/client-bindings`, input, {
    headers: correlationHeaders("loyalty-client-binding", correlationId)
  });
  return unwrap<LoyaltyClientBinding>(data);
}

export async function listLoyaltyAccounts(filters: LoyaltyAccountFilters = {}): Promise<LoyaltyAccount[]> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/accounts:search`, { params: cleanParams(filters) });
  return unwrapList<LoyaltyAccount>(data);
}

export async function updateLoyaltyAccountStatus(
  accountId: string,
  input: UpdateLoyaltyAccountStatusRequest,
  correlationId?: string
): Promise<LoyaltyAccount> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/accounts/${accountId}/status`, input, {
    headers: correlationHeaders("loyalty-account-status", correlationId)
  });
  return unwrap<LoyaltyAccount>(data);
}

export async function queryLoyaltyLedger(filters: LoyaltyLedgerFilters = {}): Promise<LoyaltyLedgerQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/ledger`, { params: cleanParams(filters) });
  return unwrap<LoyaltyLedgerQueryResponse>(data);
}

export async function queryLoyaltyBalanceBuckets(
  accountId: string,
  asOf?: string
): Promise<LoyaltyBalanceBucketResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/accounts/${accountId}/balance-buckets`, {
    params: cleanParams({ asOf })
  });
  return unwrap<LoyaltyBalanceBucketResponse>(data);
}

export async function adjustLoyaltyPoints(input: AdjustLoyaltyPointsRequest): Promise<LoyaltyPointsMutationResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/points:adjust`, input, {
    headers: correlationHeaders("loyalty-points-adjust", input.correlationId)
  });
  return unwrap<LoyaltyPointsMutationResponse>(data);
}

export async function runLoyaltyExpiryDryRun(input: LoyaltyExpiryDryRunRequest): Promise<LoyaltyExpiryDryRunResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/points:expire-dry-run`, input);
  return unwrap<LoyaltyExpiryDryRunResponse>(data);
}

export async function executeLoyaltyExpiry(
  input: LoyaltyExpiryExecutionRequest
): Promise<LoyaltyExpiryExecutionResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/points:expire`, input, {
    headers: correlationHeaders("loyalty-expiry-execute", input.correlationId)
  });
  return unwrap<LoyaltyExpiryExecutionResponse>(data);
}

export async function submitLoyaltyExpiryApproval(
  input: SubmitLoyaltyExpiryApprovalRequest
): Promise<LoyaltyAdjustmentApproval> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/expiry-approvals`, input, {
    headers: correlationHeaders("loyalty-expiry-approval", input.correlationId)
  });
  return unwrap<LoyaltyAdjustmentApproval>(data);
}

export async function backfillLoyaltyPointLots(input: PointLotBackfillRequest): Promise<PointLotBackfillResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/point-lots:backfill`, input, {
    headers: correlationHeaders("loyalty-point-lot-backfill", input.correlationId)
  });
  return unwrap<PointLotBackfillResponse>(data);
}

export async function listLoyaltyAdjustmentApprovals(
  filters: LoyaltyAdjustmentApprovalFilters = {}
): Promise<LoyaltyAdjustmentApprovalQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/adjustment-approvals`, {
    params: cleanParams(filters)
  });
  return unwrap<LoyaltyAdjustmentApprovalQueryResponse>(data);
}

export async function submitLoyaltyAdjustmentApproval(
  input: SubmitLoyaltyAdjustmentApprovalRequest
): Promise<LoyaltyAdjustmentApproval> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/adjustment-approvals`, input, {
    headers: correlationHeaders("loyalty-adjustment-approval", input.correlationId)
  });
  return unwrap<LoyaltyAdjustmentApproval>(data);
}

export async function approveLoyaltyAdjustmentApproval(
  approvalId: string,
  input: ReviewLoyaltyAdjustmentApprovalRequest
): Promise<LoyaltyAdjustmentApproval> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/adjustment-approvals/${approvalId}:approve`, input);
  return unwrap<LoyaltyAdjustmentApproval>(data);
}

export async function rejectLoyaltyAdjustmentApproval(
  approvalId: string,
  input: ReviewLoyaltyAdjustmentApprovalRequest
): Promise<LoyaltyAdjustmentApproval> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/adjustment-approvals/${approvalId}:reject`, input);
  return unwrap<LoyaltyAdjustmentApproval>(data);
}

export async function getLoyaltyApprovalEvidencePack(approvalId: string): Promise<LoyaltyApprovalEvidencePack> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/approvals/${approvalId}/evidence-pack`);
  return unwrap<LoyaltyApprovalEvidencePack>(data);
}

export async function queryLoyaltyReconciliation(
  filters: LoyaltyReconciliationFilters = {}
): Promise<LoyaltyReconciliationQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/reconciliation/entries`, {
    params: cleanParams(filters)
  });
  return unwrap<LoyaltyReconciliationQueryResponse>(data);
}

export async function queryLoyaltyBenefitReconciliation(
  filters: LoyaltyBenefitReconciliationFilters = {}
): Promise<LoyaltyBenefitReconciliationQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/benefit-reconciliation/entries`, {
    params: cleanParams(filters)
  });
  return unwrap<LoyaltyBenefitReconciliationQueryResponse>(data);
}

export async function queryLoyaltyFinanceCloseout(
  filters: LoyaltyFinanceCloseoutFilters = {}
): Promise<LoyaltyFinanceCloseoutExport> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/finance/closeout`, {
    params: cleanParams(filters)
  });
  return unwrap<LoyaltyFinanceCloseoutExport>(data);
}

export async function listLoyaltyRewards(filters: LoyaltyRewardFilters = {}): Promise<LoyaltyReward[]> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/rewards`, {
    params: cleanParams(filters)
  });
  return unwrapList<LoyaltyReward>(data);
}

export async function getLoyaltyReward(rewardId: string): Promise<LoyaltyReward> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/rewards/${rewardId}`);
  return unwrap<LoyaltyReward>(data);
}

export async function createLoyaltyReward(input: CreateLoyaltyRewardRequest): Promise<LoyaltyReward> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/rewards`, input);
  return unwrap<LoyaltyReward>(data);
}

export async function updateLoyaltyReward(
  rewardId: string,
  input: UpdateLoyaltyRewardRequest
): Promise<LoyaltyReward> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/rewards/${rewardId}`, input);
  return unwrap<LoyaltyReward>(data);
}

export async function updateLoyaltyRewardStatus(
  rewardId: string,
  input: UpdateLoyaltyRewardStatusRequest,
  correlationId?: string
): Promise<LoyaltyReward> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/rewards/${rewardId}/status`, input, {
    headers: correlationHeaders("loyalty-reward-status", correlationId)
  });
  return unwrap<LoyaltyReward>(data);
}

export async function queryLoyaltyRewardRedemptions(
  filters: LoyaltyRewardRedemptionFilters = {}
): Promise<LoyaltyRewardRedemptionQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/reward-redemptions`, {
    params: cleanParams(filters)
  });
  return unwrap<LoyaltyRewardRedemptionQueryResponse>(data);
}

export async function getLoyaltyRewardRedemption(redemptionId: string): Promise<LoyaltyRewardRedemption> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/reward-redemptions/${redemptionId}`);
  return unwrap<LoyaltyRewardRedemption>(data);
}

export async function reverseLoyaltyRewardRedemption(
  redemptionId: string,
  input: ReverseLoyaltyRewardRedemptionRequest
): Promise<LoyaltyRewardRedemption> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/reward-redemptions/${redemptionId}:reverse`, input);
  return unwrap<LoyaltyRewardRedemption>(data);
}

export async function updateLoyaltyRewardFulfillment(
  redemptionId: string,
  input: UpdateLoyaltyRewardFulfillmentRequest
): Promise<LoyaltyRewardRedemption> {
  const { data } = await apiClient.patch(`${loyaltyBasePath}/reward-redemptions/${redemptionId}/fulfillment`, input, {
    headers: correlationHeaders("loyalty-reward-fulfillment-execute", input.correlationId)
  });
  return unwrap<LoyaltyRewardRedemption>(data);
}

export async function submitLoyaltyRewardFulfillmentApproval(
  redemptionId: string,
  input: SubmitLoyaltyRewardFulfillmentApprovalRequest
): Promise<LoyaltyAdjustmentApproval> {
  const { data } = await apiClient.post(
    `${loyaltyBasePath}/reward-redemptions/${redemptionId}/fulfillment-approvals`,
    input,
    { headers: correlationHeaders("loyalty-reward-fulfillment-approval", input.correlationId) }
  );
  return unwrap<LoyaltyAdjustmentApproval>(data);
}

export async function retryLoyaltyRewardFulfillment(
  redemptionId: string,
  input: RetryLoyaltyRewardFulfillmentRequest = {}
): Promise<LoyaltyRewardRedemption> {
  const { data } = await apiClient.post(
    `${loyaltyBasePath}/reward-redemptions/${redemptionId}/fulfillment:retry`,
    input
  );
  return unwrap<LoyaltyRewardRedemption>(data);
}

export async function runDueLoyaltyRewardFulfillments(limit = 50): Promise<RewardFulfillmentRunResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/reward-fulfillment:run-due`, undefined, {
    params: cleanParams({ limit })
  });
  return unwrap<RewardFulfillmentRunResponse>(data);
}

export async function queryLearnerLoyaltyRewards(
  filters: Pick<LoyaltyRewardFilters, "tenantId" | "applicationId" | "programId"> = {}
): Promise<LearnerLoyaltyRewardCatalogResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/me/rewards`, {
    params: cleanParams(filters)
  });
  return unwrap<LearnerLoyaltyRewardCatalogResponse>(data);
}

export async function redeemLoyaltyReward(
  rewardId: string,
  input: RedeemLoyaltyRewardRequest
): Promise<LoyaltyRewardRedemption> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/me/rewards/${rewardId}:redeem`, input);
  return unwrap<LoyaltyRewardRedemption>(data);
}

export async function queryLoyaltyDeadLetters(
  filters: LoyaltyInboundDeadLetterFilters = {}
): Promise<LoyaltyInboundDeadLetterQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/dead-letters`, {
    params: cleanParams(filters)
  });
  return unwrap<LoyaltyInboundDeadLetterQueryResponse>(data);
}

export async function getLoyaltyDeadLetter(deadLetterId: string): Promise<LoyaltyInboundDeadLetterDetail> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/dead-letters/${deadLetterId}`);
  return unwrap<LoyaltyInboundDeadLetterDetail>(data);
}

export async function queryLoyaltyDeadLetterApprovals(
  deadLetterId: string,
  filters: { status?: string; limit?: number } = {}
): Promise<LoyaltyInboundDeadLetterApprovalQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/dead-letters/${deadLetterId}/approvals`, {
    params: cleanParams(filters)
  });
  return unwrap<LoyaltyInboundDeadLetterApprovalQueryResponse>(data);
}

export async function requestLoyaltyDeadLetterApproval(
  deadLetterId: string,
  input: LoyaltyInboundDeadLetterApprovalRequest
): Promise<LoyaltyInboundDeadLetterApproval> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/dead-letters/${deadLetterId}/approvals`, input);
  return unwrap<LoyaltyInboundDeadLetterApproval>(data);
}

export async function approveLoyaltyDeadLetterApproval(
  approvalId: string,
  input: LoyaltyInboundDeadLetterApprovalReviewRequest
): Promise<LoyaltyInboundDeadLetterApproval> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/dead-letters/approvals/${approvalId}:approve`, input);
  return unwrap<LoyaltyInboundDeadLetterApproval>(data);
}

export async function rejectLoyaltyDeadLetterApproval(
  approvalId: string,
  input: LoyaltyInboundDeadLetterApprovalReviewRequest
): Promise<LoyaltyInboundDeadLetterApproval> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/dead-letters/approvals/${approvalId}:reject`, input);
  return unwrap<LoyaltyInboundDeadLetterApproval>(data);
}

export async function replayLoyaltyDeadLetter(
  deadLetterId: string,
  input: LoyaltyInboundDeadLetterActionRequest
): Promise<LoyaltyInboundDeadLetterActionResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/dead-letters/${deadLetterId}:replay`, input);
  return unwrap<LoyaltyInboundDeadLetterActionResponse>(data);
}

export async function discardLoyaltyDeadLetter(
  deadLetterId: string,
  input: LoyaltyInboundDeadLetterActionRequest
): Promise<LoyaltyInboundDeadLetterActionResponse> {
  const { data } = await apiClient.post(`${loyaltyBasePath}/dead-letters/${deadLetterId}:discard`, input);
  return unwrap<LoyaltyInboundDeadLetterActionResponse>(data);
}

export async function queryLoyaltyAudit(filters: AuditFilters = {}): Promise<AuditQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/audit`, { params: cleanParams(filters) });
  return unwrap<AuditQueryResponse>(data);
}

export async function queryOutboxDeadLetters(
  filters: OutboxDeadLetterFilters = {}
): Promise<OutboxDeadLetterQueryResponse> {
  const { data } = await apiClient.get(`${outboxBasePath}/dead-letters`, {
    params: cleanParams(filters)
  });
  return unwrap<OutboxDeadLetterQueryResponse>(data);
}

function outboxDeadLetterActionBody(input: OutboxDeadLetterActionRequest) {
  return {
    idempotencyKey: input.idempotencyKey,
    reason: input.reason,
    dryRun: input.dryRun,
    approvalId: input.approvalId
  };
}

export async function queryOutboxDeadLetterApprovals(
  deadLetterId: string,
  filters: { status?: string; limit?: number } = {}
): Promise<OutboxDeadLetterApprovalQueryResponse> {
  const { data } = await apiClient.get(`${outboxBasePath}/dead-letters/${deadLetterId}/approvals`, {
    params: cleanParams(filters)
  });
  return unwrap<OutboxDeadLetterApprovalQueryResponse>(data);
}

export async function requestOutboxDeadLetterApproval(
  deadLetterId: string,
  input: OutboxDeadLetterApprovalRequest
): Promise<OutboxDeadLetterApproval> {
  const { data } = await apiClient.post(
    `${outboxBasePath}/dead-letters/${deadLetterId}/approvals`,
    {
      action: input.action,
      reason: input.reason,
      evidenceReference: input.evidenceReference
    },
    { headers: correlationHeaders("outbox-dlt-approval", input.correlationId) }
  );
  return unwrap<OutboxDeadLetterApproval>(data);
}

export async function approveOutboxDeadLetterApproval(
  approvalId: string,
  input: OutboxDeadLetterApprovalReviewRequest
): Promise<OutboxDeadLetterApproval> {
  const { data } = await apiClient.post(`${outboxBasePath}/dead-letters/approvals/${approvalId}:approve`, input);
  return unwrap<OutboxDeadLetterApproval>(data);
}

export async function rejectOutboxDeadLetterApproval(
  approvalId: string,
  input: OutboxDeadLetterApprovalReviewRequest
): Promise<OutboxDeadLetterApproval> {
  const { data } = await apiClient.post(`${outboxBasePath}/dead-letters/approvals/${approvalId}:reject`, input);
  return unwrap<OutboxDeadLetterApproval>(data);
}

export async function replayOutboxDeadLetter(
  deadLetterId: string,
  input: OutboxDeadLetterActionRequest
): Promise<OutboxDeadLetterActionResponse> {
  const { data } = await apiClient.post(
    `${outboxBasePath}/dead-letters/${deadLetterId}:replay`,
    outboxDeadLetterActionBody(input),
    { headers: correlationHeaders("outbox-dlt-replay", input.correlationId) }
  );
  return unwrap<OutboxDeadLetterActionResponse>(data);
}

export async function discardOutboxDeadLetter(
  deadLetterId: string,
  input: OutboxDeadLetterActionRequest
): Promise<OutboxDeadLetterActionResponse> {
  const { data } = await apiClient.post(
    `${outboxBasePath}/dead-letters/${deadLetterId}:discard`,
    outboxDeadLetterActionBody(input),
    { headers: correlationHeaders("outbox-dlt-discard", input.correlationId) }
  );
  return unwrap<OutboxDeadLetterActionResponse>(data);
}

export async function loyaltyProgramTimeline(programId: string, limit = 25): Promise<AuditQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/programs/${programId}/timeline`, { params: { limit } });
  return unwrap<AuditQueryResponse>(data);
}

export async function loyaltyAccountTimeline(accountId: string, limit = 25): Promise<AuditQueryResponse> {
  const { data } = await apiClient.get(`${loyaltyBasePath}/accounts/${accountId}/timeline`, { params: { limit } });
  return unwrap<AuditQueryResponse>(data);
}

export async function listCampaignVersionReviewQueue(
  filters: ReviewQueueFilters = {}
): Promise<CampaignVersionReviewQueueResponse> {
  const { data } = await apiClient.get(`${basePath}/campaign-versions/review-queue`, {
    params: cleanParams(filters)
  });
  return unwrap<CampaignVersionReviewQueueResponse>(data);
}

export async function listSubmittedCampaignVersions(
  filters: ReviewQueueFilters = {}
): Promise<SubmittedCampaignVersion[]> {
  const queue = await listCampaignVersionReviewQueue({ status: "SUBMITTED", ...filters });
  return queue.items;
}

export async function getRetentionPolicies(): Promise<RetentionPolicyRegistry> {
  const { data } = await apiClient.get(`${basePath}/retention/policies`);
  return unwrap<RetentionPolicyRegistry>(data);
}

export async function runRetentionDryRun(input: RetentionDryRunRequest, correlationId?: string): Promise<RetentionDryRunResponse> {
  const { data } = await apiClient.post(`${basePath}/retention/dry-runs`, input, {
    headers: correlationHeaders("admin-retention-dry-run", correlationId)
  });
  return unwrap<RetentionDryRunResponse>(data);
}

export async function registerRetentionRestoreDrill(
  input: RetentionRestoreDrillRequest,
  correlationId?: string
): Promise<RetentionRestoreDrill> {
  const { data } = await apiClient.post(`${basePath}/retention/restore-drills`, input, {
    headers: correlationHeaders("admin-retention-restore-drill", correlationId)
  });
  return unwrap<RetentionRestoreDrill>(data);
}

export async function getRetentionRestoreDrill(restoreDrillRef: string): Promise<RetentionRestoreDrill> {
  const { data } = await apiClient.get(`${basePath}/retention/restore-drills/${encodeURIComponent(restoreDrillRef)}`);
  return unwrap<RetentionRestoreDrill>(data);
}

export async function requestRetentionApproval(input: RetentionApprovalRequest, correlationId?: string): Promise<RetentionApproval> {
  const { data } = await apiClient.post(`${basePath}/retention/approvals`, input, {
    headers: correlationHeaders("admin-retention-approval", correlationId)
  });
  return unwrap<RetentionApproval>(data);
}

export async function listRetentionApprovals(filters: RetentionApprovalFilters): Promise<RetentionApprovalQueryResponse> {
  const { data } = await apiClient.get(`${basePath}/retention/approvals`, { params: cleanParams(filters) });
  return unwrap<RetentionApprovalQueryResponse>(data);
}

export async function getRetentionApproval(approvalId: string): Promise<RetentionApproval> {
  const { data } = await apiClient.get(`${basePath}/retention/approvals/${approvalId}`);
  return unwrap<RetentionApproval>(data);
}

export async function getRetentionEvidencePack(approvalId: string, correlationId?: string): Promise<RetentionEvidencePack> {
  const { data } = await apiClient.get(`${basePath}/retention/approvals/${approvalId}/evidence-pack`, {
    headers: correlationHeaders("admin-retention-evidence-view", correlationId)
  });
  return unwrap<RetentionEvidencePack>(data);
}

export async function exportRetentionEvidencePack(
  approvalId: string,
  format: "json" | "csv",
  correlationId?: string
): Promise<RetentionEvidencePackExport> {
  const { data } = await apiClient.get(`${basePath}/retention/approvals/${approvalId}/evidence-pack/export`, {
    params: { format },
    headers: correlationHeaders("admin-retention-evidence-export", correlationId)
  });
  return unwrap<RetentionEvidencePackExport>(data);
}

export async function approveRetentionApproval(
  approvalId: string,
  input: RetentionApprovalDecisionRequest = {},
  correlationId?: string
): Promise<RetentionApproval> {
  const { data } = await apiClient.post(`${basePath}/retention/approvals/${approvalId}:approve`, input, {
    headers: correlationHeaders("admin-retention-approve", correlationId)
  });
  return unwrap<RetentionApproval>(data);
}

export async function rejectRetentionApproval(
  approvalId: string,
  input: RetentionApprovalDecisionRequest = {},
  correlationId?: string
): Promise<RetentionApproval> {
  const { data } = await apiClient.post(`${basePath}/retention/approvals/${approvalId}:reject`, input, {
    headers: correlationHeaders("admin-retention-reject", correlationId)
  });
  return unwrap<RetentionApproval>(data);
}

export async function executeRetention(input: RetentionExecutionRequest, correlationId?: string): Promise<RetentionExecutionResponse> {
  const { data } = await apiClient.post(`${basePath}/retention/executions`, input, {
    headers: correlationHeaders("admin-retention-execution", correlationId)
  });
  return unwrap<RetentionExecutionResponse>(data);
}
