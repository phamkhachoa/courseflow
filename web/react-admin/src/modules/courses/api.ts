import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";
import type { Course, CourseMaterial, CreateCourseInput } from "./types";

export type AddCourseMaterialInput = {
  title: string;
  materialType: string;
  mediaId?: string;
  position?: number;
};

export async function listCourses(status?: string): Promise<Course[]> {
  const { data } = await apiClient.get("/admin/v1/courses", {
    params: status ? { status } : undefined
  });
  return unwrapList<Course>(data);
}

export async function getCourse(courseId: string): Promise<Course> {
  const { data } = await apiClient.get(`/admin/v1/courses/${courseId}`);
  return unwrap<Course>(data);
}

export async function createCourse(input: CreateCourseInput): Promise<Course> {
  const { data } = await apiClient.post("/admin/v1/courses", input);
  return unwrap<Course>(data);
}

export async function addCourseMaterial(
  courseId: string,
  input: AddCourseMaterialInput
): Promise<CourseMaterial> {
  const { data } = await apiClient.post(`/admin/v1/courses/${courseId}/materials`, input);
  return unwrap<CourseMaterial>(data);
}

export async function publishCourse(courseId: string): Promise<Course> {
  const { data } = await apiClient.post(`/admin/v1/courses/${courseId}/publish`, {});
  return unwrap<Course>(data);
}

export async function archiveCourse(courseId: string): Promise<Course> {
  const { data } = await apiClient.post(`/admin/v1/courses/${courseId}/archive`, {});
  return unwrap<Course>(data);
}

export type CourseDraft = {
  courseId: string;
  title: string;
  slug: string;
  summary?: string;
  status: string;
  reviewState?: string;
  currentVersionNo: number;
  lastAuthoredBy?: string;
  modules: CourseModule[];
};

export type CourseModule = {
  moduleId: string;
  title: string;
  description?: string;
  position: number;
  status: string;
  items: CourseModuleItem[];
};

export type CourseModuleItem = {
  itemId: string;
  itemType: string;
  refId: string;
  title: string;
  description?: string;
  videoMediaId?: string;
  documentMediaIds?: string[];
  contentUrl?: string;
  estimatedMinutes?: number;
  position: number;
  required: boolean;
};

export type CourseVersion = {
  id: string;
  courseId: string;
  versionNo: number;
  state: string;
  createdBy?: string;
  note?: string;
  createdAt?: string;
  publishedAt?: string;
};

export async function createCourseDraft(input: {
  code: string;
  title: string;
  slug: string;
  summary: string;
  departmentId: string;
  level: string;
}): Promise<CourseDraft> {
  const { data } = await apiClient.post("/admin/v1/authoring/courses", input);
  return unwrap<CourseDraft>(data);
}

export async function getCourseDraft(courseId: string): Promise<CourseDraft> {
  const { data } = await apiClient.get(`/admin/v1/authoring/courses/${courseId}/draft`);
  return unwrap<CourseDraft>(data);
}

export async function updateCurriculum(
  courseId: string,
  modules: Array<{ moduleId: string; itemIds: string[] }>
): Promise<CourseDraft> {
  const { data } = await apiClient.put(`/admin/v1/authoring/courses/${courseId}/curriculum`, { modules });
  return unwrap<CourseDraft>(data);
}

export async function createModule(
  courseId: string,
  input: { title: string; description?: string; status?: string }
): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/modules`, input);
  return unwrap<CourseDraft>(data);
}

export async function createModuleItem(
  courseId: string,
  moduleId: string,
  input: {
    itemType: string;
    refId?: string;
    title: string;
    description?: string;
    videoMediaId?: string;
    documentMediaIds?: string[];
    contentUrl?: string;
    estimatedMinutes?: number;
    required?: boolean;
  }
): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/modules/${moduleId}/items`, input);
  return unwrap<CourseDraft>(data);
}

export async function listCourseVersions(courseId: string): Promise<CourseVersion[]> {
  const { data } = await apiClient.get(`/admin/v1/authoring/courses/${courseId}/versions`);
  return unwrap<CourseVersion[]>(data);
}

export async function submitCourseForReview(courseId: string): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/submit-review`);
  return unwrap<CourseDraft>(data);
}

export async function approveCourseReview(courseId: string, note?: string): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/approve`, note ? { note } : {});
  return unwrap<CourseDraft>(data);
}

export async function rejectCourseReview(courseId: string, note?: string): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/reject`, note ? { note } : {});
  return unwrap<CourseDraft>(data);
}

/** Shown when the gateway is offline so the console still renders. */
export const fallbackCourses: Course[] = [
  {
    id: "30000000-0000-0000-0000-000000000001",
    code: "SE401",
    title: "Production Microservices with Spring Boot",
    slug: "production-microservices-spring-boot",
    summary: "Local demo course shown when the gateway is not running.",
    departmentId: "20000000-0000-0000-0000-000000000001",
    ownerId: "2",
    level: "ADVANCED",
    status: "PUBLISHED",
    createdAt: "2026-06-07T00:00:00Z",
    materials: []
  }
];
