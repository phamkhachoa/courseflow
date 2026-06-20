# Council 0094: Product Readiness Live Response Metrics Ingest

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Promote live response-metrics ingest from follow-up into a required Product Readiness gate |
| SA AI Engineer | Keep incident timestamps deterministic, parseable and tenant-safe |
| PO/BA | Make stakeholder readiness distinguish SLO health from live-ingest coverage |
| Governance Reviewer | Confirm the live metrics ledger excludes tenant, principal, payload and credential values |
| Admin/Ops | Use live acknowledgement, containment, recovery and closure timestamps as response evidence |

## Decision

Connect the Product Readiness Freshness response metrics report to a tenant-safe live
response metrics ledger. The metrics report now prefers live observations by scenario
and falls back to the synthetic drill baseline only when a live observation is missing.

| Surface | Result |
| --- | --- |
| Live ledger | `platform/operations/metrics/product-readiness-freshness-live-response-metrics-v1.yaml` |
| Report field | `ingest_status: live_ingest_connected` |
| Product gate | `product_readiness_freshness_live_response_metrics_ingest_connected` |
| SLO gate | `product_readiness_freshness_response_metrics_slo_met` |
| Follow-up | `trend_product_readiness_freshness_response_slo_by_owner` |

## Acceptance Evidence

The live ingest baseline covers every Product Readiness Freshness response-drill
scenario without exposing raw tenant or runtime payload data.

| Metric | Required result |
| --- | --- |
| Ingest status | `live_ingest_connected` |
| Live observations | `5` |
| Synthetic observations | `0` |
| Missing live observations | `0` |
| Raw identifier count | `0` |
| Response metrics status | `slo_met` |

## Outcome

Product Readiness now requires both live-ingest coverage and SLO compliance. A missing
or partial live metrics ledger blocks the ingest gate even if the synthetic response
baseline still meets SLO.

## Next Step

Trend response SLOs by owner role and scenario class, then route drift alerts to
Admin/Ops before response performance degrades into stakeholder-visible freshness risk.
