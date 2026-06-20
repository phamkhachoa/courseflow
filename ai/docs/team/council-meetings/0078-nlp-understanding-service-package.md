# Council 0078: NLP Understanding Service Package

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The AI Platform now has an independently runnable NLP understanding service package. It provides a
shared baseline for intent classification, semantic tags, retrieval-query shaping and rubric
feedback while preserving a transformer adapter upgrade path behind the same policy controls.

This promotes NLP/transformer understanding from tooling to a service-integrated platform
capability. LMS CourseFlow, Support Platform and Enterprise Knowledge Assistant can reuse the same
service boundary instead of implementing product-specific language parsing.

The platform added:

- `platform/src/courseflow_ai_platform/nlp_understanding_service.py`
- `platform/governance/policies/nlp-understanding-access-policy.yaml`
- `platform/tests/test_nlp_understanding_service.py`
- `services/nlp-understanding-service/service.yaml`
- `services/nlp-understanding-service/src/courseflow_nlp_understanding_service/service.py`
- `services/nlp-understanding-service/src/courseflow_nlp_understanding_service/cli.py`
- `services/nlp-understanding-service/src/courseflow_nlp_understanding_service/http_server.py`
- `services/nlp-understanding-service/tests/test_service_contract.py`

## Service Contract

| Route | Scope | Purpose |
|---|---|---|
| `POST /v1/nlp-understanding/analyze` | `internal:ai-platform:nlp-understanding:analyze` | intent, semantic tag and rubric understanding |
| `GET /v1/nlp-understanding/health` | `internal:ai-platform:nlp-understanding:ops` | NLP understanding health |
| `GET /v1/nlp-understanding/metrics` | `internal:ai-platform:nlp-understanding:ops` | NLP understanding metrics |

## Current Consumers

| Consumer | Product | Principal |
|---|---|---|
| LMS semantic search and auto-grading | `lms-courseflow` | `service:lms-courseflow-nlp` |
| Support agent assist and speech QA | `support-platform` | `service:support-platform-nlp` |
| Enterprise Knowledge Assistant | `ai-platform` | `service:enterprise-knowledge-nlp` |

## Guardrails

- Route scopes are separate from model serving, retrieval, RAG answer and prompt gateway scopes.
- Principal grants are tenant, product and use-case scoped.
- Direct learner, customer, account, contact, user, email and phone identifiers are rejected.
- Rubric feedback, support assist and speech QA outputs require human review.
- Future transformer adapters must keep this service contract and policy boundary.

## Validation Evidence

| Check | Result |
|---|---|
| NLP understanding service contract tests | 6 passed |
| Platform NLP understanding runtime tests | 3 passed |
| Service lint | passed |
| Platform lint | passed |

## Next Step

Connect a trainable transformer or hosted embedding/classification adapter only after it passes the
same support-agent golden gate, tenant/privacy controls and service contract tests.
