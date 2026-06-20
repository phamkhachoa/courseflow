# Council 0046: Serving Access Controlled Applier

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The platform now has a controlled applier for model-serving access policy proposals. The applier is deliberately split into a report path and an explicit target write path:

- CLI writes `platform/governance/reports/model-serving-access-policy-apply-report-v1.yaml`.
- Runtime API can write the proposed policy only when an explicit output policy path is supplied.
- The default CLI path does not mutate the active policy.

The platform added:

- `platform/src/courseflow_ai_platform/serving_access_policy_applier.py`
- `platform/tests/test_serving_access_policy_applier.py`
- `platform/governance/reports/model-serving-access-policy-apply-report-v1.yaml`
- CLI flag `--write-serving-access-policy-apply-report`

## Current Controlled Apply Status

| Scope | Value |
|---|---:|
| Apply status | ready_to_write |
| Ready applications | 1 |
| Blocked entries | 0 |
| Checksum mismatches | 0 |
| Planned operations | 1 |
| Active policy would change | 1 |

The controlled applier can write a policy containing `tenant-lms-sandbox` for `service:lms-courseflow-serving` to an explicit target. The active policy remains unchanged until Admin/Ops intentionally runs that write path.

## Guardrails

- No patch-plan operations means no apply.
- No ready ledger entry means no apply.
- Any blocked ledger entry prevents apply.
- Any checksum mismatch prevents apply.
- Any missing reviewer role prevents apply.
- Policy write requires an explicit `output_policy_path`.

## Next Step

Council 0047 adds applied-state reconciliation. The next control-plane slice is to project pending apply, reconciliation and drift queues into the operating cockpit for Admin/Ops.
