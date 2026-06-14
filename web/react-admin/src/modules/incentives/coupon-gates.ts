import type { CouponImportApproval, CouponImportCommitResponse, CouponImportDryRunResponse } from "./types";

export type CouponActor = { id: number; email: string; fullName: string; role?: string | null } | null | undefined;

export type CouponImportGateReasonCode =
  | "AUTH_CONTEXT_UNRESOLVED"
  | "RBAC_COUPON_MANAGE_REQUIRED"
  | "RBAC_COUPON_READ_REQUIRED"
  | "RBAC_REVIEW_REQUIRED"
  | "CAMPAIGN_REQUIRED"
  | "CSV_FILE_REQUIRED"
  | "CSV_FILE_INVALID"
  | "DRY_RUN_REQUIRED"
  | "DRY_RUN_NOT_COMMIT_READY"
  | "DRY_RUN_STALE"
  | "REASON_REQUIRED"
  | "CHANGE_TICKET_REQUIRED"
  | "APPROVAL_REQUIRED"
  | "APPROVAL_ALREADY_EXISTS"
  | "APPROVAL_NOT_PENDING"
  | "APPROVAL_NOT_APPROVED"
  | "APPROVAL_EXPIRED"
  | "SELF_APPROVAL_BLOCKED"
  | "SELF_COMMIT_BLOCKED"
  | "FILE_REATTACH_REQUIRED"
  | "CONFIRM_REQUIRED"
  | "IDEMPOTENCY_KEY_REQUIRED"
  | "CORRELATION_ID_REQUIRED"
  | "COMMIT_ALREADY_COMPLETED"
  | "DRY_RUN_EXPIRED"
  | "RESULT_HASH_MISMATCH"
  | "IDEMPOTENCY_KEY_REUSED"
  | "IDEMPOTENCY_KEY_EXPIRED"
  | "IDEMPOTENCY_KEY_NOT_REPLAYABLE"
  | "IDEMPOTENCY_KEY_ACQUIRE_FAILED"
  | "COUPON_DUPLICATE"
  | "SERVER_FORBIDDEN"
  | "SERVER_RATE_LIMITED"
  | "SERVER_CONFLICT"
  | "SERVER_VALIDATION_FAILED"
  | "SERVER_NOT_FOUND"
  | "SERVER_ERROR";

export type CouponImportGateIssue = {
  code: CouponImportGateReasonCode;
  message: string;
};

export type CouponImportGateResult = {
  allowed: boolean;
  issues: CouponImportGateIssue[];
};

export const couponImportGateReasonMessages: Record<CouponImportGateReasonCode, string> = {
  AUTH_CONTEXT_UNRESOLVED: "Không xác định được operator hiện tại.",
  RBAC_COUPON_MANAGE_REQUIRED: "Coupon import operation yêu cầu role ADMIN, ORG_ADMIN, INCENTIVE_ADMIN hoặc INCENTIVE_OPERATOR.",
  RBAC_COUPON_READ_REQUIRED: "Coupon import read operation yêu cầu role ADMIN, ORG_ADMIN, INCENTIVE_ADMIN, INCENTIVE_OPERATOR hoặc INCENTIVE_REVIEWER.",
  RBAC_REVIEW_REQUIRED: "Coupon import approval decision yêu cầu role ADMIN, ORG_ADMIN, INCENTIVE_ADMIN hoặc INCENTIVE_REVIEWER.",
  CAMPAIGN_REQUIRED: "Campaign ID là bắt buộc.",
  CSV_FILE_REQUIRED: "Cần chọn file CSV.",
  CSV_FILE_INVALID: "File phải là CSV.",
  DRY_RUN_REQUIRED: "Cần dry-run trước khi request approval.",
  DRY_RUN_NOT_COMMIT_READY: "Dry-run chưa commit-ready.",
  DRY_RUN_STALE: "File hoặc scope đã đổi sau dry-run.",
  REASON_REQUIRED: "Reason là bắt buộc.",
  CHANGE_TICKET_REQUIRED: "Change ticket là bắt buộc.",
  APPROVAL_REQUIRED: "Chưa chọn approval.",
  APPROVAL_ALREADY_EXISTS: "Dry-run này đã có approval đang active.",
  APPROVAL_NOT_PENDING: "Approval không còn ở trạng thái pending.",
  APPROVAL_NOT_APPROVED: "Approval phải ở trạng thái APPROVED.",
  APPROVAL_EXPIRED: "Approval đã hết hạn.",
  SELF_APPROVAL_BLOCKED: "Người request không được tự approve/reject approval này.",
  SELF_COMMIT_BLOCKED: "Người approve không được tự commit.",
  FILE_REATTACH_REQUIRED: "Cần reattach file CSV để backend xác nhận hash.",
  CONFIRM_REQUIRED: "Cần confirm commit.",
  IDEMPOTENCY_KEY_REQUIRED: "Idempotency key là bắt buộc.",
  CORRELATION_ID_REQUIRED: "Correlation ID là bắt buộc.",
  COMMIT_ALREADY_COMPLETED: "Import này đã có commit response trong phiên hiện tại.",
  DRY_RUN_EXPIRED: "Coupon import dry-run đã hết hạn.",
  RESULT_HASH_MISMATCH: "Payload hoặc file hiện tại không còn khớp result hash đã duyệt.",
  IDEMPOTENCY_KEY_REUSED: "Idempotency key đã được dùng với payload khác.",
  IDEMPOTENCY_KEY_EXPIRED: "Idempotency key đã hết hạn; cần tạo key mới.",
  IDEMPOTENCY_KEY_NOT_REPLAYABLE: "Idempotency key không còn ở trạng thái có thể replay; cần tạo key mới.",
  IDEMPOTENCY_KEY_ACQUIRE_FAILED: "Server chưa khóa được idempotency key; hãy thử lại với correlation id hiện tại.",
  COUPON_DUPLICATE: "Coupon import chứa mã đã tồn tại trong campaign.",
  SERVER_FORBIDDEN: "Server từ chối quyền thao tác coupon import.",
  SERVER_RATE_LIMITED: "Server đang giới hạn tần suất thao tác coupon import; hãy chờ rồi thử lại.",
  SERVER_CONFLICT: "Server từ chối vì trạng thái dữ liệu đã thay đổi.",
  SERVER_VALIDATION_FAILED: "Server từ chối vì request không hợp lệ.",
  SERVER_NOT_FOUND: "Server không tìm thấy tài nguyên coupon import liên quan.",
  SERVER_ERROR: "Server trả lỗi chưa phân loại; kiểm tra correlation id và audit."
};

function issue(code: CouponImportGateReasonCode): CouponImportGateIssue {
  return { code, message: couponImportGateReasonMessages[code] };
}

function issueWithServerDetail(code: CouponImportGateReasonCode, detail?: string) {
  const base = couponImportGateReasonMessages[code];
  return {
    code,
    message: detail?.trim() ? `${base} Server detail: ${detail.trim()}` : base
  };
}

function allowed(issues: CouponImportGateIssue[]): CouponImportGateResult {
  return { allowed: issues.length === 0, issues };
}

export function couponActorRole(user: CouponActor) {
  return user?.role?.trim().toUpperCase() ?? "";
}

export function hasCouponActor(user: CouponActor) {
  if (!user) return false;
  return [
    user.id === undefined || user.id === null ? "" : String(user.id),
    user.email ?? "",
    user.fullName ?? ""
  ].some((item) => item.trim().length > 0);
}

export function couponActorMatches(user: CouponActor, actor?: string | null) {
  if (!user || !actor) return false;
  const normalized = actor.trim().toLowerCase();
  return [String(user.id), user.email, user.fullName]
    .filter(Boolean)
    .map((item) => item.trim().toLowerCase())
    .includes(normalized);
}

export function hasCouponManageRole(user: CouponActor) {
  return ["ADMIN", "ORG_ADMIN", "INCENTIVE_ADMIN", "INCENTIVE_OPERATOR"].includes(couponActorRole(user));
}

export function hasCouponReviewRole(user: CouponActor) {
  return ["ADMIN", "ORG_ADMIN", "INCENTIVE_ADMIN", "INCENTIVE_REVIEWER"].includes(couponActorRole(user));
}

export function couponApprovalExpired(approval?: CouponImportApproval | null, nowMs = Date.now()) {
  if (!approval?.expiresAt) return false;
  const parsed = Date.parse(approval.expiresAt);
  return Number.isFinite(parsed) && parsed <= nowMs;
}

export function couponImportDryRunGate({
  user,
  campaignId,
  file,
  fileLooksCsv
}: {
  user: CouponActor;
  campaignId: string;
  file: File | null;
  fileLooksCsv: boolean;
}) {
  const issues: CouponImportGateIssue[] = [];
  if (!hasCouponActor(user)) issues.push(issue("AUTH_CONTEXT_UNRESOLVED"));
  if (!hasCouponManageRole(user)) issues.push(issue("RBAC_COUPON_MANAGE_REQUIRED"));
  if (!campaignId.trim()) issues.push(issue("CAMPAIGN_REQUIRED"));
  if (!file) issues.push(issue("CSV_FILE_REQUIRED"));
  if (file && !fileLooksCsv) issues.push(issue("CSV_FILE_INVALID"));
  return allowed(issues);
}

export function couponImportApprovalRequestGate({
  dryRun,
  user,
  dryRunStale,
  file,
  reason,
  changeTicket
}: {
  dryRun: CouponImportDryRunResponse | null;
  user: CouponActor;
  dryRunStale: boolean;
  file: File | null;
  reason: string;
  changeTicket: string;
}) {
  const issues: CouponImportGateIssue[] = [];
  if (!hasCouponActor(user)) issues.push(issue("AUTH_CONTEXT_UNRESOLVED"));
  if (!hasCouponManageRole(user)) issues.push(issue("RBAC_COUPON_MANAGE_REQUIRED"));
  if (!dryRun) issues.push(issue("DRY_RUN_REQUIRED"));
  if (dryRun && !dryRun.commitReady) issues.push(issue("DRY_RUN_NOT_COMMIT_READY"));
  if (dryRunStale) issues.push(issue("DRY_RUN_STALE"));
  if (!file) issues.push(issue("FILE_REATTACH_REQUIRED"));
  if (!reason.trim()) issues.push(issue("REASON_REQUIRED"));
  if (!changeTicket.trim()) issues.push(issue("CHANGE_TICKET_REQUIRED"));
  return allowed(issues);
}

export function couponImportApprovalDecisionGate(
  approval: CouponImportApproval | null,
  user: CouponActor,
  nowMs = Date.now()
) {
  const issues: CouponImportGateIssue[] = [];
  if (!approval?.approvalId) issues.push(issue("APPROVAL_REQUIRED"));
  if (!hasCouponActor(user)) issues.push(issue("AUTH_CONTEXT_UNRESOLVED"));
  if (!hasCouponReviewRole(user)) issues.push(issue("RBAC_REVIEW_REQUIRED"));
  if (approval?.approvalId && approval.status !== "PENDING_APPROVAL") issues.push(issue("APPROVAL_NOT_PENDING"));
  if (couponApprovalExpired(approval, nowMs)) issues.push(issue("APPROVAL_EXPIRED"));
  if (couponActorMatches(user, approval?.requestedBy)) issues.push(issue("SELF_APPROVAL_BLOCKED"));
  return allowed(issues);
}

export function couponImportCommitGate({
  approval,
  user,
  dryRunStale,
  file,
  idempotencyKey,
  correlationId,
  confirm,
  commit,
  nowMs = Date.now()
}: {
  approval: CouponImportApproval | null;
  user: CouponActor;
  dryRunStale: boolean;
  file: File | null;
  idempotencyKey: string;
  correlationId: string;
  confirm: boolean;
  commit?: CouponImportCommitResponse | null;
  nowMs?: number;
}) {
  const issues: CouponImportGateIssue[] = [];
  if (!approval?.approvalId) issues.push(issue("APPROVAL_REQUIRED"));
  if (!hasCouponActor(user)) issues.push(issue("AUTH_CONTEXT_UNRESOLVED"));
  if (!hasCouponManageRole(user)) issues.push(issue("RBAC_COUPON_MANAGE_REQUIRED"));
  if (approval?.approvalId && approval.status !== "APPROVED") issues.push(issue("APPROVAL_NOT_APPROVED"));
  if (couponApprovalExpired(approval, nowMs)) issues.push(issue("APPROVAL_EXPIRED"));
  if (couponActorMatches(user, approval?.approvedBy)) issues.push(issue("SELF_COMMIT_BLOCKED"));
  if (dryRunStale) issues.push(issue("DRY_RUN_STALE"));
  if (!file) issues.push(issue("FILE_REATTACH_REQUIRED"));
  if (!idempotencyKey.trim()) issues.push(issue("IDEMPOTENCY_KEY_REQUIRED"));
  if (!correlationId.trim()) issues.push(issue("CORRELATION_ID_REQUIRED"));
  if (!confirm) issues.push(issue("CONFIRM_REQUIRED"));
  if (commit) issues.push(issue("COMMIT_ALREADY_COMPLETED"));
  return allowed(issues);
}

type ErrorDtoLike = {
  statusCode?: string;
  title?: string;
  detail?: string;
  errorCode?: string;
  fieldErrors?: string[];
};

type HttpErrorLike = {
  response?: {
    status?: number;
    data?: unknown;
  };
  message?: string;
};

function errorData(error: unknown) {
  if (!error || typeof error !== "object") return undefined;
  return (error as HttpErrorLike).response?.data;
}

function errorStatus(error: unknown) {
  if (!error || typeof error !== "object") return undefined;
  const responseStatus = (error as HttpErrorLike).response?.status;
  if (typeof responseStatus === "number") return responseStatus;
  const data = errorData(error);
  if (data && typeof data === "object") {
    const statusCode = (data as ErrorDtoLike).statusCode;
    const parsed = Number.parseInt(statusCode ?? "", 10);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function errorDetail(error: unknown) {
  const data = errorData(error);
  if (data && typeof data === "object") {
    const dto = data as ErrorDtoLike;
    return dto.detail ?? dto.title ?? dto.fieldErrors?.join(" ");
  }
  if (error instanceof Error) return error.message;
  return undefined;
}

function errorCode(error: unknown) {
  const data = errorData(error);
  if (data && typeof data === "object") {
    const code = (data as ErrorDtoLike).errorCode;
    return typeof code === "string" && code.trim() ? code.trim() : undefined;
  }
  return undefined;
}

function normalizedDetail(error: unknown) {
  return errorDetail(error)?.trim().toLowerCase() ?? "";
}

const couponImportServerErrorCodeMap: Partial<Record<string, CouponImportGateReasonCode>> = {
  ADMIN_OPERATION_RATE_LIMITED: "SERVER_RATE_LIMITED",
  COUPON_IMPORT_MANAGE_FORBIDDEN: "RBAC_COUPON_MANAGE_REQUIRED",
  COUPON_IMPORT_READ_FORBIDDEN: "RBAC_COUPON_READ_REQUIRED",
  COUPON_IMPORT_REVIEW_FORBIDDEN: "RBAC_REVIEW_REQUIRED",
  COUPON_IMPORT_OPERATOR_REQUIRED: "AUTH_CONTEXT_UNRESOLVED",
  COUPON_IMPORT_SELF_APPROVAL_BLOCKED: "SELF_APPROVAL_BLOCKED",
  COUPON_IMPORT_SELF_COMMIT_BLOCKED: "SELF_COMMIT_BLOCKED",
  COUPON_IMPORT_DRY_RUN_NOT_FOUND: "SERVER_NOT_FOUND",
  COUPON_IMPORT_APPROVAL_NOT_FOUND: "SERVER_NOT_FOUND",
  COUPON_IMPORT_DRY_RUN_NOT_COMMIT_READY: "DRY_RUN_NOT_COMMIT_READY",
  COUPON_IMPORT_DRY_RUN_EXPIRED: "DRY_RUN_EXPIRED",
  COUPON_IMPORT_ALREADY_COMMITTED: "COMMIT_ALREADY_COMPLETED",
  COUPON_IMPORT_RESULT_HASH_MISMATCH: "RESULT_HASH_MISMATCH",
  COUPON_IMPORT_PAYLOAD_CHANGED: "DRY_RUN_STALE",
  COUPON_IMPORT_DUPLICATE_CODE: "COUPON_DUPLICATE",
  COUPON_IMPORT_APPROVAL_ALREADY_EXISTS: "APPROVAL_ALREADY_EXISTS",
  COUPON_IMPORT_APPROVAL_NOT_PENDING: "APPROVAL_NOT_PENDING",
  COUPON_IMPORT_APPROVAL_NOT_APPROVED: "APPROVAL_NOT_APPROVED",
  COUPON_IMPORT_APPROVAL_EXPIRED: "APPROVAL_EXPIRED",
  COUPON_IMPORT_APPROVAL_SUBJECT_CHANGED: "DRY_RUN_STALE",
  IDEMPOTENCY_KEY_REUSED: "IDEMPOTENCY_KEY_REUSED",
  IDEMPOTENCY_KEY_EXPIRED: "IDEMPOTENCY_KEY_EXPIRED",
  IDEMPOTENCY_KEY_NOT_REPLAYABLE: "IDEMPOTENCY_KEY_NOT_REPLAYABLE",
  IDEMPOTENCY_KEY_ACQUIRE_FAILED: "IDEMPOTENCY_KEY_ACQUIRE_FAILED"
};

export function couponImportServerGateIssues(error: unknown): CouponImportGateIssue[] {
  const status = errorStatus(error);
  const detail = errorDetail(error);
  const mappedCode = errorCode(error);
  const normalized = normalizedDetail(error);

  if (mappedCode) {
    const mappedIssue = couponImportServerErrorCodeMap[mappedCode];
    if (mappedIssue) return [issueWithServerDetail(mappedIssue, detail)];
  }

  if (status === 403) {
    if (normalized.includes("review")) return [issueWithServerDetail("RBAC_REVIEW_REQUIRED", detail)];
    if (normalized.includes("operate coupon import") || normalized.includes("manage")) {
      return [issueWithServerDetail("RBAC_COUPON_MANAGE_REQUIRED", detail)];
    }
    return [issueWithServerDetail("SERVER_FORBIDDEN", detail)];
  }
  if (status === 429) return [issueWithServerDetail("SERVER_RATE_LIMITED", detail)];
  if (status === 400) return [issueWithServerDetail("SERVER_VALIDATION_FAILED", detail)];
  if (status === 404) return [issueWithServerDetail("SERVER_NOT_FOUND", detail)];
  if (status === 409) {
    if (normalized.includes("not pending")) return [issueWithServerDetail("APPROVAL_NOT_PENDING", detail)];
    if (normalized.includes("not approved")) return [issueWithServerDetail("APPROVAL_NOT_APPROVED", detail)];
    if (normalized.includes("approval is expired")) return [issueWithServerDetail("APPROVAL_EXPIRED", detail)];
    if (normalized.includes("dry-run has expired")) return [issueWithServerDetail("DRY_RUN_EXPIRED", detail)];
    if (normalized.includes("already been committed")) return [issueWithServerDetail("COMMIT_ALREADY_COMPLETED", detail)];
    if (normalized.includes("not commit-ready")) return [issueWithServerDetail("DRY_RUN_NOT_COMMIT_READY", detail)];
    if (normalized.includes("result hash") || normalized.includes("no longer matches")) {
      return [issueWithServerDetail("RESULT_HASH_MISMATCH", detail)];
    }
    if (normalized.includes("idempotency key was reused")) return [issueWithServerDetail("IDEMPOTENCY_KEY_REUSED", detail)];
    if (normalized.includes("idempotency key has expired")) return [issueWithServerDetail("IDEMPOTENCY_KEY_EXPIRED", detail)];
    if (normalized.includes("codes that already exist") || normalized.includes("duplicate")) {
      return [issueWithServerDetail("COUPON_DUPLICATE", detail)];
    }
    return [issueWithServerDetail("SERVER_CONFLICT", detail)];
  }
  if (status !== undefined && status >= 500) return [issueWithServerDetail("SERVER_ERROR", detail)];
  return detail ? [issueWithServerDetail("SERVER_ERROR", detail)] : [];
}
