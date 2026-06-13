import type { ModuleItem } from "./api";

export function getModuleItemKind(item: ModuleItem): string {
  const type = item.itemType?.toUpperCase();
  if (type === "VIDEO" || item.videoMediaId) return "VIDEO";
  if (type === "DOCUMENT" || type === "PDF" || type === "MATERIAL" || (item.documentMediaIds?.length ?? 0) > 0) {
    return "DOCUMENT";
  }
  if (type === "LINK" || item.contentUrl) return "LINK";
  return type ?? "LESSON";
}

export function getModuleItemReadinessIssue(item: ModuleItem): string | null {
  const kind = getModuleItemKind(item);
  const docs = item.documentMediaIds ?? [];

  if (kind === "VIDEO" && !item.videoMediaId) return "Video đang được bổ sung";
  if ((kind === "DOCUMENT" || kind === "PDF" || kind === "MATERIAL") && docs.length === 0 && !item.contentUrl) {
    return "Tài liệu đang được bổ sung";
  }
  if (kind === "LINK" && !item.contentUrl) return "Liên kết đang được bổ sung";
  if (kind === "QUIZ" && !item.itemId) return "Bài thi đang được cấu hình";
  if (kind === "ASSIGNMENT" && !item.itemId) return "Bài tập đang được cấu hình";
  if (!item.description && !item.videoMediaId && docs.length === 0 && !item.contentUrl && !item.itemId) {
    return "Nội dung đang được giảng viên bổ sung";
  }

  return null;
}

export function isModuleItemReady(item: ModuleItem): boolean {
  return !getModuleItemReadinessIssue(item);
}
