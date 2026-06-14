import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ClipboardList,
  Copy,
  FileDown,
  FileCheck2,
  FileSearch,
  RefreshCcw,
  Search,
  ShieldCheck,
  TicketPercent,
  Upload,
  XCircle
} from "lucide-react";
import { queryKeys } from "@/shared/api/query-keys";
import { useAuth } from "@/shared/auth/auth-context";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ConfirmDialog,
  Drawer,
  EmptyState,
  ErrorState,
  FormField,
  Input,
  Notice,
  PageHeader,
  Select,
  Spinner,
  StatCard,
  Table,
  Td,
  Textarea,
  Th,
  Toolbar
} from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import {
  approveCouponImportApproval,
  commitCouponImportApproval,
  exportCouponImportOperation,
  getCouponImportApproval,
  listCouponImportApprovals,
  listCouponImportOperations,
  queryAudit,
  queryReconciliation,
  rejectCouponImportApproval,
  requestCouponImportApproval,
  retentionOperationId,
  runCouponImportDryRun
} from "./api";
import {
  compactId,
  formatDateTime,
  formatDateTimeInput,
  statusLabel,
  statusTone,
  toIsoDateTime,
  toNumberOrUndefined
} from "./labels";
import { formatJson } from "./json";
import {
  couponImportApprovalDecisionGate,
  couponImportApprovalRequestGate,
  couponImportCommitGate,
  couponImportDryRunGate,
  couponImportServerGateIssues
} from "./coupon-gates";
import { IncentiveNav } from "./pages";
import type {
  AuditFilters,
  CouponImportApproval,
  CouponImportApprovalFilters,
  CouponImportCommitResponse,
  CouponImportDryRunResponse,
  CouponImportOperation,
  IncentiveReconciliationEntry,
  IncentiveReconciliationFilters
} from "./types";

type CouponImportForm = {
  campaignId: string;
  file: File | null;
  maxRows: string;
  holderProfileId: string;
  startsAt: string;
  expiresAt: string;
  maxRedemptions: string;
  maxRedemptionsPerProfile: string;
  reason: string;
  changeTicket: string;
  dryRunIdempotencyKey: string;
  correlationId: string;
};

type CommitForm = {
  idempotencyKey: string;
  correlationId: string;
  confirm: boolean;
};

type DryRunVariables = {
  payload: ReturnType<typeof toImportPayload> & { idempotencyKey?: string };
  correlationId: string;
  fingerprint: string;
};

function StatusPill({ value, label }: { value?: string | null; label?: ReactNode }) {
  return <Badge value={value ?? undefined} label={label ?? statusLabel(value)} tone={statusTone(value)} />;
}

function KeyValue({
  label,
  value,
  mono = false
}: {
  label: string;
  value?: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <div className={cn("mt-1 break-words text-sm font-semibold text-slate-800", mono && "font-mono text-xs")}>
        {value ?? "-"}
      </div>
    </div>
  );
}

function JsonBlock({ value, className }: { value: unknown; className?: string }) {
  return (
    <pre
      className={cn(
        "max-h-72 overflow-auto rounded-md border border-slate-200 bg-slate-950 p-3 text-xs leading-5 text-slate-100",
        className
      )}
    >
      {formatJson(value)}
    </pre>
  );
}

function CopyableId({ value, label = "Copy" }: { value?: string | number | null; label?: string }) {
  if (value === undefined || value === null || value === "") return <span>-</span>;
  const text = String(value);
  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <span className="truncate font-mono text-xs">{compactId(text)}</span>
      <Button variant="ghost" size="xs" className="shrink-0" onClick={() => copyText(text)} aria-label={label}>
        <Copy size={13} />
      </Button>
    </span>
  );
}

function copyText(value?: string | null) {
  if (!value) return;
  void navigator.clipboard?.writeText(value);
}

function downloadTextFile(filename: string, contentType: string, content: string) {
  const blob = new Blob([content], { type: contentType || "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename || "coupon-import-operation.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function gateIssueTitle(issues: { message: string }[]) {
  return issues.map((issue) => issue.message).join(" ");
}

function GateIssues({ issues }: { issues: { code: string; message: string }[] }) {
  if (!issues.length) return null;
  return (
    <div className="space-y-2">
      {issues.map((issue) => (
        <div key={issue.code} className="flex flex-wrap items-start gap-2">
          <Badge label={issue.code} tone="slate" className="font-mono" />
          <span>{issue.message}</span>
        </div>
      ))}
    </div>
  );
}

function ServerGateErrorNotice({ error, title = "Server gate" }: { error: unknown; title?: string }) {
  const issues = couponImportServerGateIssues(error);
  if (!issues.length) return <ErrorState error={error} />;
  return (
    <Notice tone="danger" title={title}>
      <GateIssues issues={issues} />
    </Notice>
  );
}

function fileLabel(file: File | null) {
  if (!file) return "Chưa chọn file";
  const kb = Math.max(1, Math.round(file.size / 1024));
  return `${file.name} · ${kb.toLocaleString()} KB`;
}

function fileLooksCsv(file: File | null) {
  if (!file) return false;
  return file.name.toLowerCase().endsWith(".csv") || file.type === "text/csv" || file.type === "application/vnd.ms-excel";
}

function couponImportFingerprint(form: CouponImportForm) {
  const file = form.file;
  return JSON.stringify({
    campaignId: form.campaignId.trim(),
    fileName: file?.name,
    fileSize: file?.size,
    fileModified: file?.lastModified,
    maxRows: form.maxRows.trim(),
    holderProfileId: form.holderProfileId.trim(),
    startsAt: form.startsAt,
    expiresAt: form.expiresAt,
    maxRedemptions: form.maxRedemptions.trim(),
    maxRedemptionsPerProfile: form.maxRedemptionsPerProfile.trim()
  });
}

function hasReconciliationScope(filters: IncentiveReconciliationFilters) {
  return Boolean(
    filters.tenantId?.trim() &&
      filters.applicationId?.trim() &&
      (
        filters.profileId?.trim() ||
        filters.externalReference?.trim() ||
        filters.campaignId?.trim() ||
        filters.couponId?.trim() ||
        filters.redemptionId?.trim() ||
        filters.reservationId?.trim() ||
        filters.entryType?.trim() ||
        filters.from ||
        filters.to
      )
  );
}

function toImportPayload(form: CouponImportForm) {
  if (!form.file) throw new Error("Cần chọn file CSV");
  if (!form.campaignId.trim()) throw new Error("Cần campaignId");
  return {
    campaignId: form.campaignId.trim(),
    file: form.file,
    maxRows: toNumberOrUndefined(form.maxRows),
    holderProfileId: form.holderProfileId.trim() || undefined,
    startsAt: toIsoDateTime(form.startsAt),
    expiresAt: toIsoDateTime(form.expiresAt),
    maxRedemptions: toNumberOrUndefined(form.maxRedemptions),
    maxRedemptionsPerProfile: toNumberOrUndefined(form.maxRedemptionsPerProfile)
  };
}

function makeCouponImportForm(): CouponImportForm {
  return {
    campaignId: "",
    file: null,
    maxRows: "5000",
    holderProfileId: "",
    startsAt: "",
    expiresAt: "",
    maxRedemptions: "",
    maxRedemptionsPerProfile: "",
    reason: "bulk coupon import",
    changeTicket: "",
    dryRunIdempotencyKey: retentionOperationId("coupon-import-dry-run"),
    correlationId: retentionOperationId("corr-coupon-import")
  };
}

function makeCommitForm(): CommitForm {
  return {
    idempotencyKey: retentionOperationId("coupon-import-commit"),
    correlationId: retentionOperationId("corr-coupon-import-commit"),
    confirm: false
  };
}

function OperationSteps({
  fileScopeReady,
  dryRun,
  approval,
  commit
}: {
  fileScopeReady: boolean;
  dryRun: CouponImportDryRunResponse | null;
  approval: CouponImportApproval | null;
  commit: CouponImportCommitResponse | null;
}) {
  const steps = [
    { label: "File & scope", done: fileScopeReady, active: !fileScopeReady },
    { label: "Dry-run", done: Boolean(dryRun), active: fileScopeReady && !dryRun },
    { label: "Approval", done: Boolean(approval), active: Boolean(dryRun && !approval) },
    { label: "Commit", done: Boolean(commit), active: Boolean(approval && !commit) }
  ];
  return (
    <div className="grid gap-2 md:grid-cols-4">
      {steps.map((step, index) => (
        <div
          key={step.label}
          className={cn(
            "flex items-center gap-3 rounded-md border px-3 py-2 text-sm font-semibold",
            step.done
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : step.active
                ? "border-brand-200 bg-brand-50 text-brand-800"
                : "border-slate-200 bg-white text-slate-500"
          )}
        >
          <span className="grid size-6 shrink-0 place-items-center rounded-full bg-white text-xs">{index + 1}</span>
          <span>{step.label}</span>
        </div>
      ))}
    </div>
  );
}

function DryRunSummary({ dryRun }: { dryRun: CouponImportDryRunResponse | null }) {
  if (!dryRun) {
    return <EmptyState message="Chạy dry-run để xem summary, issue theo dòng và result hash trước khi request approval." />;
  }
  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Requested rows"
          value={dryRun.requestedRows.toLocaleString()}
          detail={`${dryRun.validRows.toLocaleString()} valid · ${dryRun.invalidRows.toLocaleString()} invalid`}
          icon={<FileSearch size={18} />}
          tone={dryRun.invalidRows > 0 ? "warning" : "success"}
        />
        <StatCard
          label="Duplicate in file"
          value={dryRun.duplicateInFileRows.toLocaleString()}
          detail={`${dryRun.duplicateExistingRows.toLocaleString()} duplicate existing`}
          icon={<ClipboardList size={18} />}
          tone={dryRun.duplicateInFileRows || dryRun.duplicateExistingRows ? "warning" : "neutral"}
        />
        <StatCard
          label="Commit gate"
          value={dryRun.commitReady ? "Ready" : "Blocked"}
          detail={dryRun.storageInventoryReady ? "Storage inventory ready" : "Storage inventory warning"}
          icon={<ShieldCheck size={18} />}
          tone={dryRun.commitReady ? "success" : "danger"}
        />
        <StatCard
          label="Result hash"
          value={compactId(dryRun.resultHash)}
          detail={formatDateTime(dryRun.generatedAt)}
          icon={<FileCheck2 size={18} />}
          tone="brand"
        />
      </div>
      {dryRun.warnings.length > 0 && (
        <Notice tone="warning" title="Dry-run warnings">
          {dryRun.warnings.join(" ")}
        </Notice>
      )}
      <div className="grid gap-4 xl:grid-cols-2">
        <Card variant="muted">
          <CardHeader title="Issues" subtitle="Chỉ hiển thị mask và reason; UI không expose raw coupon code." compact />
          {dryRun.issues.length === 0 ? (
            <EmptyState message="Không có issue trong sample trả về." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Row</Th>
                  <Th>Code mask</Th>
                  <Th>Field</Th>
                  <Th>Reason</Th>
                </tr>
              </thead>
              <tbody>
                {dryRun.issues.slice(0, 25).map((issue) => (
                  <tr key={`${issue.rowNumber}-${issue.reasonCode}-${issue.field ?? "row"}`}>
                    <Td>{issue.rowNumber}</Td>
                    <Td className="font-mono text-xs">{issue.codeMask ?? "-"}</Td>
                    <Td>{issue.field ?? "-"}</Td>
                    <Td>
                      <StatusPill value={issue.reasonCode} label={issue.reasonCode} />
                      <p className="mt-1 text-xs text-slate-500">{issue.message}</p>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
        <Card variant="muted">
          <CardHeader title="Sample rows" subtitle="Preview đã được backend mask/redact." compact />
          {dryRun.sampleRows.length === 0 ? (
            <EmptyState message="Backend chưa trả sample row." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Row</Th>
                  <Th>Status</Th>
                  <Th>Code mask</Th>
                  <Th>Issue codes</Th>
                </tr>
              </thead>
              <tbody>
                {dryRun.sampleRows.map((row) => (
                  <tr key={row.rowNumber}>
                    <Td>{row.rowNumber}</Td>
                    <Td><StatusPill value={row.status} /></Td>
                    <Td className="font-mono text-xs">{row.codeMask ?? "-"}</Td>
                    <Td className="text-xs">{row.issueCodes?.join(", ") || "-"}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>
    </div>
  );
}

function CouponApprovalDetail({
  approval,
  commit,
  onClose
}: {
  approval: CouponImportApproval | null;
  commit: CouponImportCommitResponse | null;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={Boolean(approval)}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={approval ? `Coupon import ${compactId(approval.approvalId)}` : "Coupon import"}
      description={approval ? <StatusPill value={approval.status} /> : undefined}
      className="max-w-3xl"
    >
      {approval && (
        <div className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-2">
            <KeyValue label="Approval ID" value={<CopyableId value={approval.approvalId} />} />
            <KeyValue label="Dry-run ID" value={<CopyableId value={approval.dryRunId} />} />
            <KeyValue label="Campaign" value={<CopyableId value={approval.campaignId} />} />
            <KeyValue label="Result hash" value={<CopyableId value={approval.approvedResultHash} />} />
            <KeyValue label="Requested rows" value={approval.requestedRows.toLocaleString()} />
            <KeyValue label="Valid / Invalid" value={`${approval.validRows.toLocaleString()} / ${approval.invalidRows.toLocaleString()}`} />
            <KeyValue label="Duplicate in file" value={approval.duplicateInFileRows.toLocaleString()} />
            <KeyValue label="Duplicate existing" value={approval.duplicateExistingRows.toLocaleString()} />
            <KeyValue label="Requested by" value={approval.requestedBy ?? "-"} />
            <KeyValue label="Approved by" value={approval.approvedBy ?? "-"} />
            <KeyValue label="Rejected by" value={approval.rejectedBy ?? "-"} />
            <KeyValue label="Committed by" value={approval.committedBy ?? "-"} />
            <KeyValue label="Created" value={formatDateTime(approval.createdAt)} />
            <KeyValue label="Expires" value={formatDateTime(approval.expiresAt)} />
            <KeyValue label="Approved at" value={formatDateTime(approval.approvedAt)} />
            <KeyValue label="Committed at" value={formatDateTime(approval.committedAt)} />
          </div>
          <Notice tone={approval.commitReady ? "success" : "warning"} title="Commit readiness">
            {approval.commitReady
              ? "Dry-run result đủ điều kiện để commit nếu approval còn hiệu lực và file reattach khớp hash."
              : "Approval chưa commit-ready; kiểm tra invalid row, duplicate hoặc storage inventory."}
          </Notice>
          <div className="grid gap-3 md:grid-cols-2">
            <KeyValue label="Reason" value={approval.reason} />
            <KeyValue label="Change ticket" value={approval.changeTicket} />
          </div>
          {commit && (
            <Notice tone={commit.idempotencyReplay ? "info" : "success"} title={commit.idempotencyReplay ? "Commit replay" : "Commit completed"}>
              Import {compactId(commit.importId)} · {commit.importedRows.toLocaleString()} / {commit.requestedRows.toLocaleString()} rows.
            </Notice>
          )}
        </div>
      )}
    </Drawer>
  );
}

export function CouponImportConsolePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<CouponImportForm>(() => makeCouponImportForm());
  const [dryRun, setDryRun] = useState<CouponImportDryRunResponse | null>(null);
  const [dryRunFingerprint, setDryRunFingerprint] = useState<string | null>(null);
  const [approval, setApproval] = useState<CouponImportApproval | null>(null);
  const [approvalLookupId, setApprovalLookupId] = useState("");
  const [decisionNote, setDecisionNote] = useState("");
  const [commitForm, setCommitForm] = useState<CommitForm>(() => makeCommitForm());
  const [commit, setCommit] = useState<CouponImportCommitResponse | null>(null);
  const [commitOpen, setCommitOpen] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<CouponImportApproval | null>(null);
  const [approvalFilters, setApprovalFilters] = useState<CouponImportApprovalFilters>({
    tenantId: "courseflow",
    applicationId: "lms",
    limit: 50
  });
  const [draftApprovalFilters, setDraftApprovalFilters] = useState<CouponImportApprovalFilters>(approvalFilters);

  const currentFingerprint = useMemo(() => couponImportFingerprint(form), [form]);
  const dryRunStale = Boolean(dryRun && dryRunFingerprint && dryRunFingerprint !== currentFingerprint);
  const fileScopeReady = Boolean(form.file && fileLooksCsv(form.file) && form.campaignId.trim());
  const dryRunGate = useMemo(
    () => couponImportDryRunGate({
      user,
      campaignId: form.campaignId,
      file: form.file,
      fileLooksCsv: fileLooksCsv(form.file)
    }),
    [form.campaignId, form.file, user]
  );
  const canRunDryRun = dryRunGate.allowed;
  const approvalRequestGate = useMemo(
    () => couponImportApprovalRequestGate({
      dryRun,
      user,
      dryRunStale,
      file: form.file,
      reason: form.reason,
      changeTicket: form.changeTicket
    }),
    [dryRun, dryRunStale, form.changeTicket, form.file, form.reason, user]
  );
  const canRequestApproval = approvalRequestGate.allowed;
  const decisionGate = useMemo(
    () => (approval ? couponImportApprovalDecisionGate(approval, user) : { allowed: false, issues: [] }),
    [approval, user]
  );
  const canDecideApproval = approval ? decisionGate.allowed : false;
  const commitGate = useMemo(
    () => couponImportCommitGate({
      approval,
      user,
      dryRunStale,
      file: form.file,
      idempotencyKey: commitForm.idempotencyKey,
      correlationId: commitForm.correlationId,
      confirm: commitForm.confirm,
      commit
    }),
    [approval, commit, commitForm.confirm, commitForm.correlationId, commitForm.idempotencyKey, dryRunStale, form.file, user]
  );
  const canCommit = commitGate.allowed;
  const approvalListEnabled = Boolean(approvalFilters.tenantId?.trim() && approvalFilters.applicationId?.trim());
  const approvalAuditFilters = useMemo<AuditFilters>(
    () => ({
      tenantId: approvalFilters.tenantId,
      applicationId: approvalFilters.applicationId,
      aggregateType: approval?.approvalId ? "coupon-import-approval" : undefined,
      aggregateId: approval?.approvalId,
      correlationId: approval?.approvalId ? undefined : form.correlationId,
      limit: 8
    }),
    [approval?.approvalId, approvalFilters.applicationId, approvalFilters.tenantId, form.correlationId]
  );

  const approvalsQuery = useQuery({
    queryKey: queryKeys.incentives.couponImportApprovals(approvalFilters),
    queryFn: () => listCouponImportApprovals(approvalFilters),
    enabled: approvalListEnabled,
    retry: 1
  });
  const operationsQuery = useQuery({
    queryKey: queryKeys.incentives.couponImportOperations({
      tenantId: approvalFilters.tenantId,
      applicationId: approvalFilters.applicationId,
      campaignId: approvalFilters.campaignId,
      limit: approvalFilters.limit ?? 50
    }),
    queryFn: () =>
      listCouponImportOperations({
        tenantId: approvalFilters.tenantId,
        applicationId: approvalFilters.applicationId,
        campaignId: approvalFilters.campaignId,
        limit: approvalFilters.limit ?? 50
      }),
    enabled: approvalListEnabled,
    retry: 1
  });
  const approvalLookup = useQuery({
    queryKey: queryKeys.incentives.couponImportApproval(approvalLookupId),
    queryFn: () => getCouponImportApproval(approvalLookupId.trim()),
    enabled: Boolean(approvalLookupId.trim()),
    retry: 1
  });
  const audit = useQuery({
    queryKey: queryKeys.incentives.audit(approvalAuditFilters),
    queryFn: () => queryAudit(approvalAuditFilters),
    enabled: Boolean(approvalAuditFilters.tenantId && approvalAuditFilters.applicationId),
    retry: 1
  });

  useEffect(() => {
    if (approvalLookup.data) {
      setApproval(approvalLookup.data);
      setSelectedApproval(approvalLookup.data);
      setCommit(null);
    }
  }, [approvalLookup.data]);

  const dryRunMutation = useMutation({
    mutationFn: (variables: DryRunVariables) =>
      runCouponImportDryRun(variables.payload, variables.correlationId),
    onSuccess: (response, variables) => {
      setDryRun(response);
      setDryRunFingerprint(variables.fingerprint);
      setApproval(null);
      setCommit(null);
    }
  });
  const requestApprovalMutation = useMutation({
    mutationFn: () => {
      if (!dryRun) throw new Error("Cần dry-run trước khi request approval");
      return requestCouponImportApproval(
        {
          ...toImportPayload(form),
          dryRunId: dryRun.dryRunId,
          approvedResultHash: dryRun.resultHash,
          reason: form.reason.trim(),
          changeTicket: form.changeTicket.trim()
        },
        form.correlationId
      );
    },
    onSuccess: (response) => {
      setApproval(response);
      setApprovalLookupId(response.approvalId);
      setSelectedApproval(response);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
    }
  });
  const approveMutation = useMutation({
    mutationFn: () => {
      if (!approval?.approvalId) throw new Error("Chưa chọn approval");
      return approveCouponImportApproval(approval.approvalId, { note: decisionNote.trim() || undefined }, form.correlationId);
    },
    onSuccess: (response) => {
      setApproval(response);
      setSelectedApproval(response);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
    }
  });
  const rejectMutation = useMutation({
    mutationFn: () => {
      if (!approval?.approvalId) throw new Error("Chưa chọn approval");
      return rejectCouponImportApproval(approval.approvalId, { note: decisionNote.trim() || undefined }, form.correlationId);
    },
    onSuccess: (response) => {
      setApproval(response);
      setSelectedApproval(response);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
    }
  });
  const commitMutation = useMutation({
    mutationFn: () => {
      if (!approval?.approvalId) throw new Error("Chưa chọn approval");
      return commitCouponImportApproval(
        {
          ...toImportPayload(form),
          approvalId: approval.approvalId,
          dryRunId: approval.dryRunId,
          campaignId: approval.campaignId,
          approvedResultHash: approval.approvedResultHash,
          reason: approval.reason ?? form.reason,
          changeTicket: approval.changeTicket ?? form.changeTicket,
          idempotencyKey: commitForm.idempotencyKey.trim(),
          confirm: commitForm.confirm
        },
        commitForm.correlationId
      );
    },
    onSuccess: (response) => {
      setCommit(response);
      setCommitOpen(false);
      setCommitForm((current) => ({ ...current, confirm: false }));
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
      void approvalLookup.refetch();
    }
  });
  const operationExportMutation = useMutation({
    mutationFn: ({ importId }: { importId: string }) => exportCouponImportOperation(importId),
    onSuccess: (response) => {
      downloadTextFile(response.filename, response.contentType, response.content);
    }
  });

  const approvalItems = approvalsQuery.data ?? [];
  const operationItems = operationsQuery.data?.items ?? [];
  const pendingCount = approvalItems.filter((item) => item.status === "PENDING_APPROVAL").length;
  const approvedCount = approvalItems.filter((item) => item.status === "APPROVED").length;
  const executedCount = operationItems.length || approvalItems.filter((item) => item.status === "EXECUTED" || item.committedAt).length;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Coupon operations"
        title="Coupon import console"
        description="Import coupon theo luồng dry-run, maker-checker approval và commit idempotent. UI chỉ hiển thị mask/hash, không expose raw coupon code."
      />
      <IncentiveNav />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Pending approvals" value={pendingCount.toLocaleString()} detail="Đang chờ reviewer xử lý." icon={<ShieldCheck size={18} />} tone="info" />
        <StatCard label="Commit-ready" value={approvedCount.toLocaleString()} detail="Đã duyệt và chờ commit." icon={<FileCheck2 size={18} />} tone="success" />
        <StatCard label="Executed" value={executedCount.toLocaleString()} detail="Approval đã commit/executed." icon={<CheckCircle2 size={18} />} tone="neutral" />
        <StatCard
          label="Current file"
          value={form.file ? "Attached" : "None"}
          detail={fileLabel(form.file)}
          icon={<Upload size={18} />}
          tone={form.file ? (fileLooksCsv(form.file) ? "brand" : "warning") : "neutral"}
        />
      </div>

      <OperationSteps fileScopeReady={fileScopeReady} dryRun={dryRun} approval={approval} commit={commit} />

      <Card>
        <CardHeader
          title="1. File, scope và dry-run"
          subtitle="Backend validate trùng code, storage inventory, quota/default và trả result hash để chống commit nhầm file."
          actions={
            <Button
              onClick={() =>
                dryRunMutation.mutate({
                  payload: { ...toImportPayload(form), idempotencyKey: form.dryRunIdempotencyKey.trim() || undefined },
                  correlationId: form.correlationId,
                  fingerprint: currentFingerprint
                })
              }
              disabled={dryRunMutation.isPending || !canRunDryRun}
              title={gateIssueTitle(dryRunGate.issues)}
            >
              <RefreshCcw size={16} />
              {dryRunMutation.isPending ? "Đang chạy" : "Run dry-run"}
            </Button>
          }
        />
        <form
          className="grid gap-4 p-4"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            dryRunMutation.mutate({
              payload: { ...toImportPayload(form), idempotencyKey: form.dryRunIdempotencyKey.trim() || undefined },
              correlationId: form.correlationId,
              fingerprint: currentFingerprint
            });
          }}
        >
          <Toolbar>
            <FormField label="Campaign ID" required>
              <Input value={form.campaignId} onChange={(event) => setForm({ ...form, campaignId: event.target.value })} />
            </FormField>
            <FormField label="CSV file" required hint={fileLabel(form.file)}>
              <Input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => setForm({ ...form, file: event.target.files?.[0] ?? null })}
              />
            </FormField>
            <FormField label="Max rows">
              <Input value={form.maxRows} inputMode="numeric" onChange={(event) => setForm({ ...form, maxRows: event.target.value })} />
            </FormField>
            <FormField label="Holder profile">
              <Input value={form.holderProfileId} onChange={(event) => setForm({ ...form, holderProfileId: event.target.value })} />
            </FormField>
          </Toolbar>
          <Toolbar>
            <FormField label="Starts at">
              <Input type="datetime-local" value={form.startsAt} onChange={(event) => setForm({ ...form, startsAt: event.target.value })} />
            </FormField>
            <FormField label="Expires at">
              <Input type="datetime-local" value={form.expiresAt} onChange={(event) => setForm({ ...form, expiresAt: event.target.value })} />
            </FormField>
            <FormField label="Max redemptions">
              <Input value={form.maxRedemptions} inputMode="numeric" onChange={(event) => setForm({ ...form, maxRedemptions: event.target.value })} />
            </FormField>
            <FormField label="Max per profile">
              <Input
                value={form.maxRedemptionsPerProfile}
                inputMode="numeric"
                onChange={(event) => setForm({ ...form, maxRedemptionsPerProfile: event.target.value })}
              />
            </FormField>
          </Toolbar>
          <Toolbar>
            <FormField label="Dry-run idempotency key">
              <Input value={form.dryRunIdempotencyKey} onChange={(event) => setForm({ ...form, dryRunIdempotencyKey: event.target.value })} />
            </FormField>
            <FormField label="Correlation ID">
              <Input value={form.correlationId} onChange={(event) => setForm({ ...form, correlationId: event.target.value })} />
            </FormField>
          </Toolbar>
          {!form.file && <Notice tone="neutral" title="CSV required">Chọn file CSV có cột `code` để backend dry-run. Không paste raw coupon vào UI khác.</Notice>}
          {form.file && !fileLooksCsv(form.file) && (
            <Notice tone="warning" title="File extension warning">File không có đuôi `.csv`; backend vẫn sẽ validate nhưng UI chặn dry-run để giảm thao tác nhầm.</Notice>
          )}
          {!canRunDryRun && (
            <Notice tone="neutral" title="Dry-run gate">
              <GateIssues issues={dryRunGate.issues} />
            </Notice>
          )}
          {dryRunStale && (
            <Notice tone="warning" title="Dry-run stale">
              File hoặc scope đã đổi sau dry-run. Chạy lại dry-run trước khi request approval/commit.
            </Notice>
          )}
          {dryRunMutation.isError && <ServerGateErrorNotice error={dryRunMutation.error} title="Dry-run server gate" />}
          <DryRunSummary dryRun={dryRun} />
        </form>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader title="2. Request và review approval" subtitle="Người request không được tự approve; backend vẫn là guardrail chính." />
          <div className="grid gap-4 p-4">
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Reason" required>
                <Input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
              </FormField>
              <FormField label="Change ticket" required>
                <Input value={form.changeTicket} onChange={(event) => setForm({ ...form, changeTicket: event.target.value })} />
              </FormField>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => requestApprovalMutation.mutate()}
                disabled={!canRequestApproval || requestApprovalMutation.isPending}
                title={gateIssueTitle(approvalRequestGate.issues)}
              >
                <ShieldCheck size={16} />
                {requestApprovalMutation.isPending ? "Đang gửi" : "Request approval"}
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  setForm((current) => ({
                    ...current,
                    dryRunIdempotencyKey: retentionOperationId("coupon-import-dry-run"),
                    correlationId: retentionOperationId("corr-coupon-import")
                  }))
                }
              >
                New dry-run key
              </Button>
            </div>
            {!canRequestApproval && (
              <Notice tone="neutral" title="Approval gate">
                <GateIssues issues={approvalRequestGate.issues} />
              </Notice>
            )}
            {requestApprovalMutation.isError && (
              <ServerGateErrorNotice error={requestApprovalMutation.error} title="Approval request server gate" />
            )}
            {approval && (
              <div className="grid gap-3 rounded-md border border-slate-200 p-3 md:grid-cols-3">
                <KeyValue label="Approval" value={<CopyableId value={approval.approvalId} />} />
                <KeyValue label="Status" value={<StatusPill value={approval.status} />} />
                <KeyValue label="Expires" value={formatDateTime(approval.expiresAt)} />
                <KeyValue label="Requested by" value={approval.requestedBy ?? "-"} />
                <KeyValue label="Approved by" value={approval.approvedBy ?? "-"} />
                <KeyValue label="Result hash" value={<CopyableId value={approval.approvedResultHash} />} />
              </div>
            )}
            {approval && !canDecideApproval && (
              <Notice tone="neutral" title="Reviewer gate">
                <GateIssues issues={decisionGate.issues} />
              </Notice>
            )}
            <FormField label="Reviewer note">
              <Textarea value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)} />
            </FormField>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => approveMutation.mutate()}
                disabled={!canDecideApproval || approveMutation.isPending}
                title={gateIssueTitle(decisionGate.issues)}
              >
                <CheckCircle2 size={16} />
                Approve
              </Button>
              <Button
                variant="danger"
                onClick={() => rejectMutation.mutate()}
                disabled={!canDecideApproval || rejectMutation.isPending}
                title={gateIssueTitle(decisionGate.issues)}
              >
                <XCircle size={16} />
                Reject
              </Button>
            </div>
            {(approveMutation.isError || rejectMutation.isError) && (
              <ServerGateErrorNotice error={approveMutation.error ?? rejectMutation.error} title="Reviewer server gate" />
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="3. Commit gate" subtitle="Commit dùng approval đã duyệt, file reattach và idempotency key ổn định." />
          <div className="grid gap-4 p-4">
            <Notice tone={canCommit ? "warning" : "neutral"} title="Commit readiness">
              {canCommit
                ? "Approval đã đủ điều kiện commit. Backend sẽ so file hash với approved result hash và commit all-or-nothing."
                : (
                  <GateIssues issues={commitGate.issues} />
                )}
            </Notice>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Commit idempotency key" required>
                <Input value={commitForm.idempotencyKey} onChange={(event) => setCommitForm({ ...commitForm, idempotencyKey: event.target.value })} />
              </FormField>
              <FormField label="Commit correlation ID" required>
                <Input value={commitForm.correlationId} onChange={(event) => setCommitForm({ ...commitForm, correlationId: event.target.value })} />
              </FormField>
            </div>
            <div className="flex flex-wrap gap-2">
              <label className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
                <input
                  type="checkbox"
                  className="size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  checked={commitForm.confirm}
                  onChange={(event) => setCommitForm({ ...commitForm, confirm: event.target.checked })}
                />
                Confirm commit
              </label>
              <Button variant="secondary" onClick={() => setCommitForm(makeCommitForm())}>
                New commit key
              </Button>
              <Button variant="secondary" onClick={() => copyText(commitForm.correlationId)}>
                <Copy size={16} />
                Copy correlation
              </Button>
            </div>
            <Button
              variant="danger"
              disabled={!canCommit || commitMutation.isPending}
              title={gateIssueTitle(commitGate.issues)}
              onClick={() => setCommitOpen(true)}
            >
              <TicketPercent size={16} />
              Commit import
            </Button>
            {commitMutation.isError && <ServerGateErrorNotice error={commitMutation.error} title="Commit server gate" />}
            {commit && (
              <Notice tone={commit.idempotencyReplay ? "info" : "success"} title={commit.idempotencyReplay ? "Idempotency replay" : "Commit completed"}>
                Import {compactId(commit.importId)} · {commit.importedRows.toLocaleString()} / {commit.requestedRows.toLocaleString()} rows · hash{" "}
                {compactId(commit.resultHash)}
              </Notice>
            )}
            {commit?.warnings.length ? (
              <Notice tone="warning" title="Commit warnings">
                {commit.warnings.join(" ")}
              </Notice>
            ) : null}
          </div>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader title="Approval queue" subtitle="Bắt buộc tenant/application để tránh truy vấn quá rộng hoặc cross-tenant." />
          <div className="grid gap-4 p-4">
            <Toolbar>
              <FormField label="Tenant" required>
                <Input value={draftApprovalFilters.tenantId ?? ""} onChange={(event) => setDraftApprovalFilters({ ...draftApprovalFilters, tenantId: event.target.value })} />
              </FormField>
              <FormField label="Application" required>
                <Input value={draftApprovalFilters.applicationId ?? ""} onChange={(event) => setDraftApprovalFilters({ ...draftApprovalFilters, applicationId: event.target.value })} />
              </FormField>
              <FormField label="Campaign">
                <Input value={draftApprovalFilters.campaignId ?? ""} onChange={(event) => setDraftApprovalFilters({ ...draftApprovalFilters, campaignId: event.target.value || undefined })} />
              </FormField>
              <FormField label="Status">
                <Select value={draftApprovalFilters.status ?? ""} onChange={(event) => setDraftApprovalFilters({ ...draftApprovalFilters, status: event.target.value || undefined })}>
                  <option value="">All</option>
                  <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
                  <option value="APPROVED">APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                  <option value="EXECUTED">EXECUTED</option>
                </Select>
              </FormField>
              <FormField label="Limit">
                <Input
                  value={String(draftApprovalFilters.limit ?? 50)}
                  inputMode="numeric"
                  onChange={(event) => setDraftApprovalFilters({ ...draftApprovalFilters, limit: toNumberOrUndefined(event.target.value) })}
                />
              </FormField>
              <div className="flex items-end gap-2">
                <Button onClick={() => setApprovalFilters(draftApprovalFilters)}>
                  <Search size={16} />
                  Apply
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    const reset = { tenantId: "courseflow", applicationId: "lms", limit: 50 };
                    setDraftApprovalFilters(reset);
                    setApprovalFilters(reset);
                  }}
                >
                  Reset
                </Button>
              </div>
            </Toolbar>
            {!approvalListEnabled && <Notice tone="warning" title="Scope required">Nhập tenant và application trước khi tải approval queue.</Notice>}
            {approvalsQuery.isLoading && <Spinner />}
            {approvalsQuery.isError && <ErrorState error={approvalsQuery.error} />}
            {approvalsQuery.data && approvalItems.length === 0 && <EmptyState message="Không có coupon import approval phù hợp." />}
            {approvalItems.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Status</Th>
                    <Th>Approval</Th>
                    <Th>Campaign</Th>
                    <Th>Rows</Th>
                    <Th>Created</Th>
                    <Th />
                  </tr>
                </thead>
                <tbody>
                  {approvalItems.map((item) => (
                    <tr key={item.approvalId}>
                      <Td><StatusPill value={item.status} /></Td>
                      <Td><CopyableId value={item.approvalId} /></Td>
                      <Td><CopyableId value={item.campaignId} /></Td>
                      <Td>{item.validRows.toLocaleString()} / {item.requestedRows.toLocaleString()}</Td>
                      <Td>{formatDateTime(item.createdAt)}</Td>
                      <Td>
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() => {
                            setApproval(item);
                            setSelectedApproval(item);
                            setApprovalLookupId(item.approvalId);
                            setCommit(null);
                          }}
                        >
                          Load
                        </Button>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Import operations"
            subtitle="Lịch sử commit all-or-nothing theo cùng tenant/application/campaign scope; không trả raw CSV hoặc idempotency hash."
          />
          <div className="grid gap-4 p-4">
            {operationsQuery.isLoading && <Spinner />}
            {operationsQuery.isError && <ErrorState error={operationsQuery.error} />}
            {operationExportMutation.isError && (
              <ServerGateErrorNotice error={operationExportMutation.error} title="Export server gate" />
            )}
            {operationsQuery.data?.hasMore && (
              <Notice tone="warning" title="Result limited">
                Còn import operation ngoài limit hiện tại. Thu hẹp campaign hoặc tăng limit trong phạm vi cho phép.
              </Notice>
            )}
            {operationsQuery.data && operationItems.length === 0 && <EmptyState message="Chưa có import operation phù hợp với scope hiện tại." />}
            {operationItems.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Status</Th>
                    <Th>Import</Th>
                    <Th>Approval</Th>
                    <Th>Rows</Th>
                    <Th>Ticket</Th>
                    <Th>Correlation</Th>
                    <Th>Committed</Th>
                    <Th />
                  </tr>
                </thead>
                <tbody>
                  {operationItems.map((item: CouponImportOperation) => (
                    <tr key={item.importId}>
                      <Td><StatusPill value={item.status} /></Td>
                      <Td><CopyableId value={item.importId} /></Td>
                      <Td><CopyableId value={item.approvalId} /></Td>
                      <Td>{item.importedRows.toLocaleString()} / {item.requestedRows.toLocaleString()}</Td>
                      <Td>{item.changeTicket}</Td>
                      <Td><CopyableId value={item.correlationId} /></Td>
                      <Td>{formatDateTime(item.createdAt)}</Td>
                      <Td>
                        <Button
                          size="xs"
                          variant="secondary"
                          disabled={operationExportMutation.isPending && operationExportMutation.variables?.importId === item.importId}
                          onClick={() => operationExportMutation.mutate({ importId: item.importId })}
                          aria-label={`Download operation export for ${compactId(item.importId)}`}
                        >
                          <FileDown size={13} />
                          CSV
                        </Button>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Audit evidence" subtitle="Dùng correlation/approval id để support truy lại actor/action." />
          <div className="grid gap-4 p-4">
            <Toolbar>
              <FormField label="Lookup approval ID">
                <Input value={approvalLookupId} onChange={(event) => setApprovalLookupId(event.target.value)} />
              </FormField>
              <div className="flex items-end">
                <Button variant="secondary" onClick={() => approvalLookup.refetch()} disabled={!approvalLookupId.trim()}>
                  <Search size={16} />
                  Load
                </Button>
              </div>
            </Toolbar>
            {approvalLookup.isError && <ErrorState error={approvalLookup.error} />}
            {audit.isLoading && <Spinner />}
            {audit.isError && <ErrorState error={audit.error} />}
            {audit.data && audit.data.items.length === 0 && <EmptyState message="Chưa có audit event phù hợp với scope hiện tại." />}
            {audit.data && audit.data.items.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Time</Th>
                    <Th>Action</Th>
                    <Th>Actor</Th>
                    <Th>Correlation</Th>
                  </tr>
                </thead>
                <tbody>
                  {audit.data.items.map((event) => (
                    <tr key={event.id}>
                      <Td>{formatDateTime(event.createdAt)}</Td>
                      <Td><StatusPill value={event.action ?? "INFO"} label={event.action ?? "event"} /></Td>
                      <Td>{event.actorId ?? "-"}</Td>
                      <Td><CopyableId value={event.correlationId} /></Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>
        </Card>
      </div>

      <ConfirmDialog
        open={commitOpen}
        onOpenChange={setCommitOpen}
        title="Commit coupon import"
        description="Backend sẽ so lại approved result hash và file hiện tại. Nếu key idempotency đã chạy với cùng payload, response sẽ là replay."
        confirmLabel="Commit"
        tone="danger"
        isPending={commitMutation.isPending}
        onConfirm={() => {
          if (canCommit) commitMutation.mutate();
        }}
      >
        <div className="grid gap-3">
          <KeyValue label="Approval" value={<CopyableId value={approval?.approvalId} />} />
          <KeyValue label="Dry-run" value={<CopyableId value={approval?.dryRunId} />} />
          <KeyValue label="Result hash" value={<CopyableId value={approval?.approvedResultHash} />} />
          <KeyValue label="Idempotency key" value={commitForm.idempotencyKey} mono />
        </div>
      </ConfirmDialog>

      <CouponApprovalDetail approval={selectedApproval} commit={commit} onClose={() => setSelectedApproval(null)} />
    </div>
  );
}

function reconciliationStats(items: IncentiveReconciliationEntry[]) {
  const counts = new Map<string, number>();
  const outboxCounts = new Map<string, number>();
  items.forEach((item) => {
    counts.set(item.reconciliationStatus, (counts.get(item.reconciliationStatus) ?? 0) + 1);
    outboxCounts.set(item.outboxStatus, (outboxCounts.get(item.outboxStatus) ?? 0) + 1);
  });
  return {
    matched: counts.get("MATCHED") ?? 0,
    outboxPending: outboxCounts.get("PENDING") ?? 0,
    missingOutbox: counts.get("MISSING_OUTBOX") ?? 0,
    missingEffect: counts.get("MISSING_EFFECT") ?? 0,
    duplicate: counts.get("DUPLICATE") ?? 0,
    reversed: counts.get("REVERSED") ?? 0
  };
}

function reconciliationRowKey(item: IncentiveReconciliationEntry) {
  return [
    item.ledgerEntryId,
    item.effect?.effectId ?? "no-effect",
    item.entryType,
    item.reconciliationKey
  ].join(":");
}

function compactQuotaPolicyLabel(value?: string | null) {
  if (value === "NO_RELEASE_ON_COMMITTED_REVERSAL") return "Không hoàn quota";
  if (value === "RELEASE_RESERVED_QUOTA") return "Release quota";
  if (value === "HOLD_RESERVED_QUOTA") return "Hold quota";
  return statusLabel(value);
}

function ReconciliationDetail({
  entry,
  onClose
}: {
  entry: IncentiveReconciliationEntry | null;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={Boolean(entry)}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={entry ? `Reconciliation ${compactId(entry.reconciliationKey)}` : "Reconciliation"}
      description={entry ? <StatusPill value={entry.reconciliationStatus} /> : undefined}
      className="max-w-4xl"
    >
      {entry && (
        <div className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-2">
            <KeyValue label="Reconciliation key" value={<CopyableId value={entry.reconciliationKey} />} />
            <KeyValue label="Ledger entry" value={<CopyableId value={entry.ledgerEntryId} />} />
            <KeyValue label="Redemption" value={<CopyableId value={entry.redemptionId} />} />
            <KeyValue label="Reservation" value={<CopyableId value={entry.reservationId} />} />
            <KeyValue label="Campaign" value={<CopyableId value={entry.campaignId} />} />
            <KeyValue label="Campaign version" value={entry.campaignVersion} />
            <KeyValue label="Coupon" value={<CopyableId value={entry.couponId} />} />
            <KeyValue label="Profile" value={entry.profileId} />
            <KeyValue label="External ref" value={entry.externalReference} />
            <KeyValue label="Entry type" value={<StatusPill value={entry.entryType} label={entry.entryType} />} />
            <KeyValue label="Direction" value={<StatusPill value={entry.direction} />} />
            <KeyValue label="Redemption status" value={<StatusPill value={entry.redemptionStatus} />} />
            <KeyValue label="Quota policy" value={<StatusPill value={entry.quotaPolicy} />} />
            <KeyValue label="Quota released" value={entry.quotaReleased === null || entry.quotaReleased === undefined ? "-" : String(entry.quotaReleased)} />
            <KeyValue label="Outbox" value={<StatusPill value={entry.outboxStatus} />} />
            <KeyValue label="Outbox event" value={entry.outboxEventType ?? "-"} />
            <KeyValue label="Correlation" value={<CopyableId value={entry.correlationId} />} />
            <KeyValue label="Source client" value={entry.sourceClientId ?? "-"} />
            <KeyValue label="Ledger time" value={formatDateTime(entry.ledgerCreatedAt)} />
            <KeyValue label="Outbox published" value={formatDateTime(entry.outboxPublishedAt)} />
          </div>
          {entry.reasonCodes.length > 0 && (
            <Notice tone={entry.reconciliationStatus === "MATCHED" ? "success" : "warning"} title="Reason codes">
              {entry.reasonCodes.join(", ")}
            </Notice>
          )}
          <Card variant="muted">
            <CardHeader title="Effect snapshot" compact />
            <div className="p-4">
              <JsonBlock value={entry.effect ?? {}} />
            </div>
          </Card>
        </div>
      )}
    </Drawer>
  );
}

export function ReconciliationPage() {
  const [filters, setFilters] = useState<IncentiveReconciliationFilters>({
    tenantId: "courseflow",
    applicationId: "lms",
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<IncentiveReconciliationFilters>(filters);
  const [hasQueried, setHasQueried] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<IncentiveReconciliationEntry | null>(null);
  const queryEnabled = hasQueried && hasReconciliationScope(filters);
  const query = useQuery({
    queryKey: queryKeys.incentives.reconciliation(filters),
    queryFn: () => queryReconciliation(filters),
    enabled: queryEnabled,
    retry: 1
  });
  const items = query.data?.items ?? [];
  const stats = reconciliationStats(items);

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Finance & support"
        title="Reconciliation viewer"
        description="Read-only view trên ledger/effect/outbox để kiểm tra redemption, quota policy và trạng thái publish event."
      />
      <IncentiveNav />

      <Card>
        <CardHeader title="Filter scope" subtitle="Không auto query khi filter rỗng; tenant/application là guardrail mặc định cho support." />
        <div className="grid gap-4 p-4">
          <Toolbar>
            <FormField label="Tenant" required>
              <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
            </FormField>
            <FormField label="Application" required>
              <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
            </FormField>
            <FormField label="Profile">
              <Input value={draftFilters.profileId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, profileId: event.target.value || undefined })} />
            </FormField>
            <FormField label="External ref">
              <Input value={draftFilters.externalReference ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, externalReference: event.target.value || undefined })} />
            </FormField>
            <FormField label="Campaign">
              <Input value={draftFilters.campaignId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, campaignId: event.target.value || undefined })} />
            </FormField>
            <FormField label="Coupon">
              <Input value={draftFilters.couponId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, couponId: event.target.value || undefined })} />
            </FormField>
            <FormField label="Redemption">
              <Input value={draftFilters.redemptionId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, redemptionId: event.target.value || undefined })} />
            </FormField>
            <FormField label="Reservation">
              <Input value={draftFilters.reservationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, reservationId: event.target.value || undefined })} />
            </FormField>
            <FormField label="Entry type">
              <Select value={draftFilters.entryType ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, entryType: event.target.value || undefined })}>
                <option value="">All</option>
                <option value="RESERVE">RESERVE</option>
                <option value="COMMIT">COMMIT</option>
                <option value="CANCEL">CANCEL</option>
                <option value="EXPIRE">EXPIRE</option>
                <option value="REVERSE">REVERSE</option>
              </Select>
            </FormField>
            <FormField label="From">
              <Input
                type="datetime-local"
                value={draftFilters.from ? formatDateTimeInput(draftFilters.from) : ""}
                onChange={(event) => setDraftFilters({ ...draftFilters, from: toIsoDateTime(event.target.value) })}
              />
            </FormField>
            <FormField label="To">
              <Input
                type="datetime-local"
                value={draftFilters.to ? formatDateTimeInput(draftFilters.to) : ""}
                onChange={(event) => setDraftFilters({ ...draftFilters, to: toIsoDateTime(event.target.value) })}
              />
            </FormField>
            <FormField label="Limit">
              <Input
                value={String(draftFilters.limit ?? 50)}
                inputMode="numeric"
                onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
              />
            </FormField>
            <div className="flex items-end gap-2">
              <Button
                onClick={() => {
                  setFilters(draftFilters);
                  setHasQueried(true);
                }}
              >
                <Search size={16} />
                Query
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  const reset = { tenantId: "courseflow", applicationId: "lms", limit: 50 };
                  setDraftFilters(reset);
                  setFilters(reset);
                  setHasQueried(false);
                }}
              >
                Reset
              </Button>
            </div>
          </Toolbar>
          {!hasQueried && <EmptyState message="Nhập scope rồi bấm Query để truy reconciliation. UI không tự tải global ledger." />}
          {hasQueried && !hasReconciliationScope(filters) && (
            <Notice tone="warning" title="Scope required">
              Cần tenant/application và ít nhất một filter nghiệp vụ như profile, campaign, redemption, entry type hoặc time range.
            </Notice>
          )}
        </div>
      </Card>

      {queryEnabled && (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <StatCard label="Matched" value={stats.matched.toLocaleString()} detail="Ledger/effect/outbox ổn." icon={<CheckCircle2 size={18} />} tone="success" />
            <StatCard label="Outbox pending" value={stats.outboxPending.toLocaleString()} detail="Outbox chưa publish." icon={<RefreshCcw size={18} />} tone="info" />
            <StatCard label="Missing outbox" value={stats.missingOutbox.toLocaleString()} detail="Cần kiểm tra outbox relay." icon={<FileSearch size={18} />} tone="warning" />
            <StatCard label="Missing effect" value={stats.missingEffect.toLocaleString()} detail="Ledger thiếu effect snapshot." icon={<ClipboardList size={18} />} tone="warning" />
            <StatCard label="Duplicate" value={stats.duplicate.toLocaleString()} detail="Có nhiều ledger entry cùng key." icon={<XCircle size={18} />} tone="danger" />
            <StatCard label="Reversed" value={stats.reversed.toLocaleString()} detail="Benefit đã bù trừ/reverse." icon={<ShieldCheck size={18} />} tone="neutral" />
          </div>

          <Card>
            <CardHeader
              title="Reconciliation entries"
              subtitle={query.data ? `${items.length.toLocaleString()} effect-level rows · generated ${formatDateTime(query.data.generatedAt)}` : "Effect-level rows"}
            />
            {query.isLoading && <Spinner />}
            {query.isError && <ErrorState error={query.error} />}
            {query.data?.hasMore && (
              <Notice tone="warning" title="Result limited" className="m-4">
                Backend còn dữ liệu ngoài limit hiện tại. Thu hẹp filter hoặc giảm time range để điều tra chính xác hơn.
              </Notice>
            )}
            {query.data && items.length === 0 && <EmptyState message="Không có reconciliation entry phù hợp." />}
            {items.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Status</Th>
                    <Th>Type</Th>
                    <Th>Redemption</Th>
                    <Th>Profile</Th>
                    <Th>Campaign</Th>
                    <Th>Effect</Th>
                    <Th>Quota</Th>
                    <Th>Outbox</Th>
                    <Th>Time</Th>
                    <Th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={reconciliationRowKey(item)}>
                      <Td><StatusPill value={item.reconciliationStatus} /></Td>
                      <Td>
                        <div className="flex flex-col gap-1">
                          <StatusPill value={item.entryType} label={item.entryType} />
                          <StatusPill value={item.direction} />
                        </div>
                      </Td>
                      <Td>
                        {item.redemptionId ? (
                          <Link className="font-mono text-xs font-semibold text-brand-700 hover:underline" to={`/incentives/redemptions/${item.redemptionId}`}>
                            {compactId(item.redemptionId)}
                          </Link>
                        ) : (
                          "-"
                        )}
                      </Td>
                      <Td className="font-mono text-xs">{compactId(item.profileId)}</Td>
                      <Td>
                        <div className="font-mono text-xs">{compactId(item.campaignId)}</div>
                        <div className="text-xs text-slate-400">v{item.campaignVersion}</div>
                      </Td>
                      <Td className="text-xs">
                        <div>{item.effect?.type ?? item.effect?.benefitType ?? "-"}</div>
                        <div className="font-mono text-slate-400">{compactId(item.effect?.effectId)}</div>
                      </Td>
                      <Td><StatusPill value={item.quotaPolicy} label={compactQuotaPolicyLabel(item.quotaPolicy)} /></Td>
                      <Td><StatusPill value={item.outboxStatus} /></Td>
                      <Td>{formatDateTime(item.ledgerCreatedAt)}</Td>
                      <Td>
                        <Button size="xs" variant="secondary" onClick={() => setSelectedEntry(item)}>
                          Detail
                        </Button>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      )}

      <ReconciliationDetail entry={selectedEntry} onClose={() => setSelectedEntry(null)} />
    </div>
  );
}
