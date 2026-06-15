import { serverFetch } from "@/shared/api/server";
import type { CatalogCourse } from "@/features/course-catalog/api";
import { getFeaturedCourses } from "@/features/course-catalog/api";
import { normalizeRelatedCourses, type RelatedCourseRecommendation } from "./related-courses";

// GET /v1/courses/{courseId}/related
export async function getRelatedCourses(courseId: string): Promise<RelatedCourseRecommendation[]> {
  const payload = await serverFetch<unknown>(`/v1/courses/${courseId}/related?limit=6`, {
    revalidate: 60
  });
  let catalog: CatalogCourse[] = [];
  try {
    catalog = await getFeaturedCourses();
  } catch {
    catalog = [];
  }
  return normalizeRelatedCourses(payload, catalog, courseId);
}
