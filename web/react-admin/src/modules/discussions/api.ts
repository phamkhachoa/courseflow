import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type DiscussionThread = {
  id: string;
  courseId?: string;
  title: string;
  authorId?: string;
  status?: string;
  createdAt?: string;
};
export type DiscussionComment = {
  id: string;
  threadId: string;
  authorId?: string;
  body: string;
  accepted?: boolean;
  createdAt?: string;
};
export type ThreadDetail = DiscussionThread & { comments?: DiscussionComment[] };

export async function listThreads(courseId?: string): Promise<DiscussionThread[]> {
  const { data } = await apiClient.get("/admin/v1/discussions/threads", {
    params: courseId ? { courseId } : undefined
  });
  return unwrapList<DiscussionThread>(data);
}
export async function createThread(input: {
  courseId: string;
  title: string;
  body: string;
}): Promise<DiscussionThread> {
  const { data } = await apiClient.post("/admin/v1/discussions/threads", input);
  return unwrap<DiscussionThread>(data);
}
export async function getThread(threadId: string): Promise<ThreadDetail> {
  const { data } = await apiClient.get(`/admin/v1/discussions/threads/${threadId}`);
  return unwrap<ThreadDetail>(data);
}
export async function addComment(
  threadId: string,
  input: { body: string }
): Promise<DiscussionComment> {
  const { data } = await apiClient.post(`/admin/v1/discussions/threads/${threadId}/comments`, input);
  return unwrap<DiscussionComment>(data);
}
export async function acceptComment(threadId: string, commentId: string): Promise<unknown> {
  const { data } = await apiClient.post(
    `/admin/v1/discussions/threads/${threadId}/comments/${commentId}/accept`,
    {}
  );
  return unwrap<unknown>(data);
}
