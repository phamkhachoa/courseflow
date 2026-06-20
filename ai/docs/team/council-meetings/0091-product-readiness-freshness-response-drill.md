# Council 0091: Product Readiness Freshness Response Drill

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| PO/BA | Make product readiness recovery evidence visible to release stakeholders |
| SA AI Platform | Keep the drill snapshot-backed and independent from live route probing |
| SA AI Engineer | Validate stale report, route outage, static snapshot, runtime error and audit-gap response paths |
| Governance Reviewer | Preserve tenant safety by using product-readiness hash refs and omitting raw runtime payloads |
| Admin/Ops | Prove incident acknowledgement, assignment, containment, remediation, verification and closure steps |

## Decision

Add `product-readiness-freshness-incident-response-drill-v1` as an executable runbook
drill. The drill reads the current Product Readiness Freshness incident export and validates
synthetic P0/P1 scenarios against the structured runbook
`product-readiness-freshness-incident-response-v1`. It remains deterministic because it uses
snapshot evidence and synthetic incident generation instead of calling the runtime product
readiness route.

## Runtime Evidence

| Surface | Result |
| --- | --- |
| Drill report | `platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml` is `passed` |
| Scenario coverage | 5/5 scenarios pass across report stale, route unreachable, static snapshot stale, runtime error/audit failure and audit gap |
| Admin/Ops dashboard | Adds Product Runbook status card and Product Readiness Freshness Response Drill panel |
| Freshness manifest | Dashboard source tracking increases to 8/8 current sources |
| Product readiness | Required gates increase to 9/9 passed and include the product freshness response drill |
| Safety | Drill snapshot has `tenant_safe=true`, `raw_identifier_count=0` and only product-readiness hash refs |

## Outcome

Product readiness freshness incidents now have an executable Admin/Ops response path. The
platform can prove that stale snapshots, route outages and runtime audit gaps have defined,
tenant-safe detection, acknowledgement, assignment, containment, remediation, verification,
communication and closure steps.

## Next Step

Persist acceptance of the Product Readiness Freshness response drill in the delivery state
ledger so release stakeholders can see the same state-accepted evidence path used for
Governance Evaluation response readiness.
