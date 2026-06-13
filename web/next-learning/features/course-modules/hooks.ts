"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clientFetch } from "@/shared/api/client";
import type { CourseModule, CourseProgress, LearnerCoursePlayer } from "./api";

export function useCourseModules(courseId: string, enabled = true) {
  return useQuery({
    queryKey: ["course-modules", courseId],
    queryFn: () => clientFetch<CourseModule[]>(`/v1/courses/${courseId}/modules`),
    enabled: Boolean(courseId && enabled)
  });
}

export function useCourseProgress(courseId: string, enabled = true) {
  return useQuery({
    queryKey: ["course-progress", courseId],
    queryFn: () => clientFetch<CourseProgress>(`/v1/courses/${courseId}/modules/progress`),
    enabled: Boolean(courseId && enabled)
  });
}

export function useCoursePlayer(courseId: string, enabled = true) {
  return useQuery({
    queryKey: ["course-player", courseId],
    queryFn: () => clientFetch<LearnerCoursePlayer>(`/v1/courses/${courseId}/modules/player`),
    enabled: Boolean(courseId && enabled)
  });
}

export function useMarkProgress(courseId: string) {
  const qc = useQueryClient();
  return useMutation({
    // Identity comes from the gateway; the endpoint always marks the module COMPLETED.
    mutationFn: ({ moduleId }: { moduleId: string }) =>
      clientFetch(`/v1/courses/${courseId}/modules/${moduleId}/progress`, {
        method: "POST"
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["course-modules", courseId] });
      qc.invalidateQueries({ queryKey: ["course-progress", courseId] });
      qc.invalidateQueries({ queryKey: ["course-player", courseId] });
    }
  });
}

export function useMarkItemProgress(courseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      moduleId,
      itemId,
      progressType
    }: {
      moduleId: string;
      itemId: string;
      progressType?: string;
    }) =>
      clientFetch(`/v1/courses/${courseId}/modules/${moduleId}/items/${itemId}/progress`, {
        method: "POST",
        body: { progressType }
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["course-modules", courseId] });
      qc.invalidateQueries({ queryKey: ["course-progress", courseId] });
      qc.invalidateQueries({ queryKey: ["course-player", courseId] });
    }
  });
}
