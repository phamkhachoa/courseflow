import { describe, expect, it } from "vitest";
import { compactId, splitCommaList, statusLabel, toNumberOrUndefined } from "./labels";
import { parseSpecList } from "./json";
import { retentionOperationId } from "./api";
import {
  isActionableDeadLetterStatus,
  isOpenDeadLetterStatus,
  loyaltyDltOpsFilters,
  outboxDltOpsFilters
} from "./ops-console-helpers";
import { parseRestoreDrillEvidenceJson } from "./retention-evidence";
import {
  couponImportApprovalDecisionGate,
  couponImportApprovalRequestGate,
  couponImportCommitGate,
  couponImportDryRunGate,
  couponImportServerGateIssues
} from "./coupon-gates";
import {
  canDecideRetentionApproval,
  canExecuteRetentionApproval,
  dryRunExpired,
  restoreDrillIssues,
  retentionApprovalDecisionGate,
  retentionApprovalDecisionIssues,
  retentionExecutionConsumed,
  retentionExecutionGate,
  retentionExecutionIssues,
  retentionServerGateIssues,
  retentionScopeFingerprint
} from "./retention-gates";
import type {
  CouponImportApproval,
  CouponImportDryRunResponse,
  RetentionApproval,
  RetentionDryRunResponse,
  RetentionRestoreDrill
} from "./types";

const fixedNow = Date.parse("2026-06-14T10:00:00Z");
const validHash = `sha256:${"a".repeat(64)}`;
const couponCsv = new File(["code\nSAVE10\n"], "coupons.csv", { type: "text/csv" });

const retentionDryRun: RetentionDryRunResponse = {
  dryRunId: "dry-run-1",
  resultHash: validHash,
  dryRun: true,
  nonDestructive: true,
  tenantId: "courseflow",
  applicationId: "lms",
  generatedAt: "2026-06-14T09:30:00Z",
  results: [
    {
      policyId: "terminal-reservation-request-snapshots",
      policyVersion: "v1",
      targetDataset: "promotion_reservation_request_snapshots",
      actionType: "REDACT",
      cutoff: "2026-05-15T09:30:00Z",
      retentionDays: 30,
      eligibleCount: 8,
      blockedCount: 0,
      batchLimit: 500,
      destructiveExecutionSupported: true,
      resultHash: validHash
    }
  ],
  warnings: []
};

const passedRestoreDrill: RetentionRestoreDrill = {
  id: "restore-drill-id",
  restoreDrillRef: "restore-drill-cf_promotion-20260614",
  databaseName: "cf_promotion",
  backupPath: "/tmp/backup/cf_promotion.dump",
  artifactHash: validHash,
  status: "PASSED",
  checkedAt: "2026-06-14T09:00:00Z",
  expiresAt: "2026-06-14T11:00:00Z",
  createdBy: "ops@example.com",
  createdAt: "2026-06-14T09:00:01Z"
};

const couponDryRun: CouponImportDryRunResponse = {
  dryRunId: "coupon-dry-run-1",
  campaignId: "campaign-1",
  dryRun: true,
  requestedRows: 1,
  validRows: 1,
  invalidRows: 0,
  duplicateInFileRows: 0,
  duplicateExistingRows: 0,
  storageInventoryReady: true,
  commitReady: true,
  resultHash: validHash,
  generatedAt: "2026-06-14T09:30:00Z",
  warnings: [],
  issues: [],
  sampleRows: []
};

const pendingCouponApproval: CouponImportApproval = {
  approvalId: "coupon-approval-1",
  status: "PENDING_APPROVAL",
  dryRunId: couponDryRun.dryRunId,
  campaignId: couponDryRun.campaignId,
  approvedResultHash: couponDryRun.resultHash,
  requestedRows: 1,
  validRows: 1,
  invalidRows: 0,
  duplicateInFileRows: 0,
  duplicateExistingRows: 0,
  storageInventoryReady: true,
  commitReady: true,
  reason: "bulk import",
  changeTicket: "CHG-1",
  requestedBy: "operator@example.com",
  approvedBy: null,
  rejectedBy: null,
  committedBy: null,
  expiresAt: "2026-06-14T11:00:00Z",
  createdAt: "2026-06-14T09:30:00Z"
};

const approvedRetention: RetentionApproval = {
  approvalId: "approval-1",
  status: "APPROVED",
  policyId: "terminal-reservation-request-snapshots",
  policyVersion: "v1",
  targetDataset: "promotion_reservation_request_snapshots",
  tenantId: "courseflow",
  applicationId: "lms",
  asOf: "2026-06-14T09:30:00Z",
  cutoff: "2026-05-15T09:30:00Z",
  retentionDays: 30,
  dryRunId: "dry-run-1",
  approvedResultHash: validHash,
  eligibleCount: 8,
  batchLimit: 500,
  restoreDrillRef: "restore-drill-cf_promotion-20260614",
  changeTicket: "CHG-42",
  reason: "privacy redaction",
  requestedBy: "requester@example.com",
  approvedBy: "reviewer@example.com",
  expiresAt: "2026-06-14T11:00:00Z",
  createdAt: "2026-06-14T09:31:00Z",
  approvedAt: "2026-06-14T09:45:00Z"
};

describe("incentive admin helpers", () => {
  it("parses rule/action JSON specs with type validation", () => {
    const specs = parseSpecList('[{"type":"MIN_ORDER_AMOUNT","parameters":{"amount":100}}]', "Rules");

    expect(specs).toEqual([{ type: "MIN_ORDER_AMOUNT", parameters: { amount: 100 } }]);
  });

  it("rejects malformed JSON specs before sending to backend", () => {
    expect(() => parseSpecList('{"type":"ORDER_FIXED_OFF"}', "Actions")).toThrow("Actions phải là một mảng JSON");
    expect(() => parseSpecList("[{}]", "Actions")).toThrow("Actions[0] phải có trường type");
  });

  it("formats operational labels and compact identifiers", () => {
    expect(statusLabel("SUBMITTED")).toBe("Chờ duyệt");
    expect(statusLabel("PENDING_APPROVAL")).toBe("Chờ duyệt");
    expect(statusLabel("MISSING_OUTBOX")).toBe("Thiếu outbox");
    expect(statusLabel("EXECUTION_FAILED")).toBe("Execute thất bại");
    expect(compactId("1234567890abcdef")).toBe("12345678...cdef");
    expect(splitCommaList("read, write, ,approve")).toEqual(["read", "write", "approve"]);
    expect(toNumberOrUndefined("25")).toBe(25);
    expect(toNumberOrUndefined("")).toBeUndefined();
  });

  it("generates stable retention operation identifiers with prefixes", () => {
    expect(retentionOperationId("retention-exec")).toMatch(/^retention-exec-/);
    expect(retentionOperationId("corr-retention-exec")).toMatch(/^corr-retention-exec-/);
  });

  it("queries ops console DLT without hiding failed actionable records", () => {
    expect(loyaltyDltOpsFilters({ dltPayloadHash: "sha256:abc", limit: 25 })).toEqual({
      payloadHash: "sha256:abc",
      limit: 25
    });
    expect(outboxDltOpsFilters({
      dltPayloadHash: "sha256:def",
      outboxService: "promotion-service",
      outboxEventType: "PromotionCommitted",
      limit: 50
    }, "enrollment-1")).toEqual({
      service: "promotion-service",
      eventType: "PromotionCommitted",
      aggregateId: "enrollment-1",
      payloadHash: "sha256:def",
      limit: 50
    });
    expect(isOpenDeadLetterStatus("FAILED")).toBe(true);
    expect(isActionableDeadLetterStatus("FAILED")).toBe(true);
    expect(isActionableDeadLetterStatus("DISCARDED")).toBe(false);
  });

  it("parses postgres restore drill evidence into safe restore-drill fields", () => {
    const evidence = parseRestoreDrillEvidenceJson(JSON.stringify({
      artifactType: "postgres_restore_drill_evidence",
      restoreDrillRef: "restore-drill-cf_promotion-20260614100300",
      databaseName: "cf_promotion",
      backupPath: "/tmp/backup/cf_promotion.dump",
      artifactHash: `sha256:${"A".repeat(64)}`,
      status: "PASSED",
      checkedAt: "2026-06-14T10:03:01Z",
      temporaryDatabase: "restore_drill_cf_promotion_20260614100300"
    }));

    expect(evidence).toMatchObject({
      restoreDrillRef: "restore-drill-cf_promotion-20260614100300",
      databaseName: "cf_promotion",
      backupPath: "/tmp/backup/cf_promotion.dump",
      artifactHash: `sha256:${"a".repeat(64)}`,
      status: "PASSED",
      checkedAt: "2026-06-14T10:03:01Z",
      note: "restore-check restore_drill_cf_promotion_20260614100300"
    });
  });

  it("rejects restore drill evidence for the wrong database or malformed hash", () => {
    expect(() =>
      parseRestoreDrillEvidenceJson(JSON.stringify({
        artifactType: "postgres_restore_drill_evidence",
        restoreDrillRef: "restore-drill-cf_access_control",
        databaseName: "cf_access_control",
        backupPath: "/tmp/backup/cf_access_control.dump",
        artifactHash: `sha256:${"a".repeat(64)}`,
        status: "PASSED",
        checkedAt: "2026-06-14T10:03:01Z"
      }))
    ).toThrow("cf_promotion");

    expect(() =>
      parseRestoreDrillEvidenceJson(JSON.stringify({
        artifactType: "postgres_restore_drill_evidence",
        restoreDrillRef: "restore-drill-cf_promotion",
        databaseName: "cf_promotion",
        backupPath: "/tmp/backup/cf_promotion.dump",
        artifactHash: "sha256:not-a-hash",
        status: "PASSED",
        checkedAt: "2026-06-14T10:03:01Z"
      }))
    ).toThrow("sha256");
  });

  it("blocks stale retention dry-runs and detects changed scope fingerprints", () => {
    expect(dryRunExpired(retentionDryRun, Date.parse("2026-06-14T10:31:00Z"))).toBe(true);
    expect(dryRunExpired(retentionDryRun, Date.parse("2026-06-14T10:29:00Z"))).toBe(false);

    const baseScope = {
      tenantId: " courseflow ",
      applicationId: "lms",
      policyId: "terminal-reservation-request-snapshots",
      retentionDays: "30",
      batchLimit: "500"
    };

    expect(retentionScopeFingerprint(baseScope)).toBe(retentionScopeFingerprint({ ...baseScope, tenantId: "courseflow" }));
    expect(retentionScopeFingerprint(baseScope)).not.toBe(retentionScopeFingerprint({ ...baseScope, batchLimit: "1000" }));
  });

  it("requires restore drill evidence to pass database, hash, expiry and dry-run timing gates", () => {
    expect(
      restoreDrillIssues(
        passedRestoreDrill,
        passedRestoreDrill.restoreDrillRef,
        retentionDryRun,
        fixedNow
      )
    ).toEqual([]);

    expect(
      restoreDrillIssues(
        { ...passedRestoreDrill, expiresAt: "2026-06-14T09:45:00Z" },
        passedRestoreDrill.restoreDrillRef,
        retentionDryRun,
        fixedNow
      ).join(" ")
    ).toContain("hết hạn");

    expect(
      restoreDrillIssues(
        { ...passedRestoreDrill, databaseName: "cf_access_control", artifactHash: "sha256:not-a-hash" },
        passedRestoreDrill.restoreDrillRef,
        retentionDryRun,
        fixedNow
      ).join(" ")
    ).toContain("cf_promotion");

    expect(
      restoreDrillIssues(null, passedRestoreDrill.restoreDrillRef, retentionDryRun, fixedNow).join(" ")
    ).toContain("lookup restore drill");
  });

  it("enforces two-person retention approval decisions", () => {
    const requester = { id: 7, email: "requester@example.com", fullName: "Requester User", role: "INCENTIVE_REVIEWER" };
    const reviewer = { id: 8, email: "reviewer@example.com", fullName: "Reviewer User", role: "INCENTIVE_REVIEWER" };
    const pendingApproval = { ...approvedRetention, status: "PENDING_APPROVAL", approvedBy: null };

    expect(canDecideRetentionApproval(pendingApproval, requester, fixedNow)).toBe(false);
    expect(canDecideRetentionApproval(pendingApproval, reviewer, fixedNow)).toBe(true);
    expect(canDecideRetentionApproval({ ...pendingApproval, status: "REJECTED" }, reviewer, fixedNow)).toBe(false);
    expect(canDecideRetentionApproval({ ...pendingApproval, expiresAt: "2026-06-14T09:59:59Z" }, reviewer, fixedNow)).toBe(false);
    expect(canDecideRetentionApproval(pendingApproval, null, fixedNow)).toBe(false);
    expect(retentionApprovalDecisionIssues(null, reviewer, fixedNow).join(" "))
      .not.toContain("Global retention approval");
    expect(retentionApprovalDecisionIssues(pendingApproval, { ...reviewer, role: "STUDENT" }, fixedNow).join(" "))
      .toContain("Review approval yêu cầu");
    expect(
      retentionApprovalDecisionGate(pendingApproval, { ...reviewer, role: "STUDENT" }, fixedNow).issues.map(
        (issue) => issue.code
      )
    ).toContain("RBAC_REVIEW_REQUIRED");
    expect(retentionApprovalDecisionGate({ ...pendingApproval, tenantId: null, applicationId: null }, reviewer, fixedNow).issues)
      .toContainEqual(expect.objectContaining({ code: "GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN" }));
    expect(retentionApprovalDecisionGate(pendingApproval, null, fixedNow).issues)
      .toContainEqual(expect.objectContaining({ code: "AUTH_CONTEXT_UNRESOLVED" }));
  });

  it("prevents approver self-execution, expired approvals, consumed approvals and unsafe retries", () => {
    const reviewer = { id: 8, email: "reviewer@example.com", fullName: "Reviewer User", role: "INCENTIVE_REVIEWER" };
    const operator = { id: 9, email: "ops@example.com", fullName: "Ops User", role: "INCENTIVE_ADMIN" };

    expect(
      canExecuteRetentionApproval({
        approval: approvedRetention,
        user: operator,
        executionAttemptBlocked: false,
        nowMs: fixedNow
      })
    ).toBe(true);

    expect(
      canExecuteRetentionApproval({
        approval: approvedRetention,
        user: reviewer,
        executionAttemptBlocked: false,
        nowMs: fixedNow
      })
    ).toBe(false);

    expect(
      canExecuteRetentionApproval({
        approval: approvedRetention,
        user: null,
        executionAttemptBlocked: false,
        nowMs: fixedNow
      })
    ).toBe(false);

    expect(
      retentionExecutionIssues({
        approval: approvedRetention,
        user: { ...operator, role: "INCENTIVE_REVIEWER" },
        executionAttemptBlocked: false,
        nowMs: fixedNow
      }).join(" ")
    ).toContain("Execution destructive retention yêu cầu");
    expect(
      retentionExecutionGate({
        approval: approvedRetention,
        user: { ...operator, role: "INCENTIVE_REVIEWER" },
        executionAttemptBlocked: false,
        nowMs: fixedNow
      }).issues
    ).toContainEqual(expect.objectContaining({ code: "RBAC_RETENTION_ADMIN_REQUIRED" }));
    expect(
      retentionExecutionIssues({
        approval: null,
        user: operator,
        executionAttemptBlocked: false,
        nowMs: fixedNow
      }).join(" ")
    ).not.toContain("Global retention execution");

    expect(
      canExecuteRetentionApproval({
        approval: { ...approvedRetention, expiresAt: "2026-06-14T09:59:59Z" },
        user: operator,
        executionAttemptBlocked: false,
        nowMs: fixedNow
      })
    ).toBe(false);

    expect(
      canExecuteRetentionApproval({
        approval: approvedRetention,
        user: operator,
        executionAttemptBlocked: true,
        nowMs: fixedNow
      })
    ).toBe(false);

    expect(retentionExecutionConsumed({ ...approvedRetention, status: "EXECUTION_FAILED" })).toBe(true);
    expect(retentionExecutionConsumed({ ...approvedRetention, executedAt: "2026-06-14T10:05:00Z" })).toBe(true);
    expect(
      retentionExecutionGate({
        approval: { ...approvedRetention, executedAt: "2026-06-14T10:05:00Z" },
        user: operator,
        executionAttemptBlocked: false,
        nowMs: fixedNow
      }).issues
    ).toContainEqual(expect.objectContaining({ code: "APPROVAL_CONSUMED" }));
  });

  it("allows coupon import operators to manage but not review approvals", () => {
    const operator = { id: 10, email: "operator@example.com", fullName: "Coupon Operator", role: "INCENTIVE_OPERATOR" };
    const reviewer = { id: 11, email: "reviewer@example.com", fullName: "Coupon Reviewer", role: "INCENTIVE_REVIEWER" };

    expect(couponImportDryRunGate({
      user: operator,
      campaignId: "campaign-1",
      file: couponCsv,
      fileLooksCsv: true
    }).allowed).toBe(true);

    expect(couponImportApprovalRequestGate({
      dryRun: couponDryRun,
      user: operator,
      dryRunStale: false,
      file: couponCsv,
      reason: "bulk import",
      changeTicket: "CHG-1"
    }).allowed).toBe(true);

    expect(couponImportApprovalDecisionGate(pendingCouponApproval, operator, fixedNow).issues)
      .toContainEqual(expect.objectContaining({ code: "RBAC_REVIEW_REQUIRED" }));

    expect(couponImportApprovalDecisionGate(pendingCouponApproval, reviewer, fixedNow).allowed).toBe(true);
  });

  it("enforces coupon import commit maker-checker and form readiness", () => {
    const operator = { id: 10, email: "operator@example.com", fullName: "Coupon Operator", role: "INCENTIVE_OPERATOR" };
    const approver = { id: 11, email: "reviewer@example.com", fullName: "Coupon Reviewer", role: "INCENTIVE_REVIEWER" };
    const approvedCouponApproval = {
      ...pendingCouponApproval,
      status: "APPROVED",
      approvedBy: "reviewer@example.com",
      approvedAt: "2026-06-14T10:05:00Z"
    };

    expect(couponImportCommitGate({
      approval: approvedCouponApproval,
      user: operator,
      dryRunStale: false,
      file: couponCsv,
      idempotencyKey: "coupon-import-commit-1",
      correlationId: "corr-coupon-import-commit-1",
      confirm: true,
      nowMs: fixedNow
    }).allowed).toBe(true);

    expect(couponImportCommitGate({
      approval: approvedCouponApproval,
      user: approver,
      dryRunStale: false,
      file: couponCsv,
      idempotencyKey: "coupon-import-commit-1",
      correlationId: "corr-coupon-import-commit-1",
      confirm: true,
      nowMs: fixedNow
    }).issues).toContainEqual(expect.objectContaining({ code: "RBAC_COUPON_MANAGE_REQUIRED" }));

    expect(couponImportCommitGate({
      approval: approvedCouponApproval,
      user: operator,
      dryRunStale: true,
      file: null,
      idempotencyKey: "",
      correlationId: "",
      confirm: false,
      nowMs: fixedNow
    }).issues.map((issue) => issue.code)).toEqual(expect.arrayContaining([
      "DRY_RUN_STALE",
      "FILE_REATTACH_REQUIRED",
      "IDEMPOTENCY_KEY_REQUIRED",
      "CORRELATION_ID_REQUIRED",
      "CONFIRM_REQUIRED"
    ]));
  });

  it("maps coupon import server errors to stable reason codes", () => {
    const serverError = (status: number, detail: string, errorCode?: string) => ({
      response: {
        status,
        data: {
          statusCode: `${status} TEST`,
          title: "Server error",
          detail,
          errorCode,
          fieldErrors: []
        }
      }
    });

    expect(couponImportServerGateIssues(serverError(409, "Conflict", "COUPON_IMPORT_APPROVAL_NOT_PENDING")))
      .toContainEqual(expect.objectContaining({ code: "APPROVAL_NOT_PENDING" }));
    expect(couponImportServerGateIssues(serverError(403, "Forbidden", "COUPON_IMPORT_REVIEW_FORBIDDEN")))
      .toContainEqual(expect.objectContaining({ code: "RBAC_REVIEW_REQUIRED" }));
    expect(couponImportServerGateIssues(serverError(429, "Too many requests", "ADMIN_OPERATION_RATE_LIMITED")))
      .toContainEqual(expect.objectContaining({ code: "SERVER_RATE_LIMITED" }));
    expect(couponImportServerGateIssues(serverError(409, "Conflict", "COUPON_IMPORT_PAYLOAD_CHANGED")))
      .toContainEqual(expect.objectContaining({ code: "DRY_RUN_STALE" }));
    expect(couponImportServerGateIssues(serverError(409, "Conflict", "IDEMPOTENCY_KEY_NOT_REPLAYABLE")))
      .toContainEqual(expect.objectContaining({ code: "IDEMPOTENCY_KEY_NOT_REPLAYABLE" }));

    expect(couponImportServerGateIssues(serverError(403, "Not allowed to operate coupon import: courseflow/lms")))
      .toContainEqual(expect.objectContaining({ code: "RBAC_COUPON_MANAGE_REQUIRED" }));
    expect(couponImportServerGateIssues(serverError(403, "Not allowed to review incentive campaign: courseflow/lms")))
      .toContainEqual(expect.objectContaining({ code: "RBAC_REVIEW_REQUIRED" }));
    expect(couponImportServerGateIssues(serverError(429, "Promotion admin operation rate limit exceeded")))
      .toContainEqual(expect.objectContaining({ code: "SERVER_RATE_LIMITED" }));
    expect(couponImportServerGateIssues(serverError(409, "Coupon import dry-run result hash no longer matches")))
      .toContainEqual(expect.objectContaining({ code: "RESULT_HASH_MISMATCH" }));
    expect(couponImportServerGateIssues(serverError(409, "Idempotency key was reused with a different payload")))
      .toContainEqual(expect.objectContaining({ code: "IDEMPOTENCY_KEY_REUSED" }));
  });

  it("maps retention server errors to stable reason codes", () => {
    const serverError = (status: number, detail: string, errorCode?: string) => ({
      response: {
        status,
        data: {
          statusCode: `${status} TEST`,
          title: "Server error",
          detail,
          errorCode,
          fieldErrors: []
        }
      }
    });

    expect(retentionServerGateIssues(serverError(403, "Forbidden", "RETENTION_REVIEW_FORBIDDEN")))
      .toContainEqual(expect.objectContaining({ code: "RBAC_REVIEW_REQUIRED" }));
    expect(retentionServerGateIssues(serverError(403, "Forbidden", "RETENTION_ADMIN_FORBIDDEN")))
      .toContainEqual(expect.objectContaining({ code: "RBAC_RETENTION_ADMIN_REQUIRED" }));
    expect(retentionServerGateIssues(serverError(403, "Forbidden", "RETENTION_PLATFORM_ADMIN_REQUIRED")))
      .toContainEqual(expect.objectContaining({ code: "GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN" }));
    expect(retentionServerGateIssues(serverError(409, "Conflict", "RETENTION_RESTORE_DRILL_INVALID")))
      .toContainEqual(expect.objectContaining({ code: "RESTORE_DRILL_INVALID" }));
    expect(retentionServerGateIssues(serverError(409, "Conflict", "RETENTION_APPROVAL_CONSUMED")))
      .toContainEqual(expect.objectContaining({ code: "APPROVAL_CONSUMED" }));
    expect(retentionServerGateIssues(serverError(409, "Conflict", "RETENTION_EXECUTION_IDEMPOTENCY_REUSED")))
      .toContainEqual(expect.objectContaining({ code: "IDEMPOTENCY_KEY_REUSED" }));
    expect(retentionServerGateIssues(serverError(409, "Conflict", "RETENTION_EXECUTION_IDEMPOTENCY_IN_PROGRESS")))
      .toContainEqual(expect.objectContaining({ code: "IDEMPOTENCY_KEY_IN_PROGRESS" }));
    expect(retentionServerGateIssues(serverError(429, "Too many requests", "ADMIN_OPERATION_RATE_LIMITED")))
      .toContainEqual(expect.objectContaining({ code: "SERVER_RATE_LIMITED" }));

    expect(retentionServerGateIssues(serverError(409, "Approved retention dry-run no longer matches current candidates")))
      .toContainEqual(expect.objectContaining({ code: "RESULT_HASH_MISMATCH" }));
  });
});
