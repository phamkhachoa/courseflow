import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Award, BadgeCheck, Ban, Search, UsersRound } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
import { adminUserLabel, useLearnerUsers } from "@/modules/identity/useLearnerUsers";
import { queryKeys } from "@/shared/api/query-keys";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Select,
  Spinner
} from "@/shared/ui";
import { getCertificateEligibility, issueCertificate, revokeCertificate, verifyCertificate } from "./api";

function compactId(value?: string) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function courseLabel(course?: Course, fallbackId?: string) {
  if (!course) return fallbackId ? `Khóa ${compactId(fallbackId)}` : "Chọn khóa học";
  return course.code ? `${course.code} · ${course.title}` : course.title;
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

export function CertificatesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedCourseId = searchParams.get("courseId") ?? "";
  const requestedStudentId = searchParams.get("studentId") ?? "";
  const [code, setCode] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [issueForm, setIssueForm] = useState({
    studentId: requestedStudentId,
    courseId: requestedCourseId,
    finalGrade: ""
  });
  const [revokeForm, setRevokeForm] = useState({ certificateId: "", reason: "" });

  function updateIssueScope(next: Partial<{ studentId: string; courseId: string }>) {
    const updated = { ...issueForm, ...next };
    setIssueForm(updated);
    setSearchParams({
      ...(updated.courseId ? { courseId: updated.courseId } : {}),
      ...(updated.studentId ? { studentId: updated.studentId } : {})
    }, { replace: true });
  }

  const courses = useQuery({
    queryKey: queryKeys.courses.list("certificate-picker"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const { learnerUsers, roleQueriesLoading, userById, usersQuery } = useLearnerUsers();

  const courseById = useMemo(() => {
    const map = new Map<string, Course>();
    for (const course of courses.data ?? []) map.set(course.id, course);
    return map;
  }, [courses.data]);

  const verify = useQuery({
    queryKey: queryKeys.certificates.verify(submitted),
    queryFn: () => verifyCertificate(submitted),
    enabled: Boolean(submitted)
  });
  const eligibility = useQuery({
    queryKey: queryKeys.certificates.eligibility(issueForm.courseId, issueForm.studentId),
    queryFn: () => getCertificateEligibility(issueForm.courseId, issueForm.studentId),
    enabled: Boolean(issueForm.courseId && issueForm.studentId)
  });

  const issue = useMutation({
    mutationFn: () =>
      issueCertificate({
        studentId: issueForm.studentId,
        courseId: issueForm.courseId,
        finalGrade: Number(eligibility.data?.finalGrade ?? issueForm.finalGrade)
      })
  });

  const revoke = useMutation({
    mutationFn: () => revokeCertificate(revokeForm.certificateId, revokeForm.reason)
  });

  const verifiedCourse = courseById.get(verify.data?.courseId ?? "");
  const verifiedUser = userById.get(verify.data?.studentId ?? "");
  const issuedCourse = courseById.get(issue.data?.courseId ?? "");
  const issuedUser = userById.get(issue.data?.studentId ?? "");
  const selectedCourse = courseById.get(issueForm.courseId);
  const selectedUser = userById.get(issueForm.studentId);
  const finalGradeValue = eligibility.data?.finalGrade ?? (issueForm.finalGrade ? Number(issueForm.finalGrade) : undefined);

  return (
    <div>
      <PageHeader
        title="Chứng chỉ"
        description="Cấp, thu hồi và xác minh chứng chỉ bằng dữ liệu học viên và khóa học có sẵn."
      />

      <div className="mb-4 grid gap-3 md:grid-cols-3">
        <Metric
          icon={<Award size={18} />}
          label="Khóa có thể cấp"
          value={String(courses.data?.length ?? 0)}
          detail={courses.isLoading ? "Đang tải catalog" : "Chọn trực tiếp theo mã và tên khóa"}
        />
        <Metric
          icon={<UsersRound size={18} />}
          label="Learner"
          value={String(learnerUsers.length)}
          detail={usersQuery.isLoading || roleQueriesLoading ? "Đang phân loại learner" : "Không lẫn tài khoản instructor"}
        />
        <Metric
          icon={<BadgeCheck size={18} />}
          label="Mã xác minh"
          value={submitted ? "Đã nhập" : "—"}
          detail={submitted ? compactId(submitted) : "Dùng để tra cứu chứng chỉ đã cấp"}
        />
      </div>

      <Card className="mb-4">
        <CardHeader title="Xác minh theo mã" subtitle="Tra cứu trạng thái chứng chỉ và đối chiếu với tên học viên, khóa học." />
        <form
          className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setSubmitted(code.trim());
          }}
        >
          <FormField label="Mã xác minh" htmlFor="c-code">
            <Input id="c-code" value={code} onChange={(e) => setCode(e.target.value)} required />
          </FormField>
          <Button type="submit" className="self-end">
            <Search size={16} />
            Xác minh
          </Button>
        </form>
        {verify.isLoading && <Spinner />}
        {verify.isError && <ErrorState error={verify.error} />}
        {verify.data && (
          <div className="grid gap-3 px-4 pb-4 md:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-bold uppercase text-slate-400">Mã</p>
              <p className="mt-2 font-semibold text-slate-900">{verify.data.verificationCode}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 md:col-span-2">
              <p className="text-xs font-bold uppercase text-slate-400">Học viên</p>
              <p className="mt-2 font-semibold text-slate-900">
                {adminUserLabel(verifiedUser, compactId(verify.data.studentId))}
              </p>
              <p className="mt-1 text-xs text-slate-500">ID {compactId(verify.data.studentId)}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-bold uppercase text-slate-400">Trạng thái</p>
              <div className="mt-2">
                <Badge value={verify.data.status} />
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 md:col-span-4">
              <p className="text-xs font-bold uppercase text-slate-400">Khóa học</p>
              <p className="mt-2 font-semibold text-slate-900">
                {courseLabel(verifiedCourse, verify.data.courseId)}
              </p>
              <p className="mt-1 text-xs text-slate-500">ID {compactId(verify.data.courseId)}</p>
            </div>
          </div>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <Card>
          <CardHeader title="Cấp chứng chỉ" subtitle="Chọn learner và course, kiểm tra eligibility rồi cấp mã xác minh." />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              issue.mutate();
            }}
          >
            <div className="grid gap-3 md:grid-cols-2">
              <FormField label="Học viên" htmlFor="i-student">
                <Select
                  id="i-student"
                  value={issueForm.studentId}
                  onChange={(e) => updateIssueScope({ studentId: e.target.value })}
                  required
                >
                  <option value="">Chọn học viên</option>
                  {learnerUsers.map((user) => (
                    <option key={user.id} value={String(user.id)}>
                      {adminUserLabel(user)}
                    </option>
                  ))}
                  {issueForm.studentId && !selectedUser && (
                    <option value={issueForm.studentId}>Học viên {compactId(issueForm.studentId)}</option>
                  )}
                </Select>
              </FormField>
              <FormField label="Khóa học" htmlFor="i-course">
                <Select
                  id="i-course"
                  value={issueForm.courseId}
                  onChange={(e) => updateIssueScope({ courseId: e.target.value })}
                  required
                >
                  <option value="">Chọn khóa học</option>
                  {(courses.data ?? []).map((course) => (
                    <option key={course.id} value={course.id}>
                      {courseLabel(course)}
                    </option>
                  ))}
                  {issueForm.courseId && !selectedCourse && (
                    <option value={issueForm.courseId}>Khóa {compactId(issueForm.courseId)}</option>
                  )}
                </Select>
              </FormField>
            </div>

            {(selectedUser || selectedCourse) && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                <p className="font-semibold text-slate-900">
                  {selectedUser ? adminUserLabel(selectedUser) : "Chưa chọn học viên"}
                </p>
                <p className="mt-1 text-slate-500">
                  {selectedCourse ? courseLabel(selectedCourse) : "Chưa chọn khóa học"}
                </p>
              </div>
            )}

            {eligibility.isLoading && <Spinner />}
            {eligibility.isError && <ErrorState error={eligibility.error} />}
            {eligibility.data && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900">Eligibility checklist</p>
                    <p className="mt-1 text-slate-500">
                      Final grade {eligibility.data.finalGrade ?? "—"} · Threshold {eligibility.data.gradeThreshold ?? "—"}
                    </p>
                  </div>
                  <Badge value={eligibility.data.status} />
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-3">
                  <div className="rounded-md border border-slate-200 bg-white p-2">
                    <p className="text-xs font-bold uppercase text-slate-400">Completion</p>
                    <Badge value={eligibility.data.completionEligible ? "READY" : "DRAFT"} label={eligibility.data.completionEligible ? "Đạt" : "Chưa đạt"} />
                  </div>
                  <div className="rounded-md border border-slate-200 bg-white p-2">
                    <p className="text-xs font-bold uppercase text-slate-400">Required items</p>
                    <Badge value={eligibility.data.requiredItemsEligible ? "READY" : "DRAFT"} label={eligibility.data.requiredItemsEligible ? "Đạt" : "Chưa đạt"} />
                  </div>
                  <div className="rounded-md border border-slate-200 bg-white p-2">
                    <p className="text-xs font-bold uppercase text-slate-400">Final grade</p>
                    <Badge value={eligibility.data.gradeEligible ? "READY" : "DRAFT"} label={eligibility.data.finalGradeStatus ?? (eligibility.data.gradeEligible ? "Đạt" : "Chưa đạt")} />
                  </div>
                </div>
                {eligibility.data.missingRequirements.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {eligibility.data.missingRequirements.map((item) => (
                      <div key={item.code} className="rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-800">
                        <p className="font-semibold">{item.label}</p>
                        {item.detail && <p className="mt-1 text-xs">{item.detail}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <FormField
              label="Điểm tổng kết"
              htmlFor="i-grade"
              hint={eligibility.data?.finalGrade != null ? "Lấy từ final grade đã chốt trong gradebook." : "Chỉ nhập khi eligibility chưa trả final grade."}
            >
              <Input
                id="i-grade"
                type="number"
                min="0"
                step="0.01"
                value={eligibility.data?.finalGrade ?? issueForm.finalGrade}
                onChange={(e) => setIssueForm({ ...issueForm, finalGrade: e.target.value })}
                readOnly={eligibility.data?.finalGrade != null}
                required={eligibility.data?.finalGrade == null}
              />
            </FormField>
            {(courses.isError || usersQuery.isError) && (
              <div className="grid gap-3 md:grid-cols-2">
                {courses.isError && <ErrorState error={courses.error} />}
                {usersQuery.isError && <ErrorState error={usersQuery.error} />}
              </div>
            )}
            {issue.isError && <ErrorState error={issue.error} />}
            {issue.isSuccess && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                <p className="font-bold">Đã cấp chứng chỉ</p>
                <p className="mt-1">Mã xác minh: {issue.data?.verificationCode}</p>
                <p className="mt-1">{adminUserLabel(issuedUser, compactId(issue.data?.studentId))}</p>
                <p>{courseLabel(issuedCourse, issue.data?.courseId)}</p>
              </div>
            )}
            <Button
              type="submit"
              disabled={
                issue.isPending ||
                !issueForm.studentId ||
                !issueForm.courseId ||
                !finalGradeValue ||
                !eligibility.data?.eligible ||
                eligibility.data?.issued
              }
            >
              <Award size={16} />
              {issue.isPending ? "Đang cấp" : "Cấp chứng chỉ"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title="Thu hồi chứng chỉ" subtitle="Thu hồi bằng certificate ID khi phát hiện cấp sai hoặc cần khóa hiệu lực." />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              revoke.mutate();
            }}
          >
            <FormField label="Certificate ID" htmlFor="r-id" hint="Có thể lấy từ kết quả cấp hoặc dữ liệu backend.">
              <Input
                id="r-id"
                value={revokeForm.certificateId}
                onChange={(e) => setRevokeForm({ ...revokeForm, certificateId: e.target.value })}
                required
              />
            </FormField>
            <FormField label="Lý do" htmlFor="r-reason">
              <Input
                id="r-reason"
                value={revokeForm.reason}
                onChange={(e) => setRevokeForm({ ...revokeForm, reason: e.target.value })}
                required
              />
            </FormField>
            {revoke.isError && <ErrorState error={revoke.error} />}
            {revoke.isSuccess && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">
                Đã thu hồi chứng chỉ {compactId(revoke.data?.certificateId)}
              </div>
            )}
            <Button type="submit" variant="danger" disabled={revoke.isPending || !revokeForm.certificateId || !revokeForm.reason}>
              <Ban size={16} />
              {revoke.isPending ? "Đang thu hồi" : "Thu hồi"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
