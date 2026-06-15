import type { CatalogCourse } from "@/features/course-catalog/api";

export type RelatedCourseEventType = "IMPRESSION" | "CLICK";

export type RelatedCourseRecommendation = {
  recommendationId?: string;
  sourceCourseId: string;
  relatedCourseId: string;
  course: CatalogCourse;
  source: string;
  reason: string;
  reasonCode?: string;
  placement?: string;
  modelVersion?: string;
  score?: number;
};

type RelatedCourseRecord = Record<string, unknown>;

function isRecord(value: unknown): value is RelatedCourseRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function numberValue(value: unknown): number | undefined {
  const next = typeof value === "number" ? value : Number(value);
  return Number.isFinite(next) ? next : undefined;
}

function asCatalogCourse(value: unknown): CatalogCourse | null {
  if (!isRecord(value)) return null;
  const title = stringValue(value.title);
  const slug = stringValue(value.slug);
  const id = stringValue(value.id);
  if (!title && !slug && !id) return null;

  return {
    id,
    code: stringValue(value.code) ?? "COURSE",
    title: title ?? `Khóa ${compactCourseId(id)}`,
    slug: slug ?? "",
    summary:
      stringValue(value.summary) ??
      stringValue(value.description) ??
      "Khóa học liên quan trong catalog CourseFlow.",
    level: stringValue(value.level),
    status: stringValue(value.status),
    listPrice: typeof value.listPrice === "number" || typeof value.listPrice === "string" ? value.listPrice : undefined,
    currency: typeof value.currency === "string" || value.currency === null ? value.currency : undefined,
    priceStatus: typeof value.priceStatus === "string" || value.priceStatus === null ? value.priceStatus : undefined
  };
}

export function compactCourseId(value?: string) {
  if (!value) return "chưa rõ";
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

export function relatedCourseHref(course: CatalogCourse): string {
  return course.slug ? `/courses/${course.slug}` : `/search?q=${encodeURIComponent(course.title || course.id || "")}`;
}

export function relatedCourseSourceLabel(source?: string): string {
  const labels: Record<string, string> = {
    MANUAL: "Curated",
    CURATED: "Curated",
    ANALYTICS: "Analytics",
    ENROLLMENT: "Learner trend",
    SEARCH: "Search",
    POPULARITY: "Popular"
  };
  return labels[(source ?? "").toUpperCase()] ?? source ?? "Related";
}

export function defaultRelatedCourseReason(source?: string, score?: number): string {
  const normalized = (source ?? "").toUpperCase();
  if (normalized === "MANUAL" || normalized === "CURATED") {
    return "Được đội học thuật chọn làm khóa học tiếp theo phù hợp.";
  }
  if (typeof score === "number" && score >= 0.85) {
    return "Có độ liên quan cao dựa trên hành vi học và chủ đề khóa học.";
  }
  return "Người học cùng chủ đề thường tiếp tục với khóa học này.";
}

export function normalizeRelatedCourses(
  payload: unknown,
  catalog: CatalogCourse[],
  sourceCourseId: string
): RelatedCourseRecommendation[] {
  const rows = Array.isArray(payload) ? payload : [];
  const catalogById = new Map(catalog.filter((course) => course.id).map((course) => [course.id!, course]));
  const seen = new Set<string>();

  return rows.flatMap((row) => {
    if (!isRecord(row)) return [];
    const nestedCourse = asCatalogCourse(row.course) ?? asCatalogCourse(row.relatedCourse);
    const directCourse = asCatalogCourse(row);
    const relatedCourseId =
      stringValue(row.relatedCourseId) ??
      nestedCourse?.id ??
      (directCourse?.id && directCourse.id !== sourceCourseId ? directCourse.id : undefined);

    if (!relatedCourseId || relatedCourseId === sourceCourseId || seen.has(relatedCourseId)) return [];

    const catalogCourse = catalogById.get(relatedCourseId);
    const course =
      nestedCourse ??
      (directCourse?.title || directCourse?.slug ? directCourse : null) ??
      catalogCourse ?? {
        id: relatedCourseId,
        code: "COURSE",
        title: `Khóa ${compactCourseId(relatedCourseId)}`,
        slug: "",
        summary: "Khóa học liên quan trong catalog CourseFlow."
      };
    const source = stringValue(row.source) ?? stringValue(row.recommendationSource) ?? stringValue(row.sourceType) ?? "ANALYTICS";
    const score = numberValue(row.score);
    const reason = stringValue(row.reason) ?? defaultRelatedCourseReason(source, score);

    seen.add(relatedCourseId);
    return [
      {
        recommendationId: stringValue(row.id),
        sourceCourseId,
        relatedCourseId,
        course,
        source,
        reason,
        reasonCode: stringValue(row.reasonCode),
        placement: stringValue(row.placement),
        modelVersion: stringValue(row.modelVersion),
        score
      }
    ];
  });
}
