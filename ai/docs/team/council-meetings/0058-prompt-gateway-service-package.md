# Council 0058: Prompt Gateway Service Package

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Package the runtime prompt safety gateway as an independent AI Platform service.
This turns GenAI/LLM/RAG guardrails into a reusable service boundary instead of a
library that each product must embed.

## Service Contract

| Route | Scope | Purpose |
| --- | --- | --- |
| `POST /v1/prompt-gateway/evaluate` | `internal:ai-platform:prompt-gateway:evaluate` | redact prompt text, filter tenant context, enforce budget and HITL gates |
| `GET /v1/prompt-gateway/health` | `internal:ai-platform:prompt-gateway:ops` | expose package health |
| `GET /v1/prompt-gateway/metrics` | `internal:ai-platform:prompt-gateway:ops` | expose request, allowed, blocked, error and HITL counters |

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Service package | `services/prompt-gateway-service` |
| Service manifest | `services/prompt-gateway-service/service.yaml` |
| Runtime module | `platform/src/courseflow_ai_platform/prompt_gateway_service.py` |
| Access policy | `platform/governance/policies/prompt-gateway-access-policy.yaml` |
| Contract tests | `services/prompt-gateway-service/tests/test_service_contract.py` |

## Guardrails

- Principals are scoped by product, use case and tenant.
- Cross-tenant retrieved context is filtered before prompt assembly.
- External auto-send remains blocked by default.
- Human review is required for high-impact outputs.
- Sanitized audit payloads must remain free of emails, phone numbers, secrets and raw identifiers.

## Product Impact

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | RAG Tutor and auto-grading prompts use the same safety gateway |
| Support Platform | Agent-assist prompts are tenant-safe and HITL-bound |
| Billing/Finance | Reconciliation/document prompts are blocked from auto-send |
| AI Platform | Admin/Ops has health and metrics routes for prompt safety |

## Next Step

Completed in Council 0059: Prompt Gateway is now connected to LLM adapter
shadow evaluation.

Completed in Council 0060: the provider-neutral LLM adapter is now packaged as
an independent service boundary.

Next harden deployment alongside model-serving and retrieval service packages,
then connect live provider credentials and rate limits to the adapter.
