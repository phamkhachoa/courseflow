import { describe, expect, it } from "vitest";
import type { CourseModule } from "./api";
import {
  buildContentIssues,
  buildCurriculumOrder,
  buildWorkspaceSummary,
  moveItemOrder,
  moveModuleOrder
} from "./workspace";

const readyModules: CourseModule[] = [
  {
    moduleId: "module-1",
    title: "Foundations",
    position: 1,
    status: "DRAFT",
    items: [
      {
        itemId: "lesson-1",
        itemType: "LESSON",
        refId: "",
        title: "Intro lesson",
        description: "Set the context",
        videoMediaId: "video-1",
        documentMediaIds: ["doc-1"],
        estimatedMinutes: 20,
        position: 1,
        required: true
      },
      {
        itemId: "quiz-1",
        itemType: "QUIZ",
        refId: "quiz-published",
        title: "Knowledge check",
        estimatedMinutes: 10,
        position: 2,
        required: true
      },
      {
        itemId: "assignment-1",
        itemType: "ASSIGNMENT",
        refId: "assignment-published",
        title: "Practice task",
        estimatedMinutes: 30,
        position: 3,
        required: true
      }
    ]
  }
];

describe("course workspace summary", () => {
  it("reports high confidence when content and dependencies are learner-visible", () => {
    const issues = buildContentIssues({
      modules: readyModules,
      quizzes: [{ id: "quiz-published", title: "Knowledge check", status: "PUBLISHED" }],
      assignments: [{ id: "assignment-published", title: "Practice task", status: "PUBLISHED" }],
      canValidateQuizzes: true,
      canValidateAssignments: true,
      quizCheckFailed: false,
      assignmentCheckFailed: false
    });

    const summary = buildWorkspaceSummary({
      modules: readyModules,
      quizzes: [{ id: "quiz-published", title: "Knowledge check", status: "PUBLISHED" }],
      assignments: [{ id: "assignment-published", title: "Practice task", status: "PUBLISHED" }],
      contentIssues: issues,
      reviewState: "APPROVED",
      courseStatus: "DRAFT",
      readinessChecksPending: false,
      quizLoading: false,
      quizError: false,
      assignmentLoading: false,
      assignmentError: false
    });

    expect(issues).toHaveLength(0);
    expect(summary.publishConfidence.label).toBe("Cao");
    expect(summary.publishConfidence.score).toBeGreaterThanOrEqual(90);
    expect(summary.dependencies.map((dependency) => dependency.status)).toEqual(["ready", "ready", "ready"]);
  });

  it("surfaces blocking quiz and assignment dependencies", () => {
    const modules: CourseModule[] = [
      {
        moduleId: "module-1",
        title: "Assessments",
        position: 1,
        status: "DRAFT",
        items: [
          {
            itemId: "quiz-1",
            itemType: "QUIZ",
            refId: "quiz-draft",
            title: "Draft quiz",
            position: 1,
            required: true
          },
          {
            itemId: "assignment-1",
            itemType: "ASSIGNMENT",
            refId: "assignment-missing",
            title: "Missing assignment",
            position: 2,
            required: true
          }
        ]
      }
    ];
    const issues = buildContentIssues({
      modules,
      quizzes: [{ id: "quiz-draft", title: "Draft quiz", status: "DRAFT" }],
      assignments: [],
      canValidateQuizzes: true,
      canValidateAssignments: true,
      quizCheckFailed: false,
      assignmentCheckFailed: false
    });

    const summary = buildWorkspaceSummary({
      modules,
      quizzes: [{ id: "quiz-draft", title: "Draft quiz", status: "DRAFT" }],
      assignments: [],
      contentIssues: issues,
      reviewState: "DRAFT",
      courseStatus: "DRAFT",
      readinessChecksPending: false,
      quizLoading: false,
      quizError: false,
      assignmentLoading: false,
      assignmentError: false
    });

    expect(issues.map((issue) => issue.title)).toEqual([
      "Quiz chưa công khai",
      "Assignment reference không tìm thấy"
    ]);
    expect(summary.blockers).toBe(2);
    expect(summary.dependencies.find((dependency) => dependency.key === "quiz")?.status).toBe("blocked");
    expect(summary.dependencies.find((dependency) => dependency.key === "assignment")?.status).toBe("blocked");
    expect(summary.publishConfidence.label).toBe("Thấp");
  });

  it("keeps referenced catalog dependencies in loading state while checks are pending", () => {
    const modules: CourseModule[] = [
      {
        moduleId: "module-1",
        title: "Checks",
        position: 1,
        status: "DRAFT",
        items: [
          {
            itemId: "quiz-1",
            itemType: "QUIZ",
            refId: "quiz-pending",
            title: "Pending quiz",
            position: 1,
            required: true
          }
        ]
      }
    ];
    const issues = buildContentIssues({
      modules,
      quizzes: [],
      assignments: [],
      canValidateQuizzes: false,
      canValidateAssignments: true,
      quizCheckFailed: false,
      assignmentCheckFailed: false
    });

    const summary = buildWorkspaceSummary({
      modules,
      quizzes: [],
      assignments: [],
      contentIssues: issues,
      reviewState: "DRAFT",
      courseStatus: "DRAFT",
      readinessChecksPending: true,
      quizLoading: true,
      quizError: false,
      assignmentLoading: false,
      assignmentError: false
    });

    expect(summary.dependencies.find((dependency) => dependency.key === "quiz")?.status).toBe("loading");
    expect(summary.dependencies.find((dependency) => dependency.key === "assignment")?.status).toBe("empty");
    expect(summary.publishConfidence.detail).toContain("Đang chờ kiểm tra");
  });

  it("does not treat a generated lesson ref as learning content", () => {
    const modules: CourseModule[] = [
      {
        moduleId: "module-1",
        title: "Generated refs",
        position: 1,
        status: "DRAFT",
        items: [
          {
            itemId: "lesson-1",
            itemType: "LESSON",
            refId: "lesson-1",
            title: "Empty lesson",
            position: 1,
            required: true
          }
        ]
      }
    ];

    const issues = buildContentIssues({
      modules,
      quizzes: [],
      assignments: [],
      canValidateQuizzes: true,
      canValidateAssignments: true,
      quizCheckFailed: false,
      assignmentCheckFailed: false
    });

    expect(issues.map((issue) => issue.title)).toContain("Bài học chưa có nội dung");
  });

  it("blocks review when a populated course has no required learning item", () => {
    const modules: CourseModule[] = [
      {
        moduleId: "module-1",
        title: "Optional track",
        position: 1,
        status: "DRAFT",
        items: [
          {
            itemId: "lesson-1",
            itemType: "LESSON",
            refId: "",
            title: "Optional lesson",
            description: "Readable content",
            videoMediaId: "video-1",
            estimatedMinutes: 15,
            position: 1,
            required: false
          }
        ]
      }
    ];

    const issues = buildContentIssues({
      modules,
      quizzes: [],
      assignments: [],
      canValidateQuizzes: true,
      canValidateAssignments: true,
      quizCheckFailed: false,
      assignmentCheckFailed: false
    });
    const summary = buildWorkspaceSummary({
      modules,
      quizzes: [],
      assignments: [],
      contentIssues: issues,
      reviewState: "DRAFT",
      courseStatus: "DRAFT",
      readinessChecksPending: false,
      quizLoading: false,
      quizError: false,
      assignmentLoading: false,
      assignmentError: false
    });

    expect(issues.map((issue) => issue.title)).toEqual([
      "Chương chưa có bài bắt buộc",
      "Course chưa có bài học bắt buộc"
    ]);
    expect(summary.requiredItems).toBe(0);
    expect(summary.blockers).toBe(2);
    expect(summary.publishConfidence.label).toBe("Thấp");
  });

  it("treats quiz or assignment items without refs as blocked dependencies", () => {
    const modules: CourseModule[] = [
      {
        moduleId: "module-1",
        title: "Assessment shell",
        position: 1,
        status: "DRAFT",
        items: [
          {
            itemId: "quiz-1",
            itemType: "QUIZ",
            refId: "",
            title: "Unselected quiz",
            position: 1,
            required: true
          },
          {
            itemId: "assignment-1",
            itemType: "ASSIGNMENT",
            refId: "",
            title: "Unselected assignment",
            position: 2,
            required: true
          }
        ]
      }
    ];

    const issues = buildContentIssues({
      modules,
      quizzes: [],
      assignments: [],
      canValidateQuizzes: true,
      canValidateAssignments: true,
      quizCheckFailed: false,
      assignmentCheckFailed: false
    });
    const summary = buildWorkspaceSummary({
      modules,
      quizzes: [],
      assignments: [],
      contentIssues: issues,
      reviewState: "DRAFT",
      courseStatus: "DRAFT",
      readinessChecksPending: false,
      quizLoading: false,
      quizError: false,
      assignmentLoading: false,
      assignmentError: false
    });

    expect(issues.map((issue) => issue.title)).toEqual([
      "Bài thi chưa được chọn",
      "Bài tập chưa được chọn"
    ]);
    expect(summary.dependencies.find((dependency) => dependency.key === "quiz")).toMatchObject({
      status: "blocked",
      attention: 1,
      detail: "Có 1 quiz blocker cần xử lý."
    });
    expect(summary.dependencies.find((dependency) => dependency.key === "assignment")).toMatchObject({
      status: "blocked",
      attention: 1,
      detail: "Có 1 assignment blocker cần xử lý."
    });
  });
});

describe("course curriculum reorder", () => {
  const unorderedModules: CourseModule[] = [
    {
      moduleId: "module-b",
      title: "Module B",
      position: 2,
      status: "DRAFT",
      items: [
        {
          itemId: "item-b2",
          itemType: "LESSON",
          refId: "",
          title: "B2",
          position: 2,
          required: true
        },
        {
          itemId: "item-b1",
          itemType: "LESSON",
          refId: "",
          title: "B1",
          position: 1,
          required: true
        }
      ]
    },
    {
      moduleId: "module-a",
      title: "Module A",
      position: 1,
      status: "DRAFT",
      items: [
        {
          itemId: "item-a1",
          itemType: "LESSON",
          refId: "",
          title: "A1",
          position: 1,
          required: true
        }
      ]
    }
  ];

  it("builds an API-ready curriculum order from module and item positions", () => {
    expect(buildCurriculumOrder(unorderedModules)).toEqual([
      { moduleId: "module-a", itemIds: ["item-a1"] },
      { moduleId: "module-b", itemIds: ["item-b1", "item-b2"] }
    ]);
  });

  it("moves a module relative to the currently displayed order", () => {
    expect(moveModuleOrder(unorderedModules, "module-b", "up")).toEqual([
      { moduleId: "module-b", itemIds: ["item-b1", "item-b2"] },
      { moduleId: "module-a", itemIds: ["item-a1"] }
    ]);
  });

  it("moves an item inside its module and preserves the other modules", () => {
    expect(moveItemOrder(unorderedModules, "module-b", "item-b2", "up")).toEqual([
      { moduleId: "module-a", itemIds: ["item-a1"] },
      { moduleId: "module-b", itemIds: ["item-b2", "item-b1"] }
    ]);
  });

  it("does not build a reorder request for boundary moves", () => {
    expect(moveModuleOrder(unorderedModules, "module-a", "up")).toBeNull();
    expect(moveItemOrder(unorderedModules, "module-b", "item-b2", "down")).toBeNull();
  });
});
