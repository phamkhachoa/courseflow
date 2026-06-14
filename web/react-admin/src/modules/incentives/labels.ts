export type UiTone = "neutral" | "brand" | "success" | "info" | "warning" | "danger" | "slate";

const labels: Record<string, string> = {
  ACTIVE: "Đang hoạt động",
  INACTIVE: "Tạm dừng",
  DISABLED: "Đã tắt",
  SUSPENDED: "Bị khóa",
  DRAFT: "Bản nháp",
  SUBMITTED: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Bị từ chối",
  PUBLISHED: "Đã publish",
  ARCHIVED: "Lưu trữ",
  CLOSED: "Đã đóng",
  REDEEMED: "Đã sử dụng",
  REVERSED: "Đã hoàn",
  RESERVED: "Đã giữ chỗ",
  CANCELLED: "Đã hủy",
  EXPIRED: "Hết hạn",
  VALID: "Hợp lệ",
  INVALID: "Không hợp lệ",
  BLOCKER: "Chặn publish",
  WARNING: "Cảnh báo",
  INFO: "Thông tin",
  PASSED: "Đã kiểm chứng",
  FAILED: "Thất bại",
  PENDING_APPROVAL: "Chờ duyệt",
  EXECUTED: "Đã execute",
  EXECUTION_FAILED: "Execute thất bại",
  SUCCEEDED: "Thành công",
  IN_PROGRESS: "Đang xử lý",
  OPEN: "Đang mở",
  REPLAYED: "Đã replay",
  DISCARDED: "Đã bỏ qua",
  COMMITTED: "Đã commit",
  ISSUED: "Đã phát hành",
  MANUAL_REQUIRED: "Cần xử lý tay",
  COMMIT_READY: "Sẵn sàng commit",
  MATCHED: "Khớp",
  MISSING_OUTBOX: "Thiếu outbox",
  MISSING_EFFECT: "Thiếu effect",
  INVALID_EFFECT_JSON: "Effect JSON lỗi",
  DUPLICATE: "Trùng lặp",
  PENDING: "Đang chờ",
  PENDING_OUTBOX: "Chờ publish outbox",
  CREDIT: "Ghi có",
  DEBIT: "Ghi nợ",
  NOT_REQUIRED: "Không cần",
  APPLY: "Áp dụng",
  COMPENSATE: "Bù trừ",
  RELEASE: "Giải phóng",
  HOLD_RESERVED_QUOTA: "Giữ quota reserve",
  RELEASE_RESERVED_QUOTA: "Giải phóng quota reserve",
  NO_RELEASE_ON_COMMITTED_REVERSAL: "Không hoàn quota đã commit",
  NO_QUOTA_CHANGE: "Không đổi quota"
};

const tones: Record<string, UiTone> = {
  ACTIVE: "success",
  PUBLISHED: "success",
  APPROVED: "success",
  VALID: "success",
  PASSED: "success",
  SUCCEEDED: "success",
  EXECUTED: "success",
  COMMITTED: "success",
  COMMIT_READY: "success",
  MATCHED: "success",
  NOT_REQUIRED: "success",
  REDEEMED: "success",
  REPLAYED: "success",
  ISSUED: "success",
  SUBMITTED: "info",
  PENDING_APPROVAL: "info",
  IN_PROGRESS: "info",
  OPEN: "warning",
  PENDING: "info",
  MANUAL_REQUIRED: "warning",
  PENDING_OUTBOX: "warning",
  RESERVED: "info",
  CREDIT: "success",
  DEBIT: "danger",
  APPLY: "info",
  HOLD_RESERVED_QUOTA: "info",
  NO_QUOTA_CHANGE: "neutral",
  DRAFT: "warning",
  WARNING: "warning",
  MISSING_OUTBOX: "warning",
  MISSING_EFFECT: "warning",
  INVALID_EFFECT_JSON: "danger",
  DUPLICATE: "danger",
  COMPENSATE: "warning",
  RELEASE_RESERVED_QUOTA: "warning",
  NO_RELEASE_ON_COMMITTED_REVERSAL: "warning",
  REJECTED: "danger",
  FAILED: "danger",
  EXECUTION_FAILED: "danger",
  SUSPENDED: "danger",
  DISABLED: "danger",
  REVERSED: "danger",
  CANCELLED: "slate",
  ARCHIVED: "slate",
  CLOSED: "slate",
  EXPIRED: "slate",
  DISCARDED: "slate",
  BLOCKER: "danger",
  INVALID: "danger"
};

export function statusLabel(value?: string | null): string {
  if (!value) return "-";
  return labels[value] ?? value;
}

export function statusTone(value?: string | null): UiTone {
  if (!value) return "neutral";
  return tones[value] ?? "neutral";
}

export function compactId(value?: string | number | null, head = 8, tail = 4): string {
  if (value === undefined || value === null || value === "") return "-";
  const text = String(value);
  return text.length > head + tail + 3 ? `${text.slice(0, head)}...${text.slice(-tail)}` : text;
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(date);
}

export function formatDateTimeInput(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

export function toIsoDateTime(value?: string): string | undefined {
  if (!value?.trim()) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

export function toNumberOrUndefined(value?: string): number | undefined {
  if (!value?.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function splitCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function transitionVerb(action: string): string {
  const verbs: Record<string, string> = {
    submit: "Gửi duyệt",
    approve: "Duyệt",
    reject: "Từ chối",
    publish: "Publish",
    rollback: "Tạo draft rollback"
  };
  return verbs[action] ?? action;
}
