import { clientFetch } from "@/shared/api/client";

export type LearnerNextActionKind =
  | "CONTINUE_ITEM"
  | "START_COURSE"
  | "COURSE_COMPLETE"
  | "EMPTY"
  | "SOURCE_SYNC_PENDING"
  | "OVERDUE_ITEM"
  | "AWAITING_GRADE"
  | "CERTIFICATE_ELIGIBLE"
  | "CERTIFICATE_ISSUED"
  | "LEARNER_CONTEXT_UNAVAILABLE"
  | "LOCKED_BY_PREREQUISITE"
  | "NOT_AVAILABLE_YET"
  | "SOURCE_LOCKED"
  | "SOURCE_STATUS_UNAVAILABLE"
  | "SOURCE_UNAVAILABLE";

export type NextActionCourseSummary = {
  id: string;
  title: string;
  slug: string;
  progressPercent: number;
};

export type NextActionModuleSummary = {
  id: string;
  title?: string | null;
  progressPercent: number;
  totalItems: number;
  completedItems: number;
  totalRequiredItems: number;
  completedRequiredItems: number;
  completed: boolean;
};

export type NextActionItemSummary = {
  id: string;
  type: string;
  title: string;
  required: boolean;
  status: string;
  refId?: string | null;
};

export type NextActionTarget = {
  type: string;
  id?: string | null;
  refId?: string | null;
};

export type LearnerNextAction = {
  generatedAt: string;
  kind: LearnerNextActionKind;
  course?: NextActionCourseSummary | null;
  module?: NextActionModuleSummary | null;
  item?: NextActionItemSummary | null;
  target?: NextActionTarget | null;
  href: string;
  ctaLabel: string;
  reason: string;
  reasonCode?: string | null;
  priorityScore?: number | null;
  dueAt?: string | null;
};

export function emptyNextAction(reason = "Đăng nhập để CourseFlow gợi ý bài học tiếp theo cho bạn."): LearnerNextAction {
  return {
    generatedAt: new Date().toISOString(),
    kind: "EMPTY",
    href: "/search",
    ctaLabel: "Tìm khóa học",
    reason
  };
}

export function nextActionTitle(action: LearnerNextAction): string {
  if (action.kind === "CERTIFICATE_ISSUED") return `Chứng chỉ: ${action.course?.title ?? "khóa học"}`;
  if (action.kind === "CERTIFICATE_ELIGIBLE") return `Nhận chứng chỉ: ${action.course?.title ?? "khóa học"}`;
  if (action.kind === "AWAITING_GRADE" && !action.item) return `Chờ chốt điểm: ${action.course?.title ?? "khóa học"}`;
  if (action.kind === "LEARNER_CONTEXT_UNAVAILABLE") return "Chưa tải được nhịp học";
  if (action.kind === "SOURCE_SYNC_PENDING") return `Đang đồng bộ: ${action.course?.title ?? "khóa học"}`;
  return action.item?.title ?? action.course?.title ?? "Mở catalog để bắt đầu";
}

export function nextActionBadgeLabel(action: LearnerNextAction): string {
  const kindLabels: Partial<Record<LearnerNextActionKind, string>> = {
    CERTIFICATE_ISSUED: "Chứng chỉ",
    CERTIFICATE_ELIGIBLE: "Đủ điều kiện",
    LEARNER_CONTEXT_UNAVAILABLE: "Chưa đồng bộ",
    AWAITING_GRADE: "Chờ điểm",
    SOURCE_SYNC_PENDING: "Đồng bộ",
    OVERDUE_ITEM: "Quá hạn",
    LOCKED_BY_PREREQUISITE: "Đang khóa",
    NOT_AVAILABLE_YET: "Chưa mở",
    SOURCE_LOCKED: "Đã khóa",
    SOURCE_STATUS_UNAVAILABLE: "Chờ nguồn",
    SOURCE_UNAVAILABLE: "Chưa sẵn sàng"
  };
  if (kindLabels[action.kind]) return kindLabels[action.kind]!;
  if (action.kind === "COURSE_COMPLETE") return "Hoàn thành";
  if (action.kind === "START_COURSE") return "Bắt đầu";
  if (action.kind === "CONTINUE_ITEM") return action.item?.type ?? "Tiếp tục";
  return "Catalog";
}

export async function getLearnerNextAction(): Promise<LearnerNextAction> {
  return clientFetch<LearnerNextAction>("/v1/learning/next-action");
}
