import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { Link, NavLink, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgePercent,
  CheckCircle2,
  ClipboardCheck,
  FileDown,
  FileJson2,
  GitCompare,
  History,
  Plus,
  RefreshCcw,
  RotateCcw,
  Search,
  Send,
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
  approveCampaignVersion,
  approveRetentionApproval,
  campaignTimeline,
  couponStorageInventory,
  createApplication,
  createCampaign,
  createCampaignVersion,
  createCoupon,
  executeRetention,
  exportRetentionEvidencePack,
  generateCoupons,
  getCampaign,
  getCampaignVersion,
  getCampaignVersionDiff,
  getCampaignVersionValidation,
  getRedemption,
  getRetentionApproval,
  getRetentionEvidencePack,
  getRetentionPolicies,
  getRetentionRestoreDrill,
  listRetentionApprovals,
  listApplications,
  listCampaigns,
  listCampaignVersions,
  listCoupons,
  listLoyaltyPrograms,
  listRedemptions,
  listReservations,
  listSubmittedCampaignVersions,
  publishCampaignVersion,
  queryAudit,
  redemptionTimeline,
  rejectCampaignVersion,
  rejectRetentionApproval,
  registerRetentionRestoreDrill,
  requestRetentionApproval,
  reverseRedemption,
  retentionOperationId,
  rollbackCampaignVersion,
  runRetentionDryRun,
  submitCampaignVersion,
  updateCampaignVersionDraft,
  updateCouponStatus,
  upsertApplicationClientBinding
} from "./api";
import {
  compactId,
  formatDateTime,
  formatDateTimeInput,
  splitCommaList,
  statusLabel,
  statusTone,
  toIsoDateTime,
  toNumberOrUndefined,
  transitionVerb
} from "./labels";
import { actionTemplates, formatJson, loyaltyPointsEarnActionTemplate, parseSpecList, ruleTemplates } from "./json";
import { parseRestoreDrillEvidenceJson } from "./retention-evidence";
import {
  approvalReady,
  canDecideRetentionApproval,
  canExecuteRetentionApproval,
  dryRunExpiresAt,
  dryRunExpired,
  executableRetentionPolicy,
  isPast,
  restoreDrillIssues,
  restoreFormIssues,
  retentionDryRunTtlMinutes,
  retentionApprovalDecisionGate,
  retentionExecutionConsumed,
  retentionExecutionGate,
  retentionServerGateIssues,
  retentionScopeFingerprint
} from "./retention-gates";
import type {
  ActionSpec,
  ApplicationFilters,
  AuditEvent,
  AuditFilters,
  Campaign,
  CampaignFilters,
  CampaignVersion,
  CampaignVersionDetail,
  Coupon,
  CouponFilters,
  LoyaltyProgram,
  Redemption,
  RedemptionFilters,
  Reservation,
  ReservationFilters,
  RetentionApproval,
  RetentionApprovalFilters,
  RetentionDryRunResponse,
  RetentionDryRunResult,
  RetentionEvidencePack,
  ReviewQueueFilters,
  RuleSpec
} from "./types";

const navItems = [
  { to: "/incentives", label: "Tổng quan" },
  { to: "/incentives/applications", label: "Applications" },
  { to: "/incentives/campaigns", label: "Campaigns" },
  { to: "/incentives/coupons", label: "Coupons" },
  { to: "/incentives/review", label: "Review queue" },
  { to: "/incentives/coupon-imports", label: "Coupon imports" },
  { to: "/incentives/redemptions", label: "Support" },
  { to: "/incentives/reconciliation", label: "Reconciliation" },
  { to: "/incentives/loyalty", label: "Loyalty" },
  { to: "/incentives/retention", label: "Retention" },
  { to: "/incentives/audit", label: "Audit" }
];

type ConfirmAction = {
  action: "submit" | "approve" | "reject" | "publish" | "rollback";
  versionNumber: number;
  title: string;
  description: string;
  tone?: "primary" | "danger" | "secondary";
};

export function IncentiveNav() {
  return (
    <nav className="mb-4 flex flex-wrap gap-2 border-b border-slate-200 pb-3">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/incentives"}
          className={({ isActive }) =>
            cn(
              "inline-flex h-9 items-center rounded-md px-3 text-sm font-semibold transition",
              isActive ? "bg-brand-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

function StatusPill({ value, label }: { value?: string | null; label?: ReactNode }) {
  return <Badge value={value ?? undefined} label={label ?? statusLabel(value)} tone={statusTone(value)} />;
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

function Timeline({ events }: { events?: AuditEvent[] }) {
  if (!events?.length) return <EmptyState message="Chưa có audit event phù hợp." />;
  return (
    <ol className="divide-y divide-slate-100">
      {events.map((event) => (
        <li key={event.id} className="grid gap-3 px-4 py-3 md:grid-cols-[180px_1fr]">
          <div>
            <p className="text-xs font-semibold text-slate-400">{formatDateTime(event.createdAt)}</p>
            <p className="mt-1 font-mono text-xs text-slate-400">{compactId(event.id)}</p>
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill value={event.action ?? "INFO"} label={event.action ?? "event"} />
              {event.aggregateType && <Badge value="AGGREGATE" label={event.aggregateType} tone="slate" />}
            </div>
            <p className="mt-2 text-sm font-semibold text-slate-800">{event.note || event.actorId || "System event"}</p>
            <p className="mt-1 break-words font-mono text-xs text-slate-400">
              {compactId(event.aggregateId)} · {event.sourceClientId ?? "unknown client"}
            </p>
            {event.correlationId && (
              <p className="mt-1 break-words font-mono text-xs text-slate-400">
                corr {compactId(event.correlationId)}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function FilterActions({ children }: { children: ReactNode }) {
  return <div className="flex items-end gap-2">{children}</div>;
}

function checkboxLabel(label: string, checked: boolean, onChange: (checked: boolean) => void) {
  return (
    <label className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700">
      <input
        type="checkbox"
        className="size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label}
    </label>
  );
}

function invalidateIncentives(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: queryKeys.incentives.all });
}

function toCampaignPayload(form: CampaignDraftForm) {
  const actions = parseSpecList<ActionSpec>(form.actionsJson, "Actions");
  if (actions.length === 0) {
    throw new Error("Actions phải có ít nhất một action");
  }

  return {
    code: form.code.trim(),
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    incentiveType: form.incentiveType.trim() || undefined,
    startsAt: toIsoDateTime(form.startsAt),
    endsAt: toIsoDateTime(form.endsAt),
    priority: toNumberOrUndefined(form.priority),
    exclusive: form.exclusive,
    stackable: form.stackable,
    couponRequired: form.couponRequired,
    matchPolicy: form.matchPolicy,
    currency: form.currency.trim() || undefined,
    rules: parseSpecList<RuleSpec>(form.rulesJson, "Rules"),
    actions,
    maxRedemptions: toNumberOrUndefined(form.maxRedemptions),
    maxRedemptionsPerProfile: toNumberOrUndefined(form.maxRedemptionsPerProfile)
  };
}

type CampaignDraftForm = {
  tenantId: string;
  applicationId: string;
  code: string;
  name: string;
  description: string;
  incentiveType: string;
  startsAt: string;
  endsAt: string;
  priority: string;
  exclusive: boolean;
  stackable: boolean;
  couponRequired: boolean;
  matchPolicy: string;
  currency: string;
  rulesJson: string;
  actionsJson: string;
  maxRedemptions: string;
  maxRedemptionsPerProfile: string;
};

const defaultCampaignForm: CampaignDraftForm = {
  tenantId: "courseflow",
  applicationId: "lms",
  code: "",
  name: "",
  description: "",
  incentiveType: "PROMOTION",
  startsAt: "",
  endsAt: "",
  priority: "100",
  exclusive: false,
  stackable: true,
  couponRequired: false,
  matchPolicy: "ALL",
  currency: "USD",
  rulesJson: formatJson(ruleTemplates),
  actionsJson: formatJson(actionTemplates),
  maxRedemptions: "",
  maxRedemptionsPerProfile: ""
};

function versionToForm(version: CampaignVersionDetail): CampaignDraftForm {
  return {
    tenantId: version.tenantId,
    applicationId: version.applicationId,
    code: version.code,
    name: version.name,
    description: version.description ?? "",
    incentiveType: version.incentiveType ?? "PROMOTION",
    startsAt: formatDateTimeInput(version.startsAt),
    endsAt: formatDateTimeInput(version.endsAt),
    priority: String(version.priority ?? 0),
    exclusive: version.exclusive,
    stackable: version.stackable,
    couponRequired: version.couponRequired,
    matchPolicy: version.matchPolicy ?? "ALL",
    currency: version.currency ?? "USD",
    rulesJson: formatJson(version.rules ?? []),
    actionsJson: formatJson(version.actions ?? []),
    maxRedemptions: version.maxRedemptions ? String(version.maxRedemptions) : "",
    maxRedemptionsPerProfile: version.maxRedemptionsPerProfile ? String(version.maxRedemptionsPerProfile) : ""
  };
}

function loyaltyProgramLabel(program: LoyaltyProgram) {
  return `${program.programId} · ${program.name} · ${program.status}`;
}

function CampaignSpecForm({
  form,
  setForm,
  includeTenantApplication = false,
  disabled = false
}: {
  form: CampaignDraftForm;
  setForm: (form: CampaignDraftForm) => void;
  includeTenantApplication?: boolean;
  disabled?: boolean;
}) {
  const [actionBuilder, setActionBuilder] = useState({
    type: "ORDER_FIXED_OFF",
    amount: "10",
    points: "100",
    programId: ""
  });
  const [actionBuilderError, setActionBuilderError] = useState<string | null>(null);
  const loyaltyPrograms = useQuery({
    queryKey: queryKeys.incentives.loyaltyPrograms({
      tenantId: form.tenantId,
      applicationId: form.applicationId,
      limit: 100
    }),
    queryFn: () => listLoyaltyPrograms({
      tenantId: form.tenantId,
      applicationId: form.applicationId,
      limit: 100
    }),
    enabled: Boolean(form.tenantId && form.applicationId)
  });
  const selectedLoyaltyProgram = loyaltyPrograms.data?.find(
    (program) => program.programId === actionBuilder.programId
  );

  useEffect(() => {
    if (!actionBuilder.programId && loyaltyPrograms.data?.length) {
      setActionBuilder((current) => ({ ...current, programId: loyaltyPrograms.data[0].programId }));
    }
  }, [actionBuilder.programId, loyaltyPrograms.data]);

  function applyActionBuilder() {
    setActionBuilderError(null);
    if (actionBuilder.type === "LOYALTY_POINTS_EARN") {
      const points = Number(actionBuilder.points);
      if (!actionBuilder.programId) {
        setActionBuilderError("Chọn loyalty program trước khi tạo action tích điểm.");
        return;
      }
      if (!Number.isFinite(points) || points <= 0) {
        setActionBuilderError("Points phải là số lớn hơn 0.");
        return;
      }
      setForm({
        ...form,
        incentiveType: "LOYALTY",
        actionsJson: formatJson([loyaltyPointsEarnActionTemplate(actionBuilder.programId, points)])
      });
      return;
    }

    const amount = Number(actionBuilder.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setActionBuilderError("Amount phải là số lớn hơn 0.");
      return;
    }
    setForm({
      ...form,
      incentiveType: form.incentiveType || "PROMOTION",
      actionsJson: formatJson([
        {
          type: "ORDER_FIXED_OFF",
          schemaVersion: 1,
          parameters: {
            amount,
            currency: form.currency || "USD"
          }
        }
      ])
    });
  }

  return (
    <div className="grid gap-4">
      {includeTenantApplication && (
        <div className="grid gap-3 md:grid-cols-2">
          <FormField label="Tenant" required>
            <Input value={form.tenantId} onChange={(event) => setForm({ ...form, tenantId: event.target.value })} disabled={disabled} />
          </FormField>
          <FormField label="Application" required>
            <Input value={form.applicationId} onChange={(event) => setForm({ ...form, applicationId: event.target.value })} disabled={disabled} />
          </FormField>
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-[1fr_1.5fr]">
        <FormField label="Code" required>
          <Input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} disabled={disabled} />
        </FormField>
        <FormField label="Tên campaign" required>
          <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} disabled={disabled} />
        </FormField>
      </div>

      <FormField label="Mô tả">
        <Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} disabled={disabled} />
      </FormField>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <FormField label="Loại incentive">
          <Input value={form.incentiveType} onChange={(event) => setForm({ ...form, incentiveType: event.target.value })} disabled={disabled} />
        </FormField>
        <FormField label="Currency">
          <Input value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })} disabled={disabled} />
        </FormField>
        <FormField label="Priority">
          <Input value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} disabled={disabled} inputMode="numeric" />
        </FormField>
        <FormField label="Match policy">
          <Select value={form.matchPolicy} onChange={(event) => setForm({ ...form, matchPolicy: event.target.value })} disabled={disabled}>
            <option value="ALL">ALL</option>
            <option value="ANY">ANY</option>
          </Select>
        </FormField>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <FormField label="Bắt đầu">
          <Input type="datetime-local" value={form.startsAt} onChange={(event) => setForm({ ...form, startsAt: event.target.value })} disabled={disabled} />
        </FormField>
        <FormField label="Kết thúc">
          <Input type="datetime-local" value={form.endsAt} onChange={(event) => setForm({ ...form, endsAt: event.target.value })} disabled={disabled} />
        </FormField>
        <FormField label="Max redemptions">
          <Input value={form.maxRedemptions} onChange={(event) => setForm({ ...form, maxRedemptions: event.target.value })} disabled={disabled} inputMode="numeric" />
        </FormField>
        <FormField label="Max/profile">
          <Input value={form.maxRedemptionsPerProfile} onChange={(event) => setForm({ ...form, maxRedemptionsPerProfile: event.target.value })} disabled={disabled} inputMode="numeric" />
        </FormField>
      </div>

      <div className="flex flex-wrap gap-2">
        {checkboxLabel("Exclusive", form.exclusive, (checked) => setForm({ ...form, exclusive: checked }))}
        {checkboxLabel("Stackable", form.stackable, (checked) => setForm({ ...form, stackable: checked }))}
        {checkboxLabel("Coupon required", form.couponRequired, (checked) => setForm({ ...form, couponRequired: checked }))}
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
        <div className="grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)_160px_auto]">
          <FormField label="Action type">
            <Select
              value={actionBuilder.type}
              onChange={(event) => setActionBuilder({ ...actionBuilder, type: event.target.value })}
              disabled={disabled}
            >
              <option value="ORDER_FIXED_OFF">ORDER_FIXED_OFF</option>
              <option value="LOYALTY_POINTS_EARN">LOYALTY_POINTS_EARN</option>
            </Select>
          </FormField>
          {actionBuilder.type === "LOYALTY_POINTS_EARN" ? (
            <FormField label="Loyalty program">
              <Select
                value={actionBuilder.programId}
                onChange={(event) => setActionBuilder({ ...actionBuilder, programId: event.target.value })}
                disabled={disabled || loyaltyPrograms.isLoading}
              >
                <option value="">Chọn program</option>
                {(loyaltyPrograms.data ?? []).map((program) => (
                  <option key={program.id} value={program.programId}>
                    {loyaltyProgramLabel(program)}
                  </option>
                ))}
              </Select>
            </FormField>
          ) : (
            <FormField label="Currency">
              <Input value={form.currency} onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })} disabled={disabled} />
            </FormField>
          )}
          <FormField label={actionBuilder.type === "LOYALTY_POINTS_EARN" ? "Points" : "Amount"}>
            <Input
              value={actionBuilder.type === "LOYALTY_POINTS_EARN" ? actionBuilder.points : actionBuilder.amount}
              onChange={(event) =>
                setActionBuilder(actionBuilder.type === "LOYALTY_POINTS_EARN"
                  ? { ...actionBuilder, points: event.target.value }
                  : { ...actionBuilder, amount: event.target.value })}
              disabled={disabled}
              inputMode="decimal"
            />
          </FormField>
          <Button className="self-end" variant="secondary" onClick={applyActionBuilder} disabled={disabled}>
            <FileJson2 size={16} />
            Apply action
          </Button>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          {actionBuilder.type === "LOYALTY_POINTS_EARN" && selectedLoyaltyProgram && (
            <Badge value={selectedLoyaltyProgram.status} label={`${selectedLoyaltyProgram.pointUnit} program`} />
          )}
          {loyaltyPrograms.isError && <span className="font-semibold text-red-600">Không tải được loyalty programs</span>}
          {actionBuilderError && <span className="font-semibold text-red-600">{actionBuilderError}</span>}
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <FormField label="Rules JSON" required>
          <Textarea
            className="min-h-72 font-mono text-xs"
            value={form.rulesJson}
            onChange={(event) => setForm({ ...form, rulesJson: event.target.value })}
            disabled={disabled}
          />
        </FormField>
        <FormField label="Actions JSON" required>
          <Textarea
            className="min-h-72 font-mono text-xs"
            value={form.actionsJson}
            onChange={(event) => setForm({ ...form, actionsJson: event.target.value })}
            disabled={disabled}
          />
        </FormField>
      </div>
    </div>
  );
}

export function IncentiveDashboardPage() {
  const applications = useQuery({
    queryKey: queryKeys.incentives.applications({}),
    queryFn: () => listApplications(),
    retry: 1
  });
  const campaigns = useQuery({
    queryKey: queryKeys.incentives.campaigns({}),
    queryFn: () => listCampaigns(),
    retry: 1
  });
  const redemptions = useQuery({
    queryKey: queryKeys.incentives.redemptions({ limit: 8 }),
    queryFn: () => listRedemptions({ limit: 8 }),
    retry: 1
  });
  const audit = useQuery({
    queryKey: queryKeys.incentives.audit({ limit: 8 }),
    queryFn: () => queryAudit({ limit: 8 }),
    retry: 1
  });

  const campaignRows = campaigns.data ?? [];
  const activeCampaigns = campaignRows.filter((campaign) => campaign.status === "ACTIVE").length;
  const publishedCampaigns = campaignRows.filter((campaign) => campaign.publishedVersion).length;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Incentive platform"
        title="Promotion operations"
        description="Quản lý application registry, campaign/version lifecycle, audit trail và redemption support cho promotion/coupon/loyalty engine."
        actions={
          <Link to="campaigns/new">
            <Button>
              <Plus size={16} />
              Tạo campaign
            </Button>
          </Link>
        }
      />
      <IncentiveNav />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Applications"
          value={applications.data?.length ?? "—"}
          detail="Tenant/application registry được phép gọi incentive engine."
          icon={<ShieldCheck size={18} />}
          tone="brand"
        />
        <StatCard
          label="Campaigns"
          value={campaignRows.length || "—"}
          detail={`${activeCampaigns} campaign đang active.`}
          icon={<BadgePercent size={18} />}
          tone="info"
        />
        <StatCard
          label="Published versions"
          value={publishedCampaigns || "—"}
          detail="Learner/client chỉ nhận published snapshot."
          icon={<CheckCircle2 size={18} />}
          tone="success"
        />
        <StatCard
          label="Recent redemptions"
          value={redemptions.data?.length ?? "—"}
          detail="Luồng commit/reverse gần nhất qua API."
          icon={<TicketPercent size={18} />}
          tone="warning"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader
            title="Campaigns cần chú ý"
            subtitle="Theo dõi trạng thái draft/published và mở workspace để xử lý version."
            actions={
              <Link to="campaigns">
                <Button variant="secondary" size="sm">
                  Mở danh sách
                </Button>
              </Link>
            }
          />
          {campaigns.isLoading && <Spinner />}
          {campaigns.isError && <ErrorState error={campaigns.error} />}
          {campaignRows.length === 0 && !campaigns.isLoading && !campaigns.isError && <EmptyState message="Chưa có campaign." />}
          {campaignRows.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Campaign</Th>
                  <Th>Application</Th>
                  <Th>Status</Th>
                  <Th>Version</Th>
                </tr>
              </thead>
              <tbody>
                {campaignRows.slice(0, 8).map((campaign) => (
                  <tr key={campaign.id} className="hover:bg-slate-50">
                    <Td>
                      <Link to={`campaigns/${campaign.id}`} className="font-semibold text-brand-700 hover:underline">
                        {campaign.name}
                      </Link>
                      <p className="mt-1 font-mono text-xs text-slate-400">{campaign.code}</p>
                    </Td>
                    <Td>
                      <span className="font-semibold">{campaign.applicationId}</span>
                      <p className="mt-1 text-xs text-slate-400">{campaign.tenantId}</p>
                    </Td>
                    <Td>
                      <StatusPill value={campaign.status} />
                    </Td>
                    <Td>
                      <span className="text-sm text-slate-700">draft v{campaign.draftVersion ?? "-"}</span>
                      <p className="mt-1 text-xs text-slate-400">published v{campaign.publishedVersion ?? "-"}</p>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Audit mới nhất" subtitle="Dấu vết actor/action/note để reviewer và support truy ngược." />
          {audit.isLoading && <Spinner />}
          {audit.isError && <ErrorState error={audit.error} />}
          {audit.data && <Timeline events={audit.data.items} />}
        </Card>
      </div>
    </div>
  );
}

function retentionDaysOverride(policyId: string, value: string) {
  const parsed = toNumberOrUndefined(value);
  return parsed === undefined ? undefined : { [policyId]: parsed };
}

function retentionResult(dryRun: RetentionDryRunResponse | null, policyId: string): RetentionDryRunResult | undefined {
  return dryRun?.results.find((item) => item.policyId === policyId);
}

function copyText(value?: string | null) {
  if (!value) return;
  navigator.clipboard?.writeText(value).catch(() => undefined);
}

function downloadTextFile(filename: string, contentType: string, content: string) {
  const blob = new Blob([content], { type: contentType || "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename || "retention-evidence-pack.json";
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

function RetentionServerGateErrorNotice({ error, title = "Retention server gate" }: { error: unknown; title?: string }) {
  const issues = retentionServerGateIssues(error);
  if (!issues.length) return <ErrorState error={error} />;
  return (
    <Notice tone="danger" title={title}>
      <GateIssues issues={issues} />
    </Notice>
  );
}

function retentionApprovalSignal(approval: RetentionApproval, user: Parameters<typeof canDecideRetentionApproval>[1]) {
  if (retentionExecutionConsumed(approval)) return { label: "Consumed", tone: "slate" as const };
  if ((approval.status === "PENDING_APPROVAL" || approval.status === "APPROVED") && isPast(approval.expiresAt)) {
    return { label: "Expired", tone: "danger" as const };
  }
  if (canDecideRetentionApproval(approval, user)) return { label: "Ready to review", tone: "warning" as const };
  if (canExecuteRetentionApproval({ approval, user, executionAttemptBlocked: false })) {
    return { label: "Ready to execute", tone: "success" as const };
  }
  return { label: statusLabel(approval.status), tone: statusTone(approval.status) };
}

function RetentionResultTable({ dryRun }: { dryRun: RetentionDryRunResponse | null }) {
  if (!dryRun) return <EmptyState message="Chạy dry-run để xem candidate aggregate." />;
  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-3">
        <KeyValue label="Dry-run ID" value={compactId(dryRun.dryRunId)} mono />
        <KeyValue label="Generated" value={formatDateTime(dryRun.generatedAt)} />
        <KeyValue label="Result hash" value={compactId(dryRun.resultHash)} mono />
      </div>
      {dryRun.warnings.length > 0 && (
        <Notice tone="warning" title="Dry-run warnings">
          {dryRun.warnings.join(" · ")}
        </Notice>
      )}
      <Table>
        <thead>
          <tr>
            <Th>Policy</Th>
            <Th>Cutoff</Th>
            <Th>Eligible</Th>
            <Th>Blocked</Th>
            <Th>Batch</Th>
            <Th>Hash</Th>
          </tr>
        </thead>
        <tbody>
          {dryRun.results.map((item) => (
            <tr key={item.policyId} className="hover:bg-slate-50">
              <Td>
                <p className="font-semibold text-slate-900">{item.policyId}</p>
                <p className="mt-1 text-xs text-slate-400">{item.targetDataset}</p>
              </Td>
              <Td>{formatDateTime(item.cutoff)}</Td>
              <Td>{item.eligibleCount.toLocaleString()}</Td>
              <Td>
                {item.blockedCount.toLocaleString()}
                {item.blockedReason && <p className="mt-1 text-xs text-slate-400">{item.blockedReason}</p>}
              </Td>
              <Td>{item.batchLimit.toLocaleString()}</Td>
              <Td>
                <span className="font-mono text-xs">{compactId(item.resultHash)}</span>
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

export function RetentionConsolePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [scope, setScope] = useState({
    tenantId: "courseflow",
    applicationId: "lms",
    policyId: executableRetentionPolicy,
    retentionDays: "",
    batchLimit: "500",
    reason: "monthly privacy retention dry-run"
  });
  const [dryRun, setDryRun] = useState<RetentionDryRunResponse | null>(null);
  const [dryRunFingerprint, setDryRunFingerprint] = useState<string | null>(null);
  const [restoreForm, setRestoreForm] = useState({
    restoreDrillRef: "",
    databaseName: "cf_promotion",
    backupPath: "",
    artifactHash: "",
    status: "PASSED",
    checkedAt: "",
    expiresAt: "",
    note: ""
  });
  const [restoreEvidenceText, setRestoreEvidenceText] = useState("");
  const [restoreEvidenceError, setRestoreEvidenceError] = useState<string | null>(null);
  const [restoreLookup, setRestoreLookup] = useState("");
  const [approvalForm, setApprovalForm] = useState({
    restoreDrillRef: "",
    reason: "privacy redaction execution",
    changeTicket: ""
  });
  const [approvalId, setApprovalId] = useState("");
  const [approval, setApproval] = useState<RetentionApproval | null>(null);
  const [decisionNote, setDecisionNote] = useState("");
  const [executionAttemptBlocked, setExecutionAttemptBlocked] = useState(false);
  const [executionForm, setExecutionForm] = useState({
    idempotencyKey: retentionOperationId("retention-exec"),
    correlationId: retentionOperationId("corr-retention-exec"),
    confirm: false
  });
  const [execution, setExecution] = useState<Awaited<ReturnType<typeof executeRetention>> | null>(null);
  const [executeOpen, setExecuteOpen] = useState(false);
  const [approvalQueueFilters, setApprovalQueueFilters] = useState<RetentionApprovalFilters>({
    scopeType: "APPLICATION",
    tenantId: "courseflow",
    applicationId: "lms",
    status: "PENDING_APPROVAL",
    expired: false,
    limit: 50
  });
  const [draftApprovalQueueFilters, setDraftApprovalQueueFilters] = useState<RetentionApprovalFilters>(approvalQueueFilters);
  const [evidencePack, setEvidencePack] = useState<RetentionEvidencePack | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  const policies = useQuery({
    queryKey: queryKeys.incentives.retentionPolicies,
    queryFn: getRetentionPolicies,
    retry: 1
  });

  const selectedPolicy = useMemo(
    () => policies.data?.policies.find((policy) => policy.policyId === scope.policyId) ?? policies.data?.policies[0],
    [policies.data?.policies, scope.policyId]
  );
  const selectedResult = useMemo(() => retentionResult(dryRun, scope.policyId), [dryRun, scope.policyId]);
  const currentDryRunFingerprint = useMemo(() => retentionScopeFingerprint(scope), [scope]);
  const dryRunScopeChanged = Boolean(dryRun && dryRunFingerprint && dryRunFingerprint !== currentDryRunFingerprint);
  const approvalQueueEnabled = Boolean(
    approvalQueueFilters.scopeType === "GLOBAL"
      || (approvalQueueFilters.tenantId?.trim() && approvalQueueFilters.applicationId?.trim())
  );
  const approvalQueue = useQuery({
    queryKey: queryKeys.incentives.retentionApprovals(approvalQueueFilters),
    queryFn: () => listRetentionApprovals(approvalQueueFilters),
    enabled: approvalQueueEnabled,
    retry: 1
  });
  const approvalQueueItems = approvalQueue.data?.items ?? [];
  const dryRunIsExpired = dryRunExpired(dryRun);
  const dryRunExpiry = dryRunExpiresAt(dryRun);
  const restoreFormReadiness = useMemo(() => restoreFormIssues(restoreForm), [restoreForm]);
  const decisionGate = useMemo(
    () => (approval ? retentionApprovalDecisionGate(approval, user) : { allowed: false, issues: [] }),
    [approval, user]
  );
  const decisionIssues = decisionGate.issues;
  const canDecideApproval = approval ? decisionGate.allowed : false;
  const executionGate = useMemo(
    () => retentionExecutionGate({ approval, user, execution, executionAttemptBlocked }),
    [approval, user, execution, executionAttemptBlocked]
  );
  const executionGateIssues = executionGate.issues;
  const canExecuteApproval = executionGate.allowed;
  const approvalAuditFilters = useMemo<AuditFilters>(
    () => ({
      tenantId: approval?.tenantId ?? scope.tenantId,
      applicationId: approval?.applicationId ?? scope.applicationId,
      aggregateType: approval?.approvalId ? "retention-approval" : undefined,
      aggregateId: approval?.approvalId,
      limit: 8
    }),
    [approval?.applicationId, approval?.approvalId, approval?.tenantId, scope.applicationId, scope.tenantId]
  );
  const audit = useQuery({
    queryKey: queryKeys.incentives.audit(approvalAuditFilters),
    queryFn: () => queryAudit(approvalAuditFilters),
    retry: 1
  });
  const executionAuditFilters = useMemo<AuditFilters>(
    () => ({
      tenantId: execution?.tenantId ?? approval?.tenantId ?? scope.tenantId,
      applicationId: execution?.applicationId ?? approval?.applicationId ?? scope.applicationId,
      correlationId: executionForm.correlationId.trim() || undefined,
      limit: 8
    }),
    [
      approval?.applicationId,
      approval?.tenantId,
      execution?.applicationId,
      execution?.tenantId,
      executionForm.correlationId,
      scope.applicationId,
      scope.tenantId
    ]
  );
  const executionAudit = useQuery({
    queryKey: queryKeys.incentives.audit(executionAuditFilters),
    queryFn: () => queryAudit(executionAuditFilters),
    enabled: Boolean(executionAuditFilters.correlationId),
    retry: 1
  });

  const dryRunMutation = useMutation({
    mutationFn: () =>
      runRetentionDryRun({
        tenantId: scope.tenantId.trim() || undefined,
        applicationId: scope.applicationId.trim() || undefined,
        policyIds: [scope.policyId],
        retentionDaysOverride: retentionDaysOverride(scope.policyId, scope.retentionDays),
        batchLimit: toNumberOrUndefined(scope.batchLimit),
        reason: scope.reason.trim() || undefined
      }),
    onSuccess: (response) => {
      setDryRun(response);
      const result = retentionResult(response, scope.policyId);
      const nextScope = result?.batchLimit ? { ...scope, batchLimit: String(result.batchLimit) } : scope;
      setDryRunFingerprint(retentionScopeFingerprint(nextScope));
      setApproval(null);
      setExecution(null);
      setExecutionAttemptBlocked(false);
      setApprovalForm((current) => ({
        ...current,
        restoreDrillRef: current.restoreDrillRef || restoreForm.restoreDrillRef,
        reason: current.reason || scope.reason,
        changeTicket: current.changeTicket
      }));
      if (result?.batchLimit) {
        setScope((current) => ({ ...current, batchLimit: String(result.batchLimit) }));
      }
    }
  });

  const registerDrill = useMutation({
    mutationFn: () =>
      registerRetentionRestoreDrill({
        restoreDrillRef: restoreForm.restoreDrillRef.trim(),
        databaseName: restoreForm.databaseName.trim(),
        backupPath: restoreForm.backupPath.trim(),
        artifactHash: restoreForm.artifactHash.trim(),
        status: restoreForm.status,
        checkedAt: toIsoDateTime(restoreForm.checkedAt),
        expiresAt: toIsoDateTime(restoreForm.expiresAt),
        note: restoreForm.note.trim() || undefined
      }),
    onSuccess: (drill) => {
      setRestoreLookup(drill.restoreDrillRef);
      setApprovalForm((current) => ({ ...current, restoreDrillRef: drill.restoreDrillRef }));
      queryClient.invalidateQueries({ queryKey: queryKeys.incentives.retentionRestoreDrill(drill.restoreDrillRef) });
    }
  });

  function applyRestoreEvidence(rawJson: string) {
    try {
      const evidence = parseRestoreDrillEvidenceJson(rawJson);
      setRestoreForm((current) => ({
        ...current,
        restoreDrillRef: evidence.restoreDrillRef,
        databaseName: evidence.databaseName,
        backupPath: evidence.backupPath,
        artifactHash: evidence.artifactHash,
        status: evidence.status,
        checkedAt: formatDateTimeInput(evidence.checkedAt),
        expiresAt: formatDateTimeInput(evidence.expiresAt),
        note: current.note || evidence.note || ""
      }));
      setApprovalForm((current) => ({ ...current, restoreDrillRef: evidence.restoreDrillRef }));
      setRestoreEvidenceError(null);
    } catch (error) {
      setRestoreEvidenceError(error instanceof Error ? error.message : "Không đọc được restore drill evidence");
    }
  }

  async function handleRestoreEvidenceFile(file?: File | null) {
    if (!file) return;
    const text = await file.text();
    setRestoreEvidenceText(text);
    applyRestoreEvidence(text);
  }

  const restoreDrill = useQuery({
    queryKey: queryKeys.incentives.retentionRestoreDrill(restoreLookup),
    queryFn: () => getRetentionRestoreDrill(restoreLookup.trim()),
    enabled: Boolean(restoreLookup.trim()),
    retry: 1
  });
  const activeRestoreDrill =
    restoreDrill.data?.restoreDrillRef === approvalForm.restoreDrillRef.trim()
      ? restoreDrill.data
      : registerDrill.data?.restoreDrillRef === approvalForm.restoreDrillRef.trim()
        ? registerDrill.data
        : null;
  const restoreGateIssues = useMemo(
    () => restoreDrillIssues(activeRestoreDrill, approvalForm.restoreDrillRef, dryRun),
    [activeRestoreDrill, approvalForm.restoreDrillRef, dryRun]
  );
  const restoreReady = restoreGateIssues.length === 0;

  const requestApproval = useMutation({
    mutationFn: () => {
      if (!dryRun || !selectedResult) throw new Error("Cần dry-run hợp lệ trước khi request approval");
      return requestRetentionApproval({
        tenantId: scope.tenantId.trim() || undefined,
        applicationId: scope.applicationId.trim() || undefined,
        policyId: selectedResult.policyId,
        asOf: dryRun.generatedAt,
        retentionDaysOverride: retentionDaysOverride(selectedResult.policyId, scope.retentionDays),
        batchLimit: selectedResult.batchLimit,
        approvedDryRunId: dryRun.dryRunId,
        approvedResultHash: dryRun.resultHash,
        reason: approvalForm.reason.trim(),
        changeTicket: approvalForm.changeTicket.trim(),
        restoreDrillRef: approvalForm.restoreDrillRef.trim()
      });
    },
    onSuccess: (response) => {
      setApproval(response);
      setApprovalId(response.approvalId);
      setExecution(null);
      setExecutionAttemptBlocked(false);
      invalidateIncentives(queryClient);
    }
  });

  const approvalLookup = useQuery({
    queryKey: queryKeys.incentives.retentionApproval(approvalId),
    queryFn: () => getRetentionApproval(approvalId.trim()),
    enabled: Boolean(approvalId.trim()),
    retry: 1
  });

  useEffect(() => {
    if (approvalLookup.data) {
      setApproval(approvalLookup.data);
      setExecution(null);
      setExecutionAttemptBlocked(false);
    }
  }, [approvalLookup.data]);

  const approve = useMutation({
    mutationFn: () => {
      if (!approval?.approvalId) throw new Error("Chưa chọn approval");
      return approveRetentionApproval(approval.approvalId, { note: decisionNote.trim() || undefined });
    },
    onSuccess: (response) => {
      setApproval(response);
      setExecutionAttemptBlocked(false);
      invalidateIncentives(queryClient);
    }
  });

  const reject = useMutation({
    mutationFn: () => {
      if (!approval?.approvalId) throw new Error("Chưa chọn approval");
      return rejectRetentionApproval(approval.approvalId, { note: decisionNote.trim() || undefined });
    },
    onSuccess: (response) => {
      setApproval(response);
      setExecutionAttemptBlocked(false);
      invalidateIncentives(queryClient);
    }
  });

  const execute = useMutation({
    mutationFn: () => {
      if (!approval?.approvalId) throw new Error("Chưa chọn approval");
      return executeRetention(
        {
          approvalId: approval.approvalId,
          idempotencyKey: executionForm.idempotencyKey,
          confirm: executionForm.confirm
        },
        executionForm.correlationId
      );
    },
    onMutate: () => {
      setExecutionAttemptBlocked(true);
    },
    onSuccess: (response) => {
      setExecution(response);
      setExecuteOpen(false);
      setExecutionForm((current) => ({
        ...current,
        confirm: false
      }));
      invalidateIncentives(queryClient);
    },
    onError: () => {
      setExecuteOpen(false);
      if (approval?.approvalId) {
        void approvalLookup.refetch();
      }
    }
  });

  const viewEvidence = useMutation({
    mutationFn: ({ approvalId }: { approvalId: string }) => getRetentionEvidencePack(approvalId),
    onSuccess: (response) => {
      setEvidencePack(response);
      setEvidenceOpen(true);
    }
  });

  const exportEvidence = useMutation({
    mutationFn: ({ approvalId, format }: { approvalId: string; format: "json" | "csv" }) =>
      exportRetentionEvidencePack(approvalId, format),
    onSuccess: (response) => {
      downloadTextFile(response.filename, response.contentType, response.content);
    }
  });

  function applyApprovalQueueFilters() {
    setApprovalQueueFilters({
      ...draftApprovalQueueFilters,
      tenantId: draftApprovalQueueFilters.scopeType === "GLOBAL" ? undefined : draftApprovalQueueFilters.tenantId?.trim(),
      applicationId: draftApprovalQueueFilters.scopeType === "GLOBAL" ? undefined : draftApprovalQueueFilters.applicationId?.trim(),
      approvalId: draftApprovalQueueFilters.approvalId?.trim(),
      dryRunId: draftApprovalQueueFilters.dryRunId?.trim(),
      policyId: draftApprovalQueueFilters.policyId?.trim(),
      changeTicket: draftApprovalQueueFilters.changeTicket?.trim(),
      requestedBy: draftApprovalQueueFilters.requestedBy?.trim(),
      approvedBy: draftApprovalQueueFilters.approvedBy?.trim(),
      executedBy: draftApprovalQueueFilters.executedBy?.trim(),
      from: toIsoDateTime(draftApprovalQueueFilters.from),
      to: toIsoDateTime(draftApprovalQueueFilters.to),
      limit: draftApprovalQueueFilters.limit ?? 50
    });
  }

  function loadApprovalFromQueue(item: RetentionApproval) {
    setApproval(item);
    setApprovalId(item.approvalId);
    setExecution(null);
    setExecutionAttemptBlocked(false);
    setScope((current) => ({
      ...current,
      tenantId: item.tenantId ?? "",
      applicationId: item.applicationId ?? "",
      policyId: item.policyId,
      retentionDays: String(item.retentionDays),
      batchLimit: String(item.batchLimit)
    }));
    setApprovalForm((current) => ({
      ...current,
      restoreDrillRef: item.restoreDrillRef,
      changeTicket: item.changeTicket,
      reason: item.reason || current.reason
    }));
    setRestoreLookup(item.restoreDrillRef);
    setDecisionNote(item.note ?? "");
  }

  const executable = selectedPolicy?.destructiveExecutionSupported && selectedPolicy.policyId === executableRetentionPolicy;
  const canRequestApproval = Boolean(
    dryRun &&
      selectedResult &&
      executable &&
      !dryRunScopeChanged &&
      !dryRunIsExpired &&
      restoreReady &&
      approvalForm.restoreDrillRef.trim() &&
      approvalForm.reason.trim() &&
      approvalForm.changeTicket.trim()
  );
  const executionReady = Boolean(
    canExecuteApproval &&
      executionForm.confirm &&
      executionForm.idempotencyKey.trim() &&
      executionForm.correlationId.trim()
  );

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Retention operations"
        title="Retention console"
        description="Luồng vận hành dry-run, restore drill, approval hai người và execution có audit cho promotion retention."
      />
      <IncentiveNav />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Policies"
          value={policies.data?.policies.length ?? "—"}
          detail="Registry retention policy hiện có trong promotion-service."
          icon={<ClipboardCheck size={18} />}
          tone="brand"
        />
        <StatCard
          label="Eligible"
          value={selectedResult ? selectedResult.eligibleCount.toLocaleString() : "—"}
          detail={selectedResult ? `Blocked ${selectedResult.blockedCount.toLocaleString()}` : "Chưa có dry-run."}
          icon={<FileJson2 size={18} />}
          tone="info"
        />
        <StatCard
          label="Approval"
          value={approval ? statusLabel(approval.status) : "—"}
          detail={approval ? compactId(approval.approvalId) : "Chưa có approval được chọn."}
          icon={<ShieldCheck size={18} />}
          tone={approvalReady(approval) ? "success" : approval?.status === "EXECUTION_FAILED" ? "danger" : "warning"}
        />
        <StatCard
          label="Execution"
          value={execution ? statusLabel(execution.status) : "—"}
          detail={execution ? `${execution.redactedCount}/${execution.eligibleBefore} redacted` : "Chưa execute."}
          icon={<Send size={18} />}
          tone={execution?.status === "SUCCEEDED" ? "success" : "neutral"}
        />
      </div>

      <Card>
        <CardHeader
          title="Retention approval queue"
          subtitle="Reviewer/operator queue cho approval destructive retention; chỉ hiển thị aggregate count, hash và audit identifiers."
          actions={
            <Button variant="secondary" onClick={() => approvalQueue.refetch()} disabled={!approvalQueueEnabled || approvalQueue.isFetching}>
              <RefreshCcw size={16} />
              Refresh
            </Button>
          }
        />
        <div className="grid gap-4 p-4">
          <Toolbar>
            <FormField label="Scope">
              <Select
                value={draftApprovalQueueFilters.scopeType ?? "APPLICATION"}
                onChange={(event) => {
                  const scopeType = event.target.value as RetentionApprovalFilters["scopeType"];
                  setDraftApprovalQueueFilters({
                    ...draftApprovalQueueFilters,
                    scopeType,
                    tenantId: scopeType === "GLOBAL" ? undefined : (draftApprovalQueueFilters.tenantId ?? scope.tenantId),
                    applicationId: scopeType === "GLOBAL" ? undefined : (draftApprovalQueueFilters.applicationId ?? scope.applicationId)
                  });
                }}
              >
                <option value="APPLICATION">Application</option>
                <option value="GLOBAL">Global</option>
              </Select>
            </FormField>
            <FormField label="Tenant">
              <Input
                value={draftApprovalQueueFilters.tenantId ?? ""}
                disabled={draftApprovalQueueFilters.scopeType === "GLOBAL"}
                onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, tenantId: event.target.value })}
              />
            </FormField>
            <FormField label="Application">
              <Input
                value={draftApprovalQueueFilters.applicationId ?? ""}
                disabled={draftApprovalQueueFilters.scopeType === "GLOBAL"}
                onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, applicationId: event.target.value })}
              />
            </FormField>
            <FormField label="Status">
              <Select value={draftApprovalQueueFilters.status ?? ""} onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, status: event.target.value || undefined })}>
                <option value="">All</option>
                <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
                <option value="APPROVED">APPROVED</option>
                <option value="REJECTED">REJECTED</option>
                <option value="EXECUTED">EXECUTED</option>
                <option value="EXECUTION_FAILED">EXECUTION_FAILED</option>
              </Select>
            </FormField>
            <FormField label="Expired">
              <Select
                value={draftApprovalQueueFilters.expired === undefined ? "" : String(draftApprovalQueueFilters.expired)}
                onChange={(event) =>
                  setDraftApprovalQueueFilters({
                    ...draftApprovalQueueFilters,
                    expired: event.target.value === "" ? undefined : event.target.value === "true"
                  })
                }
              >
                <option value="">All</option>
                <option value="false">Not expired</option>
                <option value="true">Expired</option>
              </Select>
            </FormField>
            <FormField label="Change ticket">
              <Input value={draftApprovalQueueFilters.changeTicket ?? ""} onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, changeTicket: event.target.value })} />
            </FormField>
            <FormField label="Requested by">
              <Input value={draftApprovalQueueFilters.requestedBy ?? ""} onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, requestedBy: event.target.value })} />
            </FormField>
            <FormField label="Approval ID">
              <Input value={draftApprovalQueueFilters.approvalId ?? ""} onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, approvalId: event.target.value })} />
            </FormField>
            <FormField label="Dry-run ID">
              <Input value={draftApprovalQueueFilters.dryRunId ?? ""} onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, dryRunId: event.target.value })} />
            </FormField>
            <FormField label="From">
              <Input type="datetime-local" value={draftApprovalQueueFilters.from ?? ""} onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, from: event.target.value })} />
            </FormField>
            <FormField label="To">
              <Input type="datetime-local" value={draftApprovalQueueFilters.to ?? ""} onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, to: event.target.value })} />
            </FormField>
            <FormField label="Limit">
              <Input
                value={String(draftApprovalQueueFilters.limit ?? 50)}
                inputMode="numeric"
                onChange={(event) => setDraftApprovalQueueFilters({ ...draftApprovalQueueFilters, limit: toNumberOrUndefined(event.target.value) })}
              />
            </FormField>
            <FilterActions>
              <Button onClick={applyApprovalQueueFilters}>
                <Search size={16} />
                Apply
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  const next: RetentionApprovalFilters = {
                    scopeType: "APPLICATION",
                    tenantId: scope.tenantId || "courseflow",
                    applicationId: scope.applicationId || "lms",
                    status: "PENDING_APPROVAL",
                    expired: false,
                    limit: 50
                  };
                  setDraftApprovalQueueFilters(next);
                  setApprovalQueueFilters(next);
                }}
              >
                Reset
              </Button>
            </FilterActions>
          </Toolbar>
          {!approvalQueueEnabled && (
            <Notice tone="warning" title="Queue scope required">
              Application scope cần đủ tenant và application. Global scope chỉ trả approval không gắn application.
            </Notice>
          )}
          {approvalQueue.isLoading && <Spinner />}
          {approvalQueue.isError && <ErrorState error={approvalQueue.error} />}
          {viewEvidence.isError && <ErrorState error={viewEvidence.error} />}
          {exportEvidence.isError && <ErrorState error={exportEvidence.error} />}
          {approvalQueue.data?.hasMore && (
            <Notice tone="warning" title="Result limited">
              Còn approval ngoài limit hiện tại. Thu hẹp filter hoặc tăng limit tối đa 200.
            </Notice>
          )}
          {approvalQueue.data && approvalQueueItems.length === 0 && <EmptyState message="Không có retention approval phù hợp." />}
          {approvalQueueItems.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Status</Th>
                  <Th>Approval</Th>
                  <Th>Scope / Policy</Th>
                  <Th>Counts</Th>
                  <Th>Dry-run / Hash</Th>
                  <Th>Ticket / Actors</Th>
                  <Th>Expires</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {approvalQueueItems.map((item) => {
                  const signal = retentionApprovalSignal(item, user);
                  return (
                    <tr key={item.approvalId} className="hover:bg-slate-50">
                      <Td>
                        <div className="flex flex-col gap-1">
                          <StatusPill value={item.status} />
                          <Badge label={signal.label} tone={signal.tone} />
                        </div>
                      </Td>
                      <Td>
                        <button type="button" className="font-mono text-xs font-semibold text-brand-700" onClick={() => copyText(item.approvalId)}>
                          {compactId(item.approvalId)}
                        </button>
                        <p className="mt-1 text-xs text-slate-400">{formatDateTime(item.createdAt)}</p>
                      </Td>
                      <Td>
                        <p className="font-semibold text-slate-900">{item.tenantId && item.applicationId ? `${item.tenantId}/${item.applicationId}` : "GLOBAL"}</p>
                        <p className="mt-1 text-xs text-slate-500">{item.policyId}</p>
                        <p className="mt-1 text-xs text-slate-400">{item.targetDataset}</p>
                      </Td>
                      <Td>
                        <p>{item.eligibleCount.toLocaleString()} eligible</p>
                        <p className="mt-1 text-xs text-slate-400">batch {item.batchLimit.toLocaleString()} · {item.retentionDays} days</p>
                      </Td>
                      <Td>
                        <button type="button" className="font-mono text-xs font-semibold text-brand-700" onClick={() => copyText(item.dryRunId)}>
                          {compactId(item.dryRunId)}
                        </button>
                        <p className="mt-1 font-mono text-xs text-slate-400">{compactId(item.approvedResultHash)}</p>
                      </Td>
                      <Td>
                        <p className="font-semibold text-slate-900">{item.changeTicket}</p>
                        <p className="mt-1 line-clamp-2 text-xs text-slate-500">{item.reason}</p>
                        <p className="mt-1 text-xs text-slate-400">req {item.requestedBy ?? "-"} · app {item.approvedBy ?? "-"}</p>
                      </Td>
                      <Td>
                        <p>{formatDateTime(item.expiresAt)}</p>
                        <p className="mt-1 text-xs text-slate-400">cutoff {formatDateTime(item.cutoff)}</p>
                      </Td>
                      <Td>
                        <div className="flex flex-wrap justify-end gap-2">
                          <Button size="xs" variant="secondary" onClick={() => loadApprovalFromQueue(item)}>
                            Load
                          </Button>
                          <Button
                            size="xs"
                            variant="secondary"
                            disabled={viewEvidence.isPending}
                            onClick={() => viewEvidence.mutate({ approvalId: item.approvalId })}
                          >
                            <FileJson2 size={14} />
                            Evidence
                          </Button>
                          <Button
                            size="xs"
                            variant="secondary"
                            disabled={exportEvidence.isPending && exportEvidence.variables?.approvalId === item.approvalId}
                            onClick={() => exportEvidence.mutate({ approvalId: item.approvalId, format: "json" })}
                          >
                            <FileDown size={14} />
                            JSON
                          </Button>
                          <Button
                            size="xs"
                            variant="secondary"
                            disabled={exportEvidence.isPending && exportEvidence.variables?.approvalId === item.approvalId}
                            onClick={() => exportEvidence.mutate({ approvalId: item.approvalId, format: "csv" })}
                          >
                            CSV
                          </Button>
                          <Button size="xs" variant="secondary" onClick={() => copyText(item.correlationId)}>
                            Copy corr
                          </Button>
                        </div>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader
          title="1. Policy và dry-run"
          subtitle="Dry-run chỉ trả aggregate count/hash; không hiển thị row id hay payload nhạy cảm."
          actions={
            <Button onClick={() => dryRunMutation.mutate()} disabled={dryRunMutation.isPending || !scope.policyId}>
              <RefreshCcw size={16} />
              {dryRunMutation.isPending ? "Đang chạy" : "Run dry-run"}
            </Button>
          }
        />
        <div className="grid gap-4 p-4">
          <Toolbar>
            <FormField label="Tenant">
              <Input value={scope.tenantId} onChange={(event) => setScope({ ...scope, tenantId: event.target.value })} />
            </FormField>
            <FormField label="Application">
              <Input value={scope.applicationId} onChange={(event) => setScope({ ...scope, applicationId: event.target.value })} />
            </FormField>
            <FormField label="Policy">
              <Select value={scope.policyId} onChange={(event) => setScope({ ...scope, policyId: event.target.value })}>
                {(policies.data?.policies ?? []).map((policy) => (
                  <option key={policy.policyId} value={policy.policyId}>
                    {policy.policyId}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Retention days">
              <Input
                value={scope.retentionDays}
                placeholder={selectedPolicy ? String(selectedPolicy.defaultRetentionDays) : ""}
                inputMode="numeric"
                onChange={(event) => setScope({ ...scope, retentionDays: event.target.value })}
              />
            </FormField>
            <FormField label="Batch limit">
              <Input value={scope.batchLimit} inputMode="numeric" onChange={(event) => setScope({ ...scope, batchLimit: event.target.value })} />
            </FormField>
          </Toolbar>
          <FormField label="Reason">
            <Input value={scope.reason} onChange={(event) => setScope({ ...scope, reason: event.target.value })} />
          </FormField>
          {selectedPolicy && (
            <Notice tone={executable ? "warning" : "info"} title={selectedPolicy.targetDataset}>
              {selectedPolicy.eligibleWhen || "Retention policy"} · min {selectedPolicy.minimumRetentionDays} days · default batch{" "}
              {selectedPolicy.defaultBatchLimit}
            </Notice>
          )}
          {dryRun && (
            <Notice tone={!dryRunScopeChanged && !dryRunIsExpired ? "success" : "warning"} title="Dry-run freshness gate">
              {!dryRunScopeChanged && !dryRunIsExpired
                ? `Dry-run còn hiệu lực tới ${dryRunExpiry ? formatDateTime(new Date(dryRunExpiry).toISOString()) : "N/A"}.`
                : [
                    dryRunScopeChanged ? "Scope/batch/retention input đã đổi sau dry-run." : null,
                    dryRunIsExpired ? `Dry-run quá ${retentionDryRunTtlMinutes} phút.` : null
                  ]
                    .filter(Boolean)
                    .join(" ")}
            </Notice>
          )}
          {dryRunMutation.isError && <RetentionServerGateErrorNotice error={dryRunMutation.error} title="Retention dry-run server gate" />}
          <RetentionResultTable dryRun={dryRun} />
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader title="2. Restore drill evidence" subtitle="Execution chỉ được duyệt khi có restore drill PASSED cho cf_promotion." />
          <div className="border-b border-slate-100 p-4">
            <Toolbar className="items-stretch">
              <FormField label="Evidence JSON" className="min-w-[260px] flex-1">
                <Textarea
                  className="min-h-20 font-mono text-xs"
                  value={restoreEvidenceText}
                  onChange={(event) => setRestoreEvidenceText(event.target.value)}
                />
              </FormField>
              <FilterActions>
                <label className="inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700">
                  <Upload size={16} />
                  Upload JSON
                  <input
                    type="file"
                    accept="application/json,.json"
                    className="sr-only"
                    onChange={(event) => {
                      void handleRestoreEvidenceFile(event.target.files?.[0]);
                      event.currentTarget.value = "";
                    }}
                  />
                </label>
                <Button
                  variant="secondary"
                  onClick={() => applyRestoreEvidence(restoreEvidenceText)}
                  disabled={!restoreEvidenceText.trim()}
                >
                  <FileJson2 size={16} />
                  Apply evidence
                </Button>
              </FilterActions>
            </Toolbar>
            {restoreEvidenceError && (
              <Notice tone="danger" title="Restore evidence rejected" className="mt-3">
                {restoreEvidenceError}
              </Notice>
            )}
          </div>
          <form
            className="grid gap-3 p-4"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              registerDrill.mutate();
            }}
          >
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Drill ref" required>
                <Input value={restoreForm.restoreDrillRef} onChange={(event) => setRestoreForm({ ...restoreForm, restoreDrillRef: event.target.value })} />
              </FormField>
              <FormField label="Database" required>
                <Input value={restoreForm.databaseName} onChange={(event) => setRestoreForm({ ...restoreForm, databaseName: event.target.value })} />
              </FormField>
            </div>
            <FormField label="Backup path" required>
              <Input value={restoreForm.backupPath} onChange={(event) => setRestoreForm({ ...restoreForm, backupPath: event.target.value })} />
            </FormField>
            <FormField label="Artifact hash" required hint="sha256:<64-hex>">
              <Input value={restoreForm.artifactHash} onChange={(event) => setRestoreForm({ ...restoreForm, artifactHash: event.target.value })} />
            </FormField>
            <div className="grid gap-3 md:grid-cols-3">
              <FormField label="Status">
                <Select value={restoreForm.status} onChange={(event) => setRestoreForm({ ...restoreForm, status: event.target.value })}>
                  <option value="PASSED">PASSED</option>
                  <option value="FAILED">FAILED</option>
                </Select>
              </FormField>
              <FormField label="Checked at">
                <Input type="datetime-local" value={restoreForm.checkedAt} onChange={(event) => setRestoreForm({ ...restoreForm, checkedAt: event.target.value })} />
              </FormField>
              <FormField label="Expires at">
                <Input type="datetime-local" value={restoreForm.expiresAt} onChange={(event) => setRestoreForm({ ...restoreForm, expiresAt: event.target.value })} />
              </FormField>
            </div>
            <FormField label="Note">
              <Textarea value={restoreForm.note} onChange={(event) => setRestoreForm({ ...restoreForm, note: event.target.value })} />
            </FormField>
            {restoreFormReadiness.length > 0 && (
              <Notice tone="neutral" title="Restore drill form readiness">
                {restoreFormReadiness.join(" ")}
              </Notice>
            )}
            {registerDrill.isError && <RetentionServerGateErrorNotice error={registerDrill.error} title="Restore drill server gate" />}
            {registerDrill.data && (
              <Notice tone="success" title="Restore drill registered">
                {registerDrill.data.restoreDrillRef} · expires {formatDateTime(registerDrill.data.expiresAt)}
              </Notice>
            )}
            <Button type="submit" disabled={registerDrill.isPending || restoreFormReadiness.length > 0}>
              {registerDrill.isPending ? "Đang lưu" : "Register restore drill"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title="3. Approval workflow" subtitle="Approval là nguồn sự thật cho execution; không execute từ body proof cũ." />
          <div className="grid gap-4 p-4">
            <Toolbar>
              <FormField label="Lookup approval ID">
                <Input value={approvalId} onChange={(event) => setApprovalId(event.target.value)} />
              </FormField>
              <FilterActions>
                <Button variant="secondary" onClick={() => approvalLookup.refetch()} disabled={!approvalId.trim()}>
                  <Search size={16} />
                  Load
                </Button>
              </FilterActions>
            </Toolbar>
            <div className="grid gap-3 md:grid-cols-3">
              <FormField label="Restore drill ref" required>
                <Input value={approvalForm.restoreDrillRef} onChange={(event) => setApprovalForm({ ...approvalForm, restoreDrillRef: event.target.value })} />
              </FormField>
              <FormField label="Change ticket" required>
                <Input value={approvalForm.changeTicket} onChange={(event) => setApprovalForm({ ...approvalForm, changeTicket: event.target.value })} />
              </FormField>
              <FormField label="Reason" required>
                <Input value={approvalForm.reason} onChange={(event) => setApprovalForm({ ...approvalForm, reason: event.target.value })} />
              </FormField>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => requestApproval.mutate()} disabled={!canRequestApproval || requestApproval.isPending}>
                <ShieldCheck size={16} />
                {requestApproval.isPending ? "Đang gửi" : "Request approval"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => setRestoreLookup(approvalForm.restoreDrillRef.trim())}
                disabled={!approvalForm.restoreDrillRef.trim()}
              >
                Check drill
              </Button>
            </div>
            {approvalForm.restoreDrillRef.trim() && (
              <Notice tone={restoreReady ? "success" : "warning"} title="Restore drill approval gate">
                {restoreReady ? "Restore drill đã pass, đúng database, hash hợp lệ và chưa hết hạn." : restoreGateIssues.join(" ")}
              </Notice>
            )}
            {dryRun && (dryRunScopeChanged || dryRunIsExpired) && (
              <Notice tone="warning" title="Approval request blocked">
                Chạy lại dry-run trước khi request approval để reviewer duyệt đúng candidate snapshot hiện tại.
              </Notice>
            )}
            {requestApproval.isError && <RetentionServerGateErrorNotice error={requestApproval.error} title="Retention approval request server gate" />}
            {approvalLookup.isError && <RetentionServerGateErrorNotice error={approvalLookup.error} title="Retention approval lookup server gate" />}
            {activeRestoreDrill && (
              <div className="grid gap-3 rounded-md border border-slate-200 p-3 md:grid-cols-3">
                <KeyValue label="Drill status" value={<StatusPill value={activeRestoreDrill.status} />} />
                <KeyValue label="Database" value={activeRestoreDrill.databaseName} />
                <KeyValue label="Expires" value={formatDateTime(activeRestoreDrill.expiresAt)} />
              </div>
            )}
            {approval && (
              <div className="grid gap-3 rounded-md border border-slate-200 p-3 md:grid-cols-4">
                <KeyValue label="Approval" value={compactId(approval.approvalId)} mono />
                <KeyValue label="Status" value={<StatusPill value={approval.status} />} />
                <KeyValue label="Expires" value={formatDateTime(approval.expiresAt)} />
                <KeyValue label="Eligible" value={approval.eligibleCount.toLocaleString()} />
                <KeyValue label="Requested by" value={approval.requestedBy ?? "-"} />
                <KeyValue label="Approved by" value={approval.approvedBy ?? "-"} />
                <KeyValue label="Executed by" value={approval.executedBy ?? "-"} />
                <KeyValue label="Dry-run" value={compactId(approval.dryRunId)} mono />
              </div>
            )}
            {approval?.status === "EXECUTION_FAILED" && (
              <Notice tone="danger" title="Execution failed">
                Không retry mù. Kiểm tra audit/correlation, restore evidence và chạy lại dry-run/approval sau khi remediation.
              </Notice>
            )}
            {approval && !canDecideApproval && (
              <Notice tone="neutral" title="Reviewer gate">
                <GateIssues issues={decisionIssues} />
              </Notice>
            )}
            <FormField label="Reviewer note">
              <Textarea value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)} />
            </FormField>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => approve.mutate()}
                disabled={!canDecideApproval || approve.isPending}
                title={gateIssueTitle(decisionIssues)}
              >
                <CheckCircle2 size={16} />
                Approve
              </Button>
              <Button
                variant="danger"
                onClick={() => reject.mutate()}
                disabled={!canDecideApproval || reject.isPending}
                title={gateIssueTitle(decisionIssues)}
              >
                <XCircle size={16} />
                Reject
              </Button>
            </div>
            {(approve.isError || reject.isError) && (
              <RetentionServerGateErrorNotice error={approve.error ?? reject.error} title="Retention reviewer server gate" />
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader title="4. Execution gate" subtitle="Chỉ chạy khi approval APPROVED, confirm=true và idempotency key ổn định." />
          <div className="grid gap-4 p-4">
            <Notice tone={approvalReady(approval) ? "warning" : "neutral"} title="Execution readiness">
              {canExecuteApproval
                ? "Approval đã sẵn sàng. Correlation ID và idempotency key sẽ được dùng để truy audit."
                : (
                  <GateIssues issues={executionGateIssues} />
                )}
            </Notice>
            <div className="grid gap-3 md:grid-cols-2">
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
            </div>
            <div className="flex flex-wrap gap-2">
              {checkboxLabel("Confirm destructive execution", executionForm.confirm, (checked) => setExecutionForm({ ...executionForm, confirm: checked }))}
              <Button variant="secondary" onClick={() => copyText(executionForm.correlationId)}>
                Copy correlation
              </Button>
              <Button variant="secondary" onClick={() => approvalLookup.refetch()} disabled={!approval?.approvalId || approvalLookup.isFetching}>
                <RefreshCcw size={16} />
                Reload approval
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  setExecutionForm({
                    idempotencyKey: retentionOperationId("retention-exec"),
                    correlationId: retentionOperationId("corr-retention-exec"),
                    confirm: false
                  })
                }
              >
                New attempt key
              </Button>
            </div>
            <Button
              variant="danger"
              disabled={!executionReady || execute.isPending}
              title={!canExecuteApproval ? gateIssueTitle(executionGateIssues) : undefined}
              onClick={() => setExecuteOpen(true)}
            >
              <Send size={16} />
              Execute retention
            </Button>
            {execute.isError && <RetentionServerGateErrorNotice error={execute.error} title="Retention execution server gate" />}
            {execution && (
              <Notice tone={execution.idempotencyReplay ? "info" : "success"} title={execution.idempotencyReplay ? "Idempotency replay" : "Execution completed"}>
                {execution.redactedCount.toLocaleString()} / {execution.eligibleBefore.toLocaleString()} redacted · {execution.hasMore ? "has more candidates" : "batch complete"}
              </Notice>
            )}
            {execution?.hasMore && (
              <Notice tone="warning" title="More candidates remain">
                Chạy batch tiếp theo bằng dry-run và approval mới; không reuse approval cũ để xử lý phần còn lại.
              </Notice>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="5. Audit evidence" subtitle="Theo dõi actor/action/correlation cho approval và execution." />
          <div className="grid gap-4 p-4 xl:grid-cols-2">
            <div className="rounded-md border border-slate-200">
              <div className="border-b border-slate-200 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">Approval audit</p>
                <p className="mt-1 text-xs text-slate-500">{approval?.approvalId ? compactId(approval.approvalId) : "Recent retention activity"}</p>
              </div>
              {audit.isLoading && <Spinner />}
              {audit.isError && <ErrorState error={audit.error} />}
              {audit.data && <Timeline events={audit.data.items} />}
            </div>
            <div className="rounded-md border border-slate-200">
              <div className="border-b border-slate-200 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">Execution correlation audit</p>
                <p className="mt-1 break-words font-mono text-xs text-slate-500">
                  {executionForm.correlationId.trim() || "Correlation ID is required before execution."}
                </p>
              </div>
              {executionAudit.isLoading && <Spinner />}
              {executionAudit.isError && <ErrorState error={executionAudit.error} />}
              {executionAudit.data ? <Timeline events={executionAudit.data.items} /> : <EmptyState message="Nhập correlation ID để truy execution audit." />}
            </div>
          </div>
        </Card>
      </div>

      <ConfirmDialog
        open={executeOpen}
        onOpenChange={setExecuteOpen}
        title="Execute destructive retention"
        description="Backend sẽ chỉ dùng approvalId đã duyệt làm nguồn sự thật. Hãy chắc chắn restore drill và change ticket đã được reviewer kiểm tra."
        confirmLabel="Execute"
        tone="danger"
        isPending={execute.isPending}
        onConfirm={() => {
          if (!executionReady) {
            setExecuteOpen(false);
            return;
          }
          execute.mutate();
        }}
      >
        <div className="grid gap-3">
          <KeyValue label="Approval" value={compactId(approval?.approvalId)} mono />
          <KeyValue label="Idempotency key" value={executionForm.idempotencyKey} mono />
          <KeyValue label="Correlation" value={executionForm.correlationId} mono />
        </div>
      </ConfirmDialog>

      <Drawer
        open={evidenceOpen}
        onOpenChange={setEvidenceOpen}
        title="Evidence pack"
        description={evidencePack ? compactId(evidencePack.approvalId) : "Retention evidence"}
        className="max-w-4xl"
        footer={
          evidencePack && (
            <div className="flex flex-wrap justify-end gap-2">
              <Button
                variant="secondary"
                disabled={exportEvidence.isPending}
                onClick={() => exportEvidence.mutate({ approvalId: evidencePack.approvalId, format: "json" })}
              >
                <FileDown size={16} />
                Export JSON
              </Button>
              <Button
                variant="secondary"
                disabled={exportEvidence.isPending}
                onClick={() => exportEvidence.mutate({ approvalId: evidencePack.approvalId, format: "csv" })}
              >
                Export CSV
              </Button>
            </div>
          )
        }
      >
        {!evidencePack && <EmptyState message="Chọn một approval để xem evidence pack." />}
        {evidencePack && (
          <div className="grid gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill value={evidencePack.approval.status} />
              <Badge
                label={
                  evidencePack.execution
                    ? evidencePack.approval.status === "EXECUTION_FAILED"
                      ? "Failed evidence"
                      : "Complete evidence"
                    : "Incomplete evidence"
                }
                tone={evidencePack.execution ? (evidencePack.approval.status === "EXECUTION_FAILED" ? "danger" : "success") : "warning"}
              />
              <Badge label={evidencePack.schemaVersion} tone="info" />
            </div>
            {evidencePack.warnings.length > 0 && (
              <Notice tone="warning" title="Evidence warnings">
                {evidencePack.warnings.join(" ")}
              </Notice>
            )}
            <div className="grid gap-3 rounded-md border border-slate-200 p-3 md:grid-cols-3">
              <KeyValue label="Approval" value={compactId(evidencePack.approval.approvalId)} mono />
              <KeyValue label="Scope" value={evidencePack.approval.tenantId && evidencePack.approval.applicationId ? `${evidencePack.approval.tenantId}/${evidencePack.approval.applicationId}` : "GLOBAL"} />
              <KeyValue label="Generated" value={formatDateTime(evidencePack.generatedAt)} />
              <KeyValue label="Policy" value={`${evidencePack.approval.policyId} · ${evidencePack.approval.policyVersion}`} />
              <KeyValue label="Eligible / Batch" value={`${evidencePack.approval.eligibleCount.toLocaleString()} / ${evidencePack.approval.batchLimit.toLocaleString()}`} />
              <KeyValue label="Retention days" value={evidencePack.approval.retentionDays.toLocaleString()} />
              <KeyValue label="As of" value={formatDateTime(evidencePack.approval.asOf)} />
              <KeyValue label="Cutoff" value={formatDateTime(evidencePack.approval.cutoff)} />
              <KeyValue label="Expires" value={formatDateTime(evidencePack.approval.expiresAt)} />
              <KeyValue label="Dry-run" value={compactId(evidencePack.approval.dryRunId)} mono />
              <KeyValue label="Result hash" value={compactId(evidencePack.approval.approvedResultHash)} mono />
              <KeyValue label="Change ticket" value={evidencePack.approval.changeTicket} />
              <KeyValue label="Requested by" value={evidencePack.approval.requestedBy ?? "-"} />
              <KeyValue label="Approved by" value={evidencePack.approval.approvedBy ?? "-"} />
              <KeyValue label="Executed by" value={evidencePack.approval.executedBy ?? "-"} />
            </div>

            <div className="rounded-md border border-slate-200 p-3">
              <p className="text-sm font-semibold text-slate-900">Restore drill</p>
              {evidencePack.restoreDrill ? (
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <KeyValue label="Ref" value={evidencePack.restoreDrill.restoreDrillRef} mono />
                  <KeyValue label="Database" value={evidencePack.restoreDrill.databaseName} />
                  <KeyValue label="Status" value={<StatusPill value={evidencePack.restoreDrill.status} />} />
                  <KeyValue label="Artifact hash" value={compactId(evidencePack.restoreDrill.artifactHash)} mono />
                  <KeyValue label="Checked" value={formatDateTime(evidencePack.restoreDrill.checkedAt)} />
                  <KeyValue label="Expires" value={formatDateTime(evidencePack.restoreDrill.expiresAt)} />
                </div>
              ) : (
                <EmptyState message="Restore drill evidence không còn trong registry." />
              )}
            </div>

            <div className="rounded-md border border-slate-200 p-3">
              <p className="text-sm font-semibold text-slate-900">Execution</p>
              {evidencePack.execution ? (
                <div className="mt-3 grid gap-3 md:grid-cols-3">
                  <KeyValue label="Execution" value={compactId(evidencePack.execution.executionId)} mono />
                  <KeyValue label="Status" value={<StatusPill value={evidencePack.execution.status} />} />
                  <KeyValue label="Rows" value={`${evidencePack.execution.redactedCount.toLocaleString()} / ${evidencePack.execution.expectedEligibleCount.toLocaleString()}`} />
                  <KeyValue label="Has more" value={evidencePack.execution.hasMore === null || evidencePack.execution.hasMore === undefined ? "-" : String(evidencePack.execution.hasMore)} />
                  <KeyValue label="Idempotency hash" value={compactId(evidencePack.execution.idempotencyKeyHash)} mono />
                  <KeyValue label="Correlation" value={evidencePack.execution.correlationId ?? "-"} mono />
                  <KeyValue label="Started" value={formatDateTime(evidencePack.execution.startedAt)} />
                  <KeyValue label="Completed" value={formatDateTime(evidencePack.execution.completedAt)} />
                  <KeyValue label="Last error" value={evidencePack.execution.lastError ?? "-"} />
                </div>
              ) : (
                <EmptyState message="Approval này chưa có execution operation." />
              )}
            </div>

            <div className="rounded-md border border-slate-200">
              <div className="border-b border-slate-200 px-3 py-2">
                <p className="text-sm font-semibold text-slate-900">Audit trail</p>
              </div>
              {evidencePack.auditTrail.length === 0 ? (
                <EmptyState message="Chưa có audit event phù hợp trong evidence pack." />
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <Th>Action</Th>
                      <Th>Actor</Th>
                      <Th>Correlation</Th>
                      <Th>Created</Th>
                      <Th>Payload summary</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {evidencePack.auditTrail.map((event) => (
                      <tr key={event.eventId}>
                        <Td>
                          <p className="font-semibold text-slate-900">{event.action}</p>
                          <p className="mt-1 text-xs text-slate-400">{event.aggregateType} · {compactId(event.aggregateId)}</p>
                        </Td>
                        <Td>{event.actorId ?? "-"}</Td>
                        <Td><span className="font-mono text-xs">{compactId(event.correlationId)}</span></Td>
                        <Td>{formatDateTime(event.createdAt)}</Td>
                        <Td><JsonBlock value={event.payloadSummary} className="max-h-32" /></Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

export function ApplicationRegistryPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ApplicationFilters>({});
  const [draftFilters, setDraftFilters] = useState<ApplicationFilters>({});
  const [form, setForm] = useState({
    tenantId: "courseflow",
    applicationId: "lms",
    name: "CourseFlow LMS",
    status: "ACTIVE",
    allowedClientIds: "courseflow-admin-web, courseflow-learn-web"
  });
  const [bindingTarget, setBindingTarget] = useState<string | null>(null);
  const [bindingForm, setBindingForm] = useState({
    clientId: "",
    status: "ACTIVE",
    allowedOperations: "evaluate,reserve,commit,cancel,reverse"
  });

  const applications = useQuery({
    queryKey: queryKeys.incentives.applications(filters),
    queryFn: () => listApplications(filters),
    retry: 1
  });

  const create = useMutation({
    mutationFn: () =>
      createApplication({
        tenantId: form.tenantId.trim(),
        applicationId: form.applicationId.trim(),
        name: form.name.trim(),
        status: form.status,
        allowedClientIds: splitCommaList(form.allowedClientIds)
      }),
    onSuccess: () => invalidateIncentives(queryClient)
  });

  const binding = useMutation({
    mutationFn: () => {
      if (!bindingTarget) throw new Error("Chưa chọn application");
      return upsertApplicationClientBinding(bindingTarget, {
        clientId: bindingForm.clientId.trim(),
        status: bindingForm.status,
        allowedOperations: splitCommaList(bindingForm.allowedOperations)
      });
    },
    onSuccess: () => {
      setBindingTarget(null);
      invalidateIncentives(queryClient);
    }
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Application registry"
        description="Quản lý tenant/application và client binding được phép dùng incentive platform."
      />
      <IncentiveNav />

      <Toolbar>
        <FormField label="Tenant">
          <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
        </FormField>
        <FormField label="Application">
          <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
        </FormField>
        <FormField label="Status">
          <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value || undefined })}>
            <option value="">Tất cả</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="SUSPENDED">SUSPENDED</option>
            <option value="DISABLED">DISABLED</option>
          </Select>
        </FormField>
        <FilterActions>
          <Button onClick={() => setFilters(draftFilters)}>
            <Search size={16} />
            Lọc
          </Button>
          <Button variant="secondary" onClick={() => { setDraftFilters({}); setFilters({}); }}>
            Xóa
          </Button>
        </FilterActions>
      </Toolbar>

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader title="Applications" subtitle="Mỗi application là một boundary rõ cho policy, client binding và audit." />
          {applications.isLoading && <Spinner />}
          {applications.isError && <ErrorState error={applications.error} />}
          {applications.data?.length === 0 && <EmptyState message="Chưa có application phù hợp." />}
          {applications.data && applications.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Application</Th>
                  <Th>Tenant</Th>
                  <Th>Status</Th>
                  <Th>Client bindings</Th>
                  <Th>Action</Th>
                </tr>
              </thead>
              <tbody>
                {applications.data.map((application) => (
                  <tr key={application.id} className="hover:bg-slate-50">
                    <Td>
                      <p className="font-semibold text-slate-900">{application.name}</p>
                      <p className="mt-1 font-mono text-xs text-slate-400">{application.applicationId}</p>
                    </Td>
                    <Td>{application.tenantId}</Td>
                    <Td>
                      <StatusPill value={application.status} />
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1.5">
                        {(application.clientBindings ?? []).slice(0, 3).map((item) => (
                          <Badge key={item.id} value="CLIENT" label={item.clientId} tone="slate" />
                        ))}
                        {(application.clientBindings?.length ?? 0) > 3 && (
                          <Badge value="MORE" label={`+${(application.clientBindings?.length ?? 0) - 3}`} tone="neutral" />
                        )}
                      </div>
                    </Td>
                    <Td>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setBindingTarget(application.id);
                          setBindingForm({
                            clientId: application.clientBindings?.[0]?.clientId ?? "",
                            status: application.clientBindings?.[0]?.status ?? "ACTIVE",
                            allowedOperations: (application.clientBindings?.[0]?.allowedOperations ?? ["evaluate", "reserve", "commit"]).join(",")
                          });
                        }}
                      >
                        Binding
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Tạo application" subtitle="Dùng khi onboard một hệ nghiệp vụ mới vào incentive platform." />
          <form
            className="grid gap-3 p-4"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              create.mutate();
            }}
          >
            <FormField label="Tenant" required>
              <Input value={form.tenantId} onChange={(event) => setForm({ ...form, tenantId: event.target.value })} />
            </FormField>
            <FormField label="Application ID" required>
              <Input value={form.applicationId} onChange={(event) => setForm({ ...form, applicationId: event.target.value })} />
            </FormField>
            <FormField label="Tên" required>
              <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
            </FormField>
            <FormField label="Status">
              <Select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>
                <option value="ACTIVE">ACTIVE</option>
                <option value="SUSPENDED">SUSPENDED</option>
                <option value="DISABLED">DISABLED</option>
              </Select>
            </FormField>
            <FormField label="Allowed client IDs">
              <Textarea value={form.allowedClientIds} onChange={(event) => setForm({ ...form, allowedClientIds: event.target.value })} />
            </FormField>
            {create.isError && <ErrorState error={create.error} />}
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Đang tạo" : "Tạo application"}
            </Button>
          </form>
        </Card>
      </div>

      <Drawer
        open={Boolean(bindingTarget)}
        onOpenChange={(open) => !open && setBindingTarget(null)}
        title="Client binding"
        description="Ràng buộc client OAuth/internal với các operation được phép."
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setBindingTarget(null)} disabled={binding.isPending}>
              Hủy
            </Button>
            <Button onClick={() => binding.mutate()} disabled={binding.isPending || !bindingForm.clientId.trim()}>
              {binding.isPending ? "Đang lưu" : "Lưu binding"}
            </Button>
          </div>
        }
      >
        <div className="grid gap-3">
          <FormField label="Client ID" required>
            <Input value={bindingForm.clientId} onChange={(event) => setBindingForm({ ...bindingForm, clientId: event.target.value })} />
          </FormField>
          <FormField label="Status">
            <Select value={bindingForm.status} onChange={(event) => setBindingForm({ ...bindingForm, status: event.target.value })}>
              <option value="ACTIVE">ACTIVE</option>
              <option value="SUSPENDED">SUSPENDED</option>
              <option value="DISABLED">DISABLED</option>
            </Select>
          </FormField>
          <FormField label="Allowed operations">
            <Textarea value={bindingForm.allowedOperations} onChange={(event) => setBindingForm({ ...bindingForm, allowedOperations: event.target.value })} />
          </FormField>
          {binding.isError && <ErrorState error={binding.error} />}
        </div>
      </Drawer>
    </div>
  );
}

export function CampaignListPage() {
  const [filters, setFilters] = useState<CampaignFilters>({});
  const [draftFilters, setDraftFilters] = useState<CampaignFilters>({});
  const campaigns = useQuery({
    queryKey: queryKeys.incentives.campaigns(filters),
    queryFn: () => listCampaigns(filters),
    retry: 1
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Campaigns"
        description="Danh sách campaign theo tenant/application, mở workspace để quản lý draft, review, diff và publish."
        actions={
          <Link to="new">
            <Button>
              <Plus size={16} />
              Tạo campaign
            </Button>
          </Link>
        }
      />
      <IncentiveNav />

      <Toolbar>
        <FormField label="Tenant">
          <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
        </FormField>
        <FormField label="Application">
          <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
        </FormField>
        <FilterActions>
          <Button onClick={() => setFilters(draftFilters)}>
            <Search size={16} />
            Lọc
          </Button>
          <Button variant="secondary" onClick={() => { setDraftFilters({}); setFilters({}); }}>
            Xóa
          </Button>
        </FilterActions>
      </Toolbar>

      <Card>
        <CardHeader title="Campaign catalog" subtitle="Published version là snapshot client nhìn thấy; draft version dùng cho vận hành nội bộ." />
        {campaigns.isLoading && <Spinner />}
        {campaigns.isError && <ErrorState error={campaigns.error} />}
        {campaigns.data?.length === 0 && <EmptyState message="Chưa có campaign phù hợp." />}
        {campaigns.data && campaigns.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Campaign</Th>
                <Th>Scope</Th>
                <Th>Status</Th>
                <Th>Rules</Th>
                <Th>Version</Th>
                <Th>Updated</Th>
              </tr>
            </thead>
            <tbody>
              {campaigns.data.map((campaign) => (
                <tr key={campaign.id} className="hover:bg-slate-50">
                  <Td>
                    <Link to={campaign.id} className="font-semibold text-brand-700 hover:underline">
                      {campaign.name}
                    </Link>
                    <p className="mt-1 font-mono text-xs text-slate-400">{campaign.code}</p>
                  </Td>
                  <Td>
                    <p className="font-semibold">{campaign.applicationId}</p>
                    <p className="mt-1 text-xs text-slate-400">{campaign.tenantId}</p>
                  </Td>
                  <Td>
                    <StatusPill value={campaign.status} />
                  </Td>
                  <Td>
                    <span className="text-sm font-semibold text-slate-700">{campaign.rules?.length ?? 0} rules</span>
                    <p className="mt-1 text-xs text-slate-400">{campaign.actions?.length ?? 0} actions</p>
                  </Td>
                  <Td>
                    <span className="text-sm text-slate-700">draft v{campaign.draftVersion ?? "-"}</span>
                    <p className="mt-1 text-xs text-slate-400">published v{campaign.publishedVersion ?? "-"}</p>
                  </Td>
                  <Td>{formatDateTime(campaign.updatedAt)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}

export function CampaignCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(defaultCampaignForm);
  const [formError, setFormError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => {
      const payload = toCampaignPayload(form);
      return createCampaign({
        ...payload,
        tenantId: form.tenantId.trim(),
        applicationId: form.applicationId.trim(),
        actions: payload.actions
      });
    },
    onSuccess: (campaign) => {
      invalidateIncentives(queryClient);
      navigate(`../${campaign.id}`);
    },
    onError: (error) => setFormError(error instanceof Error ? error.message : "Không thể tạo campaign")
  });

  return (
    <div className="space-y-4">
      <Link to=".." className="inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-800">
        <ArrowLeft size={16} />
        Quay lại campaigns
      </Link>
      <PageHeader
        title="Tạo campaign"
        description="Tạo campaign draft đầu tiên. Backend vẫn là nguồn sự thật cho validation, quota và publish snapshot."
      />
      <IncentiveNav />

      <Card>
        <CardHeader title="Campaign definition" subtitle="Rules/actions giữ dạng JSON để platform đủ generic cho nhiều nghiệp vụ." />
        <form
          className="grid gap-4 p-4"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            setFormError(null);
            create.mutate();
          }}
        >
          <CampaignSpecForm form={form} setForm={setForm} includeTenantApplication disabled={create.isPending} />
          {(formError || create.isError) && <Notice tone="danger" title="Không thể lưu campaign">{formError ?? create.error?.message ?? "Không thể tạo campaign"}</Notice>}
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => navigate("..")}>
              Hủy
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Đang tạo" : "Tạo campaign"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function couponDisplay(coupon: Coupon) {
  return coupon.codeMask || coupon.code || coupon.normalizedCode || compactId(coupon.id);
}

function CouponTable({
  rows,
  campaignById,
  onStatus
}: {
  rows?: Coupon[];
  campaignById: Map<string, Campaign>;
  onStatus: (coupon: Coupon, status: string) => void;
}) {
  if (!rows?.length) return <EmptyState message="Không có coupon phù hợp." />;
  return (
    <Table>
      <thead>
        <tr>
          <Th>Coupon</Th>
          <Th>Campaign</Th>
          <Th>Holder</Th>
          <Th>Status</Th>
          <Th>Limits</Th>
          <Th>Window</Th>
          <Th>Action</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((coupon) => {
          const campaign = campaignById.get(coupon.campaignId);
          return (
            <tr key={coupon.id} className="hover:bg-slate-50">
              <Td>
                <p className="font-mono text-sm font-semibold text-slate-900">{couponDisplay(coupon)}</p>
                <p className="mt-1 font-mono text-xs text-slate-400">{compactId(coupon.id)}</p>
              </Td>
              <Td>
                {campaign ? (
                  <Link to={`/incentives/campaigns/${campaign.id}`} className="font-semibold text-brand-700 hover:underline">
                    {campaign.name}
                  </Link>
                ) : (
                  <span className="font-mono text-xs">{compactId(coupon.campaignId)}</span>
                )}
                <p className="mt-1 font-mono text-xs text-slate-400">{campaign?.code ?? compactId(coupon.campaignId)}</p>
              </Td>
              <Td>
                <span className="font-mono text-xs text-slate-700">{coupon.holderProfileId || "Any learner"}</span>
              </Td>
              <Td>
                <StatusPill value={coupon.status} />
              </Td>
              <Td>
                <p className="text-xs text-slate-500">max {coupon.maxRedemptions ?? "∞"}</p>
                <p className="mt-1 text-xs text-slate-500">per profile {coupon.maxRedemptionsPerProfile ?? "∞"}</p>
              </Td>
              <Td>
                <p className="text-xs text-slate-500">from {formatDateTime(coupon.startsAt)}</p>
                <p className="mt-1 text-xs text-slate-500">to {formatDateTime(coupon.expiresAt)}</p>
              </Td>
              <Td>
                <div className="flex flex-wrap gap-2">
                  <Button size="xs" variant="secondary" disabled={coupon.status === "ACTIVE"} onClick={() => onStatus(coupon, "ACTIVE")}>
                    Active
                  </Button>
                  <Button size="xs" variant="secondary" disabled={coupon.status === "PAUSED"} onClick={() => onStatus(coupon, "PAUSED")}>
                    Pause
                  </Button>
                  <Button size="xs" variant="danger" disabled={coupon.status === "VOID"} onClick={() => onStatus(coupon, "VOID")}>
                    Void
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

export function CouponCatalogPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<CouponFilters>({ limit: 50 });
  const [draftFilters, setDraftFilters] = useState<CouponFilters>({ limit: 50 });
  const [generateForm, setGenerateForm] = useState({
    campaignId: "",
    prefix: "CF",
    quantity: "25",
    codeLength: "10",
    holderProfileId: "",
    startsAt: "",
    expiresAt: "",
    maxRedemptions: "1",
    maxRedemptionsPerProfile: "1",
    metadataJson: "{}"
  });
  const [statusTarget, setStatusTarget] = useState<{ coupon: Coupon; status: string } | null>(null);
  const [statusReason, setStatusReason] = useState("Updated by coupon operations");

  const campaigns = useQuery({
    queryKey: queryKeys.incentives.campaigns({}),
    queryFn: () => listCampaigns({}),
    staleTime: 60_000
  });
  const coupons = useQuery({
    queryKey: queryKeys.incentives.coupons(filters),
    queryFn: () => listCoupons(filters),
    retry: 1
  });
  const inventoryFilters = {
    tenantId: filters.tenantId,
    applicationId: filters.applicationId,
    campaignId: filters.campaignId,
    activeOnly: true
  };
  const inventory = useQuery({
    queryKey: queryKeys.incentives.couponStorageInventory(inventoryFilters),
    queryFn: () => couponStorageInventory(inventoryFilters),
    retry: 1
  });

  const campaignById = useMemo(() => {
    const map = new Map<string, Campaign>();
    for (const campaign of campaigns.data ?? []) map.set(campaign.id, campaign);
    return map;
  }, [campaigns.data]);

  const generate = useMutation({
    mutationFn: () => {
      let metadata: Record<string, unknown> | undefined;
      if (generateForm.metadataJson.trim()) {
        const parsed = JSON.parse(generateForm.metadataJson) as unknown;
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          throw new Error("Metadata phải là JSON object");
        }
        metadata = parsed as Record<string, unknown>;
      }
      if (!generateForm.campaignId) throw new Error("Chọn campaign trước khi generate coupon");
      return generateCoupons({
        campaignId: generateForm.campaignId,
        prefix: generateForm.prefix.trim() || undefined,
        quantity: toNumberOrUndefined(generateForm.quantity) ?? 0,
        codeLength: toNumberOrUndefined(generateForm.codeLength),
        holderProfileId: generateForm.holderProfileId.trim() || undefined,
        startsAt: toIsoDateTime(generateForm.startsAt),
        expiresAt: toIsoDateTime(generateForm.expiresAt),
        maxRedemptions: toNumberOrUndefined(generateForm.maxRedemptions),
        maxRedemptionsPerProfile: toNumberOrUndefined(generateForm.maxRedemptionsPerProfile),
        metadata
      });
    },
    onSuccess: (response) => {
      invalidateIncentives(queryClient);
      setFilters((current) => ({ ...current, campaignId: response.campaignId }));
      setDraftFilters((current) => ({ ...current, campaignId: response.campaignId }));
    }
  });

  const statusMutation = useMutation({
    mutationFn: () => {
      if (!statusTarget) throw new Error("Chưa chọn coupon");
      return updateCouponStatus(statusTarget.coupon.id, {
        status: statusTarget.status,
        reason: statusReason.trim() || `Coupon marked ${statusTarget.status} by operations`
      });
    },
    onSuccess: () => {
      setStatusTarget(null);
      setStatusReason("Updated by coupon operations");
      invalidateIncentives(queryClient);
    }
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Coupons"
        description="Catalog vận hành coupon: tìm kiếm, kiểm tra storage inventory, generate batch và đổi trạng thái coupon."
      />
      <IncentiveNav />

      <Toolbar>
        <FormField label="Tenant">
          <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value || undefined })} />
        </FormField>
        <FormField label="Application">
          <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value || undefined })} />
        </FormField>
        <FormField label="Campaign">
          <Select value={draftFilters.campaignId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, campaignId: event.target.value || undefined })}>
            <option value="">Tất cả campaign</option>
            {(campaigns.data ?? []).map((campaign) => (
              <option key={campaign.id} value={campaign.id}>
                {campaign.code} · {campaign.name}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Status">
          <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value || undefined })}>
            <option value="">Tất cả</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="PAUSED">PAUSED</option>
            <option value="EXPIRED">EXPIRED</option>
            <option value="VOID">VOID</option>
          </Select>
        </FormField>
        <FormField label="Holder">
          <Input value={draftFilters.holderProfileId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, holderProfileId: event.target.value || undefined })} />
        </FormField>
        <FormField label="Code">
          <Input value={draftFilters.code ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, code: event.target.value || undefined })} />
        </FormField>
        <FormField label="Limit">
          <Input value={String(draftFilters.limit ?? 50)} onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })} inputMode="numeric" />
        </FormField>
        <FilterActions>
          <Button onClick={() => setFilters(draftFilters)}>
            <Search size={16} />
            Tìm
          </Button>
          <Button variant="secondary" onClick={() => { setDraftFilters({ limit: 50 }); setFilters({ limit: 50 }); }}>
            Reset
          </Button>
        </FilterActions>
      </Toolbar>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <CardHeader
            title="Coupon catalog"
            subtitle="Danh sách coupon theo campaign/status/holder/code. Code thật có thể bị mask tùy storage policy."
            actions={<Badge value="ROWS" label={`${coupons.data?.length ?? 0} rows`} tone="info" />}
          />
          {coupons.isLoading && <Spinner />}
          {coupons.isError && <ErrorState error={coupons.error} />}
          {!coupons.isLoading && !coupons.isError && (
            <CouponTable rows={coupons.data} campaignById={campaignById} onStatus={(coupon, status) => {
              setStatusTarget({ coupon, status });
              setStatusReason(status === "VOID" ? "Coupon voided by operations" : `Coupon marked ${status} by operations`);
            }} />
          )}
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Storage inventory" subtitle="Tín hiệu cutover: legacy/malformed coupon còn tồn tại hay chưa." compact />
            {inventory.isLoading && <Spinner />}
            {inventory.isError && <ErrorState error={inventory.error} />}
            {inventory.data && (
              <div className="grid gap-3 p-4">
                <div className="grid grid-cols-2 gap-3">
                  <KeyValue label="Total active" value={inventory.data.totalCoupons} />
                  <KeyValue label="Legacy" value={inventory.data.legacyCoupons} />
                  <KeyValue label="Malformed" value={inventory.data.malformedCoupons} />
                  <KeyValue label="Cutover ready" value={<StatusPill value={inventory.data.fallbackDisableReady ? "READY" : "BLOCKED"} />} />
                </div>
                <div className="space-y-2">
                  {inventory.data.items.map((item) => (
                    <div key={item.storageFormat} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                      <span className="font-semibold text-slate-700">{item.storageFormat}</span>
                      <span className="font-mono text-xs text-slate-500">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Generate batch" subtitle="Tạo coupon random theo prefix và limit mặc định." compact />
            <div className="grid gap-3 p-4">
              <FormField label="Campaign" required>
                <Select value={generateForm.campaignId} onChange={(event) => setGenerateForm({ ...generateForm, campaignId: event.target.value })}>
                  <option value="">Chọn campaign</option>
                  {(campaigns.data ?? []).map((campaign) => (
                    <option key={campaign.id} value={campaign.id}>
                      {campaign.code} · {campaign.name}
                    </option>
                  ))}
                </Select>
              </FormField>
              <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
                <FormField label="Prefix">
                  <Input value={generateForm.prefix} onChange={(event) => setGenerateForm({ ...generateForm, prefix: event.target.value.toUpperCase() })} />
                </FormField>
                <FormField label="Quantity">
                  <Input value={generateForm.quantity} onChange={(event) => setGenerateForm({ ...generateForm, quantity: event.target.value })} inputMode="numeric" />
                </FormField>
                <FormField label="Code length">
                  <Input value={generateForm.codeLength} onChange={(event) => setGenerateForm({ ...generateForm, codeLength: event.target.value })} inputMode="numeric" />
                </FormField>
              </div>
              <FormField label="Holder profile">
                <Input value={generateForm.holderProfileId} onChange={(event) => setGenerateForm({ ...generateForm, holderProfileId: event.target.value })} />
              </FormField>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
                <FormField label="Starts">
                  <Input type="datetime-local" value={generateForm.startsAt} onChange={(event) => setGenerateForm({ ...generateForm, startsAt: event.target.value })} />
                </FormField>
                <FormField label="Expires">
                  <Input type="datetime-local" value={generateForm.expiresAt} onChange={(event) => setGenerateForm({ ...generateForm, expiresAt: event.target.value })} />
                </FormField>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
                <FormField label="Max redemptions">
                  <Input value={generateForm.maxRedemptions} onChange={(event) => setGenerateForm({ ...generateForm, maxRedemptions: event.target.value })} inputMode="numeric" />
                </FormField>
                <FormField label="Max/profile">
                  <Input value={generateForm.maxRedemptionsPerProfile} onChange={(event) => setGenerateForm({ ...generateForm, maxRedemptionsPerProfile: event.target.value })} inputMode="numeric" />
                </FormField>
              </div>
              <FormField label="Metadata JSON">
                <Textarea className="font-mono text-xs" value={generateForm.metadataJson} onChange={(event) => setGenerateForm({ ...generateForm, metadataJson: event.target.value })} />
              </FormField>
              {generate.isError && <Notice tone="danger" title="Không thể generate">{generate.error.message}</Notice>}
              {generate.data && (
                <Notice tone="success" title="Generated">
                  Created {generate.data.created}/{generate.data.requested}; duplicate retries {generate.data.duplicateRetries}.
                </Notice>
              )}
              <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
                <Plus size={16} />
                {generate.isPending ? "Đang generate" : "Generate coupons"}
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(statusTarget)}
        onOpenChange={(open) => {
          if (!open) setStatusTarget(null);
        }}
        title={`Đổi coupon sang ${statusTarget?.status ?? ""}`}
        description={statusTarget ? `${couponDisplay(statusTarget.coupon)} · ${compactId(statusTarget.coupon.id)}` : undefined}
        confirmLabel={statusTarget?.status === "VOID" ? "Void coupon" : "Update status"}
        tone={statusTarget?.status === "VOID" ? "danger" : "primary"}
        onConfirm={() => statusMutation.mutate()}
        isPending={statusMutation.isPending}
      >
        <FormField label="Reason">
          <Textarea value={statusReason} onChange={(event) => setStatusReason(event.target.value)} />
        </FormField>
        {statusMutation.isError && <Notice tone="danger" title="Không thể đổi trạng thái">{statusMutation.error.message}</Notice>}
      </ConfirmDialog>
    </div>
  );
}

function VersionRail({
  versions,
  selected,
  onSelect
}: {
  versions?: CampaignVersion[];
  selected?: number;
  onSelect: (versionNumber: number) => void;
}) {
  if (!versions?.length) return <EmptyState message="Campaign chưa có version." />;
  return (
    <div className="divide-y divide-slate-100">
      {[...versions]
        .sort((a, b) => b.versionNumber - a.versionNumber)
        .map((version) => (
          <button
            key={version.id}
            className={cn(
              "flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition hover:bg-slate-50",
              selected === version.versionNumber && "bg-brand-50"
            )}
            onClick={() => onSelect(version.versionNumber)}
          >
            <span className="min-w-0">
              <span className="block text-sm font-bold text-slate-900">Version {version.versionNumber}</span>
              <span className="mt-1 block text-xs text-slate-400">{formatDateTime(version.createdAt)}</span>
            </span>
            <StatusPill value={version.versionStatus} />
          </button>
        ))}
    </div>
  );
}

function ValidationPanel({
  validation,
  isLoading
}: {
  validation?: Awaited<ReturnType<typeof getCampaignVersionValidation>>;
  isLoading: boolean;
}) {
  if (isLoading) return <Spinner label="Đang kiểm tra validation" />;
  if (!validation) return <EmptyState message="Chọn version để xem validation." />;
  const messages = [...validation.blockers, ...validation.warnings];
  return (
    <div className="p-4">
      <Notice
        tone={validation.publishable ? "success" : "warning"}
        title={validation.publishable ? "Có thể publish" : "Chưa đủ điều kiện publish"}
      >
        {validation.blockers.length} blocker · {validation.warnings.length} warning
      </Notice>
      {messages.length > 0 && (
        <div className="mt-3 divide-y divide-slate-100 rounded-md border border-slate-200">
          {messages.map((message) => (
            <div key={`${message.code}-${message.field ?? ""}`} className="grid gap-2 px-3 py-2 md:grid-cols-[120px_1fr]">
              <StatusPill value={message.severity} />
              <div>
                <p className="text-sm font-semibold text-slate-800">{message.message}</p>
                <p className="mt-1 font-mono text-xs text-slate-400">{message.field ?? "definition"} · {message.code}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DiffPanel({
  diff,
  isLoading,
  sameVersion
}: {
  diff?: Awaited<ReturnType<typeof getCampaignVersionDiff>>;
  isLoading: boolean;
  sameVersion: boolean;
}) {
  if (sameVersion) return <EmptyState message="Version đang chọn trùng published snapshot." />;
  if (isLoading) return <Spinner label="Đang tính diff" />;
  if (!diff) return <EmptyState message="Chưa có published version để so sánh." />;
  if (diff.changes.length === 0) return <EmptyState message="Không có thay đổi." />;
  return (
    <div className="divide-y divide-slate-100">
      {diff.changes.map((change) => (
        <div key={change.field} className="grid gap-3 p-4 xl:grid-cols-[180px_1fr_1fr]">
          <div>
            <p className="font-mono text-xs font-bold text-slate-500">{change.field}</p>
          </div>
          <JsonBlock value={change.leftValue} className="max-h-44" />
          <JsonBlock value={change.rightValue} className="max-h-44" />
        </div>
      ))}
    </div>
  );
}

export function CampaignWorkspacePage() {
  const { campaignId = "", versionNumber } = useParams();
  const routeVersion = Number(versionNumber);
  const queryClient = useQueryClient();
  const [selectedVersion, setSelectedVersion] = useState<number | undefined>(Number.isFinite(routeVersion) ? routeVersion : undefined);
  const [draftForm, setDraftForm] = useState(defaultCampaignForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<ConfirmAction | null>(null);
  const [note, setNote] = useState("");
  const [couponOpen, setCouponOpen] = useState(false);
  const [couponForm, setCouponForm] = useState({
    code: "",
    holderProfileId: "",
    startsAt: "",
    expiresAt: "",
    maxRedemptions: "",
    maxRedemptionsPerProfile: "",
    metadataJson: "{}"
  });

  const campaign = useQuery({
    queryKey: queryKeys.incentives.campaign(campaignId),
    queryFn: () => getCampaign(campaignId),
    enabled: Boolean(campaignId),
    retry: 1
  });
  const versions = useQuery({
    queryKey: queryKeys.incentives.versions(campaignId),
    queryFn: () => listCampaignVersions(campaignId),
    enabled: Boolean(campaignId),
    retry: 1
  });

  useEffect(() => {
    if (Number.isFinite(routeVersion)) {
      setSelectedVersion(routeVersion);
      return;
    }
    if (!selectedVersion && versions.data?.length) {
      setSelectedVersion(campaign.data?.draftVersion ?? campaign.data?.publishedVersion ?? versions.data[0].versionNumber);
    }
  }, [campaign.data?.draftVersion, campaign.data?.publishedVersion, routeVersion, selectedVersion, versions.data]);

  const detail = useQuery({
    queryKey: queryKeys.incentives.version(campaignId, selectedVersion),
    queryFn: () => getCampaignVersion(campaignId, selectedVersion ?? 0),
    enabled: Boolean(campaignId && selectedVersion),
    retry: 1
  });
  const validation = useQuery({
    queryKey: queryKeys.incentives.validation(campaignId, selectedVersion),
    queryFn: () => getCampaignVersionValidation(campaignId, selectedVersion ?? 0),
    enabled: Boolean(campaignId && selectedVersion),
    retry: 1
  });
  const publishedVersion = campaign.data?.publishedVersion ?? undefined;
  const diff = useQuery({
    queryKey: queryKeys.incentives.diff(campaignId, publishedVersion, selectedVersion),
    queryFn: () => getCampaignVersionDiff(campaignId, publishedVersion ?? 0, selectedVersion ?? 0),
    enabled: Boolean(campaignId && publishedVersion && selectedVersion && publishedVersion !== selectedVersion),
    retry: 1
  });
  const timeline = useQuery({
    queryKey: queryKeys.incentives.timeline("campaign", campaignId),
    queryFn: () => campaignTimeline(campaignId, 30),
    enabled: Boolean(campaignId),
    retry: 1
  });

  useEffect(() => {
    if (detail.data) {
      setDraftForm(versionToForm(detail.data));
      setFormError(null);
    }
  }, [detail.data]);

  const refreshWorkspace = () => {
    invalidateIncentives(queryClient);
  };

  const createDraft = useMutation({
    mutationFn: () => createCampaignVersion(campaignId),
    onSuccess: (version) => {
      setSelectedVersion(version.versionNumber);
      refreshWorkspace();
    }
  });

  const saveDraft = useMutation({
    mutationFn: () => {
      if (!selectedVersion) throw new Error("Chưa chọn version");
      const payload = toCampaignPayload(draftForm);
      return updateCampaignVersionDraft(campaignId, selectedVersion, payload);
    },
    onSuccess: (version) => {
      setSelectedVersion(version.versionNumber);
      refreshWorkspace();
    },
    onError: (error) => setFormError(error instanceof Error ? error.message : "Không thể lưu draft")
  });

  const transition = useMutation({
    mutationFn: async ({ state, reviewNote }: { state: ConfirmAction; reviewNote: string }) => {
      const input = { note: reviewNote.trim() || undefined };
      if (state.action === "submit") return submitCampaignVersion(campaignId, state.versionNumber, input);
      if (state.action === "approve") return approveCampaignVersion(campaignId, state.versionNumber, input);
      if (state.action === "reject") return rejectCampaignVersion(campaignId, state.versionNumber, input);
      if (state.action === "publish") return publishCampaignVersion(campaignId, state.versionNumber, input);
      return rollbackCampaignVersion(campaignId, state.versionNumber, input);
    },
    onSuccess: (result) => {
      if ("versionNumber" in result) setSelectedVersion(result.versionNumber);
      setConfirm(null);
      setNote("");
      refreshWorkspace();
    }
  });

  const coupon = useMutation({
    mutationFn: () => {
      if (!campaignId) throw new Error("Thiếu campaign");
      let metadata: Record<string, unknown> | undefined;
      if (couponForm.metadataJson.trim()) {
        const parsed = JSON.parse(couponForm.metadataJson) as unknown;
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          throw new Error("Metadata phải là JSON object");
        }
        metadata = parsed as Record<string, unknown>;
      }
      return createCoupon({
        campaignId,
        code: couponForm.code.trim(),
        holderProfileId: couponForm.holderProfileId.trim() || undefined,
        startsAt: toIsoDateTime(couponForm.startsAt),
        expiresAt: toIsoDateTime(couponForm.expiresAt),
        maxRedemptions: toNumberOrUndefined(couponForm.maxRedemptions),
        maxRedemptionsPerProfile: toNumberOrUndefined(couponForm.maxRedemptionsPerProfile),
        metadata
      });
    },
    onSuccess: () => {
      setCouponOpen(false);
      refreshWorkspace();
    }
  });

  const selectedDetail = detail.data;
  const editable = selectedDetail?.versionStatus === "DRAFT" || selectedDetail?.versionStatus === "REJECTED";
  const sameVersion = Boolean(publishedVersion && selectedVersion && publishedVersion === selectedVersion);

  return (
    <div className="space-y-4">
      <Link to="/incentives/campaigns" className="inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-800">
        <ArrowLeft size={16} />
        Quay lại campaign list
      </Link>
      <PageHeader
        title={campaign.data?.name ?? "Campaign workspace"}
        description="Workspace vận hành version lifecycle: validate, diff, review, publish, rollback và coupon support."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => createDraft.mutate()} disabled={createDraft.isPending || !campaign.data}>
              <FileJson2 size={16} />
              Tạo draft version
            </Button>
            <Button variant="secondary" onClick={() => setCouponOpen(true)} disabled={!campaign.data}>
              <TicketPercent size={16} />
              Tạo coupon
            </Button>
          </div>
        }
      />
      <IncentiveNav />

      {campaign.isError && <ErrorState error={campaign.error} />}
      {versions.isError && <ErrorState error={versions.error} />}

      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card>
            <CardHeader title="Versions" subtitle="Chọn version để xem detail, validation và diff." compact />
            {versions.isLoading && <Spinner />}
            <VersionRail versions={versions.data} selected={selectedVersion} onSelect={setSelectedVersion} />
          </Card>

          <Card>
            <CardHeader title="Campaign scope" compact />
            <div className="grid gap-3 p-4">
              <KeyValue label="Tenant" value={campaign.data?.tenantId} />
              <KeyValue label="Application" value={campaign.data?.applicationId} />
              <KeyValue label="Code" value={campaign.data?.code} mono />
              <KeyValue label="Status" value={<StatusPill value={campaign.data?.status} />} />
              <KeyValue label="Published" value={`v${campaign.data?.publishedVersion ?? "-"}`} />
              <KeyValue label="Draft" value={`v${campaign.data?.draftVersion ?? "-"}`} />
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader
              title={selectedDetail ? `Version ${selectedDetail.versionNumber}` : "Version detail"}
              subtitle={selectedDetail ? `Trạng thái ${statusLabel(selectedDetail.versionStatus)} · tạo bởi ${selectedDetail.createdBy ?? "-"}` : undefined}
              actions={selectedDetail && <StatusPill value={selectedDetail.versionStatus} />}
            />
            {detail.isLoading && <Spinner />}
            {detail.isError && <ErrorState error={detail.error} />}
            {selectedDetail && (
              <div className="border-b border-slate-100 p-4">
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <KeyValue label="Submitted" value={formatDateTime(selectedDetail.submittedAt)} />
                  <KeyValue label="Reviewed" value={formatDateTime(selectedDetail.reviewedAt)} />
                  <KeyValue label="Published" value={formatDateTime(selectedDetail.publishedAt)} />
                  <KeyValue label="Rollback source" value={selectedDetail.rollbackSourceVersion ? `v${selectedDetail.rollbackSourceVersion}` : "-"} />
                </div>
                {selectedDetail.reviewNote && (
                  <Notice tone="neutral" title="Review note" className="mt-4">
                    {selectedDetail.reviewNote}
                  </Notice>
                )}
              </div>
            )}
            {selectedDetail && (
              <form
                className="grid gap-4 p-4"
                onSubmit={(event: FormEvent) => {
                  event.preventDefault();
                  setFormError(null);
                  saveDraft.mutate();
                }}
              >
                {!editable && (
                  <Notice tone="info" title="Version đang khóa chỉnh sửa">
                    Chỉ DRAFT/REJECTED version được chỉnh. Muốn sửa từ snapshot đã publish, tạo draft mới hoặc rollback thành draft.
                  </Notice>
                )}
                <CampaignSpecForm form={draftForm} setForm={setDraftForm} disabled={!editable || saveDraft.isPending} />
                {(formError || saveDraft.isError) && <Notice tone="danger" title="Không thể lưu draft">{formError ?? saveDraft.error?.message ?? "Không thể lưu draft"}</Notice>}
                <div className="flex flex-wrap justify-end gap-2">
                  {editable && (
                    <Button type="submit" disabled={saveDraft.isPending}>
                      {saveDraft.isPending ? "Đang lưu" : "Lưu draft"}
                    </Button>
                  )}
                  {(selectedDetail.versionStatus === "DRAFT" || selectedDetail.versionStatus === "REJECTED") && (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() =>
                        setConfirm({
                          action: "submit",
                          versionNumber: selectedDetail.versionNumber,
                          title: "Gửi version đi duyệt",
                          description: "Reviewer sẽ nhìn thấy version này trong review queue."
                        })
                      }
                    >
                      <Send size={16} />
                      Gửi duyệt
                    </Button>
                  )}
                  {selectedDetail.versionStatus === "SUBMITTED" && (
                    <>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          setConfirm({
                            action: "approve",
                            versionNumber: selectedDetail.versionNumber,
                            title: "Duyệt version",
                            description: "Backend sẽ kiểm tra rule reviewer không tự approve campaign mình sở hữu."
                          })
                        }
                      >
                        <CheckCircle2 size={16} />
                        Duyệt
                      </Button>
                      <Button
                        type="button"
                        variant="danger"
                        onClick={() =>
                          setConfirm({
                            action: "reject",
                            versionNumber: selectedDetail.versionNumber,
                            title: "Từ chối version",
                            description: "Ghi note để author biết cần sửa gì.",
                            tone: "danger"
                          })
                        }
                      >
                        <XCircle size={16} />
                        Từ chối
                      </Button>
                    </>
                  )}
                  {selectedDetail.versionStatus === "APPROVED" && (
                    <Button
                      type="button"
                      onClick={() =>
                        setConfirm({
                          action: "publish",
                          versionNumber: selectedDetail.versionNumber,
                          title: "Publish version",
                          description: "Snapshot này sẽ trở thành published definition mà client có thể đánh giá."
                        })
                      }
                    >
                      <BadgePercent size={16} />
                      Publish
                    </Button>
                  )}
                  {selectedDetail.versionStatus !== "DRAFT" && (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() =>
                        setConfirm({
                          action: "rollback",
                          versionNumber: selectedDetail.versionNumber,
                          title: "Tạo draft rollback",
                          description: "Backend sẽ copy snapshot này thành một draft version mới, không thay đổi published snapshot hiện tại."
                        })
                      }
                    >
                      <RotateCcw size={16} />
                      Rollback draft
                    </Button>
                  )}
                </div>
              </form>
            )}
          </Card>

          <div className="grid gap-4 2xl:grid-cols-2">
            <Card>
              <CardHeader title="Readiness blockers" subtitle="Backend validation là nguồn sự thật cho publish confidence." actions={<ClipboardCheck size={18} className="text-brand-700" />} />
              {validation.isError && <ErrorState error={validation.error} />}
              <ValidationPanel validation={validation.data} isLoading={validation.isLoading} />
            </Card>
            <Card>
              <CardHeader title="Diff với published" subtitle="So sánh snapshot đang chọn với published version." actions={<GitCompare size={18} className="text-brand-700" />} />
              {diff.isError && <ErrorState error={diff.error} />}
              <DiffPanel diff={diff.data} isLoading={diff.isLoading} sameVersion={sameVersion} />
            </Card>
          </div>

          <Card>
            <CardHeader title="Campaign audit timeline" subtitle="Actor, action, note và correlation để support/reviewer truy vết." actions={<History size={18} className="text-brand-700" />} />
            {timeline.isLoading && <Spinner />}
            {timeline.isError && <ErrorState error={timeline.error} />}
            {timeline.data && <Timeline events={timeline.data.items} />}
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(open) => {
          if (!open) {
            setConfirm(null);
            setNote("");
          }
        }}
        title={confirm?.title ?? "Xác nhận"}
        description={confirm?.description}
        confirmLabel={confirm ? transitionVerb(confirm.action) : "Xác nhận"}
        tone={confirm?.tone ?? "primary"}
        isPending={transition.isPending}
        onConfirm={() => confirm && transition.mutate({ state: confirm, reviewNote: note })}
      >
        <FormField label="Note">
          <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Ghi chú review/audit" />
        </FormField>
        {transition.isError && <ErrorState error={transition.error} />}
      </ConfirmDialog>

      <Drawer
        open={couponOpen}
        onOpenChange={setCouponOpen}
        title="Tạo coupon"
        description="Tạo coupon đơn lẻ cho campaign. Batch/generator sẽ là sprint sau."
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCouponOpen(false)} disabled={coupon.isPending}>
              Hủy
            </Button>
            <Button onClick={() => coupon.mutate()} disabled={coupon.isPending || !couponForm.code.trim()}>
              {coupon.isPending ? "Đang tạo" : "Tạo coupon"}
            </Button>
          </div>
        }
      >
        <div className="grid gap-3">
          <FormField label="Code" required>
            <Input value={couponForm.code} onChange={(event) => setCouponForm({ ...couponForm, code: event.target.value })} />
          </FormField>
          <FormField label="Holder profile">
            <Input value={couponForm.holderProfileId} onChange={(event) => setCouponForm({ ...couponForm, holderProfileId: event.target.value })} />
          </FormField>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Starts at">
              <Input type="datetime-local" value={couponForm.startsAt} onChange={(event) => setCouponForm({ ...couponForm, startsAt: event.target.value })} />
            </FormField>
            <FormField label="Expires at">
              <Input type="datetime-local" value={couponForm.expiresAt} onChange={(event) => setCouponForm({ ...couponForm, expiresAt: event.target.value })} />
            </FormField>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Max redemptions">
              <Input value={couponForm.maxRedemptions} onChange={(event) => setCouponForm({ ...couponForm, maxRedemptions: event.target.value })} inputMode="numeric" />
            </FormField>
            <FormField label="Max/profile">
              <Input value={couponForm.maxRedemptionsPerProfile} onChange={(event) => setCouponForm({ ...couponForm, maxRedemptionsPerProfile: event.target.value })} inputMode="numeric" />
            </FormField>
          </div>
          <FormField label="Metadata JSON">
            <Textarea className="font-mono text-xs" value={couponForm.metadataJson} onChange={(event) => setCouponForm({ ...couponForm, metadataJson: event.target.value })} />
          </FormField>
          {coupon.isError && <ErrorState error={coupon.error} />}
        </div>
      </Drawer>
    </div>
  );
}

export function ReviewQueuePage() {
  const [filters, setFilters] = useState<ReviewQueueFilters>({ status: "SUBMITTED", limit: 50 });
  const [draftFilters, setDraftFilters] = useState<ReviewQueueFilters>({ status: "SUBMITTED", limit: 50 });
  const reviewQueue = useQuery({
    queryKey: queryKeys.incentives.reviewQueue(filters),
    queryFn: () => listSubmittedCampaignVersions(filters),
    retry: 1,
    staleTime: 30_000
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Version review queue"
        description="Các campaign version đang SUBMITTED cần reviewer kiểm tra validation, diff và approve/reject."
      />
      <IncentiveNav />

      <Toolbar>
        <FormField label="Tenant">
          <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
        </FormField>
        <FormField label="Application">
          <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
        </FormField>
        <FilterActions>
          <Button onClick={() => setFilters(draftFilters)}>
            <Search size={16} />
            Lọc
          </Button>
          <Button variant="secondary" onClick={() => { setDraftFilters({ status: "SUBMITTED", limit: 50 }); setFilters({ status: "SUBMITTED", limit: 50 }); }}>
            Xóa
          </Button>
        </FilterActions>
      </Toolbar>

      <Card>
        <CardHeader
          title="Chờ reviewer"
          subtitle="Queue đọc từ backend review endpoint để reviewer thấy readiness mà không cần fan-out từng campaign."
          actions={<Badge value="SUBMITTED" label={`${reviewQueue.data?.length ?? 0} chờ duyệt`} tone="info" />}
        />
        {reviewQueue.isLoading && <Spinner />}
        {reviewQueue.isError && <ErrorState error={reviewQueue.error} />}
        {reviewQueue.data?.length === 0 && <EmptyState message="Không có version nào đang chờ duyệt." />}
        {reviewQueue.data && reviewQueue.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Campaign</Th>
                <Th>Scope</Th>
                <Th>Version</Th>
                <Th>Readiness</Th>
                <Th>Submitted</Th>
                <Th>Reviewer action</Th>
              </tr>
            </thead>
            <tbody>
              {reviewQueue.data.map((item) => {
                const version = item.version;
                return (
                <tr key={version.id} className="hover:bg-slate-50">
                  <Td>
                    <Link to={`/incentives/campaigns/${version.campaignId}/versions/${version.versionNumber}`} className="font-semibold text-brand-700 hover:underline">
                      {item.campaignName}
                    </Link>
                    <p className="mt-1 font-mono text-xs text-slate-400">{item.campaignCode}</p>
                  </Td>
                  <Td>
                    <span className="font-semibold">{item.applicationId}</span>
                    <p className="mt-1 text-xs text-slate-400">{item.tenantId}</p>
                  </Td>
                  <Td>
                    <StatusPill value={version.versionStatus} label={`v${version.versionNumber} · ${statusLabel(version.versionStatus)}`} />
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      <Badge value={item.publishable ? "READY" : "BLOCKED"} label={item.publishable ? "Ready" : "Blocked"} tone={item.publishable ? "success" : "danger"} />
                      <Badge value="BLOCKERS" label={`${item.blockerCount} blocker`} tone={item.blockerCount > 0 ? "danger" : "slate"} />
                      <Badge value="WARNINGS" label={`${item.warningCount} warning`} tone={item.warningCount > 0 ? "warning" : "slate"} />
                    </div>
                  </Td>
                  <Td>
                    <span>{formatDateTime(version.submittedAt)}</span>
                    <p className="mt-1 text-xs text-slate-400">by {version.submittedBy ?? "-"}</p>
                  </Td>
                  <Td>
                    <Link to={`/incentives/campaigns/${version.campaignId}/versions/${version.versionNumber}`}>
                      <Button size="sm" variant="secondary">
                        Mở workspace
                      </Button>
                    </Link>
                  </Td>
                </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}

function ReservationTable({ rows }: { rows?: Reservation[] }) {
  if (!rows?.length) return <EmptyState message="Không có reservation phù hợp." />;
  return (
    <Table>
      <thead>
        <tr>
          <Th>Reservation</Th>
          <Th>Profile</Th>
          <Th>Campaign</Th>
          <Th>Coupon</Th>
          <Th>Status</Th>
          <Th>Timing</Th>
          <Th>Evidence</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((reservation) => (
          <tr key={reservation.id} className="hover:bg-slate-50">
            <Td>
              <span className="font-mono text-xs font-semibold text-slate-800">{compactId(reservation.id)}</span>
              <p className="mt-1 text-xs text-slate-400">{reservation.externalReference ?? "no external ref"}</p>
              {reservation.requestHash && <p className="mt-1 font-mono text-xs text-slate-400">hash {compactId(reservation.requestHash)}</p>}
            </Td>
            <Td>
              <span className="font-semibold">{reservation.profileId}</span>
              <p className="mt-1 text-xs text-slate-400">{reservation.applicationId}</p>
            </Td>
            <Td>
              <span className="font-mono text-xs">{compactId(reservation.campaignId)}</span>
              <p className="mt-1 text-xs text-slate-400">v{reservation.campaignVersion ?? "-"}</p>
            </Td>
            <Td>
              {reservation.couponId ? (
                <span className="font-mono text-xs">{compactId(reservation.couponId)}</span>
              ) : (
                <span className="text-xs text-slate-400">No coupon</span>
              )}
            </Td>
            <Td>
              <StatusPill value={reservation.status} />
              {reservation.expired && (
                <div className="mt-1">
                  <Badge value="expired" label="expired by time" tone="warning" />
                </div>
              )}
              {reservation.failureReason && <p className="mt-1 text-xs text-red-500">{reservation.failureReason}</p>}
            </Td>
            <Td>
              <p className="text-xs text-slate-500">reserved {formatDateTime(reservation.reservedAt)}</p>
              <p className="mt-1 text-xs text-slate-500">expires {formatDateTime(reservation.expiresAt)}</p>
              {reservation.committedAt && <p className="mt-1 text-xs text-emerald-600">committed {formatDateTime(reservation.committedAt)}</p>}
              {reservation.cancelledAt && <p className="mt-1 text-xs text-red-500">cancelled {formatDateTime(reservation.cancelledAt)}</p>}
            </Td>
            <Td>
              <p className="text-xs text-slate-500">{reservation.effects?.length ?? 0} effects</p>
              <p className="mt-1 text-xs text-slate-500">{reservation.quotaSnapshot?.length ?? 0} quota holds</p>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function RedemptionTable({
  rows,
  onReverse
}: {
  rows?: Redemption[];
  onReverse: (redemption: Redemption) => void;
}) {
  if (!rows?.length) return <EmptyState message="Không có redemption phù hợp." />;
  return (
    <Table>
      <thead>
        <tr>
          <Th>Redemption</Th>
          <Th>Profile</Th>
          <Th>Campaign</Th>
          <Th>Status</Th>
          <Th>Redeemed</Th>
          <Th>Action</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((redemption) => (
          <tr key={redemption.id} className="hover:bg-slate-50">
            <Td>
              <Link to={`/incentives/redemptions/${redemption.id}`} className="font-mono text-xs font-semibold text-brand-700 hover:underline">
                {compactId(redemption.id)}
              </Link>
              <p className="mt-1 text-xs text-slate-400">{redemption.externalReference ?? "no external ref"}</p>
            </Td>
            <Td>
              <span className="font-semibold">{redemption.profileId}</span>
              <p className="mt-1 text-xs text-slate-400">{redemption.applicationId}</p>
            </Td>
            <Td>
              <span className="font-mono text-xs">{compactId(redemption.campaignId)}</span>
              <p className="mt-1 text-xs text-slate-400">v{redemption.campaignVersion ?? "-"}</p>
            </Td>
            <Td>
              <StatusPill value={redemption.status} />
            </Td>
            <Td>{formatDateTime(redemption.redeemedAt)}</Td>
            <Td>
              <Button size="sm" variant="danger" disabled={redemption.status === "REVERSED"} onClick={() => onReverse(redemption)}>
                Reverse
              </Button>
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function RedemptionSupportPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ReservationFilters>({ limit: 50 });
  const [draftFilters, setDraftFilters] = useState<ReservationFilters>({ limit: 50 });
  const [target, setTarget] = useState<Redemption | null>(null);
  const [reason, setReason] = useState("");
  const redemptionFilters = useMemo<RedemptionFilters>(
    () => ({
      tenantId: filters.tenantId,
      applicationId: filters.applicationId,
      profileId: filters.profileId,
      externalReference: filters.externalReference,
      campaignId: filters.campaignId,
      couponId: filters.couponId,
      limit: filters.limit
    }),
    [filters]
  );
  const reservations = useQuery({
    queryKey: queryKeys.incentives.reservations(filters),
    queryFn: () => listReservations(filters),
    retry: 1
  });
  const redemptions = useQuery({
    queryKey: queryKeys.incentives.redemptions(redemptionFilters),
    queryFn: () => listRedemptions(redemptionFilters),
    retry: 1
  });
  const reverse = useMutation({
    mutationFn: () => {
      if (!target) throw new Error("Chưa chọn redemption");
      return reverseRedemption(target.id, {
        idempotencyKey: `admin-reversal-${crypto.randomUUID()}`,
        reason: reason.trim()
      });
    },
    onSuccess: () => {
      setTarget(null);
      setReason("");
      invalidateIncentives(queryClient);
    }
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Promotion support"
        description="Tra cứu reservation/redemption theo tenant/application/profile/campaign/coupon và xử lý reverse có idempotency + audit."
      />
      <IncentiveNav />

      <Toolbar>
        <FormField label="Tenant">
          <Input value={draftFilters.tenantId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, tenantId: event.target.value })} />
        </FormField>
        <FormField label="Application">
          <Input value={draftFilters.applicationId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, applicationId: event.target.value })} />
        </FormField>
        <FormField label="Profile">
          <Input value={draftFilters.profileId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, profileId: event.target.value })} />
        </FormField>
        <FormField label="External ref">
          <Input value={draftFilters.externalReference ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, externalReference: event.target.value })} />
        </FormField>
        <FormField label="Campaign ID">
          <Input value={draftFilters.campaignId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, campaignId: event.target.value })} />
        </FormField>
        <FormField label="Coupon ID">
          <Input value={draftFilters.couponId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, couponId: event.target.value })} />
        </FormField>
        <FormField label="Reservation status">
          <Select value={draftFilters.status ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, status: event.target.value || undefined })}>
            <option value="">Tất cả</option>
            <option value="RESERVED">RESERVED</option>
            <option value="REDEEMED">REDEEMED</option>
            <option value="CANCELLED">CANCELLED</option>
            <option value="EXPIRED">EXPIRED</option>
            <option value="FAILED">FAILED</option>
          </Select>
        </FormField>
        <FormField label="Expired">
          <Select
            value={draftFilters.expiredOnly ? "true" : ""}
            onChange={(event) => setDraftFilters({ ...draftFilters, expiredOnly: event.target.value === "true" || undefined })}
          >
            <option value="">Tất cả</option>
            <option value="true">Expired RESERVED</option>
          </Select>
        </FormField>
        <FormField label="Limit">
          <Input value={String(draftFilters.limit ?? 50)} onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })} inputMode="numeric" />
        </FormField>
        <FilterActions>
          <Button onClick={() => setFilters(draftFilters)}>
            <Search size={16} />
            Tìm
          </Button>
          <Button variant="secondary" onClick={() => { setDraftFilters({ limit: 50 }); setFilters({ limit: 50 }); }}>
            Reset
          </Button>
        </FilterActions>
      </Toolbar>

      <Card>
        <CardHeader title="Reservations" subtitle="Soi trạng thái reserve trước khi commit: expired, cancelled, coupon/quota holds và request hash để đối chiếu audit." />
        {reservations.isLoading && <Spinner />}
        {reservations.isError && <ErrorState error={reservations.error} />}
        {!reservations.isLoading && !reservations.isError && <ReservationTable rows={reservations.data} />}
      </Card>

      <Card>
        <CardHeader title="Redemptions" subtitle="Reverse không release lại quota đã commit; backend ghi ledger REVERSE và audit event." />
        {redemptions.isLoading && <Spinner />}
        {redemptions.isError && <ErrorState error={redemptions.error} />}
        {!redemptions.isLoading && !redemptions.isError && <RedemptionTable rows={redemptions.data} onReverse={setTarget} />}
      </Card>

      <ConfirmDialog
        open={Boolean(target)}
        onOpenChange={(open) => {
          if (!open) {
            setTarget(null);
            setReason("");
          }
        }}
        title="Reverse redemption"
        description="Thao tác này ghi audit và ledger reversal. Cần nhập lý do rõ ràng."
        confirmLabel="Reverse"
        tone="danger"
        isPending={reverse.isPending}
        onConfirm={() => reverse.mutate()}
      >
        <FormField label="Reason" required>
          <Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="VD: Order refunded / duplicate payment" />
        </FormField>
        {reverse.isError && <ErrorState error={reverse.error} />}
      </ConfirmDialog>
    </div>
  );
}

export function RedemptionDetailPage() {
  const { redemptionId = "" } = useParams();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const redemption = useQuery({
    queryKey: queryKeys.incentives.redemption(redemptionId),
    queryFn: () => getRedemption(redemptionId),
    enabled: Boolean(redemptionId),
    retry: 1
  });
  const timeline = useQuery({
    queryKey: queryKeys.incentives.timeline("redemption", redemptionId),
    queryFn: () => redemptionTimeline(redemptionId, 30),
    enabled: Boolean(redemptionId),
    retry: 1
  });
  const reverse = useMutation({
    mutationFn: () =>
      reverseRedemption(redemptionId, {
        idempotencyKey: `admin-reversal-${crypto.randomUUID()}`,
        reason: reason.trim()
      }),
    onSuccess: () => {
      setConfirmOpen(false);
      setReason("");
      invalidateIncentives(queryClient);
    }
  });

  return (
    <div className="space-y-4">
      <Link to="/incentives/redemptions" className="inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-slate-800">
        <ArrowLeft size={16} />
        Quay lại redemptions
      </Link>
      <PageHeader
        title="Redemption detail"
        description="Chi tiết trạng thái, campaign snapshot, effects và audit timeline cho một redemption."
        actions={
          <Button
            variant="danger"
            disabled={!redemption.data || redemption.data.status === "REVERSED"}
            onClick={() => setConfirmOpen(true)}
          >
            <RotateCcw size={16} />
            Reverse
          </Button>
        }
      />
      <IncentiveNav />

      {redemption.isLoading && <Spinner />}
      {redemption.isError && <ErrorState error={redemption.error} />}
      {redemption.data && (
        <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
          <Card>
            <CardHeader title="Redemption" actions={<StatusPill value={redemption.data.status} />} />
            <div className="grid gap-4 p-4">
              <KeyValue label="ID" value={redemption.data.id} mono />
              <KeyValue label="Reservation" value={compactId(redemption.data.reservationId)} mono />
              <KeyValue label="Tenant/Application" value={`${redemption.data.tenantId} / ${redemption.data.applicationId}`} />
              <KeyValue label="Profile" value={redemption.data.profileId} />
              <KeyValue label="External ref" value={redemption.data.externalReference ?? "-"} />
              <KeyValue label="Campaign" value={`${compactId(redemption.data.campaignId)} · v${redemption.data.campaignVersion ?? "-"}`} mono />
              <KeyValue label="Redeemed" value={formatDateTime(redemption.data.redeemedAt)} />
              <KeyValue label="Reversed" value={formatDateTime(redemption.data.reversedAt)} />
            </div>
          </Card>
          <Card>
            <CardHeader title="Effects" subtitle="Các effect backend đã commit cho redemption này." />
            <div className="p-4">
              <JsonBlock value={redemption.data.effects ?? []} className="max-h-[520px]" />
            </div>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader title="Audit timeline" />
        {timeline.isLoading && <Spinner />}
        {timeline.isError && <ErrorState error={timeline.error} />}
        {timeline.data && <Timeline events={timeline.data.items} />}
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Reverse redemption"
        description="Cần lý do để audit/support trace sau này."
        confirmLabel="Reverse"
        tone="danger"
        isPending={reverse.isPending}
        onConfirm={() => reverse.mutate()}
      >
        <FormField label="Reason" required>
          <Textarea value={reason} onChange={(event) => setReason(event.target.value)} />
        </FormField>
        {reverse.isError && <ErrorState error={reverse.error} />}
      </ConfirmDialog>
    </div>
  );
}

export function AuditExplorerPage() {
  const [filters, setFilters] = useState<AuditFilters>({ limit: 50 });
  const [draftFilters, setDraftFilters] = useState<AuditFilters>({ limit: 50 });
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const audit = useQuery({
    queryKey: queryKeys.incentives.audit(filters),
    queryFn: () => queryAudit(filters),
    retry: 1
  });

  const rows = audit.data?.items ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Audit explorer"
        description="Tìm kiếm actor/action/aggregate/correlation để điều tra lifecycle campaign và redemption."
      />
      <IncentiveNav />

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
        <FormField label="Source client">
          <Input value={draftFilters.sourceClientId ?? ""} onChange={(event) => setDraftFilters({ ...draftFilters, sourceClientId: event.target.value })} />
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
          <Input value={String(draftFilters.limit ?? 50)} onChange={(event) => setDraftFilters({ ...draftFilters, limit: toNumberOrUndefined(event.target.value) })} inputMode="numeric" />
        </FormField>
        <FilterActions>
          <Button onClick={() => setFilters(draftFilters)}>
            <Search size={16} />
            Tìm
          </Button>
          <Button variant="secondary" onClick={() => { setDraftFilters({ limit: 50 }); setFilters({ limit: 50 }); }}>
            Reset
          </Button>
        </FilterActions>
      </Toolbar>

      <Card>
        <CardHeader
          title="Audit events"
          subtitle={audit.data?.hasMore ? "Còn thêm event phía sau; tăng filter hoặc limit để thu hẹp." : "Kết quả theo filter hiện tại."}
          actions={<Badge value="RESULT" label={`${rows.length} events`} tone="slate" />}
        />
        {audit.isLoading && <Spinner />}
        {audit.isError && <ErrorState error={audit.error} />}
        {!audit.isLoading && !audit.isError && rows.length === 0 && <EmptyState message="Không có audit event phù hợp." />}
        {rows.length > 0 && (
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
              {rows.map((event) => (
                <tr key={event.id} className="hover:bg-slate-50">
                  <Td>{formatDateTime(event.createdAt)}</Td>
                  <Td>
                    <StatusPill value={event.action ?? "INFO"} label={event.action ?? "event"} />
                  </Td>
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
                    <Button size="sm" variant="secondary" onClick={() => setSelectedEvent(event)}>
                      Xem
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Drawer
        open={Boolean(selectedEvent)}
        onOpenChange={(open) => !open && setSelectedEvent(null)}
        title="Audit event detail"
        description={selectedEvent ? `${selectedEvent.action ?? "event"} · ${formatDateTime(selectedEvent.createdAt)}` : undefined}
      >
        {selectedEvent && (
          <div className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <KeyValue label="ID" value={selectedEvent.id} mono />
              <KeyValue label="Correlation" value={compactId(selectedEvent.correlationId)} mono />
              <KeyValue label="Actor" value={selectedEvent.actorId ?? "-"} />
              <KeyValue label="Source client" value={selectedEvent.sourceClientId ?? "-"} />
              <KeyValue label="Aggregate" value={`${selectedEvent.aggregateType ?? "-"} / ${compactId(selectedEvent.aggregateId)}`} />
              <KeyValue label="Scope" value={`${selectedEvent.tenantId ?? "-"} / ${selectedEvent.applicationId ?? "-"}`} />
            </div>
            {selectedEvent.note && <Notice tone="neutral" title="Note">{selectedEvent.note}</Notice>}
            <JsonBlock value={selectedEvent.payload ?? {}} className="max-h-[560px]" />
          </div>
        )}
      </Drawer>
    </div>
  );
}
