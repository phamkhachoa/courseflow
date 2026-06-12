"use client";

import { Client } from "@stomp/stompjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, MessageSquareText, SendHorizontal, Wifi, WifiOff } from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  listCourseChatMessages,
  sendCourseChatMessage,
  type ChatMessage
} from "@/features/chat/api";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { API_BASE_URL } from "@/shared/api/envelope";
import { Badge, Button, Textarea, cn } from "@/shared/ui";

type CourseChatPanelProps = {
  courseId: string;
};

function chatQueryKey(courseId: string) {
  return ["course-chat", courseId] as const;
}

function chatWsUrl() {
  const edge = API_BASE_URL.replace(/\/api\/?$/, "");
  return `${edge.replace(/^http/i, "ws")}/ws/chat`;
}

function mergeMessages(current: ChatMessage[] | undefined, incoming: ChatMessage) {
  const messages = current ?? [];
  if (messages.some((message) => message.id === incoming.id)) {
    return messages;
  }
  return [...messages, incoming].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  );
}

function messageTime(value: string) {
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit"
    }).format(new Date(value));
  } catch {
    return "";
  }
}

export function CourseChatPanel({ courseId }: CourseChatPanelProps) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [draft, setDraft] = useState("");
  const [connected, setConnected] = useState(false);
  const [socketError, setSocketError] = useState("");
  const messageListRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setSession(learnerSession.read());
  }, []);

  const messagesQuery = useQuery({
    queryKey: chatQueryKey(courseId),
    enabled: Boolean(courseId && session?.accessToken),
    queryFn: () => listCourseChatMessages(courseId)
  });

  useEffect(() => {
    if (!courseId || !session?.accessToken) return undefined;

    const client = new Client({
      brokerURL: chatWsUrl(),
      connectHeaders: {
        Authorization: `Bearer ${session.accessToken}`
      },
      reconnectDelay: 4000,
      heartbeatIncoming: 10000,
      heartbeatOutgoing: 10000,
      debug: () => {}
    });

    client.onConnect = () => {
      setConnected(true);
      setSocketError("");
      client.subscribe(`/topic/courses/${courseId}/chat`, (frame) => {
        const message = JSON.parse(frame.body) as ChatMessage;
        queryClient.setQueryData<ChatMessage[]>(chatQueryKey(courseId), (current) =>
          mergeMessages(current, message)
        );
      });
    };
    client.onWebSocketClose = () => {
      setConnected(false);
    };
    client.onStompError = (frame) => {
      setConnected(false);
      setSocketError(
        frame.headers.message?.includes("ExecutorSubscribableChannel")
          ? "Chat realtime đang tạm offline. Bạn vẫn có thể tiếp tục học và thử lại sau."
          : "Không kết nối được chat realtime. Bạn vẫn có thể tiếp tục học và thử lại sau."
      );
    };
    client.activate();

    return () => {
      setConnected(false);
      void client.deactivate();
    };
  }, [courseId, queryClient, session?.accessToken]);

  useEffect(() => {
    if (!messagesQuery.data?.length) return;
    const list = messageListRef.current;
    if (!list) return;
    list.scrollTop = list.scrollHeight;
  }, [messagesQuery.data?.length]);

  const sendMutation = useMutation({
    mutationFn: (body: string) => sendCourseChatMessage(courseId, { body }),
    onSuccess: (message) => {
      queryClient.setQueryData<ChatMessage[]>(chatQueryKey(courseId), (current) =>
        mergeMessages(current, message)
      );
      setDraft("");
    }
  });

  const messages = useMemo(() => messagesQuery.data ?? [], [messagesQuery.data]);
  const currentUserId = session?.user?.id == null ? "" : String(session.user.id);

  function submitDraft() {
    const body = draft.trim();
    if (!body || sendMutation.isPending) return;
    sendMutation.mutate(body);
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitDraft();
  }

  function onDraftKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    submitDraft();
  }

  return (
    <article className="rounded-lg border border-black/10 bg-white shadow-[0_18px_45px_rgba(23,33,31,0.08)]">
      <div className="flex items-start justify-between gap-3 border-b border-black/10 p-5">
        <div className="min-w-0">
          <p className="text-sm font-bold text-brand-600">Phòng chat</p>
          <h3 className="mt-1 flex items-center gap-2 text-lg font-bold text-ink-900">
            <MessageSquareText className="size-5 text-brand-700" />
            Trao đổi khóa học
          </h3>
        </div>
        <Badge tone={connected ? "sky" : "neutral"} className="shrink-0">
          {connected ? <Wifi className="mr-1 size-3.5" /> : <WifiOff className="mr-1 size-3.5" />}
          {connected ? "Live" : "Offline"}
        </Badge>
      </div>

      <div ref={messageListRef} className="max-h-[360px] min-h-[260px] space-y-3 overflow-y-auto bg-[#fbfaf7] p-4">
        {!session && (
          <p className="rounded-md border border-black/10 bg-white p-3 text-sm text-ink-500">
            Đăng nhập để tham gia phòng chat của khóa học.
          </p>
        )}
        {messagesQuery.isLoading && session && (
          <p className="flex items-center gap-2 text-sm text-ink-500">
            <Loader2 className="size-4 animate-spin" /> Đang tải chat...
          </p>
        )}
        {messagesQuery.isError && (
          <p className="rounded-md border border-red-100 bg-red-50 p-3 text-sm font-semibold text-red-600">
            Chưa tải được lịch sử chat. Có thể bạn cần ghi danh khóa học hoặc chat đang tạm offline.
          </p>
        )}
        {socketError && (
          <p className="rounded-md border border-accent-100 bg-accent-50 p-3 text-sm font-semibold text-accent-700">
            {socketError}
          </p>
        )}
        {messages.length === 0 && !messagesQuery.isLoading && session && (
          <p className="rounded-md border border-black/10 bg-white p-3 text-sm text-ink-500">
            Chưa có tin nhắn nào trong khóa học này.
          </p>
        )}
        {messages.map((message) => {
          const mine = message.senderId === currentUserId;
          return (
            <div key={message.id} className={cn("flex", mine ? "justify-end" : "justify-start")}>
              <div
                className={cn(
                  "max-w-[86%] rounded-lg border px-3 py-2 text-sm shadow-sm",
                  mine
                    ? "border-brand-100 bg-brand-600 text-white"
                    : "border-black/10 bg-white text-ink-900"
                )}
              >
                <div className={cn("mb-1 flex items-center gap-2 text-xs", mine ? "text-white/70" : "text-ink-500")}>
                  <span className="font-bold">{mine ? "Bạn" : message.senderName}</span>
                  <span>{messageTime(message.createdAt)}</span>
                </div>
                <p className="whitespace-pre-wrap break-words leading-5">{message.body}</p>
              </div>
            </div>
          );
        })}
      </div>

      <form onSubmit={onSubmit} className="border-t border-black/10 p-4">
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onDraftKeyDown}
          disabled={!session || sendMutation.isPending}
          maxLength={2000}
          className="min-h-20 resize-none"
          placeholder="Nhập tin nhắn..."
        />
        {sendMutation.isError && (
          <p className="mt-2 text-sm font-semibold text-red-600">
            Chưa gửi được tin nhắn. Vui lòng thử lại sau.
          </p>
        )}
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="text-xs font-medium text-ink-500">{draft.length}/2000</span>
          <Button type="submit" disabled={!session || !draft.trim() || sendMutation.isPending}>
            {sendMutation.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <SendHorizontal className="size-4" />
            )}
            Gửi
          </Button>
        </div>
      </form>
    </article>
  );
}
