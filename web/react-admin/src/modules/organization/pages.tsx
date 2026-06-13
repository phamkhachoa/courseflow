import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
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
import { fallbackCourses, listCourses } from "../courses/api";
import { createSection, listDepartments, listSections, listTerms } from "./api";

function SimpleList<T extends { id: string }>({
  title,
  queryKey,
  queryFn,
  columns
}: {
  title: string;
  queryKey: readonly unknown[];
  queryFn: () => Promise<T[]>;
  columns: { header: string; render: (row: T) => React.ReactNode }[];
}) {
  const { data, isLoading, isError, error } = useQuery({ queryKey, queryFn });
  return (
    <Card>
      <CardHeader title={title} />
      {isLoading && <Spinner />}
      {isError && <ErrorState error={error} />}
      {data && data.length === 0 && <EmptyState message="Không có dữ liệu" />}
      {data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              {columns.map((c) => (
                <Th key={c.header}>{c.header}</Th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.id} className="hover:bg-slate-50">
                {columns.map((c) => (
                  <Td key={c.header}>{c.render(row)}</Td>
                ))}
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function courseLabel(course?: { code?: string; title?: string }, fallbackId?: string) {
  if (course) return [course.code, course.title].filter(Boolean).join(" · ");
  return fallbackId ? `Course ${compactId(fallbackId)}` : "Chưa chọn khóa học";
}

function termLabel(term?: { name?: string; startDate?: string; endDate?: string }, fallbackId?: string) {
  if (!term) return fallbackId ? `Kỳ ${compactId(fallbackId)}` : "Chưa chọn kỳ";
  return term.name ?? `Kỳ ${compactId(fallbackId)}`;
}

export function OrganizationPage() {
  const qc = useQueryClient();
  const courses = useQuery({
    queryKey: queryKeys.courses.list("organization"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const terms = useQuery({
    queryKey: queryKeys.organization.terms,
    queryFn: listTerms,
    retry: 1,
    staleTime: 60_000
  });
  const [form, setForm] = useState({ courseId: "", termId: "", code: "", capacity: 30 });
  const create = useMutation({
    mutationFn: () => createSection(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.organization.sections });
      setForm((current) => ({ ...current, code: "" }));
    }
  });
  const courseRows = courses.data?.length ? courses.data : fallbackCourses;
  const termRows = terms.data ?? [];
  const courseById = useMemo(() => new Map(courseRows.map((course) => [course.id, course])), [courseRows]);
  const termById = useMemo(() => new Map(termRows.map((term) => [term.id, term])), [termRows]);

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div>
      <PageHeader title="Tổ chức" description="Phòng ban, kỳ học và lớp học phần" />
      <div className="grid gap-4 lg:grid-cols-2">
        <SimpleList
          title="Phòng ban"
          queryKey={queryKeys.organization.departments}
          queryFn={listDepartments}
          columns={[
            { header: "Mã", render: (r) => r.code ?? "—" },
            { header: "Tên", render: (r) => r.name }
          ]}
        />
        <SimpleList
          title="Kỳ học"
          queryKey={queryKeys.organization.terms}
          queryFn={listTerms}
          columns={[
            { header: "Tên", render: (r) => r.name },
            { header: "Bắt đầu", render: (r) => r.startDate ?? "—" },
            { header: "Kết thúc", render: (r) => r.endDate ?? "—" }
          ]}
        />
        <SimpleList
          title="Lớp học phần"
          queryKey={queryKeys.organization.sections}
          queryFn={listSections}
          columns={[
            { header: "Mã", render: (r) => r.code ?? "—" },
            {
              header: "Khóa học",
              render: (r) => (
                <div>
                  <p className="font-semibold text-slate-900">{courseLabel(courseById.get(r.courseId), r.courseId)}</p>
                  <p className="mt-1 text-xs text-slate-500">ID {compactId(r.courseId)}</p>
                </div>
              )
            },
            {
              header: "Kỳ",
              render: (r) => (
                <div>
                  <p className="font-semibold text-slate-900">{termLabel(termById.get(r.termId), r.termId)}</p>
                  <p className="mt-1 text-xs text-slate-500">ID {compactId(r.termId)}</p>
                </div>
              )
            },
            { header: "Sức chứa", render: (r) => r.capacity ?? "—" }
          ]}
        />
        <Card>
          <CardHeader
            title="Tạo lớp học phần"
            subtitle={[courseLabel(courseById.get(form.courseId), form.courseId), termLabel(termById.get(form.termId), form.termId)]
              .filter((item) => !item.startsWith("Chưa chọn"))
              .join(" · ") || "Chọn khóa học và kỳ học trước khi tạo lớp."}
          />
          <form className="space-y-4 p-4" onSubmit={submit}>
            <FormField label="Khóa học" htmlFor="s-course">
              <Select id="s-course" value={form.courseId} onChange={(e) => setForm({ ...form, courseId: e.target.value })} required>
                <option value="">Chọn khóa học</option>
                {courseRows.map((course) => (
                  <option key={course.id} value={course.id}>
                    {courseLabel(course)}
                  </option>
                ))}
                {form.courseId && !courseById.has(form.courseId) && (
                  <option value={form.courseId}>Course {compactId(form.courseId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Kỳ học" htmlFor="s-term">
              <Select id="s-term" value={form.termId} onChange={(e) => setForm({ ...form, termId: e.target.value })} required>
                <option value="">Chọn kỳ học</option>
                {termRows.map((term) => (
                  <option key={term.id} value={term.id}>
                    {termLabel(term)}
                  </option>
                ))}
                {form.termId && !termById.has(form.termId) && (
                  <option value={form.termId}>Kỳ {compactId(form.termId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Mã lớp" htmlFor="s-code">
              <Input id="s-code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required />
            </FormField>
            <FormField label="Sức chứa" htmlFor="s-cap">
              <Input id="s-cap" type="number" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })} />
            </FormField>
            {create.isError && <ErrorState error={create.error} />}
            <Button type="submit" disabled={create.isPending || !form.courseId || !form.termId || !form.code}>
              {create.isPending ? "Đang lưu" : "Tạo lớp"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
