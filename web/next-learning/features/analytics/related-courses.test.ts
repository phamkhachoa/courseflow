import { describe, expect, it } from "vitest";
import type { CatalogCourse } from "@/features/course-catalog/api";
import { normalizeRelatedCourses, relatedCourseHref } from "./related-courses";

const catalog: CatalogCourse[] = [
  {
    id: "course-a",
    code: "SE401",
    title: "Production Microservices",
    slug: "production-microservices",
    summary: "Build reliable services.",
    level: "ADVANCED"
  },
  {
    id: "course-b",
    code: "SE402",
    title: "Observability",
    slug: "observability",
    summary: "Trace and monitor services.",
    level: "INTERMEDIATE"
  }
];

describe("related course normalization", () => {
  it("enriches analytics related-course rows with catalog details", () => {
    const rows = normalizeRelatedCourses(
      [{ courseId: "course-a", relatedCourseId: "course-b", score: 0.91 }],
      catalog,
      "course-a"
    );

    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      sourceCourseId: "course-a",
      relatedCourseId: "course-b",
      source: "ANALYTICS",
      score: 0.91,
      course: {
        code: "SE402",
        title: "Observability",
        slug: "observability"
      }
    });
    expect(rows[0].reason).toContain("độ liên quan cao");
    expect(relatedCourseHref(rows[0].course)).toBe("/courses/observability");
  });

  it("supports future curated responses with nested course and reason", () => {
    const rows = normalizeRelatedCourses(
      [
        {
          id: "relation-1",
          relatedCourseId: "course-b",
          source: "MANUAL",
          reason: "Học tiếp để vận hành production tốt hơn.",
          relatedCourse: catalog[1]
        }
      ],
      catalog,
      "course-a"
    );

    expect(rows[0].recommendationId).toBe("relation-1");
    expect(rows[0].source).toBe("MANUAL");
    expect(rows[0].reason).toBe("Học tiếp để vận hành production tốt hơn.");
  });
});
