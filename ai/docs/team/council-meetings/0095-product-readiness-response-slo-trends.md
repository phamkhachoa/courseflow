# Council 0095: Product Readiness Response SLO Trends

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Promote response SLO owner trends into Product Readiness evidence |
| SA AI Engineer | Derive tenant-safe owner/scenario trend metrics from live response observations |
| PO/BA | Keep stakeholder readiness visible when trends are ready but drift alerts remain follow-up work |
| Governance Reviewer | Confirm trend snapshots do not expose tenant, principal, request body or credential values |
| Admin/Ops | Use owner-level watch scenarios to prioritize response hardening |

## Decision

Add a Product Readiness Freshness response SLO trend report that groups live
response metrics by owner role and scenario class. The report marks SLO breaches as
blocking and marks scenarios that use at least 80% of an SLO budget as watch items.

| Surface | Result |
| --- | --- |
| Trend report | `platform/operations/reports/product-readiness-freshness-response-trends-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_trend_ready` |
| Dashboard panel | Product Readiness Freshness Response Trends |
| Current trend status | `trend_ready_with_watch` |
| Follow-up | `configure_product_readiness_response_slo_drift_alerts` |

## Acceptance Evidence

The trend report is generated from the live response metrics ledger and remains
tenant-safe.

| Metric | Required result |
| --- | --- |
| Owner roles | `1` |
| Scenario classes | `5` |
| Live observations | `5` |
| SLO breaches | `0` |
| Watch scenarios | `1` |
| Max recover SLO usage | `87%` |
| Raw identifier count | `0` |

## Outcome

Product Readiness now has a required trend gate in addition to response drill,
live ingest and SLO compliance. The current state is stakeholder-ready with one
watch scenario, so the platform can proceed while Admin/Ops configures drift alerts.

## Next Step

Configure response SLO drift alerts so watch scenarios become routed Admin/Ops
actions before they turn into Product Readiness Freshness incidents.
