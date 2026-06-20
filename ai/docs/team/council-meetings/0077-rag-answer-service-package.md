# Council 0077: RAG Answer Service Package

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The AI Platform now has an independently runnable RAG answer service package. It composes the
retrieval runtime, citation enforcement, insufficient-context refusal and prompt gateway safety gate
behind one policy-enforced service boundary.

This promotes RAG from a vector-index shadow artifact to a service-integrated platform capability.
LMS CourseFlow is one consumer through `lms-rag-tutor`; Support Platform and Enterprise Knowledge
Assistant are separate non-LMS consumers using the same control surface.

The platform added:

- `platform/src/courseflow_ai_platform/rag_answer_service.py`
- `platform/governance/policies/rag-answer-access-policy.yaml`
- `platform/tests/test_rag_answer_service.py`
- `services/rag-answer-service/service.yaml`
- `services/rag-answer-service/src/courseflow_rag_answer_service/service.py`
- `services/rag-answer-service/src/courseflow_rag_answer_service/cli.py`
- `services/rag-answer-service/src/courseflow_rag_answer_service/http_server.py`
- `services/rag-answer-service/tests/test_service_contract.py`

## Service Contract

| Route | Scope | Purpose |
|---|---|---|
| `POST /v1/rag-answer/answer` | `internal:ai-platform:rag-answer:answer` | grounded answer with required citations |
| `GET /v1/rag-answer/health` | `internal:ai-platform:rag-answer:ops` | RAG answer health |
| `GET /v1/rag-answer/metrics` | `internal:ai-platform:rag-answer:ops` | RAG answer metrics |

## Current Consumers

| Consumer | Product | Collection | Principal |
|---|---|---|---|
| RAG AI Tutor | `lms-courseflow` | `course_content_chunks` | `service:lms-courseflow-rag-answer` |
| Support Agent Assist | `support-platform` | `support_knowledge_articles` | `service:support-platform-rag-answer` |
| Enterprise Knowledge Assistant | `ai-platform` | course and support collections | `service:enterprise-knowledge-rag-answer` |

## Guardrails

- Route scopes are separate from retrieval and prompt gateway scopes.
- Principal grants are tenant, product, use-case and collection scoped.
- Citations are required for grounded answers.
- Insufficient retrieval confidence must return a refusal instead of a synthesized answer.
- Direct learner, customer, account, contact and user identifiers are rejected.
- External auto-send is forbidden.
- Baseline answers require human review.
- Cross-tenant/private asks must not be answered without matching evidence.

## Validation Evidence

| Check | Result |
|---|---|
| RAG answer service contract tests | 6 passed |
| Platform RAG answer runtime tests | 3 passed |
| Service lint | passed |
| Platform lint | passed |

## Next Step

Connect `rag-answer-service` to the approved LLM adapter only after provider credential, runtime
probe and budget gates remain green. The deterministic grounded-answer baseline remains the
promotion gate for citations, refusal accuracy and tenant isolation.
