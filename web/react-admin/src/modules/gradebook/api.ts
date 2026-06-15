import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type GradeItem = {
  id: string;
  courseId: string;
  categoryName?: string;
  sourceType?: string;
  sourceId?: string;
  title: string;
  maxScore?: number;
  itemWeightPercent?: number;
  categoryWeightPercent?: number;
  aggregationMethod?: string;
  dropLowest?: number;
  latePenaltyPercent?: number;
};

export type GradeEntry = {
  id: string;
  gradeItemId: string;
  title?: string;
  categoryName?: string;
  rawScore?: number;
  adjustedScore?: number;
  maxScore?: number;
  latePenaltyApplied?: number;
  isLate?: boolean;
  minutesLate?: number;
  letter?: string;
  status?: string;
  gradedAt?: string;
};

export type CategorySummary = {
  name: string;
  aggregationMethod?: string;
  dropLowest?: number;
  weightPercent?: number;
  contribution?: number;
  itemCount?: number;
  droppedCount?: number;
};

export type StudentGradebook = {
  courseId: string;
  studentId: string;
  finalScore?: number;
  finalLetter?: string;
  gradingSchemeName?: string;
  categories: CategorySummary[];
  entries: GradeEntry[];
};

export type GradePublishAudit = {
  id: string;
  action: string;
  courseId: string;
  studentId?: string;
  gradeItemId?: string;
  gradeEntryId?: string;
  finalGradeId?: string;
  actorId?: string;
  reasonCodes: string[];
  payload: Record<string, unknown>;
  createdAt?: string;
};

export type GradingQueueItem = {
  queueKey: string;
  courseId: string;
  studentId: string;
  status: string;
  reasonCodes: string[];
  gradeItemId?: string | null;
  gradeEntryId?: string | null;
  finalGradeId?: string | null;
  title?: string | null;
  categoryName?: string | null;
  sourceType?: string | null;
  sourceId?: string | null;
  rawScore?: number | null;
  adjustedScore?: number | null;
  maxScore?: number | null;
  finalGradeStatus?: string | null;
  gradedAt?: string | null;
  finalizedAt?: string | null;
};

export async function listGradeItems(courseId: string): Promise<GradeItem[]> {
  const { data } = await apiClient.get(`/admin/v1/gradebook/courses/${courseId}/items`);
  return unwrap<GradeItem[]>(data);
}
export async function getStudentGradebook(courseId: string, studentId: string): Promise<StudentGradebook> {
  const { data } = await apiClient.get(
    `/admin/v1/gradebook/courses/${courseId}/students/${studentId}`
  );
  return unwrap<StudentGradebook>(data);
}
export async function upsertEntry(input: {
  gradeItemId: string;
  studentId: string;
  rawScore: number;
  isLate?: boolean;
  minutesLate?: number;
  reason?: string;
}): Promise<StudentGradebook> {
  // The grader is taken from the authenticated caller, never sent in the body.
  const { data } = await apiClient.post("/admin/v1/gradebook/entries", input);
  return unwrap<StudentGradebook>(data);
}

export async function listGradePublishAudit(
  courseId: string,
  filters?: { studentId?: string; gradeItemId?: string; limit?: number }
): Promise<GradePublishAudit[]> {
  const { data } = await apiClient.get(`/admin/v1/gradebook/courses/${courseId}/grade-publish-audit`, {
    params: filters
  });
  return unwrap<GradePublishAudit[]>(data);
}

export async function listGradingQueue(
  courseId: string,
  filters?: { studentId?: string; status?: string; limit?: number }
): Promise<GradingQueueItem[]> {
  const { data } = await apiClient.get(`/admin/v1/gradebook/courses/${courseId}/grading-queue`, {
    params: filters
  });
  return unwrap<GradingQueueItem[]>(data);
}

// ---- Grade categories (weights) ----

export type GradeCategory = {
  id: string;
  courseId: string;
  name: string;
  weightPercent?: number;
  position?: number;
  aggregationMethod?: string;
  dropLowest?: number;
};

export async function listCategories(courseId: string): Promise<GradeCategory[]> {
  const { data } = await apiClient.get(`/admin/v1/gradebook/courses/${courseId}/categories`);
  return unwrap<GradeCategory[]>(data);
}

export async function createCategory(
  courseId: string,
  input: { name: string; weightPercent: number; aggregationMethod?: string; dropLowest?: number }
): Promise<GradeCategory> {
  const { data } = await apiClient.post(
    `/admin/v1/gradebook/courses/${courseId}/categories`,
    input
  );
  return unwrap<GradeCategory>(data);
}

export async function updateCategory(
  courseId: string,
  categoryId: string,
  input: { name: string; weightPercent: number; aggregationMethod?: string; dropLowest?: number }
): Promise<GradeCategory> {
  const { data } = await apiClient.put(
    `/admin/v1/gradebook/courses/${courseId}/categories/${categoryId}`,
    input
  );
  return unwrap<GradeCategory>(data);
}

// ---- Grading schemes ----

export type GradingSchemeEntry = {
  id?: string;
  letter: string;
  minPercent: number;
  gpaPoints?: number;
};

export type GradingScheme = {
  id: string;
  courseId: string;
  name: string;
  isDefault: boolean;
  entries: GradingSchemeEntry[];
};

export async function listGradingSchemes(courseId: string): Promise<GradingScheme[]> {
  const { data } = await apiClient.get(`/admin/v1/gradebook/courses/${courseId}/grading-schemes`);
  return unwrap<GradingScheme[]>(data);
}

export async function createGradingScheme(
  courseId: string,
  input: { name: string; isDefault: boolean; entries: GradingSchemeEntry[] }
): Promise<GradingScheme> {
  const { data } = await apiClient.post(
    `/admin/v1/gradebook/courses/${courseId}/grading-schemes`,
    input
  );
  return unwrap<GradingScheme>(data);
}

// ---- Final grades ----

export type FinalGrade = {
  id: string;
  courseId: string;
  studentId: string;
  finalScore?: number;
  letter?: string;
  passed?: boolean;
  status?: string;
  finalizedBy?: string;
  finalizedAt?: string;
};

export async function finalizeGrade(courseId: string, studentId: string): Promise<FinalGrade> {
  // No body: the actor is the authenticated caller.
  const { data } = await apiClient.post(
    `/admin/v1/gradebook/courses/${courseId}/students/${studentId}/finalize`,
    {}
  );
  return unwrap<FinalGrade>(data);
}

export async function getFinalGrade(courseId: string, studentId: string): Promise<FinalGrade> {
  const { data } = await apiClient.get(
    `/admin/v1/gradebook/courses/${courseId}/students/${studentId}/final-grade`
  );
  return unwrap<FinalGrade>(data);
}

export async function exportGradebook(courseId: string): Promise<void> {
  const response = await apiClient.get(
    `/admin/v1/gradebook/courses/${courseId}/export.csv`,
    { responseType: "blob" }
  );
  const url = URL.createObjectURL(response.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gradebook-${courseId}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
