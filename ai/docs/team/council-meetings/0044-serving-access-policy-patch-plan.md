# Council 0044: Serving Access Policy Patch Plan

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Approved serving-access requests are no longer left as manual notes. The platform now generates a reviewable patch plan from `ready_for_apply` requests without mutating the active access policy.

The platform added:

- `platform/src/courseflow_ai_platform/serving_access_policy_plan.py`
- `platform/tests/test_serving_access_policy_plan.py`
- `platform/governance/reports/model-serving-access-policy-patch-plan-v1.yaml`
- CLI flag `--write-serving-access-policy-patch-plan`

## Current Patch Plan

| Scope | Value |
|---|---:|
| Ready requests | 1 |
| Planned operations | 1 |
| Skipped non-ready requests | 4 |
| Proposed principals | 5 |
| Human review required | 1 |

The planned operation merges `tenant-lms-sandbox` into `service:lms-courseflow-serving`. The active policy file remains unchanged until a human reviewer accepts the proposal.

## Guardrails

- Only requests with `review_status: ready_for_apply` are planned.
- `applied`, `needs_approval`, `blocked` and `rejected` requests are skipped.
- The report includes before/after grant snapshots and the full proposed policy.
- Cross-product grants remain blocked by the review stage before the planner runs.

## Next Step

Council 0045 adds the apply ledger. The next control-plane slice is a controlled policy applier that writes the proposed policy only when the ledger is `ready_to_apply`.
