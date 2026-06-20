# AI Platform Product Council 0042

Date: 2026-06-17

## Topic

Model serving access policy as data.

## Participants

- SA AI Platform: Policy-as-data and ownership validation owner
- SA AI Engineer: Principal resolver and adapter integration owner
- PO/BA: Product ownership visibility owner
- Governance Reviewer: Least-privilege grant review owner

## Decision

Add `platform/governance/policies/model-serving-access-policy.yaml` as the
policy-as-data source for hosted model serving access. The policy maps service
principals to product ownership, route scopes, tenant IDs and allowed model IDs.

`load_serving_access_policy()` resolves a registered principal into a
`ServingPrincipal` that can be passed directly to `ModelServingHostedAdapter`.
The loader validates that model grants reference known artifact manifests and
that non-platform principals only receive models owned by their product.

## Evidence

| Capability | Path |
|---|---|
| Access policy | `platform/governance/policies/model-serving-access-policy.yaml` |
| Policy loader/resolver | `platform/src/courseflow_ai_platform/model_serving_auth.py` |
| Adapter auth enforcement | `platform/src/courseflow_ai_platform/model_serving_adapter.py` |
| Policy tests | `platform/tests/test_model_serving_auth.py` |

## Registered Principals

| Principal | Product | Grants |
|---|---|---|
| `service:ai-platform-ops` | AI Platform | catalog + ops |
| `service:lms-courseflow-serving` | LMS CourseFlow | sequence-risk model in `tenant-lms` |
| `service:support-platform-serving` | Support Platform | support assist and SLA risk models in `tenant-support` |
| `service:finance-risk-serving` | Billing/Finance | document intelligence and payment fraud models in `tenant-finance` |
| `service:enterprise-operations-serving` | Enterprise Operations | demand forecast and routing simulator models in `tenant-ops` |

## Controls

- Model IDs must exist in artifact manifests.
- Product-scoped principals cannot receive models owned by another product.
- Requested JWT scopes must be a subset of registered policy scopes.
- Tenant and model allowlists remain enforced by the serving adapter.

## Product Impact

| Product | Impact |
|---|---|
| AI Platform | Serving access can be reviewed as governed data |
| LMS CourseFlow | LMS model serving grants are explicit and isolated |
| Support Platform | Support models share reusable grants without support-specific code |
| Billing/Finance | Sensitive model grants are inspectable by Governance Reviewer |
| Enterprise Operations | Forecasting and routing models use the same principal policy shape |

## Next Steps

1. Bind principal resolution to JWT claims in a real ingress.
2. Add change-request approval for edits to model-serving access policy.
3. Surface principal/model grants in the Admin/Ops governance dashboard.
