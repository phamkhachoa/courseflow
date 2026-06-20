# 0076 Graph Entity Service Package

Date: 2026-06-17

## Participants

| Role | Focus |
| --- | --- |
| SA AI Platform | Graph service boundary and runtime roadmap |
| SA AI Engineer | Entity-link adapter, contract tests and metrics |
| PO/BA | Finance graph-risk evidence and cross-product reuse |
| Governance Reviewer | Pseudonymous graph inputs and no automated adverse action |

## Decision

Promote graph/entity-link behavior from runtime-library evidence to a
service-integrated baseline through `graph-entity-service`.
The service reuses `finance-payment-fraud-baseline-v1` entity-link evidence for
graph-risk triage, while Payment Fraud Service remains the owner of payment risk
scoring and payment workflow guardrails.

## Scope

| Area | Decision |
| --- | --- |
| Product | `billing-finance` |
| Use case | `finance-payment-fraud-scoring` |
| Service route | `POST /v1/graph-entity/analyze` |
| Runtime | Deterministic entity-link evidence from payment fraud baseline |
| Access | Tenant, product, use-case and scope grants from `graph-entity-access-policy.yaml` |
| Privacy | Pseudonymous hashes only; direct account, counterparty, customer, user, device and contact identifiers are rejected |
| Safety | Graph evidence is review support only |
| Activation | Automated adverse action remains forbidden |

## Non-Scope

- No production graph database or graph embedding runtime.
- No automated payment hold, account restriction or access revocation.
- No raw account, counterparty, customer, employee, learner, device or contact
  identifiers.
- No identity-risk service activation in this slice.

## Evidence

| Artifact | Path |
| --- | --- |
| Service package | `services/graph-entity-service/service.yaml` |
| Platform runtime | `platform/src/courseflow_ai_platform/graph_entity_service.py` |
| Access policy | `platform/governance/policies/graph-entity-access-policy.yaml` |
| Contract tests | `services/graph-entity-service/tests/test_service_contract.py` |
| Platform tests | `platform/tests/test_graph_entity_service.py` |
| Model IO contract | `contracts/models/finance-payment-fraud-model-io.v1.yaml` |
| Evaluation report | `platform/evaluation/reports/finance-payment-fraud-v1-eval.yaml` |
| Coverage taxonomy | `platform/coverage/business-capability-coverage.yaml` |

## Acceptance

- The service enforces tenant, product, use-case and scope grants before
  analysis.
- Direct identity fields and raw hash-like values are rejected before model
  execution.
- Entity-link evidence, link strength counts and graph review flags are exposed
  in tenant-safe metrics.
- The runtime roadmap no longer counts graph/knowledge intelligence as a
  runtime-library gap.
- A real graph store, identity-risk contract and graph ML model remain separate
  roadmap items.
