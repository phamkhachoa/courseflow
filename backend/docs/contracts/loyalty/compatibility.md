# Loyalty Contract Compatibility

`loyalty-service` is a separate bounded context from `promotion-service`. Promotion may decide an
offer or emit a points intent, but it must not own account balances, expiry buckets, tier state,
reward state, or the immutable loyalty ledger.

## Stable API Rules

- `openapi.yaml` is the file-based source of truth for REST consumers.
- `asyncapi.yaml` is the file-based source of truth for loyalty outbox events.
- Internal callers must use signed internal JWT scopes, not legacy shared headers.
- Runtime service operations verify internal JWT issuer, audience, signature and expiry before
  trusting `actor_type`, `azp`, or `scope` claims.
- The promotion points consumer obtains an STS `client_credentials` token for the configured actor
  client, default `promotion-service`, and caches it until shortly before expiry.
- Earn, burn, and reverse mutations must carry an idempotency key.
- Reward redemption must burn points through the loyalty ledger kernel before recording reward
  redemption state. Reward must not maintain a separate spendable points balance.
- Reward redemption records must retain a safe reward snapshot captured at redemption time. Support
  and reconciliation must not explain historical redemptions by reading mutable reward catalog fields.
- Manual adjustment must carry a signed non-zero `pointsDelta`, a reason, a correlation id, and an
  idempotency key.
- `sourceReference` must be unique per program and mutation type for non-reversal entries.
- Ledger entries are immutable. Corrections are new compensating entries.
- Burn, reward redemption, and earn reversal cannot overdraw active unexpired point lots unless the
  program explicitly allows negative balance. Ledger balance is retained for audit/reconciliation
  only; spendable balance is the materialized active lot balance.
- Debit entries record point-lot allocation metadata. Reversing a debit restores the original lots
  and expiry buckets instead of creating a new non-expiring credit bucket.
- Responses and events do not include request hashes, idempotency key hashes, raw secrets, or mutable
  rule snapshots.

## Current Internal Endpoints

- `GET /internal/loyalty/me/balances`
- `GET /internal/loyalty/me/wallet`
- `GET /internal/loyalty/me/rewards`
- `POST /internal/loyalty/me/rewards/{rewardId}:redeem`
- `GET /internal/loyalty/programs`
- `GET /internal/loyalty/program-readiness`
- `POST /internal/loyalty/programs`
- `GET /internal/loyalty/programs/{programUuid}`
- `PATCH /internal/loyalty/programs/{programUuid}`
- `PATCH /internal/loyalty/programs/{programUuid}/status`
- `POST /internal/loyalty/programs/{programUuid}/client-bindings`
- `GET /internal/loyalty/programs/{programUuid}/timeline`
- `POST /internal/loyalty/accounts`
- `GET /internal/loyalty/accounts/{accountId}`
- `GET /internal/loyalty/accounts?tenantId&applicationId&programId&profileId`
- `GET /internal/loyalty/accounts:search`
- `PATCH /internal/loyalty/accounts/{accountId}/status`
- `GET /internal/loyalty/accounts/{accountId}/timeline`
- `GET /internal/loyalty/accounts/{accountId}/balance-buckets`
- `POST /internal/loyalty/points:earn`
- `POST /internal/loyalty/points:burn`
- `POST /internal/loyalty/points:adjust`
- `POST /internal/loyalty/points/{entryId}:reverse`
- `POST /internal/loyalty/points:expire-dry-run`
- `POST /internal/loyalty/points:expire`
- `POST /internal/loyalty/expiry-approvals`
- `POST /internal/loyalty/point-lots:backfill`
- `GET /internal/loyalty/adjustment-approvals`
- `POST /internal/loyalty/adjustment-approvals`
- `POST /internal/loyalty/adjustment-approvals/{approvalId}:approve`
- `POST /internal/loyalty/adjustment-approvals/{approvalId}:reject`
- `GET /internal/loyalty/approvals/{approvalId}/evidence-pack`
- `GET /internal/loyalty/ledger?accountId={accountId}`
- `GET /internal/loyalty/reconciliation/entries`
- `GET /internal/loyalty/finance/closeout`
- `GET /internal/loyalty/rewards`
- `POST /internal/loyalty/rewards`
- `GET /internal/loyalty/rewards/{rewardId}`
- `PATCH /internal/loyalty/rewards/{rewardId}`
- `PATCH /internal/loyalty/rewards/{rewardId}/status`
- `GET /internal/loyalty/reward-redemptions`
- `GET /internal/loyalty/reward-redemptions/{redemptionId}`
- `POST /internal/loyalty/reward-redemptions/{redemptionId}:reverse`
- `PATCH /internal/loyalty/reward-redemptions/{redemptionId}/fulfillment`
- `GET /internal/loyalty/dead-letters`
- `GET /internal/loyalty/dead-letters/{deadLetterId}`
- `POST /internal/loyalty/dead-letters/{deadLetterId}:replay`
- `POST /internal/loyalty/dead-letters/{deadLetterId}:discard`
- `GET /internal/loyalty/audit`

`POST /internal/loyalty/points:expire-dry-run` is intentionally non-mutating. It previews
materialized remaining lots when available and falls back to gross ledger candidates for old data.
`POST /internal/loyalty/expiry-approvals` locks the dry-run `resultHash` into maker-checker review.
`POST /internal/loyalty/points:expire` requires an approved `approvalId`, verifies that the current
materialized lot candidate hash still matches the approved dry-run, and then writes immutable
`EXPIRE` ledger entries. Idempotent retries may replay an already executed approval only when the
same idempotency key and request hash are used.
`GET /internal/loyalty/accounts/{accountId}/balance-buckets` is a read-only FIFO projection for
operations visibility. When materialized lots exist, the endpoint reports
`MATERIALIZED_REMAINING_LOT_TABLE` and reflects settlement state used by expiry execution.
`GET /internal/loyalty/me/balances` is learner-facing. It resolves `profileId` from the
authenticated caller, never from a query parameter, and returns compact wallet totals for web learn.
`GET /internal/loyalty/me/wallet` is the learner wallet BFF read model. It resolves `profileId` from
the caller and returns account summaries, expiry buckets, recent ledger entries, reward eligibility
and redemption history in one response so web learn does not fan out across multiple loyalty APIs.
`GET /internal/loyalty/program-readiness` is a read-only pre-publish probe for integrations such as
promotion campaigns that emit `LOYALTY_POINTS_EARN` intents. It checks program existence, active
status, client binding and requested operation access, and returns blockers instead of mutating
loyalty state.
`GET /internal/loyalty/me/rewards` is learner-facing. It requires tenant/application scope,
calculates advisory eligibility from the caller profile, active unexpired point lots, active reward
window, inventory and per-profile limits, and never accepts a caller-supplied `profileId`.
`POST /internal/loyalty/me/rewards/{rewardId}:redeem` rechecks eligibility inside the transaction,
burns only active unexpired point lots with an immutable `BURN` ledger entry, then records
`loyalty_reward_redemptions`.
Idempotent retry with the same key/request replays; the same key with different payload conflicts.
The redemption response includes a safe historical reward snapshot and excludes raw secret-bearing
fulfillment config.
`POST /internal/loyalty/point-lots:backfill` rebuilds materialized remaining-lot settlement state
from immutable ledger entries. It defaults to dry-run and returns a `resultHash`; execute requires
the latest hash as `expectedResultHash`, then creates missing lots, resets existing lot consumption,
and replays debits FIFO by expiry then occurrence time under account-first locks.
`GET /internal/loyalty/approvals/{approvalId}/evidence-pack` returns the approval, related audit
events, ledger/reconciliation rows, safe metadata and warnings for finance/compliance evidence.
`GET /internal/loyalty/finance/closeout` returns scoped ledger totals for the full closeout window
and a limited row sample/export page. `totals` are not derived from the returned page. Outbox status
counts cover the full window so finance can reject reports with pending or missing publication.
The response includes a deterministic `closeoutId` and `resultHash` derived from scope, window and
totals. `certifiable` is `false` when the export page is incomplete or the closeout still has
pending/missing outbox evidence. When `hasMore` is true the client should pass the opaque
`nextCursor` back as `cursor` with the same filters and `limit` to continue the export.
`GET /internal/loyalty/dead-letters` and related action endpoints expose the promotion-to-loyalty
Kafka DLT operations queue. Only platform admins or service callers with loyalty admin scope may
view or resolve records. Detail responses intentionally expose payload hash, payload size, headers,
Kafka position and exception metadata, but not raw payload. Live replay/discard requires an approved
maker-checker `approvalId`; dry-run remains read-only. Replay republishes the stored original payload
to the captured source topic; discard marks the record as manually resolved without publishing it.
The live promotion-to-loyalty consumer records processed upstream `eventId`s after successful
handling. Replayed records with the same payload are skipped before ledger mutation; same event id
with a different payload is treated as an inbound payload conflict and is retry/DLT eligible.
`GET /internal/loyalty/rewards` and related admin reward endpoints manage reward catalog metadata,
lifecycle status, inventory and per-profile limits. `GET /internal/loyalty/reward-redemptions`
exposes redemption history for operations/reconciliation without exposing idempotency keys or request
hashes.
`POST /internal/loyalty/reward-redemptions/{redemptionId}:reverse` is an admin support action that
reverses the original burn ledger entry and marks the redemption `REVERSED`; it must not use manual
adjustment as a shortcut.
`POST /internal/loyalty/reward-redemptions/{redemptionId}/fulfillment-approvals` submits manual
reward fulfillment overrides for maker-checker review. The approval metadata captures current
fulfillment status/reference, target status/reference/note, threshold policy, idempotency key and
request hash.
`PATCH /internal/loyalty/reward-redemptions/{redemptionId}/fulfillment` only changes fulfillment
status/reference/note after receiving an approved `approvalId` whose scope/hash still matches the
current redemption. It must not mutate points, and failed fulfillment that should return points must
use reward redemption reversal. Provider callbacks and retry runs remain separate service/admin
operations and do not use the manual override approval contract.

## Producer Events

- `loyalty.points.earned`
- `loyalty.points.burned`
- `loyalty.points.reversed`
- `loyalty.points.adjusted`
- `loyalty.points.expired`
- `loyalty.reward.redeemed`
- `loyalty.reward.reversed`
- `loyalty.reward.fulfillment_status_changed`

All point-change events share the `loyalty-points-changed.v1.json` schema. Consumers must treat event
payloads as append-only: new optional fields may be added, existing field semantics must not change,
and `schemaVersion=1` remains backward compatible.
Reward lifecycle events share the `loyalty-reward-redemption.v1.json` schema. They are emitted from
the same transaction as reward redemption/reversal/fulfillment state changes and carry safe reward
and redemption identifiers, fulfillment state, burn/reversal entry ids, actor/correlation context,
and no idempotency keys or request hashes.
