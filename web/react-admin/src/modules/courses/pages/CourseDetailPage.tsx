import { FormEvent, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
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
  Table,
  Td,
  Th
} from "@/shared/ui";
import { listAssets, listVideos } from "@/modules/media/api";
import type { Course } from "../types";
import type { ManualRelatedCourse } from "../api";
import { useCourse, useCourseLifecycle, useCourses, useManualRelatedCourseMutations, useManualRelatedCourses } from "../hooks";

function compactId(value?: string) {
  if (!value) return "-";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function courseLabel(course?: Pick<Course, "code" | "title"> | null, fallbackId?: string) {
  if (!course) return fallbackId ? `Khóa ${compactId(fallbackId)}` : "Chọn khóa học";
  return course.code ? `${course.code} · ${course.title}` : course.title;
}

function relatedCourseLabel(row: ManualRelatedCourse, courseById: Map<string, Course>) {
  return courseLabel(row.relatedCourse ?? courseById.get(row.relatedCourseId), row.relatedCourseId);
}

function scoreText(score?: number) {
  if (typeof score !== "number") return "-";
  return score <= 1 ? `${Math.round(score * 100)}%` : String(score);
}

export function CourseDetailPage() {
  const { courseId = "" } = useParams();
  const { data: course, isLoading, isError, error } = useCourse(courseId);
  const { publish, archive, addMaterial } = useCourseLifecycle(courseId);
  const coursePicker = useCourses();
  const relatedCourses = useManualRelatedCourses(courseId);
  const relatedMutations = useManualRelatedCourseMutations(courseId);
  const assets = useQuery({
    queryKey: queryKeys.media.list,
    queryFn: listAssets,
    staleTime: 60_000
  });
  const videos = useQuery({
    queryKey: queryKeys.media.videos(courseId),
    queryFn: () => listVideos(courseId),
    enabled: Boolean(courseId),
    staleTime: 60_000
  });

  const [title, setTitle] = useState("");
  const [materialType, setMaterialType] = useState("VIDEO");
  const [mediaId, setMediaId] = useState("");
  const [relatedCourseId, setRelatedCourseId] = useState("");
  const [relatedReason, setRelatedReason] = useState("");
  const [relatedScore, setRelatedScore] = useState("0.9");
  const [relatedPosition, setRelatedPosition] = useState("");

  const courseById = useMemo(() => {
    const map = new Map<string, Course>();
    for (const row of coursePicker.data ?? []) map.set(row.id, row);
    return map;
  }, [coursePicker.data]);
  const relatedRows = relatedCourses.data ?? [];
  const relatedIds = useMemo(() => new Set(relatedRows.map((row) => row.relatedCourseId)), [relatedRows]);
  const availableRelatedCourses = useMemo(
    () => (coursePicker.data ?? []).filter((row) => row.id !== courseId && !relatedIds.has(row.id)),
    [courseId, coursePicker.data, relatedIds]
  );

  function submitMaterial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    addMaterial.mutate(
      {
        title,
        materialType,
        mediaId: mediaId.trim() || undefined,
        position: course?.materials?.length ?? 0
      },
      {
        onSuccess: () => {
          setTitle("");
          setMediaId("");
        }
      }
    );
  }

  function submitRelatedCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const score = relatedScore.trim() ? Number(relatedScore) : undefined;
    const position = relatedPosition.trim() ? Number(relatedPosition) : undefined;
    relatedMutations.create.mutate(
      {
        relatedCourseId,
        placement: "COURSE_DETAIL_RELATED",
        reason: relatedReason.trim() || undefined,
        weight: Number.isFinite(score) ? score : undefined,
        position: Number.isFinite(position) ? position : undefined
      },
      {
        onSuccess: () => {
          setRelatedCourseId("");
          setRelatedReason("");
          setRelatedScore("0.9");
          setRelatedPosition("");
        }
      }
    );
  }

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!course) return null;

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại danh sách
      </Link>
      <PageHeader
        title={course.title}
        description={`${course.code} · ${course.slug}`}
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={publish.isPending || course.status === "PUBLISHED"}
              onClick={() => publish.mutate()}
            >
              Xuất bản
            </Button>
            <Button
              variant="danger"
              disabled={archive.isPending || course.status === "ARCHIVED"}
              onClick={() => archive.mutate()}
            >
              Lưu trữ
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader title="Thông tin" />
          <dl className="grid grid-cols-[140px_1fr] gap-y-3 p-4 text-sm">
            <dt className="text-slate-500">Trạng thái</dt>
            <dd>
              <Badge value={course.status} />
            </dd>
            <dt className="text-slate-500">Cấp độ</dt>
            <dd>{course.level}</dd>
            <dt className="text-slate-500">Phòng ban</dt>
            <dd>{course.departmentId}</dd>
            <dt className="text-slate-500">Chủ sở hữu</dt>
            <dd>{course.ownerId}</dd>
            <dt className="text-slate-500">Mô tả</dt>
            <dd>{course.summary}</dd>
          </dl>
        </Card>

        <Card>
          <CardHeader title="Thêm tài liệu" />
          <form className="space-y-4 p-4" onSubmit={submitMaterial}>
            <FormField label="Tiêu đề" htmlFor="m-title">
              <Input id="m-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            </FormField>
            <FormField label="Loại" htmlFor="m-type">
              <Select
                id="m-type"
                value={materialType}
                onChange={(e) => {
                  setMaterialType(e.target.value);
                  setMediaId("");
                }}
              >
                <option value="VIDEO">VIDEO</option>
                <option value="IMAGE">IMAGE</option>
                <option value="PDF">PDF</option>
                <option value="LINK">LINK</option>
              </Select>
            </FormField>
            <FormField label="Media" htmlFor="m-media-id" hint="Chọn media đã upload; link ngoài có thể để trống.">
              <Select
                id="m-media-id"
                value={mediaId}
                onChange={(e) => setMediaId(e.target.value)}
                disabled={materialType === "LINK"}
              >
                <option value="">Không gắn media</option>
                {materialType === "VIDEO"
                  ? (videos.data ?? []).map((video) => (
                    <option key={video.id} value={video.id}>
                      {video.title} · {video.status}
                    </option>
                  ))
                  : (assets.data ?? []).map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.fileName} · {asset.contentType}
                    </option>
                  ))}
              </Select>
              {materialType === "VIDEO" && videos.isLoading && <span className="text-xs text-slate-400">Đang tải video...</span>}
              {materialType !== "VIDEO" && materialType !== "LINK" && assets.isLoading && <span className="text-xs text-slate-400">Đang tải media...</span>}
            </FormField>
            {videos.isError && materialType === "VIDEO" && <ErrorState error={videos.error} />}
            {assets.isError && materialType !== "VIDEO" && materialType !== "LINK" && <ErrorState error={assets.error} />}
            {addMaterial.isError && <ErrorState error={addMaterial.error} />}
            <Button type="submit" disabled={addMaterial.isPending}>
              {addMaterial.isPending ? "Đang lưu" : "Thêm tài liệu"}
            </Button>
          </form>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Khóa học liên quan thủ công"
          subtitle="Curate danh sách recommendation thủ công cho course detail."
          actions={
            <Button variant="secondary" size="sm" onClick={() => relatedCourses.refetch()} disabled={relatedCourses.isFetching}>
              <RefreshCw size={15} />
              Tải lại
            </Button>
          }
        />
        <form className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_120px_120px_auto]" onSubmit={submitRelatedCourse}>
          <FormField label="Khóa liên quan" htmlFor="related-course">
            <Select
              id="related-course"
              value={relatedCourseId}
              onChange={(event) => setRelatedCourseId(event.target.value)}
              required
            >
              <option value="">Chọn khóa học</option>
              {availableRelatedCourses.map((row) => (
                <option key={row.id} value={row.id}>
                  {courseLabel(row)}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Lý do hiển thị" htmlFor="related-reason" hint="Hiện trên learner card.">
            <Input
              id="related-reason"
              value={relatedReason}
              onChange={(event) => setRelatedReason(event.target.value)}
              placeholder="Ví dụ: Học tiếp để đào sâu production readiness"
            />
          </FormField>
          <FormField label="Weight" htmlFor="related-score">
            <Input
              id="related-score"
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={relatedScore}
              onChange={(event) => setRelatedScore(event.target.value)}
            />
          </FormField>
          <FormField label="Thứ tự" htmlFor="related-position">
            <Input
              id="related-position"
              type="number"
              min="1"
              value={relatedPosition}
              onChange={(event) => setRelatedPosition(event.target.value)}
              placeholder="Auto"
            />
          </FormField>
          <Button type="submit" className="self-end" disabled={relatedMutations.create.isPending || !relatedCourseId}>
            <Plus size={16} />
            Thêm
          </Button>
        </form>

        {coursePicker.isError && <ErrorState error={coursePicker.error} />}
        {relatedCourses.isLoading && <Spinner label="Đang tải khóa liên quan" />}
        {relatedCourses.isError && (
          <Notice tone="warning" title="Không tải được related courses" className="mx-4 mb-4">
            Kiểm tra quyền course staff/admin hoặc analytics-service.
          </Notice>
        )}
        {relatedMutations.create.isError && <ErrorState error={relatedMutations.create.error} />}
        {relatedMutations.update.isError && <ErrorState error={relatedMutations.update.error} />}
        {relatedMutations.remove.isError && <ErrorState error={relatedMutations.remove.error} />}

        {!relatedCourses.isLoading && !relatedCourses.isError && relatedRows.length === 0 && (
          <EmptyState message="Chưa có khóa học liên quan thủ công." />
        )}
        {relatedRows.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Khóa liên quan</Th>
                <Th>Nguồn</Th>
                <Th>Lý do</Th>
                <Th>Weight</Th>
                <Th>Trạng thái</Th>
                <Th>Hành động</Th>
              </tr>
            </thead>
            <tbody>
              {relatedRows.map((row) => (
                <tr key={row.id ?? row.relatedCourseId} className="hover:bg-slate-50">
                  <Td>
                    <p className="font-semibold text-slate-900">{relatedCourseLabel(row, courseById)}</p>
                    <p className="mt-1 text-xs text-slate-500">ID {compactId(row.relatedCourseId)}</p>
                  </Td>
                  <Td><Badge value={row.source ?? "MANUAL"} label={row.placement ?? row.source ?? "MANUAL"} /></Td>
                  <Td className="max-w-sm">
                    <p className="line-clamp-2">{row.reason || "Được curator chọn làm khóa học tiếp theo phù hợp."}</p>
                    {typeof row.position === "number" && (
                      <p className="mt-1 text-xs text-slate-400">Thứ tự {row.position}</p>
                    )}
                  </Td>
                  <Td>{scoreText(row.weight ?? row.score)}</Td>
                  <Td><Badge value={row.status ?? "ACTIVE"} /></Td>
                  <Td>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => relatedMutations.remove.mutate(row.relatedCourseId)}
                      disabled={relatedMutations.remove.isPending}
                    >
                      <Trash2 size={15} />
                      Gỡ
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card className="mt-4">
        <CardHeader title="Tài liệu khóa học" />
        <div className="divide-y divide-slate-100">
          {course.materials.length === 0 && (
            <p className="p-4 text-sm text-slate-500">Chưa có tài liệu.</p>
          )}
          {course.materials.map((material) => (
            <div key={material.id ?? `${material.title}-${material.position}`} className="flex items-center justify-between gap-4 p-4 text-sm">
              <div>
                <p className="font-medium text-slate-900">{material.title}</p>
                <p className="text-slate-500">
                  {material.materialType} · vị trí {material.position}
                  {material.mediaId ? ` · media ${material.mediaId}` : ""}
                </p>
              </div>
              <Badge value={material.materialType} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
