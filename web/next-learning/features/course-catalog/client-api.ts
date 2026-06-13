"use client";

import { clientFetch } from "@/shared/api/client";
import type { CatalogCourse } from "./api";

export async function listCatalogCourses(): Promise<CatalogCourse[]> {
  return clientFetch<CatalogCourse[]>("/v1/courses");
}

export function courseModuleHref(course?: CatalogCourse | null): string {
  if (!course) return "/search";
  return course.id ? `/courses/${course.slug}/modules` : `/courses/${course.slug}`;
}

export function courseDetailHref(course?: CatalogCourse | null): string {
  if (!course) return "/search";
  return `/courses/${course.slug}`;
}
