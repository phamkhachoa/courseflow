# CourseFlow Engineering Conventions

This document is the shared baseline for architecture review, refactoring and
new feature work across CourseFlow.

## Service Boundaries

- Keycloak owns external IAM: login, SSO, MFA, sessions, OAuth2/OIDC tokens and
  password policy.
- `identity-token-converter-service` owns token exchange from verified external
  identity tokens to short-lived CourseFlow internal JWTs.
- `access-control-service` owns CourseFlow user identity links, roles,
  permissions, scoped grants and authorization audit.
- `user-management-service` owns profile and directory data only.
- Domain services own their aggregate data and business authorization checks for
  their own resources. They must not recreate user/profile/role tables locally.
- Shared modules must stay generic. `common-library` may contain wrappers,
  correlation, error handling, service metadata, mapper config and reusable
  security plumbing, but not LMS business policy such as course entitlement,
  staff role matrices or product-specific route/scope maps.
- Product authorization policy should live in `access-control-service` or an
  explicitly owned service-local policy. Controllers may keep coarse endpoint
  guards, but course, department, staff and ancestor-scope decisions should not
  be duplicated across services.

## Backend Layers

Every Spring service should keep this package shape:

```text
config/       framework config, security, clients, messaging
controller/   REST API boundary only
service/      use cases, transactions and domain decisions
repository/   persistence adapters and persistence-facing projections
model/        JPA/Mongo/Elasticsearch domain models
dto/          request/response records; never expose entities
mapper/       MapStruct mappers or explicit mapping helpers
```

Controllers validate and delegate. Services own transactions, orchestration,
idempotency, authorization and audit. Repositories do persistence work only.

## Persistence

- Prefer Spring Data JPA repositories for aggregate CRUD and relationship-rich
  domains.
- Use `JdbcClient` for outbox workers, reporting-style reads, DLT queues, or
  query shapes that are simpler as SQL than as entities.
- Keep one persistence style dominant within a service unless a second adapter
  is explicitly justified by the data shape.
- Liquibase migrations are the schema source of truth. Tests that rely on
  Postgres-specific JSONB, indexes, locks or constraints need Testcontainers
  coverage.
- Raw SQL with optional filters should build predicates dynamically instead of
  relying on `:param IS NULL OR ...` when JDBC/PostgreSQL cannot infer null
  parameter types.

## DTO Mapping

- Entity-to-DTO and request-to-entity mapping should use MapStruct when the
  mapping is structural or repeated.
- All MapStruct mappers should use `CourseFlowMapperConfig`, which sets
  `componentModel = "spring"` and fails on unmapped targets.
- Manual mapping is acceptable for computed DTOs, audit/evidence packs,
  external-provider envelopes, reconciliation rows, policy decisions and
  objects whose fields require branching or security redaction.
- Manual mapping should live in a mapper/helper or a clearly named private
  method, not inline in controllers.
- Do not map JPA entities directly to client responses from controllers.

## APIs And Events

- Public/learner APIs use `/api/v1/**`; admin APIs use `/api/admin/v1/**`;
  service-to-service APIs use `/internal/**` behind internal JWT protection.
- External clients call through the API gateway. Service-to-service calls carry
  short-lived internal JWTs with endpoint-specific scopes.
- Business events should be emitted through transactional outbox when state
  changes must be delivered reliably.
- Producers should publish typed `CourseFlowEvent` records or a documented
  versioned envelope. Raw `Map` or ad hoc JSON payloads are allowed only for
  explicitly documented CDC/projection paths.
- Consumers should follow one template: idempotency via `processed_events` or an
  approved natural-key exception, malformed-payload policy, `DefaultErrorHandler`
  plus DLT, and tests for duplicate delivery.
- DLT replay/discard and high-risk overrides require idempotency, audit, reason
  and maker-checker where policy marks the operation high risk.
- Outbox relay credentials must be least-privilege per producer database:
  read/update/delete on `outbox_events`, with no domain-table privileges.

## Frontend

- `web/react-admin` is the operation-heavy backoffice client. Prefer dense,
  scan-friendly screens, shared API helpers and explicit loading/error/empty
  states.
- `web/next-learning` is the learner/public web surface. Keep BFF aggregation
  in feature/shared API modules; avoid duplicating gateway path composition in
  components.
- Learner classroom screens must treat `/modules/player` as the authoritative
  source for enrollment, lock, source-status, next-action and certificate state.
  Do not fall back to public module/progress endpoints unless the fallback
  carries the same state contract.
- API clients should unwrap the shared envelope in one place and preserve typed
  errors for screens.
- UI components should stay domain-specific at the feature boundary and reusable
  only when there is real reuse.

## Tests And Review Gates

- Backend local gate: targeted module tests for touched services, then
  `mvn test` before declaring backend-wide readiness.
- Frontend gates: targeted Vitest files first, then `npm run lint` and
  `npm run build` for the touched app.
- Database-specific changes need Testcontainers smoke tests when the behavior
  depends on PostgreSQL syntax, JSONB, locks, constraints or migration order.
- Architecture review should check service ownership, internal JWT/authz
  boundaries, data ownership, mapping policy, transaction/idempotency guarantees,
  and whether the selected tests prove the changed behavior.
