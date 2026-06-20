# Council 0060: LLM Adapter Service Package

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Package the provider-neutral LLM adapter as an independent AI Platform service.
Product teams must call this boundary instead of calling external LLM providers
directly. The service resolves product/use-case/tenant/provider grants, calls
Prompt Gateway before provider generation, skips provider calls when the gateway
blocks and records sanitized prompt audit evidence.

## Service Contract

| Route | Scope | Purpose |
| --- | --- | --- |
| `POST /v1/llm-adapter/generate` | `internal:ai-platform:llm-adapter:generate` | prompt-gateway-bound generation |
| `GET /v1/llm-adapter/health` | `internal:ai-platform:llm-adapter:ops` | adapter health |
| `GET /v1/llm-adapter/metrics` | `internal:ai-platform:llm-adapter:ops` | request, blocked, provider-call and audit counters |

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Service package | `services/llm-adapter-service` |
| Service manifest | `services/llm-adapter-service/service.yaml` |
| Runtime module | `platform/src/courseflow_ai_platform/llm_provider_adapter.py` |
| Access policy | `platform/governance/policies/llm-adapter-access-policy.yaml` |
| Provider ops policy | `platform/governance/policies/llm-provider-ops-policy.yaml` |
| Contract tests | `services/llm-adapter-service/tests/test_service_contract.py` |
| Platform tests | `platform/tests/test_llm_provider_adapter.py` |
| Shadow gate | `platform/evaluation/reports/llm-adapter-shadow-gateway-v1-eval.yaml` |

## Guardrails

- Provider access is scoped by product, use case, tenant and provider ID.
- Product principals are mapped to Prompt Gateway principals before generation.
- Prompt Gateway denial must skip provider calls.
- The current provider is a CI-safe contract stub with network disabled.
- Sanitized prompt audit records must not retain raw PII or secrets.

## Product Impact

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | RAG Tutor and auto-grading can use one governed generation boundary |
| Support Platform | Agent assist gets cited answers and skips unsafe prompts |
| Billing/Finance | Reconciliation/document assistants inherit provider and HITL controls |
| AI Platform | Admin/Ops has health, metrics and provider-policy evidence |

## Next Step

Completed in Council 0061: provider rate limits, timeout policy, circuit-breaker
thresholds and failover providers are now governed in `llm-provider-ops-policy.yaml`.

Next connect live provider credentials and deployment hardening while keeping
Prompt Gateway mandatory before every provider call.
