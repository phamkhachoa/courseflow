import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Select,
  Spinner
} from "@/shared/ui";
import { useCourse, useCourseLifecycle } from "../hooks";

export function CourseDetailPage() {
  const { courseId = "" } = useParams();
  const { data: course, isLoading, isError, error } = useCourse(courseId);
  const { publish, archive, addMaterial } = useCourseLifecycle(courseId);

  const [title, setTitle] = useState("");
  const [materialType, setMaterialType] = useState("VIDEO");
  const [mediaId, setMediaId] = useState("");

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
              <Select id="m-type" value={materialType} onChange={(e) => setMaterialType(e.target.value)}>
                <option value="VIDEO">VIDEO</option>
                <option value="IMAGE">IMAGE</option>
                <option value="PDF">PDF</option>
                <option value="LINK">LINK</option>
              </Select>
            </FormField>
            <FormField label="Media ID" htmlFor="m-media-id">
              <Input
                id="m-media-id"
                value={mediaId}
                onChange={(e) => setMediaId(e.target.value)}
                placeholder="UUID trong media-service, có thể bỏ trống"
              />
            </FormField>
            {addMaterial.isError && <ErrorState error={addMaterial.error} />}
            <Button type="submit" disabled={addMaterial.isPending}>
              {addMaterial.isPending ? "Đang lưu" : "Thêm tài liệu"}
            </Button>
          </form>
        </Card>
      </div>

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
