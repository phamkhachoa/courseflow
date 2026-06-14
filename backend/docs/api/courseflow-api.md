# CourseFlow API v2

Public traffic goes through `api-gateway`.

## API Entrypoints

| Gateway path | Audience | Downstream mapping |
|---|---|---|
| Keycloak OIDC endpoints | user/admin login and token lifecycle | external IAM/IdP; clients receive OAuth2/OIDC tokens |
| `/api/v1/auth/**` | legacy local compatibility only | blocked by the gateway in Keycloak/OIDC mode |
| `/api/v1/**` | learner/public API | service `/public/**` for whitelisted reads, otherwise service `/internal/**` |
| `/api/admin/v1/**` | admin/backoffice API | service `/internal/**` or identity `/backoffice/**` |
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
| Enrollment | `GET /api/v1/enrollments?courseId=&studentId=`, `GET /api/v1/enrollments/coupons`, `GET /api/v1/enrollments/{id}/promotion-application`, `POST /api/v1/enrollments`, `POST /api/v1/enrollments/promotion-preview`, `POST /api/v1/enrollments/checkout`, `POST /api/v1/waitlist`, `PUT /api/admin/v1/courses/{id}/capacity` |
| Assignment | `GET /api/v1/assignments?courseId=`, `POST /api/v1/assignments/{id}/submissions`, `POST /api/admin/v1/submissions/{id}/grade` |
| Course Modules | `GET /api/v1/courses/{courseId}/modules`, `POST /api/v1/courses/{courseId}/modules/{moduleId}/progress` |
| Deadline | `GET /api/v1/deadlines/reminders/due`, `POST /api/admin/v1/deadlines/reminders` |
| Announcement | `GET /api/v1/announcements`, `POST /api/admin/v1/announcements`, `POST /api/admin/v1/announcements/{id}/publish` |
| Portfolio | `GET /api/v1/portfolios/students/{studentId}/evidence`, `POST /api/v1/portfolios/students/{studentId}/evidence` |
| Discussion | `GET /api/v1/discussions/threads`, `POST /api/v1/discussions/threads`, `POST /api/v1/discussions/threads/{id}/comments` |
| Notification | `GET /api/v1/notifications?userId=`, `POST /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/preferences` |
| Media/Video | `GET /api/v1/media/videos/{id}`, `GET /api/v1/media/videos/{id}/playback-url`, `POST /api/admin/v1/media/videos/{id}/transcode` |

Course authoring submit-review and publish gates require purchasable pricing (`ACTIVE` or `FREE`)
because learner checkout builds promotion facts from `GET /internal/courses/{id}/pricing`.
| Search | `GET /api/v1/search/courses?q=`, `POST /api/admin/v1/search/courses` |
| Analytics | `GET /api/admin/v1/analytics/courses/{id}/metrics`, `GET /api/v1/analytics/students/{id}/recommendations` |
| Gradebook | `GET /api/v1/gradebook/courses/{courseId}/students/{studentId}`, `POST /api/admin/v1/gradebook/entries` |
| Quiz | `GET /api/v1/quizzes/{quizId}`, `POST /api/v1/quizzes/{quizId}/attempts`, `POST /api/admin/v1/quizzes/attempts/{attemptId}/answers/{questionId}/grade` |
| Certificate | `GET /api/v1/certificates/verify/{code}`, `POST /api/admin/v1/certificates/issue`, `POST /api/admin/v1/certificates/{id}/revoke` |
| Peer Review | `GET /api/v1/peer-reviews/settings/{assignmentId}`, `POST /api/admin/v1/peer-reviews/assignments`, `POST /api/v1/peer-reviews/review-assignments/{id}/submit` |
| Live Session | `GET /api/v1/live-sessions?courseId=`, `POST /api/admin/v1/live-sessions`, `POST /api/v1/live-sessions/{id}/register` |
| Review | `GET /api/v1/reviews/courses/{courseId}`, `GET /api/v1/reviews/courses/{courseId}/summary`, `POST /api/v1/reviews`, `POST /api/admin/v1/reviews/{id}/moderate` |

`GET /api/v1/users/me`, profile update, public profiles and profile summary batch are served by
`user-management-service`. In Keycloak mode, `/api/v1/auth/**` is legacy-only and blocked by the
gateway so login/session/password policy stay in Keycloak. Profile summary batch responses preserve
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
