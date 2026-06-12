"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import type Hls from "hls.js";
import { usePlaybackUrl, useSaveProgress, useVideoManifest, useVideoProgress } from "./hooks";

type VideoPlayerProps = {
  videoId: string;
  userId: string;
  onTimeUpdate?: (seconds: number) => void;
  seekRequest?: { seconds: number; token: number } | null;
  onCompleted?: () => void;
};

const SAVE_INTERVAL_MS = 10_000;

function getVideoLoadErrorCopy(error: unknown) {
  const status = (error as Error & { status?: number } | null)?.status;
  if (status === 401) {
    return {
      title: "Phiên đăng nhập đã hết hạn",
      description: "Hãy đăng nhập lại để tiếp tục xem bài học này."
    };
  }
  if (status === 403) {
    return {
      title: "Bạn chưa có quyền xem video này",
      description: "Hãy kiểm tra trạng thái ghi danh khóa học hoặc chọn bài học thuộc khóa học của bạn."
    };
  }
  if (status === 404) {
    return {
      title: "Không tìm thấy video",
      description: "Video có thể đã bị gỡ khỏi bài học hoặc chưa được xuất bản."
    };
  }
  return {
    title: "Không tải được video",
    description: "Vui lòng thử lại sau hoặc chọn bài học khác trong khóa học."
  };
}

function PlayerState({
  title,
  description,
  loading = false
}: {
  title: string;
  description?: string;
  loading?: boolean;
}) {
  return (
    <div className="grid aspect-video w-full place-items-center rounded-lg bg-black px-6 text-center text-white">
      <div>
        <span className="mx-auto grid size-12 place-items-center rounded-full bg-white/10 text-white/80">
          {loading ? <Loader2 className="size-6 animate-spin" /> : <AlertCircle className="size-6" />}
        </span>
        <p className="mt-4 text-sm font-bold">{title}</p>
        {description && <p className="mt-2 max-w-md text-sm leading-6 text-white/60">{description}</p>}
      </div>
    </div>
  );
}

export function VideoPlayer({ videoId, userId, onTimeUpdate, seekRequest, onCompleted }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const manifest = useVideoManifest(videoId);
  const playback = usePlaybackUrl(videoId);
  const progress = useVideoProgress(videoId, userId);
  const saveProgress = useSaveProgress(videoId);
  const [resumed, setResumed] = useState(false);
  const [playerError, setPlayerError] = useState<string | null>(null);
  const renditions = manifest.data?.renditions ?? [];
  const captions = manifest.data?.captions ?? [];
  const playbackUrl = playback.data?.url;

  useEffect(() => {
    setResumed(false);
    setPlayerError(null);
  }, [videoId]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !playbackUrl) return undefined;
    let hls: Hls | null = null;
    let disposed = false;

    setPlayerError(null);
    el.removeAttribute("src");

    if (el.canPlayType("application/vnd.apple.mpegurl")) {
      el.src = playbackUrl;
      return () => {
        disposed = true;
        el.removeAttribute("src");
        el.load();
      };
    }

    const attachHls = async () => {
      try {
        const { default: HlsPlayer } = await import("hls.js");
        if (disposed) return;

        if (HlsPlayer.isSupported()) {
          hls = new HlsPlayer({ enableWorker: true });
          hls.loadSource(playbackUrl);
          hls.attachMedia(el);
          hls.on(HlsPlayer.Events.ERROR, (_event, data) => {
            if (data.fatal && !disposed) {
              setPlayerError("Không phát được stream HLS. Vui lòng thử lại hoặc kiểm tra trạng thái video.");
              hls?.destroy();
            }
          });
        } else {
          el.src = playbackUrl;
        }
      } catch {
        if (!disposed) {
          setPlayerError("Không tải được trình phát HLS. Vui lòng thử lại sau.");
        }
      }
    };

    void attachHls();

    return () => {
      disposed = true;
      hls?.destroy();
      el.removeAttribute("src");
      el.load();
    };
  }, [playbackUrl]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || resumed || !progress.data) return;
    const onLoaded = () => {
      if (progress.data && progress.data.positionSeconds > 0) {
        el.currentTime = progress.data.positionSeconds;
      }
      setResumed(true);
    };
    el.addEventListener("loadedmetadata", onLoaded, { once: true });
    return () => el.removeEventListener("loadedmetadata", onLoaded);
  }, [progress.data, resumed]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !onTimeUpdate) return undefined;
    const notify = () => onTimeUpdate(Math.max(0, Math.floor(el.currentTime || 0)));
    el.addEventListener("timeupdate", notify);
    el.addEventListener("loadedmetadata", notify);
    return () => {
      el.removeEventListener("timeupdate", notify);
      el.removeEventListener("loadedmetadata", notify);
    };
  }, [onTimeUpdate, videoId]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !seekRequest) return;
    el.currentTime = Math.max(0, seekRequest.seconds);
    void el.play().catch(() => undefined);
  }, [seekRequest]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !userId) return;
    const save = (completed = false) =>
      saveProgress.mutate({
        userId,
        positionSeconds: Math.floor(el.currentTime),
        durationSeconds: Number.isFinite(el.duration) ? Math.floor(el.duration) : undefined,
        playbackRate: el.playbackRate,
        completed
      });
    const interval = setInterval(() => {
      if (!el.paused) save();
    }, SAVE_INTERVAL_MS);
    const onPause = () => save();
    const onEnded = () => {
      save(true);
      onCompleted?.();
    };
    const onPageHide = () => save();
    const onVisibilityChange = () => {
      if (document.visibilityState === "hidden") save();
    };
    el.addEventListener("pause", onPause);
    el.addEventListener("ended", onEnded);
    window.addEventListener("pagehide", onPageHide);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      clearInterval(interval);
      el.removeEventListener("pause", onPause);
      el.removeEventListener("ended", onEnded);
      window.removeEventListener("pagehide", onPageHide);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, videoId, onCompleted]);

  if (manifest.isLoading || playback.isLoading) {
    return <PlayerState title="Đang tải video..." loading />;
  }
  if (manifest.error || playback.error) {
    const copy = getVideoLoadErrorCopy(manifest.error ?? playback.error);
    return <PlayerState title={copy.title} description={copy.description} />;
  }
  if (playerError) {
    return <PlayerState title="Không phát được video" description={playerError} />;
  }
  if (manifest.data?.status !== "READY") {
    return (
      <PlayerState
        title="Video đang xử lý"
        description={`Trạng thái hiện tại: ${manifest.data?.status ?? "UNKNOWN"}. Hãy quay lại sau khi transcode hoàn tất.`}
      />
    );
  }

  return (
    <div className="space-y-3 rounded-lg bg-black p-3">
      <video
        ref={videoRef}
        controls
        className="aspect-video w-full rounded-lg bg-black shadow-[0_24px_70px_rgba(0,0,0,0.35)]"
        crossOrigin="anonymous"
      >
        {captions.map((c) => (
          <track
            key={c.id}
            kind="subtitles"
            srcLang={c.language}
            label={c.language.toUpperCase()}
            src={`/api/media/captions/${c.id}`}
          />
        ))}
      </video>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-medium text-white/60">
        <span>
          {renditions.length > 0
            ? `${renditions.length} chất lượng phát`
            : "Video sẵn sàng phát"}
        </span>
        <span>
          {captions.length > 0
            ? `${captions.length} phụ đề`
            : "Chưa có phụ đề"}
        </span>
        <span>
          {userId
            ? saveProgress.isError
              ? "Chưa lưu được tiến độ"
              : "Tự lưu tiến độ"
            : "Đăng nhập để lưu tiến độ"}
        </span>
      </div>
    </div>
  );
}
