"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Compass,
  Filter,
  GraduationCap,
  Layers3,
  RefreshCw,
  Search,
  Sparkles,
  WandSparkles
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { API_BASE_URL, unwrap } from "@/shared/api/envelope";
import { Badge, Button, Card, EmptyState, TextInput, cn } from "@/shared/ui";

type SearchResult = {
  id: string;
  code?: string;
  title: string;
  slug?: string;
  description?: string;
  summary?: string;
  departmentId?: string;
  level?: string;
  status?: string;
  updatedAt?: string;
};

type CourseRecommendation = {
  course: SearchResult;
  reason: string;
};

type SearchResponse =
  | SearchResult[]
  | {
      content?: SearchResult[];
      totalHits?: number;
      page?: number;
      size?: number;
    };

type SearchPage = {
  content: SearchResult[];
  totalHits: number;
  page: number;
  size: number;
};

const PAGE_SIZE = 9;
const SUGGESTION_LIMIT = 6;
const RECOMMENDATION_LIMIT = 4;
const SEARCH_DEBOUNCE_MS = 120;

const topics = [
  "spring boot service",
  "microservices observability",
  "secure API gateway",
  "event driven architecture",
  "data pipeline",
  "kubernetes deployment"
];

const levelTone: Record<string, "brand" | "sky" | "amber" | "coral" | "neutral"> = {
  BEGINNER: "brand",
  INTERMEDIATE: "sky",
  ADVANCED: "amber",
  EXPERT: "coral"
};

function normalizeSearchResponse(payload: SearchResponse, page: number, size: number): SearchPage {
  if (Array.isArray(payload)) {
    return {
      content: payload,
      totalHits: payload.length,
      page,
      size
    };
  }

  const content = payload.content ?? [];
  return {
    content,
    totalHits: payload.totalHits ?? content.length,
    page: payload.page ?? page,
    size: payload.size ?? size
  };
}

async function searchCourses(q: string, page: number): Promise<SearchPage> {
  const params = new URLSearchParams({
    q,
    page: String(page),
    size: String(PAGE_SIZE)
  });
  const response = await fetch(`${API_BASE_URL}/v1/search/courses?${params.toString()}`);
  if (!response.ok) throw new Error(`Search failed (${response.status})`);
  return normalizeSearchResponse(unwrap<SearchResponse>(await response.json()), page, PAGE_SIZE);
}

async function suggestCourses(q: string): Promise<SearchResult[]> {
  const params = new URLSearchParams({
    q,
    limit: String(SUGGESTION_LIMIT)
  });
  const response = await fetch(`${API_BASE_URL}/v1/search/courses/suggest?${params.toString()}`);
  if (!response.ok) throw new Error(`Suggest failed (${response.status})`);
  return unwrap<SearchResult[]>(await response.json());
}

async function recommendCourses(q: string): Promise<CourseRecommendation[]> {
  const params = new URLSearchParams({
    q,
    limit: String(RECOMMENDATION_LIMIT)
  });
  const response = await fetch(`${API_BASE_URL}/v1/search/courses/recommendations?${params.toString()}`);
  if (!response.ok) throw new Error(`Recommendations failed (${response.status})`);
  return unwrap<CourseRecommendation[]>(await response.json());
}

function levelLabel(level?: string): string {
  const labels: Record<string, string> = {
    BEGINNER: "Nhập môn",
    INTERMEDIATE: "Trung cấp",
    ADVANCED: "Nâng cao",
    EXPERT: "Chuyên sâu"
  };
  return labels[level ?? ""] ?? level ?? "Mọi trình độ";
}

function statusLabel(status?: string): string {
  if (status === "PUBLISHED") return "Đang mở";
  if (status === "ARCHIVED") return "Lưu trữ";
  if (status === "DRAFT") return "Nháp";
  return status ?? "Catalog";
}

function formatUpdatedAt(value?: string): string {
  if (!value) return "Cập nhật gần đây";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Cập nhật gần đây";
  return new Intl.DateTimeFormat("vi-VN", {
    month: "short",
    day: "2-digit",
    year: "numeric"
  }).format(date);
}

function departmentLabel(departmentId?: string): string | undefined {
  if (!departmentId) return undefined;
  const looksLikeUuid =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(departmentId);
  return looksLikeUuid ? undefined : departmentId;
}

function descriptionText(result: SearchResult): string {
  return result.description?.trim() || result.summary?.trim() || "Khóa học đã có trong catalog CourseFlow.";
}

function courseHref(result: SearchResult): string {
  return result.slug ? `/courses/${result.slug}` : `/search?q=${encodeURIComponent(result.title)}`;
}

function resultAccent(index: number): string {
  const accents = [
    "from-brand-600 to-signal-500",
    "from-accent-500 to-coral-500",
    "from-signal-600 to-brand-500",
    "from-ink-800 to-brand-600"
  ];
  return accents[index % accents.length];
}

function SearchStat({
  icon,
  label,
  value
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-black/10 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-ink-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-ink-900">{value}</p>
        </div>
        <span className="grid size-10 place-items-center rounded-md bg-brand-50 text-brand-700">
          {icon}
        </span>
      </div>
    </div>
  );
}

function SuggestionLine({ result }: { result: SearchResult }) {
  return (
    <span className="block min-w-0 truncate">
      <span className="font-semibold text-ink-900">{result.title}</span>
      <span className="text-ink-500"> - {descriptionText(result)}</span>
    </span>
  );
}

function ResultCard({ result, index }: { result: SearchResult; index: number }) {
  const href = courseHref(result);
  const levelToneName = levelTone[result.level ?? ""] ?? "neutral";
  const department = departmentLabel(result.departmentId);

  return (
    <Card className="flex min-h-[330px] flex-col overflow-hidden" padding="none">
      <div className={cn("bg-gradient-to-br p-4 text-white", resultAccent(index))}>
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-bold">{result.code ?? "COURSE"}</span>
          <Badge tone="dark">{statusLabel(result.status)}</Badge>
        </div>
        <div className="mt-8 flex items-end justify-between gap-4">
          <span className="grid size-12 place-items-center rounded-md bg-white/15">
            <BookOpen className="size-6" />
          </span>
          <Badge tone="dark">{levelLabel(result.level)}</Badge>
        </div>
      </div>

      <div className="flex flex-1 flex-col p-5">
        <div className="flex flex-wrap gap-2">
          <Badge tone={levelToneName}>{levelLabel(result.level)}</Badge>
          {department && <Badge tone="neutral">{department}</Badge>}
        </div>
        <h2 className="mt-4 text-lg font-bold leading-6 text-ink-900">
          <Link href={href} className="transition hover:text-brand-700">
            {result.title}
          </Link>
        </h2>
        <p className="mt-2 line-clamp-3 flex-1 text-sm leading-6 text-ink-500">
          {descriptionText(result)}
        </p>

        <div className="mt-5 grid gap-2 rounded-lg border border-black/10 bg-[#fbfaf7] p-3 text-sm text-ink-500">
          <span className="inline-flex items-center gap-2">
            <Clock3 className="size-4" />
            {formatUpdatedAt(result.updatedAt)}
          </span>
          <span className="inline-flex items-center gap-2">
            <GraduationCap className="size-4" />
            {statusLabel(result.status)}
          </span>
        </div>

        <div className="mt-5 flex items-center justify-end">
          <Link
            href={href}
            className="inline-flex items-center gap-1 text-sm font-bold text-brand-700 transition hover:text-brand-900"
          >
            Xem khóa học <ArrowRight className="size-4" />
          </Link>
        </div>
      </div>
    </Card>
  );
}

function RecommendationCard({
  item,
  index,
  onPick
}: {
  item: CourseRecommendation;
  index: number;
  onPick: (title: string) => void;
}) {
  const result = item.course;
  const href = courseHref(result);

  return (
    <article className="group rounded-lg border border-black/10 bg-white p-4 shadow-[0_12px_35px_rgba(23,33,31,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_18px_45px_rgba(23,33,31,0.1)]">
      <div className="flex items-start justify-between gap-3">
        <span className={cn("grid size-10 shrink-0 place-items-center rounded-md bg-gradient-to-br text-white", resultAccent(index))}>
          <WandSparkles className="size-5" />
        </span>
        <Badge tone="brand">{item.reason}</Badge>
      </div>
      <Link href={href} className="mt-4 block text-sm leading-6 transition group-hover:text-brand-700">
        <SuggestionLine result={result} />
      </Link>
      <Button variant="ghost" size="sm" className="mt-3 px-0 text-brand-700" onClick={() => onPick(result.title)}>
        Tìm khóa tương tự
        <ArrowRight className="size-4" />
      </Button>
    </article>
  );
}

export function SearchView() {
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(0);
  const [suggestOpen, setSuggestOpen] = useState(false);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setPage(0);
      setDebouncedQ(q.trim());
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [q]);

  const searchQuery = useQuery({
    queryKey: ["search", debouncedQ, page],
    queryFn: () => searchCourses(debouncedQ, page),
    placeholderData: (previous) => previous,
    staleTime: 15_000
  });
  const suggestionsQuery = useQuery({
    queryKey: ["search-suggest", debouncedQ],
    queryFn: () => suggestCourses(debouncedQ),
    enabled: debouncedQ.length >= 2,
    placeholderData: (previous) => previous,
    staleTime: 30_000
  });
  const recommendationsQuery = useQuery({
    queryKey: ["search-recommendations", debouncedQ],
    queryFn: () => recommendCourses(debouncedQ),
    placeholderData: (previous) => previous,
    staleTime: 30_000
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    setPage(0);
    setDebouncedQ(q.trim());
    setSuggestOpen(false);
  }

  function pickTopic(term: string) {
    setQ(term);
    setPage(0);
    setDebouncedQ(term);
    setSuggestOpen(false);
  }

  const results = searchQuery.data?.content ?? [];
  const totalHits = searchQuery.data?.totalHits ?? 0;
  const maxPage = Math.max(Math.ceil(totalHits / PAGE_SIZE) - 1, 0);
  const showingFrom = totalHits === 0 ? 0 : page * PAGE_SIZE + 1;
  const showingTo = Math.min((page + 1) * PAGE_SIZE, totalHits);
  const headline = debouncedQ ? `Kết quả realtime cho "${debouncedQ}"` : "Khóa học đang mở";
  const hasNextPage = page < maxPage;
  const hasPreviousPage = page > 0;
  const suggestions = suggestionsQuery.data ?? [];
  const recommendations = useMemo(
    () => (recommendationsQuery.data ?? []).slice(0, RECOMMENDATION_LIMIT),
    [recommendationsQuery.data]
  );
  const showSuggestions = suggestOpen && debouncedQ.length >= 2;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="space-y-4 xl:sticky xl:top-28 xl:self-start">
          <Card className="rounded-[24px] border-slate-200/80 bg-white/95">
            <div className="flex items-start gap-3">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
                <Filter className="size-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-brand-600">Khung duyệt khóa học</p>
                <h2 className="mt-1 text-xl font-bold tracking-tight text-ink-900">Search workspace</h2>
                <p className="mt-2 text-sm leading-6 text-ink-500">
                  Dùng pattern sidebar + result grid để learner catalog gọn hơn, dễ mở rộng filter về sau.
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-xs font-bold uppercase text-ink-500">Realtime</p>
                <p className="mt-2 text-sm font-semibold text-ink-900">Debounce {SEARCH_DEBOUNCE_MS}ms</p>
                <p className="mt-1 text-sm leading-6 text-ink-500">
                  Search, suggest và recommend cùng cập nhật trong lúc người học gõ.
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-xs font-bold uppercase text-ink-500">Mục đích</p>
                <p className="mt-2 text-sm font-semibold text-ink-900">Từ khám phá đến vào học</p>
                <p className="mt-1 text-sm leading-6 text-ink-500">
                  Giúp người học đi từ catalog sang course detail và lesson player liền mạch hơn.
                </p>
              </div>
            </div>

            <div className="mt-5">
              <p className="inline-flex items-center gap-2 text-sm font-semibold text-ink-900">
                <Sparkles className="size-4 text-brand-700" />
                Chủ đề gợi ý
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {topics.map((term) => (
                  <Button
                    key={term}
                    type="button"
                    variant={debouncedQ === term ? "primary" : "secondary"}
                    size="sm"
                    onClick={() => pickTopic(term)}
                    className="justify-start"
                  >
                    {term}
                  </Button>
                ))}
              </div>
            </div>
          </Card>

          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <SearchStat
              icon={<Layers3 className="size-5" />}
              label="Kết quả"
              value={searchQuery.isFetching && !searchQuery.data ? "..." : `${totalHits}`}
            />
            <SearchStat
              icon={<BookOpen className="size-5" />}
              label="Đang hiển thị"
              value={totalHits > 0 ? `${showingFrom}-${showingTo}` : "0"}
            />
            <SearchStat
              icon={<Filter className="size-5" />}
              label="Trang"
              value={`${page + 1}/${maxPage + 1}`}
            />
          </div>
        </aside>

        <div className="space-y-6">
          <Card className="rounded-[24px] border-slate-200/80 bg-white/95">
            <div className="flex items-start gap-4">
              <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
                <Compass className="size-6" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-2xl font-bold tracking-tight text-ink-900">Bạn muốn học gì tiếp theo?</h2>
                  <Badge tone="sky">Realtime ES</Badge>
                </div>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
                  Tìm theo tên khóa học hoặc nội dung mô tả. Kết quả và gợi ý được cập nhật khi bạn gõ.
                </p>
              </div>
            </div>

            <form className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto]" onSubmit={submit}>
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-ink-500" />
                <TextInput
                  value={q}
                  onChange={(e) => {
                    setQ(e.target.value);
                    setSuggestOpen(true);
                  }}
                  onFocus={() => setSuggestOpen(true)}
                  onBlur={() => window.setTimeout(() => setSuggestOpen(false), 140)}
                  placeholder="Tìm theo tên khóa học hoặc nội dung..."
                  className="pl-11"
                />

                {showSuggestions && (
                  <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-20 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_22px_55px_rgba(23,33,31,0.16)]">
                    <div className="border-b border-slate-200 px-4 py-3">
                      <p className="text-xs font-bold uppercase text-ink-500">Gợi ý khóa học</p>
                    </div>
                    {suggestionsQuery.isFetching && (
                      <div className="space-y-2 p-4">
                        {[1, 2, 3].map((item) => (
                          <div key={item} className="h-5 animate-pulse rounded-md bg-black/10" />
                        ))}
                      </div>
                    )}
                    {!suggestionsQuery.isFetching && suggestions.length === 0 && (
                      <p className="px-4 py-3 text-sm text-ink-500">Chưa có gợi ý phù hợp.</p>
                    )}
                    {!suggestionsQuery.isFetching &&
                      suggestions.map((result) => (
                        <Link
                          key={result.id}
                          href={courseHref(result)}
                          className="block border-b border-black/5 px-4 py-3 text-sm transition last:border-b-0 hover:bg-brand-50"
                        >
                          <SuggestionLine result={result} />
                        </Link>
                      ))}
                  </div>
                )}
              </div>
              <Button type="submit" className="min-w-36">
                <Search className="size-4" />
                Tìm kiếm
              </Button>
            </form>

            <div className="mt-5 flex flex-wrap items-center gap-2 text-sm text-ink-500">
              <span className="inline-flex items-center gap-2 font-semibold">
                <Sparkles className="size-4" />
                Search UX theo hướng learner app
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-ink-700">
                Suggest inline
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-ink-700">
                Recommendation rail
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-ink-700">
                Catalog grid
              </span>
            </div>
          </Card>

          {recommendations.length > 0 && (
            <section className="rounded-[24px] border border-slate-200/80 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-brand-600">Recommend từ Elasticsearch</p>
                  <h2 className="mt-1 text-xl font-bold tracking-tight text-ink-900">Có thể bạn sẽ học tiếp</h2>
                </div>
                {recommendationsQuery.isFetching && <Badge tone="neutral">Đang cập nhật</Badge>}
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {recommendations.map((item, index) => (
                  <RecommendationCard key={item.course.id} item={item} index={index} onPick={pickTopic} />
                ))}
              </div>
            </section>
          )}

          <section className="flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-slate-200/80 bg-white px-5 py-4 shadow-sm">
            <div>
              <p className="text-sm font-bold text-brand-600">{headline}</p>
              <p className="mt-1 text-sm text-ink-500">
                {searchQuery.isFetching ? "Đang cập nhật danh sách..." : `${totalHits} khóa học phù hợp`}
              </p>
            </div>
            {debouncedQ && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setQ("");
                  setDebouncedQ("");
                  setPage(0);
                }}
              >
                Xem tất cả
              </Button>
            )}
          </section>
        </div>
      </section>

      {searchQuery.isError && (
        <Card className="rounded-[24px] border-coral-50 bg-coral-50/60">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-bold text-ink-900">Không tải được catalog</h3>
              <p className="mt-1 text-sm text-ink-500">
                Search service, Elasticsearch hoặc API gateway có thể chưa sẵn sàng.
              </p>
            </div>
            <Button variant="secondary" onClick={() => searchQuery.refetch()}>
              <RefreshCw className="size-4" />
              Tải lại
            </Button>
          </div>
        </Card>
      )}

      {searchQuery.isFetching && !searchQuery.data && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="h-[330px] animate-pulse rounded-2xl border border-slate-200 bg-white/70"
            />
          ))}
        </div>
      )}

      {!searchQuery.isFetching && !searchQuery.isError && totalHits === 0 && (
        <EmptyState
          title="Không có khóa học phù hợp"
          description="Thử nhập tên khóa học hoặc một cụm từ xuất hiện trong phần mô tả."
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setQ("");
                setDebouncedQ("");
                setPage(0);
              }}
            >
              Xem catalog
            </Button>
          }
        />
      )}

      {results.length > 0 && (
        <div
          className={cn(
            "grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3",
            searchQuery.isFetching && "opacity-70"
          )}
        >
          {results.map((result, index) => (
            <ResultCard key={result.id} result={result} index={index} />
          ))}
        </div>
      )}

      {totalHits > PAGE_SIZE && (
        <div className="flex flex-col gap-3 rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-ink-500">
            Hiển thị {showingFrom}-{showingTo} trong {totalHits} khóa học
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={!hasPreviousPage || searchQuery.isFetching}
              onClick={() => setPage((current) => Math.max(current - 1, 0))}
            >
              <ChevronLeft className="size-4" />
              Trước
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!hasNextPage || searchQuery.isFetching}
              onClick={() => setPage((current) => Math.min(current + 1, maxPage))}
            >
              Sau
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
