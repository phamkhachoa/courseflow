import { FormEvent, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, Link2, Play, Square, UserPlus, Video, UsersRound } from "lucide-react";
import { listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
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
import {
  createLiveSession,
  endLiveSession,
  getLiveSession,
  getJoinInfo,
  listLiveSessions,
  registerToSession,
  startLiveSession,
  type Registration
} from "./api";

type LiveSessionForm = {
  courseId: string;
  title: string;
  hostId: string;
  scheduledStart: string;
  scheduledEnd: string;
  capacity: string;
};

function compactId(value?: string) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function courseLabel(course?: Course, fallbackId?: string) {
  if (!course) return fallbackId ? `Khóa ${compactId(fallbackId)}` : "Chọn khóa học";
  return course.code ? `${course.code} · ${course.title}` : course.title;
}

function formatDateTime(value?: string) {
  if (!value) return "Chưa đặt lịch";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("vi-VN");
}

function toApiDateTime(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (trimmed.endsWith("Z")) return trimmed;
  const date = new Date(trimmed);
  return Number.isNaN(date.getTime()) ? trimmed : date.toISOString();
}

function emptyForm(): LiveSessionForm {
  return {
    courseId: "",
    title: "",
    hostId: "",
    scheduledStart: "",
    scheduledEnd: "",
    capacity: ""
  };
}

function Metric({
  icon,
  label,
  value,
  detail
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <span className="grid size-10 place-items-center rounded-md bg-brand-50 text-brand-700">
          {icon}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

function useCoursePicker() {
  const courses = useQuery({
    queryKey: queryKeys.courses.list("live-session-picker"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const courseById = useMemo(() => {
    const map = new Map<string, Course>();
    for (const course of courses.data ?? []) map.set(course.id, course);
    return map;
  }, [courses.data]);
  return { courseById, courses, courseRows: courses.data ?? [] };
}

export function LiveSessionsPage() {
  const qc = useQueryClient();
  const { courseById, courseRows, courses } = useCoursePicker();
  const { allUsers, staffUsers, userById, usersQuery, roleQueriesLoading } = useLearnerUsers();
  const hostUsers = staffUsers.length ? staffUsers : allUsers;
  const [courseFilter, setCourseFilter] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [form, setForm] = useState<LiveSessionForm>(emptyForm);

  const sessions = useQuery({
    queryKey: queryKeys.liveSessions.list(submitted),
    queryFn: () => listLiveSessions(submitted || undefined)
  });

  const invalidateList = () => qc.invalidateQueries({ queryKey: queryKeys.liveSessions.list(submitted) });

  const create = useMutation({
    mutationFn: () =>
      createLiveSession({
        courseId: form.courseId,
        title: form.title.trim(),
        hostId: form.hostId,
        scheduledStart: toApiDateTime(form.scheduledStart),
        scheduledEnd: form.scheduledEnd ? toApiDateTime(form.scheduledEnd) : undefined,
        capacity: form.capacity ? Number(form.capacity) : undefined
      }),
    onSuccess: () => {
      invalidateList();
      setForm(emptyForm());
    }
  });
  const start = useMutation({ mutationFn: startLiveSession, onSuccess: invalidateList });
  const end = useMutation({ mutationFn: (id: string) => endLiveSession(id), onSuccess: invalidateList });

  const sessionsRows = sessions.data ?? [];
  const scheduledCount = sessionsRows.filter((session) => session.status === "SCHEDULED").length;
  const liveCount = sessionsRows.filter((session) => session.status === "LIVE").length;

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };

  return (
    <div>
      <PageHeader
        title="Lớp trực tuyến"
        description="Lên lịch, bắt đầu, kết thúc webinar và đăng ký learner mà không cần tra ID thủ công."
      />

      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Metric icon={<Video size={18} />} label="Buổi live" value={String(sessionsRows.length)} detail={submitted ? courseLabel(courseById.get(submitted), submitted) : "Tất cả khóa học"} />
        <Metric icon={<CalendarClock size={18} />} label="Sắp diễn ra" value={String(scheduledCount)} detail="Trạng thái SCHEDULED" />
        <Metric icon={<Play size={18} />} label="Đang live" value={String(liveCount)} detail="Có thể kết thúc và lưu recording" />
        <Metric icon={<UsersRound size={18} />} label="Host" value={String(hostUsers.length)} detail={usersQuery.isLoading || roleQueriesLoading ? "Đang tải người dùng" : "Admin/instructor/TA"} />
      </div>

      <Card className="mb-4">
        <CardHeader title="Tạo buổi live" subtitle="Chọn khóa và host từ dữ liệu hệ thống, đặt lịch bằng thời gian địa phương." />
        <form className="grid gap-3 p-4 lg:grid-cols-2" onSubmit={onCreate}>
          <FormField label="Khóa học" htmlFor="ls-course">
            <Select id="ls-course" value={form.courseId} onChange={(e) => setForm({ ...form, courseId: e.target.value })} required>
              <option value="">Chọn khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Host" htmlFor="ls-host">
            <Select id="ls-host" value={form.hostId} onChange={(e) => setForm({ ...form, hostId: e.target.value })} required>
              <option value="">Chọn host</option>
              {hostUsers.map((user) => (
                <option key={user.id} value={String(user.id)}>
                  {adminUserLabel(user)}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Tiêu đề" htmlFor="ls-title">
            <Input id="ls-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </FormField>
          <FormField label="Sức chứa" htmlFor="ls-capacity" hint="Để trống nếu không giới hạn.">
            <Input id="ls-capacity" type="number" min="1" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
          </FormField>
          <FormField label="Bắt đầu" htmlFor="ls-start">
            <Input id="ls-start" type="datetime-local" value={form.scheduledStart} onChange={(e) => setForm({ ...form, scheduledStart: e.target.value })} required />
          </FormField>
          <FormField label="Kết thúc dự kiến" htmlFor="ls-end">
            <Input id="ls-end" type="datetime-local" value={form.scheduledEnd} onChange={(e) => setForm({ ...form, scheduledEnd: e.target.value })} />
          </FormField>
          {(courses.isError || usersQuery.isError) && (
            <div className="grid gap-3 lg:col-span-2 lg:grid-cols-2">
              {courses.isError && <ErrorState error={courses.error} />}
              {usersQuery.isError && <ErrorState error={usersQuery.error} />}
            </div>
          )}
          {create.isError && <ErrorState error={create.error} />}
          <div className="lg:col-span-2">
            <Button type="submit" disabled={create.isPending || !form.courseId || !form.hostId || !form.title || !form.scheduledStart}>
              <CalendarClock size={16} />
              {create.isPending ? "Đang tạo" : "Tạo buổi live"}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="mb-4">
        <CardHeader title="Danh sách buổi live" subtitle="Lọc theo khóa học và xử lý start/end trực tiếp trên từng dòng." />
        <form
          className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setSubmitted(courseFilter);
          }}
        >
          <FormField label="Khóa học" htmlFor="ls-filter">
            <Select id="ls-filter" value={courseFilter} onChange={(e) => setCourseFilter(e.target.value)}>
              <option value="">Tất cả khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
            </Select>
          </FormField>
          <Button type="submit" variant="secondary" className="self-end">
            Lọc
          </Button>
        </form>

        {sessions.isLoading && <Spinner />}
        {sessions.isError && <ErrorState error={sessions.error} />}
        {sessions.data && sessions.data.length === 0 && <EmptyState message="Chưa có buổi live phù hợp." />}
        {sessions.data && sessions.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Buổi live</Th>
                <Th>Khóa học</Th>
                <Th>Host</Th>
                <Th>Thời gian</Th>
                <Th>Trạng thái</Th>
                <Th>Hành động</Th>
              </tr>
            </thead>
            <tbody>
              {sessions.data.map((session) => {
                const course = courseById.get(session.courseId);
                const host = userById.get(session.hostId);
                return (
                  <tr key={session.id} className="hover:bg-slate-50">
                    <Td>
                      <p className="font-semibold text-slate-900">{session.title}</p>
                      <p className="mt-1 text-xs text-slate-500">{session.provider} · ID {compactId(session.id)}</p>
                    </Td>
                    <Td>
                      <p className="font-semibold text-slate-900">{courseLabel(course, session.courseId)}</p>
                      <p className="mt-1 text-xs text-slate-500">ID {compactId(session.courseId)}</p>
                    </Td>
                    <Td>
                      <p className="font-semibold text-slate-900">{host?.fullName ?? `User ${compactId(session.hostId)}`}</p>
                      <p className="mt-1 text-xs text-slate-500">{host?.email ?? `ID ${compactId(session.hostId)}`}</p>
                    </Td>
                    <Td>{formatDateTime(session.scheduledStart)}</Td>
                    <Td><Badge value={session.status} /></Td>
                    <Td className="space-x-2">
                      <Link to={session.id}><Button variant="secondary" size="sm">Chi tiết</Button></Link>
                      <Button variant="secondary" disabled={session.status !== "SCHEDULED" || start.isPending} onClick={() => start.mutate(session.id)}>
                        <Play size={15} />
                        Bắt đầu
                      </Button>
                      <Button variant="secondary" disabled={session.status !== "LIVE" || end.isPending} onClick={() => end.mutate(session.id)}>
                        <Square size={15} />
                        Kết thúc
                      </Button>
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

export function LiveSessionDetailPage() {
  const { sessionId = "" } = useParams<{ sessionId: string }>();
  const qc = useQueryClient();
  const { courseById } = useCoursePicker();
  const { learnerUsers, userById } = useLearnerUsers();
  const [endRecordingKey, setEndRecordingKey] = useState("");
  const [registerUserId, setRegisterUserId] = useState("");
  const [registrationResult, setRegistrationResult] = useState<Registration | null>(null);
  const [joinUserId, setJoinUserId] = useState("");
  const [joinUserIdSubmitted, setJoinUserIdSubmitted] = useState("");

  const session = useQuery({
    queryKey: queryKeys.liveSessions.detail(sessionId),
    queryFn: () => getLiveSession(sessionId),
    enabled: Boolean(sessionId)
  });

  const invalidateDetail = () => qc.invalidateQueries({ queryKey: queryKeys.liveSessions.detail(sessionId) });
  const start = useMutation({ mutationFn: () => startLiveSession(sessionId), onSuccess: invalidateDetail });
  const end = useMutation({
    mutationFn: () => endLiveSession(sessionId, endRecordingKey || undefined),
    onSuccess: invalidateDetail
  });
  const register = useMutation({
    mutationFn: () => registerToSession(sessionId, registerUserId),
    onSuccess: (data) => {
      setRegistrationResult(data);
      setRegisterUserId("");
    }
  });
  const joinInfo = useQuery({
    queryKey: queryKeys.liveSessions.joinInfo(sessionId, joinUserIdSubmitted),
    queryFn: () => getJoinInfo(sessionId, joinUserIdSubmitted),
    enabled: Boolean(joinUserIdSubmitted)
  });

  if (session.isLoading) return <Spinner />;
  if (session.isError) return <ErrorState error={session.error} />;
  if (!session.data) return null;

  const s = session.data;
  const course = courseById.get(s.courseId);
  const host = userById.get(s.hostId);
  const registeredUser = userById.get(registrationResult?.userId ?? "");
  const joinUser = userById.get(joinUserIdSubmitted);

  return (
    <div>
      <div className="mb-4">
        <Link to=".." className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Quay lại danh sách
        </Link>
      </div>

      <PageHeader title={s.title} description={`${s.provider} · ID ${compactId(s.id)}`} />

      <Card className="mb-4">
        <CardHeader title="Thông tin buổi học" subtitle="Tổng quan live session, khóa học, host và lịch chạy." />
        <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-400">Khóa học</p>
            <p className="mt-2 font-semibold text-slate-900">{courseLabel(course, s.courseId)}</p>
            <p className="mt-1 text-xs text-slate-500">ID {compactId(s.courseId)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-400">Host</p>
            <p className="mt-2 font-semibold text-slate-900">{adminUserLabel(host, compactId(s.hostId))}</p>
            <p className="mt-1 text-xs text-slate-500">ID {compactId(s.hostId)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-400">Trạng thái</p>
            <div className="mt-2"><Badge value={s.status} /></div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-400">Bắt đầu</p>
            <p className="mt-2 font-semibold text-slate-900">{formatDateTime(s.scheduledStart)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-400">Kết thúc</p>
            <p className="mt-2 font-semibold text-slate-900">{formatDateTime(s.scheduledEnd)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-bold uppercase text-slate-400">Sức chứa</p>
            <p className="mt-2 font-semibold text-slate-900">{s.capacity ?? "Không giới hạn"}</p>
          </div>
          {s.recordingStorageKey && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 sm:col-span-2 xl:col-span-3">
              <p className="text-xs font-bold uppercase text-slate-400">Recording</p>
              <p className="mt-2 break-all font-semibold text-slate-900">{s.recordingStorageKey}</p>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 border-t p-4">
          <div className="flex flex-wrap items-end gap-3">
            <Button disabled={s.status !== "SCHEDULED" || start.isPending} onClick={() => start.mutate()}>
              <Play size={16} />
              {start.isPending ? "Đang xử lý" : "Bắt đầu"}
            </Button>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-full max-w-lg">
              <FormField label="Khóa lưu trữ ghi hình" htmlFor="end-recording-key" hint="Tùy chọn, ví dụ s3://bucket/recording.mp4">
                <Input
                  id="end-recording-key"
                  value={endRecordingKey}
                  onChange={(e) => setEndRecordingKey(e.target.value)}
                />
              </FormField>
            </div>
            <Button variant="secondary" disabled={s.status !== "LIVE" || end.isPending} onClick={() => end.mutate()}>
              <Square size={16} />
              {end.isPending ? "Đang xử lý" : "Kết thúc"}
            </Button>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Đăng ký tham dự" subtitle="Chọn learner đã có trong hệ thống để đăng ký vào buổi live." />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              setRegistrationResult(null);
              register.mutate();
            }}
          >
            <FormField label="Learner" htmlFor="reg-user-id">
              <Select id="reg-user-id" value={registerUserId} onChange={(e) => setRegisterUserId(e.target.value)} required>
                <option value="">Chọn learner</option>
                {learnerUsers.map((user) => (
                  <option key={user.id} value={String(user.id)}>
                    {adminUserLabel(user)}
                  </option>
                ))}
              </Select>
            </FormField>
            <Button type="submit" disabled={register.isPending || !registerUserId}>
              <UserPlus size={16} />
              {register.isPending ? "Đang đăng ký" : "Đăng ký"}
            </Button>
          </form>
          {register.isError && <ErrorState error={register.error} />}
          {registrationResult && (
            <div className="px-4 pb-4">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                <p className="font-bold">Đăng ký thành công</p>
                <p className="mt-1">{adminUserLabel(registeredUser, compactId(registrationResult.userId))}</p>
                <p className="mt-1">Mã đăng ký: {compactId(registrationResult.id)}</p>
              </div>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Thông tin tham gia" subtitle="Lấy join link theo learner đã đăng ký." />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              setJoinUserIdSubmitted(joinUserId.trim());
            }}
          >
            <FormField label="Learner" htmlFor="join-user-id">
              <Select id="join-user-id" value={joinUserId} onChange={(e) => setJoinUserId(e.target.value)} required>
                <option value="">Chọn learner</option>
                {learnerUsers.map((user) => (
                  <option key={user.id} value={String(user.id)}>
                    {adminUserLabel(user)}
                  </option>
                ))}
              </Select>
            </FormField>
            <Button type="submit" variant="secondary" disabled={joinInfo.isFetching || !joinUserId}>
              <Link2 size={16} />
              {joinInfo.isFetching ? "Đang lấy" : "Lấy link"}
            </Button>
          </form>
          {joinInfo.isError && <ErrorState error={joinInfo.error} />}
          {joinInfo.data && (
            <div className="space-y-3 px-4 pb-4 text-sm">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-bold uppercase text-slate-400">Learner</p>
                <p className="mt-2 font-semibold text-slate-900">{adminUserLabel(joinUser, compactId(joinUserIdSubmitted))}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-bold uppercase text-slate-400">Nhà cung cấp</p>
                <p className="mt-2 font-semibold text-slate-900">{joinInfo.data.provider}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-bold uppercase text-slate-400">Link tham gia</p>
                <a
                  href={joinInfo.data.joinUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 block break-all font-semibold text-brand-700 hover:underline"
                >
                  {joinInfo.data.joinUrl}
                </a>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
