import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
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
  Notice,
  PageHeader,
  Select,
  Spinner,
  StatCard,
  Toolbar
} from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import { listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
import { listModules, type CourseModule, type ModuleItem } from "./api";

const LEARNER_WEB_URL = (import.meta.env.VITE_LEARNER_WEB_URL ?? "http://localhost:3000").replace(/\/$/, "");

const contentFilters = [
  { value: "ALL", label: "Tất cả nội dung" },
  { value: "REQUIRED", label: "Bài bắt buộc" },
  { value: "VIDEO", label: "Video" },
  { value: "ASSESSMENT", label: "Đánh giá" },
  { value: "RESOURCES", label: "Tài nguyên" },
  { value: "MISSING_CONTENT", label: "Thiếu nội dung" }
] as const;

type ContentFilter = (typeof contentFilters)[number]["value"];

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

function learnerModulesUrl(course: Course) {
  return `${LEARNER_WEB_URL}/courses/${course.slug}/modules`;
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

function itemContentIssue(item: ModuleItem) {
  const kind = itemKind(item);
  const docs = item.documentMediaIds ?? [];
  if (kind === "VIDEO" && !item.videoMediaId) return "Thiếu file video";
  if ((kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL") && docs.length === 0 && !item.contentUrl) {
    return "Thiếu tài liệu/link";
  }
  if (kind === "LINK" && !item.contentUrl) return "Thiếu URL";
  if ((kind === "QUIZ" || kind === "ASSIGNMENT") && !item.itemId) return "Thiếu liên kết";
  if (!item.description && !item.videoMediaId && docs.length === 0 && !item.contentUrl && !item.itemId) {
    return "Chưa có nội dung";
  }
  return null;
}

function itemFixAction(item: ModuleItem, courseId: string) {
  const kind = itemKind(item);
  if (kind === "VIDEO") {
    return { to: `/media?courseId=${courseId}`, label: "Gắn video", icon: <Upload size={14} /> };
  }
  if (kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL" || kind === "LINK") {
    return { to: `/authoring/${courseId}/draft`, label: "Sửa học liệu", icon: <PenLine size={14} /> };
  }
  if (kind === "QUIZ") {
    return { to: `/quizzes?courseId=${courseId}`, label: "Mở bài thi", icon: <ClipboardCheck size={14} /> };
  }
  if (kind === "ASSIGNMENT") {
    return { to: `/assignments?courseId=${courseId}`, label: "Mở bài tập", icon: <BookOpenCheck size={14} /> };
  }
  return { to: `/authoring/${courseId}/draft`, label: "Sửa lesson", icon: <PenLine size={14} /> };
}

function itemMatchesContentFilter(item: ModuleItem, filter: ContentFilter) {
  const kind = itemKind(item);
  if (filter === "REQUIRED") return Boolean(item.required);
  if (filter === "VIDEO") return kind === "VIDEO";
  if (filter === "ASSESSMENT") return kind === "QUIZ" || kind === "ASSIGNMENT";
  if (filter === "RESOURCES") {
    return kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL" || kind === "LINK";
  }
  if (filter === "MISSING_CONTENT") return Boolean(itemContentIssue(item));
  return true;
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

function ExternalQuickAction({
  href,
  icon,
  title,
  detail
}: {
  href: string;
  icon: ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="flex gap-3 rounded-md border border-slate-200 bg-white p-3 transition hover:border-brand-200 hover:bg-brand-50"
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
        {icon}
      </span>
      <span>
        <span className="block text-sm font-bold text-slate-900">{title}</span>
        <span className="mt-1 block text-xs leading-5 text-slate-500">{detail}</span>
      </span>
    </a>
  );
}

function LessonRow({ item, index, courseId }: { item: ModuleItem; index: number; courseId: string }) {
  const kind = itemKind(item);
  const docs = item.documentMediaIds ?? [];
  const issue = itemContentIssue(item);
  const fixAction = issue ? itemFixAction(item, courseId) : null;

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
          {issue && <Badge value="DRAFT" label={issue} />}
        </div>
        {item.description && (
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-500">{item.description}</p>
        )}
        {issue && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">
              <AlertTriangle className="size-3.5" />
              Learner sẽ thấy nội dung chưa hoàn chỉnh cho bài này.
            </p>
            {fixAction && (
              <Link
                to={fixAction.to}
                className="inline-flex items-center gap-1.5 rounded-md border border-amber-200 bg-white px-2 py-1 text-xs font-bold text-amber-800 shadow-sm transition hover:bg-amber-50"
              >
                {fixAction.icon}
                {fixAction.label}
              </Link>
            )}
          </div>
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

function ModuleCard({
  module,
  keyword,
  contentFilter,
  courseId,
  index
}: {
  module: CourseModule;
  keyword: string;
  contentFilter: ContentFilter;
  courseId: string;
  index: number;
}) {
  const items = moduleItems(module).filter((item) => itemMatches(item, keyword) && itemMatchesContentFilter(item, contentFilter));
  const allItems = moduleItems(module);
  const duration = totalMinutes(allItems);
  const videoCount = allItems.filter((item) => itemKind(item) === "VIDEO").length;
  const assessmentCount = allItems.filter((item) => ["QUIZ", "ASSIGNMENT"].includes(itemKind(item))).length;
  const issueCount = allItems.filter((item) => itemContentIssue(item)).length;

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
        {issueCount > 0 && <Badge value="DRAFT" label={`${issueCount} cần bổ sung`} />}
        <Badge value="default" label={formatMinutes(duration)} />
      </div>
      {items.length === 0 ? (
        <EmptyState message={keyword || contentFilter !== "ALL" ? "Không có bài học phù hợp bộ lọc." : "Chương này chưa có bài học."} />
      ) : (
        items.map((item, itemIndex) => <LessonRow key={item.id} item={item} index={itemIndex} courseId={courseId} />)
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
  const [contentFilter, setContentFilter] = useState<ContentFilter>("ALL");

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
    setLessonSearch("");
    setContentFilter("ALL");
  }, [requestedCourseId]);

  const selectedCourse = useMemo(
    () => courses.data?.find((course) => course.id === submitted) ?? null,
    [courses.data, submitted]
  );
  const learnerPreviewUrl = selectedCourse ? learnerModulesUrl(selectedCourse) : null;

  const modules = useMemo(
    () => (modulesQuery.data ?? []).slice().sort((a, b) => a.position - b.position),
    [modulesQuery.data]
  );
  const items = useMemo(() => flattenItems(modules), [modules]);
  const videoCount = items.filter((item) => itemKind(item) === "VIDEO").length;
  const documentCount = items.filter((item) => itemKind(item) === "DOCUMENT").length;
  const assessmentCount = items.filter((item) => ["QUIZ", "ASSIGNMENT"].includes(itemKind(item))).length;
  const requiredCount = items.filter((item) => item.required).length;
  const issueItems = items.filter((item) => itemContentIssue(item));
  const totalDuration = totalMinutes(items);

  function pickCourse(nextCourseId: string) {
    setCourseId(nextCourseId);
    setSubmitted(nextCourseId);
    setLessonSearch("");
    setContentFilter("ALL");
    setSearchParams(nextCourseId ? { courseId: nextCourseId } : {}, { replace: true });
  }

  return (
    <div>
      <PageHeader
        title="Module khóa học"
        description="Xem lộ trình, bài học, video, tài liệu và điểm nối sang quiz/assignment/media của từng khóa."
        actions={
          submitted ? (
            <div className="flex flex-wrap items-center gap-2">
              {learnerPreviewUrl && (
                <a
                  href={learnerPreviewUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-brand-50 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-100"
                >
                  <ExternalLink size={16} />
                  Xem web learn
                </a>
              )}
              <Link to={`/authoring/${submitted}/draft`}>
                <Button>
                  <PenLine size={16} />
                  Mở editor
                </Button>
              </Link>
            </div>
          ) : null
        }
      />

      <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Card>
          <CardHeader
            title="Chọn khóa học"
            subtitle={selectedCourse ? courseName(selectedCourse) : "Chọn trực tiếp từ catalog khóa học."}
          />
          <div className="p-4">
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
                {submitted && !selectedCourse && (
                  <option value={submitted}>Khóa từ liên kết {shortId(submitted)}</option>
                )}
              </Select>
            </FormField>
            {courses.isLoading && <p className="mt-2 text-sm text-slate-500">Đang tải catalog khóa học...</p>}
          </div>
          {courses.isError && <ErrorState error={courses.error} />}
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
                {learnerPreviewUrl && (
                  <ExternalQuickAction
                    href={learnerPreviewUrl}
                    icon={<ExternalLink size={17} />}
                    title="Preview web learn"
                    detail="Mở đúng phòng học learner với courseId hiện tại."
                  />
                )}
                <QuickAction
                  to={`/media?courseId=${submitted}`}
                  icon={<Upload size={17} />}
                  title="Media library"
                  detail="Upload video và tài liệu cho khóa học."
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
          <StatCard
            label="Chương"
            value={modules.length}
            detail="Số module trong lộ trình."
            icon={<Layers3 size={18} />}
            tone="brand"
          />
          <StatCard
            label="Bài học"
            value={items.length}
            detail={`${requiredCount} bài bắt buộc.`}
            icon={<PlayCircle size={18} />}
            tone="success"
          />
          <StatCard
            label="Video / tài liệu"
            value={`${videoCount}/${documentCount}`}
            detail={`${issueItems.length} bài cần kiểm tra trước khi publish.`}
            icon={<Video size={18} />}
            tone={issueItems.length > 0 ? "warning" : "info"}
          />
          <StatCard
            label="Đánh giá"
            value={assessmentCount}
            detail={`Tổng thời lượng: ${formatMinutes(totalDuration)}.`}
            icon={<ClipboardCheck size={18} />}
            tone="warning"
          />
        </div>
      )}

      {submitted && (
        <Card className="mb-4" variant="elevated">
          <CardHeader
            title="Bộ lọc lesson"
            subtitle="Tìm theo tiêu đề, mô tả, loại bài, link hoặc lọc các bài thiếu nội dung hiển thị trên web learn."
          />
          <Toolbar className="border-x-0 border-t-0 bg-white p-4">
            <FormField label="Tìm kiếm" htmlFor="cm-lesson-search" className="min-w-[260px] flex-1">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-400" />
                <Input
                  id="cm-lesson-search"
                  value={lessonSearch}
                  onChange={(event) => setLessonSearch(event.target.value)}
                  placeholder="Ví dụ: video, jwt, quiz, link..."
                  className="pl-9"
                />
              </div>
            </FormField>
            <FormField label="Loại nội dung" htmlFor="cm-content-filter" className="w-full sm:w-64">
              <Select
                id="cm-content-filter"
                value={contentFilter}
                onChange={(event) => setContentFilter(event.target.value as ContentFilter)}
              >
                {contentFilters.map((filter) => (
                  <option key={filter.value} value={filter.value}>
                    {filter.label}
                  </option>
                ))}
              </Select>
            </FormField>
          </Toolbar>
          {issueItems.length > 0 && (
            <div className="p-4 pt-3">
              <Notice
                tone="warning"
                title={`${issueItems.length} bài có nguy cơ hiển thị thiếu nội dung trên web learn.`}
                icon={<AlertTriangle className="size-4" />}
                actions={
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setLessonSearch("");
                      setContentFilter("MISSING_CONTENT");
                    }}
                  >
                    Chỉ xem bài thiếu
                  </Button>
                }
              >
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  {issueItems.slice(0, 5).map((item) => (
                    <div key={item.id} className="rounded-md border border-amber-200 bg-white/70 px-3 py-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-bold uppercase text-amber-700">{itemContentIssue(item)}</p>
                          <p className="mt-1 truncate text-sm font-semibold text-slate-900">{item.title}</p>
                        </div>
                        <Link
                          to={itemFixAction(item, submitted).to}
                          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-amber-200 bg-white px-2 py-1 text-xs font-bold text-amber-800 shadow-sm transition hover:bg-amber-50"
                        >
                          {itemFixAction(item, submitted).icon}
                          {itemFixAction(item, submitted).label}
                        </Link>
                      </div>
                    </div>
                  ))}
                  {issueItems.length > 5 && (
                    <div className="rounded-md border border-amber-200 bg-white/70 px-3 py-2 text-sm font-semibold text-slate-600">
                      +{issueItems.length - 5} bài cần kiểm tra trong bộ lọc thiếu nội dung
                    </div>
                  )}
                </div>
              </Notice>
            </div>
          )}
        </Card>
      )}

      {!submitted && (
        <EmptyState message="Chưa chọn khóa học. Hãy chọn một khóa từ catalog để xem lộ trình." />
      )}
      {modulesQuery.isLoading && <Spinner />}
      {modulesQuery.isError && <ErrorState error={modulesQuery.error} />}
      {submitted && modulesQuery.data && modules.length === 0 && (
        <EmptyState message="Khóa học chưa có module. Mở editor để thêm chương đầu tiên." />
      )}
      {modules.length > 0 && (
        <div className="space-y-4">
          {modules.map((module, index) => (
            <ModuleCard
              key={module.id}
              module={module}
              keyword={lessonSearch}
              contentFilter={contentFilter}
              courseId={submitted}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}
