# Architecture Review Backlog

This backlog captures the SA, senior backend, senior frontend and QA findings
from the hardening review. Items marked implemented were changed in this pass;
the rest need separate scoped work because they cross service boundaries or
change runtime semantics.

## Implemented In This Pass

- Notification delivery no longer calls external delivery ports or SSE push
  while notification create/fan-out transactions are open. Dispatch is
  registered after commit, failed retries are claimed as `DISPATCHING`, and
  stale `DISPATCHING` rows become retryable again.
- Learner classroom no longer falls back from `/modules/player` to public module
  and progress endpoints. `/modules/player` is the authoritative source for
  lock state, source status, next action and certificate state.
- All MapStruct mappers now use the shared `CourseFlowMapperConfig` convention.
- The architecture database inventory includes access-control, user-management,
  promotion, loyalty, outbox and chat stores.
- Product hardening CI now runs TypeScript lint gates before web builds.

## P1 Architecture Refactors

- Split `common-library` into generic shared plumbing only. Move LMS business
  policy such as course entitlement and product route/scope maps into owned
  service-local policy modules or a dedicated entitlement client.
- Consolidate product authorization decisions through `access-control-service`.
  Controllers should keep coarse endpoint guards; course, department, staff and
  ancestor-scope decisions should not be hard-coded differently per service.
- Redesign loyalty reward fulfillment as `claim -> commit claim -> dispatch
  provider outside transaction -> settle outcome`. Current fulfillment code is
  tied to redemption, retry, callback, audit and outbox behavior, so it should
  become a dedicated worker/dispatcher with idempotent external references.
- Replace duplicate-constraint catch paths around JPA `save(...)` with explicit
  `saveAndFlush` where intentional or Postgres `INSERT ... ON CONFLICT` helpers
  for idempotency tables and reward redemption keys.

## P2 Product And Contract Refactors

- Emit typed `CourseFlowEvent` records or documented versioned envelopes from
  producers. Raw maps should be limited to explicit CDC/projection paths.
- Standardize consumer templates: `processed_events` or approved natural-key
  exception, malformed payload policy, `DefaultErrorHandler`, DLT and duplicate
  delivery tests.
- Normalize web API clients around `getOne`, `getList` and typed `ApiError`
  with `status`, `code`, `message` and `traceId`.
- Replace native `window.confirm` and manual approval-id entry on high-risk
  admin actions with reusable confirmation modals showing impact, evidence,
  correlation and idempotency context.
- Add component/MSW tests for learner player error/locked item behavior,
  enrollment remediation actions, quiz submit, and incentive approval gates.

## Tooling Gaps

- Flutter SDK is not available locally and the mobile app currently has no
  `test` or `integration_test` suite.
- Browser E2E coverage is not present for admin or learner golden paths.
- Coverage gates are not configured for Maven or Vitest.
- Backend modules without tests should receive at least smoke coverage:
  discovery-service, organization-service and portfolio-service.
