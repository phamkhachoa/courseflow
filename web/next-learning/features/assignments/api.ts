import { clientFetch } from "@/shared/api/client";

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
  status: string; // SUBMITTED | GRADED | LATE
  submissionText?: string;
  submissionUrl?: string;
  isLate: boolean;
  minutesLate: number;
  rawScore?: number;
  latePenaltyApplied?: number;
  finalScore?: number;
  graderId?: string;
  gradedAt?: string;
  feedback?: string;
  attachments?: SubmissionAttachment[];
};

export type Assignment = {
  id: string;
  courseId: string;
  title: string;
  assignmentType: string;
  instructions?: string;
  availableAt?: string;
  dueAt?: string;
  lockAt?: string;
  maxScore?: number;
  status: string;
  submissionTypes?: string;
  maxAttempts: number;
  allowResubmission: boolean;
  latePenaltyPercent?: number;
  latePenaltyInterval?: string;
  latePenaltyMaxPercent?: number;
  rubricId?: string;
};

export async function listAssignments(courseId: string): Promise<Assignment[]> {
  return clientFetch<Assignment[]>(`/v1/assignments?courseId=${courseId}`);
}

export async function getAssignment(assignmentId: string): Promise<Assignment> {
  return clientFetch<Assignment>(`/v1/assignments/${assignmentId}`);
}

export async function listMySubmissions(
  assignmentId: string,
  studentId: string
): Promise<Submission[]> {
  return clientFetch<Submission[]>(
    `/v1/assignments/${assignmentId}/submissions?studentId=${studentId}`
  );
}

// studentId is taken from the gateway identity, never sent in the body.
export async function submitAssignment(
  assignmentId: string,
  input: { submissionText?: string; submissionUrl?: string }
): Promise<Submission> {
  return clientFetch<Submission>(`/v1/assignments/${assignmentId}/submissions`, {
    method: "POST",
    body: input
  });
}
