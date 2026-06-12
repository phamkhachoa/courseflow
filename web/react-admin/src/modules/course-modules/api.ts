import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type ModuleItem = {
  id: string;
  title: string;
  itemType?: string;
  itemId?: string;
  description?: string;
  videoMediaId?: string;
  documentMediaIds?: string[];
  contentUrl?: string;
  estimatedMinutes?: number;
  required?: boolean;
  position: number;
};

export type CourseModule = {
  id: string;
  title: string;
  description?: string;
  position: number;
  status?: string;
  items?: ModuleItem[];
};

export type ModuleProgress = {
  id: string;
  courseId: string;
  moduleId: string;
  studentId: string;
  status: string;
  completedAt?: string;
};

export async function listModules(courseId: string): Promise<CourseModule[]> {
  const { data } = await apiClient.get(`/admin/v1/courses/${courseId}/modules`);
  return unwrap<CourseModule[]>(data);
}

// Identity comes from the gateway; the endpoint always marks the module COMPLETED.
export async function markProgress(courseId: string, moduleId: string): Promise<ModuleProgress> {
  const { data } = await apiClient.post(
    `/admin/v1/courses/${courseId}/modules/${moduleId}/progress`
  );
  return unwrap<ModuleProgress>(data);
}
