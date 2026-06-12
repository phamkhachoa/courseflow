"use client";

import { clientFetch } from "@/shared/api/client";

export type ChatAttachment = {
  mediaId?: string;
  fileName?: string;
  contentType?: string;
  url?: string;
};

export type ChatMessage = {
  id: string;
  roomId: string;
  courseId: string;
  senderId: string;
  senderName: string;
  senderEmail: string;
  messageType: string;
  body: string;
  attachments?: ChatAttachment[];
  replyToMessageId?: string;
  editedAt?: string;
  deletedAt?: string;
  createdAt: string;
};

export type SendChatMessageInput = {
  body: string;
  attachments?: ChatAttachment[];
  replyToMessageId?: string;
};

export function listCourseChatMessages(courseId: string, limit = 50) {
  return clientFetch<ChatMessage[]>(
    `/v1/chat/courses/${encodeURIComponent(courseId)}/messages?limit=${limit}`
  );
}

export function sendCourseChatMessage(courseId: string, input: SendChatMessageInput) {
  return clientFetch<ChatMessage>(`/v1/chat/courses/${encodeURIComponent(courseId)}/messages`, {
    method: "POST",
    body: input
  });
}
