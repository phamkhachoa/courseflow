import { clientFetch } from "@/shared/api/client";

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
  courseId?: string;
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

export function getPeerReviewSettings(assignmentId: string) {
  return clientFetch<PeerReviewSettings>(`/v1/peer-reviews/settings/${assignmentId}`);
}

export function listMyReviewAssignments() {
  return clientFetch<ReviewAssignment[]>("/v1/peer-reviews/review-assignments/mine");
}

export function submitPeerReview(
  reviewAssignmentId: string,
  input: { score: number; comment: string }
) {
  return clientFetch<ReviewSubmission>(
    `/v1/peer-reviews/review-assignments/${reviewAssignmentId}/submit`,
    {
      method: "POST",
      body: input
    }
  );
}
