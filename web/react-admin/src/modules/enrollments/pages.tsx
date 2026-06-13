import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Clock3,
  GraduationCap,
  ListChecks,
  Search,
  UserPlus,
  UsersRound
} from "lucide-react";
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
import { listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
import type { AdminUser } from "@/modules/identity/api";
import { useLearnerUsers } from "@/modules/identity/useLearnerUsers";
import {
  addToWaitlist,
  createEnrollment,
  getStats,
  listEnrollments,
  listWaitlist,
  setCapacity
} from "./api";

function compactId(value?: string) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function enrollmentStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    ACTIVE: "Đang học",
    COMPLETED: "Hoàn thành",
    DROPPED: "Đã rời khóa",
    WAITLISTED: "Chờ ghi danh"
  };
  return labels[status ?? ""] ?? status ?? "Chưa rõ";
}

function waitlistStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    WAITING: "Đang chờ",
    OFFERED: "Đã mời",
    EXPIRED: "Hết hạn",
    CANCELLED: "Đã hủy"
  };
  return labels[status ?? ""] ?? status ?? "Đang chờ";
}

function courseLabel(course?: Course, fallbackId?: string) {
  if (!course) return fallbackId ? `Khóa ${compactId(fallbackId)}` : "Tất cả khóa";
  return course.code ? `${course.code} · ${course.title}` : course.title;
}

function userLabel(user?: AdminUser, fallbackId?: string) {
  if (!user) return fallbackId ? `User ${compactId(fallbackId)}` : "Tất cả học viên";
  return `${user.fullName || user.email} · ${user.email}`;
}

function Metric({
  icon,
  label,
  value,
  detail,
  tone = "brand"
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  tone?: "brand" | "emerald" | "amber" | "sky";
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    sky: "bg-sky-50 text-sky-700"
  }[tone];

  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-md", toneClass)}>
          {icon}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

export function EnrollmentsPage() {
  const qc = useQueryClient();
  const [courseId, setCourseId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [capacity, setCapacityValue] = useState("");
  const [enrollForm, setEnrollForm] = useState({ courseId: "", studentId: "" });
  const [waitForm, setWaitForm] = useState({ courseId: "", studentId: "" });

  const courses = useQuery({
    queryKey: queryKeys.courses.list("enrollment-picker"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const { learnerUsers: studentUsers, roleQueriesLoading, userById, usersQuery: users } = useLearnerUsers();
  const enrollments = useQuery({
    queryKey: queryKeys.enrollments.list(courseId, studentId),
    queryFn: () => listEnrollments({ courseId: courseId || undefined, studentId: studentId || undefined })
  });
  const waitlist = useQuery({
    queryKey: queryKeys.enrollments.waitlist(courseId),
    queryFn: () => listWaitlist(courseId),
    enabled: Boolean(courseId)
  });
  const stats = useQuery({
    queryKey: queryKeys.enrollments.stats(courseId),
    queryFn: () => getStats(courseId),
    enabled: Boolean(courseId)
  });

  const courseById = useMemo(() => {
    const map = new Map<string, Course>();
    for (const course of courses.data ?? []) map.set(course.id, course);
    return map;
  }, [courses.data]);
  const selectedCourse = courseById.get(courseId);

  function invalidateEnrollmentData(nextCourseId = courseId) {
    qc.invalidateQueries({ queryKey: ["enrollments"] });
    if (nextCourseId) {
      qc.invalidateQueries({ queryKey: queryKeys.enrollments.stats(nextCourseId) });
      qc.invalidateQueries({ queryKey: queryKeys.enrollments.waitlist(nextCourseId) });
    }
  }

  function pickCourse(nextCourseId: string) {
    setCourseId(nextCourseId);
    setEnrollForm((current) => ({ ...current, courseId: current.courseId || nextCourseId }));
    setWaitForm((current) => ({ ...current, courseId: current.courseId || nextCourseId }));
  }

  function pickStudent(nextStudentId: string) {
    setStudentId(nextStudentId);
    setEnrollForm((current) => ({ ...current, studentId: current.studentId || nextStudentId }));
    setWaitForm((current) => ({ ...current, studentId: current.studentId || nextStudentId }));
  }

  const capacityMutation = useMutation({
    mutationFn: () => setCapacity(courseId, capacity === "" ? null : Number(capacity)),
    onSuccess: () => invalidateEnrollmentData()
  });

  const enroll = useMutation({
    mutationFn: () => createEnrollment(enrollForm),
    onSuccess: (row) => {
      setEnrollForm({ courseId: row.courseId, studentId: "" });
      invalidateEnrollmentData(row.courseId);
    }
  });

  const wait = useMutation({
    mutationFn: () => addToWaitlist(waitForm),
    onSuccess: (row) => {
      setWaitForm({ courseId: row.courseId, studentId: "" });
      invalidateEnrollmentData(row.courseId);
    }
  });

  return (
    <div>
      <PageHeader
        title="Ghi danh"
        description="Quản lý enrollment, waitlist và sức chứa bằng bộ chọn khóa học, learner và trạng thái."
      />

      <div className="mb-4 grid gap-3 md:grid-cols-4">
        <Metric
          icon={<GraduationCap size={18} />}
          label="Khóa trong hệ thống"
          value={String(courses.data?.length ?? 0)}
          detail={courses.isLoading ? "Đang tải catalog" : "Dùng để lọc và ghi danh nhanh"}
        />
        <Metric
          icon={<UsersRound size={18} />}
          label="Học viên"
          value={String(studentUsers.length)}
          detail={users.isLoading || roleQueriesLoading ? "Đang phân loại learner" : "Có thể chọn để ghi danh"}
          tone="sky"
        />
        <Metric
          icon={<ListChecks size={18} />}
          label="Enrollment đang xem"
          value={String(enrollments.data?.length ?? 0)}
          detail={courseId ? courseLabel(selectedCourse, courseId) : "Tất cả khóa"}
          tone="emerald"
        />
        <Metric
          icon={<Clock3 size={18} />}
          label="Waitlist"
          value={courseId && stats.data ? String(stats.data.waitlistCount) : "—"}
          detail={courseId ? "Theo khóa đang chọn" : "Chọn một khóa để xem"}
          tone="amber"
        />
      </div>

      <Card className="mb-4">
        <CardHeader
          title="Bộ lọc"
          subtitle="Chọn theo tên khóa và học viên; bảng bên dưới vẫn hỗ trợ dữ liệu ngoài danh sách bằng ID rút gọn."
        />
        <div className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
          <FormField label="Khóa học" htmlFor="f-course">
            <Select id="f-course" value={courseId} onChange={(e) => pickCourse(e.target.value)}>
              <option value="">Tất cả khóa học</option>
              {(courses.data ?? []).map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Học viên" htmlFor="f-student">
            <Select id="f-student" value={studentId} onChange={(e) => pickStudent(e.target.value)}>
              <option value="">Tất cả học viên</option>
              {studentUsers.map((user) => (
                <option key={user.id} value={String(user.id)}>
                  {userLabel(user)}
                </option>
              ))}
            </Select>
          </FormField>
          <Button
            type="button"
            variant="secondary"
            className="self-end"
            onClick={() => {
              setCourseId("");
              setStudentId("");
            }}
          >
            <Search size={16} />
            Xóa lọc
          </Button>
        </div>
        {(courses.isError || users.isError) && (
          <div className="grid gap-3 p-4 pt-0 md:grid-cols-2">
            {courses.isError && <ErrorState error={courses.error} />}
            {users.isError && <ErrorState error={users.error} />}
          </div>
        )}
      </Card>

      {courseId && (
        <Card className="mb-4">
          <CardHeader
            title="Thống kê & sức chứa"
            subtitle={courseLabel(selectedCourse, courseId)}
          />
          <div className="grid gap-4 p-4 xl:grid-cols-[1fr_360px]">
            {stats.isLoading && <Spinner />}
            {stats.isError && <ErrorState error={stats.error} />}
            {stats.data && (
              <div className="grid gap-3 sm:grid-cols-4">
                <Metric icon={<UsersRound size={18} />} label="Đang học" value={String(stats.data.totalActive)} detail="Enrollment active" tone="emerald" />
                <Metric icon={<Clock3 size={18} />} label="Waitlist" value={String(stats.data.waitlistCount)} detail="Đang chờ chỗ" tone="amber" />
                <Metric icon={<GraduationCap size={18} />} label="Hoàn thành" value={String(stats.data.totalCompleted)} detail="Đã hoàn tất khóa" tone="brand" />
                <Metric icon={<ListChecks size={18} />} label="Đã rời" value={String(stats.data.totalDropped)} detail="Dropped" tone="sky" />
              </div>
            )}
            <form
              className="rounded-lg border border-black/10 bg-slate-50 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                capacityMutation.mutate();
              }}
            >
              <FormField label="Sức chứa" htmlFor="cap-value" hint="Để trống nếu khóa không giới hạn số lượng học viên.">
                <Input
                  id="cap-value"
                  type="number"
                  min={0}
                  value={capacity}
                  onChange={(e) => setCapacityValue(e.target.value)}
                  placeholder="Không giới hạn"
                />
              </FormField>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button type="submit" variant="secondary" disabled={capacityMutation.isPending}>
                  {capacityMutation.isPending ? "Đang lưu" : "Đặt sức chứa"}
                </Button>
                {capacityMutation.isSuccess && <span className="text-sm font-semibold text-emerald-600">Đã cập nhật</span>}
              </div>
              {capacityMutation.isError && <ErrorState error={capacityMutation.error} />}
            </form>
          </div>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <Card>
          <CardHeader title="Enrollment" subtitle={`${enrollments.data?.length ?? 0} bản ghi đang hiển thị`} />
          {enrollments.isLoading && <Spinner />}
          {enrollments.isError && <ErrorState error={enrollments.error} />}
          {enrollments.data && enrollments.data.length === 0 && <EmptyState message="Không có enrollment phù hợp." />}
          {enrollments.data && enrollments.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Khóa học</Th>
                  <Th>Học viên</Th>
                  <Th>Trạng thái</Th>
                  <Th>Mốc thời gian</Th>
                </tr>
              </thead>
              <tbody>
                {enrollments.data.map((row) => {
                  const course = courseById.get(row.courseId);
                  const user = userById.get(row.studentId);
                  return (
                    <tr key={row.id} className="hover:bg-slate-50">
                      <Td>
                        <p className="font-semibold text-slate-900">{courseLabel(course, row.courseId)}</p>
                        <p className="mt-1 text-xs text-slate-500">ID {compactId(row.courseId)}</p>
                      </Td>
                      <Td>
                        <p className="font-semibold text-slate-900">{user?.fullName ?? `User ${compactId(row.studentId)}`}</p>
                        <p className="mt-1 text-xs text-slate-500">{user?.email ?? `ID ${compactId(row.studentId)}`}</p>
                      </Td>
                      <Td>
                        <Badge value={row.status} label={enrollmentStatusLabel(row.status)} />
                      </Td>
                      <Td>
                        <p className="text-xs text-slate-500">
                          {row.enrolledAt ? `Ghi danh ${new Date(row.enrolledAt).toLocaleDateString("vi-VN")}` : "Chưa có ngày"}
                        </p>
                        {row.completedAt && <p className="mt-1 text-xs text-emerald-600">Hoàn thành {new Date(row.completedAt).toLocaleDateString("vi-VN")}</p>}
                        {row.droppedAt && <p className="mt-1 text-xs text-red-600">Rời khóa {new Date(row.droppedAt).toLocaleDateString("vi-VN")}</p>}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Ghi danh học viên" subtitle="Chọn course và student, hệ thống sẽ tạo enrollment active." />
            <form
              className="space-y-4 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                enroll.mutate();
              }}
            >
              <FormField label="Khóa học" htmlFor="e-course">
                <Select
                  id="e-course"
                  value={enrollForm.courseId}
                  onChange={(e) => setEnrollForm({ ...enrollForm, courseId: e.target.value })}
                  required
                >
                  <option value="">Chọn khóa học</option>
                  {(courses.data ?? []).map((course) => (
                    <option key={course.id} value={course.id}>{courseLabel(course)}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Học viên" htmlFor="e-student">
                <Select
                  id="e-student"
                  value={enrollForm.studentId}
                  onChange={(e) => setEnrollForm({ ...enrollForm, studentId: e.target.value })}
                  required
                >
                  <option value="">Chọn học viên</option>
                  {studentUsers.map((user) => (
                    <option key={user.id} value={String(user.id)}>{userLabel(user)}</option>
                  ))}
                </Select>
              </FormField>
              {enroll.isError && <ErrorState error={enroll.error} />}
              <Button type="submit" disabled={enroll.isPending || !enrollForm.courseId || !enrollForm.studentId}>
                <UserPlus size={16} />
                {enroll.isPending ? "Đang lưu" : "Ghi danh"}
              </Button>
            </form>
          </Card>

          <Card>
            <CardHeader title="Waitlist" subtitle={courseId ? courseLabel(selectedCourse, courseId) : "Chọn khóa ở bộ lọc để xem waitlist."} />
            {!courseId && <EmptyState message="Chọn một khóa học để xem danh sách chờ." />}
            {courseId && waitlist.isLoading && <Spinner />}
            {courseId && waitlist.isError && <ErrorState error={waitlist.error} />}
            {courseId && waitlist.data && waitlist.data.length === 0 && <EmptyState message="Không có waitlist cho khóa này." />}
            {courseId && waitlist.data && waitlist.data.length > 0 && (
              <Table>
                <thead>
                  <tr>
                    <Th>Vị trí</Th>
                    <Th>Học viên</Th>
                    <Th>Trạng thái</Th>
                  </tr>
                </thead>
                <tbody>
                  {waitlist.data.map((row) => {
                    const user = userById.get(row.studentId);
                    return (
                      <tr key={row.id}>
                        <Td>#{row.position ?? "—"}</Td>
                        <Td>
                          <p className="font-semibold text-slate-900">{user?.fullName ?? `User ${compactId(row.studentId)}`}</p>
                          <p className="mt-1 text-xs text-slate-500">{user?.email ?? `ID ${compactId(row.studentId)}`}</p>
                        </Td>
                        <Td><Badge value={row.status} label={waitlistStatusLabel(row.status)} /></Td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            )}
          </Card>

          <Card>
            <CardHeader title="Thêm vào waitlist" subtitle="Dùng khi khóa đã đầy hoặc cần duyệt sau." />
            <form
              className="space-y-4 p-4"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                wait.mutate();
              }}
            >
              <FormField label="Khóa học" htmlFor="w-course">
                <Select
                  id="w-course"
                  value={waitForm.courseId}
                  onChange={(e) => setWaitForm({ ...waitForm, courseId: e.target.value })}
                  required
                >
                  <option value="">Chọn khóa học</option>
                  {(courses.data ?? []).map((course) => (
                    <option key={course.id} value={course.id}>{courseLabel(course)}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Học viên" htmlFor="w-student">
                <Select
                  id="w-student"
                  value={waitForm.studentId}
                  onChange={(e) => setWaitForm({ ...waitForm, studentId: e.target.value })}
                  required
                >
                  <option value="">Chọn học viên</option>
                  {studentUsers.map((user) => (
                    <option key={user.id} value={String(user.id)}>{userLabel(user)}</option>
                  ))}
                </Select>
              </FormField>
              {wait.isError && <ErrorState error={wait.error} />}
              <Button type="submit" variant="secondary" disabled={wait.isPending || !waitForm.courseId || !waitForm.studentId}>
                {wait.isPending ? "Đang lưu" : "Thêm waitlist"}
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
