"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  ListTodo,
  RefreshCw
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import { listCatalogCourses } from "@/features/course-catalog/client-api";
import { listMyEnrollments } from "@/features/enrollments/api";
import { listAssignments, type Assignment } from "@/features/assignments/api";
import { clientFetch } from "@/shared/api/client";
import { Badge, Button, Card, EmptyState, ProgressBar, cn } from "@/shared/ui";
import type { StudentQuiz } from "@/features/quiz-attempts/hooks";

type DeadlineItem = {
  id: string;
  courseId: string;
  courseTitle: string;
  title: string;
  type: "ASSIGNMENT" | "QUIZ";
  dueAt: string;
  href: string;
  status?: string;
};

type LearnerDeadlineHubProps = {
  compact?: boolean;
  maxItems?: number;
};

const ACTIVE_ENROLLMENT_STATUSES = new Set(["ACTIVE", "ENROLLED", "COMPLETED"]);

function isActiveEnrollment(status?: string) {
  return ACTIVE_ENROLLMENT_STATUSES.has((status ?? "ACTIVE").toUpperCase());
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa rõ hạn";
  return new Intl.DateTimeFormat("vi-VN", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function relativeDue(value: string): string {
  const dueAt = new Date(value).getTime();
  if (Number.isNaN(dueAt)) return "Chưa rõ";
  const diff = dueAt - Date.now();
  const abs = Math.abs(diff);
  const hour = 60 * 60 * 1000;
  const day = 24 * hour;

  if (diff < 0) {
    if (abs < hour) return "Quá hạn dưới 1 giờ";
    if (abs < day) return `Quá hạn ${Math.ceil(abs / hour)} giờ`;
    return `Quá hạn ${Math.ceil(abs / day)} ngày`;
  }
  if (diff < hour) return "Còn dưới 1 giờ";
  if (diff < day) return `Còn ${Math.ceil(diff / hour)} giờ`;
  return `Còn ${Math.ceil(diff / day)} ngày`;
}

function deadlineTone(value: string): "brand" | "sky" | "amber" | "coral" | "neutral" {
  const dueAt = new Date(value).getTime();
  if (Number.isNaN(dueAt)) return "neutral";
  const diff = dueAt - Date.now();
  const day = 24 * 60 * 60 * 1000;
  if (diff < 0 || diff <= day) return "coral";
  if (diff <= 3 * day) return "amber";
  if (diff <= 7 * day) return "sky";
  return "brand";
}

function completionValue(items: DeadlineItem[]): number {
  if (items.length === 0) return 100;
  const overdue = items.filter((item) => new Date(item.dueAt).getTime() < Date.now()).length;
  return Math.round(((items.length - overdue) / items.length) * 100);
}

function upcomingOnly(item: DeadlineItem) {
  const dueAt = new Date(item.dueAt).getTime();
  if (Number.isNaN(dueAt)) return false;
  return dueAt >= Date.now() - 7 * 24 * 60 * 60 * 1000;
}

async function listCourseQuizzes(courseId: string): Promise<StudentQuiz[]> {
  return clientFetch<StudentQuiz[]>(`/v1/quizzes?courseId=${courseId}`);
}

export function LearnerDeadlineHub({ compact = false, maxItems }: LearnerDeadlineHubProps) {
  const { session, hydrated } = useLearnerSession();
  const coursesQuery = useQuery({
    queryKey: ["catalog-courses"],
    queryFn: listCatalogCourses,
    enabled: hydrated
  });
  const enrollmentsQuery = useQuery({
    queryKey: ["my-enrollments", session?.user.id],
    queryFn: () => listMyEnrollments(),
    enabled: Boolean(session?.accessToken)
  });

  const courses = coursesQuery.data ?? [];
  const courseById = useMemo(() => new Map(courses.filter((course) => course.id).map((course) => [course.id!, course])), [courses]);
  const activeCourseIds = useMemo(
    () =>
      (enrollmentsQuery.data ?? [])
        .filter((enrollment) => isActiveEnrollment(enrollment.status))
        .map((enrollment) => enrollment.courseId),
    [enrollmentsQuery.data]
  );

  const assignmentQueries = useQueries({
    queries: activeCourseIds.map((courseId) => ({
      queryKey: ["course-assignments", courseId],
      queryFn: () => listAssignments(courseId),
      enabled: Boolean(session?.accessToken && courseId),
      retry: 0
    }))
  });

  const quizQueries = useQueries({
    queries: activeCourseIds.map((courseId) => ({
      queryKey: ["course-quizzes", courseId],
      queryFn: () => listCourseQuizzes(courseId),
      enabled: Boolean(session?.accessToken && courseId),
      retry: 0
    }))
  });

  const deadlines = useMemo(() => {
    const items: DeadlineItem[] = [];

    assignmentQueries.forEach((query, index) => {
      const courseId = activeCourseIds[index];
      const course = courseById.get(courseId);
      const assignments = (query.data ?? []) as Assignment[];
      assignments.forEach((assignment) => {
        if (!assignment.dueAt) return;
        items.push({
          id: `assignment-${assignment.id}`,
          courseId,
          courseTitle: course?.title ?? "Khóa học",
          title: assignment.title,
          type: "ASSIGNMENT",
          dueAt: assignment.dueAt,
          href: course
            ? `/courses/${course.slug}/assignments?assignmentId=${assignment.id}`
            : `/search?q=${encodeURIComponent(courseId)}`,
          status: assignment.status
        });
      });
    });

    quizQueries.forEach((query, index) => {
      const courseId = activeCourseIds[index];
      const course = courseById.get(courseId);
      const quizzes = (query.data ?? []) as StudentQuiz[];
      quizzes.forEach((quiz) => {
        if (!quiz.closeAt) return;
        items.push({
          id: `quiz-${quiz.id}`,
          courseId,
          courseTitle: course?.title ?? "Khóa học",
          title: quiz.title,
          type: "QUIZ",
          dueAt: quiz.closeAt,
          href: `/quizzes/${quiz.id}`,
          status: quiz.status
        });
      });
    });

    return items
      .filter(upcomingOnly)
      .sort((a, b) => new Date(a.dueAt).getTime() - new Date(b.dueAt).getTime());
  }, [activeCourseIds, assignmentQueries, courseById, quizQueries]);

  const visibleDeadlines = typeof maxItems === "number" ? deadlines.slice(0, maxItems) : deadlines;
  const isLoading =
    !hydrated ||
    coursesQuery.isLoading ||
    enrollmentsQuery.isLoading ||
    assignmentQueries.some((query) => query.isLoading) ||
    quizQueries.some((query) => query.isLoading);
  const urgentCount = deadlines.filter((item) => {
    const dueAt = new Date(item.dueAt).getTime();
    return Number.isFinite(dueAt) && dueAt - Date.now() <= 3 * 24 * 60 * 60 * 1000;
  }).length;

  if (!hydrated) {
    return <Card className="h-72 animate-pulse"><span className="sr-only">Đang tải deadline</span></Card>;
  }

  if (!session) {
    return (
      <Card>
        <div className="flex items-start gap-3">
          <span className="grid size-10 place-items-center rounded-md bg-accent-50 text-accent-600">
            <CalendarClock className="size-5" />
          </span>
          <div>
            <p className="font-bold text-ink-900">Deadline cá nhân</p>
            <p className="mt-2 text-sm leading-6 text-ink-500">
              Đăng nhập để xem quiz, assignment và các việc cần làm theo khóa học đã ghi danh.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center gap-3 text-sm font-semibold text-ink-500">
          <RefreshCw className="size-4 animate-spin" />
          Đang gom deadline học tập...
        </div>
      </Card>
    );
  }

  if (deadlines.length === 0) {
    return (
      <EmptyState
        title="Chưa có deadline gần"
        description="Khi giảng viên mở quiz hoặc assignment có hạn nộp, danh sách việc cần làm sẽ xuất hiện tại đây."
        action={
          compact ? (
            <Button asChild variant="secondary">
              <Link href="/search">Tìm khóa học</Link>
            </Button>
          ) : undefined
        }
      />
    );
  }

  return (
    <Card padding={compact ? "md" : "lg"}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Việc cần làm</p>
          <h2 className={cn("mt-1 font-bold text-ink-900", compact ? "text-xl" : "text-3xl")}>
            Deadline học tập
          </h2>
        </div>
        <Badge tone={urgentCount > 0 ? "amber" : "brand"}>
          <AlertCircle className="mr-1 size-3.5" />
          {urgentCount} việc gấp
        </Badge>
      </div>

      {!compact && (
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-black/10 bg-[#fbfaf7] p-4">
            <p className="text-sm text-ink-500">Tổng deadline</p>
            <p className="mt-2 text-3xl font-bold text-ink-900">{deadlines.length}</p>
          </div>
          <div className="rounded-lg border border-black/10 bg-[#fbfaf7] p-4">
            <p className="text-sm text-ink-500">Trong 3 ngày</p>
            <p className="mt-2 text-3xl font-bold text-ink-900">{urgentCount}</p>
          </div>
          <div className="rounded-lg border border-black/10 bg-[#fbfaf7] p-4">
            <p className="text-sm text-ink-500">Nhịp học</p>
            <div className="mt-4">
              <ProgressBar value={completionValue(deadlines)} />
            </div>
          </div>
        </div>
      )}

      <div className="mt-5 space-y-3">
        {visibleDeadlines.map((item) => (
          <Link
            key={item.id}
            href={item.href}
            className="flex items-start gap-3 rounded-lg border border-black/10 bg-[#fbfaf7] p-3 transition hover:border-brand-200 hover:bg-brand-50/60"
          >
            <span
              className={cn(
                "grid size-10 shrink-0 place-items-center rounded-md",
                item.type === "QUIZ" ? "bg-coral-50 text-coral-600" : "bg-accent-50 text-accent-600"
              )}
            >
              {item.type === "QUIZ" ? <ClipboardCheck className="size-5" /> : <ListTodo className="size-5" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex flex-wrap items-center gap-2">
                <Badge tone={deadlineTone(item.dueAt)}>{relativeDue(item.dueAt)}</Badge>
                <Badge tone="neutral">{item.type === "QUIZ" ? "Quiz" : "Assignment"}</Badge>
              </span>
              <span className="mt-2 block font-bold leading-5 text-ink-900">{item.title}</span>
              <span className="mt-1 block text-sm leading-5 text-ink-500">{item.courseTitle}</span>
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-ink-500">
                <Clock3 className="size-3.5" />
                {formatDateTime(item.dueAt)}
              </span>
            </span>
            <CheckCircle2 className="mt-1 size-5 shrink-0 text-brand-700" />
          </Link>
        ))}
      </div>

      {compact && deadlines.length > visibleDeadlines.length && (
        <Button asChild variant="secondary" className="mt-4 w-full">
          <Link href="/deadlines">Xem tất cả deadline</Link>
        </Button>
      )}
    </Card>
  );
}
