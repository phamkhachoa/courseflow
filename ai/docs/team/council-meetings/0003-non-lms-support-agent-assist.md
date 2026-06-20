# AI Platform Product Council 0003

Date: 2026-06-16

## Topic

Prove Enterprise AI Platform reuse outside LMS with `support-agent-assist`.

## Decision

The first non-LMS implementation slice is Support Agent Assist. It starts with a deterministic baseline to prove platform lifecycle reuse before adding LLM/RAG dependencies.

## Why Support

- Enterprise support is a natural AI platform customer.
- It exercises LLM/RAG/HITL governance patterns.
- It needs tenant isolation, audit and safe human review.
- It can reuse model cards, evaluation reports, artifact manifests and registry validation.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Support product onboarding | `products/support-platform/README.md` |
| Use case definition | `use-cases/support-agent-assist/README.md` |
| Feature contract | `contracts/features/support-case-features.v1.yaml` |
| Model IO contract | `contracts/models/support-agent-assist-model-io.v1.yaml` |
| Baseline model code | `models/llm/support_agent_assist/support_agent_assist.py` |
| Baseline tests | `models/llm/support_agent_assist/tests/test_support_agent_assist.py` |
| Model card | `platform/model-registry/model-cards/support-agent-assist-baseline-v1.md` |
| Evaluation report | `platform/evaluation/reports/support-agent-assist-baseline-v1-eval.yaml` |
| Artifact manifest | `platform/artifacts/manifests/support-agent-assist-baseline-v1.yaml` |

## Governance Notes

- The baseline never sends external replies.
- `requires_human_review` is always true.
- Tenant ID and case ID are mandatory.
- LLM/RAG promotion requires golden dataset, prompt redaction tests, citation quality and cost budget gates.

## Next Actions

1. Add golden support dataset for intent and draft quality.
2. Add support knowledge vector index fixture.
3. Add prompt redaction tests before any LLM adapter.
4. Add a shared evaluation runner so support and LMS use cases use the same gate engine.

