import { serverFetch } from "@/shared/api/server";

export type CatalogCourse = {
  id?: string;
  code: string;
  title: string;
  slug: string;
  summary: string;
  level?: string;
  status?: string;
  listPrice?: number | string | null;
  currency?: string | null;
  priceStatus?: string | null;
};

const FALLBACK: CatalogCourse[] = [
  {
    id: "30000000-0000-0000-0000-000000000001",
    code: "SE401",
    title: "Production Microservices with Spring Boot",
    slug: "production-microservices-spring-boot",
    summary: "Demo course seeded by course-service for CourseFlow v2.",
    level: "ADVANCED",
    status: "PUBLISHED",
    listPrice: 100,
    currency: "USD",
    priceStatus: "ACTIVE"
  }
];


/** Public catalog. Falls back to a seeded demo when the gateway is offline. */
export async function getFeaturedCourses(): Promise<CatalogCourse[]> {
  try {
    return await serverFetch<CatalogCourse[]>("/v1/courses", { revalidate: 60 });
  } catch {
    return FALLBACK;
  }
}

export async function getCourseBySlug(slug: string): Promise<CatalogCourse | null> {
  try {
    return await serverFetch<CatalogCourse>(`/v1/courses/${slug}`, { revalidate: 60 });
  } catch {
    return FALLBACK.find((c) => c.slug === slug) ?? null;
  }
}
