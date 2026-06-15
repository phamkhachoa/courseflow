import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Archive,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  EyeOff,
  FileText,
  Plus,
  RotateCcw,
  Search,
  Star,
  UserCheck
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
  Notice,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Textarea,
  Th
} from "@/shared/ui";
import {
  createAssignment,
  getAssignment,
  getRubric,
  gradeSubmission,
  listAssignments,
  listGradingQueue,
  listSubmissions,
  setAssignmentLifecycle,
  upsertRubric
} from "./api";
import type { AssignmentLifecycleAction } from "./api";
import { listCourses } from "../courses/api";
import { adminUserLabel, useLearnerUsers } from "../identity/useLearnerUsers";

const ASSIGNMENT_TYPES = ["ONLINE_TEXT", "FILE_UPLOAD", "CODE_PROJECT", "CASE_STUDY", "LAB_REPORT", "PORTFOLIO"];

function formatDateTime(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function dueLabel(value?: string) {
  if (!value) return { label: "Không hạn", urgent: false };
  const due = new Date(value).getTime();
  if (Number.isNaN(due)) return { label: value, urgent: false };
  const diffDays = Math.ceil((due - Date.now()) / 86_400_000);
  if (diffDays < 0) return { label: `Trễ ${Math.abs(diffDays)} ngày`, urgent: true };
  if (diffDays === 0) return { label: "Hạn hôm nay", urgent: true };
  if (diffDays <= 3) return { label: `Còn ${diffDays} ngày`, urgent: true };
  return { label: `Còn ${diffDays} ngày`, urgent: false };
}

function toDateTimeLocalValue(value: string) {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) return value;
  return value;
}

function dateTimeLocalToIso(value: string) {
  if (!value) return "";
  if (value.endsWith("Z")) return value;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
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

function assignmentStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    DRAFT: "Nháp - chưa hiển thị",
    PUBLISHED: "Đã công khai",
    ARCHIVED: "Đã lưu trữ"
  };
  return labels[status ?? ""] ?? status ?? "Nháp - chưa hiển thị";
}

function learnerVisibilityText(status?: string) {
  if (status === "PUBLISHED") return "Learner có thể nhìn thấy và nộp bài.";
  if (status === "ARCHIVED") return "Đã lưu trữ, không nên dùng trong curriculum đang publish.";
  return "Nháp chưa hiển thị cho learner.";
}

function nextLifecycleAction(status?: string): { action: AssignmentLifecycleAction; label: string } {
  if (status === "PUBLISHED") return { action: "archive", label: "Archive" };
  if (status === "ARCHIVED") return { action: "draft", label: "Đưa về nháp" };
  return { action: "publish", label: "Publish" };
}

export function AssignmentListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get("courseId") ?? "";
  const [courseId, setCourseId] = useState(requestedCourseId);
  const qc = useQueryClient();
  const courses = useQuery({
    queryKey: queryKeys.courses.list("assignments"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.assignments.list(courseId),
    queryFn: () => listAssignments(courseId),
    enabled: Boolean(courseId)
  });
  const gradingQueue = useQuery({
    queryKey: queryKeys.assignments.gradingQueue(courseId),
    queryFn: () => listGradingQueue(courseId),
    enabled: Boolean(courseId),
    staleTime: 30_000
  });

  useEffect(() => {
    setCourseId(requestedCourseId);
  }, [requestedCourseId]);

  function changeCourseId(value: string) {
    setCourseId(value);
    const nextCourseId = value.trim();
    setSearchParams(nextCourseId ? { courseId: nextCourseId } : {}, { replace: true });
  }

  const courseRows = courses.data ?? [];
  const selectedCourse = courseRows.find((course) => course.id === courseId);
  const assignments = data ?? [];
  const queueRows = gradingQueue.data ?? [];
  const publishedCount = assignments.filter((assignment) => assignment.status === "PUBLISHED").length;
  const rubricCount = assignments.filter((assignment) => Boolean(assignment.rubricId)).length;
  const urgentCount = assignments.filter((assignment) => dueLabel(assignment.dueAt).urgent).length;
  const lifecycle = useMutation({
    mutationFn: ({ assignmentId, action }: { assignmentId: string; action: AssignmentLifecycleAction }) =>
      setAssignmentLifecycle(assignmentId, action),
    onSuccess: (assignment) => {
      qc.invalidateQueries({ queryKey: queryKeys.assignments.list(assignment.courseId) });
      qc.invalidateQueries({ queryKey: queryKeys.assignments.detail(assignment.id) });
    }
  });

  return (
    <div>
      <PageHeader
        title="Bài tập"
        description="Quản lý assignment, rubric, deadline và bài nộp của từng khóa học."
        actions={
          <Link to={courseId ? `new?courseId=${courseId}` : "new"}>
            <Button>
              <Plus size={16} /> Tạo bài tập
            </Button>
          </Link>
        }
      />

      <Card className="mb-4">
        <CardHeader
          title="Chọn khóa học"
          subtitle="Course được giữ trên URL để chuyển qua bài thi, module, bảng điểm hoặc tạo assignment không mất context."
        />
        <div className="grid gap-4 p-4 lg:grid-cols-[1fr_1fr]">
          <FormField label="Khóa học" htmlFor="assignment-course">
            <Select id="assignment-course" value={courseId} onChange={(event) => changeCourseId(event.target.value)}>
              <option value="">Chọn khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {[course.code, course.title].filter(Boolean).join(" · ")}
                </option>
              ))}
              {courseId && !selectedCourse && <option value={courseId}>Course {compactId(courseId)}</option>}
            </Select>
          </FormField>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <p className="font-semibold text-slate-900">
              {courseLabel(selectedCourse, courseId)}
            </p>
            <p className="mt-1 line-clamp-2 text-slate-500">
              {selectedCourse?.summary ?? "Chọn course để tải assignment, rubric và bài nộp."}
            </p>
          </div>
          {courses.isError && <ErrorState error={courses.error} />}
        </div>
      </Card>

      <div className="mb-4 grid gap-3 md:grid-cols-3">
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-500">Tổng assignment</p>
              <p className="mt-2 text-2xl font-bold text-slate-950">{courseId ? assignments.length : "—"}</p>
            </div>
            <span className="grid size-10 place-items-center rounded-md bg-brand-50 text-brand-700">
              <ClipboardCheck size={18} />
            </span>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-500">Đã công khai</p>
              <p className="mt-2 text-2xl font-bold text-slate-950">{courseId ? publishedCount : "—"}</p>
            </div>
            <span className="grid size-10 place-items-center rounded-md bg-emerald-50 text-emerald-700">
              <CheckCircle2 size={18} />
            </span>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-500">Cần chú ý</p>
              <p className="mt-2 text-2xl font-bold text-slate-950">{courseId ? urgentCount : "—"}</p>
            </div>
            <span className="grid size-10 place-items-center rounded-md bg-amber-50 text-amber-700">
              <CalendarClock size={18} />
            </span>
          </div>
          <p className="mt-3 text-xs font-semibold text-slate-500">{rubricCount} assignment có rubric.</p>
        </Card>
      </div>

      <Card className="mb-4">
        <CardHeader
          title="Hàng chờ chấm điểm"
          subtitle={courseId ? `${queueRows.length} bài nộp đang chờ xử lý` : "Chọn course để xem submission cần chấm."}
        />
        {!courseId && <EmptyState message="Chọn khóa học để xem grading queue." />}
        {gradingQueue.isLoading && <Spinner />}
        {gradingQueue.isError && <ErrorState error={gradingQueue.error} />}
        {courseId && gradingQueue.data && gradingQueue.data.length === 0 && <EmptyState message="Không có bài nộp cần chấm" />}
        {gradingQueue.data && gradingQueue.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Assignment</Th>
                <Th>Học viên</Th>
                <Th>Nộp lúc</Th>
                <Th>Trạng thái</Th>
                <Th>Cấu hình</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {gradingQueue.data.map((item) => (
                <tr key={item.submissionId} className="hover:bg-slate-50">
                  <Td>
                    <p className="font-semibold text-slate-900">{item.assignmentTitle}</p>
                    <p className="mt-1 text-xs text-slate-500">Submission {compactId(item.submissionId)}</p>
                  </Td>
                  <Td>
                    <p className="font-semibold text-slate-900">Learner {compactId(item.studentId)}</p>
                    <p className="mt-1 text-xs text-slate-500">Attempt {item.attemptNo}</p>
                  </Td>
                  <Td>{formatDateTime(item.submittedAt)}</Td>
                  <Td>
                    <Badge value={item.status} />
                    {item.isLate && <p className="mt-1 text-xs font-semibold text-amber-700">{item.minutesLate} phút trễ</p>}
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-1">
                      <Badge value="default" label={`${item.maxScore ?? 0} điểm`} />
                      <Badge value={item.rubricId ? "READY" : "DRAFT"} label={item.rubricId ? "Có rubric" : "Chưa rubric"} />
                      <Badge value="default" label={`${item.attachmentCount} file`} />
                    </div>
                  </Td>
                  <Td>
                    <Link to={`${item.assignmentId}/submissions?studentId=${encodeURIComponent(item.studentId)}`}>
                      <Button size="sm" variant="secondary">
                        <ClipboardCheck size={14} />
                        Chấm bài
                      </Button>
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Danh sách bài tập"
          subtitle="Mở chi tiết để xem hướng dẫn, rubric hoặc danh sách bài nộp."
        />
        {lifecycle.isError && <ErrorState error={lifecycle.error} />}
        {!courseId && <EmptyState message="Chọn khóa học để xem assignment." />}
        {isLoading && <Spinner />}
        {isError && <ErrorState error={error} />}
        {data && data.length === 0 && <EmptyState message="Không có bài tập" />}
        {data && data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Tiêu đề</Th>
                <Th>Loại</Th>
                <Th>Hạn nộp</Th>
                <Th>Cấu hình</Th>
                <Th>Trạng thái</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {data.map((assignment) => {
                const deadline = dueLabel(assignment.dueAt);
                const lifecycleAction = nextLifecycleAction(assignment.status);
                return (
                  <tr key={assignment.id} className="hover:bg-slate-50">
                    <Td>
                      <Link className="font-semibold text-brand-600 hover:underline" to={assignment.id}>
                        {assignment.title}
                      </Link>
                      <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                        {assignment.instructions ?? `Assignment ${compactId(assignment.id)}`}
                      </p>
                    </Td>
                    <Td>
                      <Badge value={assignment.assignmentType ?? "ASSIGNMENT"} />
                    </Td>
                    <Td>
                      <p className="font-medium text-slate-800">{formatDateTime(assignment.dueAt)}</p>
                      <p className={deadline.urgent ? "mt-1 text-xs font-semibold text-amber-700" : "mt-1 text-xs text-slate-500"}>
                        {deadline.label}
                      </p>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        <Badge value={assignment.rubricId ? "READY" : "DRAFT"} label={assignment.rubricId ? "Có rubric" : "Chưa rubric"} />
                        <Badge value={assignment.allowResubmission ? "ACTIVE" : "default"} label={assignment.allowResubmission ? "Nộp lại" : "1 lượt"} />
                        <Badge value="default" label={`${assignment.maxScore ?? 0} điểm`} />
                      </div>
                    </Td>
                    <Td>
                      <Badge value={assignment.status} label={assignmentStatusLabel(assignment.status)} />
                      <p className="mt-1 text-xs font-semibold text-slate-500">
                        {learnerVisibilityText(assignment.status)}
                      </p>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant={lifecycleAction.action === "archive" ? "ghost" : "secondary"}
                          disabled={lifecycle.isPending}
                          onClick={() => lifecycle.mutate({ assignmentId: assignment.id, action: lifecycleAction.action })}
                        >
                          {lifecycleAction.action === "archive" ? <Archive size={14} /> : lifecycleAction.action === "draft" ? <RotateCcw size={14} /> : <CheckCircle2 size={14} />}
                          {lifecycleAction.label}
                        </Button>
                        <Link to={assignment.id}>
                          <Button size="sm" variant="secondary">Chi tiết</Button>
                        </Link>
                        <Link to={`${assignment.id}/submissions`}>
                          <Button size="sm" variant="ghost">Bài nộp</Button>
                        </Link>
                      </div>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}

export function AssignmentDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.assignments.detail(id),
    queryFn: () => getAssignment(id),
    enabled: Boolean(id)
  });
  const courses = useQuery({
    queryKey: queryKeys.courses.list("assignment-detail"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const lifecycle = useMutation({
    mutationFn: (action: AssignmentLifecycleAction) => setAssignmentLifecycle(id, action),
    onSuccess: (assignment) => {
      qc.invalidateQueries({ queryKey: queryKeys.assignments.detail(id) });
      qc.invalidateQueries({ queryKey: queryKeys.assignments.list(assignment.courseId) });
    }
  });

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!data) return null;

  const courseRows = courses.data ?? [];
  const selectedCourse = courseRows.find((course) => course.id === data.courseId);
  const deadline = dueLabel(data.dueAt);
  const submissionTypes = (data.submissionTypes ?? "TEXT")
    .split(",")
    .map((type) => type.trim())
    .filter(Boolean);
  const operationalChecks = [
    {
      label: data.status === "PUBLISHED" ? "Đã công khai cho học viên" : "Chưa công khai",
      ready: data.status === "PUBLISHED"
    },
    {
      label: data.rubricId ? "Đã gắn rubric chấm điểm" : "Chưa có rubric",
      ready: Boolean(data.rubricId)
    },
    {
      label: data.dueAt ? "Đã đặt hạn nộp" : "Chưa đặt hạn nộp",
      ready: Boolean(data.dueAt)
    },
    {
      label: data.instructions ? "Có hướng dẫn bài làm" : "Thiếu hướng dẫn bài làm",
      ready: Boolean(data.instructions)
    }
  ];

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader
        title={data.title}
        description={`Quản lý assignment thuộc ${courseLabel(selectedCourse, data.courseId)}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={data.status === "DRAFT" || lifecycle.isPending}
              onClick={() => lifecycle.mutate("draft")}
            >
              <RotateCcw size={16} />
              Đưa về nháp
            </Button>
            <Button
              disabled={data.status === "PUBLISHED" || lifecycle.isPending}
              onClick={() => lifecycle.mutate("publish")}
            >
              <CheckCircle2 size={16} />
              Publish
            </Button>
            <Button
              variant="secondary"
              disabled={data.status === "ARCHIVED" || lifecycle.isPending}
              onClick={() => lifecycle.mutate("archive")}
            >
              <Archive size={16} />
              Archive
            </Button>
            <Link to={`/assignments/${id}/submissions`}>
              <Button>
                <UserCheck size={16} />
                Chấm bài
              </Button>
            </Link>
            <Link to={`/assignments/${id}/rubric`}>
              <Button variant="secondary">
                <Star size={16} />
                Rubric
              </Button>
            </Link>
          </div>
        }
      />

      {lifecycle.isError && (
        <div className="mb-4">
          <ErrorState error={lifecycle.error} />
        </div>
      )}

      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Card className="p-4">
          <p className="text-sm font-semibold text-slate-500">Trạng thái</p>
          <div className="mt-3">
            <Badge value={data.status} label={assignmentStatusLabel(data.status)} />
          </div>
          <p className="mt-3 text-xs font-semibold text-slate-500">
            {learnerVisibilityText(data.status)}
          </p>
          {data.status !== "PUBLISHED" && (
            <p className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-amber-700">
              <EyeOff size={13} />
              Không learner-visible
            </p>
          )}
        </Card>
        <Card className="p-4">
          <p className="text-sm font-semibold text-slate-500">Hạn nộp</p>
          <p className="mt-2 text-lg font-bold text-slate-950">{formatDateTime(data.dueAt)}</p>
          <p className={deadline.urgent ? "mt-2 text-xs font-bold text-amber-700" : "mt-2 text-xs text-slate-500"}>
            {deadline.label}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-sm font-semibold text-slate-500">Điểm tối đa</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{data.maxScore ?? "—"}</p>
          <p className="mt-2 text-xs text-slate-500">{data.rubricId ? "Đã có rubric." : "Nên tạo rubric trước khi chấm."}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm font-semibold text-slate-500">Lượt nộp</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{data.maxAttempts ?? 1}</p>
          <p className="mt-2 text-xs text-slate-500">
            {data.allowResubmission ? "Cho phép nộp lại." : "Không cho nộp lại sau khi đã gửi."}
          </p>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Card>
          <CardHeader
            title="Hướng dẫn cho học viên"
            subtitle="Nội dung này xuất hiện ở web learner trong khu nộp bài."
          />
          <div className="p-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="whitespace-pre-line text-sm leading-6 text-slate-700">
                {data.instructions || "Chưa có hướng dẫn. Hãy bổ sung yêu cầu bài làm, tiêu chí nộp và tài liệu tham khảo."}
              </p>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge value={data.assignmentType ?? "ASSIGNMENT"} />
              {submissionTypes.map((type) => (
                <Badge key={type} value={type} />
              ))}
              {data.latePenaltyPercent ? (
                <Badge value="DRAFT" label={`Phạt trễ ${data.latePenaltyPercent}%`} />
              ) : (
                <Badge value="READY" label="Chưa đặt phạt trễ" />
              )}
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Checklist vận hành"
            subtitle="Dùng trước khi thông báo bài tập cho học viên."
          />
          <div className="space-y-3 p-4">
            {operationalChecks.map((check) => (
              <div key={check.label} className="flex items-start gap-3 rounded-md border border-slate-200 bg-white p-3">
                <span className={check.ready ? "text-emerald-600" : "text-amber-600"}>
                  {check.ready ? <CheckCircle2 size={18} /> : <CalendarClock size={18} />}
                </span>
                <p className="text-sm font-semibold text-slate-800">{check.label}</p>
              </div>
            ))}
            <div className="grid gap-2 pt-2">
              <Link to={`/assignments/${id}/submissions`}>
                <Button className="w-full">
                  <UserCheck size={16} />
                  Mở hàng chờ chấm
                </Button>
              </Link>
              <Link to={`/assignments/${id}/rubric`}>
                <Button className="w-full" variant="secondary">
                  <Star size={16} />
                  Thiết lập rubric
                </Button>
              </Link>
              <Link to={`/assignments?courseId=${data.courseId}`}>
                <Button className="w-full" variant="ghost">
                  Về danh sách cùng khóa
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

export function AssignmentCreatePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [searchParams] = useSearchParams();
  const requestedCourseId = searchParams.get("courseId") ?? "";
  const courses = useQuery({
    queryKey: queryKeys.courses.list("assignment-create"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const [form, setForm] = useState({
    courseId: requestedCourseId,
    title: "",
    assignmentType: "ONLINE_TEXT",
    instructions: "",
    dueAt: "",
    maxScore: 100,
    submissionTypes: "TEXT"
  });
  const courseRows = courses.data ?? [];
  const selectedCourse = courseRows.find((course) => course.id === form.courseId);
  const create = useMutation({
    mutationFn: () =>
      createAssignment({
        courseId: form.courseId,
        title: form.title,
        assignmentType: form.assignmentType,
        instructions: form.instructions || undefined,
        dueAt: dateTimeLocalToIso(form.dueAt),
        maxScore: form.maxScore,
        submissionTypes: form.submissionTypes
      }),
    onSuccess: (a) => {
      qc.invalidateQueries({ queryKey: ["assignments"] });
      navigate(`../${a.id}`);
    }
  });

  return (
    <div>
      <PageHeader
        title="Tạo bài tập"
        description="Thiết lập assignment đủ thông tin để học viên nộp bài và gradebook nhận điểm."
      />
      <Card className="max-w-5xl">
        <CardHeader
          title="Thông tin bài tập"
          subtitle={selectedCourse ? selectedCourse.title : "Chọn khóa học trước khi tạo assignment."}
        />
        <form
          className="grid gap-4 p-4 lg:grid-cols-[1.1fr_0.9fr]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="space-y-4">
            <FormField label="Khóa học" htmlFor="a-course">
              <Select
                id="a-course"
                value={form.courseId}
                onChange={(e) => setForm({ ...form, courseId: e.target.value })}
                required
              >
                <option value="">Chọn khóa học</option>
                {courseRows.map((course) => (
                  <option key={course.id} value={course.id}>
                    {[course.code, course.title].filter(Boolean).join(" · ")}
                  </option>
                ))}
                {form.courseId && !selectedCourse && <option value={form.courseId}>Course {compactId(form.courseId)}</option>}
              </Select>
            </FormField>
            {courses.isError && <ErrorState error={courses.error} />}
            <FormField label="Tiêu đề" htmlFor="a-title">
              <Input
                id="a-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </FormField>
            <FormField label="Hướng dẫn" htmlFor="a-desc">
              <Textarea
                id="a-desc"
                value={form.instructions}
                onChange={(e) => setForm({ ...form, instructions: e.target.value })}
                placeholder="Yêu cầu bài làm, tiêu chí nộp và tài liệu cần đính kèm."
              />
            </FormField>
          </div>

          <div className="space-y-4">
            <Notice tone="warning" title="Assignment mới sẽ là nháp">
              Learner chưa nhìn thấy assignment draft. Publish assignment trước khi gắn vào curriculum đã sẵn sàng cho learner.
            </Notice>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Loại bài tập" htmlFor="a-type">
                <Select
                  id="a-type"
                  value={form.assignmentType}
                  onChange={(e) => setForm({ ...form, assignmentType: e.target.value })}
                  required
                >
                  {ASSIGNMENT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Điểm tối đa" htmlFor="a-max">
                <Input
                  id="a-max"
                  type="number"
                  min="1"
                  value={form.maxScore}
                  onChange={(e) => setForm({ ...form, maxScore: Number(e.target.value) })}
                  required
                />
              </FormField>
            </div>
            <FormField label="Hạn nộp" htmlFor="a-due">
              <Input
                id="a-due"
                type="datetime-local"
                value={toDateTimeLocalValue(form.dueAt)}
                onChange={(e) => setForm({ ...form, dueAt: e.target.value })}
                required
              />
            </FormField>
            <FormField label="Kiểu nộp bài" htmlFor="a-submission-types">
              <Input
                id="a-submission-types"
                value={form.submissionTypes}
                onChange={(e) => setForm({ ...form, submissionTypes: e.target.value })}
                placeholder="TEXT,URL,FILE"
              />
            </FormField>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
              <p className="font-semibold text-slate-900">Preview cấu hình</p>
              <div className="mt-3 grid gap-2 text-slate-600">
                <span className="inline-flex items-center gap-2">
                  <FileText size={15} />
                  {form.assignmentType} · {form.maxScore || 0} điểm
                </span>
                <span className="inline-flex items-center gap-2">
                  <CalendarClock size={15} />
                  {form.dueAt ? formatDateTime(dateTimeLocalToIso(form.dueAt)) : "Chưa chọn hạn nộp"}
                </span>
                <span className="inline-flex items-center gap-2">
                  <Star size={15} />
                  {form.submissionTypes || "TEXT"}
                </span>
              </div>
            </div>
            {create.isError && <ErrorState error={create.error} />}
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={create.isPending || !form.courseId || !form.title || !form.dueAt}>
                {create.isPending ? "Đang tạo" : "Tạo bài tập"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate("..")}>
                Hủy
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  );
}

export function SubmissionsPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedStudentId = searchParams.get("studentId") ?? "";
  const [studentId, setStudentId] = useState(requestedStudentId);
  const [searchedStudentId, setSearchedStudentId] = useState(requestedStudentId);
  const { learnerUsers, roleQueriesLoading, userById, usersQuery } = useLearnerUsers();
  const assignment = useQuery({
    queryKey: queryKeys.assignments.detail(id),
    queryFn: () => getAssignment(id),
    enabled: Boolean(id)
  });
  const courses = useQuery({
    queryKey: queryKeys.courses.list("assignment-submissions"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.assignments.submissions(id, searchedStudentId),
    queryFn: () => listSubmissions(id, searchedStudentId),
    enabled: Boolean(id && searchedStudentId)
  });
  const [gradeForm, setGradeForm] = useState<Record<string, { score: string; feedback: string }>>({});
  const grade = useMutation({
    mutationFn: ({ submissionId, form }: { submissionId: string; form: { score: string; feedback: string } }) =>
      gradeSubmission(submissionId, { rawScore: Number(form.score), feedback: form.feedback }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.assignments.submissions(id, searchedStudentId) });
      qc.invalidateQueries({ queryKey: queryKeys.assignments.gradingQueue(assignment.data?.courseId ?? "") });
    }
  });

  const getForm = (submissionId: string) =>
    gradeForm[submissionId] ?? { score: "", feedback: "" };
  const setForm = (submissionId: string, patch: Partial<{ score: string; feedback: string }>) =>
    setGradeForm((prev) => ({ ...prev, [submissionId]: { ...getForm(submissionId), ...patch } }));
  const submissions = data ?? [];
  const pendingCount = submissions.filter((submission) => submission.status !== "GRADED").length;
  const latestSubmission = submissions[0];
  const selectedLearner = userById.get(studentId || searchedStudentId);
  const searchedLearner = userById.get(searchedStudentId);
  const learnerRows = useMemo(() => {
    if (!selectedLearner) return learnerUsers;
    return learnerUsers.some((user) => String(user.id) === String(selectedLearner.id))
      ? learnerUsers
      : [selectedLearner, ...learnerUsers];
  }, [learnerUsers, selectedLearner]);
  const quickLearners = learnerRows.slice(0, 6);
  const learnerHint =
    usersQuery.isLoading || roleQueriesLoading
      ? "Đang tải danh sách learner..."
      : usersQuery.isError
        ? "Không tải được danh sách learner."
        : `${learnerRows.length} learner khả dụng`;
  const courseRows = courses.data ?? [];
  const selectedCourse = assignment.data
    ? courseRows.find((course) => course.id === assignment.data?.courseId)
    : undefined;

  useEffect(() => {
    setStudentId(requestedStudentId);
    setSearchedStudentId(requestedStudentId);
  }, [requestedStudentId]);

  function searchStudent(nextStudentId = studentId) {
    const trimmed = nextStudentId.trim();
    setStudentId(trimmed);
    setSearchedStudentId(trimmed);
    setSearchParams(trimmed ? { studentId: trimmed } : {}, { replace: true });
  }

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader
        title="Bài nộp"
        description={
          assignment.data
            ? `${assignment.data.title} · ${courseLabel(selectedCourse, assignment.data.courseId)}`
            : `Assignment ${compactId(id)}`
        }
      />
      <div className="mb-4 grid gap-3 md:grid-cols-3">
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-500">Học viên</p>
              <p className="mt-2 text-2xl font-bold text-slate-950">
                {searchedLearner?.fullName ?? (searchedStudentId ? `Học viên ${compactId(searchedStudentId)}` : "—")}
              </p>
            </div>
            <span className="grid size-10 place-items-center rounded-md bg-brand-50 text-brand-700">
              <UserCheck size={18} />
            </span>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-500">Số lượt nộp</p>
              <p className="mt-2 text-2xl font-bold text-slate-950">{searchedStudentId ? submissions.length : "—"}</p>
            </div>
            <span className="grid size-10 place-items-center rounded-md bg-sky-50 text-sky-700">
              <FileText size={18} />
            </span>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-500">Cần chấm</p>
              <p className="mt-2 text-2xl font-bold text-slate-950">{searchedStudentId ? pendingCount : "—"}</p>
            </div>
            <span className="grid size-10 place-items-center rounded-md bg-amber-50 text-amber-700">
              <ClipboardCheck size={18} />
            </span>
          </div>
        </Card>
      </div>
      <Card className="mb-4">
        <CardHeader
          title="Tra cứu học viên"
          subtitle="Chọn learner để xem lượt nộp, trạng thái và nhập điểm."
        />
        <form
          className="grid gap-3 p-4 md:grid-cols-[1fr_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            searchStudent();
          }}
        >
          <FormField label="Học viên" htmlFor="sub-student" hint={learnerHint}>
            <Select
              id="sub-student"
              value={studentId}
              onChange={(e) => searchStudent(e.target.value)}
              disabled={usersQuery.isLoading && learnerRows.length === 0}
              required
            >
              <option value="">Chọn học viên</option>
              {learnerRows.map((user) => (
                <option key={user.id} value={String(user.id)}>
                  {adminUserLabel(user)}
                </option>
              ))}
              {studentId && !selectedLearner && (
                <option value={studentId}>Học viên {compactId(studentId)}</option>
              )}
            </Select>
          </FormField>
          <div className="flex items-end">
            <Button type="submit">
              <Search size={16} />
              Xem bài nộp
            </Button>
          </div>
          {quickLearners.length > 0 && (
            <div className="flex flex-wrap gap-2 md:col-span-2">
              {quickLearners.map((user) => {
                const id = String(user.id);
                return (
                  <Button
                    key={id}
                    type="button"
                    variant={searchedStudentId === id ? "primary" : "secondary"}
                    size="sm"
                    onClick={() => searchStudent(id)}
                  >
                    {(user.fullName || user.email)} · {id}
                  </Button>
                );
              })}
            </div>
          )}
          {usersQuery.isError && <ErrorState error={usersQuery.error} />}
        </form>
      </Card>
      {searchedStudentId && isLoading && <Spinner />}
      {isError && <ErrorState error={error} />}
      {data && data.length === 0 && <EmptyState message="Chưa có bài nộp" />}
      {data && data.length > 0 && (
        <Card>
          <Table>
            <thead>
              <tr>
                <Th>Học viên</Th>
                <Th>Lần thử</Th>
                <Th>Nộp lúc</Th>
                <Th>Trạng thái</Th>
                <Th>Điểm cuối</Th>
                <Th>Trễ</Th>
                <Th>Chấm điểm</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => {
                const f = getForm(s.id);
                const isLatest = latestSubmission?.id === s.id;
                const learner = userById.get(s.studentId);
                return (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <Td>
                      <p className="font-semibold text-slate-900">
                        {learner?.fullName ?? `Học viên ${compactId(s.studentId)}`}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {learner?.email ?? `ID ${compactId(s.studentId)}`}
                      </p>
                      {isLatest && <p className="mt-1 text-xs font-semibold text-brand-600">Lượt mới nhất</p>}
                    </Td>
                    <Td>{s.attemptNo}</Td>
                    <Td>{formatDateTime(s.submittedAt)}</Td>
                    <Td><Badge value={s.status} /></Td>
                    <Td>{s.finalScore ?? "—"}</Td>
                    <Td>{s.isLate ? <Badge value="DRAFT" label={`${s.minutesLate ?? 0} phút`} /> : "—"}</Td>
                    <Td>
                      <form
                        className="grid min-w-[260px] gap-2"
                        onSubmit={(e: FormEvent) => {
                          e.preventDefault();
                          grade.mutate({ submissionId: s.id, form: f });
                        }}
                      >
                        <Input
                          type="number"
                          placeholder="Điểm"
                          value={f.score}
                          onChange={(e) => setForm(s.id, { score: e.target.value })}
                          required
                        />
                        <Input
                          placeholder="Nhận xét"
                          value={f.feedback}
                          onChange={(e) => setForm(s.id, { feedback: e.target.value })}
                        />
                        <Button type="submit" disabled={grade.isPending || !f.score}>
                          {grade.isPending ? "Đang lưu" : "Lưu điểm"}
                        </Button>
                        {s.feedback && <p className="text-xs text-slate-500">Feedback cũ: {s.feedback}</p>}
                      </form>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </Card>
      )}
    </div>
  );
}

export function RubricPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.assignments.rubric(id),
    queryFn: () => getRubric(id),
    enabled: Boolean(id)
  });
  const [form, setForm] = useState({
    title: "",
    maxScore: "",
    c1Title: "",
    c1Desc: "",
    c1Max: "",
    c2Title: "",
    c2Desc: "",
    c2Max: "",
    c3Title: "",
    c3Desc: "",
    c3Max: ""
  });
  const upsert = useMutation({
    mutationFn: () => {
      const criteria = [
        { name: form.c1Title, description: form.c1Desc, maxPoints: Number(form.c1Max) },
        { name: form.c2Title, description: form.c2Desc, maxPoints: Number(form.c2Max) },
        { name: form.c3Title, description: form.c3Desc, maxPoints: Number(form.c3Max) }
      ].filter((c) => c.name.trim());
      return upsertRubric(id, { title: form.title, maxScore: Number(form.maxScore), criteria });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.assignments.rubric(id) })
  });

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader title="Rubric" description={`Assignment ${compactId(id)}`} />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader title="Rubric hiện tại" />
          {isLoading && <Spinner />}
          {isError && <ErrorState error={error} />}
          {data && (
            <div className="p-4 space-y-3">
              <p className="text-sm font-medium">{data.title} — Điểm tối đa: {data.maxScore}</p>
              <Table>
                <thead>
                  <tr>
                    <Th>Tiêu chí</Th>
                    <Th>Mô tả</Th>
                    <Th>Điểm tối đa</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.criteria.map((c) => (
                    <tr key={c.id}>
                      <Td>{c.name}</Td>
                      <Td>{c.description ?? "—"}</Td>
                      <Td>{c.maxPoints}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          )}
          {!data && !isLoading && !isError && <EmptyState message="Chưa có rubric" />}
        </Card>
        <Card>
          <CardHeader title="Tạo / cập nhật rubric" />
          <form
            className="space-y-3 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              upsert.mutate();
            }}
          >
            <FormField label="Tiêu đề rubric" htmlFor="r-title">
              <Input id="r-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </FormField>
            <FormField label="Điểm tối đa" htmlFor="r-max">
              <Input id="r-max" type="number" value={form.maxScore} onChange={(e) => setForm({ ...form, maxScore: e.target.value })} required />
            </FormField>
            <p className="text-xs font-medium text-slate-500 uppercase">Tiêu chí 1</p>
            <FormField label="Tên" htmlFor="r-c1t">
              <Input id="r-c1t" value={form.c1Title} onChange={(e) => setForm({ ...form, c1Title: e.target.value })} />
            </FormField>
            <FormField label="Mô tả" htmlFor="r-c1d">
              <Input id="r-c1d" value={form.c1Desc} onChange={(e) => setForm({ ...form, c1Desc: e.target.value })} />
            </FormField>
            <FormField label="Điểm tối đa" htmlFor="r-c1m">
              <Input id="r-c1m" type="number" value={form.c1Max} onChange={(e) => setForm({ ...form, c1Max: e.target.value })} />
            </FormField>
            <p className="text-xs font-medium text-slate-500 uppercase">Tiêu chí 2</p>
            <FormField label="Tên" htmlFor="r-c2t">
              <Input id="r-c2t" value={form.c2Title} onChange={(e) => setForm({ ...form, c2Title: e.target.value })} />
            </FormField>
            <FormField label="Mô tả" htmlFor="r-c2d">
              <Input id="r-c2d" value={form.c2Desc} onChange={(e) => setForm({ ...form, c2Desc: e.target.value })} />
            </FormField>
            <FormField label="Điểm tối đa" htmlFor="r-c2m">
              <Input id="r-c2m" type="number" value={form.c2Max} onChange={(e) => setForm({ ...form, c2Max: e.target.value })} />
            </FormField>
            <p className="text-xs font-medium text-slate-500 uppercase">Tiêu chí 3</p>
            <FormField label="Tên" htmlFor="r-c3t">
              <Input id="r-c3t" value={form.c3Title} onChange={(e) => setForm({ ...form, c3Title: e.target.value })} />
            </FormField>
            <FormField label="Mô tả" htmlFor="r-c3d">
              <Input id="r-c3d" value={form.c3Desc} onChange={(e) => setForm({ ...form, c3Desc: e.target.value })} />
            </FormField>
            <FormField label="Điểm tối đa" htmlFor="r-c3m">
              <Input id="r-c3m" type="number" value={form.c3Max} onChange={(e) => setForm({ ...form, c3Max: e.target.value })} />
            </FormField>
            {upsert.isError && <ErrorState error={upsert.error} />}
            {upsert.isSuccess && <p className="text-sm text-emerald-600">Đã lưu rubric</p>}
            <Button type="submit" disabled={upsert.isPending}>
              {upsert.isPending ? "Đang lưu" : "Lưu rubric"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
