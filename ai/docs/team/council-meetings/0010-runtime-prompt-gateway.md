# AI Platform Product Council 0010

Date: 2026-06-16

## Topic

Promote prompt safety from evaluation-only logic to a reusable runtime gateway library.

## Decision

Create `courseflow_ai_platform.prompt_gateway` as the shared runtime wrapper that every future LLM/GenAI/RAG adapter should call before any model request. The evaluation runner now uses this same gateway implementation, preventing drift between tests and runtime behavior.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Runtime prompt gateway | `platform/src/courseflow_ai_platform/prompt_gateway.py` |
| Runtime gateway tests | `platform/tests/test_prompt_gateway.py` |
| Evaluator integration | `platform/src/courseflow_ai_platform/evaluation.py` |
| Public package exports | `platform/src/courseflow_ai_platform/__init__.py` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Prompt redaction | Emails, phone numbers, bearer/API tokens and raw learner/principal IDs are replaced before prompt/audit use |
| Tenant context filter | Only same-tenant or global context is included in the model prompt |
| Cost budget gate | Input, output and total estimated tokens are checked before model execution |
| HITL default | External auto-send is blocked and human review is required |
| Audit safety | Audit payloads are generated from sanitized values only |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Shared guardrail library for LLM/RAG adapters |
| LMS CourseFlow | RAG Tutor and grading prompts can be wrapped before model calls |
| Support Platform | Agent-assist draft generation can be kept HITL and tenant-safe |
| Billing/Finance | Reconciliation assistant prompts can be human-approved and secret-free |

## Next Actions

1. Completed in Council 0058: prompt gateway service now exposes the wrapper as a policy-enforced service package.
2. Add storage adapter for prompt/response audit records when hosted deployment is promoted.
3. Completed in Council 0059: LLM adapter shadow evaluation calls Prompt Gateway before generation.
