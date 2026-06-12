import { serverFetch } from "@/shared/api/server";

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

export type CourseProgress = {
  courseId: string;
  studentId: string;
  totalModules: number;
  completedModules: number;
  totalItems?: number;
  completedItems?: number;
  totalRequiredItems?: number;
  completedRequiredItems?: number;
  percentComplete: number;
  completed: boolean;
  breakdown?: ProgressBreakdown[];
  modules?: ModuleProgressSummary[];
  items?: ItemProgress[];
  missingRequirements?: MissingRequirement[];
};

export type ProgressBreakdown = {
  itemType: string;
  total: number;
  completed: number;
  required: number;
  completedRequired: number;
};

export type ModuleProgressSummary = {
  moduleId: string;
  totalItems: number;
  completedItems: number;
  totalRequiredItems: number;
  completedRequiredItems: number;
  percentComplete: number;
  completed: boolean;
};

export type ItemProgress = {
  itemId: string;
  moduleId: string;
  itemType: string;
  title: string;
  required: boolean;
  status: string;
  progressType?: string;
  completedAt?: string;
};

export type MissingRequirement = {
  itemId: string;
  moduleId: string;
  itemType: string;
  title: string;
};

export async function getCourseModules(courseId: string): Promise<CourseModule[]> {
  return serverFetch<CourseModule[]>(`/v1/courses/${courseId}/modules`, { revalidate: 30 });
}
