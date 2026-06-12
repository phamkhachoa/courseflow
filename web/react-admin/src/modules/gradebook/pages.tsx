import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  Calculator,
  CheckCircle2,
  Download,
  FileCheck2,
  GraduationCap,
  Save,
  Sparkles,
  Trophy,
  UserCheck
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
  Textarea,
  Th
} from "@/shared/ui";
import { cn } from "@/shared/ui/cn";
import { fallbackCourses, listCourses } from "../courses/api";
import type { Course } from "../courses/types";
import { adminUserLabel, useLearnerUsers } from "../identity/useLearnerUsers";
import {
  createCategory,
  createGradingScheme,
  exportGradebook,
  finalizeGrade,
  getStudentGradebook,
  listCategories,
  listGradeItems,
  listGradingSchemes,
  type GradeEntry,
  type GradeItem,
  upsertEntry
} from "./api";

type DemoScope = {
  label: string;
  courseId: string;
  studentId: string;
  detail: string;
};

const DEMO_SCOPES: DemoScope[] = [
  {
    label: "AI210 - Minh Tran",
    courseId: "30000000-0000-0000-0000-000000000002",
    studentId: "4",
    detail: "Có assignment, quiz, thang điểm và final grade mẫu."
  },
  {
    label: "LX120 - An Le",
    courseId: "30000000-0000-0000-0000-000000000004",
    studentId: "5",
    detail: "Có portfolio/studio work để kiểm thử nhập điểm."
  },
  {
    label: "SE401 - Minh Tran",
    courseId: "30000000-0000-0000-0000-000000000001",
    studentId: "4",
    detail: "Có final grade mẫu cho course backend production."
  }
];

const AGGREGATION_OPTIONS = [
  { value: "WEIGHTED_MEAN", label: "Weighted mean" },
  { value: "MEAN", label: "Mean" },
  { value: "SUM", label: "Sum" },
  { value: "BEST_SCORE", label: "Best score" }
];

function formatNumber(value?: number | null, suffix = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${Number(value.toFixed(2))}${suffix}`;
}

function scoreFor(entry: GradeEntry) {
  return entry.adjustedScore ?? entry.rawScore;
}

function entryPercent(entry: GradeEntry) {
  const score = scoreFor(entry);
  if (score === undefined || score === null || !entry.maxScore) return null;
  return Math.round((score / entry.maxScore) * 100);
}

function gradeItemMeta(item: GradeItem) {
  const source = item.sourceType ? item.sourceType.toLowerCase() : "manual";
  const weight = item.itemWeightPercent ?? item.categoryWeightPercent;
  return [item.categoryName, source, weight !== undefined ? `${weight}%` : undefined]
    .filter(Boolean)
    .join(" · ");
}

function courseLabel(course?: Course) {
  if (!course) return "";
  return [course.code, course.title].filter(Boolean).join(" · ");
}

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = "brand"
}: {
  icon: typeof Calculator;
  label: string;
  value: string;
  detail: string;
  tone?: "brand" | "emerald" | "amber" | "sky";
}) {
  const toneClasses = {
    brand: "bg-brand-50 text-brand-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    sky: "bg-sky-50 text-sky-700"
  }[tone];

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <span className={cn("grid size-10 shrink-0 place-items-center rounded-md", toneClasses)}>
          <Icon size={18} />
        </span>
      </div>
      <p className="mt-3 text-sm leading-5 text-slate-500">{detail}</p>
    </div>
  );
}

function ScopeButton({
  scope,
  active,
  onClick
}: {
  scope: DemoScope;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-lg border p-3 text-left transition",
        active
          ? "border-brand-300 bg-brand-50 text-brand-900"
          : "border-slate-200 bg-white text-slate-700 hover:border-brand-200 hover:bg-brand-50/60"
      )}
    >
      <span className="flex items-center gap-2 text-sm font-bold">
        <Sparkles size={15} />
        {scope.label}
      </span>
      <span className="mt-1 block text-xs leading-5 text-slate-500">{scope.detail}</span>
    </button>
  );
}

export function GradebookPage() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get("courseId") ?? "";
  const requestedStudentId = searchParams.get("studentId") ?? "";
  const [courseId, setCourseId] = useState(requestedCourseId);
  const [studentId, setStudentId] = useState(requestedStudentId);

  useEffect(() => {
    setCourseId(requestedCourseId);
  }, [requestedCourseId]);

  useEffect(() => {
    setStudentId(requestedStudentId);
  }, [requestedStudentId]);

  function updateScope(nextCourseId: string, nextStudentId = studentId) {
    setCourseId(nextCourseId);
    setStudentId(nextStudentId);
    setEntry((current) => ({ ...current, gradeItemId: "" }));
    setSearchParams(
      {
        ...(nextCourseId ? { courseId: nextCourseId } : {}),
        ...(nextStudentId ? { studentId: nextStudentId } : {})
      },
      { replace: true }
    );
  }

  const courses = useQuery({
    queryKey: queryKeys.courses.list("gradebook"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });

  const courseRows = courses.data?.length ? courses.data : fallbackCourses;
  const selectedCourse = courseRows.find((course) => course.id === courseId);
  const { learnerUsers, roleQueriesLoading, userById, usersQuery } = useLearnerUsers();
  const selectedLearner = userById.get(studentId);
  const learnerRows = useMemo(() => {
    if (!selectedLearner) return learnerUsers;
    return learnerUsers.some((user) => String(user.id) === String(selectedLearner.id))
      ? learnerUsers
      : [selectedLearner, ...learnerUsers];
  }, [learnerUsers, selectedLearner]);
  const selectedLearnerLabel = selectedLearner
    ? adminUserLabel(selectedLearner)
    : studentId
      ? `Học viên ${compactId(studentId)}`
      : "Chưa chọn học viên";
  const learnerHint =
    usersQuery.isLoading || roleQueriesLoading
      ? "Đang tải danh sách learner..."
      : usersQuery.isError
        ? "Không tải được danh sách learner."
        : `${learnerRows.length} learner khả dụng`;

  const items = useQuery({
    queryKey: queryKeys.gradebook.items(courseId),
    queryFn: () => listGradeItems(courseId),
    enabled: Boolean(courseId)
  });
  const grades = useQuery({
    queryKey: queryKeys.gradebook.student(courseId, studentId),
    queryFn: () => getStudentGradebook(courseId, studentId),
    enabled: Boolean(courseId && studentId)
  });
  const categories = useQuery({
    queryKey: queryKeys.gradebook.categories(courseId),
    queryFn: () => listCategories(courseId),
    enabled: Boolean(courseId)
  });
  const schemes = useQuery({
    queryKey: queryKeys.gradebook.schemes(courseId),
    queryFn: () => listGradingSchemes(courseId),
    enabled: Boolean(courseId)
  });

  const gradeItems = items.data ?? [];
  const gradeEntries = grades.data?.entries ?? [];
  const gradedEntries = gradeEntries.filter((entry) => scoreFor(entry) !== undefined && scoreFor(entry) !== null);
  const selectedGradeItemIds = new Set(gradeEntries.map((entry) => entry.gradeItemId));
  const missingGradeItems = gradeItems.filter((item) => !selectedGradeItemIds.has(item.id));
  const averagePercent = gradedEntries.length
    ? Math.round(
        gradedEntries.reduce((sum, entry) => sum + (entryPercent(entry) ?? 0), 0) / gradedEntries.length
      )
    : null;
  const categoryWeightTotal = (categories.data ?? []).reduce(
    (sum, category) => sum + (category.weightPercent ?? 0),
    0
  );

  const [entry, setEntry] = useState({
    gradeItemId: "",
    rawScore: "",
    isLate: false,
    minutesLate: ""
  });
  const selectedItem = gradeItems.find((item) => item.id === entry.gradeItemId);
  const rawScore = Number(entry.rawScore);
  const scoreIsInvalid = entry.rawScore.trim() === "" || Number.isNaN(rawScore);
  const scoreExceedsMax = selectedItem?.maxScore !== undefined && rawScore > selectedItem.maxScore;

  const create = useMutation({
    mutationFn: () =>
      upsertEntry({
        gradeItemId: entry.gradeItemId,
        studentId,
        rawScore,
        isLate: entry.isLate,
        minutesLate: entry.isLate && entry.minutesLate !== "" ? Number(entry.minutesLate) : undefined
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.gradebook.student(courseId, studentId) });
      qc.invalidateQueries({ queryKey: queryKeys.gradebook.items(courseId) });
      setEntry((current) => ({ ...current, rawScore: "", minutesLate: "" }));
    }
  });

  const finalize = useMutation({
    mutationFn: () => finalizeGrade(courseId, studentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.gradebook.student(courseId, studentId) });
    }
  });

  const [categoriesOpen, setCategoriesOpen] = useState(false);
  const [categoryForm, setCategoryForm] = useState({
    name: "",
    weightPercent: 0,
    aggregationMethod: "WEIGHTED_MEAN",
    dropLowest: 0
  });
  const createCategoryMutation = useMutation({
    mutationFn: () =>
      createCategory(courseId, {
        name: categoryForm.name,
        weightPercent: categoryForm.weightPercent,
        aggregationMethod: categoryForm.aggregationMethod || undefined,
        dropLowest: categoryForm.dropLowest || undefined
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.gradebook.categories(courseId) });
      setCategoryForm({ name: "", weightPercent: 0, aggregationMethod: "WEIGHTED_MEAN", dropLowest: 0 });
    }
  });

  const [schemesOpen, setSchemesOpen] = useState(false);
  const [schemeForm, setSchemeForm] = useState({
    name: "Default percentage scale",
    isDefault: false,
    entries: "A:90\nB:80\nC:70\nD:60\nF:0"
  });
  const parsedSchemeEntries = useMemo(
    () =>
      schemeForm.entries
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const [letter, minPercent] = line.split(":");
          return { letter: letter.trim(), minPercent: Number(minPercent) };
        }),
    [schemeForm.entries]
  );
  const schemeEntriesInvalid = parsedSchemeEntries.some(
    (item) => !item.letter || Number.isNaN(item.minPercent)
  );
  const createScheme = useMutation({
    mutationFn: () =>
      createGradingScheme(courseId, {
        name: schemeForm.name,
        isDefault: schemeForm.isDefault,
        entries: parsedSchemeEntries
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.gradebook.schemes(courseId) });
      setSchemeForm({
        name: "Default percentage scale",
        isDefault: false,
        entries: "A:90\nB:80\nC:70\nD:60\nF:0"
      });
    }
  });

  return (
    <div>
      <PageHeader
        title="Bảng điểm"
        description="Quản lý hạng mục điểm, nhập điểm học viên, kiểm tra trọng số và finalize kết quả cuối khóa."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" disabled={!courseId} onClick={() => exportGradebook(courseId)}>
              <Download size={16} />
              Xuất CSV
            </Button>
            <Button
              disabled={!courseId || !studentId || finalize.isPending}
              onClick={() => finalize.mutate()}
            >
              <FileCheck2 size={16} />
              {finalize.isPending ? "Đang chốt" : "Chốt điểm"}
            </Button>
          </div>
        }
      />

      <Card className="mb-4">
        <CardHeader
          title="Phạm vi chấm điểm"
          subtitle="Chọn course và học viên một lần, toàn bộ bảng điểm bên dưới sẽ bám theo scope này."
        />
        <div className="grid gap-4 p-4 xl:grid-cols-[1.4fr_1fr]">
          <div className="grid gap-3 lg:grid-cols-2">
            <FormField label="Khóa học" htmlFor="g-course-select">
              <Select
                id="g-course-select"
                value={courseId}
                onChange={(event) => updateScope(event.target.value)}
              >
                <option value="">Chọn khóa học</option>
                {courseRows.map((course) => (
                  <option key={course.id} value={course.id}>
                    {courseLabel(course)}
                  </option>
                ))}
                {courseId && !selectedCourse && <option value={courseId}>Course {compactId(courseId)}</option>}
              </Select>
            </FormField>
            <FormField label="Học viên" htmlFor="g-student-select" hint={learnerHint}>
              <Select
                id="g-student-select"
                value={studentId}
                onChange={(event) => updateScope(courseId, event.target.value)}
                disabled={usersQuery.isLoading && learnerRows.length === 0}
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
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600 lg:col-span-2">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Khóa học</p>
                  <p className="mt-1 font-semibold text-slate-900">
                    {selectedCourse ? courseLabel(selectedCourse) : courseId ? `Course ${compactId(courseId)}` : "Chưa chọn khóa học"}
                  </p>
                  <p className="mt-1 leading-5">
                    {selectedCourse?.summary || "Chọn course để tải hạng mục, trọng số và thang điểm."}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Học viên</p>
                  <p className="mt-1 font-semibold text-slate-900">{selectedLearnerLabel}</p>
                  <p className="mt-1 leading-5">
                    {studentId ? "Bảng điểm, nhập điểm và chốt điểm đang bám theo học viên này." : "Chọn học viên để xem tiến độ chấm."}
                  </p>
                </div>
              </div>
              {courses.isError && (
                <p className="mt-3 text-xs font-semibold text-amber-700">
                  Không tải được danh sách course, đang dùng fallback local.
                </p>
              )}
            </div>
            <details className="rounded-lg border border-dashed border-slate-200 bg-white p-3 text-sm text-slate-600 lg:col-span-2">
              <summary className="cursor-pointer font-semibold text-slate-700">Nhập ID thủ công</summary>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <FormField label="Course ID" htmlFor="g-course-manual" hint="Dùng khi course chưa có trong dropdown.">
                  <Input
                    id="g-course-manual"
                    value={courseId}
                    onChange={(event) => updateScope(event.target.value.trim())}
                    placeholder="UUID khóa học"
                  />
                </FormField>
                <FormField label="Học viên ID" htmlFor="g-student-manual" hint="Dùng khi learner chưa có trong dropdown.">
                  <Input
                    id="g-student-manual"
                    value={studentId}
                    onChange={(event) => updateScope(courseId, event.target.value.trim())}
                    placeholder="VD: 4"
                  />
                </FormField>
              </div>
            </details>
          </div>
          <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-1">
            {DEMO_SCOPES.map((scope) => (
              <ScopeButton
                key={`${scope.courseId}-${scope.studentId}`}
                scope={scope}
                active={scope.courseId === courseId && scope.studentId === studentId}
                onClick={() => updateScope(scope.courseId, scope.studentId)}
              />
            ))}
          </div>
        </div>
      </Card>

      <div className="mb-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Calculator}
          label="Hạng mục điểm"
          value={courseId ? String(gradeItems.length) : "—"}
          detail={courseId ? `${missingGradeItems.length} mục chưa có điểm cho học viên này.` : "Chọn khóa học để tải."}
        />
        <MetricCard
          icon={UserCheck}
          label="Điểm đã nhập"
          value={studentId ? `${gradedEntries.length}/${gradeEntries.length || gradeItems.length}` : "—"}
          detail={studentId ? "Tính theo bảng điểm hiện tại của học viên." : "Nhập học viên để xem tiến độ chấm."}
          tone="emerald"
        />
        <MetricCard
          icon={Trophy}
          label="Điểm tổng kết"
          value={`${formatNumber(grades.data?.finalScore)}${grades.data?.finalLetter ? ` ${grades.data.finalLetter}` : ""}`}
          detail={grades.data?.gradingSchemeName ?? "Sẽ hiển thị sau khi có bảng điểm học viên."}
          tone="sky"
        />
        <MetricCard
          icon={GraduationCap}
          label="Trọng số category"
          value={courseId ? `${formatNumber(categoryWeightTotal, "%")}` : "—"}
          detail={averagePercent !== null ? `Trung bình các mục đã có điểm: ${averagePercent}%.` : "Nên đạt 100% trước khi finalize."}
          tone={categoryWeightTotal === 100 ? "emerald" : "amber"}
        />
      </div>

      {finalize.isError && <ErrorState error={finalize.error} />}
      {finalize.isSuccess && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">
          <CheckCircle2 size={17} />
          Đã chốt điểm cuối khóa cho học viên.
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader
            title="Hạng mục điểm"
            subtitle="Chọn một dòng để đưa vào form nhập điểm, không cần copy UUID."
          />
          {!courseId && <EmptyState message="Chọn course để xem hạng mục điểm." />}
          {courseId && items.isLoading && <Spinner />}
          {items.isError && <ErrorState error={items.error} />}
          {items.data && items.data.length === 0 && <EmptyState message="Không có hạng mục điểm cho course này." />}
          {items.data && items.data.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Hạng mục</Th>
                  <Th>Loại</Th>
                  <Th>Trọng số</Th>
                  <Th>Tối đa</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {items.data.map((item) => (
                  <tr
                    key={item.id}
                    className={cn(item.id === entry.gradeItemId && "bg-brand-50/60")}
                  >
                    <Td>
                      <p className="font-semibold text-slate-900">{item.title}</p>
                      <p className="mt-1 text-xs text-slate-500">{gradeItemMeta(item) || item.id}</p>
                    </Td>
                    <Td>
                      <Badge value={item.sourceType ?? "MANUAL"} />
                    </Td>
                    <Td>{formatNumber(item.itemWeightPercent ?? item.categoryWeightPercent, "%")}</Td>
                    <Td>{formatNumber(item.maxScore)}</Td>
                    <Td>
                      <Button
                        size="sm"
                        variant={item.id === entry.gradeItemId ? "primary" : "secondary"}
                        onClick={() => setEntry((current) => ({ ...current, gradeItemId: item.id }))}
                      >
                        Chọn
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader title="Nhập điểm nhanh" subtitle="Form tự khóa khi thiếu course, học viên hoặc mục điểm." />
          <form
            className="space-y-4 p-4"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              create.mutate();
            }}
          >
            <FormField label="Mục điểm" htmlFor="ge-item">
              <Select
                id="ge-item"
                value={entry.gradeItemId}
                onChange={(event) => setEntry({ ...entry, gradeItemId: event.target.value })}
                required
              >
                <option value="">Chọn hạng mục</option>
                {gradeItems.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title}
                  </option>
                ))}
              </Select>
            </FormField>
            {selectedItem && (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <p className="font-semibold text-slate-900">{selectedItem.title}</p>
                <p className="mt-1 text-slate-500">
                  Max {formatNumber(selectedItem.maxScore)} · {gradeItemMeta(selectedItem) || selectedItem.id}
                </p>
              </div>
            )}
            <FormField label="Điểm thô" htmlFor="ge-score">
              <Input
                id="ge-score"
                type="number"
                min="0"
                step="0.01"
                value={entry.rawScore}
                onChange={(event) => setEntry({ ...entry, rawScore: event.target.value })}
                required
              />
            </FormField>
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
              <input
                type="checkbox"
                checked={entry.isLate}
                onChange={(event) => setEntry({ ...entry, isLate: event.target.checked })}
              />
              Nộp trễ
            </label>
            {entry.isLate && (
              <FormField label="Số phút trễ" htmlFor="ge-late">
                <Input
                  id="ge-late"
                  type="number"
                  min="0"
                  value={entry.minutesLate}
                  onChange={(event) => setEntry({ ...entry, minutesLate: event.target.value })}
                />
              </FormField>
            )}
            {scoreExceedsMax && (
              <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <AlertTriangle size={17} className="mt-0.5 shrink-0" />
                Điểm đang lớn hơn điểm tối đa của hạng mục. Bạn vẫn có thể lưu nếu đây là điểm bonus.
              </div>
            )}
            {create.isError && <ErrorState error={create.error} />}
            {create.isSuccess && (
              <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">
                Đã lưu điểm và làm mới bảng điểm học viên.
              </p>
            )}
            <Button
              type="submit"
              className="w-full"
              disabled={
                create.isPending ||
                !courseId ||
                !studentId ||
                !entry.gradeItemId ||
                scoreIsInvalid
              }
            >
              <Save size={16} />
              {create.isPending ? "Đang lưu" : "Lưu điểm"}
            </Button>
          </form>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader
            title="Điểm học viên"
            subtitle="Theo dõi từng entry, late penalty và trạng thái publish."
          />
          {!(courseId && studentId) && <EmptyState message="Chọn course và học viên để xem bảng điểm." />}
          {courseId && studentId && grades.isLoading && <Spinner />}
          {grades.isError && <ErrorState error={grades.error} />}
          {grades.data && grades.data.entries.length === 0 && <EmptyState message="Học viên chưa có điểm." />}
          {grades.data && grades.data.entries.length > 0 && (
            <Table>
              <thead>
                <tr>
                  <Th>Hạng mục</Th>
                  <Th>Điểm</Th>
                  <Th>%</Th>
                  <Th>Late</Th>
                  <Th>Trạng thái</Th>
                </tr>
              </thead>
              <tbody>
                {grades.data.entries.map((grade) => (
                  <tr key={grade.id}>
                    <Td>
                      <p className="font-semibold text-slate-900">{grade.title ?? grade.gradeItemId}</p>
                      <p className="mt-1 text-xs text-slate-500">{grade.categoryName ?? grade.gradeItemId}</p>
                    </Td>
                    <Td>
                      {formatNumber(scoreFor(grade))} / {formatNumber(grade.maxScore)}
                      {grade.letter ? <span className="ml-2 font-semibold text-slate-700">{grade.letter}</span> : null}
                    </Td>
                    <Td>{entryPercent(grade) !== null ? `${entryPercent(grade)}%` : "—"}</Td>
                    <Td>
                      {grade.isLate ? (
                        <span className="text-amber-700">
                          {grade.minutesLate ?? 0} phút · -{formatNumber(grade.latePenaltyApplied, "%")}
                        </span>
                      ) : (
                        "Đúng hạn"
                      )}
                    </Td>
                    <Td>
                      <Badge value={grade.status ?? "DRAFT"} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader
            title="Hạng mục & trọng số"
            subtitle={courseId ? `Tổng trọng số hiện tại: ${formatNumber(categoryWeightTotal, "%")}` : "Chọn course để cấu hình."}
            actions={
              <Button variant="secondary" onClick={() => setCategoriesOpen((open) => !open)}>
                {categoriesOpen ? "Thu gọn" : "Mở cấu hình"}
              </Button>
            }
          />
          {categoriesOpen && (
            <div className="space-y-4 p-4">
              {!courseId && <EmptyState message="Chọn course để xem hạng mục." />}
              {courseId && categories.isLoading && <Spinner />}
              {categories.isError && <ErrorState error={categories.error} />}
              {categories.data && categories.data.length === 0 && <EmptyState message="Chưa có hạng mục." />}
              {categories.data && categories.data.length > 0 && (
                <Table>
                  <thead>
                    <tr>
                      <Th>Tên</Th>
                      <Th>Trọng số</Th>
                      <Th>Cách tính</Th>
                      <Th>Bỏ điểm thấp</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {categories.data.map((category) => (
                      <tr key={category.id}>
                        <Td>{category.name}</Td>
                        <Td>{formatNumber(category.weightPercent, "%")}</Td>
                        <Td>{category.aggregationMethod ?? "—"}</Td>
                        <Td>{category.dropLowest ?? 0}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
              <form
                className="grid gap-3 border-t pt-4 lg:grid-cols-[1.2fr_0.6fr_0.8fr_0.6fr_auto]"
                onSubmit={(event: FormEvent) => {
                  event.preventDefault();
                  createCategoryMutation.mutate();
                }}
              >
                <FormField label="Tên hạng mục" htmlFor="cat-name">
                  <Input
                    id="cat-name"
                    value={categoryForm.name}
                    onChange={(event) => setCategoryForm({ ...categoryForm, name: event.target.value })}
                    required
                  />
                </FormField>
                <FormField label="Trọng số (%)" htmlFor="cat-weight">
                  <Input
                    id="cat-weight"
                    type="number"
                    min="0"
                    max="100"
                    value={categoryForm.weightPercent}
                    onChange={(event) => setCategoryForm({ ...categoryForm, weightPercent: Number(event.target.value) })}
                    required
                  />
                </FormField>
                <FormField label="Cách tính" htmlFor="cat-method">
                  <Select
                    id="cat-method"
                    value={categoryForm.aggregationMethod}
                    onChange={(event) => setCategoryForm({ ...categoryForm, aggregationMethod: event.target.value })}
                  >
                    {AGGREGATION_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </FormField>
                <FormField label="Bỏ thấp" htmlFor="cat-drop">
                  <Input
                    id="cat-drop"
                    type="number"
                    min="0"
                    value={categoryForm.dropLowest}
                    onChange={(event) => setCategoryForm({ ...categoryForm, dropLowest: Number(event.target.value) })}
                  />
                </FormField>
                <div className="flex items-end">
                  <Button type="submit" disabled={createCategoryMutation.isPending || !courseId}>
                    {createCategoryMutation.isPending ? "Đang tạo" : "Tạo"}
                  </Button>
                </div>
                {createCategoryMutation.isError && <ErrorState error={createCategoryMutation.error} />}
                {createCategoryMutation.isSuccess && (
                  <p className="text-sm font-semibold text-emerald-600">Đã tạo hạng mục.</p>
                )}
              </form>
            </div>
          )}
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader
            title="Thang điểm"
            subtitle="Định nghĩa letter grade để tính final letter nhất quán."
            actions={
              <Button variant="secondary" onClick={() => setSchemesOpen((open) => !open)}>
                {schemesOpen ? "Thu gọn" : "Mở cấu hình"}
              </Button>
            }
          />
          {schemesOpen && (
            <div className="space-y-4 p-4">
              {!courseId && <EmptyState message="Chọn course để xem thang điểm." />}
              {courseId && schemes.isLoading && <Spinner />}
              {schemes.isError && <ErrorState error={schemes.error} />}
              {schemes.data && schemes.data.length === 0 && <EmptyState message="Chưa có thang điểm." />}
              {schemes.data && schemes.data.length > 0 && (
                <Table>
                  <thead>
                    <tr>
                      <Th>Tên</Th>
                      <Th>Mặc định</Th>
                      <Th>Bậc điểm</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {schemes.data.map((scheme) => (
                      <tr key={scheme.id}>
                        <Td>{scheme.name}</Td>
                        <Td>{scheme.isDefault ? "Có" : "Không"}</Td>
                        <Td>{scheme.entries.map((entry) => `${entry.letter}:${entry.minPercent}%`).join(", ")}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
              <form
                className="grid gap-3 border-t pt-4 lg:grid-cols-[0.8fr_1.2fr_auto]"
                onSubmit={(event: FormEvent) => {
                  event.preventDefault();
                  createScheme.mutate();
                }}
              >
                <FormField label="Tên thang điểm" htmlFor="sc-name">
                  <Input
                    id="sc-name"
                    value={schemeForm.name}
                    onChange={(event) => setSchemeForm({ ...schemeForm, name: event.target.value })}
                    required
                  />
                </FormField>
                <FormField label="Bậc điểm" htmlFor="sc-entries" hint="Mỗi dòng theo dạng A:90">
                  <Textarea
                    id="sc-entries"
                    value={schemeForm.entries}
                    onChange={(event) => setSchemeForm({ ...schemeForm, entries: event.target.value })}
                    required
                  />
                </FormField>
                <div className="space-y-3 lg:pt-7">
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <input
                      type="checkbox"
                      checked={schemeForm.isDefault}
                      onChange={(event) => setSchemeForm({ ...schemeForm, isDefault: event.target.checked })}
                    />
                    Mặc định
                  </label>
                  <Button
                    type="submit"
                    disabled={createScheme.isPending || !courseId || schemeEntriesInvalid}
                  >
                    {createScheme.isPending ? "Đang tạo" : "Tạo thang điểm"}
                  </Button>
                </div>
                {schemeEntriesInvalid && (
                  <p className="text-sm font-semibold text-amber-700">Có dòng bậc điểm chưa đúng định dạng.</p>
                )}
                {createScheme.isError && <ErrorState error={createScheme.error} />}
                {createScheme.isSuccess && (
                  <p className="text-sm font-semibold text-emerald-600">Đã tạo thang điểm.</p>
                )}
              </form>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
