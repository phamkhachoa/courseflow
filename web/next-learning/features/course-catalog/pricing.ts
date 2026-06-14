import type { CatalogCourse } from "./api";

export function formatCoursePrice(course?: Pick<CatalogCourse, "listPrice" | "currency" | "priceStatus"> | null) {
  if (!course) return null;
  const status = (course.priceStatus ?? "").toUpperCase();
  const value = typeof course.listPrice === "number" ? course.listPrice : Number(course.listPrice ?? Number.NaN);
  if (status === "FREE" || value === 0) return "Miễn phí";
  if (!Number.isFinite(value) || !course.currency) return "Chưa mở bán";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: course.currency,
    maximumFractionDigits: 0
  }).format(value);
}
