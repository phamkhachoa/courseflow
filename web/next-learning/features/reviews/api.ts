import { serverFetch } from "@/shared/api/server";

export type CourseReview = {
  id: string;
  courseId: string;
  userId: string;
  rating: number;
  title?: string;
  body?: string;
  status: string;
  helpfulCount: number;
  createdAt: string;
};

export type RatingSummary = {
  courseId: string;
  reviewCount: number;
  averageRating: number;
  count1: number;
  count2: number;
  count3: number;
  count4: number;
  count5: number;
};

export async function getCourseReviews(courseId: string): Promise<CourseReview[]> {
  return serverFetch<CourseReview[]>(`/v1/reviews/courses/${courseId}`, { revalidate: 60 });
}

export async function getRatingSummary(courseId: string): Promise<RatingSummary> {
  return serverFetch<RatingSummary>(`/v1/reviews/courses/${courseId}/summary`, { revalidate: 60 });
}
