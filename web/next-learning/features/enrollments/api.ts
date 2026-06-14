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

export type PromotionEffect = {
  type?: string | null;
  benefitType?: string | null;
  actionType?: string | null;
  targetType?: string | null;
  targetId?: string | null;
  amount?: number | string | null;
  currency?: string | null;
  unit?: string | null;
  quantity?: number | string | null;
  metadata?: Record<string, unknown> | null;
};

export type PromotionPreview = {
  previewId: string;
  courseId: string;
  couponCode?: string | null;
  couponId?: string | null;
  status: string;
  eligible: boolean;
  reasonCodes: string[];
  message?: string | null;
  originalAmount: number | string;
  discountAmount: number | string;
  finalAmount: number | string;
  currency: string;
  priceSource?: string | null;
  effects: PromotionEffect[];
  promotionUnavailable: boolean;
};

export type EnrollmentPromotionApplication = {
  id?: string;
  enrollmentId?: string;
  status: string;
  reservationId?: string | null;
  redemptionId?: string | null;
  couponCode?: string | null;
  couponId?: string | null;
  reasonCodes: string[];
  message?: string | null;
  effects: PromotionEffect[];
  retryCount?: number;
  nextRetryAt?: string | null;
  lastRetryError?: string | null;
  updatedAt?: string;
};

export type EnrollmentCheckoutResponse = {
  enrollment: Enrollment;
  promotion?: EnrollmentPromotionApplication | null;
  attemptId?: string | null;
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

export async function previewEnrollmentPromotion(input: {
  courseId: string;
  couponCode?: string;
  couponId?: string;
}): Promise<PromotionPreview> {
  return clientFetch<PromotionPreview>("/v1/enrollments/promotion-preview", {
    method: "POST",
    body: input
  });
}

export async function checkoutEnrollment(input: {
  courseId: string;
  couponCode?: string;
  couponId?: string;
  promotionPreviewId?: string;
  idempotencyKey?: string;
}): Promise<EnrollmentCheckoutResponse> {
  return clientFetch<EnrollmentCheckoutResponse>("/v1/enrollments/checkout", {
    method: "POST",
    body: input
  });
}

export async function getEnrollmentPromotionApplication(
  enrollmentId: string
): Promise<EnrollmentPromotionApplication | null> {
  try {
    return await clientFetch<EnrollmentPromotionApplication>(
      `/v1/enrollments/${encodeURIComponent(enrollmentId)}/promotion-application`
    );
  } catch (error) {
    if ((error as Error & { status?: number }).status === 404) return null;
    throw error;
  }
}
