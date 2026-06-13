import { FormEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Tabs from "@radix-ui/react-tabs";
import * as Tooltip from "@radix-ui/react-tooltip";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Film,
  HardDrive,
  Play,
  RefreshCw,
  Search,
  Upload,
  X
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
  Spinner,
  Table,
  Td,
  Th
} from "@/shared/ui";
import {
  getAssetUploadUrl,
  getVideoPlaybackUrl,
  getVideoUploadUrl,
  listAssets,
  listVideos,
  registerAsset,
  registerVideo,
  type MediaAsset,
  type VideoAsset
} from "./api";
import { listCourses } from "../courses/api";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleString("vi-VN") : "-";
}

function contentTypeOf(file: File) {
  return file.type || "application/octet-stream";
}

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function courseLabel(course?: { code?: string; title?: string }, fallbackId?: string) {
  if (course) return [course.code, course.title].filter(Boolean).join(" · ");
  return fallbackId ? `Course ${compactId(fallbackId)}` : "Không gắn khóa học";
}

function metric(label: string, value: string | number, icon: ReactNode, tone: string) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-md ${tone}`}>{icon}</div>
      </div>
    </Card>
  );
}

function VideoPreviewDialog({
  open,
  onOpenChange,
  video,
  playback,
  onRetry
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  video: VideoAsset | null;
  playback: ReturnType<typeof useMutation<{ videoId: string; url: string; expiresAt: string }, Error, string>>;
  onRetry: () => void;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-slate-950/55" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(960px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-lg bg-white shadow-2xl">
          <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
            <div>
              <Dialog.Title className="text-base font-semibold text-slate-900">
                {video?.title ?? "Video"}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-slate-500">
                {video?.id ? `ID ${compactId(video.id)}` : "Video"}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                aria-label="Đóng"
              >
                <X size={18} />
              </button>
            </Dialog.Close>
          </header>
          <div className="bg-slate-950">
            {playback.isPending && (
              <div className="flex aspect-video items-center justify-center text-sm text-slate-300">
                Đang tải video
              </div>
            )}
            {playback.isError && (
              <div className="flex aspect-video flex-col items-center justify-center gap-3 text-sm text-slate-200">
                <p>{playback.error.message}</p>
                <Button type="button" variant="secondary" onClick={onRetry}>
                  <RefreshCw size={16} /> Thử lại
                </Button>
              </div>
            )}
            {playback.data && (
              <video
                key={playback.data.url}
                className="aspect-video w-full bg-slate-950"
                controls
                preload="metadata"
                src={playback.data.url}
              />
            )}
          </div>
          <footer className="flex items-center justify-between gap-3 px-5 py-3 text-sm text-slate-500">
            <span>{video?.sourceStorageKey ? `Storage ${compactId(video.sourceStorageKey)}` : ""}</span>
            {playback.data && <span>Hết hạn: {formatDate(playback.data.expiresAt)}</span>}
          </footer>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function AssetsTab() {
  const qc = useQueryClient();
  const assets = useQuery({ queryKey: queryKeys.media.list, queryFn: listAssets });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [search, setSearch] = useState("");
  const [progress, setProgress] = useState("");
  const [uploaded, setUploaded] = useState<MediaAsset | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const filteredAssets = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return (assets.data ?? []).filter((asset) => {
      if (!keyword) return true;
      return [asset.fileName, asset.contentType, asset.id, asset.storageKey]
        .some((value) => value?.toLowerCase().includes(keyword));
    });
  }, [assets.data, search]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setError(null);
    setUploaded(null);
    setProgress("Đang lấy URL tải lên...");
    try {
      const contentType = contentTypeOf(file);
      const presigned = await getAssetUploadUrl(file.name, contentType);
      setProgress("Đang tải tệp lên...");
      const upload = await fetch(presigned.uploadUrl, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": contentType }
      });
      if (!upload.ok) throw new Error(`Tải lên thất bại: ${upload.status}`);
      setProgress("Đang đăng ký media...");
      const asset = await registerAsset({
        fileName: file.name,
        contentType,
        storageKey: presigned.storageKey,
        sizeBytes: file.size
      });
      setUploaded(asset);
      setProgress("Hoàn tất");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      qc.invalidateQueries({ queryKey: queryKeys.media.list });
    } catch (err) {
      setProgress("");
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <Card>
        <CardHeader
          title="Thư viện tài liệu"
          subtitle={`${filteredAssets.length} / ${assets.data?.length ?? 0} tệp`}
          actions={
            <Button type="button" variant="secondary" size="sm" onClick={() => assets.refetch()}>
              <RefreshCw size={15} /> Làm mới
            </Button>
          }
        />
        <div className="border-b border-slate-100 p-4">
          <div className="relative max-w-md">
            <Search className="pointer-events-none absolute left-3 top-2.5 text-slate-400" size={16} />
              <Input
                className="pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm theo tên hoặc loại"
              />
          </div>
        </div>
        {assets.isLoading && <Spinner />}
        {assets.isError && <ErrorState error={assets.error} />}
        {assets.data && filteredAssets.length === 0 && <EmptyState message="Không có tài liệu phù hợp" />}
        {filteredAssets.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Tệp</Th>
                <Th>Loại</Th>
                <Th>Kích thước</Th>
                <Th>Ngày tạo</Th>
              </tr>
            </thead>
            <tbody>
              {filteredAssets.map((asset) => (
                <tr key={asset.id} className="hover:bg-slate-50">
                  <Td>
                    <div className="font-medium text-slate-900">{asset.fileName}</div>
                    <div className="mt-1 max-w-xl truncate text-xs text-slate-500">ID {compactId(asset.id)}</div>
                  </Td>
                  <Td><Badge value={asset.contentType} /></Td>
                  <Td>{formatBytes(asset.sizeBytes)}</Td>
                  <Td>{formatDate(asset.createdAt)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card>
        <CardHeader title="Tải lên tài liệu" />
        <form className="space-y-4 p-4" onSubmit={handleSubmit}>
          <FormField label="Tệp" htmlFor="asset-file">
            <input
              ref={fileInputRef}
              id="asset-file"
              type="file"
              accept="image/*,video/*,audio/*,application/pdf"
              className="hidden"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex min-h-36 w-full flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 text-center text-sm text-slate-500 hover:border-brand-400 hover:bg-brand-50"
            >
              <Upload size={28} />
              <span className="font-medium text-slate-700">{file ? file.name : "Chọn tệp"}</span>
              {file && <span>{formatBytes(file.size)}</span>}
            </button>
          </FormField>
          {progress && <p className="text-sm text-slate-600">{progress}</p>}
          {error && <ErrorState error={error} />}
          {uploaded && (
            <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
              <p><span className="font-medium">Media: </span>{compactId(uploaded.id)}</p>
              <p className="mt-1 truncate"><span className="font-medium">Storage key: </span>{compactId(uploaded.storageKey)}</p>
            </div>
          )}
          <Button type="submit" disabled={!file}>
            <Upload size={16} /> Tải lên
          </Button>
        </form>
      </Card>
    </div>
  );
}

function VideoUploadTab({ initialCourseId = "" }: { initialCourseId?: string }) {
  const qc = useQueryClient();
  const videos = useQuery({ queryKey: queryKeys.media.videos(), queryFn: () => listVideos() });
  const courses = useQuery({
    queryKey: queryKeys.courses.list("media"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const playback = useMutation({
    mutationFn: getVideoPlaybackUrl
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [courseId, setCourseId] = useState(initialCourseId);
  const [file, setFile] = useState<File | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [courseFilter, setCourseFilter] = useState(initialCourseId);
  const [selectedVideo, setSelectedVideo] = useState<VideoAsset | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [progress, setProgress] = useState("");
  const [video, setVideo] = useState<VideoAsset | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const courseRows = courses.data ?? [];
  const courseById = useMemo(() => new Map(courseRows.map((course) => [course.id, course])), [courseRows]);
  const selectedCourse = courseById.get(courseId);
  const selectedFilterCourse = courseById.get(courseFilter);

  const filteredVideos = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return (videos.data ?? []).filter((item) => {
      const itemCourseId = item.courseId ?? "";
      const itemCourseLabel = courseLabel(courseById.get(itemCourseId), itemCourseId || undefined).toLowerCase();
      const matchesSearch = !keyword || [item.title, item.id, item.sourceStorageKey, item.courseId ?? "", itemCourseLabel]
        .some((value) => value.toLowerCase().includes(keyword));
      const matchesStatus = statusFilter === "ALL" || item.status === statusFilter;
      const matchesCourse = !courseFilter || item.courseId === courseFilter;
      return matchesSearch && matchesStatus && matchesCourse;
    });
  }, [courseById, courseFilter, search, statusFilter, videos.data]);

  const readyCount = (videos.data ?? []).filter((item) => item.status === "READY").length;
  const uploadedCount = (videos.data ?? []).filter((item) => item.status === "UPLOADED").length;

  useEffect(() => {
    setCourseId(initialCourseId);
    setCourseFilter(initialCourseId);
  }, [initialCourseId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setError(null);
    setVideo(null);
    setProgress("Đang lấy URL tải lên...");
    try {
      const contentType = contentTypeOf(file);
      const presigned = await getVideoUploadUrl(title, file.name, contentType);
      setProgress("Đang tải video lên...");
      const upload = await fetch(presigned.uploadUrl, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": contentType }
      });
      if (!upload.ok) throw new Error(`Tải video thất bại: ${upload.status}`);
      setProgress("Đang đăng ký video...");
      const registered = await registerVideo({
        title,
        sourceStorageKey: presigned.storageKey,
        courseId: courseId.trim() || undefined
      });
      setVideo(registered);
      setProgress("Hoàn tất");
      qc.invalidateQueries({ queryKey: queryKeys.media.videos() });
      setTitle("");
      setCourseId(initialCourseId);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setProgress("");
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  }

  function openPreview(item: VideoAsset) {
    setSelectedVideo(item);
    setPreviewOpen(true);
    playback.reset();
    playback.mutate(item.id);
  }

  function closePreview(open: boolean) {
    setPreviewOpen(open);
    if (!open) {
      setSelectedVideo(null);
      playback.reset();
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        {metric("Tổng video", videos.data?.length ?? 0, <Film size={22} className="text-sky-700" />, "bg-sky-100")}
        {metric("Sẵn sàng", readyCount, <Play size={22} className="text-emerald-700" />, "bg-emerald-100")}
        {metric("Đã upload", uploadedCount, <HardDrive size={22} className="text-indigo-700" />, "bg-indigo-100")}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Card>
          <CardHeader
            title="Danh sách video"
            subtitle={`${filteredVideos.length} / ${videos.data?.length ?? 0} video`}
            actions={
              <Button type="button" variant="secondary" size="sm" onClick={() => videos.refetch()}>
                <RefreshCw size={15} /> Làm mới
              </Button>
            }
          />
          <div className="grid gap-3 border-b border-slate-100 p-4 md:grid-cols-[1fr_180px_1fr]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 text-slate-400" size={16} />
              <Input
                className="pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm video hoặc khóa học"
              />
            </div>
            <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="ALL">Tất cả trạng thái</option>
              <option value="READY">READY</option>
              <option value="UPLOADED">UPLOADED</option>
              <option value="TRANSCODING">TRANSCODING</option>
            </Select>
            <Select
              value={courseFilter}
              onChange={(event) => setCourseFilter(event.target.value)}
            >
              <option value="">Tất cả khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
              {courseFilter && !selectedFilterCourse && (
                <option value={courseFilter}>Course {compactId(courseFilter)}</option>
              )}
            </Select>
            {courses.isError && <ErrorState error={courses.error} />}
          </div>

          {videos.isLoading && <Spinner />}
          {videos.isError && <ErrorState error={videos.error} />}
          {videos.data && filteredVideos.length === 0 && <EmptyState message="Không có video phù hợp" />}
          {filteredVideos.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Video</Th>
                  <Th>Trạng thái</Th>
                  <Th>Course</Th>
                  <Th>Ngày tạo</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody>
                {filteredVideos.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <Td>
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="mt-1 max-w-lg truncate text-xs text-slate-500">ID {compactId(item.id)}</div>
                      <div className="mt-1 max-w-lg truncate text-xs text-slate-400">Storage {compactId(item.sourceStorageKey)}</div>
                    </Td>
                    <Td><Badge value={item.status} /></Td>
                    <Td>
                      <div className="font-medium text-slate-900">{courseLabel(courseById.get(item.courseId ?? ""), item.courseId ?? undefined)}</div>
                      {item.courseId && <div className="mt-1 text-xs text-slate-500">ID {compactId(item.courseId)}</div>}
                    </Td>
                    <Td>{formatDate(item.createdAt)}</Td>
                    <Td>
                      <div className="flex items-center justify-end gap-2">
                        <Tooltip.Root>
                          <Tooltip.Trigger asChild>
                            <button
                              type="button"
                              onClick={() => openPreview(item)}
                              className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-brand-500 text-white hover:bg-brand-600"
                              aria-label="Xem video"
                            >
                              <Play size={15} />
                            </button>
                          </Tooltip.Trigger>
                          <Tooltip.Portal>
                            <Tooltip.Content side="top" className="rounded-md bg-slate-900 px-2 py-1 text-xs font-medium text-white shadow">
                              Xem video
                              <Tooltip.Arrow className="fill-slate-900" />
                            </Tooltip.Content>
                          </Tooltip.Portal>
                        </Tooltip.Root>
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Tải lên video" />
          <form className="space-y-4 p-4" onSubmit={handleSubmit}>
            <FormField label="Tiêu đề video" htmlFor="v-title">
              <Input
                id="v-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
              />
            </FormField>
            <FormField label="Khóa học" htmlFor="v-course">
              <Select
                id="v-course"
                value={courseId}
                onChange={(event) => setCourseId(event.target.value)}
              >
                <option value="">Không gắn khóa học</option>
                {courseRows.map((course) => (
                  <option key={course.id} value={course.id}>
                    {courseLabel(course)}
                  </option>
                ))}
                {courseId && !selectedCourse && <option value={courseId}>Course {compactId(courseId)}</option>}
              </Select>
              {courses.isLoading && <span className="text-xs text-slate-400">Đang tải catalog khóa học...</span>}
            </FormField>
            {courses.isError && <ErrorState error={courses.error} />}
            <FormField label="Tệp video" htmlFor="v-file">
              <input
                ref={fileInputRef}
                id="v-file"
                type="file"
                accept="video/mp4,video/webm,video/quicktime"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex min-h-40 w-full flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 text-center text-sm text-slate-500 hover:border-brand-400 hover:bg-brand-50"
              >
                <Film size={30} />
                <span className="font-medium text-slate-700">{file ? file.name : "Chọn video"}</span>
                {file && <span>{formatBytes(file.size)}</span>}
              </button>
            </FormField>
            {progress && <p className="text-sm text-slate-600">{progress}</p>}
            {error && <ErrorState error={error} />}
            {video && (
              <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
                <p><span className="font-medium">Video ID: </span>{compactId(video.id)}</p>
                <p className="mt-1 truncate"><span className="font-medium">Storage key: </span>{compactId(video.sourceStorageKey)}</p>
              </div>
            )}
            <Button type="submit" disabled={!file || !title}>
              <Upload size={16} /> Tải lên
            </Button>
          </form>
        </Card>
      </div>

      <VideoPreviewDialog
        open={previewOpen}
        onOpenChange={closePreview}
        video={selectedVideo}
        playback={playback}
        onRetry={() => selectedVideo && playback.mutate(selectedVideo.id)}
      />
    </div>
  );
}

type Tab = "assets" | "video";

export function MediaPage() {
  const [searchParams] = useSearchParams();
  const scopedCourseId = searchParams.get("courseId") ?? "";
  const [tab, setTab] = useState<Tab>("video");

  return (
    <Tooltip.Provider delayDuration={200}>
      <div>
        <PageHeader
          title="Media"
          description="Video, tài liệu và asset phục vụ khóa học"
          actions={
            <div className="hidden items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500 md:flex">
              <FileText size={16} />
              <span>{scopedCourseId ? `Course ${compactId(scopedCourseId)}` : "courseflow-media"}</span>
            </div>
          }
        />
        <Tabs.Root value={tab} onValueChange={(value) => setTab(value as Tab)}>
          <Tabs.List className="mb-4 flex w-fit gap-1 rounded-lg border border-slate-200 bg-slate-100 p-1">
            <Tabs.Trigger
              value="video"
              className="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-slate-600 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
            >
              <Film size={16} /> Video
            </Tabs.Trigger>
            <Tabs.Trigger
              value="assets"
              className="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-slate-600 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
            >
              <FileText size={16} /> Tài liệu
            </Tabs.Trigger>
          </Tabs.List>
          <Tabs.Content value="video">
            <VideoUploadTab initialCourseId={scopedCourseId} />
          </Tabs.Content>
          <Tabs.Content value="assets">
            <AssetsTab />
          </Tabs.Content>
        </Tabs.Root>
      </div>
    </Tooltip.Provider>
  );
}
