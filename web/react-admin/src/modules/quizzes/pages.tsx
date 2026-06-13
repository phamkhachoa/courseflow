import { FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  FileQuestion,
  ListChecks,
  Plus,
  Save,
  Search,
  Settings2,
  Trash2,
  XCircle
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  FormField,
  Input,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Textarea,
  Th
} from "@/shared/ui";
import { listCourses } from "@/modules/courses/api";
import type { Course } from "@/modules/courses/types";
import { listUsers, type AdminUser } from "@/modules/identity/api";
import {
  createQuiz,
  createQuizQuestion,
  getAttempt,
  getEffectiveScore,
  getQuiz,
  listCourseQuizzes,
  listQuizAttempts,
  manualGradeAnswer,
  removeQuizQuestion,
  updateQuiz,
  updateQuizQuestion,
  type Quiz,
  type QuizAttempt,
  type QuizQuestion,
  type UpsertQuizQuestionInput
} from "./api";

const choiceTypes = ["MULTIPLE_CHOICE", "TRUE_FALSE", "MULTIPLE_RESPONSE"];
const questionTypes = [
  "MULTIPLE_CHOICE",
  "TRUE_FALSE",
  "MULTIPLE_RESPONSE",
  "SHORT_ANSWER",
  "FILL_BLANK",
  "NUMERICAL",
  "MATCHING",
  "ESSAY"
];
const scoringMethods = ["HIGHEST", "LATEST", "AVERAGE", "FIRST"];
const quizStatuses = ["DRAFT", "PUBLISHED", "ARCHIVED"];
const quizListFilters = ["ALL", ...quizStatuses];
const questionStatuses = ["ACTIVE", "DRAFT", "ARCHIVED"];
const difficultyLevels = ["EASY", "MEDIUM", "HARD"];

const questionTypeLabels: Record<string, string> = {
  MULTIPLE_CHOICE: "Một đáp án",
  TRUE_FALSE: "Đúng / sai",
  MULTIPLE_RESPONSE: "Nhiều đáp án",
  SHORT_ANSWER: "Trả lời ngắn",
  FILL_BLANK: "Điền khuyết",
  NUMERICAL: "Số",
  MATCHING: "Ghép cặp",
  ESSAY: "Tự luận"
};

const scoringMethodLabels: Record<string, string> = {
  HIGHEST: "Lấy điểm cao nhất",
  LATEST: "Lấy lần gần nhất",
  AVERAGE: "Lấy điểm trung bình",
  FIRST: "Lấy lần đầu tiên"
};

const quizStatusLabels: Record<string, string> = {
  DRAFT: "Nháp",
  PUBLISHED: "Đã công khai",
  ARCHIVED: "Lưu trữ"
};

const questionStatusLabels: Record<string, string> = {
  ACTIVE: "Đang dùng",
  DRAFT: "Nháp",
  ARCHIVED: "Lưu trữ"
};

const difficultyLabels: Record<string, string> = {
  EASY: "Dễ",
  MEDIUM: "Trung bình",
  HARD: "Khó"
};

const attemptStatusLabels: Record<string, string> = {
  IN_PROGRESS: "Đang làm",
  SUBMITTED: "Đã nộp",
  GRADED: "Đã chấm",
  PARTIALLY_GRADED: "Chờ chấm tay",
  EXPIRED: "Quá hạn"
};

function labelFrom(labels: Record<string, string>, value?: string, fallback = "—") {
  return value ? labels[value] ?? value : fallback;
}

function questionTypeLabel(value?: string) {
  return labelFrom(questionTypeLabels, value, "Câu hỏi");
}

function scoringMethodLabel(value?: string) {
  return labelFrom(scoringMethodLabels, value, "Lấy điểm cao nhất");
}

function quizStatusLabel(value?: string) {
  return labelFrom(quizStatusLabels, value, "Nháp");
}

function quizListFilterLabel(value: string) {
  if (value === "ALL") return "Tất cả";
  return quizStatusLabel(value);
}

function questionStatusLabel(value?: string) {
  return labelFrom(questionStatusLabels, value, "Đang dùng");
}

function difficultyLabel(value?: string) {
  return labelFrom(difficultyLabels, value, "Trung bình");
}

function attemptStatusLabel(value?: string) {
  return labelFrom(attemptStatusLabels, value, "Chưa rõ");
}

function compactId(value?: string | number | null) {
  if (value === undefined || value === null) return "";
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 8)}...${text.slice(-4)}` : text;
}

function userLabel(userById: Map<string, AdminUser>, userId?: string | number | null) {
  if (userId === undefined || userId === null) return "Học viên";
  const id = String(userId);
  const user = userById.get(id);
  if (user) return user.fullName || user.email;
  return `Học viên ${compactId(id)}`;
}

function attemptLabel(attempt: QuizAttempt, userById: Map<string, AdminUser>) {
  return [
    `Lượt ${attempt.attemptNo ?? compactId(attempt.id)}`,
    userLabel(userById, attempt.studentId),
    attemptStatusLabel(attempt.status)
  ].join(" · ");
}

type QuizFormState = {
  title: string;
  durationMinutes: string;
  attemptsAllowed: string;
  gracePeriodSeconds: string;
  scoringMethod: string;
  status: string;
  randomizeQuestions: boolean;
  randomizeOptions: boolean;
  timeLimitEnforced: boolean;
  showCorrectAnswers: boolean;
  openAt: string;
  closeAt: string;
};

type OptionFormState = {
  label: string;
  content: string;
  correct: boolean;
  weight: string;
  feedback: string;
};

type QuestionFormState = {
  questionId: string;
  type: string;
  stem: string;
  points: string;
  position: string;
  difficulty: string;
  status: string;
  correctAnswer: string;
  feedback: string;
  options: OptionFormState[];
};

const defaultOptions: OptionFormState[] = [
  { label: "A", content: "", correct: true, weight: "1", feedback: "" },
  { label: "B", content: "", correct: false, weight: "0", feedback: "" },
  { label: "C", content: "", correct: false, weight: "0", feedback: "" },
  { label: "D", content: "", correct: false, weight: "0", feedback: "" }
];

function emptyQuizForm(): QuizFormState {
  return {
    title: "",
    durationMinutes: "30",
    attemptsAllowed: "1",
    gracePeriodSeconds: "60",
    scoringMethod: "HIGHEST",
    status: "DRAFT",
    randomizeQuestions: false,
    randomizeOptions: true,
    timeLimitEnforced: true,
    showCorrectAnswers: false,
    openAt: "",
    closeAt: ""
  };
}

function quizToForm(quiz?: Quiz): QuizFormState {
  if (!quiz) return emptyQuizForm();
  return {
    title: quiz.title ?? "",
    durationMinutes: String(quiz.durationMinutes ?? 30),
    attemptsAllowed: String(quiz.attemptsAllowed ?? 1),
    gracePeriodSeconds: String(quiz.gracePeriodSeconds ?? 60),
    scoringMethod: quiz.scoringMethod ?? "HIGHEST",
    status: quiz.status ?? "DRAFT",
    randomizeQuestions: Boolean(quiz.randomizeQuestions),
    randomizeOptions: Boolean(quiz.randomizeOptions),
    timeLimitEnforced: Boolean(quiz.timeLimitEnforced),
    showCorrectAnswers: Boolean(quiz.showCorrectAnswers),
    openAt: toLocalInput(quiz.openAt),
    closeAt: toLocalInput(quiz.closeAt)
  };
}

function emptyQuestionForm(position = 1): QuestionFormState {
  return {
    questionId: "",
    type: "MULTIPLE_CHOICE",
    stem: "",
    points: "1",
    position: String(position),
    difficulty: "MEDIUM",
    status: "ACTIVE",
    correctAnswer: "",
    feedback: "",
    options: defaultOptions.map((option) => ({ ...option }))
  };
}

function questionToForm(question: QuizQuestion): QuestionFormState {
  const options = question.options?.length
    ? question.options.map((option) => ({
        label: option.label ?? "",
        content: option.content ?? "",
        correct: Boolean(option.correct),
        weight: String(option.weight ?? (option.correct ? 1 : 0)),
        feedback: option.feedback ?? ""
      }))
    : defaultOptions.map((option) => ({ ...option }));

  return {
    questionId: question.id,
    type: question.type ?? "MULTIPLE_CHOICE",
    stem: question.stem ?? "",
    points: String(question.points ?? 1),
    position: String(question.position ?? 1),
    difficulty: question.difficulty ?? "MEDIUM",
    status: question.status ?? "ACTIVE",
    correctAnswer: question.correctAnswer ? JSON.stringify(question.correctAnswer, null, 2) : "",
    feedback: question.feedback ?? "",
    options
  };
}

function toLocalInput(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 16);
}

function fromLocalInput(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function toQuizPayload(form: QuizFormState) {
  return {
    title: form.title.trim(),
    openAt: fromLocalInput(form.openAt),
    closeAt: fromLocalInput(form.closeAt),
    durationMinutes: Number(form.durationMinutes),
    attemptsAllowed: Number(form.attemptsAllowed),
    gracePeriodSeconds: Number(form.gracePeriodSeconds),
    scoringMethod: form.scoringMethod,
    status: form.status,
    randomizeQuestions: form.randomizeQuestions,
    randomizeOptions: form.randomizeOptions,
    timeLimitEnforced: form.timeLimitEnforced,
    showCorrectAnswers: form.showCorrectAnswers
  };
}

function parseCorrectAnswer(raw: string) {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
}

function toQuestionPayload(form: QuestionFormState): UpsertQuizQuestionInput {
  const isChoice = choiceTypes.includes(form.type);
  const options = isChoice
    ? form.options
        .map((option) => ({
          label: option.label.trim(),
          content: option.content.trim(),
          correct: option.correct,
          weight: option.weight ? Number(option.weight) : undefined,
          feedback: option.feedback.trim() || undefined
        }))
        .filter((option) => option.label && option.content)
    : undefined;

  return {
    type: form.type,
    stem: form.stem.trim(),
    difficulty: form.difficulty,
    points: Number(form.points),
    position: form.position ? Number(form.position) : undefined,
    status: form.status,
    feedback: form.feedback.trim() || undefined,
    correctAnswer: isChoice ? undefined : parseCorrectAnswer(form.correctAnswer),
    options
  };
}

function questionFormPreview(form: QuestionFormState): QuizQuestion {
  const payload = toQuestionPayload(form);
  return {
    id: form.questionId || "draft-question",
    ...payload,
    options: payload.options?.map((option, index) => ({
      id: `draft-option-${index}`,
      ...option
    }))
  };
}

function formatDateTime(value?: string) {
  if (!value) return "Chưa đặt";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function formatAnswerValue(value: unknown) {
  if (value === undefined || value === null || value === "") return "Chưa cấu hình";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function optionIsCorrect(option: { correct?: boolean }) {
  return Boolean(option.correct);
}

function choiceAnswerSummary(question: QuizQuestion) {
  return (question.options ?? [])
    .filter(optionIsCorrect)
    .map((option) => `${option.label ?? "?"}. ${option.content ?? ""}`.trim());
}

function questionNeedsAnswerWarning(question: QuizQuestion) {
  if (!choiceTypes.includes(question.type ?? "")) return false;
  return choiceAnswerSummary(question).length === 0;
}

function questionIssueMessages(question: QuizQuestion) {
  const issues: string[] = [];
  const type = question.type ?? "";
  const points = Number(question.points ?? 0);

  if (!question.stem?.trim()) issues.push("Thiếu nội dung đề bài");
  if (!Number.isFinite(points) || points <= 0) issues.push("Điểm phải lớn hơn 0");

  if (choiceTypes.includes(type)) {
    const options = question.options ?? [];
    const correctCount = choiceAnswerSummary(question).length;
    if (options.length < 2) issues.push("Cần ít nhất 2 lựa chọn");
    if (type === "MULTIPLE_RESPONSE") {
      if (correctCount === 0) issues.push("Cần ít nhất 1 đáp án đúng");
    } else if (correctCount !== 1) {
      issues.push("Cần đúng 1 đáp án đúng");
    }
  } else if (type !== "ESSAY" && formatAnswerValue(question.correctAnswer) === "Chưa cấu hình") {
    issues.push("Chưa có đáp án chấm tự động");
  }

  return issues;
}

function buildQuizQuality(quiz?: Quiz, attempts: QuizAttempt[] = []) {
  const questions = quiz?.questions ?? [];
  const issueRows = questions.flatMap((question, index) =>
    questionIssueMessages(question).map((message) => ({
      question,
      index,
      message
    }))
  );
  const totalPoints = questions.reduce((sum, question) => sum + Number(question.points ?? 0), 0);
  const manualQueue = attempts.filter((attempt) => attempt.status === "PARTIALLY_GRADED").length;
  const canPublish = Boolean(quiz && questions.length > 0 && issueRows.length === 0);

  return {
    canPublish,
    issueRows,
    totalPoints,
    manualQueue,
    questionCount: questions.length,
    attemptCount: attempts.length
  };
}

function quizPublishBlockedReason(quality: ReturnType<typeof buildQuizQuality>) {
  if (quality.canPublish) return undefined;
  if (quality.questionCount === 0) return "Bài thi cần ít nhất 1 câu hỏi trước khi publish.";
  const firstIssue = quality.issueRows[0];
  if (firstIssue) {
    return `Còn ${quality.issueRows.length} cảnh báo cấu hình. Sửa trước: Câu ${firstIssue.index + 1} - ${firstIssue.message}.`;
  }
  return "Bài thi chưa đủ điều kiện publish.";
}

function quizQuickIssues(quiz: Quiz) {
  return (quiz.questions ?? []).flatMap(questionIssueMessages);
}

function quizReadiness(quiz?: Quiz) {
  if (!quiz) {
    return { value: "DRAFT", label: "Chưa chọn bài thi", detail: "Chọn hoặc tạo bài thi để kiểm tra." };
  }
  const questions = quiz.questions ?? [];
  const issues = quizQuickIssues(quiz);
  if (questions.length === 0) {
    return { value: "DRAFT", label: "Thiếu câu hỏi", detail: "Cần ít nhất 1 câu hỏi trước khi công khai." };
  }
  if (issues.length > 0) {
    return { value: "DRAFT", label: `${issues.length} cảnh báo`, detail: "Cần sửa đề hoặc đáp án trước khi publish." };
  }
  return { value: "READY", label: "Sẵn sàng", detail: "Đề và đáp án đã đủ điều kiện cơ bản." };
}

function quizScheduleSummary(quiz: Quiz) {
  const now = Date.now();
  const openAt = quiz.openAt ? new Date(quiz.openAt).getTime() : 0;
  const closeAt = quiz.closeAt ? new Date(quiz.closeAt).getTime() : 0;

  if (openAt && now < openAt) return `Mở ${formatDateTime(quiz.openAt)}`;
  if (closeAt && now > closeAt) return `Đã đóng ${formatDateTime(quiz.closeAt)}`;
  if (closeAt) return `Đóng ${formatDateTime(quiz.closeAt)}`;
  if (openAt) return `Đã mở ${formatDateTime(quiz.openAt)}`;
  return "Chưa đặt lịch";
}

function choiceHelpText(type: string) {
  if (type === "TRUE_FALSE") return "Câu đúng/sai cần đúng 1 đáp án đúng. Có thể chỉnh nội dung nếu muốn dùng Có/Không.";
  if (type === "MULTIPLE_RESPONSE") return "Câu nhiều đáp án có thể có nhiều lựa chọn đúng. Mỗi đáp án đúng thường có trọng số 1.";
  return "Câu một đáp án cần đúng 1 lựa chọn được đánh dấu đúng.";
}

function AnswerKeyPreview({ question }: { question: QuizQuestion }) {
  const isChoice = choiceTypes.includes(question.type ?? "");
  const answers = isChoice ? choiceAnswerSummary(question) : [formatAnswerValue(question.correctAnswer)];
  const hasWarning = questionNeedsAnswerWarning(question);

  return (
    <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Đáp án chấm điểm</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {answers.length && answers[0] !== "Chưa cấu hình" ? (
              answers.map((answer) => (
                <span key={answer} className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                  {answer}
                </span>
              ))
            ) : (
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">
                Chưa cấu hình
              </span>
            )}
          </div>
        </div>
        {hasWarning && (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">
            <AlertTriangle size={13} /> Thiếu đáp án đúng
          </span>
        )}
      </div>
      {question.feedback && (
        <p className="mt-3 rounded-md bg-white px-3 py-2 text-xs leading-5 text-slate-600">
          <span className="font-semibold text-slate-700">Feedback chung:</span> {question.feedback}
        </p>
      )}
    </div>
  );
}

function OptionPreview({
  option,
  type
}: {
  option: NonNullable<QuizQuestion["options"]>[number];
  type?: string;
}) {
  const correct = optionIsCorrect(option);
  const weight = Number(option.weight ?? (option.correct ? 1 : 0));
  const isMultipleResponse = type === "MULTIPLE_RESPONSE";
  const penalizesWrongSelection = isMultipleResponse && !correct && weight > 0;

  return (
    <div
      className={`rounded-md border px-3 py-2 ${
        correct
          ? "border-emerald-200 bg-emerald-50"
          : penalizesWrongSelection
            ? "border-amber-200 bg-amber-50"
            : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-start gap-2">
        <span
          className={`mt-0.5 inline-flex h-6 min-w-[1.5rem] shrink-0 items-center justify-center rounded-full px-2 text-[11px] font-bold ${
            correct ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"
          }`}
        >
          {option.label ?? "?"}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="break-words text-sm font-semibold text-slate-900">{option.content || "Chưa nhập nội dung"}</p>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                correct
                  ? "bg-emerald-100 text-emerald-700"
                  : penalizesWrongSelection
                    ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-500"
              }`}
            >
              {correct ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
              {correct ? "Đáp án đúng" : penalizesWrongSelection ? "Trừ điểm nếu chọn" : "Không tính điểm"}
            </span>
            {isMultipleResponse && (
              <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-500">
                Trọng số {Number.isFinite(weight) ? weight : 0}
              </span>
            )}
          </div>
          {option.feedback && <p className="mt-1 text-xs leading-5 text-slate-500">{option.feedback}</p>}
        </div>
      </div>
    </div>
  );
}

function answerValues(answer: unknown): string[] {
  if (answer === undefined || answer === null) return [];
  if (Array.isArray(answer)) return answer.map((value) => String(value).trim()).filter(Boolean);
  if (typeof answer === "object") return [formatAnswerValue(answer)];
  const value = String(answer).trim();
  return value ? [value] : [];
}

function formatAttemptAnswer(answer: unknown, question?: QuizQuestion) {
  const values = answerValues(answer);
  if (!values.length) return "Chưa trả lời";
  if (!question?.options?.length) return values.join(", ");

  const optionMap = new Map(
    question.options.map((option) => [String(option.label ?? "").trim(), `${option.label}. ${option.content}`])
  );
  return values.map((value) => optionMap.get(value) ?? value).join(", ");
}

function scoreLabel(value?: number) {
  return value === undefined || value === null ? "—" : value;
}

function AttemptOptionReview({
  option,
  selected
}: {
  option: NonNullable<QuizQuestion["options"]>[number];
  selected: boolean;
}) {
  const correct = optionIsCorrect(option);
  return (
    <div
      className={`rounded-md border px-3 py-2 text-sm ${
        correct
          ? "border-emerald-200 bg-emerald-50"
          : selected
            ? "border-amber-200 bg-amber-50"
            : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex h-6 min-w-[1.5rem] items-center justify-center rounded-full px-2 text-[11px] font-bold ${
            correct ? "bg-emerald-600 text-white" : selected ? "bg-amber-500 text-white" : "bg-slate-200 text-slate-600"
          }`}
        >
          {option.label ?? "?"}
        </span>
        <span className="font-semibold text-slate-900">{option.content}</span>
        {selected && <Badge value="UPLOADED" label="Học viên chọn" />}
        {correct && <Badge value="PUBLISHED" label="Đáp án đúng" />}
      </div>
    </div>
  );
}

export function QuizzesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const qc = useQueryClient();
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const [selectedQuizId, setSelectedQuizId] = useState("");
  const [quizSearch, setQuizSearch] = useState("");
  const [quizStatusFilter, setQuizStatusFilter] = useState("ALL");
  const [createForm, setCreateForm] = useState<QuizFormState>(() => emptyQuizForm());
  const [editForm, setEditForm] = useState<QuizFormState>(() => emptyQuizForm());
  const [questionForm, setQuestionForm] = useState<QuestionFormState>(() => emptyQuestionForm());
  const [attemptId, setAttemptId] = useState("");

  const courses = useQuery({
    queryKey: queryKeys.courses.list("all"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const users = useQuery({
    queryKey: queryKeys.users.list,
    queryFn: listUsers,
    staleTime: 60_000
  });

  const courseRows = (courses.data ?? []) as Course[];
  const userById = useMemo(
    () => new Map((users.data ?? []).map((user) => [String(user.id), user])),
    [users.data]
  );
  const availableCourses = courseRows;
  const requestedCourseId = searchParams.get("courseId") ?? "";

  useEffect(() => {
    if (!availableCourses.length) return;
    if (requestedCourseId && courses.isLoading) return;

    const firstCourseId = availableCourses[0].id;
    const requestedCourseExists = availableCourses.some((course) => course.id === requestedCourseId);

    if (requestedCourseId && requestedCourseExists && selectedCourseId !== requestedCourseId) {
      setSelectedCourseId(requestedCourseId);
      return;
    }

    if (requestedCourseId && !requestedCourseExists) {
      if (selectedCourseId !== firstCourseId) {
        setSelectedCourseId(firstCourseId);
      }
      setSearchParams({ courseId: firstCourseId }, { replace: true });
      return;
    }

    if (!selectedCourseId) {
      setSelectedCourseId(firstCourseId);
      setSearchParams({ courseId: firstCourseId }, { replace: true });
    }
  }, [availableCourses, courses.isLoading, requestedCourseId, selectedCourseId, setSearchParams]);

  const quizzes = useQuery({
    queryKey: queryKeys.quizzes.list(selectedCourseId),
    queryFn: () => listCourseQuizzes(selectedCourseId),
    enabled: Boolean(selectedCourseId)
  });

  const selectedQuiz = useMemo(
    () => quizzes.data?.find((quiz) => quiz.id === selectedQuizId) ?? quizzes.data?.[0],
    [quizzes.data, selectedQuizId]
  );
  const filteredQuizzes = useMemo(() => {
    const normalizedSearch = quizSearch.trim().toLowerCase();
    return (quizzes.data ?? []).filter((quiz) => {
      const matchesStatus = quizStatusFilter === "ALL" || quiz.status === quizStatusFilter;
      const matchesSearch =
        !normalizedSearch ||
        quiz.title.toLowerCase().includes(normalizedSearch) ||
        quiz.id.toLowerCase().includes(normalizedSearch);
      return matchesStatus && matchesSearch;
    });
  }, [quizSearch, quizStatusFilter, quizzes.data]);

  useEffect(() => {
    if (quizzes.data?.length && !quizzes.data.some((quiz) => quiz.id === selectedQuizId)) {
      setSelectedQuizId(quizzes.data[0].id);
    }
    if (quizzes.data?.length === 0) {
      setSelectedQuizId("");
    }
  }, [quizzes.data, selectedQuizId]);

  useEffect(() => {
    setEditForm(quizToForm(selectedQuiz));
    setQuestionForm(emptyQuestionForm((selectedQuiz?.questions?.length ?? 0) + 1));
  }, [selectedQuiz?.id]);

  const attempts = useQuery({
    queryKey: queryKeys.quizzes.attempts(selectedQuiz?.id ?? ""),
    queryFn: () => listQuizAttempts(selectedQuiz?.id ?? ""),
    enabled: Boolean(selectedQuiz?.id)
  });
  const selectedAttempt = attempts.data?.find((attempt) => attempt.id === attemptId);

  useEffect(() => {
    setAttemptId(attempts.data?.[0]?.id ?? "");
  }, [attempts.data]);

  const createMutation = useMutation({
    mutationFn: () => createQuiz({ courseId: selectedCourseId, ...toQuizPayload(createForm) }),
    onSuccess: (quiz) => {
      setCreateForm(emptyQuizForm());
      setSelectedQuizId(quiz.id);
      qc.invalidateQueries({ queryKey: queryKeys.quizzes.list(selectedCourseId) });
    }
  });

  const updateMutation = useMutation({
    mutationFn: () => updateQuiz(selectedQuiz?.id ?? "", toQuizPayload(editForm)),
    onSuccess: (quiz) => {
      qc.invalidateQueries({ queryKey: queryKeys.quizzes.list(selectedCourseId) });
      qc.invalidateQueries({ queryKey: queryKeys.quizzes.detail(quiz.id) });
    }
  });

  const questionMutation = useMutation({
    mutationFn: () => {
      if (!selectedQuiz) throw new Error("Chọn bài thi trước khi lưu câu hỏi");
      const payload = toQuestionPayload(questionForm);
      return questionForm.questionId
        ? updateQuizQuestion(selectedQuiz.id, questionForm.questionId, payload)
        : createQuizQuestion(selectedQuiz.id, payload);
    },
    onSuccess: (quiz) => {
      setSelectedQuizId(quiz.id);
      setQuestionForm(emptyQuestionForm((quiz.questions?.length ?? 0) + 1));
      qc.invalidateQueries({ queryKey: queryKeys.quizzes.list(selectedCourseId) });
      qc.invalidateQueries({ queryKey: queryKeys.quizzes.detail(quiz.id) });
    }
  });

  const removeQuestionMutation = useMutation({
    mutationFn: ({ quizId, questionId }: { quizId: string; questionId: string }) => removeQuizQuestion(quizId, questionId),
    onSuccess: (quiz, variables) => {
      setSelectedQuizId(quiz.id);
      if (questionForm.questionId === variables.questionId) {
        setQuestionForm(emptyQuestionForm((quiz.questions?.length ?? 0) + 1));
      }
      qc.invalidateQueries({ queryKey: queryKeys.quizzes.list(selectedCourseId) });
      qc.invalidateQueries({ queryKey: queryKeys.quizzes.detail(quiz.id) });
    }
  });

  function goAttempt(e: FormEvent) {
    e.preventDefault();
    if (attemptId.trim()) navigate(`/quizzes/${attemptId.trim()}/detail`);
  }

  const currentCourse = availableCourses.find((course) => course.id === selectedCourseId);
  const quizCount = quizzes.data?.length ?? 0;
  const questionCount = selectedQuiz?.questions?.length ?? 0;
  const hasQuizAttempts = (attempts.data?.length ?? 0) > 0;
  const readiness = quizReadiness(selectedQuiz);
  const quality = useMemo(
    () => buildQuizQuality(selectedQuiz, attempts.data ?? []),
    [selectedQuiz, attempts.data]
  );
  const publishBlockedReason = quizPublishBlockedReason(quality);
  const publishPolicyBlocked = editForm.status === "PUBLISHED" && !quality.canPublish;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản lý bài thi"
        description="Tạo bài thi theo từng khóa học, quản lý câu hỏi, đáp án, chính sách làm bài và theo dõi lượt nộp."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link to="score">
              <Button variant="secondary">
                <Search size={16} /> Điểm hiệu quả
              </Button>
            </Link>
          </div>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <Card>
            <CardHeader
              title="Khóa học"
              subtitle={courses.isError ? "Không tải được catalog khóa học" : "Chọn khóa học để quản lý bài thi"}
            />
            <div className="space-y-4 p-4">
              <FormField label="Khóa học" htmlFor="course-select">
                <Select
                  id="course-select"
                  value={selectedCourseId}
                  onChange={(event) => {
                    const nextCourseId = event.target.value;
                    setSelectedCourseId(nextCourseId);
                    setSelectedQuizId("");
                    setSearchParams({ courseId: nextCourseId });
                  }}
                >
                  <option value="">Chọn khóa học</option>
                  {availableCourses.map((course: Course) => (
                    <option key={course.id} value={course.id}>
                      {course.code ? `${course.code} - ${course.title}` : course.title}
                    </option>
                  ))}
                </Select>
              </FormField>
              {courses.isError && <ErrorState error={courses.error} />}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <Metric label="Bài thi" value={quizCount} />
                <Metric label="Câu hỏi" value={questionCount} />
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Danh sách bài thi"
              actions={<Badge value={selectedQuiz?.status} label={quizStatusLabel(selectedQuiz?.status)} />}
              subtitle={currentCourse?.title}
            />
            {quizzes.isLoading && <Spinner />}
            {quizzes.isError && <ErrorState error={quizzes.error} />}
            {quizzes.data?.length === 0 && <EmptyState message="Khóa học này chưa có bài thi" />}
            {quizzes.data && quizzes.data.length > 0 && (
              <div className="space-y-3 border-b border-slate-100 p-3">
                <FormField label="Tìm bài thi" htmlFor="quiz-search">
                  <Input
                    id="quiz-search"
                    value={quizSearch}
                    onChange={(event) => setQuizSearch(event.target.value)}
                    placeholder="Tên bài thi"
                  />
                </FormField>
                <div className="flex flex-wrap gap-2">
                  {quizListFilters.map((status) => (
                    <Button
                      key={status}
                      type="button"
                      size="sm"
                      variant={quizStatusFilter === status ? "primary" : "secondary"}
                      onClick={() => setQuizStatusFilter(status)}
                    >
                      {quizListFilterLabel(status)}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            <div className="max-h-[560px] overflow-y-auto p-3">
              {quizzes.data && quizzes.data.length > 0 && filteredQuizzes.length === 0 && (
                <EmptyState message="Không có bài thi khớp bộ lọc." />
              )}
              {filteredQuizzes.map((quiz) => {
                const quickReadiness = quizReadiness(quiz);
                const active = selectedQuiz?.id === quiz.id;
                return (
                  <button
                    key={quiz.id}
                    type="button"
                    onClick={() => setSelectedQuizId(quiz.id)}
                    className={`mb-2 w-full rounded-md border p-3 text-left transition ${
                      active
                        ? "border-brand-300 bg-brand-50 shadow-sm"
                        : "border-slate-200 bg-white hover:border-brand-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-slate-900">{quiz.title}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {(quiz.questions?.length ?? 0)} câu · {quiz.durationMinutes ?? "—"} phút · {quiz.attemptsAllowed ?? 1} lần
                          </p>
                        </div>
                        <Badge value={quiz.status} label={quizStatusLabel(quiz.status)} />
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge value={quickReadiness.value} label={quickReadiness.label} />
                        <span className="text-xs font-medium text-slate-500">{quizScheduleSummary(quiz)}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Mở nhanh lượt làm"
              subtitle={selectedAttempt ? attemptLabel(selectedAttempt, userById) : "Chọn một lượt làm của bài thi đang mở"}
            />
            <form className="space-y-3 p-4" onSubmit={goAttempt}>
              <FormField label="Lượt làm" htmlFor="attempt-id">
                <Select id="attempt-id" value={attemptId} onChange={(e) => setAttemptId(e.target.value)} required>
                  <option value="">Chọn lượt làm</option>
                  {(attempts.data ?? []).map((attempt) => (
                    <option key={attempt.id} value={attempt.id}>
                      {attemptLabel(attempt, userById)}
                    </option>
                  ))}
                  {attemptId && !selectedAttempt && <option value={attemptId}>Attempt {compactId(attemptId)}</option>}
                </Select>
              </FormField>
              <div>
                <Button type="submit" variant="secondary" disabled={!attemptId}>
                  <Search size={16} /> Xem
                </Button>
              </div>
            </form>
          </Card>
        </aside>

        <main className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-4">
            <SummaryCard icon={<ClipboardCheck size={18} />} label="Bài thi đang chọn" value={selectedQuiz?.title ?? "Chưa có"} />
            <SummaryCard icon={<ListChecks size={18} />} label="Tổng câu hỏi" value={questionCount} />
            <SummaryCard icon={<FileQuestion size={18} />} label="Điểm tối đa" value={quality.totalPoints} />
            <SummaryCard icon={<CheckCircle2 size={18} />} label="Lượt nộp" value={attempts.data?.length ?? 0} />
          </div>

          {selectedQuiz && (
            <Card className="overflow-hidden">
              <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_360px]">
                <div className="space-y-3 p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge value={selectedQuiz.status} label={quizStatusLabel(selectedQuiz.status)} />
                    <Badge value={readiness.value} label={readiness.label} />
                    <span className="text-xs font-semibold text-slate-500">{quizScheduleSummary(selectedQuiz)}</span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-950">{selectedQuiz.title}</h2>
                    <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                      {readiness.detail} Bài thi thuộc khóa {currentCourse?.code ?? currentCourse?.title ?? selectedCourseId}.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                    <span className="rounded-md bg-slate-100 px-2 py-1">ID: {compactId(selectedQuiz.id)}</span>
                    <span className="rounded-md bg-slate-100 px-2 py-1">{selectedQuiz.durationMinutes ?? "—"} phút</span>
                    <span className="rounded-md bg-slate-100 px-2 py-1">{selectedQuiz.attemptsAllowed ?? 1} lần làm</span>
                    <span className="rounded-md bg-slate-100 px-2 py-1">{scoringMethodLabel(selectedQuiz.scoringMethod)}</span>
                  </div>
                </div>
                <div className="border-t border-slate-100 bg-slate-50 p-5 lg:border-l lg:border-t-0">
                  <p className="text-xs font-bold uppercase text-slate-400">Thao tác nhanh</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => document.getElementById("quiz-policy-editor")?.scrollIntoView({ behavior: "smooth", block: "start" })}
                    >
                      <Settings2 size={16} /> Chính sách
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => document.getElementById("quiz-question-builder")?.scrollIntoView({ behavior: "smooth", block: "start" })}
                    >
                      <FileQuestion size={16} /> Thêm câu hỏi
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )}

          <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_420px]">
            <section className="space-y-4">
              <Card>
                <CardHeader
                  title="Tạo bài thi mới"
                  subtitle="Bài thi được gắn trực tiếp với khóa học đang chọn"
                  actions={<Plus size={18} className="text-brand-600" />}
                />
                <QuizPolicyForm
                  form={createForm}
                  setForm={setCreateForm}
                  submitLabel={createMutation.isPending ? "Đang tạo" : "Tạo bài thi"}
                  publishDisabled
                  publishDisabledReason="Tạo bài thi ở trạng thái DRAFT, thêm câu hỏi rồi publish."
                  onSubmit={(event) => {
                    event.preventDefault();
                    createMutation.mutate();
                  }}
                />
                {createMutation.isError && <ErrorState error={createMutation.error} />}
              </Card>

              <Card id="quiz-policy-editor">
                <CardHeader
                  title={selectedQuiz ? "Thiết lập bài thi" : "Chưa chọn bài thi"}
                  subtitle={selectedQuiz ? `ID ${compactId(selectedQuiz.id)}` : "Tạo bài thi hoặc chọn từ danh sách bên trái"}
                  actions={selectedQuiz && <Badge value={selectedQuiz.status} label={quizStatusLabel(selectedQuiz.status)} />}
                />
                {selectedQuiz ? (
                  <>
                    <QuizPolicyForm
                      form={editForm}
                      setForm={setEditForm}
                      submitLabel={updateMutation.isPending ? "Đang lưu" : "Lưu chính sách"}
                      publishDisabled={!quality.canPublish}
                      publishDisabledReason={publishBlockedReason}
                      submitDisabled={publishPolicyBlocked}
                      submitDisabledReason={publishBlockedReason}
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (publishPolicyBlocked) return;
                        updateMutation.mutate();
                      }}
                    />
                    {updateMutation.isError && <ErrorState error={updateMutation.error} />}
                  </>
                ) : (
                  <EmptyState message="Chưa có bài thi để chỉnh sửa" />
                )}
              </Card>

              <Card id="quiz-question-builder">
                <CardHeader
                  title={questionForm.questionId ? "Sửa câu hỏi" : "Thêm câu hỏi"}
                  subtitle="Quản lý đề bài, đáp án đúng, trọng số và feedback cho từng lựa chọn"
                  actions={<FileQuestion size={18} className="text-brand-600" />}
                />
                {selectedQuiz ? (
                  <QuestionBuilderForm
                    form={questionForm}
                    setForm={setQuestionForm}
                    submitLabel={questionMutation.isPending ? "Đang lưu" : questionForm.questionId ? "Cập nhật câu hỏi" : "Thêm câu hỏi"}
                    onCancelEdit={() => setQuestionForm(emptyQuestionForm((selectedQuiz.questions?.length ?? 0) + 1))}
                    onSubmit={(event) => {
                      event.preventDefault();
                      questionMutation.mutate();
                    }}
                  />
                ) : (
                  <EmptyState message="Chọn bài thi trước khi thêm câu hỏi" />
                )}
                {questionMutation.isError && <ErrorState error={questionMutation.error} />}
              </Card>
            </section>

            <aside className="space-y-4">
              <QuizQualityCard quiz={selectedQuiz} quality={quality} />

              <Card>
                <CardHeader title="Câu hỏi trong bài thi" subtitle="Bấm sửa để nạp lại vào form bên trái" />
                {!selectedQuiz && <EmptyState message="Chưa chọn bài thi" />}
                {selectedQuiz?.questions?.length === 0 && <EmptyState message="Bài thi chưa có câu hỏi" />}
                {removeQuestionMutation.isError && <ErrorState error={removeQuestionMutation.error} />}
                <div className="space-y-3 p-4">
                  {selectedQuiz?.questions?.map((question, index) => (
                    <article id={`quiz-question-${question.id}`} key={question.id} className="scroll-mt-24 rounded-md border border-slate-200 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase text-slate-400">Câu {index + 1}</p>
                          <h4 className="mt-1 font-semibold text-slate-900">{question.stem}</h4>
                          <p className="mt-1 text-xs text-slate-500">
                            {questionTypeLabel(question.type)} · {difficultyLabel(question.difficulty)} · {question.points ?? 0} điểm · vị trí {question.position ?? index + 1}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-wrap justify-end gap-2">
                          <Button type="button" size="sm" variant="secondary" onClick={() => setQuestionForm(questionToForm(question))}>
                            <Settings2 size={14} /> Sửa
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="danger"
                            disabled={removeQuestionMutation.isPending || hasQuizAttempts}
                            title={hasQuizAttempts ? "Không thể gỡ câu hỏi khi bài thi đã có lượt làm" : "Gỡ khỏi bài thi"}
                            onClick={() => {
                              if (!selectedQuiz) return;
                              if (window.confirm("Gỡ câu hỏi này khỏi bài thi? Câu hỏi vẫn được giữ trong ngân hàng câu hỏi.")) {
                                removeQuestionMutation.mutate({ quizId: selectedQuiz.id, questionId: question.id });
                              }
                            }}
                          >
                            <Trash2 size={14} /> Gỡ
                          </Button>
                        </div>
                      </div>
                      {question.options?.length ? (
                        <div className="mt-3 space-y-2">
                          {question.options.map((option) => (
                            <OptionPreview key={option.id} option={option} type={question.type} />
                          ))}
                        </div>
                      ) : null}
                      <AnswerKeyPreview question={question} />
                    </article>
                  ))}
                </div>
              </Card>

              <Card>
                <CardHeader title="Lịch & lượt nộp" subtitle="Theo dõi nhanh các attempt gần nhất" />
                {selectedQuiz && (
                  <dl className="grid grid-cols-[120px_1fr] gap-y-3 border-b border-slate-100 p-4 text-sm">
                    <dt className="text-slate-500">Mở bài</dt>
                    <dd>{formatDateTime(selectedQuiz.openAt)}</dd>
                    <dt className="text-slate-500">Đóng bài</dt>
                    <dd>{formatDateTime(selectedQuiz.closeAt)}</dd>
                    <dt className="text-slate-500">Tính điểm</dt>
                    <dd>{scoringMethodLabel(selectedQuiz.scoringMethod)}</dd>
                  </dl>
                )}
                {attempts.isLoading && <Spinner />}
                {attempts.isError && <ErrorState error={attempts.error} />}
                {attempts.data?.length === 0 && <EmptyState message="Chưa có attempt" />}
                {attempts.data?.length ? (
                  <Table>
                    <thead>
                      <tr>
                        <Th>#</Th>
                        <Th>Học viên</Th>
                        <Th>Trạng thái</Th>
                        <Th>Điểm</Th>
                        <Th />
                      </tr>
                    </thead>
                    <tbody>
                      {attempts.data.slice(0, 8).map((attempt) => (
                        <tr key={attempt.id}>
                          <Td>{attempt.attemptNo ?? "—"}</Td>
                          <Td>
                            <div className="font-medium text-slate-900">{userLabel(userById, attempt.studentId)}</div>
                            {attempt.studentId && <div className="mt-1 text-xs text-slate-500">ID {compactId(attempt.studentId)}</div>}
                          </Td>
                          <Td><Badge value={attempt.status} label={attemptStatusLabel(attempt.status)} /></Td>
                          <Td>{attempt.score ?? "—"}</Td>
                          <Td>
                            <Link to={`/quizzes/${attempt.id}/detail`} className="text-sm font-semibold text-brand-600 hover:text-brand-700">
                              Xem
                            </Link>
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                ) : null}
              </Card>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-950">{value}</p>
    </div>
  );
}

function SummaryCard({ icon, label, value }: { icon: ReactNode; label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <span className="rounded-md bg-brand-50 p-2 text-brand-700">{icon}</span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase text-slate-400">{label}</p>
          <p className="truncate text-lg font-bold text-slate-950">{value}</p>
        </div>
      </div>
    </Card>
  );
}

function QuizQualityCard({
  quiz,
  quality
}: {
  quiz?: Quiz;
  quality: ReturnType<typeof buildQuizQuality>;
}) {
  if (!quiz) {
    return (
      <Card>
        <CardHeader title="Bảng kiểm chất lượng" subtitle="Chọn bài thi để kiểm tra điều kiện công khai" />
        <EmptyState message="Chưa chọn bài thi." />
      </Card>
    );
  }

  const publishLabel = quality.canPublish ? "Sẵn sàng công khai" : "Cần bổ sung";
  const publishValue = quality.canPublish ? "READY" : "DRAFT";

  return (
    <Card>
      <CardHeader
        title="Bảng kiểm chất lượng"
        subtitle="Kiểm tra nhanh đề, đáp án và lượt chấm trước khi công khai"
        actions={<Badge value={publishValue} label={publishLabel} />}
      />
      <div className="space-y-4 p-4">
        <div className="grid grid-cols-3 gap-2 text-sm">
          <Metric label="Câu hỏi" value={quality.questionCount} />
          <Metric label="Điểm" value={quality.totalPoints} />
          <Metric label="Chờ chấm" value={quality.manualQueue} />
        </div>

        {quality.issueRows.length === 0 ? (
          <div className="rounded-md border border-emerald-100 bg-emerald-50 p-3 text-sm leading-6 text-emerald-700">
            Đề đã có cấu hình đáp án cơ bản. Admin vẫn nên xem lại nội dung từng câu trước khi công khai.
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              {quality.issueRows.length} điểm cần xử lý
            </p>
            {quality.issueRows.slice(0, 6).map(({ question, index, message }) => (
              <button
                key={`${question.id}-${message}`}
                type="button"
                className="w-full rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-left text-xs leading-5 text-amber-800"
                onClick={() => document.getElementById(`quiz-question-${question.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
              >
                <span className="font-bold">Câu {index + 1}:</span> {message}
              </button>
            ))}
            {quality.issueRows.length > 6 && (
              <p className="text-xs text-slate-500">Còn {quality.issueRows.length - 6} cảnh báo khác trong danh sách câu hỏi.</p>
            )}
          </div>
        )}

        {quiz.status === "PUBLISHED" && quality.issueRows.length > 0 && (
          <div className="rounded-md border border-red-100 bg-red-50 p-3 text-sm leading-6 text-red-700">
            Bài thi đang công khai nhưng còn cảnh báo cấu hình. Nên chuyển về nháp hoặc sửa ngay để tránh học viên gặp đề lỗi.
          </div>
        )}
      </div>
    </Card>
  );
}

function QuizPolicyForm({
  form,
  setForm,
  submitLabel,
  publishDisabled = false,
  publishDisabledReason,
  submitDisabled = false,
  submitDisabledReason,
  onSubmit
}: {
  form: QuizFormState;
  setForm: (next: QuizFormState) => void;
  submitLabel: string;
  publishDisabled?: boolean;
  publishDisabledReason?: string;
  submitDisabled?: boolean;
  submitDisabledReason?: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const patch = (next: Partial<QuizFormState>) => setForm({ ...form, ...next });
  return (
    <form className="space-y-4 p-4" onSubmit={onSubmit}>
      <FormField label="Tên bài thi" htmlFor={`${submitLabel}-title`}>
        <Input
          id={`${submitLabel}-title`}
          value={form.title}
          onChange={(event) => patch({ title: event.target.value })}
          placeholder="VD: Midterm - Spring Boot fundamentals"
          required
        />
      </FormField>

      <div className="grid gap-4 md:grid-cols-3">
        <FormField label="Thời lượng (phút)">
          <Input
            type="number"
            min={1}
            value={form.durationMinutes}
            onChange={(event) => patch({ durationMinutes: event.target.value })}
            required
          />
        </FormField>
        <FormField label="Số lần làm">
          <Input
            type="number"
            min={1}
            value={form.attemptsAllowed}
            onChange={(event) => patch({ attemptsAllowed: event.target.value })}
            required
          />
        </FormField>
        <FormField label="Grace period (giây)">
          <Input
            type="number"
            min={0}
            value={form.gracePeriodSeconds}
            onChange={(event) => patch({ gracePeriodSeconds: event.target.value })}
            required
          />
        </FormField>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <FormField label="Cách tính điểm">
          <Select value={form.scoringMethod} onChange={(event) => patch({ scoringMethod: event.target.value })}>
            {scoringMethods.map((method) => <option key={method} value={method}>{scoringMethodLabel(method)}</option>)}
          </Select>
        </FormField>
        <FormField label="Trạng thái" hint={publishDisabled ? publishDisabledReason : undefined}>
          <Select value={form.status} onChange={(event) => patch({ status: event.target.value })}>
            {quizStatuses.map((status) => (
              <option key={status} value={status} disabled={status === "PUBLISHED" && publishDisabled}>
                {quizStatusLabel(status)}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Công bố đáp án">
          <Select
            value={form.showCorrectAnswers ? "true" : "false"}
            onChange={(event) => patch({ showCorrectAnswers: event.target.value === "true" })}
          >
            <option value="false">Ẩn đáp án</option>
            <option value="true">Hiện đáp án sau khi nộp</option>
          </Select>
        </FormField>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="Mở bài lúc">
          <Input type="datetime-local" value={form.openAt} onChange={(event) => patch({ openAt: event.target.value })} />
        </FormField>
        <FormField label="Đóng bài lúc">
          <Input type="datetime-local" value={form.closeAt} onChange={(event) => patch({ closeAt: event.target.value })} />
        </FormField>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <ToggleField
          label="Xáo trộn câu hỏi"
          checked={form.randomizeQuestions}
          onChange={(checked) => patch({ randomizeQuestions: checked })}
        />
        <ToggleField
          label="Xáo trộn đáp án"
          checked={form.randomizeOptions}
          onChange={(checked) => patch({ randomizeOptions: checked })}
        />
        <ToggleField
          label="Giới hạn thời gian"
          checked={form.timeLimitEnforced}
          onChange={(checked) => patch({ timeLimitEnforced: checked })}
        />
      </div>

      {submitDisabled && submitDisabledReason && (
        <p className="rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">
          {submitDisabledReason}
        </p>
      )}

      <Button type="submit" disabled={submitDisabled}>
        <Save size={16} /> {submitLabel}
      </Button>
    </form>
  );
}

function ToggleField({
  label,
  checked,
  onChange
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
      <span>{label}</span>
      <input
        type="checkbox"
        className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  );
}

function QuestionBuilderForm({
  form,
  setForm,
  submitLabel,
  onCancelEdit,
  onSubmit
}: {
  form: QuestionFormState;
  setForm: (next: QuestionFormState) => void;
  submitLabel: string;
  onCancelEdit: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const isChoice = choiceTypes.includes(form.type);
  const previewQuestion = questionFormPreview(form);
  const previewIssues = questionIssueMessages(previewQuestion);
  const filledOptionCount = form.options.filter((option) => option.label.trim() && option.content.trim()).length;
  const correctOptionCount = form.options.filter((option) => option.correct).length;
  const patch = (next: Partial<QuestionFormState>) => setForm({ ...form, ...next });
  const setType = (type: string) => {
    if (type === "TRUE_FALSE") {
      patch({
        type,
        options: [
          { label: "TRUE", content: "Đúng", correct: true, weight: "1", feedback: "" },
          { label: "FALSE", content: "Sai", correct: false, weight: "0", feedback: "" }
        ]
      });
      return;
    }
    if (choiceTypes.includes(type) && !choiceTypes.includes(form.type)) {
      patch({ type, options: defaultOptions.map((option) => ({ ...option })) });
      return;
    }
    patch({ type });
  };
  const setOption = (index: number, next: Partial<OptionFormState>) => {
    const isSingleChoiceCorrect = next.correct === true && form.type !== "MULTIPLE_RESPONSE";
    const options = form.options.map((option, optionIndex) => {
      if (isSingleChoiceCorrect && optionIndex !== index) {
        return { ...option, correct: false, weight: "0" };
      }
      if (optionIndex !== index) return option;
      return { ...option, ...next };
    });
    setForm({ ...form, options });
  };
  const removeOption = (index: number) => {
    if (form.options.length <= 2) return;
    const options = form.options
      .filter((_, optionIndex) => optionIndex !== index)
      .map((option, optionIndex) => ({
        ...option,
        label: String.fromCharCode(65 + optionIndex)
      }));
    if (!options.some((option) => option.correct)) {
      options[0] = { ...options[0], correct: true, weight: "1" };
    }
    setForm({ ...form, options });
  };

  return (
    <form className="space-y-4 p-4" onSubmit={onSubmit}>
      <div className="grid gap-4 md:grid-cols-5">
        <FormField label="Loại câu hỏi">
          <Select value={form.type} onChange={(event) => setType(event.target.value)}>
            {questionTypes.map((type) => <option key={type} value={type}>{questionTypeLabel(type)}</option>)}
          </Select>
        </FormField>
        <FormField label="Điểm">
          <Input type="number" min={0.1} step="0.1" value={form.points} onChange={(event) => patch({ points: event.target.value })} />
        </FormField>
        <FormField label="Độ khó">
          <Select value={form.difficulty} onChange={(event) => patch({ difficulty: event.target.value })}>
            {difficultyLevels.map((level) => <option key={level} value={level}>{difficultyLabel(level)}</option>)}
          </Select>
        </FormField>
        <FormField label="Vị trí">
          <Input type="number" min={1} value={form.position} onChange={(event) => patch({ position: event.target.value })} />
        </FormField>
        <FormField label="Trạng thái">
          <Select value={form.status} onChange={(event) => patch({ status: event.target.value })}>
            {questionStatuses.map((status) => <option key={status} value={status}>{questionStatusLabel(status)}</option>)}
          </Select>
        </FormField>
      </div>

      <FormField label="Đề bài">
        <Textarea
          value={form.stem}
          onChange={(event) => patch({ stem: event.target.value })}
          placeholder="Nhập nội dung câu hỏi rõ ràng, có đủ ngữ cảnh cho học viên"
          required
        />
      </FormField>

      <div
        className={`rounded-md border p-3 ${
          previewIssues.length === 0
            ? "border-emerald-100 bg-emerald-50 text-emerald-800"
            : "border-amber-100 bg-amber-50 text-amber-800"
        }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {previewIssues.length === 0 ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <p className="text-sm font-bold">
              {previewIssues.length === 0 ? "Câu hỏi đã đủ cấu hình cơ bản" : "Câu hỏi còn cần xử lý"}
            </p>
          </div>
          {isChoice && (
            <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold">
              {filledOptionCount} lựa chọn · {correctOptionCount} đúng
            </span>
          )}
        </div>
        {previewIssues.length > 0 && (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5">
            {previewIssues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}
      </div>

      {isChoice ? (
        <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-700">Đáp án lựa chọn</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">{choiceHelpText(form.type)}</p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={form.type === "TRUE_FALSE"}
              title={form.type === "TRUE_FALSE" ? "Câu đúng/sai chỉ có hai lựa chọn" : "Thêm đáp án"}
              onClick={() =>
                patch({
                  options: [
                    ...form.options,
                    { label: String.fromCharCode(65 + form.options.length), content: "", correct: false, weight: "0", feedback: "" }
                  ]
                })
              }
            >
              <Plus size={14} /> Thêm đáp án
            </Button>
          </div>
          {form.options.map((option, index) => (
            <div key={`${option.label}-${index}`} className="grid gap-3 rounded-md border border-white bg-white p-3 md:grid-cols-[80px_minmax(0,1fr)_90px_90px_auto]">
              <FormField label="Nhãn">
                <Input value={option.label} onChange={(event) => setOption(index, { label: event.target.value.toUpperCase() })} required />
              </FormField>
              <FormField label="Nội dung đáp án">
                <Input value={option.content} onChange={(event) => setOption(index, { content: event.target.value })} required />
              </FormField>
              <FormField label="Trọng số">
                <Input type="number" step="0.01" value={option.weight} onChange={(event) => setOption(index, { weight: event.target.value })} />
              </FormField>
              <ToggleField label="Đúng" checked={option.correct} onChange={(checked) => setOption(index, { correct: checked, weight: checked ? "1" : "0" })} />
              <div className="flex items-end">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-10 text-red-600 hover:bg-red-50"
                  disabled={form.options.length <= 2}
                  title="Bỏ đáp án"
                  aria-label={`Bỏ đáp án ${option.label || index + 1}`}
                  onClick={() => removeOption(index)}
                >
                  <Trash2 size={15} />
                </Button>
              </div>
              <div className="md:col-span-5">
                <FormField label="Feedback đáp án">
                  <Input value={option.feedback} onChange={(event) => setOption(index, { feedback: event.target.value })} placeholder="Giải thích ngắn cho lựa chọn này" />
                </FormField>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <FormField label="Đáp án đúng" hint='Có thể nhập text thường hoặc JSON, ví dụ ["dependency injection", "DI"]'>
          <Textarea
            value={form.correctAnswer}
            onChange={(event) => patch({ correctAnswer: event.target.value })}
            placeholder='["answer 1", "answer 2"]'
          />
        </FormField>
      )}

      <FormField label="Feedback chung">
        <Textarea
          value={form.feedback}
          onChange={(event) => patch({ feedback: event.target.value })}
          placeholder="Giải thích hiển thị cho admin/giảng viên sau khi chấm"
        />
      </FormField>

      <div className="flex flex-wrap gap-2">
        <Button type="submit">
          <Save size={16} /> {submitLabel}
        </Button>
        {form.questionId && (
          <Button type="button" variant="secondary" onClick={onCancelEdit}>
            Hủy sửa
          </Button>
        )}
      </div>
    </form>
  );
}

export function AttemptDetailPage() {
  const { attemptId = "" } = useParams();
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.quizzes.attempt(attemptId),
    queryFn: () => getAttempt(attemptId),
    enabled: Boolean(attemptId)
  });
  const quiz = useQuery({
    queryKey: queryKeys.quizzes.detail(data?.attempt.quizId ?? ""),
    queryFn: () => getQuiz(data?.attempt.quizId ?? ""),
    enabled: Boolean(data?.attempt.quizId)
  });
  const questionMap = useMemo(
    () => new Map((quiz.data?.questions ?? []).map((question) => [question.id, question])),
    [quiz.data?.questions]
  );

  const [openForms, setOpenForms] = useState<Record<string, boolean>>({});
  const [gradeForms, setGradeForms] = useState<Record<string, { score: string; feedback: string }>>({});

  const grade = useMutation({
    mutationFn: ({ questionId, form }: { questionId: string; form: { score: string; feedback: string } }) =>
      manualGradeAnswer(attemptId, questionId, {
        score: Number(form.score),
        feedback: form.feedback || undefined
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.quizzes.attempt(attemptId) })
  });

  const getForm = (qid: string, answer?: { manualScore?: number; totalScore?: number; manualFeedback?: string }) =>
    gradeForms[qid] ?? {
      score: answer?.manualScore !== undefined ? String(answer.manualScore) : "",
      feedback: answer?.manualFeedback ?? ""
    };
  const setForm = (qid: string, patch: Partial<{ score: string; feedback: string }>) =>
    setGradeForms((prev) => ({ ...prev, [qid]: { ...getForm(qid), ...patch } }));
  const toggleForm = (qid: string) => setOpenForms((prev) => ({ ...prev, [qid]: !prev[qid] }));

  if (isLoading) return <Spinner />;
  if (isError) return <ErrorState error={error} />;
  if (!data) return null;

  const { attempt, answers } = data;
  const sortedAnswers = answers
    .slice()
    .sort((left, right) => {
      const leftQuestion = questionMap.get(left.questionId);
      const rightQuestion = questionMap.get(right.questionId);
      return (leftQuestion?.position ?? 9999) - (rightQuestion?.position ?? 9999);
    });

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader
        title="Chấm bài thi"
        description="Xem câu hỏi, câu trả lời của học viên, đáp án đúng và chấm thủ công khi cần."
      />
      <Card className="mb-4">
        <CardHeader title="Thông tin" />
        <dl className="grid gap-4 p-4 text-sm md:grid-cols-4">
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-xs font-semibold uppercase text-slate-400">Bài thi</dt>
            <dd className="mt-1 font-bold text-slate-900">{quiz.data?.title ?? attempt.quizId}</dd>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-xs font-semibold uppercase text-slate-400">Lượt làm</dt>
            <dd className="mt-1 font-bold text-slate-900">#{attempt.attemptNo ?? "—"}</dd>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-xs font-semibold uppercase text-slate-400">Trạng thái</dt>
            <dd className="mt-1"><Badge value={attempt.status} label={attemptStatusLabel(attempt.status)} /></dd>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <dt className="text-xs font-semibold uppercase text-slate-400">Điểm tổng</dt>
            <dd className="mt-1 text-2xl font-bold text-brand-600">{attempt.score ?? "—"}</dd>
          </div>
        </dl>
        {quiz.isLoading && <Spinner label="Đang tải đề thi" />}
        {quiz.isError && <ErrorState error={quiz.error} />}
      </Card>

      <div className="space-y-4">
        {sortedAnswers.length === 0 && (
          <Card>
            <EmptyState message="Lượt làm này chưa có câu trả lời." />
          </Card>
        )}
        {sortedAnswers.map((ans, index) => {
          const question = questionMap.get(ans.questionId);
          const selectedValues = answerValues(ans.answer);
          const correctAnswers = question
            ? choiceTypes.includes(question.type ?? "")
              ? choiceAnswerSummary(question)
              : [formatAnswerValue(question.correctAnswer)]
            : [];
          const f = getForm(ans.questionId, ans);
          const open = openForms[ans.questionId] ?? false;

          return (
            <Card key={ans.questionId}>
              <CardHeader
                title={
                  <div>
                    <p className="text-xs font-semibold uppercase text-slate-400">Câu {index + 1}</p>
                    <h3 className="mt-1 text-base font-bold text-slate-900">
                      {question?.stem ?? ans.questionId}
                    </h3>
                  </div>
                }
                subtitle={question ? `${questionTypeLabel(question.type)} · ${question.points ?? 0} điểm` : "Không tìm thấy metadata câu hỏi"}
                actions={<Badge value={ans.totalScore === question?.points ? "PUBLISHED" : "DRAFT"} label={`${scoreLabel(ans.totalScore)} điểm`} />}
              />
              <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-4">
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Câu trả lời học viên</p>
                    <p className="mt-2 text-base font-bold text-slate-900">
                      {formatAttemptAnswer(ans.answer, question)}
                    </p>
                  </div>

                  {question?.options?.length ? (
                    <div className="space-y-2">
                      {question.options.map((option) => (
                        <AttemptOptionReview
                          key={option.id}
                          option={option}
                          selected={selectedValues.includes(String(option.label ?? "").trim())}
                        />
                      ))}
                    </div>
                  ) : null}

                  {correctAnswers.length > 0 && correctAnswers[0] !== "Chưa cấu hình" && (
                    <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Đáp án đúng</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {correctAnswers.map((answer) => (
                          <span key={answer} className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-emerald-700">
                            {answer}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <aside className="space-y-3">
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-md bg-slate-50 p-3">
                      <dt className="text-xs font-semibold uppercase text-slate-400">Tự động</dt>
                      <dd className="mt-1 font-bold text-slate-900">{scoreLabel(ans.autoScore)}</dd>
                    </div>
                    <div className="rounded-md bg-slate-50 p-3">
                      <dt className="text-xs font-semibold uppercase text-slate-400">Thủ công</dt>
                      <dd className="mt-1 font-bold text-slate-900">{scoreLabel(ans.manualScore)}</dd>
                    </div>
                    <div className="rounded-md bg-slate-50 p-3">
                      <dt className="text-xs font-semibold uppercase text-slate-400">Tổng</dt>
                      <dd className="mt-1 font-bold text-brand-600">{scoreLabel(ans.totalScore)}</dd>
                    </div>
                    <div className="rounded-md bg-slate-50 p-3">
                      <dt className="text-xs font-semibold uppercase text-slate-400">Người chấm</dt>
                      <dd className="mt-1 truncate font-bold text-slate-900">{ans.graderId ?? "—"}</dd>
                    </div>
                  </dl>

                  {ans.manualFeedback && (
                    <div className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                      <p className="text-xs font-semibold uppercase text-slate-400">Nhận xét thủ công</p>
                      <p className="mt-2 leading-6 text-slate-700">{ans.manualFeedback}</p>
                    </div>
                  )}

                  <div>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => toggleForm(ans.questionId)}
                    >
                      {open ? "Ẩn" : "Chấm thủ công"}
                    </Button>
                    {open && (
                      <form
                        className="mt-2 space-y-2"
                        onSubmit={(e: FormEvent) => {
                          e.preventDefault();
                          grade.mutate({ questionId: ans.questionId, form: f });
                        }}
                      >
                        <Input
                          type="number"
                          placeholder="Điểm"
                          value={f.score}
                          onChange={(e) => setForm(ans.questionId, { score: e.target.value })}
                          required
                        />
                        <Textarea
                          placeholder="Nhận xét (tùy chọn)"
                          value={f.feedback}
                          onChange={(e) => setForm(ans.questionId, { feedback: e.target.value })}
                        />
                        {grade.isError && <ErrorState error={grade.error} />}
                        {grade.isSuccess && <p className="text-xs text-emerald-600">Đã chấm</p>}
                        <Button type="submit" disabled={grade.isPending}>
                          {grade.isPending ? "Đang lưu" : "Lưu"}
                        </Button>
                      </form>
                    )}
                  </div>
                </aside>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export function EffectiveScorePage() {
  const [courseId, setCourseId] = useState("");
  const [quizId, setQuizId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [submitted, setSubmitted] = useState({ quizId: "", studentId: "" });

  const courses = useQuery({
    queryKey: queryKeys.courses.list("score"),
    queryFn: () => listCourses(),
    staleTime: 60_000
  });
  const users = useQuery({
    queryKey: queryKeys.users.list,
    queryFn: listUsers,
    staleTime: 60_000
  });
  const courseRows = courses.data ?? [];
  const userRows = users.data ?? [];
  const userById = useMemo(() => new Map(userRows.map((user) => [String(user.id), user])), [userRows]);
  const selectedCourse = courseRows.find((course) => course.id === courseId);
  const selectedLearner = userById.get(studentId);

  useEffect(() => {
    if (!courseId && courseRows.length) setCourseId(courseRows[0].id);
  }, [courseId, courseRows]);

  const courseQuizzes = useQuery({
    queryKey: queryKeys.quizzes.list(courseId),
    queryFn: () => listCourseQuizzes(courseId),
    enabled: Boolean(courseId),
    staleTime: 60_000
  });
  const selectedQuiz = courseQuizzes.data?.find((quiz) => quiz.id === quizId);

  useEffect(() => {
    setQuizId(courseQuizzes.data?.[0]?.id ?? "");
  }, [courseQuizzes.data]);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.quizzes.score(submitted.quizId, submitted.studentId),
    queryFn: () => getEffectiveScore(submitted.quizId, submitted.studentId),
    enabled: Boolean(submitted.quizId && submitted.studentId)
  });

  function lookup(e: FormEvent) {
    e.preventDefault();
    setSubmitted({ quizId, studentId });
  }

  return (
    <div>
      <Link to=".." className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={16} /> Quay lại
      </Link>
      <PageHeader title="Điểm hiệu quả" description="Tra cứu điểm tổng kết theo phương pháp tính" />
      <Card className="mb-4 max-w-3xl">
        <CardHeader
          title="Tra cứu"
          subtitle={[
            selectedCourse ? `${selectedCourse.code} · ${selectedCourse.title}` : "Chọn khóa học",
            selectedQuiz?.title,
            selectedLearner ? userLabel(userById, selectedLearner.id) : undefined
          ].filter(Boolean).join(" · ")}
        />
        <form className="space-y-4 p-4" onSubmit={lookup}>
          <FormField label="Khóa học" htmlFor="es-course">
            <Select
              id="es-course"
              value={courseId}
              onChange={(e) => {
                setCourseId(e.target.value);
                setQuizId("");
              }}
              required
            >
              <option value="">Chọn khóa học</option>
              {courseRows.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.code ? `${course.code} · ${course.title}` : course.title}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Bài thi" htmlFor="es-quiz">
            <Select id="es-quiz" value={quizId} onChange={(e) => setQuizId(e.target.value)} required>
              <option value="">Chọn bài thi</option>
              {(courseQuizzes.data ?? []).map((quiz) => (
                <option key={quiz.id} value={quiz.id}>
                  {quiz.title} · {quizStatusLabel(quiz.status)}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Học viên" htmlFor="es-student">
            <Select id="es-student" value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
              <option value="">Chọn học viên</option>
              {userRows.map((user) => (
                <option key={user.id} value={user.id}>
                  {userLabel(userById, user.id)}
                </option>
              ))}
            </Select>
          </FormField>
          {courses.isError && <ErrorState error={courses.error} />}
          {users.isError && <ErrorState error={users.error} />}
          <Button type="submit" disabled={!quizId || !studentId}>Tra cứu</Button>
        </form>
      </Card>

      {isLoading && <Spinner />}
      {isError && <ErrorState error={error} />}
      {data && (
        <Card className="max-w-lg">
          <CardHeader title="Kết quả" />
          <dl className="grid grid-cols-[160px_1fr] gap-y-3 p-4 text-sm">
            <dt className="text-slate-500">Phương pháp tính</dt>
            <dd>{scoringMethodLabel(data.scoringMethod)}</dd>
            <dt className="text-slate-500">Điểm hiệu quả</dt>
            <dd className="text-2xl font-bold text-brand-600">{data.effectiveScore}</dd>
            <dt className="text-slate-500">Số lần tính</dt>
            <dd>{data.attemptsCounted}</dd>
          </dl>
        </Card>
      )}
    </div>
  );
}
