import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
  Button,
  Card,
  CardHeader,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Spinner
} from "@/shared/ui";
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
          onSubmit={(e: FormEvent) => { e.preventDefault(); setSubmittedCourse(courseId.trim()); }}
        >
          <div className="flex-1">
            <FormField label="Khóa học (ID)" htmlFor="rp-course">
              <Input id="rp-course" value={courseId} onChange={(e) => setCourseId(e.target.value)} required />
            </FormField>
          </div>
          <Button type="submit">Xem</Button>
        </form>
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
          onSubmit={(e: FormEvent) => { e.preventDefault(); setSubmittedOrg(orgId.trim()); }}
        >
          <div className="flex-1">
            <FormField label="Tổ chức (ID)" htmlFor="rp-org">
              <Input id="rp-org" value={orgId} onChange={(e) => setOrgId(e.target.value)} required />
            </FormField>
          </div>
          <Button type="submit">Xem</Button>
        </form>
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
