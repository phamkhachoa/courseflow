# Generic Incentive Platform Design

Status: Design approved by PO, BA, SA, Senior Backend Dev, and Senior Platform Dev review round.

Date: 2026-06-14

## Team Review

- PO, Fermat: product scope, personas, roadmap, production acceptance.
- BA, Erdos: business vocabulary, workflows, business rules, edge cases.
- SA, Parfit: service boundary, architecture, data ownership, consistency model.
- Senior Backend Dev, Tesla: implementation plan, file/API/module risks, tests.
- Senior Platform Dev, Locke: production gates, concurrency, observability, operations.

## Executive Decision

Promotion, coupon, and loyalty belong to the same product family: incentives. They must not be modeled as one flat coupon entity.

The platform will be implemented as `promotion-service`, but the domain language and API are generic incentives:

- Promotion is a campaign-driven incentive with rules and effects.
- Coupon is a redeemable key or credential that may unlock or track a campaign.
- Loyalty is a ledger-backed program for points, tiers, rewards, earn, burn, expiry, and reversal.

Sprint 1 must build the generic incentive transaction kernel, not a full loyalty suite and not just campaign/coupon CRUD.

## Product Stance

The service is a decisioning and ledger platform. It accepts generic facts from an integrating system, evaluates eligible incentives, reserves quota, commits or cancels a redemption, and produces auditable effects.

The core must not contain LMS-specific fields such as `course_id`, `enrollment_id`, `student_id`, or `department_id`. CourseFlow LMS is only the first integration client. LMS services must resolve LMS facts and send them as generic context attributes.

## Bounded Context

`promotion-service` owns:

- Campaign definition.
- Coupon/redeemable code.
- Typed rule/action definitions.
- Evaluation and validation.
- Reservation, commit, cancellation, expiry.
- Quota counters.
- Redemption ledger.
- Idempotency records.
- Audit events.
- Outbox events for downstream consumers.

It does not own:

- Course, enrollment, order, payment, gradebook, profile, notification, or CRM data.
- Applying the returned effect inside the source domain.
- Calling back into LMS to enrich facts during evaluation.

## Architecture

The service has two cores in one bounded context:

1. Decisioning core
   - Reads active campaign versions.
   - Evaluates typed rules from JSONB configs.
   - Produces deterministic effects and reason codes.
   - Has no write side effects for evaluate requests.

2. Ledger and redemption core
   - Owns reservation, redemption, cancellation, expiry, and reversal.
   - Is the source of truth for quota and financial/benefit audit.
   - Writes audit and outbox records in the same transaction as state change.

Postgres is the source of truth. Redis may later cache active campaign reads or rate-limit attempts, but must not be the correctness source for redemption quota.

## Rule Engine Decision

Use typed Java evaluators, not embedded scripts, Groovy, JavaScript, or arbitrary expressions.

Campaign `rules_json` and `actions_json` are stored as serialized typed configs:

```json
{
  "schemaVersion": 1,
  "type": "MIN_ORDER_AMOUNT",
  "parameters": {
    "amount": 100,
    "currency": "USD"
  }
}
```

Each `type` maps to a Java evaluator or action resolver. Unknown type or malformed parameters fail at publish time and at runtime fail closed.

Trade-off: new rule types require deploys, but the engine is safer, testable, observable, and avoids remote-code-execution risk.

## Sprint 1 Default Policies

These defaults are intentionally opinionated so implementation can proceed without waiting on more business clarification:

- Only active or published campaigns are decisioned.
- Coupon codes are trimmed and case-insensitive.
- One best campaign/coupon applies per transaction in Sprint 1.
- Campaign priority wins; if tied, older `created_at` wins.
- Min spend is based on subtotal before incentive, excluding tax and shipping.
- Discount base is current sale/subtotal price, before tax and shipping.
- Currency rounding is half-up to the currency minor unit.
- Reservation TTL is 15 minutes.
- Commit happens when the source system confirms order/payment success.
- Cancel releases reservation quota before commit.
- Committed redemption is never deleted; cancellation/reversal creates a compensating state or ledger entry.
- Quota exhaustion is a hard stop.
- Missing attributes for a required rule fail closed.
- Idempotency key reuse with identical payload returns the stored result.
- Idempotency key reuse with different payload returns conflict.

## Sprint 2A Production Runtime Contract

Status: implemented in `promotion-service` after SA/BA/UI/Tech Lead roundtable.

Sprint 2A intentionally does not include coupon batch, loyalty points ledger, full audit explorer, or admin UI. It closes the production correctness gaps first:

- `incentive_applications` is the tenant/application registry.
- `incentive_application_client_bindings` optionally binds runtime callers/clients to an application.
- Runtime/admin mutation rejects unknown or suspended applications.
- Runtime caller binding is fail-closed; migrated active apps are explicitly bound to `api-gateway`.
- `incentive_campaign_versions` stores immutable campaign definition snapshots.
- Runtime evaluate/reserve reads only active `PUBLISHED` campaign versions, never the mutable campaign shell.
- Reservations, redemptions, ledger entries, effects metadata, and outbox payloads carry `campaignVersion`.
- Reserve stores a quota snapshot so cancel/expire releases the exact counters consumed by that reservation.
- Quota checks and consumes use the active campaign version's effective limit, not stale counter limits from earlier versions.
- Campaign publish uses the minimal workflow: `DRAFT -> SUBMITTED -> APPROVED -> PUBLISHED`.
- The creator cannot approve their own campaign version.
- Legacy `PATCH /campaigns/{id}/status` no longer publishes; publish must go through the version workflow. It remains for pause/archive/draft state changes and deactivates the active snapshot.

Sprint 2A admin/internal endpoints:

- `GET/POST /internal/incentives/applications`
- `PATCH /internal/incentives/applications/{applicationUuid}`
- `PATCH /internal/incentives/applications/{applicationUuid}/status`
- `POST /internal/incentives/applications/{applicationUuid}/client-bindings`
- `GET/POST /internal/incentives/campaigns/{campaignId}/versions`
- `POST /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}/submit`
- `POST /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}/approve`
- `POST /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}/reject`
- `POST /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}/publish`

## Sprint 2B Production Operations Contract

Status: backend contract implemented after PO/BA/UI/SA/Tech Lead/QA review round.

Sprint 2B closes the production operations gap before expanding into coupon batch or full loyalty. The platform now gives operators and reviewers the ability to inspect what is live, compare what will change, recover from bad releases through controlled rollback-to-draft, and reverse committed redemptions through compensating ledger entries.

Implemented capabilities:

- Campaign version detail returns the full immutable snapshot, including rules, actions, quota, dates, status, actors, timestamps, and rollback source.
- Draft workspace supports patching `DRAFT` or `REJECTED` versions only.
- `PUBLISHED` and `SUPERSEDED` snapshots remain immutable.
- Version validation returns deterministic blockers and warnings.
- Version diff compares two versions using canonical JSON for rule/action snapshots.
- Rollback creates a new `DRAFT` version from a `PUBLISHED` or `SUPERSEDED` source; it never mutates the old snapshot and must still go through submit/approve/publish.
- Audit explorer filters by tenant, application, aggregate type/id, action, actor, and time range with bounded limits.
- Timeline endpoints expose campaign, application, and redemption/reservation history for support.
- Application registry and client binding mutations now write audit events.
- Redemption reversal is idempotent. Trusted runtime service actors with `internal:promotion:reverse`
  plus a bound `reverse` operation may execute automated compensation directly. Admin/operator
  support reversal requires a hash-bound maker-checker approval with reason, change ticket, reviewer,
  non-self execution, audit `redemption.reversal_approval_*`, ledger `REVERSE`, audit
  `redemption.reversed`, and outbox `incentive.redemption.reversed`.
- Reversal does not release committed quota by default.
- Migration 005 adds audit query indexes, `rollback_source_version`, `campaign_version NOT NULL`, and a unique reversed outbox event guard.
- Minimal Micrometer observability was added for version transitions, reversal results, and audit query duration.

Sprint 2B admin/internal endpoints:

- `GET /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}`
- `PATCH /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}/draft`
- `GET /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}/validation`
- `GET /internal/incentives/campaigns/{campaignId}/versions/{leftVersion}/diff?rightVersion={rightVersion}`
- `POST /internal/incentives/campaigns/{campaignId}/versions/{versionNumber}/rollback`
- `GET /internal/incentives/audit`
- `GET /internal/incentives/campaigns/{campaignId}/timeline`
- `GET /internal/incentives/applications/{applicationUuid}/timeline`
- `GET /internal/incentives/redemptions/{redemptionId}/timeline`
- `POST /internal/incentives/redemptions/{redemptionId}/reverse`

## Sprint 2BF Loyalty Control Plane Contract

Status: implemented for `loyalty-service` and web-admin after SA sidecar review.

Loyalty now has its own control-plane surface instead of requiring manual database writes for
program, binding, account, ledger, and audit operations.

Implemented capabilities:

- Admin can create, list, inspect, edit, suspend, archive, and reactivate loyalty programs.
- Admin can upsert program client bindings with status and allowed operations.
- Runtime earn/burn/reverse still requires a trusted service actor, matching internal JWT scope, and
  an active program-client binding.
- Admin can search accounts by tenant/application/program/profile/status.
- Admin can suspend, close, or reactivate an account with note and correlation id.
- Admin ledger lookup intentionally does not enforce active program/account state, so operators can
  investigate a suspended or closed account.
- Program timeline includes program audit events and client-binding audit events belonging to that
  program.
- Account timeline exposes lifecycle audit events for investigation.
- Admin can manually adjust account points with signed `pointsDelta`, required reason, required
  correlation id, source reference, idempotency key, immutable `ADJUST` ledger entry, audit, and
  outbox event `loyalty.points.adjusted`.
- Admin can run an expiry dry-run for tenant/application/program/as-of time. The dry-run returns
  candidate entries, affected accounts, gross expiring points, warnings, and a result hash without
  mutating ledger state.
- Gateway exposes the admin surface at `/api/admin/v1/loyalty/**`, rewritten internally to
  `/internal/loyalty/**`.
- Web-admin includes `/incentives/loyalty` with Programs, Accounts & ledger, Expiry dry-run, and
  Audit workspaces.

Sprint 2BF admin/internal endpoints:

- `GET/POST /internal/loyalty/programs`
- `GET/PATCH /internal/loyalty/programs/{programUuid}`
- `PATCH /internal/loyalty/programs/{programUuid}/status`
- `POST /internal/loyalty/programs/{programUuid}/client-bindings`
- `GET /internal/loyalty/programs/{programUuid}/timeline`
- `GET /internal/loyalty/accounts:search`
- `PATCH /internal/loyalty/accounts/{accountId}/status`
- `GET /internal/loyalty/accounts/{accountId}/timeline`
- `POST /internal/loyalty/points:adjust`
- `POST /internal/loyalty/points:expire-dry-run`
- `GET /internal/loyalty/ledger`
- `GET /internal/loyalty/audit`

Sprint 2C+ backlog:

- Coupon batch import/generation.
- Admin Ops UI for Campaign Workspace, Version Review Queue, Redemption Support Console, and Audit Explorer.
- Domain metrics and alerts beyond the minimal Sprint 2B metrics.
- Full loyalty points/tier/reward ledger.
- Runtime multi-campaign stacking beyond admin simulation policy analysis.
- Fraud/abuse controls and velocity limits.
- Refund proration policy for partial line-level returns.

## Sprint 1 Rule And Action Scope

Rules:

- Campaign active date window.
- Coupon present and valid.
- Global campaign usage cap.
- Coupon usage cap.
- Per-profile campaign or coupon cap.
- Min order amount.
- Profile segment or group from context attributes.
- Item/category include or exclude from line item attributes.
- Channel/application match.

Actions:

- Fixed amount off order.
- Percentage off order with max discount cap.
- Fixed amount off eligible line/category.
- Free shipping when shipping amount exists in context.

Deferred:

- Full loyalty earn/burn/tier/reward catalog.
- BOGO and cheapest-item-free.
- Runtime advanced stacking of multiple campaigns.
- Bulk coupon import/export.
- Fraud ML and complex personalization.
- Admin UI.
- Partial refund and line-level return proration.

## API Surface

Gateway routes:

- `/api/admin/v1/incentives/**` maps to `/internal/incentives/**`.
- Browser-facing `/api/v1/incentives/**` runtime routes are intentionally not exposed. Trusted source
  services or a BFF, such as enrollment-service for learner coupons, must build server-owned facts
  and call `/internal/incentives/**` with service internal JWTs and application client bindings.

Admin API:

- `POST /internal/incentives/campaigns`
- `GET /internal/incentives/campaigns`
- `GET /internal/incentives/campaigns/{id}`
- `PATCH /internal/incentives/campaigns/{id}`
- `PATCH /internal/incentives/campaigns/{id}/status`
- `POST /internal/incentives/coupons`
- `POST /internal/incentives/coupons:batch` only after Sprint 1 if simple batch is safe
- `GET /internal/incentives/campaigns/{id}/redemptions`
- `GET /internal/incentives/audit`

Runtime API:

- `POST /internal/incentives/evaluate`
- `POST /internal/incentives/reservations`
- `POST /internal/incentives/reservations/{id}/commit`
- `POST /internal/incentives/reservations/{id}/cancel`
- `GET /internal/incentives/redemptions/{id}`
- `GET /internal/incentives/redemptions?externalReference=...`

Mutating runtime APIs require an idempotency key.

## Request Shape

Runtime request must stay generic:

```json
{
  "tenantId": "courseflow",
  "applicationId": "lms",
  "profileId": "123",
  "externalReference": "order-or-enrollment-reference",
  "channel": "WEB",
  "currency": "USD",
  "couponCodes": ["WELCOME10"],
  "transaction": {
    "subtotal": 120,
    "shippingAmount": 10
  },
  "items": [
    {
      "id": "item-1",
      "type": "COURSE",
      "quantity": 1,
      "unitPrice": 120,
      "attributes": {
        "category": "spring",
        "department": "engineering"
      }
    }
  ],
  "attributes": {
    "segment": "NEW_LEARNER"
  }
}
```

## Response Shape

Evaluation and reservation responses must include:

- `eligible`
- `campaignId`
- `campaignCode`
- `campaignVersion`
- `couponId`
- `effects`
- `reasonCodes`
- `reservationId` only for reservation
- `expiresAt` only for reservation
- `idempotencyReplay`

Effects must be traceable to campaign, rule, and action.

## Schema Direction

Before implementation continues, the current draft schema must be adjusted. If Liquibase has not run in a shared environment, rewrite the baseline. Otherwise add forward migrations.

Required tables:

- `incentive_campaigns`
- `incentive_campaign_versions` or immutable version columns/snapshots
- `incentive_coupons`
- `incentive_reservations`
- `incentive_redemptions`
- `incentive_ledger_entries`
- `incentive_quota_counters`
- `incentive_idempotency_keys`
- `incentive_audit_events`
- `outbox_events`

Important corrections to the draft:

- Do not rely on nullable `idempotency_key` in redemptions.
- Add a dedicated idempotency table keyed by tenant, application, operation, and key.
- Store request hash and response snapshot for idempotent replay.
- Add reservation status and expiry.
- Add quota counters as the authoritative concurrency control.
- Add normalized coupon code and preferably code hash/mask for sensitive coupons.
- Add outbox events so downstream integrations do not need to poll.
- Add check constraints for statuses, non-negative counters, and valid dates.

## State Machines

Campaign:

`DRAFT -> PUBLISHED -> PAUSED -> PUBLISHED -> ARCHIVED`

Reservation:

`RESERVED -> REDEEMED`

`RESERVED -> CANCELLED`

`RESERVED -> EXPIRED`

Redemption:

`REDEEMED -> REVERSED`

Committed redemption must not be deleted.

## Consistency Model

Reserve flow:

1. Validate idempotency key.
2. Load active campaigns.
3. Evaluate rules.
4. Lock or atomic-update quota counters in stable order.
5. Insert reservation and ledger entry.
6. Store idempotency response.
7. Write audit and outbox if state changed.

Commit flow:

1. Validate idempotency key.
2. Lock reservation.
3. If already committed, replay stored response.
4. Move reservation to redeemed.
5. Insert redemption and ledger entry.
6. Write audit and outbox in the same transaction.

Cancel flow:

1. Validate idempotency key.
2. Lock reservation or redemption.
3. Release quota only for uncommitted reservations.
4. For committed redemption, write reversal state/ledger instead of deletion.

## Security

- Keep existing gateway and internal JWT pattern.
- Do not trust `tenantId` or `applicationId` blindly.
- Bind application access to caller/client identity where possible.
- Admin endpoints require platform or tenant operator roles.
- Runtime mutation APIs must be called by trusted application services carrying an internal JWT with
  `actor_type=service`; browser/user traffic must not submit raw economic/profile facts directly.
- Admin/operator traffic may evaluate raw facts only for preview/troubleshooting and must not reserve,
  commit, or cancel ledger entries without a trusted service actor.
- Never accept actor id from request body when `CurrentUser` exists.
- Audit all config and ledger mutations with actor/source/correlation id.

Future access-control permissions:

- `incentive:manage`
- `incentive:redeem`
- `incentive:audit`

## Observability

Metrics:

- evaluation count by result and reason.
- evaluation duration.
- reservation count by status.
- redemption count by status.
- idempotency replay count.
- quota conflict count.
- coupon invalid and exhausted count.
- reservation expiry count.
- outbox lag.

Logs:

- Include correlation id, tenant id, application id, campaign id, reservation id, redemption id.
- Do not log raw coupon secrets.

## Production Gates

Sprint 1 cannot be considered complete unless:

- Service builds and starts.
- Liquibase migration runs cleanly.
- Gateway route test passes.
- Evaluate, reserve, commit, and cancel APIs work.
- Same idempotency key replays result.
- Same idempotency key with different payload returns conflict.
- Concurrent reservation test cannot exceed quota.
- Audit is written for campaign publish and ledger mutation.
- Outbox is written for committed redemption if events are enabled in Sprint 1.
- No LMS-specific field exists in the core incentive schema.

## Sprint Plan

Sprint 1: Generic incentive transaction kernel

- Correct schema baseline before first shared migration.
- Build Java app skeleton, DTOs, entities, repositories, service, controller.
- Implement campaign and coupon minimal admin.
- Implement typed rule/action validation.
- Implement evaluate.
- Implement reserve, commit, cancel.
- Implement idempotency table.
- Implement quota counters.
- Implement audit.
- Add tests for rules, idempotency, quota concurrency, state transitions.
- Wire Docker local cluster enough for service health.

Sprint 2: Production operations

- Add outbox events and outbox-relay config if deferred from Sprint 1.
- Add Prometheus scrape, metrics, dashboards, alerts.
- Add prod compose, prod validation script, CI workflow updates.
- Add reservation expiry job.
- Add rate limit and brute-force protection signals.
- Add smoke tests through gateway.

Sprint 3: Scale and extension

- Add coupon batch generation/import with staging and dry-run.
- Add richer campaign version diff and approval.
- Add simple loyalty account and immutable points ledger.
- Add refund/reversal policies beyond full cancel.
- Add support/admin lookup APIs.
- Add load test and runbook.

## Sprint 2B/2C Implementation Status

Backend production operations completed in Sprint 2B:

- Campaign version workspace APIs for draft, submit, approve, reject, publish, rollback, validation, and diff.
- Audit explorer and entity timelines for application, campaign, and redemption operations.
- Redemption support API with reversal command and immutable ledger/audit trail.
- Prometheus-facing metrics for runtime operations and admin operations.
- Gateway routing through `/api/admin/v1/incentives/**`; later hardening removed browser-facing
  `/api/v1/incentives/**` runtime routes.

Admin UI completed in Sprint 2C:

- Incentive operations module mounted under `/incentives`.
- Application registry with client binding and application status operations.
- Campaign list, create flow, and campaign workspace.
- Version rail, draft editor, validation panel, draft-vs-published diff, coupon creation drawer, audit timeline, and guarded workflow actions.
- Review queue for submitted campaign versions.
- Redemption support console, redemption detail, timeline, and guarded reversal.
- Audit explorer with filters and detail drawer.

Sprint 2C verification:

- `npm run lint` passed for `web/react-admin`.
- `npm run test` passed for all current admin tests.
- `npm run build` passed; the current Vite bundle warning remains a future code-splitting task.
- Browser smoke covered Keycloak login, `/incentives`, `/incentives/campaigns/new`, desktop and mobile viewport checks.
- Backend Docker cluster was up, gateway health returned `UP`, and unauthenticated incentive traffic returned `401` as expected.

Known Sprint 2C follow-up:

- Replace JSON rule/action editing with a visual rule builder once the rule catalog stabilizes.
- Add coupon import dry-run validation.
- Add loyalty account and immutable points ledger as a separate bounded context, not as campaign metadata.

## Sprint 2D Implementation Status

The PO/BA/SA/dev review concluded that promotion, coupon, and loyalty belong to one incentive platform, but not to one flat entity. The current deployable remains `promotion-service` for promotion/coupon decisioning and redemption. Loyalty must become a separate bounded context for accounts, points ledger, tier state, earn, burn, expiry, and reversal.

Backend hardening completed in Sprint 2D:

- Server-side campaign version review queue at `/internal/incentives/campaign-versions/review-queue`.
- Coupon inventory APIs: list, detail, status transition, and batch generation.
- Coupon lifecycle validation for date windows and quota limits.
- Decision engine hardening: campaign currency mismatch fails closed, percent actions are limited to 0-100, fixed discounts are capped to payable order or line amount.
- Reservation request snapshots mask coupon codes and store fingerprints instead of raw coupon codes.
- Campaign master data now syncs from the published version snapshot.
- Liquibase production invariants in `006-production-invariants.sql`: campaign-version FK guards, active snapshot check, external reference uniqueness guards, and migrated `api-gateway` bindings receive `reverse`.

Admin UI completed in Sprint 2D:

- Review queue now uses the backend review queue endpoint instead of client-side campaign/version fan-out.
- Review queue displays publishable state, blocker count, and warning count.
- Admin API client now has coupon list/detail/status/batch generation contracts.

Sprint 2D verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed. The Testcontainers JPA smoke class was skipped because the Java Testcontainers client could not connect to the local Docker daemon from the test JVM.
- `npm run lint`, `npm run test`, and `npm run build` passed for `web/react-admin`; the existing Vite chunk-size warning remains.
- Docker compose rebuilt and recreated `promotion-service`.
- Liquibase ran `promotion-006-production-invariants` successfully.
- Gateway health returned `UP`.
- Unauthenticated gateway smoke calls to `/api/admin/v1/incentives/campaign-versions/review-queue` and `/api/admin/v1/incentives/coupons` returned `401`.

Known Sprint 2D follow-up:

- Add coupon CSV/import dry-run and richer coupon detail usage metrics.
- Add DB-level immutability trigger for published/superseded campaign versions.
- Add loyalty-service or a clearly isolated loyalty module for account balance, subledger, points expiry, tiering, earn/burn/reverse, and manual adjustment workflow.

## Sprint 2E Implementation Status

The SA/backend review identified the highest-risk remaining production issue: raw runtime facts such as
subtotal, segment, item category, and channel must not be trusted when submitted by a browser/user actor.
Promotion remains generic and does not call LMS/order services to enrich facts; instead, the source
application must validate facts and call promotion as a trusted service.

Backend hardening completed in Sprint 2E:

- `evaluate`, `reserve`, `commit`, and `cancel` now require a trusted runtime caller after application/client binding.
- A trusted runtime caller is an internal JWT with `actor_type=service`; the bound client still needs the matching operation.
- Sprint 2F tightened this further: admin/operator actors must use the explicit no-ledger preview endpoint instead of runtime `evaluate`.
- Liquibase `007-trusted-runtime-access.sql` removes runtime operations from active `api-gateway` bindings, leaving `admin` and `reverse`.
- JPA smoke setup now models the intended integration: `api-gateway` for admin/support and `checkout-service` for runtime operations.

Sprint 2E verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `IncentiveAccessServiceTest` covers user actor rejection, service actor allowance, admin runtime-evaluate rejection, admin reserve rejection, and source-client audit metadata extraction.
- Docker compose rebuilt and recreated `promotion-service`.
- Liquibase ran `promotion-007-trusted-runtime-access` successfully.
- Gateway health returned `UP`; unauthenticated runtime evaluate through the gateway returned `401`.
- Database smoke confirmed `api-gateway` has zero active bindings with `evaluate`, `reserve`, `commit`, or `cancel`.

Known Sprint 2E follow-up:

- Add signed facts snapshot endpoints if browser relay is required: browser sends only a short-lived signed snapshot token, not raw facts.

## Sprint 2F Implementation Status

The PO/BA, SA, UI/UX, and backend review agreed the next gate should be production operability rather
than more rule types or loyalty features. The first Sprint 2F slice separates admin troubleshooting from
runtime contract.

Backend hardening completed in Sprint 2F:

- Added `POST /internal/incentives/admin/preview` for operator troubleshooting.
- Preview accepts the same generic facts context but returns an explicit envelope:
  `preview=true`, `ledgerImpact=false`, `contextHash`, and the evaluate decision.
- Preview reuses the published runtime snapshot selection path and does not create reservation,
  redemption, ledger, quota, outbox, or idempotency records.
- Preview writes an audit event `incentive.previewed` with masked coupon codes, coupon fingerprints,
  context hash, decision summary, `X-Correlation-Id`, and source client id from the internal JWT.
- Runtime `evaluate`, `reserve`, `commit`, and `cancel` are now service-actor only; admin/operator
  actors no longer bypass `evaluate`.

Sprint 2F verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `PromotionControllerSecurityTest` covers missing internal JWT rejection, admin preview routing with
  correlation id, and service-actor runtime evaluate routing.
- `PromotionServiceTest` proves admin preview returns a decision without touching reservation,
  redemption, ledger, idempotency, or outbox repositories, and stores sanitized audit payload.
- The Testcontainers JPA smoke class remains skipped locally because the Java Testcontainers client
  cannot connect to the local Docker daemon from the test JVM.

Known Sprint 2F follow-up:

- Add signed facts snapshot endpoints if browser relay is required: browser sends only a short-lived signed snapshot token, not raw facts.
- Add controller-level tests for unbound service client `403` and user actor runtime `403` through the full service layer.
- Add runtime metrics for evaluate/reserve/commit/cancel, idempotency replay/conflict, quota exhaustion, invalid coupon, expiry, reversal, and outbox lag.

## Sprint 2G Implementation Status

The PO/BA, SA, and backend lead review selected traceability as the next production gate. The decision
was to make audit rows useful for incident investigation before adding more rule types or loyalty
subsystems.

Backend and admin improvements completed in Sprint 2G:

- Added a shared `AuditMetadata` value object to normalize `X-Correlation-Id` and internal source
  client id.
- All promotion/application/campaign-version/coupon/reservation/redemption mutation paths now pass
  trace metadata into `IncentiveAuditEvent`.
- System reservation expiry emits synthetic correlation ids with source client
  `promotion-service/reservation-expiry`.
- Redemption commit/reverse outbox payloads now include correlation id and source client id so
  downstream consumers can stitch events back to the initiating request.
- Audit explorer query now supports `correlationId` and `sourceClientId` filters.
- Admin Incentives Audit Explorer UI now exposes Correlation and Source client filters and displays
  source client in event summaries/details.

Sprint 2G verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `PromotionControllerSecurityTest` now covers correlation forwarding for admin preview, application
  mutation, runtime reservation, and audit explorer filters.
- `IncentiveAuditQueryServiceTest` covers repository filter forwarding, response mapping for
  `correlationId/sourceClientId`, blank-filter normalization, and limit bounding.
- `PromotionServiceTest` continues to prove admin preview writes sanitized trace metadata without
  ledger side effects.
- `npm run lint` passed for `web/react-admin`.
- The Testcontainers JPA smoke class remains skipped locally because the Java Testcontainers client
  cannot connect to the local Docker daemon from the test JVM, even though the Docker CLI itself is
  reachable.

Known Sprint 2G follow-up:

- Add service-layer tests for audit metadata on commit and cancel.
- Add controller-level tests for unbound service client `403` and user actor runtime `403` through the
  full service layer.
- Add runtime metrics for evaluate/reserve/commit/cancel, idempotency replay/conflict, quota
  exhaustion, invalid coupon, expiry, reversal, and outbox lag.
- Add signed facts snapshot endpoints if browser relay is required: browser sends only a short-lived
  signed snapshot token, not raw facts.

## Sprint 2H Implementation Status

The PO/BA, SA/SRE, and backend review split between observability, tests, and database integrity. The
main implementation chose the common production gate that prevents silent corruption first: campaign
version snapshot immutability plus service-layer traceability tests. Runtime metrics/alerts remain the
next sprint because they need careful bounded-cardinality label design.

Backend hardening completed in Sprint 2H:

- Added Liquibase `promotion-008-campaign-version-immutability`.
- Added a PostgreSQL trigger that blocks direct `UPDATE` of protected business fields when a campaign
  version is already `PUBLISHED` or `SUPERSEDED`.
- Added a PostgreSQL trigger guard that blocks `DELETE` of `PUBLISHED` or `SUPERSEDED` campaign
  versions.
- Kept legitimate lifecycle movement safe: an active `PUBLISHED` snapshot may still be deactivated or
  superseded without changing business fields.
- Added `PromotionServiceTraceabilityTest` for create campaign, coupon batch generation, redemption
  reverse audit/outbox trace metadata, and reservation expiry synthetic system trace metadata.
- Added `CampaignVersionServiceTraceabilityTest` for submit and publish trace metadata.

Sprint 2H verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `PromotionServiceTraceabilityTest` ran 4 tests with 0 failures.
- `CampaignVersionServiceTraceabilityTest` ran 2 tests with 0 failures.
- Docker compose rebuilt and recreated `promotion-service`.
- Liquibase ran `promotion-008-campaign-version-immutability` successfully.
- Gateway health returned `UP`.
- Database smoke confirmed the trigger exists on `incentive_campaign_versions`.
- Direct SQL `UPDATE` of a protected campaign version business field failed with
  `Published campaign versions are immutable and cannot be updated`.
- Direct SQL `DELETE` of a protected campaign version failed with
  `Published campaign versions are immutable and cannot be deleted`.
- Lifecycle-safe `active_snapshot=false` on an active published snapshot succeeded inside a rollbacked
  transaction.
- The Testcontainers JPA smoke class remains skipped locally because the Java Testcontainers client
  cannot connect to the local Docker daemon from the test JVM, even though Docker CLI and Compose are
  reachable.

Known Sprint 2H follow-up:

- Add richer coupon-match metrics if fraud/client-debug signals require distinction between not found,
  inactive, not started, expired, and holder mismatch.
- Add signed facts snapshot endpoints only if browser relay becomes a real product requirement.

## Sprint 2I Implementation Status

The PO/BA, SA/SRE, and backend review selected runtime observability as the next gate. The platform
already had integrity and audit traceability, but operators still needed early warning for runtime
failures, idempotency conflicts, quota exhaustion, expiry stalls, and outbox lag.

Backend and observability improvements completed in Sprint 2I:

- Added bounded-cardinality runtime operation metrics for `evaluate`, `preview`, `reserve`, `commit`,
  `cancel`, `reverse`, and `reservation_expiry`.
- Added idempotency metrics for acquired, replay, missing key, payload conflict, expired,
  not replayable, and acquire failed outcomes.
- Added quota metrics for available, exhausted, consumed, released, and release-missing outcomes.
- Added cached outbox gauges for unpublished incentive-redemption events and oldest unpublished age.
- Added cached reservation-expiry backlog gauges for expired reserved reservations and oldest backlog
  age.
- Added reservation-expiry run and expired-count counters plus duration histogram.
- Enabled histogram buckets for promotion runtime and reservation expiry timers.
- Added Prometheus alert rules for runtime error rate, p95 latency, idempotency conflict spike, quota
  exhaustion spike, invalid coupon signal, outbox lag/backlog, expiry stalled, and reversal failures.
- Added `IncentiveMetricsTest` for runtime, idempotency, quota, expiry, outbox, and backlog metrics.
- Extended `PromotionServiceTraceabilityTest` for commit/cancel audit metadata and runtime metric hooks.
- Added `PromotionServiceBoundaryTest` proving user actors cannot call runtime reserve even with a
  client binding, and unbound service clients are rejected.

Sprint 2I verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `IncentiveMetricsTest` ran 2 tests with 0 failures.
- `PromotionServiceTraceabilityTest` ran 6 tests with 0 failures.
- `PromotionServiceBoundaryTest` ran 2 tests with 0 failures.
- Prometheus alert syntax validation passed with `promtool check rules`; 11 rules were found.
- Docker compose rebuilt and recreated `promotion-service`.
- Gateway health returned `UP`.
- Direct `/actuator/prometheus` smoke inside the promotion container exposed:
  `promotion_runtime_operation_total`, `promotion_reservation_expiry_runs_total`,
  `promotion_reservation_expiry_expired_total`, `promotion_outbox_unpublished`,
  `promotion_outbox_oldest_unpublished_age_seconds`, `promotion_reservation_expiry_backlog`, and
  `promotion_reservation_expiry_oldest_age_seconds`.
- Direct internal reserve smoke with a valid service internal JWT but unbound client returned `403`
  and emitted `promotion_runtime_operation_total{operation="reserve",result="forbidden"}`.
- Logs showed transient `/eureka/apps/**` errors immediately after discovery/promotion recreate; a
  follow-up 30-second log check found no new errors.
- The Testcontainers JPA smoke class remains skipped locally because the Java Testcontainers client
  cannot connect to the local Docker daemon from the test JVM, even though Docker CLI and Compose are
  reachable.

Known Sprint 2I follow-up:

- Add detailed coupon-match metrics if needed: not supplied, matched, not found, inactive, not started,
  expired, holder mismatch.
- Add dashboard JSON/provisioning for the new promotion metrics.
- Add signed facts snapshot endpoints only if browser relay becomes a real product requirement.
- Start loyalty bounded-context design only after promotion runtime dashboards are reviewed.

## Sprint 2J Implementation Status

The PO/BA, SA/SRE, and senior backend review selected production visibility and coupon diagnostics as
the next gate. The platform already emitted runtime metrics, but operators still needed a stable
Grafana cockpit and coupon failure taxonomy before larger coupon import or loyalty work.

Backend and observability improvements completed in Sprint 2J:

- Added `promotion.coupon.match` metrics with bounded tags: `operation`, `result`, `coupon_supplied`,
  and `coupon_required`.
- Coupon match result taxonomy is: `not_supplied`, `matched`, `not_found`, `inactive`, `not_started`,
  `expired`, `holder_mismatch`, and `no_active_campaign`.
- Coupon diagnostics intentionally do not tag coupon code, coupon id, fingerprint, profile id,
  external reference, campaign id, tenant, or application.
- Runtime `evaluate`, admin `preview`, and runtime `reserve` emit at most one coupon-match metric per
  real decision attempt. Idempotency replay does not re-emit because no matching is re-executed.
- Added `promotion.metrics.refresh` with `success/error` results for cached outbox/reservation gauge
  refresh health.
- Gauge refresh now preserves the last-known values on refresh failure instead of resetting backlog
  and age gauges to zero.
- Added Grafana datasource `uid: courseflow-prometheus` and provisioned the `Promotion Runtime`
  dashboard under the `CourseFlow` folder.
- Dashboard panels cover runtime operation result, runtime p95 latency, coupon match diagnostics,
  idempotency outcomes, quota outcomes, outbox backlog/age, reservation expiry backlog/runs, reversal
  outcomes, metrics refresh health, and 15-minute support pressure.
- Added Prometheus alerts for detailed coupon-match failure spike and metrics refresh failure.

Sprint 2J operations runbook:

- Runtime error/latency alert: open Grafana `Promotion Runtime`, check `Runtime Operations By Result`
  and `Runtime P95 Latency`, then drill into audit explorer by correlation id or operation time
  window.
- Coupon-match alert: open `Coupon Match Diagnostics`, identify whether failures are `not_found`,
  `inactive`, `not_started`, `expired`, or `holder_mismatch`, then use coupon list/detail and campaign
  workspace. Do not search Prometheus by coupon code.
- Quota alert: open `Quota Outcomes`, compare campaign/coupon quota scope, then review campaign
  version limits and coupon detail.
- Outbox alert: open `Outbox Backlog`, then check outbox relay logs before replaying or restarting
  relay.
- Expiry alert: open `Reservation Expiry`, then check the reservation expiry job and stale reserved
  reservations.
- Metrics-refresh alert: treat outbox/expiry gauges as last-known values, check promotion-service DB
  connectivity and repository query failures.
- Reversal alert: open `Redemption Reversal Outcomes`, then inspect redemption support detail and
  audit timeline before retrying an idempotent reversal.

Sprint 2J verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `IncentiveMetricsTest` covers coupon-match metrics and refresh failure preserving last-known gauge
  values.
- `PromotionServiceTest` covers expired coupon, holder mismatch, and quota recheck without
  coupon-match double counting.
- Grafana dashboard JSON parsed successfully with `jq`.
- Docker compose config validation passed for backend plus observability files.
- `promtool check rules` passed; 13 rules were found.
- `promtool check config` passed when mounted at the same paths used by Prometheus.
- Docker compose rebuilt and recreated `promotion-service`.
- Gateway health returned `UP`.
- Grafana health returned `ok`, datasource `courseflow-prometheus` was provisioned, and dashboard
  `Promotion Runtime` was loaded under folder `CourseFlow`.
- Prometheus was reloaded and `promotion-service:8080` target became `up`.
- Direct promotion scrape exposed `promotion_metrics_refresh_total` and the existing promotion runtime,
  outbox, and reservation expiry metrics.
- The Testcontainers JPA smoke class remains skipped locally because the Java Testcontainers client
  cannot connect to the local Docker daemon from the test JVM, even though Docker CLI and Compose are
  reachable.

Known Sprint 2J follow-up:

- Consider HMAC/peppered coupon fingerprints for new coupon codes, with a migration/backfill plan for
  legacy hashes.
- Add data retention and purge policy for idempotency rows, request snapshots, audit payload privacy,
  and old outbox rows.
- Add coupon CSV/import dry-run, duplicate/error report, and export workflow.
- Add a loyalty bounded-context ADR before implementing points, tier, rewards, expiry, earn, burn,
  and reversal.
- Add reservation expiry multi-replica hardening if promotion-service runs with more than one writer.

## Sprint 2K Implementation Status

The PO/BA, SA/security, and senior backend review selected coupon secret hardening as the next
production gate. Coupon operations should not scale through import or loyalty reward generation while
coupon lookup tokens remain dictionary-attackable.

Backend and production-profile improvements completed in Sprint 2K:

- Split coupon canonicalization from fingerprinting:
  - `CouponCodeNormalizer` now owns only normalize, mask, and legacy SHA-256 fallback.
  - `CouponCodeFingerprintService` owns configurable HMAC-SHA256 fingerprinting.
- New coupon writes store `normalized_code` as `hmac-sha256:<keyId>:<hex>`.
- The active key id comes from `PROMOTION_COUPON_FINGERPRINT_KEY_ID`.
- The active pepper/secret comes from `PROMOTION_COUPON_FINGERPRINT_PEPPER`.
- Previous keys can be supplied through `PROMOTION_COUPON_PREVIOUS_FINGERPRINT_KEYS` as comma-separated
  `keyId:secret` entries so lookup survives rotation.
- Runtime/admin lookup is dual-read in deterministic order:
  current HMAC, previous-key HMAC, legacy SHA-256, then legacy raw normalized code.
- New create/generate duplicate detection checks the same lookup set before writing a new HMAC row, so
  old raw/SHA rows cannot be duplicated by creating a new HMAC row with the same coupon code.
- Admin coupon search uses the same lookup set and still returns masks, not raw coupon codes.
- Audit/request snapshots now write the current HMAC fingerprint instead of the previous plain SHA-256
  fingerprint.
- The production compose profile now requires `PROMOTION_COUPON_FINGERPRINT_KEY_ID` and
  `PROMOTION_COUPON_FINGERPRINT_PEPPER` for `promotion-service`.
- The production validation script rejects missing, weak, placeholder, or malformed coupon fingerprint
  production configuration.

Sprint 2K rollout plan:

- Phase 1: deploy dual-read/HMAC-write. Existing raw/SHA coupons continue to redeem, while all new
  coupons use HMAC.
- Phase 2: monitor legacy fallback usage once a bounded metric or DB report is added.
- Phase 3: backfill or reissue legacy coupons. For rows that only store SHA and no raw coupon, prefer
  reissue or alias table migration rather than trying to recover the original coupon.
- Phase 4: disable raw/SHA fallback after the legacy population is retired.

Sprint 2K verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `CouponCodeFingerprintServiceTest` covers versioned HMAC output, no raw leakage, current/previous
  key lookup order, and legacy SHA/raw fallback candidates.
- `CouponCodeNormalizerTest` keeps normalize/mask behavior and documents SHA-256 as legacy only.
- `PromotionServiceTest` covers new coupon creation storing HMAC instead of raw/SHA and duplicate
  detection against a legacy raw row.
- Existing preview tests still prove raw coupon codes are not written into preview audit payloads.
- Existing coupon diagnostics tests still pass after dual-read lookup changes.
- The Testcontainers JPA smoke class remains skipped locally because the Java Testcontainers client
  cannot connect to the local Docker daemon from the test JVM, even though Docker CLI and Compose are
  reachable.

Known Sprint 2K follow-up:

- Add bounded metrics for coupon lookup storage path: current HMAC, previous HMAC, legacy SHA, legacy
  raw, and miss.
- Consider an `incentive_coupon_fingerprints` alias table with algorithm/key id columns before large
  imports or aggressive key rotation.
- Add retention and purge policy/job for expired idempotency rows, old published outbox rows, and
  privacy-sensitive request snapshots while preserving immutable ledger/redemption/campaign-version
  trails.
- Add coupon CSV/import dry-run only after retention and legacy-fallback visibility are in place.
- Draft the loyalty bounded-context ADR before starting any loyalty-service implementation.

## Sprint 2L Implementation Status

The PO/BA, SA/SRE, and senior backend review selected coupon migration readiness as the next gate.
Sprint 2K made new coupon writes safe, but operations still needed a migration signal before legacy
fallback could be disabled.

Backend and observability improvements completed in Sprint 2L:

- Added lookup candidates with explicit storage paths:
  `current_hmac`, `previous_hmac`, `legacy_sha`, and `legacy_raw`.
- Added `promotion.coupon.lookup`, exposed to Prometheus as `promotion_coupon_lookup_total`.
- Lookup metric labels are bounded: `operation`, `storage_path`, `coupon_supplied`, and
  `coupon_required`.
- Lookup metrics intentionally do not tag coupon code, mask, fingerprint, coupon id, campaign id,
  tenant, application, profile id, external reference, correlation id, source client id, or key id.
- `evaluate`, `preview`, and `reserve` emit at most one lookup metric per real decision attempt.
  Idempotency replay does not emit because lookup is not re-executed.
- The metric is emitted from the same diagnostics object as coupon-match metrics, so quota recheck
  paths that call `select(true)` and `select(false)` do not double-count.
- Added `PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED`, defaulting to `true`, so operators can disable
  legacy SHA/raw lookup after migration burn-down.
- Grafana `Promotion Runtime` now includes lookup storage path data in the coupon diagnostics panel.
- Added `PromotionCouponLegacyLookupInUse` info alert to show legacy SHA/raw fallback is still being
  used.

Sprint 2L migration runbook:

- Treat `legacy_sha` and `legacy_raw` as migration debt, not an outage.
- Do not search Prometheus by coupon code or fingerprint; use the time window, support workflow, audit
  explorer, and coupon workspace.
- `legacy_raw` rows can usually be reissued or backfilled from a trusted source because the raw code is
  still present in old storage.
- `legacy_sha` rows cannot be reversed into the original code; prefer reissue or a future alias-table
  migration.
- Keep `PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED=true` until legacy runtime lookup is zero for an
  agreed observation window and active legacy inventory has been retired.
- After disabling fallback, monitor `miss`, `invalid_coupon`, and support tickets before deleting
  legacy lookup code.

Sprint 2L verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `CouponCodeFingerprintServiceTest` covers candidate storage path order and disabling legacy
  fallback.
- `IncentiveMetricsTest` covers `promotion.coupon.lookup`.
- `PromotionServiceTest` covers current HMAC, previous HMAC, legacy SHA, legacy raw, miss, and
  no-active-campaign lookup paths, plus quota recheck without double-counting.
- Grafana dashboard JSON parsed successfully with `jq`.
- `promtool check rules` passed; 14 rules were found.
- Docker compose config validation passed for backend plus observability files.
- The Testcontainers JPA smoke class remains skipped locally because the Java Testcontainers client
  cannot connect to the local Docker daemon from the test JVM, even though Docker CLI and Compose are
  reachable.

Known Sprint 2L follow-up:

- Add a safe inventory report/API that counts active coupon rows by storage format without exposing
  coupon values. Completed in Sprint 2M as the coupon storage inventory contract.
- Add retention and purge policy/job for expired idempotency rows, old published outbox rows, and
  privacy-sensitive request snapshots while preserving immutable ledger/redemption/campaign-version
  trails.
- Consider an `incentive_coupon_fingerprints` alias table with algorithm/key id columns before large
  coupon imports or aggressive rotation.
- Add coupon CSV/import dry-run only after retention and legacy-fallback inventory reporting are in
  place.
- Draft the loyalty bounded-context ADR before starting any loyalty-service implementation.

## Sprint 2M Implementation Status

The PO/BA, UI/UX, SA/SRE, and backend review renamed this gate to Coupon Migration Readiness &
Retention Gate. The implementation deliberately hardened inventory/readiness first; destructive purge
execution and coupon CSV import remain follow-up work.

Backend contract completed in Sprint 2M:

- Added `GET /internal/incentives/coupons/storage-inventory`, exposed through the existing admin
  incentive gateway route.
- Supported filters are `tenantId`, `applicationId`, `campaignId`, and `activeOnly`, defaulting
  `activeOnly` to `true`.
- The response is aggregate-only: it returns `legacyFallbackEnabled`, `fallbackDisableReady`,
  `totalCoupons`, `legacyCoupons`, `malformedCoupons`, `generatedAt`, and ordered bucket counts for
  `current_hmac`, `previous_hmac`, `legacy_sha`, `legacy_raw`, and `malformed`.
- The response intentionally does not expose raw coupon code, `normalized_code`, code mask,
  fingerprint, coupon id, key id, holder profile id, external reference, correlation id, or source
  client id.
- Scoped inventory requires admin/operator access (`ORG_ADMIN` or `INCENTIVE_ADMIN`) for the
  tenant/application or campaign scope. Unscoped/global inventory requires platform `ADMIN`.
- Storage classification is shape-aware:
  - `current_hmac`: `hmac-sha256:<currentKeyId>:<64 hex>`.
  - `previous_hmac`: valid HMAC shape with a non-current key id.
  - `legacy_sha`: exactly 64 lowercase hex characters.
  - `legacy_raw`: nonblank non-HMAC/non-SHA legacy value.
  - `malformed`: blank values or HMAC-looking values with an invalid shape/digest.
- The service always returns all five known buckets in stable order, including zero counts.
- Added coupon inventory indexes for campaign/status/code and campaign scope filtering.

Sprint 2M migration gate:

- `fallbackDisableReady=true` means the selected inventory scope has zero `legacy_sha`,
  `legacy_raw`, and `malformed` rows.
- Do not disable `PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED` from inventory alone. Operators must also
  verify `promotion_coupon_lookup_total{storage_path=~"legacy_sha|legacy_raw"}` is zero for the
  agreed observation window, normally 24 to 72 hours for a production cutover and longer for high-risk
  tenants.
- `previous_hmac` does not block legacy fallback disablement, but it is key-rotation debt and must keep
  matching entries in `PROMOTION_COUPON_PREVIOUS_FINGERPRINT_KEYS` until its own retirement window is
  complete.
- If `legacyFallbackEnabled=false` while inventory still reports `legacy_sha`, `legacy_raw`, or
  `malformed`, treat it as a cutover risk and monitor `miss`, `invalid_coupon`, and support tickets
  before any purge or import scale-up.

Retention/purge contract agreed for the next implementation slice:

- Start with dry-run only. Dry-run must return policy id, cutoff, target dataset, eligible count,
  oldest/newest candidate timestamp, blocked count, blocked reason, batch limit, generated timestamp,
  and an operator-visible result id/hash.
- Preserve immutable ledger, redemption, published campaign-version, and audit trails unless an
  explicit legal/compliance retention policy later allows redaction or archival.
- Purge execution must require a fresh dry-run reference, reason/change ticket, correlation id,
  chunking, audit event, metrics, and a rollback/restore drill. It is not part of Sprint 2M.

Sprint 2M verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `PromotionServiceTest` covers safe ordered inventory counts, readiness, campaign scope, and global
  platform-admin access.
- `PromotionControllerSecurityTest` covers internal endpoint routing, forwarded filters/current user,
  and aggregate-only response shape.
- `PromotionServiceBoundaryTest` covers scoped reviewer denial for migration inventory.
- `PromotionServiceJpaSmokeTest` includes PostgreSQL classification coverage for all storage formats
  and `activeOnly`; locally it remains skipped when the Java Testcontainers client cannot connect to
  Docker, while the overall Maven test gate still passes.

Known Sprint 2M follow-up:

- Implement retention policy registry and dry-run endpoint before any destructive purge. Completed in
  Sprint 2N as a non-destructive aggregate dry-run contract.
- Add the admin read-only `Coupon Storage & Retention Gate` page with filter bar, summary stats,
  readiness checklist, inventory table, and no destructive action.
- Add inventory/export redaction tests before exposing export from admin UI.
- Add coupon CSV/import dry-run only after retention dry-run and storage inventory are both stable.
- Draft the loyalty bounded-context ADR before implementing points ledger, tiers, rewards, earn/burn,
  expiry, or reversal.

## Sprint 2N Implementation Status

Sprint 2N implemented the first retention gate for the generic incentive platform. The goal is to let
operators see what would become eligible under retention policy without deleting, redacting, or
mutating target business data.

Backend contract completed in Sprint 2N:

- Added `GET /internal/incentives/retention/policies`.
- Added `POST /internal/incentives/retention/dry-runs`.
- The registry is code-level and intentionally conservative. It lists runnable policies plus immutable
  `NEVER_PURGE` policies.
- Runnable P0 policies:
  - `expired-idempotency-keys`: aggregate expired `incentive_idempotency_keys`.
  - `published-outbox-events`: aggregate published `outbox_events`; global only because outbox rows do
    not have tenant/application columns.
  - `terminal-reservation-request-snapshots`: aggregate terminal reservation request snapshots for
    future redaction, not row deletion.
- Immutable policies:
  - `immutable-ledger-entries`
  - `immutable-redemptions`
  - `immutable-audit-events`
  - `immutable-campaign-versions`
- Dry-run response is aggregate-only and includes dry-run id, result hash, scope, cutoff, retention
  days, eligible count, blocked count, oldest/newest candidate timestamp, batch limit, and warnings.
- Dry-run writes only an audit event `retention.dry_run_requested`; it does not update/delete target
  idempotency, outbox, reservation, redemption, ledger, campaign-version, coupon, or audit rows.
- Scoped dry-run requires `ORG_ADMIN` or `INCENTIVE_ADMIN` for the tenant/application. Global dry-run
  requires platform `ADMIN`. Runtime service actors are rejected.
- Response/audit payloads intentionally do not include raw `request_json`, `response_json`, outbox
  payload, idempotency key, coupon code, fingerprint, profile id, external reference, or row ids.
- Added bounded dry-run metrics:
  `promotion_retention_dry_run_requests`,
  `promotion_retention_dry_run_candidates`, and
  `promotion_retention_dry_run_duration_seconds`.
- Added dry-run predicate indexes for idempotency expiry, published outbox rows, and terminal
  reservations.
- Disabled outbox-relay published-row purge by default through `courseflow.outbox.purge-enabled=false`.
  Future destructive outbox purge must go through a dedicated approval/audit sprint.

Sprint 2N production gate:

- Do not add retention execution endpoints until dry-run results can be reviewed from API/UI and
  backed by a restore drill.
- Keep `OUTBOX_PURGE_ENABLED=false` in production unless a future purge execution design explicitly
  approves it.
- Treat `published-outbox-events` dry-run as global until outbox rows carry tenant/application
  metadata or a safe projection table exists.
- Do not purge or redact ledger, redemption, audit, or published campaign-version trails.
- Do not expose samples or row ids in enterprise/admin UI until a redaction layer and purpose-bound
  access model are implemented.

Sprint 2N verification:

- `mvn -pl services/promotion-service,services/outbox-relay -am test -DskipTests=false` passed.
- `RetentionPolicyRegistryTest` covers stable policy ids and `NEVER_PURGE` registry entries.
- `RetentionDryRunServiceTest` covers scoped/global auth, aggregate result mapping, audit event,
  scoped outbox blocking, partial-scope rejection, and minimum-retention guard.
- `PromotionControllerSecurityTest` covers retention policy/dry-run controller boundaries.
- `IncentiveMetricsTest` covers bounded dry-run metrics.
- Testcontainers JPA smoke remains skipped locally when the Java Docker client cannot connect to the
  Docker daemon; the Maven gate still passes.

Known Sprint 2N follow-up:

- Add the admin read-only `Retention Gate` page.
- Add persisted dry-run history only if operators need approval handoff or compare drift over time.
- Implement retention execution as a separate sprint with fresh dry-run reference, reason/change
  ticket, chunking, metrics, audit, backup/restore drill, and rollback plan.
- Add schema-aware request snapshot redaction before any redaction execution.
- Add coupon CSV/import dry-run after retention UI and storage inventory are stable.
- Draft the loyalty bounded-context ADR before coding loyalty-service.

## Sprint 2P-D-B Implementation Status

Sprint 2P-D-B implements the first destructive retention execution, limited to redacting legacy
terminal reservation request snapshots. It does not purge rows and does not mutate ledger,
redemption, audit, campaign-version, coupon, outbox, or idempotency evidence.

Backend contract completed in Sprint 2P-D-B:

- Added `POST /internal/incentives/retention/executions`.
- Only `terminal-reservation-request-snapshots` is executable. Other retention policies remain
  dry-run only until they have their own approval and restore design.
- Execution requires an authenticated non-service operator, scope authorization, `confirm=true`,
  `approvedDryRunId`, `approvedResultHash`, `idempotencyKey`, `reason`, `changeTicket`,
  `restoreDrillRef`, and `X-Correlation-Id`.
- The service recomputes the dry-run server-side from current data and rejects stale or mismatched
  approvals. The dry-run hash now includes `batchLimit` so approval cannot be reused with a larger
  destructive batch.
- Added `incentive_retention_operations` for idempotency, operation status, actor, reason, change
  ticket, restore drill reference, aggregate counts, and replayable aggregate response JSON.
- Redaction uses a JPA native update with `FOR UPDATE SKIP LOCKED`, ordered by terminal timestamp and
  id, so multiple promotion-service replicas can claim different rows safely.
- The replacement `request_json` is a minimal redaction envelope with policy/version, execution id,
  dry-run id, result hash, redacted timestamp, `retentionRedacted=true`, and
  `requestSnapshotMinimized=true`. It contains no raw request context, coupon data, profile id,
  external reference, item id, row id, or payload sample.
- Execution writes aggregate-only audit events `retention.execution_requested` and
  `retention.execution_completed`.
- Added bounded metrics:
  `promotion_retention_execution_requests`,
  `promotion_retention_execution_redacted`, and
  `promotion_retention_execution_duration_seconds`.
- Added `PROMOTION_RETENTION_EXECUTION_ENABLED` and
  `PROMOTION_RETENTION_EXECUTION_DRY_RUN_TTL_MINUTES` runtime configuration.
- `scripts/postgres-backup-drill.sh` now includes `cf_promotion`, making a restore drill possible for
  the exact database touched by retention execution.

Sprint 2P-D-B production gate:

- Keep `PROMOTION_RETENTION_EXECUTION_ENABLED=false` in production until the operator runbook requires
  a fresh dry-run, restore-check artifact, change ticket, and reviewer approval.
- Run `scripts/postgres-backup-drill.sh backup` and
  `scripts/postgres-backup-drill.sh restore-check <backup-dir> cf_promotion` before the first
  destructive execution in a production environment.
- Do not expose row ids, payload samples, or raw request snapshots in the admin UI.
- Treat failed DB smoke through Java Testcontainers as an environment issue only if Docker CLI smoke
  and service health checks pass; do not skip SQL syntax/liquibase validation in CI.

## Sprint 2P-D-C Implementation Status

Sprint 2P-D-C hardens the destructive retention execution gate before any production enablement.
It keeps the same executable policy scope: only legacy terminal reservation request snapshot
redaction.

Backend contract completed in Sprint 2P-D-C:

- Added restore-drill registry APIs:
  - `POST /internal/incentives/retention/restore-drills`
  - `GET /internal/incentives/retention/restore-drills/{restoreDrillRef}`
- Added approval workflow APIs:
  - `POST /internal/incentives/retention/approvals`
  - `GET /internal/incentives/retention/approvals/{approvalId}`
  - `POST /internal/incentives/retention/approvals/{approvalId}:approve`
  - `POST /internal/incentives/retention/approvals/{approvalId}:reject`
- Execution now requires `approvalId`, `idempotencyKey`, `confirm=true`, and `X-Correlation-Id`.
  The old body-only proof fields are no longer sufficient to execute redaction.
- Approval creation recomputes the dry-run hash server-side and requires a valid registered
  `cf_promotion` restore drill.
- Restore-drill registration rejects future evidence, non-`cf_promotion` databases, and malformed
  `sha256:<64-hex>` artifact hashes.
- Approval review revalidates current candidates, requires review access, and rejects self-approval.
- Execution requires an approved, unexpired approval row; executor must differ from approver.
- An approval can produce at most one execution operation through `approval_id` and a unique
  operation index.
- Active approvals are unique by `policy_id + scope_key + dry_run_id + dry_run_result_hash +
  batch_limit`, preventing duplicate approvals from multiplying a single approved dry-run.
- Execution commits the `IN_PROGRESS` operation before destructive work, runs redaction in a separate
  transaction, and records `FAILED` operation state plus `EXECUTION_FAILED` approval state after
  rollback.
- Execution failure records `retention.execution_failed` audit and failure metrics in a separate
  transaction, without mutating already `SUCCEEDED` operations.
- Prometheus now exposes `promotion_retention_execution_stale_in_progress` and alerts on failed or
  stuck destructive retention execution.

Remaining production-enable blockers:

- Run browser-based acceptance for the admin Retention Console against the Docker backend cluster,
  then retain screenshots/evidence with the release record.
- CI must run the PostgreSQL/Testcontainers JPA smoke, including Liquibase 012-016 and the redaction
  CTE path.
- Run and retain the restore-check evidence JSON from `scripts/postgres-backup-drill.sh restore-check
  <backup-dir> cf_promotion` in the real production release record.

Sprint 2AQ restore-check evidence artifact:

- `scripts/postgres-backup-drill.sh restore-check` now writes a machine-readable
  `postgres_restore_drill_evidence` JSON file after `pg_restore` and a restored-database probe pass.
- The evidence includes `restoreDrillRef`, `databaseName`, `backupPath`, `artifactHash`,
  `status=PASSED`, `checkedAt`, source Postgres container/user, and the temporary restore database
  name. For `cf_promotion`, these values are the source of truth for
  `POST /admin/v1/incentives/retention/restore-drills`.
- The backup command now points operators to restore-check `cf_promotion` by default because
  promotion retention redaction touches `cf_promotion`, not only the historical identity example.

Sprint 2AR Retention Console restore evidence import:

- Web admin `Incentives > Retention` now accepts the `postgres_restore_drill_evidence` JSON emitted
  by `scripts/postgres-backup-drill.sh restore-check <backup-dir> cf_promotion`.
- The console validates the evidence artifact type, `databaseName=cf_promotion`, `status=PASSED`,
  `artifactHash=sha256:<64-hex>`, and timestamp shape before filling restore-drill registration
  fields. This closes the operator gap between a restore-check artifact and the restore-drill API
  without asking the operator to manually retype hash material.
- The existing destructive execution gates remain unchanged: dry-run freshness, restore-drill
  lookup, two-person approval, idempotency key, correlation id, `confirm=true`, and audit panels.

Sprint 2AS Retention Console gate coverage:

- Web admin retention destructive-action gate logic now lives in a pure helper module so production
  rules can be tested without rendering the full console.
- Unit coverage locks the current SA decisions: dry-run expires after the configured TTL, scope
  fingerprints change when batch/retention inputs change, restore drill must match `cf_promotion`
  with `PASSED` status and a SHA-256 artifact hash, requesters cannot approve their own approval,
  unauthenticated/unknown operators cannot decide or execute, approvers cannot execute their own
  approval, and expired/consumed/failed approvals block execution.
- `promotion-service` now rejects approve/reject decisions for expired pending retention approvals,
  so the backend source of truth matches the console's fail-closed gate.
- This keeps the React UI as orchestration only; backend remains the source of truth for destructive
  execution, but the console now fails closed before an operator can submit unsafe actions.

Sprint 2AT Retention approval queue:

- `promotion-service` now exposes `GET /internal/incentives/retention/approvals` for retention
  approval queue operations. Filters include scope type, tenant/application, approval id, dry-run id,
  status, policy id, change ticket, actor fields, expired flag, created time range, and bounded
  limit. The response follows the enterprise queue contract `{items, limit, hasMore, generatedAt}`.
- Retention approval DTOs now include evidence fields needed by reviewers and auditors: reason,
  note, rejected actor/time, failure time, correlation id, and source client id. Detail lookup now
  uses the same reviewer access rule as approve/reject.
- Liquibase adds retention approval queue indexes for tenant/application/status, global status,
  dry-run lookup, and change-ticket lookup. OpenAPI now documents the retention queue endpoint and
  the previously implemented coupon import operation export endpoint.
- Web admin `Incentives > Retention` now starts with a retention approval queue. Operators can
  filter pending/approved/rejected/executed/failed approvals, expired/not expired approvals, ids,
  ticket, actor, scope, and time range; rows show aggregate counts, hashes, restore evidence handle,
  actor chain, expiry, and derived state badges before loading the selected approval into the
  existing review/execution workflow.

Sprint 2AU Retention compliance evidence pack:

- `promotion-service` now exposes audit-safe retention evidence pack endpoints:
  `GET /internal/incentives/retention/approvals/{approvalId}/evidence-pack` and
  `GET /internal/incentives/retention/approvals/{approvalId}/evidence-pack/export?format=json|csv`.
- The pack contains schema/version metadata, the immutable approval snapshot, restore drill evidence,
  nullable execution evidence, audit trail entries ordered oldest-first, and warnings for incomplete
  evidence. Audit trail payloads are summarized through an allowlist and do not expose raw request
  snapshots, raw response JSON, reservation/profile identifiers, raw idempotency keys, uploaded file
  contents, or backup artifact contents.
- Viewing a pack writes `retention.evidence_pack_viewed`. Exporting JSON/CSV writes
  `retention.evidence_pack_exported` with the content SHA-256, format, included audit event count,
  approval id, dry-run id, result hash, ticket, and restore drill reference, but never the exported
  content itself.
- Web admin `Incentives > Retention` queue rows now support `Evidence`, `JSON`, and `CSV` actions.
  The evidence drawer shows approval, restore drill, execution, warning, and audit summary sections
  with `Incomplete evidence`, `Complete evidence`, and `Failed evidence` badges.

Sprint 2AV Retention RBAC reason-code UX:

- Web admin retention destructive-action gates now expose structured reason codes plus operator
  messages instead of only boolean disabled state. The current slice covers approval decision and
  execution gates.
- Approval decision gate returns `AUTH_CONTEXT_UNRESOLVED`, `RBAC_REVIEW_REQUIRED`,
  `GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN`, `APPROVAL_NOT_PENDING`, `APPROVAL_EXPIRED`, and
  `SELF_APPROVAL_BLOCKED` where applicable.
- Execution gate returns `AUTH_CONTEXT_UNRESOLVED`, `RBAC_RETENTION_ADMIN_REQUIRED`,
  `GLOBAL_RETENTION_REQUIRES_PLATFORM_ADMIN`, `APPROVAL_NOT_APPROVED`, `APPROVAL_EXPIRED`,
  `APPROVAL_CONSUMED`, `EXECUTION_ATTEMPT_BLOCKED`, and `SELF_EXECUTION_BLOCKED` where applicable.
- The Retention Console renders these reason codes as compact operational evidence in reviewer and
  execution notices, while retaining human-readable messages in button titles. This keeps the UI
  aligned with backend maker-checker/RBAC semantics and gives support teams stable codes to search
  in tests, runbooks, and future component assertions.
- Deferred follow-up: apply the same gate-result pattern to coupon import/commit/single-coupon
  operations, including the scoped `INCENTIVE_OPERATOR` role, before broadening mutation access.

Sprint 2AW Coupon import operator RBAC and reason-code UX:

- Coupon import now has bounded-context access methods instead of reusing generic application admin
  access for every operation. `requireCouponImportManageAccess` allows platform `ADMIN` plus scoped
  `ORG_ADMIN`, `INCENTIVE_ADMIN`, and `INCENTIVE_OPERATOR`; `requireCouponImportReadAccess` also
  allows scoped `INCENTIVE_REVIEWER`.
- `INCENTIVE_OPERATOR` can run import dry-runs, request approvals, and commit already-approved
  imports for its tenant/application scope, but it still cannot manage incentive applications,
  campaign lifecycle, retention, or approve/reject coupon import approvals.
- Coupon import history, operation detail, masked issue export, approval queue, and approval detail
  use coupon import read access. Approval decisions continue to use review access so
  `INCENTIVE_OPERATOR` cannot become checker.
- Web admin coupon import gates now use structured reason codes for dry-run, approval request,
  approval decision, and commit readiness. The first code set covers RBAC, campaign/CSV readiness,
  stale dry-runs, commit-ready state, required reason/change ticket, approval state/expiry,
  self-approval, self-commit, idempotency key, correlation id, confirm, and completed commit.
- Sprint 2AX now aligns access-control-service permission seed with explicit coupon-import
  permissions. Remaining follow-up: map backend forbidden/rate-limit responses into stable web
  reason codes.

Sprint 2AX Coupon import permission contract:

- `access-control-service` now has explicit application-scoped coupon import permissions:
  `incentive:coupon:import:read`, `incentive:coupon:import:manage`, and
  `incentive:coupon:import:review`.
- `incentive:coupon:manage` remains for individual coupon lifecycle operations and no longer acts
  as the broad import permission for `INCENTIVE_OPERATOR`.
- `INCENTIVE_ADMIN` receives coupon read/manage plus coupon import read/manage/review.
  `INCENTIVE_REVIEWER` receives coupon read plus coupon import read/review.
  `INCENTIVE_OPERATOR` receives coupon read plus coupon import read/manage, but not coupon import
  review and not broad coupon manage.
- Liquibase changeset `004-incentive-coupon-import-permissions.sql` inserts the explicit permissions
  and removes the broad `incentive:coupon:manage` grant from `INCENTIVE_OPERATOR`, so fresh and
  already-migrated databases converge on the same contract.
- Access-control unit tests and JPA smoke now prove the operator/reviewer split:
  operator can manage imports but cannot review approvals; reviewer can review imports but cannot
  manage/commit them.

Sprint 2AY Coupon import server-gate reason mapping:

- Web admin coupon import operations now map backend `ErrorDto`/HTTP failures into the same
  structured reason-code model used by client-side gates.
- The first server-gate mapper covers:
  - `403` permission failures, mapped to `RBAC_COUPON_MANAGE_REQUIRED`, `RBAC_REVIEW_REQUIRED`, or
    `SERVER_FORBIDDEN`.
  - `429` admin operation guard failures, mapped to `SERVER_RATE_LIMITED`.
  - `409` workflow conflicts, mapped to approval state, dry-run expiry, stale/result-hash mismatch,
    commit already completed, idempotency reuse/expiry, duplicate coupon, or generic server conflict.
  - `400`, `404`, and `5xx` fallback codes for validation, missing resources, and unexpected server
    failure.
- Coupon Import Console renders these server-gate issues for dry-run, approval request,
  approve/reject, commit, and operation export mutations instead of showing only raw Axios messages.
- Unit tests now lock the high-risk mappings for RBAC manage/review, rate limit, result-hash
  mismatch, and idempotency key reuse.
- Deferred follow-up: introduce backend machine-readable error codes in `ErrorDto` so web mapping can
  stop depending on controlled message patterns.

## Sprint 2O Implementation Status

The PO/BA, SA/SRE, and backend review split on Retention Execution vs Coupon Import, but the SA/SRE
review found a higher-priority production blocker: application client bindings were effectively
fail-open when `allowed_operations=[]`. Sprint 2O fixes that security gate before adding more
runtime surfaces.

Backend contract completed in Sprint 2O:

- `allowed_operations=[]` now means deny all, not allow all.
- Runtime/admin operation checks require the requested operation to be explicitly present in the
  active client binding.
- Supported binding operations are `admin`, `evaluate`, `reserve`, `commit`, `cancel`, and `reverse`.
- Campaign status changes, coupon status changes, campaign-version draft creation/update, submit,
  approve, reject, publish, and rollback now require both the existing role check and an explicit
  client binding for `admin`.
- `POST /internal/incentives/applications/{applicationUuid}/client-bindings` normalizes operation
  names, deduplicates them, rejects blank/unknown operations, and audits the resulting allowlist.
- The older `allowedClientIds` convenience field on application create/update remains a binding
  registration helper only. It creates/reactivates clients with an empty allowlist, so operators must
  explicitly grant operations through the client-binding endpoint.
- Malformed or non-array `allowed_operations` values are normalized to deny-all by migration before a
  database check constraint enforces JSON array shape.

Sprint 2O production gate:

- Do not treat a bound client as trusted for any incentive operation until the binding has an explicit
  operation allowlist.
- Do not use `allowedClientIds` as an authorization grant. It is only a registration/suspension
  convenience until a richer application onboarding workflow replaces it.
- Keep runtime user/browser traffic blocked by `actor_type=service`; operation allowlists are not a
  replacement for service-actor attestation.
- Sprint 2P adds token-scope enforcement with `internal:promotion:<operation>` scopes, so service
  actors must present both a matching internal JWT scope and a matching application client binding.

Sprint 2P operation-scope gate:

- `/internal/incentives/evaluate` requires `internal:promotion:evaluate`.
- `POST /internal/incentives/reservations` requires `internal:promotion:reserve`.
- Reservation commit/cancel endpoints require `internal:promotion:commit` and
  `internal:promotion:cancel`.
- Redemption reversal requires `internal:promotion:reverse`.
- Other incentive admin/internal endpoints fall back to `internal:promotion:admin` for service
  actors.
- User/admin UI traffic continues through user internal JWTs plus role/scoped-role checks; promotion
  operation scopes are not granted to `api-gateway` by default.
- The STS client-scope policy grants promotion operation scopes only to the explicitly configured
  promotion/integrating service clients such as `checkout-service` and the enrollment coupon BFF;
  wildcard grants are rejected by the production validator.

## Sprint 2P-B - Outbox DLQ Visibility And Replay

The recoverability gate closes the "green lag, hidden failure" gap in `outbox-relay`. When a poison
event exhausts its non-retryable publish attempt budget, the relay may mark the source row as
published to unblock the stream. That must not hide the failure from operators.

Implemented production behavior:

- `relay_dead_letters` tracks status: `OPEN`, `REPLAYING`, `FAILED`, `REPLAYED`, or `DISCARDED`.
- `relay_delivery_states` persists publish failure attempts across relay restart/replica movement.
- `relay_operator_actions` makes replay/discard idempotent by `(idempotencyKey, action,
  deadLetterId)`.
- `relay_dead_letter_approvals` adds maker-checker for live replay/discard: the maker submits action,
  reason, evidence reference, payload hash, request hash, and `OUTBOX_DLT_DUAL_CONTROL_V1`; a
  different platform admin must approve before execution.
- Dead-letter API responses expose only metadata, error text, payload size, and `payloadHash`; raw
  event payload is never returned by list/detail/replay responses.
- `POST /internal/outbox/dead-letters/{id}:replay` reuses the original `event_type`, `aggregate_id`,
  and stored payload. Operators cannot override the Kafka topic or payload. Live replay requires an
  approved `approvalId`; dry-run does not.
- `POST /internal/outbox/dead-letters/{id}:discard` records the resolution actor and note without
  deleting the row. Live discard also requires an approved `approvalId`.
- Gateway route `/api/admin/v1/outbox/**` maps to `outbox-relay`; the controller requires platform
  `ADMIN`.
- Outbox relay metrics include publish failures, created dead letters, replay results, open dead
  letter gauges, and oldest open dead-letter age.
- Prometheus alerts now fire for promotion DLQ rows, aging DLQ rows, and elevated relay publish
  failures.

Operational runbook:

1. Inspect `GET /api/admin/v1/outbox/dead-letters?status=OPEN&service=promotion`.
2. Fix the downstream broker/topic/consumer/config issue first.
3. Submit approval with action, reason, and evidence:
   `POST /api/admin/v1/outbox/dead-letters/{id}/approvals`.
4. A different platform admin approves:
   `POST /api/admin/v1/outbox/dead-letters/approvals/{approvalId}:approve`.
5. Replay with an idempotency key, reason, and approved `approvalId`:
   `POST /api/admin/v1/outbox/dead-letters/{id}:replay`.
6. If the event is intentionally abandoned, discard with an idempotency key, reason, and approved
   `approvalId`.
7. Treat replay as at-least-once. Consumers must continue deduplicating by the stable event identity
   in the payload.

## Sprint 2P-C - Reservation Expiry Multi-Replica Safety

The reservation expiry job is safe to run on multiple `promotion-service` replicas. The job still
uses the existing JPA repository/domain service pattern; the only PostgreSQL-specific behavior is
inside the Spring Data repository query that must claim expired rows without waiting on rows already
held by another worker.

Implemented production behavior:

- Expiry batch claim uses a native JPA query with `FOR UPDATE SKIP LOCKED`.
- The query only claims `status = 'RESERVED'` rows whose `expires_at <= :now`.
- Claim order is deterministic by `expires_at, id` and bounded by the configured batch size.
- The service keeps the existing transactional domain flow: release quota, mark reservation expired,
  persist one `EXPIRE` ledger entry, write audit, then emit expiry metrics.
- No JDBC repository or bulk update path was added to `promotion-service`.
- Concurrent workers get disjoint expired rows instead of blocking on the same oldest reservation.

Operational notes:

- `courseflow.promotion.reservation-expiry.enabled` may be enabled on more than one replica.
- Keep `courseflow.promotion.reservation-expiry.batch-size` bounded; the service clamps requests to
  `1..500`.
- Watch `promotion_reservation_expiry_backlog`, `promotion_reservation_expiry_oldest_age_seconds`,
  `promotion_reservation_expiry_runs_total`, and `promotion_reservation_expiry_expired_total` after
  scaling writer replicas.
- Retry/duplicate safety still depends on the domain invariant that only `RESERVED` reservations can
  expire. Terminal `REDEEMED`, `CANCELLED`, `EXPIRED`, and `FAILED` reservations are ignored.

## Sprint 2P-D-A - Request Snapshot Write-Time Minimization

The privacy gate starts by changing what the platform writes from now on. It does not mutate legacy
reservation snapshots yet; destructive redaction execution remains a separate gate that still needs a
fresh dry-run reference, audit event, restore-drill reference, and reviewer approval.

Implemented production behavior:

- `ReservationRequestSnapshotSanitizer` builds reservation `request_json` from an allowlist instead
  of serializing the full evaluation request.
- New snapshots carry `snapshotVersion=reservation-request-snapshot.v2`, `policyId`, `policyVersion`,
  and `requestSnapshotMinimized=true`.
- Raw `profileId` and `externalReference` are replaced by HMAC-SHA256 fingerprints.
- Coupon snapshots keep only count and masked codes; raw coupon codes and coupon fingerprints are not
  stored in reservation request snapshots or preview audit payloads.
- Item ids, item attributes, and root request attribute values are not stored. The snapshot keeps
  aggregate counts, item types, total quantity, and attribute key names only.
- Admin preview audit payloads use the same sanitized facts and no longer write raw profile,
  external reference, or coupon fingerprint data.
- Retention dry-run for terminal reservation snapshots excludes rows already marked
  `requestSnapshotMinimized=true` or `retentionRedacted=true`, so operators can distinguish legacy
  rows that still need a future redaction execution.

Operational notes:

- Configure a dedicated `courseflow.promotion.request-snapshot.hash-secret` in production. If it is
  not set, the service falls back to the internal JWT secret, which is acceptable for local/dev but
  should not be the long-term enterprise keying model.
- Existing terminal reservation snapshots are not rewritten by this sprint.
- Retention execution for legacy snapshots remains blocked until a separate destructive-execution
  sprint adds approved dry-run replay, chunked `FOR UPDATE SKIP LOCKED` claims, audit, metrics, and
  restore-drill enforcement.

Sprint 2O verification:

- `mvn -pl services/promotion-service -am test -DskipTests=false` passed.
- `IncentiveAccessServiceTest` covers empty allowlist denial, explicit operation pass, wrong
  operation denial, and unsupported operation rejection.
- `PromotionServiceBoundaryTest` covers empty admin-binding denial for campaign and coupon status
  mutations.
- `CampaignVersionServiceBoundaryTest` covers empty admin-binding denial for create draft, update
  draft, submit, approve, reject, publish, and rollback.
- `git diff --check` passed for the worktree.
- Liquibase changelog XML parsed successfully with `xmllint`.
- Docker rebuild/recreate for `promotion-service` passed.
- Liquibase applied `promotion-011-client-binding-fail-closed-normalize` and
  `promotion-011-client-binding-fail-closed-constraint` in the local `cf_promotion` database.
- The database constraint `chk_incentive_application_client_allowed_operations_array` exists, and no
  binding row has a non-array `allowed_operations` value.
- Promotion health is `UP` through the Docker network, and an unauthenticated gateway call still
  returns `401`.
- Testcontainers JPA smoke remains skipped locally when the Java Docker client cannot connect to the
  Docker daemon; the Maven gate still passes.

Known Sprint 2O follow-up:

- Extend promotion operation scopes to any future checkout/order/integrating service client only
  through explicit `COURSEFLOW_STS_CLIENT_SCOPES` entries and matching application bindings.
- Add destructive legacy request snapshot redaction execution after the write-time minimization gate,
  with approved dry-run reference, restore drill, audit, metrics, and chunked locking.
- Add coupon CSV/import dry-run and import history after this security gate remains stable.
- Draft the loyalty bounded-context ADR before implementing account, points ledger, tiers, rewards,
  earn/burn, expiry, and reversal.

## Open Source Reference Patterns

The team reviewed common patterns from:

- Spree Promotions: rules/actions and adjustment model.
- Sylius Promotion: rule/action abstractions and coupon usage limits.
- django-oscar Offers/Vouchers: availability, conditions, benefits, caps.
- Adobe Commerce cart rules and reward points: late checkout context and exchange rates.
- Voucherify: qualification, validation, redemption, rollback, stackable redeemables.
- Talon.One: campaign rules and effects.
- OpenLoyalty: loyalty program, points states, API-first loyalty engine.

## Sprint 2Q Portable Contract Slice

The PO/BA/SA/backend review selected portable contract hardening as the next generic-platform slice.
Coupon import and loyalty ledger remain important, but the platform first needs a formal contract that
integrators and admin UI can inspect without reading Java source.

Implemented in this slice:

- `GET /internal/incentives/catalog` exposes the rule/action/effect/reason/idempotency catalog.
- `IncentiveEffectDto` now keeps the existing money fields and adds portable effect metadata:
  `effectId`, `benefitType`, `actionType`, `unit`, `quantity`, and `campaignVersion`.
- Decision effects emitted by the current engine are classified as `benefitType=DISCOUNT`,
  `unit=MONEY`; future non-discount effects are reserved in the catalog rather than implied by
  campaign metadata.
- Typed incentive redemption committed/reversed event contracts were added under `event-contracts`.
- Redemption committed/reversed events include nullable `couponId` so coupon attribution can be
  reconciled from events without joining back to promotion-service.
- The outbox payload for redemption commit/reverse now serializes typed event records while preserving
  existing event type names and top-level correlation/source-client fields.
- Legacy or in-flight stored effect JSON is normalized when emitted as event v1 so `effectId`,
  `benefitType`, `actionType`, `unit`, and `quantity` remain present where possible.
- Public catalog reason codes now describe the runtime contract and do not expose wildcard rule
  failure codes that are not returned as public response codes.
- Loyalty bounded-context ADR was added at
  `backend/docs/architecture/loyalty-bounded-context-adr.md`.

Sprint 2Q verification:

- PO, BA, SA, and Senior Backend Dev review returned GO after the contract fixes.
- `DOCKER_HOST=unix:///Users/hoapham/.docker/run/docker.sock mvn -q -pl event-contracts,services/promotion-service -am test -DskipTests=false -DtrimStackTrace=true`
  passed.
- `PromotionServiceJpaSmokeTest` ran against a real PostgreSQL Testcontainer with `tests=7`,
  `failures=0`, `errors=0`, `skipped=0`.
- Testcontainers BOM was raised to `1.21.4` because `1.20.3` could not connect reliably to the
  current Docker Desktop/Engine combination and caused false-positive skipped DB smoke locally.

Known follow-up:

- Formal OpenAPI plus AsyncAPI/JSON Schema for `/internal/incentives/*` and redemption events,
  including schema compatibility policy.
- Ledger reconciliation contract for normalized `effectId`, effect type, amount, currency, `couponId`,
  operation id, redemption id, and reversal link.
- Coupon CSV/import dry-run, commit history, duplicate report, masked error export, and legacy
  fallback shutdown checklist.
- Retention approval/execution list APIs for operator discoverability.
- Loyalty ADR acceptance before implementing loyalty accounts, points ledger, tiers, rewards, earn,
  burn, expiry, and reversal.

## Sprint 2R Incentive Contract Pack v2

The PO, BA, SA, and Senior Backend Dev review selected formal contract hardening as the next P1
slice. Coupon bulk import and loyalty implementation remain deferred because they would create or
consume large volumes of incentive records before the external API, event, and reconciliation
contracts are stable.

Implemented in this slice:

- `backend/docs/contracts/incentives/openapi.yaml` documents the current `/internal/incentives/**`
  REST surface, gateway aliases, auth model, idempotency behavior, and response/error shape.
- `backend/docs/contracts/incentives/asyncapi.yaml` documents the current redemption event topics:
  `incentive.redemption.committed` and `incentive.redemption.reversed`.
- JSON Schema files define the portable effect envelope, committed/reversed event payloads, and a
  normalized reconciliation projection.
- Golden examples cover committed, reversed, and reconciliation payloads without raw coupon code or
  coupon fingerprint exposure.
- `backend/docs/contracts/incentives/compatibility.md` defines additive-only event v1 evolution,
  idempotency semantics, privacy rules, and reconciliation invariants.
- `backend/docs/architecture/loyalty-bounded-context-adr.md` moved from `Proposed` to `Accepted`.

Sprint 2R reconciliation stance:

- Promotion remains the source of truth for promotion/coupon reservation, redemption, ledger, audit,
  and outbox records.
- Consumers reconcile by `redemptionId + effectId`; no consumer should join back to mutable campaign
  or coupon state to compute net benefit.
- `COMMIT` maps to `direction=APPLY`; `REVERSE` maps to `direction=COMPENSATE`.
- `couponId` remains nullable for non-coupon incentives.
- Current committed-redemption reversal uses `quotaPolicy=NO_RELEASE_ON_COMMITTED_REVERSAL` and
  keeps `quotaReleased=false` by default.

Sprint 2S operations/correctness update:

- `GET /internal/incentives/reconciliation/entries` exposes a read-only support/finance view over
  ledger entries, effect rows, redemption state, outbox state, correlation id, source client id, and
  quota policy.
- Reconciliation rows remain effect-level and use `redemptionId + entryType + effectId` as a stable
  row key. Raw coupon codes, coupon fingerprints, and raw request snapshots are not returned.
- Runtime reservation now treats quota consume as a bounded candidate attempt. If a preferred
  campaign passes decisioning but loses a quota race while locking/consuming counters, the service
  releases any partially consumed counters and tries the next deterministic candidate before
  returning `QUOTA_EXHAUSTED`.
- The current resolver is still intentionally single-best: published campaign versions are evaluated
  by deterministic priority order (`priority desc`, `createdAt asc`). Full multi-campaign stacking
  and compatibility groups remain a separate runtime policy sprint.
- Admin preview/simulation exposes simulation-only stacking governance for each matched candidate:
  `stackingStatus`, `stackingReasonCodes`, `exclusive`, `stackable`, and would-consume quota
  exposure. `WOULD_STACK` means policy-compatible under the sample context; it does not mean runtime
  reservation/commit already applies multiple campaigns.

Sprint 2T operations console/history update:

- Web admin now includes a coupon import console for CSV dry-run, masked issue/sample review,
  maker/checker approval, approved commit, idempotency/correlation evidence, approval queue, commit
  operation history, and audit drill-down.
- Web admin also includes a reconciliation viewer with tenant/application scoped filters, effect
  rows, quota policy, outbox status, correlation/source client, and detail drawer.
- `GET /internal/incentives/coupons/import-dry-runs` exposes read-only dry-run history with counters,
  masks/hashes, actor/correlation, expiry, and commit outcome fields.
- `GET /internal/incentives/coupons/import-operations` and
  `GET /internal/incentives/coupons/import-operations/{importId}` expose read-only commit history.
  These projections intentionally omit raw CSV content, raw coupon codes, request hashes,
  idempotency key hashes, coupon fingerprints, and stored response JSON.
- Reconciliation queries now require explicit `tenantId` and `applicationId`; global reconciliation
  scans require a future explicit audited global-query contract instead of platform-admin fallback.
- Gateway no longer exposes promotion runtime operations (`evaluate`, `reservations/**`) as
  browser-facing `/api/v1/incentives/**` routes. Admin import/reconciliation operations go through
  `/api/admin/v1/incentives/**`; runtime calls remain service-to-service.

Sprint 2U enterprise runtime hardening update:

- The PO/BA/SA/UI/Tech Lead/QA roundtable selected release hardening over loyalty or large UI work.
- Access-control now treats `TENANT` and `APPLICATION` as first-class assignment/permission scopes
  and seeds `INCENTIVE_ADMIN`, `INCENTIVE_REVIEWER`, and `INCENTIVE_OPERATOR` roles.
- Runtime mutation contracts use `Idempotency-Key` as the canonical retry key; request-body
  `idempotencyKey` fields remain compatibility fallbacks while clients migrate.
- Security observability now includes token-converter, access-control, and user-management scrape
  targets plus alerts for STS failures, JWKS failures, internal JWT rejections, and authz denial
  spikes.
- Runtime incentive API remains service-to-service only. Browser/learner/admin clients must go
  through a source domain workflow or BFF that resolves trusted facts server-side.
- Post-review hardening closed the two release blockers found by SA/Tech Lead:
  `user:assign-role` is now an `ANY` permission so a platform admin can assign incentive roles at
  `TENANT`/`APPLICATION` scope, and `APPLICATION` scope ids are validated as `tenantId:applicationId`.
- STS client policy now models the intended runtime chain: trusted source clients such as
  `checkout-service` and `enrollment-service` receive only the promotion operation scopes they need,
  while `promotion-service` keeps only `internal:promotion:admin` by default. Runtime authorization
  still also requires an active incentive application client binding.

Sprint 2V runtime smoke gate update:

- The SA/QA review selected a reusable promotion runtime smoke as the next release gate before
  expanding loyalty scope. The gate is intentionally black-box over the deployed cluster, not a unit
  test.
- Added `backend/scripts/promotion-runtime-smoke.mjs` with `local` and `staging` modes. Local mode
  seeds a disposable tenant/application/check-out binding/campaign fixture through Postgres; staging
  mode requires pre-provisioned fixture data and read-only database access for outbox assertions.
- The smoke verifies the service boundary and runtime contract end to end: browser-facing gateway
  runtime routes stay closed, STS rejects a wrong client secret, STS rejects promotion-service runtime
  operation scopes, checkout-service mints only explicit promotion runtime scopes, evaluate selects
  the fresh smoke campaign, reserve/cancel/commit/reverse are idempotent by `Idempotency-Key`,
  committed and reversed redemption outbox events are published exactly once, and outbox relay DLQ has
  no open `promotion` rows.
- Runtime reversal is deliberately service-callable for trusted source clients such as checkout/order
  services when they hold `internal:promotion:reverse` and an application binding that includes
  `reverse`; user/operator reversal requires incentive admin access plus maker-checker approval.
- CI validates the script syntax in lightweight artifact checks and runs it in the manual local
  cluster smoke job after the product hardening gateway smoke.
- Staging promotion smoke is intentionally fixture-pinned: it requires
  `PROMOTION_SMOKE_EXPECTED_CAMPAIGN_CODE`, and any run that skips database outbox/DLQ checks is a
  partial diagnostic smoke rather than release evidence.

Sprint 2W pilot verification gate update:

- Added a dedicated `run_promotion_runtime_smoke` workflow-dispatch gate for staging/pre-production.
  It runs `promotion-runtime-smoke.mjs` in `staging` mode, requires fixture-pinned campaign code and
  promotion/outbox database URLs, forces `PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=false`, installs
  `psql`, and uploads the smoke log artifact as release evidence.
- Added `promotion-observability-smoke.mjs` to the same staging gate. It verifies Prometheus scrape
  targets for gateway, token-converter, promotion-service, and outbox-relay, asserts promotion
  runtime metrics exist after the run, and fails when critical promotion/outbox/token-converter
  alerts are firing.
- Expanded the runtime smoke negative matrix with a non-mutating scope check: a `checkout-service`
  token that only has `internal:promotion:evaluate` must be rejected when calling reserve.
- The full pilot gate is still broader than Sprint 2W: load/soak testing, hot-quota concurrency,
  synthetic alert firing, and run-scoped DLQ/reconciliation evidence remain follow-up work before
  loyalty implementation.

Sprint 2X negative smoke matrix update:

- The PO/BA, SA/security, QA/SRE, and backend review selected a P0 negative matrix before building
  loyalty mechanics. The intent is to prove that promotion can be exposed as a generic service-only
  runtime without letting checkout/order integrations forge facts, reuse idempotency keys across
  payloads, or move terminal reservations into invalid money states.
- Expanded `promotion-runtime-smoke.mjs` from the happy path plus basic scope denial into a
  deployment gate for fail-closed runtime access:
  missing and malformed internal JWTs are rejected, every runtime operation rejects a token missing
  its matching `internal:promotion:<operation>` scope, and unknown tenant/application traffic is
  rejected before any runtime mutation.
- Mutating runtime calls now prove idempotency invariants beyond replay: reserve, commit, cancel, and
  reverse require an idempotency key, and reusing a successful key with a different payload returns
  `409` without changing the already-recorded result.
- Terminal-state behavior is covered by a production-relevant business negative: commit on a
  cancelled reservation returns `committed=false`, `RESERVATION_CANCELLED`, no redemption id, and a
  database assertion proves no redemption row was created for that cancelled reservation.
- Promotion observability smoke now requires fresh evidence from the same release run rather than
  accepting stale counters: runtime operations must increase within the recent window, promotion
  outbox unpublished count and oldest-age gauges must stay within configured smoke thresholds, and
  open promotion relay DLQ rows must remain zero.
- Still deferred from the full production gate at this point in the sprint history: hot-quota race
  tests, load/soak, synthetic alert firing, and run-scoped reconciliation evidence. Coupon abuse
  coverage is closed later by the Sprint 2Z release-gate smoke.

Sprint 2Y client-binding fixture gate update:

- The PO/BA, SA/security, QA/SRE, and backend review closed the next P0 gap in the production pilot
  gate: application/client-binding denials are now proven with real fixture applications, not only by
  unknown-app `404` or token-scope failures.
- Local smoke seeds five disposable negative applications alongside the positive checkout fixture:
  an active unbound app, a suspended app with active checkout binding, an active app with suspended
  checkout binding, an active app with checkout binding `allowed_operations=[]`, and an active app
  with checkout binding exactly `["evaluate"]`.
- Staging smoke remains non-destructive. It requires explicit pre-provisioned fixture IDs through
  `PROMOTION_SMOKE_UNBOUND_APPLICATION_ID`, `PROMOTION_SMOKE_SUSPENDED_APPLICATION_ID`,
  `PROMOTION_SMOKE_SUSPENDED_BINDING_APPLICATION_ID`,
  `PROMOTION_SMOKE_EMPTY_BINDING_APPLICATION_ID`, and
  `PROMOTION_SMOKE_EVALUATE_ONLY_APPLICATION_ID`. Derived local defaults are not accepted in
  staging.
- Before sending HTTP negative probes, the smoke runs a read-only database preflight: positive app is
  active, checkout binding includes all runtime operations, expected campaign has a published active
  snapshot, negative app IDs are distinct and not the positive app, each negative fixture has the
  required status/binding/operation shape, and no negative fixture has a published campaign snapshot.
- Runtime probes then use a valid full-scope `checkout-service` token. The expected result is `403`
  with the specific denial detail for unbound, suspended-app, suspended-binding, empty-binding, and
  evaluate-only reserve attempts, plus a DB assertion that each denial created zero reservations for
  the run-scoped profile/external reference.
- Still deferred: full negative binding coverage for commit/cancel/reverse fixture records,
  hot-quota concurrency, load/soak, and synthetic alert firing. Run-scoped reconciliation evidence is
  closed later by the next release-gate smoke.

Sprint 2Z coupon abuse fixture gate update:

- The PO/BA, SA/security, QA/SRE, and backend review closed the next P0 promotion-platform gap:
  coupon abuse is now a release-gate smoke, not only unit coverage or dashboard diagnostics.
- Local smoke seeds a dedicated coupon-required application and campaign so invalid coupon attempts
  cannot accidentally fall back to the normal non-coupon smoke campaign. Staging remains
  non-destructive and requires explicit `PROMOTION_SMOKE_COUPON_*` fixture values.
- Coupon storage preflight proves the fixture uses current HMAC storage, not raw/legacy rows:
  `code` and `code_mask` are masks, `normalized_code` uses the current
  `hmac-sha256:<keyId>:<hex>` prefix, and the invalid coupon code is not present in the campaign.
- The runtime smoke covers missing coupon, invalid coupon, inactive coupon, future/not-started
  coupon, expired coupon, holder mismatch, exhausted coupon, and a valid control coupon. Negative
  evaluate calls return generic business declines without campaign/coupon enumeration except
  `QUOTA_EXHAUSTED`, raw coupon codes and fingerprints are absent from response text, and DB checks
  prove no reservation rows were created. A reserve invalid-coupon sentinel also returns
  `reserved=false` with no reservation row.
- Promotion observability smoke now requires recent bounded coupon-match metrics for
  `not_supplied`, `not_found`, `inactive`, `not_started`, `expired`, `holder_mismatch`, and
  `matched` with `coupon_required=true`, in addition to runtime/outbox/DLQ health.
- Still deferred: coupon brute-force rate limiting, legacy raw/SHA fallback smoke, coupon import
  abuse paths, hot quota/concurrency, load/soak, and synthetic alert firing. Run-scoped
  reconciliation evidence is closed by the follow-up release-gate sprint.

Sprint 2AA run-scoped reconciliation evidence gate update:

- The PO/BA, QA/SRE, and backend review selected reconciliation release-safety as the next P0 gate,
  with the SA/security coupon brute-force/rate-limit proposal retained as the following security
  sprint. The intent is to prove the disposable smoke run did not only call successful APIs, but also
  left a balanced money trail across reservation, ledger, redemption, outbox, and quota policy facts.
- Runtime smoke now checks the cancelled-reservation branch: exactly one `RESERVE` ledger row,
  exactly one `CANCEL` ledger row, no redemption, no commit/reverse ledger rows, non-empty effects,
  reservation status `CANCELLED`, no coupon secret leakage in the evidence JSON, and the derived
  `RELEASE_RESERVED_QUOTA` reconciliation policy.
- Runtime smoke also checks the commit/reverse branch after the outbox relay publishes both events:
  exactly one `RESERVE`, one `COMMIT`, and one `REVERSE` ledger row; no cancel row; redemption status
  `REVERSED`; committed/reversed outbox events published with the smoke correlation id and
  `checkout-service` source client; non-empty effects; no coupon secret leakage; and the derived
  `NO_RELEASE_ON_COMMITTED_REVERSAL` policy.
- This remains a smoke gate, not a financial reporting subsystem. It deliberately avoids changing
  admin access semantics for `internal:promotion:admin` service tokens and uses read-only database
  evidence for the release run rather than widening operator permissions.
- Still deferred: coupon brute-force/rate limiting, legacy fallback cutover smoke, coupon import
  abuse paths, hot quota/concurrency, load/soak, synthetic alert firing, and UI dashboards for
  finance/ops reconciliation.

Sprint 2AB coupon brute-force guard update:

- The PO/BA, SA/security, QA/SRE, and backend review selected coupon brute-force protection as the
  next security gate before coupon import scale-up or loyalty work. The platform already declined
  invalid coupons safely; this sprint adds velocity protection for repeated suspicious coupon
  attempts.
- Added `CouponAbuseGuard` on the runtime `evaluate` and `reserve` paths for coupon-required
  campaigns. It triggers only for suspicious non-successful coupon outcomes:
  `not_supplied`, `not_found`, `inactive`, `not_started`, `expired`, and `holder_mismatch`. Exhausted
  and valid coupons remain business/quota outcomes rather than abuse signals.
- The guard stores no raw coupon/profile/client identifiers. Redis keys are HMAC-SHA256 values keyed
  with `PROMOTION_COUPON_ABUSE_GUARD_KEY_ID` and `PROMOTION_COUPON_ABUSE_GUARD_PEPPER`, partitioned
  by profile, source client, application, coupon, and missing-identity scopes.
- Modes are explicit: `disabled` bypasses the guard, `shadow` records limited decisions but allows
  the request, and `enforced` returns a generic `RATE_LIMITED` decline before reservation, ledger,
  idempotency success, outbox, or redemption side effects.
- Local Docker defaults use `enforced` with low profile/coupon capacities so the release smoke proves
  real blocking. Production compose defaults to `shadow` with required key/pepper configuration so
  operators can observe thresholds before moving to enforced.
- Store failure behavior is configurable through `PROMOTION_COUPON_ABUSE_GUARD_FAIL_POLICY`:
  `allow_with_alert` is the safer default for availability, while `deny_coupon_required` can be used
  in stricter environments.
- Observability is bounded-cardinality through `promotion.coupon.abuse_guard` with tags for
  operation, mode, scope, and result. It intentionally omits coupon code, coupon id, fingerprint,
  profile id, external reference, tenant, application, and campaign id.
- Runtime smoke now bursts invalid evaluate and reserve attempts against the dedicated
  coupon-required fixture until the guard returns `RATE_LIMITED`, asserts the response is generic,
  asserts coupon secrets are absent, and proves no reservation row was created.
- Promotion observability smoke now requires recent evidence for
  `promotion_coupon_abuse_guard_total{result="limited"}` after the runtime smoke. It prefers
  `increase()`, and also handles a fresh-deploy first-scrape case where Prometheus only has a
  recent `max_over_time()` sample after the guard event.

P2 fraud scoring preview update:

- Added `POST /internal/incentives/admin/fraud-score:preview` for operator/support review of a
  checkout or learner incentive context. Gateway alias is
  `/api/admin/v1/incentives/admin/fraud-score:preview`.
- The score is explainable and non-mutating: it returns a 0-100 score, severity,
  `recommendedAction` (`ALLOW`, `CHALLENGE`, `REVIEW`, `BLOCK`), reason signals, bounded evidence,
  and `ledgerImpact=false`. It does not reserve quota, commit ledger, publish outbox events, or
  change runtime `evaluate`/`reserve` enforcement.
- Signals combine safe context features such as coupon selector count, missing source client, and
  transaction value with recent reservation/redemption/reversal/coupon-id velocity from the
  promotion ledger. Raw coupon codes are not written to audit payloads.
- Each preview writes `fraud_score.previewed` to incentive audit with policy version, score,
  recommended action, lookback window, and signal codes so support decisions can be traced.
- Coupon brute-force protection remains owned by `CouponAbuseGuard`; fraud scoring is the operator
  explainability layer and can be promoted to enforcement only after threshold governance and false
  positive review are approved.

P2 A/B incentive testing preview update:

- Added `POST /internal/incentives/admin/experiments:preview` for deterministic traffic-allocation
  preview before publish. Gateway alias is `/api/admin/v1/incentives/admin/experiments:preview`.
- The request takes a normal incentive context plus an `experimentKey`, assignment unit
  (`PROFILE`, `EXTERNAL_REFERENCE` or `ATTRIBUTE`) and weighted variants in basis points. If
  configured weights total less than 10000 bps the remaining traffic is represented as an implicit
  `__HOLDOUT__` variant, which lets operators dry-run gradual rollout and holdout design.
- The response is non-mutating: `ledgerImpact=false`, bucket, selected variant, selected holdout
  state, recommended action, reason codes and allocation bands. It does not alter campaign
  evaluation, reservations, quota counters, ledger entries, coupon usage or outbox events.
- Each preview writes `experiment.previewed` to incentive audit with policy version, bucket,
  selected variant and assignment-key hash. Raw profile ids, external references and coupon codes
  are not written to the audit payload.
- Runtime enforcement is intentionally deferred until experiment id/variant attribution is added to
  reservation, redemption, ledger and reconciliation rows. Until then this endpoint is an operator
  simulation and governance tool, not a production assignment source of truth.

Sprint 2AC hot quota/concurrency release gate update:

- The PO/BA, SA/SRE, QA/SRE, and backend lead review selected quota correctness under concurrent
  reserve as the next P0 gate. The release criterion is deterministic bounded quota, not optimistic
  UX behavior.
- Quota consume now uses a Postgres atomic conditional update after `insert if absent`:
  increment `used_count` only when the target counter exists and `used_count < limit_count`.
  The service no longer relies on a read-modify-write entity save in the hot consume path.
- Postgres remains the correctness boundary. Redis may support abuse guard/rate limiting or future
  read caching, but it must not decide whether quota has been consumed.
- Testcontainers JPA smoke covers parallel reserve against campaign quota, campaign per-profile cap,
  coupon quota, and coupon per-profile cap. Each test expects exactly one successful reservation and
  all other attempts to return `QUOTA_EXHAUSTED`.
- Runtime smoke seeds or verifies a dedicated non-coupon `max_redemptions=1` hot quota fixture,
  sends parallel reserve attempts with distinct idempotency keys, profiles, and external references,
  and verifies DB evidence: one reservation, one `RESERVE` ledger row, one bounded quota counter, and
  zero counter invariant violations. It then cancels the winning reservation and verifies the quota
  counter returns to `used_count=0`, keeping the staging fixture reusable across release-candidate
  runs.
- Local smoke deactivates old active hot-quota snapshots in the disposable fixture app so the smoke
  is repeatable on the same Docker database. Staging remains non-destructive and must pre-provision
  the exact fixture through `PROMOTION_SMOKE_QUOTA_APPLICATION_ID` and
  `PROMOTION_SMOKE_QUOTA_CAMPAIGN_CODE`.
- Observability smoke now requires recent quota consumed/exhausted/released and reserve-fallback
  metrics, alongside runtime, coupon-match, coupon-abuse, outbox, DLQ, and alert evidence.

Sprint 2AD coupon cutover and import-ops evidence update:

- The PO/BA, SA/security, QA/SRE, and backend lead review selected the first Coupon Inventory
  Cutover & Import Abuse Gate slice. The implementation keeps the import workflow in
  `promotion-service` and focuses on release evidence and safe operator feedback before adding
  large-scale async import workers.
- Added a masked dry-run issue export endpoint:
  `GET /internal/incentives/coupons/import-dry-runs/{dryRunId}/issue-export`.
- The export is CSV content embedded in the DTO for the existing internal admin API. It includes
  only `rowNumber`, `codeMask`, `rowStatus`, and pipe-delimited issue codes. It intentionally omits
  raw coupon code, normalized HMAC/SHA values, coupon id, holder profile id, external reference,
  source client id, idempotency key, and row-level free-form issue payload.
- Downloading the issue export requires the same review access as dry-run query screens and writes
  an immutable audit event with actor, correlation id, campaign, row status, row count, and filename.
  The audit payload deliberately stores metadata only, not the CSV content or row masks.
- Promotion observability smoke now proves coupon storage cutover evidence after runtime smoke:
  `current_hmac` lookup paths must have recent evidence, while forbidden legacy paths such as
  `legacy_sha` and `legacy_raw` must not increase in the same smoke window. The required and
  forbidden storage paths are configurable for staged rollout.
- CI workflow dispatch forwards those lookup observability variables so staging can tighten or widen
  the cutover gate without editing the script.

Sprint 2AE coupon inventory readiness gate update:

- The PO/BA follow-up review identified that legacy lookup no-hit metrics alone are not enough for
  cutover: legacy inventory can exist without being exercised during the smoke window.
- Promotion runtime smoke now checks active coupon storage inventory for the dedicated coupon fixture
  campaign and fixture application before runtime coupon scenarios run.
- The inventory gate uses the same storage classes as the service inventory API:
  `current_hmac`, `previous_hmac`, `legacy_sha`, `legacy_raw`, and `malformed`.
- The smoke fails unless active inventory has at least one `current_hmac` coupon and zero
  `legacy_sha`, `legacy_raw`, and `malformed` coupons in the checked scope. `previous_hmac` is
  reported but does not block legacy fallback cutover because it is key-rotation debt rather than
  raw/SHA migration debt.
- The release artifact summary now prints `couponInventoryReady=campaign,application` when both
  readiness checks run successfully.
- The gate is enabled by default through `PROMOTION_SMOKE_REQUIRE_COUPON_INVENTORY_READY=true`; a
  disabled run is only partial evidence and must not be treated as production cutover-ready.
- Added a fail-closed coupon write guard for fallback-off deployments. When
  `PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED=false`, new single-coupon writes, batch coupon
  generation, and coupon import commit re-check active campaign inventory and reject writes if
  `legacy_sha`, `legacy_raw`, or `malformed` rows remain. This prevents fallback-off duplicate
  detection from silently ignoring old storage formats during the migration window.

Sprint 2AF issue-export size guard update:

- Coupon import issue export now performs a count query before loading export rows. If the selected
  `rowStatus` would return more than `PROMOTION_COUPON_IMPORT_ISSUE_EXPORT_MAX_ROWS` rows
  (`10000` by default), the request fails fast with `EXPORT_TOO_LARGE` and does not build CSV or
  write a download audit event. The production profile validator also requires any override to be a
  positive integer.
- This keeps the current CSV-in-DTO admin contract safe for release gates while preserving the same
  redacted export shape. Large operator downloads remain deferred until a paged or streaming export
  contract is designed.
- Promotion runtime smoke now has an opt-in admin gateway lane
  (`PROMOTION_SMOKE_COUPON_IMPORT_GATEWAY_ENABLED=true`) that uses a real admin bearer token and the
  `/api/admin/v1/incentives/**` route to prove storage inventory, multipart import dry-run,
  idempotency replay, history/detail lookup, and masked issue export through the gateway. This is
  staging evidence only until CI/staging provides a short-lived admin OAuth2 token.

Sprint 2AG admin operation rate guard update:

- The PO/BA, SA/security, QA/SRE, and backend lead review selected admin/import abuse protection as
  the next small production slice. The goal is to protect expensive operator flows before expanding
  into larger async import workers or loyalty modules.
- Added `AdminOperationRateGuard` for coupon import dry-run, masked issue export, approval request,
  import commit, and coupon generation. The guard runs after authorization and active-application
  checks, but before idempotency lookup, heavy CSV parsing, row count/fetch, approval mutation,
  coupon writes, operation writes, or audit writes.
- Redis keys are HMAC-SHA256 values with a separate
  `PROMOTION_ADMIN_OPERATION_RATE_GUARD_KEY_ID` and
  `PROMOTION_ADMIN_OPERATION_RATE_GUARD_PEPPER`. Raw actor ids, source clients, content hashes,
  tenants, applications, campaigns, coupon codes, and CSV contents are never stored in guard keys or
  metric tags.
- Modes match the runtime coupon abuse guard: `disabled` bypasses, `shadow` records limited
  decisions while allowing the request, and `enforced` fails fast with a generic
  `429 RATE_LIMITED`. Store failures obey `PROMOTION_ADMIN_OPERATION_RATE_GUARD_FAIL_POLICY`
  (`allow_with_alert` or `deny`).
- Local Docker defaults to `enforced` so developer clusters catch runaway imports early. Production
  compose defaults to `shadow` but requires a non-local key id and pepper; the production profile
  validator rejects `disabled` mode, weak peppers, invalid key ids, and non-positive capacities.
- Observability is bounded-cardinality through `promotion.admin_operation.rate_guard` with tags for
  operation, mode, scope, and result only.

Sprint 2AH admin guard closure and alerting update:

- The follow-up PO/BA, SA/security, QA/SRE, and backend review closed the remaining low-cost admin
  guard gaps instead of opening a larger import-worker sprint.
- Admin preview now runs the same admin operation guard after admin/active-application checks and
  before campaign decisioning or audit writes. Its content bucket uses the already minimized
  preview context hash, not raw profile id, external reference, coupon code, or request attributes.
- Coupon import approval approve/reject now share the same `coupon_import_approval_decision` guard
  bucket after review access and before different-operator/status checks, batch revalidation,
  approval mutation, or audit writes.
- Added deterministic tests proving preview, approve, and reject fail fast with `429 RATE_LIMITED`
  and do not reach decisioning, batch validation, mutation, or audit when the guard denies.
- Added Prometheus alerts for admin operation rate limiting and guard store failures. Observability
  smoke can assert `promotion_admin_operation_rate_guard_total` evidence through
  `PROMOTION_OBSERVABILITY_REQUIRED_ADMIN_OPERATION_RATE_GUARD_RESULTS` and
  `PROMOTION_OBSERVABILITY_REQUIRED_ADMIN_OPERATION_RATE_GUARD_OPERATIONS` once staging runs an
  admin gateway lane that intentionally exercises the guard.

Sprint 2AI coupon import commit replay hardening update:

- The follow-up SA/QA/BE review selected a narrow commit replay failure mode rather than a broad
  import worker rewrite. The core transaction already serializes same-approval commits through
  pessimistic locks on approval and dry-run batches, while the operation table has unique dry-run and
  approval constraints.
- Hardened the retry path where the dry-run batch has already been committed and the durable
  `incentive_coupon_import_operations` row exists, but the idempotency key did not reach
  `SUCCEEDED` yet. This can happen around process failure between durable business writes and
  idempotency response completion.
- In that state, a matching retry now reads the committed import operation by dry-run id, verifies
  the approval id, request hash, and idempotency key hash, returns the original stored response as an
  idempotency replay, and completes the still-`IN_PROGRESS` idempotency record. A mismatched request
  or different idempotency key still fails closed as already committed.
- Added deterministic unit coverage proving no coupon write occurs during this durable replay path
  and the idempotency record is healed from the stored operation response.

Sprint 2AJ coupon import commit JPA concurrency proof:

- Added Postgres/Testcontainers smoke coverage for the coupon import commit transaction path in
  `PromotionServiceJpaSmokeTest`. The test drives the real dry-run, approval, approval decision, and
  commit services instead of mocks.
- Same approval/dry-run plus the same commit idempotency key now has a database-level regression
  proof: two concurrent commit attempts both return the same import id, exactly one response is an
  idempotency replay, and the database contains one import operation, one coupon write set, one
  executed approval, and one committed batch.
- The crash-window replay path is also exercised against Postgres by resetting the durable
  commit idempotency row to `IN_PROGRESS` after the import operation exists. A matching retry must
  replay the original import response and heal the idempotency key back to `SUCCEEDED`.
- A true double-submit with different commit idempotency keys is fail-closed: one concurrent request
  succeeds, the other receives an already-committed conflict, and operation/coupon/batch/approval
  counts remain single-write.

Sprint 2AK coupon import operation export:

- Added a single-operation admin export endpoint:
  `GET /admin/v1/incentives/coupons/import-operations/{importId}/export` through the gateway and
  `/internal/incentives/coupons/import-operations/{importId}/export` internally.
- The response mirrors the existing JSON-wrapped CSV export pattern: filename, content type, content,
  generated timestamp, and operation identifiers. It exports an operation receipt, not row-level coupon
  detail.
- Exported CSV includes safe receipt fields only: import, approval, dry-run, tenant/application,
  campaign, status, requested/imported rows, result hash, reason, change ticket, actor/source client,
  correlation, and commit time. It does not export raw coupon codes, uploaded CSV content, normalized
  codes, request/content/idempotency hashes, response JSON, metadata, fingerprints, or profile PII.
- The endpoint requires review access, runs the `coupon_import_operation_export` admin operation
  guard, and writes `coupon.import_operation_downloaded` audit metadata after a successful export.
- Web admin now adds a compact per-row CSV action in the Import operations table. The UI creates a
  browser download from the returned content and does not introduce a separate workflow.

Sprint 2AL coupon cutover smoke evidence:

- Extended `promotion-runtime-smoke.mjs` local mode with a trusted internal-admin call to
  `/internal/incentives/coupons/storage-inventory` for the seeded coupon campaign. The smoke now proves
  the admin inventory route itself, not only direct SQL inventory, before the runtime path proceeds.
- The new smoke check first verifies the internal inventory route rejects unauthenticated direct calls,
  then sends a locally signed internal user JWT with matching `X-User-*` headers to mirror the gateway
  trust boundary used by admin endpoints.
- The route evidence asserts aggregate-only cutover readiness: tenant/application/campaign match,
  `activeOnly=true`, `fallbackDisableReady=true`, zero legacy/malformed active coupons, at least one
  `current_hmac` row, and no raw coupon code, normalized code, fingerprint, or `hmac-sha256` leakage in
  the response body.
- Added a focused import-commit fail-closed test for the fallback-disabled cutover state. If active
  inventory reports a new `legacy_raw`, `legacy_sha`, or malformed row after dry-run approval, commit
  stops before re-evaluation, idempotency acquisition, coupon writes, operation writes, approval
  execution, or audit writes.

Sprint 2AM coupon cutover evidence artifact:

- Extended `promotion-observability-smoke.mjs` with an opt-in cutover evidence artifact mode. When
  `PROMOTION_CUTOVER_EVIDENCE_ENABLED=true`, the smoke queries gateway admin inventory for explicit
  `name|tenantId|applicationId|campaignId?|activeOnly?|requireNonEmpty?` scopes and writes
  `promotion_coupon_hmac_cutover_evidence` JSON.
- The artifact records schema version, environment, run/Git metadata when available, exact scopes,
  aggregate inventory counts, current-HMAC lookup evidence, forbidden legacy lookup increase over
  `PROMOTION_OBSERVABILITY_CUTOVER_WINDOW`, redaction evidence, failed observability checks, and a
  pass/fail decision.
- The staging workflow now enables the artifact by default for manual promotion runtime smoke runs,
  requires `PROMOTION_CUTOVER_EVIDENCE_SCOPES` and an admin token when evidence is enabled, and uploads
  the JSON beside the runtime/observability smoke logs.
- Added an enabled-path mock verification for the observability script proving the gateway inventory,
  Prometheus evidence, JSON write, and `decision.status=pass` path.

Sprint 2AN issue-export audit DB evidence:

- Extended the gateway coupon import smoke in `promotion-runtime-smoke.mjs` with a DB cross-check for
  masked issue export downloads. After
  `GET /admin/v1/incentives/coupons/import-dry-runs/{dryRunId}/issue-export?rowStatus=INVALID`
  succeeds, the smoke now verifies the corresponding `incentive_audit_events` row.
- The cross-check looks for `coupon.import_issue_export_downloaded` with
  `aggregate_type=coupon-import-dry-run`, the smoke dry-run id, tenant/application, the exact
  issue-export correlation id, nonblank actor and source-client traceability, and payload metadata
  matching `dryRunId`, campaign id, `rowStatus=INVALID`, exported row count, and filename.
- The audit payload is also scanned for import secrets and implementation internals: raw coupon
  values, normalized code, HMAC/fingerprint text, idempotency key, CSV content, and content hash must
  not appear.
- This remains tied to the opt-in admin gateway smoke lane because local default runs do not have a
  real OAuth admin token.

Sprint 2AO default admin guard metric evidence:

- `promotion-observability-smoke.mjs` now turns on admin operation rate-guard Prometheus assertions
  automatically when `PROMOTION_SMOKE_COUPON_IMPORT_GATEWAY_ENABLED=true`.
- The default evidence is intentionally narrow and stable: require recent
  `promotion_admin_operation_rate_guard_total{operation="coupon_import_dry_run",result="allowed"}`
  evidence. The smoke still allows explicit env overrides for additional results or operations.
- The manual promotion staging workflow now defaults the coupon import gateway lane and admin guard
  evidence requirement to `true`, requires an admin token and coupon campaign id for that lane, and
  fails configuration validation if guard evidence is required while the gateway lane is disabled.
- The assertion does not require `limited`, exact counts, tenant/application tags, or a specific
  guard bucket scope because the metric is intentionally bounded-cardinality and the staging smoke is
  expected to stay under the rate-limit threshold.

Sprint 2AP hot quota soak artifact:

- `promotion-runtime-smoke.mjs` now supports an opt-in hot quota soak gate by raising
  `PROMOTION_SMOKE_HOT_QUOTA_SOAK_WAVES` (or the compatible `PROMOTION_SMOKE_HOT_QUOTA_WAVES` /
  `PROMOTION_SMOKE_HOT_QUOTA_SOAK_ROUNDS`) above the default single deterministic probe.
- Every wave uses the existing dedicated `max_redemptions=1` hot quota fixture, keeps unique
  profile/external references per attempt, requires exactly one winner and `QUOTA_EXHAUSTED` for the
  rest, verifies bounded DB evidence, cancels the winner, and verifies quota release before the next
  wave.
- When `PROMOTION_SMOKE_HOT_QUOTA_SOAK_ARTIFACT_FILE` (or
  `PROMOTION_SMOKE_HOT_QUOTA_ARTIFACT`) is set, the smoke writes
  `promotion_hot_quota_soak_evidence` JSON with run id, tenant/application/campaign, configured
  waves/concurrency, per-wave winner/exhaustion/release evidence, aggregate failures, and duration
  percentiles. The manual staging workflow retains this file under
  `promotion-runtime-smoke-artifacts` and defaults waves to `1` so normal release smokes stay light.

Still deferred after Sprint 2AP:

- Executing and retaining the cutover artifact against the agreed real staging/production active
  scopes and observation window.
- Executing and retaining a multi-wave hot quota soak artifact against the agreed staging fixture
  under pilot load settings.
- Synthetic alert firing and alert-routing drills.
- UI dashboards for finance/ops reconciliation.

Scope intentionally deferred:

- Loyalty service/module implementation.
- Runtime OpenAPI generation or generated controllers.
- Reconciliation cursor pagination and summary aggregation.
- Masked import error report download beyond the existing dry-run issue export.

Known Sprint 2R follow-up:

- Add CI/lint automation for OpenAPI, AsyncAPI, JSON Schema, and example validation if the current
  JUnit contract checks are not enough for release governance.
- Add component/API tests for the web-admin coupon import and reconciliation flows.
- Promote simulation-only stacking analysis to runtime multi-campaign reservation/commit only after
  the reservation schema, quota consumption, discount netting, and production smoke/load tests cover
  multi-campaign benefit application.

Sprint 2AZ coupon import machine-readable error contract:

- PO/BA/SA review chose a narrow production vertical slice instead of a whole-platform migration:
  add the reusable primitive in `common-library`, then rollout stable `errorCode` values for coupon
  import, coupon import approval, and promotion admin rate-limit paths first.
- `ErrorDto` now has optional `errorCode` while preserving the existing constructors and
  `statusCode/title/detail/fieldErrors` fields. Legacy errors omit `errorCode` from JSON; coded
  exceptions include it through the shared exception handler.
- Promotion-service now emits stable top-level codes for coupon import RBAC, read/manage/review
  denial, operator-only approval actions, self-approval/self-commit blocks, approval state conflicts,
  dry-run state conflicts, result-hash/payload drift, duplicate coupon codes, idempotency conflicts,
  and admin operation rate limiting.
- Admin web maps `response.data.errorCode` before falling back to legacy status/detail matching, so
  mixed backend/frontend rollout remains safe while new deployments stop parsing human-readable
  messages for normal coupon import operations.
- Verification covered the common error handler, rate guard, incentive access, promotion admin
  operations, coupon import dry-run/approval/commit/query services, and the admin incentives mapper,
  lint, and production build.

Sprint 2BA coupon import API error contract evidence:

- Added controller-level MockMvc contract coverage for the shared `ApiExceptionHandler` attached to
  `PromotionController`. This proves the actual HTTP boundary serializes coded exceptions into the
  stable `ErrorDto` shape, not only service-level unit tests.
- P1 coupon import paths now assert JSON `Content-Type`, HTTP status, `statusCode`, `title`,
  `detail`, `errorCode`, and empty `fieldErrors` for dry-run rate limiting, approval request result
  hash mismatch, approval decision forbidden, approval decision not-pending, issue-export read
  forbidden, and commit rate limiting.
- The suite intentionally keeps filter-level 401 behavior outside this advice contract because
  `TrustedGatewayHeaderFilter` writes those responses before controller dispatch.
- Verification covered the controller contract suite, the common error handler, promotion service
  coupon-import/rate-limit tests, and the admin incentives mapper/typecheck.

Sprint 2BB retention machine-readable gate contract:

- Extended the same `ErrorDto.errorCode` contract to destructive retention approval and execution
  paths. Backend now emits stable retention codes for platform/admin/reviewer gates, restore-drill
  validation, approval lifecycle conflicts, stale dry-run/result-hash drift, self-approval,
  self-execution, consumed approvals, and execution idempotency states.
- Retention approval/execution services keep the existing JPA/domain flow and only add coded
  exceptions at the production gate boundaries. This avoids text parsing without refactoring the
  transaction model or adding a parallel error framework.
- Web admin `Incentives > Retention` now maps retention `errorCode` values into explicit gate
  reasons for dry-run, restore drill, approval lookup/request, reviewer decision, and destructive
  execution failures. Fallback HTTP/status-detail mapping remains for mixed deployments.
- Verification covered retention approval/execution service tests, promotion-service regression,
  admin incentives mapper tests, TypeScript typecheck, and production web build.

Sprint 2BC loyalty bounded-context bootstrap:

- Added `loyalty-service` as a separate deployable module instead of mixing loyalty balances into
  `promotion-service`. The first slice owns programs, accounts, immutable points entries,
  idempotency keys, audit events, and local outbox rows.
- Implemented internal APIs for program/account creation, account lookup, earn, burn, reverse, and
  ledger query. Earn may auto-open an account; burn and reversal enforce no-overdraw unless the
  program explicitly allows negative balance.
- Added service-JWT scope gates for `internal:loyalty:read`, `earn`, `burn`, `reverse`, `adjust`,
  `expire`, and `admin`. The legacy `X-Service-Token` path is not expanded for loyalty.
- Added Docker/local/prod integration for the new service and `cf_loyalty` database.
- Added contract docs and event-contract Java type for `loyalty.points.earned`,
  `loyalty.points.burned`, and `loyalty.points.reversed`.
- Added `outbox-relay` polling configuration for the loyalty database so loyalty ledger events are
  published through the same at-least-once relay path as the other service outboxes.
- Added account-level pessimistic locking for points mutations and Postgres concurrency smoke tests
  proving concurrent burn/reverse operations cannot overdraw or duplicate compensating entries.
- Added Prometheus scrape coverage for `loyalty-service` and a critical DLQ alert for loyalty relay
  dead letters.

Sprint 2BD loyalty observability and typed events:

- Replaced hand-built loyalty outbox maps with the typed `LoyaltyPointsChangedEvent` contract so
  `loyalty.points.earned`, `loyalty.points.burned`, and `loyalty.points.reversed` payloads share the
  same Java contract and schema intent. Event metadata carries correlation id, actor id, reversal
  causation id, and point unit.
- Added bounded-cardinality loyalty metrics for earn/burn/reverse mutation result/latency,
  idempotency outcomes, source-reference replay/conflict, outbox enqueue counts, unpublished outbox
  backlog, and oldest unpublished loyalty event age.
- Added Prometheus alerts for loyalty mutation error rate, loyalty outbox lag/backlog, loyalty
  metrics refresh failures, and existing relay DLQ visibility.
- Verification covers loyalty payload contract assertions, metrics counters/gauges, and the existing
  Postgres concurrency smoke tests.

Sprint 2BE loyalty program/client binding gate:

- Added program-level client bindings for `loyalty-service`. Runtime service tokens are now checked
  in two layers: `TrustedGatewayHeaderFilter` validates the coarse `internal:loyalty:*` scope, then
  `LoyaltyAccessService` verifies the internal JWT `azp` has an ACTIVE binding on the exact
  `(tenantId, applicationId, programId, operation)`.
- Added `loyalty_program_client_bindings` with fail-closed `allowed_operations`. Program creation
  can seed bindings, while empty/missing/suspended bindings deny runtime mutation and read access.
- `earn`, `burn`, `reverse`, account read, and ledger read now enforce program binding. `reverse`
  authorizes against the original entry's persisted program, not request-provided scope.
- Service-token audit attribution now uses the internal JWT `azp`, so ledger events and audit rows
  identify the source client instead of storing null actor ids for service calls.
- `CurrentUserArgumentResolver` now mirrors the filter trust rule and only accepts Bearer internal
  tokens from `X-Internal-Authorization` or `Authorization`. A malformed internal header can no
  longer override the verified token that `TrustedGatewayHeaderFilter` accepted.
- Program and account `status` are enforced for runtime mutation/read flows. New mutations fail
  closed when a program/account is not ACTIVE, but a previously successful request still replays from
  idempotency even if the program/account is suspended later.
- Human admin audit attribution no longer prefers gateway `azp`; only service actors use `azp`.
  User-admin actions retain the human email/id from propagated identity headers.
- Verification covers deny-before-side-effect unit behavior, Postgres migration, concurrent mutation
  smoke, inactive program/account denial, idempotency replay after suspend, malformed internal header
  fallback, and an unbound service client denial even when the caller has a loyalty operation scope.

Sprint 2BF loyalty control-plane update:

- Added admin control-plane APIs for loyalty program search/detail/update/status, client-binding
  upsert, account search/status, audit query, and program/account timelines.
- Admin ledger lookup now uses control-plane semantics: it enforces admin access but does not block
  inspection after a program or account is suspended/closed.
- Program timeline includes lifecycle events from both the program aggregate and its client-binding
  aggregates, so operators can review the effective service access policy history in one place.
- Gateway config exposes `/api/admin/v1/loyalty/**` and rewrites it to `/internal/loyalty/**`.
- Web admin now has `Incentives > Loyalty` with Programs, Accounts & ledger, and Audit workspaces,
  including create/edit program, status transitions, client binding, account lookup, ledger drawer,
  and audit detail.
- Verification covered loyalty/gateway regression tests, web-admin typecheck/build, Docker rebuild
  of `loyalty-service` and `api-gateway`, and a local STS-backed smoke for program creation,
  binding upsert, runtime earn, suspend, admin ledger after suspend, timeline, and audit query.

Sprint 2BG loyalty ledger operations implementation update:

- Added manual point adjustment as an admin ledger operation. It accepts signed `pointsDelta`, source
  reference/change ticket, idempotency key, reason, correlation id, optional occurrence/expiry time,
  writes immutable `ADJUST` entries, prevents overdraw when negative balance is disabled, and emits
  `loyalty.points.adjusted`.
- Added expiry dry-run for gross expiry candidate inspection by tenant/application/program/as-of
  time. It returns samples, affected account count, expiring points, warnings, and result hash, but
  does not execute expiry until balance-bucket/remaining-lot semantics are implemented.
- Added read-only loyalty balance bucket projection by account. It allocates debits against positive
  point lots using FIFO by earliest expiry then occurrence time, exposes active/expired/unallocated
  points, and is intentionally marked as an operational projection rather than settlement ledger.
- Added loyalty reconciliation query for support/finance. It is tenant/application scoped and
  exposes ledger direction, point delta, source reference, reversal linkage, and outbox state without
  exposing request hashes or idempotency keys.
- Added materialized remaining-lot settlement state. New positive ledger entries create point lots,
  debit entries consume lots FIFO by earliest expiry, and expiry execution consumes remaining expired
  lots before writing immutable `EXPIRE` ledger entries and `loyalty.points.expired` outbox events.
- Added maker-checker approval workflow for high-risk manual point adjustments. Direct adjustment
  over the service threshold is blocked, approval requester cannot self-approve, and approve writes
  the ledger in the same transaction.
- Added promotion `LOYALTY_POINTS_EARN` action support. Promotion emits portable
  `POINTS_EARN_INTENT` effects with `programId`, point quantity, stable `effectId`, and idempotency
  material for loyalty; it still does not mutate loyalty state directly.
- Added loyalty consumer for promotion points intent. `loyalty-service` consumes
  `incentive.redemption.committed`, filters `POINTS_EARN_INTENT`, applies points through the existing
  idempotent `EARN` command, and requires the loyalty program to bind client `promotion-service` for
  operation `earn`.
- Added promotion reversal compensation. `loyalty-service` consumes
  `incentive.redemption.reversed`, locates the original promotion earn source reference, and writes
  a normal idempotent loyalty `REVERSE` entry through the existing reversal path.
- Hardened the promotion-to-loyalty consumer identity. The consumer no longer constructs unsigned
  internal tokens; it obtains an STS `client_credentials` token for the configured promotion actor
  client, caches it until near expiry, and loyalty verifies internal JWT signature/audience/issuer
  before trusting service claims.
- Added loyalty Kafka DLT backstop for promotion points intent consumers. Unexpected processing
  failures retry with bounded exponential backoff before moving the record to `<topic>.DLT`; malformed
  non-retryable intent data is skipped with warning logs.
- Added loyalty-specific RBAC seed roles and permissions for admin/reviewer/operator and published
  the REST/event contract updates in `backend/docs/contracts/loyalty`.
- Web admin `Incentives > Loyalty` now exposes manual adjustment from account ledger, balance bucket
  projection in the account drawer, approval queue, Expiry dry-run/execute tab, and a scoped
  Reconciliation workspace.
- Web learn now has a compact loyalty balance read endpoint and dashboard card. The endpoint resolves
  the learner profile from the authenticated user, returns active/expired/expiring-soon totals, and
  falls back to ledger balance with a warning when historical accounts have not been materialized
  into point lots.
- Added point-lot backfill dry-run/execute for production migration. Operators can scope by
  tenant/application/program/profile/account, preview missing lots and unallocated debits, then
  rebuild materialized lots from immutable ledger history before expiry execution.
- Added maker-checker gate for expiry execution. Operators submit the dry-run `resultHash` as an
  expiry approval, reviewers approve in the same operation approval queue, and execute requires the
  approved `approvalId` plus a still-matching materialized lot candidate hash.
  Deep tests and Docker smoke for this slice are intentionally deferred to the next test phase per
  current sprint instruction.
- Still deferred after 2BG: deep regression/Docker smoke for the new loyalty promotion integration
  slice.

Sprint 2BH proposed backlog from BA/PO/SA review:

- Implemented P0 approval evidence pack for loyalty operation approvals. The admin API exports
  expiry/adjustment approval metadata, requester/reviewer, dry-run hash, related audit events,
  ledger/reconciliation rows, outbox warnings and a safe evidence summary.
- Implemented P0 finance closeout export for loyalty points. The admin API returns scoped
  tenant/application/program report totals for earned/burned/reversed/adjusted/expired/net points,
  reconciliation rows, outbox status counts and warnings when the result is partial or publication is
  incomplete.
- Implemented P0 DLT operations view for promotion-to-loyalty consumers. `loyalty-service` consumes
  `incentive.redemption.committed.DLT` and `incentive.redemption.reversed.DLT` into
  `loyalty_inbound_dead_letters`, exposes platform-admin list/detail/replay/discard APIs, adds
  `loyalty.inbound_dead_letter` counters plus open/unresolved gauges, Prometheus alerts for
  unresolved DLT and replay publish failures, and web-admin adds a DLT Ops tab with filters,
  details, dry-run, replay, and discard actions.
- Implemented maker-checker for loyalty inbound DLT live replay/discard. Operators submit action,
  reason, evidence reference, payload hash, request hash, and `LOYALTY_INBOUND_DLT_DUAL_CONTROL_V1`;
  a different platform admin must approve before replay/discard can execute with `approvalId`.
- DLT runbook: inspect `GET /api/admin/v1/loyalty/dead-letters?status=OPEN`, open detail and compare
  `payloadHash`, exception class/message, source topic and Kafka position; fix the consumer/config or
  upstream payload issue first; dry-run replay; submit and approve
  `POST /api/admin/v1/loyalty/dead-letters/{id}/approvals`; then call
  `POST /api/admin/v1/loyalty/dead-letters/{id}:replay` with reason and approved `approvalId`. Use
  discard only when the event has been manually compensated or is confirmed non-retryable.
- P1 Loyalty reward catalog and redemption skeleton. Keep it separate from promotion decisioning:
  rewards consume loyalty points, promotion may award loyalty points, and both reconcile by source
  references rather than database joins.
- Implemented P1 Loyalty reward catalog/redemption skeleton. `loyalty-service` now owns
  `loyalty_rewards` and `loyalty_reward_redemptions`, exposes admin reward CRUD/status/search,
  learner catalog and learner redeem APIs, burns points through the existing immutable `BURN` ledger
  path, records reward redemption state with idempotency replay/conflict handling, and web-admin adds
  a Rewards tab for catalog and redemption operations. Redemption support can inspect detail and
  reverse the original burn through a linked `REVERSE` ledger entry; fulfillment remains a skeleton
  `MANUAL`/`AUTO_ISSUE` state machine until the dedicated fulfillment integration sprint.
- Implemented maker-checker for manual reward fulfillment override. Operators submit
  `REWARD_FULFILLMENT_OVERRIDE` approval with current/target fulfillment state, idempotency key,
  reason, correlation id and request hash; a different reviewer approves in the shared loyalty
  operation approval queue, then execution requires the approved `approvalId` and fails if the
  redemption fulfillment state drifted. Fulfillment changes do not mutate points; returning points
  remains a linked reward redemption reversal.
- P1 Learner wallet detail page. Show program balances, expiring buckets, recent ledger entries,
  source labels and certificate/reward eligibility hints without exposing internal hashes.
- Implemented first P1 Learner wallet detail. `loyalty-service` exposes
  `GET /internal/loyalty/me/wallet` as a BFF-style read model with totals, account summaries,
  materialized expiry buckets, recent ledger entries, reward eligibility and redemption history.
  API Gateway exposes `/api/v1/loyalty/wallet`, and web learn adds `/loyalty` with a dashboard entry
  point from the existing reward-points card.
- P1 Contract/regression suite and Docker smoke. Cover expiry approval replay/mismatch, STS consumer
  token failures, promotion reversal idempotency, point-lot backfill replay, reward redemption
  idempotency/stock/profile-limit handling, and admin UI typecheck.
- P1 DLT workflow hardening. Add operator action idempotency snapshots, owner/triage notes,
  tenant/application/business-reference extraction for scoped filtering, bulk retry only within the
  same scope/failure class, and ledger-exists safety indicators before replay.
- Implemented first learner enrollment promotion BFF. Web learn now previews a coupon through
  enrollment-service before enrollment confirmation; enrollment-service builds trusted course/profile
  facts and calls promotion runtime internally with `enrollment-service` scoped JWTs. On confirmation
  it reserves before enrollment, commits after enrollment success, and cancels the reservation if
  enrollment fails. Runtime `/internal/incentives/**` remains service-to-service only.

## Implementation Guardrails

- Do not continue the current draft as a simple CRUD service.
- Do not add UI before the transaction kernel is correct.
- Do not implement arbitrary scripting rule engine.
- Do not mutate published campaign rules without versioning or audit.
- Do not evaluate by calling back into LMS.
- Do not use Redis as redemption source of truth.
- Do not store only mutable counters without ledger.
- Do not claim production readiness without concurrency and idempotency tests.
