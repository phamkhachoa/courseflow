# Council 0111 - Enterprise adoption SLO release governance

Date: 2026-06-17

Attendees:
- SA AI Platform
- SA AI Engineer
- PO/BA AI Platform
- Admin/Ops
- Governance Reviewer

## Decision

Attach the enterprise release gate pattern adoption SLO to release governance so cross-product AI use-case promotion is blocked when adoption SLO evidence drifts.

## Evidence

| Item | Value |
|---|---|
| Source module | `platform/src/courseflow_ai_platform/product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance.py` |
| Source report | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml` |
| Upstream SLO | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml` |
| Product gate | `product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_attached` |
| Current status | `enterprise_adoption_slo_release_governance_attached` |
| Release gates | 5/5 attached |
| Tenant safety | true, raw identifier count 0 |
| Next action | `exercise_enterprise_release_gate_pattern_adoption_slo_release_governance_drill` |

## Acceptance

- Enterprise adoption SLO status must be `adoption_slo_published`.
- Release governance status must be `enterprise_adoption_slo_release_governance_attached`.
- Release governance must attach 5/5 gates for SLO publication, objective health, enterprise span, owner cadence and tenant safety.
- Product Readiness must show 29/29 required gates passed.
- Admin/Ops dashboard freshness must show 26/26 source snapshots current.
