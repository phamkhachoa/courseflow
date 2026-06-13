"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { clientFetch } from "@/shared/api/client";

// Student-facing (sanitized) views from quiz-service: never carry correctAnswer,
// option `correct` flags or feedback. The full QuizDto is only returned to staff
// or to a student with a GRADED attempt when showCorrectAnswers is true.
export type StudentQuestionOption = {
  id: string;
  label: string;
  content: string;
};

export type StudentQuizQuestion = {
  id: string;
  type: string;
  stem: string;
  points?: number;
  position: number;
  options?: StudentQuestionOption[];
};

export type StudentQuiz = {
  id: string;
  courseId: string;
  title: string;
  openAt?: string;
  closeAt?: string;
  durationMinutes: number;
  attemptsAllowed: number;
  randomizeQuestions: boolean;
  scoringMethod: string;
  timeLimitEnforced: boolean;
  showCorrectAnswers: boolean;
  status: string;
  questions?: StudentQuizQuestion[];
};

export type QuizAttempt = {
  id: string;
  quizId: string;
  studentId: string;
  attemptNo: number;
  status: string;
  score?: number;
  startedAt?: string;
  submittedAt?: string;
  deadlineAt?: string;
  autoSubmitted?: boolean;
};

export type EffectiveScore = {
  quizId: string;
  studentId: string;
  scoringMethod: string;
  effectiveScore?: number;
  attemptsCounted: number;
};

export type QuizAttemptAnswer = {
  questionId: string;
  answer?: unknown;
  autoScore?: number;
  manualScore?: number;
  totalScore?: number;
  manualFeedback?: string;
  graderId?: string;
  gradedAt?: string;
};

export type QuizAttemptDetail = {
  attempt: QuizAttempt;
  answers: QuizAttemptAnswer[];
};

export type StartAttemptResponse = {
  attempt: QuizAttempt;
  questions: StudentQuizQuestion[];
};

// Answers map question id -> answer JSON. For choice questions the backend
// grades by option label (A/B/C), so the value is label or label[].
export type QuizAnswers = Record<string, unknown>;

export function useCourseQuizzes(courseId: string, enabled = true) {
  return useQuery({
    queryKey: ["course-quizzes", courseId],
    queryFn: () => clientFetch<StudentQuiz[]>(`/v1/quizzes?courseId=${courseId}`),
    enabled: Boolean(courseId && enabled)
  });
}

export function useQuiz(quizId: string, enabled = true) {
  return useQuery({
    queryKey: ["quiz", quizId],
    queryFn: () => clientFetch<StudentQuiz>(`/v1/quizzes/${quizId}`),
    enabled: Boolean(quizId && enabled)
  });
}

export function useStartAttempt(quizId: string) {
  return useMutation({
    // studentId is taken from the gateway identity, never sent in the body.
    mutationFn: () =>
      clientFetch<StartAttemptResponse>(`/v1/quizzes/${quizId}/attempts`, {
        method: "POST"
      })
  });
}

export function useMyQuizAttempts(quizId: string, enabled = true) {
  return useQuery({
    queryKey: ["quiz-attempts", quizId, "me"],
    queryFn: () => clientFetch<QuizAttempt[]>(`/v1/quizzes/${quizId}/attempts/me`),
    enabled: Boolean(quizId && enabled)
  });
}

export function useAttemptDetail(attemptId: string, enabled = true) {
  return useQuery({
    queryKey: ["quiz-attempt", attemptId],
    queryFn: () => clientFetch<QuizAttemptDetail>(`/v1/quizzes/attempts/${attemptId}`),
    enabled: Boolean(attemptId && enabled)
  });
}

export function useSubmitAttempt() {
  return useMutation({
    mutationFn: ({ attemptId, answers }: { attemptId: string; answers: QuizAnswers }) =>
      clientFetch<QuizAttempt>(`/v1/quizzes/attempts/${attemptId}/submit`, {
        method: "POST",
        body: { answers }
      })
  });
}

export function useSaveAnswers() {
  return useMutation({
    mutationFn: ({ attemptId, answers }: { attemptId: string; answers: QuizAnswers }) =>
      clientFetch<QuizAttempt>(`/v1/quizzes/attempts/${attemptId}/answers`, {
        method: "PUT",
        body: { answers }
      })
  });
}

export function useEffectiveScore(quizId: string, studentId: string) {
  return useQuery({
    queryKey: ["quiz-score", quizId, studentId],
    queryFn: () =>
      clientFetch<EffectiveScore>(`/v1/quizzes/${quizId}/students/${studentId}/score`),
    enabled: Boolean(quizId && studentId)
  });
}
