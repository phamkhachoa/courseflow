/**
 * Centralised React Query keys so cache invalidation stays consistent across
 * modules. Each module owns a namespace.
 */
export const queryKeys = {
  courses: {
    all: ["courses"] as const,
    list: (status?: string) => ["courses", "list", status ?? "all"] as const,
    detail: (id: string) => ["courses", "detail", id] as const
  },
  users: {
    all: ["users"] as const,
    list: ["users", "list"] as const,
    detail: (id: string | number) => ["users", "detail", String(id)] as const
  },
  organization: {
    departments: ["organization", "departments"] as const,
    terms: ["organization", "terms"] as const,
    sections: ["organization", "sections"] as const
  },
  enrollments: {
    list: (courseId?: string, studentId?: string) =>
      ["enrollments", "list", courseId ?? "", studentId ?? ""] as const,
    waitlist: (courseId?: string) => ["enrollments", "waitlist", courseId ?? ""] as const,
    stats: (courseId?: string) => ["enrollments", "stats", courseId ?? ""] as const,
    audit: (id: string) => ["enrollments", "audit", id] as const
  },
  assignments: {
    list: (courseId?: string) => ["assignments", "list", courseId ?? ""] as const,
    detail: (id: string) => ["assignments", "detail", id] as const,
    submissions: (assignmentId: string, studentId?: string) =>
      ["assignments", "submissions", assignmentId, studentId ?? ""] as const,
    rubric: (assignmentId: string) => ["assignments", "rubric", assignmentId] as const
  },
  announcements: {
    list: ["announcements", "list"] as const,
    detail: (id: string) => ["announcements", "detail", id] as const
  },
  discussions: {
    threads: (courseId?: string) => ["discussions", "threads", courseId ?? ""] as const,
    thread: (id: string) => ["discussions", "thread", id] as const
  },
  analytics: {
    course: (courseId: string) => ["analytics", "course", courseId] as const,
    completion: (courseId: string) => ["analytics", "completion", courseId] as const,
    org: (orgId: string) => ["analytics", "org", orgId] as const
  },
  gradebook: {
    items: (courseId: string) => ["gradebook", "items", courseId] as const,
    student: (courseId: string, studentId: string) =>
      ["gradebook", "student", courseId, studentId] as const,
    schemes: (courseId: string) => ["gradebook", "schemes", courseId] as const,
    categories: (courseId: string) => ["gradebook", "categories", courseId] as const
  },
  quizzes: {
    list: (courseId?: string) => ["quizzes", "list", courseId ?? ""] as const,
    detail: (id: string) => ["quizzes", "detail", id] as const,
    attempts: (quizId: string) => ["quizzes", "attempts", quizId] as const,
    attempt: (id: string) => ["quizzes", "attempt", id] as const,
    score: (quizId: string, studentId: string) => ["quizzes", "score", quizId, studentId] as const
  },
  courseModules: {
    list: (courseId: string) => ["course-modules", "list", courseId] as const
  },
  certificates: {
    verify: (code: string) => ["certificates", "verify", code] as const
  },
  peerReview: {
    settings: (assignmentId: string) => ["peer-review", "settings", assignmentId] as const
  },
  deadlines: {
    policies: ["deadlines", "policies"] as const,
    due: ["deadlines", "reminders", "due"] as const
  },
  notifications: {
    list: (userId?: string) => ["notifications", "list", userId ?? ""] as const,
    preferences: (userId?: string) => ["notifications", "preferences", userId ?? ""] as const
  },
  media: {
    list: ["media", "list"] as const,
    detail: (id: string) => ["media", "detail", id] as const,
    videos: (courseId?: string) => ["media", "videos", courseId ?? "all"] as const
  },
  portfolio: {
    evidence: (studentId: string) => ["portfolio", "evidence", studentId] as const
  },
  search: {
    courses: (q: string) => ["search", "courses", q] as const
  },
  authoring: {
    draft: (courseId: string) => ["authoring", "draft", courseId] as const,
    versions: (courseId: string) => ["authoring", "versions", courseId] as const,
    versionDiff: (courseId: string, versionNo?: number) => ["authoring", "version-diff", courseId, versionNo ?? "latest"] as const,
    reviewHistory: (courseId: string) => ["authoring", "review-history", courseId] as const,
    reviewQueue: ["authoring", "review-queue"] as const
  },
  liveSessions: {
    list: (courseId: string) => ["live-sessions", courseId] as const,
    detail: (id: string) => ["live-sessions", "detail", id] as const,
    joinInfo: (sessionId: string, userId: string) => ["live-sessions", "join", sessionId, userId] as const,
  },
  roles: {
    all: ["roles"] as const,
    list: ["roles", "list"] as const,
    detail: (id: string) => ["roles", "detail", id] as const,
    permissions: ["permissions"] as const,
    assignments: (userId: string) => ["roles", "assignments", userId] as const
  }
};
