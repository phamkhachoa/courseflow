"use client";

import Link from "next/link";
import { ArrowRight, BookOpenCheck, Sparkles } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { Badge, Card, cn } from "@/shared/ui";
import {
  relatedCourseHref,
  relatedCourseSourceLabel,
  type RelatedCourseRecommendation
} from "./related-courses";
import { trackRelatedCourseEvent } from "./tracking-client";

const accents = [
  "from-brand-600 to-signal-500",
  "from-accent-500 to-coral-500",
  "from-signal-600 to-brand-500"
];

function levelLabel(level?: string) {
  const labels: Record<string, string> = {
    BEGINNER: "Nhập môn",
    INTERMEDIATE: "Trung cấp",
    ADVANCED: "Nâng cao",
    EXPERT: "Chuyên sâu"
  };
  return labels[level ?? ""] ?? level ?? "Khóa học";
}

function scoreLabel(score?: number) {
  if (typeof score !== "number") return null;
  if (score >= 0 && score <= 1) return `${Math.round(score * 100)}% match`;
  return `${score.toFixed(1)} score`;
}

export function RelatedCoursesClient({
  recommendations
}: {
  recommendations: RelatedCourseRecommendation[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const trackedRef = useRef(new Set<string>());
  const byCourseId = useMemo(
    () => new Map(recommendations.map((item) => [item.relatedCourseId, item])),
    [recommendations]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container || recommendations.length === 0) return;
    const nodes = Array.from(container.querySelectorAll<HTMLElement>("[data-related-course-id]"));

    const trackImpression = (relatedCourseId: string) => {
      if (trackedRef.current.has(relatedCourseId)) return;
      const item = byCourseId.get(relatedCourseId);
      if (!item) return;
      trackedRef.current.add(relatedCourseId);
      void trackRelatedCourseEvent({
        eventType: "IMPRESSION",
        sourceCourseId: item.sourceCourseId,
        relatedCourseId: item.relatedCourseId,
        recommendationId: item.recommendationId,
        source: item.source,
        reason: item.reason,
        reasonCode: item.reasonCode,
        placement: item.placement,
        modelVersion: item.modelVersion,
        score: item.score
      });
    };

    if (!("IntersectionObserver" in window)) {
      nodes.forEach((node) => trackImpression(node.dataset.relatedCourseId ?? ""));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const relatedCourseId = (entry.target as HTMLElement).dataset.relatedCourseId;
          if (relatedCourseId) trackImpression(relatedCourseId);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.35 }
    );

    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [byCourseId, recommendations.length]);

  return (
    <div ref={containerRef} className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {recommendations.map((item, index) => {
        const href = relatedCourseHref(item.course);
        const match = scoreLabel(item.score);

        return (
          <Link
            key={item.relatedCourseId}
            href={href}
            data-related-course-id={item.relatedCourseId}
            onClick={() =>
              void trackRelatedCourseEvent({
                eventType: "CLICK",
                sourceCourseId: item.sourceCourseId,
                relatedCourseId: item.relatedCourseId,
                recommendationId: item.recommendationId,
                source: item.source,
                reason: item.reason,
                reasonCode: item.reasonCode,
                placement: item.placement,
                modelVersion: item.modelVersion,
                score: item.score
              })
            }
            className="group block"
          >
            <Card className="flex h-full min-h-[320px] flex-col overflow-hidden rounded-lg border-slate-200/80 transition group-hover:-translate-y-0.5 group-hover:shadow-[0_18px_45px_rgba(23,33,31,0.10)]" padding="none">
              <div className={cn("bg-gradient-to-br p-4 text-white", accents[index % accents.length])}>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-bold">{item.course.code}</span>
                  <Badge tone="dark">{levelLabel(item.course.level)}</Badge>
                </div>
                <div className="mt-8 flex items-end justify-between gap-4">
                  <span className="grid size-11 place-items-center rounded-md bg-white/15">
                    <BookOpenCheck className="size-6" />
                  </span>
                  <Sparkles className="size-5 text-white/75" />
                </div>
              </div>

              <div className="flex flex-1 flex-col p-5">
                <div className="flex flex-wrap gap-2">
                  <Badge tone="brand">{relatedCourseSourceLabel(item.source)}</Badge>
                  {match && <Badge tone="amber">{match}</Badge>}
                </div>
                <h3 className="mt-4 text-lg font-bold leading-6 text-ink-900 transition group-hover:text-brand-700">
                  {item.course.title}
                </h3>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-ink-500">{item.course.summary}</p>
                <p className="mt-4 rounded-md border border-brand-100 bg-brand-50 p-3 text-sm leading-6 text-brand-700">
                  {item.reason}
                </p>
                <span className="mt-auto inline-flex items-center justify-end gap-1 pt-5 text-sm font-bold text-brand-700">
                  Xem khóa học
                  <ArrowRight className="size-4" />
                </span>
              </div>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}
