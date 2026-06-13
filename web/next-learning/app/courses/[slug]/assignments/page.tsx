import Link from "next/link";
import { notFound } from "next/navigation";
import { getCourseBySlug } from "@/features/course-catalog/api";
import { AssignmentsView } from "@/features/assignments/AssignmentsView";
import { SectionHeader } from "@/shared/ui";

export default async function CourseAssignmentsPage({
  params,
  searchParams
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ assignmentId?: string }>;
}) {
  const { slug } = await params;
  const { assignmentId = "" } = await searchParams;
  const course = await getCourseBySlug(slug);
  if (!course?.id) notFound();

  return (
    <main className="mx-auto max-w-6xl px-5 py-8 sm:px-6 lg:px-8">
      <Link href={`/courses/${slug}`} className="text-sm font-semibold text-ink-500 hover:text-ink-800">
        ← Quay lại khóa học
      </Link>
      <SectionHeader
        eyebrow="CourseFlow LMS"
        title="Bài tập của khóa học"
        description="Theo dõi hạn nộp, đọc yêu cầu và nộp bài trong cùng một màn hình."
        className="mb-7 mt-3"
      />
      <AssignmentsView courseId={course.id} initialAssignmentId={assignmentId} />
    </main>
  );
}
