# CourseFlow API v2

Public traffic goes through `api-gateway`.

## API Entrypoints

| Gateway path | Audience | Downstream mapping |
|---|---|
| `/api/v1/auth/**` | user/admin login and token lifecycle | identity-service `/auth/**` |
| `/api/v1/**` | learner/public API | service `/public/**` for whitelisted reads, otherwise service `/internal/**` |
| `/api/admin/v1/**` | admin/backoffice API | service `/internal/**` or identity `/backoffice/**` |
| `/ws/**` | WebSocket/STOMP | notification-service `/ws/**` |

Do not expose `/api/internal/**` or `/api/public/**` as client-facing paths. Those prefixes are
service-internal controller conventions only. Gateway routing owns the translation.

Clients (Next.js, React admin, Flutter) call the gateway directly. Next.js server-side handles screen-level aggregation for web; a shared aggregation layer can be added later for mobile if call fan-out becomes a measured problem.

## Domain API Draft

| Domain | Example APIs |
|---|---|
| Identity | `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /api/v1/users/me` |
| Admin Identity/RBAC | `GET /api/admin/v1/users`, `GET /api/admin/v1/roles`, `GET /api/admin/v1/permissions`, `POST /api/admin/v1/users/{id}/assignments` |
| Organization | `GET /api/admin/v1/organizations/departments`, `GET /api/admin/v1/terms`, `POST /api/admin/v1/sections` |
| Course | `GET /api/v1/courses`, `GET /api/v1/courses/{slug}`, `GET /api/admin/v1/courses`, `POST /api/admin/v1/courses/{id}/publish` |
| Course Authoring | `POST /api/admin/v1/authoring/courses`, `GET /api/admin/v1/authoring/courses/{id}/draft`, `PUT /api/admin/v1/authoring/courses/{id}/curriculum` |
| Enrollment | `GET /api/v1/enrollments?courseId=&studentId=`, `POST /api/v1/enrollments`, `POST /api/v1/waitlist`, `PUT /api/admin/v1/courses/{id}/capacity` |
| Assignment | `GET /api/v1/assignments?courseId=`, `POST /api/v1/assignments/{id}/submissions`, `POST /api/admin/v1/submissions/{id}/grade` |
| Course Modules | `GET /api/v1/courses/{courseId}/modules`, `POST /api/v1/courses/{courseId}/modules/{moduleId}/progress` |
| Deadline | `GET /api/v1/deadlines/reminders/due`, `POST /api/admin/v1/deadlines/reminders` |
| Announcement | `GET /api/v1/announcements`, `POST /api/admin/v1/announcements`, `POST /api/admin/v1/announcements/{id}/publish` |
| Portfolio | `GET /api/v1/portfolios/students/{studentId}/evidence`, `POST /api/v1/portfolios/students/{studentId}/evidence` |
| Discussion | `GET /api/v1/discussions/threads`, `POST /api/v1/discussions/threads`, `POST /api/v1/discussions/threads/{id}/comments` |
| Notification | `GET /api/v1/notifications?userId=`, `POST /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/preferences` |
| Media/Video | `GET /api/v1/media/videos/{id}`, `GET /api/v1/media/videos/{id}/playback-url`, `POST /api/admin/v1/media/videos/{id}/transcode` |
| Search | `GET /api/v1/search/courses?q=`, `POST /api/admin/v1/search/courses` |
| Analytics | `GET /api/admin/v1/analytics/courses/{id}/metrics`, `GET /api/v1/analytics/students/{id}/recommendations` |
| Gradebook | `GET /api/v1/gradebook/courses/{courseId}/students/{studentId}`, `POST /api/admin/v1/gradebook/entries` |
| Quiz | `GET /api/v1/quizzes/{quizId}`, `POST /api/v1/quizzes/{quizId}/attempts`, `POST /api/admin/v1/quizzes/attempts/{attemptId}/answers/{questionId}/grade` |
| Certificate | `GET /api/v1/certificates/verify/{code}`, `POST /api/admin/v1/certificates/issue`, `POST /api/admin/v1/certificates/{id}/revoke` |
| Peer Review | `GET /api/v1/peer-reviews/settings/{assignmentId}`, `POST /api/admin/v1/peer-reviews/assignments`, `POST /api/v1/peer-reviews/review-assignments/{id}/submit` |
| Live Session | `GET /api/v1/live-sessions?courseId=`, `POST /api/admin/v1/live-sessions`, `POST /api/v1/live-sessions/{id}/register` |
| Review | `GET /api/v1/reviews/courses/{courseId}`, `GET /api/v1/reviews/courses/{courseId}/summary`, `POST /api/v1/reviews`, `POST /api/admin/v1/reviews/{id}/moderate` |

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
