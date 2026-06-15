import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type CourseMetrics = {
  courseId: string;
  enrolledCount: number;
  submittedCount: number;
  averageScore?: number;
  discussionCount: number;
  updatedAt?: string;
  [key: string]: unknown;
};

export async function getCourseMetrics(courseId: string): Promise<CourseMetrics> {
  const { data } = await apiClient.get(`/admin/v1/analytics/courses/${courseId}/metrics`);
  return unwrap<CourseMetrics>(data);
}
export type AtRiskStudent = {
  studentId: string;
  courseId: string;
  engagementScore: number;
  riskLevel: string;
  lastActivityAt?: string;
  daysSinceActivity: number;
  riskReasons: string[];
};

export async function getAtRiskStudents(courseId: string): Promise<AtRiskStudent[]> {
  const { data } = await apiClient.get(`/admin/v1/analytics/courses/${courseId}/at-risk`);
  return unwrap<AtRiskStudent[]>(data);
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

export type MarketingFunnelStage = {
  stage: string;
  count: number;
  stepConversionRate?: number | null;
  overallConversionRate?: number | null;
};

export type MarketingFunnelRow = {
  bucketDate: string;
  campaignCode?: string | null;
  source?: string | null;
  stage: string;
  count: number;
};

export type MarketingFunnel = {
  tenantId: string;
  applicationId: string;
  campaignCode?: string | null;
  source?: string | null;
  from?: string | null;
  to?: string | null;
  stages: MarketingFunnelStage[];
  rows: MarketingFunnelRow[];
  generatedAt?: string | null;
};

export type MarketingFunnelFilters = {
  tenantId: string;
  applicationId: string;
  campaignCode?: string;
  source?: string;
  from?: string;
  to?: string;
  limit?: number;
};

export async function getMarketingFunnel(filters: MarketingFunnelFilters): Promise<MarketingFunnel> {
  const { data } = await apiClient.get("/admin/v1/analytics/marketing/funnel", {
    params: Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value !== undefined && value !== "")
    )
  });
  return unwrap<MarketingFunnel>(data);
}
