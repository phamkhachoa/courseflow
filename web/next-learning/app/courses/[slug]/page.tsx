import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowRight,
  BookOpenCheck,
  ClipboardCheck,
  GraduationCap,
  PlayCircle,
  Radio,
  Sparkles,
  Trophy,
  Video
} from "lucide-react";
import { getCourseBySlug } from "@/features/course-catalog/api";
import { formatCoursePrice } from "@/features/course-catalog/pricing";
import { CourseOverviewPanel } from "@/features/course-modules/CourseOverviewPanel";
import { EnrollmentCta } from "@/features/enrollments/EnrollmentCta";
import { RelatedCoursesSection } from "@/features/analytics/RelatedCoursesSection";
import { CourseQuizList } from "@/features/quiz-attempts/CourseQuizList";
import {
  Badge,
  Card,
  LinkButton,
  MetricCard,
  NumberedList,
  SectionHeader
} from "@/shared/ui";

const outcomes = [
  "Học theo từng chương với video, tài liệu và checklist rõ ràng",
  "Làm quiz, assignment và theo dõi kết quả trong cùng hệ thống",
  "Hoàn thành bài thực hành để đưa vào portfolio cuối khóa"
];

const snapshotMetrics = [
  { label: "Phòng học", value: "Video", tone: "brand" as const, stateLabel: "Player + chapter", icon: Video },
  { label: "Bài thi", value: "Quiz", tone: "amber" as const, stateLabel: "Tự lưu bài làm", icon: ClipboardCheck },
  { label: "Live", value: "Mở", tone: "sky" as const, stateLabel: "Học cùng mentor", icon: Radio },
  { label: "Kết quả", value: "Điểm", tone: "coral" as const, stateLabel: "Gradebook", icon: Trophy }
];

const learningFlow = [
  {
    title: "Xem bài theo chương",
    detail: "Player, lesson list và tài liệu nằm cạnh nhau để học viên không bị lạc luồng.",
    icon: PlayCircle
  },
  {
    title: "Luyện tập ngay trong khóa",
    detail: "Quiz và assignment được gắn vào đúng chương, có trạng thái và điều hướng rõ ràng.",
    icon: ClipboardCheck
  },
  {
    title: "Theo dõi hoàn thành",
    detail: "Progress chương và điểm số giúp học viên biết phần nào cần quay lại ôn.",
    icon: Trophy
  }
];

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    PUBLISHED: "Đã công khai",
    DRAFT: "Nháp",
    ARCHIVED: "Lưu trữ"
  };
  return labels[status ?? ""] ?? status ?? "Đã công khai";
}

function levelLabel(level?: string) {
  const labels: Record<string, string> = {
    BEGINNER: "Cơ bản",
    INTERMEDIATE: "Trung cấp",
    ADVANCED: "Nâng cao"
  };
  return labels[level ?? ""] ?? level ?? "Khóa học";
}

export default async function CourseDetailPage({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const course = await getCourseBySlug(slug);
  if (!course) notFound();
  const priceLabel = formatCoursePrice(course);

  return (
    <main className="pb-12">
      <section
        className="border-b border-slate-200/80 bg-cover bg-center text-white"
        style={{
          backgroundImage:
            "linear-gradient(115deg, rgba(2,6,23,0.94), rgba(15,23,42,0.8), rgba(15,111,95,0.38)), url('/images/lms-hero-dashboard.png')"
        }}
      >
        <div className="mx-auto grid max-w-7xl gap-6 px-5 py-8 sm:px-6 lg:grid-cols-[minmax(0,1fr)_400px] lg:px-8">
          <div className="min-h-[420px] py-4">
            <Link href="/" className="inline-flex items-center gap-2 text-sm font-semibold text-white/75 transition hover:text-white">
              Dashboard học viên
              <ArrowRight className="size-4" />
            </Link>
            <div className="mt-10 flex flex-wrap gap-2">
              <Badge tone="dark">{course.code}</Badge>
              <Badge tone="dark">{levelLabel(course.level)}</Badge>
              <Badge tone="dark">{statusLabel(course.status)}</Badge>
              {priceLabel && <Badge tone="dark">{priceLabel}</Badge>}
            </div>
            <h1 className="mt-5 max-w-4xl text-4xl font-bold tracking-tight leading-tight sm:text-5xl">{course.title}</h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-white/78 sm:text-lg">{course.summary}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              {course.id && <EnrollmentCta courseId={course.id} courseSlug={course.slug} inverse />}
              {course.id && (
                <Link
                  href={`/courses/${course.slug}/modules`}
                  className="inline-flex items-center justify-center gap-2 rounded-md border border-white/25 bg-white/10 px-4 py-2 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/20"
                >
                  <PlayCircle className="size-4" />
                  Xem lộ trình
                </Link>
              )}
              <Link
                href="/search"
                className="inline-flex items-center justify-center rounded-md border border-white/25 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                Khóa học khác
              </Link>
            </div>

            <div className="mt-10 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur">
                <p className="text-sm text-white/60">Hình thức học</p>
                <p className="mt-2 text-2xl font-bold">Video + Quiz</p>
                <p className="mt-1 text-sm text-white/70">Theo chapter và tiến độ</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur">
                <p className="text-sm text-white/60">Không gian học</p>
                <p className="mt-2 text-2xl font-bold">Lesson player</p>
                <p className="mt-1 text-sm text-white/70">Đi thẳng từ detail sang player</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/8 p-4 backdrop-blur">
                <p className="text-sm text-white/60">Theo dõi kết quả</p>
                <p className="mt-2 text-2xl font-bold">Gradebook</p>
                <p className="mt-1 text-sm text-white/70">Quiz, assignment, completion</p>
              </div>
            </div>
          </div>

          <aside className="self-end rounded-[28px] border border-white/15 bg-white/10 p-5 backdrop-blur">
            <div className="flex items-start gap-3">
              <span className="grid size-11 place-items-center rounded-xl bg-white text-brand-700">
                <GraduationCap className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-white/75">Không gian học</p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight">Video, quiz, assignment</h2>
                <p className="mt-2 text-sm leading-6 text-white/70">
                  Mở phòng học để xem chapter, chuyển bài và cập nhật tiến độ.
                </p>
                {priceLabel && (
                  <p className="mt-3 inline-flex rounded-md bg-white/15 px-2.5 py-1 text-sm font-bold text-white">
                    Giá catalog: {priceLabel}
                  </p>
                )}
              </div>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3">
              {snapshotMetrics.map(({ icon: Icon, ...metric }) => (
                <MetricCard key={metric.label} {...metric} icon={<Icon className="size-5" />} />
              ))}
            </div>
            <div className="mt-5 rounded-2xl border border-white/10 bg-black/10 p-4">
              <p className="text-xs font-bold uppercase text-white/60">Learner flow</p>
              <p className="mt-2 text-sm font-semibold text-white">Catalog to course detail to modules to lesson player</p>
              <p className="mt-2 text-sm leading-6 text-white/70">
                Mục tiêu của màn này là để học viên hiểu khóa học đủ nhanh trước khi đi vào bài học đầu tiên.
              </p>
            </div>
          </aside>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-8 sm:px-6 lg:grid-cols-[340px_minmax(0,1fr)] lg:px-8">
        <aside className="space-y-5 lg:sticky lg:top-28 lg:self-start">
          <Card className="rounded-[24px] border-slate-200/80">
            <p className="text-sm font-bold text-brand-600">Mục tiêu</p>
            <div className="mt-5"><NumberedList items={outcomes} /></div>
          </Card>

          <Card className="rounded-[24px] border-slate-200/80">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-accent-50 text-accent-600">
                <Sparkles className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-ink-900">Gợi ý học</p>
                <p className="mt-1 text-sm leading-6 text-ink-500">
                  Bắt đầu từ phòng học, hoàn thành chương, rồi quay lại quiz/assignment nếu cần ôn.
                </p>
              </div>
            </div>
          </Card>
        </aside>

        <div className="space-y-8">
          <div className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-sm">
            <SectionHeader
              eyebrow="Trải nghiệm học"
              title="Luồng học giống một classroom hiện đại"
              description="Trang này không chỉ giới thiệu khóa học; nó cho học viên nhìn được bài học, video, đánh giá và đường vào phòng học."
              className="mb-5"
            />
            <div className="grid gap-4 md:grid-cols-3">
              {learningFlow.map(({ icon: Icon, ...item }) => (
                <Card key={item.title} className="rounded-2xl border-slate-200/80 bg-slate-50/60 shadow-none">
                  <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-700">
                    <Icon className="size-5" />
                  </span>
                  <h3 className="mt-4 font-bold text-ink-900">{item.title}</h3>
                  <p className="mt-2 min-h-20 text-sm leading-6 text-ink-500">{item.detail}</p>
                </Card>
              ))}
            </div>
          </div>

          {course.id && (
            <div className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-sm">
              <SectionHeader
                eyebrow="Lộ trình"
                title="Chương, bài học và học liệu"
                action={
                  <LinkButton href={`/courses/${course.slug}/modules`} variant="secondary">
                    <BookOpenCheck className="size-4" />
                    Mở phòng học
                  </LinkButton>
                }
                className="mb-5"
              />
              <CourseOverviewPanel courseId={course.id} courseSlug={course.slug} />
            </div>
          )}

          {course.id && <CourseQuizList courseId={course.id} />}
          {course.id && <RelatedCoursesSection courseId={course.id} />}
        </div>
      </section>
    </main>
  );
}
