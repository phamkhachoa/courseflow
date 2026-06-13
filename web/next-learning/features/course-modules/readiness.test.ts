import { describe, expect, it } from "vitest";
import type { ModuleItem } from "./api";
import { getModuleItemKind, getModuleItemReadinessIssue, isModuleItemReady } from "./readiness";

function item(overrides: Partial<ModuleItem>): ModuleItem {
  return {
    id: "item-1",
    position: 1,
    title: "Lesson",
    ...overrides
  };
}

describe("course module readiness", () => {
  it("blocks video lessons without an attached media file", () => {
    const lesson = item({ itemType: "VIDEO" });

    expect(getModuleItemKind(lesson)).toBe("VIDEO");
    expect(isModuleItemReady(lesson)).toBe(false);
    expect(getModuleItemReadinessIssue(lesson)).toBe("Video đang được bổ sung");
  });

  it("marks document lessons with media as ready", () => {
    const lesson = item({ documentMediaIds: ["media-1"], itemType: "DOCUMENT" });

    expect(getModuleItemKind(lesson)).toBe("DOCUMENT");
    expect(isModuleItemReady(lesson)).toBe(true);
    expect(getModuleItemReadinessIssue(lesson)).toBeNull();
  });

  it("blocks assessments without a linked quiz or assignment id", () => {
    const quiz = item({ itemType: "QUIZ" });
    const assignment = item({ itemType: "ASSIGNMENT" });

    expect(isModuleItemReady(quiz)).toBe(false);
    expect(getModuleItemReadinessIssue(quiz)).toBe("Bài thi đang được cấu hình");
    expect(isModuleItemReady(assignment)).toBe(false);
    expect(getModuleItemReadinessIssue(assignment)).toBe("Bài tập đang được cấu hình");
  });

  it("marks text lessons ready once they have learning content", () => {
    const lesson = item({ description: "Read the chapter notes before moving on." });

    expect(getModuleItemKind(lesson)).toBe("LESSON");
    expect(isModuleItemReady(lesson)).toBe(true);
  });
});
