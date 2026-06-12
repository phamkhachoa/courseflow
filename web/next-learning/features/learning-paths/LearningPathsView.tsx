"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  Compass,
  GraduationCap,
  Layers3,
  RefreshCw,
  Route,
  Search,
  Sparkles,
  Target
} from "lucide-react";
import { useLearnerSession } from "@/features/auth/useLearnerSession";
import { courseDetailHref, courseModuleHref, listCatalogCourses } from "@/features/course-catalog/client-api";
import { API_BASE_URL, unwrap } from "@/shared/api/envelope";
import { Badge, Button, Card, ProgressBar, TextInput, cn } from "@/shared/ui";
import type { CatalogCourse } from "@/features/course-catalog/api";

type SearchResult = {
  id: string;
  code?: string;
  title: string;
  slug?: string;
  description?: string;
  summary?: string;
  level?: string;
  status?: string;
};

type CourseRecommendation = {
  course: SearchResult;
  reason: string;
};

type LearningTask = {
  id: string;
  label: string;
  done: boolean;
};

const STORAGE_KEY = "courseflow.learning.path.state";

const defaultTasks: LearningTask[] = [
  { id: "pick-course", label: "Chọn 1 khóa học chính để theo đuổi trong tuần", done: false },
  { id: "finish-module", label: "Hoàn thành ít nhất 1 chương có video", done: false },
  { id: "ask-question", label: "Đặt câu hỏi trong Q&A nếu bị kẹt", done: false },
  { id: "submit-work", label: "Làm quiz hoặc nộp assignment gần nhất", done: false }
];

const trackTemplates = [
  {
    title: "Backend engineer",
    query: "spring boot microservices",
    detail: "API design, service boundary, observability và deployment.",
    icon: Layers3
  },
  {
    title: "Data & analytics",
    query: "data pipeline analytics",
    detail: "Pipeline, reporting, đánh giá dữ liệu và vận hành.",
    icon: Compass
  },
  {
    title: "Production readiness",
    query: "secure api gateway kubernetes",
    detail: "Security, CI/CD, gateway và reliability.",
    icon: Target
  }
];

function loadPathState(): { goal: string; tasks: LearningTask[] } {
  if (typeof window === "undefined") return { goal: "spring boot microservices", tasks: defaultTasks };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { goal: "spring boot microservices", tasks: defaultTasks };
    const parsed = JSON.parse(raw) as { goal?: string; tasks?: LearningTask[] };
    return {
      goal: parsed.goal?.trim() || "spring boot microservices",
      tasks: parsed.tasks?.length ? parsed.tasks : defaultTasks
    };
  } catch {
    return { goal: "spring boot microservices", tasks: defaultTasks };
  }
}

function savePathState(goal: string, tasks: LearningTask[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ goal, tasks }));
}

function resultToCourse(result: SearchResult): CatalogCourse {
  return {
    id: result.id,
    code: result.code ?? "COURSE",
    title: result.title,
    slug: result.slug ?? result.id,
    summary: result.description ?? result.summary ?? "Khóa học phù hợp với mục tiêu hiện tại.",
    level: result.level,
    status: result.status
  };
}

async function recommendCourses(goal: string): Promise<CourseRecommendation[]> {
  const params = new URLSearchParams({ q: goal, limit: "6" });
  const response = await fetch(`${API_BASE_URL}/v1/search/courses/recommendations?${params.toString()}`);
  if (!response.ok) throw new Error(`Recommendations failed (${response.status})`);
  return unwrap<CourseRecommendation[]>(await response.json());
}

function levelLabel(level?: string) {
  const labels: Record<string, string> = {
    BEGINNER: "Nhập môn",
    INTERMEDIATE: "Trung cấp",
    ADVANCED: "Nâng cao",
    EXPERT: "Chuyên sâu"
  };
  return labels[level ?? ""] ?? level ?? "Mọi trình độ";
}

function CourseRecommendationCard({
  course,
  reason,
  index
}: {
  course: CatalogCourse;
  reason?: string;
  index: number;
}) {
  const accents = [
    "from-brand-600 to-signal-500",
    "from-accent-500 to-coral-500",
    "from-signal-600 to-brand-500"
  ];
  return (
    <Card className="overflow-hidden" padding="none">
      <div className={cn("bg-gradient-to-br p-4 text-white", accents[index % accents.length])}>
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-bold">{course.code}</span>
          <Badge tone="dark">{levelLabel(course.level)}</Badge>
        </div>
        <div className="mt-8 flex items-center justify-between">
          <span className="grid size-11 place-items-center rounded-md bg-white/15">
            <BookOpenCheck className="size-6" />
          </span>
          <Sparkles className="size-5 text-white/70" />
        </div>
      </div>
      <div className="p-5">
        <h3 className="text-lg font-bold leading-6 text-ink-900">{course.title}</h3>
        <p className="mt-2 line-clamp-3 text-sm leading-6 text-ink-500">{course.summary}</p>
        {reason && (
          <p className="mt-4 rounded-md border border-brand-100 bg-brand-50 p-3 text-sm leading-6 text-brand-700">
            {reason}
          </p>
        )}
        <div className="mt-5 flex flex-wrap gap-2">
          <Button asChild>
            <Link href={courseModuleHref(course)}>
              <Route className="size-4" />
              Vào học
            </Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href={courseDetailHref(course)}>Chi tiết</Link>
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function LearningPathsView() {
  const { session } = useLearnerSession();
  const [goal, setGoal] = useState("spring boot microservices");
  const [draftGoal, setDraftGoal] = useState("spring boot microservices");
  const [tasks, setTasks] = useState(defaultTasks);
  const catalog = useQuery({ queryKey: ["catalog-courses"], queryFn: listCatalogCourses });
  const recommendations = useQuery({
    queryKey: ["learning-path-recommendations", goal],
    queryFn: () => recommendCourses(goal),
    enabled: goal.trim().length >= 2,
    retry: 0
  });

  useEffect(() => {
    const state = loadPathState();
    setGoal(state.goal);
    setDraftGoal(state.goal);
    setTasks(state.tasks);
  }, []);

  useEffect(() => {
    savePathState(goal, tasks);
  }, [goal, tasks]);

  const recommendedCourses = useMemo(() => {
    if (recommendations.data?.length) {
      return recommendations.data.map((item) => ({
        course: resultToCourse(item.course),
        reason: item.reason
      }));
    }
    return (catalog.data ?? []).slice(0, 6).map((course) => ({
      course,
      reason: "Khóa học đang có trong catalog và phù hợp để bắt đầu lộ trình."
    }));
  }, [catalog.data, recommendations.data]);

  const doneCount = tasks.filter((task) => task.done).length;
  const progress = Math.round((doneCount / tasks.length) * 100);

  function applyGoal(nextGoal: string) {
    const trimmed = nextGoal.trim();
    if (!trimmed) return;
    setGoal(trimmed);
    setDraftGoal(trimmed);
  }

  function toggleTask(id: string) {
    setTasks((current) =>
      current.map((task) => (task.id === id ? { ...task, done: !task.done } : task))
    );
  }

  return (
    <div className="space-y-7">
      <section
        className="overflow-hidden rounded-lg bg-cover bg-center p-6 text-white sm:p-8"
        style={{
          backgroundImage:
            "linear-gradient(90deg, rgba(16,43,40,0.94), rgba(16,43,40,0.7), rgba(16,43,40,0.28)), url('/images/lms-hero-dashboard.png')"
        }}
      >
        <div className="flex flex-wrap gap-2">
          <Badge tone="dark">Learning path</Badge>
          {session && <Badge tone="dark">{session.user.fullName || session.user.email}</Badge>}
        </div>
        <div className="mt-14 max-w-3xl">
          <p className="text-sm font-bold uppercase tracking-wide text-accent-100">Mục tiêu hiện tại</p>
          <h1 className="mt-3 text-4xl font-bold leading-tight sm:text-5xl">{goal}</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-white/80">
            Hệ thống dùng search recommendations để đề xuất khóa học theo mục tiêu, sau đó gom thành checklist học tập tuần này.
          </p>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-5">
          <Card>
            <div className="flex items-start gap-3">
              <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
                <Search className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-brand-600">Tùy chỉnh lộ trình</p>
                <div className="mt-3 flex flex-col gap-3 sm:flex-row">
                  <TextInput
                    value={draftGoal}
                    onChange={(event) => setDraftGoal(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") applyGoal(draftGoal);
                    }}
                    placeholder="Ví dụ: spring boot microservices"
                  />
                  <Button type="button" onClick={() => applyGoal(draftGoal)} className="sm:w-36">
                    <Sparkles className="size-4" />
                    Gợi ý
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            {trackTemplates.map(({ icon: Icon, ...track }) => (
              <button
                key={track.title}
                type="button"
                onClick={() => applyGoal(track.query)}
                className="rounded-lg border border-black/10 bg-white p-4 text-left shadow-[0_18px_45px_rgba(23,33,31,0.08)] transition hover:border-brand-200 hover:bg-brand-50/45"
              >
                <span className="grid size-10 place-items-center rounded-md bg-brand-50 text-brand-700">
                  <Icon className="size-5" />
                </span>
                <p className="mt-4 font-bold text-ink-900">{track.title}</p>
                <p className="mt-2 text-sm leading-6 text-ink-500">{track.detail}</p>
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-bold text-brand-600">Khóa học đề xuất</p>
              <h2 className="mt-1 text-3xl font-bold text-ink-900">Học theo mục tiêu</h2>
            </div>
            {recommendations.isFetching && (
              <Badge tone="neutral">
                <RefreshCw className="mr-1 size-3.5 animate-spin" />
                Đang cập nhật
              </Badge>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {recommendedCourses.map(({ course, reason }, index) => (
              <CourseRecommendationCard key={`${course.slug}-${index}`} course={course} reason={reason} index={index} />
            ))}
          </div>
        </div>

        <aside className="space-y-5">
          <Card>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-bold text-brand-600">Checklist</p>
                <h2 className="mt-1 text-2xl font-bold text-ink-900">Tuần này</h2>
              </div>
              <span className="grid size-10 place-items-center rounded-md bg-accent-50 text-accent-600">
                <Target className="size-5" />
              </span>
            </div>
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="font-medium text-ink-500">
                  {doneCount}/{tasks.length} việc xong
                </span>
                <span className="font-bold text-ink-900">{progress}%</span>
              </div>
              <ProgressBar value={progress} />
            </div>
            <div className="mt-5 space-y-3">
              {tasks.map((task) => (
                <button
                  key={task.id}
                  type="button"
                  onClick={() => toggleTask(task.id)}
                  className={cn(
                    "flex w-full items-start gap-3 rounded-md border p-3 text-left transition",
                    task.done
                      ? "border-brand-100 bg-brand-50 text-brand-800"
                      : "border-black/10 bg-[#fbfaf7] text-ink-700 hover:border-brand-200"
                  )}
                >
                  <CheckCircle2 className={cn("mt-0.5 size-5 shrink-0", task.done ? "text-brand-700" : "text-ink-400")} />
                  <span className="text-sm font-semibold leading-5">{task.label}</span>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-md bg-signal-50 text-signal-600">
                <GraduationCap className="size-5" />
              </span>
              <div>
                <p className="font-bold text-ink-900">Luồng học đề xuất</p>
                <p className="mt-2 text-sm leading-6 text-ink-500">
                  Chọn khóa chính, hoàn thành chapter đầu, hỏi trong Q&A khi kẹt, rồi kiểm tra bằng quiz/assignment.
                </p>
                <Link href="/search" className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-brand-700">
                  Mở search realtime
                  <ArrowRight className="size-4" />
                </Link>
              </div>
            </div>
          </Card>
        </aside>
      </section>
    </div>
  );
}
