# CourseFlow API v2

Public traffic goes through `api-gateway`.

## API Entrypoints

| Gateway path | Audience | Downstream mapping |
|---|---|---|
| Keycloak OIDC endpoints | user/admin login and token lifecycle | external IAM/IdP; clients receive OAuth2/OIDC tokens |
| `/api/v1/auth/**` | removed custom password auth | blocked by the gateway with `410 Gone` |
| `/api/v1/**` | learner/public API | service `/public/**` for whitelisted reads, otherwise service `/internal/**` |
| `/api/admin/v1/**` | admin/backoffice API | service `/internal/**` or `/backoffice/**` |
| `/ws/**` | WebSocket/STOMP | notification-service `/ws/**` |

Do not expose `/api/internal/**` or `/api/public/**` as client-facing paths. Those prefixes are
service-internal controller conventions only. Gateway routing owns the translation.

Clients (Next.js, React admin, Flutter) call the gateway directly. Next.js server-side handles screen-level aggregation for web; a shared aggregation layer can be added later for mobile if call fan-out becomes a measured problem.

## Domain API Draft

| Domain | Example APIs |
|---|---|
| Identity/Profile | Keycloak OIDC login/logout/token endpoints, `GET /api/v1/users/me`, `GET/PUT /api/v1/users/me/profile`, `GET /api/v1/profiles/{id}`, `POST /api/v1/profiles/summary:batch` |
| Admin Identity | `GET/POST /api/admin/v1/users`, `GET /api/admin/v1/users/{id}`, `GET /api/admin/v1/users/{id}/privacy-export`, `POST /api/admin/v1/users/{id}/deactivate` through user-management lifecycle facade + Keycloak Admin REST |
| Admin Access Control/RBAC | `GET /api/admin/v1/roles`, `GET /api/admin/v1/permissions`, `POST /api/admin/v1/users/{id}/assignments` |
| Organization | `GET /api/admin/v1/organizations/departments`, `GET /api/admin/v1/terms`, `POST /api/admin/v1/sections` |
| Course | `GET /api/v1/courses`, `GET /api/v1/courses/{slug}`, `GET /api/admin/v1/courses`, `GET /internal/courses/{id}/pricing`, `POST /api/admin/v1/courses/{id}/pricing`, `POST /api/admin/v1/courses/{id}/publish` |
| Course Authoring | `POST /api/admin/v1/authoring/courses`, `GET /api/admin/v1/authoring/courses/{id}/draft`, `PUT /api/admin/v1/authoring/courses/{id}/curriculum` |
| Enrollment | `GET /api/v1/enrollments?courseId=&studentId=`, `GET /api/v1/enrollments/coupons`, `POST /api/v1/enrollments`, `POST /api/v1/enrollments/promotion-preview`, `POST /api/v1/enrollments/checkout`, `POST /internal/enrollments/orders/{id}:record-payment`, `GET /api/admin/v1/enrollments/promotion-applications`, `GET /api/admin/v1/enrollments/benefit-reconciliation`, `GET /api/admin/v1/enrollments/audit`, `GET/POST /api/admin/v1/enrollments/remediation-cases/**`, `POST /api/admin/v1/enrollments/refund-drop-policy:evaluate`, `POST /api/v1/waitlist`, `PUT /api/admin/v1/courses/{id}/capacity` |
| Incentives | `POST /api/admin/v1/incentives/admin/preview`, `POST /api/admin/v1/incentives/admin/experiments:preview`, `POST /api/admin/v1/incentives/admin/fraud-score:preview`, `GET /api/admin/v1/incentives/reconciliation`, `GET /api/admin/v1/incentives/audit` |
| Assignment | `GET /api/v1/assignments?courseId=`, `GET /api/admin/v1/assignments/grading-queue?courseId=`, `POST /api/v1/assignments/{id}/submissions`, `POST /api/admin/v1/submissions/{id}/grade` |
| Course Modules | `GET /api/v1/courses/{courseId}/modules`, `GET /api/v1/courses/{courseId}/learning-path`, `POST /api/v1/courses/{courseId}/modules/{moduleId}/progress` |
| Deadline | `GET /api/v1/deadlines/reminders/due`, `POST /api/admin/v1/deadlines/reminders` |
| Announcement | `GET /api/v1/announcements`, `POST /api/admin/v1/announcements`, `POST /api/admin/v1/announcements/{id}/publish` |
| Portfolio | `GET /api/v1/portfolios/students/{studentId}/evidence`, `POST /api/v1/portfolios/students/{studentId}/evidence` |
| Discussion | `GET /api/v1/discussions/threads`, `POST /api/v1/discussions/threads`, `POST /api/v1/discussions/threads/{id}/comments` |
| Notification | `GET /api/v1/notifications?userId=`, `GET /api/v1/notifications/stream?userId=`, `POST /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/preferences` |
| Media/Video | `GET /api/v1/media/videos/{id}`, `GET /api/v1/media/videos/{id}/playback-url`, `POST /api/admin/v1/media/videos/{id}/transcode` |

Course authoring submit-review and publish gates require purchasable pricing (`ACTIVE` or `FREE`)
because learner checkout builds promotion facts from `GET /internal/courses/{id}/pricing`.
| Search | `GET /api/v1/search/courses?q=`, `POST /api/admin/v1/search/courses` |
| Analytics | `GET /api/admin/v1/analytics/courses/{id}/metrics`, `GET /api/admin/v1/analytics/courses/{id}/at-risk`, `GET /api/admin/v1/analytics/marketing/funnel`, `POST /api/admin/v1/analytics/warehouse/exports`, `POST /api/admin/v1/analytics/recommendations/batch/related-course-pairs`, `POST /api/admin/v1/analytics/recommendations/batch/related-course-pairs/async`, `POST /api/admin/v1/analytics/recommendations/batch/related-course-pairs/async/{trainingRunId}/materialize`, `GET /api/v1/courses/{id}/related`, `GET /api/v1/analytics/students/{id}/recommendations` |
| Recommendation ML | `POST /api/admin/v1/recommendation-ml/related-courses:train`, `POST /api/admin/v1/recommendation-ml/related-courses:enqueue`, `GET /api/admin/v1/recommendation-ml/training-runs/{trainingRunId}`, `GET /api/admin/v1/recommendation-ml/models/active`, `POST /api/admin/v1/recommendation-ml/models/{modelVersion}:request-activation`, `POST /api/admin/v1/recommendation-ml/models/activation-requests/{approvalId}:approve`, `GET /api/admin/v1/recommendation-ml/courses/{id}/related` |
| Gradebook | `GET /api/v1/gradebook/courses/{courseId}/students/{studentId}`, `GET /api/admin/v1/gradebook/courses/{courseId}/grade-publish-audit`, `POST /api/admin/v1/gradebook/entries` |
| Quiz | `GET /api/v1/quizzes/{quizId}`, `POST /api/v1/quizzes/{quizId}/attempts`, `POST /api/admin/v1/quizzes/attempts/{attemptId}/answers/{questionId}/grade` |
| Certificate | `GET /api/v1/certificates/verify/{code}`, `GET /api/admin/v1/certificates/eligibility?courseId=&studentId=`, `POST /api/admin/v1/certificates/issue`, `POST /api/admin/v1/certificates/{id}/revoke` |
| Peer Review | `GET /api/v1/peer-reviews/settings/{assignmentId}`, `POST /api/admin/v1/peer-reviews/assignments`, `POST /api/v1/peer-reviews/review-assignments/{id}/submit` |
| Live Session | `GET /api/v1/live-sessions?courseId=`, `POST /api/admin/v1/live-sessions`, `POST /api/v1/live-sessions/{id}/register` |
| Review | `GET /api/v1/reviews/courses/{courseId}`, `GET /api/v1/reviews/courses/{courseId}/summary`, `POST /api/v1/reviews`, `POST /api/admin/v1/reviews/{id}/moderate` |

`GET /api/v1/users/me`, profile update, public profiles and profile summary batch are served by
`user-management-service`. `/api/v1/auth/**` is blocked by the gateway so login/session/password
policy stay in Keycloak. Profile summary batch responses preserve
the requested user id order and omit missing profiles.
`POST /api/admin/v1/users` creates the Keycloak account and user profile only; it does not grant a
CourseFlow product role. Operators assign product roles separately through
`POST /api/admin/v1/users/{id}/assignments` with explicit `roleId`, `scopeType` and `scopeId`.
Public profile reads only return profiles marked `PUBLIC`; `PRIVATE` and `ORG` profiles are not
exposed through the public profile endpoint. Authenticated/internal surfaces that need avatar/name
for enrolled users should use the profile summary batch endpoint instead.

`POST /internal/authz/check` accepts `scopeType` values `PLATFORM`, `ORG`, `DEPARTMENT`, `COURSE`
and `SECTION`. `PLATFORM` must be sent without `scopeId`; every other scope requires a non-empty
`scopeId`. The requested scope must be compatible with the permission definition scope maintained by
`access-control-service`; mismatches are rejected before an allow/deny decision is returned.
When checking a child resource, only the domain service that owns the resource topology should pass
server-derived `ancestorScopes`, for example `{scopeType:"COURSE", scopeId:"course-1",
ancestorScopes:[{scopeType:"DEPARTMENT", scopeId:"dept-1"}]}`. Access-control then evaluates role
assignments granted at platform, requested scope and supplied ancestor scopes without learning
course/organization topology itself. `ancestorScopes` are accepted only from service internal JWTs
with `internal:authz:assert-topology`; never forward client-supplied ancestor paths directly.

`POST /internal/analytics/marketing/funnel/events` is not a client API. Trusted services may use it
to feed shadow funnel read-model events when their internal JWT carries
`internal:analytics:funnel-write`; writes are idempotent by event id.

`recommendation-ml-service` is an internal/admin Python ML boundary for recommendation only. Trusted
batch callers must use `internal:recommendation-ml:train`; inference callers must use
`internal:recommendation-ml:infer`; model/training operations such as cancel, requeue, audit reads
and activation approval require `internal:recommendation-ml:ops` or a verified platform-admin user
token. Training requests send hashed principals plus course
interactions, not raw learner profile data. The Python project owns recommendation training runs,
model versioning, Alembic migrations, quality counters and reason-coded related-course scores. The
service fails closed when internal JWT issuer, audience and verifier material are not configured. For
production, callers should prefer async training: analytics submits `related-courses:enqueue`, an ML
worker claims `QUEUED` jobs, stale `RUNNING` jobs are requeued or failed by lease recovery, and
analytics tracks completed runs in `recommendation_ml_training_jobs`. The scheduled materializer claims
tracker rows through a DB-backed lease before projecting completed `ACTIVE` runs into its learner read
model. A run that produces recommendations but misses activation quality thresholds
ends as `QUALITY_GATE_FAILED` and leaves the previous active model/read model untouched. In
production, passing runs become `PENDING_ACTIVATION` candidates until a separate ops checker approves
activation; only then does analytics project the ML read model. Rejected candidates become
`ACTIVATION_REJECTED` and never replace the current learner read model. ML ops can
list training runs/model versions, request prior-model reactivation with mandatory reason/evidence,
and audit all model activations through `recommendation_model_ops_audit`. Prior-model reactivation
uses maker-checker approval: each model can have only one pending activation request, the requester
cannot approve/reject their own request, and direct activation is disabled. Operators can also
cancel/requeue
eligible async training runs with mandatory reason/evidence; those changes are recorded in
`recommendation_training_ops_audit`. The service also exposes `/actuator/prometheus` metrics for
training run status counts, stale worker leases, queue/running age, active-model freshness, migration
readiness and metrics refresh failures. The sync
`related-courses:train` endpoint remains for backward-compatible internal callers.
Learner traffic still reads related courses through `analytics-service`, which filters unpublished
related courses and falls back to behavioral recommendations if ML is unavailable.

## Response Rules

All services use:

```json
{
  "data": {},
  "traceId": "correlation-id",
  "timestamp": "2026-06-07T00:00:00Z"
}
```

Error responses use:

```json
{
  "code": "COURSE_NOT_FOUND",
  "message": "Course does not exist",
  "traceId": "correlation-id",
  "timestamp": "2026-06-07T00:00:00Z"
}
```
