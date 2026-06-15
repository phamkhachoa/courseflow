import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
  addCourseMaterial,
  archiveCourse,
  createCourse,
  createManualRelatedCourse,
  deleteManualRelatedCourse,
  fallbackCourses,
  getCourse,
  listManualRelatedCourses,
  listCourses,
  publishCourse,
  updateManualRelatedCourse
} from "./api";
import type { AddCourseMaterialInput, UpsertManualRelatedCourseInput } from "./api";
import type { CreateCourseInput } from "./types";

export function useCourses(status?: string) {
  return useQuery({
    queryKey: queryKeys.courses.list(status),
    queryFn: () => listCourses(status),
    placeholderData: fallbackCourses
  });
}

export function useCourse(courseId: string) {
  return useQuery({
    queryKey: queryKeys.courses.detail(courseId),
    queryFn: () => getCourse(courseId),
    enabled: Boolean(courseId)
  });
}

export function useCreateCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateCourseInput) => createCourse(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.courses.all })
  });
}

export function useCourseLifecycle(courseId: string) {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: queryKeys.courses.all });
    qc.invalidateQueries({ queryKey: queryKeys.courses.detail(courseId) });
  };
  return {
    publish: useMutation({ mutationFn: () => publishCourse(courseId), onSuccess: invalidate }),
    archive: useMutation({ mutationFn: () => archiveCourse(courseId), onSuccess: invalidate }),
    addMaterial: useMutation({
      mutationFn: (input: AddCourseMaterialInput) => addCourseMaterial(courseId, input),
      onSuccess: invalidate
    })
  };
}

export function useManualRelatedCourses(courseId: string) {
  return useQuery({
    queryKey: queryKeys.courses.related(courseId),
    queryFn: () => listManualRelatedCourses(courseId),
    enabled: Boolean(courseId),
    retry: 1
  });
}

export function useManualRelatedCourseMutations(courseId: string) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: queryKeys.courses.related(courseId) });

  return {
    create: useMutation({
      mutationFn: (input: UpsertManualRelatedCourseInput) => createManualRelatedCourse(courseId, input),
      onSuccess: invalidate
    }),
    update: useMutation({
      mutationFn: ({ relatedCourseId, input }: { relatedCourseId: string; input: UpsertManualRelatedCourseInput }) =>
        updateManualRelatedCourse(courseId, relatedCourseId, input),
      onSuccess: invalidate
    }),
    remove: useMutation({
      mutationFn: (relatedCourseId: string) => deleteManualRelatedCourse(courseId, relatedCourseId),
      onSuccess: invalidate
    })
  };
}
