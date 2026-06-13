import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type PeerReviewSettings = {
  id?: string;
  assignmentId: string;
  reviewersPerSubmission?: number;
  anonymous?: boolean;
  reviewDueAt?: string;
  status?: string;
};

export type ReviewAssignment = {
  id: string;
  assignmentId: string;
  submissionId: string;
  reviewerId: string;
  revieweeId: string;
  status?: string;
  assignedAt?: string;
};

export type ReviewSubmission = {
  id: string;
  reviewAssignmentId: string;
  score?: number;
  comment?: string;
  status?: string;
  submittedAt?: string;
};

export type PeerReviewResult = {
  id: string;
  submissionId: string;
  finalScore?: number;
  finalizedBy?: string;
  finalizedAt?: string;
};

export async function getSettings(assignmentId: string): Promise<PeerReviewSettings> {
  const { data } = await apiClient.get(`/admin/v1/peer-reviews/settings/${assignmentId}`);
  return unwrap<PeerReviewSettings>(data);
}

/** Assign a reviewer to a specific submission. Staff-only. */
export async function assignReview(input: {
  assignmentId: string;
  submissionId: string;
  reviewerId: string;
  revieweeId: string;
}): Promise<ReviewAssignment> {
  const { data } = await apiClient.post("/admin/v1/peer-reviews/assignments", input);
  return unwrap<ReviewAssignment>(data);
}

export async function listMyReviewAssignments(): Promise<ReviewAssignment[]> {
  const { data } = await apiClient.get("/admin/v1/peer-reviews/review-assignments/mine");
  return unwrapList<ReviewAssignment>(data);
}

export async function submitReview(
  reviewAssignmentId: string,
  input: { score: number; comment: string }
): Promise<ReviewSubmission> {
  const { data } = await apiClient.post(
    `/admin/v1/peer-reviews/review-assignments/${reviewAssignmentId}/submit`,
    input
  );
  return unwrap<ReviewSubmission>(data);
}

/** Finalize a submission's peer-review score. Only the submissionId is sent; the score and actor are derived server-side. */
export async function finalizeResults(submissionId: string): Promise<PeerReviewResult> {
  const { data } = await apiClient.post("/admin/v1/peer-reviews/results/finalize", { submissionId });
  return unwrap<PeerReviewResult>(data);
}
