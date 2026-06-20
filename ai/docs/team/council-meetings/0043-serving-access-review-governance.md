# Council 0043: Serving Access Review Governance

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Model-serving access policy changes are now handled as governed change requests before they are applied to `model-serving-access-policy.yaml`.

The platform added:

- `platform/governance/requests/model-serving-access-requests.yaml`
- `platform/governance/reports/model-serving-access-review-v1.yaml`
- `platform/src/courseflow_ai_platform/serving_access_review.py`
- `platform/tests/test_serving_access_review.py`

## Review Rules

- Every request must name a target principal, product, owner role, business justification, scopes, tenants, models and evidence refs.
- Base serving grants require `PO/BA`, `SA AI Platform` and `SA AI Engineer` approvals.
- Tenant expansion also requires `Governance Reviewer`.
- Ops scope also requires `Admin/Ops`.
- Non-platform products cannot grant models owned by another product.
- The report separates `applied`, `ready_for_apply`, `needs_approval`, `blocked` and `rejected` queues.

## Current Queue

| Queue | Count | Notes |
|---|---:|---|
| Applied | 2 | LMS sequence-risk and Support serving grants already match active policy |
| Ready for apply | 1 | LMS sandbox tenant expansion has required approvals |
| Needs approval | 1 | Enterprise Operations ops observability still needs PO/BA and Admin/Ops |
| Blocked | 1 | Finance request for Support SLA model is blocked as cross-product access |

## Next Step

Council 0044 adds the reviewable policy patch generator. The next control-plane slice is an apply ledger that records reviewer identity, timestamp and checksum when a proposed policy is accepted.
