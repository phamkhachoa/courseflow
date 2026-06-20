# 0074 Routing Policy Service Package

Date: 2026-06-17

## Participants

| Role | Focus |
| --- | --- |
| SA AI Platform | Platform service boundary, tenant policy and runtime roadmap |
| SA AI Engineer | Routing simulator adapter, contract tests and metrics |
| PO/BA | Enterprise Operations routing use case and release guardrails |
| Governance Reviewer | Identifier controls, HITL and online policy activation block |

## Decision

Promote `operations-routing-policy-simulator-v1` from a reusable runtime
library to a service-integrated baseline through `routing-policy-service`.
The service provides bounded queue recommendation for Enterprise Operations
while keeping the simulator behind a platform-managed policy boundary.

## Scope

| Area | Decision |
| --- | --- |
| Product | `enterprise-operations` |
| Use case | `operations-routing-optimization` |
| Service route | `POST /v1/routing-policy/recommend` |
| Runtime | Deterministic constrained routing simulator |
| Access | Tenant, product, use-case and scope grants from `routing-policy-access-policy.yaml` |
| Privacy | Reject direct agent, assignee, customer, learner and contact identifiers |
| Safety | Constraint violations require human review |
| Activation | Online policy activation remains forbidden |

## Non-Scope

- No online RL learner activation.
- No automated staffing, routing or customer-impacting action.
- No direct person identity, contact detail or raw customer profile input.
- No cross-tenant routing recommendation.

## Evidence

| Artifact | Path |
| --- | --- |
| Service package | `services/routing-policy-service/service.yaml` |
| Platform runtime | `platform/src/courseflow_ai_platform/routing_policy_service.py` |
| Access policy | `platform/governance/policies/routing-policy-access-policy.yaml` |
| Contract tests | `services/routing-policy-service/tests/test_service_contract.py` |
| Platform tests | `platform/tests/test_routing_policy_service.py` |
| Model IO contract | `contracts/models/operations-routing-policy-model-io.v1.yaml` |
| Evaluation report | `platform/evaluation/reports/operations-routing-policy-v1-eval.yaml` |
| Coverage taxonomy | `platform/coverage/business-capability-coverage.yaml` |
| AI capability taxonomy | `platform/coverage/ai-capability-taxonomy.yaml` |

## Acceptance

- The service enforces tenant, product, use-case and scope grants before
  recommendation.
- Direct identity fields are rejected before model execution.
- Constraint violations and unsafe exploration states are surfaced in metrics
  and kept under human review.
- The runtime roadmap no longer counts RL/bandit decisioning as a runtime gap.
- Online policy activation needs a separate shadow review, logged-policy
  dataset, counterfactual evaluation and governance approval.
