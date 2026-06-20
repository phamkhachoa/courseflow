# Council 0103 - Product Readiness Response SLO Drift Suppression Policy Coverage Regression

Date: 2026-06-17
Product: Enterprise AI Platform

## Roles

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Monitor Product Readiness suppression policy coverage for regression |
| SA AI Engineer | Guard scenario coverage, active watch policy, explicit exclusions and tenant safety |
| PO/BA | Move the follow-up from regression monitoring to an owner-facing coverage SLO |

## Decision

The council accepts regression monitoring for the Product Readiness Freshness
response SLO drift suppression policy coverage matrix. The monitor checks that
coverage remains expanded, every scenario class stays covered, the watch-level
route outage scenario keeps active policy and effective signal coverage, the
within-SLO scenarios remain explicit non-watch exclusions and the artifact stays
tenant-safe.

## Evidence

| Item | Evidence |
| --- | --- |
| Source module | `platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression.py` |
| Regression report | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_monitored` |
| Dashboard panel | Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Regression |
| Current regression status | `regression_monitored` |
| Regression checks | `7/7` passed |
| Coverage baseline | `5/5` scenario classes and `100%` coverage |
| Tenant safety | `0` raw identifier markers |
| Next action | `publish_product_readiness_response_slo_drift_suppression_policy_coverage_slo` |

## Acceptance

- Coverage status must remain `coverage_expanded`.
- Scenario class count and coverage percentage must stay at or above baseline.
- Active watch policy and effective signal coverage must not regress.
- Explicit non-watch exclusions must remain present for within-SLO scenarios.
- The report must remain tenant-safe with zero raw identifier markers.
- Product Readiness must promote the regression monitor into a required gate and
  move the follow-up to publishing a coverage SLO.
