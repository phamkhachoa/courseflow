import { toIsoDateTime, toNumberOrUndefined } from "./labels";
import type { RetentionApproval, RetentionDryRunResponse, RetentionExecutionResponse, RetentionRestoreDrill } from "./types";

export const executableRetentionPolicy = "terminal-reservation-request-snapshots";
export const retentionDryRunTtlMinutes = 60;
export const retentionRestoreDatabase = "cf_promotion";
export const sha256ArtifactPattern = /^sha256:[a-f0-9]{64}$/i;

export type RetentionScopeForm = {
  tenantId: string;
  applicationId: string;
  policyId: string;
  retentionDays: string;
  batchLimit: string;
};

export type RestoreDrillForm = {
  restoreDrillRef: string;
  databaseName: string;
  backupPath: string;
  artifactHash: string;
  checkedAt: string;
  expiresAt: string;
};

export type RetentionActor = { id: number; email: string; fullName: string; role?: string | null } | null | undefined;

export type RetentionGateReasonCode =
  | "APPROVAL_REQUIRED"
  | "AUTH_CONTEXT_UNRESOLVED"
  | "RBAC_RETENTION_ADMIN_REQUIRED"
  | "RBAC_REVIEW_REQUIRED"
  | "GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN"
  | "DRY_RUN_STALE"
  | "RESULT_HASH_MISMATCH"
  | "RESTORE_DRILL_INVALID"
  | "RESTORE_DRILL_ALREADY_EXISTS"
  | "APPROVAL_ALREADY_EXISTS"
  | "APPROVAL_NOT_PENDING"
  | "APPROVAL_NOT_APPROVED"
  | "APPROVAL_EXPIRED"
  | "SELF_APPROVAL_BLOCKED"
  | "SELF_EXECUTION_BLOCKED"
  | "APPROVAL_CONSUMED"
  | "EXECUTION_ATTEMPT_BLOCKED"
  | "EXECUTION_DISABLED"
  | "IDEMPOTENCY_KEY_REUSED"
  | "IDEMPOTENCY_KEY_IN_PROGRESS"
  | "IDEMPOTENCY_KEY_NOT_REPLAYABLE"
  | "IDEMPOTENCY_KEY_ACQUIRE_FAILED"
  | "SERVER_VALIDATION_FAILED"
  | "SERVER_FORBIDDEN"
  | "SERVER_RATE_LIMITED"
  | "SERVER_CONFLICT"
  | "SERVER_NOT_FOUND"
  | "SERVER_ERROR";

export type RetentionGateIssue = {
  code: RetentionGateReasonCode;
  message: string;
};

export type RetentionGateResult = {
  allowed: boolean;
  issues: RetentionGateIssue[];
};

export const retentionGateReasonMessages: Record<RetentionGateReasonCode, string> = {
  APPROVAL_REQUIRED: "Chưa chọn approval.",
  AUTH_CONTEXT_UNRESOLVED: "Không xác định được operator hiện tại.",
  RBAC_RETENTION_ADMIN_REQUIRED: "Execution destructive retention yêu cầu role ADMIN, ORG_ADMIN hoặc INCENTIVE_ADMIN.",
  RBAC_REVIEW_REQUIRED: "Review approval yêu cầu role ADMIN, ORG_ADMIN, INCENTIVE_ADMIN hoặc INCENTIVE_REVIEWER.",
  GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN: "Global retention yêu cầu platform role ADMIN.",
  DRY_RUN_STALE: "Retention dry-run đã cũ; cần chạy dry-run mới.",
  RESULT_HASH_MISMATCH: "Retention candidate snapshot không còn khớp result hash đã duyệt.",
  RESTORE_DRILL_INVALID: "Restore drill chưa hợp lệ hoặc đã hết hiệu lực cho retention execution.",
  RESTORE_DRILL_ALREADY_EXISTS: "Restore drill reference đã tồn tại.",
  APPROVAL_ALREADY_EXISTS: "Dry-run này đã có retention approval đang active.",
  APPROVAL_NOT_PENDING: "Approval không còn ở trạng thái pending.",
  APPROVAL_NOT_APPROVED: "Cần approval APPROVED trước khi destructive execution.",
  APPROVAL_EXPIRED: "Approval đã hết hạn.",
  SELF_APPROVAL_BLOCKED: "Người request không được tự approve/reject.",
  SELF_EXECUTION_BLOCKED: "Người approve không được tự execute.",
  APPROVAL_CONSUMED: "Approval này đã có execution hoặc failure state, cần dry-run/approval mới.",
  EXECUTION_ATTEMPT_BLOCKED: "Execution attempt vừa lỗi/không xác định; reload approval trước khi thao tác tiếp.",
  EXECUTION_DISABLED: "Backend đang tắt destructive retention execution.",
  IDEMPOTENCY_KEY_REUSED: "Idempotency key đã được dùng với payload khác.",
  IDEMPOTENCY_KEY_IN_PROGRESS: "Execution với idempotency key này đang in-progress; reload trạng thái trước khi retry.",
  IDEMPOTENCY_KEY_NOT_REPLAYABLE: "Idempotency key không còn replay được; cần tạo attempt mới sau khi kiểm tra audit.",
  IDEMPOTENCY_KEY_ACQUIRE_FAILED: "Server chưa khóa được retention execution attempt; hãy thử lại với correlation id hiện tại.",
  SERVER_VALIDATION_FAILED: "Server từ chối vì request retention không hợp lệ.",
  SERVER_FORBIDDEN: "Server từ chối quyền thao tác retention.",
  SERVER_RATE_LIMITED: "Server đang giới hạn tần suất thao tác retention; hãy chờ rồi thử lại.",
  SERVER_CONFLICT: "Server từ chối vì trạng thái retention đã thay đổi.",
  SERVER_NOT_FOUND: "Server không tìm thấy tài nguyên retention liên quan.",
  SERVER_ERROR: "Server trả lỗi retention chưa phân loại; kiểm tra correlation id và audit."
};

function retentionIssue(code: RetentionGateReasonCode, message = retentionGateReasonMessages[code]): RetentionGateIssue {
  return { code, message };
}

function retentionIssueWithServerDetail(code: RetentionGateReasonCode, detail?: string) {
  const base = retentionGateReasonMessages[code];
  return retentionIssue(code, detail?.trim() ? `${base} Server detail: ${detail.trim()}` : base);
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
    const parsed = Number.parseInt((data as ErrorDtoLike).statusCode ?? "", 10);
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

const retentionServerErrorCodeMap: Partial<Record<string, RetentionGateReasonCode>> = {
  ADMIN_OPERATION_RATE_LIMITED: "SERVER_RATE_LIMITED",
  RETENTION_OPERATOR_REQUIRED: "AUTH_CONTEXT_UNRESOLVED",
  RETENTION_ADMIN_FORBIDDEN: "RBAC_RETENTION_ADMIN_REQUIRED",
  RETENTION_REVIEW_FORBIDDEN: "RBAC_REVIEW_REQUIRED",
  RETENTION_PLATFORM_ADMIN_REQUIRED: "GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN",
  RETENTION_EXECUTION_DISABLED: "EXECUTION_DISABLED",
  RETENTION_RESTORE_DRILL_ALREADY_EXISTS: "RESTORE_DRILL_ALREADY_EXISTS",
  RETENTION_RESTORE_DRILL_INVALID: "RESTORE_DRILL_INVALID",
  RETENTION_APPROVAL_NOT_FOUND: "SERVER_NOT_FOUND",
  RETENTION_APPROVAL_ALREADY_EXISTS: "APPROVAL_ALREADY_EXISTS",
  RETENTION_APPROVAL_NOT_PENDING: "APPROVAL_NOT_PENDING",
  RETENTION_APPROVAL_NOT_APPROVED: "APPROVAL_NOT_APPROVED",
  RETENTION_APPROVAL_EXPIRED: "APPROVAL_EXPIRED",
  RETENTION_APPROVAL_CONSUMED: "APPROVAL_CONSUMED",
  RETENTION_APPROVAL_NOT_REPLAYABLE: "APPROVAL_CONSUMED",
  RETENTION_SELF_APPROVAL_BLOCKED: "SELF_APPROVAL_BLOCKED",
  RETENTION_SELF_EXECUTION_BLOCKED: "SELF_EXECUTION_BLOCKED",
  RETENTION_DRY_RUN_STALE: "DRY_RUN_STALE",
  RETENTION_RESULT_HASH_MISMATCH: "RESULT_HASH_MISMATCH",
  RETENTION_EXECUTION_IDEMPOTENCY_REUSED: "IDEMPOTENCY_KEY_REUSED",
  RETENTION_EXECUTION_IDEMPOTENCY_IN_PROGRESS: "IDEMPOTENCY_KEY_IN_PROGRESS",
  RETENTION_EXECUTION_IDEMPOTENCY_NOT_REPLAYABLE: "IDEMPOTENCY_KEY_NOT_REPLAYABLE",
  RETENTION_EXECUTION_ACQUIRE_FAILED: "IDEMPOTENCY_KEY_ACQUIRE_FAILED",
  RETENTION_EXECUTION_NOT_STARTED: "EXECUTION_ATTEMPT_BLOCKED",
  RETENTION_EXECUTION_NOT_IN_PROGRESS: "EXECUTION_ATTEMPT_BLOCKED",
  RETENTION_EXECUTION_RESPONSE_NOT_REPLAYABLE: "IDEMPOTENCY_KEY_NOT_REPLAYABLE"
};

export function retentionServerGateIssues(error: unknown): RetentionGateIssue[] {
  const status = errorStatus(error);
  const detail = errorDetail(error);
  const mappedCode = errorCode(error);
  const normalized = normalizedDetail(error);

  if (mappedCode) {
    const mappedIssue = retentionServerErrorCodeMap[mappedCode];
    if (mappedIssue) return [retentionIssueWithServerDetail(mappedIssue, detail)];
  }

  if (status === 400) return [retentionIssueWithServerDetail("SERVER_VALIDATION_FAILED", detail)];
  if (status === 429) return [retentionIssueWithServerDetail("SERVER_RATE_LIMITED", detail)];
  if (status === 403) {
    if (normalized.includes("review")) return [retentionIssueWithServerDetail("RBAC_REVIEW_REQUIRED", detail)];
    if (normalized.includes("platform") || normalized.includes("global")) {
      return [retentionIssueWithServerDetail("GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN", detail)];
    }
    if (normalized.includes("admin") || normalized.includes("manage")) {
      return [retentionIssueWithServerDetail("RBAC_RETENTION_ADMIN_REQUIRED", detail)];
    }
    return [retentionIssueWithServerDetail("SERVER_FORBIDDEN", detail)];
  }
  if (status === 404) return [retentionIssueWithServerDetail("SERVER_NOT_FOUND", detail)];
  if (status === 409) {
    if (normalized.includes("not pending")) return [retentionIssueWithServerDetail("APPROVAL_NOT_PENDING", detail)];
    if (normalized.includes("not approved")) return [retentionIssueWithServerDetail("APPROVAL_NOT_APPROVED", detail)];
    if (normalized.includes("expired")) return [retentionIssueWithServerDetail("APPROVAL_EXPIRED", detail)];
    if (normalized.includes("restore drill")) return [retentionIssueWithServerDetail("RESTORE_DRILL_INVALID", detail)];
    if (normalized.includes("already exists")) return [retentionIssueWithServerDetail("APPROVAL_ALREADY_EXISTS", detail)];
    if (normalized.includes("already executed") || normalized.includes("already has an execution")) {
      return [retentionIssueWithServerDetail("APPROVAL_CONSUMED", detail)];
    }
    if (normalized.includes("stale")) return [retentionIssueWithServerDetail("DRY_RUN_STALE", detail)];
    if (normalized.includes("no longer matches")) return [retentionIssueWithServerDetail("RESULT_HASH_MISMATCH", detail)];
    if (normalized.includes("idempotency key was reused")) return [retentionIssueWithServerDetail("IDEMPOTENCY_KEY_REUSED", detail)];
    if (normalized.includes("already in progress")) return [retentionIssueWithServerDetail("IDEMPOTENCY_KEY_IN_PROGRESS", detail)];
    if (normalized.includes("not replayable")) return [retentionIssueWithServerDetail("IDEMPOTENCY_KEY_NOT_REPLAYABLE", detail)];
    return [retentionIssueWithServerDetail("SERVER_CONFLICT", detail)];
  }
  if (status !== undefined && status >= 500) return [retentionIssueWithServerDetail("SERVER_ERROR", detail)];
  return detail ? [retentionIssueWithServerDetail("SERVER_ERROR", detail)] : [];
}

export function timestamp(value?: string | null) {
  if (!value) return undefined;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function isPast(value?: string | null, nowMs = Date.now()) {
  const parsed = timestamp(value);
  return parsed !== undefined && parsed <= nowMs;
}

export function retentionScopeFingerprint(scope: RetentionScopeForm) {
  return JSON.stringify({
    tenantId: scope.tenantId.trim(),
    applicationId: scope.applicationId.trim(),
    policyId: scope.policyId,
    retentionDays: toNumberOrUndefined(scope.retentionDays) ?? "",
    batchLimit: toNumberOrUndefined(scope.batchLimit) ?? ""
  });
}

export function dryRunExpiresAt(dryRun: RetentionDryRunResponse | null) {
  const generated = timestamp(dryRun?.generatedAt);
  return generated === undefined ? undefined : generated + retentionDryRunTtlMinutes * 60_000;
}

export function dryRunExpired(dryRun: RetentionDryRunResponse | null, nowMs = Date.now()) {
  const expiresAt = dryRunExpiresAt(dryRun);
  return expiresAt !== undefined && expiresAt <= nowMs;
}

export function restoreDrillIssues(
  drill: RetentionRestoreDrill | null | undefined,
  expectedRef: string,
  dryRun: RetentionDryRunResponse | null,
  nowMs = Date.now()
) {
  const issues: string[] = [];
  const ref = expectedRef.trim();
  if (!ref) {
    issues.push("Cần restore drill ref.");
    return issues;
  }
  if (!drill || drill.restoreDrillRef !== ref) {
    issues.push("Cần lookup restore drill thành công trước khi request approval.");
    return issues;
  }
  if (drill.status !== "PASSED") {
    issues.push("Restore drill phải PASSED.");
  }
  if (drill.databaseName !== retentionRestoreDatabase) {
    issues.push(`Restore drill phải thuộc ${retentionRestoreDatabase}.`);
  }
  if (!sha256ArtifactPattern.test(drill.artifactHash)) {
    issues.push("Artifact hash phải đúng format sha256:<64-hex>.");
  }
  if (isPast(drill.expiresAt, nowMs)) {
    issues.push("Restore drill đã hết hạn.");
  }
  const drillExpiry = timestamp(drill.expiresAt);
  const dryRunGenerated = timestamp(dryRun?.generatedAt);
  if (drillExpiry !== undefined && dryRunGenerated !== undefined && drillExpiry <= dryRunGenerated) {
    issues.push("Restore drill phải còn hiệu lực sau thời điểm dry-run.");
  }
  return issues;
}

export function restoreFormIssues(form: RestoreDrillForm, nowMs = Date.now()) {
  const issues: string[] = [];
  if (!form.restoreDrillRef.trim()) issues.push("Drill ref là bắt buộc.");
  if (form.databaseName.trim() !== retentionRestoreDatabase) issues.push(`Database phải là ${retentionRestoreDatabase}.`);
  if (!form.backupPath.trim()) issues.push("Backup path là bắt buộc.");
  if (!sha256ArtifactPattern.test(form.artifactHash.trim())) issues.push("Artifact hash phải đúng format sha256:<64-hex>.");
  const checkedAt = timestamp(toIsoDateTime(form.checkedAt));
  const expiresAt = timestamp(toIsoDateTime(form.expiresAt));
  if (checkedAt !== undefined && checkedAt > nowMs) issues.push("Checked at không được ở tương lai.");
  if (checkedAt !== undefined && expiresAt !== undefined && expiresAt <= checkedAt) {
    issues.push("Expires at phải sau checked at.");
  }
  return issues;
}

export function actorMatches(user: RetentionActor, actor?: string | null) {
  if (!user || !actor) return false;
  const normalized = actor.trim().toLowerCase();
  return [String(user.id), user.email, user.fullName]
    .filter(Boolean)
    .map((item) => item.trim().toLowerCase())
    .includes(normalized);
}

export function hasRetentionActor(user: RetentionActor) {
  if (!user) return false;
  return [
    user.id === undefined || user.id === null ? "" : String(user.id),
    user.email ?? "",
    user.fullName ?? ""
  ].some((item) => item.trim().length > 0);
}

export function retentionActorRole(user: RetentionActor) {
  return user?.role?.trim().toUpperCase() ?? "";
}

export function retentionScopeLabel(approval?: RetentionApproval | null) {
  return approval?.tenantId && approval.applicationId ? "application" : "global";
}

export function hasRetentionReviewRole(user: RetentionActor, approval?: RetentionApproval | null) {
  const role = retentionActorRole(user);
  if (!role) return false;
  if (retentionScopeLabel(approval) === "global") {
    return role === "ADMIN";
  }
  return ["ADMIN", "ORG_ADMIN", "INCENTIVE_ADMIN", "INCENTIVE_REVIEWER"].includes(role);
}

export function hasRetentionAdminRole(user: RetentionActor, approval?: RetentionApproval | null) {
  const role = retentionActorRole(user);
  if (!role) return false;
  if (retentionScopeLabel(approval) === "global") {
    return role === "ADMIN";
  }
  return ["ADMIN", "ORG_ADMIN", "INCENTIVE_ADMIN"].includes(role);
}

export function approvalReady(approval?: RetentionApproval | null) {
  return approval?.status === "APPROVED";
}

export function retentionApprovalDecisionGate(
  approval: RetentionApproval | null,
  user: RetentionActor,
  nowMs = Date.now()
) {
  const issues: RetentionGateIssue[] = [];
  if (!approval?.approvalId) issues.push(retentionIssue("APPROVAL_REQUIRED"));
  if (!hasRetentionActor(user)) issues.push(retentionIssue("AUTH_CONTEXT_UNRESOLVED"));
  if (approval?.approvalId && !hasRetentionReviewRole(user, approval)) {
    issues.push(
      retentionScopeLabel(approval) === "global"
        ? retentionIssue("GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN", "Global retention approval yêu cầu platform role ADMIN.")
        : retentionIssue("RBAC_REVIEW_REQUIRED")
    );
  }
  if (approval?.approvalId && approval.status !== "PENDING_APPROVAL") {
    issues.push(retentionIssue("APPROVAL_NOT_PENDING"));
  }
  if (isPast(approval?.expiresAt, nowMs)) issues.push(retentionIssue("APPROVAL_EXPIRED"));
  if (actorMatches(user, approval?.requestedBy)) issues.push(retentionIssue("SELF_APPROVAL_BLOCKED"));
  return { allowed: issues.length === 0, issues };
}

export function retentionApprovalDecisionIssues(
  approval: RetentionApproval | null,
  user: RetentionActor,
  nowMs = Date.now()
) {
  return retentionApprovalDecisionGate(approval, user, nowMs).issues.map((issue) => issue.message);
}

export function canDecideRetentionApproval(approval: RetentionApproval | null, user: RetentionActor, nowMs = Date.now()) {
  return retentionApprovalDecisionGate(approval, user, nowMs).allowed;
}

export function retentionExecutionConsumed(
  approval: RetentionApproval | null,
  execution?: RetentionExecutionResponse | null
) {
  return Boolean(
    execution || approval?.executedAt || approval?.status === "EXECUTED" || approval?.status === "EXECUTION_FAILED"
  );
}

export function canExecuteRetentionApproval({
  approval,
  user,
  execution,
  executionAttemptBlocked,
  nowMs = Date.now()
}: {
  approval: RetentionApproval | null;
  user: RetentionActor;
  execution?: RetentionExecutionResponse | null;
  executionAttemptBlocked: boolean;
  nowMs?: number;
}) {
  return retentionExecutionGate({ approval, user, execution, executionAttemptBlocked, nowMs }).allowed;
}

export function retentionExecutionGate({
  approval,
  user,
  execution,
  executionAttemptBlocked,
  nowMs = Date.now()
}: {
  approval: RetentionApproval | null;
  user: RetentionActor;
  execution?: RetentionExecutionResponse | null;
  executionAttemptBlocked: boolean;
  nowMs?: number;
}) {
  const issues: RetentionGateIssue[] = [];
  if (!approval?.approvalId) issues.push(retentionIssue("APPROVAL_REQUIRED"));
  if (!hasRetentionActor(user)) issues.push(retentionIssue("AUTH_CONTEXT_UNRESOLVED"));
  if (approval?.approvalId && !hasRetentionAdminRole(user, approval)) {
    issues.push(
      retentionScopeLabel(approval) === "global"
        ? retentionIssue("GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN", "Global retention execution yêu cầu platform role ADMIN.")
        : retentionIssue("RBAC_RETENTION_ADMIN_REQUIRED")
    );
  }
  if (approval?.approvalId && !approvalReady(approval)) issues.push(retentionIssue("APPROVAL_NOT_APPROVED"));
  if (isPast(approval?.expiresAt, nowMs)) issues.push(retentionIssue("APPROVAL_EXPIRED"));
  if (retentionExecutionConsumed(approval, execution)) {
    issues.push(retentionIssue("APPROVAL_CONSUMED"));
  }
  if (executionAttemptBlocked) issues.push(retentionIssue("EXECUTION_ATTEMPT_BLOCKED"));
  if (actorMatches(user, approval?.approvedBy)) issues.push(retentionIssue("SELF_EXECUTION_BLOCKED"));
  return { allowed: issues.length === 0, issues };
}

export function retentionExecutionIssues({
  approval,
  user,
  execution,
  executionAttemptBlocked,
  nowMs = Date.now()
}: {
  approval: RetentionApproval | null;
  user: RetentionActor;
  execution?: RetentionExecutionResponse | null;
  executionAttemptBlocked: boolean;
  nowMs?: number;
}) {
  return retentionExecutionGate({ approval, user, execution, executionAttemptBlocked, nowMs }).issues.map((issue) => issue.message);
}
