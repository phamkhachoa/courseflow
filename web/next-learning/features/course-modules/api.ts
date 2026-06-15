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
  publishedVersionNo?: number | null;
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

export type CoursePlayerNextAction = {
  kind: string;
  moduleId?: string | null;
  itemId?: string | null;
  itemType?: string | null;
  title: string;
  locked: boolean;
  ctaLabel: string;
  reason: string;
};

export type CoursePlayerPrerequisite = {
  moduleId: string;
  title: string;
  completed: boolean;
};

export type CoursePlayerModuleState = {
  moduleId: string;
  locked: boolean;
  lockedReasonCode?: string | null;
  lockedReasonText?: string | null;
  unmetPrerequisites?: CoursePlayerPrerequisite[];
};

export type CoursePlayerItemState = {
  itemId: string;
  moduleId: string;
  itemType: string;
  required: boolean;
  progressStatus: string;
  progressType?: string | null;
  completedAt?: string | null;
  completionMode: "SELF" | "VERIFIED" | string;
  locked: boolean;
  lockedReasonCode?: string | null;
  lockedReasonText?: string | null;
  sourceStatus?: string | null;
  sourceDueAt?: string | null;
  sourceLockAt?: string | null;
};

export type CertificateMissingRequirement = {
  code: string;
  label: string;
  detail?: string | null;
};

export type CertificateEligibility = {
  generatedAt?: string | null;
  courseId: string;
  studentId: string;
  eligible: boolean;
  status: string;
  completionEligible: boolean;
  gradeEligible: boolean;
  requiredItemsEligible: boolean;
  issued: boolean;
  finalGrade?: number | string | null;
  gradeThreshold?: number | string | null;
  finalGradeStatus?: string | null;
  certificateId?: string | null;
  verificationCode?: string | null;
  issuedAt?: string | null;
  missingRequirements?: CertificateMissingRequirement[];
};

export type LearnerCoursePlayer = {
  generatedAt: string;
  courseId: string;
  publishedVersionNo?: number | null;
  modules: CourseModule[];
  progress: CourseProgress;
  certificateEligibility?: CertificateEligibility | null;
  nextAction?: CoursePlayerNextAction | null;
  moduleStates?: CoursePlayerModuleState[];
  itemStates?: CoursePlayerItemState[];
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
