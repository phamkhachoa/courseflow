import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";
import type { Course, CourseMaterial, CreateCourseInput } from "./types";

export type AddCourseMaterialInput = {
  title: string;
  materialType: string;
  mediaId?: string;
  position?: number;
};

export type RelatedCourseSource = "MANUAL" | "CURATED" | "ANALYTICS" | "SEARCH" | "ENROLLMENT" | "POPULARITY";
export type RelatedCourseStatus = "ACTIVE" | "DISABLED";

export type RelatedCourseSummary = Pick<Course, "id" | "code" | "title" | "slug" | "summary" | "level" | "status">;

export type ManualRelatedCourse = {
  id?: string;
  courseId: string;
  relatedCourseId: string;
  source?: RelatedCourseSource | string;
  placement?: string;
  reason?: string;
  score?: number;
  weight?: number;
  position?: number;
  status?: RelatedCourseStatus | string;
  relatedCourse?: RelatedCourseSummary | null;
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
};

export type UpsertManualRelatedCourseInput = {
  relatedCourseId: string;
  placement?: string;
  reason?: string;
  weight?: number;
  position?: number;
  effectiveFrom?: string;
  effectiveTo?: string;
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

export async function updateCoursePricing(
  courseId: string,
  input: { listPrice?: number; currency?: string }
): Promise<Pick<Course, "id" | "listPrice" | "currency" | "priceStatus"> & { purchasable: boolean; priceSource: string }> {
  const { data } = await apiClient.post(`/admin/v1/courses/${courseId}/pricing`, input);
  return unwrap(data);
}

export async function addCourseMaterial(
  courseId: string,
  input: AddCourseMaterialInput
): Promise<CourseMaterial> {
  const { data } = await apiClient.post(`/admin/v1/courses/${courseId}/materials`, input);
  return unwrap<CourseMaterial>(data);
}

export async function listManualRelatedCourses(courseId: string): Promise<ManualRelatedCourse[]> {
  const { data } = await apiClient.get(`/admin/v1/analytics/courses/${courseId}/manual-related`);
  return unwrapList<ManualRelatedCourse>(data);
}

export async function createManualRelatedCourse(
  courseId: string,
  input: UpsertManualRelatedCourseInput
): Promise<ManualRelatedCourse> {
  const { data } = await apiClient.post(`/admin/v1/analytics/courses/${courseId}/manual-related`, input);
  return unwrap<ManualRelatedCourse>(data);
}

export async function updateManualRelatedCourse(
  courseId: string,
  relatedCourseId: string,
  input: UpsertManualRelatedCourseInput
): Promise<ManualRelatedCourse> {
  const { data } = await apiClient.put(`/admin/v1/analytics/courses/${courseId}/manual-related/${relatedCourseId}`, input);
  return unwrap<ManualRelatedCourse>(data);
}

export async function deleteManualRelatedCourse(courseId: string, relatedCourseId: string): Promise<void> {
  await apiClient.delete(`/admin/v1/analytics/courses/${courseId}/manual-related/${relatedCourseId}`);
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

export type CourseDraftPreviewItem = {
  moduleId: string;
  moduleTitle: string;
  itemId: string;
  itemType: string;
  title: string;
  estimatedMinutes?: number;
  required: boolean;
};

export type CourseDraftPreview = {
  courseId: string;
  title: string;
  slug: string;
  summary?: string;
  status: string;
  reviewState?: string;
  currentVersionNo: number;
  generatedAt?: string;
  readinessStatus: string;
  moduleCount: number;
  itemCount: number;
  requiredItemCount: number;
  totalEstimatedMinutes: number;
  firstRequiredItem?: CourseDraftPreviewItem | null;
  nextAction?: CourseDraftPreviewItem | null;
  modules: CourseModule[];
  issues: string[];
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

export type CourseReviewAudit = {
  id: string;
  courseId: string;
  versionNo: number;
  actorId: string;
  actorRole?: string;
  action: string;
  fromState?: string;
  toState?: string;
  note?: string;
  checklist?: string[];
  createdAt?: string;
};

export type CourseReviewChecklistItem = {
  id: string;
  label: string;
  required: boolean;
};

export type CourseReviewQueueItem = {
  courseId: string;
  title: string;
  slug: string;
  summary?: string;
  status: string;
  reviewState: string;
  currentVersionNo: number;
  ownerId: string;
  departmentId: string;
  lastAuthoredBy?: string;
  moduleCount: number;
  itemCount: number;
  submittedBy?: string;
  submittedAt?: string;
};

export type CourseVersionDiffChange = {
  scope: string;
  changeType: string;
  moduleId?: string;
  itemId?: string;
  title?: string;
  field?: string;
  fromValue?: string;
  toValue?: string;
};

export type CourseVersionDiff = {
  courseId: string;
  draftVersionNo: number;
  publishedVersionNo?: number;
  baseLabel: string;
  targetLabel: string;
  addedModules: number;
  removedModules: number;
  changedModules: number;
  movedModules: number;
  addedItems: number;
  removedItems: number;
  changedItems: number;
  movedItems: number;
  requiredItemsAdded: number;
  requiredItemsRemoved: number;
  changes: CourseVersionDiffChange[];
  warnings: string[];
};

export type ReviewDecisionInput = {
  note?: string;
  checklist?: string[];
};

export type RollbackVersionInput = {
  note?: string;
  expectedCurrentVersionNo?: number;
};

export type ModuleInput = {
  title: string;
  description?: string;
  status?: string;
};

export type ModuleItemInput = {
  itemType: string;
  refId?: string;
  title: string;
  description?: string;
  videoMediaId?: string;
  documentMediaIds?: string[];
  contentUrl?: string;
  estimatedMinutes?: number;
  required?: boolean;
};

export async function createCourseDraft(input: {
  code: string;
  title: string;
  slug: string;
  summary: string;
  departmentId: string;
  level: string;
  listPrice?: number;
  currency?: string;
}): Promise<CourseDraft> {
  const { data } = await apiClient.post("/admin/v1/authoring/courses", input);
  return unwrap<CourseDraft>(data);
}

export async function getCourseDraft(courseId: string): Promise<CourseDraft> {
  const { data } = await apiClient.get(`/admin/v1/authoring/courses/${courseId}/draft`);
  return unwrap<CourseDraft>(data);
}

export async function getCourseDraftPreview(courseId: string): Promise<CourseDraftPreview> {
  const { data } = await apiClient.get(`/admin/v1/authoring/courses/${courseId}/preview`);
  return unwrap<CourseDraftPreview>(data);
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
  input: ModuleInput
): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/modules`, input);
  return unwrap<CourseDraft>(data);
}

export async function updateModule(
  courseId: string,
  moduleId: string,
  input: ModuleInput
): Promise<CourseDraft> {
  const { data } = await apiClient.patch(`/admin/v1/authoring/courses/${courseId}/modules/${moduleId}`, input);
  return unwrap<CourseDraft>(data);
}

export async function duplicateModule(courseId: string, moduleId: string): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/modules/${moduleId}/duplicate`, {});
  return unwrap<CourseDraft>(data);
}

export async function archiveModule(courseId: string, moduleId: string): Promise<CourseDraft> {
  const { data } = await apiClient.delete(`/admin/v1/authoring/courses/${courseId}/modules/${moduleId}`);
  return unwrap<CourseDraft>(data);
}

export async function createModuleItem(
  courseId: string,
  moduleId: string,
  input: ModuleItemInput
): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/modules/${moduleId}/items`, input);
  return unwrap<CourseDraft>(data);
}

export async function updateModuleItem(
  courseId: string,
  moduleId: string,
  itemId: string,
  input: ModuleItemInput
): Promise<CourseDraft> {
  const { data } = await apiClient.patch(
    `/admin/v1/authoring/courses/${courseId}/modules/${moduleId}/items/${itemId}`,
    input
  );
  return unwrap<CourseDraft>(data);
}

export async function duplicateModuleItem(
  courseId: string,
  moduleId: string,
  itemId: string
): Promise<CourseDraft> {
  const { data } = await apiClient.post(
    `/admin/v1/authoring/courses/${courseId}/modules/${moduleId}/items/${itemId}/duplicate`,
    {}
  );
  return unwrap<CourseDraft>(data);
}

export async function archiveModuleItem(
  courseId: string,
  moduleId: string,
  itemId: string
): Promise<CourseDraft> {
  const { data } = await apiClient.delete(`/admin/v1/authoring/courses/${courseId}/modules/${moduleId}/items/${itemId}`);
  return unwrap<CourseDraft>(data);
}

export async function listCourseVersions(courseId: string): Promise<CourseVersion[]> {
  const { data } = await apiClient.get(`/admin/v1/authoring/courses/${courseId}/versions`);
  return unwrap<CourseVersion[]>(data);
}

export async function getCourseVersionDiff(
  courseId: string,
  publishedVersionNo?: number
): Promise<CourseVersionDiff> {
  const { data } = await apiClient.get(`/admin/v1/authoring/courses/${courseId}/versions/diff`, {
    params: publishedVersionNo ? { publishedVersionNo } : undefined
  });
  return unwrap<CourseVersionDiff>(data);
}

export async function rollbackCourseVersion(
  courseId: string,
  versionNo: number,
  input: RollbackVersionInput
): Promise<CourseDraft> {
  const { data } = await apiClient.post(
    `/admin/v1/authoring/courses/${courseId}/versions/${versionNo}/rollback-to-draft`,
    input
  );
  return unwrap<CourseDraft>(data);
}

export async function listCourseReviewHistory(courseId: string): Promise<CourseReviewAudit[]> {
  const { data } = await apiClient.get(`/admin/v1/authoring/courses/${courseId}/review-history`);
  return unwrap<CourseReviewAudit[]>(data);
}

export async function getCourseReviewChecklist(): Promise<CourseReviewChecklistItem[]> {
  const { data } = await apiClient.get("/admin/v1/authoring/courses/review-checklist");
  return unwrap<CourseReviewChecklistItem[]>(data);
}

export async function listCourseReviewQueue(): Promise<CourseReviewQueueItem[]> {
  const { data } = await apiClient.get("/admin/v1/authoring/courses/review-queue");
  return unwrap<CourseReviewQueueItem[]>(data);
}

export async function submitCourseForReview(courseId: string): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/submit-review`);
  return unwrap<CourseDraft>(data);
}

export async function approveCourseReview(courseId: string, input: ReviewDecisionInput = {}): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/approve`, input);
  return unwrap<CourseDraft>(data);
}

export async function rejectCourseReview(courseId: string, input: ReviewDecisionInput = {}): Promise<CourseDraft> {
  const { data } = await apiClient.post(`/admin/v1/authoring/courses/${courseId}/reject`, input);
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
    listPrice: 100,
    currency: "USD",
    priceStatus: "ACTIVE",
    createdAt: "2026-06-07T00:00:00Z",
    materials: []
  }
];
