import { describe, expect, it } from "vitest";
import { emptyNextAction, nextActionBadgeLabel, nextActionTitle, type LearnerNextAction } from "./next-action";

describe("learner next-action helpers", () => {
  it("uses the item title and item type for continue-item actions", () => {
    const action: LearnerNextAction = {
      generatedAt: "2026-06-13T08:00:00.000Z",
      kind: "CONTINUE_ITEM",
      course: {
        id: "course-1",
        title: "Production LMS",
        slug: "production-lms",
        progressPercent: 50
      },
      item: {
        id: "item-1",
        type: "LESSON",
        title: "Read architecture overview",
        required: true,
        status: "NOT_STARTED",
        refId: "lesson-ref"
      },
      href: "/courses/production-lms/modules",
      ctaLabel: "Tiếp tục học",
      reason: "Bài bắt buộc tiếp theo chưa hoàn thành."
    };

    expect(nextActionTitle(action)).toBe("Read architecture overview");
    expect(nextActionBadgeLabel(action)).toBe("LESSON");
  });

  it("falls back to catalog copy for empty actions", () => {
    const action = emptyNextAction();

    expect(nextActionTitle(action)).toBe("Mở catalog để bắt đầu");
    expect(nextActionBadgeLabel(action)).toBe("Catalog");
    expect(action.href).toBe("/search");
  });

  it("surfaces certificate copy for issued certificates", () => {
    const action: LearnerNextAction = {
      generatedAt: "2026-06-13T08:00:00.000Z",
      kind: "CERTIFICATE_ISSUED",
      course: {
        id: "course-1",
        title: "Production LMS",
        slug: "production-lms",
        progressPercent: 100
      },
      target: {
        type: "CERTIFICATE",
        id: "certificate-1",
        refId: "CF-VERIFY"
      },
      href: "/certificates/verify/CF-VERIFY",
      ctaLabel: "Xác minh chứng chỉ",
      reason: "Chứng chỉ của bạn đã được cấp."
    };

    expect(nextActionTitle(action)).toBe("Chứng chỉ: Production LMS");
    expect(nextActionBadgeLabel(action)).toBe("Chứng chỉ");
  });

  it("labels operational next-action states clearly", () => {
    const awaitingGrade: LearnerNextAction = {
      generatedAt: "2026-06-13T08:00:00.000Z",
      kind: "AWAITING_GRADE",
      course: {
        id: "course-1",
        title: "Production LMS",
        slug: "production-lms",
        progressPercent: 100
      },
      href: "/gradebook",
      ctaLabel: "Xem bảng điểm",
      reason: "Khóa học đã hoàn thành; bạn đang chờ instructor chốt điểm cuối khóa."
    };
    const sourceSync: LearnerNextAction = {
      generatedAt: "2026-06-13T08:00:00.000Z",
      kind: "SOURCE_SYNC_PENDING",
      course: {
        id: "course-1",
        title: "Production LMS",
        slug: "production-lms",
        progressPercent: 80
      },
      href: "/courses/production-lms/modules",
      ctaLabel: "Làm mới sau",
      reason: "Các hoạt động bắt buộc đã hoàn tất ở hệ thống nguồn."
    };

    expect(nextActionTitle(awaitingGrade)).toBe("Chờ chốt điểm: Production LMS");
    expect(nextActionBadgeLabel(awaitingGrade)).toBe("Chờ điểm");
    expect(nextActionTitle(sourceSync)).toBe("Đang đồng bộ: Production LMS");
    expect(nextActionBadgeLabel(sourceSync)).toBe("Đồng bộ");
  });

  it("labels learner context degradation separately from an empty catalog", () => {
    const action: LearnerNextAction = {
      generatedAt: "2026-06-13T08:00:00.000Z",
      kind: "LEARNER_CONTEXT_UNAVAILABLE",
      href: "/",
      ctaLabel: "Thử lại sau",
      reason: "Chưa tải được danh sách khóa học của bạn.",
      reasonCode: "ENROLLMENT_MEMBERSHIP_UNAVAILABLE"
    };

    expect(nextActionTitle(action)).toBe("Chưa tải được nhịp học");
    expect(nextActionBadgeLabel(action)).toBe("Chưa đồng bộ");
  });

  it("allows contextual fallback reasons", () => {
    const action = emptyNextAction("Chưa tải được gợi ý tiếp theo.");

    expect(action.reason).toBe("Chưa tải được gợi ý tiếp theo.");
    expect(action.ctaLabel).toBe("Tìm khóa học");
  });
});
