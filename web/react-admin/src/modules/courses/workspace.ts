import type { CourseModule, CourseModuleItem } from "./api";

export type ContentIssue = {
  id: string;
  severity: "blocker" | "warning";
  itemType: string;
  title: string;
  detail: string;
  moduleId?: string;
  moduleTitle?: string;
  itemId?: string;
  itemTitle?: string;
};

export type DependencyStatus = "ready" | "loading" | "error" | "empty" | "blocked" | "warning";
export type DependencyKey = "media" | "quiz" | "assignment";

export type WorkspaceDependency = {
  key: DependencyKey;
  label: string;
  total: number;
  ready: number;
  attention: number;
  status: DependencyStatus;
  detail: string;
};

export type PublishConfidence = {
  score: number;
  label: "Cao" | "Trung bình" | "Thấp";
  tone: "success" | "warning" | "danger";
  detail: string;
};

export type CourseWorkspaceSummary = {
  totalItems: number;
  requiredItems: number;
  optionalItems: number;
  totalMinutes: number;
  mediaCount: number;
  videoCount: number;
  documentCount: number;
  linkCount: number;
  blockers: number;
  warnings: number;
  dependencies: WorkspaceDependency[];
  publishConfidence: PublishConfidence;
};

export type CurriculumOrder = { moduleId: string; itemIds: string[] };
export type ReorderDirection = "up" | "down";

type CatalogItem = { id: string; title: string; status?: string };

function sortByPosition<T extends { position: number }>(rows: T[]) {
  return [...rows].sort((a, b) => a.position - b.position);
}

function moveByDirection<T>(rows: T[], currentIndex: number, direction: ReorderDirection) {
  const targetIndex = direction === "up" ? currentIndex - 1 : currentIndex + 1;
  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= rows.length) return null;
  const next = [...rows];
  [next[currentIndex], next[targetIndex]] = [next[targetIndex], next[currentIndex]];
  return next;
}

function shortRef(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function assignmentStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    DRAFT: "Nháp - chưa hiển thị",
    PUBLISHED: "Đã công khai",
    ARCHIVED: "Đã lưu trữ"
  };
  return labels[status ?? ""] ?? status ?? "Nháp - chưa hiển thị";
}

function referencedStatusLabel(status?: string) {
  if (!status) return "không rõ trạng thái";
  return assignmentStatusLabel(status);
}

export function orderedCourseModules(modules: CourseModule[]) {
  return sortByPosition(modules);
}

export function orderedModuleItems(module: CourseModule) {
  return sortByPosition(module.items ?? []);
}

function curriculumOrderFromOrderedModules(modules: CourseModule[]): CurriculumOrder[] {
  return modules.map((module) => ({
    moduleId: module.moduleId,
    itemIds: orderedModuleItems(module).map((item) => item.itemId)
  }));
}

export function buildCurriculumOrder(modules: CourseModule[]): CurriculumOrder[] {
  return curriculumOrderFromOrderedModules(orderedCourseModules(modules));
}

export function moveModuleOrder(
  modules: CourseModule[],
  moduleId: string,
  direction: ReorderDirection
): CurriculumOrder[] | null {
  const orderedModules = orderedCourseModules(modules);
  const nextModules = moveByDirection(
    orderedModules,
    orderedModules.findIndex((module) => module.moduleId === moduleId),
    direction
  );
  return nextModules ? curriculumOrderFromOrderedModules(nextModules) : null;
}

export function moveItemOrder(
  modules: CourseModule[],
  moduleId: string,
  itemId: string,
  direction: ReorderDirection
): CurriculumOrder[] | null {
  const orderedModules = orderedCourseModules(modules);
  const targetModule = orderedModules.find((module) => module.moduleId === moduleId);
  if (!targetModule) return null;

  const orderedItems = orderedModuleItems(targetModule);
  const nextItems = moveByDirection(
    orderedItems,
    orderedItems.findIndex((item) => item.itemId === itemId),
    direction
  );
  if (!nextItems) return null;

  return orderedModules.map((module) => ({
    moduleId: module.moduleId,
    itemIds: module.moduleId === moduleId
      ? nextItems.map((item) => item.itemId)
      : orderedModuleItems(module).map((item) => item.itemId)
  }));
}

function flattenItems(modules: CourseModule[]) {
  return orderedCourseModules(modules).flatMap(orderedModuleItems);
}

function contentIssue(
  item: CourseModuleItem,
  module: CourseModule,
  severity: ContentIssue["severity"],
  title: string,
  detail: string
): ContentIssue {
  return {
    id: `${module.moduleId}:${item.itemId}:${title}`,
    severity,
    itemType: item.itemType,
    title,
    detail,
    moduleId: module.moduleId,
    moduleTitle: module.title,
    itemId: item.itemId,
    itemTitle: item.title
  };
}

export function buildContentIssues({
  modules,
  quizzes,
  assignments,
  canValidateQuizzes,
  canValidateAssignments,
  quizCheckFailed,
  assignmentCheckFailed
}: {
  modules: CourseModule[];
  quizzes: CatalogItem[];
  assignments: CatalogItem[];
  canValidateQuizzes: boolean;
  canValidateAssignments: boolean;
  quizCheckFailed: boolean;
  assignmentCheckFailed: boolean;
}): ContentIssue[] {
  const issues: ContentIssue[] = [];
  const quizById = new Map(quizzes.map((quiz) => [quiz.id, quiz]));
  const assignmentById = new Map(assignments.map((assignment) => [assignment.id, assignment]));
  const hasQuizItem = modules.some((module) => module.items?.some((item) => item.itemType === "QUIZ"));
  const hasAssignmentItem = modules.some((module) => module.items?.some((item) => item.itemType === "ASSIGNMENT"));

  if (modules.length === 0) {
    issues.push({
      id: "course:no-modules",
      severity: "blocker",
      itemType: "MODULE",
      title: "Course chưa có chương",
      detail: "Tạo ít nhất một chương và thêm nội dung học trước khi gửi duyệt."
    });
  }

  if (hasQuizItem && quizCheckFailed) {
    issues.push({
      id: "quiz-catalog-check",
      severity: "blocker",
      itemType: "QUIZ",
      title: "Không kiểm tra được bài thi",
      detail: "Cần tải được danh sách quiz để xác nhận learner có thể mở bài thi trước khi gửi duyệt hoặc publish."
    });
  }

  if (hasAssignmentItem && assignmentCheckFailed) {
    issues.push({
      id: "assignment-catalog-check",
      severity: "blocker",
      itemType: "ASSIGNMENT",
      title: "Không kiểm tra được bài tập",
      detail: "Cần tải được danh sách assignment để tránh publish course trỏ tới assignment nháp."
    });
  }

  for (const module of modules) {
    const items = orderedModuleItems(module);
    if (items.length === 0) {
      issues.push({
        id: `${module.moduleId}:empty`,
        severity: "blocker",
        itemType: "MODULE",
        title: "Chương chưa có bài học",
        detail: "Mỗi chương cần ít nhất một item sẵn sàng trước khi gửi duyệt.",
        moduleId: module.moduleId,
        moduleTitle: module.title
      });
    } else if (!items.some((item) => item.required)) {
      issues.push({
        id: `${module.moduleId}:no-required-items`,
        severity: "blocker",
        itemType: "MODULE",
        title: "Chương chưa có bài bắt buộc",
        detail: "Mỗi chương cần ít nhất một item bắt buộc để progress và certificate eligibility có cơ sở tính.",
        moduleId: module.moduleId,
        moduleTitle: module.title
      });
    }

    for (const item of items) {
      const type = item.itemType;
      const docs = item.documentMediaIds ?? [];
      const description = item.description?.trim();
      const hasAnyPayload = Boolean(
        description ||
          item.videoMediaId ||
          docs.length > 0 ||
          item.contentUrl
      );

      if ((type === "LESSON" || !type) && !hasAnyPayload) {
        issues.push(contentIssue(
          item,
          module,
          "blocker",
          "Bài học chưa có nội dung",
          "Thêm mô tả, video, tài liệu hoặc link để learner không mở vào trang rỗng."
        ));
      }

      if ((type === "LESSON" || !type) && description && !item.videoMediaId && docs.length === 0 && !item.contentUrl) {
        issues.push(contentIssue(
          item,
          module,
          "warning",
          "Bài học chỉ có mô tả",
          "Nên gắn thêm video, tài liệu hoặc link để learner có học liệu rõ ràng hơn."
        ));
      }

      if (type === "VIDEO" && !item.videoMediaId) {
        issues.push(contentIssue(
          item,
          module,
          "blocker",
          "Video chưa gắn file phát",
          "Upload hoặc chọn video media trước khi gửi duyệt."
        ));
      }

      if ((type === "DOCUMENT" || type === "PDF" || type === "MATERIAL") && docs.length === 0 && !item.contentUrl) {
        issues.push(contentIssue(
          item,
          module,
          "blocker",
          "Tài liệu chưa có file hoặc link",
          "Gắn ít nhất một media asset hoặc link tài liệu."
        ));
      }

      if (type === "LINK" && !item.contentUrl) {
        issues.push(contentIssue(
          item,
          module,
          "blocker",
          "Liên kết đang trống",
          "Thêm URL trước khi learner nhìn thấy bài này."
        ));
      }

      if (item.estimatedMinutes == null && type !== "QUIZ" && type !== "ASSIGNMENT") {
        issues.push(contentIssue(
          item,
          module,
          "warning",
          "Chưa ước lượng thời lượng",
          "Thêm estimated minutes để workspace dự báo effort và pacing chính xác hơn."
        ));
      }

      if (type === "QUIZ") {
        if (!item.refId) {
          issues.push(contentIssue(item, module, "blocker", "Bài thi chưa được chọn", "Chọn quiz đã thuộc khóa học này."));
        } else if (canValidateQuizzes) {
          const quiz = quizById.get(item.refId);
          if (!quiz) {
            issues.push(contentIssue(item, module, "blocker", "Quiz reference không tìm thấy", `Không tìm thấy quiz ${shortRef(item.refId)} trong khóa học.`));
          } else if (quiz.status !== "PUBLISHED") {
            issues.push(contentIssue(
              item,
              module,
              "blocker",
              "Quiz chưa công khai",
              `${quiz.title} đang ở trạng thái ${referencedStatusLabel(quiz.status)}; learner sẽ không mở được quiz này.`
            ));
          }
        }
      }

      if (type === "ASSIGNMENT") {
        if (!item.refId) {
          issues.push(contentIssue(item, module, "blocker", "Bài tập chưa được chọn", "Chọn assignment đã thuộc khóa học này."));
        } else if (canValidateAssignments) {
          const assignment = assignmentById.get(item.refId);
          if (!assignment) {
            issues.push(contentIssue(item, module, "blocker", "Assignment reference không tìm thấy", `Không tìm thấy assignment ${shortRef(item.refId)} trong khóa học.`));
          } else if (assignment.status !== "PUBLISHED") {
            issues.push(contentIssue(
              item,
              module,
              "blocker",
              "Assignment chưa learner-visible",
              `${assignment.title} đang ở trạng thái ${referencedStatusLabel(assignment.status)}; assignment nháp không hiển thị cho learner.`
            ));
          }
        }
      }
    }
  }

  if (flattenItems(modules).length > 0 && !flattenItems(modules).some((item) => item.required)) {
    issues.push({
      id: "course:no-required-items",
      severity: "blocker",
      itemType: "MODULE",
      title: "Course chưa có bài học bắt buộc",
      detail: "Đánh dấu ít nhất một item là bắt buộc trước khi gửi duyệt hoặc publish."
    });
  }

  return issues;
}

function issueCount(issues: ContentIssue[], itemTypes: string[], severity?: ContentIssue["severity"]) {
  return issues.filter((issue) => itemTypes.includes(issue.itemType) && (!severity || issue.severity === severity)).length;
}

function dependencyStatus({
  total,
  ready,
  attention,
  isLoading,
  isError
}: {
  total: number;
  ready: number;
  attention: number;
  isLoading?: boolean;
  isError?: boolean;
}): DependencyStatus {
  if (isLoading) return "loading";
  if (isError) return "error";
  if (attention > 0) return "blocked";
  if (total === 0) return "empty";
  if (ready < total) return "warning";
  return "ready";
}

function dependencyDetail(status: DependencyStatus, total: number, ready: number, noun: string, attention = 0) {
  if (status === "empty") return `Chưa có ${noun} trong curriculum.`;
  if (status === "loading") return `Đang tải catalog để kiểm tra ${noun}.`;
  if (status === "error") return `Không tải được catalog ${noun}; cần thử lại trước khi publish.`;
  if (status === "blocked") return `Có ${attention || Math.max(total - ready, 0)} ${noun} blocker cần xử lý.`;
  if (status === "warning") return `${ready}/${total} ${noun} đã sẵn sàng, cần rà lại phần còn lại.`;
  return `${ready}/${total} ${noun} đã sẵn sàng cho learner.`;
}

function catalogReadyCount(refIds: string[], catalog: CatalogItem[]) {
  const byId = new Map(catalog.map((item) => [item.id, item]));
  return refIds.filter((refId) => byId.get(refId)?.status === "PUBLISHED").length;
}

function confidenceLabel(score: number): PublishConfidence["label"] {
  if (score >= 85) return "Cao";
  if (score >= 60) return "Trung bình";
  return "Thấp";
}

export function buildWorkspaceSummary({
  modules,
  quizzes,
  assignments,
  contentIssues,
  reviewState,
  courseStatus,
  readinessChecksPending,
  quizLoading,
  quizError,
  assignmentLoading,
  assignmentError
}: {
  modules: CourseModule[];
  quizzes: CatalogItem[];
  assignments: CatalogItem[];
  contentIssues: ContentIssue[];
  reviewState: string;
  courseStatus: string;
  readinessChecksPending: boolean;
  quizLoading: boolean;
  quizError: boolean;
  assignmentLoading: boolean;
  assignmentError: boolean;
}): CourseWorkspaceSummary {
  const items = flattenItems(modules);
  const requiredItems = items.filter((item) => item.required).length;
  const optionalItems = Math.max(items.length - requiredItems, 0);
  const totalMinutes = items.reduce((sum, item) => sum + (item.estimatedMinutes ?? 0), 0);
  const videoCount = items.filter((item) => Boolean(item.videoMediaId)).length;
  const documentCount = items.reduce((sum, item) => sum + (item.documentMediaIds?.length ?? 0), 0);
  const linkCount = items.filter((item) => Boolean(item.contentUrl)).length;
  const mediaCount = videoCount + documentCount + linkCount;
  const quizRefs = items.filter((item) => item.itemType === "QUIZ").map((item) => item.refId).filter(Boolean);
  const assignmentRefs = items.filter((item) => item.itemType === "ASSIGNMENT").map((item) => item.refId).filter(Boolean);
  const blockers = contentIssues.filter((issue) => issue.severity === "blocker").length;
  const warnings = contentIssues.filter((issue) => issue.severity === "warning").length;
  const mediaTypes = ["LESSON", "VIDEO", "DOCUMENT", "PDF", "MATERIAL", "LINK"];
  const mediaAttention = issueCount(contentIssues, mediaTypes);
  const mediaBlockers = issueCount(contentIssues, mediaTypes, "blocker");
  const mediaStatus: DependencyStatus = items.length === 0
    ? "empty"
    : mediaBlockers > 0
      ? "blocked"
      : mediaAttention > 0
        ? "warning"
        : mediaCount > 0
          ? "ready"
          : "empty";
  const quizReady = catalogReadyCount(quizRefs, quizzes);
  const quizAttention = issueCount(contentIssues, ["QUIZ"]);
  const quizStatus = dependencyStatus({
    total: quizRefs.length,
    ready: quizReady,
    attention: quizAttention,
    isLoading: quizLoading,
    isError: quizError
  });
  const assignmentReady = catalogReadyCount(assignmentRefs, assignments);
  const assignmentAttention = issueCount(contentIssues, ["ASSIGNMENT"]);
  const assignmentStatus = dependencyStatus({
    total: assignmentRefs.length,
    ready: assignmentReady,
    attention: assignmentAttention,
    isLoading: assignmentLoading,
    isError: assignmentError
  });
  const dependencies: WorkspaceDependency[] = [
    {
      key: "media",
      label: "Media & links",
      total: mediaCount,
      ready: mediaCount,
      attention: mediaAttention,
      status: mediaStatus,
      detail: mediaStatus === "empty"
        ? "Chưa có video, tài liệu hoặc link ngoài trong curriculum."
        : mediaStatus === "blocked"
          ? `${mediaBlockers} media blocker cần xử lý trước review.`
          : mediaStatus === "warning"
            ? `${mediaAttention} media warning nên xử lý để tăng chất lượng học liệu.`
            : `${videoCount} video, ${documentCount} tài liệu, ${linkCount} link đã gắn.`
    },
    {
      key: "quiz",
      label: "Quiz",
      total: quizRefs.length,
      ready: quizReady,
      attention: quizAttention,
      status: quizStatus,
      detail: dependencyDetail(quizStatus, quizRefs.length, quizReady, "quiz", quizAttention)
    },
    {
      key: "assignment",
      label: "Assignment",
      total: assignmentRefs.length,
      ready: assignmentReady,
      attention: assignmentAttention,
      status: assignmentStatus,
      detail: dependencyDetail(assignmentStatus, assignmentRefs.length, assignmentReady, "assignment", assignmentAttention)
    }
  ];

  let score = 0;
  if (modules.length > 0) score += 10;
  if (items.length > 0) score += 10;
  if (requiredItems > 0) score += 5;
  if (!readinessChecksPending && blockers === 0) score += 35;
  else if (!readinessChecksPending && blockers <= 2) score += 12;
  const dependencyHealthy = dependencies.every((dependency) => dependency.status === "ready" || dependency.status === "empty");
  const dependencySettled = dependencies.every((dependency) => dependency.status !== "loading");
  if (dependencyHealthy) score += 15;
  else if (!dependencySettled) score += 6;
  if (reviewState === "APPROVED" || reviewState === "PUBLISHED") score += 20;
  else if (reviewState === "IN_REVIEW") score += 10;
  if (courseStatus === "DRAFT" || courseStatus === "PUBLISHED") score += 5;
  if (warnings > 0) score -= Math.min(10, warnings * 2);
  score = Math.max(0, Math.min(100, score));

  const label = confidenceLabel(score);
  const tone: PublishConfidence["tone"] = label === "Cao" ? "success" : label === "Trung bình" ? "warning" : "danger";
  const detail = readinessChecksPending
    ? "Đang chờ kiểm tra dependency quiz/assignment."
    : blockers > 0
      ? `Còn ${blockers} blocker cần xử lý trước publish.`
      : reviewState !== "APPROVED" && reviewState !== "PUBLISHED"
        ? "Nội dung ổn, còn bước review trước publish."
        : "Đủ tín hiệu để publish cho learner.";

  return {
    totalItems: items.length,
    requiredItems,
    optionalItems,
    totalMinutes,
    mediaCount,
    videoCount,
    documentCount,
    linkCount,
    blockers,
    warnings,
    dependencies,
    publishConfidence: { score, label, tone, detail }
  };
}
