"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  HelpCircle,
  Loader2,
  MessageCircle,
  MessagesSquare,
  Search,
  Send,
  UserRound
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import {
  addDiscussionComment,
  createDiscussionThread,
  listDiscussionThreads,
  type DiscussionThread
} from "./api";
import { Badge, Button, Card, EmptyState, TextInput, Textarea, cn } from "@/shared/ui";

type CourseQAPanelProps = {
  courseId: string;
};

function formatTime(value?: string) {
  if (!value) return "Vừa xong";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Vừa xong";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function authorLabel(authorId: string, currentUserId?: string) {
  return currentUserId && authorId === currentUserId ? "Bạn" : `Thành viên ${authorId.slice(0, 6)}`;
}

function threadHasAcceptedAnswer(thread: DiscussionThread) {
  return thread.comments.some((comment) => comment.accepted);
}

export function CourseQAPanel({ courseId }: CourseQAPanelProps) {
  const { session } = useLearnerSession();
  const queryClient = useQueryClient();
  const userId = session?.user.id ? String(session.user.id) : "";
  const [filter, setFilter] = useState("");
  const [selectedThreadId, setSelectedThreadId] = useState("");
  const [questionTitle, setQuestionTitle] = useState("");
  const [questionBody, setQuestionBody] = useState("");
  const [replyBody, setReplyBody] = useState("");

  const threadsQuery = useQuery({
    queryKey: ["course-discussions", courseId],
    queryFn: () => listDiscussionThreads(courseId),
    enabled: Boolean(session?.accessToken && courseId),
    retry: 0
  });

  const threads = useMemo(() => {
    const normalizedFilter = filter.trim().toLowerCase();
    const items = (threadsQuery.data ?? []).slice().sort((a, b) => {
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });
    if (!normalizedFilter) return items;
    return items.filter((thread) => {
      const body = thread.comments.map((comment) => comment.body).join(" ");
      return `${thread.title} ${body}`.toLowerCase().includes(normalizedFilter);
    });
  }, [filter, threadsQuery.data]);

  const selectedThread = threads.find((thread) => thread.id === selectedThreadId) ?? threads[0];

  useEffect(() => {
    if (threads.length === 0) {
      setSelectedThreadId("");
      return;
    }
    if (!selectedThreadId || !threads.some((thread) => thread.id === selectedThreadId)) {
      setSelectedThreadId(threads[0].id);
    }
  }, [selectedThreadId, threads]);

  const askQuestion = useMutation({
    mutationFn: async () => {
      const title = questionTitle.trim();
      const body = questionBody.trim();
      if (!title) throw new Error("Hãy nhập tiêu đề câu hỏi.");
      const thread = await createDiscussionThread({ courseId, title });
      if (body) await addDiscussionComment(thread.id, body);
      return thread;
    },
    onSuccess: (thread) => {
      setQuestionTitle("");
      setQuestionBody("");
      setSelectedThreadId(thread.id);
      void queryClient.invalidateQueries({ queryKey: ["course-discussions", courseId] });
    }
  });

  const addReply = useMutation({
    mutationFn: async () => {
      const body = replyBody.trim();
      if (!selectedThread) throw new Error("Chọn một câu hỏi trước.");
      if (!body) throw new Error("Hãy nhập nội dung trả lời.");
      return addDiscussionComment(selectedThread.id, body);
    },
    onSuccess: () => {
      setReplyBody("");
      void queryClient.invalidateQueries({ queryKey: ["course-discussions", courseId] });
    }
  });

  if (!session) {
    return (
      <Card>
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
            <MessagesSquare className="size-5" />
          </span>
          <div>
            <p className="font-bold text-ink-900">Q&A khóa học</p>
            <p className="mt-2 text-sm leading-6 text-ink-500">
              Đăng nhập để đặt câu hỏi và xem thảo luận trong khóa học.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="border-b border-black/10 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-bold text-brand-600">Q&A</p>
            <h3 className="mt-1 text-xl font-bold text-ink-900">Hỏi đáp khóa học</h3>
          </div>
          <Badge tone="brand">
            <MessageCircle className="mr-1 size-3.5" />
            {threadsQuery.data?.length ?? 0}
          </Badge>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <Search className="size-4 text-ink-500" />
          <TextInput
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Tìm trong câu hỏi hoặc trả lời"
            className="min-h-10 py-2"
          />
        </div>
      </div>

      <div className="grid min-h-[520px] lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="border-b border-black/10 bg-[#fbfaf7] lg:border-b-0 lg:border-r">
          <div className="p-4">
            <p className="text-xs font-bold uppercase text-ink-500">Đặt câu hỏi</p>
            <div className="mt-3 space-y-2">
              <TextInput
                value={questionTitle}
                onChange={(event) => setQuestionTitle(event.target.value)}
                placeholder="Ví dụ: Vì sao service boundary cần rõ?"
                className="min-h-10 py-2"
              />
              <Textarea
                value={questionBody}
                onChange={(event) => setQuestionBody(event.target.value)}
                placeholder="Thêm bối cảnh, lỗi gặp phải hoặc đoạn bạn chưa hiểu"
                className="min-h-24"
              />
              <Button
                type="button"
                onClick={() => askQuestion.mutate()}
                disabled={askQuestion.isPending}
                className="w-full"
              >
                {askQuestion.isPending ? <Loader2 className="size-4 animate-spin" /> : <HelpCircle className="size-4" />}
                Gửi câu hỏi
              </Button>
              {askQuestion.isError && (
                <p className="text-xs font-semibold text-coral-600">{(askQuestion.error as Error).message}</p>
              )}
            </div>
          </div>

          <div className="border-t border-black/10">
            {threadsQuery.isLoading ? (
              <div className="flex items-center gap-2 p-4 text-sm font-semibold text-ink-500">
                <Loader2 className="size-4 animate-spin" />
                Đang tải Q&A...
              </div>
            ) : threads.length === 0 ? (
              <div className="p-4">
                <p className="text-sm font-semibold text-ink-900">Chưa có câu hỏi</p>
                <p className="mt-1 text-sm leading-5 text-ink-500">Hãy là người mở thảo luận đầu tiên.</p>
              </div>
            ) : (
              threads.map((thread) => (
                <button
                  key={thread.id}
                  type="button"
                  onClick={() => setSelectedThreadId(thread.id)}
                  className={cn(
                    "w-full border-b border-black/10 p-4 text-left transition last:border-b-0",
                    selectedThread?.id === thread.id ? "bg-brand-50" : "bg-white hover:bg-white/70"
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span className="line-clamp-2 flex-1 text-sm font-bold leading-5 text-ink-900">{thread.title}</span>
                    {threadHasAcceptedAnswer(thread) && <CheckCircle2 className="size-4 shrink-0 text-brand-700" />}
                  </span>
                  <span className="mt-2 flex flex-wrap items-center gap-2">
                    <Badge tone={threadHasAcceptedAnswer(thread) ? "brand" : "neutral"}>
                      {threadHasAcceptedAnswer(thread) ? "Đã trả lời" : "Đang mở"}
                    </Badge>
                    <span className="text-xs font-semibold text-ink-500">{thread.comments.length} phản hồi</span>
                  </span>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="min-w-0 p-5">
          {!selectedThread ? (
            <EmptyState
              title="Chọn hoặc tạo câu hỏi"
              description="Q&A giúp học viên giữ câu hỏi theo khóa học thay vì trôi trong chat realtime."
            />
          ) : (
            <div className="flex h-full flex-col">
              <div className="border-b border-black/10 pb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={threadHasAcceptedAnswer(selectedThread) ? "brand" : "neutral"}>
                    {threadHasAcceptedAnswer(selectedThread) ? "Có accepted answer" : selectedThread.status}
                  </Badge>
                  <span className="text-xs font-semibold text-ink-500">{formatTime(selectedThread.createdAt)}</span>
                </div>
                <h4 className="mt-3 text-2xl font-bold leading-8 text-ink-900">{selectedThread.title}</h4>
                <p className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-ink-500">
                  <UserRound className="size-4" />
                  {authorLabel(selectedThread.authorId, userId)}
                </p>
              </div>

              <div className="flex-1 space-y-3 py-4">
                {selectedThread.comments.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-black/15 bg-[#fbfaf7] p-4 text-sm leading-6 text-ink-500">
                    Câu hỏi này chưa có mô tả hoặc phản hồi. Bạn có thể bổ sung thêm ngữ cảnh ở ô trả lời bên dưới.
                  </p>
                ) : (
                  selectedThread.comments.map((comment) => (
                    <div
                      key={comment.id}
                      className={cn(
                        "rounded-lg border p-4",
                        comment.accepted ? "border-brand-200 bg-brand-50" : "border-black/10 bg-[#fbfaf7]"
                      )}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-2 text-sm font-bold text-ink-900">
                          <UserRound className="size-4" />
                          {authorLabel(comment.authorId, userId)}
                        </span>
                        <span className="flex items-center gap-2">
                          {comment.accepted && <Badge tone="brand">Accepted</Badge>}
                          <span className="text-xs font-semibold text-ink-500">{formatTime(comment.createdAt)}</span>
                        </span>
                      </div>
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-ink-700">{comment.body}</p>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-black/10 pt-4">
                <Textarea
                  value={replyBody}
                  onChange={(event) => setReplyBody(event.target.value)}
                  placeholder="Viết phản hồi hoặc bổ sung thông tin..."
                />
                <div className="mt-3 flex items-center justify-between gap-3">
                  {addReply.isError ? (
                    <p className="text-xs font-semibold text-coral-600">{(addReply.error as Error).message}</p>
                  ) : (
                    <p className="text-xs font-semibold text-ink-500">Câu trả lời sẽ được lưu theo thread này.</p>
                  )}
                  <Button type="button" onClick={() => addReply.mutate()} disabled={addReply.isPending}>
                    {addReply.isPending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                    Gửi phản hồi
                  </Button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </Card>
  );
}
