"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Clock3,
  Download,
  ExternalLink,
  FileText,
  ListFilter,
  ListChecks,
  Lock,
  PlayCircle,
  RotateCcw,
  Search,
  Video
} from "lucide-react";
import { VideoPlayer } from "@/features/video-player/VideoPlayer";
import { CourseChatPanel } from "@/features/chat/CourseChatPanel";
import { CourseQAPanel } from "@/features/discussions/CourseQAPanel";
import { EnrollmentCta } from "@/features/enrollments/EnrollmentCta";
import { CourseQuizList } from "@/features/quiz-attempts/CourseQuizList";
import { useCoursePlayer, useMarkItemProgress, useMarkProgress } from "@/features/course-modules/hooks";
import { clientFetch, learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, Card, EmptyState, ProgressBar, TextInput, cn } from "@/shared/ui";
import type {
  CertificateEligibility,
  CourseModule,
  CoursePlayerItemState,
  CoursePlayerModuleState,
  CoursePlayerNextAction,
  ItemProgress,
  ModuleItem
} from "./api";
import { getModuleItemKind, getModuleItemReadinessIssue, isModuleItemReady } from "./readiness";

const lessonFilterOptions = [
  { value: "ALL", label: "Tất cả" },
  { value: "INCOMPLETE", label: "Chưa xong" },
  { value: "REQUIRED", label: "Bắt buộc" },
  { value: "VIDEO", label: "Video" },
  { value: "ASSESSMENT", label: "Đánh giá" },
  { value: "RESOURCES", label: "Tài nguyên" },
  { value: "READY", label: "Sẵn sàng" },
  { value: "PREPARING", label: "Đang bổ sung" }
] as const;

type LessonFilter = (typeof lessonFilterOptions)[number]["value"];

type LessonWithContext = ModuleItem & {
  moduleId: string;
  moduleTitle: string;
  moduleDescription?: string;
  moduleIndex: number;
  itemIndex: number;
};

function normalizeModules(data?: CourseModule[]): CourseModule[] {
  return (data ?? [])
    .slice()
    .sort((a, b) => a.position - b.position)
    .map((module) => ({
      ...module,
      items: (module.items ?? []).slice().sort((a, b) => a.position - b.position)
    }));
}

function flattenLessons(modules: CourseModule[]): LessonWithContext[] {
  return modules.flatMap((module, moduleIndex) =>
    (module.items ?? []).map((item, itemIndex) => ({
      ...item,
      moduleId: module.id,
      moduleTitle: module.title,
      moduleDescription: module.description,
      moduleIndex: moduleIndex + 1,
      itemIndex: itemIndex + 1
    }))
  );
}

function lessonKind(item: ModuleItem): string {
  return getModuleItemKind(item);
}

function itemTone(kind: string): "neutral" | "brand" | "amber" | "sky" | "coral" {
  if (kind === "LESSON") return "brand";
  if (kind === "VIDEO") return "sky";
  if (kind === "DOCUMENT" || kind === "PDF") return "amber";
  if (kind === "QUIZ" || kind === "ASSIGNMENT") return "coral";
  return "neutral";
}

function kindLabel(kind: string) {
  const labels: Record<string, string> = {
    LESSON: "Bài học",
    VIDEO: "Video",
    DOCUMENT: "Tài liệu",
    MATERIAL: "Tài liệu",
    PDF: "PDF",
    LINK: "Liên kết",
    QUIZ: "Bài thi",
    ASSIGNMENT: "Bài tập"
  };
  return labels[kind] ?? kind;
}

function progressTypeForLesson(item: ModuleItem) {
  const kind = lessonKind(item);
  if (kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL") return "DOCUMENT_CONFIRMED";
  if (kind === "LINK") return "LINK_CONFIRMED";
  return "LESSON_CONFIRMED";
}

function requiresVerifiedCompletion(item: ModuleItem) {
  const kind = lessonKind(item);
  return kind === "VIDEO" || kind === "QUIZ" || kind === "ASSIGNMENT";
}

function isCompletedProgress(progress?: ItemProgress) {
  return progress?.status === "COMPLETED";
}

function isCompletedSourceStatus(itemState?: CoursePlayerItemState) {
  const status = itemState?.sourceStatus?.toUpperCase();
  return status === "COMPLETED" || status === "GRADED";
}

function isLessonEffectivelyCompleted(
  lesson: LessonWithContext,
  progressById: Map<string, ItemProgress>,
  itemStateById?: Map<string, CoursePlayerItemState>
) {
  return (
    isModuleItemReady(lesson) &&
    (isCompletedProgress(progressById.get(lesson.id)) || isCompletedSourceStatus(itemStateById?.get(lesson.id)))
  );
}

function isLessonLocked(
  lesson: LessonWithContext,
  itemStateById: Map<string, CoursePlayerItemState>,
  moduleStateById: Map<string, CoursePlayerModuleState>
) {
  return Boolean(itemStateById.get(lesson.id)?.locked || moduleStateById.get(lesson.moduleId)?.locked);
}

function lessonLockedReason(
  lesson: LessonWithContext,
  itemStateById: Map<string, CoursePlayerItemState>,
  moduleStateById: Map<string, CoursePlayerModuleState>
) {
  return itemStateById.get(lesson.id)?.lockedReasonText ?? moduleStateById.get(lesson.moduleId)?.lockedReasonText ?? null;
}

function findResumeLesson(
  lessons: LessonWithContext[],
  progressById: Map<string, ItemProgress>,
  itemStateById: Map<string, CoursePlayerItemState>,
  moduleStateById: Map<string, CoursePlayerModuleState>
) {
  const availableLessons = lessons.filter(
    (lesson) => isModuleItemReady(lesson) && !isLessonLocked(lesson, itemStateById, moduleStateById)
  );
  return (
    availableLessons.find((lesson) => lesson.required && !isLessonEffectivelyCompleted(lesson, progressById, itemStateById)) ??
    availableLessons.find((lesson) => !isLessonEffectivelyCompleted(lesson, progressById, itemStateById)) ??
    availableLessons.find((lesson) => lesson.videoMediaId) ??
    availableLessons[0] ??
    lessons.find((lesson) => lesson.required && !isLessonEffectivelyCompleted(lesson, progressById, itemStateById)) ??
    lessons.find((lesson) => !isLessonEffectivelyCompleted(lesson, progressById, itemStateById)) ??
    lessons[0]
  );
}

function lessonMatchesSearch(lesson: LessonWithContext, keyword: string) {
  const normalized = keyword.trim().toLowerCase();
  if (!normalized) return true;
  return [
    lesson.title,
    lesson.description,
    lesson.moduleTitle,
    lesson.moduleDescription,
    lesson.itemType,
    lesson.itemId,
    lesson.videoMediaId,
    lesson.contentUrl,
    ...(lesson.documentMediaIds ?? [])
  ]
    .filter(Boolean)
    .some((value) => value?.toLowerCase().includes(normalized));
}

function lessonMatchesFilter(lesson: LessonWithContext, filter: LessonFilter, completed: boolean) {
  const kind = lessonKind(lesson);
  if (filter === "INCOMPLETE") return !completed;
  if (filter === "REQUIRED") return Boolean(lesson.required);
  if (filter === "VIDEO") return kind === "VIDEO" || Boolean(lesson.videoMediaId);
  if (filter === "ASSESSMENT") return kind === "QUIZ" || kind === "ASSIGNMENT";
  if (filter === "READY") return isModuleItemReady(lesson);
  if (filter === "PREPARING") return !isModuleItemReady(lesson);
  if (filter === "RESOURCES") {
    return (
      kind === "DOCUMENT" ||
      kind === "PDF" ||
      kind === "MATERIAL" ||
      kind === "LINK" ||
      Boolean(lesson.contentUrl) ||
      (lesson.documentMediaIds?.length ?? 0) > 0
    );
  }
  return true;
}

function itemIcon(item: ModuleItem, className = "size-4") {
  const kind = lessonKind(item);
  if (kind === "VIDEO") return <Video className={className} />;
  if (kind === "QUIZ") return <ClipboardCheck className={className} />;
  if (kind === "ASSIGNMENT") return <ListChecks className={className} />;
  if (kind === "DOCUMENT" || kind === "PDF") {
    return <FileText className={className} />;
  }
  if (kind === "LINK") return <ExternalLink className={className} />;
  return <BookOpen className={className} />;
}

function formatMinutes(minutes: number) {
  if (!minutes) return "Chưa ước lượng";
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h ${rest}p` : `${hours}h`;
}

function formatDateTime(value?: string | null) {
  if (!value) return "Chưa đặt";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa đặt";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatScore(value?: number | string | null) {
  if (value === null || value === undefined || value === "") return "Chưa có";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${numeric.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}%`;
}

function totalMinutes(items: ModuleItem[]) {
  return items.reduce((sum, item) => sum + (item.estimatedMinutes ?? 0), 0);
}

type ContentStats = {
  videos: number;
  documents: number;
  links: number;
  quizzes: number;
  assignments: number;
  required: number;
};

function countContent(items: ModuleItem[]): ContentStats {
  return items.reduce<ContentStats>(
    (stats, item) => {
      const kind = lessonKind(item);
      if (kind === "VIDEO" || item.videoMediaId) stats.videos += 1;
      if (kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL" || (item.documentMediaIds?.length ?? 0) > 0) {
        stats.documents += 1;
      }
      if (kind === "LINK" || item.contentUrl) stats.links += 1;
      if (kind === "QUIZ") stats.quizzes += 1;
      if (kind === "ASSIGNMENT") stats.assignments += 1;
      if (item.required) stats.required += 1;
      return stats;
    },
    { videos: 0, documents: 0, links: 0, quizzes: 0, assignments: 0, required: 0 }
  );
}

function compactContentLabels(stats: ContentStats) {
  return [
    stats.videos > 0 ? `${stats.videos} video` : null,
    stats.documents > 0 ? `${stats.documents} tài liệu` : null,
    stats.quizzes > 0 ? `${stats.quizzes} bài thi` : null,
    stats.assignments > 0 ? `${stats.assignments} bài tập` : null,
    stats.links > 0 ? `${stats.links} link` : null
  ].filter(Boolean) as string[];
}

function lessonFocusText(lesson: ModuleItem) {
  const kind = lessonKind(lesson);
  if (kind === "VIDEO") return "Xem video, ghi chú ý chính và tiếp tục bài kế tiếp.";
  if (kind === "QUIZ") return "Làm bài thi để kiểm tra mức độ hiểu sau chương.";
  if (kind === "ASSIGNMENT") return "Đọc yêu cầu, chuẩn bị bài nộp và theo dõi phản hồi.";
  if (kind === "DOCUMENT" || kind === "PDF") return "Đọc học liệu, đối chiếu với nội dung chương.";
  if (kind === "LINK") return "Mở tài nguyên ngoài và quay lại lộ trình khi hoàn tất.";
  return "Hoàn thành nội dung chính của bài học này.";
}

function lessonActionHref(lesson: ModuleItem, courseSlug: string) {
  const kind = lessonKind(lesson);
  if (kind === "QUIZ" && lesson.itemId) return `/quizzes/${lesson.itemId}`;
  if (kind === "ASSIGNMENT") {
    const params = new URLSearchParams();
    if (lesson.itemId) params.set("assignmentId", lesson.itemId);
    const query = params.toString();
    return `/courses/${courseSlug}/assignments${query ? `?${query}` : ""}`;
  }
  if (lesson.contentUrl) return lesson.contentUrl;
  return null;
}

function lessonActionLabel(lesson: ModuleItem) {
  const kind = lessonKind(lesson);
  if (kind === "QUIZ") return "Vào bài thi";
  if (kind === "ASSIGNMENT") return "Mở bài tập";
  if (kind === "LINK") return "Mở liên kết";
  return "Mở nội dung";
}

function lessonPlaceholderText(lesson: ModuleItem) {
  const kind = lessonKind(lesson);
  if (kind === "QUIZ") {
    return "Bài kiểm tra này mở trong trình làm bài riêng để lưu lượt làm, thời gian và điểm số.";
  }
  if (kind === "ASSIGNMENT") {
    return "Bài tập này mở trong khu nộp bài để xem hướng dẫn, hạn nộp và lịch sử bài nộp.";
  }
  if (kind === "VIDEO") {
    return "Bài video này chưa được gắn file phát. Khi admin upload video, player sẽ xuất hiện ngay tại đây.";
  }
  return "Bài này tập trung vào nội dung đọc, tài liệu hoặc hoạt động thực hành.";
}

function isExternalHref(href: string) {
  return href.startsWith("http://") || href.startsWith("https://");
}

type DocumentDownloadGrant = {
  storageKey?: string;
  downloadUrl: string;
  expiresAt?: string;
};

function compactMediaId(mediaId: string) {
  return mediaId.length > 12 ? `${mediaId.slice(0, 8)}...${mediaId.slice(-4)}` : mediaId;
}

function documentLabel(mediaId: string, index: number) {
  return `Tài liệu ${index + 1} · ${compactMediaId(mediaId)}`;
}

function LessonMeta({ item, className }: { item: ModuleItem; className?: string }) {
  const docs = item.documentMediaIds ?? [];
  return (
    <div className={cn("flex flex-wrap items-center gap-3 text-xs font-medium text-ink-500", className)}>
      {(item.estimatedMinutes ?? 0) > 0 && (
        <span className="inline-flex items-center gap-1">
          <Clock3 className="size-3.5" /> {item.estimatedMinutes} phút
        </span>
      )}
      {item.videoMediaId && (
        <span className="inline-flex items-center gap-1">
          <Video className="size-3.5" /> Có video
        </span>
      )}
      {docs.length > 0 && (
        <span className="inline-flex items-center gap-1">
          <FileText className="size-3.5" /> {docs.length} tài liệu
        </span>
      )}
      {item.contentUrl && (
        <span className="inline-flex items-center gap-1">
          <ExternalLink className="size-3.5" /> Link ngoài
        </span>
      )}
    </div>
  );
}

function LessonPlayer({
  lesson,
  userId,
  courseSlug,
  courseId,
  lockedReason,
  onVideoCompleted
}: {
  lesson?: LessonWithContext;
  userId: string;
  courseSlug: string;
  courseId: string;
  lockedReason?: string | null;
  onVideoCompleted?: () => void;
}) {
  if (!lesson) {
    return (
      <div className="grid aspect-video place-items-center rounded-lg border border-white/10 bg-black text-center text-white/70">
        <div>
          <BookOpen className="mx-auto size-10" />
          <p className="mt-3 text-sm font-semibold">Chọn một bài học để bắt đầu.</p>
        </div>
      </div>
    );
  }

  const actionHref = lessonActionHref(lesson, courseSlug);
  const readinessIssue = getModuleItemReadinessIssue(lesson);

  if (lockedReason) {
    return (
      <div className="grid aspect-video place-items-center rounded-lg border border-white/10 bg-black text-center">
        <div className="max-w-md px-6">
          <span className="mx-auto grid size-16 place-items-center rounded-full bg-white/10 text-white">
            <Lock className="size-8" />
          </span>
          <p className="mt-5 text-lg font-bold text-white">Bài học đang khóa</p>
          <p className="mt-2 text-sm leading-6 text-white/65">{lockedReason}</p>
        </div>
      </div>
    );
  }

  if (readinessIssue) {
    return (
      <div className="grid aspect-video place-items-center rounded-lg border border-white/10 bg-black text-center">
        <div className="max-w-md px-6">
          <span className="mx-auto grid size-16 place-items-center rounded-full bg-amber-400/15 text-amber-100">
            <AlertTriangle className="size-8" />
          </span>
          <p className="mt-5 text-lg font-bold text-white">Nội dung đang được hoàn thiện</p>
          <p className="mt-2 text-sm leading-6 text-white/65">
            {readinessIssue}. Bài này vẫn nằm trong lộ trình để bạn biết thứ tự học, nhưng chưa được tính là nội dung sẵn sàng.
          </p>
        </div>
      </div>
    );
  }

  if (lesson.videoMediaId) {
    return (
      <div className="overflow-hidden rounded-lg bg-black shadow-[0_30px_90px_rgba(0,0,0,0.35)]">
        <VideoPlayer videoId={lesson.videoMediaId} userId={userId} onCompleted={onVideoCompleted} />
      </div>
    );
  }

  return (
    <div className="grid aspect-video place-items-center rounded-lg border border-white/10 bg-black text-center">
      <div className="max-w-md px-6">
        <span className="mx-auto grid size-16 place-items-center rounded-full bg-white/10 text-white">
          {itemIcon(lesson, "size-8")}
        </span>
        <p className="mt-5 text-lg font-bold text-white">{lesson.title}</p>
        <p className="mt-2 text-sm leading-6 text-white/65">{lessonPlaceholderText(lesson)}</p>
        {actionHref && (
          <Button asChild className="mt-5">
            {isExternalHref(actionHref) ? (
              <a href={actionHref} target="_blank" rel="noreferrer">
                <ExternalLink className="size-4" />
                {lessonActionLabel(lesson)}
              </a>
            ) : (
              <Link href={actionHref}>
                <PlayCircle className="size-4" />
                {lessonActionLabel(lesson)}
              </Link>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

function LessonButton({
  lesson,
  selected,
  nextUp,
  completed,
  locked,
  lockedReason,
  onSelect
}: {
  lesson: LessonWithContext;
  selected: boolean;
  nextUp?: boolean;
  completed?: boolean;
  locked?: boolean;
  lockedReason?: string | null;
  onSelect: () => void;
}) {
  const kind = lessonKind(lesson);
  const readinessIssue = getModuleItemReadinessIssue(lesson);
  return (
    <button
      type="button"
      disabled={locked}
      onClick={onSelect}
      className={cn(
        "flex w-full items-start gap-3 border-t border-black/10 px-4 py-3 text-left transition",
        locked
          ? "cursor-not-allowed bg-slate-50 text-ink-500 opacity-80"
          : selected
            ? "bg-brand-50"
            : "bg-white hover:bg-[#fbfaf7]"
      )}
    >
      <span
        className={cn(
          "mt-0.5 grid size-8 shrink-0 place-items-center rounded-md text-sm font-bold",
          locked
            ? "bg-black/5 text-ink-400"
            : completed
            ? "bg-brand-600 text-white"
            : selected
              ? "bg-brand-600 text-white"
              : "bg-black/5 text-ink-700"
        )}
      >
        {locked ? <Lock className="size-4" /> : completed ? <CheckCircle2 className="size-4" /> : lesson.itemIndex}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className={cn("shrink-0", selected ? "text-brand-700" : "text-ink-500")}>
            {itemIcon(lesson)}
          </span>
          <span className="truncate text-sm font-bold text-ink-900">{lesson.title}</span>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <LessonMeta item={lesson} className="gap-2" />
          {completed && <Badge tone="brand">Đã xong</Badge>}
          {selected && <Badge tone="brand">Đang học</Badge>}
          {!selected && nextUp && <Badge tone="amber">Tiếp theo</Badge>}
          {locked && <Badge tone="neutral">{lockedReason ?? "Đang khóa"}</Badge>}
          {readinessIssue && <Badge tone="amber">{readinessIssue}</Badge>}
          {!lesson.required && <Badge tone="neutral">Tùy chọn</Badge>}
        </div>
      </div>
      <Badge tone={itemTone(kind)} className="shrink-0">
        {kindLabel(kind)}
      </Badge>
    </button>
  );
}

function LessonNavigator({
  current,
  total,
  previousLesson,
  nextLesson,
  previousLockedReason,
  nextLockedReason,
  onSelect
}: {
  current: number;
  total: number;
  previousLesson?: LessonWithContext;
  nextLesson?: LessonWithContext;
  previousLockedReason?: string | null;
  nextLockedReason?: string | null;
  onSelect: (lessonId: string) => void;
}) {
  return (
    <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-md border border-white/10 bg-white/[0.06] px-3 py-3">
      <div>
        <p className="text-xs font-bold uppercase tracking-wide text-white/45">Tiến trình bài học</p>
        <p className="mt-1 text-sm font-semibold text-white">
          Bài {current} / {total}
        </p>
        {nextLockedReason && <p className="mt-1 text-xs font-semibold text-white/55">Bài tiếp đang khóa: {nextLockedReason}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="inverse"
          size="sm"
          disabled={!previousLesson || Boolean(previousLockedReason)}
          onClick={() => previousLesson && onSelect(previousLesson.id)}
        >
          <ArrowLeft className="size-4" />
          Bài trước
        </Button>
        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={!nextLesson || Boolean(nextLockedReason)}
          onClick={() => nextLesson && onSelect(nextLesson.id)}
        >
          Bài tiếp theo
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}

function progressStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    NOT_STARTED: "Chưa bắt đầu",
    IN_PROGRESS: "Đang làm",
    SUBMITTED: "Đã nộp",
    RESUBMITTED: "Đã nộp lại",
    GRADED: "Đã chấm",
    COMPLETED: "Đã hoàn thành"
  };
  return labels[status ?? ""] ?? status ?? "Chưa bắt đầu";
}

function sourceStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    ATTEMPTS_EXHAUSTED: "Hết lượt làm",
    COMPLETED: "Đã hoàn tất",
    GRADED: "Đã chấm",
    IN_PROGRESS: "Đang làm",
    LOCKED: "Đã khóa",
    NOT_AVAILABLE: "Chưa mở",
    OVERDUE: "Quá hạn",
    PENDING_GRADE: "Chờ chấm",
    READY: "Sẵn sàng",
    RESUBMITTED: "Đã nộp lại",
    SOURCE_STATUS_UNAVAILABLE: "Chưa lấy được trạng thái",
    SUBMITTED: "Đã nộp",
    UNAVAILABLE: "Chưa sẵn sàng"
  };
  return labels[status ?? ""] ?? status ?? "Chưa có trạng thái";
}

function sourceStatusTone(status?: string | null) {
  switch (status?.toUpperCase()) {
    case "COMPLETED":
    case "GRADED":
      return "brand" as const;
    case "OVERDUE":
    case "ATTEMPTS_EXHAUSTED":
      return "amber" as const;
    case "IN_PROGRESS":
    case "SUBMITTED":
    case "RESUBMITTED":
    case "PENDING_GRADE":
      return "sky" as const;
    case "LOCKED":
    case "NOT_AVAILABLE":
    case "SOURCE_STATUS_UNAVAILABLE":
    case "UNAVAILABLE":
      return "neutral" as const;
    default:
      return "neutral" as const;
  }
}

function completionModeLabel(mode?: string | null) {
  if (mode === "VERIFIED") return "Tự xác nhận từ hệ thống";
  if (mode === "SELF") return "Học viên xác nhận";
  return "Theo cấu hình bài học";
}

function certificateStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    COURSE_NOT_COMPLETED: "Chưa hoàn thành khóa",
    ELIGIBILITY_UNAVAILABLE: "Chưa kiểm tra được",
    ELIGIBLE: "Đủ điều kiện",
    FINAL_GRADE_NOT_FINALIZED: "Chờ chốt điểm",
    GRADE_THRESHOLD_NOT_MET: "Chưa đạt điểm",
    ISSUED: "Đã cấp",
    NOT_ELIGIBLE: "Chưa đủ điều kiện",
    PROGRESS_SYNC_PENDING: "Chờ đồng bộ",
    REQUIRED_ITEMS_INCOMPLETE: "Còn thiếu bài"
  };
  return labels[status ?? ""] ?? status ?? "Chưa kiểm tra";
}

function certificateStatusTone(status?: string | null) {
  switch (status?.toUpperCase()) {
    case "ELIGIBLE":
    case "ISSUED":
      return "brand" as const;
    case "FINAL_GRADE_NOT_FINALIZED":
    case "PROGRESS_SYNC_PENDING":
      return "sky" as const;
    case "COURSE_NOT_COMPLETED":
    case "GRADE_THRESHOLD_NOT_MET":
    case "REQUIRED_ITEMS_INCOMPLETE":
      return "amber" as const;
    default:
      return "neutral" as const;
  }
}

function certificateStatusMessage(eligibility: CertificateEligibility) {
  switch (eligibility.status?.toUpperCase()) {
    case "ISSUED":
      return "Chứng chỉ đã được cấp và có thể xác minh công khai.";
    case "ELIGIBLE":
      return "Bạn đã đủ điều kiện. Hệ thống sẽ cấp hoặc hiển thị chứng chỉ sau khi đồng bộ.";
    case "PROGRESS_SYNC_PENDING":
      return "Các mục bắt buộc đã hoàn tất, CourseFlow đang chờ đồng bộ hoàn thành khóa.";
    case "ELIGIBILITY_UNAVAILABLE":
      return "Chưa lấy được điều kiện chứng chỉ. Hãy thử lại sau.";
    default:
      return "Hoàn tất các yêu cầu bên dưới để đủ điều kiện nhận chứng chỉ.";
  }
}

function certificateRequirementTarget(
  label: string,
  missingRequirements: Array<{ itemId: string; title: string }>
) {
  return missingRequirements.find((item) => item.title === label);
}

function CourseProgressPanel({
  progressPercent,
  completedRequiredItems,
  totalRequiredItems,
  completedItems,
  totalItems,
  activeLesson,
  activeItemState,
  activeLessonCompleted,
  activeLockReason,
  certificateEligibility,
  nextAction,
  missingRequirements,
  onSelectLesson
}: {
  progressPercent: number;
  completedRequiredItems: number;
  totalRequiredItems: number;
  completedItems: number;
  totalItems: number;
  activeLesson?: LessonWithContext;
  activeItemState?: CoursePlayerItemState;
  activeLessonCompleted: boolean;
  activeLockReason?: string | null;
  certificateEligibility?: CertificateEligibility | null;
  nextAction?: CoursePlayerNextAction | null;
  missingRequirements: Array<{ itemId: string; title: string }>;
  onSelectLesson: (lessonId: string) => void;
}) {
  const activeKind = activeLesson ? lessonKind(activeLesson) : "LESSON";
  const dueAt = activeItemState?.sourceDueAt ?? activeItemState?.sourceLockAt;

  return (
    <aside className="border-t border-black/10 bg-[#fbfaf7] p-5 lg:col-span-2 xl:col-span-1 xl:border-l xl:border-t-0">
      <div className="space-y-5 xl:sticky xl:top-4">
        <section className="rounded-md border border-black/10 bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase text-brand-600">Tiến độ</p>
              <h2 className="mt-1 text-lg font-bold text-ink-900">Khóa học</h2>
            </div>
            <Badge tone={progressPercent >= 100 ? "brand" : "neutral"}>{progressPercent}%</Badge>
          </div>
          <div className="mt-4">
            <ProgressBar value={progressPercent} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs font-semibold text-ink-500">
            <span>{completedRequiredItems}/{totalRequiredItems} bắt buộc</span>
            <span className="text-right">{completedItems}/{totalItems} bài đã xong</span>
          </div>
        </section>

        {certificateEligibility && (
          <section className="rounded-md border border-black/10 bg-white p-4">
            <div className="flex items-start gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-md bg-accent-50 text-accent-600">
                <Award className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-bold uppercase text-ink-500">Chứng chỉ</p>
                  <Badge tone={certificateStatusTone(certificateEligibility.status)}>
                    {certificateStatusLabel(certificateEligibility.status)}
                  </Badge>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-semibold text-ink-500">
                  <span>Điểm: {formatScore(certificateEligibility.finalGrade)}</span>
                  <span className="text-right">Ngưỡng: {formatScore(certificateEligibility.gradeThreshold)}</span>
                </div>
                <p className="mt-3 text-xs font-semibold leading-5 text-ink-600">
                  {certificateStatusMessage(certificateEligibility)}
                </p>
                {certificateEligibility.verificationCode && (
                  <p className="mt-3 rounded-md bg-[#fbfaf7] px-3 py-2 text-xs font-bold text-ink-700">
                    {certificateEligibility.verificationCode}
                  </p>
                )}
                {(certificateEligibility.missingRequirements?.length ?? 0) > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {certificateEligibility.missingRequirements?.slice(0, 4).map((requirement, index) => {
                      const target = certificateRequirementTarget(requirement.label, missingRequirements);
                      return target ? (
                        <button
                          key={`${requirement.code}-${index}`}
                          type="button"
                          className={cn(
                            "inline-flex items-center rounded-md border border-accent-100 bg-accent-50 px-2 py-0.5 text-left text-xs font-semibold text-accent-600 transition hover:bg-accent-100"
                          )}
                          onClick={() => onSelectLesson(target.itemId)}
                        >
                          {requirement.label}
                        </button>
                      ) : (
                        <Badge key={`${requirement.code}-${index}`} tone="amber">
                          {requirement.label}
                        </Badge>
                      );
                    })}
                    {(certificateEligibility.missingRequirements?.length ?? 0) > 4 && (
                      <Badge tone="neutral">+{(certificateEligibility.missingRequirements?.length ?? 0) - 4} mục</Badge>
                    )}
                  </div>
                )}
                {certificateEligibility.issued && certificateEligibility.verificationCode ? (
                  <Button asChild variant="secondary" className="mt-4 w-full">
                    <Link href={`/certificates/verify/${encodeURIComponent(certificateEligibility.verificationCode)}`}>
                      <ExternalLink className="size-4" />
                      Xác minh chứng chỉ
                    </Link>
                  </Button>
                ) : certificateEligibility.eligible || certificateEligibility.status === "ELIGIBLE" ? (
                  <Button asChild variant="secondary" className="mt-4 w-full">
                    <Link href="/certificates">
                      <Award className="size-4" />
                      Mở ví chứng chỉ
                    </Link>
                  </Button>
                ) : null}
              </div>
            </div>
          </section>
        )}

        {nextAction && (
          <section className="rounded-md border border-brand-100 bg-brand-50 p-4">
            <div className="flex items-start gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-md bg-white text-brand-700 shadow-sm">
                {nextAction.locked ? <Lock className="size-4" /> : <PlayCircle className="size-4" />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold uppercase text-brand-700">Việc nên làm tiếp</p>
                <p className="mt-1 line-clamp-2 text-sm font-bold leading-5 text-ink-900">{nextAction.title}</p>
                <p className="mt-2 text-xs font-semibold leading-5 text-ink-600">{nextAction.reason}</p>
              </div>
            </div>
            <Button
              type="button"
              className="mt-4 w-full"
              variant={nextAction.locked ? "secondary" : "primary"}
              disabled={!nextAction.itemId || nextAction.locked}
              onClick={() => nextAction.itemId && onSelectLesson(nextAction.itemId)}
            >
              {nextAction.locked ? <Lock className="size-4" /> : <ArrowRight className="size-4" />}
              {nextAction.ctaLabel}
            </Button>
          </section>
        )}

        {activeLesson && (
          <section className="rounded-md border border-black/10 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase text-ink-500">Bài đang mở</p>
                <h3 className="mt-1 line-clamp-2 text-sm font-bold leading-5 text-ink-900">{activeLesson.title}</h3>
              </div>
              <Badge tone={activeLessonCompleted ? "brand" : activeLockReason ? "neutral" : itemTone(activeKind)}>
                {activeLessonCompleted ? "Đã xong" : activeLockReason ? "Đang khóa" : kindLabel(activeKind)}
              </Badge>
            </div>
            <div className="mt-4 space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-ink-500">Hoàn thành</span>
                <span className="text-right font-bold text-ink-900">
                  {progressStatusLabel(activeItemState?.progressStatus)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-ink-500">Cơ chế</span>
                <span className="text-right font-bold text-ink-900">
                  {completionModeLabel(activeItemState?.completionMode)}
                </span>
              </div>
              {(activeKind === "QUIZ" || activeKind === "ASSIGNMENT") && (
                <>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-ink-500">Trạng thái nguồn</span>
                    <Badge tone={sourceStatusTone(activeItemState?.sourceStatus)}>
                      {sourceStatusLabel(activeItemState?.sourceStatus)}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-ink-500">Deadline</span>
                    <span className="text-right font-bold text-ink-900">{formatDateTime(dueAt)}</span>
                  </div>
                </>
              )}
            </div>
            {activeLockReason && (
              <p className="mt-4 rounded-md bg-slate-100 px-3 py-2 text-xs font-semibold leading-5 text-ink-600">
                {activeLockReason}
              </p>
            )}
          </section>
        )}

        {missingRequirements.length > 0 && (
          <section className="rounded-md border border-accent-100 bg-accent-50 p-4">
            <p className="text-sm font-bold text-accent-700">Còn thiếu để hoàn thành</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {missingRequirements.slice(0, 6).map((item) => (
                <Badge key={item.itemId} tone="amber">
                  {item.title}
                </Badge>
              ))}
              {missingRequirements.length > 6 && <Badge tone="neutral">+{missingRequirements.length - 6} mục</Badge>}
            </div>
          </section>
        )}
      </div>
    </aside>
  );
}

export function ModuleList({ courseId, courseSlug }: { courseId: string; courseSlug: string }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requestedItemId = searchParams.get("itemId") ?? "";
  const [session, setSession] = useState<StoredSession | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const modulesEnabled = Boolean(session?.accessToken);
  const playerQuery = useCoursePlayer(courseId, modulesEnabled);
  const mark = useMarkProgress(courseId);
  const markItem = useMarkItemProgress(courseId);
  const progress = playerQuery.data?.progress;
  const modules = useMemo(() => normalizeModules(playerQuery.data?.modules), [playerQuery.data?.modules]);
  const lessons = useMemo(() => flattenLessons(modules), [modules]);
  const itemProgressById = useMemo(
    () => new Map((progress?.items ?? []).map((itemProgress) => [itemProgress.itemId, itemProgress])),
    [progress?.items]
  );
  const moduleStateById = useMemo(
    () => new Map((playerQuery.data?.moduleStates ?? []).map((state) => [state.moduleId, state])),
    [playerQuery.data?.moduleStates]
  );
  const itemStateById = useMemo(
    () => new Map((playerQuery.data?.itemStates ?? []).map((state) => [state.itemId, state])),
    [playerQuery.data?.itemStates]
  );
  const [selectedLessonId, setSelectedLessonId] = useState<string>("");
  const [userId, setUserId] = useState("");
  const [lessonSearch, setLessonSearch] = useState("");
  const [lessonFilter, setLessonFilter] = useState<LessonFilter>("ALL");
  const [documentBusyId, setDocumentBusyId] = useState("");
  const [documentError, setDocumentError] = useState("");

  useEffect(() => {
    const current = learnerSession.read();
    setSession(current);
    setUserId(String(current?.user?.id ?? ""));
    setSessionReady(true);
    return learnerSession.subscribe((nextSession) => {
      setSession(nextSession);
      setUserId(String(nextSession?.user?.id ?? ""));
      setSessionReady(true);
    });
  }, []);

  function selectLesson(lessonId: string) {
    setSelectedLessonId(lessonId);
    const params = new URLSearchParams(searchParams.toString());
    params.set("itemId", lessonId);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  useEffect(() => {
    if (lessons.length === 0) return;
    const requestedLesson = requestedItemId ? lessons.find((lesson) => lesson.id === requestedItemId) : undefined;
    const requestedLessonAvailable =
      requestedLesson && !isLessonLocked(requestedLesson, itemStateById, moduleStateById);
    if (requestedLessonAvailable && selectedLessonId !== requestedItemId) {
      setSelectedLessonId(requestedItemId);
      return;
    }
    const selectedLesson = lessons.find((lesson) => lesson.id === selectedLessonId);
    const selectedStillAvailable =
      selectedLesson && !isLessonLocked(selectedLesson, itemStateById, moduleStateById);
    if (!selectedLessonId || !selectedStillAvailable || (requestedLesson && !requestedLessonAvailable)) {
      setSelectedLessonId(findResumeLesson(lessons, itemProgressById, itemStateById, moduleStateById)?.id ?? lessons[0].id);
    }
  }, [itemProgressById, itemStateById, lessons, moduleStateById, requestedItemId, selectedLessonId]);

  const activeLesson = lessons.find((lesson) => lesson.id === selectedLessonId) ?? lessons[0];
  const resumeLesson = useMemo(
    () => findResumeLesson(lessons, itemProgressById, itemStateById, moduleStateById),
    [itemProgressById, itemStateById, lessons, moduleStateById]
  );
  const activeLessonIndex = activeLesson ? lessons.findIndex((lesson) => lesson.id === activeLesson.id) : -1;
  const previousLesson = activeLessonIndex > 0 ? lessons[activeLessonIndex - 1] : undefined;
  const nextLesson = activeLessonIndex >= 0 && activeLessonIndex < lessons.length - 1 ? lessons[activeLessonIndex + 1] : undefined;
  const activeKind = activeLesson ? lessonKind(activeLesson) : "LESSON";
  const activeActionHref = activeLesson ? lessonActionHref(activeLesson, courseSlug) : null;
  const activeReadinessIssue = activeLesson ? getModuleItemReadinessIssue(activeLesson) : null;
  const activeItemState = activeLesson ? itemStateById.get(activeLesson.id) : undefined;
  const activeLockedReason = activeLesson ? lessonLockedReason(activeLesson, itemStateById, moduleStateById) : null;
  const previousLockedReason = previousLesson ? lessonLockedReason(previousLesson, itemStateById, moduleStateById) : null;
  const nextLockedReason = nextLesson ? lessonLockedReason(nextLesson, itemStateById, moduleStateById) : null;
  const activeDocs = activeLesson?.documentMediaIds ?? [];
  const courseMinutes = totalMinutes(lessons);
  const attachedVideoCount = lessons.filter((lesson) => lesson.videoMediaId).length;
  const videoLessonCount = lessons.filter((lesson) => lessonKind(lesson) === "VIDEO").length;
  const courseContentStats = useMemo(() => countContent(lessons), [lessons]);
  const courseContentLabels = useMemo(() => compactContentLabels(courseContentStats), [courseContentStats]);
  const preparingLessonCount = useMemo(() => lessons.filter((lesson) => !isModuleItemReady(lesson)).length, [lessons]);
  const readyLessonCount = lessons.length - preparingLessonCount;
  const effectiveProgress = useMemo(() => {
    const moduleProgressById = new Map<
      string,
      {
        completedItems: number;
        completedRequiredItems: number;
        completed: boolean;
        percentComplete: number;
        totalItems: number;
        totalRequiredItems: number;
      }
    >();
    let completedModules = 0;
    const breakdownByKind = new Map<string, { itemType: string; completedRequired: number; required: number }>();

    for (const module of modules) {
      const moduleLessons = lessons.filter((lesson) => lesson.moduleId === module.id);
      const requiredLessons = moduleLessons.filter((lesson) => lesson.required);
      const completedRequiredLessons = requiredLessons.filter((lesson) =>
        isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById)
      );
      const completedLessons = moduleLessons.filter((lesson) =>
        isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById)
      );
      const totalRequiredItems = requiredLessons.length;
      const completedRequiredItems = completedRequiredLessons.length;
      const completed = totalRequiredItems > 0 && completedRequiredItems >= totalRequiredItems;
      const percentComplete = totalRequiredItems > 0 ? Math.round((completedRequiredItems / totalRequiredItems) * 100) : 0;

      if (completed) completedModules += 1;
      moduleProgressById.set(module.id, {
        completedItems: completedLessons.length,
        completedRequiredItems,
        completed,
        percentComplete,
        totalItems: moduleLessons.length,
        totalRequiredItems
      });
    }

    for (const lesson of lessons) {
      if (!lesson.required) continue;
      const kind = lessonKind(lesson);
      const current = breakdownByKind.get(kind) ?? { itemType: kind, completedRequired: 0, required: 0 };
      current.required += 1;
      if (isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById)) current.completedRequired += 1;
      breakdownByKind.set(kind, current);
    }

    const requiredLessons = lessons.filter((lesson) => lesson.required);
    const completedLessons = lessons.filter((lesson) =>
      isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById)
    );
    const completedRequiredLessons = requiredLessons.filter((lesson) =>
      isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById)
    );
    const totalRequiredItems = requiredLessons.length;
    const completedRequiredItems = completedRequiredLessons.length;
    const percentComplete = totalRequiredItems > 0 ? Math.round((completedRequiredItems / totalRequiredItems) * 100) : 0;

    return {
      breakdown: Array.from(breakdownByKind.values()),
      completedItems: completedLessons.length,
      completedModules,
      completedRequiredItems,
      missingRequirements: requiredLessons
        .filter((lesson) => !isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById))
        .map((lesson) => ({ itemId: lesson.id, title: lesson.title })),
      moduleProgressById,
      percentComplete,
      totalItems: lessons.length,
      totalModules: modules.length,
      totalRequiredItems
    };
  }, [itemProgressById, itemStateById, lessons, modules]);
  const activeLessonCompleted = activeLesson
    ? isLessonEffectivelyCompleted(activeLesson, itemProgressById, itemStateById)
    : false;
  const activeModuleProgress = activeLesson ? effectiveProgress.moduleProgressById.get(activeLesson.moduleId) : undefined;
  const totalRequiredItems = effectiveProgress.totalRequiredItems;
  const completedRequiredItems = effectiveProgress.completedRequiredItems;
  const completedItems = effectiveProgress.completedItems;
  const totalItems = effectiveProgress.totalItems;
  const courseComplete = totalRequiredItems > 0 && completedRequiredItems >= totalRequiredItems;
  const lessonFilterCounts = useMemo(() => {
    return lessonFilterOptions.reduce<Record<LessonFilter, number>>(
      (counts, option) => {
        counts[option.value] = lessons.filter((lesson) =>
          lessonMatchesFilter(lesson, option.value, isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById))
        ).length;
        return counts;
      },
      {
        ALL: 0,
        INCOMPLETE: 0,
        REQUIRED: 0,
        VIDEO: 0,
        ASSESSMENT: 0,
        RESOURCES: 0,
        READY: 0,
        PREPARING: 0
      }
    );
  }, [itemProgressById, itemStateById, lessons]);
  const visibleLessonIds = useMemo(() => {
    return new Set(
      lessons
        .filter((lesson) =>
          lessonMatchesFilter(lesson, lessonFilter, isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById))
        )
        .filter((lesson) => lessonMatchesSearch(lesson, lessonSearch))
        .map((lesson) => lesson.id)
    );
  }, [itemProgressById, itemStateById, lessonFilter, lessonSearch, lessons]);
  const visibleLessonCount = visibleLessonIds.size;
  const hasLessonFilter = lessonFilter !== "ALL" || lessonSearch.trim().length > 0;
  const activeLessonVisible = activeLesson ? visibleLessonIds.has(activeLesson.id) : true;

  useEffect(() => {
    if (!hasLessonFilter || visibleLessonIds.size === 0) return;
    if (activeLesson && visibleLessonIds.has(activeLesson.id)) return;
    const firstVisibleLesson =
      lessons.find(
        (lesson) => visibleLessonIds.has(lesson.id) && !isLessonLocked(lesson, itemStateById, moduleStateById)
      ) ?? lessons.find((lesson) => visibleLessonIds.has(lesson.id));
    if (firstVisibleLesson) setSelectedLessonId(firstVisibleLesson.id);
  }, [activeLesson, hasLessonFilter, itemStateById, lessons, moduleStateById, visibleLessonIds]);

  useEffect(() => {
    setDocumentError("");
  }, [activeLesson?.id]);

  async function openDocument(mediaId: string, mode: "open" | "download") {
    if (activeLockedReason) {
      setDocumentError(activeLockedReason);
      return;
    }
    setDocumentBusyId(mediaId);
    setDocumentError("");
    try {
      const grant = await clientFetch<DocumentDownloadGrant>(
        `/v1/courses/${courseId}/media/assets/${mediaId}/download-url`
      );
      const anchor = document.createElement("a");
      anchor.href = grant.downloadUrl;
      anchor.target = "_blank";
      anchor.rel = "noreferrer";
      if (mode === "download") anchor.download = `courseflow-${compactMediaId(mediaId)}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : "Không mở được tài liệu.");
    } finally {
      setDocumentBusyId("");
    }
  }

  if (!courseId) return <p className="text-ink-500">Thiếu courseId.</p>;
  if (!sessionReady) return <p className="text-ink-500">Đang kiểm tra phiên đăng nhập...</p>;
  if (!session) {
    return (
      <Card>
        <p className="text-sm font-bold text-red-600">Cần đăng nhập để mở phòng học.</p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
          Đăng nhập hoặc đăng ký để xem chương học, video, bài tập, bài thi và tiến độ cá nhân.
        </p>
        <div className="mt-5">
          <EnrollmentCta courseId={courseId} courseSlug={courseSlug} />
        </div>
      </Card>
    );
  }
  if (playerQuery.isLoading) return <p className="text-ink-500">Đang tải chương học...</p>;
  if (playerQuery.isError)
    return (
      <Card>
        <p className="text-sm font-bold text-red-600">Không tải được phòng học.</p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
          Bạn cần đăng nhập và tham gia khóa học trước khi mở nội dung. Nếu đã ghi danh, hãy thử tải lại phòng học.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => void playerQuery.refetch()}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            Thử lại
          </Button>
          <EnrollmentCta courseId={courseId} courseSlug={courseSlug} />
        </div>
      </Card>
    );

  if (modules.length === 0) {
    return <EmptyState title="Khóa học chưa có chương" description="Nội dung sẽ xuất hiện khi giảng viên công khai lộ trình học." />;
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-lg border border-black/10 bg-white shadow-[0_24px_70px_rgba(23,33,31,0.12)]">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_430px] xl:grid-cols-[320px_minmax(0,1fr)_320px]">
          <div className="min-w-0 bg-ink-900 p-4 text-white sm:p-5 lg:order-1 lg:p-6 xl:order-2">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="dark">Phòng học</Badge>
                <span className="text-sm font-medium text-white/65">
                  {readyLessonCount}/{lessons.length} bài sẵn sàng · {formatMinutes(courseMinutes)}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm font-semibold text-white/75">
                {videoLessonCount > 0 && (
                  <span className="inline-flex items-center gap-1">
                    <Video className="size-4" />
                    {attachedVideoCount > 0 ? `${attachedVideoCount} video` : `${videoLessonCount} bài video`}
                  </span>
                )}
                {courseContentStats.quizzes > 0 && <Badge tone="dark">{courseContentStats.quizzes} bài thi</Badge>}
                {courseContentStats.assignments > 0 && (
                  <Badge tone="dark">{courseContentStats.assignments} bài tập</Badge>
                )}
                {preparingLessonCount > 0 && <Badge tone="dark">{preparingLessonCount} đang bổ sung</Badge>}
              </div>
            </div>

            <LessonPlayer
              lesson={activeLesson}
              userId={userId}
              courseSlug={courseSlug}
              courseId={courseId}
              lockedReason={activeLockedReason}
              onVideoCompleted={() => {
                void queryClient.invalidateQueries({ queryKey: ["course-progress", courseId] });
                void queryClient.invalidateQueries({ queryKey: ["course-player", courseId] });
              }}
            />

            {activeLesson && (
              <div className="mt-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="dark">Chương {activeLesson.moduleIndex}</Badge>
                  <Badge tone="dark">Bài {activeLesson.itemIndex}</Badge>
                  <Badge tone={itemTone(activeKind)}>{kindLabel(activeKind)}</Badge>
                  {activeLesson.required && <Badge tone="dark">Bắt buộc</Badge>}
                  {activeReadinessIssue && <Badge tone="amber">{activeReadinessIssue}</Badge>}
                </div>
                <h2 className="mt-4 max-w-3xl text-2xl font-bold leading-tight text-white">
                  {activeLesson.title}
                </h2>
                <p className="mt-2 text-sm font-semibold text-white/55">{activeLesson.moduleTitle}</p>
                {activeLesson.description && (
                  <p className="mt-4 max-w-3xl text-sm leading-6 text-white/72">
                    {activeLesson.description}
                  </p>
                )}

                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  <div className="rounded-md border border-white/10 bg-white/[0.06] p-3">
                    <p className="text-xs font-bold uppercase text-white/45">Mục tiêu</p>
                    <p className="mt-1 text-sm leading-5 text-white/80">{lessonFocusText(activeLesson)}</p>
                  </div>
                  <div className="rounded-md border border-white/10 bg-white/[0.06] p-3">
                    <p className="text-xs font-bold uppercase text-white/45">Tiếp theo</p>
                    <p className="mt-1 text-sm font-semibold leading-5 text-white/80">
                      {nextLesson ? nextLesson.title : "Bạn đang ở bài cuối của khóa học."}
                    </p>
                  </div>
                  <div className="rounded-md border border-white/10 bg-white/[0.06] p-3">
                    <p className="text-xs font-bold uppercase text-white/45">Học liệu</p>
                    <p className="mt-1 text-sm font-semibold leading-5 text-white/80">
                      {[
                        activeReadinessIssue ? "Đang bổ sung" : null,
                        activeLesson.videoMediaId ? "Video" : null,
                        activeDocs.length > 0 ? `${activeDocs.length} tài liệu` : null,
                        activeLesson.contentUrl ? "Link ngoài" : null
                      ]
                        .filter(Boolean)
                        .join(" · ") || "Nội dung đọc"}
                    </p>
                  </div>
                  <div className="rounded-md border border-white/10 bg-white/[0.06] p-3 md:col-span-3">
                    <p className="text-xs font-bold uppercase text-white/45">Điều kiện hoàn thành</p>
                    <p className="mt-1 text-sm font-semibold leading-5 text-white/80">
	                      {activeReadinessIssue
	                        ? "Bài này sẽ được mở hoàn thành sau khi học liệu sẵn sàng."
                          : activeLockedReason
                            ? activeLockedReason
	                        : activeLessonCompleted
	                          ? "Bài này đã được tính vào tiến độ khóa học."
                          : activeLesson.required
                          ? "Hoàn thành bài này để tăng tiến độ mục bắt buộc."
                          : "Bài tùy chọn không chặn hoàn thành khóa học."}
                    </p>
                  </div>
                </div>

                <LessonNavigator
                  current={activeLessonIndex >= 0 ? activeLessonIndex + 1 : 0}
                  total={lessons.length}
                  previousLesson={previousLesson}
                  nextLesson={nextLesson}
                  previousLockedReason={previousLockedReason}
                  nextLockedReason={nextLockedReason}
                  onSelect={selectLesson}
                />

                <div className="mt-5 flex flex-wrap gap-3">
                  {activeLesson.videoMediaId && !activeLockedReason && (
                    <Button asChild>
                      <Link href={`/videos/${activeLesson.videoMediaId}`}>
                        <span className="inline-flex items-center gap-2">
                          <PlayCircle className="size-4" />
                          <span>Mở trang video</span>
                        </span>
                      </Link>
                    </Button>
                  )}
                  {activeActionHref && !activeLesson.videoMediaId && !activeLockedReason && (
                    <Button
                      asChild
                      variant={lessonKind(activeLesson) === "LINK" ? "inverse" : "primary"}
                    >
                      {isExternalHref(activeActionHref) ? (
                        <a href={activeActionHref} target="_blank" rel="noreferrer">
                          <ExternalLink className="size-4" />
                          {lessonActionLabel(activeLesson)}
                        </a>
                      ) : (
                        <Link href={activeActionHref}>
                          <PlayCircle className="size-4" />
                          {lessonActionLabel(activeLesson)}
                        </Link>
                      )}
                    </Button>
                  )}
                  {activeLesson.contentUrl && activeLesson.videoMediaId && !activeLockedReason && (
                    <Button asChild variant="inverse">
                      <a href={activeLesson.contentUrl} target="_blank" rel="noreferrer">
                        <ExternalLink className="size-4" />
                        Mở liên kết
                      </a>
                    </Button>
                  )}
                  {activeDocs.length > 0 && !activeLockedReason && (
                    <Button
                      type="button"
                      variant="inverse"
                      disabled={Boolean(documentBusyId)}
                      onClick={() => openDocument(activeDocs[0], "open")}
                    >
                      <FileText className="size-4" />
                      {documentBusyId === activeDocs[0] ? "Đang mở tài liệu" : activeDocs.length > 1 ? "Mở tài liệu đầu" : "Mở tài liệu"}
                    </Button>
                  )}
	                  {requiresVerifiedCompletion(activeLesson) ? (
                    <Badge tone={activeLessonCompleted ? "brand" : activeLockedReason ? "neutral" : "neutral"}>
	                      {activeLessonCompleted ? "Bài đã xong" : activeLockedReason ? "Bài đang khóa" : "Tự cập nhật khi hoàn tất"}
	                    </Badge>
                  ) : (
                    <Button
                      variant="inverse"
                      disabled={activeLessonCompleted || markItem.isPending || Boolean(activeReadinessIssue || activeLockedReason)}
                      onClick={() =>
                        markItem.mutate({
                          moduleId: activeLesson.moduleId,
                          itemId: activeLesson.id,
                          progressType: progressTypeForLesson(activeLesson)
                        })
                      }
                    >
                      <CheckCircle2 className="size-4" />
                      {activeReadinessIssue
                        ? "Chưa thể hoàn thành"
                        : activeLockedReason
                          ? "Bài đang khóa"
                          : activeLessonCompleted
                          ? "Bài đã xong"
                          : markItem.isPending
                            ? "Đang lưu"
                            : "Đánh dấu bài xong"}
                    </Button>
                  )}
                  {activeModuleProgress && (
                    <Badge tone={activeModuleProgress.completed ? "brand" : "neutral"}>
                      Chương {activeModuleProgress.completedRequiredItems}/{activeModuleProgress.totalRequiredItems} mục bắt buộc
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </div>

          <aside className="border-black/10 bg-white lg:order-2 lg:max-h-[calc(100vh-104px)] lg:overflow-y-auto lg:border-l xl:order-1 xl:border-l-0 xl:border-r">
            <div className="sticky top-0 z-10 border-b border-black/10 bg-white/95 p-5 backdrop-blur">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase text-brand-600">Nội dung học</p>
                  <h2 className="mt-1 text-xl font-bold text-ink-900">Nội dung khóa học</h2>
                </div>
                <Badge tone="brand">{modules.length} chương</Badge>
              </div>
              {lessons.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-ink-500">
                      {completedRequiredItems}/{totalRequiredItems} mục bắt buộc
                    </span>
                    <span className="font-bold text-ink-900">{effectiveProgress.percentComplete}%</span>
                  </div>
                  <ProgressBar value={effectiveProgress.percentComplete} />
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-semibold text-ink-500">
                    <span>
                      {effectiveProgress.completedModules}/{effectiveProgress.totalModules} chương đủ điều kiện
                    </span>
                    <span className="text-right">{completedItems}/{totalItems} bài đã xong</span>
                  </div>
                </div>
              )}
              {courseContentLabels.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {courseContentLabels.slice(0, 5).map((label) => (
                    <Badge key={label} tone="neutral">
                      {label}
                    </Badge>
                  ))}
                </div>
              )}
              {resumeLesson && (
                <div
                  className={cn(
                    "mt-4 rounded-md border p-3",
                    courseComplete
                      ? "border-signal-100 bg-signal-50"
                      : "border-brand-100 bg-brand-50"
                  )}
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={cn(
                        "grid size-9 shrink-0 place-items-center rounded-md bg-white shadow-sm",
                        courseComplete ? "text-signal-700" : "text-brand-700"
                      )}
                    >
                      {itemIcon(resumeLesson)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p
                          className={cn(
                            "text-xs font-bold uppercase",
                            courseComplete ? "text-signal-700" : "text-brand-700"
                          )}
                        >
                          {courseComplete ? "Khóa học đã hoàn tất" : "Bài cần học tiếp"}
                        </p>
                        {courseComplete && <Badge tone="sky">Ôn tập</Badge>}
                        {!courseComplete && resumeLesson.id === activeLesson?.id && <Badge tone="brand">Đang mở</Badge>}
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedLessonId(resumeLesson.id)}
                        className="mt-1 block w-full truncate text-left text-sm font-bold text-ink-900 hover:text-brand-700"
                      >
                        {resumeLesson.title}
                      </button>
                      <p className="mt-1 text-xs font-medium text-ink-500">
                        {courseComplete ? "Ôn lại: " : ""}
                        Chương {resumeLesson.moduleIndex} · Bài {resumeLesson.itemIndex} · {kindLabel(lessonKind(resumeLesson))}
                      </p>
                    </div>
                  </div>
                </div>
              )}
              <div className="mt-4">
                <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase text-ink-500">
                  <ListFilter className="size-3.5" />
                  Lọc nội dung
                </div>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-3 size-4 text-ink-500/55" />
                  <TextInput
                    value={lessonSearch}
                    onChange={(event) => setLessonSearch(event.target.value)}
                    placeholder="Tìm bài, mô tả, link..."
                    className="min-h-10 rounded-md py-2 pl-9 pr-3"
                  />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {lessonFilterOptions.map((option) => {
                    const selected = lessonFilter === option.value;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => setLessonFilter(option.value)}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-bold transition",
                          selected
                            ? "border-brand-500 bg-brand-600 text-white shadow-sm"
                            : "border-black/10 bg-white text-ink-600 hover:border-brand-200 hover:bg-brand-50"
                        )}
                      >
                        <span>{option.label}</span>
                        <span
                          className={cn(
                            "rounded bg-black/5 px-1.5 py-0.5 text-[10px]",
                            selected && "bg-white/20 text-white"
                          )}
                        >
                          {lessonFilterCounts[option.value]}
                        </span>
                      </button>
                    );
                  })}
                </div>
                {hasLessonFilter && (
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs font-semibold text-ink-500">
                    <span>
                      Đang hiển thị {visibleLessonCount}/{lessons.length} bài
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setLessonFilter("ALL");
                        setLessonSearch("");
                      }}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-brand-700 hover:bg-brand-50"
                    >
                      <RotateCcw className="size-3.5" />
                      Xóa lọc
                    </button>
                  </div>
                )}
                {hasLessonFilter && !activeLessonVisible && (
                  <p className="mt-2 rounded-md bg-accent-50 px-3 py-2 text-xs font-semibold leading-5 text-accent-700">
                    Bài đang mở không nằm trong bộ lọc hiện tại.
                  </p>
                )}
              </div>
            </div>

            <div>
              {modules.map((module, moduleIndex) => {
                const items = module.items ?? [];
                const lessonsInModule = items.map<LessonWithContext>((item, itemIndex) => ({
                  ...item,
                  moduleId: module.id,
                  moduleTitle: module.title,
                  moduleDescription: module.description,
                  moduleIndex: moduleIndex + 1,
                  itemIndex: itemIndex + 1
                }));
                const visibleLessonsInModule = lessonsInModule.filter((lesson) => visibleLessonIds.has(lesson.id));
                const hiddenLessonCount = lessonsInModule.length - visibleLessonsInModule.length;
                const moduleDuration = totalMinutes(items);
                const moduleContentLabels = compactContentLabels(countContent(items));
                const modulePreparingCount = items.filter((item) => !isModuleItemReady(item)).length;
                const moduleProgress = effectiveProgress.moduleProgressById.get(module.id);
                const moduleState = moduleStateById.get(module.id);
                const moduleRequiredCount = moduleProgress?.totalRequiredItems ?? items.filter((item) => item.required).length;
                const canCompleteModule =
                  !moduleState?.locked &&
                  modulePreparingCount === 0 &&
                  (moduleRequiredCount === 0 || Boolean(moduleProgress?.completed));
                return (
                  <details key={module.id} open className="group border-b border-black/10 last:border-b-0">
                    <summary className="flex cursor-pointer list-none items-start justify-between gap-3 p-4 marker:hidden">
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-brand-600">Chương {moduleIndex + 1}</p>
                        <h3 className="mt-1 text-sm font-bold leading-5 text-ink-900">{module.title}</h3>
                        <p className="mt-1 text-xs text-ink-500">
                          {items.length} bài · {formatMinutes(moduleDuration)}
                        </p>
                        {moduleProgress && (
                          <div className="mt-2">
                            <div className="mb-1 flex items-center justify-between text-[11px] font-semibold text-ink-500">
                              <span>
                                {moduleProgress.completedRequiredItems}/{moduleProgress.totalRequiredItems} bắt buộc
                              </span>
                              <span>{moduleProgress.percentComplete}%</span>
                            </div>
                            <ProgressBar value={moduleProgress.percentComplete} />
                          </div>
                        )}
                        {(moduleContentLabels.length > 0 || modulePreparingCount > 0) && (
                          <p className="mt-2 flex flex-wrap gap-1.5">
	                            {modulePreparingCount > 0 && (
	                              <span className="rounded-md bg-accent-50 px-2 py-0.5 text-[11px] font-semibold text-accent-700">
	                                {modulePreparingCount} đang bổ sung
	                              </span>
	                            )}
                            {moduleState?.locked && (
                              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-ink-500">
                                Đang khóa
                              </span>
                            )}
                            {moduleContentLabels.slice(0, 4).map((label) => (
                              <span
                                key={label}
                                className="rounded-md bg-black/[0.04] px-2 py-0.5 text-[11px] font-semibold text-ink-500"
                              >
                                {label}
                              </span>
                            ))}
                          </p>
                        )}
                      </div>
                      <ChevronDown className="mt-1 size-4 shrink-0 text-ink-500 transition group-open:rotate-180" />
                    </summary>

                    {module.description && (
                      <p className="px-4 pb-3 text-xs leading-5 text-ink-500">{module.description}</p>
                    )}

                    {items.length === 0 ? (
                      <p className="border-t border-black/10 px-4 py-4 text-sm text-ink-500">
                        Chương này chưa có bài học.
                      </p>
                    ) : visibleLessonsInModule.length === 0 ? (
                      <div className="border-t border-black/10 px-4 py-4">
                        <p className="text-sm font-semibold text-ink-700">Không có bài phù hợp bộ lọc.</p>
                        {hasLessonFilter && (
                          <p className="mt-1 text-xs leading-5 text-ink-500">
                            {items.length} bài trong chương này đang bị ẩn.
                          </p>
                        )}
                      </div>
                    ) : (
                      <>
                        {visibleLessonsInModule.map((lesson) => (
                          <LessonButton
                            key={lesson.id}
                            lesson={lesson}
                            selected={lesson.id === activeLesson?.id}
                            nextUp={lesson.id === nextLesson?.id}
                            completed={isLessonEffectivelyCompleted(lesson, itemProgressById, itemStateById)}
                            locked={isLessonLocked(lesson, itemStateById, moduleStateById)}
                            lockedReason={lessonLockedReason(lesson, itemStateById, moduleStateById)}
                            onSelect={() => selectLesson(lesson.id)}
                          />
                        ))}
                        {hasLessonFilter && hiddenLessonCount > 0 && (
                          <p className="border-t border-black/10 px-4 py-2 text-xs font-semibold text-ink-500">
                            Đang ẩn {hiddenLessonCount} bài trong chương này.
                          </p>
                        )}
                      </>
                    )}

                    <div className="border-t border-black/10 bg-[#fbfaf7] p-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full"
                        disabled={mark.isPending || !canCompleteModule}
                        onClick={() => mark.mutate({ moduleId: module.id })}
                      >
                        <CheckCircle2 className="size-4" />
                        {moduleProgress?.completed || moduleRequiredCount === 0
                          ? "Chương đã đủ điều kiện"
                          : moduleState?.locked
                            ? "Chương đang khóa"
                          : modulePreparingCount > 0
                            ? "Chờ bổ sung nội dung"
                            : "Hoàn thành các bài bắt buộc trước"}
                      </Button>
                    </div>
                  </details>
                );
              })}
            </div>
          </aside>

          <CourseProgressPanel
            progressPercent={effectiveProgress.percentComplete}
            completedRequiredItems={completedRequiredItems}
            totalRequiredItems={totalRequiredItems}
            completedItems={completedItems}
            totalItems={totalItems}
            activeLesson={activeLesson}
            activeItemState={activeItemState}
            activeLessonCompleted={activeLessonCompleted}
            activeLockReason={activeLockedReason}
            certificateEligibility={playerQuery.data?.certificateEligibility}
            nextAction={playerQuery.data?.nextAction}
            missingRequirements={effectiveProgress.missingRequirements}
            onSelectLesson={selectLesson}
          />
	        </div>
	      </section>

      {activeLesson && (
        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="rounded-lg border border-black/10 bg-white p-5 shadow-[0_18px_45px_rgba(23,33,31,0.08)]">
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
                <ListChecks className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-brand-600">Thông tin bài học</p>
                <h3 className="mt-1 text-xl font-bold text-ink-900">{activeLesson.title}</h3>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-ink-500">
                  {activeLesson.description ??
                    "Giảng viên chưa thêm mô tả chi tiết cho bài học này. Bạn vẫn có thể học theo video, tài liệu hoặc liên kết được gắn trong curriculum."}
                </p>
                <LessonMeta item={activeLesson} className="mt-4" />
                {effectiveProgress.breakdown.length > 0 && (
                  <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {effectiveProgress.breakdown.map((item) => (
                      <div key={item.itemType} className="rounded-md border border-black/10 bg-[#fbfaf7] p-3">
                        <p className="text-xs font-bold uppercase text-ink-500">{kindLabel(item.itemType)}</p>
                        <p className="mt-1 text-lg font-bold text-ink-900">
                          {item.completedRequired}/{item.required}
                        </p>
                        <p className="mt-1 text-xs font-semibold text-ink-500">mục bắt buộc</p>
                      </div>
                    ))}
                  </div>
                )}
                {effectiveProgress.missingRequirements.length > 0 && (
                  <div className="mt-5 rounded-md border border-accent-100 bg-accent-50 p-3">
                    <p className="text-sm font-bold text-accent-700">Còn thiếu để hoàn thành khóa</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {effectiveProgress.missingRequirements.slice(0, 5).map((item) => (
                        <Badge key={item.itemId} tone="amber">
                          {item.title}
                        </Badge>
                      ))}
                      {effectiveProgress.missingRequirements.length > 5 && (
                        <Badge tone="neutral">+{effectiveProgress.missingRequirements.length - 5} mục</Badge>
                      )}
                    </div>
                  </div>
                )}
                {activeReadinessIssue && (
                  <div className="mt-5 rounded-md border border-accent-100 bg-accent-50 p-3">
                    <p className="inline-flex items-center gap-2 text-sm font-bold text-accent-700">
                      <AlertTriangle className="size-4" />
                      Nội dung chưa sẵn sàng
                    </p>
                    <p className="mt-2 text-sm leading-6 text-ink-700">
                      {activeReadinessIssue}. Bạn có thể chuyển sang bài khác trong lộ trình và quay lại khi giảng viên cập nhật.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-5">
            <CourseQuizList courseId={courseId} compact variant="rail" />
            <CourseQAPanel courseId={courseId} />
            <div className="rounded-lg border border-black/10 bg-white p-5 shadow-[0_18px_45px_rgba(23,33,31,0.08)]">
              <p className="text-sm font-bold text-brand-600">Học liệu</p>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3 rounded-md bg-[#fbfaf7] p-3">
                  <span className="inline-flex items-center gap-2 font-semibold text-ink-900">
                    <Video className="size-4 text-signal-600" /> Video
                  </span>
                  <Badge tone={activeLesson.videoMediaId ? "sky" : activeKind === "VIDEO" ? "amber" : "neutral"}>
                    {activeLesson.videoMediaId ? "Phát được" : activeKind === "VIDEO" ? "Chưa gắn file" : "Không"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between gap-3 rounded-md bg-[#fbfaf7] p-3">
                  <span className="inline-flex items-center gap-2 font-semibold text-ink-900">
                    <FileText className="size-4 text-accent-600" /> Tài liệu
                  </span>
                  <Badge tone={activeDocs.length > 0 ? "amber" : "neutral"}>
                    {activeDocs.length > 0 ? `${activeDocs.length} tài liệu` : "Chưa có"}
                  </Badge>
                </div>
                {activeDocs.length > 0 && (
                  <div className="space-y-2 rounded-md border border-black/10 bg-white p-3">
                    {activeDocs.map((mediaId, index) => (
                      <div
                        key={mediaId}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-[#fbfaf7] px-3 py-2"
                      >
                        <span className="min-w-0 truncate text-sm font-semibold text-ink-800">
                          {documentLabel(mediaId, index)}
                        </span>
                        <span className="flex shrink-0 gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            disabled={Boolean(documentBusyId || activeLockedReason)}
                            onClick={() => openDocument(mediaId, "open")}
                          >
                            <ExternalLink className="size-4" />
                            {activeLockedReason ? "Khóa" : "Mở"}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            disabled={Boolean(documentBusyId || activeLockedReason)}
                            onClick={() => openDocument(mediaId, "download")}
                          >
                            <Download className="size-4" />
                            Tải
                          </Button>
                        </span>
                      </div>
                    ))}
                    {documentError && (
                      <p className="rounded-md bg-coral-50 px-3 py-2 text-xs font-semibold leading-5 text-coral-600">
                        {documentError}
                      </p>
                    )}
                  </div>
                )}
                <div className="flex items-center justify-between gap-3 rounded-md bg-[#fbfaf7] p-3">
                  <span className="inline-flex items-center gap-2 font-semibold text-ink-900">
                    <ExternalLink className="size-4 text-brand-700" /> Link ngoài
                  </span>
                  <Badge tone={activeLesson.contentUrl ? "brand" : "neutral"}>
                    {activeLesson.contentUrl ? "Có link" : "Chưa có"}
                  </Badge>
                </div>
              </div>
            </div>
            <CourseChatPanel courseId={courseId} />
          </div>
        </section>
      )}
    </div>
  );
}
