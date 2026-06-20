# AI Platform Product Council 0009

Date: 2026-06-16

## Topic

Add a platform-level prompt safety gateway before any LLM/RAG adapter is allowed to run.

## Decision

Register `platform-llm-safety-gateway` as an AI Platform use case and add an executable prompt safety gate. The gate redacts PII and secrets, filters cross-tenant context, checks cost budgets, keeps audit payloads secret-free and requires human review for external or high-impact outputs.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Prompt envelope contract | `contracts/prompts/llm-prompt-envelope.v1.yaml` |
| Redaction policy | `platform/prompt-safety/redaction-policy.yaml` |
| Prompt safety golden set | `platform/evaluation/datasets/prompt-safety-golden.yaml` |
| Prompt safety eval report | `platform/evaluation/reports/prompt-safety-v1-eval.yaml` |
| Prompt safety evaluator | `platform/src/courseflow_ai_platform/evaluation.py` |
| Evaluation tests | `platform/tests/test_evaluation.py` |

## Gate Metrics

| Metric | Purpose |
|---|---|
| PII redaction recall | Raw email, phone and identifiers must not reach prompts or audit payloads |
| Secret redaction recall | API keys, bearer tokens and token assignments must be removed |
| Expected token coverage | Required redaction tokens must appear after sanitization |
| Tenant context pass rate | Only same-tenant or global context can be included |
| Cost budget pass rate | Estimated prompt and output tokens must fit the budget |
| Audit safety rate | Audit evidence must not contain raw sensitive values |
| Human review rate | External/high-impact outputs must remain human-reviewed by default |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Shared safety gate for all LLM/GenAI/RAG use cases |
| LMS CourseFlow | Tutor/grading prompts cannot leak learner PII or cross-tenant content |
| Support Platform | Agent-assist drafts stay HITL and secret-free |
| Billing/Finance | Reconciliation assistant prompts stay human-approved and token-safe |

## Next Actions

1. Completed via runtime library in Council 0010 and policy-enforced service package in Council 0058.
2. Generate eval reports from runner output instead of hand-authored report files.
3. Completed in Council 0059: LLM adapter shadow evaluation now calls Prompt Gateway before generation.
