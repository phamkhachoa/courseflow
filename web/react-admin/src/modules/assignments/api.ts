import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type Assignment = {
  id: string;
  courseId: string;
  title: string;
  assignmentType?: string;
  instructions?: string;
  availableAt?: string;
  dueAt?: string;
  lockAt?: string;
  maxScore?: number;
  status?: string;
  submissionTypes?: string;
  maxAttempts?: number;
  allowResubmission?: boolean;
  latePenaltyPercent?: number;
  latePenaltyInterval?: string;
  latePenaltyMaxPercent?: number;
  rubricId?: string;
};

export type AssignmentLifecycleAction = "draft" | "publish" | "archive";

const lifecycleStatus: Record<AssignmentLifecycleAction, string> = {
  draft: "DRAFT",
  publish: "PUBLISHED",
  archive: "ARCHIVED"
};

function isLifecycleEndpointMissing(error: unknown) {
  const status = (error as { response?: { status?: number } }).response?.status;
  return status === 404 || status === 405;
}

export type SubmissionAttachment = {
  id: string;
  mediaAssetId?: string;
  fileName: string;
  storageKey: string;
  contentType?: string;
  sizeBytes?: number;
  createdAt?: string;
};

export type Submission = {
  id: string;
  assignmentId: string;
  studentId: string;
  attemptNo: number;
  submittedAt?: string;
  status?: string;
  submissionText?: string;
  submissionUrl?: string;
  isLate?: boolean;
  minutesLate?: number;
  rawScore?: number;
  latePenaltyApplied?: number;
  finalScore?: number;
  graderId?: string;
  gradedAt?: string;
  feedback?: string;
  attachments?: SubmissionAttachment[];
};

export type GradingQueueItem = {
  submissionId: string;
  assignmentId: string;
  assignmentTitle: string;
  courseId: string;
  studentId: string;
  attemptNo: number;
  submittedAt?: string;
  status: string;
  isLate: boolean;
  minutesLate: number;
  maxScore?: number;
  rubricId?: string;
  attachmentCount: number;
};

export type RubricCriterion = {
  id: string;
  name: string;
  description?: string;
  maxPoints: number;
  position?: number;
};

export type Rubric = {
  id: string;
  assignmentId: string;
  title: string;
  maxScore: number;
  criteria: RubricCriterion[];
};

export async function listAssignments(courseId: string): Promise<Assignment[]> {
  const { data } = await apiClient.get("/admin/v1/assignments", { params: { courseId } });
  return unwrapList<Assignment>(data);
}
export async function getAssignment(id: string): Promise<Assignment> {
  const { data } = await apiClient.get(`/admin/v1/assignments/${id}`);
  return unwrap<Assignment>(data);
}
export async function createAssignment(input: {
  courseId: string;
  title: string;
  assignmentType: string;
  instructions?: string;
  dueAt: string;
  maxScore: number;
  submissionTypes?: string;
}): Promise<Assignment> {
  const { data } = await apiClient.post("/admin/v1/assignments", input);
  return unwrap<Assignment>(data);
}

export async function setAssignmentLifecycle(
  assignmentId: string,
  action: AssignmentLifecycleAction
): Promise<Assignment> {
  try {
    const { data } = await apiClient.post(`/admin/v1/assignments/${assignmentId}/${action}`, {});
    return unwrap<Assignment>(data);
  } catch (error) {
    if (!isLifecycleEndpointMissing(error)) throw error;
    const { data } = await apiClient.patch(`/admin/v1/assignments/${assignmentId}/status`, {
      status: lifecycleStatus[action]
    });
    return unwrap<Assignment>(data);
  }
}
export async function submitAssignment(
  assignmentId: string,
  input: { submissionText?: string; submissionUrl?: string }
): Promise<Submission> {
  // studentId is taken from the gateway identity, never sent in the body.
  const { data } = await apiClient.post(`/admin/v1/assignments/${assignmentId}/submissions`, input);
  return unwrap<Submission>(data);
}

export async function listSubmissions(assignmentId: string, studentId: string): Promise<Submission[]> {
  const { data } = await apiClient.get(`/admin/v1/assignments/${assignmentId}/submissions`, {
    params: { studentId }
  });
  return unwrapList<Submission>(data);
}

export async function listGradingQueue(courseId: string, limit = 50): Promise<GradingQueueItem[]> {
  const { data } = await apiClient.get("/admin/v1/assignments/grading-queue", {
    params: { courseId, limit }
  });
  return unwrapList<GradingQueueItem>(data);
}

export type RubricScore = {
  criterionId: string;
  points: number;
  comment?: string;
};

export async function gradeSubmission(
  submissionId: string,
  input: { rawScore?: number; feedback?: string; rubricScores?: RubricScore[] }
): Promise<Submission> {
  // graderId is taken from the authenticated instructor/admin, never sent in the body.
  const { data } = await apiClient.post(`/admin/v1/submissions/${submissionId}/grade`, input);
  return unwrap<Submission>(data);
}

export async function getRubric(assignmentId: string): Promise<Rubric> {
  const { data } = await apiClient.get(`/admin/v1/assignments/${assignmentId}/rubric`);
  return unwrap<Rubric>(data);
}

export async function upsertRubric(
  assignmentId: string,
  input: { title: string; maxScore: number; criteria: { name: string; description?: string; maxPoints: number }[] }
): Promise<Rubric> {
  const { data } = await apiClient.put(`/admin/v1/assignments/${assignmentId}/rubric`, input);
  return unwrap<Rubric>(data);
}
