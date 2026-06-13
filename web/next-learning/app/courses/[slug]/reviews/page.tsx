import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Star } from "lucide-react";
import { getCourseBySlug } from "@/features/course-catalog/api";
import { getCourseReviews, getRatingSummary } from "@/features/reviews/api";
import { ReviewsPanel } from "@/features/reviews/ReviewsPanel";
import { Badge, LinkButton } from "@/shared/ui";

type Props = { params: Promise<{ slug: string }> };

export default async function CourseReviewsPage({ params }: Props) {
  const { slug } = await params;
  const course = await getCourseBySlug(slug);
  if (!course?.id) notFound();

  const [summaryResult, reviewsResult] = await Promise.allSettled([
    getRatingSummary(course.id),
    getCourseReviews(course.id)
  ]);
  const summary = summaryResult.status === "fulfilled" ? summaryResult.value : null;
  const reviews = reviewsResult.status === "fulfilled" ? reviewsResult.value : [];
  const average = summary?.averageRating ?? 0;

  return (
    <main className="bg-[#f7f4ee] pb-12">
      <section className="border-b border-black/10 bg-white">
        <div className="mx-auto max-w-6xl px-5 py-8 sm:px-6 lg:px-8">
          <Link href={`/courses/${course.slug}`} className="inline-flex items-center gap-2 text-sm font-semibold text-ink-500 transition hover:text-ink-900">
            <ArrowLeft className="size-4" />
            Quay lại khóa học
          </Link>
          <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
            <div>
              <div className="flex flex-wrap gap-2">
                <Badge tone="brand">{course.code}</Badge>
                <Badge tone="amber">Review học viên</Badge>
              </div>
              <h1 className="mt-4 max-w-3xl text-3xl font-bold leading-tight text-ink-900 sm:text-4xl">
                Đánh giá khóa học
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-ink-500">{course.title}</p>
            </div>
            <div className="rounded-lg border border-black/10 bg-[#102b28] p-5 text-white shadow-[0_18px_40px_rgba(16,43,40,0.18)]">
              <div className="flex items-center gap-3">
                <span className="text-4xl font-bold">{average.toFixed(1)}</span>
                <div>
                  <div className="flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((item) => (
                      <Star
                        key={item}
                        className={`size-4 ${item <= Math.round(average) ? "fill-accent-400 text-accent-400" : "text-white/25"}`}
                      />
                    ))}
                  </div>
                  <p className="mt-1 text-sm text-white/70">{summary?.reviewCount ?? reviews.length} đánh giá</p>
                </div>
              </div>
              <LinkButton
                href={`/courses/${course.slug}/modules`}
                variant="inverse"
                className="mt-5 w-full"
              >
                Vào lớp học
              </LinkButton>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-8 sm:px-6 lg:px-8">
        <ReviewsPanel
          courseId={course.id}
          courseSlug={course.slug}
          courseTitle={course.title}
          initialSummary={summary}
          initialReviews={reviews}
        />
      </section>
    </main>
  );
}
