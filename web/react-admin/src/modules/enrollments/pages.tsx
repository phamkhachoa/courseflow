import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Clock3,
  Ban,
  GraduationCap,
  ListChecks,
  RefreshCcw,
  Search,
  TicketPercent,
  UserPlus,
  UsersRound
} from "lucide-react";
import { queryKeys } from "@/shared/api/query-keys";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th
} from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import { listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
import type { AdminUser } from "@/modules/identity/api";
import { useLearnerUsers } from "@/modules/identity/useLearnerUsers";
import {
  addToWaitlist,
  cancelPromotionApplicationReservation,
  createEnrollment,
  evaluateRefundDropPolicy,
  getStats,
  listEnrollments,
  listPromotionApplications,
  retryPromotionApplicationCommit,
  listWaitlist,
  setCapacity,
  type RefundDropPolicyEvaluationResponse
} from "./api";

function compactId(value?: string) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function enrollmentStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    ACTIVE: "Đang học",
    COMPLETED: "Hoàn thành",
    DROPPED: "Đã rời khóa",
    WAITLISTED: "Chờ ghi danh"
  };
  return labels[status ?? ""] ?? status ?? "Chưa rõ";
}

function waitlistStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    WAITING: "Đang chờ",
    OFFERED: "Đã mời",
    EXPIRED: "Hết hạn",
    CANCELLED: "Đã hủy"
  };
  return labels[status ?? ""] ?? status ?? "Đang chờ";
}

function promotionStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    RESERVED: "Đã giữ ưu đãi",
    APPLIED: "Đã áp dụng",
    COMMIT_FAILED: "Chờ retry",
    MANUAL_REVIEW: "Cần xử lý",
    CANCELLED: "Đã hủy",
    REVERSED: "Đã đảo giao dịch",
    SKIPPED: "Không dùng ưu đãi",
    UNAVAILABLE: "Không khả dụng"
  };
  return labels[status ?? ""] ?? status ?? "Chưa rõ";
}

function reasonSummary(reasonCodes?: string[]) {
  return reasonCodes?.length ? reasonCodes.join(", ") : "Không có reason code";
}

function formatDateTime(value?: string | null) {
  return value ? new Date(value).toLocaleString("vi-VN") : "Chưa lên lịch";
}

function canRemediatePromotion(status?: string) {
  return status === "COMMIT_FAILED" || status === "RESERVED";
}

function courseLabel(course?: Course, fallbackId?: string) {
  if (!course) return fallbackId ? `Khóa ${compactId(fallbackId)}` : "Tất cả khóa";
  return course.code ? `${course.code} · ${course.title}` : course.title;
}

function userLabel(user?: AdminUser, fallbackId?: string) {
  if (!user) return fallbackId ? `User ${compactId(fallbackId)}` : "Tất cả học viên";
  return `${user.fullName || user.email} · ${user.email}`;
}

type RefundPolicyForm = {
  enrollmentId: string;
  reason: string;
  refundWindowDays: string;
  paymentStatus: string;
  paidAmount: string;
  currency: string;
  paidAt: string;
  promotionStatus: string;
  reservationId: string;
  redemptionId: string;
  loyaltyPointsEarned: string;
  loyaltyPointsReversed: string;
  loyaltyEarnEntryId: string;
  rewardStatus: string;
  rewardRedemptionId: string;
  rewardFulfillmentStatus: string;
  rewardFulfilled: boolean;
};

const defaultRefundPolicyForm: RefundPolicyForm = {
  enrollmentId: "",
  reason: "Learner refund/drop request",
  refundWindowDays: "14",
  paymentStatus: "",
  paidAmount: "",
  currency: "USD",
  paidAt: "",
  promotionStatus: "",
  reservationId: "",
  redemptionId: "",
  loyaltyPointsEarned: "",
  loyaltyPointsReversed: "",
  loyaltyEarnEntryId: "",
  rewardStatus: "",
  rewardRedemptionId: "",
  rewardFulfillmentStatus: "",
  rewardFulfilled: false
};

function optionalText(value: string) {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
}

function optionalNumber(value: string) {
  const normalized = value.trim();
  return normalized ? Number(normalized) : undefined;
}

function optionalIsoDate(value: string) {
  const normalized = value.trim();
  return normalized ? new Date(normalized).toISOString() : undefined;
}

function refundPolicyPayload(form: RefundPolicyForm) {
  return {
    enrollmentId: form.enrollmentId.trim(),
    reason: optionalText(form.reason),
    refundWindowDays: optionalNumber(form.refundWindowDays),
    paymentStatus: optionalText(form.paymentStatus),
    paidAmount: optionalNumber(form.paidAmount),
    currency: optionalText(form.currency),
    paidAt: optionalIsoDate(form.paidAt),
    promotionStatus: optionalText(form.promotionStatus),
    reservationId: optionalText(form.reservationId),
    redemptionId: optionalText(form.redemptionId),
    loyaltyPointsEarned: optionalNumber(form.loyaltyPointsEarned),
    loyaltyPointsReversed: optionalNumber(form.loyaltyPointsReversed),
    loyaltyEarnEntryId: optionalText(form.loyaltyEarnEntryId),
    rewardStatus: optionalText(form.rewardStatus),
    rewardRedemptionId: optionalText(form.rewardRedemptionId),
    rewardFulfillmentStatus: optionalText(form.rewardFulfillmentStatus),
    rewardFulfilled: form.rewardFulfilled,
    evidence: { source: "admin-enrollment-ops" }
  };
}

function policyStatusLabel(value?: string) {
  const labels: Record<string, string> = {
    ACTION_REQUIRED: "Cần xử lý",
    MANUAL_REVIEW: "Cần duyệt",
    NO_ACTION: "Không cần xử lý"
  };
  return labels[value ?? ""] ?? value ?? "Chưa chạy";
}

function decisionLabel(value?: string) {
  const labels: Record<string, string> = {
    REQUIRED: "Phải làm",
    NOT_REQUIRED: "Không cần",
    ALREADY_DONE: "Đã xong",
    MANUAL_REVIEW: "Cần duyệt",
    BLOCKED: "Đang chặn"
  };
  return labels[value ?? ""] ?? value ?? "Chưa rõ";
}

function severityTone(value?: string) {
  if (value === "CRITICAL") return "danger" as const;
  if (value === "HIGH") return "warning" as const;
  if (value === "MEDIUM") return "info" as const;
  return "slate" as const;
}

function RefundPolicyResult({ result }: { result: RefundDropPolicyEvaluationResponse }) {
  return (
    <div className="border-t border-black/10 p-4">
      <div className="grid gap-3 md:grid-cols-4">
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">Matrix</p>
          <Badge value={result.matrixStatus} label={policyStatusLabel(result.matrixStatus)} className="mt-2" />
        </div>
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">Severity</p>
          <Badge value={result.severity} label={result.severity} tone={severityTone(result.severity)} className="mt-2" />
        </div>
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">Refund</p>
          <Badge value={result.refundEligible ? "REQUIRED" : "SKIPPED"} label={result.refundEligible ? "Eligible" : "Không tự động"} className="mt-2" />
        </div>
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">Manual review</p>
          <Badge value={result.manualReviewRequired ? "MANUAL_REVIEW" : "READY"} label={result.manualReviewRequired ? "Có" : "Không"} className="mt-2" />
        </div>
      </div>
      <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-3">
        <p>Payment {result.facts.paymentStatus ?? "—"} · {result.facts.paidAmount ?? "0"} {result.facts.currency ?? ""}</p>
        <p>Promotion {result.facts.promotionStatus ?? "—"} · redemption {compactId(result.facts.redemptionId ?? undefined)}</p>
        <p>Points outstanding {result.facts.loyaltyPointsOutstanding} · reward {result.facts.rewardFulfillmentStatus ?? result.facts.rewardStatus ?? "—"}</p>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {result.reasonCodes.slice(0, 8).map((reason) => (
          <Badge key={reason} value={reason} label={reason} tone="slate" />
        ))}
      </div>
      <div className="mt-4">
        <Table>
          <thead>
            <tr>
              <Th>Domain</Th>
              <Th>Action</Th>
              <Th>Decision</Th>
              <Th>Endpoint</Th>
              <Th>Idempotency</Th>
            </tr>
          </thead>
          <tbody>
            {result.actions.map((action) => (
              <tr key={`${action.domain}-${action.action}`} className="hover:bg-slate-50">
                <Td>{action.domain}</Td>
                <Td>
                  <p className="font-semibold text-slate-900">{action.action}</p>
                  {action.makerCheckerRequired && <p className="mt-1 text-xs text-amber-700">maker-checker</p>}
                </Td>
                <Td>
                  <Badge value={action.decision} label={decisionLabel(action.decision)} tone={severityTone(action.severity)} />
                  {action.blocking && <p className="mt-1 text-xs text-slate-500">blocking</p>}
                </Td>
                <Td><span className="break-all text-xs text-slate-600">{action.endpoint ?? "—"}</span></Td>
                <Td><span className="break-all text-xs text-slate-600">{action.idempotencyKey ?? "—"}</span></Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
  detail,
  tone = "brand"
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  tone?: "brand" | "emerald" | "amber" | "sky";
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    sky: "bg-sky-50 text-sky-700"
  }[tone];

  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-md", toneClass)}>
          {icon}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

export function EnrollmentsPage() {
  const qc = useQueryClient();
  const [courseId, setCourseId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [promotionStatus, setPromotionStatus] = useState("");
  const [capacity, setCapacityValue] = useState("");
  const [enrollForm, setEnrollForm] = useState({ courseId: "", studentId: "" });
  const [waitForm, setWaitForm] = useState({ courseId: "", studentId: "" });
  const [refundPolicyForm, setRefundPolicyForm] = useState<RefundPolicyForm>(defaultRefundPolicyForm);

  const courses = useQuery({
    queryKey: queryKeys.courses.list("enrollment-picker"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const { learnerUsers: studentUsers, roleQueriesLoading, userById, usersQuery: users } = useLearnerUsers();
  const enrollments = useQuery({
    queryKey: queryKeys.enrollments.list(courseId, studentId),
    queryFn: () => listEnrollments({ courseId: courseId || undefined, studentId: studentId || undefined })
  });
  const waitlist = useQuery({
    queryKey: queryKeys.enrollments.waitlist(courseId),
    queryFn: () => listWaitlist(courseId),
    enabled: Boolean(courseId)
  });
  const stats = useQuery({
    queryKey: queryKeys.enrollments.stats(courseId),
    queryFn: () => getStats(courseId),
    enabled: Boolean(courseId)
  });
  const promotionApplicationFilters = {
    status: promotionStatus || undefined,
    courseId: courseId || undefined,
    studentId: studentId || undefined,
    limit: 25
  };
  const promotionApplications = useQuery({
    queryKey: queryKeys.enrollments.promotionApplications(promotionApplicationFilters),
    queryFn: () => listPromotionApplications(promotionApplicationFilters)
  });

  const courseById = useMemo(() => {
    const map = new Map<string, Course>();
    for (const course of courses.data ?? []) map.set(course.id, course);
    return map;
  }, [courses.data]);
  const selectedCourse = courseById.get(courseId);

  function invalidateEnrollmentData(nextCourseId = courseId) {
    qc.invalidateQueries({ queryKey: ["enrollments"] });
    if (nextCourseId) {
      qc.invalidateQueries({ queryKey: queryKeys.enrollments.stats(nextCourseId) });
      qc.invalidateQueries({ queryKey: queryKeys.enrollments.waitlist(nextCourseId) });
    }
  }

  function pickCourse(nextCourseId: string) {
    setCourseId(nextCourseId);
    setEnrollForm((current) => ({ ...current, courseId: current.courseId || nextCourseId }));
    setWaitForm((current) => ({ ...current, courseId: current.courseId || nextCourseId }));
  }

  function pickStudent(nextStudentId: string) {
    setStudentId(nextStudentId);
    setEnrollForm((current) => ({ ...current, studentId: current.studentId || nextStudentId }));
    setWaitForm((current) => ({ ...current, studentId: current.studentId || nextStudentId }));
  }

  const capacityMutation = useMutation({
    mutationFn: () => setCapacity(courseId, capacity === "" ? null : Number(capacity)),
    onSuccess: () => invalidateEnrollmentData()
  });

  const enroll = useMutation({
    mutationFn: () => createEnrollment(enrollForm),
    onSuccess: (row) => {
      setEnrollForm({ courseId: row.courseId, studentId: "" });
      invalidateEnrollmentData(row.courseId);
    }
  });

  const wait = useMutation({
    mutationFn: () => addToWaitlist(waitForm),
    onSuccess: (row) => {
      setWaitForm({ courseId: row.courseId, studentId: "" });
      invalidateEnrollmentData(row.courseId);
    }
  });

  const retryPromotionApplication = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      retryPromotionApplicationCommit(id, { reason: "Operator retry from admin enrollment ops queue" }),
    onSuccess: (row) => invalidateEnrollmentData(row.courseId)
  });

  const cancelPromotionApplication = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      cancelPromotionApplicationReservation(id, { reason: "Operator cancelled coupon hold from admin enrollment ops queue" }),
    onSuccess: (row) => invalidateEnrollmentData(row.courseId)
  });

  const evaluateRefundPolicy = useMutation({
    mutationFn: () => evaluateRefundDropPolicy(refundPolicyPayload(refundPolicyForm))
  });

  const promotionActionPending = retryPromotionApplication.isPending || cancelPromotionApplication.isPending;

  return (
    <div>
      <PageHeader
        title="Ghi danh"
        description="Quản lý enrollment, waitlist và sức chứa bằng bộ chọn khóa học, learner và trạng thái."
      />

      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Metric
          icon={<GraduationCap size={18} />}
          label="Khóa trong hệ thống"
          value={String(courses.data?.length ?? 0)}
          detail={courses.isLoading ? "Đang tải catalog" : "Dùng để lọc và ghi danh nhanh"}
        />
        <Metric
          icon={<UsersRound size={18} />}
          label="Học viên"
          value={String(studentUsers.length)}
          detail={users.isLoading || roleQueriesLoading ? "Đang phân loại learner" : "Có thể chọn để ghi danh"}
          tone="sky"
        />
        <Metric
          icon={<ListChecks size={18} />}
          label="Enrollment đang xem"
          value={String(enrollments.data?.length ?? 0)}
          detail={courseId ? courseLabel(selectedCourse, courseId) : "Tất cả khóa"}
          tone="emerald"
        />
        <Metric
          icon={<Clock3 size={18} />}
          label="Waitlist"
          value={courseId && stats.data ? String(stats.data.waitlistCount) : "—"}
          detail={courseId ? "Theo khóa đang chọn" : "Chọn một khóa để xem"}
          tone="amber"
        />
      </div>

      <Card className="mb-4">
        <CardHeader
          title="Bộ lọc"
          subtitle="Chọn theo tên khóa và học viên; bảng bên dưới vẫn hỗ trợ dữ liệu ngoài danh sách bằng ID rút gọn."
        />
        <div className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
          <FormField label="Khóa học" htmlFor="f-course">
            <Select id="f-course" value={courseId} onChange={(e) => pickCourse(e.target.value)}>
              <option value="">Tất cả khóa học</option>
              {(courses.data ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Học viên" htmlFor="f-student">
            <Select id="f-student" value={studentId} onChange={(e) => pickStudent(e.target.value)}>
              <option value="">Tất cả học viên</option>
              {studentUsers.map((user) => (
                <option key={user.id} value={String(user.id)}>
                  {userLabel(user)}
                </option>
              ))}
            </Select>
          </FormField>
          <Button
            type="button"
            variant="secondary"
            className="self-end"
            onClick={() => {
              setCourseId("");
              setStudentId("");
              setPromotionStatus("");
            }}
          >
            <Search size={16} />
            Xóa lọc
          </Button>
        </div>
        {(courses.isError || users.isError) && (
          <div className="grid gap-3 p-4 pt-0 md:grid-cols-2">
            {courses.isError && <ErrorState error={courses.error} />}
            {users.isError && <ErrorState error={users.error} />}
          </div>
        )}
      </Card>

      <Card className="mb-4">
        <CardHeader
          title="Coupon application ops"
          subtitle="Các checkout ưu đãi đang chờ retry hoặc cần hỗ trợ xử lý."
          actions={
            <Select
              value={promotionStatus}
              onChange={(event) => setPromotionStatus(event.target.value)}
              className="min-w-44"
              aria-label="Lọc trạng thái coupon application"
            >
              <option value="">Open queue</option>
              <option value="COMMIT_FAILED">Chờ retry</option>
              <option value="MANUAL_REVIEW">Cần xử lý</option>
              <option value="RESERVED">Đã giữ ưu đãi</option>
              <option value="APPLIED">Đã áp dụng</option>
              <option value="CANCELLED">Đã hủy</option>
              <option value="REVERSED">Đã đảo giao dịch</option>
            </Select>
          }
        />
        {promotionApplications.isLoading && <Spinner />}
        {promotionApplications.isError && <ErrorState error={promotionApplications.error} />}
        {retryPromotionApplication.isError && <ErrorState error={retryPromotionApplication.error} />}
        {cancelPromotionApplication.isError && <ErrorState error={cancelPromotionApplication.error} />}
        {promotionApplications.data && promotionApplications.data.length === 0 && (
          <EmptyState message="Không có coupon application cần xử lý theo bộ lọc hiện tại." />
        )}
        {promotionApplications.data && promotionApplications.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Trạng thái</Th>
                <Th>Khóa học</Th>
                <Th>Học viên</Th>
                <Th>Coupon</Th>
                <Th>Lý do</Th>
                <Th>Cập nhật</Th>
                <Th>Xử lý</Th>
              </tr>
            </thead>
            <tbody>
              {promotionApplications.data.map((row) => {
                const course = courseById.get(row.courseId);
                const user = userById.get(row.studentId);
                return (
                  <tr key={row.id} className="hover:bg-slate-50">
                    <Td>
                      <div className="flex flex-col gap-1">
                        <Badge value={row.status} label={promotionStatusLabel(row.status)} />
                        <span className="text-xs text-slate-500">Enrollment {compactId(row.enrollmentId)}</span>
                      </div>
                    </Td>
                    <Td>
                      <p className="font-semibold text-slate-900">{courseLabel(course, row.courseId)}</p>
                      <p className="mt-1 text-xs text-slate-500">ID {compactId(row.courseId)}</p>
                    </Td>
                    <Td>
                      <p className="font-semibold text-slate-900">{user?.fullName ?? `User ${compactId(row.studentId)}`}</p>
                      <p className="mt-1 text-xs text-slate-500">{user?.email ?? `ID ${compactId(row.studentId)}`}</p>
                    </Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <TicketPercent size={16} className="text-brand-600" />
                        <div>
                          <p className="font-semibold text-slate-900">{row.couponCode || compactId(row.couponId ?? undefined) || "Coupon"}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            Reservation {compactId(row.reservationId ?? undefined)}
                          </p>
                        </div>
                      </div>
                    </Td>
                    <Td>
                      <p className="max-w-xs text-sm text-slate-700">{row.message ?? reasonSummary(row.reasonCodes)}</p>
                      {row.message && <p className="mt-1 max-w-xs text-xs text-slate-500">{reasonSummary(row.reasonCodes)}</p>}
                      {(row.retryCount > 0 || row.nextRetryAt || row.lastRetryError) && (
                        <div className="mt-2 rounded-md border border-amber-100 bg-amber-50 px-2 py-1.5 text-xs text-amber-800">
                          <p className="font-semibold">Retry {row.retryCount} · next {formatDateTime(row.nextRetryAt)}</p>
                          {row.lastRetryError && <p className="mt-0.5 text-amber-700">{row.lastRetryError}</p>}
                        </div>
                      )}
                    </Td>
                    <Td>
                      <p className="text-xs text-slate-500">
                        {formatDateTime(row.updatedAt)}
                      </p>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="xs"
                          variant="secondary"
                          disabled={!canRemediatePromotion(row.status) || promotionActionPending}
                          onClick={() => {
                            if (window.confirm("Retry commit coupon application này?")) {
                              retryPromotionApplication.mutate({ id: row.id });
                            }
                          }}
                        >
                          <RefreshCcw size={14} />
                          Retry
                        </Button>
                        <Button
                          size="xs"
                          variant="danger"
                          disabled={!canRemediatePromotion(row.status) || promotionActionPending}
                          onClick={() => {
                            if (window.confirm("Cancel coupon reservation này? Enrollment đang active sẽ bị backend chặn.")) {
                              cancelPromotionApplication.mutate({ id: row.id });
                            }
                          }}
                        >
                          <Ban size={14} />
                          Cancel hold
                        </Button>
                      </div>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card>

      <Card className="mb-4">
        <CardHeader
          title="Refund/drop policy matrix"
          subtitle="Dry-run drop, refund, discount reversal, points clawback và reward reversal theo facts hiện có."
        />
        <form
          className="space-y-4 p-4"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            evaluateRefundPolicy.mutate();
          }}
        >
          <div className="grid gap-3 lg:grid-cols-4">
            <FormField label="Enrollment ID" htmlFor="policy-enrollment">
              <Input
                id="policy-enrollment"
                list="policy-enrollment-options"
                value={refundPolicyForm.enrollmentId}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, enrollmentId: event.target.value })}
                placeholder="UUID"
                required
              />
              <datalist id="policy-enrollment-options">
                {(enrollments.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.status} · {row.studentId}
                  </option>
                ))}
              </datalist>
            </FormField>
            <FormField label="Reason" htmlFor="policy-reason">
              <Input
                id="policy-reason"
                value={refundPolicyForm.reason}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, reason: event.target.value })}
              />
            </FormField>
            <FormField label="Refund window" htmlFor="policy-window">
              <Input
                id="policy-window"
                type="number"
                min={0}
                max={365}
                value={refundPolicyForm.refundWindowDays}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, refundWindowDays: event.target.value })}
              />
            </FormField>
            <FormField label="Payment override" htmlFor="policy-payment">
              <Select
                id="policy-payment"
                value={refundPolicyForm.paymentStatus}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, paymentStatus: event.target.value })}
              >
                <option value="">Dùng order hiện có</option>
                <option value="PAID">PAID</option>
                <option value="PAYMENT_PENDING">PAYMENT_PENDING</option>
                <option value="PAYMENT_FAILED">PAYMENT_FAILED</option>
                <option value="EXPIRED">EXPIRED</option>
                <option value="MANUAL_REVIEW">MANUAL_REVIEW</option>
              </Select>
            </FormField>
          </div>
          <div className="grid gap-3 lg:grid-cols-4">
            <FormField label="Paid amount" htmlFor="policy-paid-amount">
              <Input
                id="policy-paid-amount"
                type="number"
                min={0}
                step="0.01"
                value={refundPolicyForm.paidAmount}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, paidAmount: event.target.value })}
                placeholder="Auto"
              />
            </FormField>
            <FormField label="Currency" htmlFor="policy-currency">
              <Input
                id="policy-currency"
                value={refundPolicyForm.currency}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, currency: event.target.value.toUpperCase() })}
              />
            </FormField>
            <FormField label="Paid at" htmlFor="policy-paid-at">
              <Input
                id="policy-paid-at"
                type="datetime-local"
                value={refundPolicyForm.paidAt}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, paidAt: event.target.value })}
              />
            </FormField>
            <FormField label="Promotion override" htmlFor="policy-promotion">
              <Select
                id="policy-promotion"
                value={refundPolicyForm.promotionStatus}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, promotionStatus: event.target.value })}
              >
                <option value="">Dùng application hiện có</option>
                <option value="RESERVED">RESERVED</option>
                <option value="APPLIED">APPLIED</option>
                <option value="COMMIT_FAILED">COMMIT_FAILED</option>
                <option value="REVERSED">REVERSED</option>
                <option value="CANCELLED">CANCELLED</option>
                <option value="MANUAL_REVIEW">MANUAL_REVIEW</option>
                <option value="SKIPPED">SKIPPED</option>
              </Select>
            </FormField>
          </div>
          <div className="grid gap-3 lg:grid-cols-4">
            <FormField label="Reservation ID" htmlFor="policy-reservation">
              <Input
                id="policy-reservation"
                value={refundPolicyForm.reservationId}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, reservationId: event.target.value })}
                placeholder="Auto"
              />
            </FormField>
            <FormField label="Redemption ID" htmlFor="policy-redemption">
              <Input
                id="policy-redemption"
                value={refundPolicyForm.redemptionId}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, redemptionId: event.target.value })}
                placeholder="Auto"
              />
            </FormField>
            <FormField label="Points earned" htmlFor="policy-points-earned">
              <Input
                id="policy-points-earned"
                type="number"
                min={0}
                value={refundPolicyForm.loyaltyPointsEarned}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, loyaltyPointsEarned: event.target.value })}
              />
            </FormField>
            <FormField label="Points reversed" htmlFor="policy-points-reversed">
              <Input
                id="policy-points-reversed"
                type="number"
                min={0}
                value={refundPolicyForm.loyaltyPointsReversed}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, loyaltyPointsReversed: event.target.value })}
              />
            </FormField>
          </div>
          <div className="grid gap-3 lg:grid-cols-4">
            <FormField label="Earn entry ID" htmlFor="policy-earn-entry">
              <Input
                id="policy-earn-entry"
                value={refundPolicyForm.loyaltyEarnEntryId}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, loyaltyEarnEntryId: event.target.value })}
              />
            </FormField>
            <FormField label="Reward status" htmlFor="policy-reward-status">
              <Select
                id="policy-reward-status"
                value={refundPolicyForm.rewardStatus}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, rewardStatus: event.target.value })}
              >
                <option value="">Không có reward</option>
                <option value="COMMITTED">COMMITTED</option>
                <option value="REVERSED">REVERSED</option>
                <option value="FAILED">FAILED</option>
              </Select>
            </FormField>
            <FormField label="Reward redemption" htmlFor="policy-reward-redemption">
              <Input
                id="policy-reward-redemption"
                value={refundPolicyForm.rewardRedemptionId}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, rewardRedemptionId: event.target.value })}
              />
            </FormField>
            <FormField label="Fulfillment" htmlFor="policy-fulfillment">
              <Select
                id="policy-fulfillment"
                value={refundPolicyForm.rewardFulfillmentStatus}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, rewardFulfillmentStatus: event.target.value })}
              >
                <option value="">Không có</option>
                <option value="PENDING">PENDING</option>
                <option value="ISSUED">ISSUED</option>
                <option value="MANUAL_REQUIRED">MANUAL_REQUIRED</option>
                <option value="FAILED">FAILED</option>
              </Select>
            </FormField>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700">
              <input
                type="checkbox"
                checked={refundPolicyForm.rewardFulfilled}
                onChange={(event) => setRefundPolicyForm({ ...refundPolicyForm, rewardFulfilled: event.target.checked })}
                className="size-4 rounded border-slate-300 text-brand-600"
              />
              Reward fulfilled
            </label>
            <Button type="submit" disabled={evaluateRefundPolicy.isPending || !refundPolicyForm.enrollmentId.trim()}>
              <ListChecks size={16} />
              {evaluateRefundPolicy.isPending ? "Đang chạy" : "Run matrix"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setRefundPolicyForm(defaultRefundPolicyForm);
                evaluateRefundPolicy.reset();
              }}
            >
              Clear
            </Button>
          </div>
          {evaluateRefundPolicy.isError && <ErrorState error={evaluateRefundPolicy.error} />}
        </form>
        {evaluateRefundPolicy.data && <RefundPolicyResult result={evaluateRefundPolicy.data} />}
      </Card>

      {courseId && (
        <Card className="mb-4">
          <CardHeader
            title="Thống kê & sức chứa"
            subtitle={courseLabel(selectedCourse, courseId)}
          />
          <div className="grid gap-4 p-4 xl:grid-cols-[1fr_360px]">
            {stats.isLoading && <Spinner />}
            {stats.isError && <ErrorState error={stats.error} />}
            {stats.data && (
              <div className="grid gap-3 sm:grid-cols-4">
                <Metric icon={<UsersRound size={18} />} label="Đang học" value={String(stats.data.totalActive)} detail="Enrollment active" tone="emerald" />
                <Metric icon={<Clock3 size={18} />} label="Waitlist" value={String(stats.data.waitlistCount)} detail="Đang chờ chỗ" tone="amber" />
                <Metric icon={<GraduationCap size={18} />} label="Hoàn thành" value={String(stats.data.totalCompleted)} detail="Đã hoàn tất khóa" tone="brand" />
                <Metric icon={<ListChecks size={18} />} label="Đã rời" value={String(stats.data.totalDropped)} detail="Dropped" tone="sky" />
              </div>
            )}
            <form
              className="rounded-lg border border-black/10 bg-slate-50 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                capacityMutation.mutate();
              }}
            >
              <FormField label="Sức chứa" htmlFor="cap-value" hint="Để trống nếu khóa không giới hạn số lượng học viên.">
                <Input
                  id="cap-value"
                  type="number"
                  min={0}
                  value={capacity}
                  onChange={(e) => setCapacityValue(e.target.value)}
                  placeholder="Không giới hạn"
                />
              </FormField>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button type="submit" variant="secondary" disabled={capacityMutation.isPending}>
                  {capacityMutation.isPending ? "Đang lưu" : "Đặt sức chứa"}
                </Button>
                {capacityMutation.isSuccess && <span className="text-sm font-semibold text-emerald-600">Đã cập nhật</span>}
              </div>
              {capacityMutation.isError && <ErrorState error={capacityMutation.error} />}
            </form>
          </div>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <Card>
          <CardHeader title="Enrollment" subtitle={`${enrollments.data?.length ?? 0} bản ghi đang hiển thị`} />
          {enrollments.isLoading && <Spinner />}
          {enrollments.isError && <ErrorState error={enrollments.error} />}
          {enrollments.data && enrollments.data.length === 0 && <EmptyState message="Không có enrollment phù hợp." />}
          {enrollments.data && enrollments.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Khóa học</Th>
                  <Th>Học viên</Th>
                  <Th>Trạng thái</Th>
                  <Th>Mốc thời gian</Th>
                  <Th>Policy</Th>
                </tr>
              </thead>
              <tbody>
                {enrollments.data.map((row) => {
                  const course = courseById.get(row.courseId);
                  const user = userById.get(row.studentId);
                  return (
                    <tr key={row.id} className="hover:bg-slate-50">
                      <Td>
                        <p className="font-semibold text-slate-900">{courseLabel(course, row.courseId)}</p>
                        <p className="mt-1 text-xs text-slate-500">ID {compactId(row.courseId)}</p>
                      </Td>
                      <Td>
                        <p className="font-semibold text-slate-900">{user?.fullName ?? `User ${compactId(row.studentId)}`}</p>
                        <p className="mt-1 text-xs text-slate-500">{user?.email ?? `ID ${compactId(row.studentId)}`}</p>
                      </Td>
                      <Td>
                        <Badge value={row.status} label={enrollmentStatusLabel(row.status)} />
                      </Td>
                      <Td>
                        <p className="text-xs text-slate-500">
                          {row.enrolledAt ? `Ghi danh ${new Date(row.enrolledAt).toLocaleDateString("vi-VN")}` : "Chưa có ngày"}
                        </p>
                        {row.completedAt && <p className="mt-1 text-xs text-emerald-600">Hoàn thành {new Date(row.completedAt).toLocaleDateString("vi-VN")}</p>}
                        {row.droppedAt && <p className="mt-1 text-xs text-red-600">Rời khóa {new Date(row.droppedAt).toLocaleDateString("vi-VN")}</p>}
                      </Td>
                      <Td>
                        <Button
                          type="button"
                          size="xs"
                          variant="secondary"
                          onClick={() => {
                            setRefundPolicyForm((current) => ({ ...current, enrollmentId: row.id }));
                            evaluateRefundPolicy.reset();
                          }}
                        >
                          <ListChecks size={14} />
                          Matrix
                        </Button>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Ghi danh học viên" subtitle="Chọn course và student, hệ thống sẽ tạo enrollment active." />
            <form
              className="space-y-4 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                enroll.mutate();
              }}
            >
              <FormField label="Khóa học" htmlFor="e-course">
                <Select
                  id="e-course"
                  value={enrollForm.courseId}
                  onChange={(e) => setEnrollForm({ ...enrollForm, courseId: e.target.value })}
                  required
                >
                  <option value="">Chọn khóa học</option>
                  {(courses.data ?? []).map((course) => (
                    <option key={course.id} value={course.id}>{courseLabel(course)}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Học viên" htmlFor="e-student">
                <Select
                  id="e-student"
                  value={enrollForm.studentId}
                  onChange={(e) => setEnrollForm({ ...enrollForm, studentId: e.target.value })}
                  required
                >
                  <option value="">Chọn học viên</option>
                  {studentUsers.map((user) => (
                    <option key={user.id} value={String(user.id)}>{userLabel(user)}</option>
                  ))}
                </Select>
              </FormField>
              {enroll.isError && <ErrorState error={enroll.error} />}
              <Button type="submit" disabled={enroll.isPending || !enrollForm.courseId || !enrollForm.studentId}>
                <UserPlus size={16} />
                {enroll.isPending ? "Đang lưu" : "Ghi danh"}
              </Button>
            </form>
          </Card>

          <Card>
            <CardHeader title="Waitlist" subtitle={courseId ? courseLabel(selectedCourse, courseId) : "Chọn khóa ở bộ lọc để xem waitlist."} />
            {!courseId && <EmptyState message="Chọn một khóa học để xem danh sách chờ." />}
            {courseId && waitlist.isLoading && <Spinner />}
            {courseId && waitlist.isError && <ErrorState error={waitlist.error} />}
            {courseId && waitlist.data && waitlist.data.length === 0 && <EmptyState message="Không có waitlist cho khóa này." />}
            {courseId && waitlist.data && waitlist.data.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Vị trí</Th>
                    <Th>Học viên</Th>
                    <Th>Trạng thái</Th>
                  </tr>
                </thead>
                <tbody>
                  {waitlist.data.map((row) => {
                    const user = userById.get(row.studentId);
                    return (
                      <tr key={row.id}>
                        <Td>#{row.position ?? "—"}</Td>
                        <Td>
                          <p className="font-semibold text-slate-900">{user?.fullName ?? `User ${compactId(row.studentId)}`}</p>
                          <p className="mt-1 text-xs text-slate-500">{user?.email ?? `ID ${compactId(row.studentId)}`}</p>
                        </Td>
                        <Td><Badge value={row.status} label={waitlistStatusLabel(row.status)} /></Td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <CardHeader title="Thêm vào waitlist" subtitle="Dùng khi khóa đã đầy hoặc cần duyệt sau." />
            <form
              className="space-y-4 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                wait.mutate();
              }}
            >
              <FormField label="Khóa học" htmlFor="w-course">
                <Select
                  id="w-course"
                  value={waitForm.courseId}
                  onChange={(e) => setWaitForm({ ...waitForm, courseId: e.target.value })}
                  required
                >
                  <option value="">Chọn khóa học</option>
                  {(courses.data ?? []).map((course) => (
                    <option key={course.id} value={course.id}>{courseLabel(course)}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Học viên" htmlFor="w-student">
                <Select
                  id="w-student"
                  value={waitForm.studentId}
                  onChange={(e) => setWaitForm({ ...waitForm, studentId: e.target.value })}
                  required
                >
                  <option value="">Chọn học viên</option>
                  {studentUsers.map((user) => (
                    <option key={user.id} value={String(user.id)}>{userLabel(user)}</option>
                  ))}
                </Select>
              </FormField>
              {wait.isError && <ErrorState error={wait.error} />}
              <Button type="submit" variant="secondary" disabled={wait.isPending || !waitForm.courseId || !waitForm.studentId}>
                {wait.isPending ? "Đang lưu" : "Thêm waitlist"}
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
