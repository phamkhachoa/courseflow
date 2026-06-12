"use client";

import { FormEvent, useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  FileCheck2,
  Inbox,
  LockKeyhole,
  MessageSquareText,
  Send,
  ShieldCheck,
  Star,
  UsersRound
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ProgressBar,
  SelectInput,
  Textarea,
  TextInput,
  cn
} from "@/shared/ui";
import {
  getPeerReviewSettings,
  listMyReviewAssignments,
  submitPeerReview,
  type PeerReviewSettings,
  type ReviewAssignment,
  type ReviewSubmission
} from "./api";

const DRAFT_PREFIX = "courseflow.peerReview.draft";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function formatDateTime(value?: string) {
  if (!value) return "Chưa đặt";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa đặt";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    ASSIGNED: "Đang chờ đánh giá",
    REVIEWED: "Đã đánh giá",
    SUBMITTED: "Đã gửi",
    CLOSED: "Đã đóng",
    ACTIVE: "Đang mở",
    DRAFT: "Nháp"
  };
  return labels[status ?? ""] ?? status ?? "Đang chờ";
}

function statusTone(status?: string): "brand" | "amber" | "coral" | "sky" | "neutral" {
  if (status === "REVIEWED" || status === "SUBMITTED") return "brand";
  if (status === "ASSIGNED" || status === "ACTIVE") return "sky";
  if (status === "CLOSED") return "coral";
  if (status === "DRAFT") return "amber";
  return "neutral";
}

function dueState(settings?: PeerReviewSettings) {
  const dueAt = settings?.reviewDueAt ? new Date(settings.reviewDueAt).getTime() : 0;
  const reviewers = settings?.reviewersPerSubmission ?? 0;
  const now = Date.now();

  if (dueAt && now > dueAt) {
    return {
      label: "Đã quá hạn",
      detail: `Hạn đánh giá ${formatDateTime(settings?.reviewDueAt)}`,
      tone: "coral" as const,
      icon: LockKeyhole
    };
  }
  if (dueAt && dueAt - now < 24 * 60 * 60 * 1000) {
    return {
      label: "Sắp đến hạn",
      detail: `Cần gửi trước ${formatDateTime(settings?.reviewDueAt)}`,
      tone: "amber" as const,
      icon: Clock3
    };
  }
  return {
    label: "Đang mở",
    detail: dueAt ? `Hạn đánh giá ${formatDateTime(settings?.reviewDueAt)}` : "Chưa đặt hạn đánh giá",
    tone: "brand" as const,
    icon: reviewers > 0 ? UsersRound : ClipboardCheck
  };
}

function ScoreGuide({ score }: { score: number }) {
  const rows = [
    { label: "90-100", detail: "Xuất sắc, đáp ứng đầy đủ và có phân tích sâu" },
    { label: "70-89", detail: "Tốt, còn vài điểm cần làm rõ hoặc hoàn thiện" },
    { label: "50-69", detail: "Đạt một phần, thiếu bằng chứng hoặc triển khai chưa chắc" },
    { label: "0-49", detail: "Chưa đạt yêu cầu cốt lõi của bài nộp" }
  ];

  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const [min, max] = row.label.split("-").map(Number);
        const active = score >= min && score <= max;
        return (
          <div
            key={row.label}
            className={cn(
              "rounded-lg border p-3 text-sm",
              active ? "border-brand-200 bg-brand-50 text-brand-800" : "border-black/10 bg-white text-ink-600"
            )}
          >
            <p className="font-bold">{row.label} điểm</p>
            <p className="mt-1 leading-5">{row.detail}</p>
          </div>
        );
      })}
    </div>
  );
}

function ReviewStat({
  icon,
  label,
  value
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="flex items-center gap-2 text-xs font-bold uppercase text-ink-500">
        {icon}
        {label}
      </div>
      <p className="mt-2 text-sm font-semibold text-ink-900">{value}</p>
    </div>
  );
}

function AssignmentCard({
  assignment,
  active,
  onSelect
}: {
  assignment: ReviewAssignment;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border p-4 text-left transition",
        active ? "border-brand-200 bg-brand-50 shadow-sm" : "border-black/10 bg-white hover:border-brand-200 hover:bg-brand-50/50"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase text-brand-600">Lượt chấm</p>
          <h3 className="mt-1 font-bold text-ink-900">Review {compactId(assignment.id)}</h3>
          <p className="mt-2 text-sm leading-5 text-ink-500">
            Submission {compactId(assignment.submissionId)}
          </p>
        </div>
        <Badge tone={statusTone(assignment.status)}>{statusLabel(assignment.status)}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold text-ink-500">
        <span>Được giao {formatDateTime(assignment.assignedAt)}</span>
        {assignment.courseId && <span>Course {compactId(assignment.courseId)}</span>}
      </div>
    </button>
  );
}

function ResultSummary({ result }: { result: ReviewSubmission }) {
  return (
    <div className="rounded-lg border border-brand-100 bg-brand-50 p-4">
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-white text-brand-700">
          <CheckCircle2 className="size-5" />
        </span>
        <div>
          <p className="font-bold text-brand-900">Đã gửi đánh giá</p>
          <p className="mt-1 text-sm leading-6 text-brand-800">
            Điểm {result.score ?? "--"} · {formatDateTime(result.submittedAt)}
          </p>
          {result.comment && <p className="mt-2 text-sm leading-6 text-brand-800">{result.comment}</p>}
        </div>
      </div>
    </div>
  );
}

export function PeerReviewView({ assignmentId }: { assignmentId: string }) {
  const qc = useQueryClient();
  const { session, hydrated } = useLearnerSession();
  const [form, setForm] = useState({ reviewAssignmentId: "", score: 80, comment: "" });
  const [draftReady, setDraftReady] = useState(false);
  const userId = session?.user.id ? String(session.user.id) : "";
  const draftKey = `${DRAFT_PREFIX}.${assignmentId}`;

  const settings = useQuery({
    queryKey: ["peer-review-settings", assignmentId],
    queryFn: () => getPeerReviewSettings(assignmentId),
    enabled: Boolean(assignmentId && userId)
  });
  const mine = useQuery({
    queryKey: ["peer-review-assignments", userId],
    queryFn: listMyReviewAssignments,
    enabled: Boolean(userId)
  });

  const relevantAssignments = useMemo(
    () => (mine.data ?? []).filter((item) => item.assignmentId === assignmentId),
    [assignmentId, mine.data]
  );
  const selectedAssignment = relevantAssignments.find((item) => item.id === form.reviewAssignmentId);
  const state = dueState(settings.data);
  const StateIcon = state.icon;
  const progressValue = Math.max(0, Math.min(100, form.score));
  const commentLength = form.comment.trim().length;
  const scoreValid = form.score >= 0 && form.score <= 100;
  const dueClosed = state.label === "Đã quá hạn";
  const canSubmit = Boolean(form.reviewAssignmentId && scoreValid && commentLength >= 10 && !dueClosed);

  const submit = useMutation({
    mutationFn: () =>
      submitPeerReview(form.reviewAssignmentId, {
        score: form.score,
        comment: form.comment.trim()
      }),
    onSuccess: () => {
      localStorage.removeItem(draftKey);
      qc.invalidateQueries({ queryKey: ["peer-review-assignments", userId] });
    }
  });

  useEffect(() => {
    if (!hydrated) return;
    try {
      const raw = localStorage.getItem(draftKey);
      if (raw) {
        const draft = JSON.parse(raw) as Partial<typeof form>;
        setForm((current) => ({ ...current, ...draft }));
      }
    } catch {
      localStorage.removeItem(draftKey);
    } finally {
      setDraftReady(true);
    }
  }, [draftKey, hydrated]);

  useEffect(() => {
    if (!draftReady || form.reviewAssignmentId) return;
    const pending = relevantAssignments.find((item) => item.status !== "REVIEWED") ?? relevantAssignments[0];
    if (pending) setForm((current) => ({ ...current, reviewAssignmentId: pending.id }));
  }, [draftReady, form.reviewAssignmentId, relevantAssignments]);

  useEffect(() => {
    if (!draftReady) return;
    const hasDraft = form.reviewAssignmentId || form.comment.trim() || form.score !== 80;
    if (!hasDraft) {
      localStorage.removeItem(draftKey);
      return;
    }
    localStorage.setItem(draftKey, JSON.stringify(form));
  }, [draftKey, draftReady, form]);

  if (!hydrated) {
    return (
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <div className="h-[360px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
        <div className="h-[420px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
      </div>
    );
  }

  if (!userId) {
    return (
      <Card>
        <p className="text-sm font-medium text-amber-700">Bạn cần đăng nhập để xem và nộp đánh giá đồng cấp.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3">
        <ReviewStat
          icon={<UsersRound className="size-4" />}
          label="Reviewer / bài"
          value={`${settings.data?.reviewersPerSubmission ?? "--"} người`}
        />
        <ReviewStat
          icon={<ShieldCheck className="size-4" />}
          label="Ẩn danh"
          value={settings.data?.anonymous ? "Có" : "Không"}
        />
        <ReviewStat
          icon={<Clock3 className="size-4" />}
          label="Hạn đánh giá"
          value={formatDateTime(settings.data?.reviewDueAt)}
        />
      </div>

      <Card className="overflow-hidden" padding="none">
        <div className="grid gap-0 lg:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="border-b border-black/10 bg-[#fbfaf7] p-4 lg:border-b-0 lg:border-r">
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
                <Inbox className="size-5" />
              </span>
              <div>
                <h2 className="font-bold text-ink-900">Queue được giao</h2>
                <p className="mt-1 text-sm leading-6 text-ink-500">
                  Chọn lượt chấm để điền nhận xét. Nếu giảng viên gửi mã riêng, dùng mục nhập thủ công bên dưới.
                </p>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {mine.isLoading &&
                Array.from({ length: 2 }).map((_, index) => (
                  <div key={index} className="h-[112px] animate-pulse rounded-lg border border-black/10 bg-white" />
                ))}
              {mine.isError && (
                <div className="rounded-lg border border-coral-100 bg-coral-50 p-3 text-sm font-medium text-coral-600">
                  Không tải được queue chấm chéo.
                </div>
              )}
              {!mine.isLoading && relevantAssignments.length === 0 && (
                <EmptyState
                  title="Chưa có lượt chấm"
                  description="Khi giảng viên phân công peer review cho bài này, lượt chấm sẽ xuất hiện ở đây."
                />
              )}
              {relevantAssignments.map((item) => (
                <AssignmentCard
                  key={item.id}
                  assignment={item}
                  active={item.id === form.reviewAssignmentId}
                  onSelect={() => setForm((current) => ({ ...current, reviewAssignmentId: item.id }))}
                />
              ))}
            </div>
          </aside>

          <section className="space-y-5 p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={state.tone}>
                    <StateIcon className="mr-1 size-3.5" />
                    {state.label}
                  </Badge>
                  {settings.data?.status && (
                    <Badge tone={statusTone(settings.data.status)}>{statusLabel(settings.data.status)}</Badge>
                  )}
                  {selectedAssignment?.status && (
                    <Badge tone={statusTone(selectedAssignment.status)}>{statusLabel(selectedAssignment.status)}</Badge>
                  )}
                </div>
                <h2 className="mt-3 text-2xl font-bold text-ink-900">Nộp đánh giá đồng cấp</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">{state.detail}</p>
              </div>
              <div className="rounded-lg border border-black/10 bg-white p-3 text-sm">
                <p className="font-bold text-ink-900">{progressValue}/100</p>
                <p className="mt-1 text-ink-500">Điểm đề xuất</p>
              </div>
            </div>

            {settings.isError && (
              <div className="rounded-lg border border-amber-100 bg-amber-50 p-3 text-sm font-medium text-amber-700">
                Không tải được cấu hình peer review. Bạn vẫn có thể gửi nếu có mã lượt chấm hợp lệ.
              </div>
            )}

            {submit.isSuccess && submit.data && <ResultSummary result={submit.data} />}

            <form
              className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]"
              onSubmit={(event: FormEvent) => {
                event.preventDefault();
                if (canSubmit) submit.mutate();
              }}
            >
              <div className="space-y-4">
                <label className="block text-sm font-semibold text-ink-700">
                  Lượt chấm
                  <SelectInput
                    value={form.reviewAssignmentId}
                    onChange={(event) => setForm((current) => ({ ...current, reviewAssignmentId: event.target.value }))}
                    className="mt-2"
                    required
                  >
                    <option value="">Chọn lượt chấm được giao</option>
                    {relevantAssignments.map((item) => (
                      <option key={item.id} value={item.id}>
                        Review {compactId(item.id)} · Submission {compactId(item.submissionId)} · {statusLabel(item.status)}
                      </option>
                    ))}
                    {form.reviewAssignmentId && !selectedAssignment && (
                      <option value={form.reviewAssignmentId}>Review {compactId(form.reviewAssignmentId)}</option>
                    )}
                  </SelectInput>
                </label>

                <details className="rounded-lg border border-dashed border-black/15 bg-white p-3 text-sm text-ink-600">
                  <summary className="cursor-pointer font-semibold text-ink-800">Nhập mã lượt chấm thủ công</summary>
                  <label className="mt-3 block text-sm font-semibold text-ink-700">
                    Review assignment ID
                    <TextInput
                      value={form.reviewAssignmentId}
                      onChange={(event) => setForm((current) => ({ ...current, reviewAssignmentId: event.target.value.trim() }))}
                      className="mt-2 font-mono text-xs"
                      placeholder="UUID lượt chấm chéo"
                    />
                  </label>
                </details>

                <div className="rounded-lg border border-black/10 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <label className="text-sm font-semibold text-ink-700" htmlFor="peer-score">
                      Điểm đánh giá
                    </label>
                    <span className={cn("text-sm font-bold", scoreValid ? "text-brand-700" : "text-coral-600")}>
                      {form.score}/100
                    </span>
                  </div>
                  <input
                    id="peer-score"
                    type="range"
                    min={0}
                    max={100}
                    step={1}
                    value={form.score}
                    onChange={(event) => setForm((current) => ({ ...current, score: Number(event.target.value) }))}
                    className="mt-4 w-full accent-brand-600"
                  />
                  <ProgressBar value={progressValue} />
                  <TextInput
                    type="number"
                    min={0}
                    max={100}
                    value={form.score}
                    onChange={(event) => setForm((current) => ({ ...current, score: Number(event.target.value) }))}
                    className="mt-3 max-w-36"
                  />
                  {!scoreValid && <p className="mt-2 text-sm font-medium text-coral-600">Điểm phải nằm trong khoảng 0-100.</p>}
                </div>

                <label className="block text-sm font-semibold text-ink-700">
                  Nhận xét cho bạn học
                  <Textarea
                    value={form.comment}
                    onChange={(event) => setForm((current) => ({ ...current, comment: event.target.value }))}
                    placeholder="Nêu điểm mạnh, điểm cần cải thiện và gợi ý hành động tiếp theo..."
                    rows={8}
                    className="mt-2"
                    required
                  />
                </label>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs font-medium text-ink-500">
                    Bản nháp tự lưu trên trình duyệt này · {commentLength} ký tự
                  </p>
                  {commentLength > 0 && commentLength < 10 && (
                    <p className="text-xs font-semibold text-amber-600">Viết ít nhất 10 ký tự để gửi nhận xét có ý nghĩa.</p>
                  )}
                </div>

                {dueClosed && (
                  <div className="rounded-lg border border-coral-100 bg-coral-50 p-3 text-sm font-medium text-coral-600">
                    <AlertTriangle className="mr-2 inline size-4" />
                    Hạn đánh giá đã qua. Backend sẽ từ chối lượt gửi mới.
                  </div>
                )}
                {submit.isError && (
                  <div className="rounded-lg border border-coral-100 bg-coral-50 p-3 text-sm font-medium text-coral-600">
                    {submit.error instanceof Error ? submit.error.message : "Gửi đánh giá thất bại."}
                  </div>
                )}
                <Button type="submit" disabled={submit.isPending || !canSubmit}>
                  <Send className="size-4" />
                  {submit.isPending ? "Đang gửi..." : "Gửi đánh giá"}
                </Button>
              </div>

              <aside className="space-y-4">
                <Card className="bg-[#fbfaf7]" padding="md">
                  <div className="flex items-center gap-2 text-sm font-bold text-ink-900">
                    <FileCheck2 className="size-4 text-brand-600" />
                    Checklist nhận xét
                  </div>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-ink-600">
                    <li className="flex gap-2">
                      <CheckCircle2 className="mt-1 size-4 shrink-0 text-brand-600" />
                      Đưa ra bằng chứng từ bài nộp, không chỉ nhận xét chung chung.
                    </li>
                    <li className="flex gap-2">
                      <CheckCircle2 className="mt-1 size-4 shrink-0 text-brand-600" />
                      Nêu ít nhất một điểm mạnh và một điểm cần cải thiện.
                    </li>
                    <li className="flex gap-2">
                      <CheckCircle2 className="mt-1 size-4 shrink-0 text-brand-600" />
                      Giữ giọng văn tôn trọng, tập trung vào sản phẩm học tập.
                    </li>
                  </ul>
                </Card>

                <Card padding="md">
                  <div className="mb-3 flex items-center gap-2 text-sm font-bold text-ink-900">
                    <Star className="size-4 text-accent-600" />
                    Thang điểm
                  </div>
                  <ScoreGuide score={form.score} />
                </Card>

                {selectedAssignment && (
                  <Card padding="md">
                    <div className="mb-3 flex items-center gap-2 text-sm font-bold text-ink-900">
                      <MessageSquareText className="size-4 text-signal-600" />
                      Thông tin lượt chấm
                    </div>
                    <dl className="grid grid-cols-[110px_1fr] gap-y-2 text-sm">
                      <dt className="text-ink-500">Submission</dt>
                      <dd className="font-semibold text-ink-900">{compactId(selectedAssignment.submissionId)}</dd>
                      <dt className="text-ink-500">Reviewee</dt>
                      <dd className="font-semibold text-ink-900">{compactId(selectedAssignment.revieweeId)}</dd>
                      <dt className="text-ink-500">Giao lúc</dt>
                      <dd className="font-semibold text-ink-900">{formatDateTime(selectedAssignment.assignedAt)}</dd>
                    </dl>
                  </Card>
                )}
              </aside>
            </form>
          </section>
        </div>
      </Card>
    </div>
  );
}
