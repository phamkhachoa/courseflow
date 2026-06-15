import { FormEvent, type ReactNode, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Copy,
  ExternalLink,
  Eye,
  FileUp,
  FileText,
  History,
  Layers3,
  Link2,
  ListChecks,
  PackageCheck,
  Plus,
  Pencil,
  RotateCcw,
  Rocket,
  Send,
  ShieldCheck,
  Trash2,
  UploadCloud,
  Video,
  XCircle
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  Spinner,
  Table,
  Td,
  Textarea,
  Th,
  Notice
} from "@/shared/ui";
import {
  getAssetUploadUrl,
  getVideoUploadUrl,
  registerAsset,
  registerVideo
} from "@/modules/media/api";
import { listAssignments } from "@/modules/assignments/api";
import { listCourseQuizzes } from "@/modules/quizzes/api";
import {
  approveCourseReview,
  archiveModule,
  archiveModuleItem,
  createModule,
  createModuleItem,
  duplicateModule,
  duplicateModuleItem,
  getCourseReviewChecklist,
  getCourseVersionDiff,
  getCourseDraft,
  getCourseDraftPreview,
  listCourseReviewHistory,
  listCourseVersions,
  publishCourse,
  rejectCourseReview,
  rollbackCourseVersion,
  submitCourseForReview,
  updateCurriculum,
  updateModule,
  updateModuleItem,
  type CourseReviewChecklistItem,
  type CourseVersion,
  type CourseVersionDiff,
  type CourseReviewAudit,
  type CourseDraftPreview,
  type CourseModule,
  type CourseModuleItem
} from "../api";
import {
  buildContentIssues,
  moveItemOrder,
  moveModuleOrder,
  orderedCourseModules,
  orderedModuleItems,
  buildWorkspaceSummary,
  type CurriculumOrder,
  type ContentIssue,
  type DependencyStatus,
  type WorkspaceDependency,
  type CourseWorkspaceSummary
} from "../workspace";

type ItemForm = {
  title: string;
  itemType: string;
  refId: string;
  description: string;
  videoMediaId: string;
  documentMediaIds: string[];
  contentUrl: string;
  estimatedMinutes: string;
  required: boolean;
};

type UploadFiles = {
  videoFile?: File;
  documentFiles: File[];
};

const FALLBACK_REVIEW_CHECKLIST: CourseReviewChecklistItem[] = [
  { id: "content-ready", label: "Nội dung không còn blocker", required: true },
  { id: "dependency-ready", label: "Media, quiz và assignment đã sẵn sàng", required: true },
  { id: "learner-preview-checked", label: "Learner preview đã được kiểm tra", required: true },
  { id: "publish-risk-reviewed", label: "Rủi ro publish đã được rà soát", required: true }
];

const createEmptyItem = (): ItemForm => ({
  title: "",
  itemType: "LESSON",
  refId: "",
  description: "",
  videoMediaId: "",
  documentMediaIds: [],
  contentUrl: "",
  estimatedMinutes: "20",
  required: true
});

const createEmptyFiles = (): UploadFiles => ({
  documentFiles: []
});

function formFromItem(item: CourseModuleItem): ItemForm {
  return {
    title: item.title,
    itemType: item.itemType,
    refId: item.refId ?? "",
    description: item.description ?? "",
    videoMediaId: item.videoMediaId ?? "",
    documentMediaIds: item.documentMediaIds ?? [],
    contentUrl: item.contentUrl ?? "",
    estimatedMinutes: item.estimatedMinutes == null ? "" : String(item.estimatedMinutes),
    required: item.required
  };
}

function itemTypeResetPatch(itemType: string): Partial<ItemForm> {
  if (itemType === "VIDEO") {
    return { itemType, refId: "", documentMediaIds: [], contentUrl: "" };
  }
  if (itemType === "DOCUMENT") {
    return { itemType, refId: "", videoMediaId: "" };
  }
  if (itemType === "LINK") {
    return { itemType, refId: "", videoMediaId: "", documentMediaIds: [] };
  }
  if (itemType === "QUIZ" || itemType === "ASSIGNMENT") {
    return { itemType, refId: "", videoMediaId: "", documentMediaIds: [], contentUrl: "" };
  }
  return { itemType, refId: "", videoMediaId: "" };
}

function itemIcon(itemType: string) {
  if (itemType === "VIDEO" || itemType === "LESSON") return <Video size={16} />;
  if (itemType === "DOCUMENT" || itemType === "PDF" || itemType === "MATERIAL") return <FileText size={16} />;
  if (itemType === "LINK") return <Link2 size={16} />;
  return <BookOpen size={16} />;
}

function contentTypeLabel(itemType: string) {
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
  return labels[itemType] ?? itemType;
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function reviewStateLabel(value?: string) {
  const labels: Record<string, string> = {
    DRAFT: "Đang biên soạn",
    IN_REVIEW: "Đang chờ duyệt",
    APPROVED: "Đã duyệt",
    REJECTED: "Cần chỉnh sửa",
    PUBLISHED: "Đã publish"
  };
  return labels[value ?? ""] ?? value ?? "Đang biên soạn";
}

function reviewActionLabel(value: string) {
  const labels: Record<string, string> = {
    CREATE_DRAFT: "Tạo draft",
    SUBMIT_REVIEW: "Gửi duyệt",
    APPROVE: "Duyệt",
    REJECT: "Từ chối",
    PUBLISH: "Publish",
    ROLLBACK_TO_DRAFT: "Rollback draft"
  };
  return labels[value] ?? value;
}

function reviewChecklistLabel(id: string, checklist: CourseReviewChecklistItem[]) {
  return checklist.find((item) => item.id === id)?.label ?? id;
}

function displayReviewChecklistItems(items: CourseReviewChecklistItem[]) {
  return items.map((item) => ({
    ...item,
    label: FALLBACK_REVIEW_CHECKLIST.find((fallback) => fallback.id === item.id)?.label ?? item.label
  }));
}

function diffChangeLabel(value: string) {
  const labels: Record<string, string> = {
    ADDED: "Thêm",
    REMOVED: "Xóa",
    CHANGED: "Sửa",
    MOVED: "Di chuyển"
  };
  return labels[value] ?? value;
}

function diffScopeLabel(value: string) {
  return value === "MODULE" ? "Chương" : value === "ITEM" ? "Bài" : value;
}

function diffFieldLabel(value?: string) {
  const labels: Record<string, string> = {
    title: "Tên",
    description: "Mô tả",
    position: "Vị trí",
    itemType: "Loại",
    refId: "Nguồn",
    videoMediaId: "Video",
    documentMediaIds: "Tài liệu",
    contentUrl: "URL",
    estimatedMinutes: "Thời lượng",
    required: "Bắt buộc"
  };
  return value ? labels[value] ?? value : "Nội dung";
}

function formatDateTime(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function itemTypeLabel(itemType: string) {
  return contentTypeLabel(itemType === "MATERIAL" ? "DOCUMENT" : itemType);
}

async function putToUploadUrl(uploadUrl: string, file: File) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file
  });
  if (!response.ok) {
    throw new Error(`Upload failed (${response.status})`);
  }
}

async function uploadVideoFile(courseId: string, title: string, file: File): Promise<string> {
  const grant = await getVideoUploadUrl(title, file.name, file.type || "video/mp4");
  await putToUploadUrl(grant.uploadUrl, file);
  const video = await registerVideo({
    title,
    sourceStorageKey: grant.storageKey,
    courseId
  });
  return video.id;
}

async function uploadDocumentFile(file: File): Promise<string> {
  const grant = await getAssetUploadUrl(file.name, file.type || "application/octet-stream");
  await putToUploadUrl(grant.uploadUrl, file);
  const asset = await registerAsset({
    fileName: file.name,
    contentType: file.type || "application/octet-stream",
    storageKey: grant.storageKey,
    sizeBytes: file.size
  });
  return asset.id;
}

function formatMinutes(minutes: number) {
  if (!minutes) return "Chưa ước lượng";
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h ${rest}p` : `${hours}h`;
}

function issueTone(issues: ContentIssue[]) {
  if (issues.some((issue) => issue.severity === "blocker")) return "danger";
  if (issues.length > 0) return "warning";
  return "success";
}

function issueLabel(issues: ContentIssue[]) {
  const blockers = issues.filter((issue) => issue.severity === "blocker").length;
  const warnings = issues.filter((issue) => issue.severity === "warning").length;
  if (blockers > 0) return `${blockers} blocker`;
  if (warnings > 0) return `${warnings} cảnh báo`;
  return "Ready";
}

function issuesForModule(issues: ContentIssue[], moduleId: string) {
  return issues.filter((issue) => issue.moduleId === moduleId);
}

function issuesForItem(issues: ContentIssue[], itemId: string) {
  return issues.filter((issue) => issue.itemId === itemId);
}

function dependencyTone(status: DependencyStatus) {
  if (status === "ready") return "success";
  if (status === "loading" || status === "warning") return "warning";
  if (status === "error" || status === "blocked") return "danger";
  return "neutral";
}

function dependencyLabel(status: DependencyStatus) {
  const labels: Record<DependencyStatus, string> = {
    ready: "Ready",
    loading: "Đang tải",
    error: "Lỗi tải",
    empty: "Không dùng",
    blocked: "Blocker",
    warning: "Cảnh báo"
  };
  return labels[status];
}

function dependencyIcon(key: WorkspaceDependency["key"]) {
  if (key === "media") return <PackageCheck size={18} />;
  if (key === "quiz") return <ListChecks size={18} />;
  return <FileText size={18} />;
}

function dependencyLink(key: WorkspaceDependency["key"], courseId: string) {
  if (key === "media") return `/media?courseId=${courseId}`;
  if (key === "quiz") return `/quizzes?courseId=${courseId}`;
  return `/assignments?courseId=${courseId}`;
}

function LessonCard({
  item,
  displayIndex,
  issues,
  actions
}: {
  item: CourseModuleItem;
  displayIndex: number;
  issues: ContentIssue[];
  actions?: ReactNode;
}) {
  const docs = item.documentMediaIds ?? [];
  return (
    <div id={`item-${item.itemId}`} className="scroll-mt-6 rounded-lg border border-black/10 bg-white p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="grid size-8 place-items-center rounded-md bg-brand-50 text-brand-700">
              {itemIcon(item.itemType)}
            </span>
            <h3 className="min-w-0 break-words font-bold text-slate-950">{item.title}</h3>
            <Badge value={item.itemType === "MATERIAL" ? "DOCUMENT" : item.itemType} label={contentTypeLabel(item.itemType)} />
            {item.required && <Badge value="REQUIRED" />}
            <Badge tone={issueTone(issues)} label={issueLabel(issues)} />
          </div>
          {item.description && (
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">{item.description}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            {item.estimatedMinutes != null && (
              <span className="inline-flex items-center gap-1">
                <Clock3 size={14} /> {item.estimatedMinutes} phút
              </span>
            )}
            {item.videoMediaId && (
              <span className="inline-flex items-center gap-1">
                <Video size={14} /> Video {shortId(item.videoMediaId)}
              </span>
            )}
            {docs.length > 0 && (
              <span className="inline-flex items-center gap-1">
                <FileText size={14} /> {docs.length} tài liệu
              </span>
            )}
            {item.contentUrl && (
              <span className="inline-flex items-center gap-1">
                <Link2 size={14} /> External link
              </span>
            )}
            {item.refId && (
              <span className="inline-flex items-center gap-1">
                <ListChecks size={14} /> Ref {shortId(item.refId)}
              </span>
            )}
          </div>
          {issues.length > 0 && (
            <div className="mt-3 space-y-2">
              {issues.map((issue) => (
                <div
                  key={issue.id}
                  className={
                    issue.severity === "blocker"
                      ? "rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900"
                      : "rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
                  }
                >
                  <span className="font-semibold">{issue.title}</span>
                  <span className="ml-1 opacity-85">{issue.detail}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {actions}
          <span className="text-xs font-bold text-slate-400">#{displayIndex}</span>
        </div>
      </div>
    </div>
  );
}

function UploadTile({
  id,
  title,
  description,
  icon,
  accept,
  multiple,
  selectedText,
  onChange
}: {
  id: string;
  title: string;
  description: string;
  icon: ReactNode;
  accept: string;
  multiple?: boolean;
  selectedText?: string;
  onChange: (files: FileList | null) => void;
}) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <label
        htmlFor={id}
        className="flex min-h-36 cursor-pointer flex-col justify-between rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 transition hover:border-brand-300 hover:bg-brand-50"
      >
        <span>
          <span className="mb-3 grid size-10 place-items-center rounded-md bg-white text-brand-700 shadow-sm">
            {icon}
          </span>
          <span className="block font-semibold text-slate-900">{title}</span>
          <span className="mt-1 block text-sm leading-5 text-slate-500">{description}</span>
        </span>
        <span className="mt-4 inline-flex w-fit items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-brand-700 shadow-sm">
          <FileUp size={16} />
          Chọn file
        </span>
      </label>
      <input
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={(e) => onChange(e.target.files)}
        className="sr-only"
      />
      {selectedText && <p className="mt-2 text-xs font-medium text-slate-500">{selectedText}</p>}
    </div>
  );
}

function ContentIssueList({ issues, pending }: { issues: ContentIssue[]; pending?: boolean }) {
  if (pending) {
    return (
      <Notice tone="warning" title="Đang kiểm tra nội dung tham chiếu">
        Hệ thống đang tải quiz/assignment được gắn vào curriculum trước khi kết luận readiness.
      </Notice>
    );
  }

  if (issues.length === 0) {
    return (
      <Notice tone="success" title="Không còn blocker nội dung">
        Course draft có đủ học liệu bắt buộc để đi tiếp trong lifecycle hiện tại.
      </Notice>
    );
  }

  return (
    <div className="space-y-3">
      {issues.map((issue) => (
        <div
          key={issue.id}
          className={
            issue.severity === "blocker"
              ? "rounded-md border border-red-200 bg-red-50 p-3"
              : "rounded-md border border-amber-200 bg-amber-50 p-3"
          }
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  value={issue.severity === "blocker" ? "REVOKED" : "DRAFT"}
                  label={issue.severity === "blocker" ? "Blocker" : "Cảnh báo"}
                />
                <Badge value={issue.itemType} label={itemTypeLabel(issue.itemType)} />
                {issue.moduleTitle && <span className="text-xs font-semibold text-slate-500">{issue.moduleTitle}</span>}
              </div>
              <p className="mt-2 text-sm font-bold text-slate-950">{issue.title}</p>
              {issue.itemTitle && <p className="mt-0.5 text-xs font-semibold text-slate-600">{issue.itemTitle}</p>}
              <p className="mt-1 text-sm leading-6 text-slate-600">{issue.detail}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ReadinessGate({
  label,
  ready,
  pending,
  blockedText,
  readyText,
  issues
}: {
  label: string;
  ready: boolean;
  pending?: boolean;
  blockedText: string;
  readyText: string;
  issues: ContentIssue[];
}) {
  const blockers = issues.filter((issue) => issue.severity === "blocker");
  const tone = ready ? "success" : pending ? "warning" : "danger";

  return (
    <div
      className={
        ready
          ? "rounded-lg border border-emerald-200 bg-emerald-50/70 p-4"
          : pending
            ? "rounded-lg border border-amber-200 bg-amber-50/70 p-4"
            : "rounded-lg border border-red-200 bg-red-50/70 p-4"
      }
    >
      <div className="flex items-start gap-3">
        <span
          className={
            ready
              ? "grid size-10 shrink-0 place-items-center rounded-md bg-white text-emerald-700 shadow-sm"
              : pending
                ? "grid size-10 shrink-0 place-items-center rounded-md bg-white text-amber-700 shadow-sm"
                : "grid size-10 shrink-0 place-items-center rounded-md bg-white text-red-700 shadow-sm"
          }
        >
          {ready ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-bold text-slate-950">{label}</p>
            <Badge
              tone={tone}
              label={ready ? "Sẵn sàng" : pending ? "Đang kiểm tra" : blockers.length > 0 ? `${blockers.length} blocker` : "Chờ review"}
            />
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {ready ? readyText : pending ? "Đang kiểm tra quiz/assignment được gắn vào curriculum." : blockedText}
          </p>
        </div>
      </div>
    </div>
  );
}

function PublishConfidencePanel({
  summary,
  preview,
  previewLoading,
  previewError
}: {
  summary: CourseWorkspaceSummary;
  preview?: CourseDraftPreview;
  previewLoading: boolean;
  previewError: boolean;
}) {
  const previewIssueCount = preview?.issues?.length ?? 0;
  const previewReady = preview?.readinessStatus === "READY_FOR_REVIEW";
  const nextAction = preview?.nextAction ?? preview?.firstRequiredItem;

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50/80 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-950">
            <ShieldCheck size={18} className="text-brand-700" />
            Publish confidence
          </div>
          <p className="mt-1 text-sm leading-6 text-slate-500">{summary.publishConfidence.detail}</p>
        </div>
        <Badge tone={summary.publishConfidence.tone} label={summary.publishConfidence.label} />
      </div>
      <div className="mt-4">
        <div className="flex items-end justify-between gap-3">
          <span className="text-3xl font-bold text-slate-950">{summary.publishConfidence.score}%</span>
          <a
            href="#draft-learner-preview"
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
            title="Xem draft learner preview"
          >
            <Eye size={16} />
            Draft preview
          </a>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-white">
          <div
            className={
              summary.publishConfidence.tone === "success"
                ? "h-full rounded-full bg-emerald-500"
                : summary.publishConfidence.tone === "warning"
                  ? "h-full rounded-full bg-amber-500"
                  : "h-full rounded-full bg-red-500"
            }
            style={{ width: `${summary.publishConfidence.score}%` }}
          />
        </div>
      </div>
      <div id="draft-learner-preview" className="mt-4 border-t border-slate-200 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-950">
            <Eye size={16} className="text-brand-700" />
            Draft learner preview
          </div>
          {previewLoading ? (
            <Badge tone="warning" label="Đang tải" />
          ) : previewError ? (
            <Badge tone="danger" label="Không tải được" />
          ) : (
            <Badge
              tone={previewReady ? "success" : "danger"}
              label={previewReady ? "Ready" : `${previewIssueCount} issue`}
            />
          )}
        </div>
        {previewLoading ? (
          <p className="mt-3 text-sm text-slate-500">Đang tạo preview từ draft hiện tại.</p>
        ) : previewError ? (
          <p className="mt-3 text-sm text-red-700">Không tải được draft preview từ authoring service.</p>
        ) : preview ? (
          <div className="mt-3 space-y-3">
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <p className="font-semibold text-slate-500">Module</p>
                <p className="mt-1 text-sm font-bold text-slate-950">{preview.moduleCount}</p>
              </div>
              <div>
                <p className="font-semibold text-slate-500">Item</p>
                <p className="mt-1 text-sm font-bold text-slate-950">{preview.itemCount}</p>
              </div>
              <div>
                <p className="font-semibold text-slate-500">Thời lượng</p>
                <p className="mt-1 text-sm font-bold text-slate-950">{formatMinutes(preview.totalEstimatedMinutes)}</p>
              </div>
            </div>
            <div className="rounded-md border border-slate-200 bg-white p-3">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Next action</p>
              {nextAction ? (
                <>
                  <p className="mt-1 truncate text-sm font-bold text-slate-950">{nextAction.title}</p>
                  <p className="mt-1 truncate text-xs text-slate-500">{nextAction.moduleTitle} · {contentTypeLabel(nextAction.itemType)}</p>
                </>
              ) : (
                <p className="mt-1 text-sm text-slate-500">Chưa có required item để learner bắt đầu.</p>
              )}
            </div>
            {preview.issues?.length > 0 && (
              <p className="text-sm leading-6 text-red-700">{preview.issues[0]}</p>
            )}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">Chưa có preview từ authoring service.</p>
        )}
      </div>
    </div>
  );
}

function DependencySummaryPanel({
  dependencies,
  courseId
}: {
  dependencies: WorkspaceDependency[];
  courseId: string;
}) {
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      {dependencies.map((dependency) => (
        <div key={dependency.key} className="rounded-md border border-slate-200 bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className="grid size-9 shrink-0 place-items-center rounded-md bg-slate-100 text-slate-700">
                {dependencyIcon(dependency.key)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-950">{dependency.label}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {dependency.ready}/{dependency.total} ready
                </p>
              </div>
            </div>
            <Badge tone={dependencyTone(dependency.status)} label={dependencyLabel(dependency.status)} />
          </div>
          <p className="mt-3 min-h-10 text-sm leading-5 text-slate-600">{dependency.detail}</p>
          <Link
            to={dependencyLink(dependency.key, courseId)}
            className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-brand-700 hover:underline"
          >
            Mở console
            <ExternalLink size={12} />
          </Link>
        </div>
      ))}
    </div>
  );
}

function ReviewOperationsPanel({
  reviewState,
  reviewNote,
  reviewChecklist,
  checklistItems,
  history,
  historyLoading,
  historyError,
  historyErrorValue,
  canApprove,
  canApproveDecision,
  canRejectDecision,
  learnerPreviewGateReady,
  approvePending,
  rejectPending,
  approveTitle,
  rejectTitle,
  onReviewNoteChange,
  onChecklistChange,
  onApprove,
  onReject
}: {
  reviewState: string;
  reviewNote: string;
  reviewChecklist: Record<string, boolean>;
  checklistItems: CourseReviewChecklistItem[];
  history?: CourseReviewAudit[];
  historyLoading: boolean;
  historyError: boolean;
  historyErrorValue: unknown;
  canApprove: boolean;
  canApproveDecision: boolean;
  canRejectDecision: boolean;
  learnerPreviewGateReady: boolean;
  approvePending: boolean;
  rejectPending: boolean;
  approveTitle: string;
  rejectTitle: string;
  onReviewNoteChange: (value: string) => void;
  onChecklistChange: (id: string, checked: boolean) => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  const entries = history ?? [];
  const lifecycleTone = reviewState === "IN_REVIEW" ? "warning" : reviewState === "APPROVED" || reviewState === "PUBLISHED" ? "success" : "neutral";

  return (
    <Card className="mb-4">
      <CardHeader
        title={
          <span className="inline-flex items-center gap-2">
            <ClipboardCheck size={18} className="text-brand-700" />
            Review operations
          </span>
        }
        subtitle="Checklist, note và lịch sử quyết định nội dung."
        actions={<Badge value={reviewState} label={reviewStateLabel(reviewState)} />}
      />
      <div className="grid gap-5 p-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Notice
            tone={lifecycleTone}
            title={reviewState === "IN_REVIEW" ? "Đang chờ reviewer quyết định" : reviewStateLabel(reviewState)}
          >
            {reviewState === "IN_REVIEW"
              ? "Reviewer cần hoàn tất checklist trước khi duyệt và phải ghi rõ lý do nếu từ chối."
              : "Course chưa ở trạng thái cần reviewer quyết định."}
          </Notice>

          <div className="space-y-2">
            {checklistItems.map((item) => {
              const lockedByPreview = item.id === "learner-preview-checked" && !learnerPreviewGateReady;
              const disabled = !canApprove || lockedByPreview;
              return (
                <label
                  key={item.id}
                  className={
                    disabled
                      ? "flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm font-semibold text-slate-400"
                      : "flex items-start gap-3 rounded-md border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700"
                  }
                >
                  <input
                    type="checkbox"
                    checked={Boolean(reviewChecklist[item.id]) && !lockedByPreview}
                    disabled={disabled}
                    onChange={(event) => onChecklistChange(item.id, event.target.checked)}
                    className="mt-1"
                  />
                  <span>
                    {item.label}
                    {item.required && <span className="ml-1 text-xs text-slate-400">Bắt buộc</span>}
                    {lockedByPreview && <span className="mt-1 block text-xs text-slate-400">Tải draft preview trước</span>}
                  </span>
                </label>
              );
            })}
          </div>

          <FormField
            label="Reviewer note"
            htmlFor="review-note"
            hint={canApprove ? "Bắt buộc khi từ chối, tùy chọn khi duyệt." : undefined}
          >
            <Textarea
              id="review-note"
              value={reviewNote}
              onChange={(event) => onReviewNoteChange(event.target.value)}
              rows={4}
              disabled={!canApprove}
              placeholder="Ghi chú review, blocker còn lại hoặc xác nhận publish readiness..."
            />
          </FormField>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              disabled={!canApproveDecision || approvePending}
              title={approveTitle}
              onClick={onApprove}
            >
              <CheckCircle2 size={16} />
              {approvePending ? "Đang duyệt..." : "Duyệt"}
            </Button>
            <Button
              variant="danger"
              disabled={!canRejectDecision || rejectPending}
              title={rejectTitle}
              onClick={onReject}
            >
              <XCircle size={16} />
              {rejectPending ? "Đang trả..." : "Từ chối"}
            </Button>
          </div>
        </div>

        <div className="min-w-0">
          <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-950">
            <History size={18} className="text-brand-700" />
            Review history
          </div>
          {historyLoading && <Spinner label="Đang tải lịch sử review" />}
          {historyError && <ErrorState error={historyErrorValue} />}
          {!historyLoading && !historyError && entries.length === 0 && (
            <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm text-slate-500">
              Chưa có lịch sử review cho course này.
            </div>
          )}
          {!historyLoading && !historyError && entries.length > 0 && (
            <div className="space-y-3">
              {entries.map((entry) => (
                <div key={entry.id} className="rounded-md border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge value={entry.action} label={reviewActionLabel(entry.action)} />
                        <span className="text-xs font-semibold text-slate-500">v{entry.versionNo}</span>
                        {entry.fromState && entry.toState && (
                          <span className="text-xs font-semibold text-slate-500">
                            {reviewStateLabel(entry.fromState)}{" -> "}{reviewStateLabel(entry.toState)}
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-sm font-semibold text-slate-900">
                        Actor {entry.actorId}{entry.actorRole ? ` · ${entry.actorRole}` : ""}
                      </p>
                      {entry.note && <p className="mt-1 text-sm leading-6 text-slate-600">{entry.note}</p>}
                      {(entry.checklist?.length ?? 0) > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {entry.checklist?.map((item) => (
                            <Badge key={item} value="READY" label={reviewChecklistLabel(item, checklistItems)} />
                          ))}
                        </div>
                      )}
                    </div>
                    <span className="shrink-0 text-xs font-semibold text-slate-400">{formatDateTime(entry.createdAt)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function VersionControlPanel({
  versions,
  selectedPublished,
  diff,
  diffLoading,
  diffError,
  diffErrorValue,
  rollbackNote,
  rollbackPending,
  rollbackError,
  rollbackErrorValue,
  currentVersionNo,
  onSelectedVersionChange,
  onRollbackNoteChange,
  onRollback
}: {
  versions?: CourseVersion[];
  selectedPublished?: CourseVersion;
  diff?: CourseVersionDiff;
  diffLoading: boolean;
  diffError: boolean;
  diffErrorValue: unknown;
  rollbackNote: string;
  rollbackPending: boolean;
  rollbackError: boolean;
  rollbackErrorValue: unknown;
  currentVersionNo: number;
  onSelectedVersionChange: (value: number | undefined) => void;
  onRollbackNoteChange: (value: string) => void;
  onRollback: () => void;
}) {
  const publishedVersions = versions?.filter((version) => version.state === "PUBLISHED") ?? [];
  const totalChanges = diff
    ? diff.addedModules + diff.removedModules + diff.changedModules + diff.movedModules
      + diff.addedItems + diff.removedItems + diff.changedItems + diff.movedItems
    : 0;
  const rollbackReady = Boolean(selectedPublished) && rollbackNote.trim().length > 0;

  return (
    <Card className="mb-4">
      <CardHeader
        title={
          <span className="inline-flex items-center gap-2">
            <History size={18} className="text-brand-700" />
            Version diff & rollback
          </span>
        }
        subtitle="So sánh draft hiện tại với snapshot đã publish và tạo draft rollback có audit."
        actions={
          selectedPublished
            ? <Badge value="PUBLISHED" label={`Rollback target v${selectedPublished.versionNo}`} />
            : <Badge value="DRAFT" label="Chưa có live snapshot" />
        }
      />
      <div className="grid gap-5 p-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Notice tone={selectedPublished ? "info" : "warning"} title={selectedPublished ? "Published snapshot được khóa" : "Chưa thể diff"}>
            {selectedPublished
              ? `Rollback sẽ lấy published snapshot v${selectedPublished.versionNo} để tạo draft mới v${currentVersionNo + 1}; learner vẫn học từ bản live hiện tại cho tới lần publish tiếp theo.`
              : "Course cần ít nhất một phiên bản PUBLISHED trước khi có thể so sánh hoặc rollback."}
          </Notice>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase text-slate-500">Published</p>
              <p className="mt-1 text-2xl font-bold text-slate-950">{publishedVersions.length}</p>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold uppercase text-slate-500">Changes</p>
              <p className="mt-1 text-2xl font-bold text-slate-950">{diff ? totalChanges : "-"}</p>
            </div>
          </div>

          <FormField label="Published snapshot" htmlFor="rollback-version">
            <Select
              id="rollback-version"
              value={selectedPublished?.versionNo ?? ""}
              disabled={publishedVersions.length === 0 || rollbackPending}
              onChange={(event) => onSelectedVersionChange(event.target.value ? Number(event.target.value) : undefined)}
            >
              {publishedVersions.length === 0 && <option value="">Chưa có published version</option>}
              {publishedVersions.map((version) => (
                <option key={version.id} value={version.versionNo}>
                  v{version.versionNo}{version.publishedAt ? ` - ${formatDateTime(version.publishedAt)}` : ""}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField
            label="Rollback note"
            htmlFor="rollback-note"
            hint={selectedPublished ? "Bắt buộc để tạo audit trail." : undefined}
          >
            <Textarea
              id="rollback-note"
              value={rollbackNote}
              onChange={(event) => onRollbackNoteChange(event.target.value)}
              rows={4}
              disabled={!selectedPublished || rollbackPending}
              placeholder="Lý do rollback snapshot này thành draft mới..."
            />
          </FormField>

          {rollbackError && <ErrorState error={rollbackErrorValue} />}
          <Button
            variant="danger"
            disabled={!rollbackReady || rollbackPending}
            title={rollbackReady ? "Tạo draft rollback từ live snapshot" : "Chọn snapshot và nhập rollback note"}
            onClick={onRollback}
          >
            <RotateCcw size={16} />
            {rollbackPending ? "Đang rollback..." : "Rollback thành draft"}
          </Button>
        </div>

        <div className="min-w-0">
          {diffLoading && <Spinner label="Đang tải version diff" />}
          {diffError && <ErrorState error={diffErrorValue} />}
          {!diffLoading && !diffError && !diff && (
            <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm text-slate-500">
              Chưa có diff để hiển thị.
            </div>
          )}
          {diff && (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-md border border-slate-200 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Module</p>
                  <p className="mt-1 text-sm font-bold text-slate-950">
                    +{diff.addedModules} / -{diff.removedModules} / {diff.changedModules} sửa / {diff.movedModules} chuyển
                  </p>
                </div>
                <div className="rounded-md border border-slate-200 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Item</p>
                  <p className="mt-1 text-sm font-bold text-slate-950">
                    +{diff.addedItems} / -{diff.removedItems} / {diff.changedItems} sửa / {diff.movedItems} chuyển
                  </p>
                </div>
                <div className="rounded-md border border-slate-200 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Required +</p>
                  <p className="mt-1 text-sm font-bold text-emerald-700">{diff.requiredItemsAdded}</p>
                </div>
                <div className="rounded-md border border-slate-200 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Required -</p>
                  <p className="mt-1 text-sm font-bold text-red-700">{diff.requiredItemsRemoved}</p>
                </div>
              </div>

              {diff.warnings.length > 0 && (
                <div className="space-y-2">
                  {diff.warnings.map((warning) => (
                    <Notice key={warning} tone="warning" title="Publish risk">
                      {warning}
                    </Notice>
                  ))}
                </div>
              )}

              <div className="space-y-2">
                {diff.changes.slice(0, 10).map((change, index) => (
                  <div key={`${change.scope}-${change.itemId ?? change.moduleId}-${change.field}-${index}`} className="rounded-md border border-slate-200 bg-white p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge value={change.changeType} label={diffChangeLabel(change.changeType)} />
                      <span className="text-xs font-semibold text-slate-500">{diffScopeLabel(change.scope)}</span>
                      <span className="min-w-0 truncate text-sm font-bold text-slate-950">{change.title ?? change.itemId ?? change.moduleId}</span>
                    </div>
                    <p className="mt-2 text-xs font-semibold text-slate-500">
                      {diffFieldLabel(change.field)}: {change.fromValue ?? "-"}{" -> "}{change.toValue ?? "-"}
                    </p>
                  </div>
                ))}
                {diff.changes.length > 10 && (
                  <p className="text-xs font-semibold text-slate-500">
                    Còn {diff.changes.length - 10} thay đổi khác trong snapshot diff.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function WorkspaceStats({
  summary,
  moduleCount,
  versionNo
}: {
  summary: CourseWorkspaceSummary;
  moduleCount: number;
  versionNo: number;
}) {
  return (
    <div className="mb-6 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      <div className="rounded-lg border border-black/10 bg-white p-4">
        <p className="text-sm text-slate-500">Chương</p>
        <p className="mt-1 text-3xl font-bold text-slate-950">{moduleCount}</p>
        <p className="mt-2 text-xs text-slate-500">Module trong outline</p>
      </div>
      <div className="rounded-lg border border-black/10 bg-white p-4">
        <p className="text-sm text-slate-500">Items</p>
        <p className="mt-1 text-3xl font-bold text-slate-950">{summary.totalItems}</p>
        <p className="mt-2 text-xs text-slate-500">{summary.requiredItems} bắt buộc · {summary.optionalItems} tùy chọn</p>
      </div>
      <div className="rounded-lg border border-black/10 bg-white p-4">
        <p className="text-sm text-slate-500">Thời lượng</p>
        <p className="mt-1 break-words text-2xl font-bold text-slate-950">{formatMinutes(summary.totalMinutes)}</p>
        <p className="mt-2 text-xs text-slate-500">Tổng estimated minutes</p>
      </div>
      <div className="rounded-lg border border-black/10 bg-white p-4">
        <p className="text-sm text-slate-500">Dependencies</p>
        <p className="mt-1 text-3xl font-bold text-slate-950">{summary.mediaCount}</p>
        <p className="mt-2 text-xs text-slate-500">{summary.videoCount} video · {summary.documentCount} tài liệu · {summary.linkCount} link</p>
      </div>
      <div className="rounded-lg border border-black/10 bg-white p-4">
        <p className="text-sm text-slate-500">Phiên bản</p>
        <p className="mt-1 text-3xl font-bold text-slate-950">v{versionNo}</p>
        <p className="mt-2 text-xs text-slate-500">{summary.blockers} blocker · {summary.warnings} cảnh báo</p>
      </div>
    </div>
  );
}

function CourseOutline({ modules, issues }: { modules: CourseModule[]; issues: ContentIssue[] }) {
  return (
    <Card className="sticky top-6 max-h-[calc(100vh-7rem)] overflow-y-auto">
      <CardHeader
        title={
          <span className="inline-flex items-center gap-2">
            <ListChecks size={18} className="text-brand-700" />
            Outline
          </span>
        }
        subtitle="Module, item và trạng thái readiness"
      />
      <div className="space-y-3 p-4">
        {modules.length === 0 && <EmptyState message="Chưa có chương" />}
        {modules.map((module) => {
          const moduleIssues = issuesForModule(issues, module.moduleId);
          const items = orderedModuleItems(module);

          return (
            <div key={module.moduleId} className="rounded-md border border-black/10 bg-white">
              <a
                href={`#module-${module.moduleId}`}
                className="flex items-start justify-between gap-3 px-3 py-3 text-sm transition hover:bg-brand-50"
              >
                <span className="min-w-0">
                  <span className="block truncate font-bold text-slate-900">{module.title}</span>
                  <span className="mt-1 block text-xs text-slate-500">{items.length} item</span>
                </span>
                <Badge tone={issueTone(moduleIssues)} label={issueLabel(moduleIssues)} />
              </a>
              <div className="border-t border-black/10 px-2 py-2">
                {items.length === 0 ? (
                  <p className="px-2 py-2 text-xs text-slate-500">Chưa có item trong module này.</p>
                ) : (
                  <div className="space-y-1">
                    {items.map((item) => {
                      const itemIssues = issuesForItem(issues, item.itemId);
                      return (
                        <a
                          key={item.itemId}
                          href={`#item-${item.itemId}`}
                          className="flex items-center justify-between gap-2 rounded-md px-2 py-2 text-xs transition hover:bg-slate-50"
                        >
                          <span className="flex min-w-0 items-center gap-2">
                            <span className="grid size-6 shrink-0 place-items-center rounded bg-slate-100 text-slate-600">
                              {itemIcon(item.itemType)}
                            </span>
                            <span className="truncate font-semibold text-slate-700">{item.title}</span>
                          </span>
                          <Badge tone={issueTone(itemIssues)} label={issueLabel(itemIssues)} className="shrink-0" />
                        </a>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function CourseDraftPage() {
  const { courseId = "" } = useParams();
  const qc = useQueryClient();

  const draft = useQuery({
    queryKey: queryKeys.authoring.draft(courseId),
    queryFn: () => getCourseDraft(courseId),
    enabled: Boolean(courseId)
  });
  const draftPreview = useQuery({
    queryKey: queryKeys.authoring.preview(courseId),
    queryFn: () => getCourseDraftPreview(courseId),
    enabled: Boolean(courseId),
    retry: 1,
    staleTime: 30_000
  });

  const versions = useQuery({
    queryKey: queryKeys.authoring.versions(courseId),
    queryFn: () => listCourseVersions(courseId),
    enabled: Boolean(courseId)
  });
  const [selectedRollbackVersionNo, setSelectedRollbackVersionNo] = useState<number | undefined>();
  const publishedVersions = versions.data?.filter((version) => version.state === "PUBLISHED") ?? [];
  const selectedPublishedVersion = publishedVersions.find((version) => version.versionNo === selectedRollbackVersionNo)
    ?? publishedVersions[0];
  const versionDiff = useQuery({
    queryKey: queryKeys.authoring.versionDiff(courseId, selectedPublishedVersion?.versionNo),
    queryFn: () => getCourseVersionDiff(courseId, selectedPublishedVersion?.versionNo),
    enabled: Boolean(courseId && selectedPublishedVersion)
  });
  const reviewHistory = useQuery({
    queryKey: queryKeys.authoring.reviewHistory(courseId),
    queryFn: () => listCourseReviewHistory(courseId),
    enabled: Boolean(courseId)
  });
  const reviewChecklistPolicy = useQuery({
    queryKey: ["authoring", "review-checklist"] as const,
    queryFn: getCourseReviewChecklist,
    retry: 1,
    staleTime: 300_000
  });
  const quizzes = useQuery({
    queryKey: queryKeys.quizzes.list(courseId),
    queryFn: () => listCourseQuizzes(courseId),
    enabled: Boolean(courseId),
    retry: 1,
    staleTime: 60_000
  });
  const assignments = useQuery({
    queryKey: queryKeys.assignments.list(courseId),
    queryFn: () => listAssignments(courseId),
    enabled: Boolean(courseId),
    retry: 1,
    staleTime: 60_000
  });
  const reviewChecklistItems = reviewChecklistPolicy.data?.length
    ? displayReviewChecklistItems(reviewChecklistPolicy.data)
    : FALLBACK_REVIEW_CHECKLIST;

  const [moduleForm, setModuleForm] = useState({ title: "", description: "" });
  const [itemForms, setItemForms] = useState<Record<string, ItemForm>>({});
  const [uploadFiles, setUploadFiles] = useState<Record<string, UploadFiles>>({});
  const [reviewNote, setReviewNote] = useState("");
  const [reviewChecklist, setReviewChecklist] = useState<Record<string, boolean>>({});
  const [rollbackNote, setRollbackNote] = useState("");
  const [editingModuleId, setEditingModuleId] = useState<string | null>(null);
  const [moduleEdits, setModuleEdits] = useState<Record<string, { title: string; description: string }>>({});
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [itemEdits, setItemEdits] = useState<Record<string, ItemForm>>({});

  function invalidateDraft() {
    qc.invalidateQueries({ queryKey: queryKeys.authoring.draft(courseId) });
    qc.invalidateQueries({ queryKey: queryKeys.authoring.preview(courseId) });
  }

  function invalidateLifecycle() {
    invalidateDraft();
    qc.invalidateQueries({ queryKey: queryKeys.authoring.versions(courseId) });
    qc.invalidateQueries({ queryKey: ["authoring", "version-diff", courseId] });
    qc.invalidateQueries({ queryKey: queryKeys.authoring.reviewHistory(courseId) });
  }

  const addModule = useMutation({
    mutationFn: () => createModule(courseId, {
      title: moduleForm.title,
      description: moduleForm.description || undefined,
      status: "DRAFT"
    }),
    onSuccess: () => {
      setModuleForm({ title: "", description: "" });
      invalidateLifecycle();
    }
  });

  const addItem = useMutation({
    mutationFn: async ({ moduleId, form, files }: { moduleId: string; form: ItemForm; files: UploadFiles }) => {
      const uploadedVideoId = files.videoFile
        ? await uploadVideoFile(courseId, form.title, files.videoFile)
        : undefined;
      const uploadedDocumentIds = files.documentFiles.length > 0
        ? await Promise.all(files.documentFiles.map(uploadDocumentFile))
        : [];
      const documentMediaIds = [...form.documentMediaIds, ...uploadedDocumentIds];
      return createModuleItem(courseId, moduleId, {
        title: form.title,
        itemType: form.itemType,
        refId: form.refId || undefined,
        description: form.description || undefined,
        videoMediaId: uploadedVideoId || form.videoMediaId || undefined,
        documentMediaIds,
        contentUrl: form.contentUrl || undefined,
        estimatedMinutes: form.estimatedMinutes ? Number(form.estimatedMinutes) : undefined,
        required: form.required
      });
    },
    onSuccess: (_data, variables) => {
      setItemForms((prev) => ({ ...prev, [variables.moduleId]: createEmptyItem() }));
      setUploadFiles((prev) => ({ ...prev, [variables.moduleId]: createEmptyFiles() }));
      invalidateLifecycle();
    }
  });

  const updateModuleMutation = useMutation({
    mutationFn: ({ moduleId, form }: { moduleId: string; form: { title: string; description: string } }) =>
      updateModule(courseId, moduleId, {
        title: form.title,
        description: form.description || undefined
      }),
    onSuccess: () => {
      setEditingModuleId(null);
      invalidateLifecycle();
    }
  });

  const duplicateModuleMutation = useMutation({
    mutationFn: (moduleId: string) => duplicateModule(courseId, moduleId),
    onSuccess: invalidateLifecycle
  });

  const archiveModuleMutation = useMutation({
    mutationFn: (moduleId: string) => archiveModule(courseId, moduleId),
    onSuccess: invalidateLifecycle
  });

  const updateItemMutation = useMutation({
    mutationFn: ({ moduleId, itemId, form }: { moduleId: string; itemId: string; form: ItemForm }) =>
      updateModuleItem(courseId, moduleId, itemId, {
        title: form.title,
        itemType: form.itemType,
        refId: form.refId || undefined,
        description: form.description || undefined,
        videoMediaId: form.videoMediaId || undefined,
        documentMediaIds: form.documentMediaIds,
        contentUrl: form.contentUrl || undefined,
        estimatedMinutes: form.estimatedMinutes ? Number(form.estimatedMinutes) : undefined,
        required: form.required
      }),
    onSuccess: () => {
      setEditingItemId(null);
      invalidateLifecycle();
    }
  });

  const duplicateItemMutation = useMutation({
    mutationFn: ({ moduleId, itemId }: { moduleId: string; itemId: string }) => duplicateModuleItem(courseId, moduleId, itemId),
    onSuccess: invalidateLifecycle
  });

  const archiveItemMutation = useMutation({
    mutationFn: ({ moduleId, itemId }: { moduleId: string; itemId: string }) => archiveModuleItem(courseId, moduleId, itemId),
    onSuccess: invalidateLifecycle
  });

  const reorderCurriculumMutation = useMutation({
    mutationFn: (modules: CurriculumOrder[]) => updateCurriculum(courseId, modules),
    onSuccess: invalidateLifecycle
  });

  const submitReview = useMutation({
    mutationFn: () => submitCourseForReview(courseId),
    onSuccess: invalidateLifecycle
  });

  const approveReview = useMutation({
    mutationFn: () => approveCourseReview(courseId, {
      note: reviewNote.trim() || undefined,
      checklist: reviewChecklistItems.filter((item) => reviewChecklist[item.id]).map((item) => item.id)
    }),
    onSuccess: () => {
      setReviewNote("");
      setReviewChecklist({});
      invalidateLifecycle();
    }
  });

  const rejectReview = useMutation({
    mutationFn: () => rejectCourseReview(courseId, {
      note: reviewNote.trim(),
      checklist: reviewChecklistItems.filter((item) => reviewChecklist[item.id]).map((item) => item.id)
    }),
    onSuccess: () => {
      setReviewNote("");
      setReviewChecklist({});
      invalidateLifecycle();
    }
  });

  const publish = useMutation({
    mutationFn: () => publishCourse(courseId),
    onSuccess: () => {
      invalidateLifecycle();
      qc.invalidateQueries({ queryKey: queryKeys.courses.list() });
    }
  });

  const rollbackVersion = useMutation({
    mutationFn: () => {
      if (!selectedPublishedVersion) {
        throw new Error("No published version available for rollback");
      }
      return rollbackCourseVersion(courseId, selectedPublishedVersion.versionNo, {
        note: rollbackNote.trim(),
        expectedCurrentVersionNo: draft.data?.currentVersionNo
      });
    },
    onSuccess: () => {
      setRollbackNote("");
      invalidateLifecycle();
    }
  });

  function formFor(moduleId: string): ItemForm {
    return itemForms[moduleId] ?? createEmptyItem();
  }

  function filesFor(moduleId: string): UploadFiles {
    return uploadFiles[moduleId] ?? createEmptyFiles();
  }

  function updateItemForm(moduleId: string, patch: Partial<ItemForm>) {
    setItemForms((prev) => ({ ...prev, [moduleId]: { ...formFor(moduleId), ...patch } }));
  }

  function updateFiles(moduleId: string, patch: Partial<UploadFiles>) {
    setUploadFiles((prev) => ({ ...prev, [moduleId]: { ...filesFor(moduleId), ...patch } }));
  }

  function startEditModule(module: CourseModule) {
    setEditingModuleId(module.moduleId);
    setModuleEdits((prev) => ({
      ...prev,
      [module.moduleId]: {
        title: module.title,
        description: module.description ?? ""
      }
    }));
  }

  function updateModuleEdit(moduleId: string, patch: Partial<{ title: string; description: string }>) {
    const current = moduleEdits[moduleId] ?? { title: "", description: "" };
    setModuleEdits((prev) => ({ ...prev, [moduleId]: { ...current, ...patch } }));
  }

  function startEditItem(item: CourseModuleItem) {
    setEditingItemId(item.itemId);
    setItemEdits((prev) => ({ ...prev, [item.itemId]: formFromItem(item) }));
  }

  function updateItemEdit(itemId: string, patch: Partial<ItemForm>) {
    const current = itemEdits[itemId] ?? createEmptyItem();
    setItemEdits((prev) => ({ ...prev, [itemId]: { ...current, ...patch } }));
  }

  function submitModule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    addModule.mutate();
  }

  function submitItem(event: FormEvent<HTMLFormElement>, moduleId: string) {
    event.preventDefault();
    addItem.mutate({ moduleId, form: formFor(moduleId), files: filesFor(moduleId) });
  }

  function submitModuleEdit(event: FormEvent<HTMLFormElement>, moduleId: string) {
    event.preventDefault();
    const form = moduleEdits[moduleId];
    if (form) updateModuleMutation.mutate({ moduleId, form });
  }

  function submitItemEdit(event: FormEvent<HTMLFormElement>, moduleId: string, itemId: string) {
    event.preventDefault();
    const form = itemEdits[itemId];
    if (form) updateItemMutation.mutate({ moduleId, itemId, form });
  }

  function reorderCurriculum(order: CurriculumOrder[] | null) {
    if (order && !reorderCurriculumMutation.isPending) {
      reorderCurriculumMutation.mutate(order);
    }
  }

  if (draft.isLoading) return <Spinner label="Đang tải course builder workspace" />;
  if (draft.isError) return <ErrorState error={draft.error} />;
  if (!draft.data) return <EmptyState message="Không tìm thấy draft course để biên soạn." />;

  const d = draft.data;
  const modules = orderedCourseModules(d.modules ?? []);
  const quizRows = quizzes.data ?? [];
  const assignmentRows = assignments.data ?? [];
  const lessonCount = modules.reduce((sum, module) => sum + (module.items?.length ?? 0), 0);
  const reviewState = d.reviewState ?? "DRAFT";
  const hasQuizItems = modules.some((module) => module.items?.some((item) => item.itemType === "QUIZ"));
  const hasAssignmentItems = modules.some((module) => module.items?.some((item) => item.itemType === "ASSIGNMENT"));
  const readinessChecksPending = (hasQuizItems && quizzes.isLoading) || (hasAssignmentItems && assignments.isLoading);
  const contentIssues = buildContentIssues({
    modules,
    quizzes: quizRows,
    assignments: assignmentRows,
    canValidateQuizzes: quizzes.isSuccess,
    canValidateAssignments: assignments.isSuccess,
    quizCheckFailed: quizzes.isError,
    assignmentCheckFailed: assignments.isError
  });
  const contentBlockers = contentIssues.filter((issue) => issue.severity === "blocker");
  const contentReady = !readinessChecksPending && modules.length > 0 && lessonCount > 0 && contentBlockers.length === 0;
  const courseCanAuthor = d.status !== "ARCHIVED";
  const reorderDisabled = !courseCanAuthor || reorderCurriculumMutation.isPending;
  const canSubmitReview = courseCanAuthor && reviewState === "DRAFT" && contentReady;
  const canApprove = reviewState === "IN_REVIEW";
  const learnerPreviewGateReady = draftPreview.isSuccess && !draftPreview.isFetching && Boolean(draftPreview.data);
  const reviewChecklistComplete = reviewChecklistItems
    .filter((item) => item.required)
    .every((item) => Boolean(reviewChecklist[item.id]) && (item.id !== "learner-preview-checked" || learnerPreviewGateReady));
  const reviewNoteReady = reviewNote.trim().length > 0;
  const canApproveDecision = canApprove && reviewChecklistComplete;
  const canRejectDecision = canApprove && reviewNoteReady;
  const canPublish = courseCanAuthor && reviewState === "APPROVED" && contentReady;
  const submitReviewTitle = canSubmitReview
    ? "Sẵn sàng gửi duyệt"
    : "Cần course chưa archived, review DRAFT và không còn blocker nội dung";
  const approveTitle = !canApprove
    ? "Chỉ duyệt khi course đang IN_REVIEW"
    : !learnerPreviewGateReady
      ? "Tải draft learner preview trước khi duyệt"
    : reviewChecklistComplete
      ? "Sẵn sàng duyệt"
      : "Hoàn tất reviewer checklist trước khi duyệt";
  const rejectTitle = !canApprove
    ? "Chỉ từ chối khi course đang IN_REVIEW"
    : reviewNoteReady
      ? "Trả course về trạng thái cần sửa"
      : "Nhập reviewer note trước khi từ chối";
  const publishTitle = canPublish ? "Sẵn sàng publish" : "Cần course chưa archived, review APPROVED và không còn blocker nội dung";
  const workspaceSummary = buildWorkspaceSummary({
    modules,
    quizzes: quizRows,
    assignments: assignmentRows,
    contentIssues,
    reviewState,
    courseStatus: d.status,
    readinessChecksPending,
    quizLoading: quizzes.isLoading,
    quizError: quizzes.isError,
    assignmentLoading: assignments.isLoading,
    assignmentError: assignments.isError
  });
  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-brand-700">
        <ArrowLeft size={16} /> Quay lại danh sách
      </Link>

      <PageHeader
        title={d.title}
        description={`${d.slug} · ID ${shortId(d.courseId)}`}
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Badge value={reviewState} label={reviewStateLabel(reviewState)} />
            <Button
              variant="secondary"
              disabled={!canSubmitReview || submitReview.isPending}
              title={submitReviewTitle}
              onClick={() => submitReview.mutate()}
            >
              <Send size={16} />
              {submitReview.isPending ? "Đang gửi..." : "Gửi duyệt"}
            </Button>
            <Button
              disabled={!canPublish || publish.isPending}
              title={publishTitle}
              onClick={() => publish.mutate()}
            >
              <Rocket size={16} />
              {publish.isPending ? "Đang publish..." : "Publish"}
            </Button>
          </div>
        }
      />

      {(submitReview.isError || approveReview.isError || rejectReview.isError || publish.isError
        || updateModuleMutation.isError || duplicateModuleMutation.isError || archiveModuleMutation.isError
        || updateItemMutation.isError || duplicateItemMutation.isError || archiveItemMutation.isError
        || reorderCurriculumMutation.isError) && (
        <div className="mb-4">
          {submitReview.isError && <ErrorState error={submitReview.error} />}
          {approveReview.isError && <ErrorState error={approveReview.error} />}
          {rejectReview.isError && <ErrorState error={rejectReview.error} />}
          {publish.isError && <ErrorState error={publish.error} />}
          {updateModuleMutation.isError && <ErrorState error={updateModuleMutation.error} />}
          {duplicateModuleMutation.isError && <ErrorState error={duplicateModuleMutation.error} />}
          {archiveModuleMutation.isError && <ErrorState error={archiveModuleMutation.error} />}
          {updateItemMutation.isError && <ErrorState error={updateItemMutation.error} />}
          {duplicateItemMutation.isError && <ErrorState error={duplicateItemMutation.error} />}
          {archiveItemMutation.isError && <ErrorState error={archiveItemMutation.error} />}
          {reorderCurriculumMutation.isError && <ErrorState error={reorderCurriculumMutation.error} />}
        </div>
      )}

      <Card className="mb-4">
        <CardHeader
          title="Course builder workspace"
          subtitle="Tổng hợp readiness, dependency và preview learner từ draft hiện tại."
          actions={<Badge value={d.status} label={d.status} />}
        />
        <div className="grid gap-4 p-5 xl:grid-cols-[320px_minmax(0,1fr)]">
          <PublishConfidencePanel
            summary={workspaceSummary}
            preview={draftPreview.data}
            previewLoading={draftPreview.isLoading}
            previewError={draftPreview.isError}
          />
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-950">
                <PackageCheck size={18} className="text-brand-700" />
                Dependency summary
              </div>
              <span className="text-xs font-semibold text-slate-500">
                {workspaceSummary.blockers} blocker · {workspaceSummary.warnings} cảnh báo
              </span>
            </div>
            <DependencySummaryPanel dependencies={workspaceSummary.dependencies} courseId={courseId} />
          </div>
        </div>
      </Card>

      <ReviewOperationsPanel
        reviewState={reviewState}
        reviewNote={reviewNote}
        reviewChecklist={reviewChecklist}
        checklistItems={reviewChecklistItems}
        history={reviewHistory.data}
        historyLoading={reviewHistory.isLoading}
        historyError={reviewHistory.isError}
        historyErrorValue={reviewHistory.error}
        canApprove={canApprove}
        canApproveDecision={canApproveDecision}
        canRejectDecision={canRejectDecision}
        learnerPreviewGateReady={learnerPreviewGateReady}
        approvePending={approveReview.isPending}
        rejectPending={rejectReview.isPending}
        approveTitle={approveTitle}
        rejectTitle={rejectTitle}
        onReviewNoteChange={setReviewNote}
        onChecklistChange={(id, checked) => setReviewChecklist((current) => ({ ...current, [id]: checked }))}
        onApprove={() => approveReview.mutate()}
        onReject={() => rejectReview.mutate()}
      />

      <VersionControlPanel
        versions={versions.data}
        selectedPublished={selectedPublishedVersion}
        diff={versionDiff.data}
        diffLoading={versionDiff.isLoading}
        diffError={versionDiff.isError}
        diffErrorValue={versionDiff.error}
        rollbackNote={rollbackNote}
        rollbackPending={rollbackVersion.isPending}
        rollbackError={rollbackVersion.isError}
        rollbackErrorValue={rollbackVersion.error}
        currentVersionNo={d.currentVersionNo}
        onSelectedVersionChange={setSelectedRollbackVersionNo}
        onRollbackNoteChange={setRollbackNote}
        onRollback={() => {
          if (selectedPublishedVersion && window.confirm(`Rollback published v${selectedPublishedVersion.versionNo} thành draft mới?`)) {
            rollbackVersion.mutate();
          }
        }}
      />

      <Card className="mb-4">
        <CardHeader
          title="Readiness gate"
          subtitle="Blocker theo từng item type trước khi gửi duyệt hoặc mở khóa học cho learner."
          actions={
            <Badge
              value={contentReady ? "READY" : "DRAFT"}
              label={contentReady ? "Nội dung sẵn sàng" : `${contentBlockers.length} blocker`}
            />
          }
        />
        <div className="grid gap-4 p-5 xl:grid-cols-[360px_minmax(0,1fr)]">
          <div className="space-y-3">
            <ReadinessGate
              label="Submit review"
              ready={canSubmitReview}
              pending={readinessChecksPending}
              readyText="Course có thể được đưa vào hàng chờ review."
              blockedText={
                d.status === "ARCHIVED"
                  ? "Course đã archive nên không thể gửi duyệt."
                  : reviewState !== "DRAFT"
                    ? `Review hiện tại: ${reviewStateLabel(reviewState)}.`
                    : "Sửa các blocker nội dung trước khi gửi duyệt."
              }
              issues={contentIssues}
            />
            <ReadinessGate
              label="Publish"
              ready={canPublish}
              pending={readinessChecksPending}
              readyText="Snapshot đã duyệt có thể publish cho learner."
              blockedText={
                d.status === "ARCHIVED"
                  ? "Course đã archive nên không thể publish."
                  : reviewState !== "APPROVED"
                  ? "Reviewer cần duyệt course trước khi publish."
                  : "Sửa các blocker nội dung trước khi publish."
              }
              issues={contentIssues}
            />
          </div>
          <ContentIssueList issues={contentIssues} pending={readinessChecksPending} />
        </div>
      </Card>

      <WorkspaceStats summary={workspaceSummary} moduleCount={modules.length} versionNo={d.currentVersionNo} />
      {reorderCurriculumMutation.isPending && (
        <Notice className="mb-4" title="Đang lưu thứ tự curriculum">
          Module và bài học sẽ cập nhật sau khi server xác nhận.
        </Notice>
      )}

      <div className="grid gap-5 2xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <CourseOutline modules={modules} issues={contentIssues} />

        <div className="space-y-5">
          {modules.length === 0 && (
            <Card>
              <EmptyState message="Tạo chương đầu tiên để bắt đầu thiết kế khóa học." />
            </Card>
          )}

          {modules.map((module, moduleIndex) => {
            const itemForm = formFor(module.moduleId);
            const files = filesFor(module.moduleId);
            const moduleEdit = moduleEdits[module.moduleId] ?? {
              title: module.title,
              description: module.description ?? ""
            };
            const items = orderedModuleItems(module);
            const canAttachVideo = itemForm.itemType === "LESSON" || itemForm.itemType === "VIDEO";
            const canAttachDocuments = itemForm.itemType === "LESSON" || itemForm.itemType === "DOCUMENT";
            const canAttachUrl = ["LESSON", "DOCUMENT", "LINK"].includes(itemForm.itemType);

            return (
              <Card key={module.moduleId} id={`module-${module.moduleId}`}>
                <CardHeader
                  title={
                    <span className="inline-flex items-center gap-2">
                      <Layers3 size={18} className="text-brand-700" />
                      {module.title}
                    </span>
                  }
                  subtitle={module.description}
                  actions={
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <Badge value={module.status} />
                      <Button
                        variant="secondary"
                        size="xs"
                        className="w-8 px-0"
                        type="button"
                        title="Đưa chương lên"
                        aria-label="Đưa chương lên"
                        disabled={moduleIndex === 0 || reorderDisabled}
                        onClick={() => reorderCurriculum(moveModuleOrder(modules, module.moduleId, "up"))}
                      >
                        <ArrowUp size={15} />
                      </Button>
                      <Button
                        variant="secondary"
                        size="xs"
                        className="w-8 px-0"
                        type="button"
                        title="Đưa chương xuống"
                        aria-label="Đưa chương xuống"
                        disabled={moduleIndex === modules.length - 1 || reorderDisabled}
                        onClick={() => reorderCurriculum(moveModuleOrder(modules, module.moduleId, "down"))}
                      >
                        <ArrowDown size={15} />
                      </Button>
                      <Button variant="secondary" type="button" title="Sửa chương" onClick={() => startEditModule(module)}>
                        <Pencil size={16} />
                      </Button>
                      <Button
                        variant="secondary"
                        type="button"
                        title="Nhân bản chương"
                        disabled={duplicateModuleMutation.isPending}
                        onClick={() => duplicateModuleMutation.mutate(module.moduleId)}
                      >
                        <Copy size={16} />
                      </Button>
                      <Button
                        variant="danger"
                        type="button"
                        title="Archive chương"
                        disabled={archiveModuleMutation.isPending}
                        onClick={() => {
                          if (window.confirm(`Archive chương "${module.title}" và toàn bộ bài học bên trong?`)) {
                            archiveModuleMutation.mutate(module.moduleId);
                          }
                        }}
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  }
                />

                {editingModuleId === module.moduleId && (
                  <form className="border-t border-black/10 bg-brand-50/40 p-5" onSubmit={(event) => submitModuleEdit(event, module.moduleId)}>
                    <div className="grid gap-4 md:grid-cols-2">
                      <FormField label="Tên chương" htmlFor={`module-edit-title-${module.moduleId}`}>
                        <Input
                          id={`module-edit-title-${module.moduleId}`}
                          value={moduleEdit.title}
                          onChange={(event) => updateModuleEdit(module.moduleId, { title: event.target.value })}
                          required
                        />
                      </FormField>
                      <FormField label="Mô tả chương" htmlFor={`module-edit-description-${module.moduleId}`}>
                        <Textarea
                          id={`module-edit-description-${module.moduleId}`}
                          value={moduleEdit.description}
                          onChange={(event) => updateModuleEdit(module.moduleId, { description: event.target.value })}
                          rows={3}
                        />
                      </FormField>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button type="submit" disabled={updateModuleMutation.isPending}>
                        <CheckCircle2 size={16} />
                        {updateModuleMutation.isPending ? "Đang lưu..." : "Lưu chương"}
                      </Button>
                      <Button type="button" variant="secondary" onClick={() => setEditingModuleId(null)}>
                        <XCircle size={16} />
                        Hủy
                      </Button>
                    </div>
                  </form>
                )}

                <div className="space-y-3 p-5">
                  {items.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm text-slate-500">
                      Chương này chưa có bài học.
                    </div>
                  ) : (
                    items.map((item, itemIndex) => {
                      const editForm = itemEdits[item.itemId] ?? formFromItem(item);
                      const editCanAttachUrl = ["LESSON", "DOCUMENT", "LINK"].includes(editForm.itemType);
                      return (
                        <div key={item.itemId} className="space-y-3">
                          <LessonCard
                            item={item}
                            displayIndex={itemIndex + 1}
                            issues={issuesForItem(contentIssues, item.itemId)}
                            actions={
                              <>
                                <Button
                                  variant="secondary"
                                  size="xs"
                                  className="w-8 px-0"
                                  type="button"
                                  title="Đưa bài học lên"
                                  aria-label="Đưa bài học lên"
                                  disabled={itemIndex === 0 || reorderDisabled}
                                  onClick={() => reorderCurriculum(moveItemOrder(modules, module.moduleId, item.itemId, "up"))}
                                >
                                  <ArrowUp size={15} />
                                </Button>
                                <Button
                                  variant="secondary"
                                  size="xs"
                                  className="w-8 px-0"
                                  type="button"
                                  title="Đưa bài học xuống"
                                  aria-label="Đưa bài học xuống"
                                  disabled={itemIndex === items.length - 1 || reorderDisabled}
                                  onClick={() => reorderCurriculum(moveItemOrder(modules, module.moduleId, item.itemId, "down"))}
                                >
                                  <ArrowDown size={15} />
                                </Button>
                                <Button variant="secondary" type="button" title="Sửa bài học" onClick={() => startEditItem(item)}>
                                  <Pencil size={16} />
                                </Button>
                                <Button
                                  variant="secondary"
                                  type="button"
                                  title="Nhân bản bài học"
                                  disabled={duplicateItemMutation.isPending}
                                  onClick={() => duplicateItemMutation.mutate({ moduleId: module.moduleId, itemId: item.itemId })}
                                >
                                  <Copy size={16} />
                                </Button>
                                <Button
                                  variant="danger"
                                  type="button"
                                  title="Archive bài học"
                                  disabled={archiveItemMutation.isPending}
                                  onClick={() => {
                                    if (window.confirm(`Archive bài học "${item.title}"?`)) {
                                      archiveItemMutation.mutate({ moduleId: module.moduleId, itemId: item.itemId });
                                    }
                                  }}
                                >
                                  <Trash2 size={16} />
                                </Button>
                              </>
                            }
                          />
                          {editingItemId === item.itemId && (
                            <form className="rounded-lg border border-brand-200 bg-brand-50/40 p-4" onSubmit={(event) => submitItemEdit(event, module.moduleId, item.itemId)}>
                              <div className="grid gap-4 xl:grid-cols-2">
                                <FormField label="Tên bài học" htmlFor={`item-edit-title-${item.itemId}`}>
                                  <Input
                                    id={`item-edit-title-${item.itemId}`}
                                    value={editForm.title}
                                    onChange={(event) => updateItemEdit(item.itemId, { title: event.target.value })}
                                    required
                                  />
                                </FormField>
                                <FormField label="Loại nội dung" htmlFor={`item-edit-type-${item.itemId}`}>
                                  <Select
                                    id={`item-edit-type-${item.itemId}`}
                                    value={editForm.itemType}
                                    onChange={(event) => updateItemEdit(item.itemId, itemTypeResetPatch(event.target.value))}
                                  >
                                    <option value="LESSON">Bài học</option>
                                    <option value="VIDEO">Video</option>
                                    <option value="DOCUMENT">Tài liệu</option>
                                    <option value="LINK">Liên kết</option>
                                    <option value="QUIZ">Bài thi</option>
                                    <option value="ASSIGNMENT">Bài tập</option>
                                  </Select>
                                </FormField>
                                <FormField label="Mô tả bài học" htmlFor={`item-edit-description-${item.itemId}`}>
                                  <Textarea
                                    id={`item-edit-description-${item.itemId}`}
                                    value={editForm.description}
                                    onChange={(event) => updateItemEdit(item.itemId, { description: event.target.value })}
                                    rows={4}
                                  />
                                </FormField>
                                <div className="grid gap-4">
                                  <FormField label="Thời lượng ước tính" htmlFor={`item-edit-minutes-${item.itemId}`}>
                                    <Input
                                      id={`item-edit-minutes-${item.itemId}`}
                                      type="number"
                                      min={0}
                                      value={editForm.estimatedMinutes}
                                      onChange={(event) => updateItemEdit(item.itemId, { estimatedMinutes: event.target.value })}
                                    />
                                  </FormField>
                                  {editCanAttachUrl && (
                                    <FormField label="Liên kết nội dung" htmlFor={`item-edit-url-${item.itemId}`}>
                                      <Input
                                        id={`item-edit-url-${item.itemId}`}
                                        value={editForm.contentUrl}
                                        onChange={(event) => updateItemEdit(item.itemId, { contentUrl: event.target.value })}
                                        placeholder="https://..."
                                      />
                                    </FormField>
                                  )}
                                  {editForm.itemType === "QUIZ" && (
                                    <FormField label="Bài thi" htmlFor={`item-edit-ref-${item.itemId}`}>
                                      <Select
                                        id={`item-edit-ref-${item.itemId}`}
                                        value={editForm.refId}
                                        onChange={(event) => updateItemEdit(item.itemId, { refId: event.target.value })}
                                        required
                                      >
                                        <option value="">Chọn bài thi</option>
                                        {quizRows.map((quiz) => (
                                          <option key={quiz.id} value={quiz.id}>{quiz.title} · {quiz.status ?? "DRAFT"}</option>
                                        ))}
                                        {editForm.refId && !quizRows.some((quiz) => quiz.id === editForm.refId) && (
                                          <option value={editForm.refId}>Bài thi {shortId(editForm.refId)}</option>
                                        )}
                                      </Select>
                                    </FormField>
                                  )}
                                  {editForm.itemType === "ASSIGNMENT" && (
                                    <FormField label="Bài tập" htmlFor={`item-edit-ref-${item.itemId}`}>
                                      <Select
                                        id={`item-edit-ref-${item.itemId}`}
                                        value={editForm.refId}
                                        onChange={(event) => updateItemEdit(item.itemId, { refId: event.target.value })}
                                        required
                                      >
                                        <option value="">Chọn bài tập</option>
                                        {assignmentRows.map((assignment) => (
                                          <option key={assignment.id} value={assignment.id}>{assignment.title} · {assignment.status ?? "DRAFT"}</option>
                                        ))}
                                        {editForm.refId && !assignmentRows.some((assignment) => assignment.id === editForm.refId) && (
                                          <option value={editForm.refId}>Bài tập {shortId(editForm.refId)}</option>
                                        )}
                                      </Select>
                                    </FormField>
                                  )}
                                </div>
                              </div>
                              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                                <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
                                  <input
                                    type="checkbox"
                                    checked={editForm.required}
                                    onChange={(event) => updateItemEdit(item.itemId, { required: event.target.checked })}
                                  />
                                  Bắt buộc hoàn thành
                                </label>
                                <div className="flex flex-wrap gap-2">
                                  <Button
                                    type="submit"
                                    disabled={updateItemMutation.isPending || ((editForm.itemType === "QUIZ" || editForm.itemType === "ASSIGNMENT") && !editForm.refId)}
                                  >
                                    <CheckCircle2 size={16} />
                                    {updateItemMutation.isPending ? "Đang lưu..." : "Lưu bài học"}
                                  </Button>
                                  <Button type="button" variant="secondary" onClick={() => setEditingItemId(null)}>
                                    <XCircle size={16} />
                                    Hủy
                                  </Button>
                                </div>
                              </div>
                            </form>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>

                <form className="border-t border-black/10 bg-slate-50/70 p-5" onSubmit={(e) => submitItem(e, module.moduleId)}>
                  <div className="mb-4 flex items-center gap-2">
                    <Plus size={18} className="text-brand-700" />
                    <h3 className="font-bold text-slate-950">Thêm bài học</h3>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <FormField label="Tên bài học" htmlFor={`item-title-${module.moduleId}`}>
                      <Input
                        id={`item-title-${module.moduleId}`}
                        value={itemForm.title}
                        onChange={(e) => updateItemForm(module.moduleId, { title: e.target.value })}
                        placeholder="Ví dụ: Thiết kế bounded context"
                        required
                      />
                    </FormField>

                    <FormField label="Loại nội dung" htmlFor={`item-type-${module.moduleId}`}>
                      <Select
                        id={`item-type-${module.moduleId}`}
                        value={itemForm.itemType}
                        onChange={(e) => updateItemForm(module.moduleId, itemTypeResetPatch(e.target.value))}
                      >
                        <option value="LESSON">Bài học</option>
                        <option value="VIDEO">Video</option>
                        <option value="DOCUMENT">Tài liệu</option>
                        <option value="LINK">Liên kết</option>
                        <option value="QUIZ">Bài thi</option>
                        <option value="ASSIGNMENT">Bài tập</option>
                      </Select>
                    </FormField>

                    <FormField label="Mô tả bài học" htmlFor={`item-description-${module.moduleId}`}>
                      <Textarea
                        id={`item-description-${module.moduleId}`}
                        value={itemForm.description}
                        onChange={(e) => updateItemForm(module.moduleId, { description: e.target.value })}
                        rows={4}
                        placeholder="Mục tiêu, nội dung chính, yêu cầu trước khi học..."
                      />
                    </FormField>

                    <div className="grid gap-4">
                      <FormField label="Thời lượng ước tính" htmlFor={`item-minutes-${module.moduleId}`}>
                        <Input
                          id={`item-minutes-${module.moduleId}`}
                          type="number"
                          min={0}
                          value={itemForm.estimatedMinutes}
                          onChange={(e) => updateItemForm(module.moduleId, { estimatedMinutes: e.target.value })}
                        />
                      </FormField>

                      {canAttachUrl && (
                        <FormField label="Liên kết nội dung" htmlFor={`item-url-${module.moduleId}`} hint="Dùng cho bài dạng link hoặc tài nguyên bên ngoài.">
                          <Input
                            id={`item-url-${module.moduleId}`}
                            value={itemForm.contentUrl}
                            onChange={(e) => updateItemForm(module.moduleId, { contentUrl: e.target.value })}
                            placeholder="https://..."
                          />
                        </FormField>
                      )}

                      {itemForm.itemType === "QUIZ" && (
                        <FormField label="Bài thi" htmlFor={`item-ref-${module.moduleId}`} hint="Chọn quiz đã thuộc khóa học này.">
                          <Select
                            id={`item-ref-${module.moduleId}`}
                            value={itemForm.refId}
                            onChange={(e) => updateItemForm(module.moduleId, { refId: e.target.value })}
                            required
                          >
                            <option value="">Chọn bài thi</option>
                            {quizRows.map((quiz) => (
                              <option key={quiz.id} value={quiz.id}>
                                {quiz.title} · {quiz.status ?? "DRAFT"}
                              </option>
                            ))}
                            {itemForm.refId && !quizRows.some((quiz) => quiz.id === itemForm.refId) && (
                              <option value={itemForm.refId}>Bài thi {shortId(itemForm.refId)}</option>
                            )}
                          </Select>
                          {quizzes.isLoading && <span className="text-xs text-slate-400">Đang tải quiz...</span>}
                          {quizzes.isError && <ErrorState error={quizzes.error} />}
                        </FormField>
                      )}

                      {itemForm.itemType === "ASSIGNMENT" && (
                        <FormField label="Bài tập" htmlFor={`item-ref-${module.moduleId}`} hint="Chọn assignment đã thuộc khóa học này.">
                          <Select
                            id={`item-ref-${module.moduleId}`}
                            value={itemForm.refId}
                            onChange={(e) => updateItemForm(module.moduleId, { refId: e.target.value })}
                            required
                          >
                            <option value="">Chọn bài tập</option>
                            {assignmentRows.map((assignment) => (
                              <option key={assignment.id} value={assignment.id}>
                                {assignment.title} · {assignment.status ?? "DRAFT"}
                              </option>
                            ))}
                            {itemForm.refId && !assignmentRows.some((assignment) => assignment.id === itemForm.refId) && (
                              <option value={itemForm.refId}>Bài tập {shortId(itemForm.refId)}</option>
                            )}
                          </Select>
                          {assignments.isLoading && <span className="text-xs text-slate-400">Đang tải assignment...</span>}
                          {assignments.isError && <ErrorState error={assignments.error} />}
                        </FormField>
                      )}
                    </div>

                    {canAttachVideo && (
                      <UploadTile
                        id={`item-video-${module.moduleId}`}
                        title="Tải video"
                        description="Tải video bài học lên kho media, sau đó gắn video vào lesson."
                        icon={<UploadCloud size={20} />}
                        accept="video/*"
                        selectedText={files.videoFile?.name}
                        onChange={(selected) => updateFiles(module.moduleId, { videoFile: selected?.[0] })}
                      />
                    )}

                    {canAttachDocuments && (
                      <UploadTile
                        id={`item-docs-${module.moduleId}`}
                        title="Tải tài liệu"
                        description="PDF, slide, workbook hoặc tài liệu bổ trợ cho bài học."
                        icon={<FileText size={20} />}
                        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,text/*,application/pdf"
                        multiple
                        selectedText={files.documentFiles.length > 0 ? `${files.documentFiles.length} file đã chọn` : undefined}
                        onChange={(selected) => updateFiles(module.moduleId, { documentFiles: Array.from(selected ?? []) })}
                      />
                    )}
                  </div>

                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
                      <input
                        type="checkbox"
                        checked={itemForm.required}
                        onChange={(e) => updateItemForm(module.moduleId, { required: e.target.checked })}
                      />
                      Bắt buộc hoàn thành
                    </label>
                    <Button
                      type="submit"
                      disabled={addItem.isPending || ((itemForm.itemType === "QUIZ" || itemForm.itemType === "ASSIGNMENT") && !itemForm.refId)}
                    >
                      <CheckCircle2 size={16} />
                      {addItem.isPending ? "Đang lưu/upload..." : "Lưu bài học"}
                    </Button>
                  </div>
                </form>
              </Card>
            );
          })}

          {addItem.isError && <ErrorState error={addItem.error} />}
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Thêm chương" subtitle="Mỗi chương chứa nhiều bài học hoặc tài nguyên." />
            <form className="space-y-4 p-5" onSubmit={submitModule}>
              <FormField label="Tên chương" htmlFor="dr-module-title">
                <Input
                  id="dr-module-title"
                  value={moduleForm.title}
                  onChange={(e) => setModuleForm({ ...moduleForm, title: e.target.value })}
                  placeholder="Ví dụ: Chương 1 - Nền tảng kiến trúc"
                  required
                />
              </FormField>
              <FormField label="Mô tả chương" htmlFor="dr-module-desc">
                <Textarea
                  id="dr-module-desc"
                  value={moduleForm.description}
                  onChange={(e) => setModuleForm({ ...moduleForm, description: e.target.value })}
                  rows={4}
                />
              </FormField>
              {addModule.isError && <ErrorState error={addModule.error} />}
              <Button type="submit" disabled={addModule.isPending}>
                <Plus size={16} />
                {addModule.isPending ? "Đang lưu..." : "Thêm chương"}
              </Button>
            </form>
          </Card>

          <Card>
            <CardHeader title="Thông tin draft" />
            <dl className="grid grid-cols-[120px_1fr] gap-y-3 p-5 text-sm">
              <dt className="text-slate-500">Trạng thái</dt>
              <dd><Badge value={d.status} /></dd>
              <dt className="text-slate-500">Review</dt>
              <dd><Badge value={d.reviewState ?? "DRAFT"} /></dd>
              <dt className="text-slate-500">Phiên bản</dt>
              <dd>{d.currentVersionNo}</dd>
              <dt className="text-slate-500">Tóm tắt</dt>
              <dd className="leading-6">{d.summary ?? "-"}</dd>
            </dl>
          </Card>
        </div>
      </div>

      <Card className="mt-5">
        <CardHeader title="Phiên bản" />
        {versions.isLoading && <Spinner />}
        {versions.isError && <ErrorState error={versions.error} />}
        {versions.data && versions.data.length === 0 && (
          <EmptyState message="Chưa có phiên bản nào" />
        )}
        {versions.data && versions.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Phiên bản</Th>
                <Th>Trạng thái</Th>
                <Th>Người tạo</Th>
                <Th>Ngày xuất bản</Th>
              </tr>
            </thead>
            <tbody>
              {versions.data.map((v) => (
                <tr key={v.id}>
                  <Td>v{v.versionNo}</Td>
                  <Td><Badge value={v.state} /></Td>
                  <Td>{v.createdBy ?? "-"}</Td>
                  <Td>{v.publishedAt ? new Date(v.publishedAt).toLocaleDateString("vi-VN") : "-"}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}
