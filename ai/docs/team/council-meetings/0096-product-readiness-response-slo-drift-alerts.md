# Council 0096: Product Readiness Response SLO Drift Alerts

Date: 2026-06-18

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Promote response SLO drift alerts into Product Readiness evidence |
| SA AI Engineer | Route tenant-safe alerts from response trend watch scenarios |
| PO/BA | Keep stakeholder readiness visible while the alert drill remains follow-up work |
| Governance Reviewer | Confirm alert payloads exclude tenant, principal, request body and credential values |
| Admin/Ops | Own routed response drift alerts before they become freshness incidents |

## Decision

Add a Product Readiness Freshness response SLO drift alert report. The report reads
the owner/scenario trend snapshot, creates a routed Admin/Ops alert for each watch
scenario and blocks Product Readiness if watch scenarios are not fully routed.

| Surface | Result |
| --- | --- |
| Alert report | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alerts-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_drift_alerts_configured` |
| Dashboard panel | Product Readiness Freshness Response SLO Drift Alerts |
| Current alert status | `alerts_configured_with_watch` |
| Follow-up | `exercise_product_readiness_response_slo_drift_alert_drill` |

## Acceptance Evidence

The alert route is configured for the current watch scenario without exposing raw
tenant or runtime payload data.

| Metric | Required result |
| --- | --- |
| Watch scenarios | `1` |
| Alerts | `1` |
| Routed alerts | `1` |
| Alert route | `admin-ops` |
| Alert action | `triage_product_readiness_response_slo_drift` |
| Max trigger usage | `87%` |
| Raw identifier count | `0` |

## Outcome

Product Readiness now requires response SLO drift alerts in addition to response
drill, live ingest, SLO compliance and owner trend readiness. The platform remains
stakeholder-ready with follow-ups because the alert path still needs an operations
drill.

## Next Step

Exercise the response SLO drift alert drill and record accepted delivery-state
evidence so Admin/Ops can prove the route works before a watch scenario escalates.
