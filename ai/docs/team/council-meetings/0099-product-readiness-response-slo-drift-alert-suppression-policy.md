# Council 0099 - Product Readiness Response SLO Drift Alert Suppression Policy

Date: 2026-06-17
Product: Enterprise AI Platform

## Roles

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Promote response SLO drift alert suppression policy into Product Readiness evidence |
| SA AI Engineer | Codify dedupe, cooldown and escalation-preservation rules from calibrated alert evidence |
| PO/BA | Keep stakeholder readiness visible while suppression policy drill remains a follow-up |

## Decision

The council accepts a tenant-safe suppression policy for Product Readiness
Freshness response SLO drift alerts. The policy activates only after calibration
passes, suppresses under-threshold noise, deduplicates watch-level alert repeats,
applies a cooldown window and preserves escalation when trigger usage reaches the
escalation floor.

## Evidence

| Item | Evidence |
| --- | --- |
| Source module | `platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_alert_suppression_policy.py` |
| Policy report | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_drift_alert_suppression_policy_codified` |
| Dashboard panel | Product Readiness Freshness Response SLO Drift Alert Suppression Policy |
| Current policy status | `suppression_policy_codified` |
| Active rules | `1/1` |
| Dedupe/cooldown | `30m` dedupe and `60m` cooldown |
| Escalation floor | `100%` SLO usage |
| Next action | `exercise_product_readiness_response_slo_drift_suppression_policy_drill` |

## Acceptance

- The policy must activate only after calibration is `calibrated_with_watch`.
- Under-threshold alerts must be suppressed rather than routed.
- Watch-level repeats must dedupe and cool down before re-notifying Admin/Ops.
- Escalation must be preserved at or above the escalation floor.
- The next follow-up shifts from policy codification to a suppression policy drill.
