import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  FileSearch,
  Gift,
  RefreshCcw,
  Search,
  ShieldAlert,
  TicketPercent,
  Trash2
} from "lucide-react";
import { queryKeys } from "@/shared/api/query-keys";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ConfirmDialog,
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
import {
  addRemediationCaseNote,
  assignRemediationCase,
  listPromotionApplications,
  queryAuditLog as queryEnrollmentAuditLog,
  queryBenefitReconciliation,
  queryRemediationCases,
  resolveRemediationCase
} from "@/modules/enrollments/api";
import type {
  AuditLogEntry,
  EnrollmentBenefitReconciliationEntry,
  EnrollmentBenefitReconciliationResponse,
  EnrollmentPromotionApplicationState,
  EnrollmentRemediationCase
} from "@/modules/enrollments/api";
import { cn } from "@/shared/ui/cn";
import {
  approveOutboxDeadLetterApproval,
  discardOutboxDeadLetter,
  getCoupon,
  getLoyaltyRewardRedemption,
  getRedemption,
  listRedemptions,
  listReservations,
  queryAudit,
  queryLoyaltyBenefitReconciliation,
  queryLoyaltyAudit,
  queryLoyaltyDeadLetters,
  queryLoyaltyLedger,
  queryLoyaltyRewardRedemptions,
  queryOutboxDeadLetters,
  queryReconciliation,
  replayOutboxDeadLetter,
  requestOutboxDeadLetterApproval,
  retentionOperationId
} from "./api";
import { IncentiveNav } from "./pages";
import { compactId, formatDateTime, statusLabel, statusTone } from "./labels";
import {
  isActionableDeadLetterStatus,
  isOpenDeadLetterStatus,
  loyaltyDltOpsFilters,
  outboxDltOpsFilters
} from "./ops-console-helpers";
import type {
  AuditEvent,
  Coupon,
  IncentiveReconciliationEntry,
  LoyaltyBenefitReconciliationEntry,
  LoyaltyBenefitReconciliationQueryResponse,
  LoyaltyInboundDeadLetter,
  LoyaltyLedgerEntry,
  OutboxDeadLetterApproval,
  OutboxDeadLetterActionResponse,
  LoyaltyRewardRedemption,
  OutboxDeadLetterSummary,
  Redemption,
  Reservation
} from "./types";

type OpsFilters = {
  tenantId: string;
  applicationId: string;
  profileId: string;
  courseId: string;
  enrollmentId: string;
  couponId: string;
  promotionRedemptionId: string;
  rewardRedemptionId: string;
  loyaltyAccountId: string;
  correlationId: string;
  dltPayloadHash: string;
  outboxService: string;
  outboxEventType: string;
  limit: string;
};

type SubmittedOpsFilters = {
  tenantId?: string;
  applicationId?: string;
  profileId?: string;
  courseId?: string;
  enrollmentId?: string;
  couponId?: string;
  promotionRedemptionId?: string;
  rewardRedemptionId?: string;
  loyaltyAccountId?: string;
  correlationId?: string;
  dltPayloadHash?: string;
  outboxService?: string;
  outboxEventType?: string;
  limit: number;
};

type OutboxDltActionTarget = {
  deadLetter: OutboxDeadLetterSummary;
  action: "replay" | "discard";
  dryRun: boolean;
  operationId: string;
  correlationId: string;
};

type RemediationActionTarget = {
  remediationCase: EnrollmentRemediationCase;
  action: "assign" | "note" | "resolve";
  correlationId: string;
};

const defaultFilters: OpsFilters = {
  tenantId: "courseflow",
  applicationId: "lms",
  profileId: "",
  courseId: "",
  enrollmentId: "",
  couponId: "",
  promotionRedemptionId: "",
  rewardRedemptionId: "",
  loyaltyAccountId: "",
  correlationId: "",
  dltPayloadHash: "",
  outboxService: "",
  outboxEventType: "",
  limit: "25"
};

function trim(value: string) {
  const next = value.trim();
  return next || undefined;
}

function normalizeFilters(form: OpsFilters): SubmittedOpsFilters {
  const limit = Number(form.limit);
  return {
    tenantId: trim(form.tenantId),
    applicationId: trim(form.applicationId),
    profileId: trim(form.profileId),
    courseId: trim(form.courseId),
    enrollmentId: trim(form.enrollmentId),
    couponId: trim(form.couponId),
    promotionRedemptionId: trim(form.promotionRedemptionId),
    rewardRedemptionId: trim(form.rewardRedemptionId),
    loyaltyAccountId: trim(form.loyaltyAccountId),
    correlationId: trim(form.correlationId),
    dltPayloadHash: trim(form.dltPayloadHash),
    outboxService: trim(form.outboxService),
    outboxEventType: trim(form.outboxEventType),
    limit: Number.isFinite(limit) ? Math.max(5, Math.min(limit, 100)) : 25
  };
}

function hasCaseAnchor(filters: SubmittedOpsFilters) {
  return Boolean(
    filters.profileId ||
      filters.courseId ||
      filters.enrollmentId ||
      filters.couponId ||
      filters.promotionRedemptionId ||
      filters.rewardRedemptionId ||
      filters.loyaltyAccountId ||
      filters.correlationId ||
      filters.dltPayloadHash ||
      filters.outboxService ||
      filters.outboxEventType
  );
}

function StatusPill({ value }: { value?: string | null }) {
  return <Badge value={value ?? undefined} label={statusLabel(value)} tone={statusTone(value)} />;
}

function IdLink({
  value,
  to,
  label
}: {
  value?: string | null;
  to?: string;
  label?: string;
}) {
  if (!value) return <span>-</span>;
  const text = label ?? compactId(value);
  if (!to) return <span className="font-mono text-xs">{text}</span>;
  return (
    <Link to={to} className="font-mono text-xs font-semibold text-brand-700 hover:underline">
      {text}
    </Link>
  );
}

function problemPromotionApplication(row: EnrollmentPromotionApplicationState) {
  return ["COMMIT_FAILED", "MANUAL_REVIEW", "RESERVED"].includes(row.status);
}

function problemRemediationCase(row: EnrollmentRemediationCase) {
  return row.slaBreached || ["OPEN", "IN_PROGRESS"].includes(row.status);
}

function problemEnrollmentReconciliation(row: EnrollmentBenefitReconciliationEntry) {
  return row.reconciliationStatus !== "MATCHED";
}

function problemLoyaltyBenefitReconciliation(row: LoyaltyBenefitReconciliationEntry) {
  return row.reconciliationStatus !== "MATCHED";
}

function problemReconciliation(row: IncentiveReconciliationEntry) {
  return row.reconciliationStatus !== "MATCHED" || row.outboxStatus === "MISSING" || row.outboxStatus === "PENDING";
}

function problemReward(row: LoyaltyRewardRedemption) {
  return ["FAILED", "MANUAL_REQUIRED", "PENDING"].includes(row.fulfillmentStatus) || row.status === "REVERSED";
}

function openLoyaltyDeadLetter(row: LoyaltyInboundDeadLetter) {
  return isOpenDeadLetterStatus(row.status);
}

function openOutboxDeadLetter(row: OutboxDeadLetterSummary) {
  return isOpenDeadLetterStatus(row.status);
}

function actionableOutboxDeadLetter(row: OutboxDeadLetterSummary) {
  return isActionableDeadLetterStatus(row.status);
}

function compactError(error?: string | null) {
  if (!error) return "-";
  return error.length > 160 ? `${error.slice(0, 160)}...` : error;
}

function maskCouponDisplay(code?: string | null, fallbackId?: string | null) {
  if (!code || code.length < 8) return fallbackId ? compactId(fallbackId) : "-";
  return `${code.slice(0, 3)}...${code.slice(-3)}`;
}

function remediationActionCorrelation(action?: { payload?: Record<string, unknown> | null } | null) {
  const value = action?.payload?.correlationId;
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function latestRemediationCorrelation(item: EnrollmentRemediationCase) {
  for (let index = item.actionHistory.length - 1; index >= 0; index -= 1) {
    const correlationId = remediationActionCorrelation(item.actionHistory[index]);
    if (correlationId) return correlationId;
  }
  return undefined;
}

function outboxTopic(row: OutboxDeadLetterSummary) {
  return row.topic || row.eventType;
}

function outboxPosition(row: OutboxDeadLetterSummary) {
  if (row.kafkaOffset !== undefined && row.kafkaOffset !== null) {
    return `p${row.kafkaPartition ?? "-"}:o${row.kafkaOffset}`;
  }
  return `source ${compactId(row.sourceEventId, 12, 6)}`;
}

function SectionError({ error }: { error: unknown }) {
  return (
    <div className="p-4">
      <ErrorState error={error} />
    </div>
  );
}

function LoadingOrEmpty({
  loading,
  empty,
  children
}: {
  loading: boolean;
  empty: boolean;
  children: React.ReactNode;
}) {
  if (loading) return <div className="p-4"><Spinner /></div>;
  if (empty) return <EmptyState message="Không có dữ liệu phù hợp với case filter." />;
  return <>{children}</>;
}

export function IncentiveOpsConsolePage() {
  const [form, setForm] = useState<OpsFilters>(defaultFilters);
  const [submitted, setSubmitted] = useState<SubmittedOpsFilters | null>(null);
  const [outboxAction, setOutboxAction] = useState<OutboxDltActionTarget | null>(null);
  const [outboxActionReason, setOutboxActionReason] = useState("Reviewed by incentive operations");
  const [outboxApprovalEvidence, setOutboxApprovalEvidence] = useState("");
  const [outboxApprovalId, setOutboxApprovalId] = useState("");
  const [outboxApprovalReviewNote, setOutboxApprovalReviewNote] = useState("Checked evidence and threshold policy");
  const [outboxApprovalResult, setOutboxApprovalResult] = useState<OutboxDeadLetterApproval | null>(null);
  const [outboxActionResult, setOutboxActionResult] = useState<OutboxDeadLetterActionResponse | null>(null);
  const [remediationAction, setRemediationAction] = useState<RemediationActionTarget | null>(null);
  const [remediationAssignee, setRemediationAssignee] = useState("");
  const [remediationNote, setRemediationNote] = useState("Reviewed by enrollment operations");
  const [remediationResult, setRemediationResult] = useState<EnrollmentRemediationCase | null>(null);
  const queryClient = useQueryClient();
  const ready = Boolean(submitted && hasCaseAnchor(submitted));
  const limit = submitted?.limit ?? 25;
  const aggregateId = submitted?.promotionRedemptionId || submitted?.rewardRedemptionId || submitted?.enrollmentId || submitted?.couponId;
  const loyaltyAggregateId = submitted?.loyaltyAccountId || submitted?.rewardRedemptionId || submitted?.promotionRedemptionId;
  const opsKey = queryKeys.incentives.opsConsole(submitted ?? {});

  function update<K extends keyof OpsFilters>(key: K, value: OpsFilters[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(normalizeFilters(form));
    setOutboxActionResult(null);
    setOutboxApprovalResult(null);
  }

  function openOutboxAction(deadLetter: OutboxDeadLetterSummary, action: "replay" | "discard", dryRun = false) {
    const prefix = action === "replay" ? "outbox-dlt-replay" : "outbox-dlt-discard";
    outboxActionMutation.reset();
    outboxApprovalMutation.reset();
    outboxApprovalReviewMutation.reset();
    setOutboxActionResult(null);
    setOutboxApprovalResult(null);
    setOutboxAction({
      deadLetter,
      action,
      dryRun,
      operationId: retentionOperationId(prefix),
      correlationId: retentionOperationId(`corr-${prefix}`)
    });
    setOutboxActionReason(action === "replay" ? "Replay after relay failure review" : "Discard after manual resolution");
    setOutboxApprovalEvidence(`${deadLetter.serviceName}:${deadLetter.sourceEventId}:${deadLetter.payloadHash}`);
    setOutboxApprovalId("");
    setOutboxApprovalReviewNote("Checked evidence and threshold policy");
  }

  function openRemediationAction(remediationCase: EnrollmentRemediationCase, action: "assign" | "note" | "resolve") {
    remediationActionMutation.reset();
    const prefix = action === "assign" ? "enrollment-remediation-assign" : action === "resolve" ? "enrollment-remediation-resolve" : "enrollment-remediation-note";
    setRemediationAction({
      remediationCase,
      action,
      correlationId: submitted?.correlationId || retentionOperationId(`corr-${prefix}`)
    });
    setRemediationAssignee(remediationCase.assigneeId || "");
    setRemediationNote(
      action === "assign"
        ? `Assign ${compactId(remediationCase.id)} for ${remediationCase.reasonCode}`
        : action === "resolve"
          ? `Resolved ${remediationCase.reasonCode} after evidence review`
          : `Reviewed ${remediationCase.reasonCode}`
    );
  }

  const enrollmentApplications = useQuery({
    queryKey: [...opsKey, "enrollment-promotion-applications"],
    enabled: ready,
    queryFn: () =>
      listPromotionApplications({
        courseId: submitted?.courseId,
        studentId: submitted?.profileId,
        limit
      })
  });

  const remediationCases = useQuery({
    queryKey: [...opsKey, "enrollment-remediation-cases"],
    enabled: ready,
    queryFn: () =>
      queryRemediationCases({
        courseId: submitted?.courseId,
        enrollmentId: submitted?.enrollmentId,
        studentId: submitted?.profileId,
        couponId: submitted?.couponId,
        redemptionId: submitted?.promotionRedemptionId,
        correlationId: submitted?.correlationId,
        limit
      })
  });

  const enrollmentReconciliation = useQuery({
    queryKey: [...opsKey, "enrollment-benefit-reconciliation"],
    enabled: ready && Boolean(submitted?.courseId || submitted?.profileId || submitted?.enrollmentId),
    queryFn: () =>
      queryBenefitReconciliation({
        enrollmentId: submitted?.enrollmentId,
        courseId: submitted?.courseId,
        studentId: submitted?.profileId,
        limit
      })
  });

  const promotionRedemption = useQuery({
    queryKey: [...opsKey, "promotion-redemption", submitted?.promotionRedemptionId],
    enabled: ready && Boolean(submitted?.promotionRedemptionId),
    queryFn: () => getRedemption(submitted!.promotionRedemptionId!)
  });

  const promotionRedemptions = useQuery({
    queryKey: [...opsKey, "promotion-redemptions"],
    enabled: ready && !submitted?.promotionRedemptionId,
    queryFn: () =>
      listRedemptions({
        tenantId: submitted?.tenantId,
        applicationId: submitted?.applicationId,
        profileId: submitted?.profileId,
        externalReference: submitted?.enrollmentId,
        couponId: submitted?.couponId,
        limit
      })
  });

  const reservations = useQuery({
    queryKey: [...opsKey, "promotion-reservations"],
    enabled: ready,
    queryFn: () =>
      listReservations({
        tenantId: submitted?.tenantId,
        applicationId: submitted?.applicationId,
        profileId: submitted?.profileId,
        externalReference: submitted?.enrollmentId,
        couponId: submitted?.couponId,
        limit
      })
  });

  const coupon = useQuery({
    queryKey: [...opsKey, "coupon", submitted?.couponId],
    enabled: ready && Boolean(submitted?.couponId),
    queryFn: () => getCoupon(submitted!.couponId!)
  });

  const reconciliation = useQuery({
    queryKey: [...opsKey, "promotion-reconciliation"],
    enabled: ready,
    queryFn: () =>
      queryReconciliation({
        tenantId: submitted?.tenantId,
        applicationId: submitted?.applicationId,
        profileId: submitted?.profileId,
        externalReference: submitted?.enrollmentId,
        couponId: submitted?.couponId,
        redemptionId: submitted?.promotionRedemptionId,
        limit
      })
  });

  const rewardRedemption = useQuery({
    queryKey: [...opsKey, "reward-redemption", submitted?.rewardRedemptionId],
    enabled: ready && Boolean(submitted?.rewardRedemptionId),
    queryFn: () => getLoyaltyRewardRedemption(submitted!.rewardRedemptionId!)
  });

  const rewardRedemptions = useQuery({
    queryKey: [...opsKey, "reward-redemptions"],
    enabled: ready && !submitted?.rewardRedemptionId,
    queryFn: () =>
      queryLoyaltyRewardRedemptions({
        tenantId: submitted?.tenantId,
        applicationId: submitted?.applicationId,
        profileId: submitted?.profileId,
        limit
      })
  });

  const loyaltyLedger = useQuery({
    queryKey: [...opsKey, "loyalty-ledger", submitted?.loyaltyAccountId],
    enabled: ready && Boolean(submitted?.loyaltyAccountId),
    queryFn: () => queryLoyaltyLedger({ accountId: submitted!.loyaltyAccountId! })
  });

  const loyaltyBenefitReconciliation = useQuery({
    queryKey: [...opsKey, "loyalty-benefit-reconciliation"],
    enabled: ready && Boolean(submitted?.tenantId && submitted?.applicationId),
    queryFn: () =>
      queryLoyaltyBenefitReconciliation({
        tenantId: submitted?.tenantId,
        applicationId: submitted?.applicationId,
        profileId: submitted?.profileId,
        redemptionId: submitted?.promotionRedemptionId,
        limit
      })
  });

  const loyaltyDeadLetters = useQuery({
    queryKey: queryKeys.incentives.loyaltyDeadLetters(loyaltyDltOpsFilters({
      dltPayloadHash: submitted?.dltPayloadHash,
      limit
    })),
    enabled: ready,
    queryFn: () =>
      queryLoyaltyDeadLetters(loyaltyDltOpsFilters({
        dltPayloadHash: submitted?.dltPayloadHash,
        limit
      }))
  });

  const outboxDeadLetters = useQuery({
    queryKey: queryKeys.incentives.outboxDeadLetters(outboxDltOpsFilters({
      outboxService: submitted?.outboxService,
      outboxEventType: submitted?.outboxEventType,
      dltPayloadHash: submitted?.dltPayloadHash,
      limit
    }, aggregateId)),
    enabled: ready,
    queryFn: () =>
      queryOutboxDeadLetters(outboxDltOpsFilters({
        outboxService: submitted?.outboxService,
        outboxEventType: submitted?.outboxEventType,
        dltPayloadHash: submitted?.dltPayloadHash,
        limit
      }, aggregateId))
  });

  const enrollmentAudit = useQuery({
    queryKey: [...opsKey, "enrollment-audit"],
    enabled: ready && Boolean(submitted?.enrollmentId || submitted?.courseId || submitted?.profileId || submitted?.correlationId),
    queryFn: () =>
      queryEnrollmentAuditLog({
        enrollmentId: submitted?.enrollmentId,
        courseId: submitted?.courseId,
        studentId: submitted?.profileId,
        correlationId: submitted?.correlationId,
        limit
      })
  });

  const audit = useQuery({
    queryKey: [...opsKey, "audit"],
    enabled: ready,
    queryFn: () =>
      queryAudit({
        tenantId: submitted?.tenantId,
        applicationId: submitted?.applicationId,
        aggregateId,
        correlationId: submitted?.correlationId,
        limit
      })
  });

  const loyaltyAudit = useQuery({
    queryKey: [...opsKey, "loyalty-audit"],
    enabled: ready,
    queryFn: () =>
      queryLoyaltyAudit({
        tenantId: submitted?.tenantId,
        applicationId: submitted?.applicationId,
        aggregateId: loyaltyAggregateId,
        correlationId: submitted?.correlationId,
        limit
      })
  });

  const outboxActionMutation = useMutation({
    mutationFn: async () => {
      if (!outboxAction) throw new Error("Missing outbox DLT action target");
      const input = {
        idempotencyKey: outboxAction.operationId,
        correlationId: outboxAction.correlationId,
        reason: outboxActionReason,
        dryRun: outboxAction.dryRun,
        approvalId: outboxAction.dryRun ? undefined : outboxApprovalId.trim() || undefined
      };
      return outboxAction.action === "replay"
        ? replayOutboxDeadLetter(outboxAction.deadLetter.id, input)
        : discardOutboxDeadLetter(outboxAction.deadLetter.id, input);
    },
    onSuccess: (response) => {
      setOutboxActionResult(response);
      setOutboxAction(null);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
    }
  });

  const outboxApprovalMutation = useMutation({
    mutationFn: async () => {
      if (!outboxAction) throw new Error("Missing outbox DLT action target");
      return requestOutboxDeadLetterApproval(outboxAction.deadLetter.id, {
        action: outboxAction.action === "replay" ? "REPLAY" : "DISCARD",
        reason: outboxActionReason,
        evidenceReference: outboxApprovalEvidence,
        correlationId: outboxAction.correlationId
      });
    },
    onSuccess: (response) => {
      setOutboxApprovalResult(response);
      setOutboxApprovalId(response.id);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
    }
  });

  const outboxApprovalReviewMutation = useMutation({
    mutationFn: async () => {
      const approvalId = outboxApprovalId.trim();
      if (!approvalId) throw new Error("Missing outbox DLT approval id");
      return approveOutboxDeadLetterApproval(approvalId, { note: outboxApprovalReviewNote });
    },
    onSuccess: (response) => {
      setOutboxApprovalResult(response);
      setOutboxApprovalId(response.id);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
    }
  });

  const remediationActionMutation = useMutation({
    mutationFn: async () => {
      if (!remediationAction) throw new Error("Missing enrollment remediation action target");
      const { remediationCase, action, correlationId } = remediationAction;
      if (action === "assign") {
        const assigneeId = remediationAssignee.trim();
        if (!assigneeId) throw new Error("Missing remediation assignee");
        return assignRemediationCase(remediationCase.id, {
          assigneeId,
          note: remediationNote,
          correlationId
        });
      }
      if (action === "resolve") {
        return resolveRemediationCase(remediationCase.id, {
          note: remediationNote,
          correlationId
        });
      }
      return addRemediationCaseNote(remediationCase.id, {
        note: remediationNote,
        correlationId
      });
    },
    onSuccess: (response) => {
      setRemediationResult(response);
      setRemediationAction(null);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
    }
  });

  const promotionRedemptionItems = promotionRedemption.data
    ? [promotionRedemption.data]
    : promotionRedemptions.data ?? [];
  const rewardRedemptionItems = rewardRedemption.data
    ? [rewardRedemption.data]
    : rewardRedemptions.data?.items ?? [];
  const ledgerItems = loyaltyLedger.data?.items ?? [];

  const stats = useMemo(() => {
    const promotionIssues = (enrollmentApplications.data ?? []).filter(problemPromotionApplication).length;
    const remediationIssues = (remediationCases.data ?? []).filter(problemRemediationCase).length;
    const enrollmentReconciliationIssues = (enrollmentReconciliation.data?.items ?? []).filter(problemEnrollmentReconciliation).length;
    const loyaltyBenefitIssues = (loyaltyBenefitReconciliation.data?.items ?? []).filter(problemLoyaltyBenefitReconciliation).length;
    const reconciliationIssues = (reconciliation.data?.items ?? []).filter(problemReconciliation).length;
    const rewardIssues = rewardRedemptionItems.filter(problemReward).length;
    const loyaltyDlt = (loyaltyDeadLetters.data?.items ?? []).filter(openLoyaltyDeadLetter).length;
    const outboxDlt = (outboxDeadLetters.data?.items ?? []).filter(openOutboxDeadLetter).length;
    return {
      promotionIssues,
      remediationIssues,
      enrollmentReconciliationIssues,
      loyaltyBenefitIssues,
      reconciliationIssues,
      rewardIssues,
      openDlt: loyaltyDlt + outboxDlt,
      totalIssues: promotionIssues + remediationIssues + enrollmentReconciliationIssues + loyaltyBenefitIssues + reconciliationIssues + rewardIssues + loyaltyDlt + outboxDlt
    };
  }, [
    enrollmentApplications.data,
    remediationCases.data,
    enrollmentReconciliation.data,
    loyaltyBenefitReconciliation.data,
    loyaltyDeadLetters.data,
    outboxDeadLetters.data,
    reconciliation.data,
    rewardRedemptionItems
  ]);

  return (
    <div>
      <PageHeader
        eyebrow="Incentive operations"
        title="Unified Ops Console"
        description="Tra cứu một case xuyên enrollment, promotion, loyalty, reward và outbox/DLT để support có đủ evidence trước khi retry, reverse hoặc replay."
      />
      <IncentiveNav />

      <Card className="mb-5">
        <CardHeader
          title="Case filters"
          subtitle="Nhập ít nhất một anchor như learner/profile, enrollment, coupon, redemption, correlation hoặc DLT payload hash."
        />
        <form onSubmit={submit} className="p-4">
          <Toolbar>
            <FormField label="Tenant">
              <Input value={form.tenantId} onChange={(event) => update("tenantId", event.target.value)} />
            </FormField>
            <FormField label="Application">
              <Input value={form.applicationId} onChange={(event) => update("applicationId", event.target.value)} />
            </FormField>
            <FormField label="Profile / learner">
              <Input value={form.profileId} onChange={(event) => update("profileId", event.target.value)} placeholder="profileId hoặc studentId" />
            </FormField>
            <FormField label="Course">
              <Input value={form.courseId} onChange={(event) => update("courseId", event.target.value)} placeholder="courseId" />
            </FormField>
            <FormField label="Enrollment">
              <Input value={form.enrollmentId} onChange={(event) => update("enrollmentId", event.target.value)} placeholder="enrollmentId/externalReference" />
            </FormField>
            <FormField label="Coupon">
              <Input value={form.couponId} onChange={(event) => update("couponId", event.target.value)} placeholder="couponId" />
            </FormField>
            <FormField label="Promotion redemption">
              <Input value={form.promotionRedemptionId} onChange={(event) => update("promotionRedemptionId", event.target.value)} placeholder="redemptionId" />
            </FormField>
            <FormField label="Reward redemption">
              <Input value={form.rewardRedemptionId} onChange={(event) => update("rewardRedemptionId", event.target.value)} placeholder="reward redemption id" />
            </FormField>
            <FormField label="Loyalty account">
              <Input value={form.loyaltyAccountId} onChange={(event) => update("loyaltyAccountId", event.target.value)} placeholder="accountId" />
            </FormField>
            <FormField label="Correlation">
              <Input value={form.correlationId} onChange={(event) => update("correlationId", event.target.value)} placeholder="correlationId" />
            </FormField>
            <FormField label="DLT payload hash">
              <Input value={form.dltPayloadHash} onChange={(event) => update("dltPayloadHash", event.target.value)} placeholder="payload hash" />
            </FormField>
            <FormField label="Outbox service">
              <Input value={form.outboxService} onChange={(event) => update("outboxService", event.target.value)} placeholder="promotion-service" />
            </FormField>
            <FormField label="Outbox event">
              <Input value={form.outboxEventType} onChange={(event) => update("outboxEventType", event.target.value)} placeholder="event type" />
            </FormField>
            <FormField label="Limit">
              <Select value={form.limit} onChange={(event) => update("limit", event.target.value)}>
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </Select>
            </FormField>
            <Button type="submit" className="self-end">
              <Search size={16} />
              Query case
            </Button>
          </Toolbar>
        </form>
      </Card>

      {submitted && !ready && (
        <Notice tone="warning" title="Cần case anchor">
          Không chạy global query cho ops console. Hãy nhập learner/profile, enrollment, coupon, redemption, correlationId, payload hash hoặc outbox filter.
        </Notice>
      )}

      {!submitted && (
        <EmptyState message="Nhập case filter để bắt đầu điều tra incentive incident." />
      )}

      {ready && (
        <>
          <div className="mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-8">
            <StatCard label="Total issues" value={stats.totalIssues} detail="Tổng signal cần xử lý." icon={<ShieldAlert size={18} />} tone={stats.totalIssues ? "danger" : "success"} />
            <StatCard label="Enrollment/order" value={stats.enrollmentReconciliationIssues} detail="Payment/drop/promo lệch." icon={<FileSearch size={18} />} tone={stats.enrollmentReconciliationIssues ? "danger" : "success"} />
            <StatCard label="Remediation" value={stats.remediationIssues} detail="Case đang mở/SLA breach." icon={<ShieldAlert size={18} />} tone={stats.remediationIssues ? "danger" : "success"} />
            <StatCard label="Enrollment promo" value={stats.promotionIssues} detail="Commit/manual/hold." icon={<TicketPercent size={18} />} tone={stats.promotionIssues ? "warning" : "success"} />
            <StatCard label="Loyalty benefit" value={stats.loyaltyBenefitIssues} detail="Earn/reverse points lệch." icon={<FileSearch size={18} />} tone={stats.loyaltyBenefitIssues ? "danger" : "success"} />
            <StatCard label="Reconciliation" value={stats.reconciliationIssues} detail="Ledger/effect/outbox lệch." icon={<FileSearch size={18} />} tone={stats.reconciliationIssues ? "warning" : "success"} />
            <StatCard label="Reward ops" value={stats.rewardIssues} detail="Fulfillment hoặc reverse." icon={<Gift size={18} />} tone={stats.rewardIssues ? "warning" : "success"} />
            <StatCard label="Open DLT" value={stats.openDlt} detail="Loyalty + outbox relay." icon={<AlertTriangle size={18} />} tone={stats.openDlt ? "danger" : "success"} />
          </div>

          {stats.totalIssues > 0 && (
            <Notice tone="warning" title="Next action">
              Ưu tiên xử lý theo thứ tự: enrollment promotion failed/manual, reconciliation mismatch, reward fulfillment failed/manual, sau đó mới replay/discard DLT. Mọi action write cần reason và correlation id ở màn chuyên biệt.
            </Notice>
          )}

          {outboxActionResult && (
            <Notice
              tone={outboxActionResult.status === "FAILED" ? "danger" : outboxActionResult.dryRun ? "info" : "success"}
              title={`Outbox DLT ${outboxActionResult.action.toLowerCase()} ${outboxActionResult.status.toLowerCase()}`}
            >
              {outboxActionResult.reasonCode} · payload {compactId(outboxActionResult.payloadHash, 18, 8)}
            </Notice>
          )}

          {remediationResult && (
            <Notice tone={remediationResult.status === "RESOLVED" ? "success" : "info"} title="Enrollment remediation updated">
              {compactId(remediationResult.id)} · {remediationResult.status} · {remediationResult.reasonCode}
            </Notice>
          )}

          <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <EnrollmentBenefitReconciliationSection
              query={enrollmentReconciliation}
              enabled={Boolean(submitted?.courseId || submitted?.profileId || submitted?.enrollmentId)}
            />
            <EnrollmentPromotionSection query={enrollmentApplications} />
            <EnrollmentRemediationSection
              query={remediationCases}
              onAction={openRemediationAction}
            />
            <CouponSection query={coupon} enabled={Boolean(submitted?.couponId)} />
            <PromotionRuntimeSection
              redemptions={promotionRedemptionItems}
              redemptionsLoading={promotionRedemption.isLoading || promotionRedemptions.isLoading}
              redemptionsError={promotionRedemption.error ?? promotionRedemptions.error}
              reservations={reservations.data ?? []}
              reservationsLoading={reservations.isLoading}
              reservationsError={reservations.error}
            />
            <ReconciliationSection query={reconciliation} />
            <LoyaltyBenefitReconciliationSection query={loyaltyBenefitReconciliation} />
            <RewardSection
              rewards={rewardRedemptionItems}
              loading={rewardRedemption.isLoading || rewardRedemptions.isLoading}
              error={rewardRedemption.error ?? rewardRedemptions.error}
            />
            <LoyaltyLedgerSection items={ledgerItems} loading={loyaltyLedger.isLoading} error={loyaltyLedger.error} enabled={Boolean(submitted?.loyaltyAccountId)} />
            <DeadLetterSection
              loyaltyItems={loyaltyDeadLetters.data?.items ?? []}
              outboxItems={outboxDeadLetters.data?.items ?? []}
              loading={loyaltyDeadLetters.isLoading || outboxDeadLetters.isLoading}
              error={loyaltyDeadLetters.error ?? outboxDeadLetters.error}
              onOutboxAction={openOutboxAction}
            />
            <EnrollmentAuditSection
              query={enrollmentAudit}
              enabled={Boolean(submitted?.enrollmentId || submitted?.courseId || submitted?.profileId || submitted?.correlationId)}
            />
            <AuditSection
              query={audit}
              title="Promotion audit timeline"
              subtitle="Campaign, reservation, redemption, coupon và correlation audit từ promotion-service."
            />
            <AuditSection
              query={loyaltyAudit}
              title="Loyalty audit timeline"
              subtitle="Ledger, reward, DLT và correlation audit từ loyalty-service."
            />
          </div>

          <ConfirmDialog
            open={Boolean(remediationAction)}
            onOpenChange={(open) => !open && setRemediationAction(null)}
            title={
              remediationAction?.action === "assign"
                ? "Assign remediation case"
                : remediationAction?.action === "resolve"
                  ? "Resolve remediation case"
                  : "Add remediation note"
            }
            description={remediationAction ? `${remediationAction.remediationCase.reasonCode} · ${compactId(remediationAction.remediationCase.id)}` : undefined}
            confirmLabel={
              remediationAction?.action === "assign"
                ? "Assign"
                : remediationAction?.action === "resolve"
                  ? "Resolve"
                  : "Add note"
            }
            tone={remediationAction?.action === "resolve" ? "primary" : "secondary"}
            isPending={remediationActionMutation.isPending}
            onConfirm={() => remediationActionMutation.mutate()}
          >
            <div className="space-y-3">
              {remediationAction && (
                <div className="grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 md:grid-cols-2">
                  <span className="font-mono">case {compactId(remediationAction.remediationCase.id, 20, 8)}</span>
                  <span className="font-mono">correlation {compactId(remediationAction.correlationId, 20, 8)}</span>
                </div>
              )}
              {remediationAction?.action === "assign" && (
                <FormField label="Assignee" required>
                  <Input value={remediationAssignee} onChange={(event) => setRemediationAssignee(event.target.value)} />
                </FormField>
              )}
              <FormField label="Note" required>
                <Textarea value={remediationNote} onChange={(event) => setRemediationNote(event.target.value)} rows={3} />
              </FormField>
              {remediationActionMutation.isError && <ErrorState error={remediationActionMutation.error} />}
            </div>
          </ConfirmDialog>

          <ConfirmDialog
            open={Boolean(outboxAction)}
            onOpenChange={(open) => !open && setOutboxAction(null)}
            title={`${outboxAction?.dryRun ? "Dry-run " : ""}${outboxAction?.action === "discard" ? "Discard" : "Replay"} outbox DLT`}
            description={outboxAction ? `${outboxAction.deadLetter.serviceName} · ${compactId(outboxAction.deadLetter.id)}` : undefined}
            confirmLabel={outboxAction?.dryRun ? "Dry-run" : outboxAction?.action === "discard" ? "Discard" : "Replay"}
            tone={outboxAction?.action === "discard" ? "danger" : "primary"}
            isPending={outboxActionMutation.isPending}
            onConfirm={() => outboxActionMutation.mutate()}
          >
            <div className="space-y-3">
              <Notice tone={outboxAction?.dryRun ? "neutral" : "warning"} title={outboxAction?.dryRun ? "Dry-run only" : "Production action"}>
                {outboxAction?.dryRun
                  ? "Backend chỉ kiểm tra trạng thái hiện tại, không publish lại message và không đổi trạng thái DLT."
                  : outboxAction?.action === "replay"
                    ? "Backend sẽ publish lại payload gốc về topic đã lưu, dùng idempotency key và ghi operator audit."
                    : "Record sẽ chuyển DISCARDED, giữ operator audit với reason và correlation id."}
              </Notice>
              {outboxAction && (
                <div className="grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 md:grid-cols-2">
                  <span className="font-mono">idempotency {compactId(outboxAction.operationId, 20, 8)}</span>
                  <span className="font-mono">correlation {compactId(outboxAction.correlationId, 20, 8)}</span>
                </div>
              )}
              <FormField label="Reason" required>
                <Textarea value={outboxActionReason} onChange={(event) => setOutboxActionReason(event.target.value)} rows={3} />
              </FormField>
              {outboxAction && !outboxAction.dryRun && (
                <div className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-3">
                  <FormField label="Evidence reference" required>
                    <Input value={outboxApprovalEvidence} onChange={(event) => setOutboxApprovalEvidence(event.target.value)} />
                  </FormField>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={outboxApprovalMutation.isPending}
                      onClick={() => outboxApprovalMutation.mutate()}
                    >
                      Request approval
                    </Button>
                    {outboxApprovalResult && (
                      <Badge value={outboxApprovalResult.status} label={compactId(outboxApprovalResult.id, 18, 8)} tone={statusTone(outboxApprovalResult.status)} />
                    )}
                  </div>
                  <FormField label="Approval ID" required>
                    <Input value={outboxApprovalId} onChange={(event) => setOutboxApprovalId(event.target.value)} />
                  </FormField>
                  <FormField label="Review note" required>
                    <Input value={outboxApprovalReviewNote} onChange={(event) => setOutboxApprovalReviewNote(event.target.value)} />
                  </FormField>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={outboxApprovalReviewMutation.isPending || !outboxApprovalId.trim()}
                    onClick={() => outboxApprovalReviewMutation.mutate()}
                  >
                    Approve approval
                  </Button>
                  {outboxApprovalMutation.isError && <ErrorState error={outboxApprovalMutation.error} />}
                  {outboxApprovalReviewMutation.isError && <ErrorState error={outboxApprovalReviewMutation.error} />}
                </div>
              )}
              {outboxActionMutation.isError && <ErrorState error={outboxActionMutation.error} />}
            </div>
          </ConfirmDialog>
        </>
      )}
    </div>
  );
}

function EnrollmentBenefitReconciliationSection({
  query,
  enabled
}: {
  query: ReturnType<typeof useQuery<EnrollmentBenefitReconciliationResponse>>;
  enabled: boolean;
}) {
  const items = query.data?.items ?? [];
  return (
    <Card>
      <CardHeader
        title="Enrollment / order reconciliation"
        subtitle={query.data ? `Generated ${formatDateTime(query.data.generatedAt)}` : "Payment, drop và promotion state evidence."}
      />
      {!enabled && <EmptyState message="Nhập courseId, learner/profile hoặc enrollmentId để xem enrollment reconciliation." />}
      {enabled && query.isError && <SectionError error={query.error} />}
      {enabled && (
        <LoadingOrEmpty loading={query.isLoading} empty={!items.length}>
          <Table>
            <thead>
              <tr>
                <Th>Status</Th>
                <Th>Enrollment / order</Th>
                <Th>Promotion</Th>
                <Th>Evidence</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.reconciliationKey} className={cn(problemEnrollmentReconciliation(item) && "bg-amber-50/60")}>
                  <Td>
                    <StatusPill value={item.reconciliationStatus} />
                    <p className="mt-1 text-xs font-semibold uppercase text-slate-500">{item.severity}</p>
                  </Td>
                  <Td>
                    <p><IdLink value={item.enrollmentId} /></p>
                    <p className="mt-1 text-xs text-slate-500">
                      <StatusPill value={item.enrollmentStatus} /> {compactId(item.studentId, 14, 6)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Order {item.orderId ? compactId(item.orderId) : "-"} · {item.orderStatus ?? "-"} · {item.orderAmount ?? "-"} {item.currency ?? ""}
                    </p>
                  </Td>
                  <Td>
                    <p><StatusPill value={item.promotionStatus} /></p>
                    <p className="mt-1 text-xs text-slate-500">Reservation {compactId(item.reservationId)}</p>
                    <p className="mt-1 text-xs text-slate-500">Redemption {compactId(item.redemptionId)}</p>
                  </Td>
                  <Td>
                    <p className="text-xs font-semibold text-slate-700">{item.reasonCodes[0] ?? "-"}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.reasonCodes.slice(1).join(", ") || item.promotionLastRetryError || item.dropReason || "-"}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      paid {formatDateTime(item.paidAt)} · promo {formatDateTime(item.promotionUpdatedAt)}
                    </p>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </LoadingOrEmpty>
      )}
    </Card>
  );
}

function EnrollmentPromotionSection({
  query
}: {
  query: ReturnType<typeof useQuery<EnrollmentPromotionApplicationState[]>>;
}) {
  const items = query.data ?? [];
  return (
    <Card>
      <CardHeader title="Enrollment promotion remediation" subtitle="Coupon application state từ enrollment checkout." />
      {query.isError && <SectionError error={query.error} />}
      <LoadingOrEmpty loading={query.isLoading} empty={!items.length}>
        <Table>
          <thead>
            <tr>
              <Th>Status</Th>
              <Th>Enrollment</Th>
              <Th>Coupon</Th>
              <Th>Retry</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className={cn(problemPromotionApplication(item) && "bg-amber-50/60")}>
                <Td><StatusPill value={item.status} /></Td>
                <Td>
                  <p><IdLink value={item.enrollmentId} /></p>
                  <p className="mt-1 text-xs text-slate-500">Learner {compactId(item.studentId)}</p>
                </Td>
                <Td>
                  <p className="font-semibold text-slate-800">{maskCouponDisplay(item.couponCode, item.couponId)}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.message ?? item.reasonCodes.join(", ")}</p>
                </Td>
                <Td>
                  <p className="text-sm font-semibold text-slate-800">{item.retryCount ?? 0}</p>
                  <p className="mt-1 text-xs text-slate-500">{formatDateTime(item.nextRetryAt)}</p>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </LoadingOrEmpty>
    </Card>
  );
}

function EnrollmentRemediationSection({
  query,
  onAction
}: {
  query: ReturnType<typeof useQuery<EnrollmentRemediationCase[]>>;
  onAction: (remediationCase: EnrollmentRemediationCase, action: "assign" | "note" | "resolve") => void;
}) {
  const items = query.data ?? [];
  return (
    <Card>
      <CardHeader title="Enrollment remediation cases" subtitle="Assigned recovery workflow cho checkout, payment và promotion failures." />
      {query.isError && <SectionError error={query.error} />}
      <LoadingOrEmpty loading={query.isLoading} empty={!items.length}>
        <Table>
          <thead>
            <tr>
              <Th>Status / SLA</Th>
              <Th>Case</Th>
              <Th>Enrollment evidence</Th>
              <Th>Owner / actions</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const latestAction = item.actionHistory.at(-1);
              const latestRetry = item.retryHistory.at(-1);
              const latestCorrelation = latestRemediationCorrelation(item);
              const closed = item.status === "RESOLVED" || Boolean(item.closedAt);
              return (
                <tr key={item.id} className={cn(problemRemediationCase(item) && "bg-amber-50/60")}>
                  <Td>
                    <StatusPill value={item.status} />
                    <p className="mt-1 text-xs font-semibold uppercase text-slate-500">{item.severity}</p>
                    <p className={cn("mt-1 text-xs", item.slaBreached ? "font-semibold text-red-700" : "text-slate-500")}>
                      SLA {item.slaAgeMinutes}m · due {formatDateTime(item.slaDueAt)}
                    </p>
                  </Td>
                  <Td>
                    <p className="font-mono text-xs font-semibold text-slate-800">{compactId(item.id, 18, 8)}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.caseType}</p>
                    <p className="mt-1 text-xs font-semibold text-slate-700">{item.reasonCode}</p>
                    {latestCorrelation && (
                      <p className="mt-1 font-mono text-xs text-slate-500">corr {compactId(latestCorrelation, 14, 6)}</p>
                    )}
                  </Td>
                  <Td>
                    <p>Enrollment <IdLink value={item.enrollmentId} /></p>
                    <p className="mt-1 text-xs text-slate-500">Order {compactId(item.orderId)}</p>
                    <p className="mt-1 text-xs text-slate-500">Promotion app {compactId(item.promotionApplicationId)}</p>
                    <p className="mt-1 text-xs text-slate-500">Learner {compactId(item.studentId, 14, 6)}</p>
                  </Td>
                  <Td>
                    <p className="text-xs font-semibold text-slate-700">{item.assigneeId || "unassigned"}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.note || latestAction?.note || "-"}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      last {latestAction ? `${latestAction.action} by ${latestAction.actorId ?? "-"}` : formatDateTime(item.updatedAt)}
                      {" "}· actions {item.actionHistory.length}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      retries {item.retryHistory.length}
                      {latestRetry ? ` · ${latestRetry.action} ${formatDateTime(latestRetry.createdAt)}` : ""}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button type="button" variant="secondary" onClick={() => onAction(item, "assign")} disabled={closed}>
                        Assign
                      </Button>
                      <Button type="button" variant="outline" onClick={() => onAction(item, "note")} disabled={closed}>
                        Note
                      </Button>
                      <Button type="button" variant="primary" onClick={() => onAction(item, "resolve")} disabled={closed}>
                        Resolve
                      </Button>
                    </div>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </LoadingOrEmpty>
    </Card>
  );
}

function CouponSection({
  query,
  enabled
}: {
  query: ReturnType<typeof useQuery<Coupon>>;
  enabled: boolean;
}) {
  const coupon = query.data;
  return (
    <Card>
      <CardHeader title="Coupon snapshot" subtitle="Trạng thái coupon liên quan tới case filter." />
      {!enabled && <EmptyState message="Nhập couponId để xem coupon snapshot." />}
      {enabled && query.isError && <SectionError error={query.error} />}
      {enabled && (
        <LoadingOrEmpty loading={query.isLoading} empty={!coupon}>
          {coupon && (
            <div className="grid gap-3 p-4 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">Status</p>
                <div className="mt-1"><StatusPill value={coupon.status} /></div>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">Coupon</p>
                <p className="mt-1 font-mono text-xs text-slate-700">{coupon.codeMask || compactId(coupon.id)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">Campaign</p>
                <p className="mt-1 font-mono text-xs text-slate-700">{compactId(coupon.campaignId)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">Holder</p>
                <p className="mt-1 font-mono text-xs text-slate-700">{coupon.holderProfileId ? compactId(coupon.holderProfileId, 14, 6) : "-"}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">Window</p>
                <p className="mt-1 text-sm text-slate-700">{formatDateTime(coupon.startsAt)} - {formatDateTime(coupon.expiresAt)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">Limits</p>
                <p className="mt-1 text-sm text-slate-700">
                  {coupon.maxRedemptions ?? "-"} total · {coupon.maxRedemptionsPerProfile ?? "-"} per profile
                </p>
              </div>
            </div>
          )}
        </LoadingOrEmpty>
      )}
    </Card>
  );
}

function PromotionRuntimeSection({
  redemptions,
  redemptionsLoading,
  redemptionsError,
  reservations,
  reservationsLoading,
  reservationsError
}: {
  redemptions: Redemption[];
  redemptionsLoading: boolean;
  redemptionsError: unknown;
  reservations: Reservation[];
  reservationsLoading: boolean;
  reservationsError: unknown;
}) {
  return (
    <Card>
      <CardHeader title="Promotion runtime" subtitle="Reservations và redemptions liên quan tới case." />
      {(redemptionsError || reservationsError) ? <SectionError error={redemptionsError ?? reservationsError} /> : null}
      <div className="space-y-4 p-4">
        <div>
          <h3 className="mb-2 text-sm font-bold text-slate-900">Redemptions</h3>
          <LoadingOrEmpty loading={redemptionsLoading} empty={!redemptions.length}>
            <Table>
              <thead>
                <tr>
                  <Th>Status</Th>
                  <Th>Redemption</Th>
                  <Th>Campaign</Th>
                  <Th>Redeemed</Th>
                </tr>
              </thead>
              <tbody>
                {redemptions.map((item) => (
                  <tr key={item.id}>
                    <Td><StatusPill value={item.status} /></Td>
                    <Td><IdLink value={item.id} to={`/incentives/redemptions/${item.id}`} /></Td>
                    <Td>{compactId(item.campaignId)}</Td>
                    <Td>{formatDateTime(item.redeemedAt)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </LoadingOrEmpty>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-bold text-slate-900">Reservations</h3>
          <LoadingOrEmpty loading={reservationsLoading} empty={!reservations.length}>
            <Table>
              <thead>
                <tr>
                  <Th>Status</Th>
                  <Th>Reservation</Th>
                  <Th>External ref</Th>
                  <Th>Expires</Th>
                </tr>
              </thead>
              <tbody>
                {reservations.map((item) => (
                  <tr key={item.id} className={cn(item.expired && "bg-amber-50/60")}>
                    <Td><StatusPill value={item.status} /></Td>
                    <Td><IdLink value={item.id} /></Td>
                    <Td>{compactId(item.externalReference)}</Td>
                    <Td>{formatDateTime(item.expiresAt)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </LoadingOrEmpty>
        </div>
      </div>
    </Card>
  );
}

function ReconciliationSection({
  query
}: {
  query: ReturnType<typeof useQuery<import("./types").IncentiveReconciliationQueryResponse>>;
}) {
  const items = query.data?.items ?? [];
  return (
    <Card>
      <CardHeader title="Financial / benefit reconciliation" subtitle={query.data ? `Generated ${formatDateTime(query.data.generatedAt)}` : "Promotion ledger/effect/outbox evidence."} />
      {query.isError && <SectionError error={query.error} />}
      <LoadingOrEmpty loading={query.isLoading} empty={!items.length}>
        <Table>
          <thead>
            <tr>
              <Th>Status</Th>
              <Th>Direction</Th>
              <Th>Redemption</Th>
              <Th>Outbox</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={`${item.ledgerEntryId}-${item.reconciliationKey}`} className={cn(problemReconciliation(item) && "bg-amber-50/60")}>
                <Td><StatusPill value={item.reconciliationStatus} /></Td>
                <Td>
                  <p className="font-semibold text-slate-800">{statusLabel(item.direction)}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.reasonCodes.join(", ") || "-"}</p>
                </Td>
                <Td><IdLink value={item.redemptionId} to={item.redemptionId ? `/incentives/redemptions/${item.redemptionId}` : undefined} /></Td>
                <Td>
                  <StatusPill value={item.outboxStatus} />
                  <p className="mt-1 text-xs text-slate-500">{item.outboxEventType ?? "-"}</p>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </LoadingOrEmpty>
    </Card>
  );
}

function LoyaltyBenefitReconciliationSection({
  query
}: {
  query: ReturnType<typeof useQuery<LoyaltyBenefitReconciliationQueryResponse>>;
}) {
  const items = query.data?.items ?? [];
  return (
    <Card>
      <CardHeader
        title="Loyalty benefit reconciliation"
        subtitle={query.data ? `Generated ${formatDateTime(query.data.generatedAt)}` : "Promotion points intent và reward reversal evidence."}
      />
      {query.isError && <SectionError error={query.error} />}
      <LoadingOrEmpty loading={query.isLoading} empty={!items.length}>
        <Table>
          <thead>
            <tr>
              <Th>Status</Th>
              <Th>Benefit</Th>
              <Th>Expected / ledger</Th>
              <Th>Evidence</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.reconciliationKey} className={cn(problemLoyaltyBenefitReconciliation(item) && "bg-amber-50/60")}>
                <Td>
                  <StatusPill value={item.reconciliationStatus} />
                  <p className="mt-1 text-xs font-semibold uppercase text-slate-500">{item.severity}</p>
                </Td>
                <Td>
                  <p className="font-semibold text-slate-800">{statusLabel(item.itemType)}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.expectedEntryType ?? item.rewardStatus ?? "-"} · {item.expectedPointsDelta || item.rewardPointsCost} pts
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    redemption {compactId(item.redemptionId ?? item.rewardRedemptionId)}
                  </p>
                </Td>
                <Td>
                  <p className="font-mono text-xs text-slate-700">{compactId(item.expectedSourceReference, 18, 8)}</p>
                  <p className="mt-1 text-xs text-slate-500">ledger {compactId(item.ledgerEntryId)}</p>
                  <p className="mt-1 text-xs text-slate-500">reversal of {compactId(item.reversalOfEntryId ?? item.rewardBurnEntryId)}</p>
                </Td>
                <Td>
                  <p className="text-xs font-semibold text-slate-700">{item.reasonCodes[0] ?? "-"}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.reasonCodes.slice(1).join(", ") || item.sourceEventType || item.rewardCode || "-"}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    observed {formatDateTime(item.observedAt ?? item.rewardReversedAt)} · payload {compactId(item.payloadHash, 14, 6)}
                  </p>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </LoadingOrEmpty>
    </Card>
  );
}

function RewardSection({
  rewards,
  loading,
  error
}: {
  rewards: LoyaltyRewardRedemption[];
  loading: boolean;
  error: unknown;
}) {
  return (
    <Card>
      <CardHeader title="Reward fulfillment" subtitle="Reward burn, fulfillment state và external reference." />
      {error ? <SectionError error={error} /> : null}
      <LoadingOrEmpty loading={loading} empty={!rewards.length}>
        <Table>
          <thead>
            <tr>
              <Th>Status</Th>
              <Th>Fulfillment</Th>
              <Th>Reward</Th>
              <Th>Redeemed</Th>
            </tr>
          </thead>
          <tbody>
            {rewards.map((item) => (
              <tr key={item.id} className={cn(problemReward(item) && "bg-amber-50/60")}>
                <Td><StatusPill value={item.status} /></Td>
                <Td>
                  <StatusPill value={item.fulfillmentStatus} />
                  <p className="mt-1 text-xs text-slate-500">{item.fulfillmentRef ?? item.fulfillmentNote ?? "-"}</p>
                </Td>
                <Td>
                  <p className="font-semibold text-slate-800">{item.rewardCode}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.pointsCost.toLocaleString()} points</p>
                </Td>
                <Td>{formatDateTime(item.redeemedAt)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </LoadingOrEmpty>
    </Card>
  );
}

function LoyaltyLedgerSection({
  items,
  loading,
  error,
  enabled
}: {
  items: LoyaltyLedgerEntry[];
  loading: boolean;
  error: unknown;
  enabled: boolean;
}) {
  return (
    <Card>
      <CardHeader title="Loyalty ledger" subtitle="Ledger chỉ tải khi filter có loyalty account id để tránh query rộng." />
      {!enabled && <EmptyState message="Nhập loyaltyAccountId để xem ledger entries." />}
      {enabled && error ? <SectionError error={error} /> : null}
      {enabled && (
        <LoadingOrEmpty loading={loading} empty={!items.length}>
          <Table>
            <thead>
              <tr>
                <Th>Type</Th>
                <Th>Points</Th>
                <Th>Source</Th>
                <Th>Occurred</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <Td><StatusPill value={item.entryType} /></Td>
                  <Td className={cn(item.pointsDelta < 0 ? "text-red-700" : "text-emerald-700", "font-semibold")}>
                    {item.pointsDelta.toLocaleString()}
                  </Td>
                  <Td className="font-mono text-xs">{compactId(item.sourceReference, 18, 8)}</Td>
                  <Td>{formatDateTime(item.occurredAt ?? item.createdAt)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </LoadingOrEmpty>
      )}
    </Card>
  );
}

function DeadLetterSection({
  loyaltyItems,
  outboxItems,
  loading,
  error,
  onOutboxAction
}: {
  loyaltyItems: LoyaltyInboundDeadLetter[];
  outboxItems: OutboxDeadLetterSummary[];
  loading: boolean;
  error: unknown;
  onOutboxAction: (deadLetter: OutboxDeadLetterSummary, action: "replay" | "discard", dryRun: boolean) => void;
}) {
  return (
    <Card>
      <CardHeader title="Open DLT / dead letters" subtitle="Inbound loyalty DLT và outbox relay dead-letter cùng một nơi." />
      {error ? <SectionError error={error} /> : null}
      <LoadingOrEmpty loading={loading} empty={!loyaltyItems.length && !outboxItems.length}>
        <div className="space-y-4 p-4">
          <div>
            <h3 className="mb-2 text-sm font-bold text-slate-900">Loyalty inbound DLT</h3>
            <Table>
              <thead>
                <tr>
                  <Th>Status</Th>
                  <Th>Topic</Th>
                  <Th>Payload</Th>
                  <Th>Error</Th>
                </tr>
              </thead>
              <tbody>
                {loyaltyItems.map((item) => (
                  <tr key={item.id} className={cn(openLoyaltyDeadLetter(item) && "bg-red-50/50")}>
                    <Td><StatusPill value={item.status} /></Td>
                    <Td>
                      <p className="font-semibold text-slate-800">{item.sourceTopic}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.dltTopic}</p>
                    </Td>
                    <Td className="font-mono text-xs">{compactId(item.payloadHash, 14, 8)}</Td>
                    <Td>{compactError(item.exceptionMessage)}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-bold text-slate-900">Outbox relay dead letters</h3>
            <Table>
              <thead>
                <tr>
                  <Th>Status</Th>
                  <Th>Topic/position</Th>
                  <Th>Service/event</Th>
                  <Th>Payload/error</Th>
                  <Th>Actions</Th>
                </tr>
              </thead>
              <tbody>
                {outboxItems.map((item) => (
                  <tr key={item.id} className={cn(openOutboxDeadLetter(item) && "bg-red-50/50")}>
                    <Td>
                      <StatusPill value={item.status} />
                      <p className="mt-1 text-xs text-slate-500">{item.replayAttempts} replay · {item.attempts} relay</p>
                    </Td>
                    <Td>
                      <p className="font-semibold text-slate-800">{outboxTopic(item)}</p>
                      <p className="mt-1 font-mono text-xs text-slate-500">{outboxPosition(item)}</p>
                    </Td>
                    <Td>
                      <p className="font-semibold text-slate-800">{item.serviceName}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.eventType}</p>
                      <p className="mt-1 font-mono text-xs text-slate-500">{compactId(item.aggregateId)}</p>
                    </Td>
                    <Td>
                      <p className="font-mono text-xs text-slate-600">{compactId(item.payloadHash, 18, 8)}</p>
                      <p className="mt-1 max-w-sm truncate text-xs font-semibold text-slate-700">{item.errorClass ?? "Unknown"}</p>
                      <p className="mt-1 max-w-sm truncate text-xs text-slate-500">{compactError(item.lastError)}</p>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="xs"
                          variant="outline"
                          disabled={!actionableOutboxDeadLetter(item)}
                          onClick={() => onOutboxAction(item, "replay", true)}
                        >
                          <Search size={14} />
                          Dry-run
                        </Button>
                        <Button
                          size="xs"
                          disabled={!actionableOutboxDeadLetter(item)}
                          onClick={() => onOutboxAction(item, "replay", false)}
                        >
                          <RefreshCcw size={14} />
                          Replay
                        </Button>
                        <Button
                          size="xs"
                          variant="danger"
                          disabled={!actionableOutboxDeadLetter(item)}
                          onClick={() => onOutboxAction(item, "discard", false)}
                        >
                          <Trash2 size={14} />
                          Discard
                        </Button>
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>
      </LoadingOrEmpty>
    </Card>
  );
}

function EnrollmentAuditSection({
  query,
  enabled
}: {
  query: ReturnType<typeof useQuery<AuditLogEntry[]>>;
  enabled: boolean;
}) {
  const items = query.data ?? [];
  return (
    <Card className="xl:col-span-2">
      <CardHeader title="Enrollment audit timeline" subtitle="Checkout, payment, remediation và status audit từ enrollment-service." />
      {!enabled && <EmptyState message="Nhập enrollmentId, courseId, learner/profile hoặc correlationId để xem enrollment audit." />}
      {enabled && query.isError && <SectionError error={query.error} />}
      {enabled && (
        <LoadingOrEmpty loading={query.isLoading} empty={!items.length}>
          <Table>
            <thead>
              <tr>
                <Th>Time</Th>
                <Th>Action</Th>
                <Th>Actor</Th>
                <Th>Enrollment</Th>
                <Th>Status</Th>
                <Th>Reason</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <Td>{formatDateTime(item.createdAt)}</Td>
                  <Td className="font-semibold text-slate-800">{item.action}</Td>
                  <Td>{item.actorId ?? "-"}</Td>
                  <Td><IdLink value={item.enrollmentId} /></Td>
                  <Td>
                    <p className="text-xs text-slate-500">{item.oldStatus ?? "-"}</p>
                    <p className="text-xs font-semibold text-slate-800">{item.newStatus ?? "-"}</p>
                  </Td>
                  <Td className="max-w-md truncate text-xs text-slate-600">{item.reason ?? "-"}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </LoadingOrEmpty>
      )}
    </Card>
  );
}

function AuditSection({
  query,
  title,
  subtitle
}: {
  query: ReturnType<typeof useQuery<import("./types").AuditQueryResponse>>;
  title: string;
  subtitle: string;
}) {
  const items = query.data?.items ?? [];
  return (
    <Card className="xl:col-span-2">
      <CardHeader title={title} subtitle={subtitle} />
      {query.isError && <SectionError error={query.error} />}
      <LoadingOrEmpty loading={query.isLoading} empty={!items.length}>
        <Table>
          <thead>
            <tr>
              <Th>Time</Th>
              <Th>Action</Th>
              <Th>Actor</Th>
              <Th>Aggregate</Th>
              <Th>Note</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item: AuditEvent) => (
              <tr key={item.id}>
                <Td>{formatDateTime(item.createdAt)}</Td>
                <Td>
                  <p className="font-semibold text-slate-800">{item.action}</p>
                  {item.correlationId && <p className="mt-1 font-mono text-xs text-slate-500">{compactId(item.correlationId, 12, 6)}</p>}
                </Td>
                <Td>{item.actorId ?? "-"}</Td>
                <Td>
                  <p>{item.aggregateType ?? "-"}</p>
                  <p className="mt-1 font-mono text-xs text-slate-500">{compactId(item.aggregateId)}</p>
                </Td>
                <Td>{item.note ?? "-"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </LoadingOrEmpty>
    </Card>
  );
}
