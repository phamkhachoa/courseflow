"use client";

import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  BellRing,
  BookOpenCheck,
  CheckCheck,
  CheckCircle2,
  Clock3,
  Filter,
  Inbox,
  Mail,
  Megaphone,
  MessageSquareText,
  RefreshCw,
  Settings2,
  Smartphone,
  Trophy
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import { clientFetch } from "@/shared/api/client";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  LinkButton,
  cn
} from "@/shared/ui";

type Notification = {
  id: string;
  userId?: string;
  notificationType?: string;
  type?: string;
  title: string;
  body?: string;
  read?: boolean;
  readAt?: string | null;
  createdAt?: string;
};

type NotificationPreference = {
  id?: string;
  userId?: string;
  channel: string;
  enabled: boolean;
};

type PreferenceChannel = {
  channel: string;
  label: string;
  detail: string;
  icon: ReactNode;
};

const preferredChannels: PreferenceChannel[] = [
  {
    channel: "IN_APP",
    label: "Trong ứng dụng",
    detail: "Hộp thư học tập",
    icon: <BellRing className="size-5" />
  },
  {
    channel: "EMAIL",
    label: "Email",
    detail: "Tổng hợp quan trọng",
    icon: <Mail className="size-5" />
  },
  {
    channel: "PUSH",
    label: "Thông báo đẩy",
    detail: "Nhắc học nhanh",
    icon: <Smartphone className="size-5" />
  }
];

function channelLabel(channel: string): string {
  if (channel === "EMAIL") return "Email";
  if (channel === "PUSH") return "Thông báo đẩy";
  if (channel === "SMS") return "Tin nhắn SMS";
  if (channel === "IN_APP") return "Trong ứng dụng";
  return channel;
}

function channelIcon(channel: string): ReactNode {
  if (channel === "EMAIL") return <Mail className="size-5" />;
  if (channel === "PUSH") return <Smartphone className="size-5" />;
  if (channel === "SMS") return <MessageSquareText className="size-5" />;
  return <BellRing className="size-5" />;
}

function isRead(notification: Notification): boolean {
  return Boolean(notification.readAt ?? notification.read);
}

function notificationKind(notification: Notification): string {
  return (notification.notificationType ?? notification.type ?? "SYSTEM").toUpperCase();
}

function kindMeta(kind: string): {
  label: string;
  tone: "brand" | "amber" | "coral" | "sky" | "neutral";
  icon: ReactNode;
  rail: string;
} {
  if (kind.includes("ANNOUNCEMENT")) {
    return {
      label: "Thông báo lớp",
      tone: "sky",
      icon: <Megaphone className="size-5" />,
      rail: "bg-signal-500"
    };
  }
  if (kind.includes("ASSIGNMENT") || kind.includes("DEADLINE")) {
    return {
      label: "Bài tập",
      tone: "amber",
      icon: <Clock3 className="size-5" />,
      rail: "bg-accent-500"
    };
  }
  if (kind.includes("GRADE") || kind.includes("CERTIFICATE")) {
    return {
      label: "Kết quả",
      tone: "brand",
      icon: <Trophy className="size-5" />,
      rail: "bg-brand-500"
    };
  }
  if (kind.includes("QUIZ") || kind.includes("ASSESSMENT")) {
    return {
      label: "Bài kiểm tra",
      tone: "coral",
      icon: <BookOpenCheck className="size-5" />,
      rail: "bg-coral-500"
    };
  }
  return {
    label: "Hệ thống",
    tone: "neutral",
    icon: <Bell className="size-5" />,
    rail: "bg-ink-500"
  };
}

function formatDateTime(value?: string): string {
  if (!value) return "Vừa cập nhật";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function timeAgo(value?: string): string {
  if (!value) return "mới đây";
  const createdAt = new Date(value).getTime();
  if (Number.isNaN(createdAt)) return "mới đây";

  const diff = Date.now() - createdAt;
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;

  if (diff < minute) return "vừa xong";
  if (diff < hour) return `${Math.floor(diff / minute)} phút trước`;
  if (diff < day) return `${Math.floor(diff / hour)} giờ trước`;
  if (diff < 7 * day) return `${Math.floor(diff / day)} ngày trước`;
  return formatDateTime(value);
}

function NotificationStat({
  icon,
  label,
  value,
  tone
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone: "brand" | "sky" | "amber";
}) {
  const toneClass = {
    brand: "bg-brand-50 text-brand-700",
    sky: "bg-signal-50 text-signal-600",
    amber: "bg-accent-50 text-accent-600"
  }[tone];

  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-ink-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-ink-900">{value}</p>
        </div>
        <span className={cn("grid size-10 place-items-center rounded-md", toneClass)}>
          {icon}
        </span>
      </div>
    </div>
  );
}

function PreferenceSwitch({
  channel,
  enabled,
  isPending,
  onToggle
}: {
  channel: string;
  enabled: boolean;
  isPending: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={isPending}
      onClick={onToggle}
      className={cn(
        "relative h-7 w-12 rounded-full border transition disabled:cursor-not-allowed disabled:opacity-60",
        enabled
          ? "border-brand-500 bg-brand-500"
          : "border-black/10 bg-black/10"
      )}
    >
      <span
        className={cn(
          "absolute top-1 grid size-5 place-items-center rounded-full bg-white text-[10px] text-brand-700 shadow-sm transition",
          enabled ? "left-6" : "left-1"
        )}
      >
        <CheckCircle2 className="size-3" />
      </span>
      <span className="sr-only">
        {enabled ? "Tắt" : "Bật"} {channelLabel(channel)}
      </span>
    </button>
  );
}

function NotificationPreferences({ userId }: { userId: number }) {
  const qc = useQueryClient();

  const prefs = useQuery({
    queryKey: ["notification-preferences", userId],
    queryFn: () =>
      clientFetch<NotificationPreference[]>(
        `/v1/notifications/preferences?userId=${userId}`
      ),
    enabled: Boolean(userId)
  });

  const toggle = useMutation({
    mutationFn: ({ channel, enabled }: { channel: string; enabled: boolean }) =>
      clientFetch("/v1/notifications/preferences", {
        method: "POST",
        body: { userId, channel, enabled }
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["notification-preferences", userId] })
  });

  const channels = useMemo(() => {
    const byChannel = new Map((prefs.data ?? []).map((pref) => [pref.channel, pref]));
    const rows = preferredChannels.map((channel) => ({
      ...channel,
      enabled: byChannel.get(channel.channel)?.enabled ?? true
    }));
    for (const pref of prefs.data ?? []) {
      if (rows.some((row) => row.channel === pref.channel)) continue;
      rows.push({
        channel: pref.channel,
        label: channelLabel(pref.channel),
        detail: "Kênh tùy chỉnh",
        icon: channelIcon(pref.channel),
        enabled: pref.enabled
      });
    }
    return rows;
  }, [prefs.data]);

  return (
    <section className="rounded-lg border border-black/10 bg-white p-5">
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
          <Settings2 className="size-5" />
        </span>
        <div>
          <h2 className="font-bold text-ink-900">Kênh nhận thông báo</h2>
          <p className="mt-1 text-sm leading-6 text-ink-500">
            CourseFlow mặc định bật các kênh chính cho tài khoản của bạn.
          </p>
        </div>
      </div>

      {prefs.isError && (
        <p className="mt-4 rounded-md bg-coral-50 px-3 py-2 text-sm font-medium text-coral-600">
          Không tải được cài đặt thông báo.
        </p>
      )}

      <div className="mt-5 space-y-3">
        {prefs.isLoading
          ? Array.from({ length: 3 }).map((_, index) => (
              <div
                key={index}
                className="h-[74px] animate-pulse rounded-lg border border-black/10 bg-black/5"
              />
            ))
          : channels.map((pref) => (
              <div
                key={pref.channel}
                className="flex items-center justify-between gap-4 rounded-lg border border-black/10 bg-[#fbfaf7] p-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-md bg-white text-brand-700">
                    {pref.icon}
                  </span>
                  <div className="min-w-0">
                    <p className="font-semibold text-ink-900">{pref.label}</p>
                    <p className="text-sm text-ink-500">{pref.detail}</p>
                  </div>
                </div>
                <PreferenceSwitch
                  channel={pref.channel}
                  enabled={pref.enabled}
                  isPending={toggle.isPending}
                  onToggle={() =>
                    toggle.mutate({
                      channel: pref.channel,
                      enabled: !pref.enabled
                    })
                  }
                />
              </div>
            ))}
      </div>
    </section>
  );
}

function NotificationCard({
  notification,
  isPending,
  onMarkRead
}: {
  notification: Notification;
  isPending: boolean;
  onMarkRead: () => void;
}) {
  const read = isRead(notification);
  const meta = kindMeta(notificationKind(notification));

  return (
    <Card
      className={cn(
        "relative overflow-hidden p-0",
        read ? "bg-white/85" : "border-brand-100 bg-white"
      )}
    >
      <span className={cn("absolute inset-y-0 left-0 w-1.5", read ? "bg-black/10" : meta.rail)} />
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-start sm:justify-between sm:p-5">
        <div className="flex min-w-0 gap-4">
          <span
            className={cn(
              "grid size-11 shrink-0 place-items-center rounded-md",
              read ? "bg-black/5 text-ink-500" : "bg-brand-50 text-brand-700"
            )}
          >
            {meta.icon}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={meta.tone}>{meta.label}</Badge>
              <Badge tone={read ? "neutral" : "brand"}>{read ? "Đã đọc" : "Mới"}</Badge>
              <span className="text-xs font-semibold text-ink-500">
                {timeAgo(notification.createdAt)}
              </span>
            </div>
            <h3 className="mt-2 text-lg font-bold text-ink-900">{notification.title}</h3>
            {notification.body && (
              <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
                {notification.body}
              </p>
            )}
            <p className="mt-3 text-xs font-medium text-ink-500">
              {formatDateTime(notification.createdAt)}
            </p>
          </div>
        </div>

        {!read && (
          <Button
            variant="secondary"
            size="sm"
            disabled={isPending}
            onClick={onMarkRead}
            className="shrink-0"
          >
            <CheckCheck className="size-4" />
            Đã đọc
          </Button>
        )}
      </div>
    </Card>
  );
}

export function NotificationsView() {
  const qc = useQueryClient();
  const { session, hydrated } = useLearnerSession();
  const userId = session?.user.id;
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const list = useQuery({
    queryKey: ["notifications", userId],
    queryFn: () => clientFetch<Notification[]>(`/v1/notifications?userId=${userId}`),
    enabled: Boolean(userId)
  });

  const notifications = useMemo(() => list.data ?? [], [list.data]);
  const unread = useMemo(
    () => notifications.filter((notification) => !isRead(notification)),
    [notifications]
  );
  const visibleNotifications = filter === "unread" ? unread : notifications;
  const todayCount = notifications.filter((notification) => {
    if (!notification.createdAt) return false;
    return new Date(notification.createdAt).toDateString() === new Date().toDateString();
  }).length;

  const markRead = useMutation({
    mutationFn: (id: string) =>
      clientFetch(`/v1/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", userId] })
  });

  const markAllRead = useMutation({
    mutationFn: async () => {
      await Promise.all(
        unread.map((notification) =>
          clientFetch(`/v1/notifications/${notification.id}/read`, { method: "POST" })
        )
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", userId] })
  });

  if (!hydrated) {
    return (
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div
                key={index}
                className="h-[114px] animate-pulse rounded-lg border border-black/10 bg-white/70"
              />
            ))}
          </div>
          <div className="h-[132px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
        </section>
        <aside className="space-y-5">
          <div className="h-[146px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
          <div className="h-[310px] animate-pulse rounded-lg border border-black/10 bg-white/70" />
        </aside>
      </div>
    );
  }

  if (!userId) {
    return (
      <EmptyState
        title="Bạn cần đăng nhập để xem thông báo"
        description="Đăng nhập để theo dõi thông báo lớp học, điểm số và bài tập cần xử lý."
        action={
          <LinkButton href="/login" variant="primary">
            Đăng nhập
          </LinkButton>
        }
      />
    );
  }

  if (list.isError) {
    return (
      <Card className="border-coral-50 bg-coral-50/60">
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-white text-coral-600">
            <RefreshCw className="size-5" />
          </span>
          <div>
            <h3 className="font-bold text-ink-900">Không tải được thông báo</h3>
            <p className="mt-1 text-sm text-ink-500">
              Backend có thể chưa sẵn sàng hoặc phiên đăng nhập đã hết hạn.
            </p>
            <Button
              className="mt-4"
              variant="secondary"
              onClick={() => list.refetch()}
            >
              <RefreshCw className="size-4" />
              Tải lại
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <section className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <NotificationStat
            icon={<Inbox className="size-5" />}
            label="Tổng thông báo"
            value={`${notifications.length}`}
            tone="brand"
          />
          <NotificationStat
            icon={<BellRing className="size-5" />}
            label="Chưa đọc"
            value={`${unread.length}`}
            tone="amber"
          />
          <NotificationStat
            icon={<Clock3 className="size-5" />}
            label="Hôm nay"
            value={`${todayCount}`}
            tone="sky"
          />
        </div>

        <div className="flex flex-col gap-3 rounded-lg border border-black/10 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink-500">
            <Filter className="size-4" />
            Lọc hộp thư
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={filter === "all" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setFilter("all")}
            >
              Tất cả
            </Button>
            <Button
              variant={filter === "unread" ? "primary" : "secondary"}
              size="sm"
              onClick={() => setFilter("unread")}
            >
              Mới
              {unread.length > 0 && <Badge tone="dark">{unread.length}</Badge>}
            </Button>
            {unread.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                disabled={markAllRead.isPending}
                onClick={() => markAllRead.mutate()}
              >
                <CheckCheck className="size-4" />
                Đọc tất cả
              </Button>
            )}
          </div>
        </div>

        {list.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="h-[132px] animate-pulse rounded-lg border border-black/10 bg-white/70"
              />
            ))}
          </div>
        ) : visibleNotifications.length === 0 ? (
          <EmptyState
            title={filter === "unread" ? "Bạn đã đọc hết thông báo mới" : "Chưa có thông báo"}
            description={
              filter === "unread"
                ? "Các cập nhật mới sẽ xuất hiện ở đây khi giảng viên hoặc hệ thống gửi tới bạn."
                : "Khi có thông báo lớp học, điểm số hoặc deadline, CourseFlow sẽ gom tại hộp thư này."
            }
          />
        ) : (
          <div className="space-y-3">
            {visibleNotifications.map((notification) => (
              <NotificationCard
                key={notification.id}
                notification={notification}
                isPending={markRead.isPending}
                onMarkRead={() => markRead.mutate(notification.id)}
              />
            ))}
          </div>
        )}
      </section>

      <aside className="space-y-5 lg:sticky lg:top-24 lg:self-start">
        <Card className="bg-brand-900 text-white">
          <p className="text-sm font-bold text-brand-100">Trạng thái hôm nay</p>
          <p className="mt-3 text-4xl font-bold">{unread.length}</p>
          <p className="mt-2 text-sm leading-6 text-white/75">
            {unread.length > 0
              ? "thông báo mới đang chờ bạn xử lý."
              : "thông báo mới đã được xử lý."}
          </p>
        </Card>
        <NotificationPreferences userId={userId} />
      </aside>
    </div>
  );
}
