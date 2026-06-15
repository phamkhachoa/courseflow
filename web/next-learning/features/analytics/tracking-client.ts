"use client";

import { clientFetch } from "@/shared/api/client";
import type { RelatedCourseEventType } from "./related-courses";

type RelatedCourseTrackingInput = {
  eventType: RelatedCourseEventType;
  sourceCourseId: string;
  relatedCourseId: string;
  recommendationId?: string;
  source?: string;
  reason?: string;
  reasonCode?: string;
  placement?: string;
  modelVersion?: string;
  score?: number;
};

function eventId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function sessionId(): string {
  const key = "courseflow.relatedCourses.sessionId";
  if (typeof window === "undefined") return eventId();
  const next = eventId();
  try {
    const existing = window.localStorage.getItem(key);
    if (existing) return existing;
    window.localStorage.setItem(key, next);
  } catch {
    return next;
  }
  return next;
}

export async function trackRelatedCourseEvent(input: RelatedCourseTrackingInput): Promise<void> {
  const placement = input.placement ?? "COURSE_DETAIL_RELATED";
  const metadata = JSON.stringify({
    recommendationId: input.recommendationId,
    score: input.score === undefined ? undefined : String(input.score)
  });
  try {
    await clientFetch<void>("/v1/analytics/recommendations/events", {
      method: "POST",
      body: {
        eventId: eventId(),
        eventType: input.eventType,
        placement,
        courseId: input.sourceCourseId,
        relatedCourseId: input.relatedCourseId,
        sessionId: sessionId(),
        recommendationSource: input.source,
        reasonCode: input.reasonCode,
        modelVersion: input.modelVersion,
        attributionId: input.recommendationId,
        metadataJson: metadata
      }
    });
  } catch {
    // Tracking must not block course discovery when the analytics endpoint is absent.
  }
}
