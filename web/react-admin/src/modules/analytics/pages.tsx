import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
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
import { fallbackCourses, listCourses } from "../courses/api";
import { listDepartments } from "../organization/api";
import { getCourseMetrics, recomputeMetrics, getCourseCompletion, getOrgDashboard } from "./api";

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-800">{value ?? "—"}</p>
    </div>
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

function orgLabel(org?: { code?: string; name?: string }, fallbackId?: string) {
  if (org) return [org.code, org.name].filter(Boolean).join(" · ");
  return fallbackId ? `Org ${compactId(fallbackId)}` : "Chưa chọn tổ chức";
}

export function AnalyticsPage() {
  const qc = useQueryClient();
  const courses = useQuery({
    queryKey: queryKeys.courses.list("analytics"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const departments = useQuery({
    queryKey: queryKeys.organization.departments,
    queryFn: () => listDepartments(),
    retry: 1,
    staleTime: 60_000
  });
  const courseRows = courses.data?.length ? courses.data : fallbackCourses;
  const courseById = useMemo(() => new Map(courseRows.map((course) => [course.id, course])), [courseRows]);
  const departmentRows = departments.data ?? [];
  const departmentById = useMemo(
    () => new Map(departmentRows.map((department) => [department.id, department])),
    [departmentRows]
  );

  const [courseId, setCourseId] = useState("");
  const [submitted, setSubmitted] = useState("");
  const metrics = useQuery({
    queryKey: queryKeys.analytics.course(submitted),
    queryFn: () => getCourseMetrics(submitted),
    enabled: Boolean(submitted)
  });
  const recompute = useMutation({
    mutationFn: () => recomputeMetrics(submitted),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.analytics.course(submitted) })
  });
  const selectedCourse = courseById.get(courseId);
  const submittedCourse = courseById.get(submitted);

  const [completionCourseId, setCompletionCourseId] = useState("");
  const [submittedCompletion, setSubmittedCompletion] = useState("");
  const completion = useQuery({
    queryKey: queryKeys.analytics.completion(submittedCompletion),
    queryFn: () => getCourseCompletion(submittedCompletion),
    enabled: Boolean(submittedCompletion)
  });
  const selectedCompletionCourse = courseById.get(completionCourseId);
  const submittedCompletionCourse = courseById.get(submittedCompletion);

  const [orgId, setOrgId] = useState("");
  const [submittedOrg, setSubmittedOrg] = useState("");
  const orgDashboard = useQuery({
    queryKey: queryKeys.analytics.org(submittedOrg),
    queryFn: () => getOrgDashboard(submittedOrg),
    enabled: Boolean(submittedOrg)
  });
  const selectedOrg = departmentById.get(orgId);
  const submittedOrgRow = departmentById.get(submittedOrg);

  return (
    <div>
      <PageHeader title="Phân tích" description="Tỷ lệ hoàn thành, mức độ tương tác và tín hiệu rủi ro theo khóa học/tổ chức." />

      <Card className="mb-4">
        <CardHeader
          title="Chỉ số khóa học"
          subtitle={submitted ? `Đang xem ${courseLabel(submittedCourse, submitted)}` : "Chọn course để xem completion, learner active và rủi ro."}
        />
        <form
          className="grid gap-3 p-4 lg:grid-cols-[1fr_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setSubmitted(courseId.trim());
          }}
        >
          <FormField label="Khóa học" htmlFor="an-course">
            <Select id="an-course" value={courseId} onChange={(e) => setCourseId(e.target.value)} required>
              <option value="">Chọn khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
              {courseId && !selectedCourse && <option value={courseId}>Course {compactId(courseId)}</option>}
            </Select>
          </FormField>
          <div className="flex items-end">
            <Button type="submit">Xem chỉ số</Button>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600 lg:col-span-2">
            <p className="font-semibold text-slate-900">{courseLabel(selectedCourse, courseId)}</p>
            <p className="mt-1 line-clamp-2">
              {selectedCourse?.summary ?? "Chọn khóa học để tải metric học tập và tính lại chỉ số khi cần."}
            </p>
          </div>
          <details className="rounded-lg border border-dashed border-slate-200 bg-white p-3 text-sm text-slate-600 lg:col-span-2">
            <summary className="cursor-pointer font-semibold text-slate-700">Nhập Course ID</summary>
            <FormField label="Course ID" htmlFor="an-course-manual">
              <Input
                id="an-course-manual"
                className="mt-3"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value.trim())}
                placeholder="UUID khóa học"
              />
            </FormField>
          </details>
        </form>
      </Card>

      {metrics.isLoading && <Spinner />}
      {metrics.isError && <ErrorState error={metrics.error} />}
      {metrics.data && (
        <>
          <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Hoàn thành" value={metrics.data.completionRate != null ? `${metrics.data.completionRate}%` : "—"} />
            <Metric label="Học viên tích cực" value={metrics.data.activeLearners} />
            <Metric label="Điểm TB" value={metrics.data.avgScore} />
            <Metric label="Có rủi ro" value={metrics.data.atRiskCount} />
          </div>
          <Button variant="secondary" disabled={recompute.isPending} onClick={() => recompute.mutate()}>
            {recompute.isPending ? "Đang tính lại" : "Tính lại chỉ số"}
          </Button>
        </>
      )}

      <div className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Hoàn thành khóa học</h2>
        <Card className="mb-4">
          <CardHeader
            title="Course completion"
            subtitle={submittedCompletion ? courseLabel(submittedCompletionCourse, submittedCompletion) : "Theo dõi enrollment và tỷ lệ hoàn thành."}
          />
          <form
            className="grid gap-3 p-4 lg:grid-cols-[1fr_auto]"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              setSubmittedCompletion(completionCourseId.trim());
            }}
          >
            <FormField label="Khóa học" htmlFor="an-completion-course">
              <Select
                id="an-completion-course"
                value={completionCourseId}
                onChange={(e) => setCompletionCourseId(e.target.value)}
                required
              >
                <option value="">Chọn khóa học</option>
                {courseRows.map((course) => (
                  <option key={course.id} value={course.id}>
                    {courseLabel(course)}
                  </option>
                ))}
                {completionCourseId && !selectedCompletionCourse && (
                  <option value={completionCourseId}>Course {compactId(completionCourseId)}</option>
                )}
              </Select>
            </FormField>
            <div className="flex items-end gap-2">
              <Button type="button" variant="secondary" disabled={!courseId} onClick={() => setCompletionCourseId(courseId)}>
                Dùng course trên
              </Button>
              <Button type="submit">Xem</Button>
            </div>
            <details className="rounded-lg border border-dashed border-slate-200 bg-white p-3 text-sm text-slate-600 lg:col-span-2">
              <summary className="cursor-pointer font-semibold text-slate-700">Nhập Course ID</summary>
              <FormField label="Course ID" htmlFor="an-completion-course-manual">
                <Input
                  id="an-completion-course-manual"
                  className="mt-3"
                  value={completionCourseId}
                  onChange={(e) => setCompletionCourseId(e.target.value.trim())}
                  placeholder="UUID khóa học"
                />
              </FormField>
            </details>
          </form>
        </Card>
        {completion.isLoading && <Spinner />}
        {completion.isError && <ErrorState error={completion.error} />}
        {completion.data && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Đã ghi danh" value={completion.data.enrolledCount} />
            <Metric label="Đã hoàn thành" value={completion.data.completedCount} />
            <Metric label="Tỷ lệ hoàn thành" value={`${completion.data.completionRate}%`} />
            <Metric label="TB ngày hoàn thành" value={completion.data.avgDaysToComplete ?? "—"} />
          </div>
        )}
      </div>

      <div className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Dashboard tổ chức</h2>
        <Card className="mb-4">
          <CardHeader
            title="Tổ chức"
            subtitle={submittedOrg ? orgLabel(submittedOrgRow, submittedOrg) : "Chọn phòng ban/tổ chức để xem dashboard tổng hợp."}
          />
          <form
            className="grid gap-3 p-4 lg:grid-cols-[1fr_auto]"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              setSubmittedOrg(orgId.trim());
            }}
          >
            <FormField label="Tổ chức" htmlFor="an-org">
              <Select id="an-org" value={orgId} onChange={(e) => setOrgId(e.target.value)} required>
                <option value="">Chọn tổ chức</option>
                {departmentRows.map((department) => (
                  <option key={department.id} value={department.id}>
                    {orgLabel(department)}
                  </option>
                ))}
                {orgId && !selectedOrg && <option value={orgId}>Org {compactId(orgId)}</option>}
              </Select>
            </FormField>
            <div className="flex items-end">
              <Button type="submit">Xem dashboard</Button>
            </div>
            <details className="rounded-lg border border-dashed border-slate-200 bg-white p-3 text-sm text-slate-600 lg:col-span-2">
              <summary className="cursor-pointer font-semibold text-slate-700">Nhập Org ID</summary>
              <FormField label="Org ID" htmlFor="an-org-manual">
                <Input
                  id="an-org-manual"
                  className="mt-3"
                  value={orgId}
                  onChange={(e) => setOrgId(e.target.value.trim())}
                  placeholder="ID tổ chức"
                />
              </FormField>
            </details>
          </form>
        </Card>
        {orgDashboard.isLoading && <Spinner />}
        {orgDashboard.isError && <ErrorState error={orgDashboard.error} />}
        {orgDashboard.data && (
          <div className="grid gap-4 sm:grid-cols-3">
            <Metric label="Học viên tích cực" value={orgDashboard.data.activeLearners} />
            <Metric label="Tổng ghi danh" value={orgDashboard.data.totalEnrollments} />
            <Metric label="Tỷ lệ hoàn thành TB" value={`${orgDashboard.data.avgCompletionRate}%`} />
          </div>
        )}
      </div>
    </div>
  );
}
