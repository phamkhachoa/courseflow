# CourseFlow Backend Architecture v2

## Architecture Decision

CourseFlow v2 removes the previous `core-service`. Identity, organization, course catalog, enrollment, assignments, deadlines, announcements, discussions, notifications, search, analytics, gradebook, quiz, certificate and peer review are separate services with explicit ownership.

This follows the same architectural lesson from YAS: independent business services, separate BFFs for different client experiences, separate search module, event-driven integration, and infra/observability outside business modules.

## Bounded Contexts

| Service | Owns | Does Not Own |
|---|---|---|
| keycloak | external IAM/IdP: login, SSO, MFA, password policy, sessions, OAuth2/OIDC access tokens, federation, JWKS/key rotation | LMS course/section permissions, profile directory |
| discovery-service | internal service registry for backend application services; lets gateway and services locate each other without static host ports | authentication, authorization, public routing policy |
| access-control-service | CourseFlow product authorization, Keycloak `issuer + subject` mapping, scoped roles, permissions, role grants, authorization audit | login, password, MFA, SSO sessions, user profile content |
| user-management-service | display name, avatar, bio, locale/timezone, public profile, profile summaries and user directory | login, password, token issuance, role/permission decisions |
| organization-service | departments, programs, academic terms, course sections | course content, user credentials |
| course-service | course catalog, syllabus, outcomes, material metadata, course modules and learning path structure, authoring drafts/versions, publish workflow | enrollment state, submissions |
| enrollment-service | roster, enrollment status, waitlist, capacity decisions | course content, identity credentials |
| assignment-service | assignment definition, rubric, submission metadata | uploaded file bytes, final learning profile |
| deadline-service | calendars, due windows, reminder rules and reminder runs | notification delivery |
| announcement-service | draft/scheduled/published course announcements | WebSocket/email delivery |
| portfolio-service | evidence documents, journal entries, feedback snapshots, published grade records | assignment definitions |
| discussion-service | threads, comments, reactions, moderation state, accepted answer | notification inbox |
| notification-service | inbox, delivery preference, WebSocket/SSE push, event dedup | source business event decisions |
| media-service | file metadata, upload policy, signed URLs, video assets, transcode jobs, HLS/DASH renditions, captions/transcripts, per-user video progress | course/assignment business rules |
| search-service | Elasticsearch course/content search documents | source-of-truth course data |
| analytics-service | reporting read models, progress metrics, risk signals, completion/time-spent reports, recommendation tracking ingestion, manual curated related courses, learner-facing related-course read model and marketing funnel read models | source-of-truth submissions/grades, marketing attribution source events, ML model registry/training/inference |
| recommendation-ml-service | standalone Python ML project for the related-course recommendation use case: training pipelines, model registry, implicit collaborative filtering, versioned related-course scores and internal inference endpoints | learner-facing read model, manual curation, tracking ingestion, course publication truth, other ML use cases |
| gradebook-service | grade categories, grade items, weighted final grades, overrides, rubric audit | quiz attempts, assignment submissions, certificates |
| quiz-service | question banks, quiz definition, attempts, answer snapshots, auto-grading | final course grade |
| certificate-service | certificate issue/revoke/reissue, verification code, public verification audit | grade calculation |
| peer-review-service | peer review settings, reviewer assignment, review submissions, disputes, finalized peer scores | assignment definition, final gradebook calculation |
| live-session-service | live/webinar session schedule, host/co-host, attendee registration, join links, recording references, session lifecycle state | video-on-demand assets, meeting transport (Zoom/WebRTC provider) |
| review-service | course star ratings, written reviews, helpful votes, moderation state, aggregated rating read model | course catalog source-of-truth, enrollment state |

Analytics marketing funnel support is a read-model boundary. Admins read aggregates through
`GET /api/admin/v1/analytics/marketing/funnel`; trusted services feed shadow funnel events through
`POST /internal/analytics/marketing/funnel/events` with an idempotent event id. The ingestion API
accepts only the fixed stage taxonomy and bounded non-PII dimension codes; client-facing tracking and
full attribution remain outside analytics-service.

Course recommendation ML is a separate Python service boundary. `analytics-service` collects bounded
recommendation events and manual related-course overrides; it sends hashed learner/session
interactions to `recommendation-ml-service` over internal JWT with
`internal:recommendation-ml:train`. Production training should use the async queue:
`analytics-service` submits `related-courses:enqueue`, a Python worker claims `QUEUED` jobs with DB
row locks, stale `RUNNING` jobs are requeued or failed by lease recovery, and analytics tracks each
training run in `recommendation_ml_training_jobs` before a scheduled materializer claims work with a
DB-backed lease and projects approved `ACTIVE` runs into its learner read model with `source=ML`.
Stale materialization leases become claimable again after the configured lock lease. Trained models
must pass activation quality gates for event count, principal count, course count, generated pair
count and quality score;
`QUALITY_GATE_FAILED` runs are terminal and do not replace the active model. In production,
`RECOMMENDATION_ML_AUTO_ACTIVATE_TRAINED_MODELS=false` makes passing training runs create a
`CANDIDATE` model and `PENDING_ACTIVATION` run; a separate ops checker must approve activation before
the model becomes `ACTIVE`; rejected candidates become `REJECTED`/`ACTIVATION_REJECTED` without
touching the active learner read model. A partial unique index allows only one pending activation
approval per model version. The sync
`related-courses:train` path remains only as a
backward-compatible internal contract. This service is intentionally scoped to recommendation, not a
generic ML monolith. It is outside the Maven reactor so a dedicated ML team can work in Python with
FastAPI, Alembic migrations, model code and training utilities. It trains versioned
`IMPLICIT_ITEM_CF_V1` model candidates, stores scores in `cf_recommendation_ml`, and exposes internal inference
with `internal:recommendation-ml:infer`. Operators use `internal:recommendation-ml:ops` or a
verified platform-admin user token to list training runs and model versions, request reactivation of
a prior model with reason/evidence, approve it through maker-checker with a different operator,
cancel or requeue eligible async training runs, and review model and training operation audit rows.
Direct prior-model activation is disabled. The service exposes DB-backed Prometheus gauges for training
status counts, stale running jobs, queue age, pending activation approval count/age, active-model
freshness, migration readiness, metrics refresh failures, and bounded HTTP request/latency SLIs by
FastAPI route template. `analytics-service` also emits
`courseflow_analytics_recommendation_ml_client_requests_total{operation,result,reason}` so SRE can
see whether production traffic is using ML, waiting on async runs, or falling back with a bounded
reason code. The shared alert rules cover no-active-model, stale-model, consumer-fallback,
HTTP 5xx/latency, stuck-training, queue-backlog, migration-mismatch and metrics-refresh-failure cases. If training is disabled,
unavailable or insufficient,
analytics falls back to the deterministic behavioral/co-enrollment read model. The ML service must
not read or write `cf_analytics` directly. Non-recommendation ML use cases should be implemented as
sibling Python services when they have different source data, prediction consumers, ownership,
latency/SLA, risk profile, audit needs or release cadence.

See [ML Service Boundary Strategy](ml-service-boundary-strategy.md) for the SA decision on when to
create a new ML service versus extending the recommendation model stack.

Analytics warehouse export is a bounded artifact boundary, not ad hoc table dumping. Platform admins
or trusted export services with `internal:analytics:export-read` call
`POST /internal/analytics/warehouse/exports` to receive CSV content with manifest metadata:
dataset name, schema version, ordered columns, row count, truncation flag and content SHA-256. The
first datasets are `MARKETING_FUNNEL_DAILY`, `COURSE_COMPLETION_SNAPSHOT`, and
`ORG_DASHBOARD_SNAPSHOT`; larger streaming/object-store exports remain a later warehouse sink.

Learner learning path is a course-service read projection over the immutable published curriculum
snapshot plus learner progress/source status. `GET /api/v1/courses/{courseId}/learning-path`
returns module order, prerequisite lock state, item progress/source status and next action. Optional
`cohortId` and `sectionId` are request context for client navigation only; section/cohort roster
truth remains in organization/enrollment boundaries.

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
`X-User-*` headers, verifies the external OAuth2/OIDC access token, exchanges it for a CourseFlow
internal JWT, then injects verified identity headers for downstream services. Gateway routes use
service discovery (`lb://<service-id>`) instead of static internal ports; application containers all
listen on internal port `8080` and are not published directly to clients.

```text
Client -> api-gateway -> discovery-service lookup -> internal domain service route
```

Clients call domain services directly through the gateway. The Next.js server layer
(`web/next-learning`) acts as the web BFF for screen-level aggregation; the React admin and Flutter
clients call the gateway directly. A shared mobile aggregation layer can be added later if request
chattiness is measured to be a problem. The gateway must stay thin: routing, auth, CORS/rate limits,
correlation id and header hardening.

## RBAC and Authorization Model

External authentication is owned by Keycloak in the enterprise target. CourseFlow product
authorization is owned by `access-control-service`. The gateway authenticates external tokens and
forwards only identities that have been converted into short-lived internal JWTs; it does not make
business authorization decisions. Domain services enforce permissions using the verified internal
identity and, where needed, an authorization check call.

Three concepts:

| Concept | Meaning | Example |
|---|---|---|
| Role | Named bundle of permissions | `STUDENT`, `INSTRUCTOR`, `TA`, `ORG_ADMIN`, `ADMIN` |
| Permission | Fine-grained capability, `resource:action` | `course:publish`, `quiz:grade`, `review:moderate` |
| Membership | Role granted to a supported LMS scope | user X is `INSTRUCTOR` in course `course-42` |

Roles: `STUDENT` (default learner), `TA` (assists grading/moderation in assigned courses),
`INSTRUCTOR` (authors and runs own courses), `ORG_ADMIN` (manages users/courses inside one
organization), `ADMIN` (platform-wide). `PROFESSOR` is kept as an alias of `INSTRUCTOR` for
backward compatibility with existing data.

The internal JWT carries CourseFlow roles and scoped role assignments resolved by
`access-control-service`. A service that needs a fine-grained decision calls
`POST /internal/authz/check` on access-control-service with `{userId, permission, scopeType,
scopeId?}` and caches the result for the request. Coarse role checks (e.g. "is ADMIN") are done
locally from internal JWT claims. Denied authorization checks are persisted in
`access_control_audit_logs` and counted through `courseflow.access_control.authz.checks`; allowed
checks can also be audited by setting `ACCESS_CONTROL_AUDIT_AUTHZ_ALLOWED=true`.

Supported role assignment scopes are `PLATFORM`, `TENANT`, `APPLICATION`, `ORG`, `DEPARTMENT`,
`COURSE` and `SECTION`. `PLATFORM` scope must not include a `scopeId`; every other scope must include
one. `APPLICATION` scope ids use `tenantId:applicationId`. Permission definitions declare a
`scopeType` of `ANY`, `PLATFORM`, `TENANT`, `APPLICATION`, `ORG`, `DEPARTMENT`, `COURSE` or
`SECTION`, and `access-control-service` rejects authorization checks whose requested scope is wider
than the permission allows. For example, an `ORG` permission can be checked at org, department,
course or section scope, and a `TENANT` permission can be checked at tenant or application scope,
but a `PLATFORM` permission can only be checked at platform scope.
Domain services that own resource topology send server-derived `ancestorScopes` to
`/internal/authz/check` when evaluating a child resource. For example, course-service can check a
course-scoped action with the course id plus its department ancestor so a department-level role
assignment is honored without making access-control call course-service or organization-service.
Access-control accepts those ancestors only when the caller's service internal JWT has
`internal:authz:assert-topology`; exact-scope checks still need only `internal:authz:check`. Do not
forward client-supplied ancestor paths directly.

Enterprise user provisioning is explicit before first login: an invite/import/SCIM worker links the
Keycloak `issuer + subject` to a CourseFlow user through `POST /internal/identities/provision` on
`access-control-service`, then creates the directory/profile row through
`POST /internal/users/provision-profile` on `user-management-service`. The token converter only
resolves existing links; it does not silently create privileged users from arbitrary external claims.
Admin role, permission and user-role-assignment routes terminate at `access-control-service`;
the former custom password/JWT service has been decommissioned.
The compatibility `GET /api/v1/users/me` route now terminates at `user-management-service`; it
combines the CourseFlow user id/email/status/primary role resolved by `access-control-service` with
display name/avatar stored in the profile repository. This keeps client hydration off the legacy
identity database while preserving the response shape expected by clients.
Admin user list/detail reads are composed by `user-management-service` so admin screens keep one
read endpoint while display profile data stays in user-management and email/status/primary role stay
in access-control. Backoffice user-management endpoints require a valid internal JWT and ask
`access-control-service` for `platform:admin` before reading or mutating admin user data. Admin
create/deactivate/privacy export are also routed through the `user-management-service` lifecycle
facade: Keycloak owns account enablement, required actions, setup email and session logout;
access-control owns product status, role-grant revocation and the authorization decision. Admin
create user does not assign a CourseFlow product role inline; operators grant role + scope through
the `access-control-service` assignment endpoint after the account/profile exists.
Profile summary batch lookup preserves request order for UI hydration. Public profile endpoints only
return profiles whose visibility is `PUBLIC`; private and organization-scoped profile data stay on
authenticated/internal surfaces.

```text
Client -> Keycloak login -> api-gateway (verify external token)
       -> identity-token-converter-service -> access-control-service (resolve CourseFlow user/roles)
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
Notification realtime SSE is exposed through the learner API route
`GET /api/v1/notifications/stream?userId=<caller-id>`, backed by
`/internal/notifications/stream`. It is self-only, best-effort, and complements the durable inbox;
`GET /api/v1/notifications` remains the source of truth after reconnect or multi-replica fan-out
misses.

`identity-token-converter-service` is the internal OAuth2 token-exchange bridge. In converter mode,
the gateway validates the external identity token, calls `/oauth/token`, and forwards a short-lived
internal JWT in `X-Internal-Authorization`. The converter resolves external identities through
`access-control-service` before issuing internal claims. `X-User-*` headers remain as a compatibility
payload for `CurrentUser`, but downstream services only trust them when `TrustedGatewayHeaderFilter`
verifies the internal JWT. `TrustedGatewayHeaderFilter` also requires an internal JWT on
`/internal/**` and `/backoffice/**` service surfaces so direct service access cannot bypass the
gateway/admin gate. Service internal JWTs are additionally checked for endpoint-level scopes:
generic internal calls need `internal:service`, while identity resolution/provisioning, authz
checks, topology assertions, user directory, role assignment and profile surfaces require their matching
`internal:*` service scopes. Gateway and chat websocket token exchange require
`internal:token-exchange`; role and permission policy reads require `internal:role-management:read`
instead of generic `internal:service`. User internal JWTs may enter `/internal/**` only when gateway/service
identity headers are present and match the token claims. Direct service clients use
`common-library`'s `InternalJwtService` to
attach internal tokens. Local/demo environments may use HS256 local signing; the production profile
uses RS256 and defaults service clients to request service/user internal tokens from
`identity-token-converter-service` via STS-style `client_credentials` or trusted-user delegation.
Each production service has its own STS client secret, while the converter owns the per-client
secret and scope policy so one service cannot borrow another service's machine privileges.
Trusted-user delegation is not a user/role assertion API: the caller must forward the verified
inbound internal user JWT as `actor_token`, and the converter copies user identity and role
assignments only from that signed token.
Token exchange attempts emit structured audit logs through
`courseflow.security.token_converter.audit`; those logs include outcome, grant type, actor, audience
and issued scopes, but never bearer tokens or client secrets. The
production profile verifies internal JWTs through the converter JWKS endpoint so domain services no
longer rely on static public-key material. Chat WebSocket STOMP `CONNECT` also exchanges its bearer
token through the converter before trusting internal JWT claims, because the gateway cannot inspect
STOMP `CONNECT` headers after the HTTP upgrade. The next enterprise hardening step is operational
key rotation and e2e verification against the running cluster.

For the enterprise Keycloak target architecture and migration plan, see
[`keycloak-enterprise-adoption.md`](./keycloak-enterprise-adoption.md).

## Data Access Convention

Services may choose the persistence adapter that fits their data shape, but the choice must be
consistent inside a service and documented in code:

| Adapter | Used For |
|---|---|
| JPA | access-control-service authorization aggregate, user-management-service profile aggregate, rich LMS aggregates |
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

Event-producing services use a local `outbox_events` table in the same transaction as domain changes. Events are published by Debezium CDC or the `outbox-relay` service under `services/outbox-relay`. The relay owns its own checkpoint, delivery-state, and dead-letter tables, exposes admin DLQ inspect endpoints plus maker-checker gated live replay/discard, and does not migrate producer service schemas.

Event-consuming services keep `processed_events` keyed by event id and consumer name. This makes Kafka at-least-once delivery safe.

## Database Boundary

Each service owns its database:

```text
cf_organization
cf_access_control
cf_user_management
cf_course
cf_enrollment
cf_assignment
cf_deadline
cf_announcement
cf_discussion
cf_notification
cf_media
cf_analytics
cf_recommendation_ml
cf_gradebook
cf_quiz
cf_certificate
cf_peer_review
cf_live_session
cf_review
cf_promotion
cf_loyalty
cf_outbox
MongoDB: cf_portfolio
MongoDB: cf_chat
Elasticsearch: courseflow-course-search, courseflow-content-search
```

Schema migrations are production-safe by default. `db.changelog-master.yaml` contains schema only.
Local/demo sample data is isolated in `db.changelog-demo.yaml` and enabled by running a service with
the `demo` Spring profile.

## Development Order

1. Backend skeleton, local infra, common-library, event-contracts.
2. Keycloak realm, `access-control-service`, `user-management-service` and
   `identity-token-converter-service`.
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
