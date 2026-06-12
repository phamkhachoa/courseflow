import { serverFetch } from "@/shared/api/server";
import { clientFetch } from "@/shared/api/client";
import type { CatalogCourse } from "@/features/course-catalog/api";

// GET /v1/courses/{courseId}/related
export async function getRelatedCourses(courseId: string): Promise<CatalogCourse[]> {
  return serverFetch<CatalogCourse[]>(`/v1/courses/${courseId}/related`, {
    revalidate: 60
  });
}

// GET /v1/analytics/students/{studentId}/recommendations
export async function getRecommendations(studentId: string): Promise<CatalogCourse[]> {
  return clientFetch<CatalogCourse[]>(
    `/v1/analytics/students/${studentId}/recommendations`
  );
}
