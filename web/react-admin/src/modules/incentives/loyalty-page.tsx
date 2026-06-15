import { FormEvent, ReactNode, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Clock3,
  ClipboardCheck,
  Eye,
  FileWarning,
  Gift,
  History,
  Link2,
  Medal,
  Pencil,
  Plus,
  RefreshCcw,
  Scale,
  Search,
  ShieldCheck,
  Trash2,
  UserRoundCheck,
  WalletCards
} from "lucide-react";
import { queryKeys } from "@/shared/api/query-keys";
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
  adjustLoyaltyPoints,
  approveLoyaltyAdjustmentApproval,
  approveLoyaltyDeadLetterApproval,
  backfillLoyaltyPointLots,
  createLoyaltyTierPolicy,
  createLoyaltyReward,
  createLoyaltyProgram,
  discardLoyaltyDeadLetter,
  executeLoyaltyExpiry,
  getLoyaltyDeadLetter,
  getLoyaltyApprovalEvidencePack,
  getLoyaltyProgram,
  listLoyaltyAdjustmentApprovals,
  listLoyaltyAccounts,
  listLoyaltyPrograms,
  listLoyaltyTierPolicies,
  loyaltyAccountTimeline,
  loyaltyProgramTimeline,
  listLoyaltyRewards,
  queryLoyaltyBalanceBuckets,
  queryLoyaltyAudit,
  queryLoyaltyDeadLetters,
  queryLoyaltyLedger,
  queryLoyaltyFinanceCloseout,
  queryLoyaltyReconciliation,
  queryLoyaltyRewardRedemptions,
  queryLoyaltyTierStates,
  recalculateLoyaltyTiers,
  rejectLoyaltyAdjustmentApproval,
  replayLoyaltyDeadLetter,
  requestLoyaltyDeadLetterApproval,
  retryLoyaltyRewardFulfillment,
  retentionOperationId,
  reverseLoyaltyRewardRedemption,
  runDueLoyaltyRewardFulfillments,
  runLoyaltyExpiryDryRun,
  submitLoyaltyAdjustmentApproval,
  submitLoyaltyExpiryApproval,
  submitLoyaltyRewardFulfillmentApproval,
  updateLoyaltyAccountStatus,
  updateLoyaltyTierPolicy,
  updateLoyaltyTierPolicyStatus,
  updateLoyaltyRewardFulfillment,
  updateLoyaltyReward,
  updateLoyaltyRewardStatus,
  updateLoyaltyProgram,
  updateLoyaltyProgramStatus,
  upsertLoyaltyClientBinding
} from "./api";
import { formatJson } from "./json";
import {
  compactId,
  formatDateTime,
  formatDateTimeInput,
  splitCommaList,
  statusLabel,
  statusTone,
  toIsoDateTime,
  toNumberOrUndefined
} from "./labels";
import { IncentiveNav } from "./pages";
import type {
  AuditEvent,
  AuditFilters,
  LoyaltyAccount,
  LoyaltyAccountFilters,
  LoyaltyAdjustmentApproval,
  LoyaltyAdjustmentApprovalFilters,
  LoyaltyApprovalEvidencePack,
  LoyaltyBalanceBucket,
  LoyaltyExpiryExecutionResponse,
  LoyaltyFinanceCloseoutExport,
  LoyaltyInboundDeadLetter,
  LoyaltyInboundDeadLetterApproval,
  LoyaltyInboundDeadLetterDetail,
  LoyaltyInboundDeadLetterFilters,
  LoyaltyClientBinding,
  LoyaltyLedgerEntry,
  PointLotBackfillResponse,
  LoyaltyProgram,
  LoyaltyProgramFilters,
  LoyaltyReconciliationEntry,
  LoyaltyReconciliationFilters,
  LoyaltyReward,
  LoyaltyRewardFilters,
  LoyaltyRewardRedemption,
  LoyaltyRewardRedemptionFilters,
  LoyaltyTierFilters,
  LoyaltyTierPolicy,
  LoyaltyTierState
} from "./types";

type LoyaltyTab = "programs" | "accounts" | "tiers" | "approvals" | "expiry" | "reconciliation" | "rewards" | "deadLetters" | "audit";

const DEFAULT_TENANT_ID = "courseflow";
const DEFAULT_APPLICATION_ID = "lms";
const ADJUSTMENT_APPROVAL_THRESHOLD = 1000;
const PROGRAM_STATUSES = ["DRAFT", "ACTIVE", "SUSPENDED", "ARCHIVED"];
const ACCOUNT_STATUSES = ["ACTIVE", "SUSPENDED", "CLOSED"];
const BINDING_STATUSES = ["ACTIVE", "SUSPENDED"];
const LOYALTY_ENTRY_TYPES = ["EARN", "BURN", "REVERSE", "ADJUST", "EXPIRE"];
const APPROVAL_STATUSES = ["PENDING", "APPROVED", "REJECTED", "EXECUTED"];
const REWARD_STATUSES = ["DRAFT", "ACTIVE", "SUSPENDED", "ARCHIVED"];
const REDEMPTION_STATUSES = ["COMMITTED", "REVERSED"];
const FULFILLMENT_STATUSES = ["PENDING", "ISSUED", "MANUAL_REQUIRED", "FAILED"];
const TIER_STATUSES = ["DRAFT", "ACTIVE", "SUSPENDED", "ARCHIVED"];
const DEAD_LETTER_STATUSES = ["OPEN", "FAILED", "REPLAYED", "DISCARDED"];
const DEFAULT_BINDING_OPERATIONS = "earn, adjust, reverse";

type BindingForm = {
  clientId: string;
  status: string;
  allowedOperations: string;
  correlationId: string;
};

type ProgramForm = {
  mode: "create" | "edit";
  program?: LoyaltyProgram;
  tenantId: string;
  applicationId: string;
  programId: string;
  name: string;
  pointUnit: string;
  allowNegativeBalance: boolean;
  defaultPointsExpiryDays: string;
  initialClientId: string;
  initialAllowedOperations: string;
  correlationId: string;
};

type AdjustmentForm = {
  pointsDelta: string;
  sourceReference: string;
  idempotencyKey: string;
  reason: string;
  correlationId: string;
  occurredAt: string;
  expiresAt: string;
};

type ExpiryDryRunForm = {
  tenantId: string;
  applicationId: string;
  programId: string;
  asOf: string;
  limit: string;
};

type PointLotBackfillForm = {
  tenantId: string;
  applicationId: string;
  programId: string;
  profileId: string;
  accountId: string;
  limit: string;
  reason: string;
  correlationId: string;
};

type RewardForm = {
  mode: "create" | "edit";
  rewardId?: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  rewardCode: string;
  name: string;
  description: string;
  pointsCost: string;
  status: string;
  startsAt: string;
  endsAt: string;
  inventoryLimit: string;
  perProfileLimit: string;
  fulfillmentType: string;
  fulfillmentConfigJson: string;
};

type TierPolicyForm = {
  mode: "create" | "edit";
  policyId?: string;
  tenantId: string;
  applicationId: string;
  programId: string;
  tierCode: string;
  name: string;
  rank: string;
  qualificationPoints: string;
  qualificationWindowDays: string;
  downgradeGraceDays: string;
  benefitsJson: string;
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

function FilterActions({ children }: { children: ReactNode }) {
  return <div className="flex items-end gap-2">{children}</div>;
}

function TabButton({
  active,
  children,
  onClick
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-semibold transition",
        active ? "bg-brand-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      )}
    >
      {children}
    </button>
  );
}

function Timeline({ events, isLoading }: { events?: AuditEvent[]; isLoading?: boolean }) {
  if (isLoading) return <Spinner label="Đang tải timeline" />;
  if (!events?.length) return <EmptyState message="Chưa có audit event phù hợp." />;
  return (
    <ol className="divide-y divide-slate-100">
      {events.map((event) => (
        <li key={event.id} className="grid gap-3 px-1 py-3 md:grid-cols-[170px_1fr]">
          <div>
            <p className="text-xs font-semibold text-slate-400">{formatDateTime(event.createdAt)}</p>
            <p className="mt-1 font-mono text-xs text-slate-400">{compactId(event.id)}</p>
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill value={event.action ?? "INFO"} label={event.action ?? "event"} />
              {event.aggregateType && <Badge value="AGGREGATE" label={event.aggregateType} tone="slate" />}
            </div>
            <p className="mt-2 break-words text-sm font-semibold text-slate-800">
              {event.note || event.actorId || "System event"}
            </p>
            <p className="mt-1 break-words font-mono text-xs text-slate-400">
              {compactId(event.aggregateId)} · corr {compactId(event.correlationId)}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function EventDrawer({
  event,
  onClose
}: {
  event: AuditEvent | null;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={Boolean(event)}
      onOpenChange={(open) => !open && onClose()}
      title="Loyalty audit event"
      description={event ? `${event.action ?? "event"} · ${formatDateTime(event.createdAt)}` : undefined}
    >
      {event && (
        <div className="grid gap-4">
          <div className="grid gap-3 md:grid-cols-2">
            <KeyValue label="ID" value={event.id} mono />
            <KeyValue label="Actor" value={event.actorId ?? "-"} />
            <KeyValue label="Aggregate" value={`${event.aggregateType ?? "-"} / ${compactId(event.aggregateId)}`} />
            <KeyValue label="Correlation" value={compactId(event.correlationId)} mono />
            <KeyValue label="Scope" value={`${event.tenantId ?? "-"} / ${event.applicationId ?? "-"}`} />
            <KeyValue label="Time" value={formatDateTime(event.createdAt)} />
          </div>
          {event.note && <Notice tone="neutral" title="Note">{event.note}</Notice>}
          <JsonBlock value={event.payload ?? {}} className="max-h-[560px]" />
        </div>
      )}
    </Drawer>
  );
}

function normalizeOperations(value: string) {
  return splitCommaList(value).map((operation) => operation.toLowerCase());
}

function bindingOperations(binding?: LoyaltyClientBinding | null) {
  return binding?.allowedOperations?.length ? binding.allowedOperations.join(", ") : DEFAULT_BINDING_OPERATIONS;
}

function programStatusOptions(current?: string | null) {
  return PROGRAM_STATUSES.filter((status) => status !== current);
}

function accountStatusOptions(current?: string | null) {
  return ACCOUNT_STATUSES.filter((status) => status !== current);
}

function newAdjustmentForm(account: LoyaltyAccount): AdjustmentForm {
  const operationId = retentionOperationId("loyalty-adjust");
  return {
    pointsDelta: "",
    sourceReference: `manual:${account.profileId}:${operationId}`,
    idempotencyKey: operationId,
    reason: "",
    correlationId: operationId,
    occurredAt: "",
    expiresAt: ""
  };
}

function newProgramForm(): ProgramForm {
  return {
    mode: "create",
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    programId: "",
    name: "",
    pointUnit: "POINT",
    allowNegativeBalance: false,
    defaultPointsExpiryDays: "",
    initialClientId: "checkout-service",
    initialAllowedOperations: DEFAULT_BINDING_OPERATIONS,
    correlationId: retentionOperationId("loyalty-program")
  };
}

function newRewardForm(): RewardForm {
  return {
    mode: "create",
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    programId: "",
    rewardCode: "",
    name: "",
    description: "",
    pointsCost: "100",
    status: "DRAFT",
    startsAt: "",
    endsAt: "",
    inventoryLimit: "",
    perProfileLimit: "",
    fulfillmentType: "MANUAL",
    fulfillmentConfigJson: "{}"
  };
}

function newTierPolicyForm(): TierPolicyForm {
  return {
    mode: "create",
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    programId: "",
    tierCode: "",
    name: "",
    rank: "1",
    qualificationPoints: "500",
    qualificationWindowDays: "365",
    downgradeGraceDays: "30",
    benefitsJson: "{}"
  };
}

function editRewardForm(reward: LoyaltyReward): RewardForm {
  return {
    mode: "edit",
    rewardId: reward.id,
    tenantId: reward.tenantId,
    applicationId: reward.applicationId,
    programId: reward.programId,
    rewardCode: reward.rewardCode,
    name: reward.name,
    description: reward.description ?? "",
    pointsCost: String(reward.pointsCost),
    status: reward.status,
    startsAt: reward.startsAt ? formatDateTimeInput(reward.startsAt) : "",
    endsAt: reward.endsAt ? formatDateTimeInput(reward.endsAt) : "",
    inventoryLimit: reward.inventoryLimit === undefined || reward.inventoryLimit === null ? "" : String(reward.inventoryLimit),
    perProfileLimit: reward.perProfileLimit === undefined || reward.perProfileLimit === null ? "" : String(reward.perProfileLimit),
    fulfillmentType: reward.fulfillmentType || "MANUAL",
    fulfillmentConfigJson: formatJson(reward.fulfillmentConfig ?? {})
  };
}

function editTierPolicyForm(policy: LoyaltyTierPolicy): TierPolicyForm {
  return {
    mode: "edit",
    policyId: policy.id,
    tenantId: policy.tenantId,
    applicationId: policy.applicationId,
    programId: policy.programId,
    tierCode: policy.tierCode,
    name: policy.name,
    rank: String(policy.rank),
    qualificationPoints: String(policy.qualificationPoints),
    qualificationWindowDays: String(policy.qualificationWindowDays),
    downgradeGraceDays: String(policy.downgradeGraceDays),
    benefitsJson: formatJson(policy.benefits ?? {})
  };
}

function editProgramForm(program: LoyaltyProgram): ProgramForm {
  return {
    mode: "edit",
    program,
    tenantId: program.tenantId,
    applicationId: program.applicationId,
    programId: program.programId,
    name: program.name,
    pointUnit: program.pointUnit,
    allowNegativeBalance: program.allowNegativeBalance,
    defaultPointsExpiryDays:
      program.defaultPointsExpiryDays === undefined || program.defaultPointsExpiryDays === null
        ? ""
        : String(program.defaultPointsExpiryDays),
    initialClientId: "",
    initialAllowedOperations: DEFAULT_BINDING_OPERATIONS,
    correlationId: retentionOperationId("loyalty-program-update")
  };
}

function ProgramsPanel() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<LoyaltyProgramFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<LoyaltyProgramFilters>(filters);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);
  const [programForm, setProgramForm] = useState<ProgramForm | null>(null);
  const [bindingProgram, setBindingProgram] = useState<LoyaltyProgram | null>(null);
  const [bindingForm, setBindingForm] = useState<BindingForm>({
    clientId: "",
    status: "ACTIVE",
    allowedOperations: DEFAULT_BINDING_OPERATIONS,
    correlationId: retentionOperationId("loyalty-binding")
  });
  const [programStatusTarget, setProgramStatusTarget] = useState<{ program: LoyaltyProgram; status: string } | null>(null);
  const [programStatusNote, setProgramStatusNote] = useState("");
  const [programStatusCorrelationId, setProgramStatusCorrelationId] = useState(retentionOperationId("loyalty-program-status"));

  const programsQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyPrograms(filters),
    queryFn: () => listLoyaltyPrograms(filters),
    retry: 1
  });

  const selectedProgramQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyProgram(selectedProgramId ?? undefined),
    queryFn: () => getLoyaltyProgram(selectedProgramId!),
    enabled: Boolean(selectedProgramId),
    retry: 1
  });

  const programTimelineQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyTimeline("program", selectedProgramId ?? undefined),
    queryFn: () => loyaltyProgramTimeline(selectedProgramId!, 25),
    enabled: Boolean(selectedProgramId),
    retry: 1
  });

  const programMutation = useMutation({
    mutationFn: () => {
      const expiryDays = toNumberOrUndefined(programForm?.defaultPointsExpiryDays);
      if (programForm?.mode === "create") {
        const initialBindings = programForm.initialClientId.trim()
          ? [
              {
                clientId: programForm.initialClientId.trim(),
                allowedOperations: normalizeOperations(programForm.initialAllowedOperations)
              }
            ]
          : undefined;
        return createLoyaltyProgram({
          tenantId: programForm.tenantId.trim(),
          applicationId: programForm.applicationId.trim(),
          programId: programForm.programId.trim(),
          name: programForm.name.trim(),
          pointUnit: programForm.pointUnit.trim() || undefined,
          allowNegativeBalance: programForm.allowNegativeBalance,
          defaultPointsExpiryDays: expiryDays,
          clientBindings: initialBindings
        });
      }
      return updateLoyaltyProgram(
        programForm!.program!.id,
        {
          name: programForm!.name.trim(),
          pointUnit: programForm!.pointUnit.trim() || undefined,
          allowNegativeBalance: programForm!.allowNegativeBalance,
          defaultPointsExpiryDays: expiryDays
        },
        programForm!.correlationId
      );
    },
    onSuccess: (program) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setProgramForm(null);
      setSelectedProgramId(program.id);
    }
  });

  const bindingMutation = useMutation({
    mutationFn: () =>
      upsertLoyaltyClientBinding(
        bindingProgram!.id,
        {
          clientId: bindingForm.clientId.trim(),
          status: bindingForm.status,
          allowedOperations: normalizeOperations(bindingForm.allowedOperations)
        },
        bindingForm.correlationId
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setBindingProgram(null);
    }
  });

  const programStatusMutation = useMutation({
    mutationFn: () =>
      updateLoyaltyProgramStatus(
        programStatusTarget!.program.id,
        { status: programStatusTarget!.status, note: programStatusNote.trim() || undefined },
        programStatusCorrelationId
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setProgramStatusTarget(null);
    }
  });

  const programs = programsQuery.data ?? [];
  const activeCount = useMemo(() => programs.filter((program) => program.status === "ACTIVE").length, [programs]);
  const bindingCount = useMemo(
    () => programs.reduce((total, program) => total + (program.clientBindings?.length ?? 0), 0),
    [programs]
  );
  const selectedProgram = selectedProgramQuery.data ?? programs.find((program) => program.id === selectedProgramId) ?? null;
  const programFormReady = programForm
    ? Boolean(
        programForm.tenantId.trim() &&
          programForm.applicationId.trim() &&
          programForm.programId.trim() &&
          programForm.name.trim()
      )
    : false;

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
  }

  function openBinding(program: LoyaltyProgram, binding?: LoyaltyClientBinding) {
    setSelectedProgramId(program.id);
    setBindingProgram(program);
    setBindingForm({
      clientId: binding?.clientId ?? "",
      status: binding?.status ?? "ACTIVE",
      allowedOperations: bindingOperations(binding),
      correlationId: retentionOperationId("loyalty-binding")
    });
  }

  function openProgramStatus(program: LoyaltyProgram, status: string) {
    setProgramStatusTarget({ program, status });
    setProgramStatusNote("");
    setProgramStatusCorrelationId(retentionOperationId("loyalty-program-status"));
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard label="Programs" value={programs.length} detail={`${activeCount} active`} icon={<ShieldCheck size={18} />} tone="success" />
        <StatCard label="Client bindings" value={bindingCount} detail="Service access policies" icon={<Link2 size={18} />} tone="brand" />
        <StatCard label="Scope" value={filters.applicationId ?? "-"} detail={filters.tenantId ?? "-"} icon={<ClipboardCheck size={18} />} tone="info" />
      </div>

      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Tenant">
            <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application">
            <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID">
            <Input value={draftFilters.programId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, programId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value })}>
              <option value="">All</option>
              {PROGRAM_STATUSES.map((status) => (
                <option key={status} value={status}>{statusLabel(status)}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Limit">
            <Input
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit">
              <Search size={16} />
              Tìm
            </Button>
            <Button type="button" variant="secondary" onClick={() => programsQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      <Card>
        <CardHeader
          title="Loyalty programs"
          subtitle="Program, trạng thái và service client được phép ghi điểm."
          actions={
            <div className="flex items-center gap-2">
              <Badge value="RESULT" label={`${programs.length} programs`} tone="slate" />
              <Button size="sm" onClick={() => setProgramForm(newProgramForm())}>
                <Plus size={15} />
                New
              </Button>
            </div>
          }
        />
        {programsQuery.isLoading && <Spinner />}
        {programsQuery.isError && <ErrorState error={programsQuery.error} />}
        {!programsQuery.isLoading && !programsQuery.isError && programs.length === 0 && <EmptyState message="Không có program phù hợp." />}
        {programs.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Program</Th>
                <Th>Status</Th>
                <Th>Point unit</Th>
                <Th>Bindings</Th>
                <Th>Updated</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {programs.map((program) => (
                <tr key={program.id} className="hover:bg-slate-50">
                  <Td>
                    <p className="font-semibold text-slate-900">{program.name}</p>
                    <p className="mt-1 font-mono text-xs text-slate-400">{program.programId}</p>
                  </Td>
                  <Td><StatusPill value={program.status} /></Td>
                  <Td>{program.pointUnit}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      {(program.clientBindings ?? []).slice(0, 3).map((binding) => (
                        <Badge key={binding.id} value={binding.status} label={binding.clientId} tone={statusTone(binding.status)} />
                      ))}
                      {(program.clientBindings?.length ?? 0) > 3 && <Badge value="MORE" label={`+${(program.clientBindings?.length ?? 0) - 3}`} tone="slate" />}
                      {!program.clientBindings?.length && <span className="text-sm text-slate-400">-</span>}
                    </div>
                  </Td>
                  <Td>{formatDateTime(program.updatedAt ?? program.createdAt)}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-2">
                      <Button size="xs" variant="secondary" onClick={() => setSelectedProgramId(program.id)}>Detail</Button>
                      <Button size="xs" variant="secondary" onClick={() => setProgramForm(editProgramForm(program))}>
                        <Pencil size={14} />
                        Edit
                      </Button>
                      <Button size="xs" variant="secondary" onClick={() => openBinding(program)}>
                        <Link2 size={14} />
                        Binding
                      </Button>
                      {programStatusOptions(program.status).slice(0, 2).map((status) => (
                        <Button
                          key={status}
                          size="xs"
                          variant={status === "SUSPENDED" || status === "ARCHIVED" ? "danger" : "secondary"}
                          onClick={() => openProgramStatus(program, status)}
                        >
                          {statusLabel(status)}
                        </Button>
                      ))}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Drawer
        open={Boolean(selectedProgramId)}
        onOpenChange={(open) => !open && setSelectedProgramId(null)}
        title="Loyalty program"
        description={selectedProgram ? `${selectedProgram.programId} · ${selectedProgram.tenantId}/${selectedProgram.applicationId}` : undefined}
      >
        {selectedProgramQuery.isLoading && <Spinner />}
        {selectedProgramQuery.isError && <ErrorState error={selectedProgramQuery.error} />}
        {selectedProgram && (
          <div className="grid gap-5">
            <div className="grid gap-3 md:grid-cols-2">
              <KeyValue label="ID" value={selectedProgram.id} mono />
              <KeyValue label="Status" value={<StatusPill value={selectedProgram.status} />} />
              <KeyValue label="Name" value={selectedProgram.name} />
              <KeyValue label="Point unit" value={selectedProgram.pointUnit} />
              <KeyValue label="Negative balance" value={selectedProgram.allowNegativeBalance ? "Allowed" : "Blocked"} />
              <KeyValue label="Default expiry" value={selectedProgram.defaultPointsExpiryDays ?? "-"} />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900">Client bindings</h3>
                <Button size="sm" variant="secondary" onClick={() => openBinding(selectedProgram)}>
                  <Link2 size={15} />
                  Add binding
                </Button>
              </div>
              <Table>
                <thead>
                  <tr>
                    <Th>Client</Th>
                    <Th>Status</Th>
                    <Th>Operations</Th>
                    <Th>Action</Th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedProgram.clientBindings ?? []).map((binding) => (
                    <tr key={binding.id}>
                      <Td>{binding.clientId}</Td>
                      <Td><StatusPill value={binding.status} /></Td>
                      <Td>{bindingOperations(binding)}</Td>
                      <Td>
                        <Button size="xs" variant="secondary" onClick={() => openBinding(selectedProgram, binding)}>Edit</Button>
                      </Td>
                    </tr>
                  ))}
                  {!selectedProgram.clientBindings?.length && (
                    <tr>
                      <Td colSpan={4}><EmptyState message="Chưa có client binding." /></Td>
                    </tr>
                  )}
                </tbody>
              </Table>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-bold text-slate-900">Timeline</h3>
              <Timeline events={programTimelineQuery.data?.items} isLoading={programTimelineQuery.isLoading} />
            </div>
          </div>
        )}
      </Drawer>

      <Drawer
        open={Boolean(programForm)}
        onOpenChange={(open) => !open && setProgramForm(null)}
        title={programForm?.mode === "edit" ? "Edit loyalty program" : "New loyalty program"}
        description={programForm?.mode === "edit" ? programForm.programId : "Create program and optional first client binding"}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setProgramForm(null)} disabled={programMutation.isPending}>Hủy</Button>
            <Button onClick={() => programMutation.mutate()} disabled={programMutation.isPending || !programFormReady}>
              {programMutation.isPending ? "Đang lưu" : programForm?.mode === "edit" ? "Lưu thay đổi" : "Tạo program"}
            </Button>
          </div>
        }
      >
        {programForm && (
          <div className="grid gap-4">
            {programMutation.isError && <ErrorState error={programMutation.error} />}
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Tenant" required>
                <Input
                  value={programForm.tenantId}
                  disabled={programForm.mode === "edit"}
                  onChange={(event) => setProgramForm({ ...programForm, tenantId: event.target.value })}
                />
              </FormField>
              <FormField label="Application" required>
                <Input
                  value={programForm.applicationId}
                  disabled={programForm.mode === "edit"}
                  onChange={(event) => setProgramForm({ ...programForm, applicationId: event.target.value })}
                />
              </FormField>
              <FormField label="Program ID" required>
                <Input
                  value={programForm.programId}
                  disabled={programForm.mode === "edit"}
                  onChange={(event) => setProgramForm({ ...programForm, programId: event.target.value })}
                />
              </FormField>
              <FormField label="Name" required>
                <Input value={programForm.name} onChange={(event) => setProgramForm({ ...programForm, name: event.target.value })} />
              </FormField>
              <FormField label="Point unit">
                <Input value={programForm.pointUnit} onChange={(event) => setProgramForm({ ...programForm, pointUnit: event.target.value })} />
              </FormField>
              <FormField label="Default expiry days">
                <Input
                  value={programForm.defaultPointsExpiryDays}
                  inputMode="numeric"
                  onChange={(event) => setProgramForm({ ...programForm, defaultPointsExpiryDays: event.target.value })}
                />
              </FormField>
            </div>
            <label className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
              <input
                type="checkbox"
                className="size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                checked={programForm.allowNegativeBalance}
                onChange={(event) => setProgramForm({ ...programForm, allowNegativeBalance: event.target.checked })}
              />
              Allow negative balance
            </label>
            {programForm.mode === "create" && (
              <div className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 md:grid-cols-2">
                <FormField label="Initial client ID">
                  <Input
                    value={programForm.initialClientId}
                    onChange={(event) => setProgramForm({ ...programForm, initialClientId: event.target.value })}
                  />
                </FormField>
                <FormField label="Allowed operations">
                  <Input
                    value={programForm.initialAllowedOperations}
                    onChange={(event) => setProgramForm({ ...programForm, initialAllowedOperations: event.target.value })}
                  />
                </FormField>
              </div>
            )}
            {programForm.mode === "edit" && (
              <FormField label="Correlation ID">
                <Input
                  value={programForm.correlationId}
                  onChange={(event) => setProgramForm({ ...programForm, correlationId: event.target.value })}
                />
              </FormField>
            )}
          </div>
        )}
      </Drawer>

      <Drawer
        open={Boolean(bindingProgram)}
        onOpenChange={(open) => !open && setBindingProgram(null)}
        title="Client binding"
        description={bindingProgram ? bindingProgram.programId : undefined}
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setBindingProgram(null)} disabled={bindingMutation.isPending}>Hủy</Button>
            <Button onClick={() => bindingMutation.mutate()} disabled={bindingMutation.isPending || !bindingForm.clientId.trim()}>
              {bindingMutation.isPending ? "Đang lưu" : "Lưu binding"}
            </Button>
          </div>
        }
      >
        <div className="grid gap-4">
          {bindingMutation.isError && <ErrorState error={bindingMutation.error} />}
          <FormField label="Client ID" required>
            <Input value={bindingForm.clientId} onChange={(event) => setBindingForm({ ...bindingForm, clientId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={bindingForm.status} onChange={(event) => setBindingForm({ ...bindingForm, status: event.target.value })}>
              {BINDING_STATUSES.map((status) => (
                <option key={status} value={status}>{statusLabel(status)}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Allowed operations">
            <Input value={bindingForm.allowedOperations} onChange={(event) => setBindingForm({ ...bindingForm, allowedOperations: event.target.value })} />
          </FormField>
          <FormField label="Correlation ID">
            <Input value={bindingForm.correlationId} onChange={(event) => setBindingForm({ ...bindingForm, correlationId: event.target.value })} />
          </FormField>
        </div>
      </Drawer>

      <ConfirmDialog
        open={Boolean(programStatusTarget)}
        onOpenChange={(open) => !open && setProgramStatusTarget(null)}
        title="Đổi trạng thái loyalty program"
        description={programStatusTarget ? `${programStatusTarget.program.programId} -> ${statusLabel(programStatusTarget.status)}` : undefined}
        confirmLabel="Cập nhật"
        tone={programStatusTarget?.status === "ACTIVE" ? "primary" : "danger"}
        isPending={programStatusMutation.isPending}
        onConfirm={() => programStatusMutation.mutate()}
      >
        <div className="grid gap-3">
          {programStatusMutation.isError && <ErrorState error={programStatusMutation.error} />}
          <FormField label="Note">
            <Textarea value={programStatusNote} onChange={(event) => setProgramStatusNote(event.target.value)} />
          </FormField>
          <FormField label="Correlation ID">
            <Input value={programStatusCorrelationId} onChange={(event) => setProgramStatusCorrelationId(event.target.value)} />
          </FormField>
        </div>
      </ConfirmDialog>
    </div>
  );
}

function AccountsPanel() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<LoyaltyAccountFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<LoyaltyAccountFilters>(filters);
  const [selectedAccount, setSelectedAccount] = useState<LoyaltyAccount | null>(null);
  const [adjustAccount, setAdjustAccount] = useState<LoyaltyAccount | null>(null);
  const [adjustmentForm, setAdjustmentForm] = useState<AdjustmentForm | null>(null);
  const [accountStatusTarget, setAccountStatusTarget] = useState<{ account: LoyaltyAccount; status: string } | null>(null);
  const [accountStatusNote, setAccountStatusNote] = useState("");
  const [accountStatusCorrelationId, setAccountStatusCorrelationId] = useState(retentionOperationId("loyalty-account-status"));

  const canSearchAccounts = Boolean(filters.tenantId && filters.applicationId && (filters.programId || filters.profileId));
  const accountsQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyAccounts(filters),
    queryFn: () => listLoyaltyAccounts(filters),
    enabled: canSearchAccounts,
    retry: 1
  });

  const ledgerQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyLedger({ accountId: selectedAccount?.id }),
    queryFn: () => queryLoyaltyLedger({ accountId: selectedAccount!.id }),
    enabled: Boolean(selectedAccount?.id),
    retry: 1
  });

  const balanceBucketsQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyBalanceBuckets(selectedAccount?.id),
    queryFn: () => queryLoyaltyBalanceBuckets(selectedAccount!.id),
    enabled: Boolean(selectedAccount?.id),
    retry: 1
  });

  const accountTimelineQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyTimeline("account", selectedAccount?.id),
    queryFn: () => loyaltyAccountTimeline(selectedAccount!.id, 25),
    enabled: Boolean(selectedAccount?.id),
    retry: 1
  });

  const adjustmentMutation = useMutation({
    mutationFn: () =>
      adjustLoyaltyPoints({
        tenantId: adjustAccount!.tenantId,
        applicationId: adjustAccount!.applicationId,
        programId: adjustAccount!.programId,
        profileId: adjustAccount!.profileId,
        pointsDelta: Number(adjustmentForm!.pointsDelta),
        sourceReference: adjustmentForm!.sourceReference.trim(),
        idempotencyKey: adjustmentForm!.idempotencyKey.trim(),
        reason: adjustmentForm!.reason.trim(),
        correlationId: adjustmentForm!.correlationId.trim(),
        occurredAt: toIsoDateTime(adjustmentForm!.occurredAt),
        expiresAt: toIsoDateTime(adjustmentForm!.expiresAt),
        metadata: { channel: "web-admin" }
      }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setSelectedAccount((current) =>
        current && current.id === response.accountId ? { ...current, balance: response.balance } : current
      );
      setAdjustAccount(null);
      setAdjustmentForm(null);
    }
  });

  const adjustmentApprovalMutation = useMutation({
    mutationFn: () =>
      submitLoyaltyAdjustmentApproval({
        tenantId: adjustAccount!.tenantId,
        applicationId: adjustAccount!.applicationId,
        programId: adjustAccount!.programId,
        profileId: adjustAccount!.profileId,
        pointsDelta: Number(adjustmentForm!.pointsDelta),
        sourceReference: adjustmentForm!.sourceReference.trim(),
        idempotencyKey: adjustmentForm!.idempotencyKey.trim(),
        reason: adjustmentForm!.reason.trim(),
        correlationId: adjustmentForm!.correlationId.trim(),
        occurredAt: toIsoDateTime(adjustmentForm!.occurredAt),
        expiresAt: toIsoDateTime(adjustmentForm!.expiresAt),
        metadata: { channel: "web-admin", approvalThreshold: ADJUSTMENT_APPROVAL_THRESHOLD }
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setAdjustAccount(null);
      setAdjustmentForm(null);
    }
  });

  const accountStatusMutation = useMutation({
    mutationFn: () =>
      updateLoyaltyAccountStatus(
        accountStatusTarget!.account.id,
        { status: accountStatusTarget!.status, note: accountStatusNote.trim() || undefined },
        accountStatusCorrelationId
      ),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setSelectedAccount(updated);
      setAccountStatusTarget(null);
    }
  });

  const accounts = accountsQuery.data ?? [];
  const ledgerRows = ledgerQuery.data?.items ?? [];
  const bucketRows = balanceBucketsQuery.data?.items ?? [];
  const adjustmentDelta = Number(adjustmentForm?.pointsDelta ?? "");
  const requiresAdjustmentApproval = Math.abs(adjustmentDelta) >= ADJUSTMENT_APPROVAL_THRESHOLD;
  const adjustmentReady = Boolean(
    adjustAccount &&
      adjustmentForm &&
      Number.isFinite(adjustmentDelta) &&
      adjustmentDelta !== 0 &&
      adjustmentForm.sourceReference.trim() &&
      adjustmentForm.idempotencyKey.trim() &&
      adjustmentForm.reason.trim() &&
      adjustmentForm.correlationId.trim()
  );

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
  }

  function openAccountStatus(account: LoyaltyAccount, status: string) {
    setAccountStatusTarget({ account, status });
    setAccountStatusNote("");
    setAccountStatusCorrelationId(retentionOperationId("loyalty-account-status"));
  }

  function openAdjustment(account: LoyaltyAccount) {
    setSelectedAccount(account);
    setAdjustAccount(account);
    setAdjustmentForm(newAdjustmentForm(account));
  }

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Tenant">
            <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application">
            <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID">
            <Input value={draftFilters.programId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, programId: event.target.value })} />
          </FormField>
          <FormField label="Profile ID">
            <Input value={draftFilters.profileId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, profileId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value })}>
              <option value="">All</option>
              {ACCOUNT_STATUSES.map((status) => (
                <option key={status} value={status}>{statusLabel(status)}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Limit">
            <Input
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit">
              <Search size={16} />
              Tìm
            </Button>
            <Button type="button" variant="secondary" onClick={() => accountsQuery.refetch()} disabled={!canSearchAccounts}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      {!canSearchAccounts && (
        <Notice tone="neutral" title="Account lookup">
          Nhập Program ID hoặc Profile ID để giới hạn phạm vi tìm kiếm account.
        </Notice>
      )}

      <Card>
        <CardHeader
          title="Loyalty accounts"
          subtitle="Balance, trạng thái account và ledger gần nhất."
          actions={<Badge value="RESULT" label={`${accounts.length} accounts`} tone="slate" />}
        />
        {accountsQuery.isLoading && <Spinner />}
        {accountsQuery.isError && <ErrorState error={accountsQuery.error} />}
        {canSearchAccounts && !accountsQuery.isLoading && !accountsQuery.isError && accounts.length === 0 && <EmptyState message="Không có account phù hợp." />}
        {accounts.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Profile</Th>
                <Th>Program</Th>
                <Th>Status</Th>
                <Th>Balance</Th>
                <Th>Opened</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.id} className="hover:bg-slate-50">
                  <Td>
                    <p className="font-semibold text-slate-900">{account.profileId}</p>
                    <p className="mt-1 font-mono text-xs text-slate-400">{compactId(account.id)}</p>
                  </Td>
                  <Td>{account.programId}</Td>
                  <Td><StatusPill value={account.status} /></Td>
                  <Td className="font-semibold">{account.balance}</Td>
                  <Td>{formatDateTime(account.openedAt)}</Td>
                  <Td>
                    <div className="flex flex-wrap gap-2">
                      <Button size="xs" variant="secondary" onClick={() => setSelectedAccount(account)}>Ledger</Button>
                      <Button
                        size="xs"
                        variant="secondary"
                        onClick={() => openAdjustment(account)}
                        disabled={account.status !== "ACTIVE"}
                      >
                        Adjust
                      </Button>
                      {accountStatusOptions(account.status).slice(0, 2).map((status) => (
                        <Button
                          key={status}
                          size="xs"
                          variant={status === "ACTIVE" ? "secondary" : "danger"}
                          onClick={() => openAccountStatus(account, status)}
                        >
                          {statusLabel(status)}
                        </Button>
                      ))}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Drawer
        open={Boolean(selectedAccount)}
        onOpenChange={(open) => !open && setSelectedAccount(null)}
        title="Account ledger"
        description={selectedAccount ? `${selectedAccount.profileId} · ${selectedAccount.programId}` : undefined}
      >
        {selectedAccount && (
          <div className="grid gap-5">
            <div className="grid gap-3 md:grid-cols-2">
              <KeyValue label="Account ID" value={selectedAccount.id} mono />
              <KeyValue label="Status" value={<StatusPill value={selectedAccount.status} />} />
              <KeyValue label="Balance" value={ledgerQuery.data?.balance ?? selectedAccount.balance} />
              <KeyValue label="Scope" value={`${selectedAccount.tenantId}/${selectedAccount.applicationId}`} />
            </div>
            <div>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900">Balance buckets</h3>
                {balanceBucketsQuery.data && (
                  <Badge value="PROJECTION" label={balanceBucketsQuery.data.projectionMode} tone="info" />
                )}
              </div>
              {balanceBucketsQuery.isLoading && <Spinner />}
              {balanceBucketsQuery.isError && <ErrorState error={balanceBucketsQuery.error} />}
              {balanceBucketsQuery.data && (
                <div className="mb-3 grid gap-3 md:grid-cols-3">
                  <StatCard label="Active points" value={balanceBucketsQuery.data.activePoints} tone="success" />
                  <StatCard label="Expired points" value={balanceBucketsQuery.data.expiredPoints} tone="warning" />
                  <StatCard label="Unallocated debit" value={balanceBucketsQuery.data.unallocatedDebitPoints} tone="danger" />
                </div>
              )}
              {balanceBucketsQuery.data?.warnings?.length ? (
                <Notice tone="warning" title="Projection warnings">
                  {balanceBucketsQuery.data.warnings.join(", ")}
                </Notice>
              ) : null}
              {!balanceBucketsQuery.isLoading && !balanceBucketsQuery.isError && bucketRows.length === 0 && (
                <EmptyState message="Không có bucket điểm còn lại." />
              )}
              {bucketRows.length > 0 && <BalanceBucketTable rows={bucketRows} />}
            </div>
            <div>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900">Ledger entries</h3>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => openAdjustment(selectedAccount)}
                  disabled={selectedAccount.status !== "ACTIVE"}
                >
                  Adjust points
                </Button>
              </div>
              {ledgerQuery.isLoading && <Spinner />}
              {ledgerQuery.isError && <ErrorState error={ledgerQuery.error} />}
              {!ledgerQuery.isLoading && !ledgerQuery.isError && ledgerRows.length === 0 && <EmptyState message="Chưa có ledger entry." />}
              {ledgerRows.length > 0 && <LedgerTable rows={ledgerRows} />}
            </div>
            <div>
              <h3 className="mb-2 text-sm font-bold text-slate-900">Timeline</h3>
              <Timeline events={accountTimelineQuery.data?.items} isLoading={accountTimelineQuery.isLoading} />
            </div>
          </div>
        )}
      </Drawer>

      <Drawer
        open={Boolean(adjustAccount)}
        onOpenChange={(open) => {
          if (!open) {
            setAdjustAccount(null);
            setAdjustmentForm(null);
          }
        }}
        title="Manual point adjustment"
        description={adjustAccount ? `${adjustAccount.profileId} · ${adjustAccount.programId}` : undefined}
        footer={
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setAdjustAccount(null);
                setAdjustmentForm(null);
              }}
              disabled={adjustmentMutation.isPending || adjustmentApprovalMutation.isPending}
            >
              Hủy
            </Button>
            {requiresAdjustmentApproval && (
              <Button
                onClick={() => adjustmentApprovalMutation.mutate()}
                disabled={adjustmentApprovalMutation.isPending || !adjustmentReady}
                variant="primary"
              >
                {adjustmentApprovalMutation.isPending ? "Đang gửi duyệt" : "Submit approval"}
              </Button>
            )}
            <Button
              onClick={() => adjustmentMutation.mutate()}
              disabled={adjustmentMutation.isPending || !adjustmentReady || requiresAdjustmentApproval}
              variant={adjustmentDelta < 0 ? "danger" : "primary"}
            >
              {adjustmentMutation.isPending ? "Đang ghi ledger" : "Ghi adjustment"}
            </Button>
          </div>
        }
      >
        {adjustAccount && adjustmentForm && (
          <div className="grid gap-4">
            {adjustmentMutation.isError && <ErrorState error={adjustmentMutation.error} />}
            {adjustmentApprovalMutation.isError && <ErrorState error={adjustmentApprovalMutation.error} />}
            <Notice tone="warning" title="Immutable ledger operation">
              Adjustment tạo ledger entry mới và không sửa/xóa entry cũ. Dùng source reference như change ticket để audit và replay an toàn.
            </Notice>
            {requiresAdjustmentApproval && (
              <Notice tone="info" title="Maker-checker required">
                Adjustment từ {ADJUSTMENT_APPROVAL_THRESHOLD} điểm trở lên phải được reviewer khác approve trước khi ghi ledger.
              </Notice>
            )}
            <div className="grid gap-3 md:grid-cols-2">
              <KeyValue label="Account" value={compactId(adjustAccount.id)} mono />
              <KeyValue label="Current balance" value={ledgerQuery.data?.balance ?? adjustAccount.balance} />
              <FormField label="Points delta" required hint="Dùng số dương để cộng điểm, số âm để trừ điểm.">
                <Input
                  value={adjustmentForm.pointsDelta}
                  inputMode="numeric"
                  onChange={(event) => setAdjustmentForm({ ...adjustmentForm, pointsDelta: event.target.value })}
                />
              </FormField>
              <FormField label="Source reference" required>
                <Input
                  value={adjustmentForm.sourceReference}
                  onChange={(event) => setAdjustmentForm({ ...adjustmentForm, sourceReference: event.target.value })}
                />
              </FormField>
              <FormField label="Idempotency key" required>
                <Input
                  value={adjustmentForm.idempotencyKey}
                  onChange={(event) => setAdjustmentForm({ ...adjustmentForm, idempotencyKey: event.target.value })}
                />
              </FormField>
              <FormField label="Correlation ID" required>
                <Input
                  value={adjustmentForm.correlationId}
                  onChange={(event) => setAdjustmentForm({ ...adjustmentForm, correlationId: event.target.value })}
                />
              </FormField>
              <FormField label="Occurred at">
                <Input
                  type="datetime-local"
                  value={adjustmentForm.occurredAt}
                  onChange={(event) => setAdjustmentForm({ ...adjustmentForm, occurredAt: event.target.value })}
                />
              </FormField>
              <FormField label="Expires at">
                <Input
                  type="datetime-local"
                  value={adjustmentForm.expiresAt}
                  onChange={(event) => setAdjustmentForm({ ...adjustmentForm, expiresAt: event.target.value })}
                />
              </FormField>
            </div>
            <FormField label="Reason" required>
              <Textarea value={adjustmentForm.reason} onChange={(event) => setAdjustmentForm({ ...adjustmentForm, reason: event.target.value })} />
            </FormField>
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        open={Boolean(accountStatusTarget)}
        onOpenChange={(open) => !open && setAccountStatusTarget(null)}
        title="Đổi trạng thái loyalty account"
        description={accountStatusTarget ? `${accountStatusTarget.account.profileId} -> ${statusLabel(accountStatusTarget.status)}` : undefined}
        confirmLabel="Cập nhật"
        tone={accountStatusTarget?.status === "ACTIVE" ? "primary" : "danger"}
        isPending={accountStatusMutation.isPending}
        onConfirm={() => accountStatusMutation.mutate()}
      >
        <div className="grid gap-3">
          {accountStatusMutation.isError && <ErrorState error={accountStatusMutation.error} />}
          <FormField label="Note">
            <Textarea value={accountStatusNote} onChange={(event) => setAccountStatusNote(event.target.value)} />
          </FormField>
          <FormField label="Correlation ID">
            <Input value={accountStatusCorrelationId} onChange={(event) => setAccountStatusCorrelationId(event.target.value)} />
          </FormField>
        </div>
      </ConfirmDialog>
    </div>
  );
}

function ApprovalsPanel() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<LoyaltyAdjustmentApprovalFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    status: "PENDING",
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<LoyaltyAdjustmentApprovalFilters>(filters);
  const [reviewTarget, setReviewTarget] = useState<{ approval: LoyaltyAdjustmentApproval; action: "approve" | "reject" } | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [evidencePack, setEvidencePack] = useState<LoyaltyApprovalEvidencePack | null>(null);

  const approvalsQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyAdjustmentApprovals(filters),
    queryFn: () => listLoyaltyAdjustmentApprovals(filters),
    enabled: Boolean(filters.tenantId && filters.applicationId),
    retry: 1
  });

  const reviewMutation = useMutation({
    mutationFn: () =>
      reviewTarget!.action === "approve"
        ? approveLoyaltyAdjustmentApproval(reviewTarget!.approval.id, { note: reviewNote.trim() })
        : rejectLoyaltyAdjustmentApproval(reviewTarget!.approval.id, { note: reviewNote.trim() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setReviewTarget(null);
      setReviewNote("");
    }
  });

  const evidenceMutation = useMutation({
    mutationFn: (approvalId: string) => getLoyaltyApprovalEvidencePack(approvalId),
    onSuccess: setEvidencePack
  });

  const approvals = approvalsQuery.data?.items ?? [];
  const pendingCount = approvals.filter((approval) => approval.status === "PENDING").length;

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
  }

  function openReview(approval: LoyaltyAdjustmentApproval, action: "approve" | "reject") {
    setReviewTarget({ approval, action });
    setReviewNote("");
  }

  function operationLabel(approval?: LoyaltyAdjustmentApproval | null) {
    if (approval?.operationType === "EXPIRY") return "expiry";
    if (approval?.operationType === "REWARD_REDEMPTION_REVERSE") return "reward reversal";
    if (approval?.operationType === "REWARD_FULFILLMENT_OVERRIDE") return "reward fulfillment";
    return "adjustment";
  }

  function approvalDescription(approval?: LoyaltyAdjustmentApproval | null) {
    if (!approval) {
      return undefined;
    }
    if (approval.operationType === "EXPIRY") {
      return `Expiry · ${formatDateTime(approval.metadata?.asOf as string)} · ${compactId(approval.metadata?.resultHash as string, 10, 6)}`;
    }
    if (approval.operationType === "REWARD_REDEMPTION_REVERSE") {
      return `${approval.metadata?.rewardCode ?? "Reward"} · reverse ${approval.pointsDelta} points`;
    }
    if (approval.operationType === "REWARD_FULFILLMENT_OVERRIDE") {
      return `${approval.metadata?.rewardCode ?? "Reward"} · ${approval.metadata?.currentFulfillmentStatus ?? "-"} to ${approval.metadata?.targetFulfillmentStatus ?? "-"}`;
    }
    return `${approval.profileId} · ${approval.pointsDelta} points`;
  }

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Tenant">
            <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application">
            <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID">
            <Input value={draftFilters.programId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, programId: event.target.value })} />
          </FormField>
          <FormField label="Profile ID">
            <Input value={draftFilters.profileId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, profileId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value })}>
              <option value="">All</option>
              {APPROVAL_STATUSES.map((status) => (
                <option key={status} value={status}>{statusLabel(status)}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Limit">
            <Input
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit">
              <Search size={16} />
              Query
            </Button>
            <Button type="button" variant="secondary" onClick={() => approvalsQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      <div className="grid gap-3 md:grid-cols-3">
        <StatCard label="Approvals" value={approvals.length} icon={<ClipboardCheck size={18} />} tone="info" />
        <StatCard label="Pending" value={pendingCount} tone="warning" />
        <StatCard label="Scope" value={filters.applicationId ?? "-"} detail={filters.tenantId ?? "-"} tone="brand" />
      </div>

      <Card>
        <CardHeader
          title="Operation approval queue"
          subtitle="Maker-checker queue cho high-risk adjustment và expiry execution."
          actions={<Badge value="RESULT" label={`${approvals.length} approvals`} tone="slate" />}
        />
        {approvalsQuery.isLoading && <Spinner />}
        {approvalsQuery.isError && <ErrorState error={approvalsQuery.error} />}
        {!approvalsQuery.isLoading && !approvalsQuery.isError && approvals.length === 0 && <EmptyState message="Không có approval phù hợp." />}
        {approvals.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Status</Th>
                <Th>Operation</Th>
                <Th>Delta</Th>
                <Th>Source</Th>
                <Th>Requested</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {approvals.map((approval) => (
                <tr key={approval.id}>
                  <Td>
                    <StatusPill value={approval.status} />
                    <p className="mt-1 font-mono text-xs text-slate-400">{compactId(approval.id)}</p>
                  </Td>
                  <Td>
                    <Badge value={approval.operationType} label={operationLabel(approval)} tone={approval.operationType === "EXPIRY" ? "danger" : "brand"} />
                    <p className="mt-2 font-semibold text-slate-900">
                      {approval.operationType === "EXPIRY"
                        ? "Expiry batch"
                        : approval.operationType === "REWARD_FULFILLMENT_OVERRIDE"
                          ? approval.metadata?.rewardCode as string ?? "Reward fulfillment"
                          : approval.profileId}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {approval.operationType === "EXPIRY" ? formatDateTime(approval.metadata?.asOf as string) : approval.programId}
                    </p>
                  </Td>
                  <Td className={cn("font-semibold", approval.pointsDelta < 0 ? "text-red-600" : "text-emerald-700")}>
                    {approval.pointsDelta > 0 ? `+${approval.pointsDelta}` : approval.pointsDelta}
                  </Td>
                  <Td>
                    <p className="font-mono text-xs text-slate-600">{approval.sourceReference}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {approval.operationType === "EXPIRY"
                        ? compactId(approval.metadata?.resultHash as string, 10, 6)
                        : approval.operationType === "REWARD_FULFILLMENT_OVERRIDE"
                          ? `${approval.metadata?.currentFulfillmentStatus ?? "-"} to ${approval.metadata?.targetFulfillmentStatus ?? "-"}`
                        : approval.reason}
                    </p>
                  </Td>
                  <Td>
                    <p>{formatDateTime(approval.requestedAt)}</p>
                    <p className="mt-1 text-xs text-slate-400">{approval.requestedBy}</p>
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-2">
                      <Button size="xs" variant="secondary" disabled={approval.status !== "PENDING"} onClick={() => openReview(approval, "approve")}>
                        Approve
                      </Button>
                      <Button size="xs" variant="danger" disabled={approval.status !== "PENDING"} onClick={() => openReview(approval, "reject")}>
                        Reject
                      </Button>
                      <Button size="xs" variant="secondary" onClick={() => evidenceMutation.mutate(approval.id)}>
                        Evidence
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {evidenceMutation.isError && <ErrorState error={evidenceMutation.error} />}
      {evidenceMutation.isPending && <Spinner label="Đang tải evidence pack" />}
      {evidencePack && (
        <Card>
          <CardHeader
            title="Approval evidence pack"
            subtitle={`${evidencePack.operationType} · ${compactId(evidencePack.approvalId)} · ${formatDateTime(evidencePack.generatedAt)}`}
            actions={<Badge value={evidencePack.approval.status} label={`${evidencePack.ledgerEntries.length} ledger rows`} tone="brand" />}
          />
          {evidencePack.warnings.length > 0 && (
            <Notice tone="warning" title="Evidence warnings">
              {evidencePack.warnings.join(", ")}
            </Notice>
          )}
          <div className="grid gap-3 md:grid-cols-4">
            <StatCard label="Ledger entries" value={evidencePack.ledgerEntries.length} tone="info" />
            <StatCard label="Audit events" value={evidencePack.auditEvents.length} tone="brand" />
            <StatCard label="Net points" value={String(evidencePack.evidenceSummary.netPoints ?? 0)} tone="warning" />
            <StatCard label="Missing outbox" value={String(evidencePack.evidenceSummary.missingOutboxCount ?? 0)} tone="danger" />
          </div>
          <pre className="mt-3 max-h-72 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
            {formatJson(evidencePack.evidenceSummary)}
          </pre>
        </Card>
      )}

      <ConfirmDialog
        open={Boolean(reviewTarget)}
        onOpenChange={(open) => !open && setReviewTarget(null)}
        title={`${reviewTarget?.action === "approve" ? "Approve" : "Reject"} ${operationLabel(reviewTarget?.approval)}`}
        description={approvalDescription(reviewTarget?.approval)}
        confirmLabel={
          reviewTarget?.action === "approve"
            ? reviewTarget.approval.operationType === "EXPIRY"
              ? "Approve"
              : "Approve & execute"
            : "Reject"
        }
        tone={reviewTarget?.action === "approve" ? "primary" : "danger"}
        isPending={reviewMutation.isPending}
        onConfirm={() => reviewMutation.mutate()}
      >
        <div className="grid gap-3">
          {reviewMutation.isError && <ErrorState error={reviewMutation.error} />}
          <FormField label="Review note" required>
            <Textarea value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
          </FormField>
        </div>
      </ConfirmDialog>
    </div>
  );
}

function BalanceBucketTable({ rows }: { rows: LoyaltyBalanceBucket[] }) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Status</Th>
          <Th>Remaining</Th>
          <Th>Original</Th>
          <Th>Expires</Th>
          <Th>Source</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((bucket) => (
          <tr key={bucket.entryId}>
            <Td><StatusPill value={bucket.status} /></Td>
            <Td className="font-semibold">{bucket.remainingPoints}</Td>
            <Td>{bucket.originalPoints}</Td>
            <Td>{formatDateTime(bucket.expiresAt)}</Td>
            <Td>
              <p className="font-mono text-xs text-slate-600">{bucket.sourceReference}</p>
              <p className="mt-1 text-xs text-slate-400">{bucket.entryType} · consumed {bucket.consumedPoints}</p>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function LedgerTable({ rows }: { rows: LoyaltyLedgerEntry[] }) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Time</Th>
          <Th>Type</Th>
          <Th>Delta</Th>
          <Th>Source</Th>
          <Th>Correlation</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((entry) => (
          <tr key={entry.id}>
            <Td>{formatDateTime(entry.occurredAt ?? entry.createdAt)}</Td>
            <Td><StatusPill value={entry.entryType} label={entry.entryType} /></Td>
            <Td className={cn("font-semibold", entry.pointsDelta < 0 ? "text-red-600" : "text-emerald-700")}>
              {entry.pointsDelta > 0 ? `+${entry.pointsDelta}` : entry.pointsDelta}
            </Td>
            <Td>
              <p className="font-mono text-xs text-slate-600">{entry.sourceReference}</p>
              {entry.reason && <p className="mt-1 text-xs text-slate-400">{entry.reason}</p>}
            </Td>
            <Td className="font-mono text-xs">{compactId(entry.correlationId)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function PointLotBackfillPanel() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<PointLotBackfillForm>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    programId: "",
    profileId: "",
    accountId: "",
    limit: "50",
    reason: "Rebuild loyalty point lots from immutable ledger",
    correlationId: retentionOperationId("loyalty-lot-backfill")
  });
  const [result, setResult] = useState<PointLotBackfillResponse | null>(null);

  const payload = (dryRun: boolean) => ({
    tenantId: form.tenantId.trim(),
    applicationId: form.applicationId.trim(),
    programId: form.programId.trim() || undefined,
    profileId: form.profileId.trim() || undefined,
    accountId: form.accountId.trim() || undefined,
    limit: toNumberOrUndefined(form.limit),
    dryRun,
    expectedResultHash: dryRun ? undefined : result?.resultHash,
    reason: form.reason.trim() || undefined,
    correlationId: form.correlationId.trim() || undefined
  });

  const dryRunMutation = useMutation({
    mutationFn: () => backfillLoyaltyPointLots(payload(true)),
    onSuccess: setResult
  });

  const executeMutation = useMutation({
    mutationFn: () => backfillLoyaltyPointLots(payload(false)),
    onSuccess: (response) => {
      setResult(response);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setForm({
        ...form,
        correlationId: retentionOperationId("loyalty-lot-backfill")
      });
    }
  });

  const canRun = Boolean(form.tenantId.trim() && form.applicationId.trim());
  const canExecute = Boolean(
    canRun &&
    form.reason.trim() &&
    form.correlationId.trim() &&
    result?.dryRun &&
    result.resultHash &&
    !result.hasMore
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canRun) {
      dryRunMutation.mutate();
    }
  }

  return (
    <Card>
      <CardHeader
        title="Point lot backfill"
        subtitle="Rebuild materialized remaining lots from immutable ledger before production expiry."
        actions={<Badge value="SETTLEMENT" label="Dry-run first" tone="warning" />}
      />
      <form onSubmit={submit}>
        <div className="grid gap-3 md:grid-cols-4">
          <FormField label="Tenant" required>
            <Input value={form.tenantId} onChange={(event) => setForm({ ...form, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application" required>
            <Input value={form.applicationId} onChange={(event) => setForm({ ...form, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID">
            <Input value={form.programId} onChange={(event) => setForm({ ...form, programId: event.target.value })} />
          </FormField>
          <FormField label="Profile ID">
            <Input value={form.profileId} onChange={(event) => setForm({ ...form, profileId: event.target.value })} />
          </FormField>
          <FormField label="Account ID">
            <Input value={form.accountId} onChange={(event) => setForm({ ...form, accountId: event.target.value })} />
          </FormField>
          <FormField label="Limit">
            <Input value={form.limit} inputMode="numeric" onChange={(event) => setForm({ ...form, limit: event.target.value })} />
          </FormField>
          <FormField label="Correlation ID" required>
            <Input value={form.correlationId} onChange={(event) => setForm({ ...form, correlationId: event.target.value })} />
          </FormField>
          <FormField label="Reason" required>
            <Input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
          </FormField>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="submit" disabled={!canRun || dryRunMutation.isPending}>
            <RefreshCcw size={16} />
            Dry-run backfill
          </Button>
          <Button
            type="button"
            variant="danger"
            disabled={!canExecute || executeMutation.isPending}
            onClick={() => executeMutation.mutate()}
          >
            Execute backfill
          </Button>
        </div>
      </form>

      {(dryRunMutation.isError || executeMutation.isError) && (
        <div className="mt-4">
          <ErrorState error={dryRunMutation.error ?? executeMutation.error} />
        </div>
      )}
      {(dryRunMutation.isPending || executeMutation.isPending) && (
        <div className="mt-4">
          <Spinner label="Đang xử lý point lot backfill" />
        </div>
      )}

      {result && (
        <div className="mt-5 space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <StatCard label="Scanned accounts" value={result.scannedAccountCount} tone="info" />
            <StatCard label="Affected accounts" value={result.affectedAccountCount} tone="brand" />
            <StatCard label="Missing lots" value={result.missingLotCount} tone="warning" />
            <StatCard label="Unallocated debit" value={result.unallocatedDebitPoints} tone="danger" />
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-500">Result hash</p>
            <p className="mt-1 break-all font-mono text-xs text-slate-700">{result.resultHash}</p>
          </div>
          {result.warnings.length > 0 && (
            <Notice tone="warning" title="Backfill warnings">
              {result.warnings.join(", ")}
            </Notice>
          )}
          {result.items.length === 0 && <EmptyState message="Không có account trong scope backfill." />}
          {result.items.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Account</Th>
                  <Th>Ledger</Th>
                  <Th>Projected remaining</Th>
                  <Th>Missing lots</Th>
                  <Th>Debits</Th>
                  <Th>Warnings</Th>
                </tr>
              </thead>
              <tbody>
                {result.items.slice(0, 12).map((item) => (
                  <tr key={item.accountId}>
                    <Td>
                      <p className="font-semibold text-slate-900">{item.profileId}</p>
                      <p className="mt-1 font-mono text-xs text-slate-400">{compactId(item.accountId)}</p>
                    </Td>
                    <Td>{item.ledgerBalance}</Td>
                    <Td>{item.projectedRemainingPoints}</Td>
                    <Td>{item.missingLotCount}</Td>
                    <Td>{item.debitEntryCount}</Td>
                    <Td className="text-xs">{item.warnings.length ? item.warnings.join(", ") : "OK"}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
      )}
    </Card>
  );
}

function ExpiryDryRunPanel() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ExpiryDryRunForm>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    programId: "",
    asOf: formatDateTimeInput(new Date().toISOString()),
    limit: "100"
  });
  const [executionForm, setExecutionForm] = useState({
    idempotencyKey: retentionOperationId("loyalty-expiry"),
    correlationId: retentionOperationId("loyalty-expiry"),
    reason: "Scheduled loyalty point expiry",
    approvalId: ""
  });
  const [executionResult, setExecutionResult] = useState<LoyaltyExpiryExecutionResponse | null>(null);
  const [expiryApproval, setExpiryApproval] = useState<LoyaltyAdjustmentApproval | null>(null);

  const dryRun = useMutation({
    mutationFn: () =>
      runLoyaltyExpiryDryRun({
        tenantId: form.tenantId.trim(),
        applicationId: form.applicationId.trim(),
        programId: form.programId.trim(),
        asOf: toIsoDateTime(form.asOf) ?? new Date().toISOString(),
        limit: toNumberOrUndefined(form.limit)
      }),
    onSuccess: () => {
      setExecutionResult(null);
      setExpiryApproval(null);
      setExecutionForm((current) => ({ ...current, approvalId: "" }));
    }
  });

  const executeMutation = useMutation({
    mutationFn: () =>
      executeLoyaltyExpiry({
        tenantId: form.tenantId.trim(),
        applicationId: form.applicationId.trim(),
        programId: form.programId.trim(),
        asOf: toIsoDateTime(form.asOf) ?? new Date().toISOString(),
        limit: toNumberOrUndefined(form.limit),
        idempotencyKey: executionForm.idempotencyKey.trim(),
        correlationId: executionForm.correlationId.trim(),
        reason: executionForm.reason.trim(),
        approvalId: executionForm.approvalId.trim()
      }),
    onSuccess: (response) => {
      setExecutionResult(response);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setExecutionForm({
        idempotencyKey: retentionOperationId("loyalty-expiry"),
        correlationId: retentionOperationId("loyalty-expiry"),
        reason: "Scheduled loyalty point expiry",
        approvalId: ""
      });
    }
  });

  const approvalMutation = useMutation({
    mutationFn: () =>
      submitLoyaltyExpiryApproval({
        tenantId: form.tenantId.trim(),
        applicationId: form.applicationId.trim(),
        programId: form.programId.trim(),
        asOf: toIsoDateTime(form.asOf) ?? new Date().toISOString(),
        limit: toNumberOrUndefined(form.limit),
        resultHash: dryRun.data!.resultHash,
        idempotencyKey: executionForm.idempotencyKey.trim(),
        correlationId: executionForm.correlationId.trim(),
        reason: executionForm.reason.trim()
      }),
    onSuccess: (approval) => {
      setExpiryApproval(approval);
      setExecutionForm((current) => ({ ...current, approvalId: approval.id }));
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
    }
  });

  const result = dryRun.data;
  const canRun = Boolean(form.tenantId.trim() && form.applicationId.trim() && form.programId.trim() && form.asOf.trim());
  const canRequestApproval = Boolean(
    result &&
      result.expiringPoints > 0 &&
      executionForm.idempotencyKey.trim() &&
      executionForm.correlationId.trim() &&
      executionForm.reason.trim()
  );
  const canExecute = Boolean(canRequestApproval && executionForm.approvalId.trim());

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canRun) {
      dryRun.mutate();
    }
  }

  return (
    <div className="space-y-4">
      <PointLotBackfillPanel />
      <form onSubmit={submit}>
        <Toolbar>
          <FormField label="Tenant" required>
            <Input value={form.tenantId} onChange={(event) => setForm({ ...form, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application" required>
            <Input value={form.applicationId} onChange={(event) => setForm({ ...form, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID" required>
            <Input value={form.programId} onChange={(event) => setForm({ ...form, programId: event.target.value })} />
          </FormField>
          <FormField label="As of" required>
            <Input type="datetime-local" value={form.asOf} onChange={(event) => setForm({ ...form, asOf: event.target.value })} />
          </FormField>
          <FormField label="Limit">
            <Input value={form.limit} inputMode="numeric" onChange={(event) => setForm({ ...form, limit: event.target.value })} />
          </FormField>
          <FilterActions>
            <Button type="submit" disabled={!canRun || dryRun.isPending}>
              <Clock3 size={16} />
              Dry-run
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      {dryRun.isError && <ErrorState error={dryRun.error} />}
      {dryRun.isPending && <Spinner label="Đang chạy expiry dry-run" />}

      {result && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <StatCard label="Candidate entries" value={result.candidateEntryCount} icon={<Clock3 size={18} />} tone="warning" />
            <StatCard label="Accounts" value={result.affectedAccountCount} icon={<WalletCards size={18} />} tone="info" />
            <StatCard label="Expiring points" value={result.expiringPoints} icon={<Activity size={18} />} tone="danger" />
            <StatCard label="Result hash" value={compactId(result.resultHash, 12, 6)} icon={<ClipboardCheck size={18} />} tone="brand" />
          </div>
          {result.warnings.length > 0 && (
            <Notice tone="warning" title="Dry-run warnings">
              {result.warnings.join(", ")}
            </Notice>
          )}
          <Card>
            <CardHeader
              title="Expiry candidates"
              subtitle={`${result.tenantId}/${result.applicationId}/${result.programId} · as of ${formatDateTime(result.asOf)}`}
              actions={<Badge value="DRY_RUN" label={`${result.samples.length} samples`} tone="warning" />}
            />
            {result.samples.length === 0 && <EmptyState message="Không có điểm đến hạn trong phạm vi dry-run." />}
            {result.samples.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Profile</Th>
                    <Th>Points</Th>
                    <Th>Source</Th>
                    <Th>Occurred</Th>
                    <Th>Expires</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.samples.map((candidate) => (
                    <tr key={candidate.entryId}>
                      <Td>
                        <p className="font-semibold text-slate-900">{candidate.profileId}</p>
                        <p className="mt-1 font-mono text-xs text-slate-400">{compactId(candidate.accountId)}</p>
                      </Td>
                      <Td className="font-semibold text-amber-700">{candidate.pointsDelta}</Td>
                      <Td className="font-mono text-xs">{candidate.sourceReference}</Td>
                      <Td>{formatDateTime(candidate.occurredAt)}</Td>
                      <Td>{formatDateTime(candidate.expiresAt)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
          <Card>
            <CardHeader
              title="Execute expiry"
              subtitle="Submit approval trước, reviewer approve ở tab Approvals, rồi execute bằng approval ID đã duyệt."
              actions={<Badge value="MAKER_CHECKER" label="Approval required" tone="danger" />}
            />
            <div className="grid gap-4">
              {approvalMutation.isError && <ErrorState error={approvalMutation.error} />}
              {executeMutation.isError && <ErrorState error={executeMutation.error} />}
              <Notice tone="warning" title="Settlement operation">
                Approval khóa dry-run result hash hiện tại. Nếu remaining lots thay đổi trước lúc execute, backend sẽ chặn vì candidate hash không còn khớp.
              </Notice>
              <div className="grid gap-3 md:grid-cols-3">
                <FormField label="Idempotency key" required>
                  <Input
                    value={executionForm.idempotencyKey}
                    onChange={(event) => setExecutionForm({ ...executionForm, idempotencyKey: event.target.value })}
                  />
                </FormField>
                <FormField label="Correlation ID" required>
                  <Input
                    value={executionForm.correlationId}
                    onChange={(event) => setExecutionForm({ ...executionForm, correlationId: event.target.value })}
                  />
                </FormField>
                <FormField label="Reason" required>
                  <Input
                    value={executionForm.reason}
                    onChange={(event) => setExecutionForm({ ...executionForm, reason: event.target.value })}
                  />
                </FormField>
                <FormField label="Approval ID" required>
                  <Input
                    value={executionForm.approvalId}
                    onChange={(event) => setExecutionForm({ ...executionForm, approvalId: event.target.value })}
                    placeholder="Paste approved expiry approval id"
                  />
                </FormField>
              </div>
              {expiryApproval && (
                <Notice tone={expiryApproval.status === "APPROVED" ? "success" : "info"} title={`Expiry approval ${expiryApproval.status}`}>
                  Approval {compactId(expiryApproval.id, 8, 6)} · {compactId(expiryApproval.metadata?.resultHash as string, 10, 6)}
                </Notice>
              )}
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => approvalMutation.mutate()} disabled={!canRequestApproval || approvalMutation.isPending}>
                  <ClipboardCheck size={16} />
                  {approvalMutation.isPending ? "Submitting approval" : "Submit approval"}
                </Button>
                <Button variant="danger" onClick={() => executeMutation.mutate()} disabled={!canExecute || executeMutation.isPending}>
                  {executeMutation.isPending ? "Executing" : "Execute expiry"}
                </Button>
              </div>
            </div>
          </Card>
          {executionResult && (
            <Card>
              <CardHeader
                title="Expiry execution result"
                subtitle={`${executionResult.tenantId}/${executionResult.applicationId}/${executionResult.programId} · ${formatDateTime(executionResult.asOf)}`}
                actions={<Badge value={executionResult.idempotencyReplay ? "REPLAY" : "EXECUTED"} label={`${executionResult.expiredLotCount} lots`} tone="success" />}
              />
              <div className="mb-3 grid gap-3 md:grid-cols-3">
                <StatCard label="Expired points" value={executionResult.expiredPoints} tone="danger" />
                <StatCard label="Accounts" value={executionResult.affectedAccountCount} tone="info" />
                <StatCard label="Entries" value={executionResult.items.length} tone="brand" />
              </div>
              {executionResult.warnings.length > 0 && (
                <Notice tone="warning" title="Execution warnings">
                  {executionResult.warnings.join(", ")}
                </Notice>
              )}
              {executionResult.items.length > 0 && (
                <Table>
                  <thead>
                    <tr>
                      <Th>Profile</Th>
                      <Th>Expired</Th>
                      <Th>Source lot</Th>
                      <Th>Ledger entry</Th>
                      <Th>Expires</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {executionResult.items.map((item) => (
                      <tr key={item.entryId}>
                        <Td>{item.profileId}</Td>
                        <Td className="font-semibold text-red-600">-{item.expiredPoints}</Td>
                        <Td className="font-mono text-xs">{compactId(item.sourceLotId)}</Td>
                        <Td className="font-mono text-xs">{compactId(item.entryId)}</Td>
                        <Td>{formatDateTime(item.expiresAt)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function ReconciliationPanel() {
  const [filters, setFilters] = useState<LoyaltyReconciliationFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<LoyaltyReconciliationFilters>(filters);
  const [hasQueried, setHasQueried] = useState(false);

  const canQuery = Boolean(filters.tenantId?.trim() && filters.applicationId?.trim());
  const reconciliationQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyReconciliation(filters),
    queryFn: () => queryLoyaltyReconciliation(filters),
    enabled: hasQueried && canQuery,
    retry: 1
  });

  const financeCloseout = useMutation({
    mutationFn: (cursor?: string) =>
      queryLoyaltyFinanceCloseout({
        tenantId: draftFilters.tenantId?.trim(),
        applicationId: draftFilters.applicationId?.trim(),
        programId: draftFilters.programId?.trim(),
        from: draftFilters.from,
        to: draftFilters.to,
        limit: draftFilters.limit,
        cursor
      })
  });

  const items = reconciliationQuery.data?.items ?? [];
  const matchedCount = useMemo(
    () => items.filter((item) => item.reconciliationStatus === "MATCHED").length,
    [items]
  );
  const pendingCount = useMemo(
    () => items.filter((item) => item.reconciliationStatus === "PENDING").length,
    [items]
  );
  const missingOutboxCount = useMemo(
    () => items.filter((item) => item.reconciliationStatus === "MISSING_OUTBOX").length,
    [items]
  );

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
    setHasQueried(true);
  }

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Tenant" required>
            <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application" required>
            <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID">
            <Input value={draftFilters.programId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, programId: event.target.value })} />
          </FormField>
          <FormField label="Profile ID">
            <Input value={draftFilters.profileId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, profileId: event.target.value })} />
          </FormField>
          <FormField label="Account ID">
            <Input value={draftFilters.accountId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, accountId: event.target.value })} />
          </FormField>
          <FormField label="Entry type">
            <Select value={draftFilters.entryType ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, entryType: event.target.value })}>
              <option value="">All</option>
              {LOYALTY_ENTRY_TYPES.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
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
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit" disabled={!draftFilters.tenantId?.trim() || !draftFilters.applicationId?.trim()}>
              <Search size={16} />
              Query
            </Button>
            <Button type="button" variant="secondary" onClick={() => reconciliationQuery.refetch()} disabled={!hasQueried || !canQuery}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => financeCloseout.mutate(undefined)}
              disabled={!draftFilters.tenantId?.trim() || !draftFilters.applicationId?.trim() || financeCloseout.isPending}
            >
              <Scale size={16} />
              Closeout
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      {financeCloseout.isError && <ErrorState error={financeCloseout.error} />}
      {financeCloseout.isPending && <Spinner label="Đang tạo finance closeout" />}
      {financeCloseout.data && (
        <FinanceCloseoutCard
          report={financeCloseout.data}
          loadingNext={financeCloseout.isPending}
          onNextPage={(cursor) => financeCloseout.mutate(cursor)}
        />
      )}

      {!hasQueried && (
        <Notice tone="neutral" title="Scoped reconciliation">
          Chọn tenant/application rồi bấm Query để truy ledger reconciliation. Màn hình này không tự tải dữ liệu rộng.
        </Notice>
      )}

      {reconciliationQuery.isLoading && <Spinner />}
      {reconciliationQuery.isError && <ErrorState error={reconciliationQuery.error} />}
      {hasQueried && !reconciliationQuery.isLoading && !reconciliationQuery.isError && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <StatCard label="Rows" value={items.length} icon={<Scale size={18} />} tone="info" />
            <StatCard label="Matched" value={matchedCount} tone="success" />
            <StatCard label="Pending" value={pendingCount} tone="warning" />
            <StatCard label="Missing outbox" value={missingOutboxCount} tone="danger" />
          </div>
          <Card>
            <CardHeader
              title="Loyalty reconciliation"
              subtitle={reconciliationQuery.data ? `Generated ${formatDateTime(reconciliationQuery.data.generatedAt)}` : "Ledger and outbox evidence"}
              actions={<Badge value="RESULT" label={`${items.length} rows`} tone="slate" />}
            />
            {items.length === 0 && <EmptyState message="Không có reconciliation entry phù hợp." />}
            {items.length > 0 && <ReconciliationTable rows={items} />}
          </Card>
        </div>
      )}
    </div>
  );
}

function FinanceCloseoutCard({
  report,
  loadingNext,
  onNextPage
}: {
  report: LoyaltyFinanceCloseoutExport;
  loadingNext?: boolean;
  onNextPage?: (cursor: string) => void;
}) {
  return (
    <Card>
      <CardHeader
        title="Finance closeout"
        subtitle={`${report.tenantId}/${report.applicationId}${report.programId ? `/${report.programId}` : ""} · ${formatDateTime(report.generatedAt)}`}
        actions={
          <div className="flex flex-wrap justify-end gap-2">
            <Badge
              value={report.certifiable ? "CERTIFIABLE" : "NOT_CERTIFIABLE"}
              label={report.certifiable ? "CERTIFIABLE" : "NOT CERTIFIABLE"}
              tone={report.certifiable ? "success" : "warning"}
            />
            <Badge value={report.hasMore ? "PARTIAL" : "COMPLETE"} label={`${report.items.length} rows`} tone={report.hasMore ? "warning" : "success"} />
            {report.nextCursor && onNextPage && (
              <Button type="button" size="sm" variant="secondary" onClick={() => onNextPage(report.nextCursor!)} disabled={loadingNext}>
                <ArrowRight size={16} />
                Next page
              </Button>
            )}
          </div>
        }
      />
      {report.warnings.length > 0 && (
        <Notice tone="warning" title="Closeout warnings" className="mx-5 mt-5">
          {report.warnings.join(", ")}
        </Notice>
      )}
      <div className="mx-5 mt-5 grid gap-3 md:grid-cols-3">
        <StatCard label="Closeout ID" value={compactId(report.closeoutId, 18, 8)} detail="Stable ID for this scope and window." tone="neutral" />
        <StatCard label="Result hash" value={compactId(report.resultHash, 16, 8)} detail="Deterministic totals hash." tone="brand" />
        <StatCard
          label="Certification"
          value={report.certifiable ? "Ready" : "Blocked"}
          detail={report.certifiable ? "No pending/missing outbox and full page returned." : "Resolve warnings before finance sign-off."}
          tone={report.certifiable ? "success" : "warning"}
          icon={<ShieldCheck size={18} />}
        />
      </div>
      <div className="mx-5 mt-3 grid gap-3 md:grid-cols-4">
        <StatCard label="Earned" value={report.totals.earnedPoints} tone="success" />
        <StatCard label="Burned" value={report.totals.burnedPoints} tone="danger" />
        <StatCard label="Expired" value={report.totals.expiredPoints} tone="warning" />
        <StatCard label="Net" value={report.totals.netPoints} tone="brand" />
      </div>
      <div className="mx-5 mt-3 grid gap-3 md:grid-cols-4">
        <StatCard label="Adjusted" value={report.totals.adjustedPoints} tone="info" />
        <StatCard label="Reversed" value={report.totals.reversedPoints} tone="neutral" />
        <StatCard label="Pending outbox" value={report.totals.pendingOutboxCount} tone="warning" />
        <StatCard label="Missing outbox" value={report.totals.missingOutboxCount} tone="danger" />
      </div>
      {report.items.length > 0 && (
        <div className="mx-5 mb-5 mt-4">
          <ReconciliationTable rows={report.items.slice(0, 50)} />
        </div>
      )}
    </Card>
  );
}

function ReconciliationTable({ rows }: { rows: LoyaltyReconciliationEntry[] }) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Status</Th>
          <Th>Entry</Th>
          <Th>Points</Th>
          <Th>Profile</Th>
          <Th>Source</Th>
          <Th>Outbox</Th>
          <Th>Created</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((entry) => (
          <tr key={entry.reconciliationKey}>
            <Td>
              <StatusPill value={entry.reconciliationStatus} />
              {entry.reasonCodes.length > 0 && (
                <p className="mt-1 text-xs text-slate-400">{entry.reasonCodes.join(", ")}</p>
              )}
            </Td>
            <Td>
              <p className="font-semibold text-slate-900">{entry.entryType}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{compactId(entry.ledgerEntryId)}</p>
            </Td>
            <Td>
              <StatusPill value={entry.direction} />
              <p className={cn("mt-1 font-semibold", entry.pointsDelta < 0 ? "text-red-600" : "text-emerald-700")}>
                {entry.pointsDelta > 0 ? `+${entry.pointsDelta}` : entry.pointsDelta}
              </p>
            </Td>
            <Td>
              <p className="font-semibold text-slate-900">{entry.profileId}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{compactId(entry.accountId)}</p>
            </Td>
            <Td>
              <p className="font-mono text-xs text-slate-600">{entry.sourceReference}</p>
              {entry.reversalOfEntryId && <p className="mt-1 text-xs text-slate-400">reversal {compactId(entry.reversalOfEntryId)}</p>}
            </Td>
            <Td><StatusPill value={entry.outboxStatus} /></Td>
            <Td>{formatDateTime(entry.ledgerCreatedAt ?? entry.occurredAt)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function TiersPanel() {
  const [filters, setFilters] = useState<LoyaltyTierFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<LoyaltyTierFilters>(filters);
  const [stateFilters, setStateFilters] = useState<LoyaltyTierFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [policyForm, setPolicyForm] = useState<TierPolicyForm>(newTierPolicyForm());
  const queryClient = useQueryClient();

  const policiesQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyTierPolicies(filters),
    queryFn: () => listLoyaltyTierPolicies(filters),
    retry: 1
  });

  const statesQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyTierStates(stateFilters),
    queryFn: () => queryLoyaltyTierStates(stateFilters),
    retry: 1
  });

  const savePolicyMutation = useMutation({
    mutationFn: () => {
      const payload = tierPolicyPayload(policyForm);
      if (policyForm.mode === "edit" && policyForm.policyId) {
        return updateLoyaltyTierPolicy(policyForm.policyId, {
          name: payload.name,
          rank: payload.rank,
          qualificationPoints: payload.qualificationPoints,
          qualificationWindowDays: payload.qualificationWindowDays,
          downgradeGraceDays: payload.downgradeGraceDays,
          benefits: payload.benefits
        });
      }
      return createLoyaltyTierPolicy(payload);
    },
    onSuccess: (policy) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setPolicyForm(editTierPolicyForm(policy));
    }
  });

  const policyStatusMutation = useMutation({
    mutationFn: ({ policy, status }: { policy: LoyaltyTierPolicy; status: string }) =>
      updateLoyaltyTierPolicyStatus(policy.id, {
        status,
        note: `Tier policy status changed to ${status}`
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty })
  });

  const recalcMutation = useMutation({
    mutationFn: () =>
      recalculateLoyaltyTiers({
        tenantId: stateFilters.tenantId,
        applicationId: stateFilters.applicationId,
        programId: stateFilters.programId,
        profileId: stateFilters.profileId,
        limit: stateFilters.limit ?? 50,
        reason: "Recalculate loyalty tier states from admin console",
        correlationId: retentionOperationId("loyalty-tier-recalculate")
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty })
  });

  const policies = policiesQuery.data ?? [];
  const states = statesQuery.data?.items ?? [];
  const activePolicyCount = policies.filter((policy) => policy.status === "ACTIVE").length;
  const graceCount = states.filter((state) => state.progress.graceUntil).length;

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
    setStateFilters({
      tenantId: draftFilters.tenantId,
      applicationId: draftFilters.applicationId,
      programId: draftFilters.programId,
      profileId: stateFilters.profileId,
      tierCode: stateFilters.tierCode,
      limit: stateFilters.limit ?? 50
    });
  }

  function submitPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    savePolicyMutation.mutate();
  }

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Tenant">
            <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application">
            <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID">
            <Input value={draftFilters.programId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, programId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value })}>
              <option value="">All</option>
              {TIER_STATUSES.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Limit">
            <Input
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit">
              <Search size={16} />
              Query
            </Button>
            <Button type="button" variant="secondary" onClick={() => policiesQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="Policies" value={policies.length} icon={<Medal size={18} />} tone="info" />
        <StatCard label="Active tiers" value={activePolicyCount} tone={activePolicyCount > 0 ? "success" : "neutral"} />
        <StatCard label="States" value={states.length} tone="brand" />
        <StatCard label="In grace" value={graceCount} tone={graceCount > 0 ? "warning" : "success"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card>
          <CardHeader
            title={policyForm.mode === "edit" ? "Edit tier policy" : "New tier policy"}
            subtitle="Qualification window, downgrade grace và benefit metadata theo loyalty program."
            actions={
              <Button size="sm" variant="secondary" onClick={() => setPolicyForm(newTierPolicyForm())}>
                <Plus size={16} />
                New
              </Button>
            }
          />
          <form className="grid gap-3 p-4 pt-0" onSubmit={submitPolicy}>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Tenant" required>
                <Input disabled={policyForm.mode === "edit"} value={policyForm.tenantId} onChange={(event) => setPolicyForm({ ...policyForm, tenantId: event.target.value })} />
              </FormField>
              <FormField label="Application" required>
                <Input disabled={policyForm.mode === "edit"} value={policyForm.applicationId} onChange={(event) => setPolicyForm({ ...policyForm, applicationId: event.target.value })} />
              </FormField>
            </div>
            <FormField label="Program ID" required>
              <Input disabled={policyForm.mode === "edit"} value={policyForm.programId} onChange={(event) => setPolicyForm({ ...policyForm, programId: event.target.value })} />
            </FormField>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Tier code" required>
                <Input disabled={policyForm.mode === "edit"} value={policyForm.tierCode} onChange={(event) => setPolicyForm({ ...policyForm, tierCode: event.target.value })} />
              </FormField>
              <FormField label="Name" required>
                <Input value={policyForm.name} onChange={(event) => setPolicyForm({ ...policyForm, name: event.target.value })} />
              </FormField>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Rank" required>
                <Input value={policyForm.rank} inputMode="numeric" onChange={(event) => setPolicyForm({ ...policyForm, rank: event.target.value })} />
              </FormField>
              <FormField label="Qualification points" required>
                <Input value={policyForm.qualificationPoints} inputMode="numeric" onChange={(event) => setPolicyForm({ ...policyForm, qualificationPoints: event.target.value })} />
              </FormField>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Window days" required>
                <Input value={policyForm.qualificationWindowDays} inputMode="numeric" onChange={(event) => setPolicyForm({ ...policyForm, qualificationWindowDays: event.target.value })} />
              </FormField>
              <FormField label="Grace days" required>
                <Input value={policyForm.downgradeGraceDays} inputMode="numeric" onChange={(event) => setPolicyForm({ ...policyForm, downgradeGraceDays: event.target.value })} />
              </FormField>
            </div>
            <FormField label="Benefits JSON">
              <Textarea value={policyForm.benefitsJson} onChange={(event) => setPolicyForm({ ...policyForm, benefitsJson: event.target.value })} rows={4} />
            </FormField>
            {savePolicyMutation.isError && <ErrorState error={savePolicyMutation.error} />}
            <Button
              type="submit"
              disabled={savePolicyMutation.isPending || !policyForm.programId.trim() || !policyForm.tierCode.trim() || !policyForm.name.trim()}
            >
              {policyForm.mode === "edit" ? <Pencil size={16} /> : <Plus size={16} />}
              {policyForm.mode === "edit" ? "Save policy" : "Create policy"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader
            title="Tier policies"
            subtitle="Active policies are evaluated from lowest to highest rank."
            actions={<Badge value="RESULT" label={`${policies.length} policies`} tone="slate" />}
          />
          {policiesQuery.isLoading && <Spinner />}
          {policiesQuery.isError && <ErrorState error={policiesQuery.error} />}
          {!policiesQuery.isLoading && !policiesQuery.isError && policies.length === 0 && <EmptyState message="Chưa có tier policy phù hợp." />}
          {policies.length > 0 && (
            <TierPolicyTable
              policies={policies}
              onEdit={(policy) => setPolicyForm(editTierPolicyForm(policy))}
              onChangeStatus={(policy, status) => policyStatusMutation.mutate({ policy, status })}
              isStatusPending={policyStatusMutation.isPending}
            />
          )}
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Tier states"
          subtitle="Current learner tier, qualification window và progress lên tier tiếp theo."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <Badge value="RESULT" label={`${states.length} states`} tone="slate" />
              <Button size="sm" variant="secondary" disabled={recalcMutation.isPending} onClick={() => recalcMutation.mutate()}>
                <RefreshCcw size={16} />
                Recalculate
              </Button>
            </div>
          }
        />
        <Toolbar className="mb-4">
          <FormField label="Profile ID">
            <Input value={stateFilters.profileId ?? ""} onChange={(event) => setStateFilters({ ...stateFilters, profileId: event.target.value })} />
          </FormField>
          <FormField label="Tier code">
            <Input value={stateFilters.tierCode ?? ""} onChange={(event) => setStateFilters({ ...stateFilters, tierCode: event.target.value })} />
          </FormField>
          <FilterActions>
            <Button type="button" variant="secondary" onClick={() => statesQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
        {statesQuery.isLoading && <Spinner />}
        {statesQuery.isError && <ErrorState error={statesQuery.error} />}
        {!statesQuery.isLoading && !statesQuery.isError && states.length === 0 && <EmptyState message="Chưa có tier state phù hợp." />}
        {states.length > 0 && <TierStateTable states={states} />}
        {recalcMutation.isError && <ErrorState error={recalcMutation.error} />}
        {recalcMutation.data && (
          <Notice tone="neutral" title="Tier recalculation">
            Scanned {recalcMutation.data.scanned}, changed {recalcMutation.data.changed}.
          </Notice>
        )}
      </Card>
    </div>
  );
}

function TierPolicyTable({
  policies,
  onEdit,
  onChangeStatus,
  isStatusPending
}: {
  policies: LoyaltyTierPolicy[];
  onEdit: (policy: LoyaltyTierPolicy) => void;
  onChangeStatus: (policy: LoyaltyTierPolicy, status: string) => void;
  isStatusPending?: boolean;
}) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Tier</Th>
          <Th>Status</Th>
          <Th>Qualification</Th>
          <Th>Grace</Th>
          <Th>Updated</Th>
          <Th>Actions</Th>
        </tr>
      </thead>
      <tbody>
        {policies.map((policy) => (
          <tr key={policy.id}>
            <Td>
              <p className="font-semibold text-slate-900">{policy.tierCode} · rank {policy.rank}</p>
              <p className="mt-1 text-xs text-slate-500">{policy.name}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{policy.programId}</p>
            </Td>
            <Td><StatusPill value={policy.status} /></Td>
            <Td>
              <p className="font-semibold text-slate-900">{policy.qualificationPoints} points</p>
              <p className="mt-1 text-xs text-slate-400">{policy.qualificationWindowDays} day window</p>
            </Td>
            <Td>{policy.downgradeGraceDays} days</Td>
            <Td>{formatDateTime(policy.updatedAt ?? policy.createdAt)}</Td>
            <Td>
              <div className="flex flex-wrap gap-2">
                <Button size="xs" variant="secondary" onClick={() => onEdit(policy)}>
                  <Pencil size={14} />
                  Edit
                </Button>
                {TIER_STATUSES.filter((status) => status !== policy.status).slice(0, 2).map((status) => (
                  <Button
                    key={status}
                    size="xs"
                    variant={status === "ARCHIVED" ? "danger" : "outline"}
                    disabled={isStatusPending}
                    onClick={() => onChangeStatus(policy, status)}
                  >
                    {statusLabel(status)}
                  </Button>
                ))}
              </div>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function TierStateTable({ states }: { states: LoyaltyTierState[] }) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Profile</Th>
          <Th>Current tier</Th>
          <Th>Qualification</Th>
          <Th>Next tier</Th>
          <Th>Grace</Th>
          <Th>Evaluated</Th>
        </tr>
      </thead>
      <tbody>
        {states.map((state) => (
          <tr key={state.id}>
            <Td>
              <p className="font-mono text-xs text-slate-600">{state.profileId}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{compactId(state.accountId)}</p>
            </Td>
            <Td>
              <StatusPill value={state.progress.currentTierCode} />
              <p className="mt-1 text-xs text-slate-500">{state.progress.currentTierName} · rank {state.progress.currentTierRank}</p>
            </Td>
            <Td>
              <p className="font-semibold text-slate-900">{state.progress.qualificationPoints} points</p>
              <p className="mt-1 text-xs text-slate-400">
                {state.progress.qualificationWindowDays ?? "-"} days · from {formatDateTime(state.progress.qualificationWindowStartedAt)}
              </p>
            </Td>
            <Td>
              {state.progress.nextTierCode ? (
                <>
                  <p className="font-semibold text-slate-900">{state.progress.nextTierCode}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {state.progress.pointsToNext ?? 0} / {state.progress.nextTierPointsRequired ?? 0} points left
                  </p>
                </>
              ) : (
                <span className="text-sm text-slate-400">Top tier</span>
              )}
            </Td>
            <Td>{state.progress.graceUntil ? formatDateTime(state.progress.graceUntil) : "-"}</Td>
            <Td>{formatDateTime(state.progress.evaluatedAt ?? state.updatedAt)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function RewardsPanel() {
  const [filters, setFilters] = useState<LoyaltyRewardFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<LoyaltyRewardFilters>(filters);
  const [redemptionFilters, setRedemptionFilters] = useState<LoyaltyRewardRedemptionFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [rewardForm, setRewardForm] = useState<RewardForm>(newRewardForm());
  const [reverseAction, setReverseAction] = useState<{
    redemption: LoyaltyRewardRedemption;
    reason: string;
    operationId: string;
  } | null>(null);
  const [fulfillmentAction, setFulfillmentAction] = useState<{
    redemption: LoyaltyRewardRedemption;
    status: string;
    fulfillmentRef: string;
    note: string;
    reason: string;
    operationId: string;
    approvalId: string;
    approval?: LoyaltyAdjustmentApproval | null;
  } | null>(null);
  const queryClient = useQueryClient();

  const rewardsQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyRewards(filters),
    queryFn: () => listLoyaltyRewards(filters),
    retry: 1
  });

  const redemptionsQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyRewardRedemptions(redemptionFilters),
    queryFn: () => queryLoyaltyRewardRedemptions(redemptionFilters),
    retry: 1
  });

  const saveRewardMutation = useMutation({
    mutationFn: () => {
      const payload = rewardPayload(rewardForm);
      if (rewardForm.mode === "edit" && rewardForm.rewardId) {
        return updateLoyaltyReward(rewardForm.rewardId, payload);
      }
      return createLoyaltyReward(payload);
    },
    onSuccess: (reward) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setRewardForm(editRewardForm(reward));
    }
  });

  const statusMutation = useMutation({
    mutationFn: ({ reward, status }: { reward: LoyaltyReward; status: string }) =>
      updateLoyaltyRewardStatus(reward.id, {
        status,
        note: `Reward status changed to ${status}`
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty })
  });

  const reverseMutation = useMutation({
    mutationFn: () => {
      if (!reverseAction) throw new Error("Missing reward redemption reverse target");
      return reverseLoyaltyRewardRedemption(reverseAction.redemption.id, {
        idempotencyKey: reverseAction.operationId,
        correlationId: reverseAction.operationId,
        reason: reverseAction.reason.trim() || "Reward redemption reversed by loyalty operations",
        metadata: { source: "web-admin", rewardCode: reverseAction.redemption.rewardCode }
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setReverseAction(null);
    }
  });

  const fulfillmentApprovalMutation = useMutation({
    mutationFn: () => {
      if (!fulfillmentAction) throw new Error("Missing reward fulfillment approval target");
      return submitLoyaltyRewardFulfillmentApproval(fulfillmentAction.redemption.id, {
        status: fulfillmentAction.status,
        fulfillmentRef: fulfillmentAction.fulfillmentRef.trim() || undefined,
        note: fulfillmentAction.note.trim() || undefined,
        idempotencyKey: fulfillmentAction.operationId,
        correlationId: fulfillmentAction.operationId,
        reason: fulfillmentAction.reason.trim() || `Reward fulfillment marked ${fulfillmentAction.status}`,
        metadata: { source: "web-admin", rewardCode: fulfillmentAction.redemption.rewardCode }
      });
    },
    onSuccess: (approval) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setFulfillmentAction((current) => current ? { ...current, approvalId: approval.id, approval } : current);
    }
  });

  const fulfillmentMutation = useMutation({
    mutationFn: () => {
      if (!fulfillmentAction) throw new Error("Missing reward fulfillment execution target");
      if (!fulfillmentAction.approvalId.trim()) throw new Error("Missing approved fulfillment approval id");
      return updateLoyaltyRewardFulfillment(fulfillmentAction.redemption.id, {
        status: fulfillmentAction.status,
        fulfillmentRef: fulfillmentAction.fulfillmentRef.trim() || undefined,
        note: fulfillmentAction.note.trim() || undefined,
        idempotencyKey: fulfillmentAction.operationId,
        correlationId: fulfillmentAction.operationId,
        reason: fulfillmentAction.reason.trim() || `Reward fulfillment marked ${fulfillmentAction.status}`,
        metadata: { source: "web-admin", rewardCode: fulfillmentAction.redemption.rewardCode },
        approvalId: fulfillmentAction.approvalId.trim()
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setFulfillmentAction(null);
    }
  });

  const retryFulfillmentMutation = useMutation({
    mutationFn: (redemption: LoyaltyRewardRedemption) =>
      retryLoyaltyRewardFulfillment(redemption.id, {
        reason: "Retry reward fulfillment from loyalty operations",
        correlationId: retentionOperationId("loyalty-reward-fulfillment-retry")
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty })
  });

  const runDueFulfillmentMutation = useMutation({
    mutationFn: () => runDueLoyaltyRewardFulfillments(redemptionFilters.limit ?? 50),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty })
  });

  const rewards = rewardsQuery.data ?? [];
  const redemptions = redemptionsQuery.data?.items ?? [];
  const activeRewards = useMemo(() => rewards.filter((reward) => reward.status === "ACTIVE").length, [rewards]);
  const pendingFulfillmentCount = useMemo(
    () => redemptions.filter((redemption) => redemption.fulfillmentStatus === "PENDING").length,
    [redemptions]
  );
  const manualFulfillmentCount = useMemo(
    () => redemptions.filter((redemption) => redemption.fulfillmentStatus === "MANUAL_REQUIRED").length,
    [redemptions]
  );
  const failedFulfillmentCount = useMemo(
    () => redemptions.filter((redemption) => redemption.fulfillmentStatus === "FAILED").length,
    [redemptions]
  );

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
    setRedemptionFilters({
      tenantId: draftFilters.tenantId,
      applicationId: draftFilters.applicationId,
      programId: draftFilters.programId,
      fulfillmentStatus: redemptionFilters.fulfillmentStatus,
      limit: redemptionFilters.limit ?? 50
    });
  }

  function submitReward(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveRewardMutation.mutate();
  }

  function openReverse(redemption: LoyaltyRewardRedemption) {
    reverseMutation.reset();
    setReverseAction({
      redemption,
      reason: "Reverse reward redemption and return burned points",
      operationId: retentionOperationId("loyalty-reward-reverse")
    });
  }

  function openFulfillment(redemption: LoyaltyRewardRedemption, status: string) {
    fulfillmentApprovalMutation.reset();
    fulfillmentMutation.reset();
    setFulfillmentAction({
      redemption,
      status,
      fulfillmentRef: status === "ISSUED" ? `manual:${redemption.id}` : redemption.fulfillmentRef ?? "",
      note: `Reward fulfillment marked ${status}`,
      reason: `Reward fulfillment marked ${status}`,
      operationId: retentionOperationId("loyalty-reward-fulfillment"),
      approvalId: "",
      approval: null
    });
  }

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Tenant">
            <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application">
            <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Program ID">
            <Input value={draftFilters.programId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, programId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value })}>
              <option value="">All</option>
              {REWARD_STATUSES.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Limit">
            <Input
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit">
              <Search size={16} />
              Query
            </Button>
            <Button type="button" variant="secondary" onClick={() => rewardsQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="Rewards" value={rewards.length} icon={<Gift size={18} />} tone="info" />
        <StatCard label="Active" value={activeRewards} tone={activeRewards > 0 ? "success" : "neutral"} />
        <StatCard label="Pending fulfill" value={pendingFulfillmentCount} tone={pendingFulfillmentCount > 0 ? "warning" : "neutral"} />
        <StatCard label="Manual/Failed" value={manualFulfillmentCount + failedFulfillmentCount} tone={manualFulfillmentCount + failedFulfillmentCount > 0 ? "danger" : "success"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card>
          <CardHeader
            title={rewardForm.mode === "edit" ? "Edit reward" : "New reward"}
            subtitle="Catalog reward tiêu điểm cho loyalty point redemption."
            actions={
              <Button size="sm" variant="secondary" onClick={() => setRewardForm(newRewardForm())}>
                <Plus size={16} />
                New
              </Button>
            }
          />
          <form className="grid gap-3 p-4 pt-0" onSubmit={submitReward}>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Tenant" required>
                <Input disabled={rewardForm.mode === "edit"} value={rewardForm.tenantId} onChange={(event) => setRewardForm({ ...rewardForm, tenantId: event.target.value })} />
              </FormField>
              <FormField label="Application" required>
                <Input disabled={rewardForm.mode === "edit"} value={rewardForm.applicationId} onChange={(event) => setRewardForm({ ...rewardForm, applicationId: event.target.value })} />
              </FormField>
            </div>
            <FormField label="Program ID" required>
              <Input disabled={rewardForm.mode === "edit"} value={rewardForm.programId} onChange={(event) => setRewardForm({ ...rewardForm, programId: event.target.value })} />
            </FormField>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Reward code" required>
                <Input disabled={rewardForm.mode === "edit"} value={rewardForm.rewardCode} onChange={(event) => setRewardForm({ ...rewardForm, rewardCode: event.target.value })} />
              </FormField>
              <FormField label="Points cost" required>
                <Input value={rewardForm.pointsCost} inputMode="numeric" onChange={(event) => setRewardForm({ ...rewardForm, pointsCost: event.target.value })} />
              </FormField>
            </div>
            <FormField label="Name" required>
              <Input value={rewardForm.name} onChange={(event) => setRewardForm({ ...rewardForm, name: event.target.value })} />
            </FormField>
            <FormField label="Description">
              <Textarea value={rewardForm.description} onChange={(event) => setRewardForm({ ...rewardForm, description: event.target.value })} rows={3} />
            </FormField>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Status">
                <Select value={rewardForm.status} onChange={(event) => setRewardForm({ ...rewardForm, status: event.target.value })} disabled={rewardForm.mode === "edit"}>
                  {REWARD_STATUSES.map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Fulfillment">
                <Select value={rewardForm.fulfillmentType} onChange={(event) => setRewardForm({ ...rewardForm, fulfillmentType: event.target.value })}>
                  <option value="MANUAL">MANUAL</option>
                  <option value="AUTO_ISSUE">AUTO_ISSUE</option>
                  <option value="WEBHOOK">WEBHOOK</option>
                  <option value="HTTP_POST">HTTP_POST</option>
                </Select>
              </FormField>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Starts">
                <Input type="datetime-local" value={rewardForm.startsAt} onChange={(event) => setRewardForm({ ...rewardForm, startsAt: event.target.value })} />
              </FormField>
              <FormField label="Ends">
                <Input type="datetime-local" value={rewardForm.endsAt} onChange={(event) => setRewardForm({ ...rewardForm, endsAt: event.target.value })} />
              </FormField>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Inventory">
                <Input value={rewardForm.inventoryLimit} inputMode="numeric" onChange={(event) => setRewardForm({ ...rewardForm, inventoryLimit: event.target.value })} />
              </FormField>
              <FormField label="Per profile">
                <Input value={rewardForm.perProfileLimit} inputMode="numeric" onChange={(event) => setRewardForm({ ...rewardForm, perProfileLimit: event.target.value })} />
              </FormField>
            </div>
            <FormField label="Fulfillment config JSON">
              <Textarea value={rewardForm.fulfillmentConfigJson} onChange={(event) => setRewardForm({ ...rewardForm, fulfillmentConfigJson: event.target.value })} rows={4} />
            </FormField>
            {saveRewardMutation.isError && <ErrorState error={saveRewardMutation.error} />}
            <Button type="submit" disabled={saveRewardMutation.isPending || !rewardForm.programId.trim() || !rewardForm.rewardCode.trim() || !rewardForm.name.trim()}>
              {rewardForm.mode === "edit" ? <Pencil size={16} /> : <Plus size={16} />}
              {rewardForm.mode === "edit" ? "Save reward" : "Create reward"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader
            title="Reward catalog"
            subtitle="Rewards consume loyalty points through immutable BURN ledger entries."
            actions={<Badge value="RESULT" label={`${rewards.length} rewards`} tone="slate" />}
          />
          {rewardsQuery.isLoading && <Spinner />}
          {rewardsQuery.isError && <ErrorState error={rewardsQuery.error} />}
          {!rewardsQuery.isLoading && !rewardsQuery.isError && rewards.length === 0 && <EmptyState message="Không có reward phù hợp." />}
          {rewards.length > 0 && (
            <RewardTable
              rewards={rewards}
              onEdit={(reward) => setRewardForm(editRewardForm(reward))}
              onChangeStatus={(reward, status) => statusMutation.mutate({ reward, status })}
              isStatusPending={statusMutation.isPending}
            />
          )}
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Reward redemptions"
          subtitle="History dùng để đối chiếu burn ledger và fulfillment."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <Badge value="RESULT" label={`${redemptions.length} redemptions`} tone="slate" />
              <Button
                size="sm"
                variant="secondary"
                disabled={runDueFulfillmentMutation.isPending}
                onClick={() => runDueFulfillmentMutation.mutate()}
              >
                <RefreshCcw size={16} />
                Run due
              </Button>
            </div>
          }
        />
        <Toolbar className="mb-4">
          <FormField label="Profile ID">
            <Input value={redemptionFilters.profileId ?? ""} onChange={(event) => setRedemptionFilters({ ...redemptionFilters, profileId: event.target.value })} />
          </FormField>
          <FormField label="Reward ID">
            <Input value={redemptionFilters.rewardId ?? ""} onChange={(event) => setRedemptionFilters({ ...redemptionFilters, rewardId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={redemptionFilters.status ?? ""} onChange={(event) => setRedemptionFilters({ ...redemptionFilters, status: event.target.value })}>
              <option value="">All</option>
              {REDEMPTION_STATUSES.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Fulfillment">
            <Select
              value={redemptionFilters.fulfillmentStatus ?? ""}
              onChange={(event) => setRedemptionFilters({ ...redemptionFilters, fulfillmentStatus: event.target.value })}
            >
              <option value="">All</option>
              {FULFILLMENT_STATUSES.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </Select>
          </FormField>
          <FilterActions>
            <Button type="button" variant="secondary" onClick={() => redemptionsQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
        {redemptionsQuery.isLoading && <Spinner />}
        {redemptionsQuery.isError && <ErrorState error={redemptionsQuery.error} />}
        {!redemptionsQuery.isLoading && !redemptionsQuery.isError && redemptions.length === 0 && <EmptyState message="Chưa có redemption phù hợp." />}
        {redemptions.length > 0 && (
          <RewardRedemptionTable
            redemptions={redemptions}
            onReverse={openReverse}
            onFulfillment={openFulfillment}
            onRetry={(redemption) => retryFulfillmentMutation.mutate(redemption)}
            isReversePending={reverseMutation.isPending}
            isFulfillmentPending={fulfillmentMutation.isPending}
            isRetryPending={retryFulfillmentMutation.isPending}
          />
        )}
        {retryFulfillmentMutation.isError && <ErrorState error={retryFulfillmentMutation.error} />}
        {runDueFulfillmentMutation.isError && <ErrorState error={runDueFulfillmentMutation.error} />}
        {runDueFulfillmentMutation.data && (
          <Notice tone="neutral" title="Fulfillment run">
            Scanned {runDueFulfillmentMutation.data.scanned}, dispatched {runDueFulfillmentMutation.data.dispatched}, issued {runDueFulfillmentMutation.data.issued}, failed {runDueFulfillmentMutation.data.failed}.
          </Notice>
        )}
      </Card>

      <ConfirmDialog
        open={Boolean(reverseAction)}
        onOpenChange={(open) => !open && setReverseAction(null)}
        title="Reverse reward redemption"
        description={reverseAction ? `${reverseAction.redemption.rewardCode} · ${compactId(reverseAction.redemption.id)}` : undefined}
        confirmLabel="Reverse points"
        tone="danger"
        isPending={reverseMutation.isPending}
        onConfirm={() => reverseMutation.mutate()}
      >
        <div className="space-y-3">
          <Notice tone="warning" title="Ledger reversal">
            Backend sẽ tạo ledger entry `REVERSE` cho burn entry của redemption và đánh dấu redemption là REVERSED.
          </Notice>
          <FormField label="Reason" required>
            <Textarea
              value={reverseAction?.reason ?? ""}
              onChange={(event) => reverseAction && setReverseAction({ ...reverseAction, reason: event.target.value })}
              rows={3}
            />
          </FormField>
          {reverseMutation.isError && <ErrorState error={reverseMutation.error} />}
        </div>
      </ConfirmDialog>

      <ConfirmDialog
        open={Boolean(fulfillmentAction)}
        onOpenChange={(open) => !open && setFulfillmentAction(null)}
        title="Reward fulfillment override"
        description={fulfillmentAction ? `${fulfillmentAction.redemption.rewardCode} · ${compactId(fulfillmentAction.redemption.id)}` : undefined}
        confirmLabel="Execute with approval"
        tone="primary"
        isPending={fulfillmentMutation.isPending}
        onConfirm={() => fulfillmentMutation.mutate()}
      >
        <div className="space-y-3">
          <Notice tone="warning" title="Maker-checker required">
            Submit approval trước, reviewer approve ở tab Approvals, rồi execute bằng approval ID đã duyệt.
          </Notice>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Target status">
              <Select
                value={fulfillmentAction?.status ?? "ISSUED"}
                onChange={(event) => fulfillmentAction && setFulfillmentAction({ ...fulfillmentAction, status: event.target.value })}
              >
                {FULFILLMENT_STATUSES.map((status) => (
                  <option key={status} value={status}>{status}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Fulfillment ref">
              <Input
                value={fulfillmentAction?.fulfillmentRef ?? ""}
                onChange={(event) => fulfillmentAction && setFulfillmentAction({ ...fulfillmentAction, fulfillmentRef: event.target.value })}
              />
            </FormField>
          </div>
          <FormField label="Reason" required>
            <Textarea
              value={fulfillmentAction?.reason ?? ""}
              onChange={(event) => fulfillmentAction && setFulfillmentAction({ ...fulfillmentAction, reason: event.target.value })}
              rows={3}
            />
          </FormField>
          <FormField label="Note">
            <Input
              value={fulfillmentAction?.note ?? ""}
              onChange={(event) => fulfillmentAction && setFulfillmentAction({ ...fulfillmentAction, note: event.target.value })}
            />
          </FormField>
          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <FormField label="Approval ID">
              <Input
                value={fulfillmentAction?.approvalId ?? ""}
                onChange={(event) => fulfillmentAction && setFulfillmentAction({ ...fulfillmentAction, approvalId: event.target.value })}
                placeholder="Paste approved fulfillment approval id"
              />
            </FormField>
            <div className="flex items-end">
              <Button
                type="button"
                variant="secondary"
                disabled={fulfillmentApprovalMutation.isPending}
                onClick={() => fulfillmentApprovalMutation.mutate()}
              >
                <ShieldCheck size={16} />
                Submit approval
              </Button>
            </div>
          </div>
          {fulfillmentAction?.approval && (
            <Notice tone={fulfillmentAction.approval.status === "APPROVED" ? "success" : "info"} title={`Approval ${fulfillmentAction.approval.status}`}>
              {compactId(fulfillmentAction.approval.id, 18, 8)} · {fulfillmentAction.approval.operationType}
            </Notice>
          )}
          {fulfillmentApprovalMutation.isError && <ErrorState error={fulfillmentApprovalMutation.error} />}
          {fulfillmentMutation.isError && <ErrorState error={fulfillmentMutation.error} />}
        </div>
      </ConfirmDialog>
    </div>
  );
}

function rewardPayload(form: RewardForm) {
  const config = parseRewardConfig(form.fulfillmentConfigJson);
  return {
    tenantId: form.tenantId.trim(),
    applicationId: form.applicationId.trim(),
    programId: form.programId.trim(),
    rewardCode: form.rewardCode.trim(),
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    pointsCost: toNumberOrUndefined(form.pointsCost) ?? 0,
    status: form.mode === "create" ? form.status : undefined,
    startsAt: toIsoDateTime(form.startsAt),
    endsAt: toIsoDateTime(form.endsAt),
    inventoryLimit: toNumberOrUndefined(form.inventoryLimit),
    perProfileLimit: toNumberOrUndefined(form.perProfileLimit),
    fulfillmentType: form.fulfillmentType.trim() || "MANUAL",
    fulfillmentConfig: config
  };
}

function tierPolicyPayload(form: TierPolicyForm) {
  const benefits = parseJsonObject(form.benefitsJson, "Benefits");
  return {
    tenantId: form.tenantId.trim(),
    applicationId: form.applicationId.trim(),
    programId: form.programId.trim(),
    tierCode: form.tierCode.trim(),
    name: form.name.trim(),
    rank: toNumberOrUndefined(form.rank) ?? 1,
    qualificationPoints: toNumberOrUndefined(form.qualificationPoints) ?? 0,
    qualificationWindowDays: toNumberOrUndefined(form.qualificationWindowDays) ?? 365,
    downgradeGraceDays: toNumberOrUndefined(form.downgradeGraceDays) ?? 30,
    benefits
  };
}

function parseRewardConfig(value: string) {
  return parseJsonObject(value, "Fulfillment config");
}

function parseJsonObject(value: string, label: string) {
  if (!value.trim()) return {};
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object`);
  }
  return parsed as Record<string, unknown>;
}

function RewardTable({
  rewards,
  onEdit,
  onChangeStatus,
  isStatusPending
}: {
  rewards: LoyaltyReward[];
  onEdit: (reward: LoyaltyReward) => void;
  onChangeStatus: (reward: LoyaltyReward, status: string) => void;
  isStatusPending?: boolean;
}) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Reward</Th>
          <Th>Status</Th>
          <Th>Cost</Th>
          <Th>Inventory</Th>
          <Th>Window</Th>
          <Th>Actions</Th>
        </tr>
      </thead>
      <tbody>
        {rewards.map((reward) => (
          <tr key={reward.id} className="hover:bg-slate-50">
            <Td>
              <p className="font-semibold text-slate-900">{reward.name}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{reward.rewardCode}</p>
            </Td>
            <Td><StatusPill value={reward.status} /></Td>
            <Td>
              <p className="font-semibold text-slate-900">{reward.pointsCost}</p>
              <p className="mt-1 text-xs text-slate-400">{reward.fulfillmentType}</p>
            </Td>
            <Td>
              <p>{reward.redeemedCount} redeemed</p>
              <p className="mt-1 text-xs text-slate-400">
                limit {reward.inventoryLimit ?? "-"} · per profile {reward.perProfileLimit ?? "-"}
              </p>
            </Td>
            <Td>
              <p className="text-xs text-slate-500">{formatDateTime(reward.startsAt)}</p>
              <p className="mt-1 text-xs text-slate-500">{formatDateTime(reward.endsAt)}</p>
            </Td>
            <Td>
              <div className="flex flex-wrap gap-2">
                <Button size="xs" variant="secondary" onClick={() => onEdit(reward)}>
                  <Pencil size={14} />
                  Edit
                </Button>
                {reward.status !== "ACTIVE" && (
                  <Button size="xs" disabled={isStatusPending} onClick={() => onChangeStatus(reward, "ACTIVE")}>
                    Activate
                  </Button>
                )}
                {reward.status === "ACTIVE" && (
                  <Button size="xs" variant="outline" disabled={isStatusPending} onClick={() => onChangeStatus(reward, "SUSPENDED")}>
                    Suspend
                  </Button>
                )}
                {reward.status !== "ARCHIVED" && (
                  <Button size="xs" variant="danger" disabled={isStatusPending} onClick={() => onChangeStatus(reward, "ARCHIVED")}>
                    Archive
                  </Button>
                )}
              </div>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function RewardRedemptionTable({
  redemptions,
  onReverse,
  onFulfillment,
  onRetry,
  isReversePending,
  isFulfillmentPending,
  isRetryPending
}: {
  redemptions: LoyaltyRewardRedemption[];
  onReverse: (redemption: LoyaltyRewardRedemption) => void;
  onFulfillment: (redemption: LoyaltyRewardRedemption, status: string) => void;
  onRetry: (redemption: LoyaltyRewardRedemption) => void;
  isReversePending?: boolean;
  isFulfillmentPending?: boolean;
  isRetryPending?: boolean;
}) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Status</Th>
          <Th>Reward</Th>
          <Th>Profile</Th>
          <Th>Points</Th>
          <Th>Ledger</Th>
          <Th>Redeemed</Th>
          <Th>Actions</Th>
        </tr>
      </thead>
      <tbody>
        {redemptions.map((redemption) => (
          <tr key={redemption.id}>
            <Td>
              <StatusPill value={redemption.status} />
              <div className="mt-1">
                <StatusPill value={redemption.fulfillmentStatus} />
              </div>
            </Td>
            <Td>
              <p className="font-semibold text-slate-900">{redemption.rewardCode}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{compactId(redemption.rewardId)}</p>
            </Td>
            <Td>
              <p className="font-mono text-xs text-slate-600">{redemption.profileId}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{compactId(redemption.accountId)}</p>
            </Td>
            <Td>{redemption.pointsCost}</Td>
            <Td>
              <p className="font-mono text-xs text-slate-600">{compactId(redemption.burnEntryId)}</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{redemption.sourceReference}</p>
              {redemption.fulfillmentRef && (
                <p className="mt-1 font-mono text-xs text-slate-500">fulfillment {redemption.fulfillmentRef}</p>
              )}
              {redemption.fulfillmentNote && (
                <p className="mt-1 text-xs text-slate-500">{redemption.fulfillmentNote}</p>
              )}
              <p className="mt-1 text-xs text-slate-400">
                {redemption.fulfillmentProvider ?? "MANUAL"} · attempt {redemption.fulfillmentAttemptCount ?? 0}
              </p>
              {(redemption.fulfillmentNextAttemptAt || redemption.fulfillmentSlaDueAt) && (
                <p className="mt-1 text-xs text-slate-400">
                  next {formatDateTime(redemption.fulfillmentNextAttemptAt)} · SLA {formatDateTime(redemption.fulfillmentSlaDueAt)}
                </p>
              )}
              {redemption.fulfillmentErrorClass && (
                <p className="mt-1 text-xs text-red-500">
                  {redemption.fulfillmentErrorClass}: {redemption.fulfillmentErrorMessage ?? "-"}
                </p>
              )}
              {redemption.fulfillmentCallbackPayloadHash && (
                <p className="mt-1 font-mono text-xs text-slate-400">
                  callback {compactId(redemption.fulfillmentCallbackPayloadHash)}
                </p>
              )}
              {redemption.reversalEntryId && (
                <p className="mt-1 font-mono text-xs text-red-500">reverse {compactId(redemption.reversalEntryId)}</p>
              )}
            </Td>
            <Td>
              <p>{formatDateTime(redemption.redeemedAt)}</p>
              {redemption.reversedAt && <p className="mt-1 text-xs text-red-500">reversed {formatDateTime(redemption.reversedAt)}</p>}
            </Td>
            <Td>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="xs"
                  variant="danger"
                  disabled={isReversePending || redemption.status === "REVERSED"}
                  onClick={() => onReverse(redemption)}
                >
                  <RefreshCcw size={14} />
                  Reverse
                </Button>
                {redemption.status !== "REVERSED" && redemption.fulfillmentStatus !== "ISSUED" && (
                  <Button
                    size="xs"
                    disabled={isFulfillmentPending}
                    onClick={() => onFulfillment(redemption, "ISSUED")}
                  >
                    Issue
                  </Button>
                )}
                {redemption.status !== "REVERSED" && redemption.fulfillmentStatus !== "MANUAL_REQUIRED" && (
                  <Button
                    size="xs"
                    variant="secondary"
                    disabled={isFulfillmentPending}
                    onClick={() => onFulfillment(redemption, "MANUAL_REQUIRED")}
                  >
                    Manual
                  </Button>
                )}
                {redemption.status !== "REVERSED" && redemption.fulfillmentStatus !== "FAILED" && (
                  <Button
                    size="xs"
                    variant="outline"
                    disabled={isFulfillmentPending}
                    onClick={() => onFulfillment(redemption, "FAILED")}
                  >
                    Fail
                  </Button>
                )}
                {redemption.status !== "REVERSED" && redemption.fulfillmentStatus !== "ISSUED" && (
                  <Button
                    size="xs"
                    variant="secondary"
                    disabled={isRetryPending}
                    onClick={() => onRetry(redemption)}
                  >
                    <RefreshCcw size={14} />
                    Retry
                  </Button>
                )}
              </div>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function DeadLetterOperationsPanel() {
  const [filters, setFilters] = useState<LoyaltyInboundDeadLetterFilters>({
    status: "OPEN",
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<LoyaltyInboundDeadLetterFilters>(filters);
  const [selectedDeadLetter, setSelectedDeadLetter] = useState<LoyaltyInboundDeadLetter | null>(null);
  const [actionTarget, setActionTarget] = useState<{
    deadLetter: LoyaltyInboundDeadLetter;
    action: "replay" | "discard";
    dryRun: boolean;
  } | null>(null);
  const [actionReason, setActionReason] = useState("Reviewed by loyalty operations");
  const [approvalEvidence, setApprovalEvidence] = useState("");
  const [approvalId, setApprovalId] = useState("");
  const [approvalReviewNote, setApprovalReviewNote] = useState("Checked evidence and threshold policy");
  const [approvalResult, setApprovalResult] = useState<LoyaltyInboundDeadLetterApproval | null>(null);
  const queryClient = useQueryClient();

  const deadLettersQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyDeadLetters(filters),
    queryFn: () => queryLoyaltyDeadLetters(filters),
    retry: 1
  });

  const detailQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyDeadLetter(selectedDeadLetter?.id),
    queryFn: () => getLoyaltyDeadLetter(selectedDeadLetter!.id),
    enabled: Boolean(selectedDeadLetter),
    retry: 1
  });

  const actionMutation = useMutation({
    mutationFn: async () => {
      if (!actionTarget) throw new Error("Missing dead-letter action target");
      const input = {
        reason: actionReason,
        dryRun: actionTarget.dryRun,
        approvalId: actionTarget.dryRun ? undefined : approvalId.trim() || undefined
      };
      return actionTarget.action === "replay"
        ? replayLoyaltyDeadLetter(actionTarget.deadLetter.id, input)
        : discardLoyaltyDeadLetter(actionTarget.deadLetter.id, input);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
      setActionTarget(null);
      setActionReason("Reviewed by loyalty operations");
      setApprovalResult(null);
    }
  });

  const approvalMutation = useMutation({
    mutationFn: async () => {
      if (!actionTarget) throw new Error("Missing dead-letter action target");
      return requestLoyaltyDeadLetterApproval(actionTarget.deadLetter.id, {
        action: actionTarget.action === "replay" ? "REPLAY" : "DISCARD",
        reason: actionReason,
        evidenceReference: approvalEvidence
      });
    },
    onSuccess: (response) => {
      setApprovalResult(response);
      setApprovalId(response.id);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
    }
  });

  const approvalReviewMutation = useMutation({
    mutationFn: async () => {
      const targetApprovalId = approvalId.trim();
      if (!targetApprovalId) throw new Error("Missing loyalty DLT approval id");
      return approveLoyaltyDeadLetterApproval(targetApprovalId, { note: approvalReviewNote });
    },
    onSuccess: (response) => {
      setApprovalResult(response);
      setApprovalId(response.id);
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.loyalty });
    }
  });

  const rows = deadLettersQuery.data?.items ?? [];
  const openCount = useMemo(() => rows.filter((row) => row.status === "OPEN").length, [rows]);
  const failedCount = useMemo(() => rows.filter((row) => row.status === "FAILED").length, [rows]);
  const resolvedCount = useMemo(
    () => rows.filter((row) => row.status === "REPLAYED" || row.status === "DISCARDED").length,
    [rows]
  );

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
  }

  function openAction(deadLetter: LoyaltyInboundDeadLetter, action: "replay" | "discard", dryRun = false) {
    actionMutation.reset();
    approvalMutation.reset();
    approvalReviewMutation.reset();
    setActionTarget({ deadLetter, action, dryRun });
    setActionReason(action === "replay" ? "Replay after payload/consumer issue review" : "Discard after manual resolution");
    setApprovalEvidence(`${deadLetter.dltTopic}:${deadLetter.kafkaPartition}:${deadLetter.kafkaOffset}:${deadLetter.payloadHash}`);
    setApprovalId("");
    setApprovalReviewNote("Checked evidence and threshold policy");
    setApprovalResult(null);
  }

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Status">
            <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value })}>
              <option value="">All</option>
              {DEAD_LETTER_STATUSES.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Source topic">
            <Input value={draftFilters.sourceTopic ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, sourceTopic: event.target.value })} />
          </FormField>
          <FormField label="DLT topic">
            <Input value={draftFilters.dltTopic ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, dltTopic: event.target.value })} />
          </FormField>
          <FormField label="Payload hash">
            <Input value={draftFilters.payloadHash ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, payloadHash: event.target.value })} />
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
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit">
              <Search size={16} />
              Query
            </Button>
            <Button type="button" variant="secondary" onClick={() => deadLettersQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="Rows" value={rows.length} icon={<FileWarning size={18} />} tone="info" />
        <StatCard label="Open" value={openCount} tone={openCount > 0 ? "warning" : "success"} />
        <StatCard label="Failed replay" value={failedCount} tone={failedCount > 0 ? "danger" : "neutral"} />
        <StatCard label="Resolved" value={resolvedCount} tone="success" />
      </div>

      <Card>
        <CardHeader
          title="Promotion-to-loyalty DLT"
          subtitle={deadLettersQuery.data?.hasMore ? "Còn thêm record phía sau; thu hẹp filter để xử lý an toàn." : "Inbound Kafka dead-letter records của loyalty consumer."}
          actions={<Badge value="DLT" label={`${rows.length} records`} tone={openCount + failedCount > 0 ? "warning" : "slate"} />}
        />
        {deadLettersQuery.isLoading && <Spinner />}
        {deadLettersQuery.isError && <ErrorState error={deadLettersQuery.error} />}
        {!deadLettersQuery.isLoading && !deadLettersQuery.isError && rows.length === 0 && <EmptyState message="Không có DLT record phù hợp." />}
        {rows.length > 0 && (
          <DeadLetterTable
            rows={rows}
            onView={setSelectedDeadLetter}
            onReplay={(deadLetter, dryRun) => openAction(deadLetter, "replay", dryRun)}
            onDiscard={(deadLetter, dryRun) => openAction(deadLetter, "discard", dryRun)}
          />
        )}
      </Card>

      <DeadLetterDetailDrawer
        deadLetter={detailQuery.data}
        isLoading={detailQuery.isLoading}
        error={detailQuery.error}
        open={Boolean(selectedDeadLetter)}
        onClose={() => setSelectedDeadLetter(null)}
      />

      <ConfirmDialog
        open={Boolean(actionTarget)}
        onOpenChange={(open) => !open && setActionTarget(null)}
        title={`${actionTarget?.dryRun ? "Dry-run " : ""}${actionTarget?.action === "discard" ? "Discard" : "Replay"} DLT record`}
        description={actionTarget ? `${actionTarget.deadLetter.sourceTopic} · ${compactId(actionTarget.deadLetter.id)}` : undefined}
        confirmLabel={actionTarget?.dryRun ? "Dry-run" : actionTarget?.action === "discard" ? "Discard" : "Replay"}
        tone={actionTarget?.action === "discard" ? "danger" : "primary"}
        isPending={actionMutation.isPending}
        onConfirm={() => actionMutation.mutate()}
      >
        <div className="space-y-3">
          <Notice tone={actionTarget?.dryRun ? "neutral" : "warning"} title={actionTarget?.dryRun ? "Dry-run only" : "Production action"}>
            {actionTarget?.dryRun
              ? "Backend chỉ kiểm tra trạng thái hiện tại, không publish lại message và không đổi trạng thái DLT."
              : actionTarget?.action === "replay"
                ? "Backend sẽ publish lại payload gốc về source topic để consumer xử lý lại."
                : "Record sẽ chuyển DISCARDED và không còn trong hàng cần xử lý."}
          </Notice>
          <FormField label="Reason" required>
            <Textarea value={actionReason} onChange={(event) => setActionReason(event.target.value)} rows={3} />
          </FormField>
          {actionTarget && !actionTarget.dryRun && (
            <div className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-3">
              <FormField label="Evidence reference" required>
                <Input value={approvalEvidence} onChange={(event) => setApprovalEvidence(event.target.value)} />
              </FormField>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={approvalMutation.isPending}
                  onClick={() => approvalMutation.mutate()}
                >
                  Request approval
                </Button>
                {approvalResult && (
                  <Badge value={approvalResult.status} label={compactId(approvalResult.id, 18, 8)} tone={statusTone(approvalResult.status)} />
                )}
              </div>
              <FormField label="Approval ID" required>
                <Input value={approvalId} onChange={(event) => setApprovalId(event.target.value)} />
              </FormField>
              <FormField label="Review note" required>
                <Input value={approvalReviewNote} onChange={(event) => setApprovalReviewNote(event.target.value)} />
              </FormField>
              <Button
                type="button"
                variant="outline"
                disabled={approvalReviewMutation.isPending || !approvalId.trim()}
                onClick={() => approvalReviewMutation.mutate()}
              >
                Approve approval
              </Button>
              {approvalMutation.isError && <ErrorState error={approvalMutation.error} />}
              {approvalReviewMutation.isError && <ErrorState error={approvalReviewMutation.error} />}
            </div>
          )}
          {actionMutation.isError && <ErrorState error={actionMutation.error} />}
        </div>
      </ConfirmDialog>
    </div>
  );
}

function DeadLetterTable({
  rows,
  onView,
  onReplay,
  onDiscard
}: {
  rows: LoyaltyInboundDeadLetter[];
  onView: (deadLetter: LoyaltyInboundDeadLetter) => void;
  onReplay: (deadLetter: LoyaltyInboundDeadLetter, dryRun: boolean) => void;
  onDiscard: (deadLetter: LoyaltyInboundDeadLetter, dryRun: boolean) => void;
}) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Status</Th>
          <Th>Topic</Th>
          <Th>Position</Th>
          <Th>Error</Th>
          <Th>Payload</Th>
          <Th>Created</Th>
          <Th>Actions</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((deadLetter) => {
          const actionable = deadLetter.status === "OPEN" || deadLetter.status === "FAILED";
          return (
            <tr key={deadLetter.id} className="hover:bg-slate-50">
              <Td>
                <StatusPill value={deadLetter.status} />
                {deadLetter.replayAttempts > 0 && (
                  <p className="mt-1 text-xs text-slate-400">{deadLetter.replayAttempts} replay attempts</p>
                )}
              </Td>
              <Td>
                <p className="font-semibold text-slate-900">{deadLetter.sourceTopic}</p>
                <p className="mt-1 font-mono text-xs text-slate-400">{deadLetter.dltTopic}</p>
              </Td>
              <Td>
                <p className="font-mono text-xs text-slate-600">
                  p{deadLetter.kafkaPartition}:o{deadLetter.kafkaOffset}
                </p>
                {deadLetter.originalOffset !== undefined && deadLetter.originalOffset !== null && (
                  <p className="mt-1 text-xs text-slate-400">
                    original p{deadLetter.originalPartition ?? "-"}:o{deadLetter.originalOffset}
                  </p>
                )}
              </Td>
              <Td>
                <p className="max-w-sm truncate font-semibold text-slate-900">{deadLetter.exceptionClass ?? "Unknown"}</p>
                <p className="mt-1 max-w-sm truncate text-xs text-slate-500">{deadLetter.exceptionMessage ?? "-"}</p>
              </Td>
              <Td>
                <p className="font-mono text-xs text-slate-600">{compactId(deadLetter.payloadHash)}</p>
                {deadLetter.recordKey && <p className="mt-1 font-mono text-xs text-slate-400">key {compactId(deadLetter.recordKey)}</p>}
              </Td>
              <Td>{formatDateTime(deadLetter.createdAt)}</Td>
              <Td>
                <div className="flex flex-wrap gap-2">
                  <Button size="xs" variant="secondary" onClick={() => onView(deadLetter)}>
                    <Eye size={14} />
                    View
                  </Button>
                  <Button size="xs" variant="outline" disabled={!actionable} onClick={() => onReplay(deadLetter, true)}>
                    <Search size={14} />
                    Dry-run
                  </Button>
                  <Button size="xs" disabled={!actionable} onClick={() => onReplay(deadLetter, false)}>
                    <RefreshCcw size={14} />
                    Replay
                  </Button>
                  <Button size="xs" variant="danger" disabled={!actionable} onClick={() => onDiscard(deadLetter, false)}>
                    <Trash2 size={14} />
                    Discard
                  </Button>
                </div>
              </Td>
            </tr>
          );
        })}
      </tbody>
    </Table>
  );
}

function DeadLetterDetailDrawer({
  deadLetter,
  isLoading,
  error,
  open,
  onClose
}: {
  deadLetter?: LoyaltyInboundDeadLetterDetail;
  isLoading: boolean;
  error: unknown;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={open}
      onOpenChange={(nextOpen) => !nextOpen && onClose()}
      title="Loyalty DLT detail"
      description={deadLetter ? `${deadLetter.sourceTopic} · ${formatDateTime(deadLetter.createdAt)}` : undefined}
      className="max-w-3xl"
    >
      {isLoading && <Spinner />}
      {error ? <ErrorState error={error} /> : null}
      {deadLetter && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <KeyValue label="ID" value={deadLetter.id} mono />
            <KeyValue label="Status" value={<StatusPill value={deadLetter.status} />} />
            <KeyValue label="Source topic" value={deadLetter.sourceTopic} mono />
            <KeyValue label="DLT topic" value={deadLetter.dltTopic} mono />
            <KeyValue label="DLT position" value={`p${deadLetter.kafkaPartition}:o${deadLetter.kafkaOffset}`} mono />
            <KeyValue label="Original position" value={`p${deadLetter.originalPartition ?? "-"}:o${deadLetter.originalOffset ?? "-"}`} mono />
            <KeyValue label="Consumer group" value={deadLetter.consumerGroup ?? "-"} />
            <KeyValue label="Payload size" value={`${deadLetter.payloadSizeBytes} bytes`} />
            <KeyValue label="Payload hash" value={deadLetter.payloadHash} mono />
            <KeyValue label="Resolved by" value={deadLetter.resolvedBy ?? "-"} />
          </div>
          <Card padding="md">
            <CardHeader title="Exception" subtitle={deadLetter.exceptionClass ?? "Unknown exception"} />
            <p className="text-sm text-slate-600">{deadLetter.exceptionMessage ?? "-"}</p>
            {deadLetter.lastReplayError && (
              <Notice tone="danger" title="Last replay error">
                {deadLetter.lastReplayError}
              </Notice>
            )}
            {deadLetter.stacktrace && (
              <pre className="mt-3 max-h-72 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                {deadLetter.stacktrace}
              </pre>
            )}
          </Card>
          <JsonBlock value={deadLetter.headers ?? {}} />
        </div>
      )}
    </Drawer>
  );
}

function AuditPanel() {
  const [filters, setFilters] = useState<AuditFilters>({
    tenantId: DEFAULT_TENANT_ID,
    applicationId: DEFAULT_APPLICATION_ID,
    limit: 50
  });
  const [draftFilters, setDraftFilters] = useState<AuditFilters>(filters);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  const auditQuery = useQuery({
    queryKey: queryKeys.incentives.loyaltyAudit(filters),
    queryFn: () => queryLoyaltyAudit(filters),
    retry: 1
  });

  const events = auditQuery.data?.items ?? [];

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters(draftFilters);
  }

  return (
    <div className="space-y-4">
      <form onSubmit={applyFilters}>
        <Toolbar>
          <FormField label="Tenant">
            <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
          </FormField>
          <FormField label="Application">
            <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
          </FormField>
          <FormField label="Action">
            <Input value={draftFilters.action ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, action: event.target.value })} />
          </FormField>
          <FormField label="Actor">
            <Input value={draftFilters.actorId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, actorId: event.target.value })} />
          </FormField>
          <FormField label="Correlation">
            <Input value={draftFilters.correlationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, correlationId: event.target.value })} />
          </FormField>
          <FormField label="Aggregate type">
            <Input value={draftFilters.aggregateType ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, aggregateType: event.target.value })} />
          </FormField>
          <FormField label="Aggregate ID">
            <Input value={draftFilters.aggregateId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, aggregateId: event.target.value })} />
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
              value={String(draftFilters.limit ?? "")}
              inputMode="numeric"
              onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })}
            />
          </FormField>
          <FilterActions>
            <Button type="submit">
              <Search size={16} />
              Tìm
            </Button>
            <Button type="button" variant="secondary" onClick={() => auditQuery.refetch()}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          </FilterActions>
        </Toolbar>
      </form>

      <Card>
        <CardHeader
          title="Loyalty audit"
          subtitle={auditQuery.data?.hasMore ? "Còn thêm event phía sau; tăng filter hoặc limit để thu hẹp." : "Kết quả theo filter hiện tại."}
          actions={<Badge value="RESULT" label={`${events.length} events`} tone="slate" />}
        />
        {auditQuery.isLoading && <Spinner />}
        {auditQuery.isError && <ErrorState error={auditQuery.error} />}
        {!auditQuery.isLoading && !auditQuery.isError && events.length === 0 && <EmptyState message="Không có audit event phù hợp." />}
        {events.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Time</Th>
                <Th>Action</Th>
                <Th>Actor</Th>
                <Th>Aggregate</Th>
                <Th>Scope</Th>
                <Th>Detail</Th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} className="hover:bg-slate-50">
                  <Td>{formatDateTime(event.createdAt)}</Td>
                  <Td><StatusPill value={event.action ?? "INFO"} label={event.action ?? "event"} /></Td>
                  <Td>{event.actorId ?? "-"}</Td>
                  <Td>
                    <span className="font-semibold">{event.aggregateType ?? "-"}</span>
                    <p className="mt-1 font-mono text-xs text-slate-400">{compactId(event.aggregateId)}</p>
                  </Td>
                  <Td>
                    <span>{event.applicationId ?? "-"}</span>
                    <p className="mt-1 text-xs text-slate-400">{event.tenantId ?? "-"}</p>
                  </Td>
                  <Td>
                    <Button size="xs" variant="secondary" onClick={() => setSelectedEvent(event)}>Xem</Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <EventDrawer event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
}

export function LoyaltyControlPlanePage() {
  const [tab, setTab] = useState<LoyaltyTab>("programs");

  return (
    <div className="space-y-4">
      <PageHeader
        title="Loyalty control plane"
        description="Program, client binding, account ledger và audit cho loyalty."
        actions={
          <Badge value="CONTROL_PLANE" label="Admin operations" tone="brand" />
        }
      />
      <IncentiveNav />

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        <TabButton active={tab === "programs"} onClick={() => setTab("programs")}>
          <ShieldCheck size={16} />
          Programs
        </TabButton>
        <TabButton active={tab === "accounts"} onClick={() => setTab("accounts")}>
          <WalletCards size={16} />
          Accounts & ledger
        </TabButton>
        <TabButton active={tab === "tiers"} onClick={() => setTab("tiers")}>
          <Medal size={16} />
          Tiers
        </TabButton>
        <TabButton active={tab === "approvals"} onClick={() => setTab("approvals")}>
          <ClipboardCheck size={16} />
          Approvals
        </TabButton>
        <TabButton active={tab === "expiry"} onClick={() => setTab("expiry")}>
          <Clock3 size={16} />
          Expiry dry-run
        </TabButton>
        <TabButton active={tab === "reconciliation"} onClick={() => setTab("reconciliation")}>
          <Scale size={16} />
          Reconciliation
        </TabButton>
        <TabButton active={tab === "rewards"} onClick={() => setTab("rewards")}>
          <Gift size={16} />
          Rewards
        </TabButton>
        <TabButton active={tab === "deadLetters"} onClick={() => setTab("deadLetters")}>
          <FileWarning size={16} />
          DLT ops
        </TabButton>
        <TabButton active={tab === "audit"} onClick={() => setTab("audit")}>
          <History size={16} />
          Audit
        </TabButton>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div>
          {tab === "programs" && <ProgramsPanel />}
          {tab === "accounts" && <AccountsPanel />}
          {tab === "tiers" && <TiersPanel />}
          {tab === "approvals" && <ApprovalsPanel />}
          {tab === "expiry" && <ExpiryDryRunPanel />}
          {tab === "reconciliation" && <ReconciliationPanel />}
          {tab === "rewards" && <RewardsPanel />}
          {tab === "deadLetters" && <DeadLetterOperationsPanel />}
          {tab === "audit" && <AuditPanel />}
        </div>
        <aside className="space-y-3">
          <Notice tone="neutral" title="Release gate" icon={<Activity size={16} />}>
            Loyalty runtime chỉ nhận write từ service client đã bind và còn ACTIVE.
          </Notice>
          <Notice tone="info" title="Audit trace" icon={<UserRoundCheck size={16} />}>
            Các thao tác admin sinh correlation ID để nối event, log và ticket vận hành.
          </Notice>
          <Notice tone="info" title="Reward redemption" icon={<Gift size={16} />}>
            Reward tiêu điểm tiêu thụ điểm bằng ledger BURN, không tạo ví điểm riêng.
          </Notice>
          <Notice tone="warning" title="DLT operations" icon={<AlertTriangle size={16} />}>
            Replay chỉ dùng sau khi đã xác nhận consumer/payload sẵn sàng xử lý lại.
          </Notice>
        </aside>
      </div>
    </div>
  );
}
