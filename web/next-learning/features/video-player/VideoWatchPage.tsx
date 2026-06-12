"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft,
  Captions,
  CheckCircle2,
  Clock3,
  Film,
  Layers3,
  LockKeyhole,
  LogIn,
  UserPlus,
  Video
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import { Badge, Button, Card } from "@/shared/ui";
import { useVideoManifest } from "./hooks";
import { VideoPlayer } from "./VideoPlayer";
import { VideoNotesPanel } from "./VideoNotesPanel";

type VideoWatchPageProps = {
  videoId: string;
};

function Skeleton() {
  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-6 lg:px-8">
      <div className="h-[520px] animate-pulse rounded-[28px] border border-slate-200 bg-white/70" />
    </main>
  );
}

function LoginGate({ videoId }: { videoId: string }) {
  const next = `/videos/${videoId}`;
  return (
    <main className="mx-auto max-w-4xl px-5 py-12 sm:px-6 lg:px-8">
      <Card className="rounded-[28px] text-center" padding="lg">
        <span className="mx-auto grid size-14 place-items-center rounded-xl bg-brand-50 text-brand-700">
          <LockKeyhole className="size-7" />
        </span>
        <h1 className="mt-5 text-2xl font-bold text-ink-900">Đăng nhập để xem video</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-ink-500">
          Video bài học được bảo vệ theo tài khoản học viên để lưu tiến độ xem và tiếp tục học từ đúng vị trí.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button asChild>
            <Link href={`/login?next=${encodeURIComponent(next)}`}>
              <LogIn className="size-4" />
              Đăng nhập
            </Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href={`/register?next=${encodeURIComponent(next)}`}>
              <UserPlus className="size-4" />
              Đăng ký
            </Link>
          </Button>
        </div>
      </Card>
    </main>
  );
}

export function VideoWatchPage({ videoId }: VideoWatchPageProps) {
  const { session, hydrated } = useLearnerSession();
  const [currentSecond, setCurrentSecond] = useState(0);
  const [seekRequest, setSeekRequest] = useState<{ seconds: number; token: number } | null>(null);
  const userId = session?.user.id ? String(session.user.id) : "";
  const manifest = useVideoManifest(userId ? videoId : "");
  const status = manifest.data?.status ?? "Đang tải";
  const renditions = manifest.data?.renditions ?? [];
  const captions = manifest.data?.captions ?? [];

  if (!hydrated) return <Skeleton />;
  if (!session) return <LoginGate videoId={videoId} />;

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-6 lg:px-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-bold text-ink-500 hover:text-brand-700">
          <ArrowLeft className="size-4" />
          Về dashboard
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="neutral">Lesson player</Badge>
          <Badge tone="brand">{session.user.fullName || session.user.email}</Badge>
        </div>
      </div>

      <section className="mb-5 rounded-[28px] border border-slate-200/80 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">Video lesson</Badge>
              <Badge tone={status === "READY" ? "neutral" : "amber"}>{status}</Badge>
            </div>
            <h1 className="mt-3 text-3xl font-bold tracking-tight text-ink-900">Bài học đang phát</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-500">
              Player, phụ đề và ghi chú nằm trên cùng một mặt phẳng để học viên không cần nhảy màn hình trong lúc học.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-right">
            <p className="text-xs font-bold uppercase text-ink-500">Lesson ID</p>
            <p className="mt-1 text-sm font-semibold text-ink-900">{videoId}</p>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-[28px] border border-slate-200/80 bg-slate-950 shadow-[0_30px_90px_rgba(23,33,31,0.18)]">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_400px]">
          <div className="min-w-0 p-4 sm:p-5 lg:p-6">
            <VideoPlayer
              videoId={videoId}
              userId={userId}
              onTimeUpdate={setCurrentSecond}
              seekRequest={seekRequest}
            />
          </div>

          <aside className="space-y-5 border-t border-white/10 bg-white p-5 lg:border-l lg:border-t-0">
            <div className="flex items-start gap-3">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
                <Film className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-brand-600">Phòng xem video</p>
                <h2 className="mt-1 text-xl font-bold leading-tight tracking-tight text-ink-900">Ngữ cảnh bài học</h2>
                <p className="mt-2 text-sm leading-6 text-ink-500">
                  Tiến độ xem được gắn với tài khoản hiện tại và đồng bộ với learner journey phía sau.
                </p>
              </div>
            </div>

            <div className="grid gap-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                <p className="flex items-center gap-2 text-xs font-bold uppercase text-ink-500">
                  <Layers3 className="size-4" />
                  Chất lượng phát
                </p>
                <p className="mt-2 text-lg font-bold text-ink-900">{renditions.length || "—"}</p>
                {renditions.length > 0 && (
                  <p className="mt-1 text-xs leading-5 text-ink-500">
                    {renditions.map((rendition) => rendition.label).join(", ")}
                  </p>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                <p className="flex items-center gap-2 text-xs font-bold uppercase text-ink-500">
                  <Captions className="size-4" />
                  Phụ đề
                </p>
                <p className="mt-2 text-lg font-bold text-ink-900">{captions.length || "—"}</p>
                {captions.length > 0 && (
                  <p className="mt-1 text-xs leading-5 text-ink-500">
                    {captions.map((caption) => caption.language.toUpperCase()).join(", ")}
                  </p>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                <p className="flex items-center gap-2 text-xs font-bold uppercase text-ink-500">
                  <Clock3 className="size-4" />
                  Trạng thái học
                </p>
                <p className="mt-2 inline-flex items-center gap-2 text-sm font-bold text-ink-900">
                  <CheckCircle2 className="size-4 text-brand-700" />
                  Tự lưu tiến độ
                </p>
              </div>
            </div>

            <VideoNotesPanel
              videoId={videoId}
              userId={userId}
              currentSecond={currentSecond}
              captions={captions}
              onSeek={(seconds) => setSeekRequest({ seconds, token: Date.now() })}
            />

            <div className="grid gap-2">
              <Button asChild className="w-full">
                <Link href="/search">
                  <Video className="size-4" />
                  Tìm khóa học khác
                </Link>
              </Button>
              <Button asChild variant="secondary" className="w-full">
                <Link href="/gradebook">Xem bảng điểm</Link>
              </Button>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
