"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Layers3,
  ListChecks,
  LockKeyhole,
  PlayCircle,
  Video
} from "lucide-react";
import { EnrollmentCta } from "@/features/enrollments/EnrollmentCta";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, Card, EmptyState, cn } from "@/shared/ui";
import { useCourseModules } from "./hooks";
import type { CourseModule, ModuleItem } from "./api";
import { getModuleItemKind, getModuleItemReadinessIssue, isModuleItemReady } from "./readiness";

type CourseOverviewPanelProps = {
  courseId: string;
  courseSlug: string;
  className?: string;
};

type LessonKind = "LESSON" | "VIDEO" | "DOCUMENT" | "LINK" | "QUIZ" | "ASSIGNMENT" | string;

function normalizeModules(data?: CourseModule[]): CourseModule[] {
  return (data ?? [])
    .slice()
    .sort((a, b) => a.position - b.position)
    .map((module) => ({
      ...module,
      items: (module.items ?? []).slice().sort((a, b) => a.position - b.position)
    }));
}

function flattenItems(modules: CourseModule[]) {
  return modules.flatMap((module) => module.items ?? []);
}

function lessonKind(item: ModuleItem): LessonKind {
  return getModuleItemKind(item);
}

function kindLabel(kind: LessonKind) {
  const labels: Record<string, string> = {
    LESSON: "Bài học",
    VIDEO: "Video",
    DOCUMENT: "Tài liệu",
    LINK: "Link",
    QUIZ: "Bài thi",
    ASSIGNMENT: "Bài tập"
  };
  return labels[kind] ?? kind;
}

function kindTone(kind: LessonKind): "neutral" | "brand" | "amber" | "sky" | "coral" {
  if (kind === "VIDEO") return "sky";
  if (kind === "DOCUMENT" || kind === "LINK") return "amber";
  if (kind === "QUIZ" || kind === "ASSIGNMENT") return "coral";
  if (kind === "LESSON") return "brand";
  return "neutral";
}

function kindIcon(kind: LessonKind, className = "size-4") {
  if (kind === "VIDEO") return <Video className={className} />;
  if (kind === "DOCUMENT") return <FileText className={className} />;
  if (kind === "LINK") return <ExternalLink className={className} />;
  if (kind === "QUIZ") return <ClipboardCheck className={className} />;
  if (kind === "ASSIGNMENT") return <ListChecks className={className} />;
  return <BookOpen className={className} />;
}

function formatMinutes(minutes: number) {
  if (!minutes) return "Chưa ước lượng";
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h ${rest}p` : `${hours}h`;
}

function totalMinutes(items: ModuleItem[]) {
  return items.reduce((sum, item) => sum + (item.estimatedMinutes ?? 0), 0);
}

function countByKind(items: ModuleItem[]) {
  return items.reduce(
    (stats, item) => {
      const kind = lessonKind(item);
      if (kind === "VIDEO") stats.videos += 1;
      if (kind === "DOCUMENT") stats.documents += 1;
      if (kind === "QUIZ") stats.quizzes += 1;
      if (kind === "ASSIGNMENT") stats.assignments += 1;
      if (item.required) stats.required += 1;
      return stats;
    },
    { videos: 0, documents: 0, quizzes: 0, assignments: 0, required: 0 }
  );
}

function StatTile({
  label,
  value,
  detail,
  icon,
  tone
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
  tone: "brand" | "sky" | "amber" | "coral";
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    sky: "bg-signal-50 text-signal-600",
    amber: "bg-accent-50 text-accent-600",
    coral: "bg-coral-50 text-coral-600"
  }[tone];

  return (
    <div className="border-t border-black/10 p-4 sm:border-l sm:border-t-0">
      <span className={cn("grid size-9 place-items-center rounded-md", toneClass)}>{icon}</span>
      <p className="mt-4 text-sm font-medium text-ink-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-ink-900">{value}</p>
      <p className="mt-1 text-xs leading-5 text-ink-500">{detail}</p>
    </div>
  );
}

function ModulePreview({ module, index }: { module: CourseModule; index: number }) {
  const items = module.items ?? [];
  const stats = countByKind(items);
  const duration = totalMinutes(items);
  const preparingCount = items.filter((item) => !isModuleItemReady(item)).length;

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase text-brand-600">Chương {index + 1}</p>
          <h3 className="mt-1 text-lg font-bold leading-6 text-ink-900">{module.title}</h3>
          {module.description && (
            <p className="mt-2 line-clamp-2 max-w-2xl text-sm leading-6 text-ink-500">{module.description}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="brand">{items.length} bài</Badge>
          <Badge tone="neutral">{formatMinutes(duration)}</Badge>
          {stats.required > 0 && <Badge tone="amber">{stats.required} bắt buộc</Badge>}
          {preparingCount > 0 && <Badge tone="amber">{preparingCount} đang bổ sung</Badge>}
        </div>
      </div>

      {items.length === 0 ? (
        <p className="border-t border-black/10 px-4 py-4 text-sm text-ink-500">Chương này chưa có bài học.</p>
      ) : (
        <div className="border-t border-black/10">
          {items.slice(0, 5).map((item, itemIndex) => {
            const kind = lessonKind(item);
            const readinessIssue = getModuleItemReadinessIssue(item);
            return (
              <div
                key={item.id}
                className="grid gap-3 border-b border-black/5 px-4 py-3 last:border-b-0 sm:grid-cols-[32px_1fr_auto]"
              >
                <span className="grid size-8 place-items-center rounded-md bg-black/[0.04] text-sm font-bold text-ink-700">
                  {itemIndex + 1}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-ink-900">{item.title}</p>
                  <p className="mt-1 flex flex-wrap items-center gap-2 text-xs font-medium text-ink-500">
                    {(item.estimatedMinutes ?? 0) > 0 && <span>{item.estimatedMinutes} phút</span>}
                    {item.videoMediaId && <span>Có video</span>}
                    {(item.documentMediaIds?.length ?? 0) > 0 && <span>{item.documentMediaIds?.length} tài liệu</span>}
                    {item.required && <span>Bắt buộc</span>}
                    {readinessIssue && <span className="font-bold text-accent-700">{readinessIssue}</span>}
                  </p>
                </div>
                <Badge tone={kindTone(kind)} className="w-fit">
                  <span className="mr-1">{kindIcon(kind, "size-3.5")}</span>
                  {kindLabel(kind)}
                </Badge>
              </div>
            );
          })}
          {items.length > 5 && (
            <p className="border-t border-black/10 bg-[#fbfaf7] px-4 py-3 text-sm font-semibold text-ink-500">
              Còn {items.length - 5} bài khác trong chương này.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

export function CourseOverviewPanel({ courseId, courseSlug, className }: CourseOverviewPanelProps) {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const modulesQuery = useCourseModules(courseId, Boolean(session?.accessToken));
  const modules = useMemo(() => normalizeModules(modulesQuery.data), [modulesQuery.data]);
  const lessons = useMemo(() => flattenItems(modules), [modules]);
  const stats = useMemo(() => countByKind(lessons), [lessons]);
  const firstVideo = lessons.find((lesson) => lesson.videoMediaId);
  const firstAssessment = lessons.find((lesson) => {
    const kind = lessonKind(lesson);
    return kind === "QUIZ" || kind === "ASSIGNMENT";
  });
  const firstReadyLesson = lessons.find(isModuleItemReady);
  const firstLesson = firstVideo ?? firstReadyLesson ?? lessons[0];
  const moduleHref = `/courses/${courseSlug}/modules`;
  const courseDuration = totalMinutes(lessons);
  const preparingLessonCount = lessons.filter((lesson) => !isModuleItemReady(lesson)).length;
  const readyLessonCount = lessons.length - preparingLessonCount;

  useEffect(() => {
    setSession(learnerSession.read());
    setSessionReady(true);
    return learnerSession.subscribe((nextSession) => {
      setSession(nextSession);
      setSessionReady(true);
    });
  }, []);

  if (!courseId) {
    return <EmptyState title="Thiếu courseId" description="Không thể tải lộ trình học cho khóa này." />;
  }

  if (!sessionReady) {
    return (
      <Card className={cn("animate-pulse", className)}>
        <div className="h-5 w-40 rounded-md bg-black/10" />
        <div className="mt-4 h-8 w-2/3 rounded-md bg-black/10" />
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <div className="h-24 rounded-md bg-black/10" />
          <div className="h-24 rounded-md bg-black/10" />
          <div className="h-24 rounded-md bg-black/10" />
        </div>
      </Card>
    );
  }

  if (!session) {
    return (
      <Card className={cn("overflow-hidden", className)} padding="none">
        <div className="grid gap-5 p-5 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="amber">
                <LockKeyhole className="mr-1 size-3.5" />
                Cần đăng nhập
              </Badge>
              <Badge tone="neutral">Lộ trình khóa học</Badge>
            </div>
            <h3 className="mt-4 text-2xl font-bold text-ink-900">Đăng nhập để xem chương, video và bài kiểm tra</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
              Trang giới thiệu vẫn mở công khai, còn lộ trình chi tiết được tải theo phiên học viên để giữ đúng quyền
              ghi danh và tránh hiển thị dữ liệu cũ sau khi đăng xuất.
            </p>
          </div>
          <EnrollmentCta courseId={courseId} courseSlug={courseSlug} />
        </div>
      </Card>
    );
  }

  if (modulesQuery.isLoading) {
    return (
      <Card className={cn("animate-pulse", className)}>
        <div className="h-5 w-40 rounded-md bg-black/10" />
        <div className="mt-4 h-8 w-2/3 rounded-md bg-black/10" />
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <div className="h-24 rounded-md bg-black/10" />
          <div className="h-24 rounded-md bg-black/10" />
          <div className="h-24 rounded-md bg-black/10" />
        </div>
      </Card>
    );
  }

  if (modulesQuery.isError) {
    return (
      <Card className={cn("overflow-hidden", className)} padding="none">
        <div className="grid gap-5 p-5 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="amber">
                <LockKeyhole className="mr-1 size-3.5" />
                Cần đăng nhập
              </Badge>
              <Badge tone="neutral">Lộ trình khóa học</Badge>
            </div>
            <h3 className="mt-4 text-2xl font-bold text-ink-900">Xem chương, video và bài kiểm tra sau khi tham gia</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
              Nội dung chi tiết được bảo vệ theo ghi danh. Đăng nhập hoặc tham gia khóa học để mở phòng học,
              xem video, làm quiz và theo dõi tiến độ.
            </p>
          </div>
          <EnrollmentCta courseId={courseId} courseSlug={courseSlug} />
        </div>
      </Card>
    );
  }

  if (modules.length === 0) {
    return (
      <EmptyState
        title="Khóa học chưa có lộ trình"
        description="Giảng viên chưa công khai chương học. Bạn vẫn có thể ghi danh để nhận thông báo khi nội dung sẵn sàng."
        action={<EnrollmentCta courseId={courseId} courseSlug={courseSlug} />}
      />
    );
  }

  return (
    <section className={cn("space-y-5", className)}>
      <Card padding="none" className="overflow-hidden">
        <div className="grid gap-5 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="brand">
                <Layers3 className="mr-1 size-3.5" />
                Lộ trình thật
              </Badge>
              <Badge tone="neutral">{modules.length} chương</Badge>
              <Badge tone={preparingLessonCount > 0 ? "amber" : "brand"}>
                {readyLessonCount}/{lessons.length} bài sẵn sàng
              </Badge>
              <Badge tone="neutral">{formatMinutes(courseDuration)}</Badge>
            </div>
            <h3 className="mt-4 text-2xl font-bold text-ink-900">Vào phòng học với video, bài đọc và đánh giá</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-500">
              Học viên có thể xem bài theo chương, chuyển lesson ngay trong player, làm quiz hoặc mở bài tập từ cùng
              một lộ trình. Những bài còn thiếu học liệu sẽ được đánh dấu đang bổ sung để không bị tính nhầm vào tiến độ.
            </p>
          </div>
          <Button asChild size="lg">
            <Link href={moduleHref}>
              <PlayCircle className="size-4" />
              Vào phòng học
            </Link>
          </Button>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Bài học"
            value={String(lessons.length)}
            detail="Tổng số lesson trong các chương."
            icon={<BookOpen className="size-5" />}
            tone="brand"
          />
          <StatTile
            label="Video"
            value={String(stats.videos)}
            detail="Bài có player hoặc media video."
            icon={<Video className="size-5" />}
            tone="sky"
          />
          <StatTile
            label="Học liệu"
            value={String(stats.documents)}
            detail="PDF, tài liệu hoặc nội dung đọc."
            icon={<FileText className="size-5" />}
            tone="amber"
          />
          <StatTile
            label="Đánh giá"
            value={String(stats.quizzes + stats.assignments)}
            detail="Quiz và assignment gắn trong khóa."
            icon={<ClipboardCheck className="size-5" />}
            tone="coral"
          />
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          {modules.slice(0, 4).map((module, index) => (
            <ModulePreview key={module.id} module={module} index={index} />
          ))}
          {modules.length > 4 && (
            <Button asChild variant="secondary" className="w-full">
              <Link href={moduleHref}>Xem tất cả {modules.length} chương</Link>
            </Button>
          )}
        </div>

        <aside className="space-y-4">
          <Card>
            <p className="text-sm font-bold text-brand-600">Học tiếp</p>
            <h3 className="mt-2 text-xl font-bold leading-7 text-ink-900">
              {firstLesson?.title ?? "Mở bài đầu tiên"}
            </h3>
            <p className="mt-3 text-sm leading-6 text-ink-500">
              {firstVideo
                ? "Khóa này có video gắn trực tiếp trong phòng học. Mở phòng học để xem player và danh sách bài bên cạnh."
                : "Mở phòng học để bắt đầu từ bài đầu tiên và theo dõi tiến độ từng chương."}
            </p>
            <Button asChild className="mt-5 w-full">
              <Link href={moduleHref}>
                <PlayCircle className="size-4" />
                Bắt đầu học
              </Link>
            </Button>
          </Card>

          <Card>
            <p className="text-sm font-bold text-brand-600">Checklist học viên</p>
            <div className="mt-4 space-y-3">
              {[
                "Xem video hoặc học liệu của từng bài",
                firstAssessment ? `Hoàn thành ${kindLabel(lessonKind(firstAssessment)).toLowerCase()}: ${firstAssessment.title}` : "Theo dõi bài đánh giá khi giảng viên mở",
                "Đánh dấu chương hoàn thành để cập nhật tiến độ"
              ].map((item) => (
                <div key={item} className="flex gap-3 rounded-md bg-[#fbfaf7] p-3">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-brand-700" />
                  <p className="text-sm font-semibold leading-5 text-ink-800">{item}</p>
                </div>
              ))}
            </div>
          </Card>
        </aside>
      </div>
    </section>
  );
}
