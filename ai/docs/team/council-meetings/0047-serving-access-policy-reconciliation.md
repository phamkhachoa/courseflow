# Council 0047: Serving Access Policy Reconciliation

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The platform now reconciles the active model-serving access policy against the apply ledger. This closes the control loop after the controlled applier: Admin/Ops can see whether the policy is still pending, applied but not recorded, fully reconciled or drifting.

The platform added:

- `platform/src/courseflow_ai_platform/serving_access_policy_reconciliation.py`
- `platform/tests/test_serving_access_policy_reconciliation.py`
- `platform/governance/reports/model-serving-access-policy-reconciliation-v1.yaml`
- CLI flag `--write-serving-access-policy-reconciliation-report`

## Current Reconciliation Status

| Scope | Value |
|---|---:|
| Applications | 1 |
| Pending apply | 1 |
| Reconciled | 0 |
| Ledger update required | 0 |
| Drift | 0 |

The active policy still matches the ledger source checksum, while the proposed checksum contains `tenant-lms-sandbox`. This is correct for the current state: the next action remains `run_controlled_policy_applier`.

## Guardrails

- Active policy equal to source checksum means pending apply unless the ledger claims applied.
- Active policy equal to proposed checksum requires the ledger to be marked applied.
- Active policy different from both source and proposed checksums is drift.
- Applied ledger entries must include applied checksum and timestamp.

## Next Step

Council 0048 promotes serving access control-plane projections into the operating cockpit. The next control-plane slice is a tenant-safe incident export for drift, blocked or stale apply conditions.
