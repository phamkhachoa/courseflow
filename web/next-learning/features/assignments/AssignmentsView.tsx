"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  ExternalLink,
  FileCheck2,
  History,
  Link2,
  LockKeyhole,
  PenLine,
  RotateCcw,
  Send,
  TimerReset,
  Trophy
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Textarea,
  TextInput,
  cn
} from "@/shared/ui";
import {
  getAssignment,
  listAssignments,
  listMySubmissions,
  submitAssignment,
  type Assignment,
  type Submission
} from "./api";

function statusLabel(status: string): string {
  if (status === "GRADED") return "ĐÃ CHẤM";
  if (status === "LATE") return "NỘP MUỘN";
  if (status === "SUBMITTED") return "ĐÃ NỘP";
  return status;
}

function statusTone(status: string): "brand" | "amber" | "coral" | "sky" | "neutral" {
  if (status === "GRADED") return "brand";
  if (status === "LATE") return "coral";
  if (status === "SUBMITTED") return "sky";
  return "neutral";
}

function formatDateTime(value?: string): string {
  if (!value) return "Chưa đặt";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function scoreLabel(value?: number, maxScore?: number): string {
  if (value == null) return maxScore != null ? `-- / ${maxScore}` : "--";
  return maxScore != null ? `${value} / ${maxScore}` : String(value);
}

function assignmentTypeLabel(type?: string): string {
  const normalized = (type ?? "").toUpperCase();
  if (normalized.includes("PROJECT")) return "Dự án";
  if (normalized.includes("PEER")) return "Peer review";
  if (normalized.includes("ESSAY")) return "Tự luận";
  if (normalized.includes("CODING")) return "Bài code";
  return "Bài tập";
}

function submissionTypeLabels(value?: string): string[] {
  const raw = (value ?? "TEXT").toUpperCase();
  const labels = new Set<string>();
  if (raw.includes("TEXT") || raw.includes("ONLINE")) labels.add("Văn bản");
  if (raw.includes("URL") || raw.includes("LINK")) labels.add("Đường dẫn");
  if (raw.includes("FILE")) labels.add("Tệp đính kèm");
  if (labels.size === 0) labels.add("Văn bản");
  return Array.from(labels);
}

function deadlineState(assignment: Assignment) {
  const now = Date.now();
  const availableAt = assignment.availableAt ? new Date(assignment.availableAt).getTime() : 0;
  const dueAt = assignment.dueAt ? new Date(assignment.dueAt).getTime() : 0;
  const lockAt = assignment.lockAt ? new Date(assignment.lockAt).getTime() : 0;

  if (lockAt && now > lockAt) {
    return {
      label: "Đã khóa",
      detail: `Khóa lúc ${formatDateTime(assignment.lockAt)}`,
      tone: "coral" as const,
      icon: LockKeyhole
    };
  }
  if (availableAt && now < availableAt) {
    return {
      label: "Chưa mở",
      detail: `Mở lúc ${formatDateTime(assignment.availableAt)}`,
      tone: "neutral" as const,
      icon: CalendarClock
    };
  }
  if (dueAt && now > dueAt) {
    return {
      label: "Quá hạn",
      detail: `Hạn ${formatDateTime(assignment.dueAt)}`,
      tone: "coral" as const,
      icon: AlertTriangle
    };
  }
  if (dueAt && dueAt - now < 24 * 60 * 60 * 1000) {
    return {
      label: "Sắp đến hạn",
      detail: `Hạn ${formatDateTime(assignment.dueAt)}`,
      tone: "amber" as const,
      icon: TimerReset
    };
  }
  return {
    label: "Đang nhận bài",
    detail: assignment.dueAt ? `Hạn ${formatDateTime(assignment.dueAt)}` : "Không giới hạn hạn nộp",
    tone: "brand" as const,
    icon: CheckCircle2
  };
}

function sortSubmissions(submissions: Submission[]): Submission[] {
  return [...submissions].sort((a, b) => {
    const submittedA = a.submittedAt ? new Date(a.submittedAt).getTime() : 0;
    const submittedB = b.submittedAt ? new Date(b.submittedAt).getTime() : 0;
    return submittedB - submittedA || b.attemptNo - a.attemptNo;
  });
}

function AssignmentStat({
  icon,
  label,
  value
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-black/10 bg-white/80 p-3">
      <div className="flex items-center gap-2 text-xs font-bold uppercase text-ink-500">
        {icon}
        {label}
      </div>
      <p className="mt-2 text-sm font-semibold text-ink-900">{value}</p>
    </div>
  );
}

function AssignmentDetail({
  assignment,
  studentId
}: {
  assignment: Assignment;
  studentId: string;
}) {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [submissionUrl, setSubmissionUrl] = useState("");
  const [draftReady, setDraftReady] = useState(false);
  const draftKey = `courseflow.assignment.draft.${studentId}.${assignment.id}`;
  const deadline = deadlineState(assignment);
  const DeadlineIcon = deadline.icon;
  const types = submissionTypeLabels(assignment.submissionTypes);
  const acceptsUrl = types.includes("Đường dẫn");
  const acceptsText = types.includes("Văn bản") || !acceptsUrl;
  const maxAttempts = assignment.maxAttempts ?? 0;

  const submissions = useQuery({
    queryKey: ["submissions", assignment.id, studentId],
    queryFn: () => listMySubmissions(assignment.id, studentId),
    enabled: Boolean(studentId)
  });

  const submit = useMutation({
    mutationFn: () =>
      submitAssignment(assignment.id, {
        submissionText: text.trim() || undefined,
        submissionUrl: submissionUrl.trim() || undefined
      }),
    onSuccess: () => {
      setText("");
      setSubmissionUrl("");
      localStorage.removeItem(draftKey);
      qc.invalidateQueries({ queryKey: ["submissions", assignment.id, studentId] });
    }
  });

  useEffect(() => {
    try {
      const raw = localStorage.getItem(draftKey);
      if (raw) {
        const draft = JSON.parse(raw) as { text?: string; submissionUrl?: string };
        setText(draft.text ?? "");
        setSubmissionUrl(draft.submissionUrl ?? "");
      }
    } catch {
      localStorage.removeItem(draftKey);
    } finally {
      setDraftReady(true);
    }
  }, [draftKey]);

  useEffect(() => {
    if (!draftReady) return;
    const hasDraft = text.trim() || submissionUrl.trim();
    if (!hasDraft) {
      localStorage.removeItem(draftKey);
      return;
    }
    localStorage.setItem(draftKey, JSON.stringify({ text, submissionUrl }));
  }, [draftKey, draftReady, submissionUrl, text]);

  const sortedSubmissions = submissions.data ? sortSubmissions(submissions.data) : [];
  const latestSubmission = sortedSubmissions[0];
  const attemptsUsed = submissions.data?.length ?? 0;
  const isGraded = submissions.data?.some((s) => s.status === "GRADED") ?? false;
  const locked = deadline.label === "Đã khóa" || deadline.label === "Chưa mở";
  const reachedMaxAttempts = maxAttempts > 0 && attemptsUsed >= maxAttempts;
  const canTryAgain = assignment.allowResubmission || attemptsUsed === 0 || !reachedMaxAttempts;
  const canSubmit = !isGraded && !locked && canTryAgain;
  const hasBody = Boolean(text.trim() || submissionUrl.trim());
  const attemptText =
    maxAttempts > 0 ? `${attemptsUsed}/${maxAttempts} lần` : `${attemptsUsed} lần đã nộp`;
  const blockReason = isGraded
    ? "Bài đã được chấm, không thể nộp thêm."
    : locked
      ? deadline.detail
      : !canTryAgain
        ? "Đã dùng hết số lần nộp."
        : "";

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3">
        <AssignmentStat
          icon={<Trophy className="size-4" />}
          label="Điểm"
          value={assignment.maxScore != null ? `${assignment.maxScore} điểm` : "Chưa đặt"}
        />
        <AssignmentStat
          icon={<RotateCcw className="size-4" />}
          label="Số lần nộp"
          value={maxAttempts > 0 ? attemptText : "Không giới hạn"}
        />
        <AssignmentStat
          icon={<FileCheck2 className="size-4" />}
          label="Cách nộp"
          value={types.join(", ")}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="rounded-lg border border-black/10 bg-white p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-bold text-ink-900">
              <ClipboardCheck className="size-4 text-brand-600" />
              Yêu cầu bài tập
            </div>
            <p className="whitespace-pre-line text-sm leading-6 text-ink-600">
              {assignment.instructions || "Giảng viên chưa thêm mô tả chi tiết cho bài tập này."}
            </p>
          </div>

          {latestSubmission?.feedback && (
            <div className="rounded-lg border border-brand-100 bg-brand-50 p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-bold text-brand-800">
                <CheckCircle2 className="size-4" />
                Nhận xét của giảng viên
              </div>
              <p className="whitespace-pre-line text-sm leading-6 text-brand-800">
                {latestSubmission.feedback}
              </p>
            </div>
          )}
        </div>

        <aside className="space-y-3">
          <div className="rounded-lg border border-black/10 bg-white p-4">
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
                <DeadlineIcon className="size-5" />
              </span>
              <div>
                <Badge tone={deadline.tone}>{deadline.label}</Badge>
                <p className="mt-2 text-sm font-semibold text-ink-900">{deadline.detail}</p>
                {assignment.lockAt && (
                  <p className="mt-1 text-xs text-ink-500">
                    Khóa bài: {formatDateTime(assignment.lockAt)}
                  </p>
                )}
              </div>
            </div>
          </div>

          {latestSubmission && (
            <div className="rounded-lg border border-black/10 bg-white p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-bold text-ink-900">
                <History className="size-4 text-signal-600" />
                Lần nộp gần nhất
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-ink-500">Trạng thái</span>
                  <Badge tone={statusTone(latestSubmission.status)}>
                    {statusLabel(latestSubmission.status)}
                  </Badge>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-ink-500">Điểm</span>
                  <span className="font-semibold text-ink-900">
                    {scoreLabel(latestSubmission.finalScore, assignment.maxScore)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-ink-500">Thời gian</span>
                  <span className="text-right font-semibold text-ink-900">
                    {formatDateTime(latestSubmission.submittedAt)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </aside>
      </div>

      {submissions.isLoading && <p className="text-sm text-ink-500">Đang tải bài nộp...</p>}
      {submissions.isError && (
        <p className="text-sm text-red-600">Không tải được bài nộp.</p>
      )}
      {sortedSubmissions.length > 0 && (
        <div className="rounded-lg border border-black/10 bg-white p-4">
          <div className="mb-4 flex items-center gap-2 text-sm font-bold text-ink-900">
            <History className="size-4 text-signal-600" />
            Lịch sử nộp bài
          </div>
          <div className="space-y-3">
            {sortedSubmissions.map((s) => (
              <div
                key={s.id}
                className="grid gap-3 rounded-lg border border-black/10 bg-slate-50/70 p-3 text-sm md:grid-cols-[80px_1fr_auto]"
              >
                <div>
                  <p className="text-xs font-bold uppercase text-ink-500">Lần</p>
                  <p className="mt-1 font-semibold text-ink-900">#{s.attemptNo}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase text-ink-500">Thời gian nộp</p>
                  <p className="mt-1 font-semibold text-ink-900">
                    {formatDateTime(s.submittedAt)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 md:justify-end">
                  <Badge tone={statusTone(s.status)}>{statusLabel(s.status)}</Badge>
                  <Badge tone="neutral">{scoreLabel(s.finalScore, assignment.maxScore)}</Badge>
                  {s.submissionUrl && (
                    <a
                      href={s.submissionUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-bold text-brand-700 hover:text-brand-900"
                    >
                      Link nộp
                      <ExternalLink className="size-3.5" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {submissions.data && submissions.data.length === 0 && (
        <div className="rounded-lg border border-dashed border-black/15 bg-white p-4 text-sm text-ink-500">
          Chưa có bài nộp nào.
        </div>
      )}

      {canSubmit ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (hasBody) submit.mutate();
          }}
          className="space-y-3 rounded-lg border border-black/10 bg-white p-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-bold text-ink-900">
                <PenLine className="size-4 text-brand-600" />
                Nộp bài
              </div>
              <p className="mt-1 text-xs text-ink-500">
                Bản nháp được lưu tự động trên trình duyệt này.
              </p>
            </div>
            <Badge tone={text.trim() || submissionUrl.trim() ? "brand" : "neutral"}>
              {text.length.toLocaleString("vi-VN")} ký tự
            </Badge>
          </div>
          {acceptsText && (
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              placeholder="Nhập nội dung bài làm, ghi chú triển khai hoặc phần tự luận của bạn..."
            />
          )}
          {acceptsUrl && (
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-semibold text-ink-700">
                <Link2 className="size-4" />
                Đường dẫn bài nộp
              </label>
              <TextInput
                value={submissionUrl}
                onChange={(e) => setSubmissionUrl(e.target.value)}
                placeholder="https://github.com/... hoặc https://docs.google.com/..."
                inputMode="url"
              />
            </div>
          )}
          {submit.isError && (
            <p className="text-sm text-red-600">Nộp bài thất bại. Vui lòng thử lại.</p>
          )}
          {submit.isSuccess && (
            <p className="text-sm font-semibold text-brand-700">Đã nộp bài thành công.</p>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-ink-500">
              {assignment.allowResubmission
                ? "Có thể nộp lại theo giới hạn của bài."
                : "Mỗi lần nộp sẽ được ghi nhận riêng."}
            </p>
            <Button type="submit" disabled={submit.isPending || !hasBody}>
              <Send className="size-4" />
              {submit.isPending ? "Đang nộp..." : "Nộp bài"}
            </Button>
          </div>
        </form>
      ) : (
        <div className="rounded-lg border border-black/10 bg-slate-50 p-4 text-sm font-medium text-ink-600">
          {blockReason}
        </div>
      )}
    </div>
  );
}

function AssignmentCard({
  assignment,
  isOpen,
  onToggle
}: {
  assignment: Assignment;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const deadline = deadlineState(assignment);
  const labels = submissionTypeLabels(assignment.submissionTypes);
  const DeadlineIcon = deadline.icon;
  const maxAttempts = assignment.maxAttempts ?? 0;

  return (
    <Card
      className={cn(
        "overflow-hidden transition",
        isOpen && "border-brand-200 shadow-[0_24px_60px_rgba(15,111,95,0.14)]"
      )}
      padding="none"
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-start justify-between gap-4 p-5 text-left transition hover:bg-brand-50/50"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="sky">{assignmentTypeLabel(assignment.assignmentType)}</Badge>
            <Badge tone={deadline.tone}>
              <DeadlineIcon className="mr-1 size-3.5" />
              {deadline.label}
            </Badge>
          </div>
          <h3 className="mt-3 text-lg font-bold text-ink-900">{assignment.title}</h3>
          <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold text-ink-500">
            <span>{deadline.detail}</span>
            {assignment.maxScore != null && <span>{assignment.maxScore} điểm</span>}
            <span>{labels.join(", ")}</span>
            {maxAttempts > 0 && <span>{maxAttempts} lần nộp</span>}
          </div>
        </div>
        <span className="grid size-9 shrink-0 place-items-center rounded-md border border-black/10 bg-white text-ink-500">
          {isOpen ? <ChevronUp className="size-5" /> : <ChevronDown className="size-5" />}
        </span>
      </button>
    </Card>
  );
}

function CourseAssignmentSummary({ assignments }: { assignments: Assignment[] }) {
  const states = assignments.map(deadlineState);
  const openCount = states.filter((state) => state.label === "Đang nhận bài").length;
  const dueSoonCount = states.filter((state) => state.label === "Sắp đến hạn").length;
  const lockedCount = states.filter((state) => state.label === "Đã khóa" || state.label === "Chưa mở").length;

  return (
    <div className="grid gap-3 md:grid-cols-4">
      <AssignmentStat
        icon={<ClipboardCheck className="size-4" />}
        label="Tổng bài"
        value={`${assignments.length} bài`}
      />
      <AssignmentStat
        icon={<CheckCircle2 className="size-4" />}
        label="Đang nhận"
        value={`${openCount} bài`}
      />
      <AssignmentStat
        icon={<TimerReset className="size-4" />}
        label="Sắp đến hạn"
        value={`${dueSoonCount} bài`}
      />
      <AssignmentStat
        icon={<LockKeyhole className="size-4" />}
        label="Đã khóa/chưa mở"
        value={`${lockedCount} bài`}
      />
    </div>
  );
}

function ExpandedAssignment({
  assignment,
  studentId
}: {
  assignment: Assignment;
  studentId: string;
}) {
  return (
    <Card className="-mt-4 border-brand-100 bg-brand-50/30" padding="md">
      <AssignmentDetail assignment={assignment} studentId={studentId} />
    </Card>
  );
}

export function AssignmentsView({
  courseId,
  initialAssignmentId = ""
}: {
  courseId: string;
  initialAssignmentId?: string;
}) {
  const { session, hydrated } = useLearnerSession();
  const studentId = session?.user.id ? String(session.user.id) : "";
  const [expandedId, setExpandedId] = useState<string | null>(initialAssignmentId || null);

  const assignments = useQuery({
    queryKey: ["assignments", courseId],
    queryFn: () => listAssignments(courseId),
    enabled: Boolean(courseId && studentId)
  });
  const focusedAssignment = useQuery({
    queryKey: ["assignment", initialAssignmentId],
    queryFn: () => getAssignment(initialAssignmentId),
    enabled: Boolean(initialAssignmentId && studentId)
  });

  useEffect(() => {
    if (initialAssignmentId) setExpandedId(initialAssignmentId);
  }, [initialAssignmentId]);

  const assignmentList = useMemo(() => {
    const courseAssignments = assignments.data ?? [];
    if (
      focusedAssignment.data &&
      !courseAssignments.some((a) => a.id === focusedAssignment.data?.id)
    ) {
      return [focusedAssignment.data, ...courseAssignments];
    }
    return courseAssignments;
  }, [assignments.data, focusedAssignment.data]);

  useEffect(() => {
    if (!expandedId && assignmentList.length) {
      setExpandedId(assignmentList[0].id);
    }
  }, [assignmentList, expandedId]);

  if (!hydrated) {
    return (
      <div className="space-y-4">
        <div className="h-[118px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
        <div className="h-[220px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
      </div>
    );
  }
  if (!studentId) {
    return (
      <Card>
        <p className="text-sm text-amber-700">Bạn cần đăng nhập để xem bài tập.</p>
      </Card>
    );
  }
  if (assignments.isLoading || (initialAssignmentId && focusedAssignment.isLoading && assignmentList.length === 0)) {
    return <p className="text-ink-500">Đang tải...</p>;
  }
  if ((assignments.isError || focusedAssignment.isError) && assignmentList.length === 0)
    return <p className="text-red-600">Không tải được bài tập. Backend có thể chưa chạy.</p>;
  if (assignmentList.length === 0)
    return <EmptyState title="Không có bài tập nào" description="Khóa học này chưa có bài tập được công khai." />;

  return (
    <div className="space-y-5">
      <CourseAssignmentSummary assignments={assignmentList} />
      <div className="grid gap-4">
        {assignmentList.map((a) => {
          const isOpen = expandedId === a.id;
          return (
            <div key={a.id} className="space-y-4">
              <AssignmentCard
                assignment={a}
                isOpen={isOpen}
                onToggle={() => setExpandedId(isOpen ? null : a.id)}
              />
              {isOpen && <ExpandedAssignment assignment={a} studentId={studentId} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
