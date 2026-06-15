import { FormEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, ClipboardList, RefreshCw, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { adminUserLabel, useLearnerUsers } from "@/modules/identity/useLearnerUsers";
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
import { listCourses } from "../courses/api";
import { listDepartments } from "../organization/api";
import { getAtRiskStudents, getCourseCompletion, getCourseMetrics, getMarketingFunnel, getOrgDashboard } from "./api";

type RiskFilter = "ALL" | "HIGH" | "MEDIUM";

function Metric({ label, value, detail }: { label: string; value: React.ReactNode; detail?: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-800">{value ?? "—"}</p>
      {detail && <p className="mt-2 text-sm text-slate-500">{detail}</p>}
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

function formatDateTime(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function formatDate(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short"
  }).format(new Date(value));
}

function formatPercent(value?: number | null) {
  return value === undefined || value === null ? "—" : `${value.toFixed(1)}%`;
}

function stageLabel(stage: string) {
  const labels: Record<string, string> = {
    IMPRESSION: "Impression",
    COURSE_VIEW: "Course view",
    CHECKOUT_STARTED: "Checkout",
    PAYMENT_SUCCESS: "Payment",
    ENROLLED: "Enrollment"
  };
  return labels[stage] ?? stage;
}

function reasonLabel(code: string) {
  const labels: Record<string, string> = {
    ENGAGEMENT_SCORE_LOW: "Engagement thấp",
    NO_ACTIVITY_7D: "Không hoạt động 7 ngày",
    NO_SUBMISSIONS_7D: "Chưa nộp bài tuần này",
    LOW_TIME_SPENT_7D: "Thời lượng thấp",
    NO_DISCUSSION_POSTS_7D: "Ít thảo luận"
  };
  return labels[code] ?? code;
}

function successGradebookLink(courseId: string, studentId: string) {
  const params = new URLSearchParams({ courseId, studentId });
  return `/gradebook?${params.toString()}`;
}

function certificateEligibilityLink(courseId: string, studentId: string) {
  const params = new URLSearchParams({ courseId, studentId });
  return `/certificates?${params.toString()}`;
}

export function AnalyticsPage() {
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
  const { userById, usersQuery } = useLearnerUsers();
  const courseRows = courses.data ?? [];
  const courseById = useMemo(() => new Map(courseRows.map((course) => [course.id, course])), [courseRows]);
  const departmentRows = departments.data ?? [];
  const departmentById = useMemo(
    () => new Map(departmentRows.map((department) => [department.id, department])),
    [departmentRows]
  );

  const [courseId, setCourseId] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("ALL");
  const metrics = useQuery({
    queryKey: queryKeys.analytics.course(submitted),
    queryFn: () => getCourseMetrics(submitted),
    enabled: Boolean(submitted)
  });
  const atRisk = useQuery({
    queryKey: queryKeys.analytics.atRisk(submitted),
    queryFn: () => getAtRiskStudents(submitted),
    enabled: Boolean(submitted)
  });
  const selectedCourse = courseById.get(courseId);
  const submittedCourse = courseById.get(submitted);
  const riskRows = atRisk.data ?? [];
  const highRiskCount = riskRows.filter((student) => student.riskLevel === "HIGH").length;
  const mediumRiskCount = riskRows.filter((student) => student.riskLevel === "MEDIUM").length;
  const staleRiskCount = riskRows.filter((student) => student.daysSinceActivity >= 7).length;
  const filteredRiskRows = riskRows.filter((student) => riskFilter === "ALL" || student.riskLevel === riskFilter);

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

  const [funnelForm, setFunnelForm] = useState({
    tenantId: "courseflow",
    applicationId: "lms",
    campaignCode: "",
    source: "",
    from: "",
    to: ""
  });
  const [submittedFunnel, setSubmittedFunnel] = useState<typeof funnelForm | null>(null);
  const marketingFunnel = useQuery({
    queryKey: queryKeys.analytics.marketingFunnel(submittedFunnel ?? {}),
    queryFn: () => getMarketingFunnel({ ...submittedFunnel!, limit: 500 }),
    enabled: Boolean(submittedFunnel?.tenantId && submittedFunnel.applicationId)
  });

  return (
    <div>
      <PageHeader title="Phân tích" description="Tỷ lệ hoàn thành, mức độ tương tác và tín hiệu rủi ro theo khóa học/tổ chức." />

      <Card className="mb-4">
        <CardHeader title="Marketing funnel" subtitle="Impression, course view, checkout, payment và enrollment theo campaign/source." />
        <form
          className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-6"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            setSubmittedFunnel(funnelForm);
          }}
        >
          <FormField label="Tenant" htmlFor="an-funnel-tenant" required>
            <Input
              id="an-funnel-tenant"
              value={funnelForm.tenantId}
              onChange={(event) => setFunnelForm({ ...funnelForm, tenantId: event.target.value })}
            />
          </FormField>
          <FormField label="Application" htmlFor="an-funnel-app" required>
            <Input
              id="an-funnel-app"
              value={funnelForm.applicationId}
              onChange={(event) => setFunnelForm({ ...funnelForm, applicationId: event.target.value })}
            />
          </FormField>
          <FormField label="Campaign" htmlFor="an-funnel-campaign">
            <Input
              id="an-funnel-campaign"
              value={funnelForm.campaignCode}
              onChange={(event) => setFunnelForm({ ...funnelForm, campaignCode: event.target.value })}
            />
          </FormField>
          <FormField label="Source" htmlFor="an-funnel-source">
            <Input
              id="an-funnel-source"
              value={funnelForm.source}
              onChange={(event) => setFunnelForm({ ...funnelForm, source: event.target.value })}
            />
          </FormField>
          <FormField label="From" htmlFor="an-funnel-from">
            <Input
              id="an-funnel-from"
              type="date"
              value={funnelForm.from}
              onChange={(event) => setFunnelForm({ ...funnelForm, from: event.target.value })}
            />
          </FormField>
          <FormField label="To" htmlFor="an-funnel-to">
            <Input
              id="an-funnel-to"
              type="date"
              value={funnelForm.to}
              onChange={(event) => setFunnelForm({ ...funnelForm, to: event.target.value })}
            />
          </FormField>
          <div className="flex items-end xl:col-span-6">
            <Button type="submit" disabled={!funnelForm.tenantId.trim() || !funnelForm.applicationId.trim()}>
              <Search size={16} />
              Xem funnel
            </Button>
          </div>
        </form>
        {marketingFunnel.isLoading && <Spinner />}
        {marketingFunnel.isError && <ErrorState error={marketingFunnel.error} />}
        {marketingFunnel.data && (
          <div className="space-y-4 p-4 pt-0">
            <div className="grid gap-3 md:grid-cols-5">
              {marketingFunnel.data.stages.map((stage) => (
                <Metric
                  key={stage.stage}
                  label={stageLabel(stage.stage)}
                  value={stage.count}
                  detail={`Step ${formatPercent(stage.stepConversionRate)} · Overall ${formatPercent(stage.overallConversionRate)}`}
                />
              ))}
            </div>
            {marketingFunnel.data.rows.length === 0 ? (
              <EmptyState message="Chưa có dữ liệu funnel cho filter này." />
            ) : (
              <Table>
                <thead>
                  <tr>
                    <Th>Ngày</Th>
                    <Th>Campaign</Th>
                    <Th>Source</Th>
                    <Th>Stage</Th>
                    <Th>Count</Th>
                  </tr>
                </thead>
                <tbody>
                  {marketingFunnel.data.rows.map((row, index) => (
                    <tr key={`${row.bucketDate}-${row.stage}-${index}`} className="hover:bg-slate-50">
                      <Td>{formatDate(row.bucketDate)}</Td>
                      <Td>{row.campaignCode || "-"}</Td>
                      <Td>{row.source || "-"}</Td>
                      <Td><Badge value={row.stage} label={stageLabel(row.stage)} /></Td>
                      <Td>{row.count}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>
        )}
      </Card>

      <Card className="mb-4">
        <CardHeader
          title="Chỉ số khóa học"
          subtitle={submitted ? `Đang xem ${courseLabel(submittedCourse, submitted)}` : "Chọn course để xem completion, learner active và rủi ro."}
        />
        <form
          className="grid gap-3 p-4 lg:grid-cols-[1fr_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setSubmitted(courseId);
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
            <Button type="submit">
              <Search size={16} />
              Xem chỉ số
            </Button>
          </div>
          {courses.isError && <ErrorState error={courses.error} />}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600 lg:col-span-2">
            <p className="font-semibold text-slate-900">{courseLabel(selectedCourse, courseId)}</p>
            <p className="mt-1 line-clamp-2">
              {selectedCourse?.summary ?? "Chọn khóa học để tải metric học tập và tính lại chỉ số khi cần."}
            </p>
          </div>
        </form>
      </Card>

      {metrics.isLoading && <Spinner />}
      {metrics.isError && <ErrorState error={metrics.error} />}
      {metrics.data && (
        <>
          <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Đã ghi danh" value={metrics.data.enrolledCount} />
            <Metric label="Đã nộp" value={metrics.data.submittedCount} />
            <Metric label="Điểm TB" value={metrics.data.averageScore ?? "—"} />
            <Metric label="Thảo luận" value={metrics.data.discussionCount} />
          </div>
          <Button
            variant="secondary"
            disabled={metrics.isFetching || atRisk.isFetching}
            onClick={() => {
              void metrics.refetch();
              void atRisk.refetch();
            }}
          >
            <RefreshCw size={16} />
            {metrics.isFetching || atRisk.isFetching ? "Đang làm mới" : "Làm mới"}
          </Button>
        </>
      )}
      {submitted && (
        <Card className="mt-4">
          <CardHeader
            title="Learner có rủi ro"
            subtitle={`Tín hiệu engagement cho ${courseLabel(submittedCourse, submitted)}`}
            actions={
              <Select
                aria-label="Lọc risk"
                className="h-9 min-w-[150px]"
                value={riskFilter}
                onChange={(event) => setRiskFilter(event.target.value as RiskFilter)}
              >
                <option value="ALL">Tất cả risk</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
              </Select>
            }
          />
          {atRisk.isLoading && <Spinner />}
          {atRisk.isError && <ErrorState error={atRisk.error} />}
          {atRisk.data && atRisk.data.length === 0 && <EmptyState message="Chưa có learner rủi ro" />}
          {riskRows.length > 0 && (
            <>
              <div className="grid gap-3 p-4 md:grid-cols-4">
                <Metric label="Tổng risk" value={riskRows.length} detail="HIGH và MEDIUM" />
                <Metric label="HIGH" value={highRiskCount} detail="Cần ưu tiên hỗ trợ" />
                <Metric label="MEDIUM" value={mediumRiskCount} detail="Theo dõi sát" />
                <Metric label="Không hoạt động" value={staleRiskCount} detail="Từ 7 ngày trở lên" />
              </div>
              {filteredRiskRows.length === 0 ? (
                <EmptyState message="Không có learner trong filter hiện tại." />
              ) : (
                <Table>
                  <thead>
                    <tr>
                      <Th>Học viên</Th>
                      <Th>Risk</Th>
                      <Th>Engagement</Th>
                      <Th>Lần hoạt động cuối</Th>
                      <Th>Lý do</Th>
                      <Th>Hành động</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRiskRows.map((student) => (
                      <tr key={student.studentId} className="hover:bg-slate-50">
                        <Td>
                          <p className="font-semibold text-slate-900">
                            {adminUserLabel(userById.get(student.studentId), compactId(student.studentId))}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">ID {student.studentId}</p>
                          {usersQuery.isError && (
                            <p className="mt-1 text-xs font-semibold text-amber-700">Không tải được tên learner</p>
                          )}
                        </Td>
                        <Td><Badge value={student.riskLevel} /></Td>
                        <Td>
                          <p className="font-semibold text-slate-900">{student.engagementScore.toFixed(1)}</p>
                          <p className="mt-1 text-xs text-slate-500">Điểm thấp được ưu tiên trước</p>
                        </Td>
                        <Td>
                          <p>{formatDateTime(student.lastActivityAt)}</p>
                          <p className="mt-1 text-xs text-slate-500">{student.daysSinceActivity} ngày</p>
                        </Td>
                        <Td>
                          <div className="flex flex-wrap gap-1">
                            {student.riskReasons.map((reason) => (
                              <span key={reason} className="rounded-md bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">
                                {reasonLabel(reason)}
                              </span>
                            ))}
                          </div>
                        </Td>
                        <Td>
                          <div className="flex flex-wrap gap-2">
                            <Link to={successGradebookLink(student.courseId, student.studentId)}>
                              <Button size="sm" variant="secondary">
                                <ClipboardList size={15} />
                                Gradebook
                              </Button>
                            </Link>
                            <Link to={certificateEligibilityLink(student.courseId, student.studentId)}>
                              <Button size="sm" variant="secondary">
                                <Award size={15} />
                                Eligibility
                              </Button>
                            </Link>
                          </div>
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </>
          )}
        </Card>
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
              setSubmittedCompletion(completionCourseId);
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
            {courses.isError && <ErrorState error={courses.error} />}
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
              setSubmittedOrg(orgId);
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
            {departments.isError && <ErrorState error={departments.error} />}
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
