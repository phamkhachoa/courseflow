# Incentive Contract Compatibility

Status: Active

Date: 2026-06-14

## Scope

This package is the file-based source of truth for generic incentive integrators:

- `openapi.yaml` describes current `/internal/incentives/**` REST APIs and the admin gateway alias.
- `asyncapi.yaml` describes outbox topics for incentive events.
- `schemas/*.json` describe event payloads, portable effects, and reconciliation projections.
- `examples/*.json` are golden payloads used by contract tests and consumer onboarding.

The Java DTOs and event records remain implementation details. A consumer should not need to read
Java source to integrate with promotion, coupon, redemption, or reconciliation flows.

## Versioning Policy

- OpenAPI changes use the `info.version` contract suffix.
- Event payloads carry `schemaVersion`; v1 is additive-only.
- JSON Schema files are immutable once consumed by downstream services. New incompatible shapes must
  use a new schema filename and a new `schemaVersion`.
- Adding an optional nullable field is backward-compatible.
- Adding a required field, removing a field, narrowing an enum, changing money sign semantics, or
  changing topic names is breaking.
- REST path and event topic renames are breaking and require an explicit migration plan.

## Security And Privacy

- Service-to-service callers use internal JWTs minted by the token converter flow.
- Service actors must have the matching `internal:promotion:<operation>` scope and an active
  application client binding.
- Operator APIs require incentive admin/reviewer/platform roles as enforced by `promotion-service`.
- Browser/user clients must not call runtime `evaluate`, `reserve`, `commit`, `cancel`, or `reverse`
  with raw transaction facts. Source services or a BFF must resolve trusted facts and call runtime
  endpoints as service actors.
- Learner enrollment coupon UX is mediated by enrollment-service BFF endpoints. The browser submits
  only `courseId`, optional `couponCode`/`couponId`, the latest `promotionPreviewId`, and a flow
  idempotency key; enrollment-service builds the trusted promotion facts and calls runtime
  `evaluate`, `reserve`, `commit`, `cancel`, and `reverse` with an `enrollment-service` internal
  service token.
- Promotion preview may report `UNAVAILABLE` for learner UX, but checkout is fail-closed when a
  coupon selector is supplied. Enrollment-service must not create an enrollment while coupon reserve
  cannot be verified.
- Coupon checkout must re-preview server-side and compare the submitted `promotionPreviewId` with a
  quote hash derived from course id, coupon selector, authoritative list price, currency, price source,
  price status, reason codes, and effect details. A stale or missing preview id is rejected before
  reservation.
- Enrollment-service must use an authoritative course/catalog/checkout price source for coupon
  promotion facts. For course enrollment, it reads `GET /internal/courses/{courseId}/pricing` from
  course-service and sends that `listPrice`, `currency`, `priceStatus` and `priceSource=COURSE_CATALOG`
  in promotion facts. The `CONFIG_DEFAULT` price source is a demo fallback only; coupon preview returns
  `UNAVAILABLE` and coupon checkout fails closed unless
  `ENROLLMENT_INCENTIVES_ALLOW_CONFIG_DEFAULT_PRICE=true` is explicitly enabled.
- Enrollment checkout persists coupon application state by `enrollmentId`, including reservation id,
  redemption id, status, effects, reason codes and the flow idempotency key. Support/reconciliation
  can read it from enrollment-service instead of relying only on the checkout response body.
- Enrollment checkout also persists a hashed checkout attempt keyed by the learner flow
  idempotency key. Same key plus same course/student/coupon/preview payload replays the stored
  checkout response; same key plus a different payload is rejected with conflict.
- A coupon commit outage leaves the enrollment response in `COMMIT_FAILED` with the reservation id
  and schedules enrollment-service retry using the original commit idempotency key. Successful retry
  moves the application to `APPLIED`; an expired/cancelled/rejected reservation moves to
  `MANUAL_REVIEW`.
- Enrollment-service exposes a staff/admin operations queue at
  `GET /internal/enrollments/promotion-applications`. Without a `status` filter it returns open
  `COMMIT_FAILED`, `MANUAL_REVIEW`, and `RESERVED` applications ordered by oldest update first.
  Non-platform staff must scope the query by `courseId`.
- Dropping an enrollment with an `APPLIED` coupon application reverses the committed redemption through
  promotion-service before the drop transaction is allowed to complete. The enrollment application is
  marked `REVERSED`; if promotion reversal is unavailable, drop fails closed and can be retried.
- Dropping an enrollment with a `RESERVED` or `COMMIT_FAILED` coupon application cancels the
  reservation through promotion-service before the drop transaction completes. The application is
  marked `CANCELLED`; if cancellation is unavailable, drop fails closed and can be retried.
- Learner coupon wallet discovery also goes through enrollment-service. Promotion-service exposes a
  service-only `/internal/incentives/learner/coupons` projection for assigned coupons and returns
  masked display fields, effective wallet status, campaign summary and redemption references only.
  It does not expose raw coupon credentials, normalized fingerprints, request snapshots or private
  coupon metadata.
- Assigned wallet coupons are applied by `couponId` from enrollment-service to promotion-service.
  Promotion runtime still validates campaign ownership, active window and `holderProfileId` before
  evaluate/reserve/commit, so the browser never needs the raw coupon code.
- Raw coupon codes are accepted only in write/lookup request fields. Responses, examples, audit,
  reports, and reconciliation exports must use masks or coupon ids only.
- Coupon fingerprints, raw request snapshots, and profile payloads are not contract fields.
- Coupon CSV import dry-run is non-destructive. The persisted batch and row reports store content
  hash, result hash, row masks, counts, warnings, and issue codes only. Raw codes and lookup
  fingerprints must never be written to audit, report JSON, examples, or API responses.
- Experiment preview is an operator-only simulation surface. `POST
  /internal/incentives/admin/experiments:preview` returns deterministic assignment buckets and
  variant allocation bands with `ledgerImpact=false`; it must not be used by checkout/enrollment as
  the runtime assignment source of truth until experiment id/variant attribution is persisted on
  reservation, redemption, ledger and reconciliation records.

## Idempotency

The mutating runtime operations use the `Idempotency-Key` header as the canonical retry key. The
request-body `idempotencyKey` fields remain compatibility fallbacks during migration:

- Reserve: `ReserveIncentiveRequestDto.idempotencyKey`
- Commit: `CommitReservationRequestDto.idempotencyKey`
- Cancel: `CancelReservationRequestDto.idempotencyKey`
- Reverse: `ReverseRedemptionRequestDto.idempotencyKey`
- Coupon CSV import dry-run: optional multipart `idempotencyKey` field or `Idempotency-Key` header.

Same key plus same request hash returns a stored response. Same key plus different request hash is a
conflict. Idempotency responses keep the original business result and set `idempotencyReplay=true`
where the DTO supports it.

Operator/admin redemption reversals now use maker-checker. Support users first call
`POST /internal/incentives/redemptions/{redemptionId}/reversal-approvals` with the execution
`idempotencyKey`, reason, and change ticket. A different reviewer approves the request, then an
operator executes `POST /internal/incentives/redemptions/{redemptionId}/reverse` with the approved
`approvalId`, same `idempotencyKey`, reason, and change ticket. Runtime service actors that hold the
bound `reverse` operation keep the direct reverse path for automated enrollment/order compensation.

## Reservation Ops Contract

`GET /internal/incentives/reservations` and `GET /internal/incentives/reservations/{reservationId}`
are read-only support projections for checkout/enrollment incidents before a reservation becomes a
redemption. They expose status, campaign/coupon/profile references, effects, quota snapshot,
request hash, and timing fields. They must not expose raw request snapshots, raw coupon codes,
coupon fingerprints, idempotency response JSON, or other payloads covered by retention redaction.

## Reconciliation Contract

Consumers must be able to compute net applied benefit without joining mutable campaign or coupon
state. The stable join key is:

```text
redemptionId + effectId
```

`operationType=COMMIT` creates an `APPLY` reconciliation entry. `operationType=REVERSE` creates a
`COMPENSATE` reconciliation entry for the same `redemptionId + effectId`. Consumers compute net
benefit by summing entries per key:

- `APPLY`: positive effect quantity/amount.
- `COMPENSATE`: negative effect quantity/amount.

`couponId` is nullable and is present only when the redemption came from a coupon-backed campaign.
Current v1 reversal behavior keeps `quotaReleased=false` unless a future version explicitly changes
quota semantics.

The read-only API projection is available at
`GET /internal/incentives/reconciliation/entries`. It mirrors the same effect-level reconciliation
model and includes `quotaPolicy` so finance/support can distinguish reserved quota release
(`CANCEL`/`EXPIRE`) from committed redemption reversal
(`NO_RELEASE_ON_COMMITTED_REVERSAL`). The API remains additive-only and must not expose raw coupon
codes, coupon fingerprints, or raw request snapshots.

Coupon import operations expose read-only history at:

- `GET /internal/incentives/coupons/import-dry-runs`
- `GET /internal/incentives/coupons/import-operations`
- `GET /internal/incentives/coupons/import-operations/{importId}`

These projections are operational records, not CSV archives. They may include tenant/application,
campaign, dry-run/import/approval ids, status, row counts, result hash, actor, correlation id,
source client id, timestamps, reason, and change ticket. They must not include raw CSV content, raw
coupon code, normalized code, coupon fingerprint, request hash, idempotency key hash, or stored
response JSON.

## Loyalty Boundary

Loyalty is accepted as a separate bounded context. Promotion may emit intent effects such as
`benefitType=POINTS_EARN_INTENT` via action `LOYALTY_POINTS_EARN`, but it must not own loyalty balances,
expiry buckets, reward inventory, or tier state.

Promotion-to-loyalty application is asynchronous and idempotent:

- campaign action parameters carry `programId` and positive `points`;
- committed redemption events include the portable effect with `effectId`, `quantity`, `unit=POINT`,
  and metadata `programId`;
- `loyalty-service` consumes `incentive.redemption.committed` and applies the intent with
  idempotency/source key `promotion:{redemptionId}:{sha256(effectId)[0..32]}`;
- the full upstream `effectId` remains in loyalty ledger metadata for reconciliation, while the
  shortened operational key stays within loyalty column limits;
- `loyalty-service` consumes `incentive.redemption.reversed` and reverses the original promotion
  earn entry with idempotency key `promotion-reversal:{redemptionId}:{sha256(effectId)[0..32]}`;
- `loyalty-service` records processed upstream `eventId`s in its inbound processed-event table.
  Replays of the same event id and payload are skipped; reuse of the same event id with a different
  payload is rejected and allowed to flow to DLT for operator review;
- `POINTS_EARN_INTENT` effects are fail-closed. Missing `programId`, `effectId`, `profileId`,
  redemption id, or positive point quantity is treated as a malformed points event and is retry/DLT
  eligible instead of being silently skipped;
- the promotion-to-loyalty consumer obtains a short-lived STS `client_credentials` token for the
  configured promotion actor client, default `promotion-service`; the token must carry
  `internal:loyalty:earn internal:loyalty:reverse`;
- the target loyalty program must bind client `promotion-service` to operations `earn` and `reverse`;
- campaign publish validation calls loyalty program readiness for each `LOYALTY_POINTS_EARN` action
  and blocks publish when the target program is missing, inactive, unbound, or not allowed for
  operation `earn`;
- unexpected consumer failures are retried with bounded backoff and then published to
  `<topic>.DLT`; malformed intent effects are rejected as data errors and routed through the same
  retry/DLT path for operator review;
- promotion never writes loyalty tables and loyalty never joins promotion tables.

No loyalty table, service, or account mutation should be added to `promotion-service`.

## Release Gates

Before promoting a contract change:

1. Parse OpenAPI and AsyncAPI successfully.
2. Parse all JSON Schema files and golden examples.
3. Confirm every `PromotionController` mapping appears in `openapi.yaml`.
4. Confirm event schemas include `eventId`, `schemaVersion`, `tenantId`, `applicationId`,
   nullable `correlationId`, nullable `sourceClientId`, and portable `effects`.
5. Confirm reconciliation schemas inherit nullable `correlationId` and nullable `sourceClientId`
   from commit/reverse event contracts.
6. Confirm coupon import dry-run remains masked and non-destructive.
7. Run the promotion service test suite, including PostgreSQL/Testcontainers smoke with zero skipped
   JPA smoke tests in CI.
