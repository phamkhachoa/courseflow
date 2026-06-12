"use client";

import { clientFetch } from "@/shared/api/client";

export type Enrollment = {
  id: string;
  studentId: string;
  courseId: string;
  sectionId?: string;
  status?: string;
  enrolledAt?: string;
  droppedAt?: string;
  completedAt?: string;
  dropReason?: string;
};

export async function listMyEnrollments(courseId?: string): Promise<Enrollment[]> {
  const query = courseId ? `?courseId=${encodeURIComponent(courseId)}` : "";
  return clientFetch<Enrollment[]>(`/v1/enrollments${query}`);
}

export async function enrollInCourse(courseId: string): Promise<Enrollment> {
  return clientFetch<Enrollment>("/v1/enrollments", {
    method: "POST",
    body: { courseId }
  });
}
