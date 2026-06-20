# Council 0056: Retrieval Service Package

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The AI Platform now has an independently runnable retrieval service package. It exposes LMS course content and Support Platform knowledge through one policy-enforced service boundary, proving retrieval/RAG is a shared platform capability rather than an LMS-only feature.

The platform added:

- `platform/src/courseflow_ai_platform/retrieval_service.py`
- `platform/governance/policies/retrieval-access-policy.yaml`
- `platform/tests/test_retrieval_service.py`
- `services/retrieval-service/service.yaml`
- `services/retrieval-service/src/courseflow_retrieval_service/service.py`
- `services/retrieval-service/src/courseflow_retrieval_service/cli.py`
- `services/retrieval-service/src/courseflow_retrieval_service/http_server.py`
- `services/retrieval-service/tests/test_service_contract.py`

## Service Contract

| Route | Scope | Purpose |
|---|---|---|
| `GET /v1/retrieval/collections` | `internal:ai-platform:retrieval:catalog` | collection catalog |
| `POST /v1/retrieval/search` | `internal:ai-platform:retrieval:search` | lexical/vector/hybrid search |
| `GET /v1/retrieval/health` | `internal:ai-platform:retrieval:ops` | retrieval health |
| `GET /v1/retrieval/metrics` | `internal:ai-platform:retrieval:ops` | retrieval metrics |

## Current Collections

| Collection | Product | Evidence |
|---|---|---|
| `course_content_chunks` | LMS CourseFlow | course corpus, collection schema, vector-index artifact and hybrid retrieval gate |
| `support_knowledge_articles` | Support Platform | support corpus, collection schema, vector-index artifact and hybrid retrieval gate |

## Guardrails

- Route scopes are separate from model-serving scopes.
- Principal grants are collection and tenant scoped.
- Tenant-private chunks cannot be returned to another tenant.
- Hybrid search reuses the vector-index artifact and lexical/vector ranking gates.
- The service remains `service_package_ready`; production ANN backend and deployment gates are still pending.

## Validation Evidence

| Check | Result |
|---|---|
| Retrieval service contract tests | 6 passed |
| Platform retrieval runtime tests | 3 passed |
| Service lint | passed |
| Platform lint | passed |

## Next Step

Completed in Council 0058: prompt gateway is now packaged as its own policy-enforced AI Platform service.

Completed in Council 0059: Prompt Gateway is connected to LLM adapter shadow evaluation.

Completed in Council 0060: the provider-neutral LLM adapter is packaged as an independent service boundary.

Next harden model-serving, retrieval, prompt-gateway and LLM-adapter deployment gates, then connect live provider credentials and rate limits.
