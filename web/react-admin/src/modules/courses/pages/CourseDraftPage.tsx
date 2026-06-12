import { FormEvent, type ReactNode, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Clock3,
  FileUp,
  FileText,
  Layers3,
  Link2,
  Plus,
  Rocket,
  Send,
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
  Th
} from "@/shared/ui";
import {
  getAssetUploadUrl,
  getVideoUploadUrl,
  registerAsset,
  registerVideo
} from "@/modules/media/api";
import {
  approveCourseReview,
  createModule,
  createModuleItem,
  getCourseDraft,
  listCourseVersions,
  publishCourse,
  rejectCourseReview,
  submitCourseForReview,
  type CourseModule,
  type CourseModuleItem
} from "../api";

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

function LessonCard({ item, displayIndex }: { item: CourseModuleItem; displayIndex: number }) {
  const docs = item.documentMediaIds ?? [];
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="grid size-8 place-items-center rounded-md bg-brand-50 text-brand-700">
              {itemIcon(item.itemType)}
            </span>
            <h3 className="font-bold text-slate-950">{item.title}</h3>
            <Badge value={item.itemType === "MATERIAL" ? "DOCUMENT" : item.itemType} label={contentTypeLabel(item.itemType)} />
            {item.required && <Badge value="REQUIRED" />}
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
          </div>
        </div>
        <span className="text-xs font-bold text-slate-400">#{displayIndex}</span>
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

function ReadinessColumn({
  title,
  subtitle,
  items
}: {
  title: string;
  subtitle: string;
  items: Array<{ done: boolean; label: string; detail: string }>;
}) {
  return (
    <div className="rounded-lg border border-black/10 bg-slate-50/70 p-4">
      <div className="mb-4">
        <p className="font-bold text-slate-950">{title}</p>
        <p className="mt-1 text-sm leading-5 text-slate-500">{subtitle}</p>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label} className="flex items-start gap-3">
            <span
              className={
                item.done
                  ? "grid size-8 shrink-0 place-items-center rounded-md bg-emerald-50 text-emerald-700"
                  : "grid size-8 shrink-0 place-items-center rounded-md bg-amber-50 text-amber-700"
              }
            >
              {item.done ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
            </span>
            <span>
              <span className="block text-sm font-semibold text-slate-900">{item.label}</span>
              <span className="mt-0.5 block text-xs leading-5 text-slate-500">{item.detail}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CourseMap({ modules }: { modules: CourseModule[] }) {
  return (
    <Card className="sticky top-6">
      <CardHeader title="Course map" subtitle="Chương và số bài học" />
      <div className="space-y-2 p-4">
        {modules.length === 0 && <EmptyState message="Chưa có chương" />}
        {modules.map((module) => (
          <a
            key={module.moduleId}
            href={`#module-${module.moduleId}`}
            className="flex items-center justify-between rounded-md border border-black/10 px-3 py-2 text-sm transition hover:bg-brand-50"
          >
            <span className="line-clamp-1 font-semibold text-slate-800">{module.title}</span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-500">
              {module.items?.length ?? 0}
            </span>
          </a>
        ))}
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

  const versions = useQuery({
    queryKey: queryKeys.authoring.versions(courseId),
    queryFn: () => listCourseVersions(courseId),
    enabled: Boolean(courseId)
  });

  const [moduleForm, setModuleForm] = useState({ title: "", description: "" });
  const [itemForms, setItemForms] = useState<Record<string, ItemForm>>({});
  const [uploadFiles, setUploadFiles] = useState<Record<string, UploadFiles>>({});

  function invalidateDraft() {
    qc.invalidateQueries({ queryKey: queryKeys.authoring.draft(courseId) });
  }

  const addModule = useMutation({
    mutationFn: () => createModule(courseId, {
      title: moduleForm.title,
      description: moduleForm.description || undefined,
      status: "DRAFT"
    }),
    onSuccess: () => {
      setModuleForm({ title: "", description: "" });
      invalidateDraft();
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
      invalidateDraft();
    }
  });

  const submitReview = useMutation({
    mutationFn: () => submitCourseForReview(courseId),
    onSuccess: invalidateDraft
  });

  const approveReview = useMutation({
    mutationFn: () => approveCourseReview(courseId),
    onSuccess: invalidateDraft
  });

  const rejectReview = useMutation({
    mutationFn: () => rejectCourseReview(courseId),
    onSuccess: invalidateDraft
  });

  const publish = useMutation({
    mutationFn: () => publishCourse(courseId),
    onSuccess: () => {
      invalidateDraft();
      qc.invalidateQueries({ queryKey: queryKeys.courses.list() });
      qc.invalidateQueries({ queryKey: queryKeys.authoring.versions(courseId) });
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

  function submitModule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    addModule.mutate();
  }

  function submitItem(event: FormEvent<HTMLFormElement>, moduleId: string) {
    event.preventDefault();
    addItem.mutate({ moduleId, form: formFor(moduleId), files: filesFor(moduleId) });
  }

  if (draft.isLoading) return <Spinner />;
  if (draft.isError) return <ErrorState error={draft.error} />;
  if (!draft.data) return null;

  const d = draft.data;
  const modules = [...(d.modules ?? [])].sort((a, b) => a.position - b.position);
  const lessonCount = modules.reduce((sum, module) => sum + (module.items?.length ?? 0), 0);
  const reviewState = d.reviewState ?? "DRAFT";
  const canSubmitReview = d.status === "DRAFT" && reviewState === "DRAFT" && lessonCount > 0;
  const canApprove = reviewState === "IN_REVIEW";
  const canPublish = d.status === "DRAFT" && reviewState === "APPROVED";
  const reviewRequirements = [
    {
      done: d.status === "DRAFT",
      label: "Course còn ở trạng thái draft",
      detail: d.status === "DRAFT" ? "Có thể tiếp tục chỉnh sửa và gửi duyệt." : "Course đã rời trạng thái draft."
    },
    {
      done: modules.length > 0,
      label: "Có ít nhất 1 chương",
      detail: modules.length > 0 ? `${modules.length} chương đã được tạo.` : "Chưa có chương trong curriculum."
    },
    {
      done: lessonCount > 0,
      label: "Có ít nhất 1 bài học",
      detail: lessonCount > 0 ? `${lessonCount} bài học đã có trong curriculum.` : "Thêm video, tài liệu, link hoặc bài học vào chương."
    },
    {
      done: reviewState === "DRAFT",
      label: "Chưa nằm trong hàng chờ duyệt",
      detail: `Review hiện tại: ${reviewStateLabel(reviewState)}.`
    }
  ];
  const publishRequirements = [
    {
      done: reviewState === "APPROVED",
      label: "Đã được reviewer duyệt",
      detail: reviewState === "APPROVED" ? "Course đủ điều kiện publish." : "Cần reviewer chuyển review sang Đã duyệt."
    },
    {
      done: d.status === "DRAFT",
      label: "Chưa publish",
      detail: d.status === "DRAFT" ? "Publish sẽ đóng băng snapshot hiện tại." : "Course không còn ở trạng thái draft."
    },
    {
      done: lessonCount > 0,
      label: "Snapshot có nội dung học",
      detail: lessonCount > 0 ? "Version publish sẽ có bài học cho learner." : "Thêm bài học trước khi gửi duyệt."
    }
  ];
  const submitReviewTitle = canSubmitReview
    ? "Sẵn sàng gửi duyệt"
    : "Cần course draft, review DRAFT và ít nhất một bài học";
  const approveTitle = canApprove ? "Sẵn sàng duyệt" : "Chỉ duyệt khi course đang IN_REVIEW";
  const publishTitle = canPublish ? "Sẵn sàng publish" : "Cần review APPROVED trước khi publish";

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
              variant="secondary"
              disabled={!canApprove || approveReview.isPending}
              title={approveTitle}
              onClick={() => approveReview.mutate()}
            >
              <CheckCircle2 size={16} />
              {approveReview.isPending ? "Đang duyệt..." : "Duyệt"}
            </Button>
            <Button
              variant="secondary"
              disabled={!canApprove || rejectReview.isPending}
              title={approveTitle}
              onClick={() => rejectReview.mutate()}
            >
              <XCircle size={16} />
              {rejectReview.isPending ? "Đang trả..." : "Từ chối"}
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

      {(submitReview.isError || approveReview.isError || rejectReview.isError || publish.isError) && (
        <div className="mb-4">
          {submitReview.isError && <ErrorState error={submitReview.error} />}
          {approveReview.isError && <ErrorState error={approveReview.error} />}
          {rejectReview.isError && <ErrorState error={rejectReview.error} />}
          {publish.isError && <ErrorState error={publish.error} />}
        </div>
      )}

      <Card className="mb-4">
        <CardHeader
          title="Checklist xuất bản"
          subtitle="Trạng thái nội dung và duyệt trước khi mở khóa học cho learner."
          actions={
            <Badge
              value={canPublish ? "READY" : canSubmitReview ? "DRAFT" : reviewState}
              label={canPublish ? "Sẵn sàng publish" : canSubmitReview ? "Sẵn sàng gửi duyệt" : reviewStateLabel(reviewState)}
            />
          }
        />
        <div className="grid gap-4 p-5 lg:grid-cols-2">
          <ReadinessColumn
            title="Gửi duyệt"
            subtitle="Hoàn tất khung nội dung trước khi đưa vào hàng chờ reviewer."
            items={reviewRequirements}
          />
          <ReadinessColumn
            title="Publish"
            subtitle="Chỉ publish sau khi reviewer đã duyệt version hiện tại."
            items={publishRequirements}
          />
        </div>
      </Card>

      <div className="mb-6 grid gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-black/10 bg-white p-4">
          <p className="text-sm text-slate-500">Chương</p>
          <p className="mt-1 text-3xl font-bold text-slate-950">{modules.length}</p>
        </div>
        <div className="rounded-lg border border-black/10 bg-white p-4">
          <p className="text-sm text-slate-500">Bài học</p>
          <p className="mt-1 text-3xl font-bold text-slate-950">{lessonCount}</p>
        </div>
        <div className="rounded-lg border border-black/10 bg-white p-4">
          <p className="text-sm text-slate-500">Phiên bản</p>
          <p className="mt-1 text-3xl font-bold text-slate-950">v{d.currentVersionNo}</p>
        </div>
        <div className="rounded-lg border border-black/10 bg-white p-4">
          <p className="text-sm text-slate-500">Review</p>
          <p className="mt-2"><Badge value={d.reviewState ?? "DRAFT"} /></p>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <CourseMap modules={modules} />

        <div className="space-y-5">
          {modules.length === 0 && (
            <Card>
              <EmptyState message="Tạo chương đầu tiên để bắt đầu thiết kế khóa học." />
            </Card>
          )}

          {modules.map((module) => {
            const itemForm = formFor(module.moduleId);
            const files = filesFor(module.moduleId);
            const items = [...(module.items ?? [])].sort((a, b) => a.position - b.position);

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
                  actions={<Badge value={module.status} />}
                />

                <div className="space-y-3 p-5">
                  {items.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm text-slate-500">
                      Chương này chưa có bài học.
                    </div>
                  ) : (
                    items.map((item, itemIndex) => (
                      <LessonCard key={item.itemId} item={item} displayIndex={itemIndex + 1} />
                    ))
                  )}
                </div>

                <form className="border-t border-black/10 bg-slate-50/70 p-5" onSubmit={(e) => submitItem(e, module.moduleId)}>
                  <div className="mb-4 flex items-center gap-2">
                    <Plus size={18} className="text-brand-700" />
                    <h3 className="font-bold text-slate-950">Thêm bài học</h3>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
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
                        onChange={(e) => updateItemForm(module.moduleId, { itemType: e.target.value })}
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

                      <FormField label="Liên kết nội dung" htmlFor={`item-url-${module.moduleId}`} hint="Dùng cho bài dạng link hoặc tài nguyên bên ngoài.">
                        <Input
                          id={`item-url-${module.moduleId}`}
                          value={itemForm.contentUrl}
                          onChange={(e) => updateItemForm(module.moduleId, { contentUrl: e.target.value })}
                          placeholder="https://..."
                        />
                      </FormField>

                      <FormField label="Ref ID nội bộ" htmlFor={`item-ref-${module.moduleId}`} hint="Dùng khi nối với bài thi, bài tập hoặc đối tượng đã tồn tại trong hệ thống.">
                        <Input
                          id={`item-ref-${module.moduleId}`}
                          value={itemForm.refId}
                          onChange={(e) => updateItemForm(module.moduleId, { refId: e.target.value })}
                          placeholder="UUID hoặc mã nội bộ"
                        />
                      </FormField>
                    </div>

                    <UploadTile
                      id={`item-video-${module.moduleId}`}
                      title="Upload video"
                      description="Tải video bài học lên media-service, sau đó lưu video ID vào lesson."
                      icon={<UploadCloud size={20} />}
                      accept="video/*"
                      selectedText={files.videoFile?.name}
                      onChange={(selected) => updateFiles(module.moduleId, { videoFile: selected?.[0] })}
                    />

                    <UploadTile
                      id={`item-docs-${module.moduleId}`}
                      title="Upload tài liệu"
                      description="PDF, slide, workbook hoặc tài liệu bổ trợ cho bài học."
                      icon={<FileText size={20} />}
                      accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,text/*,application/pdf"
                      multiple
                      selectedText={files.documentFiles.length > 0 ? `${files.documentFiles.length} file đã chọn` : undefined}
                      onChange={(selected) => updateFiles(module.moduleId, { documentFiles: Array.from(selected ?? []) })}
                    />
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
                    <Button type="submit" disabled={addItem.isPending}>
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
