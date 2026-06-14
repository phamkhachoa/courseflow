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
