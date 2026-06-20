# Council 0098 - Product Readiness Response SLO Drift Alert Calibration

Date: 2026-06-17
Product: Enterprise AI Platform

## Roles

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Promote response SLO drift alert calibration into Product Readiness evidence |
| SA AI Engineer | Validate alert trigger margins, noise status and escalation status from drill output |
| PO/BA | Keep stakeholder readiness visible while suppression policy codification remains a follow-up |

## Decision

The council accepts a tenant-safe calibration monitor for Product Readiness
Freshness response SLO drift alerts. The monitor checks routed alert paths after
the alert drill passes, validates that the trigger usage stays inside a watch
margin, confirms the alert is quiet rather than noisy, and verifies that it has
not crossed into escalation-required territory.

## Evidence

| Item | Evidence |
| --- | --- |
| Source module | `platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_alert_calibration.py` |
| Calibration report | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_drift_alert_calibration_monitored` |
| Dashboard panel | Product Readiness Freshness Response SLO Drift Alert Calibration |
| Current calibration status | `calibrated_with_watch` |
| Calibrated alerts | `1/1` |
| Noisy alerts | `0` |
| Next action | `codify_product_readiness_response_slo_drift_alert_suppression_policy` |

## Acceptance

- Calibration must pass only after the alert drill has passed.
- Watch-level alerts must remain above the watch threshold and below escalation.
- Noisy or under-threshold alerts must block Product Readiness.
- The next follow-up shifts from calibration monitoring to suppression policy codification.
