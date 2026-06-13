# CourseFlow Backend Architecture v2

## Architecture Decision

CourseFlow v2 removes the previous `core-service`. Identity, organization, course catalog, enrollment, assignments, deadlines, announcements, discussions, notifications, search, analytics, gradebook, quiz, certificate and peer review are separate services with explicit ownership.

This follows the same architectural lesson from YAS: independent business services, separate BFFs for different client experiences, separate search module, event-driven integration, and infra/observability outside business modules.

## Bounded Contexts

| Service | Owns | Does Not Own |
|---|---|---|
| identity-service | users, credentials, roles, permissions, role-permission grants, org-scoped memberships, refresh tokens, auth audit | departments, courses, enrollments |
| organization-service | departments, programs, academic terms, course sections | course content, user credentials |
| course-service | course catalog, syllabus, outcomes, material metadata, course modules and learning path structure, authoring drafts/versions, publish workflow | enrollment state, submissions |
| enrollment-service | roster, enrollment status, waitlist, capacity decisions | course content, identity credentials |
| assignment-service | assignment definition, rubric, submission metadata | uploaded file bytes, final learning profile |
| deadline-service | calendars, due windows, reminder rules and reminder runs | notification delivery |
| announcement-service | draft/scheduled/published course announcements | WebSocket/email delivery |
| portfolio-service | evidence documents, journal entries, feedback snapshots, published grade records | assignment definitions |
| discussion-service | threads, comments, reactions, moderation state, accepted answer | notification inbox |
| notification-service | inbox, delivery preference, WebSocket push, event dedup | source business event decisions |
| media-service | file metadata, upload policy, signed URLs, video assets, transcode jobs, HLS/DASH renditions, captions/transcripts, per-user video progress | course/assignment business rules |
| search-service | Elasticsearch course/content search documents | source-of-truth course data |
| analytics-service | reporting read models, progress metrics, risk signals, completion/time-spent reports, course recommendation read model | source-of-truth submissions/grades |
| gradebook-service | grade categories, grade items, weighted final grades, overrides, rubric audit | quiz attempts, assignment submissions, certificates |
| quiz-service | question banks, quiz definition, attempts, answer snapshots, auto-grading | final course grade |
| certificate-service | certificate issue/revoke/reissue, verification code, public verification audit | grade calculation |
| peer-review-service | peer review settings, reviewer assignment, review submissions, disputes, finalized peer scores | assignment definition, final gradebook calculation |
| live-session-service | live/webinar session schedule, host/co-host, attendee registration, join links, recording references, session lifecycle state | video-on-demand assets, meeting transport (Zoom/WebRTC provider) |
| review-service | course star ratings, written reviews, helpful votes, moderation state, aggregated rating read model | course catalog source-of-truth, enrollment state |

## Standard Service Layers

Every business service follows this package shape:

```text
edu.courseflow.<service>/
  config/          framework config, security, clients, messaging
  controller/      REST API boundary
  service/         use cases and transaction scripts
  repository/      persistence ports/adapters
  model/           entities/documents/domain models
  dto/             request/response DTOs, never expose entities
```

Shared modules are intentionally narrow:

| Module | Allowed |
|---|---|
| common-library | response wrapper, error model, correlation id, service-info endpoint |
| event-contracts | immutable event records only |

No shared module may contain LMS business rules.

## Gateway and Internal APIs

The `api-gateway` is the single client entrypoint and trust boundary. It strips client-supplied
`X-User-*` headers, verifies the JWT issued by `identity-service`, then injects verified identity
headers for downstream services.

```text
Client -> api-gateway -> internal domain service route
```

Clients call domain services directly through the gateway. The Next.js server layer
(`web/next-learning`) acts as the web BFF for screen-level aggregation; the React admin and Flutter
clients call the gateway directly. A shared mobile aggregation layer can be added later if request
chattiness is measured to be a problem. The gateway must stay thin: routing, auth, CORS/rate limits,
correlation id and header hardening.

## RBAC and Authorization Model

Authorization is owned by `identity-service`. The gateway only authenticates (verifies JWT) and
forwards verified identity headers; it does not make business authorization decisions. Domain services
enforce permissions using the identity headers and, where needed, an authorization check call.

Three concepts:

| Concept | Meaning | Example |
|---|---|---|
| Role | Named bundle of permissions | `STUDENT`, `INSTRUCTOR`, `TA`, `ORG_ADMIN`, `ADMIN` |
| Permission | Fine-grained capability, `resource:action` | `course:publish`, `quiz:grade`, `review:moderate` |
| Membership | Role granted, optionally scoped to an organization | user X is `INSTRUCTOR` in org `org-42` |

Roles: `STUDENT` (default learner), `TA` (assists grading/moderation in assigned courses),
`INSTRUCTOR` (authors and runs own courses), `ORG_ADMIN` (manages users/courses inside one
organization), `ADMIN` (platform-wide). `PROFESSOR` is kept as an alias of `INSTRUCTOR` for
backward compatibility with existing data.

The JWT carries `roles` and `orgId`. A service that needs a fine-grained decision calls
`POST /internal/authz/check` on identity-service with `{userId, permission, orgId?}` and caches the
result for the request. Coarse role checks (e.g. "is ADMIN") are done locally from JWT claims.

```text
Client -> api-gateway (verify JWT, inject X-User-Id/X-User-Roles/X-Org-Id)
       -> domain service (local role check, or /internal/authz/check for fine-grained permission)
```


Current route convention follows audience first, version second:

| Gateway path | Downstream intent |
|---|---|
| `/api/v1/**` | learner/public API; some GET routes are public, all other routes require JWT |
| `/api/admin/v1/**` | admin/backoffice API; gateway requires an operator role before routing |
| `/ws/**` | WebSocket/STOMP endpoint for notification-service |

Service controllers may still use `/public/**`, `/internal/**`, or `/backoffice/**` internally.
Those prefixes are implementation details behind the gateway and should not appear in client code.
True service-to-service APIs stay off the public gateway and are protected by network policy or a
short-lived internal JWT.

`identity-token-converter-service` is the internal OAuth2 token-exchange bridge. In converter mode,
the gateway validates the external identity token, calls `/oauth/token`, and forwards a short-lived
internal JWT in `X-Internal-Authorization`. `X-User-*` headers remain as a compatibility payload for
`CurrentUser`, but downstream services only trust them when `TrustedGatewayHeaderFilter` verifies
the internal JWT. Direct service clients mint service/user internal JWTs through
`common-library`'s `InternalJwtService`.

For the enterprise Keycloak target architecture and migration plan, see
[`keycloak-enterprise-adoption.md`](./keycloak-enterprise-adoption.md).

## Data Access Convention

Services may choose the persistence adapter that fits their data shape, but the choice must be
consistent inside a service and documented in code:

| Adapter | Used For |
|---|---|
| JPA | identity-service user/refresh-token aggregate |
| JdbcClient | small Postgres domain services and reporting-style reads/writes |
| MongoRepository | portfolio-service learning evidence documents |
| ElasticsearchRepository | search-service course/content search documents |

## Client/API Composition

| Client | Repo | Backend Entry |
|---|---|---|
| Next.js learner/public | `web/next-learning` | domain service routes through `api-gateway`; Next.js server layer handles screen-level aggregation for web |
| React admin/backoffice | `web/react-admin` | domain service routes through `api-gateway` |
| Flutter mobile | `app` | domain service routes through `api-gateway`; a shared aggregation layer can be added later if mobile chattiness proves to be a measured problem |

Next.js is reserved for pages that benefit from SEO or server rendering: public course catalog, course detail, learning article pages, certificate verification.

React admin is reserved for authenticated operation workflows: user/course moderation, enrollment management, announcement scheduling, analytics dashboards, discussion moderation.

## Event Flow

Core LMS flow:

```text
announcement-service --announcement.published--> notification-service, analytics-service
assignment-service   --submission.created------> portfolio-service, notification-service, analytics-service
portfolio-service    --grade.published---------> notification-service, analytics-service
deadline-service     --deadline.reminder.due---> notification-service
discussion-service   --discussion.comment.created--> notification-service, analytics-service
course-service CDC   --Debezium/Kafka----------> search-service -> Elasticsearch
course-service       --course.module.completed--> analytics-service
quiz-service         --quiz.attempt.graded-----> gradebook-service, analytics-service
gradebook-service    --gradebook.final_grade.updated--> analytics-service, certificate-service
certificate-service  --certificate.issued------> notification-service, analytics-service
peer-review-service  --peer_review.finalized---> gradebook-service, analytics-service
media-service        --media.transcode.completed--> course-service, notification-service
media-service        --video.progress.updated---> analytics-service
live-session-service --live.session.scheduled---> notification-service, deadline-service
live-session-service --live.session.started-----> notification-service
review-service       --review.posted-----------> course-service, analytics-service
```

## Outbox and Dedup

Event-producing services use a local `outbox_events` table in the same transaction as domain changes. Events are published by Debezium CDC or the `outbox-relay` service under `services/outbox-relay`.

Event-consuming services keep `processed_events` keyed by event id and consumer name. This makes Kafka at-least-once delivery safe.

## Database Boundary

Each service owns its database:

```text
cf_identity
cf_organization
cf_course
cf_enrollment
cf_assignment
cf_deadline
cf_announcement
cf_discussion
cf_notification
cf_media
cf_analytics
cf_gradebook
cf_quiz
cf_certificate
cf_peer_review
cf_live_session
cf_review
MongoDB: cf_portfolio
Elasticsearch: courseflow-course-search, courseflow-content-search
```

Schema migrations are production-safe by default. `db.changelog-master.yaml` contains schema only.
Local/demo sample data is isolated in `db.changelog-demo.yaml` and enabled by running a service with
the `demo` Spring profile.

## Development Order

1. Backend skeleton, local infra, common-library, event-contracts.
2. identity-service with auth/RBAC.
3. organization-service and course-service.
4. enrollment-service with capacity/waitlist.
5. assignment-service and media-service.
6. deadline-service and announcement-service.
7. notification-service realtime delivery.
8. portfolio-service evidence and grade publication.
9. discussion-service moderation and accepted answer.
10. outbox/dedup standardization.
11. search-service with Debezium and Elasticsearch.
12. analytics-service read models.
13. gradebook-service with weighted final grades and rubric audit.
14. quiz-service with question bank, timed attempts and auto-grading.
15. course-service module/learning-path APIs.
16. certificate-service public verification.
17. peer-review-service workflow and finalized peer scores.
18. api-gateway hardening.
