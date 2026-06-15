import { getRelatedCourses } from "./api";
import { RelatedCoursesClient } from "./RelatedCoursesClient";

export async function RelatedCoursesSection({ courseId }: { courseId: string }) {
  let recommendations;
  try {
    recommendations = await getRelatedCourses(courseId);
  } catch {
    return null;
  }

  if (!recommendations || recommendations.length === 0) return null;

  return (
    <section className="mt-10">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Gợi ý tiếp theo</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-ink-900">Khóa học liên quan</h2>
        </div>
      </div>
      <RelatedCoursesClient recommendations={recommendations} />
    </section>
  );
}
