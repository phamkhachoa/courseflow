import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type CourseMetrics = {
  courseId: string;
  completionRate?: number;
  activeLearners?: number;
  avgScore?: number;
  atRiskCount?: number;
  [key: string]: unknown;
};

export async function getCourseMetrics(courseId: string): Promise<CourseMetrics> {
  const { data } = await apiClient.get(`/admin/v1/analytics/courses/${courseId}/metrics`);
  return unwrap<CourseMetrics>(data);
}
export async function recomputeMetrics(courseId: string): Promise<unknown> {
  const { data } = await apiClient.post("/admin/v1/analytics/courses/metrics", { courseId });
  return unwrap<unknown>(data);
}

export type CourseCompletion = {
  courseId: string;
  enrolledCount: number;
  completedCount: number;
  completionRate: number;
  avgDaysToComplete?: number;
};

export type OrgDashboard = {
  orgId: string;
  activeLearners: number;
  totalEnrollments: number;
  avgCompletionRate: number;
};

export async function getCourseCompletion(courseId: string): Promise<CourseCompletion> {
  const { data } = await apiClient.get(`/admin/v1/analytics/courses/${courseId}/completion`);
  return unwrap<CourseCompletion>(data);
}

export async function getOrgDashboard(orgId: string): Promise<OrgDashboard> {
  const { data } = await apiClient.get(`/admin/v1/analytics/orgs/${orgId}/dashboard`);
  return unwrap<OrgDashboard>(data);
}
