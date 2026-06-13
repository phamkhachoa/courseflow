"use client";

import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  LogIn,
  MessageSquareText,
  Send,
  Star,
  ThumbsUp
} from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import {
  useCourseReviews,
  useMarkHelpful,
  usePostReview,
  useRatingSummary,
  type CourseReview,
  type RatingSummary
} from "./hooks";
import { Badge, Button, Card, ProgressBar, Textarea, TextInput, cn } from "@/shared/ui";

type ReviewsPanelProps = {
  courseId: string;
  courseSlug: string;
  courseTitle: string;
  initialSummary?: RatingSummary | null;
  initialReviews?: CourseReview[];
};

const ratingLabels: Record<number, string> = {
  1: "Cần cải thiện",
  2: "Tạm ổn",
  3: "Ổn",
  4: "Rất tốt",
  5: "Xuất sắc"
};

function Stars({ value, className }: { value: number; className?: string }) {
  const active = Math.round(value);
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)} aria-label={`${value.toFixed(1)} trên 5 sao`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={cn("size-4", star <= active ? "fill-accent-500 text-accent-500" : "text-black/20")}
        />
      ))}
    </span>
  );
}

function formatDate(value?: string) {
  if (!value) return "Vừa xong";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Vừa xong";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(date);
}

function learnerLabel(review: CourseReview, currentUserId?: number) {
  if (String(currentUserId ?? "") === review.userId) return "Bạn";
  return `Học viên ${review.userId.slice(-4)}`;
}

function ratingRows(summary?: RatingSummary | null) {
  return [
    { rating: 5, count: summary?.count5 ?? 0 },
    { rating: 4, count: summary?.count4 ?? 0 },
    { rating: 3, count: summary?.count3 ?? 0 },
    { rating: 2, count: summary?.count2 ?? 0 },
    { rating: 1, count: summary?.count1 ?? 0 }
  ];
}

export function ReviewsPanel({
  courseId,
  courseSlug,
  courseTitle,
  initialSummary = null,
  initialReviews = []
}: ReviewsPanelProps) {
  const { session, hydrated } = useLearnerSession();
  const summary = useRatingSummary(courseId, initialSummary);
  const reviews = useCourseReviews(courseId, initialReviews);
  const postReview = usePostReview(courseId);
  const markHelpful = useMarkHelpful(courseId);
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const summaryData = summary.data ?? initialSummary;
  const reviewList = reviews.data ?? initialReviews;
  const signedIn = hydrated && Boolean(session?.accessToken);
  const titleValue = title.trim();
  const bodyValue = body.trim();
  const canSubmit = signedIn && !postReview.isPending;

  const rows = useMemo(() => ratingRows(summaryData), [summaryData]);
  const totalReviews = summaryData?.reviewCount ?? reviewList.length;
  const averageRating = summaryData?.averageRating ?? 0;
  const postError = postReview.error instanceof Error ? postReview.error.message : null;
  const helpfulError = markHelpful.error instanceof Error ? markHelpful.error.message : null;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!signedIn) return;

    postReview.mutate(
      {
        rating,
        title: titleValue || undefined,
        body: bodyValue || undefined
      },
      {
        onSuccess: () => {
          setTitle("");
          setBody("");
          setRating(5);
        }
      }
    );
  }

  return (
    <section className="space-y-7">
      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div>
          <p className="text-sm font-semibold uppercase text-brand-700">Điểm học viên</p>
          <div className="mt-3 flex items-end gap-3">
            <span className="text-6xl font-bold leading-none text-ink-900">{averageRating.toFixed(1)}</span>
            <div className="pb-1">
              <Stars value={averageRating} className="mb-2" />
              <p className="text-sm text-ink-500">{totalReviews} đánh giá</p>
            </div>
          </div>
          {summary.isError && (
            <p className="mt-3 flex items-center gap-2 text-sm text-coral-600">
              <AlertCircle className="size-4" />
              Chưa tải được thống kê sao.
            </p>
          )}
        </div>

        <div className="space-y-3">
          {rows.map((row) => {
            const percent = totalReviews > 0 ? (row.count / totalReviews) * 100 : 0;
            return (
              <div key={row.rating} className="grid grid-cols-[58px_minmax(0,1fr)_44px] items-center gap-3">
                <span className="flex items-center gap-1 text-sm font-semibold text-ink-700">
                  {row.rating}
                  <Star className="size-4 fill-accent-500 text-accent-500" />
                </span>
                <ProgressBar value={percent} />
                <span className="text-right text-sm text-ink-500">{row.count}</span>
              </div>
            );
          })}
        </div>
      </div>

      <Card padding="lg" className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Badge tone={signedIn ? "brand" : "neutral"}>{signedIn ? session?.user.fullName || "Học viên" : "Khách"}</Badge>
            <h2 className="mt-3 text-xl font-bold text-ink-900">Đánh giá khóa học này</h2>
            <p className="mt-1 text-sm leading-6 text-ink-500">{courseTitle}</p>
          </div>
          <Button asChild variant="secondary">
            <Link href={`/courses/${courseSlug}/modules`}>
              <MessageSquareText className="size-4" />
              Vào lớp học
            </Link>
          </Button>
        </div>

        {!hydrated && <p className="text-sm text-ink-500">Đang kiểm tra phiên đăng nhập...</p>}

        {hydrated && !signedIn && (
          <div className="rounded-lg border border-dashed border-black/15 bg-brand-50/50 p-4">
            <p className="text-sm font-semibold text-ink-800">Đăng nhập để gửi đánh giá và đánh dấu review hữu ích.</p>
            <Button asChild className="mt-3">
              <Link href="/login">
                <LogIn className="size-4" />
                Đăng nhập
              </Link>
            </Button>
          </div>
        )}

        {signedIn && (
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-semibold text-ink-700">Mức hài lòng</label>
              <div className="mt-2 grid grid-cols-5 gap-2">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={cn(
                      "flex min-h-12 flex-col items-center justify-center rounded-md border px-2 py-2 text-sm font-bold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-100",
                      rating === value
                        ? "border-accent-400 bg-accent-50 text-ink-900"
                        : "border-black/10 bg-white text-ink-600 hover:bg-brand-50"
                    )}
                    onClick={() => setRating(value)}
                    aria-pressed={rating === value}
                  >
                    <span className="flex items-center gap-1">
                      {value}
                      <Star className="size-4 fill-accent-500 text-accent-500" />
                    </span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-sm text-ink-500">{ratingLabels[rating]}</p>
            </div>

            <TextInput
              value={title}
              maxLength={90}
              placeholder="Tiêu đề ngắn, ví dụ: Lộ trình rõ và bài tập sát thực tế"
              onChange={(event) => setTitle(event.target.value)}
            />
            <Textarea
              value={body}
              maxLength={1200}
              placeholder="Chia sẻ trải nghiệm học, điểm mạnh của khóa và phần cần cải thiện"
              onChange={(event) => setBody(event.target.value)}
            />

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-ink-500">{bodyValue.length}/1200 ký tự</p>
              <Button type="submit" disabled={!canSubmit}>
                {postReview.isPending ? (
                  "Đang gửi..."
                ) : (
                  <>
                    <Send className="size-4" />
                    Gửi đánh giá
                  </>
                )}
              </Button>
            </div>

            {postReview.isSuccess && (
              <p className="flex items-center gap-2 text-sm font-semibold text-brand-700">
                <CheckCircle2 className="size-4" />
                Đã ghi nhận đánh giá của bạn.
              </p>
            )}
            {postError && (
              <p className="flex items-center gap-2 text-sm text-coral-600">
                <AlertCircle className="size-4" />
                {postError}
              </p>
            )}
          </form>
        )}
      </Card>

      <div className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-ink-900">Nhận xét mới nhất</h2>
          <Badge tone="neutral">{reviewList.length} review</Badge>
        </div>

        {reviews.isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-28 animate-pulse rounded-lg border border-black/10 bg-white/70" />
            ))}
          </div>
        )}

        {reviews.isError && (
          <Card tone="muted" className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 size-5 text-coral-600" />
            <div>
              <h3 className="font-semibold text-ink-900">Chưa tải được danh sách review</h3>
              <p className="mt-1 text-sm text-ink-500">Bạn vẫn có thể gửi đánh giá khi đã đăng nhập.</p>
            </div>
          </Card>
        )}

        {!reviews.isLoading && !reviews.isError && reviewList.length === 0 && (
          <Card tone="muted" className="text-center">
            <Star className="mx-auto size-7 text-accent-500" />
            <h3 className="mt-3 font-bold text-ink-900">Chưa có đánh giá nào</h3>
            <p className="mt-1 text-sm text-ink-500">Hãy là học viên đầu tiên chia sẻ trải nghiệm của khóa này.</p>
          </Card>
        )}

        {helpfulError && (
          <p className="flex items-center gap-2 text-sm text-coral-600">
            <AlertCircle className="size-4" />
            {helpfulError}
          </p>
        )}

        <ul className="space-y-3">
          {reviewList.map((review) => (
            <li key={review.id}>
              <article className="rounded-lg border border-black/10 bg-white p-5 shadow-[0_12px_35px_rgba(23,33,31,0.06)]">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Stars value={review.rating} />
                      <span className="text-sm font-semibold text-ink-700">{ratingLabels[review.rating]}</span>
                    </div>
                    <p className="mt-2 text-sm text-ink-500">
                      {learnerLabel(review, session?.user.id)} · {formatDate(review.createdAt)}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={!signedIn || markHelpful.isPending}
                    onClick={() => markHelpful.mutate({ reviewId: review.id })}
                  >
                    <ThumbsUp className="size-4" />
                    Hữu ích ({review.helpfulCount})
                  </Button>
                </div>
                {review.title && <h3 className="mt-4 text-lg font-bold text-ink-900">{review.title}</h3>}
                {review.body && <p className="mt-2 text-sm leading-7 text-ink-600">{review.body}</p>}
              </article>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
