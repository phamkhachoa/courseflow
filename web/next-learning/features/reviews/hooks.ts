"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clientFetch } from "@/shared/api/client";
import type { CourseReview, RatingSummary } from "./api";

export type { CourseReview, RatingSummary };

export function useCourseReviews(courseId: string, initialData?: CourseReview[]) {
  return useQuery({
    queryKey: ["course-reviews", courseId],
    queryFn: () => clientFetch<CourseReview[]>(`/v1/reviews/courses/${courseId}`),
    enabled: Boolean(courseId),
    initialData
  });
}

export function useRatingSummary(courseId: string, initialData?: RatingSummary | null) {
  return useQuery({
    queryKey: ["rating-summary", courseId],
    queryFn: () => clientFetch<RatingSummary>(`/v1/reviews/courses/${courseId}/summary`),
    enabled: Boolean(courseId),
    initialData: initialData ?? undefined
  });
}

export function usePostReview(courseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { rating: number; title?: string; body?: string }) =>
      clientFetch<CourseReview>(`/v1/reviews`, { method: "POST", body: { courseId, ...input } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["course-reviews", courseId] });
      qc.invalidateQueries({ queryKey: ["rating-summary", courseId] });
    }
  });
}

export function useMarkHelpful(courseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId }: { reviewId: string }) =>
      clientFetch<CourseReview>(`/v1/reviews/${reviewId}/helpful`, { method: "POST", body: {} }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["course-reviews", courseId] });
    }
  });
}
