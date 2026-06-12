"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, ClipboardCheck, LockKeyhole, Trophy } from "lucide-react";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, Card, cn } from "@/shared/ui";
import {
  useAttemptDetail,
  useQuiz,
  type QuizAttemptAnswer,
  type StudentQuizQuestion
} from "./hooks";

function formatAnswer(answer: unknown, question?: StudentQuizQuestion) {
  const labels = Array.isArray(answer) ? answer.map(String) : answer == null ? [] : [String(answer)];
  if (labels.length === 0) return "Chưa trả lời";
  if (!question?.options?.length) return labels.join(", ");

  return labels
    .map((label) => {
      const option = question.options?.find((item) => item.label === label);
      return option ? `${option.label}. ${option.content}` : label;
    })
    .join(", ");
}

function formatDateTime(value?: string) {
  if (!value) return "Chưa có";
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      dateStyle: "short",
      timeStyle: "short"
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function visibleQuestionScore(answer: QuizAttemptAnswer) {
  const score = answer.totalScore ?? answer.manualScore ?? answer.autoScore;
  return typeof score === "number" ? score : null;
}

function attemptStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    IN_PROGRESS: "Đang làm",
    SUBMITTED: "Đã nộp",
    GRADED: "Đã chấm",
    PARTIALLY_GRADED: "Chờ chấm tay",
    EXPIRED: "Quá hạn",
    AUTO_SUBMITTED: "Tự nộp"
  };
  return labels[status ?? ""] ?? status ?? "Không rõ";
}

export function AttemptReview({ attemptId }: { attemptId: string }) {
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState<StoredSession | null>(null);
  const [currentHref, setCurrentHref] = useState(`/quizzes/attempts/${attemptId}`);
  const detail = useAttemptDetail(attemptId, mounted && Boolean(session));
  const quizId = detail.data?.attempt.quizId ?? "";
  const quiz = useQuiz(quizId, mounted && Boolean(session) && Boolean(quizId));

  useEffect(() => {
    setMounted(true);
    setCurrentHref(`${window.location.pathname}${window.location.search}`);
    setSession(learnerSession.read());
    return learnerSession.subscribe(setSession);
  }, []);

  const questionMap = useMemo(() => {
    const rows = quiz.data?.questions ?? [];
    return new Map(rows.map((question) => [question.id, question]));
  }, [quiz.data?.questions]);

  if (!mounted) return <p className="text-ink-500">Đang kiểm tra phiên đăng nhập...</p>;
  if (!session) {
    const loginHref = `/login?next=${encodeURIComponent(currentHref)}`;
    const registerHref = `/register?next=${encodeURIComponent(currentHref)}`;

    return (
      <Card className="p-6">
        <div className="flex items-start gap-3">
          <LockKeyhole className="mt-0.5 size-5 text-accent-600" />
          <div>
            <h2 className="text-xl font-bold text-ink-900">Đăng nhập để xem bài làm</h2>
            <p className="mt-2 text-sm leading-6 text-ink-500">
              Lịch sử attempt chỉ hiển thị cho đúng tài khoản đã làm bài.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button asChild>
                <Link href={loginHref}>Đăng nhập</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href={registerHref}>Đăng ký</Link>
              </Button>
            </div>
          </div>
        </div>
      </Card>
    );
  }
  if (detail.isLoading) return <p className="text-ink-500">Đang tải bài làm...</p>;
  if (detail.isError) {
    return (
      <Card className="p-6">
        <p className="font-bold text-red-600">Không tải được bài làm</p>
        <p className="mt-2 text-sm text-ink-500">
          {detail.error instanceof Error ? detail.error.message : "Lượt làm không tồn tại hoặc không thuộc tài khoản này."}
        </p>
      </Card>
    );
  }
  if (!detail.data) return null;

  const { attempt, answers } = detail.data;

  return (
    <div className="space-y-5">
      <Button asChild variant="secondary">
        <Link href={`/quizzes/${attempt.quizId}`}>
          <span className="inline-flex items-center gap-2">
            <ArrowLeft className="size-4" />
            <span>Quay lại bài thi</span>
          </span>
        </Link>
      </Button>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="p-6">
          <div className="flex flex-wrap gap-2">
            <Badge tone="coral">Lượt {attempt.attemptNo}</Badge>
            <Badge tone={attempt.status === "GRADED" ? "brand" : "amber"}>{attemptStatusLabel(attempt.status)}</Badge>
          </div>
          <h2 className="mt-5 text-3xl font-bold text-ink-900">
            {quiz.data?.title ?? "Bài làm"}
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-500">
            Xem lại câu trả lời đã nộp. Điểm từng câu chỉ hiện khi chính sách bài thi cho phép công bố đáp án/điểm chi tiết.
          </p>
        </Card>

        <Card className="p-5">
          <p className="text-sm font-bold text-brand-600">Kết quả</p>
          <div className="mt-4 space-y-3 text-sm">
            <ReviewFact icon={<Trophy className="size-4" />} label="Điểm" value={attempt.score ?? "Đang chấm"} />
            <ReviewFact icon={<ClipboardCheck className="size-4" />} label="Đã nộp" value={formatDateTime(attempt.submittedAt)} />
            <ReviewFact icon={<CheckCircle2 className="size-4" />} label="Tự nộp" value={attempt.autoSubmitted ? "Có" : "Không"} />
          </div>
        </Card>
      </section>

      <div className="grid gap-4">
        {answers.map((answer, index) => {
          const question = questionMap.get(answer.questionId);
          const score = visibleQuestionScore(answer);
          return (
            <Card key={answer.questionId} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-md bg-brand-50 text-sm font-bold text-brand-700">
                    {index + 1}
                  </span>
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="brand">{question?.type ?? "QUESTION"}</Badge>
                      {score != null ? <Badge tone="sky">{score} điểm</Badge> : <Badge tone="neutral">Điểm ẩn</Badge>}
                    </div>
                    <h3 className="mt-3 text-base font-bold leading-7 text-ink-900">
                      {question?.stem ?? `Question ${answer.questionId}`}
                    </h3>
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-md border border-black/10 bg-[#fbfaf7] p-3 text-sm">
                <p className="font-bold text-ink-900">Câu trả lời của bạn</p>
                <p className={cn("mt-2 leading-6", answer.answer == null ? "text-ink-500" : "text-ink-700")}>
                  {formatAnswer(answer.answer, question)}
                </p>
              </div>

              {answer.manualFeedback && (
                <div className="mt-3 rounded-md border border-brand-100 bg-brand-50 p-3 text-sm text-brand-700">
                  <p className="font-bold">Nhận xét</p>
                  <p className="mt-1 leading-6">{answer.manualFeedback}</p>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function ReviewFact({ icon, label, value }: { icon: ReactNode; label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-[#fbfaf7] p-3">
      <span className="inline-flex items-center gap-2 font-semibold text-ink-900">
        {icon} {label}
      </span>
      <span className="text-right font-bold text-ink-700">{value}</span>
    </div>
  );
}
