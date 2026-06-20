# Council 0100 - Product Readiness Response SLO Drift Suppression Policy Drill

Date: 2026-06-17
Product: Enterprise AI Platform

## Roles

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Move Product Readiness suppression policy from codified to exercised evidence |
| SA AI Engineer | Replay under-threshold, dedupe, cooldown and escalation-preservation decisions |
| PO/BA | Replace the drill follow-up with an effectiveness monitoring follow-up |

## Decision

The council accepts the Product Readiness Freshness response SLO drift
suppression policy drill as passed. The drill exercises every active policy rule
across four required cases: under-threshold suppression, dedupe-window
suppression, cooldown-window suppression and escalation preservation at the
configured escalation floor.

## Evidence

| Item | Evidence |
| --- | --- |
| Source module | `platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_drill.py` |
| Drill report | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_drift_suppression_policy_drill_passed` |
| Dashboard panel | Product Readiness Freshness Response SLO Drift Suppression Policy Drill |
| Current drill status | `passed` |
| Scenarios | `4/4` passed |
| Suppressed decisions | `3` under-threshold, dedupe and cooldown replays |
| Escalation preserved | `1` routed escalation replay |
| Next action | `monitor_product_readiness_response_slo_drift_suppression_policy_effectiveness` |

## Acceptance

- Every active suppression policy rule must produce four drill scenarios.
- Under-threshold, dedupe-window and cooldown-window replays must not route an
  Admin/Ops action.
- Escalation replay must route to Admin/Ops and preserve the configured action
  at or above the escalation floor.
- The report must remain tenant-safe with zero raw identifier markers.
- Product Readiness must promote the drill into a required gate and move the
  follow-up to policy effectiveness monitoring.
