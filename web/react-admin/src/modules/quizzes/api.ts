import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type QuizQuestionOption = {
  id: string;
  label?: string;
  content?: string;
  weight?: number;
  correct?: boolean;
  feedback?: string;
};
export type QuizQuestion = {
  id: string;
  type?: string;
  stem: string;
  difficulty?: string;
  status?: string;
  points?: number;
  position?: number;
  correctAnswer?: unknown;
  feedback?: string;
  options?: QuizQuestionOption[];
};
export type Quiz = {
  id: string;
  courseId?: string;
  title: string;
  openAt?: string;
  closeAt?: string;
  durationMinutes?: number;
  attemptsAllowed?: number;
  randomizeQuestions?: boolean;
  randomizeOptions?: boolean;
  gracePeriodSeconds?: number;
  scoringMethod?: string;
  timeLimitEnforced?: boolean;
  showCorrectAnswers?: boolean;
  status?: string;
  questions?: QuizQuestion[];
};
export type QuizAttempt = {
  id: string;
  quizId: string;
  studentId?: string;
  attemptNo?: number;
  status?: string;
  score?: number;
  startedAt?: string;
  submittedAt?: string;
  deadlineAt?: string;
  autoSubmitted?: boolean;
};

export type CreateQuizInput = {
  courseId: string;
  title: string;
  openAt?: string | null;
  closeAt?: string | null;
  durationMinutes: number;
  attemptsAllowed: number;
  randomizeQuestions?: boolean;
  randomizeOptions?: boolean;
  gracePeriodSeconds?: number;
  scoringMethod?: string;
  timeLimitEnforced?: boolean;
  showCorrectAnswers?: boolean;
  status?: string;
};

export type UpdateQuizInput = Omit<CreateQuizInput, "courseId">;

export type UpsertQuizQuestionInput = {
  type: string;
  stem: string;
  difficulty?: string;
  points: number;
  position?: number;
  correctAnswer?: unknown;
  feedback?: string;
  status?: string;
  options?: Array<{
    label: string;
    content: string;
    correct?: boolean;
    weight?: number;
    feedback?: string;
  }>;
};

export async function listCourseQuizzes(courseId: string): Promise<Quiz[]> {
  const { data } = await apiClient.get("/admin/v1/quizzes", { params: { courseId } });
  return unwrapList<Quiz>(data);
}

export async function getQuiz(quizId: string): Promise<Quiz> {
  const { data } = await apiClient.get(`/admin/v1/quizzes/${quizId}`);
  return unwrap<Quiz>(data);
}

export async function createQuiz(input: CreateQuizInput): Promise<Quiz> {
  const { data } = await apiClient.post("/admin/v1/quizzes", input);
  return unwrap<Quiz>(data);
}

export async function updateQuiz(quizId: string, input: UpdateQuizInput): Promise<Quiz> {
  const { data } = await apiClient.put(`/admin/v1/quizzes/${quizId}`, input);
  return unwrap<Quiz>(data);
}

export async function createQuizQuestion(
  quizId: string,
  input: UpsertQuizQuestionInput
): Promise<Quiz> {
  const { data } = await apiClient.post(`/admin/v1/quizzes/${quizId}/questions`, input);
  return unwrap<Quiz>(data);
}

export async function updateQuizQuestion(
  quizId: string,
  questionId: string,
  input: UpsertQuizQuestionInput
): Promise<Quiz> {
  const { data } = await apiClient.put(`/admin/v1/quizzes/${quizId}/questions/${questionId}`, input);
  return unwrap<Quiz>(data);
}

export async function removeQuizQuestion(quizId: string, questionId: string): Promise<Quiz> {
  const { data } = await apiClient.delete(`/admin/v1/quizzes/${quizId}/questions/${questionId}`);
  return unwrap<Quiz>(data);
}

export async function startAttempt(quizId: string): Promise<QuizAttempt> {
  // studentId is taken from the gateway identity, never sent in the body.
  const { data } = await apiClient.post(`/admin/v1/quizzes/${quizId}/attempts`, {});
  const body = unwrap<QuizAttempt | { attempt: QuizAttempt }>(data);
  return "attempt" in body ? body.attempt : body;
}
export async function submitAttempt(
  attemptId: string,
  answers: Record<string, string>
): Promise<QuizAttempt> {
  const { data } = await apiClient.post(`/admin/v1/quizzes/attempts/${attemptId}/submit`, { answers });
  return unwrap<QuizAttempt>(data);
}

export type QuizAttemptAnswer = {
  questionId: string;
  answer?: unknown;
  autoScore?: number;
  manualScore?: number;
  totalScore?: number;
  manualFeedback?: string;
  graderId?: string;
};

export type QuizAttemptDetail = {
  attempt: QuizAttempt;
  answers: QuizAttemptAnswer[];
};

export type EffectiveScore = {
  quizId: string;
  studentId: string;
  scoringMethod: string;
  effectiveScore: number;
  attemptsCounted: number;
};

export async function listQuizAttempts(quizId: string): Promise<QuizAttempt[]> {
  const { data } = await apiClient.get(`/admin/v1/quizzes/${quizId}/attempts`);
  return unwrapList<QuizAttempt>(data);
}

export async function getAttempt(attemptId: string): Promise<QuizAttemptDetail> {
  const { data } = await apiClient.get(`/admin/v1/quizzes/attempts/${attemptId}`);
  return unwrap<QuizAttemptDetail>(data);
}

export async function manualGradeAnswer(
  attemptId: string,
  questionId: string,
  // graderId is taken from the authenticated instructor/admin, never sent in the body.
  input: { score: number; feedback?: string }
): Promise<QuizAttempt> {
  const { data } = await apiClient.post(
    `/admin/v1/quizzes/attempts/${attemptId}/answers/${questionId}/grade`,
    input
  );
  return unwrap<QuizAttempt>(data);
}

export async function getEffectiveScore(quizId: string, studentId: string): Promise<EffectiveScore> {
  const { data } = await apiClient.get(`/admin/v1/quizzes/${quizId}/students/${studentId}/score`);
  return unwrap<EffectiveScore>(data);
}
