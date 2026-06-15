#!/usr/bin/env node

import { spawnSync } from "node:child_process";

/**
 * Gateway-level Product Hardening smoke test.
 *
 * This script intentionally uses only public/admin gateway routes and disposable data. It proves
 * that the production-pilot guardrails added during Product Hardening are reachable through the
 * real edge:
 *   - Keycloak/OIDC bearer tokens accepted by the gateway
 *   - public catalog read
 *   - protected module content access
 *   - admin authoring readiness review + publish workflow
 *   - media document/video readiness through MinIO-backed upload URLs
 *   - quiz and assignment references frozen into the published curriculum snapshot
 *   - negative readiness and entitlement checks around draft refs and media downloads
 *   - enrollment creation and learner module/progress access
 *   - quiz attempt snapshot, auto-grading and gradebook ingestion
 *   - final grade publication and automatic certificate issuance
 *   - admin user creation
 *   - admin notification creation with delivery status
 *   - admin notification list by user
 *   - identity privacy export
 *   - identity user deactivation
 *
 * Prerequisite: local backend cluster running with demo admin data. Direct service checks run inside
 * the Docker network by default because app services are intentionally not published to the host.
 */

const API_BASE = stripTrailingSlash(process.env.COURSEFLOW_API_URL ?? "http://localhost:28080/api");
const DIRECT_SERVICE_BASE = stripTrailingSlash(
  process.env.COURSEFLOW_DIRECT_SERVICE_URL ?? "http://course-service:8080"
);
const DIRECT_SERVICE_TRANSPORT = (process.env.COURSEFLOW_DIRECT_SERVICE_TRANSPORT ?? "auto").toLowerCase();
const DIRECT_SERVICE_DOCKER_NETWORK =
  process.env.COURSEFLOW_SMOKE_DOCKER_NETWORK ?? "courseflow-v2-backend_default";
const CURL_IMAGE = process.env.COURSEFLOW_SMOKE_CURL_IMAGE ?? "curlimages/curl:8.10.1";
const ADMIN_EMAIL = process.env.COURSEFLOW_SMOKE_ADMIN_EMAIL ?? "admin@courseflow.local";
const LEARNER_EMAIL = process.env.COURSEFLOW_SMOKE_LEARNER_EMAIL ?? "student@courseflow.local";
const LEARNER_USER_ID = process.env.COURSEFLOW_SMOKE_LEARNER_USER_ID ?? "4";
const DEPARTMENT_ID =
  process.env.COURSEFLOW_SMOKE_DEPARTMENT_ID ?? "20000000-0000-0000-0000-000000000001";
const RUN_ID = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
const DISPOSABLE_EMAIL =
  process.env.COURSEFLOW_SMOKE_USER_EMAIL ?? `smoke+${RUN_ID}@courseflow.local`;
const DISPOSABLE_PASSWORD = process.env.COURSEFLOW_SMOKE_USER_PASSWORD ?? "SmokeStrong1!";

let adminToken = "";

const checks = [];

async function main() {
  console.log(`CourseFlow Product Hardening smoke`);
  console.log(`API: ${API_BASE}`);
  console.log(`Disposable user: ${DISPOSABLE_EMAIL}`);

  adminToken = requiredBearerToken("COURSEFLOW_SMOKE_ADMIN_TOKEN");
  const learnerToken = requiredBearerToken("COURSEFLOW_SMOKE_LEARNER_TOKEN");
  record("admin bearer token supplied", Boolean(adminToken), `admin=${ADMIN_EMAIL}`);
  record("learner bearer token supplied", Boolean(learnerToken), `learner=${LEARNER_EMAIL} userId=${LEARNER_USER_ID}`);

  const courses = await get("/v1/courses");
  const courseRows = list(courses);
  record("public catalog", courseRows.length > 0, `${courseRows.length} course(s) returned`);
  const smokeCourseId = courseRows.find((row) => row.id)?.id;
  record("public catalog exposes course id", Boolean(smokeCourseId), `courseId=${smokeCourseId ?? "missing"}`);
  await assertCourseModulesProtected(smokeCourseId);
  const modules = await getAdmin(`/v1/courses/${encodeURIComponent(smokeCourseId)}/modules`);
  record("admin reads protected modules", Array.isArray(modules), `${modules.length} module(s) returned`);

  await assertDirectIdentitySpoofRejected();

  const user = await postAdmin("/admin/v1/users", {
    email: DISPOSABLE_EMAIL,
    fullName: `Smoke User ${RUN_ID}`,
    role: "STUDENT",
    password: DISPOSABLE_PASSWORD
  });
  record("admin create disposable user", Boolean(user.id), `userId=${user.id}`);

  await assertUnreadyReferencesBlocked();
  await runGoldenLearningFlow({ id: LEARNER_USER_ID, email: LEARNER_EMAIL }, learnerToken);

  const notification = await postAdmin("/admin/v1/notifications", {
    userId: String(user.id),
    notificationType: "SYSTEM",
    title: `Smoke ${RUN_ID}`,
    body: "Product hardening smoke notification"
  });
  record(
    "notification delivery status",
    ["PENDING", "DELIVERED", "FAILED"].includes(notification.deliveryStatus),
    `status=${notification.deliveryStatus ?? "missing"}`
  );

  const inbox = await getAdmin(`/admin/v1/notifications?userId=${encodeURIComponent(String(user.id))}`);
  const inboxRows = list(inbox);
  record(
    "admin list disposable inbox",
    inboxRows.some((row) => row.id === notification.id),
    `${inboxRows.length} notification row(s)`
  );

  const privacyExport = await getAdmin(`/admin/v1/users/${user.id}/privacy-export`);
  record(
    "privacy export",
    privacyExport.profile?.id === user.id && Array.isArray(privacyExport.roleAssignments),
    `roleGrants=${privacyExport.roleAssignments?.length ?? "missing"}`
  );

  const deactivated = await postAdmin(`/admin/v1/users/${user.id}/deactivate`, {
    reason: `Product hardening smoke ${RUN_ID}`
  });
  record("deactivate disposable user", deactivated.status === "DEACTIVATED", `status=${deactivated.status}`);

  printSummary();
}

async function runGoldenLearningFlow(user, learnerToken) {
  const code = `SMK${RUN_ID.slice(-8)}`;
  const slug = `smoke-golden-${RUN_ID.toLowerCase()}`;
  let draft = await postAdmin("/admin/v1/authoring/courses", {
    code,
    title: `Smoke Golden Flow ${RUN_ID}`,
    slug,
    summary: "Disposable course created by the Product Hardening gateway smoke test.",
    departmentId: DEPARTMENT_ID,
    level: "BEGINNER",
    listPrice: 100,
    currency: "USD"
  });
  const courseId = draft.courseId;
  record("authoring create disposable course", Boolean(courseId), `courseId=${courseId}`);

  draft = await postAdmin(`/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules`, {
    title: "Smoke onboarding",
    description: "Disposable module for the golden learning path.",
    status: "DRAFT"
  });
  const draftModule = last(draft.modules);
  const draftModuleId = draftModule?.moduleId;
  record("authoring create module", Boolean(draftModuleId), `moduleId=${draftModuleId ?? "missing"}`);

  const refs = await createReadyLearningRefs(courseId);

  draft = await postAdmin(
    `/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(draftModuleId)}/items`,
    {
      itemType: "DOCUMENT",
      title: "Smoke document",
      description: "Disposable required document for learner progress verification.",
      documentMediaIds: [refs.document.id],
      estimatedMinutes: 2,
      required: true
    }
  );
  const draftDocumentItem = last(draft.modules?.find((module) => module.moduleId === draftModuleId)?.items);
  record(
    "authoring create required document item",
    Boolean(draftDocumentItem?.itemId && draftDocumentItem?.documentMediaIds?.includes(refs.document.id)),
    `itemId=${draftDocumentItem?.itemId ?? "missing"} mediaId=${refs.document.id}`
  );

  draft = await postAdmin(
    `/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(draftModuleId)}/items`,
    {
      itemType: "VIDEO",
      title: "Smoke video",
      description: "Disposable ready video for publish readiness verification.",
      videoMediaId: refs.video.id,
      estimatedMinutes: 1,
      required: false
    }
  );
  const draftVideoItem = last(draft.modules?.find((module) => module.moduleId === draftModuleId)?.items);
  record(
    "authoring create ready video item",
    draftVideoItem?.videoMediaId === refs.video.id,
    `itemId=${draftVideoItem?.itemId ?? "missing"} videoId=${refs.video.id}`
  );

  draft = await postAdmin(
    `/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(draftModuleId)}/items`,
    {
      itemType: "QUIZ",
      refId: refs.quiz.id,
      title: "Smoke quiz",
      description: "Disposable published quiz linked before course publish.",
      estimatedMinutes: 3,
      required: false
    }
  );
  const draftQuizItem = last(draft.modules?.find((module) => module.moduleId === draftModuleId)?.items);
  record(
    "authoring create published quiz item",
    draftQuizItem?.refId === refs.quiz.id,
    `itemId=${draftQuizItem?.itemId ?? "missing"} refId=${draftQuizItem?.refId ?? "missing"} quizId=${refs.quiz.id}`
  );

  draft = await postAdmin(
    `/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(draftModuleId)}/items`,
    {
      itemType: "ASSIGNMENT",
      refId: refs.assignment.id,
      title: "Smoke assignment",
      description: "Disposable published assignment linked before course publish.",
      estimatedMinutes: 4,
      required: false
    }
  );
  const draftAssignmentItem = last(draft.modules?.find((module) => module.moduleId === draftModuleId)?.items);
  record(
    "authoring create published assignment item",
    draftAssignmentItem?.refId === refs.assignment.id,
    `itemId=${draftAssignmentItem?.itemId ?? "missing"} refId=${draftAssignmentItem?.refId ?? "missing"} assignmentId=${refs.assignment.id}`
  );

  draft = await postAdmin(`/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/submit-review`);
  record("authoring submit review", draft.reviewState === "IN_REVIEW", `reviewState=${draft.reviewState}`);

  draft = await postAdmin(`/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/approve`, {
    note: `Product hardening smoke ${RUN_ID}`
  });
  record("authoring approve review", draft.reviewState === "APPROVED", `reviewState=${draft.reviewState}`);

  const published = await postAdmin(`/admin/v1/courses/${encodeURIComponent(courseId)}/publish`, {});
  record("publish disposable course", published.status === "PUBLISHED", `status=${published.status}`);

  await expectStatus(
    "learner cannot download snapshot document before enrollment",
    "GET",
    `/v1/courses/${encodeURIComponent(courseId)}/media/assets/${encodeURIComponent(refs.document.id)}/download-url`,
    undefined,
    learnerToken,
    [403]
  );

  const enrollment = await postAdmin("/admin/v1/enrollments", {
    courseId,
    studentId: String(user.id)
  });
  record("admin enroll disposable learner", enrollment.status === "ACTIVE", `enrollmentId=${enrollment.id}`);

  const nextAction = await getBearer("/v1/learning/next-action", learnerToken);
  record(
    "learner next action bff",
    ["START_COURSE", "CONTINUE_ITEM"].includes(nextAction.kind)
      && nextAction.course?.id === courseId
      && Boolean(nextAction.href),
    `kind=${nextAction.kind ?? "missing"} href=${nextAction.href ?? "missing"}`
  );

  const learnerModules = await getBearer(`/v1/courses/${encodeURIComponent(courseId)}/modules`, learnerToken);
  const learnerModule = learnerModules.find((module) => module.id === draftModuleId) ?? learnerModules[0];
  const learnerItem = first(learnerModule?.items);
  const learnerItemId = learnerItem?.id ?? learnerItem?.itemId;
  record(
    "learner reads published modules",
    Boolean(learnerModule?.id && learnerItemId),
    `${learnerModules.length} module(s) returned`
  );
  record(
    "published snapshot contains ready refs",
    moduleContainsRefs(learnerModule, refs),
    `${learnerModule?.items?.length ?? 0} item(s) in learner snapshot`
  );

  const documentDownload = await getBearer(
    `/v1/courses/${encodeURIComponent(courseId)}/media/assets/${encodeURIComponent(refs.document.id)}/download-url`,
    learnerToken
  );
  record(
    "learner downloads snapshot document",
    Boolean(documentDownload.downloadUrl && documentDownload.storageKey),
    `storageKey=${documentDownload.storageKey ?? "missing"}`
  );

  await expectStatus(
    "learner cannot download document outside snapshot",
    "GET",
    `/v1/courses/${encodeURIComponent(courseId)}/media/assets/${encodeURIComponent(refs.unreferencedDocument.id)}/download-url`,
    undefined,
    learnerToken,
    [403]
  );

  const itemProgress = await postBearer(
    `/v1/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(learnerModule.id)}/items/${encodeURIComponent(learnerItemId)}/progress`,
    { progressType: "MANUAL" },
    learnerToken
  );
  record(
    "learner completes required item",
    itemProgress.status === "COMPLETED",
    `status=${itemProgress.status ?? "missing"}`
  );

  const progress = await getBearer(`/v1/courses/${encodeURIComponent(courseId)}/modules/progress`, learnerToken);
  record(
    "learner course progress",
    progress.completed === true && progress.completedRequiredItems >= 1,
    `percent=${progress.percentComplete ?? "missing"}`
  );

  const completedEnrollment = await waitForEnrollmentStatus(courseId, String(user.id), "COMPLETED");
  record(
    "course completion updates enrollment",
    completedEnrollment.status === "COMPLETED",
    `status=${completedEnrollment.status}`
  );

  await runAssessmentCredentialFlow(courseId, refs.quiz, user, learnerToken);

  const archived = await postAdmin(`/admin/v1/courses/${encodeURIComponent(courseId)}/archive`, {});
  record("archive disposable course", archived.status === "ARCHIVED", `status=${archived.status}`);
}

async function assertUnreadyReferencesBlocked() {
  const code = `SMKN${RUN_ID.slice(-8)}`;
  const slug = `smoke-negative-${RUN_ID.toLowerCase()}`;
  let draft = await postAdmin("/admin/v1/authoring/courses", {
    code,
    title: `Smoke Negative Refs ${RUN_ID}`,
    slug,
    summary: "Disposable negative-readiness course created by the Product Hardening smoke test.",
    departmentId: DEPARTMENT_ID,
    level: "BEGINNER"
  });
  const courseId = draft.courseId;
  record("negative authoring create disposable course", Boolean(courseId), `courseId=${courseId}`);

  draft = await postAdmin(`/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules`, {
    title: "Smoke unready references",
    description: "Disposable module for readiness gate verification.",
    status: "DRAFT"
  });
  const moduleId = last(draft.modules)?.moduleId;
  record("negative authoring create module", Boolean(moduleId), `moduleId=${moduleId ?? "missing"}`);

  const draftQuiz = await createDraftSmokeQuiz(courseId, "Negative draft quiz");
  const draftAssignment = await createSmokeAssignment(courseId, { title: "Negative draft assignment", publish: false });

  draft = await postAdmin(
    `/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(moduleId)}/items`,
    {
      itemType: "QUIZ",
      refId: draftQuiz.id,
      title: "Draft quiz should block readiness",
      description: "This item intentionally points at a draft quiz.",
      required: true
    }
  );
  const draftQuizItem = last(draft.modules?.find((module) => module.moduleId === moduleId)?.items);
  record(
    "negative authoring link draft quiz",
    draftQuizItem?.refId === draftQuiz.id,
    `itemId=${draftQuizItem?.itemId ?? "missing"} refId=${draftQuizItem?.refId ?? "missing"} quizId=${draftQuiz.id}`
  );

  draft = await postAdmin(
    `/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(moduleId)}/items`,
    {
      itemType: "ASSIGNMENT",
      refId: draftAssignment.id,
      title: "Draft assignment should block readiness",
      description: "This item intentionally points at a draft assignment.",
      required: false
    }
  );
  record(
    "negative authoring link draft assignment",
    last(draft.modules?.find((module) => module.moduleId === moduleId)?.items)?.refId === draftAssignment.id,
    `assignmentId=${draftAssignment.id}`
  );

  await expectStatus(
    "review blocks draft refs",
    "POST",
    `/admin/v1/authoring/courses/${encodeURIComponent(courseId)}/submit-review`,
    undefined,
    adminToken,
    [400]
  );

  await expectStatus(
    "publish blocks unapproved draft",
    "POST",
    `/admin/v1/courses/${encodeURIComponent(courseId)}/publish`,
    {},
    adminToken,
    [400]
  );

  const archived = await postAdmin(`/admin/v1/courses/${encodeURIComponent(courseId)}/archive`, {});
  record("archive negative course", archived.status === "ARCHIVED", `status=${archived.status}`);
}

async function createReadyLearningRefs(courseId) {
  const document = await createSmokeDocument("smoke-document.pdf", "Snapshot document");
  const unreferencedDocument = await createSmokeDocument("smoke-outside-snapshot.pdf", "Outside snapshot document");
  const video = await createSmokeVideo(courseId);
  const quiz = await createSmokeQuiz(courseId);
  const assignment = await createSmokeAssignment(courseId);
  return { document, unreferencedDocument, video, quiz, assignment };
}

async function createSmokeDocument(fileName, label) {
  const contentType = "application/pdf";
  const bytes = textBytes(`%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n% ${label} ${RUN_ID}\n%%EOF\n`);
  const upload = await postAdmin("/admin/v1/media/assets/upload-url", {
    fileName,
    contentType
  });
  record(`media presign ${label}`, Boolean(upload.storageKey && upload.uploadUrl), `storageKey=${upload.storageKey ?? "missing"}`);

  await putPresignedObject(`media upload ${label}`, upload.uploadUrl, bytes, contentType);

  const asset = await postAdmin("/admin/v1/media/assets", {
    fileName,
    contentType,
    storageKey: upload.storageKey,
    sizeBytes: bytes.byteLength
  });
  record(`media register ${label}`, Boolean(asset.id), `mediaId=${asset.id ?? "missing"}`);
  return asset;
}

async function createSmokeVideo(courseId) {
  const contentType = "video/mp4";
  const bytes = textBytes(`courseflow smoke mp4 placeholder ${RUN_ID}\n`);
  const upload = await postAdmin("/admin/v1/media/videos/upload-url", {
    fileName: "smoke-video.mp4",
    contentType
  });
  record("video presign source upload", Boolean(upload.storageKey && upload.uploadUrl), `storageKey=${upload.storageKey ?? "missing"}`);

  await putPresignedObject("video upload source object", upload.uploadUrl, bytes, contentType);

  const video = await postAdmin("/admin/v1/media/videos", {
    courseId,
    title: `Smoke Video ${RUN_ID}`,
    sourceStorageKey: upload.storageKey,
    durationSeconds: 1
  });
  record(
    "video register ready asset",
    Boolean(video.id) && video.status === "READY",
    `videoId=${video.id ?? "missing"} status=${video.status ?? "missing"}`
  );
  return video;
}

async function createDraftSmokeQuiz(courseId, titlePrefix = "Smoke checkpoint") {
  const quiz = await postAdmin("/admin/v1/quizzes", {
    courseId,
    title: `${titlePrefix} ${RUN_ID}`,
    durationMinutes: 5,
    attemptsAllowed: 1,
    randomizeQuestions: false,
    randomizeOptions: false,
    gracePeriodSeconds: 60,
    scoringMethod: "HIGHEST",
    timeLimitEnforced: true,
    showCorrectAnswers: false,
    status: "DRAFT"
  });
  record("quiz create draft", Boolean(quiz.id), `quizId=${quiz.id ?? "missing"}`);
  return quiz;
}

async function createSmokeQuiz(courseId) {
  let quiz = await createDraftSmokeQuiz(courseId);

  quiz = await postAdmin(`/admin/v1/quizzes/${encodeURIComponent(quiz.id)}/questions`, {
    type: "MULTIPLE_CHOICE",
    stem: "Which service owns CourseFlow public search documents?",
    difficulty: "EASY",
    points: 10,
    position: 1,
    status: "ACTIVE",
    options: [
      { label: "A", content: "course-service", correct: false },
      { label: "B", content: "search-service", correct: true }
    ]
  });
  const question = first(quiz.questions);
  record("quiz create auto-graded question", Boolean(question?.id), `questionId=${question?.id ?? "missing"}`);

  quiz = await putAdmin(`/admin/v1/quizzes/${encodeURIComponent(quiz.id)}`, {
    title: quiz.title,
    openAt: null,
    closeAt: null,
    durationMinutes: 5,
    attemptsAllowed: 1,
    randomizeQuestions: false,
    randomizeOptions: false,
    gracePeriodSeconds: 60,
    scoringMethod: "HIGHEST",
    timeLimitEnforced: true,
    showCorrectAnswers: false,
    status: "PUBLISHED"
  });
  record("quiz publish", quiz.status === "PUBLISHED", `status=${quiz.status}`);
  return quiz;
}

async function createSmokeAssignment(courseId, options = {}) {
  let assignment = await postAdmin("/admin/v1/assignments", {
    courseId,
    title: `${options.title ?? "Smoke assignment"} ${RUN_ID}`,
    assignmentType: "TEXT",
    instructions: "Disposable assignment for Product Hardening smoke readiness.",
    dueAt: "2099-01-01T00:00:00Z",
    maxScore: 10,
    submissionTypes: "TEXT",
    maxAttempts: 1,
    allowResubmission: false,
    latePenaltyPercent: 0,
    latePenaltyInterval: "NONE",
    latePenaltyMaxPercent: 0
  });
  record("assignment create draft", Boolean(assignment.id), `assignmentId=${assignment.id ?? "missing"}`);

  if (options.publish === false) {
    return assignment;
  }

  assignment = await postAdmin(`/admin/v1/assignments/${encodeURIComponent(assignment.id)}/publish`, {});
  record("assignment publish", assignment.status === "PUBLISHED", `status=${assignment.status}`);
  return assignment;
}

async function runAssessmentCredentialFlow(courseId, quiz, user, learnerToken) {
  const forbiddenStudentQuizKeys = new Set(["correct", "correctAnswer", "feedback"]);
  const learnerQuizzes = await getBearer(`/v1/quizzes?courseId=${encodeURIComponent(courseId)}`, learnerToken);
  const learnerQuiz = list(learnerQuizzes).find((row) => row.id === quiz.id);
  record(
    "learner sees sanitized quiz",
    Boolean(learnerQuiz) && !hasAnyKey(learnerQuiz, forbiddenStudentQuizKeys),
    learnerQuiz ? `quizId=${learnerQuiz.id}` : "quiz missing"
  );

  const started = await postBearer(`/v1/quizzes/${encodeURIComponent(quiz.id)}/attempts`, {}, learnerToken);
  const attempt = started.attempt ?? started;
  const attemptQuestion = first(started.questions);
  record(
    "quiz attempt snapshot",
    Boolean(attempt?.id && attempt?.deadlineAt && attemptQuestion?.id)
      && !hasAnyKey(started.questions, forbiddenStudentQuizKeys),
    `attemptId=${attempt?.id ?? "missing"}`
  );

  const submitted = await postBearer(
    `/v1/quizzes/attempts/${encodeURIComponent(attempt.id)}/submit`,
    { answers: { [attemptQuestion.id]: "B" } },
    learnerToken
  );
  record(
    "learner submits auto-graded quiz",
    submitted.status === "GRADED" && toNumber(submitted.score) === 10,
    `status=${submitted.status ?? "missing"} score=${submitted.score ?? "missing"}`
  );

  const effectiveScore = await getBearer(
    `/v1/quizzes/${encodeURIComponent(quiz.id)}/students/${encodeURIComponent(String(user.id))}/score`,
    learnerToken
  );
  record(
    "learner effective quiz score",
    toNumber(effectiveScore.effectiveScore) === 10 && effectiveScore.attemptsCounted >= 1,
    `score=${effectiveScore.effectiveScore ?? "missing"} attempts=${effectiveScore.attemptsCounted ?? "missing"}`
  );

  const gradebook = await waitFor(
    "quiz gradebook entry",
    () => getAdmin(`/admin/v1/gradebook/courses/${encodeURIComponent(courseId)}/students/${encodeURIComponent(String(user.id))}`),
    (row) => findQuizEntry(row, quiz.id)
  );
  const quizEntry = findQuizEntry(gradebook, quiz.id);
  record(
    "gradebook receives quiz score",
    Boolean(quizEntry) && toNumber(quizEntry.rawScore) === 10,
    `entryId=${quizEntry?.id ?? "missing"} score=${quizEntry?.rawScore ?? "missing"}`
  );

  await ensureQuizCategoryWeight(courseId);
  const weightedGradebook = await getAdmin(
    `/admin/v1/gradebook/courses/${encodeURIComponent(courseId)}/students/${encodeURIComponent(String(user.id))}`
  );
  record(
    "gradebook computes final score",
    toNumber(weightedGradebook.finalScore) >= 100,
    `finalScore=${weightedGradebook.finalScore ?? "missing"}`
  );

  const finalGrade = await postAdmin(
    `/admin/v1/gradebook/courses/${encodeURIComponent(courseId)}/students/${encodeURIComponent(String(user.id))}/finalize`,
    {}
  );
  record(
    "gradebook finalizes passing grade",
    finalGrade.status === "FINALIZED" && finalGrade.passed === true,
    `status=${finalGrade.status ?? "missing"} passed=${finalGrade.passed}`
  );

  const certificateRows = await waitFor(
    "certificate auto-issue",
    () => getBearer("/v1/certificates/mine", learnerToken),
    (rows) => list(rows).some((certificate) => certificate.courseId === courseId && certificate.status === "ISSUED"),
    { timeoutMs: 60000, intervalMs: 1000 }
  );
  const certificate = list(certificateRows).find(
    (row) => row.courseId === courseId && row.status === "ISSUED"
  );
  record(
    "certificate auto-issued",
    Boolean(certificate?.verificationCode),
    `certificateId=${certificate?.certificateId ?? "missing"}`
  );

  const publicVerification = await get(`/v1/certificates/verify/${encodeURIComponent(certificate.verificationCode)}`);
  record(
    "public certificate verification",
    publicVerification.valid === true
      && publicVerification.courseId === courseId
      && publicVerification.status === "ISSUED"
      && publicVerification.studentId === undefined
      && publicVerification.finalGrade === undefined,
    `valid=${publicVerification.valid} status=${publicVerification.status ?? "missing"}`
  );
}

async function waitForEnrollmentStatus(courseId, studentId, expectedStatus) {
  const rows = await waitFor(
    `enrollment ${expectedStatus}`,
    () => getAdmin(`/admin/v1/enrollments?courseId=${encodeURIComponent(courseId)}&studentId=${encodeURIComponent(studentId)}`),
    (payload) => list(payload).some((row) => row.courseId === courseId && row.studentId === studentId && row.status === expectedStatus),
    { timeoutMs: 60000, intervalMs: 1000 }
  );
  return list(rows).find((row) => row.courseId === courseId && row.studentId === studentId);
}

async function ensureQuizCategoryWeight(courseId) {
  const categories = list(await getAdmin(`/admin/v1/gradebook/courses/${encodeURIComponent(courseId)}/categories`));
  const quizCategory = categories.find((category) => category.name === "Quizzes");
  if (!quizCategory?.id) {
    throw new Error(`Quiz grade category missing for course ${courseId}`);
  }
  const weighted = toNumber(quizCategory.weightPercent) === 100
    ? quizCategory
    : await putAdmin(
        `/admin/v1/gradebook/courses/${encodeURIComponent(courseId)}/categories/${encodeURIComponent(quizCategory.id)}`,
        {
          name: "Quizzes",
          weightPercent: 100,
          aggregationMethod: quizCategory.aggregationMethod ?? "WEIGHTED_MEAN",
          dropLowest: quizCategory.dropLowest ?? 0
        }
      );
  record("gradebook weights quiz category", toNumber(weighted.weightPercent) === 100, `weight=${weighted.weightPercent}`);
}

function findQuizEntry(gradebook, quizId) {
  return list(gradebook?.entries).find((entry) => entry.title === `Quiz ${quizId}`);
}

function stripTrailingSlash(value) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function requiredBearerToken(name) {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`${name} is required. Provide a Keycloak access token for the smoke run.`);
  }
  return value.replace(/^Bearer\s+/i, "").trim();
}

async function get(path) {
  return request("GET", path);
}

async function getAdmin(path) {
  return request("GET", path, undefined, adminToken);
}

async function postAdmin(path, body) {
  return request("POST", path, body, adminToken);
}

async function putAdmin(path, body) {
  return request("PUT", path, body, adminToken);
}

async function getBearer(path, bearerToken) {
  return request("GET", path, undefined, bearerToken);
}

async function postBearer(path, body, bearerToken) {
  return request("POST", path, body, bearerToken);
}

async function request(method, path, body, bearerToken) {
  const result = await requestStatus(method, path, body, bearerToken);
  if (!result.ok) {
    throw new Error(`${method} ${path} failed: HTTP ${result.status} ${result.detail ?? ""}`.trim());
  }
  return unwrap(result.payload);
}

async function expectStatus(name, method, path, body, bearerToken, expectedStatuses) {
  const result = await requestStatus(method, path, body, bearerToken);
  const statuses = Array.isArray(expectedStatuses) ? expectedStatuses : [expectedStatuses];
  record(
    name,
    statuses.includes(result.status),
    `HTTP ${result.status}${result.detail ? ` ${truncate(result.detail, 140)}` : ""}`
  );
  return result;
}

async function requestStatus(method, path, body, bearerToken) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (bearerToken) headers.Authorization = `Bearer ${bearerToken}`;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const text = await response.text();
  const payload = text ? parseJson(text, path) : null;
  return {
    ok: response.ok,
    status: response.status,
    payload,
    detail: responseDetail(payload, text)
  };
}

async function assertDirectIdentitySpoofRejected() {
  if (!DIRECT_SERVICE_BASE || DIRECT_SERVICE_BASE.toLowerCase() === "skip") {
    record("direct service spoof rejection", true, "skipped");
    return;
  }
  const response = await directServiceRequest("GET", "/internal/courses", {
    Accept: "application/json",
    "X-User-Id": "1",
    "X-User-Email": "spoofed@example.com",
    "X-User-Role": "ADMIN",
    "X-User-Roles": "ADMIN"
  });
  record(
    "direct service spoof rejection",
    response.status === 401,
    `course-service HTTP ${response.status}`
  );
}

async function directServiceRequest(method, path, headers) {
  const url = `${DIRECT_SERVICE_BASE}${path}`;
  if (DIRECT_SERVICE_TRANSPORT === "docker"
      || (DIRECT_SERVICE_TRANSPORT === "auto" && shouldUseDockerDirectService(DIRECT_SERVICE_BASE))) {
    return dockerCurlStatus(method, url, headers);
  }
  try {
    return await fetch(url, { method, headers });
  } catch (error) {
    if (DIRECT_SERVICE_TRANSPORT === "auto") {
      return dockerCurlStatus(method, url, headers);
    }
    throw error;
  }
}

function dockerCurlStatus(method, url, headers) {
  const args = [
    "run",
    "--rm",
    "--network",
    DIRECT_SERVICE_DOCKER_NETWORK,
    CURL_IMAGE,
    "-sS",
    "-o",
    "/dev/null",
    "-w",
    "%{http_code}",
    "-X",
    method
  ];
  for (const [key, value] of Object.entries(headers ?? {})) {
    args.push("-H", `${key}: ${value}`);
  }
  args.push(url);
  const result = spawnSync("docker", args, { encoding: "utf8", maxBuffer: 1024 * 1024 });
  if (result.status !== 0) {
    throw new Error(`docker direct service request failed: ${(result.stderr || result.stdout || "").trim()}`);
  }
  return { status: Number(result.stdout.trim()) };
}

function shouldUseDockerDirectService(baseUrl) {
  try {
    const host = new URL(baseUrl).hostname;
    return Boolean(host)
      && !["localhost", "127.0.0.1", "::1"].includes(host)
      && !host.includes(".");
  } catch {
    return false;
  }
}

async function assertCourseModulesProtected(courseId) {
  const response = await fetch(`${API_BASE}/v1/courses/${encodeURIComponent(courseId)}/modules`, {
    method: "GET",
    headers: { Accept: "application/json" }
  });
  record(
    "module content requires course access",
    response.status === 401 || response.status === 403,
    `HTTP ${response.status}`
  );
}

function parseJson(text, path) {
  try {
    return JSON.parse(text);
  } catch (error) {
    return { message: `Response from ${path} is not JSON: ${text.slice(0, 160)}` };
  }
}

function responseDetail(payload, text) {
  if (payload && typeof payload === "object") {
    return payload.detail ?? payload.message ?? payload.error ?? "";
  }
  return text ?? "";
}

function unwrap(payload) {
  if (payload && typeof payload === "object" && "data" in payload) {
    return payload.data;
  }
  return payload;
}

function list(payload) {
  const data = unwrap(payload);
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    for (const key of ["content", "items", "results", "data"]) {
      if (Array.isArray(data[key])) return data[key];
    }
  }
  return [];
}

function first(items) {
  return Array.isArray(items) && items.length > 0 ? items[0] : undefined;
}

function last(items) {
  return Array.isArray(items) && items.length > 0 ? items[items.length - 1] : undefined;
}

async function waitFor(name, producer, predicate, options = {}) {
  const timeoutMs = options.timeoutMs ?? 45000;
  const intervalMs = options.intervalMs ?? 1000;
  const startedAt = Date.now();
  let lastError = "";
  while (Date.now() - startedAt <= timeoutMs) {
    try {
      const value = await producer();
      if (predicate(value)) {
        return value;
      }
      lastError = "condition not met";
    } catch (error) {
      lastError = error.message;
    }
    await sleep(intervalMs);
  }
  throw new Error(`Timed out waiting for ${name}${lastError ? ` (${lastError})` : ""}`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : NaN;
}

function hasAnyKey(value, keys) {
  if (Array.isArray(value)) {
    return value.some((item) => hasAnyKey(item, keys));
  }
  if (!value || typeof value !== "object") {
    return false;
  }
  return Object.entries(value).some(([key, child]) => keys.has(key) || hasAnyKey(child, keys));
}

async function putPresignedObject(name, uploadUrl, bytes, contentType) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: bytes
  });
  const detail = response.ok ? "" : await response.text();
  record(name, response.ok, `HTTP ${response.status}${detail ? ` ${truncate(detail, 140)}` : ""}`);
}

function moduleContainsRefs(module, refs) {
  const items = Array.isArray(module?.items) ? module.items : [];
  const documentFound = items.some((item) => item.documentMediaIds?.includes(refs.document.id));
  const videoFound = items.some((item) => item.videoMediaId === refs.video.id);
  const quizFound = items.some((item) => item.itemId === refs.quiz.id || item.refId === refs.quiz.id);
  const assignmentFound = items.some((item) => item.itemId === refs.assignment.id || item.refId === refs.assignment.id);
  return documentFound && videoFound && quizFound && assignmentFound;
}

function textBytes(value) {
  return new TextEncoder().encode(value);
}

function truncate(value, maxLength) {
  const text = String(value);
  return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
}

function record(name, passed, detail) {
  checks.push({ name, passed, detail });
  const mark = passed ? "PASS" : "FAIL";
  console.log(`[${mark}] ${name}${detail ? ` - ${detail}` : ""}`);
  if (!passed) {
    throw new Error(`Smoke check failed: ${name}`);
  }
}

function printSummary() {
  console.log("");
  console.log(`Smoke passed: ${checks.length}/${checks.length} checks`);
}

main().catch((error) => {
  console.error("");
  console.error(error.message);
  console.error("");
  console.error("Make sure the local cluster is running and SPRING_LIQUIBASE_CONTEXTS includes demo data.");
  process.exit(1);
});
