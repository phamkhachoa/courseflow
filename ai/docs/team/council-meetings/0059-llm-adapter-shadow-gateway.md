# Council 0059: LLM Adapter Shadow Gateway

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Connect Prompt Gateway to LLM adapter shadow evaluation before any external
provider adapter is promoted. This makes the pre-generation safety boundary an
executable gate: product adapters must resolve a prompt-gateway principal,
evaluate the prompt, skip generation when blocked and only generate grounded
answers from tenant-safe context when allowed.

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Shadow dataset | `platform/evaluation/datasets/llm-adapter-shadow-gateway-golden.yaml` |
| Evaluation report | `platform/evaluation/reports/llm-adapter-shadow-gateway-v1-eval.yaml` |
| Evaluation runner | `platform/src/courseflow_ai_platform/evaluation.py` |
| Access policy | `platform/governance/policies/prompt-gateway-access-policy.yaml` |
| Platform tests | `platform/tests/test_evaluation.py` |

## Gate Metrics

| Metric | Required |
| --- | --- |
| Prompt Gateway expected pass rate | `1.00` |
| Allowed generation rate | `1.00` |
| Blocked generation skip rate | `1.00` |
| Groundedness | `1.00` |
| Citation precision | `1.00` |
| Refusal accuracy | `1.00` |
| Audit safety rate | `1.00` |
| Context filter pass rate | `1.00` |

## Product Impact

| Product | Reuse |
| --- | --- |
| AI Platform | Reusable pre-call shadow gate for all LLM/RAG adapters |
| LMS CourseFlow | RAG Tutor adapter must pass gateway before generated tutor answers |
| Support Platform | Agent-assist adapter skips generation when gateway blocks unsafe prompts |
| Billing/Finance | Future reconciliation/document adapters inherit the same pre-call contract |

## Next Step

Completed in Council 0060: the same contract is now packaged as
`llm-adapter-service` with provider-scoped policy, Prompt Gateway pre-call checks,
provider-call skip on blocked prompts and sanitized prompt audit records.

Next connect live provider credentials, rate limits, failover and deployment
hardening without weakening the Prompt Gateway gate.
