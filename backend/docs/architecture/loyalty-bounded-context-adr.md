# ADR: Loyalty Bounded Context

Status: Accepted

Date: 2026-06-14

Accepted by: PO, BA, SA, Senior Backend Dev review for Incentive Contract Pack v2.

## Context

CourseFlow is evolving `promotion-service` into a portable incentive platform. Promotion, coupon, and
loyalty belong to the same product family, but they must not collapse into one coupon-like entity.

The current `promotion-service` already owns campaign decisioning, coupon credentials, reservation,
redemption, quota, audit, outbox, and retention operations. It intentionally accepts generic facts
from a source application instead of calling LMS/order/profile services itself.

Loyalty is different from campaign redemption. It needs long-lived account balances, points expiry,
tier state, rewards, earn/burn/reversal semantics, and manual adjustment controls. Those concerns are
ledger-first and should not be hidden inside campaign JSON metadata.

## Decision

Create loyalty as a separate bounded context when implementation starts. The deployable can initially
be either a separate `loyalty-service` or an isolated module, but it must own its own schema, API
contract, audit, outbox events, and retention policy.

`promotion-service` may emit promotion effects that `loyalty-service` consumes asynchronously, such as a
`POINTS_EARN_INTENT`, but it must not own loyalty account balance or points expiry.

The first production implementation must prefer a separate `loyalty-service` if cross-team ownership,
separate scaling, or independent release cadence is required. An isolated module is acceptable only
as a temporary bootstrap if it keeps a separate schema, contract package, event namespace, and test
suite.

## Domain Model

- `loyalty_program`: tenant/application scoped program definition.
- `loyalty_account`: one account per profile/program, with lifecycle status.
- `loyalty_points_entry`: immutable ledger entry for earn, burn, expire, reverse, and adjustment.
- `loyalty_balance_bucket`: read model grouped by expiry date and point state.
- `loyalty_tier_policy`: tier thresholds and grace/downgrade rules.
- `loyalty_tier_state`: account tier, qualification window, and next review date.
- `loyalty_reward`: redeemable reward definition that may generate a coupon or entitlement.
- `loyalty_reward_redemption`: reward redemption state and reversal.

## State Rules

- Points are immutable ledger entries; balance is derived or maintained as a projection.
- Earn and burn are idempotent by source event/reference.
- Burn cannot overdraw unless a program explicitly allows negative balance.
- Expiry creates `EXPIRE` entries; it never mutates original earn entries.
- Reversal creates compensating entries and links to the original entry.
- Manual adjustment requires actor, reason, correlation ID, and audit event.
- Tier changes are derived from ledger/profile facts and recorded as state transitions.

## API Contract

Initial loyalty APIs should be generic and not LMS-specific:

- `POST /internal/loyalty/programs`
- `GET /internal/loyalty/programs`
- `GET /internal/loyalty/accounts/{accountId}`
- `GET /internal/loyalty/accounts?tenantId&applicationId&programId&profileId`
- `POST /internal/loyalty/accounts`
- `POST /internal/loyalty/points:earn`
- `POST /internal/loyalty/points:burn`
- `POST /internal/loyalty/points/{entryId}:reverse`
- `POST /internal/loyalty/points:adjust`
- `POST /internal/loyalty/points:expire-dry-run`
- `POST /internal/loyalty/points:expire`
- `GET /internal/loyalty/rewards`
- `POST /internal/loyalty/rewards`
- `PATCH /internal/loyalty/rewards/{rewardId}`
- `PATCH /internal/loyalty/rewards/{rewardId}/status`
- `GET /internal/loyalty/me/wallet`
- `GET /internal/loyalty/me/rewards`
- `POST /internal/loyalty/me/rewards/{rewardId}:redeem`
- `GET /internal/loyalty/reward-redemptions`
- `GET /internal/loyalty/ledger?accountId&profileId&programId&from&to`

Every mutation requires idempotency and writes audit plus outbox in the same transaction.

## Security And Idempotency

- External user authentication remains owned by IAM/Keycloak and the access-control layer.
- Service-to-service calls use internal JWT scopes; loyalty must define `internal:loyalty:<operation>`
  scopes rather than reusing promotion scopes.
- Runtime callers must be explicitly bound to the tenant/application/program they can mutate.
- Every earn, burn, reverse, adjust, and expire command requires an idempotency key and a source
  reference.
- Same idempotency key and same request hash replays; same key and different request hash conflicts.
- Manual adjustment and reversal require actor, reason, correlation id, and audit event.

## Control Plane vs Data Plane

Runtime endpoints are data-plane behavior. They enforce active program/account state before new
business mutations and runtime reads that represent active product use.

Admin endpoints are control-plane behavior. They enforce admin access but may inspect suspended or
closed resources for investigation, recovery, and audit. For example, admin ledger lookup must still
return ledger entries after an operator suspends an account or program; otherwise the incident
workflow would block itself.

Program timeline includes both program lifecycle events and client-binding lifecycle events for the
program because binding status is part of the effective runtime access policy.

## Events

Events must be typed records in `event-contracts`, versioned, and safe for downstream dedup:

- `loyalty.points.earned`
- `loyalty.points.burned`
- `loyalty.points.expired`
- `loyalty.points.reversed`
- `loyalty.points.adjusted`
- `loyalty.tier.changed`
- `loyalty.reward.redeemed`
- `loyalty.reward.reversed`

Events must contain `eventId`, `schemaVersion`, `tenantId`, `applicationId`, `programId`, `accountId`,
`profileId`, source reference, point amount, unit, occurred time, and metadata.

## Integration With Promotion

Promotion may produce intent effects with:

- `benefitType=POINTS_EARN_INTENT`
- `actionType=LOYALTY_POINTS_EARN`
- `unit=POINT`
- `targetType=LOYALTY_ACCOUNT`
- generic metadata such as `programId`, source reference, and the full upstream `effectId`

`loyalty-service` consumes `incentive.redemption.committed`, filters `POINTS_EARN_INTENT`, and applies
an `EARN` ledger entry with source/idempotency key `promotion:{redemptionId}:{sha256(effectId)[0..32]}`.
The shorter hashed suffix keeps the operational key inside the loyalty ledger column limit while
preserving the full upstream `effectId` in metadata for reconciliation. Promotion itself must not
mutate loyalty balance.

`loyalty-service` also consumes `incentive.redemption.reversed` and creates a compensating loyalty
`REVERSE` entry against the original promotion earn source reference. Reversal uses idempotency key
`promotion-reversal:{redemptionId}:{sha256(effectId)[0..32]}`.

The consuming service actor is an STS-issued internal JWT for the configured promotion actor client,
default `promotion-service`, with `internal:loyalty:earn` and `internal:loyalty:reverse`. Loyalty
verifies issuer, audience, signature and expiry before trusting the token claims. The target loyalty
program must explicitly bind client `promotion-service` to operations `earn` and `reverse`. Missing
binding fails closed and should be fixed through the loyalty admin control plane.

Unexpected consumer failures use bounded retry and then move to `<topic>.DLT`; malformed intent
payloads are skipped with warnings because retrying the same bad data cannot repair the event.
`loyalty-service` also consumes the configured promotion-to-loyalty DLT topics into
`loyalty_inbound_dead_letters` so platform operators can inspect exception metadata, payload hash,
Kafka position, replay attempts, and resolution state from the admin control plane. Replay publishes
the original payload back to the source topic after operator review; discard records manual
resolution without mutating loyalty ledger state.

## Reward Catalog And Redemption

Rewards belong to loyalty, not promotion. A promotion may award points by emitting a points intent,
but reward redemption spends points by writing an immutable loyalty `BURN` ledger entry first. The
reward redemption row is operational state that references the burn entry, source reference and
fulfillment status; it is not a separate balance or a coupon redemption substitute.

The first reward slice intentionally supports a compact catalog and redemption skeleton:

- Admin creates and updates tenant/application/program scoped rewards.
- Reward lifecycle status controls visibility and redemption.
- Active window, inventory limit and per-profile limit are enforced in the redemption transaction.
- Learner catalog eligibility is advisory and always rechecked before burning points.
- Same idempotency key and same request hash replays; same key with different request conflicts.
- Learner redemption resolves profile id from the authenticated caller, never from the request body.
- Reward redemption stores a safe reward snapshot at redeem time so support/audit does not depend on
  mutable catalog fields later.
- Reward support reversal creates or replays a linked loyalty `REVERSE` ledger entry and marks the
  redemption `REVERSED`; it never deletes redemption state or uses an unrelated manual adjustment.
- Fulfillment support may mark a redemption `PENDING`, `MANUAL_REQUIRED`, `ISSUED`, or `FAILED` and
  attach an external/manual reference. Fulfillment status changes do not mutate points.
- Fulfillment is limited to `MANUAL` and `AUTO_ISSUE` skeleton states until a dedicated fulfillment
  integration is designed.

Promotion and loyalty integrate through stable contracts only:

- Promotion events/effects are consumed as facts or intents.
- Promotion never writes loyalty ledger, account, expiry lot, or reward state.
- Loyalty owns the points ledger and emits loyalty events after it mutates loyalty state.
- Neither context reaches into the other context's tables.
- Reconciliation is done by event/source-reference ids, not by database joins.

## Non-Goals

- No arbitrary scripting engine.
- No LMS-specific fields such as `courseId`, `studentId`, `enrollmentId`.
- No Redis-as-source-of-truth for points or balance.
- No hidden points balance inside campaign, coupon, or redemption metadata.
- No reward catalog before points ledger, expiry and reversal semantics are production-safe.
- No reward redemption that bypasses the loyalty `BURN` ledger kernel.
- No loyalty implementation inside `promotion-service`.
- No shared mutable ledger table between promotion and loyalty.

## Acceptance Criteria Before Implementation

- A dedicated contract package exists for loyalty OpenAPI/AsyncAPI/JSON Schema.
- The first schema migration creates a loyalty-owned schema or service database, not promotion tables.
- Event contracts define deduplication keys and source reference semantics.
- Expiry and reversal are covered by tests before tier/reward features are added.
- Access-control rules and internal scopes are documented before runtime endpoints are exposed.
- Promotion integration is limited to intent effects or events; no direct promotion-to-loyalty table
  writes are allowed.

## Consequences

This adds a service/context boundary, but keeps the platform portable. Promotion remains focused on
campaign decisioning and redemption correctness, while loyalty can evolve its own ledger, tier, and
reward lifecycle without overloading promotion campaign semantics.
