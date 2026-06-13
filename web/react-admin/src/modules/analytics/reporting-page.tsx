import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
  Button,
  Card,
  CardHeader,
  ErrorState,
  FormField,
  PageHeader,
  Select,
  Spinner
} from "@/shared/ui";
import { listCourses } from "../courses/api";
import { listDepartments } from "../organization/api";
import { getCourseCompletion, getOrgDashboard } from "./api";

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-800">{value ?? "—"}</p>
    </div>
  );
}

export function ReportingPage() {
  const [courseId, setCourseId] = useState("");
  const [orgId, setOrgId] = useState("");
  const [submittedCourse, setSubmittedCourse] = useState("");
  const [submittedOrg, setSubmittedOrg] = useState("");

  const courses = useQuery({
    queryKey: queryKeys.courses.list("reporting"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const departments = useQuery({
    queryKey: queryKeys.organization.departments,
    queryFn: () => listDepartments(),
    staleTime: 60_000
  });
  const courseRows = courses.data ?? [];
  const departmentRows = departments.data ?? [];

  const completion = useQuery({
    queryKey: queryKeys.analytics.completion(submittedCourse),
    queryFn: () => getCourseCompletion(submittedCourse),
    enabled: Boolean(submittedCourse)
  });

  const orgDash = useQuery({
    queryKey: queryKeys.analytics.org(submittedOrg),
    queryFn: () => getOrgDashboard(submittedOrg),
    enabled: Boolean(submittedOrg)
  });

  return (
    <div>
      <PageHeader title="Báo cáo" description="Tỷ lệ hoàn thành theo khóa học và dashboard tổ chức" />

      <Card className="mb-4 max-w-lg">
        <CardHeader title="Hoàn thành khóa học" />
        <form
          className="flex items-end gap-3 p-4"
          onSubmit={(e: FormEvent) => { e.preventDefault(); setSubmittedCourse(courseId); }}
        >
          <div className="flex-1">
            <FormField label="Khóa học" htmlFor="rp-course">
              <Select id="rp-course" value={courseId} onChange={(e) => setCourseId(e.target.value)} required>
                <option value="">Chọn khóa học</option>
                {courseRows.map((course) => (
                  <option key={course.id} value={course.id}>
                    {[course.code, course.title].filter(Boolean).join(" · ")}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <Button type="submit">Xem</Button>
        </form>
        {courses.isError && <ErrorState error={courses.error} />}
        {completion.isLoading && <Spinner />}
        {completion.isError && <ErrorState error={completion.error} />}
        {completion.data && (
          <div className="grid gap-3 p-4 sm:grid-cols-3">
            <Metric label="Ghi danh" value={completion.data.enrolledCount} />
            <Metric label="Hoàn thành" value={completion.data.completedCount} />
            <Metric label="Tỷ lệ (%)" value={`${completion.data.completionRate.toFixed(1)}%`} />
          </div>
        )}
      </Card>

      <Card className="max-w-lg">
        <CardHeader title="Dashboard tổ chức" />
        <form
          className="flex items-end gap-3 p-4"
          onSubmit={(e: FormEvent) => { e.preventDefault(); setSubmittedOrg(orgId); }}
        >
          <div className="flex-1">
            <FormField label="Tổ chức" htmlFor="rp-org">
              <Select id="rp-org" value={orgId} onChange={(e) => setOrgId(e.target.value)} required>
                <option value="">Chọn tổ chức</option>
                {departmentRows.map((department) => (
                  <option key={department.id} value={department.id}>
                    {[department.code, department.name].filter(Boolean).join(" · ")}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <Button type="submit">Xem</Button>
        </form>
        {departments.isError && <ErrorState error={departments.error} />}
        {orgDash.isLoading && <Spinner />}
        {orgDash.isError && <ErrorState error={orgDash.error} />}
        {orgDash.data && (
          <div className="grid gap-3 p-4 sm:grid-cols-3">
            <Metric label="Học viên tích cực" value={orgDash.data.activeLearners} />
            <Metric label="Tổng ghi danh" value={orgDash.data.totalEnrollments} />
            <Metric label="TB hoàn thành (%)" value={`${orgDash.data.avgCompletionRate.toFixed(1)}%`} />
          </div>
        )}
      </Card>
    </div>
  );
}
