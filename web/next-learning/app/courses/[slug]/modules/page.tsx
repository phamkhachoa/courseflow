import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, BookOpen, GraduationCap } from "lucide-react";
import { getCourseBySlug } from "@/features/course-catalog/api";
import { ModuleList } from "@/features/course-modules/ModuleList";
import { ScrollToTopOnMount } from "@/features/course-modules/ScrollToTopOnMount";
import { Badge } from "@/shared/ui";

export default async function CourseModulesPage({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const course = await getCourseBySlug(slug);
  if (!course) notFound();
  const resolvedCourseId = course.id || "";

  return (
    <main className="min-h-screen bg-[#f7f4ee]">
      <ScrollToTopOnMount />
      <section className="border-b border-black/10 bg-white">
        <div className="mx-auto max-w-7xl px-5 py-6 sm:px-6 lg:px-8">
          <Link
            href={`/courses/${slug}`}
            className="inline-flex items-center gap-2 text-sm font-semibold text-ink-500 transition hover:text-ink-900"
          >
            <ArrowLeft className="size-4" />
            Quay lại khóa học
          </Link>
          <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="flex flex-wrap gap-2">
                <Badge tone="brand">CourseFlow LMS</Badge>
                <Badge tone="sky">Lộ trình học</Badge>
              </div>
              <h1 className="mt-3 text-3xl font-bold tracking-normal text-ink-900 sm:text-4xl">
                Phòng học của bạn
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-500">
                Xem video, chuyển bài và theo dõi chương học trong một màn hình.
              </p>
            </div>
            <div className="hidden items-center gap-3 rounded-lg border border-black/10 bg-[#fbfaf7] px-4 py-3 text-sm font-semibold text-ink-700 sm:flex">
              <GraduationCap className="size-5 text-brand-700" />
              Học tiếp từ bài đang chọn
              <BookOpen className="size-5 text-accent-600" />
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-6 sm:px-6 lg:px-8">
        <ModuleList courseId={resolvedCourseId} courseSlug={slug} />
      </section>
    </main>
  );
}
