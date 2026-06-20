# AI Platform Product Council 0018

Date: 2026-06-16

## Topic

Expose artifact promotion readiness as an Admin/Ops projection, not only as a
hard validation rule.

## Decision

Create `platform/src/courseflow_ai_platform/promotion_readiness.py` and
`platform/artifacts/promotions/reports/promotion-readiness-v1.yaml`.

`evidence.py` remains the strict validator for manifests, hashes, promotion
policy, maker-checker, rollback targets and required gate files. Promotion
readiness is a product-facing projection that answers: which AI artifacts are
active, approved or shadow; which gates are ready; whether rollback is available;
whether maker-checker is satisfied; and whether a promotion is ready or blocked.
The same projection now generates the checked-in YAML report and the release
action queue used by Admin/Ops. Promotion policy also defines gate and artifact
freshness: stale evidence blocks readiness even when a gate status was
previously accepted.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Promotion readiness module | `platform/src/courseflow_ai_platform/promotion_readiness.py` |
| Promotion readiness report | `platform/artifacts/promotions/reports/promotion-readiness-v1.yaml` |
| Tests | `platform/tests/test_promotion_readiness.py`, `platform/tests/test_cli.py` |
| CLI output | `promotionReadiness` top-level key and optional report writer |
| Capability registry update | `platform/capabilities/registry.yaml` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Stage summary | Counts active, approved and shadow promotions |
| Gate readiness | Accepted gate statuses count as ready; pending/failed gates block readiness |
| Rollback readiness | Required rollback targets must resolve to known artifact manifests |
| Maker-checker | Requester and approver must differ when policy requires it |
| Non-LMS visibility | Support promotions are shown through the same path as LMS artifacts |
| Blocked reasons | Not-ready promotions are reported as blocked instead of hidden |
| Action queue | Promotions are grouped into active monitoring, ready to activate, keep shadow and blocked |
| Snapshot generation | YAML report is generated from the Python projection and tested against the checked-in snapshot |
| Freshness | Required gates and artifacts expose date, `age_days`, `fresh` and stale evidence reason codes |

## Product Impact

| User | Benefit |
|---|---|
| Admin/Ops | See whether an AI artifact can be released, kept in shadow or rolled back |
| Governance Reviewer | Inspect approval actor separation and gate evidence |
| Product Owner | See cross-product AI artifact readiness, not only LMS state |
| AI Engineer | Debug blocked promotions using gate and rollback reason codes |

## Next Actions

1. Add Admin/Ops UI projection for the generated action queue.
2. Add promotion request intake for candidate artifacts waiting on approval.
3. Add artifact retirement recommendations when an active baseline approaches max age.
