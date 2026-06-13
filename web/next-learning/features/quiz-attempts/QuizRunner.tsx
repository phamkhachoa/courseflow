"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Flag,
  History,
  ListChecks,
  LockKeyhole,
  PlayCircle,
  RotateCcw,
  Save,
  Send
} from "lucide-react";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, Card, TextInput, Textarea, cn } from "@/shared/ui";
import {
  useMyQuizAttempts,
  useQuiz,
  useStartAttempt,
  useSubmitAttempt,
  type QuizAnswers,
  type QuizAttempt,
  type StudentQuizQuestion,
  useAttemptDetail,
  useSaveAnswers
} from "./hooks";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function questionTypeLabel(type: string) {
  const labels: Record<string, string> = {
    MULTIPLE_CHOICE: "Một đáp án",
    TRUE_FALSE: "Đúng/Sai",
    MULTIPLE_RESPONSE: "Nhiều đáp án",
    SHORT_ANSWER: "Trả lời ngắn",
    FILL_BLANK: "Điền khuyết",
    NUMERICAL: "Số",
    MATCHING: "Ghép đôi",
    ESSAY: "Tự luận"
  };
  return labels[type] ?? type;
}

function attemptStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    IN_PROGRESS: "Đang làm",
    SUBMITTED: "Đã nộp",
    GRADED: "Đã chấm",
    PARTIALLY_GRADED: "Chấm một phần",
    AUTO_SUBMITTED: "Tự nộp"
  };
  return labels[status ?? ""] ?? status ?? "Không rõ";
}

function attemptStatusTone(status?: string) {
  if (status === "IN_PROGRESS") return "amber";
  if (status === "GRADED" || status === "PARTIALLY_GRADED") return "brand";
  if (status === "SUBMITTED" || status === "AUTO_SUBMITTED") return "sky";
  return "neutral";
}

function quizStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    PUBLISHED: "Đã công khai",
    DRAFT: "Nháp",
    ARCHIVED: "Lưu trữ"
  };
  return labels[status ?? ""] ?? status ?? "Bài thi";
}

function scoringMethodLabel(method?: string) {
  const labels: Record<string, string> = {
    HIGHEST: "điểm cao nhất",
    LATEST: "lần làm gần nhất",
    AVERAGE: "điểm trung bình"
  };
  return labels[method ?? ""] ?? "chính sách của giảng viên";
}

function formatAttemptTime(value?: string) {
  if (!value) return "Chưa có thời gian";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa có thời gian";
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function isAnswered(question: StudentQuizQuestion, answers: QuizAnswers) {
  const value = answers[question.id];
  if (Array.isArray(value)) return value.length > 0;
  return value !== undefined && String(value).trim() !== "";
}

function countAnswered(questions: StudentQuizQuestion[], answers: QuizAnswers) {
  return questions.filter((question) => isAnswered(question, answers)).length;
}

function secondsUntil(value?: string) {
  if (!value) return null;
  const deadline = new Date(value).getTime();
  if (Number.isNaN(deadline)) return null;
  return Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
}

function quizAttemptWindow(openAt?: string, closeAt?: string) {
  const now = Date.now();
  const opensAt = openAt ? new Date(openAt).getTime() : 0;
  const closesAt = closeAt ? new Date(closeAt).getTime() : 0;

  if (opensAt && now < opensAt) {
    return {
      canStart: false,
      actionLabel: "Chưa mở bài",
      message: `Bài thi mở lúc ${formatAttemptTime(openAt)}. Bạn có thể quay lại đúng thời gian để bắt đầu.`
    };
  }

  if (closesAt && now > closesAt) {
    return {
      canStart: false,
      actionLabel: "Đã đóng bài",
      message: `Bài thi đã đóng lúc ${formatAttemptTime(closeAt)}. Bạn vẫn có thể xem lại các lượt đã nộp.`
    };
  }

  return {
    canStart: true,
    actionLabel: null,
    message: null
  };
}

function jumpToQuestion(questionId: string) {
  document.getElementById(`question-${questionId}`)?.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

function QuestionPalette({
  questions,
  answers,
  flaggedQuestionIds
}: {
  questions: StudentQuizQuestion[];
  answers: QuizAnswers;
  flaggedQuestionIds: string[];
}) {
  const answered = countAnswered(questions, answers);
  const firstUnanswered = questions.find((question) => !isAnswered(question, answers));
  const firstFlagged = questions.find((question) => flaggedQuestionIds.includes(question.id));

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-brand-600">Bảng câu hỏi</p>
          <p className="mt-1 text-sm text-ink-500">
            {answered}/{questions.length} câu đã trả lời
          </p>
        </div>
        <span className="grid size-10 place-items-center rounded-md bg-brand-50 text-brand-700">
          <ListChecks className="size-5" />
        </span>
      </div>

      <div className="mt-4 grid grid-cols-5 gap-2 sm:grid-cols-8 xl:grid-cols-5">
        {questions.map((question, index) => {
          const done = isAnswered(question, answers);
          const flagged = flaggedQuestionIds.includes(question.id);
          return (
            <button
              key={question.id}
              type="button"
              onClick={() => jumpToQuestion(question.id)}
              className={cn(
                "relative h-10 rounded-md border text-sm font-bold transition",
                done
                  ? "border-brand-200 bg-brand-600 text-white hover:bg-brand-700"
                  : "border-black/10 bg-white text-ink-700 hover:border-accent-200 hover:bg-accent-50",
                flagged && "ring-2 ring-accent-300"
              )}
              aria-label={`Tới câu ${index + 1}${done ? " đã trả lời" : " chưa trả lời"}${flagged ? ", cần xem lại" : ""}`}
            >
              {flagged && <span className="absolute right-1 top-1 size-1.5 rounded-full bg-accent-500" />}
              {index + 1}
            </button>
          );
        })}
      </div>

      <div className="mt-4 space-y-2 text-xs font-semibold text-ink-500">
        <div className="flex items-center gap-2">
          <span className="size-3 rounded-sm bg-brand-600" />
          Đã trả lời
        </div>
        <div className="flex items-center gap-2">
          <span className="size-3 rounded-sm border border-black/10 bg-white" />
          Chưa trả lời
        </div>
        <div className="flex items-center gap-2">
          <span className="size-3 rounded-sm border border-accent-300 bg-accent-50 ring-2 ring-accent-200" />
          Cần xem lại
        </div>
      </div>

      {firstFlagged && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="mt-4 w-full"
          onClick={() => jumpToQuestion(firstFlagged.id)}
        >
          Tới câu cần xem lại
        </Button>
      )}
      {firstUnanswered && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="mt-2 w-full"
          onClick={() => jumpToQuestion(firstUnanswered.id)}
        >
          Tới câu chưa trả lời
        </Button>
      )}
    </Card>
  );
}

export function QuizRunner({ quizId }: { quizId: string }) {
  const [mounted, setMounted] = useState(false);
  const [session, setSession] = useState<StoredSession | null>(null);
  const [currentHref, setCurrentHref] = useState(`/quizzes/${quizId}`);
  const { data: quiz, isLoading, isError, error } = useQuiz(quizId, mounted && Boolean(session));
  const attempts = useMyQuizAttempts(quizId, mounted && Boolean(session));
  const start = useStartAttempt(quizId);
  const submit = useSubmitAttempt();
  const saveAnswers = useSaveAnswers();
  const submitAttempt = submit.mutate;

  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [attemptQuestions, setAttemptQuestions] = useState<StudentQuizQuestion[] | null>(null);
  const [answers, setAnswers] = useState<QuizAnswers>({});
  const [remaining, setRemaining] = useState<number | null>(null);
  const [autoSubmitted, setAutoSubmitted] = useState(false);
  const [hydratedAttemptId, setHydratedAttemptId] = useState<string | null>(null);
  const [flaggedQuestionIds, setFlaggedQuestionIds] = useState<string[]>([]);
  const [hydratedFlagsAttemptId, setHydratedFlagsAttemptId] = useState<string | null>(null);
  const attemptDetail = useAttemptDetail(attemptId ?? "", mounted && Boolean(session && attemptId));

  useEffect(() => {
    setMounted(true);
    setCurrentHref(`${window.location.pathname}${window.location.search}`);
    setSession(learnerSession.read());
    return learnerSession.subscribe(setSession);
  }, []);

  useEffect(() => {
    if (remaining === null) return;
    if (remaining <= 0) {
      if (attemptId && !autoSubmitted && !submit.isPending && !submit.isSuccess) {
        setAutoSubmitted(true);
        submitAttempt({ attemptId, answers });
      }
      return;
    }
    const timer = setTimeout(() => setRemaining((value) => (value === null ? value : value - 1)), 1000);
    return () => clearTimeout(timer);
  }, [answers, attemptId, autoSubmitted, remaining, submit.isPending, submit.isSuccess, submitAttempt]);

  useEffect(() => {
    if (!attemptId || hydratedAttemptId === attemptId || !attemptDetail.data) return;
    const draftAnswers = Object.fromEntries(
      attemptDetail.data.answers
        .filter((answer) => answer.answer !== undefined && answer.answer !== null)
        .map((answer) => [answer.questionId, answer.answer])
    );
    setAnswers(draftAnswers);
    const restoredRemaining = secondsUntil(attemptDetail.data.attempt.deadlineAt);
    if (restoredRemaining !== null) {
      setRemaining(restoredRemaining);
    }
    setHydratedAttemptId(attemptId);
  }, [attemptDetail.data, attemptId, hydratedAttemptId]);

  useEffect(() => {
    if (!attemptId || submit.isPending || submit.isSuccess || autoSubmitted) return;
    if (Object.keys(answers).length === 0) return;
    const timer = setTimeout(() => {
      saveAnswers.mutate({ attemptId, answers });
    }, 800);
    return () => clearTimeout(timer);
  }, [answers, attemptId, autoSubmitted, saveAnswers, submit.isPending, submit.isSuccess]);

  useEffect(() => {
    if (!attemptId) {
      setFlaggedQuestionIds([]);
      setHydratedFlagsAttemptId(null);
      return;
    }
    try {
      const raw = localStorage.getItem(`courseflow.quiz.flags.${attemptId}`);
      setFlaggedQuestionIds(raw ? (JSON.parse(raw) as string[]) : []);
    } catch {
      setFlaggedQuestionIds([]);
    }
    setHydratedFlagsAttemptId(attemptId);
  }, [attemptId]);

  useEffect(() => {
    if (!attemptId || hydratedFlagsAttemptId !== attemptId) return;
    localStorage.setItem(`courseflow.quiz.flags.${attemptId}`, JSON.stringify(flaggedQuestionIds));
  }, [attemptId, flaggedQuestionIds, hydratedFlagsAttemptId]);

  useEffect(() => {
    if (!attemptId || !submit.isSuccess) return;
    localStorage.removeItem(`courseflow.quiz.flags.${attemptId}`);
  }, [attemptId, submit.isSuccess]);

  const questions = useMemo(() => attemptQuestions ?? quiz?.questions ?? [], [attemptQuestions, quiz]);
  const totalPoints = useMemo(
    () => questions.reduce((sum, question) => sum + Number(question.points ?? 0), 0),
    [questions]
  );
  const answeredCount = countAnswered(questions, answers);
  const unansweredCount = Math.max(questions.length - answeredCount, 0);
  const progressPct = questions.length ? Math.round((answeredCount / questions.length) * 100) : 0;
  const attemptRows = attempts.data ?? [];
  const inProgressAttempt = attemptRows.find((attempt) => attempt.status === "IN_PROGRESS");
  const usedAttempts = attemptRows.length;
  const remainingAttempts = Math.max((quiz?.attemptsAllowed ?? 1) - usedAttempts, 0);
  const attemptWindow = quizAttemptWindow(quiz?.openAt, quiz?.closeAt);
  const canStart = (remainingAttempts > 0 || Boolean(inProgressAttempt)) && !attempts.isLoading;
  const canEnterAttempt = Boolean(inProgressAttempt) || attemptWindow.canStart;
  const flaggedCount = flaggedQuestionIds.length;
  const loginHref = `/login?next=${encodeURIComponent(currentHref)}`;
  const registerHref = `/register?next=${encodeURIComponent(currentHref)}`;

  function toggleFlag(questionId: string) {
    setFlaggedQuestionIds((current) =>
      current.includes(questionId)
        ? current.filter((id) => id !== questionId)
        : [...current, questionId]
    );
  }

  if (!mounted) return <p className="text-ink-500">Đang kiểm tra phiên đăng nhập...</p>;
  if (!session?.user?.id) {
    return (
      <Card className="p-6">
        <div className="flex items-start gap-3">
          <LockKeyhole className="mt-0.5 size-5 text-accent-600" />
          <div>
            <h2 className="text-xl font-bold text-ink-900">Đăng nhập để làm bài</h2>
            <p className="mt-2 text-sm leading-6 text-ink-500">
              Bài thi được gắn với tài khoản học viên để lưu attempt, timer và điểm số.
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
  if (isLoading) return <p className="text-ink-500">Đang tải bài thi...</p>;
  if (isError)
    return (
      <Card>
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 size-5 text-red-600" />
          <div>
            <p className="font-bold text-red-600">Không tải được bài thi</p>
            <p className="mt-1 text-sm leading-6 text-ink-500">
              {error instanceof Error ? error.message : "Bạn cần đăng nhập hoặc bài thi chưa được công khai."}
            </p>
          </div>
        </div>
      </Card>
    );
  if (!quiz) return null;

  function beginAttempt() {
    if (!session?.user?.id) return;
    start.mutate(undefined, {
      onSuccess: (response) => {
        setAnswers({});
        setAttemptQuestions(response.questions ?? []);
        setAttemptId(response.attempt.id);
        setHydratedAttemptId(null);
        setRemaining(secondsUntil(response.attempt.deadlineAt) ?? (quiz?.durationMinutes ?? 10) * 60);
        setAutoSubmitted(false);
        void attempts.refetch();
      }
    });
  }

  function handleSubmitAttempt() {
    if (!attemptId) return;
    if (unansweredCount > 0) {
      const ok = window.confirm(`Bạn còn ${unansweredCount} câu chưa trả lời. Vẫn nộp bài?`);
      if (!ok) return;
    }
    submit.mutate({ attemptId, answers });
  }

  if (submit.isSuccess) {
    return (
      <Card className="p-8 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-full bg-emerald-50 text-emerald-700">
          <CheckCircle2 className="size-7" />
        </span>
        <h2 className="mt-5 text-2xl font-bold text-ink-900">Đã nộp bài</h2>
        <p className="mt-2 text-ink-500">
          Điểm hiện tại: <span className="font-bold text-ink-900">{submit.data?.score ?? "đang chấm"}</span>
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {submit.data?.id && (
            <Button asChild>
              <Link href={`/quizzes/attempts/${submit.data.id}`}>Xem lại bài làm</Link>
            </Button>
          )}
          <Button asChild variant="secondary">
            <Link href="/">Về dashboard</Link>
          </Button>
        </div>
      </Card>
    );
  }

  if (!attemptId) {
    const startLabel = start.isPending
      ? "Đang bắt đầu"
      : inProgressAttempt
        ? "Tiếp tục bài đang làm"
        : attemptWindow.actionLabel
          ? attemptWindow.actionLabel
        : "Bắt đầu làm bài";
    const attemptBadge = inProgressAttempt
      ? "Đang giữ 1 lượt"
      : remainingAttempts > 0
        ? `Còn ${remainingAttempts} lượt`
        : "Hết lượt";

    return (
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              <Badge tone="coral">Bài thi</Badge>
              <Badge tone={quiz.status === "PUBLISHED" ? "brand" : "amber"}>{quizStatusLabel(quiz.status)}</Badge>
            </div>
            <Badge tone={inProgressAttempt ? "amber" : remainingAttempts > 0 ? "sky" : "neutral"}>
              {attemptBadge}
            </Badge>
          </div>
          <h2 className="mt-5 max-w-3xl text-3xl font-bold leading-tight text-ink-900">{quiz.title}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-500">
            Làm bài theo lượt, có đồng hồ tính giờ và tự lưu bản nháp. Nếu lỡ refresh hoặc thoát trang,
            bạn có thể quay lại để tiếp tục bài đang làm.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-4">
              <Save className="size-5 text-brand-600" />
              <p className="mt-3 text-sm font-bold text-ink-900">Tự lưu</p>
              <p className="mt-1 text-xs leading-5 text-ink-500">Câu trả lời được lưu nháp khi bạn chọn.</p>
            </div>
            <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-4">
              <Clock3 className="size-5 text-accent-600" />
              <p className="mt-3 text-sm font-bold text-ink-900">Có giới hạn giờ</p>
              <p className="mt-1 text-xs leading-5 text-ink-500">{quiz.durationMinutes ?? "—"} phút cho lượt làm này.</p>
            </div>
            <div className="rounded-md border border-black/10 bg-[#fbfaf7] p-4">
              <RotateCcw className="size-5 text-coral-600" />
              <p className="mt-3 text-sm font-bold text-ink-900">Có thể làm lại</p>
              <p className="mt-1 text-xs leading-5 text-ink-500">Điểm lấy theo {scoringMethodLabel(quiz.scoringMethod)}.</p>
            </div>
          </div>

          {start.isError && (
            <p className="mt-4 rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
              {start.error instanceof Error ? start.error.message : "Không thể bắt đầu bài thi."}
            </p>
          )}
          {!attempts.isLoading && remainingAttempts <= 0 && (
            <p className="mt-4 rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">
              Bạn đã dùng hết số lượt làm bài thi này.
            </p>
          )}
          {!inProgressAttempt && attemptWindow.message && (
            <p className="mt-4 rounded-md border border-sky-100 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-700">
              {attemptWindow.message}
            </p>
          )}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button
              onClick={beginAttempt}
              disabled={start.isPending || !session?.user?.id || quiz.status !== "PUBLISHED" || !canStart || !canEnterAttempt}
              className="w-full sm:w-auto"
            >
              <PlayCircle className="size-4" />
              {startLabel}
            </Button>
            {inProgressAttempt && (
              <span className="inline-flex items-center gap-2 text-sm font-semibold text-amber-700">
                <ArrowRight className="size-4" />
                Vào lại bài để tiếp tục từ bản nháp gần nhất
              </span>
            )}
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="p-5">
            <p className="text-sm font-bold text-brand-600">Thông tin bài thi</p>
            <div className="mt-4 space-y-3 text-sm">
              <QuizFact icon={<Clock3 className="size-4" />} label="Thời lượng" value={`${quiz.durationMinutes ?? "—"} phút`} />
              <QuizFact icon={<ClipboardCheck className="size-4" />} label="Số câu" value={`${questions.length} câu hỏi`} />
              <QuizFact icon={<ListChecks className="size-4" />} label="Tổng điểm" value={`${totalPoints} điểm`} />
              <QuizFact icon={<CheckCircle2 className="size-4" />} label="Lượt còn lại" value={`${remainingAttempts}/${quiz.attemptsAllowed ?? 1}`} />
              <QuizFact
                icon={<Save className="size-4" />}
                label="Lưu nháp"
                value={inProgressAttempt ? "Có bản nháp" : "Tự động"}
              />
            </div>
          </Card>
          <AttemptHistory attempts={attemptRows} loading={attempts.isLoading} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="sticky top-16 z-20 rounded-lg border border-black/10 bg-white/95 p-4 shadow-[0_18px_45px_rgba(23,33,31,0.10)] backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase text-brand-600">Đang làm bài</p>
            <h2 className="truncate text-lg font-bold text-ink-900">{quiz.title}</h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-md bg-ink-900 px-3 py-2 font-mono text-sm font-bold text-white">
              <Clock3 className="size-4" />
              {remaining !== null ? formatTime(remaining) : "—"}
            </span>
            <Badge tone="brand">{answeredCount}/{questions.length} câu</Badge>
            {flaggedCount > 0 && <Badge tone="amber">{flaggedCount} cần xem lại</Badge>}
            <Badge tone={saveAnswers.isError ? "coral" : saveAnswers.isPending ? "amber" : "neutral"}>
              {saveAnswers.isError
                ? "Lưu nháp lỗi"
                : saveAnswers.isPending
                  ? "Đang lưu nháp"
                  : saveAnswers.isSuccess
                    ? "Đã lưu bản nháp"
                    : "Đã bật tự lưu"}
            </Badge>
          </div>
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-black/10">
          <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${progressPct}%` }} />
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="grid gap-4">
          {questions.map((question, index) => (
            <div key={question.id} id={`question-${question.id}`} className="scroll-mt-36">
              <QuestionCard
                question={question}
                index={index}
                value={answers[question.id]}
                flagged={flaggedQuestionIds.includes(question.id)}
                onToggleFlag={() => toggleFlag(question.id)}
                onChange={(value) => setAnswers((current) => ({ ...current, [question.id]: value }))}
              />
            </div>
          ))}
        </div>
        <aside className="order-first xl:sticky xl:top-36 xl:order-none xl:self-start">
          <QuestionPalette questions={questions} answers={answers} flaggedQuestionIds={flaggedQuestionIds} />
        </aside>
      </div>

      {submit.isError && (
        <p className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
          {submit.error instanceof Error ? submit.error.message : "Không thể nộp bài."}
        </p>
      )}
      {saveAnswers.isError && (
        <p className="rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700">
          Chưa lưu được bản nháp gần nhất. Bạn vẫn có thể nộp bài, nhưng nên kiểm tra lại kết nối.
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-black/10 bg-white p-4">
        <div className="text-sm text-ink-500">
          <p>
            Đã trả lời <span className="font-bold text-ink-900">{answeredCount}</span> / {questions.length} câu.
          </p>
          {unansweredCount > 0 && (
            <button
              type="button"
              className="mt-1 font-semibold text-accent-600 hover:text-accent-700"
              onClick={() => {
                const first = questions.find((question) => !isAnswered(question, answers));
                if (first) jumpToQuestion(first.id);
              }}
            >
              Còn {unansweredCount} câu chưa trả lời
            </button>
          )}
          {flaggedCount > 0 && (
            <p className="mt-1 font-semibold text-ink-700">
              Có {flaggedCount} câu đã đánh dấu để xem lại trước khi nộp.
            </p>
          )}
        </div>
        <Button
          onClick={handleSubmitAttempt}
          disabled={submit.isPending}
        >
          <Send className="size-4" />
          {submit.isPending ? "Đang nộp" : "Nộp bài"}
        </Button>
      </div>
    </div>
  );
}

function AttemptHistory({ attempts, loading }: { attempts: QuizAttempt[]; loading: boolean }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-bold text-brand-600">Lịch sử làm bài</p>
        <History className="size-4 text-ink-500" />
      </div>
      {loading && <p className="mt-4 text-sm text-ink-500">Đang tải lịch sử...</p>}
      {!loading && attempts.length === 0 && (
        <p className="mt-4 rounded-md bg-[#fbfaf7] px-3 py-3 text-sm text-ink-500">
          Bạn chưa có lượt làm nào. Khi bắt đầu, hệ thống sẽ lưu tiến độ tại đây.
        </p>
      )}
      {attempts.length > 0 && (
        <div className="mt-4 space-y-2">
          {attempts.slice(0, 5).map((attempt) => {
            const isInProgress = attempt.status === "IN_PROGRESS";
            return (
              <Link
                key={attempt.id}
                href={isInProgress ? `/quizzes/${attempt.quizId}` : `/quizzes/attempts/${attempt.id}`}
                className="block rounded-md bg-[#fbfaf7] p-3 text-sm transition hover:bg-brand-50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-ink-900">Lần {attempt.attemptNo}</p>
                    <p className="mt-1 text-xs text-ink-500">
                      {formatAttemptTime(attempt.submittedAt ?? attempt.startedAt)}
                    </p>
                  </div>
                  <Badge tone={attemptStatusTone(attempt.status)}>{attemptStatusLabel(attempt.status)}</Badge>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span className="text-xs font-semibold text-ink-500">
                    {isInProgress ? "Tiếp tục làm bài" : "Xem bài đã nộp"}
                  </span>
                  <span className="font-bold text-ink-900">{attempt.score ?? "Đang chấm"}</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function QuizFact({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-[#fbfaf7] p-3">
      <span className="inline-flex items-center gap-2 font-semibold text-ink-900">
        {icon} {label}
      </span>
      <span className="font-bold text-ink-700">{value}</span>
    </div>
  );
}

function QuestionCard({
  question,
  index,
  value,
  flagged,
  onToggleFlag,
  onChange
}: {
  question: StudentQuizQuestion;
  index: number;
  value: unknown;
  flagged: boolean;
  onToggleFlag: () => void;
  onChange: (value: unknown) => void;
}) {
  const isMultiple = question.type === "MULTIPLE_RESPONSE";
  const isChoice = ["MULTIPLE_CHOICE", "TRUE_FALSE", "MULTIPLE_RESPONSE"].includes(question.type);
  const selectedLabels = Array.isArray(value) ? value.map(String) : [];

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-md bg-brand-50 text-sm font-bold text-brand-700">
            {index + 1}
          </span>
          <div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="brand">{questionTypeLabel(question.type)}</Badge>
              <Badge tone="neutral">{question.points ?? 0} điểm</Badge>
            </div>
            <h3 className="mt-3 text-base font-bold leading-7 text-ink-900">{question.stem}</h3>
          </div>
        </div>
        <Button
          type="button"
          variant={flagged ? "secondary" : "ghost"}
          size="sm"
          onClick={onToggleFlag}
          className={flagged ? "border-accent-200 bg-accent-50 text-accent-600 hover:bg-accent-50" : ""}
        >
          <Flag className="size-4" />
          {flagged ? "Bỏ đánh dấu" : "Đánh dấu"}
        </Button>
      </div>

      {isChoice ? (
        <div className="mt-5 grid gap-2">
          {(question.options ?? []).map((option) => {
            const checked = isMultiple ? selectedLabels.includes(option.label) : value === option.label;
            return (
              <label
                key={option.id}
                className={cn(
                  "flex cursor-pointer items-start gap-3 rounded-md border px-3 py-3 text-sm transition",
                  checked ? "border-brand-300 bg-brand-50" : "border-black/10 bg-white hover:bg-[#fbfaf7]"
                )}
              >
                <input
                  type={isMultiple ? "checkbox" : "radio"}
                  name={question.id}
                  value={option.label}
                  checked={checked}
                  className="mt-1"
                  onChange={() => {
                    if (!isMultiple) {
                      onChange(option.label);
                      return;
                    }
                    const next = selectedLabels.includes(option.label)
                      ? selectedLabels.filter((label) => label !== option.label)
                      : [...selectedLabels, option.label];
                    onChange(next);
                  }}
                />
                <span className="font-bold text-ink-900">{option.label}</span>
                <span className="text-ink-700">{option.content}</span>
              </label>
            );
          })}
        </div>
      ) : question.type === "ESSAY" ? (
        <Textarea
          className="mt-5"
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Nhập bài làm tự luận của bạn"
        />
      ) : (
        <TextInput
          className="mt-5"
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Nhập câu trả lời"
        />
      )}
    </Card>
  );
}
