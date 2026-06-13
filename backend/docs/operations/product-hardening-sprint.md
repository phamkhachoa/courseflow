# Product Hardening Sprint

This runbook defines the production-pilot gate for CourseFlow. The goal is not to add more surface
area; it is to prove that the core LMS workflow can be operated, audited and recovered.

## P0 Scope

- Golden flow: create course, submit review, approve, publish, enroll learner, learn content, submit
  assessment, grade, finalize, issue certificate, report.
- Admin UX: operators must use pickers/search for common workflows, not raw UUID lookup as the
  primary path.
- Compliance baseline: admin can export identity-owned user data and deactivate an account with a
  recorded reason, token revocation and live role-grant revocation.
- Notification baseline: every notification has durable inbox state plus delivery status
  (`PENDING`, `DELIVERED`, `FAILED`) so operators can distinguish stored rows from delivery failures.
- Trust boundary baseline: downstream services only accept propagated `X-User-*` identity headers
  when the request also presents a valid short-lived internal JWT.
- Migration safety: fresh local databases must apply Liquibase changelogs without duplicate-column
  failures.

## Golden Flow Checklist

Use demo data or a disposable test tenant. Do not run this checklist against production user data.

| Step | Actor | Evidence |
|---|---|---|
| Login | Admin/instructor/student | Access token issued; gateway forwards `X-User-*` headers |
| Create course draft | Instructor | Course is `DRAFT`, modules are server-owned draft state |
| Submit review | Instructor | Review state changes to `IN_REVIEW` |
| Approve and publish | Non-owner scoped reviewer/admin | Course is `PUBLISHED`; enrollment capacity initializes |
| Search/discover | Public/learner | Published course appears in catalog/search |
| Enroll learner | Student or scoped staff | Enrollment is `ACTIVE`; unpublished courses are rejected |
| Learn content | Student | Module/item progress updates under enrolled course |
| Take quiz | Student | Attempt uses question snapshot and deadline guard |
| Grade/finalize | Staff | Gradebook entry/final grade is scoped and auditable |
| Issue certificate | Staff | Verification code resolves publicly |
| Report | Staff/admin | Course reports require course staff scope; org dashboards require platform admin or matching org scope |
| Notify learner | Staff/admin | Notification row has delivery status and appears in learner inbox |
| Privacy action | Admin | User privacy export downloads; deactivate revokes tokens/role grants |

## Verification Commands

Pull requests and pushes to `main`/`develop` run `.github/workflows/product-hardening.yml`:

- backend reactor tests
- admin web production build
- learner mobile static analysis
- gateway smoke script syntax validation

Backend unit/regression gate:

```bash
cd backend
mvn test
```

Targeted hardening gate:

```bash
cd backend
mvn -pl services/identity-service,services/notification-service -am test
mvn -pl services/analytics-service -am test
mvn -pl services/outbox-relay -am test
```

Admin frontend build gate:

```bash
cd web/react-admin
npm run build
```

Gateway smoke gate with disposable user data:

```bash
cd backend
COURSEFLOW_API_URL=http://localhost:28080/api \
COURSEFLOW_SMOKE_ADMIN_EMAIL=admin@courseflow.local \
COURSEFLOW_SMOKE_ADMIN_PASSWORD=password \
node scripts/product-hardening-smoke.mjs
```

Keycloak security smoke gate against a running OIDC cluster. Run it from a runner/container that can
reach the internal token converter and at least one direct domain service; in local non-prod Compose,
the defaults can be host ports, while the prod profile normally uses internal DNS names.

```bash
cd backend
COURSEFLOW_API_URL=http://localhost:28080/api \
COURSEFLOW_TOKEN_CONVERTER_URL=http://identity-token-converter-service:8105 \
COURSEFLOW_DIRECT_SERVICE_URL=http://course-service:8083 \
COURSEFLOW_SECURITY_SMOKE_ACCESS_TOKEN="<keycloak-access-token-from-approved-login>" \
COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_ID=api-gateway \
COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_SECRET="<api-gateway STS client secret>" \
COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_ID=course-service \
COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_SECRET="<course-service STS client secret>" \
node scripts/keycloak-security-smoke.mjs
```

This gate proves the security architecture, not the whole LMS workflow: Keycloak access token reaches
the gateway, the converter exchanges it for a CourseFlow internal JWT, converter JWKS verifies the
internal signature and `kid`, STS `client_credentials` issues a service token, public profile lookup
does not require a bearer token, profile summary batch remains protected, and a direct service call
with forged `X-User-*` headers is rejected. Do not use password grant for production smoke; the
script only supports it when `COURSEFLOW_SECURITY_SMOKE_ALLOW_PASSWORD_GRANT=true` is explicitly set
for local/demo realms.

This gate now covers the full disposable learning path through the gateway:
public catalog, protected module access, authoring draft/module/item creation,
review approval, publish, enrollment, learner login, learner module read, item
progress completion, course-completion enrollment status, quiz authoring,
sanitized learner quiz view, attempt snapshot, auto-grading, gradebook ingestion,
final grade, automatic certificate issue, public certificate verification,
notification delivery, privacy export, and user deactivation.

PostgreSQL backup/restore drill:

```bash
cd backend
scripts/postgres-backup-drill.sh backup
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_identity
```

Mobile static gate when Flutter is installed:

```bash
cd app
flutter analyze
```

Mobile static gate without a host Flutter SDK:

```bash
docker run --rm \
  -v "$PWD/app":/workspace \
  -w /workspace \
  ghcr.io/cirruslabs/flutter:stable \
  bash -lc 'flutter pub get && flutter analyze'
```

## Local Smoke Gate

Start the local cluster:

```bash
cd backend
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

Then check:

- `GET http://localhost:28080/api/v1/courses` returns only published courses.
- Direct service calls that forge `X-User-*` without a valid internal JWT return `401`.
- `node scripts/keycloak-security-smoke.mjs` passes with `Keycloak security smoke passed`.
- Admin course publish emits lifecycle events and enrollment capacity is created.
- Disposable authoring courses can move from draft to approved and published.
- Course review/publish/archive rejects staff outside the course department scope.
- A newly enrolled learner can read published modules and complete required item progress.
- Quiz attempts produce a persisted snapshot, auto-grade, and a gradebook row through the outbox/Kafka chain.
- Finalized passing grades auto-issue certificates that verify publicly without exposing student id or grade.
- Reporting endpoints reject cross-org dashboards and unscoped cross-student analytics.
- `GET http://localhost:18083/connectors/courseflow-course-search-cdc/status` is healthy.
- Admin notifications can send a `SYSTEM` notification and show `DELIVERED` or `FAILED`.
- Admin user detail can download privacy export JSON and deactivate a disposable account.
- `node scripts/product-hardening-smoke.mjs` passes with `Smoke passed`.
- Prometheus can scrape service `/actuator/prometheus` targets when the observability compose override is enabled.
- Token converter metrics show token exchange request/success/failure/duration and JWKS request
  counters: `courseflow.token_converter.*`.
- Token converter emits structured security audit logs on
  `courseflow.security.token_converter.audit` for exchange success/failure without raw bearer tokens
  or client secrets.
- Production token converter runs with `ACCESS_CONTROL_RESOLUTION_MODE=required`; it must not fall
  back to roles embedded in external token claims when `access-control-service` is unavailable.
- Production STS client credentials use an explicit `COURSEFLOW_STS_ALLOWED_CLIENTS` allowlist; `*`
  is reserved for local/demo only, and the legacy `identity-service` is rejected in the Keycloak
  production profile.
- Production STS service scopes are explicit; wildcard `COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES=*`
  is rejected, and the list must include the endpoint-level scopes enforced by
  `TrustedGatewayHeaderFilter`.
- Downstream services expose internal JWT rejection counters through
  `courseflow.internal_jwt.rejections` for `/internal/**`, `/backoffice/**` and identity-header
  requests.
- Access-control exposes authorization decision counters through
  `courseflow.access_control.authz.checks` and persists denied decisions in
  `access_control_audit_logs`.
- Scoped authorization smoke covers an assignment at an ancestor scope, such as `DEPARTMENT`, being
  honored for a child `COURSE` check only when the service caller supplies server-derived
  `ancestorScopes` with `internal:authz:assert-topology`.
- Chat WebSocket `CONNECT` succeeds with a Keycloak access token only through token converter ->
  internal JWT verification, and direct legacy HS256 JWT verification is not used in Keycloak mode.
- Kafka Connect is verified through `GET /connectors/courseflow-course-search-cdc/status`; it is not a Spring actuator target.
- Grafana starts with the CourseFlow Prometheus datasource provisioned.
- Prometheus loads `infra/observability/alerts.yml` and evaluates basic service-down alerts.
- `scripts/postgres-backup-drill.sh restore-check ...` passes for at least one service database.

## No-Go Criteria

Do not call a build production-ready if any item below is true:

- A normal operator must paste UUIDs for the golden flow.
- A learner can access unpublished or unenrolled course assessment content.
- Quiz attempts can be graded from mutable live question data instead of saved attempt snapshots.
- Grade changes lack override reason/audit.
- Notification send creates an inbox row with no delivery status.
- Identity privacy export/deactivation lacks audit or token revocation.
- Token converter can issue a user internal JWT from external claims without resolving
  `access-control-service`.
- STS client credentials allow `COURSEFLOW_STS_ALLOWED_CLIENTS=*` or include `identity-service` in
  production.
- Downstream services trust `X-User-*` headers without internal JWT attestation.
- `/backoffice/**` service endpoints are reachable without a valid internal JWT.
- Staff roles can read org dashboards or student analytics without matching org/course scope.
- Department/org-scoped roles false-deny child course/section actions because callers omitted
  `ancestorScopes`.
- Chat/WebSocket accepts legacy CourseFlow JWTs directly instead of exchanging the bearer token
  through `identity-token-converter-service`.
- Fresh Liquibase migration fails from an empty database.
- No metrics endpoint exists for backend services.
- No restore-checked backup artifact exists for Postgres service databases.
- Backend tests or admin build fail.
- Mobile `flutter analyze` fails.

## Production Follow-Up

- For notification delivery, local/dev uses `LoggingNotificationDeliveryPort`. Production can switch
  to webhook mode without changing business code:

  ```bash
  NOTIFICATION_DELIVERY_MODE=webhook
  NOTIFICATION_DELIVERY_WEBHOOK_URL=https://notification-provider.example.com/courseflow
  ```

  The webhook endpoint receives notification id, user id, type, title and body. Replace or extend
  this adapter with a native email/push provider when provider-specific tracking is required.
- Add e2e tests that drive the golden flow through the gateway and admin/learner UIs.
- Add OpenTelemetry traces, Kafka lag/DLQ dashboards, backup/PITR checks and incident runbooks.
- Decide tenant model before adding SaaS billing, branding or tenant-scoped quotas.
