# Council 0048: Serving Access Governance Cockpit

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Serving access governance is now visible in the AI Platform operating cockpit. Pending apply, ledger update and drift queues are no longer isolated governance reports; they become Admin/Ops actions and delivery backlog work.

The platform added:

- `OperatingCockpitServingAccessGovernance`
- cockpit summary fields for serving access governance status, pending apply, ledger update required and drift counts
- cockpit action `serving_access_governance:run_controlled_policy_applier:*`
- delivery backlog phase `serving_access_governance`

## Current Cockpit State

| Scope | Value |
|---|---:|
| Serving access governance status | pending_policy_apply |
| Pending apply | 1 |
| Ledger update required | 0 |
| Drift | 0 |
| Cockpit actions | 20 |
| Delivery backlog items | 20 |
| Delivery SLA tracked items | 17 |

## Guardrails

- Drift becomes a P0 Admin/Ops + Governance action.
- Pending apply becomes a P1 Admin/Ops action.
- Ledger update required becomes a P1 Admin/Ops + Governance action.
- Delivery reports inherit owner aliases, SLA and owner views from cockpit actions.

## Next Step

Completed in Council 0049: add a serving-access incident export so Admin/Ops can hand off drift, blocked or stale apply conditions to incident response without exposing tenant or principal secrets.
