"use client";

import { clientFetch } from "@/shared/api/client";

export type DiscussionComment = {
  id: string;
  threadId: string;
  authorId: string;
  body: string;
  accepted: boolean;
  createdAt: string;
};

export type DiscussionThread = {
  id: string;
  courseId: string;
  assignmentId?: string | null;
  authorId: string;
  title: string;
  status: string;
  createdAt: string;
  comments: DiscussionComment[];
};

export async function listDiscussionThreads(courseId: string): Promise<DiscussionThread[]> {
  return clientFetch<DiscussionThread[]>(`/v1/discussions/threads?courseId=${encodeURIComponent(courseId)}`);
}

export async function createDiscussionThread(input: {
  courseId: string;
  assignmentId?: string;
  title: string;
}): Promise<DiscussionThread> {
  return clientFetch<DiscussionThread>("/v1/discussions/threads", {
    method: "POST",
    body: input
  });
}

export async function addDiscussionComment(threadId: string, body: string): Promise<DiscussionComment> {
  return clientFetch<DiscussionComment>(`/v1/discussions/threads/${threadId}/comments`, {
    method: "POST",
    body: { body }
  });
}
