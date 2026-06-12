"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ClipboardCheck, Clock3, LockKeyhole, PlayCircle, RotateCcw, Trophy } from "lucide-react";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, Card, cn } from "@/shared/ui";
import { useCourseQuizzes, useMyQuizAttempts, type QuizAttempt, type StudentQuiz } from "./hooks";

function gradedAttempts(attempts: QuizAttempt[]) {
  return attempts.filter((attempt) => attempt.status === "GRADED" || attempt.status === "PARTIALLY_GRADED");
}

function bestScore(attempts: QuizAttempt[]) {
  const scores = gradedAttempts(attempts)
    .map((attempt) => attempt.score)
    .filter((score): score is number => typeof score === "number");
  if (scores.length === 0) return null;
  return Math.max(...scores);
}

function latestStatus(attempts: QuizAttempt[]) {
  return attempts[0]?.status ?? "CHƯA LÀM";
}

function isReviewableAttempt(attempt: QuizAttempt) {
  return attempt.status !== "IN_PROGRESS";
}

function quizStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    PUBLISHED: "Đã công khai",
    DRAFT: "Nháp",
    ARCHIVED: "Lưu trữ"
  };
  return labels[status ?? ""] ?? status ?? "Bài thi";
}

function attemptStatusLabel(status: string) {
  const labels: Record<string, string> = {
    "CHƯA LÀM": "Chưa làm",
    IN_PROGRESS: "Đang làm",
    SUBMITTED: "Đã nộp",
    GRADED: "Đã chấm",
    PARTIALLY_GRADED: "Chờ chấm tay",
    EXPIRED: "Quá hạn"
  };
  return labels[status] ?? status;
}

function formatDateTime(value?: string) {
  if (!value) return "";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function quizWindowLabel(quiz: StudentQuiz): {
  label: string;
  tone: "brand" | "amber" | "coral" | "sky" | "neutral";
  canStart: boolean;
} {
  const now = Date.now();
  const openAt = quiz.openAt ? new Date(quiz.openAt).getTime() : 0;
  const closeAt = quiz.closeAt ? new Date(quiz.closeAt).getTime() : 0;

  if (openAt && now < openAt) {
    return { label: `Mở ${formatDateTime(quiz.openAt)}`, tone: "amber", canStart: false };
  }
  if (closeAt && now > closeAt) {
    return { label: `Đã đóng ${formatDateTime(quiz.closeAt)}`, tone: "neutral", canStart: false };
  }
  if (closeAt) {
    return { label: `Đóng ${formatDateTime(quiz.closeAt)}`, tone: "sky", canStart: true };
  }
  if (openAt) {
    return { label: `Đã mở ${formatDateTime(quiz.openAt)}`, tone: "brand", canStart: true };
  }
  return { label: "Không giới hạn thời gian mở", tone: "brand", canStart: true };
}

export function CourseQuizList({
  courseId,
  className,
  compact = false,
  variant = "panel"
}: {
  courseId: string;
  className?: string;
  compact?: boolean;
  variant?: "panel" | "rail";
}) {
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState<StoredSession | null>(null);
  const [currentHref, setCurrentHref] = useState("/");
  const quizzes = useCourseQuizzes(courseId, Boolean(session));

  useEffect(() => {
    setMounted(true);
    setCurrentHref(`${window.location.pathname}${window.location.search}`);
    setSession(learnerSession.read());
    return learnerSession.subscribe(setSession);
  }, []);

  const loginHref = `/login?next=${encodeURIComponent(currentHref)}`;
  const registerHref = `/register?next=${encodeURIComponent(currentHref)}`;

  const visibleQuizzes = useMemo(
    () => (quizzes.data ?? []).filter((quiz) => quiz.status === "PUBLISHED"),
    [quizzes.data]
  );

  if (!courseId) return null;

  if (!mounted) {
    return (
      <Card className={cn("p-5", className)}>
        <p className="text-sm font-bold text-brand-600">Bài thi</p>
        <h2 className={compact || variant === "rail" ? "mt-1 text-xl font-bold text-ink-900" : "mt-1 text-2xl font-bold text-ink-900"}>
          Kiểm tra năng lực
        </h2>
        <p className="mt-4 text-sm text-ink-500">Đang kiểm tra phiên đăng nhập...</p>
      </Card>
    );
  }

  if (!session) {
    return (
      <Card className={cn("p-5", className)}>
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-accent-50 text-accent-600">
            <LockKeyhole className="size-5" />
          </span>
          <div>
            <p className="text-sm font-bold text-ink-900">Bài thi khóa học</p>
            <p className="mt-1 text-sm leading-6 text-ink-500">
              Đăng nhập để xem bài thi, làm bài và lưu điểm vào tiến độ học tập.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button asChild size="sm">
                <Link href={loginHref}>Đăng nhập</Link>
              </Button>
              <Button asChild size="sm" variant="secondary">
                <Link href={registerHref}>Đăng ký</Link>
              </Button>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn("p-5", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Bài thi</p>
          <h2 className={compact || variant === "rail" ? "mt-1 text-xl font-bold text-ink-900" : "mt-1 text-2xl font-bold text-ink-900"}>
            {variant === "rail" ? "Bài thi trong khóa" : "Kiểm tra năng lực"}
          </h2>
          {!compact && variant !== "rail" && (
            <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
              Làm bài thi theo khóa học, theo dõi số câu, thời lượng và số lần được phép làm lại.
            </p>
          )}
          {variant === "rail" && (
            <p className="mt-2 text-sm leading-6 text-ink-500">
              Theo dõi lượt làm, điểm tốt nhất và quay lại bài đang làm ngay trong phòng học.
            </p>
          )}
        </div>
        <Badge tone="coral">{visibleQuizzes.length} bài thi</Badge>
      </div>

      {quizzes.isLoading && <p className="mt-5 text-sm text-ink-500">Đang tải bài thi...</p>}
      {quizzes.isError && (
        <p className="mt-5 rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
          Không tải được bài thi. Hãy kiểm tra lại đăng nhập hoặc ghi danh khóa học.
        </p>
      )}
      {!quizzes.isLoading && !quizzes.isError && visibleQuizzes.length === 0 && (
        <p className="mt-5 rounded-md bg-[#fbfaf7] px-3 py-3 text-sm text-ink-500">
          Khóa học này chưa công khai bài thi nào.
        </p>
      )}

      {visibleQuizzes.length > 0 && (
        <div className={cn("mt-5 grid gap-3", compact || variant === "rail" ? "grid-cols-1" : "md:grid-cols-2")}>
          {visibleQuizzes.map((quiz) => (
            <CourseQuizCard key={quiz.id} quiz={quiz} dense={variant === "rail"} />
          ))}
        </div>
      )}
    </Card>
  );
}

function CourseQuizCard({ quiz, dense = false }: { quiz: StudentQuiz; dense?: boolean }) {
  const attempts = useMyQuizAttempts(quiz.id);
  const rows = attempts.data ?? [];
  const inProgressAttempt = rows.find((attempt) => attempt.status === "IN_PROGRESS");
  const reviewableAttempt = rows.find(isReviewableAttempt);
  const usedAttempts = rows.length;
  const remainingAttempts = Math.max((quiz.attemptsAllowed ?? 1) - usedAttempts, 0);
  const canStartNew = remainingAttempts > 0;
  const score = bestScore(rows);
  const status = inProgressAttempt ? "IN_PROGRESS" : latestStatus(rows);
  const windowLabel = quizWindowLabel(quiz);
  const canEnterAttempt = Boolean(inProgressAttempt) || (canStartNew && windowLabel.canStart);
  const primaryLabel = inProgressAttempt
    ? "Tiếp tục làm bài"
    : !windowLabel.canStart
      ? "Xem lịch thi"
      : canStartNew
        ? "Vào bài thi"
        : "Xem bài thi";
  const attemptBadge = inProgressAttempt
    ? "Đang giữ 1 lượt"
    : canStartNew
      ? `Còn ${remainingAttempts} lượt`
      : "Hết lượt làm";

  return (
    <article className={cn("rounded-lg border border-black/10 bg-[#fbfaf7] transition hover:border-brand-200 hover:bg-brand-50/45", dense ? "p-3" : "p-4")}>
      <div className="flex items-start justify-between gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-white text-coral-600 shadow-sm">
          <ClipboardCheck className="size-5" />
        </span>
        <Badge tone="brand">{quizStatusLabel(quiz.status)}</Badge>
      </div>
      <h3 className={cn("font-bold text-ink-900", dense ? "mt-3 text-sm leading-5" : "mt-4 text-base leading-6")}>
        {quiz.title}
      </h3>
      <div className="mt-3 flex flex-wrap gap-2">
        <Badge tone={windowLabel.tone}>{windowLabel.label}</Badge>
      </div>
      <div className={cn("mt-3 grid gap-2 text-ink-500", dense ? "text-xs" : "text-sm")}>
        <span className="inline-flex items-center gap-2">
          <Clock3 className="size-4" />
          {quiz.durationMinutes ?? "—"} phút
        </span>
        <span className="inline-flex items-center gap-2">
          <ClipboardCheck className="size-4" />
          {quiz.questions?.length ?? 0} câu hỏi
        </span>
        <span className="inline-flex items-center gap-2">
          <RotateCcw className="size-4" />
          {usedAttempts}/{quiz.attemptsAllowed ?? 1} lượt đã dùng
        </span>
        <span className="inline-flex items-center gap-2">
          <Trophy className="size-4" />
          {attempts.isLoading ? "Đang tải điểm" : score == null ? "Chưa có điểm" : `Điểm tốt nhất: ${score}`}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Badge tone={status === "GRADED" ? "brand" : status === "IN_PROGRESS" ? "amber" : "neutral"}>
          {attemptStatusLabel(status)}
        </Badge>
        <Badge tone={inProgressAttempt ? "amber" : canStartNew ? "sky" : "neutral"}>
          {attemptBadge}
        </Badge>
      </div>
      {inProgressAttempt && (
        <p className="mt-3 rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-xs font-semibold leading-5 text-amber-700">
          Bạn có một bài đang làm. Vào lại để tiếp tục từ bản nháp tự lưu.
        </p>
      )}
      <Button asChild className="mt-4 w-full" variant={canEnterAttempt ? "primary" : "secondary"}>
        <Link href={`/quizzes/${quiz.id}`}>
          <span className="inline-flex items-center gap-2">
            <PlayCircle className="size-4" />
            <span>{primaryLabel}</span>
          </span>
        </Link>
      </Button>
      {reviewableAttempt && (
        <Button asChild className="mt-2 w-full" variant="secondary">
          <Link href={`/quizzes/attempts/${reviewableAttempt.id}`}>Xem lần đã nộp gần nhất</Link>
        </Button>
      )}
    </article>
  );
}
