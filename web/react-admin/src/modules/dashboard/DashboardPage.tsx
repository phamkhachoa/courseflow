import { Link, useSearchParams } from "react-router-dom";
import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Clock3,
  FileText,
  LayoutDashboard,
  ListTree,
  PenSquare,
  Plus,
  ShieldCheck,
  Sparkles,
  UsersRound,
  Video
} from "lucide-react";
import { queryKeys } from "@/shared/api/query-keys";
import { moduleRegistry } from "@/shared/module-registry";
import { Badge, Button, Card, CardHeader, ErrorState, Select, Spinner, Table, Td, Th } from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import { fallbackCourses, listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
import { listCourseQuizzes, listQuizAttempts, type Quiz, type QuizAttempt } from "@/modules/quizzes/api";
import { listAssignments, type Assignment } from "@/modules/assignments/api";
import { listUsers, type AdminUser } from "@/modules/identity/api";

type MetricTone = "brand" | "emerald" | "sky" | "amber" | "slate";
type PriorityTone = "red" | "amber" | "sky" | "emerald";
type Priority = {
  tone: PriorityTone;
  title: string;
  detail: string;
  to: string;
};

const metricTones: Record<MetricTone, string> = {
  brand: "border-brand-100 bg-brand-50 text-brand-700",
  emerald: "border-emerald-100 bg-emerald-50 text-emerald-700",
  sky: "border-sky-100 bg-sky-50 text-sky-700",
  amber: "border-amber-100 bg-amber-50 text-amber-700",
  slate: "border-slate-200 bg-slate-50 text-slate-700"
};

const quickActions = [
  {
    to: "/authoring/new",
    title: "Soạn khóa học",
    subtitle: "Tạo bản nháp, module và học liệu",
    icon: PenSquare
  },
  {
    to: "/quizzes",
    title: "Quản lý bài thi",
    subtitle: "Câu hỏi, đáp án và lượt làm",
    icon: ClipboardCheck
  },
  {
    to: "/media",
    title: "Kho media",
    subtitle: "Upload video, tài liệu và asset",
    icon: Video
  },
  {
    to: "/analytics",
    title: "Phân tích học tập",
    subtitle: "Hoàn thành, rủi ro và hiệu suất",
    icon: BarChart3
  }
];

const focusModules = [
  "courses",
  "authoring",
  "course-modules",
  "quizzes",
  "gradebook",
  "assignments",
  "media",
  "analytics"
];

function statusCount(rows: Course[], status: string) {
  return rows.filter((course) => course.status?.toUpperCase() === status).length;
}

function quizStatusCount(rows: Quiz[], status: string) {
  return rows.filter((quiz) => quiz.status?.toUpperCase() === status).length;
}

function assignmentStatusCount(rows: Assignment[], status: string) {
  return rows.filter((assignment) => assignment.status?.toUpperCase() === status).length;
}

function statusCode(status?: string) {
  return status?.toUpperCase() || "UNKNOWN";
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    PUBLISHED: "Đã công khai",
    DRAFT: "Nháp",
    ARCHIVED: "Lưu trữ",
    ACTIVE: "Đang hoạt động",
    UNKNOWN: "Chưa rõ"
  };
  return labels[statusCode(status)] ?? statusCode(status);
}

function attemptStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    IN_PROGRESS: "Đang làm",
    SUBMITTED: "Đã nộp",
    GRADED: "Đã chấm",
    PARTIALLY_GRADED: "Chờ chấm tay",
    EXPIRED: "Quá hạn",
    ABANDONED: "Bỏ dở"
  };
  return labels[statusCode(status)] ?? statusCode(status);
}

function dateLabel(value?: string) {
  if (!value) return "Chưa có ngày";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa có ngày";
  return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

function latestCourses(rows: Course[]) {
  return rows
    .slice()
    .sort((a, b) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime())
    .slice(0, 5);
}

function attemptTime(attempt: QuizAttempt) {
  return attempt.submittedAt ?? attempt.startedAt ?? attempt.deadlineAt;
}

function latestAttempts(rows: Array<{ attempt: QuizAttempt; quiz: Quiz }>) {
  return rows
    .slice()
    .sort((a, b) => new Date(attemptTime(b.attempt) || 0).getTime() - new Date(attemptTime(a.attempt) || 0).getTime());
}

function compactId(value?: string) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function userLabel(userById: Map<string, AdminUser>, userId?: string | number | null) {
  if (userId === undefined || userId === null) return "Học viên";
  const id = String(userId);
  const user = userById.get(id);
  if (user) return user.fullName || user.email;
  return `Học viên ${compactId(id)}`;
}

function courseDefaultScore(course: Course) {
  const publishedScore = statusCode(course.status) === "PUBLISHED" ? 1000 : 0;
  const materialScore = Math.min(course.materials?.length ?? 0, 20) * 20;
  const summaryScore = course.summary ? 20 : 0;
  const codeScore = course.code ? 10 : 0;
  return publishedScore + materialScore + summaryScore + codeScore;
}

function pickDefaultCourse(courses: Course[]) {
  return [...courses].sort((left, right) => courseDefaultScore(right) - courseDefaultScore(left))[0];
}

function MetricCard({
  icon,
  label,
  value,
  detail,
  tone = "slate"
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  detail: string;
  tone?: MetricTone;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-bold tracking-normal text-slate-950">{value}</p>
          <p className="mt-2 text-sm text-slate-500">{detail}</p>
        </div>
        <span className={cn("grid size-10 shrink-0 place-items-center rounded-md border", metricTones[tone])}>
          {icon}
        </span>
      </div>
    </Card>
  );
}

function PriorityItem({
  tone,
  title,
  detail,
  to
}: {
  tone: PriorityTone;
  title: string;
  detail: string;
  to: string;
}) {
  const classes = {
    red: "bg-red-50 text-red-700 border-red-100",
    amber: "bg-amber-50 text-amber-700 border-amber-100",
    sky: "bg-sky-50 text-sky-700 border-sky-100",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-100"
  };
  return (
    <Link
      to={to}
      className="flex items-start justify-between gap-4 rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50"
    >
      <div className="flex min-w-0 items-start gap-3">
        <span className={cn("mt-0.5 grid size-8 shrink-0 place-items-center rounded-md border", classes[tone])}>
          {tone === "emerald" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
        </span>
        <div className="min-w-0">
          <p className="font-semibold text-slate-900">{title}</p>
          <p className="mt-1 text-sm text-slate-500">{detail}</p>
        </div>
      </div>
      <ArrowRight className="mt-1 size-4 shrink-0 text-slate-400" />
    </Link>
  );
}

function HealthRow({
  label,
  status,
  detail,
  online
}: {
  label: string;
  status: string;
  detail: string;
  online: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-3 last:border-b-0">
      <div className="min-w-0">
        <p className="font-semibold text-slate-900">{label}</p>
        <p className="mt-1 text-sm text-slate-500">{detail}</p>
      </div>
      <span
        className={cn(
          "shrink-0 rounded-full px-2.5 py-1 text-xs font-bold",
          online ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
        )}
      >
        {status}
      </span>
    </div>
  );
}

function GradingQueue({
  rows,
  loading,
  userById
}: {
  rows: Array<{ attempt: QuizAttempt; quiz: Quiz }>;
  loading: boolean;
  userById: Map<string, AdminUser>;
}) {
  return (
    <Card>
      <CardHeader
        title="Hàng chờ chấm bài"
        subtitle="Các lượt làm cần giảng viên kiểm tra thủ công"
        actions={<Badge value={rows.length ? "DRAFT" : "READY"} label={loading ? "Đang tải" : rows.length ? `${rows.length} lượt` : "Trống"} />}
      />
      <div className="space-y-3 p-4">
        {loading && <p className="text-sm text-slate-500">Đang tải lượt nộp bài thi...</p>}
        {!loading && rows.length === 0 && (
          <div className="rounded-md border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-700">
            Chưa có lượt nào cần chấm thủ công.
          </div>
        )}
        {!loading &&
          rows.slice(0, 4).map(({ attempt, quiz }) => (
            <Link
              key={attempt.id}
              to={`/quizzes/${attempt.id}/detail`}
              className="flex items-start justify-between gap-4 rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50"
            >
              <div className="flex min-w-0 items-start gap-3">
                <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-md border border-amber-100 bg-amber-50 text-amber-700">
                  <FileText size={16} />
                </span>
                <div className="min-w-0">
                  <p className="line-clamp-1 font-semibold text-slate-900">{quiz.title}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    {userLabel(userById, attempt.studentId)} · lượt {attempt.attemptNo ?? "—"} · {dateLabel(attempt.submittedAt)}
                  </p>
                </div>
              </div>
              <Badge value={attempt.status} label={attemptStatusLabel(attempt.status)} />
            </Link>
          ))}
      </div>
    </Card>
  );
}

function CourseActionTile({
  to,
  icon,
  title,
  detail,
  value
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  detail: string;
  value: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className="rounded-md border border-slate-200 bg-white p-4 transition hover:border-brand-200 hover:bg-brand-50"
    >
      <div className="flex items-start justify-between gap-4">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-slate-100 text-slate-700">
          {icon}
        </span>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">{value}</span>
      </div>
      <p className="mt-4 font-bold text-slate-900">{title}</p>
      <p className="mt-1 text-sm leading-5 text-slate-500">{detail}</p>
    </Link>
  );
}

function ReadinessRow({
  done,
  label,
  detail
}: {
  done: boolean;
  label: string;
  detail: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-slate-200 bg-white p-3">
      <span
        className={cn(
          "mt-0.5 grid size-7 shrink-0 place-items-center rounded-full",
          done ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
        )}
      >
        {done ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
      </span>
      <div className="min-w-0">
        <p className="font-semibold text-slate-900">{label}</p>
        <p className="mt-1 text-sm leading-5 text-slate-500">{detail}</p>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedCourseId = searchParams.get("courseId") ?? "";
  const courses = useQuery({
    queryKey: queryKeys.courses.list("dashboard"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const users = useQuery({
    queryKey: queryKeys.users.list,
    queryFn: listUsers,
    staleTime: 60_000
  });

  const courseRows = courses.data?.length ? courses.data : fallbackCourses;
  const userById = useMemo(
    () => new Map((users.data ?? []).map((user) => [String(user.id), user])),
    [users.data]
  );
  const defaultCourse = useMemo(() => pickDefaultCourse(courseRows), [courseRows]);
  const selectedCourse =
    courseRows.find((course) => course.id === selectedCourseId) ?? defaultCourse;
  const changeSelectedCourse = (courseId: string) => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (courseId) {
        next.set("courseId", courseId);
      } else {
        next.delete("courseId");
      }
      return next;
    }, { replace: true });
  };
  const shouldFetchQuizzes = !courses.isError && Boolean(courses.data?.length);

  const quizQueries = useQueries({
    queries: courseRows.slice(0, 8).map((course) => ({
      queryKey: queryKeys.quizzes.list(course.id),
      queryFn: () => listCourseQuizzes(course.id),
      enabled: shouldFetchQuizzes,
      retry: 1,
      staleTime: 60_000
    }))
  });

  const quizzes = useMemo(
    () => quizQueries.flatMap((query) => query.data ?? []),
    [quizQueries]
  );
  const selectedCourseQuizzes = useMemo(
    () => quizzes.filter((quiz) => quiz.courseId === selectedCourse?.id),
    [quizzes, selectedCourse?.id]
  );
  const selectedAssignments = useQuery({
    queryKey: queryKeys.assignments.list(selectedCourse?.id ?? ""),
    queryFn: () => listAssignments(selectedCourse?.id ?? ""),
    enabled: !courses.isError && Boolean(selectedCourse?.id),
    retry: 1,
    staleTime: 60_000
  });
  const selectedAssignmentRows = selectedAssignments.data ?? [];
  const quizQueryErrors = quizQueries.filter((query) => query.isError).length;
  const quizQueryLoading = quizQueries.some((query) => query.isLoading || query.isFetching);
  const attemptTargetQuizzes = useMemo(
    () => quizzes.filter((quiz) => quiz.status === "PUBLISHED").slice(0, 12),
    [quizzes]
  );

  const attemptQueries = useQueries({
    queries: attemptTargetQuizzes.map((quiz) => ({
      queryKey: queryKeys.quizzes.attempts(quiz.id),
      queryFn: () => listQuizAttempts(quiz.id),
      enabled: Boolean(quiz.id),
      retry: 1,
      staleTime: 60_000
    }))
  });

  const attemptsWithQuiz = useMemo(
    () =>
      attemptQueries.flatMap((query, index) =>
        (query.data ?? []).map((attempt) => ({
          attempt,
          quiz: attemptTargetQuizzes[index]
        }))
      ),
    [attemptQueries, attemptTargetQuizzes]
  );
  const attemptQueryErrors = attemptQueries.filter((query) => query.isError).length;
  const attemptQueryLoading = attemptQueries.some((query) => query.isLoading || query.isFetching);
  const manualGradingQueue = latestAttempts(
    attemptsWithQuiz.filter(({ attempt }) => attempt.status === "PARTIALLY_GRADED")
  );
  const inProgressAttempts = attemptsWithQuiz.filter(({ attempt }) => attempt.status === "IN_PROGRESS").length;
  const gradedAttempts = attemptsWithQuiz.filter(({ attempt }) => attempt.status === "GRADED").length;

  const publishedCourses = statusCount(courseRows, "PUBLISHED");
  const draftCourses = statusCount(courseRows, "DRAFT");
  const archivedCourses = statusCount(courseRows, "ARCHIVED");
  const draftQuizzes = quizStatusCount(quizzes, "DRAFT");
  const publishedQuizzes = quizStatusCount(quizzes, "PUBLISHED");
  const selectedPublishedQuizzes = quizStatusCount(selectedCourseQuizzes, "PUBLISHED");
  const selectedDraftQuizzes = quizStatusCount(selectedCourseQuizzes, "DRAFT");
  const selectedPublishedAssignments = assignmentStatusCount(selectedAssignmentRows, "PUBLISHED");
  const quizzesWithoutQuestions = quizzes.filter((quiz) => (quiz.questions?.length ?? 0) === 0);
  const selectedEmptyQuizzes = selectedCourseQuizzes.filter((quiz) => (quiz.questions?.length ?? 0) === 0);
  const courseIdsWithQuiz = new Set(quizzes.map((quiz) => quiz.courseId).filter(Boolean));
  const coursesWithoutQuiz = shouldFetchQuizzes
    ? courseRows.filter((course) => !courseIdsWithQuiz.has(course.id))
    : [];
  const selectedCourseTo = selectedCourse?.id ? `/courses/${selectedCourse.id}` : "/courses";
  const selectedModulesTo = selectedCourse?.id
    ? `/course-modules?courseId=${selectedCourse.id}`
    : "/course-modules";
  const selectedQuizzesTo = selectedCourse?.id ? `/quizzes?courseId=${selectedCourse.id}` : "/quizzes";
  const selectedAssignmentsTo = selectedCourse?.id
    ? `/assignments?courseId=${selectedCourse.id}`
    : "/assignments";
  const courseReadiness = [
    {
      done: statusCode(selectedCourse?.status) === "PUBLISHED",
      label: "Khóa học đã công khai",
      detail:
        statusCode(selectedCourse?.status) === "PUBLISHED"
          ? "Học viên có thể nhìn thấy khóa học."
          : "Cần hoàn thiện và công khai khóa học."
    },
    {
      done: selectedPublishedQuizzes > 0,
      label: "Có bài thi công khai",
      detail:
        selectedPublishedQuizzes > 0
          ? `${selectedPublishedQuizzes} bài thi đang mở cho học viên.`
          : "Nên có ít nhất một bài thi để kiểm tra năng lực."
    },
    {
      done: selectedEmptyQuizzes.length === 0,
      label: "Không có bài thi rỗng",
      detail:
        selectedEmptyQuizzes.length === 0
          ? "Các bài thi đã có câu hỏi hoặc chưa được tải dữ liệu."
          : `${selectedEmptyQuizzes.length} bài thi cần bổ sung câu hỏi.`
    },
    {
      done: selectedPublishedAssignments > 0,
      label: "Có bài tập thực hành",
      detail: selectedAssignments.isLoading
        ? "Đang tải bài tập của khóa học."
        : selectedPublishedAssignments > 0
          ? `${selectedPublishedAssignments} bài tập đã công khai.`
          : "Nên bổ sung bài tập để học viên luyện tập và nộp bài."
    }
  ];
  const readinessDone = courseReadiness.filter((item) => item.done).length;

  const priorityCandidates: Array<Priority | false> = [
    draftCourses > 0 && {
      tone: "amber" as const,
      title: `${draftCourses} khóa học đang nháp`,
      detail: "Cần hoàn thiện curriculum, học liệu hoặc công khai.",
      to: "/courses"
    },
    draftQuizzes > 0 && {
      tone: "sky" as const,
      title: `${draftQuizzes} bài thi chưa công khai`,
      detail: "Kiểm tra câu hỏi, đáp án và chính sách làm bài.",
      to: `/quizzes?courseId=${quizzes.find((quiz) => quiz.status === "DRAFT")?.courseId ?? ""}`
    },
    quizzesWithoutQuestions.length > 0 && {
      tone: "red" as const,
      title: `${quizzesWithoutQuestions.length} bài thi chưa có câu hỏi`,
      detail: "Không nên công khai bài thi rỗng cho học viên.",
      to: `/quizzes?courseId=${quizzesWithoutQuestions[0].courseId ?? ""}`
    },
    coursesWithoutQuiz.length > 0 && {
      tone: "amber" as const,
      title: `${coursesWithoutQuiz.length} khóa chưa có bài thi`,
      detail: "Bổ sung bài thi để học viên có điểm kiểm tra năng lực.",
      to: `/quizzes?courseId=${coursesWithoutQuiz[0].id}`
    },
    manualGradingQueue.length > 0 && {
      tone: "red" as const,
      title: `${manualGradingQueue.length} lượt cần chấm thủ công`,
      detail: "Có bài essay/manual chưa được finalize điểm.",
      to: `/quizzes/${manualGradingQueue[0].attempt.id}/detail`
    }
  ];
  const priorities = priorityCandidates.filter((item): item is Priority => Boolean(item));

  const health = [
    {
      label: "Danh mục khóa học",
      status: courses.isError ? "Cần kiểm tra" : "Ổn định",
      detail: courses.isError ? "Đang dùng dữ liệu dự phòng trong admin." : `${courseRows.length} khóa học đã tải.`,
      online: !courses.isError
    },
    {
      label: "Dịch vụ bài thi",
      status: quizQueryErrors > 0 ? "Cần kiểm tra" : quizQueryLoading ? "Đang đồng bộ" : "Ổn định",
      detail: shouldFetchQuizzes
        ? `${quizzes.length} bài thi từ ${Math.min(courseRows.length, 8)} khóa gần nhất.`
        : "Sẵn sàng khi danh mục trả dữ liệu thật.",
      online: quizQueryErrors === 0
    },
    {
      label: "Lượt làm bài",
      status: attemptQueryErrors > 0 ? "Cần kiểm tra" : attemptQueryLoading ? "Đang đồng bộ" : "Ổn định",
      detail: `${attemptsWithQuiz.length} lượt làm · ${manualGradingQueue.length} cần chấm.`,
      online: attemptQueryErrors === 0
    },
    {
      label: "Khung quản trị",
      status: "Ổn định",
      detail: `${moduleRegistry.length} module quản trị đang được mount.`,
      online: true
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">
              <LayoutDashboard size={14} /> Trung tâm điều phối
            </span>
            <span className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-xs font-bold text-sky-700">
              <Activity size={14} /> Dữ liệu trực tiếp
            </span>
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-normal text-slate-950">Tổng quan vận hành</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Một màn hình đầu ca cho admin: tình trạng khóa học, bài thi, các việc cần xử lý và đường tắt tới module quan trọng.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/authoring/new">
            <Button>
              <Plus size={16} /> Soạn khóa học
            </Button>
          </Link>
          <Link to="/quizzes">
            <Button variant="secondary">
              <ClipboardCheck size={16} /> Bài thi
            </Button>
          </Link>
        </div>
      </div>

      {courses.isLoading && <Spinner label="Đang tải dashboard" />}
      {courses.isError && <ErrorState error={courses.error} />}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={<BookOpen size={20} />}
          label="Khóa học"
          value={courseRows.length}
          detail={`${publishedCourses} công khai · ${draftCourses} nháp · ${archivedCourses} lưu trữ`}
          tone="brand"
        />
        <MetricCard
          icon={<ClipboardCheck size={20} />}
          label="Bài thi"
          value={quizzes.length}
          detail={`${publishedQuizzes} công khai · ${draftQuizzes} nháp`}
          tone="sky"
        />
        <MetricCard
          icon={<AlertTriangle size={20} />}
          label="Cần xử lý"
          value={priorities.length}
          detail="Các điểm có thể ảnh hưởng trải nghiệm học viên"
          tone={priorities.length ? "amber" : "emerald"}
        />
        <MetricCard
          icon={<FileText size={20} />}
          label="Cần chấm"
          value={manualGradingQueue.length}
          detail={`${gradedAttempts} đã chấm · ${inProgressAttempts} đang làm`}
          tone={manualGradingQueue.length ? "amber" : "emerald"}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_420px]">
        <Card>
          <CardHeader
            title="Điều hành theo khóa"
            subtitle="Chọn một khóa học rồi mở nhanh curriculum, bài thi, bài tập và chi tiết khóa"
            actions={
              <Select
                value={selectedCourse?.id ?? ""}
                onChange={(event) => changeSelectedCourse(event.target.value)}
                className="min-w-72"
                aria-label="Chọn khóa học"
              >
                {courseRows.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} · {course.title}
                  </option>
                ))}
              </Select>
            }
          />
          <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="rounded-md border border-slate-200 bg-[#fbfaf7] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase text-brand-600">Khóa đang vận hành</p>
                  <h3 className="mt-2 text-xl font-bold leading-tight text-slate-950">
                    {selectedCourse?.title ?? "Chưa chọn khóa"}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    {selectedCourse?.summary ?? "Chọn khóa học để xem các điểm cần xử lý."}
                  </p>
                </div>
                <Badge value={statusCode(selectedCourse?.status)} label={statusLabel(selectedCourse?.status)} />
              </div>

              <dl className="mt-5 grid gap-3 sm:grid-cols-2">
                <div className="rounded-md bg-white p-3">
                  <dt className="text-xs font-bold uppercase text-slate-400">Mã khóa</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-800">{selectedCourse?.code ?? compactId(selectedCourse?.id)}</dd>
                </div>
                <div className="rounded-md bg-white p-3">
                  <dt className="text-xs font-bold uppercase text-slate-400">Cấp độ</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-800">{selectedCourse?.level ?? "Chưa đặt"}</dd>
                </div>
                <div className="rounded-md bg-white p-3">
                  <dt className="text-xs font-bold uppercase text-slate-400">Bài thi</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-800">
                    {selectedCourseQuizzes.length} bài · {selectedPublishedQuizzes} công khai · {selectedDraftQuizzes} nháp
                  </dd>
                </div>
                <div className="rounded-md bg-white p-3">
                  <dt className="text-xs font-bold uppercase text-slate-400">Bài tập</dt>
                  <dd className="mt-1 text-sm font-semibold text-slate-800">
                    {selectedAssignments.isLoading
                      ? "Đang tải"
                      : `${selectedAssignmentRows.length} bài · ${selectedPublishedAssignments} công khai`}
                  </dd>
                </div>
              </dl>

              <div className="mt-5 flex flex-wrap gap-2">
                <Link to={selectedCourseTo}>
                  <Button size="sm">
                    <BookOpen size={14} /> Chi tiết khóa
                  </Button>
                </Link>
                <Link to={selectedModulesTo}>
                  <Button variant="secondary" size="sm">
                    <ListTree size={14} /> Module
                  </Button>
                </Link>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <CourseActionTile
                to={selectedQuizzesTo}
                icon={<ClipboardCheck size={18} />}
                title="Bài thi của khóa"
                detail="Quản lý câu hỏi, đáp án, điểm và lượt làm"
                value={selectedCourseQuizzes.length}
              />
              <CourseActionTile
                to={selectedAssignmentsTo}
                icon={<ClipboardList size={18} />}
                title="Bài tập của khóa"
                detail="Theo dõi assignment, rubric và bài nộp"
                value={selectedAssignments.isLoading ? "..." : selectedAssignmentRows.length}
              />
              <CourseActionTile
                to={selectedModulesTo}
                icon={<ListTree size={18} />}
                title="Curriculum"
                detail="Kiểm tra chương, thứ tự bài học và học liệu"
                value="Mở"
              />
              <CourseActionTile
                to="/analytics"
                icon={<BarChart3 size={18} />}
                title="Phân tích"
                detail="Xem completion, rủi ro và hiệu suất học tập"
                value="Data"
              />
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Bảng kiểm sẵn sàng"
            subtitle="Các điều kiện tối thiểu trước khi khóa học vận hành ổn định"
            actions={<Badge value={readinessDone === courseReadiness.length ? "READY" : "DRAFT"} label={`${readinessDone}/${courseReadiness.length}`} />}
          />
          <div className="space-y-3 p-4">
            {selectedAssignments.isError && (
              <div className="rounded-md border border-amber-100 bg-amber-50 p-3 text-sm font-medium text-amber-700">
                Chưa tải được bài tập của khóa này. Dashboard vẫn hiển thị các mục còn lại.
              </div>
            )}
            {courseReadiness.map((item) => (
              <ReadinessRow key={item.label} {...item} />
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_420px]">
        <Card>
          <CardHeader
            title="Việc nên xử lý"
            subtitle="Ưu tiên theo dữ liệu hiện tại của danh mục và bài thi"
            actions={<Badge value={priorities.length ? "DRAFT" : "READY"} label={priorities.length ? `${priorities.length} việc` : "Ổn định"} />}
          />
          <div className="space-y-3 p-4">
            {priorities.length ? (
              priorities.map((item) => (
                <PriorityItem
                  key={item.title}
                  tone={item.tone}
                  title={item.title}
                  detail={item.detail}
                  to={item.to}
                />
              ))
            ) : (
              <div className="rounded-md border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-700">
                Các khóa học và bài thi chính đang ở trạng thái ổn định.
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Trạng thái hệ thống" subtitle="Tín hiệu từ các API đang dùng" />
          <div>
            {health.map((item) => (
              <HealthRow key={item.label} {...item} />
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card>
          <CardHeader
            title="Khóa học gần đây"
            subtitle="Mở nhanh danh mục hoặc bản nháp để xử lý tiếp"
            actions={
              <Link to="/courses">
                <Button variant="secondary" size="sm">
                  Xem danh mục <ArrowRight size={14} />
                </Button>
              </Link>
            }
          />
          <Table>
            <thead>
              <tr>
                <Th>Mã</Th>
                <Th>Tiêu đề</Th>
                <Th>Cấp độ</Th>
                <Th>Trạng thái</Th>
                <Th>Ngày tạo</Th>
              </tr>
            </thead>
            <tbody>
              {latestCourses(courseRows).map((course) => (
                <tr key={course.id} className="hover:bg-slate-50">
                  <Td>
                    <Link className="font-semibold text-brand-700 hover:underline" to={`/courses/${course.id}`}>
                      {course.code}
                    </Link>
                  </Td>
                  <Td>
                    <p className="font-semibold text-slate-900">{course.title}</p>
                    <p className="mt-1 line-clamp-1 text-xs text-slate-500">{course.summary}</p>
                  </Td>
                  <Td>{course.level || "—"}</Td>
                  <Td><Badge value={statusCode(course.status)} label={statusLabel(course.status)} /></Td>
                  <Td>{dateLabel(course.createdAt)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>

        <Card>
          <CardHeader title="Lối tắt module" subtitle="Các khu vực dùng thường xuyên nhất" />
          <div className="grid gap-3 p-4">
            {quickActions.map((action) => (
              <Link
                key={action.to}
                to={action.to}
                className="flex items-center gap-3 rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50"
              >
                <span className="grid size-10 shrink-0 place-items-center rounded-md bg-slate-100 text-slate-700">
                  <action.icon size={18} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-slate-900">{action.title}</span>
                  <span className="mt-0.5 block text-sm text-slate-500">{action.subtitle}</span>
                </span>
                <ArrowRight size={16} className="shrink-0 text-slate-400" />
              </Link>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <GradingQueue rows={manualGradingQueue} loading={attemptQueryLoading} userById={userById} />

        <Card>
          <CardHeader
            title="Hoạt động bài thi"
            subtitle="Tín hiệu gần nhất từ các bài thi đã công khai"
            actions={<Clock3 size={18} className="text-brand-600" />}
          />
          <div className="space-y-3 p-4">
            {attemptQueryLoading && <p className="text-sm text-slate-500">Đang tải hoạt động...</p>}
            {!attemptQueryLoading && attemptsWithQuiz.length === 0 && (
              <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">Chưa có lượt làm bài thi.</p>
            )}
            {!attemptQueryLoading &&
              latestAttempts(attemptsWithQuiz).slice(0, 5).map(({ attempt, quiz }) => (
                <Link
                  key={attempt.id}
                  to={`/quizzes/${attempt.id}/detail`}
                  className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50"
                >
                  <div className="min-w-0">
                    <p className="line-clamp-1 font-semibold text-slate-900">{quiz.title}</p>
                    <p className="mt-1 text-sm text-slate-500">
                      {userLabel(userById, attempt.studentId)} · {dateLabel(attemptTime(attempt))}
                    </p>
                  </div>
                  <Badge value={attempt.status} label={attemptStatusLabel(attempt.status)} />
                </Link>
              ))}
          </div>
        </Card>
      </section>

      <Card>
        <CardHeader
          title="Bản đồ workspace"
          subtitle="Module chính đang sẵn sàng trong admin"
          actions={<Sparkles size={18} className="text-brand-600" />}
        />
        <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-4">
          {moduleRegistry
            .filter((entry) => focusModules.includes(entry.path))
            .map((entry) => (
              <Link
                key={entry.path}
                to={`/${entry.path}`}
                className="rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50"
              >
                <div className="flex items-start gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-md bg-slate-100 text-slate-700">
                    <entry.icon size={17} />
                  </span>
                  <div>
                    <p className="font-semibold text-slate-900">{entry.label}</p>
                    <p className="mt-1 text-sm leading-5 text-slate-500">{entry.description}</p>
                  </div>
                </div>
              </Link>
            ))}
        </div>
      </Card>
    </div>
  );
}
