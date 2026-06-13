import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Check, MessageSquarePlus, MessagesSquare } from "lucide-react";
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
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Textarea,
  Th
} from "@/shared/ui";
import { fallbackCourses, listCourses } from "../courses/api";
import { acceptComment, addComment, createThread, getThread, listThreads } from "./api";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function courseLabel(course?: { code?: string; title?: string }, fallbackId?: string) {
  if (course) return [course.code, course.title].filter(Boolean).join(" · ");
  return fallbackId ? `Course ${compactId(fallbackId)}` : "Tất cả khóa học";
}

export function DiscussionListPage() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get("courseId") ?? "";
  const [courseId, setCourseId] = useState(requestedCourseId);
  const courses = useQuery({
    queryKey: queryKeys.courses.list("discussions"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.discussions.threads(courseId),
    queryFn: () => listThreads(courseId || undefined)
  });
  const [form, setForm] = useState({ courseId: requestedCourseId, title: "", body: "" });
  const create = useMutation({
    mutationFn: () => createThread(form),
    onSuccess: () => {
      setForm({ courseId: courseId || form.courseId, title: "", body: "" });
      qc.invalidateQueries({ queryKey: ["discussions"] });
    }
  });
  const courseRows = courses.data?.length ? courses.data : fallbackCourses;
  const courseById = useMemo(() => new Map(courseRows.map((course) => [course.id, course])), [courseRows]);
  const selectedCourse = courseById.get(courseId);

  useEffect(() => {
    setCourseId(requestedCourseId);
    if (requestedCourseId) {
      setForm((current) => ({ ...current, courseId: requestedCourseId }));
    }
  }, [requestedCourseId]);

  function changeCourse(value: string) {
    setCourseId(value);
    setForm((current) => ({ ...current, courseId: value }));
    setSearchParams(value ? { courseId: value } : {}, { replace: true });
  }

  return (
    <div>
      <PageHeader title="Thảo luận" description="Quản lý chủ đề theo khóa học và kiểm duyệt câu trả lời." />
      <Card className="mb-4">
        <CardHeader
          title="Bộ lọc khóa học"
          subtitle="Chọn course để xem và tạo chủ đề trong đúng ngữ cảnh vận hành."
        />
        <div className="grid gap-4 p-4 lg:grid-cols-[1fr_1fr_auto]">
          <FormField label="Khóa học" htmlFor="discussion-course">
            <Select id="discussion-course" value={courseId} onChange={(e) => changeCourse(e.target.value)}>
              <option value="">Tất cả khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
              {courseId && !selectedCourse && <option value={courseId}>Course {compactId(courseId)}</option>}
            </Select>
          </FormField>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            <p className="font-semibold text-slate-900">{courseLabel(selectedCourse, courseId)}</p>
            <p className="mt-1 line-clamp-2">
              {selectedCourse?.summary ?? "Dùng bộ lọc này để đọc thread và tạo chủ đề đúng khóa học."}
            </p>
          </div>
          <div className="flex items-end">
            <Button type="button" variant="secondary" onClick={() => setForm((current) => ({ ...current, courseId }))} disabled={!courseId}>
              <MessageSquarePlus size={16} />
              Dùng khóa này
            </Button>
          </div>
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader
            title="Chủ đề"
            subtitle={courseId ? courseLabel(selectedCourse, courseId) : "Đang xem tất cả khóa học"}
            actions={
              <span className="inline-flex items-center gap-2 rounded-md bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-700">
                <MessagesSquare size={16} />
                {data?.length ?? 0}
              </span>
            }
          />
          {isLoading && <Spinner />}
          {isError && <ErrorState error={error} />}
          {data && data.length === 0 && <EmptyState message="Không có chủ đề" />}
          {data && data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Tiêu đề</Th>
                  <Th>Khóa học</Th>
                  <Th>Trạng thái</Th>
                </tr>
              </thead>
              <tbody>
                {data.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <Td>
                      <Link className="font-medium text-brand-600 hover:underline" to={t.id}>
                        {t.title}
                      </Link>
                      <p className="mt-1 text-xs text-slate-500">Thread {compactId(t.id)}</p>
                    </Td>
                    <Td>
                      <p className="font-semibold text-slate-900">{courseLabel(courseById.get(t.courseId ?? ""), t.courseId)}</p>
                      {t.courseId && <p className="mt-1 text-xs text-slate-500">ID {compactId(t.courseId)}</p>}
                    </Td>
                    <Td>
                      <Badge value={t.status} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Tạo chủ đề" subtitle={courseLabel(courseById.get(form.courseId), form.courseId)} />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <FormField label="Khóa học" htmlFor="d-course">
              <Select id="d-course" value={form.courseId} onChange={(e) => setForm({ ...form, courseId: e.target.value })} required>
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
            <FormField label="Tiêu đề" htmlFor="d-title">
              <Input id="d-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </FormField>
            <FormField label="Nội dung" htmlFor="d-body">
              <Textarea id="d-body" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required />
            </FormField>
            {create.isError && <ErrorState error={create.error} />}
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Đang tạo" : "Tạo chủ đề"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}

export function DiscussionThreadPage() {
  const { threadId = "" } = useParams();
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.discussions.thread(threadId),
    queryFn: () => getThread(threadId),
    enabled: Boolean(threadId)
  });
  const courses = useQuery({
    queryKey: queryKeys.courses.list("discussion-detail"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: queryKeys.discussions.thread(threadId) });
  const [body, setBody] = useState("");
  const comment = useMutation({
    mutationFn: () => addComment(threadId, { body }),
    onSuccess: () => {
      setBody("");
      invalidate();
    }
  });
  const accept = useMutation({
    mutationFn: (commentId: string) => acceptComment(threadId, commentId),
    onSuccess: invalidate
  });

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!data) return null;

  const courseRows = courses.data?.length ? courses.data : fallbackCourses;
  const selectedCourse = courseRows.find((course) => course.id === data.courseId);

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader title={data.title} description={data.courseId ? courseLabel(selectedCourse, data.courseId) : undefined} />
      <Card className="mb-4">
        <CardHeader title="Trả lời" />
        <div className="divide-y divide-slate-100">
          {(data.comments ?? []).length === 0 && <EmptyState message="Chưa có trả lời" />}
          {(data.comments ?? []).map((c) => (
            <div key={c.id} className="flex items-start justify-between gap-4 p-4">
              <div>
                <p className="text-sm text-slate-700">{c.body}</p>
                <p className="mt-1 text-xs text-slate-400">{c.authorId ? `Tác giả ${compactId(c.authorId)}` : "—"}</p>
              </div>
              {c.accepted ? (
                <Badge value="ACCEPTED" />
              ) : (
                <Button size="sm" variant="secondary" disabled={accept.isPending} onClick={() => accept.mutate(c.id)}>
                  <Check size={14} /> Chấp nhận
                </Button>
              )}
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <CardHeader title="Thêm trả lời" />
        <form
          className="space-y-4 p-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            comment.mutate();
          }}
        >
          <FormField label="Nội dung" htmlFor="c-body">
            <Textarea id="c-body" value={body} onChange={(e) => setBody(e.target.value)} required />
          </FormField>
          {comment.isError && <ErrorState error={comment.error} />}
          <Button type="submit" disabled={comment.isPending}>
            {comment.isPending ? "Đang gửi" : "Gửi"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
