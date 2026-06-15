/**
 * Centralised React Query keys so cache invalidation stays consistent across
 * modules. Each module owns a namespace.
 */
export const queryKeys = {
  courses: {
    all: ["courses"] as const,
    list: (status?: string) => ["courses", "list", status ?? "all"] as const,
    detail: (id: string) => ["courses", "detail", id] as const,
    related: (id: string) => ["courses", "related", id] as const
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
    promotionApplications: (filters?: Record<string, unknown>) =>
      ["enrollments", "promotion-applications", filters ?? {}] as const,
    audit: (id: string) => ["enrollments", "audit", id] as const
  },
  assignments: {
    list: (courseId?: string) => ["assignments", "list", courseId ?? ""] as const,
    gradingQueue: (courseId?: string) => ["assignments", "grading-queue", courseId ?? ""] as const,
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
    atRisk: (courseId: string) => ["analytics", "at-risk", courseId] as const,
    completion: (courseId: string) => ["analytics", "completion", courseId] as const,
    org: (orgId: string) => ["analytics", "org", orgId] as const,
    marketingFunnel: (filters?: Record<string, unknown>) => ["analytics", "marketing-funnel", filters ?? {}] as const
  },
  incentives: {
    all: ["incentives"] as const,
    applications: (filters?: Record<string, unknown>) =>
      ["incentives", "applications", filters ?? {}] as const,
    campaigns: (filters?: Record<string, unknown>) => ["incentives", "campaigns", filters ?? {}] as const,
    campaign: (id: string) => ["incentives", "campaign", id] as const,
    versions: (campaignId: string) => ["incentives", "campaign", campaignId, "versions"] as const,
    version: (campaignId: string, versionNumber?: number) =>
      ["incentives", "campaign", campaignId, "version", versionNumber ?? "selected"] as const,
    validation: (campaignId: string, versionNumber?: number) =>
      ["incentives", "campaign", campaignId, "validation", versionNumber ?? "selected"] as const,
    diff: (campaignId: string, left?: number, right?: number) =>
      ["incentives", "campaign", campaignId, "diff", left ?? "left", right ?? "right"] as const,
    reviewQueue: (filters?: Record<string, unknown>) => ["incentives", "review-queue", filters ?? {}] as const,
    coupons: (filters?: Record<string, unknown>) => ["incentives", "coupons", filters ?? {}] as const,
    coupon: (id: string) => ["incentives", "coupon", id] as const,
    couponStorageInventory: (filters?: Record<string, unknown>) =>
      ["incentives", "coupons", "storage-inventory", filters ?? {}] as const,
    couponDistributions: (filters?: Record<string, unknown>) =>
      ["incentives", "coupon-distributions", filters ?? {}] as const,
    couponImportDryRun: (dryRunId?: string) =>
      ["incentives", "coupon-import", "dry-run", dryRunId ?? "selected"] as const,
    couponImportDryRuns: (filters?: Record<string, unknown>) =>
      ["incentives", "coupon-import", "dry-runs", filters ?? {}] as const,
    couponImportApprovals: (filters?: Record<string, unknown>) =>
      ["incentives", "coupon-import", "approvals", filters ?? {}] as const,
    couponImportApproval: (approvalId?: string) =>
      ["incentives", "coupon-import", "approval", approvalId ?? "selected"] as const,
    couponImportOperations: (filters?: Record<string, unknown>) =>
      ["incentives", "coupon-import", "operations", filters ?? {}] as const,
    couponImportOperation: (importId?: string) =>
      ["incentives", "coupon-import", "operation", importId ?? "selected"] as const,
    reservations: (filters?: Record<string, unknown>) => ["incentives", "reservations", filters ?? {}] as const,
    reservation: (id?: string) => ["incentives", "reservation", id ?? "selected"] as const,
    redemptions: (filters?: Record<string, unknown>) => ["incentives", "redemptions", filters ?? {}] as const,
    redemption: (id: string) => ["incentives", "redemption", id] as const,
    redemptionReversalApprovals: (filters?: Record<string, unknown>) =>
      ["incentives", "redemptions", "reversal-approvals", filters ?? {}] as const,
    reconciliation: (filters?: Record<string, unknown>) =>
      ["incentives", "reconciliation", filters ?? {}] as const,
    audit: (filters?: Record<string, unknown>) => ["incentives", "audit", filters ?? {}] as const,
    timeline: (type: string, id: string) => ["incentives", "timeline", type, id] as const,
    loyalty: ["incentives", "loyalty"] as const,
    loyaltyPrograms: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "programs", filters ?? {}] as const,
    loyaltyProgram: (id?: string) => ["incentives", "loyalty", "program", id ?? "selected"] as const,
    loyaltyAccounts: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "accounts", filters ?? {}] as const,
    loyaltyTierPolicies: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "tier-policies", filters ?? {}] as const,
    loyaltyTierStates: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "tier-states", filters ?? {}] as const,
    loyaltyLedger: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "ledger", filters ?? {}] as const,
    loyaltyBalanceBuckets: (accountId?: string, asOf?: string) =>
      ["incentives", "loyalty", "balance-buckets", accountId ?? "selected", asOf ?? "now"] as const,
    loyaltyPointLotBackfill: (scope?: Record<string, unknown>) =>
      ["incentives", "loyalty", "point-lot-backfill", scope ?? {}] as const,
    loyaltyAdjustmentApprovals: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "adjustment-approvals", filters ?? {}] as const,
    loyaltyReconciliation: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "reconciliation", filters ?? {}] as const,
    loyaltyRewards: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "rewards", filters ?? {}] as const,
    loyaltyReward: (id?: string) => ["incentives", "loyalty", "reward", id ?? "selected"] as const,
    loyaltyRewardRedemptions: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "reward-redemptions", filters ?? {}] as const,
    learnerLoyaltyRewards: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "learner-rewards", filters ?? {}] as const,
    loyaltyDeadLetters: (filters?: Record<string, unknown>) =>
      ["incentives", "loyalty", "dead-letters", filters ?? {}] as const,
    loyaltyDeadLetter: (id?: string) =>
      ["incentives", "loyalty", "dead-letter", id ?? "selected"] as const,
    loyaltyAudit: (filters?: Record<string, unknown>) => ["incentives", "loyalty", "audit", filters ?? {}] as const,
    loyaltyTimeline: (type: string, id?: string) =>
      ["incentives", "loyalty", "timeline", type, id ?? "selected"] as const,
    opsConsole: (filters?: Record<string, unknown>) => ["incentives", "ops-console", filters ?? {}] as const,
    outboxDeadLetters: (filters?: Record<string, unknown>) =>
      ["incentives", "outbox", "dead-letters", filters ?? {}] as const,
    retentionPolicies: ["incentives", "retention", "policies"] as const,
    retentionDryRun: (scope?: Record<string, unknown>) => ["incentives", "retention", "dry-run", scope ?? {}] as const,
    retentionRestoreDrill: (restoreDrillRef?: string) =>
      ["incentives", "retention", "restore-drill", restoreDrillRef ?? "selected"] as const,
    retentionApprovals: (filters?: Record<string, unknown>) =>
      ["incentives", "retention", "approvals", filters ?? {}] as const,
    retentionApproval: (approvalId?: string) =>
      ["incentives", "retention", "approval", approvalId ?? "selected"] as const,
    retentionEvidencePack: (approvalId?: string) =>
      ["incentives", "retention", "evidence-pack", approvalId ?? "selected"] as const
  },
  gradebook: {
    items: (courseId: string) => ["gradebook", "items", courseId] as const,
    student: (courseId: string, studentId: string) =>
      ["gradebook", "student", courseId, studentId] as const,
    audit: (courseId: string, studentId?: string) =>
      ["gradebook", "audit", courseId, studentId ?? ""] as const,
    gradingQueue: (courseId: string, studentId?: string, status?: string) =>
      ["gradebook", "grading-queue", courseId, studentId ?? "", status ?? ""] as const,
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
    verify: (code: string) => ["certificates", "verify", code] as const,
    eligibility: (courseId: string, studentId: string) =>
      ["certificates", "eligibility", courseId, studentId] as const
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
    preview: (courseId: string) => ["authoring", "preview", courseId] as const,
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
