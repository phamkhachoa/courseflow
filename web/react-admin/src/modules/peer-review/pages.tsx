import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
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
  Spinner,
  Textarea
} from "@/shared/ui";
import { fallbackCourses, listCourses } from "../courses/api";
import { listAssignments, listSubmissions } from "../assignments/api";
import { adminUserLabel, useLearnerUsers } from "../identity/useLearnerUsers";
import { assignReview, finalizeResults, getSettings, listMyReviewAssignments, submitReview } from "./api";

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function courseLabel(course?: { code?: string; title?: string }, fallbackId?: string) {
  if (course) return [course.code, course.title].filter(Boolean).join(" · ");
  return fallbackId ? `Course ${compactId(fallbackId)}` : "Chưa chọn khóa học";
}

function assignmentLabel(assignment?: { title?: string; id?: string }, fallbackId?: string) {
  if (assignment?.title) return assignment.title;
  return fallbackId ? `Assignment ${compactId(fallbackId)}` : "Chưa chọn assignment";
}

function dateLabel(value?: string) {
  return value ? new Date(value).toLocaleString("vi-VN") : "chưa nộp";
}

function submissionLabel(submission?: { id: string; attemptNo?: number; submittedAt?: string; status?: string }, fallbackId?: string) {
  if (submission) {
    return `Lần ${submission.attemptNo ?? 1} · ${submission.status ?? "SUBMITTED"} · ${dateLabel(submission.submittedAt)}`;
  }
  return fallbackId ? `Submission ${compactId(fallbackId)}` : "Chọn bài nộp";
}

function reviewAssignmentLabel(
  reviewAssignment: { id: string; assignmentId: string; submissionId: string; status?: string; assignedAt?: string },
  assignment?: { title?: string; id?: string }
) {
  return `${assignmentLabel(assignment, reviewAssignment.assignmentId)} · ${reviewAssignment.status ?? "ASSIGNED"} · ${dateLabel(reviewAssignment.assignedAt)}`;
}

export function PeerReviewPage() {
  const { learnerUsers, roleQueriesLoading, userById, usersQuery } = useLearnerUsers();
  const [courseId, setCourseId] = useState("");
  const [assignmentId, setAssignmentId] = useState("");
  const [submitted, setSubmitted] = useState("");
  const courses = useQuery({
    queryKey: queryKeys.courses.list("peer-review"),
    queryFn: () => listCourses(),
    retry: 1,
    staleTime: 60_000
  });
  const assignments = useQuery({
    queryKey: queryKeys.assignments.list(courseId),
    queryFn: () => listAssignments(courseId),
    enabled: Boolean(courseId),
    retry: 1
  });
  const settings = useQuery({
    queryKey: queryKeys.peerReview.settings(submitted),
    queryFn: () => getSettings(submitted),
    enabled: Boolean(submitted)
  });
  const reviewAssignments = useQuery({
    queryKey: ["peer-review", "review-assignments", "mine"],
    queryFn: listMyReviewAssignments,
    retry: 1,
    staleTime: 60_000
  });

  const [assignForm, setAssignForm] = useState({
    assignmentId: "",
    submissionId: "",
    reviewerId: "",
    revieweeId: ""
  });
  const assign = useMutation({ mutationFn: () => assignReview(assignForm) });

  const [reviewForm, setReviewForm] = useState({ reviewAssignmentId: "", score: 0, comment: "" });
  const review = useMutation({
    mutationFn: () => submitReview(reviewForm.reviewAssignmentId, { score: reviewForm.score, comment: reviewForm.comment })
  });

  const [finalizeForm, setFinalizeForm] = useState({ assignmentId: "", revieweeId: "", submissionId: "" });
  const finalize = useMutation({ mutationFn: (submissionId: string) => finalizeResults(submissionId) });
  const assignSubmissions = useQuery({
    queryKey: queryKeys.assignments.submissions(assignForm.assignmentId, assignForm.revieweeId),
    queryFn: () => listSubmissions(assignForm.assignmentId, assignForm.revieweeId),
    enabled: Boolean(assignForm.assignmentId && assignForm.revieweeId),
    retry: 1,
    staleTime: 30_000
  });
  const finalizeSubmissions = useQuery({
    queryKey: queryKeys.assignments.submissions(finalizeForm.assignmentId, finalizeForm.revieweeId),
    queryFn: () => listSubmissions(finalizeForm.assignmentId, finalizeForm.revieweeId),
    enabled: Boolean(finalizeForm.assignmentId && finalizeForm.revieweeId),
    retry: 1,
    staleTime: 30_000
  });
  const courseRows = courses.data?.length ? courses.data : fallbackCourses;
  const assignmentRows = assignments.data ?? [];
  const courseById = useMemo(() => new Map(courseRows.map((course) => [course.id, course])), [courseRows]);
  const assignmentById = useMemo(() => new Map(assignmentRows.map((assignment) => [assignment.id, assignment])), [assignmentRows]);
  const selectedCourse = courseById.get(courseId);
  const selectedAssignment = assignmentById.get(assignmentId);
  const assignAssignment = assignmentById.get(assignForm.assignmentId);
  const selectedAssignSubmission = (assignSubmissions.data ?? []).find((submission) => submission.id === assignForm.submissionId);
  const finalizeAssignment = assignmentById.get(finalizeForm.assignmentId);
  const selectedFinalizeSubmission = (finalizeSubmissions.data ?? []).find((submission) => submission.id === finalizeForm.submissionId);
  const selectedReviewAssignment = (reviewAssignments.data ?? []).find((assignment) => assignment.id === reviewForm.reviewAssignmentId);
  const learnerHint =
    usersQuery.isLoading || roleQueriesLoading
      ? "Đang tải danh sách learner..."
      : usersQuery.isError
        ? "Không tải được danh sách learner."
        : `${learnerUsers.length} learner khả dụng`;

  function pickAssignment(nextAssignmentId: string) {
    setAssignmentId(nextAssignmentId);
    setAssignForm((current) => ({ ...current, assignmentId: nextAssignmentId }));
  }

  return (
    <div>
      <PageHeader title="Chấm chéo" description="Phân công reviewer, nộp đánh giá và chốt kết quả" />

      <Card className="mb-4">
        <CardHeader
          title="Tra cứu cấu hình theo assignment"
          subtitle={submitted ? assignmentLabel(assignmentById.get(submitted), submitted) : "Chọn course rồi chọn assignment cần cấu hình peer review."}
        />
        <form
          className="grid gap-3 p-4 lg:grid-cols-[1fr_1fr_auto]"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setSubmitted(assignmentId.trim());
          }}
        >
          <FormField label="Khóa học" htmlFor="pr-course">
            <Select id="pr-course" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
              <option value="">Chọn khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {courseLabel(course)}
                </option>
              ))}
              {courseId && !selectedCourse && <option value={courseId}>Course {compactId(courseId)}</option>}
            </Select>
          </FormField>
          <FormField label="Assignment" htmlFor="pr-aid">
            <Select id="pr-aid" value={assignmentId} onChange={(e) => pickAssignment(e.target.value)} required>
              <option value="">Chọn assignment</option>
              {assignmentRows.map((assignment) => (
                <option key={assignment.id} value={assignment.id}>
                  {assignmentLabel(assignment)}
                </option>
              ))}
              {assignmentId && !selectedAssignment && (
                <option value={assignmentId}>Assignment {compactId(assignmentId)}</option>
              )}
            </Select>
          </FormField>
          <div className="flex items-end">
            <Button type="submit" disabled={!assignmentId}>Xem</Button>
          </div>
        </form>
        {settings.isLoading && <Spinner />}
        {settings.isError && <ErrorState error={settings.error} />}
        {settings.data && (
          <dl className="grid grid-cols-[180px_1fr] gap-y-2 px-4 pb-4 text-sm">
            <dt className="text-slate-500">Reviewer / bài nộp</dt>
            <dd>{settings.data.reviewersPerSubmission ?? "—"}</dd>
            <dt className="text-slate-500">Ẩn danh</dt>
            <dd>{settings.data.anonymous ? "Có" : "Không"}</dd>
            <dt className="text-slate-500">Hạn đánh giá</dt>
            <dd>{settings.data.reviewDueAt ?? "—"}</dd>
            <dt className="text-slate-500">Trạng thái</dt>
            <dd>
              <Badge value={settings.data.status} />
            </dd>
          </dl>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Phân công reviewer" subtitle={assignmentLabel(assignAssignment, assignForm.assignmentId)} />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              assign.mutate();
            }}
          >
            <FormField label="Assignment" htmlFor="pa-aid">
              <Select
                id="pa-aid"
                value={assignForm.assignmentId}
                onChange={(e) => setAssignForm({ ...assignForm, assignmentId: e.target.value, submissionId: "" })}
                required
              >
                <option value="">Chọn assignment</option>
                {assignmentRows.map((assignment) => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignmentLabel(assignment)}
                  </option>
                ))}
                {assignForm.assignmentId && !assignAssignment && (
                  <option value={assignForm.assignmentId}>Assignment {compactId(assignForm.assignmentId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Reviewer" htmlFor="pa-rev" hint={learnerHint}>
              <Select
                id="pa-rev"
                value={assignForm.reviewerId}
                onChange={(e) => setAssignForm({ ...assignForm, reviewerId: e.target.value })}
                required
              >
                <option value="">Chọn reviewer</option>
                {learnerUsers.map((user) => (
                  <option key={user.id} value={String(user.id)}>
                    {adminUserLabel(user)}
                  </option>
                ))}
                {assignForm.reviewerId && !userById.has(assignForm.reviewerId) && (
                  <option value={assignForm.reviewerId}>User {compactId(assignForm.reviewerId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Reviewee" htmlFor="pa-ree">
              <Select
                id="pa-ree"
                value={assignForm.revieweeId}
                onChange={(e) => setAssignForm({ ...assignForm, revieweeId: e.target.value, submissionId: "" })}
                required
              >
                <option value="">Chọn reviewee</option>
                {learnerUsers.map((user) => (
                  <option key={user.id} value={String(user.id)}>
                    {adminUserLabel(user)}
                  </option>
                ))}
                {assignForm.revieweeId && !userById.has(assignForm.revieweeId) && (
                  <option value={assignForm.revieweeId}>User {compactId(assignForm.revieweeId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Bài nộp" htmlFor="pa-sid" hint="Danh sách lấy theo assignment và reviewee đã chọn.">
              <Select
                id="pa-sid"
                value={assignForm.submissionId}
                onChange={(e) => setAssignForm({ ...assignForm, submissionId: e.target.value })}
                required
                disabled={!assignForm.assignmentId || !assignForm.revieweeId}
              >
                <option value="">Chọn bài nộp</option>
                {(assignSubmissions.data ?? []).map((submission) => (
                  <option key={submission.id} value={submission.id}>
                    {submissionLabel(submission)}
                  </option>
                ))}
                {assignForm.submissionId && !selectedAssignSubmission && (
                  <option value={assignForm.submissionId}>Submission {compactId(assignForm.submissionId)}</option>
                )}
              </Select>
              {assignSubmissions.isLoading && <span className="text-xs text-slate-400">Đang tải bài nộp...</span>}
              {assignSubmissions.isError && <ErrorState error={assignSubmissions.error} />}
            </FormField>
            {assign.isError && <ErrorState error={assign.error} />}
            {assign.isSuccess && <p className="text-sm text-emerald-600">Đã phân công reviewer</p>}
            <Button type="submit" disabled={assign.isPending || !assignForm.assignmentId || !assignForm.submissionId || !assignForm.reviewerId || !assignForm.revieweeId}>
              {assign.isPending ? "Đang lưu" : "Phân công"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title="Nộp đánh giá" />
          <form
            className="space-y-4 p-4"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              review.mutate();
            }}
          >
            <FormField label="Review assignment" htmlFor="pr-raid">
              <Select
                id="pr-raid"
                value={reviewForm.reviewAssignmentId}
                onChange={(e) => setReviewForm({ ...reviewForm, reviewAssignmentId: e.target.value })}
                required
              >
                <option value="">Chọn lượt review được phân công</option>
                {(reviewAssignments.data ?? []).map((reviewAssignment) => (
                  <option key={reviewAssignment.id} value={reviewAssignment.id}>
                    {reviewAssignmentLabel(reviewAssignment, assignmentById.get(reviewAssignment.assignmentId))}
                  </option>
                ))}
                {reviewForm.reviewAssignmentId && !selectedReviewAssignment && (
                  <option value={reviewForm.reviewAssignmentId}>Review {compactId(reviewForm.reviewAssignmentId)}</option>
                )}
              </Select>
              {reviewAssignments.isLoading && <span className="text-xs text-slate-400">Đang tải lượt review...</span>}
              {reviewAssignments.isError && <ErrorState error={reviewAssignments.error} />}
            </FormField>
            <FormField label="Điểm" htmlFor="pr-score">
              <Input id="pr-score" type="number" value={reviewForm.score} onChange={(e) => setReviewForm({ ...reviewForm, score: Number(e.target.value) })} />
            </FormField>
            <FormField label="Nhận xét" htmlFor="pr-fb">
              <Textarea id="pr-fb" value={reviewForm.comment} onChange={(e) => setReviewForm({ ...reviewForm, comment: e.target.value })} required />
            </FormField>
            {review.isError && <ErrorState error={review.error} />}
            {review.isSuccess && <p className="text-sm text-emerald-600">Đã nộp đánh giá</p>}
            <Button type="submit" disabled={review.isPending}>
              {review.isPending ? "Đang nộp" : "Nộp đánh giá"}
            </Button>
          </form>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title="Chốt kết quả" />
          <div className="grid gap-3 p-4 lg:grid-cols-[1fr_1fr_1fr_auto]">
            <FormField label="Assignment" htmlFor="pf-aid">
              <Select
                id="pf-aid"
                value={finalizeForm.assignmentId}
                onChange={(e) => setFinalizeForm({ assignmentId: e.target.value, revieweeId: "", submissionId: "" })}
              >
                <option value="">Chọn assignment</option>
                {assignmentRows.map((assignment) => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignmentLabel(assignment)}
                  </option>
                ))}
                {finalizeForm.assignmentId && !finalizeAssignment && (
                  <option value={finalizeForm.assignmentId}>Assignment {compactId(finalizeForm.assignmentId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Reviewee" htmlFor="pf-reviewee">
              <Select
                id="pf-reviewee"
                value={finalizeForm.revieweeId}
                onChange={(e) => setFinalizeForm({ ...finalizeForm, revieweeId: e.target.value, submissionId: "" })}
                disabled={!finalizeForm.assignmentId}
              >
                <option value="">Chọn reviewee</option>
                {learnerUsers.map((user) => (
                  <option key={user.id} value={String(user.id)}>
                    {adminUserLabel(user)}
                  </option>
                ))}
                {finalizeForm.revieweeId && !userById.has(finalizeForm.revieweeId) && (
                  <option value={finalizeForm.revieweeId}>User {compactId(finalizeForm.revieweeId)}</option>
                )}
              </Select>
            </FormField>
            <FormField label="Bài nộp" htmlFor="pf-sid">
              <Select
                id="pf-sid"
                value={finalizeForm.submissionId}
                onChange={(e) => setFinalizeForm({ ...finalizeForm, submissionId: e.target.value })}
                disabled={!finalizeForm.assignmentId || !finalizeForm.revieweeId}
              >
                <option value="">Chọn bài nộp</option>
                {(finalizeSubmissions.data ?? []).map((submission) => (
                  <option key={submission.id} value={submission.id}>
                    {submissionLabel(submission)}
                  </option>
                ))}
                {finalizeForm.submissionId && !selectedFinalizeSubmission && (
                  <option value={finalizeForm.submissionId}>Submission {compactId(finalizeForm.submissionId)}</option>
                )}
              </Select>
              {finalizeSubmissions.isLoading && <span className="text-xs text-slate-400">Đang tải bài nộp...</span>}
              {finalizeSubmissions.isError && <ErrorState error={finalizeSubmissions.error} />}
            </FormField>
            <div className="flex items-end">
              <Button
                variant="danger"
                disabled={finalize.isPending || !finalizeForm.submissionId}
                onClick={() => finalize.mutate(finalizeForm.submissionId)}
              >
                {finalize.isPending ? "Đang chốt" : "Chốt kết quả"}
              </Button>
            </div>
            {finalize.isSuccess && <span className="text-sm text-emerald-600 lg:col-span-4">Đã chốt</span>}
            {finalize.isError && <span className="text-sm text-red-600 lg:col-span-4">Lỗi khi chốt</span>}
          </div>
        </Card>
      </div>
    </div>
  );
}
