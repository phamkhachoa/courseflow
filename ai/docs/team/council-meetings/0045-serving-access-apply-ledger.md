# Council 0045: Serving Access Apply Ledger

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The platform now records review decisions and checksums before a model-serving access policy proposal is applied.

The platform added:

- `platform/governance/ledgers/model-serving-access-policy-apply-ledger.yaml`
- `platform/governance/reports/model-serving-access-policy-apply-ledger-v1.yaml`
- `platform/src/courseflow_ai_platform/serving_access_apply_ledger.py`
- `platform/tests/test_serving_access_apply_ledger.py`
- CLI flag `--write-serving-access-apply-ledger-report`

## Current Apply Ledger

| Scope | Value |
|---|---:|
| Applications | 1 |
| Ready to apply | 1 |
| Pending review | 0 |
| Blocked | 0 |
| Checksum mismatches | 0 |

The approved application records Admin/Ops and Governance Reviewer approval for the LMS sandbox tenant policy proposal. The ledger binds that decision to the source policy checksum and proposed policy checksum.

## Guardrails

- Apply entries must match the current patch plan ID.
- Apply entries must match the current source policy checksum.
- Apply entries must match the current proposed policy checksum.
- The request IDs must match the current patch-plan operations.
- `applied` entries must also record `applied_policy_sha256` and `applied_at`.

## Next Step

Council 0046 adds the controlled applier. The next control-plane slice is applied-state reconciliation after Admin/Ops intentionally writes a policy proposal.
