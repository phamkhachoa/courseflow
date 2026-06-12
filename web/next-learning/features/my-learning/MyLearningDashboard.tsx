"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import {
  Bell,
  BookOpen,
  CalendarClock,
  Compass,
  GraduationCap,
  Layers3,
  PlayCircle,
  Route,
  Search,
  ShieldCheck,
  Trophy
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import { LearnerAssessmentPanel } from "@/features/quiz-attempts/LearnerAssessmentPanel";
import { LearnerDeadlineHub } from "@/features/deadlines/LearnerDeadlineHub";
import { listMyEnrollments, type Enrollment } from "@/features/enrollments/api";
import {
  courseDetailHref,
  courseModuleHref,
  listCatalogCourses
} from "@/features/course-catalog/client-api";
import type { CatalogCourse } from "@/features/course-catalog/api";
import type { CourseProgress } from "@/features/course-modules/api";
import { clientFetch } from "@/shared/api/client";
import {
  Badge,
  Button,
  Card,
  CourseCard,
  LinkButton,
  MetricCard,
  ProgressBar,
  SectionHeader,
  cn
} from "@/shared/ui";

type MyLearningDashboardProps = {
  initialCourses: CatalogCourse[];
};

type EnrolledCourseView = {
  enrollment: Enrollment;
  course: CatalogCourse;
};

const courseTones = [
  "from-brand-600 to-signal-500",
  "from-accent-500 to-coral-500",
  "from-signal-600 to-brand-500",
  "from-ink-800 to-brand-600",
  "from-coral-500 to-accent-500",
  "from-brand-700 to-ink-900"
];

const quickActions = [
  {
    href: "/search",
    title: "Tìm khóa học",
    detail: "Tìm theo tên hoặc nội dung",
    icon: Search
  },
  {
    href: "/learning-paths",
    title: "Lộ trình",
    detail: "Gợi ý học theo mục tiêu",
    icon: Route
  },
  {
    href: "/deadlines",
    title: "Deadline",
    detail: "Quiz và assignment sắp hạn",
    icon: CalendarClock
  },
  {
    href: "/certificates",
    title: "Chứng chỉ",
    detail: "Ví thành tích cá nhân",
    icon: ShieldCheck
  }
];

const ACTIVE_ENROLLMENT_STATUSES = new Set(["ACTIVE", "ENROLLED", "COMPLETED"]);

function isActiveEnrollment(status?: string) {
  return ACTIVE_ENROLLMENT_STATUSES.has((status ?? "ACTIVE").toUpperCase());
}

function formatDate(value?: string): string {
  if (!value) return "Vừa ghi danh";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Vừa ghi danh";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(date);
}

function levelLabel(level?: string) {
  const labels: Record<string, string> = {
    BEGINNER: "Nhập môn",
    INTERMEDIATE: "Trung cấp",
    ADVANCED: "Nâng cao",
    EXPERT: "Chuyên sâu"
  };
  return labels[level ?? ""] ?? level ?? "Khóa học";
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    ACTIVE: "Đang học",
    ENROLLED: "Đã ghi danh",
    COMPLETED: "Hoàn thành",
    DROPPED: "Đã dừng",
    PUBLISHED: "Đang mở"
  };
  return labels[status ?? ""] ?? status ?? "Đang mở";
}

async function getCourseProgress(courseId: string): Promise<CourseProgress> {
  return clientFetch<CourseProgress>(`/v1/courses/${courseId}/modules/progress`);
}

function DashboardSkeleton() {
  return (
    <main className="pb-12">
      <section className="border-b border-slate-200/80 bg-white">
        <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 sm:px-6 lg:grid-cols-[1fr_380px] lg:px-8">
          <div className="min-h-[360px] animate-pulse rounded-lg bg-black/10" />
          <div className="min-h-[360px] animate-pulse rounded-lg bg-black/10" />
        </div>
      </section>
    </main>
  );
}

function WorkspaceLink({
  href,
  title,
  detail,
  icon: Icon
}: {
  href: string;
  title: string;
  detail: string;
  icon: typeof Search;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50/45"
    >
      <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-brand-700 transition group-hover:bg-brand-100">
        <Icon className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-bold text-ink-900">{title}</span>
        <span className="mt-1 block text-sm leading-5 text-ink-500">{detail}</span>
      </span>
    </Link>
  );
}

export function MyLearningDashboard({ initialCourses }: MyLearningDashboardProps) {
  const { session, hydrated } = useLearnerSession();
  const coursesQuery = useQuery({
    queryKey: ["catalog-courses"],
    queryFn: listCatalogCourses,
    initialData: initialCourses
  });
  const enrollmentsQuery = useQuery({
    queryKey: ["my-enrollments", session?.user.id],
    queryFn: () => listMyEnrollments(),
    enabled: Boolean(session?.accessToken)
  });

  const courses = coursesQuery.data ?? initialCourses;
  const courseById = useMemo(() => new Map(courses.filter((course) => course.id).map((course) => [course.id!, course])), [courses]);
  const activeEnrollments = useMemo(
    () => (enrollmentsQuery.data ?? []).filter((enrollment) => isActiveEnrollment(enrollment.status)),
    [enrollmentsQuery.data]
  );
  const enrolledCourses = useMemo<EnrolledCourseView[]>(
    () =>
      activeEnrollments.flatMap((enrollment) => {
        const course = courseById.get(enrollment.courseId);
        return course ? [{ enrollment, course }] : [];
      }),
    [activeEnrollments, courseById]
  );
  const enrolledCourseIds = activeEnrollments.map((enrollment) => enrollment.courseId);
  const progressQueries = useQueries({
    queries: enrolledCourseIds.slice(0, 8).map((courseId) => ({
      queryKey: ["course-progress", courseId],
      queryFn: () => getCourseProgress(courseId),
      enabled: Boolean(session?.accessToken && courseId),
      retry: 0
    }))
  });

  const progressByCourseId = useMemo(() => {
    const map = new Map<string, number>();
    enrolledCourseIds.slice(0, 8).forEach((courseId, index) => {
      const progress = progressQueries[index]?.data as CourseProgress | undefined;
      if (progress) map.set(courseId, progress.percentComplete);
    });
    return map;
  }, [enrolledCourseIds, progressQueries]);

  const heroCourse = enrolledCourses[0]?.course ?? courses[0];
  const averageProgress = enrolledCourseIds.length
    ? Math.round(
        enrolledCourseIds.reduce((sum, courseId) => sum + (progressByCourseId.get(courseId) ?? 0), 0) /
          enrolledCourseIds.length
      )
    : 0;
  const recommendedCourses = courses
    .filter((course) => !course.id || !enrolledCourseIds.includes(course.id))
    .slice(0, 3);
  const assessmentCourses = enrolledCourses.length > 0 ? enrolledCourses.map((item) => item.course) : courses.slice(0, 4);

  if (!hydrated) return <DashboardSkeleton />;

  return (
    <main className="pb-12">
      <section className="border-b border-slate-200/80 bg-white">
        <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 sm:px-6 xl:grid-cols-[minmax(0,1.5fr)_380px] lg:px-8">
          <div className="overflow-hidden rounded-[28px] border border-slate-200/80 bg-slate-950 text-white shadow-[0_32px_90px_rgba(15,23,42,0.16)]">
            <div
              className="min-h-[380px] bg-cover bg-center p-6 sm:p-8"
              style={{
                backgroundImage:
                  "linear-gradient(120deg, rgba(2,6,23,0.92), rgba(15,23,42,0.72), rgba(15,111,95,0.38)), url('/images/lms-hero-dashboard.png')"
              }}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="dark">CourseFlow Learn</Badge>
                <Badge tone="dark">{session ? "Workspace cá nhân" : "Public catalog"}</Badge>
                {heroCourse?.level && <Badge tone="dark">{levelLabel(heroCourse.level)}</Badge>}
              </div>

              <div className="mt-14 max-w-3xl">
                <p className="text-sm font-bold uppercase text-white/60">
                  {session ? "Tiếp tục học hôm nay" : "Nơi bắt đầu hành trình học"}
                </p>
                <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
                  {heroCourse?.title ?? "Khám phá khóa học phù hợp với mục tiêu của bạn"}
                </h1>
                <p className="mt-4 max-w-2xl text-base leading-7 text-white/78">
                  {session
                    ? heroCourse?.summary ?? "Không gian học tập thống nhất cho video, chapter, quiz, assignment và theo dõi tiến độ."
                    : "Catalog, lộ trình và lesson player được thiết kế như một product học tập thật, không chỉ là một trang giới thiệu khóa học."}
                </p>

                <div className="mt-8 flex flex-wrap gap-3">
                  <LinkButton href={courseModuleHref(heroCourse)}>
                    <PlayCircle className="size-4" />
                    {session ? "Mở phòng học" : "Xem khóa học"}
                  </LinkButton>
                  <Button asChild variant="inverse">
                    <Link href="/search">
                      <Search className="size-4" />
                      Duyệt catalog
                    </Link>
                  </Button>
                  {session ? (
                    <Button asChild variant="inverse">
                      <Link href="/learning-paths">
                        <Route className="size-4" />
                        Xem lộ trình
                      </Link>
                    </Button>
                  ) : (
                    <Button asChild variant="inverse">
                      <Link href="/register">Đăng ký để lưu tiến độ</Link>
                    </Button>
                  )}
                </div>
              </div>

              <div className="mt-10 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur">
                  <p className="text-sm text-white/60">Khóa đang học</p>
                  <p className="mt-2 text-3xl font-bold">{String(activeEnrollments.length).padStart(2, "0")}</p>
                  <p className="mt-1 text-sm text-white/70">Đồng bộ progress theo tài khoản</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur">
                  <p className="text-sm text-white/60">Tiến độ trung bình</p>
                  <p className="mt-2 text-3xl font-bold">{averageProgress}%</p>
                  <p className="mt-1 text-sm text-white/70">Bài học, quiz và chapter</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur">
                  <p className="text-sm text-white/60">Khuyến nghị tiếp theo</p>
                  <p className="mt-2 text-3xl font-bold">{recommendedCourses.length || 3}</p>
                  <p className="mt-1 text-sm text-white/70">Dựa trên catalog hiện tại</p>
                </div>
              </div>
            </div>
          </div>

          <Card className="flex flex-col rounded-[28px] border-slate-200/80 bg-slate-50/70" padding="lg">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-bold text-brand-600">Learner workspace</p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight text-ink-900">
                  {session ? "Nhịp học của bạn" : "Trải nghiệm học viên"}
                </h2>
              </div>
              <span className="grid size-11 place-items-center rounded-xl bg-white text-brand-700 shadow-sm">
                <GraduationCap className="size-5" />
              </span>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-4">
              <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                <span className="font-semibold text-ink-900">Tiến độ trung bình</span>
                <span className="text-right font-bold text-ink-900">{averageProgress}%</span>
              </div>
              <ProgressBar value={averageProgress} />
              <p className="mt-3 text-sm leading-6 text-ink-500">
                Theo dõi tiến độ tổng quát trước khi nhảy vào player, quiz hay deadline.
              </p>
            </div>

            <div className="mt-5 grid gap-3">
              {quickActions.map((item) => (
                <WorkspaceLink key={item.href} {...item} />
              ))}
            </div>

            <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-brand-600">Tiếp theo</p>
                  <h3 className="mt-1 text-lg font-bold text-ink-900">
                    {heroCourse?.title ?? "Mở catalog để bắt đầu"}
                  </h3>
                </div>
                <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-700">
                  <PlayCircle className="size-5" />
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-ink-500">
                {session ? "Đi thẳng vào chapter đang học hoặc chuyển qua lộ trình để đổi nhịp." : "Catalog công khai vẫn cho phép xem trước trước khi ghi danh."}
              </p>
              <Button asChild className="mt-4 w-full">
                <Link href={courseModuleHref(heroCourse)}>Mở learner flow</Link>
              </Button>
            </div>
          </Card>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl grid-cols-2 gap-3 px-5 py-5 sm:px-6 md:grid-cols-4 lg:px-8">
        <MetricCard
          label="Khóa đã ghi danh"
          value={String(activeEnrollments.length).padStart(2, "0")}
          tone="brand"
          stateLabel={session ? "Cá nhân" : "Chưa đăng nhập"}
          icon={<BookOpen className="size-5" />}
        />
        <MetricCard
          label="Tiến độ"
          value={`${averageProgress}%`}
          tone="sky"
          stateLabel="Module"
          icon={<Layers3 className="size-5" />}
        />
        <MetricCard
          label="Lộ trình"
          value={recommendedCourses.length ? "Mở" : "OK"}
          tone="amber"
          stateLabel="Gợi ý"
          icon={<Compass className="size-5" />}
        />
        <MetricCard
          label="Kết quả"
          value="Grade"
          tone="coral"
          stateLabel="Bảng điểm"
          icon={<Trophy className="size-5" />}
        />
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-7 sm:px-6 lg:grid-cols-[minmax(0,1fr)_380px] lg:px-8">
        <div className="space-y-8">
          <SectionHeader
            eyebrow={session ? "Khóa học của tôi" : "Catalog"}
            title={session && enrolledCourses.length > 0 ? "Tiếp tục hành trình học" : "Chọn khóa học để bắt đầu"}
            description={
              session
                ? "Các khóa đã ghi danh được đưa lên trước, với đường vào player và trạng thái tiến độ rõ ràng."
                : "Giữ cách duyệt gọn gàng như một learner app: xem nhanh, mở chi tiết, rồi vào học."
            }
            className="mb-5"
            action={<LinkButton href="/search" variant="secondary">Xem catalog</LinkButton>}
          />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(enrolledCourses.length > 0 ? enrolledCourses : courses.slice(0, 6)).map((item, index) => {
              const course = "course" in item ? item.course : item;
              const enrollment = "enrollment" in item ? item.enrollment : undefined;
              const progress = course.id ? progressByCourseId.get(course.id) ?? 0 : 0;
              return (
                <CourseCard
                  key={course.slug}
                  code={course.code}
                  title={course.title}
                  summary={course.summary}
                  href={courseModuleHref(course)}
                  status={enrollment?.status ?? course.status}
                  level={course.level}
                  progress={progress}
                  next={enrollment ? `Ghi danh: ${formatDate(enrollment.enrolledAt)}` : "Xem syllabus và ghi danh"}
                  duration={progress > 0 ? "Tiếp tục từ tiến độ đã lưu" : "Bắt đầu bài đầu tiên"}
                  tone={courseTones[index % courseTones.length]}
                />
              );
            })}
          </div>

          {recommendedCourses.length > 0 && (
            <div className="rounded-[24px] border border-slate-200/80 bg-white p-5 shadow-sm">
              <SectionHeader
                eyebrow="Khuyến nghị"
                title="Khóa học nên xem tiếp"
                className="mb-5"
                action={<LinkButton href="/learning-paths" variant="secondary">Lập lộ trình</LinkButton>}
              />
              <div className="grid gap-4 md:grid-cols-3">
                {recommendedCourses.map((course, index) => (
                  <Link
                    key={course.slug}
                    href={courseDetailHref(course)}
                    className={cn(
                      "overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/60 transition",
                      "hover:border-brand-200 hover:bg-brand-50/45"
                    )}
                  >
                    <div className={cn("h-24 bg-gradient-to-br p-4 text-white", courseTones[index % courseTones.length])}>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold">{course.code}</span>
                        <Badge tone="dark">{levelLabel(course.level)}</Badge>
                      </div>
                    </div>
                    <div className="p-4">
                      <h3 className="font-bold leading-6 text-ink-900">{course.title}</h3>
                      <p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-500">{course.summary}</p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <LearnerDeadlineHub compact maxItems={4} />

          <Card>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-bold text-brand-600">Nhắc học</p>
                <h2 className="mt-1 text-2xl font-bold text-ink-900">Thông báo</h2>
              </div>
              <span className="grid size-10 place-items-center rounded-md bg-signal-50 text-signal-600">
                <Bell className="size-5" />
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-ink-500">
              Theo dõi bài mới, deadline, điểm số và chứng chỉ trong một hộp thư học tập.
            </p>
            <Button asChild variant="secondary" className="mt-5 w-full">
              <Link href="/notifications">Mở thông báo</Link>
            </Button>
          </Card>

          <LearnerAssessmentPanel courses={assessmentCourses} />
        </aside>
      </section>
    </main>
  );
}
