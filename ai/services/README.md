# AI Services

This folder contains runtime services owned by the AI Platform.

## Active Services

| Service | Responsibility | Status |
|---|---|---|
| `recommendation-ml-service` | Related-course recommendation training, model registry, activation governance, inference and telemetry | active baseline |
| `model-serving-service` | Shared AI Platform catalog, invocation, metrics, health and cockpit service boundary over manifest-backed model runtimes | service package ready |
| `retrieval-service` | Shared lexical, vector and hybrid retrieval service for LMS and Support Platform corpora with tenant isolation | service package ready |
| `rag-answer-service` | Shared grounded-answer service for LMS, Support and Enterprise Knowledge with citation, refusal, HITL and tenant/product/use-case gates | service package ready |
| `nlp-understanding-service` | Shared NLP understanding service for intent, semantic tags, retrieval-query shaping and rubric feedback with transformer upgrade path | service package ready |
| `governance-evaluation-service` | Shared governance, safety and evaluation gate service for release, promotion, HITL and evidence decisions across LMS and enterprise AI use cases | service package ready |
| `prompt-gateway-service` | Shared prompt redaction, tenant context filtering, budget and HITL guardrail service for GenAI/LLM/RAG adapters | service package ready |
| `llm-adapter-service` | Provider-neutral GenAI/LLM adapter that enforces Prompt Gateway, tenant/provider grants, provider ops policy and sanitized prompt audit before provider calls | service package ready |
| `media-intelligence-service` | Shared document OCR-token and speech transcript-segment intelligence service with media privacy controls, product/use-case/tenant policy and HITL metrics | service package ready |
| `sequence-risk-service` | Shared recurrent sequence-risk scoring service with pseudonymous subject hashes, tenant policy, HITL intervention flags and identifier rejection metrics | service package ready |
| `payment-fraud-service` | Shared finance payment fraud scoring service with pseudonymous account/counterparty/device hashes, tenant policy, HITL payment-action guardrails and entity-link metrics | service package ready |
| `graph-entity-service` | Shared entity-link evidence service with tenant policy, pseudonymous graph inputs, graph-review metrics and no automated adverse action | service package ready |
| `forecasting-service` | Shared demand forecasting and capacity planning service with tenant policy, capacity-action HITL guardrails and LMS/operations planning grants | service package ready |
| `routing-policy-service` | Shared constrained routing simulator service with tenant policy, bounded safe exploration, constraint-violation HITL guardrails and offline policy metrics | service package ready |
| `causal-uplift-service` | Shared aggregate experiment uplift service with tenant policy, direct-identifier rejection, guardrail/HITL rollout review and LMS/enterprise experimentation grants | service package ready |

## Planned Services

Create these only when contracts and quality gates are ready:

| Service | Responsibility |
|---|---|
| `semantic-embedding-service` | production embedding generation, ANN index build and course cold-start enrichment |
| `assessment-ai-service` | auto-grading, rubric feedback, human review |
| `model-ops-service` | shared registry and model audit workflows if they outgrow the model-serving and governance-evaluation service boundaries |

## Boundary Rule

Do not put every experiment into a service. Start under `use-cases`, `contracts`, `platform` and `model-families`; promote to a runtime service only when the product contract, data contract, evaluation gate and serving SLA are clear.
