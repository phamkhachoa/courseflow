"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ClipboardCheck, Clock3, LockKeyhole, PlayCircle, RotateCcw, Trophy } from "lucide-react";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, Card, cn } from "@/shared/ui";
import {
  useCourseQuizzes,
  useMyQuizAttempts,
  type QuizAttempt,
  type StudentQuiz
} from "@/features/quiz-attempts/hooks";
import type { CatalogCourse } from "@/features/course-catalog/api";

type CourseSeed = Pick<CatalogCourse, "id" | "slug" | "title" | "code">;

function gradedAttempts(attempts: QuizAttempt[]) {
  return attempts.filter((attempt) => attempt.status === "GRADED" || attempt.status === "PARTIALLY_GRADED");
}

function bestScore(attempts: QuizAttempt[]) {
  const scores = gradedAttempts(attempts)
    .map((attempt) => attempt.score)
    .filter((score): score is number => typeof score === "number");
  return scores.length ? Math.max(...scores) : null;
}

function latestStatus(attempts: QuizAttempt[]) {
  return attempts[0]?.status ?? "CHƯA LÀM";
}

function isReviewableAttempt(attempt: QuizAttempt) {
  return attempt.status !== "IN_PROGRESS";
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
  return { label: "Đang mở", tone: "brand", canStart: true };
}

export function LearnerAssessmentPanel({
  courses,
  className
}: {
  courses: CourseSeed[];
  className?: string;
}) {
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState<StoredSession | null>(null);
  const [currentHref, setCurrentHref] = useState("/");
  const scopedCourses = useMemo(() => courses.filter((course) => course.id).slice(0, 4), [courses]);
  const loginHref = `/login?next=${encodeURIComponent(currentHref)}`;
  const registerHref = `/register?next=${encodeURIComponent(currentHref)}`;

  useEffect(() => {
    setMounted(true);
    setCurrentHref(`${window.location.pathname}${window.location.search}`);
    setSession(learnerSession.read());
    return learnerSession.subscribe(setSession);
  }, []);

  return (
    <Card className={cn("p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Bài thi cần làm</p>
          <h2 className="mt-1 text-2xl font-bold text-ink-900">Trung tâm đánh giá</h2>
        </div>
        <Badge tone="coral">
          <ClipboardCheck className="mr-1 size-3.5" />
          Bài thi
        </Badge>
      </div>

      {!mounted && <p className="mt-5 text-sm text-ink-500">Đang kiểm tra phiên đăng nhập...</p>}

      {mounted && !session && (
        <div className="mt-5 rounded-lg border border-accent-100 bg-accent-50 p-4">
          <div className="flex items-start gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-md bg-white text-accent-600">
              <LockKeyhole className="size-5" />
            </span>
            <div>
              <p className="font-bold text-ink-900">Đăng nhập để xem bài thi của bạn</p>
              <p className="mt-1 text-sm leading-6 text-ink-600">
                Hệ thống sẽ hiển thị số lượt làm, điểm gần nhất và đường vào bài thi.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button asChild size="sm">
                  <Link href={loginHref}>Đăng nhập</Link>
                </Button>
                <Button asChild size="sm" variant="secondary">
                  <Link href={registerHref}>Đăng ký</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {mounted && session && scopedCourses.length === 0 && (
        <p className="mt-5 rounded-md bg-[#fbfaf7] px-3 py-3 text-sm text-ink-500">
          Chưa có khóa học đủ dữ liệu để tải bài thi.
        </p>
      )}

      {mounted && session && scopedCourses.length > 0 && (
        <div className="mt-5 space-y-3">
          {scopedCourses.map((course) => (
            <CourseAssessmentRow key={course.id} course={course} enabled={Boolean(session)} />
          ))}
        </div>
      )}
    </Card>
  );
}

function CourseAssessmentRow({ course, enabled }: { course: CourseSeed; enabled: boolean }) {
  const quizzes = useCourseQuizzes(course.id ?? "", enabled);
  const published = useMemo(
    () => (quizzes.data ?? []).filter((quiz) => quiz.status === "PUBLISHED").slice(0, 2),
    [quizzes.data]
  );

  return (
    <section className="rounded-lg border border-black/10 bg-[#fbfaf7]">
      <div className="flex items-start justify-between gap-3 border-b border-black/10 px-4 py-3">
        <div className="min-w-0">
          <p className="text-xs font-bold text-brand-600">{course.code}</p>
          <h3 className="mt-1 truncate text-sm font-bold text-ink-900">{course.title}</h3>
        </div>
        <Badge tone="brand">{quizzes.isLoading ? "Đang tải" : `${published.length} bài thi`}</Badge>
      </div>

      {quizzes.isLoading && <p className="px-4 py-3 text-sm text-ink-500">Đang tải bài thi...</p>}
      {quizzes.isError && (
        <p className="px-4 py-3 text-sm font-semibold text-red-600">
          Chưa tải được bài thi. Có thể bạn chưa ghi danh khóa này.
        </p>
      )}
      {!quizzes.isLoading && !quizzes.isError && published.length === 0 && (
        <p className="px-4 py-3 text-sm text-ink-500">Khóa này chưa có bài thi đã công khai.</p>
      )}

      {published.length > 0 && (
        <div className="divide-y divide-black/10">
          {published.map((quiz) => (
            <QuizAssessmentItem key={quiz.id} quiz={quiz} />
          ))}
        </div>
      )}
    </section>
  );
}

function QuizAssessmentItem({ quiz }: { quiz: StudentQuiz }) {
  const attempts = useMyQuizAttempts(quiz.id);
  const rows = attempts.data ?? [];
  const inProgressAttempt = rows.find((attempt) => attempt.status === "IN_PROGRESS");
  const reviewableAttempt = rows.find(isReviewableAttempt);
  const usedAttempts = rows.length;
  const remainingAttempts = Math.max((quiz.attemptsAllowed ?? 1) - usedAttempts, 0);
  const status = inProgressAttempt ? "IN_PROGRESS" : latestStatus(rows);
  const score = bestScore(rows);
  const windowLabel = quizWindowLabel(quiz);
  const canEnterAttempt = Boolean(inProgressAttempt) || (remainingAttempts > 0 && windowLabel.canStart);
  const primaryLabel = inProgressAttempt
    ? "Tiếp tục"
    : !windowLabel.canStart
      ? "Xem lịch"
      : remainingAttempts > 0
        ? "Làm bài"
        : "Xem bài";

  return (
    <article className="px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-bold leading-5 text-ink-900">{quiz.title}</h4>
          <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium text-ink-500">
            <span className="inline-flex items-center gap-1">
              <Clock3 className="size-3.5" /> {quiz.durationMinutes ?? "—"} phút
            </span>
            <span className="inline-flex items-center gap-1">
              <RotateCcw className="size-3.5" /> {usedAttempts}/{quiz.attemptsAllowed ?? 1} lượt
            </span>
            <span className="inline-flex items-center gap-1">
              <Trophy className="size-3.5" /> {attempts.isLoading ? "Đang tải" : score == null ? "Chưa có điểm" : score}
            </span>
          </div>
        </div>
        <Badge tone={status === "GRADED" ? "brand" : status === "IN_PROGRESS" ? "amber" : "neutral"}>
          {attemptStatusLabel(status)}
        </Badge>
      </div>
      <div className="mt-2">
        <Badge tone={windowLabel.tone}>{windowLabel.label}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button asChild size="sm" variant={canEnterAttempt ? "primary" : "secondary"}>
          <Link href={`/quizzes/${quiz.id}`}>
            <PlayCircle className="size-4" />
            {primaryLabel}
          </Link>
        </Button>
        {reviewableAttempt && (
          <Button asChild size="sm" variant="secondary">
            <Link href={`/quizzes/attempts/${reviewableAttempt.id}`}>Lần đã nộp</Link>
          </Button>
        )}
      </div>
    </article>
  );
}
