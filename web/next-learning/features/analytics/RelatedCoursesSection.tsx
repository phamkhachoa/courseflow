import Link from "next/link";
import { Badge, Card } from "@/shared/ui";
import { getRelatedCourses } from "./api";

export async function RelatedCoursesSection({ courseId }: { courseId: string }) {
  let courses;
  try {
    courses = await getRelatedCourses(courseId);
  } catch {
    return null;
  }

  if (!courses || courses.length === 0) return null;

  const visibleCourses = courses.filter((course) => course.slug && course.title);
  if (visibleCourses.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="mb-4 text-xl font-semibold text-slate-800">Khóa học liên quan</h2>
      <div className="flex flex-wrap gap-4">
        {visibleCourses.map((course, index) => (
          <Link key={course.slug ?? `${course.code}-${index}`} href={`/courses/${course.slug}`} className="block w-72">
            <Card className="h-full transition hover:shadow-md">
              <p className="text-xs font-bold text-brand-600">{course.code}</p>
              <h3 className="mt-1 font-semibold text-slate-800">{course.title}</h3>
              {course.level && (
                <div className="mt-2">
                  <Badge>{course.level}</Badge>
                </div>
              )}
              <p className="mt-2 text-sm text-slate-500 line-clamp-3">{course.summary}</p>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
