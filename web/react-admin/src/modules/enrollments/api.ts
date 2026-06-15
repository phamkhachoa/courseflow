import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type Enrollment = {
  id: string;
  studentId: string;
  courseId: string;
  sectionId?: string;
  status?: string;
  enrolledAt?: string;
  droppedAt?: string;
  completedAt?: string;
  dropReason?: string;
};
export type WaitlistEntry = {
  id: string;
  studentId: string;
  courseId: string;
  position?: number;
  status?: string;
  createdAt?: string;
};

export type EnrollmentStats = {
  courseId: string;
  totalActive: number;
  totalDropped: number;
  totalCompleted: number;
  waitlistCount: number;
};

export type AuditLogEntry = {
  id: string;
  enrollmentId: string;
  actorId?: string;
  action: string;
  oldStatus?: string;
  newStatus?: string;
  reason?: string;
  createdAt?: string;
};

export type BatchEnrollEntry = {
  studentId: string;
  courseId: string;
  sectionId?: string;
};

export type BatchEnrollResult = {
  enrolled: number;
  skipped: number;
  errors: string[];
};

export type PromotionEffect = {
  type?: string | null;
  benefitType?: string | null;
  actionType?: string | null;
  targetType?: string | null;
  targetId?: string | null;
  amount?: number | string | null;
  currency?: string | null;
  unit?: string | null;
  quantity?: number | string | null;
  metadata?: Record<string, unknown> | null;
};

export type EnrollmentPromotionApplicationState = {
  id: string;
  enrollmentId: string;
  studentId: string;
  courseId: string;
  status: string;
  couponCode?: string | null;
  couponId?: string | null;
  reservationId?: string | null;
  redemptionId?: string | null;
  idempotencyKey?: string | null;
  reasonCodes: string[];
  message?: string | null;
  effects: PromotionEffect[];
  retryCount: number;
  nextRetryAt?: string | null;
  lastRetryError?: string | null;
  createdAt?: string;
  updatedAt?: string;
};

export type EnrollmentBenefitReconciliationEntry = {
  reconciliationKey: string;
  reconciliationStatus: string;
  reasonCodes: string[];
  severity: string;
  enrollmentId: string;
  studentId: string;
  courseId: string;
  enrollmentStatus: string;
  enrolledAt?: string | null;
  droppedAt?: string | null;
  dropReason?: string | null;
  orderId?: string | null;
  orderStatus?: string | null;
  orderAmount?: number | string | null;
  currency?: string | null;
  paidAt?: string | null;
  orderCreatedAt?: string | null;
  orderUpdatedAt?: string | null;
  promotionApplicationId?: string | null;
  promotionStatus?: string | null;
  reservationId?: string | null;
  redemptionId?: string | null;
  promotionRetryCount: number;
  promotionNextRetryAt?: string | null;
  promotionLastRetryError?: string | null;
  promotionUpdatedAt?: string | null;
};

export type EnrollmentBenefitReconciliationResponse = {
  items: EnrollmentBenefitReconciliationEntry[];
  limit: number;
  hasMore: boolean;
  generatedAt: string;
};

export type EnrollmentRemediationCaseAction = {
  id: string;
  action: string;
  actorId?: string | null;
  note?: string | null;
  fromStatus?: string | null;
  toStatus?: string | null;
  payload?: Record<string, unknown> | null;
  createdAt?: string | null;
};

export type EnrollmentRemediationCase = {
  id: string;
  caseType: string;
  status: string;
  severity: string;
  enrollmentId?: string | null;
  checkoutAttemptId?: string | null;
  promotionApplicationId?: string | null;
  orderId?: string | null;
  studentId: string;
  courseId: string;
  assigneeId: string;
  note?: string | null;
  reasonCode: string;
  slaDueAt?: string | null;
  slaAgeMinutes: number;
  slaBreached: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
  closedAt?: string | null;
  actionHistory: EnrollmentRemediationCaseAction[];
  retryHistory: EnrollmentRemediationCaseAction[];
};

export type RefundDropPolicyEvaluateRequest = {
  enrollmentId: string;
  reason?: string;
  requestedAt?: string;
  refundWindowDays?: number;
  paymentStatus?: string;
  paidAmount?: number | string;
  currency?: string;
  paidAt?: string;
  promotionStatus?: string;
  reservationId?: string;
  redemptionId?: string;
  loyaltyPointsEarned?: number;
  loyaltyPointsReversed?: number;
  loyaltyEarnEntryId?: string;
  rewardStatus?: string;
  rewardRedemptionId?: string;
  rewardFulfillmentStatus?: string;
  rewardFulfilled?: boolean;
  evidence?: Record<string, unknown>;
};

export type RefundDropPolicyFacts = {
  enrollmentStatus: string;
  enrolledAt?: string | null;
  droppedAt?: string | null;
  completedAt?: string | null;
  dropReason?: string | null;
  orderId?: string | null;
  paymentStatus?: string | null;
  paidAmount?: number | string | null;
  currency?: string | null;
  paidAt?: string | null;
  refundWindowDays: number;
  refundWindowEndsAt?: string | null;
  withinRefundWindow: boolean;
  promotionApplicationId?: string | null;
  promotionStatus?: string | null;
  reservationId?: string | null;
  redemptionId?: string | null;
  loyaltyPointsEarned: number;
  loyaltyPointsReversed: number;
  loyaltyPointsOutstanding: number;
  loyaltyEarnEntryId?: string | null;
  rewardStatus?: string | null;
  rewardRedemptionId?: string | null;
  rewardFulfillmentStatus?: string | null;
  rewardFulfilled?: boolean | null;
};

export type RefundDropPolicyAction = {
  domain: string;
  action: string;
  decision: string;
  severity: string;
  required: boolean;
  blocking: boolean;
  makerCheckerRequired: boolean;
  endpoint?: string | null;
  idempotencyKey?: string | null;
  reasonCodes: string[];
  evidence: Record<string, unknown>;
};

export type RefundDropPolicyEvaluationResponse = {
  enrollmentId: string;
  studentId: string;
  courseId: string;
  matrixStatus: string;
  severity: string;
  dropAllowed: boolean;
  refundEligible: boolean;
  manualReviewRequired: boolean;
  reasonCodes: string[];
  facts: RefundDropPolicyFacts;
  actions: RefundDropPolicyAction[];
  auditPreview: Record<string, unknown>;
  generatedAt: string;
};

export async function listEnrollments(params: {
  courseId?: string;
  studentId?: string;
}): Promise<Enrollment[]> {
  const { data } = await apiClient.get("/admin/v1/enrollments", { params });
  return unwrapList<Enrollment>(data);
}

export async function listPromotionApplications(params: {
  status?: string;
  courseId?: string;
  studentId?: string;
  limit?: number;
}): Promise<EnrollmentPromotionApplicationState[]> {
  const { data } = await apiClient.get("/admin/v1/enrollments/promotion-applications", { params });
  return unwrapList<EnrollmentPromotionApplicationState>(data);
}

export async function queryBenefitReconciliation(params: {
  enrollmentId?: string;
  courseId?: string;
  studentId?: string;
  status?: string;
  includeMatched?: boolean;
  limit?: number;
}): Promise<EnrollmentBenefitReconciliationResponse> {
  const { data } = await apiClient.get("/admin/v1/enrollments/benefit-reconciliation", { params });
  return unwrap<EnrollmentBenefitReconciliationResponse>(data);
}

export async function queryRemediationCases(params: {
  status?: string;
  courseId?: string;
  enrollmentId?: string;
  promotionApplicationId?: string;
  orderId?: string;
  studentId?: string;
  couponId?: string;
  redemptionId?: string;
  correlationId?: string;
  assigneeId?: string;
  limit?: number;
} = {}): Promise<EnrollmentRemediationCase[]> {
  const { data } = await apiClient.get("/admin/v1/enrollments/remediation-cases", { params });
  return unwrapList<EnrollmentRemediationCase>(data);
}

export async function assignRemediationCase(
  id: string,
  input: { assigneeId: string; note?: string; correlationId?: string }
): Promise<EnrollmentRemediationCase> {
  const { data } = await apiClient.post(`/admin/v1/enrollments/remediation-cases/${id}:assign`, input);
  return unwrap<EnrollmentRemediationCase>(data);
}

export async function addRemediationCaseNote(
  id: string,
  input: { note?: string; correlationId?: string } = {}
): Promise<EnrollmentRemediationCase> {
  const { data } = await apiClient.post(`/admin/v1/enrollments/remediation-cases/${id}:note`, input);
  return unwrap<EnrollmentRemediationCase>(data);
}

export async function resolveRemediationCase(
  id: string,
  input: { note?: string; correlationId?: string } = {}
): Promise<EnrollmentRemediationCase> {
  const { data } = await apiClient.post(`/admin/v1/enrollments/remediation-cases/${id}:resolve`, input);
  return unwrap<EnrollmentRemediationCase>(data);
}

export async function evaluateRefundDropPolicy(
  input: RefundDropPolicyEvaluateRequest
): Promise<RefundDropPolicyEvaluationResponse> {
  const { data } = await apiClient.post("/admin/v1/enrollments/refund-drop-policy:evaluate", input);
  return unwrap<RefundDropPolicyEvaluationResponse>(data);
}

export async function retryPromotionApplicationCommit(
  id: string,
  input: { reason?: string; correlationId?: string } = {}
): Promise<EnrollmentPromotionApplicationState> {
  const { data } = await apiClient.post(
    `/admin/v1/enrollments/promotion-applications/${id}:retry-commit`,
    input
  );
  return unwrap<EnrollmentPromotionApplicationState>(data);
}

export async function cancelPromotionApplicationReservation(
  id: string,
  input: { reason?: string; correlationId?: string } = {}
): Promise<EnrollmentPromotionApplicationState> {
  const { data } = await apiClient.post(
    `/admin/v1/enrollments/promotion-applications/${id}:cancel-reservation`,
    input
  );
  return unwrap<EnrollmentPromotionApplicationState>(data);
}

export async function createEnrollment(input: {
  courseId: string;
  studentId?: string;
}): Promise<Enrollment> {
  // studentId is optional and only honored for staff enrolling someone else;
  // a student caller is resolved from the gateway identity.
  const { data } = await apiClient.post("/admin/v1/enrollments", input);
  return unwrap<Enrollment>(data);
}
export async function listWaitlist(courseId: string): Promise<WaitlistEntry[]> {
  const { data } = await apiClient.get("/admin/v1/waitlist", { params: { courseId } });
  return unwrapList<WaitlistEntry>(data);
}
export async function addToWaitlist(input: {
  courseId: string;
  studentId?: string;
}): Promise<WaitlistEntry> {
  const { data } = await apiClient.post("/admin/v1/waitlist", input);
  return unwrap<WaitlistEntry>(data);
}

/** Change an enrollment's status. The actor is taken from the gateway identity, never the body. */
export async function changeStatus(
  id: string,
  input: { newStatus: string; reason?: string }
): Promise<Enrollment> {
  const { data } = await apiClient.patch(`/admin/v1/enrollments/${id}/status`, input);
  return unwrap<Enrollment>(data);
}

export async function batchEnroll(entries: BatchEnrollEntry[]): Promise<BatchEnrollResult> {
  const { data } = await apiClient.post("/admin/v1/enrollments/batch", { entries });
  return unwrap<BatchEnrollResult>(data);
}

export async function setCapacity(courseId: string, capacity: number | null): Promise<void> {
  await apiClient.put(`/admin/v1/courses/${courseId}/capacity`, { capacity });
}

export async function getStats(courseId: string): Promise<EnrollmentStats> {
  const { data } = await apiClient.get("/admin/v1/enrollments/stats", { params: { courseId } });
  return unwrap<EnrollmentStats>(data);
}

export async function getAuditLog(id: string): Promise<AuditLogEntry[]> {
  const { data } = await apiClient.get(`/admin/v1/enrollments/${id}/audit`);
  return unwrapList<AuditLogEntry>(data);
}

export async function queryAuditLog(params: {
  enrollmentId?: string;
  courseId?: string;
  studentId?: string;
  correlationId?: string;
  limit?: number;
}): Promise<AuditLogEntry[]> {
  const { data } = await apiClient.get("/admin/v1/enrollments/audit", { params });
  return unwrapList<AuditLogEntry>(data);
}
