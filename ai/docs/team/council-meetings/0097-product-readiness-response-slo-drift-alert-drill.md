# Council 0097 - Product Readiness Response SLO Drift Alert Drill

Date: 2026-06-17
Product: Enterprise AI Platform

## Roles

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Promote the response SLO drift alert drill into Product Readiness evidence |
| SA AI Engineer | Replay routed watch-level alerts without exposing raw tenant or service identifiers |
| PO/BA | Keep stakeholder readiness visible while calibration monitoring remains a follow-up |

## Decision

The council accepts a tenant-safe alert drill for Product Readiness Freshness response
SLO drift. The drill replays routed watch alerts, validates the Admin/Ops route,
validates the triage action, checks trigger usage against the watch threshold and
keeps raw tenant, service and credential values out of artifacts.

## Evidence

| Item | Evidence |
| --- | --- |
| Source module | `platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_alert_drill.py` |
| Drill report | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_drift_alert_drill_passed` |
| Dashboard panel | Product Readiness Freshness Response SLO Drift Alert Drill |
| Current drill status | `passed` |
| Routed alert replay | `1/1` |
| Next action | `monitor_product_readiness_response_slo_drift_alert_calibration` |

## Acceptance

- The drill report must pass only when every routed alert path passes validation.
- Product Readiness must block if configured alerts cannot be replayed safely.
- Admin/Ops must see the drill result in the dashboard and freshness manifest.
- The next follow-up shifts from exercising the alert path to monitoring calibration.
