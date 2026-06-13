import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import {
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  FilePenLine,
  Layers3,
  Plus,
  Rocket,
  Search,
  Send,
  Sparkles
} from "lucide-react";
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
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th
} from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import { listCourseReviewQueue, listCourses } from "../api";
import type { Course } from "../types";

const statusFilters = [
  { value: "ALL", label: "Tất cả" },
  { value: "DRAFT", label: "Đang biên soạn" },
  { value: "PUBLISHED", label: "Đã công khai" },
  { value: "ARCHIVED", label: "Lưu trữ" }
];

const templateLinks = [
  {
    title: "Khóa backend production",
    detail: "Spring Boot, microservices, outbox, bảo mật.",
    href: "new?template=backend"
  },
  {
    title: "Khóa sản phẩm AI",
    detail: "Evaluation, guardrails, checklist ra mắt.",
    href: "new?template=ai"
  },
  {
    title: "Khóa thiết kế học tập",
    detail: "Storyboard, outcome map, vòng lặp đánh giá.",
    href: "new?template=learning"
  }
];

const authoringFlow = [
  { label: "Tạo draft", icon: FilePenLine },
  { label: "Thêm chương/bài", icon: Layers3 },
  { label: "Gửi duyệt", icon: Send },
  { label: "Publish", icon: Rocket }
];

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    DRAFT: "Đang biên soạn",
    PUBLISHED: "Đã công khai",
    ARCHIVED: "Lưu trữ"
  };
  return labels[status ?? ""] ?? status ?? "—";
}

function compactId(value?: string) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function formatDateTime(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function courseMatches(course: Course, keyword: string, status: string) {
  const normalized = keyword.trim().toLowerCase();
  const statusOk = status === "ALL" || course.status === status;
  if (!statusOk) return false;
  if (!normalized) return true;
  return [course.code, course.title, course.slug, course.summary, course.id]
    .filter(Boolean)
    .some((value) => value.toLowerCase().includes(normalized));
}

function Metric({
  label,
  value,
  detail,
  icon: Icon,
  tone = "brand"
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof BookOpenCheck;
  tone?: "brand" | "emerald" | "amber" | "sky";
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    sky: "bg-sky-50 text-sky-700"
  }[tone];

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-md", toneClass)}>
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-3 text-sm leading-5 text-slate-500">{detail}</p>
    </Card>
  );
}

export function CourseAuthoringPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const courses = useQuery({
    queryKey: queryKeys.courses.list("authoring-all"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const reviewQueue = useQuery({
    queryKey: queryKeys.authoring.reviewQueue,
    queryFn: listCourseReviewQueue,
    retry: 1,
    staleTime: 60_000
  });

  const rows = courses.data ?? [];
  const queueRows = reviewQueue.data ?? [];
  const filteredRows = useMemo(
    () => rows.filter((course) => courseMatches(course, search, statusFilter)),
    [rows, search, statusFilter]
  );
  const draftCount = rows.filter((course) => course.status === "DRAFT").length;
  const publishedCount = rows.filter((course) => course.status === "PUBLISHED").length;
  const archivedCount = rows.filter((course) => course.status === "ARCHIVED").length;

  return (
    <div>
      <PageHeader
        title="Biên soạn khóa học"
        description="Tạo draft, xây chương học, gắn video/tài liệu, gửi duyệt và publish khóa học từ một luồng làm việc."
        actions={
          <Link to="new">
            <Button>
              <Plus size={16} />
              Tạo draft mới
            </Button>
          </Link>
        }
      />

      <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <Metric
          label="Tổng khóa"
          value={String(rows.length)}
          detail="Tất cả khóa trong catalog admin."
          icon={BookOpenCheck}
        />
        <Metric
          label="Đang biên soạn"
          value={String(draftCount)}
          detail="Cần thêm chương, bài học hoặc gửi duyệt."
          icon={FilePenLine}
          tone="amber"
        />
        <Metric
          label="Chờ duyệt"
          value={String(queueRows.length)}
          detail="Course IN_REVIEW cần reviewer xử lý."
          icon={ClipboardCheck}
          tone="sky"
        />
        <Metric
          label="Đã công khai"
          value={String(publishedCount)}
          detail="Learner có thể truy cập khi ghi danh."
          icon={CheckCircle2}
          tone="emerald"
        />
        <Metric
          label="Lưu trữ"
          value={String(archivedCount)}
          detail="Không còn xuất hiện trong catalog học viên."
          icon={Rocket}
          tone="sky"
        />
      </div>

      <Card className="mb-4">
        <CardHeader
          title={
            <span className="inline-flex items-center gap-2">
              <ClipboardCheck size={18} className="text-brand-700" />
              Review queue
            </span>
          }
          subtitle="Course đang IN_REVIEW, kèm owner, version và dung lượng nội dung để reviewer mở đúng việc."
          actions={<Badge value="IN_REVIEW" label={`${queueRows.length} chờ duyệt`} />}
        />
        {reviewQueue.isLoading && <Spinner />}
        {reviewQueue.isError && <ErrorState error={reviewQueue.error} />}
        {!reviewQueue.isLoading && !reviewQueue.isError && queueRows.length === 0 && (
          <EmptyState message="Không có course nào đang chờ duyệt." />
        )}
        {!reviewQueue.isLoading && !reviewQueue.isError && queueRows.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Course</Th>
                <Th>Owner</Th>
                <Th>Nội dung</Th>
                <Th>Gửi duyệt</Th>
                <Th>Action</Th>
              </tr>
            </thead>
            <tbody>
              {queueRows.map((course) => (
                <tr key={course.courseId} className="hover:bg-slate-50">
                  <Td>
                    <Link className="font-semibold text-brand-600 hover:underline" to={`${course.courseId}/draft`}>
                      {course.title}
                    </Link>
                    <p className="mt-1 text-xs text-slate-500">
                      {[course.slug, `v${course.currentVersionNo}`, `ID ${compactId(course.courseId)}`].join(" · ")}
                    </p>
                  </Td>
                  <Td>
                    <span className="font-medium text-slate-700">{course.ownerId}</span>
                    <p className="mt-1 text-xs text-slate-500">Dept {compactId(course.departmentId)}</p>
                  </Td>
                  <Td>
                    <span className="font-medium text-slate-700">{course.moduleCount} chương</span>
                    <p className="mt-1 text-xs text-slate-500">{course.itemCount} item</p>
                  </Td>
                  <Td>
                    <span className="font-medium text-slate-700">{formatDateTime(course.submittedAt)}</span>
                    <p className="mt-1 text-xs text-slate-500">By {course.submittedBy ?? course.lastAuthoredBy ?? "—"}</p>
                  </Td>
                  <Td>
                    <Link to={`${course.courseId}/draft`}>
                      <Button size="sm" variant="secondary">
                        <ClipboardCheck size={15} />
                        Review
                      </Button>
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <div className="mb-4 grid gap-4 xl:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader
            title="Bộ lọc biên soạn"
            subtitle="Tìm nhanh course để mở editor, rubric, bài thi hoặc assignment liên quan."
          />
          <div className="grid gap-3 p-4 md:grid-cols-[1fr_220px]">
            <FormField label="Tìm kiếm" htmlFor="authoring-search">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-slate-400" />
                <Input
                  id="authoring-search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  className="pl-9"
                  placeholder="Tên, mã hoặc slug"
                />
              </div>
            </FormField>
            <FormField label="Trạng thái" htmlFor="authoring-status">
              <Select
                id="authoring-status"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                {statusFilters.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
        </Card>

        <Card>
          <CardHeader title="Tạo nhanh từ template" />
          <div className="space-y-2 p-4">
            {templateLinks.map((template) => (
              <Link
                key={template.href}
                to={template.href}
                className="flex gap-3 rounded-md border border-slate-200 p-3 transition hover:border-brand-200 hover:bg-brand-50"
              >
                <span className="grid size-9 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
                  <Sparkles size={16} />
                </span>
                <span>
                  <span className="block text-sm font-bold text-slate-900">{template.title}</span>
                  <span className="mt-1 block text-xs leading-5 text-slate-500">{template.detail}</span>
                </span>
              </Link>
            ))}
          </div>
        </Card>
      </div>

      <Card className="mb-4">
        <CardHeader title="Luồng xuất bản" subtitle="Mỗi course nên đi đủ các bước trước khi mở cho learner." />
        <div className="grid gap-3 p-4 md:grid-cols-4">
          {authoringFlow.map(({ label, icon: Icon }, index) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="grid size-9 place-items-center rounded-md bg-white text-brand-700 shadow-sm">
                <Icon size={16} />
              </span>
              <p className="mt-3 text-sm font-bold text-slate-900">
                {index + 1}. {label}
              </p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title="Danh sách khóa học" subtitle={`${filteredRows.length}/${rows.length} khóa đang hiển thị`} />
        {courses.isLoading && <Spinner />}
        {courses.isError && <ErrorState error={courses.error} />}
        {!courses.isLoading && !courses.isError && filteredRows.length === 0 && (
          <EmptyState message="Không tìm thấy khóa học phù hợp." />
        )}
        {!courses.isLoading && !courses.isError && filteredRows.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Khóa học</Th>
                <Th>Cấp độ</Th>
                <Th>Trạng thái</Th>
                <Th>Điều hướng</Th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((course) => (
                <tr key={course.id} className="hover:bg-slate-50">
                  <Td>
                    <Link className="font-semibold text-brand-600 hover:underline" to={`${course.id}/draft`}>
                      {course.title}
                    </Link>
                    <p className="mt-1 text-xs text-slate-500">
                      {[course.code, course.slug, `ID ${compactId(course.id)}`].filter(Boolean).join(" · ")}
                    </p>
                  </Td>
                  <Td>{course.level || "—"}</Td>
                  <Td>
                    <Badge value={course.status} label={statusLabel(course.status)} />
                  </Td>
                  <Td>
                    <div className="flex flex-wrap gap-2">
                      <Link to={`${course.id}/draft`}>
                        <Button size="sm" variant="secondary">Editor</Button>
                      </Link>
                      <Link to={`/course-modules?courseId=${course.id}`}>
                        <Button size="sm" variant="ghost">Module</Button>
                      </Link>
                      <Link to={`/quizzes?courseId=${course.id}`}>
                        <Button size="sm" variant="ghost">Bài thi</Button>
                      </Link>
                      <Link to={`/assignments?courseId=${course.id}`}>
                        <Button size="sm" variant="ghost">Bài tập</Button>
                      </Link>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}
