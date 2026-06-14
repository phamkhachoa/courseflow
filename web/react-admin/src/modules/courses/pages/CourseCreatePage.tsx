import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, CardHeader, ErrorState, FormField, Input, PageHeader, Select } from "@/shared/ui";
import { useCreateCourse } from "../hooks";
import type { CreateCourseInput } from "../types";

const EMPTY: CreateCourseInput = {
  code: "",
  title: "",
  slug: "",
  summary: "",
  departmentId: "20000000-0000-0000-0000-000000000001",
  level: "BEGINNER",
  listPrice: 100,
  currency: "USD"
};

const DEPARTMENT_OPTIONS = [
  { value: "20000000-0000-0000-0000-000000000001", label: "Software Engineering" },
  { value: "20000000-0000-0000-0000-000000000002", label: "Computer Science" },
  { value: "20000000-0000-0000-0000-000000000003", label: "AI Lab" }
];

export function CourseCreatePage() {
  const navigate = useNavigate();
  const create = useCreateCourse();
  const [form, setForm] = useState<CreateCourseInput>(EMPTY);

  function update<K extends keyof CreateCourseInput>(key: K, value: CreateCourseInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate(form, { onSuccess: (course) => navigate(`../${course.id}`) });
  }

  return (
    <div>
      <PageHeader title="Tạo khóa học" description="Thêm khóa học mới vào danh mục" />
      <Card className="max-w-2xl">
        <CardHeader title="Thông tin khóa học" />
        <form className="grid gap-4 p-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <FormField label="Mã" htmlFor="code">
            <Input id="code" value={form.code} onChange={(e) => update("code", e.target.value)} required />
          </FormField>
          <FormField label="Cấp độ" htmlFor="level">
            <Select id="level" value={form.level} onChange={(e) => update("level", e.target.value)}>
              <option value="BEGINNER">BEGINNER</option>
              <option value="INTERMEDIATE">INTERMEDIATE</option>
              <option value="ADVANCED">ADVANCED</option>
            </Select>
          </FormField>
          <FormField label="Tiêu đề" htmlFor="title">
            <Input id="title" value={form.title} onChange={(e) => update("title", e.target.value)} required />
          </FormField>
          <FormField label="Slug" htmlFor="slug">
            <Input id="slug" value={form.slug} onChange={(e) => update("slug", e.target.value)} required />
          </FormField>
          <FormField label="List price" htmlFor="listPrice">
            <Input
              id="listPrice"
              type="number"
              min="0"
              step="0.01"
              value={String(form.listPrice ?? "")}
              onChange={(e) => update("listPrice", e.target.value === "" ? undefined : Number(e.target.value))}
            />
          </FormField>
          <FormField label="Currency" htmlFor="currency">
            <Input
              id="currency"
              value={form.currency ?? ""}
              maxLength={3}
              onChange={(e) => update("currency", e.target.value.toUpperCase())}
            />
          </FormField>
          <FormField label="Phòng ban" htmlFor="dept">
            <Select id="dept" value={form.departmentId} onChange={(e) => update("departmentId", e.target.value)} required>
              {DEPARTMENT_OPTIONS.map((department) => (
                <option key={department.value} value={department.value}>
                  {department.label}
                </option>
              ))}
            </Select>
          </FormField>
          <div className="md:col-span-2">
            <FormField label="Mô tả" htmlFor="summary">
              <Input id="summary" value={form.summary} onChange={(e) => update("summary", e.target.value)} />
            </FormField>
          </div>
          {create.isError && (
            <div className="md:col-span-2">
              <ErrorState error={create.error} />
            </div>
          )}
          <div className="flex gap-2 md:col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Đang tạo" : "Tạo khóa học"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => navigate("..")}>
              Hủy
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
