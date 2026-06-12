"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bookmark,
  Captions,
  Clock3,
  Download,
  FileText,
  StickyNote,
  Trash2
} from "lucide-react";
import { Badge, Button, Card, Textarea, cn } from "@/shared/ui";
import type { VideoCaption } from "./hooks";

type VideoNote = {
  id: string;
  kind: "NOTE" | "BOOKMARK";
  second: number;
  body: string;
  createdAt: string;
};

type VideoNotesPanelProps = {
  videoId: string;
  userId: string;
  currentSecond: number;
  captions: VideoCaption[];
  onSeek: (second: number) => void;
};

function storageKey(videoId: string, userId: string) {
  return `courseflow.video-notes.${userId}.${videoId}`;
}

function formatTime(seconds: number) {
  const safeSeconds = Math.max(0, Math.floor(seconds || 0));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const rest = safeSeconds % 60;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(rest).padStart(2, "0");
  return hours > 0 ? `${hours}:${mm}:${ss}` : `${minutes}:${ss}`;
}

function loadNotes(videoId: string, userId: string): VideoNote[] {
  if (typeof window === "undefined" || !videoId || !userId) return [];
  try {
    const raw = localStorage.getItem(storageKey(videoId, userId));
    return raw ? (JSON.parse(raw) as VideoNote[]) : [];
  } catch {
    return [];
  }
}

function saveNotes(videoId: string, userId: string, notes: VideoNote[]) {
  if (typeof window === "undefined" || !videoId || !userId) return;
  localStorage.setItem(storageKey(videoId, userId), JSON.stringify(notes));
}

export function VideoNotesPanel({
  videoId,
  userId,
  currentSecond,
  captions,
  onSeek
}: VideoNotesPanelProps) {
  const [notes, setNotes] = useState<VideoNote[]>([]);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    setNotes(loadNotes(videoId, userId));
  }, [videoId, userId]);

  useEffect(() => {
    saveNotes(videoId, userId, notes);
  }, [notes, userId, videoId]);

  const sortedNotes = useMemo(
    () =>
      notes
        .slice()
        .sort((a, b) => a.second - b.second || new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()),
    [notes]
  );
  const bookmarkCount = notes.filter((note) => note.kind === "BOOKMARK").length;
  const noteCount = notes.filter((note) => note.kind === "NOTE").length;

  function addNote(kind: VideoNote["kind"]) {
    const body =
      kind === "BOOKMARK"
        ? draft.trim() || `Bookmark tại ${formatTime(currentSecond)}`
        : draft.trim();
    if (!body) return;
    setNotes((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        kind,
        second: Math.max(0, Math.floor(currentSecond || 0)),
        body,
        createdAt: new Date().toISOString()
      }
    ]);
    setDraft("");
  }

  function removeNote(id: string) {
    setNotes((current) => current.filter((note) => note.id !== id));
  }

  return (
    <Card className="h-full" padding="none">
      <div className="border-b border-black/10 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-bold text-brand-600">Study tools</p>
            <h2 className="mt-1 text-xl font-bold text-ink-900">Ghi chú video</h2>
          </div>
          <Badge tone="brand">
            <Clock3 className="mr-1 size-3.5" />
            {formatTime(currentSecond)}
          </Badge>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-3">
            <p className="text-xs font-bold uppercase text-ink-500">Notes</p>
            <p className="mt-1 text-2xl font-bold text-ink-900">{noteCount}</p>
          </div>
          <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-3">
            <p className="text-xs font-bold uppercase text-ink-500">Bookmarks</p>
            <p className="mt-1 text-2xl font-bold text-ink-900">{bookmarkCount}</p>
          </div>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div>
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ghi lại ý chính, câu hỏi hoặc đoạn cần xem lại..."
            className="min-h-28"
          />
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Button type="button" onClick={() => addNote("NOTE")}>
              <StickyNote className="size-4" />
              Lưu ghi chú
            </Button>
            <Button type="button" variant="secondary" onClick={() => addNote("BOOKMARK")}>
              <Bookmark className="size-4" />
              Bookmark mốc này
            </Button>
          </div>
        </div>

        <div>
          <p className="mb-3 flex items-center gap-2 text-sm font-bold text-ink-900">
            <StickyNote className="size-4 text-brand-700" />
            Timeline cá nhân
          </p>
          {sortedNotes.length === 0 ? (
            <div className="rounded-lg border border-dashed border-black/15 bg-[#fbfaf7] p-4 text-sm leading-6 text-ink-500">
              Chưa có ghi chú. Khi đang xem video, hãy lưu mốc quan trọng để quay lại nhanh.
            </div>
          ) : (
            <div className="max-h-[360px] space-y-3 overflow-y-auto pr-1">
              {sortedNotes.map((note) => (
                <div key={note.id} className="rounded-lg border border-black/10 bg-[#fbfaf7] p-3">
                  <div className="flex items-start justify-between gap-3">
                    <button
                      type="button"
                      onClick={() => onSeek(note.second)}
                      className="inline-flex items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-900"
                    >
                      <Clock3 className="size-4" />
                      {formatTime(note.second)}
                    </button>
                    <div className="flex items-center gap-2">
                      <Badge tone={note.kind === "BOOKMARK" ? "amber" : "brand"}>
                        {note.kind === "BOOKMARK" ? "Bookmark" : "Note"}
                      </Badge>
                      <button
                        type="button"
                        onClick={() => removeNote(note.id)}
                        className="grid size-8 place-items-center rounded-md text-ink-500 transition hover:bg-black/5 hover:text-coral-600"
                        aria-label="Xóa ghi chú"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink-700">{note.body}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-black/10 pt-4">
          <p className="mb-3 flex items-center gap-2 text-sm font-bold text-ink-900">
            <Captions className="size-4 text-signal-600" />
            Phụ đề và transcript
          </p>
          {captions.length === 0 ? (
            <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-3 text-sm leading-6 text-ink-500">
              Video này chưa có phụ đề. Khi admin upload caption, học viên có thể tải từ đây.
            </div>
          ) : (
            <div className="space-y-2">
              {captions.map((caption) => (
                <a
                  key={caption.id}
                  href={`/api/media/captions/${caption.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    "flex items-center justify-between gap-3 rounded-md border border-black/10 bg-[#fbfaf7] p-3 text-sm transition",
                    "hover:border-brand-200 hover:bg-brand-50/60"
                  )}
                >
                  <span className="inline-flex items-center gap-2 font-semibold text-ink-900">
                    <FileText className="size-4 text-signal-600" />
                    {caption.language.toUpperCase()} {caption.autoGenerated ? "auto" : "caption"}
                  </span>
                  <Download className="size-4 text-ink-500" />
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
