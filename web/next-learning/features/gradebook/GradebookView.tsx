"use client";

import { FormEvent, useEffect, useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  ClipboardCheck,
  GraduationCap,
  Layers3,
  Medal,
  Percent,
  Search,
  TimerReset,
  Trophy
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import { listMyEnrollments } from "@/features/enrollments/api";
import { clientFetch } from "@/shared/api/client";
import { Badge, Button, Card, EmptyState, ProgressBar, SelectInput, TextInput, cn } from "@/shared/ui";

const COURSE_ID_STORAGE_KEY = "courseflow.gradebook.courseId";

type GradeEntry = {
  id: string;
  gradeItemId: string;
  title?: string;
  categoryName?: string;
  rawScore?: number;
  adjustedScore?: number;
  maxScore?: number;
  latePenaltyApplied?: number;
  isLate: boolean;
  minutesLate: number;
  letter?: string;
  status?: string;
  gradedAt?: string;
};

type CategorySummary = {
  name: string;
  aggregationMethod?: string;
  dropLowest: number;
  weightPercent?: number;
  contribution?: number;
  itemCount: number;
  droppedCount: number;
};

type StudentGradebook = {
  courseId: string;
  studentId: string;
  finalScore?: number;
  finalLetter?: string;
  gradingSchemeName?: string;
  categories?: CategorySummary[];
  entries?: GradeEntry[];
};

type FinalGrade = {
  id: string;
  courseId: string;
  studentId: string;
  finalScore?: number;
  letter?: string;
  passed: boolean;
  status?: string;
  finalizedBy?: string;
  finalizedAt?: string;
};

type CatalogCourse = {
  id?: string;
  code?: string;
  title: string;
  slug?: string;
  level?: string;
  status?: string;
};

const tileTone = {
  brand: "bg-brand-50 text-brand-700",
  sky: "bg-signal-50 text-signal-600",
  amber: "bg-accent-50 text-accent-600",
  coral: "bg-coral-50 text-coral-600"
};

function formatNumber(value?: number): string {
  if (value == null) return "--";
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(value);
}

function formatDateTime(value?: string): string {
  if (!value) return "Chưa cập nhật";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function compactId(value?: string): string {
  if (!value) return "--";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function enrollmentStatusLabel(status?: string): string {
  const labels: Record<string, string> = {
    ACTIVE: "Đang học",
    COMPLETED: "Hoàn thành",
    DROPPED: "Đã rời khóa",
    WAITLISTED: "Chờ ghi danh"
  };
  return labels[status ?? ""] ?? status ?? "Ghi danh";
}

function entryScore(entry: GradeEntry): number | undefined {
  return entry.adjustedScore ?? entry.rawScore;
}

function entryPercent(entry: GradeEntry): number | undefined {
  const score = entryScore(entry);
  if (score == null || !entry.maxScore) return undefined;
  return Math.round((score / entry.maxScore) * 1000) / 10;
}

function statusLabel(status?: string): string {
  if (status === "PUBLISHED") return "Đã công bố";
  if (status === "DRAFT") return "Nháp";
  if (status === "FINALIZED") return "Đã chốt";
  return status ?? "Đã ghi nhận";
}

function methodLabel(method?: string): string {
  if (method === "WEIGHTED_MEAN") return "Trung bình có trọng số";
  if (method === "MEAN") return "Trung bình";
  if (method === "SUM") return "Tổng điểm";
  return method ?? "Tổng hợp";
}

function scoreTone(percent?: number): "brand" | "amber" | "coral" | "sky" | "neutral" {
  if (percent == null) return "neutral";
  if (percent >= 85) return "brand";
  if (percent >= 70) return "sky";
  if (percent >= 50) return "amber";
  return "coral";
}

function SummaryTile({
  icon,
  label,
  value,
  detail,
  tone
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
  tone: keyof typeof tileTone;
}) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase text-ink-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-ink-900">{value}</p>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-md", tileTone[tone])}>
          {icon}
        </span>
      </div>
      <p className="mt-3 text-sm text-ink-500">{detail}</p>
    </div>
  );
}

export function GradebookView() {
  const searchParams = useSearchParams();
  const queryCourseId = searchParams.get("courseId") ?? "";
  const { session, hydrated: sessionHydrated } = useLearnerSession();
  const studentId = session?.user.id ? String(session.user.id) : "";
  const [courseId, setCourseId] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(COURSE_ID_STORAGE_KEY) ?? "";
    const nextCourseId = queryCourseId || stored;
    setCourseId(nextCourseId);
    setSubmitted(nextCourseId);
    setHydrated(true);
  }, [queryCourseId]);

  const enrollments = useQuery({
    queryKey: ["my-enrollments", studentId],
    queryFn: () => listMyEnrollments(),
    enabled: Boolean(studentId)
  });
  const catalog = useQuery({
    queryKey: ["gradebook-course-catalog"],
    queryFn: () => clientFetch<CatalogCourse[]>("/v1/courses"),
    enabled: Boolean(studentId),
    retry: 1,
    staleTime: 60_000
  });

  const { data, isFetching, isError } = useQuery({
    queryKey: ["gradebook", submitted, studentId],
    queryFn: () =>
      clientFetch<StudentGradebook>(
        `/v1/gradebook/courses/${submitted}/students/${studentId}`
      ),
    enabled: Boolean(submitted && studentId)
  });
  const finalGrade = useQuery({
    queryKey: ["final-grade", submitted, studentId],
    queryFn: () =>
      clientFetch<FinalGrade>(
        `/v1/gradebook/courses/${submitted}/students/${studentId}/final-grade`
      ),
    enabled: Boolean(submitted && studentId),
    retry: false
  });

  const entries = data?.entries ?? [];
  const categories = data?.categories ?? [];
  const courseById = useMemo(() => {
    const map = new Map<string, CatalogCourse>();
    for (const course of catalog.data ?? []) {
      if (course.id) map.set(course.id, course);
    }
    return map;
  }, [catalog.data]);
  const enrolledCourseIds = useMemo(() => {
    const ids = (enrollments.data ?? [])
      .map((enrollment) => enrollment.courseId)
      .filter(Boolean);
    if (submitted && !ids.includes(submitted)) return [submitted, ...ids];
    return ids;
  }, [enrollments.data, submitted]);
  const selectedCourse = courseById.get(submitted);
  const gradedEntries = entries.filter((entry) => entryScore(entry) != null);
  const lateCount = entries.filter((entry) => entry.isLate).length;
  const displayedFinalScore = finalGrade.data?.finalScore ?? data?.finalScore;
  const displayedFinalLetter = finalGrade.data?.letter ?? data?.finalLetter;
  const finalGradeDetail = finalGrade.data?.status
    ? `${statusLabel(finalGrade.data.status)} · ${formatDateTime(finalGrade.data.finalizedAt)}`
    : data?.gradingSchemeName ?? "Thang điểm hiện hành";
  const averagePercent = useMemo(() => {
    const percents = entries
      .map(entryPercent)
      .filter((value): value is number => typeof value === "number");
    if (!percents.length) return undefined;
    return percents.reduce((sum, value) => sum + value, 0) / percents.length;
  }, [entries]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const nextCourseId = courseId.trim();
    if (!nextCourseId) return;
    localStorage.setItem(COURSE_ID_STORAGE_KEY, nextCourseId);
    setSubmitted(nextCourseId);
  }

  function selectCourse(nextCourseId: string) {
    setCourseId(nextCourseId);
    setSubmitted(nextCourseId);
    if (nextCourseId) {
      localStorage.setItem(COURSE_ID_STORAGE_KEY, nextCourseId);
    } else {
      localStorage.removeItem(COURSE_ID_STORAGE_KEY);
    }
  }

  function courseTitle(courseIdValue: string): string {
    const course = courseById.get(courseIdValue);
    if (!course) return `Khóa ${compactId(courseIdValue)}`;
    return course.code ? `${course.code} · ${course.title}` : course.title;
  }

  if (!sessionHydrated) {
    return (
      <div className="space-y-4">
        <div className="h-[156px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-[126px] animate-pulse rounded-lg border border-black/10 bg-white/70"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!studentId) {
    return (
      <Card>
        <p className="text-sm text-amber-700">Bạn cần đăng nhập để xem điểm.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="space-y-4">
        <form className="grid gap-3 lg:grid-cols-[1fr_auto]" onSubmit={submit}>
          <label className="block text-sm font-semibold text-ink-700">
            Khóa học
            {enrolledCourseIds.length > 0 ? (
              <SelectInput
                value={courseId}
                onChange={(e) => selectCourse(e.target.value)}
                className="mt-2"
              >
                <option value="">Chọn khóa học</option>
                {enrolledCourseIds.map((courseIdValue) => (
                  <option key={courseIdValue} value={courseIdValue}>
                    {courseTitle(courseIdValue)}
                  </option>
                ))}
              </SelectInput>
            ) : (
              <TextInput
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
                placeholder="Nhập Course ID"
                className="mt-2 font-mono text-xs"
              />
            )}
          </label>
          <Button type="submit" className="self-end" disabled={!hydrated || !courseId.trim()}>
            <Search className="size-4" />
            Xem điểm
          </Button>
        </form>

        {enrollments.data && enrollments.data.length > 0 && (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {enrollments.data.map((enrollment) => {
              const active = submitted === enrollment.courseId;
              const course = courseById.get(enrollment.courseId);
              return (
                <button
                  key={enrollment.id}
                  type="button"
                  onClick={() => selectCourse(enrollment.courseId)}
                  className={cn(
                    "flex min-h-20 items-start gap-3 rounded-lg border p-3 text-left transition",
                    active
                      ? "border-brand-200 bg-brand-50 text-brand-800"
                      : "border-black/10 bg-white text-ink-600 hover:border-brand-200 hover:bg-brand-50/60"
                  )}
                >
                  <span className="grid size-10 shrink-0 place-items-center rounded-md bg-white text-brand-700">
                    <BookOpen className="size-5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block line-clamp-1 text-sm font-bold text-ink-900">
                      {course?.title ?? `Khóa ${compactId(enrollment.courseId)}`}
                    </span>
                    <span className="mt-1 flex flex-wrap gap-2 text-xs font-semibold text-ink-500">
                      {course?.code && <span>{course.code}</span>}
                      <span>{enrollmentStatusLabel(enrollment.status)}</span>
                      {course?.level && <span>{course.level}</span>}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        )}

        <p className="text-xs text-ink-500">
          Đang xem:{" "}
          <span className="font-semibold text-ink-700">
            {selectedCourse?.title ?? (submitted ? `Khóa ${compactId(submitted)}` : "--")}
          </span>
        </p>
      </Card>

      {!submitted && (
        <EmptyState
          title="Chọn khóa học để xem bảng điểm"
          description="Bảng điểm chỉ tải sau khi bạn chọn một khóa từ danh sách ghi danh hoặc nhập Course ID hợp lệ."
        />
      )}

      {isFetching && <p className="text-ink-500">Đang tải bảng điểm...</p>}
      {isError && <p className="text-red-600">Không tải được điểm. Backend có thể chưa chạy.</p>}

      {data && entries.length === 0 && (
        <EmptyState title="Chưa có điểm" description="Bảng điểm chưa có dữ liệu cho khóa học này." />
      )}

      {data && entries.length > 0 && (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryTile
              icon={<Trophy className="size-5" />}
              label="Điểm tổng kết"
              value={`${formatNumber(displayedFinalScore)}%`}
              detail={finalGradeDetail}
              tone="brand"
            />
            <SummaryTile
              icon={<Medal className="size-5" />}
              label="Xếp loại"
              value={displayedFinalLetter ?? "--"}
              detail={finalGrade.data ? "Điểm chính thức đã chốt" : "Dựa trên thang điểm của khóa học"}
              tone="amber"
            />
            <SummaryTile
              icon={<ClipboardCheck className="size-5" />}
              label="Đã chấm"
              value={`${gradedEntries.length}/${entries.length}`}
              detail={`${formatNumber(averagePercent)}% trung bình các mục`}
              tone="sky"
            />
            <SummaryTile
              icon={<TimerReset className="size-5" />}
              label="Nộp muộn"
              value={`${lateCount}`}
              detail="Số mục bị đánh dấu nộp trễ"
              tone="coral"
            />
          </div>

          {categories.length > 0 && (
            <Card className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-brand-600">Cơ cấu điểm</p>
                  <h2 className="mt-1 text-xl font-bold text-ink-900">Hạng mục và trọng số</h2>
                </div>
                <Badge tone="brand">
                  <Layers3 className="mr-1 size-3.5" />
                  {categories.length} hạng mục
                </Badge>
              </div>

              <div className="grid gap-3 lg:grid-cols-3">
                {categories.map((category) => (
                  <div key={category.name} className="rounded-lg border border-black/10 bg-slate-50/70 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-bold text-ink-900">{category.name}</p>
                        <p className="mt-1 text-xs text-ink-500">{methodLabel(category.aggregationMethod)}</p>
                      </div>
                      <Badge tone="sky">{formatNumber(category.weightPercent)}%</Badge>
                    </div>
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between text-xs text-ink-500">
                        <span>Đóng góp</span>
                        <span>{formatNumber(category.contribution)} điểm</span>
                      </div>
                      <ProgressBar value={category.weightPercent ?? 0} />
                    </div>
                    <p className="mt-3 text-xs text-ink-500">
                      {category.itemCount} mục, bỏ thấp nhất {category.droppedCount}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card padding="none" className="overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 p-4">
              <div>
                <p className="text-sm font-bold text-brand-600">Chi tiết điểm</p>
                <h2 className="mt-1 text-xl font-bold text-ink-900">Bài thi và bài tập đã ghi nhận</h2>
              </div>
              <Badge tone="neutral">
                <Percent className="mr-1 size-3.5" />
                {entries.length} mục
              </Badge>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-black/10 bg-slate-50 text-left text-xs uppercase text-ink-500">
                    <th className="px-4 py-3">Hạng mục</th>
                    <th className="px-4 py-3">Điểm</th>
                    <th className="px-4 py-3">Tỷ lệ</th>
                    <th className="px-4 py-3">Trạng thái</th>
                    <th className="px-4 py-3">Cập nhật</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => {
                    const percent = entryPercent(entry);
                    return (
                      <tr key={entry.id} className="border-b border-black/5 align-top">
                        <td className="px-4 py-3">
                          <p className="font-semibold text-ink-900">
                            {entry.title ?? entry.categoryName ?? compactId(entry.gradeItemId)}
                          </p>
                          <p className="mt-1 text-xs text-ink-500">{entry.categoryName ?? "Chưa phân loại"}</p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-bold text-ink-900">
                            {formatNumber(entryScore(entry))} / {formatNumber(entry.maxScore)}
                          </p>
                          {entry.letter && <p className="mt-1 text-xs text-ink-500">Xếp loại {entry.letter}</p>}
                        </td>
                        <td className="min-w-40 px-4 py-3">
                          <div className="mb-2 flex items-center justify-between gap-3 text-xs">
                            <span className="font-semibold text-ink-700">{formatNumber(percent)}%</span>
                            {entry.latePenaltyApplied != null && entry.latePenaltyApplied > 0 && (
                              <span className="text-coral-600">-{formatNumber(entry.latePenaltyApplied)}</span>
                            )}
                          </div>
                          <ProgressBar value={percent ?? 0} />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-2">
                            <Badge tone={scoreTone(percent)}>{statusLabel(entry.status)}</Badge>
                            {entry.isLate && <Badge tone="coral">Nộp muộn</Badge>}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-ink-500">{formatDateTime(entry.gradedAt)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
