# Council 0050: Serving Access Owner View Rollup

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Admin/Ops owner views now include tenant-safe serving-access incident rollups. Open P0/P1 incidents from the serving-access incident export are shown beside due-soon delivery work, while watch/P2 conditions stay in the incident export and do not crowd the owner work queue.

The platform added:

- `DeliveryOwnerIncidentItem`
- incident counters on `DeliveryOwnerView`
- incident counters on `DeliveryOwnerViewsReport`
- owner-role to owner-alias routing for serving-access incidents
- stale pending apply test coverage for `admin-ops`

## Current Owner View State

| Scope | Value |
|---|---:|
| Owner aliases | 7 |
| Delivery items | 20 |
| Open serving-access incidents | 0 |
| Owners with open incidents | 0 |
| Admin/Ops delivery items | 2 |
| Admin/Ops current open incidents | 0 |

## Stale Apply Scenario

When the existing approved policy application remains pending until 2026-06-20, it becomes:

| Scope | Value |
|---|---|
| Owner alias | `admin-ops` |
| Condition | `stale_pending_policy_apply` |
| Severity | `p1` |
| Status | `open` |
| Action | `escalate_stale_policy_apply` |
| Safety | application ref is hashed; raw tenant/principal/request values are not copied into owner views |

## Guardrails

- Owner-view delivery `item_count` remains the count of backlog/SLA work only.
- Incident counts are explicit fields so delivery work and incident handoffs are not mixed accidentally.
- Only `open` P0/P1 incident handoffs are rolled into owner views.
- Watch/P2 serving-access items remain available in the incident export.
- Incident refs point to governance report/ledger evidence, not raw tenant or principal identifiers.

## Next Step

Completed in Council 0051: add a rendered Admin/Ops dashboard artifact that combines operating cockpit, owner views and serving-access incident rollups into a single human-readable page.
