import { FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpenCheck,
  ClipboardCheck,
  Clock3,
  ExternalLink,
  FileText,
  Layers3,
  Link2,
  PenLine,
  PlayCircle,
  Search,
  Upload,
  Video
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
  Spinner
} from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import { listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
import { listModules, type CourseModule, type ModuleItem } from "./api";

const demoCourseIds = [
  "63221efe-4f37-4005-a57c-0d284178bfc1",
  "30000000-0000-0000-0000-000000000002",
  "30000000-0000-0000-0000-000000000001"
];

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    PUBLISHED: "Đã công khai",
    DRAFT: "Đang biên soạn",
    READY: "Sẵn sàng",
    ARCHIVED: "Lưu trữ",
    ACTIVE: "Đang mở"
  };
  return labels[status ?? ""] ?? status ?? "—";
}

function shortId(value?: string) {
  if (!value) return "—";
  return value.length > 14 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function itemKind(item: ModuleItem) {
  const type = item.itemType?.toUpperCase();
  if (type === "VIDEO" || item.videoMediaId) return "VIDEO";
  if (type === "DOCUMENT" || type === "PDF" || type === "MATERIAL" || (item.documentMediaIds?.length ?? 0) > 0) {
    return "DOCUMENT";
  }
  if (type === "LINK" || item.contentUrl) return "LINK";
  return type ?? "LESSON";
}

function kindLabel(kind: string) {
  const labels: Record<string, string> = {
    LESSON: "Bài học",
    VIDEO: "Video",
    DOCUMENT: "Tài liệu",
    MATERIAL: "Tài liệu",
    PDF: "PDF",
    LINK: "Link",
    QUIZ: "Bài thi",
    ASSIGNMENT: "Bài tập"
  };
  return labels[kind] ?? kind;
}

function kindIcon(kind: string, className = "size-4") {
  if (kind === "VIDEO") return <Video className={className} />;
  if (kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL") return <FileText className={className} />;
  if (kind === "LINK") return <Link2 className={className} />;
  if (kind === "QUIZ") return <ClipboardCheck className={className} />;
  if (kind === "ASSIGNMENT") return <BookOpenCheck className={className} />;
  return <PlayCircle className={className} />;
}

function kindTone(kind: string) {
  if (kind === "VIDEO") return "UPLOADED";
  if (kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL") return "DOCUMENT";
  if (kind === "LINK") return "LINK";
  if (kind === "QUIZ" || kind === "ASSIGNMENT") return "DRAFT";
  return "LESSON";
}

function totalMinutes(items: ModuleItem[]) {
  return items.reduce((sum, item) => sum + (item.estimatedMinutes ?? 0), 0);
}

function formatMinutes(minutes: number) {
  if (!minutes) return "Chưa ước lượng";
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h ${rest}p` : `${hours}h`;
}

function moduleItems(module: CourseModule) {
  return (module.items ?? []).slice().sort((a, b) => a.position - b.position);
}

function flattenItems(modules: CourseModule[]) {
  return modules.flatMap(moduleItems);
}

function courseName(course?: Course | null) {
  if (!course) return "Chưa chọn khóa học";
  return `${course.code} · ${course.title}`;
}

function itemMatches(item: ModuleItem, keyword: string) {
  const normalized = keyword.trim().toLowerCase();
  if (!normalized) return true;
  return [
    item.title,
    item.description,
    item.itemType,
    item.itemId,
    item.videoMediaId,
    item.contentUrl,
    ...(item.documentMediaIds ?? [])
  ]
    .filter(Boolean)
    .some((value) => value?.toLowerCase().includes(normalized));
}

function Metric({
  label,
  value,
  detail,
  icon,
  tone
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
  tone: "brand" | "sky" | "amber" | "emerald";
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    sky: "bg-sky-50 text-sky-700",
    amber: "bg-amber-50 text-amber-700",
    emerald: "bg-emerald-50 text-emerald-700"
  }[tone];

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-md", toneClass)}>{icon}</span>
      </div>
      <p className="mt-3 text-sm leading-5 text-slate-500">{detail}</p>
    </Card>
  );
}

function QuickAction({
  to,
  icon,
  title,
  detail
}: {
  to: string;
  icon: ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <Link
      to={to}
      className="flex gap-3 rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50"
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
        {icon}
      </span>
      <span>
        <span className="block text-sm font-bold text-slate-900">{title}</span>
        <span className="mt-1 block text-xs leading-5 text-slate-500">{detail}</span>
      </span>
    </Link>
  );
}

function LessonRow({ item, index }: { item: ModuleItem; index: number }) {
  const kind = itemKind(item);
  const docs = item.documentMediaIds ?? [];

  return (
    <div className="grid gap-3 border-t border-slate-100 px-4 py-3 md:grid-cols-[44px_minmax(0,1fr)_auto]">
      <span className="grid size-9 place-items-center rounded-md bg-slate-100 text-sm font-bold text-slate-600">
        {index + 1}
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-brand-700">{kindIcon(kind)}</span>
          <h4 className="font-bold text-slate-950">{item.title}</h4>
          <Badge value={kindTone(kind)} label={kindLabel(kind)} />
          {item.required && <Badge value="REQUIRED" label="Bắt buộc" />}
        </div>
        {item.description && (
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-500">{item.description}</p>
        )}
        <div className="mt-2 flex flex-wrap gap-3 text-xs font-medium text-slate-500">
          {(item.estimatedMinutes ?? 0) > 0 && (
            <span className="inline-flex items-center gap-1">
              <Clock3 className="size-3.5" />
              {item.estimatedMinutes} phút
            </span>
          )}
          {item.videoMediaId && (
            <span className="inline-flex items-center gap-1">
              <Video className="size-3.5" />
              Video {shortId(item.videoMediaId)}
            </span>
          )}
          {docs.length > 0 && (
            <span className="inline-flex items-center gap-1">
              <FileText className="size-3.5" />
              {docs.length} tài liệu
            </span>
          )}
          {item.contentUrl && (
            <span className="inline-flex items-center gap-1">
              <ExternalLink className="size-3.5" />
              Link ngoài
            </span>
          )}
          {item.itemId && <span>Ref {shortId(item.itemId)}</span>}
        </div>
      </div>
      <span className="text-xs font-bold text-slate-400">#{item.position}</span>
    </div>
  );
}

function ModuleCard({ module, keyword, index }: { module: CourseModule; keyword: string; index: number }) {
  const items = moduleItems(module).filter((item) => itemMatches(item, keyword));
  const allItems = moduleItems(module);
  const duration = totalMinutes(allItems);
  const videoCount = allItems.filter((item) => itemKind(item) === "VIDEO").length;
  const assessmentCount = allItems.filter((item) => ["QUIZ", "ASSIGNMENT"].includes(itemKind(item))).length;

  return (
    <Card className="overflow-hidden">
      <CardHeader
        title={
          <span>
            Chương {index + 1}: {module.title}
          </span>
        }
        subtitle={module.description ?? "Chưa có mô tả chương"}
        actions={<Badge value={module.status} label={statusLabel(module.status)} />}
      />
      <div className="flex flex-wrap gap-2 px-4 py-3 text-sm text-slate-500">
        <Badge value="LESSON" label={`${allItems.length} bài`} />
        <Badge value="UPLOADED" label={`${videoCount} video`} />
        <Badge value="DRAFT" label={`${assessmentCount} đánh giá`} />
        <Badge value="default" label={formatMinutes(duration)} />
      </div>
      {items.length === 0 ? (
        <EmptyState message={keyword ? "Không có bài học phù hợp bộ lọc." : "Chương này chưa có bài học."} />
      ) : (
        items.map((item, itemIndex) => <LessonRow key={item.id} item={item} index={itemIndex} />)
      )}
    </Card>
  );
}

export function CourseModulesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get("courseId") ?? "";
  const [courseId, setCourseId] = useState(requestedCourseId);
  const [submitted, setSubmitted] = useState(requestedCourseId);
  const [lessonSearch, setLessonSearch] = useState("");

  const courses = useQuery({
    queryKey: queryKeys.courses.list("module-picker"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });

  const modulesQuery = useQuery({
    queryKey: queryKeys.courseModules.list(submitted),
    queryFn: () => listModules(submitted),
    enabled: Boolean(submitted)
  });

  useEffect(() => {
    setCourseId(requestedCourseId);
    setSubmitted(requestedCourseId);
  }, [requestedCourseId]);

  const selectedCourse = useMemo(
    () => courses.data?.find((course) => course.id === submitted) ?? null,
    [courses.data, submitted]
  );

  const modules = useMemo(
    () => (modulesQuery.data ?? []).slice().sort((a, b) => a.position - b.position),
    [modulesQuery.data]
  );
  const items = useMemo(() => flattenItems(modules), [modules]);
  const videoCount = items.filter((item) => itemKind(item) === "VIDEO").length;
  const documentCount = items.filter((item) => itemKind(item) === "DOCUMENT").length;
  const assessmentCount = items.filter((item) => ["QUIZ", "ASSIGNMENT"].includes(itemKind(item))).length;
  const requiredCount = items.filter((item) => item.required).length;
  const totalDuration = totalMinutes(items);

  function lookup(e: FormEvent) {
    e.preventDefault();
    const nextCourseId = courseId.trim();
    setSubmitted(nextCourseId);
    setLessonSearch("");
    setSearchParams(nextCourseId ? { courseId: nextCourseId } : {}, { replace: true });
  }

  function pickCourse(nextCourseId: string) {
    setCourseId(nextCourseId);
    setSubmitted(nextCourseId);
    setLessonSearch("");
    setSearchParams(nextCourseId ? { courseId: nextCourseId } : {}, { replace: true });
  }

  return (
    <div>
      <PageHeader
        title="Module khóa học"
        description="Xem lộ trình, bài học, video, tài liệu và điểm nối sang quiz/assignment/media của từng khóa."
        actions={
          submitted ? (
            <Link to={`/authoring/${submitted}/draft`}>
              <Button>
                <PenLine size={16} />
                Mở editor
              </Button>
            </Link>
          ) : null
        }
      />

      <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Card>
          <CardHeader
            title="Chọn khóa học"
            subtitle={selectedCourse ? courseName(selectedCourse) : "Chọn từ catalog hoặc nhập Course ID thủ công."}
          />
          <form className="grid gap-3 p-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={lookup}>
            <FormField label="Catalog" htmlFor="cm-course-select">
              <Select
                id="cm-course-select"
                value={courseId}
                onChange={(event) => pickCourse(event.target.value)}
              >
                <option value="">Chọn khóa học</option>
                {(courses.data ?? []).map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} · {course.title}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Course ID" htmlFor="cm-course">
              <Input
                id="cm-course"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
                placeholder="UUID khóa học"
                required
              />
            </FormField>
            <Button type="submit" className="self-end">
              <Search size={16} />
              Xem
            </Button>
          </form>
          {courses.isError && <ErrorState error={courses.error} />}
          <div className="flex flex-wrap gap-2 border-t border-slate-100 p-4">
            {demoCourseIds.map((id, index) => (
              <Button key={id} type="button" variant="secondary" size="sm" onClick={() => pickCourse(id)}>
                Demo {index + 1}
              </Button>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Điều hướng nhanh" />
          <div className="grid gap-2 p-4">
            {submitted ? (
              <>
                <QuickAction
                  to={`/authoring/${submitted}/draft`}
                  icon={<PenLine size={17} />}
                  title="Curriculum editor"
                  detail="Thêm chương, lesson, video và tài liệu."
                />
                <QuickAction
                  to={`/media?courseId=${submitted}`}
                  icon={<Upload size={17} />}
                  title="Media library"
                  detail="Upload và copy Video ID / Media ID."
                />
                <QuickAction
                  to={`/quizzes?courseId=${submitted}`}
                  icon={<ClipboardCheck size={17} />}
                  title="Bài thi"
                  detail="Quản lý quiz, câu hỏi và đáp án."
                />
                <QuickAction
                  to={`/assignments?courseId=${submitted}`}
                  icon={<BookOpenCheck size={17} />}
                  title="Bài tập"
                  detail="Tạo assignment, rubric và chấm bài."
                />
              </>
            ) : (
              <EmptyState message="Chọn một khóa học để mở các thao tác nhanh." />
            )}
          </div>
        </Card>
      </div>

      {submitted && (
        <div className="mb-4 grid gap-3 md:grid-cols-4">
          <Metric
            label="Chương"
            value={modules.length}
            detail="Số module trong lộ trình."
            icon={<Layers3 size={18} />}
            tone="brand"
          />
          <Metric
            label="Bài học"
            value={items.length}
            detail={`${requiredCount} bài bắt buộc.`}
            icon={<PlayCircle size={18} />}
            tone="emerald"
          />
          <Metric
            label="Video / tài liệu"
            value={`${videoCount}/${documentCount}`}
            detail="Tín hiệu nội dung media trong lesson."
            icon={<Video size={18} />}
            tone="sky"
          />
          <Metric
            label="Đánh giá"
            value={assessmentCount}
            detail={`Tổng thời lượng: ${formatMinutes(totalDuration)}.`}
            icon={<ClipboardCheck size={18} />}
            tone="amber"
          />
        </div>
      )}

      {submitted && (
        <Card className="mb-4">
          <CardHeader
            title="Bộ lọc lesson"
            subtitle="Tìm theo tiêu đề, mô tả, loại bài, Video ID, Media ID hoặc link."
          />
          <div className="p-4">
            <div className="relative max-w-xl">
              <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-400" />
              <Input
                value={lessonSearch}
                onChange={(event) => setLessonSearch(event.target.value)}
                placeholder="Ví dụ: video, jwt, quiz, media id..."
                className="pl-9"
              />
            </div>
          </div>
        </Card>
      )}

      {!submitted && (
        <EmptyState message="Chưa chọn khóa học. Hãy chọn từ catalog hoặc nhập Course ID để xem lộ trình." />
      )}
      {modulesQuery.isLoading && <Spinner />}
      {modulesQuery.isError && <ErrorState error={modulesQuery.error} />}
      {submitted && modulesQuery.data && modules.length === 0 && (
        <EmptyState message="Khóa học chưa có module. Mở editor để thêm chương đầu tiên." />
      )}
      {modules.length > 0 && (
        <div className="space-y-4">
          {modules.map((module, index) => (
            <ModuleCard key={module.id} module={module} keyword={lessonSearch} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
