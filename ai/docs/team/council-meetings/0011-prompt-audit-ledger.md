# AI Platform Product Council 0011

Date: 2026-06-16

## Topic

Add prompt/response audit evidence with retention, export and deletion behavior.

## Decision

Create `courseflow_ai_platform.prompt_audit` as the runtime audit abstraction for prompt gateway outputs. It stores sanitized audit payloads, hashes sanitized prompt/response text, supports tenant export and deletion, and purges records by retention expiry.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Prompt audit event contract | `contracts/prompts/prompt-audit-event.v1.yaml` |
| Runtime audit ledger | `platform/src/courseflow_ai_platform/prompt_audit.py` |
| Audit ledger tests | `platform/tests/test_prompt_audit.py` |
| Governance policy update | `platform/governance/policies/ai-governance-policy.yaml` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| No raw sensitive audit payload | Audit payloads are generated from sanitized prompt/response text |
| Immutable evidence hash | Sanitized prompt and response are represented by SHA-256 hashes |
| Tenant export | Audit records can be exported by tenant for access/export workflows |
| Tenant deletion | Prompt audit records can be deleted by tenant for deletion workflows |
| Retention purge | Records expire according to bounded retention windows |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Shared evidence trail for LLM/RAG calls |
| LMS CourseFlow | Tutor/grading prompts can be audited without raw learner PII |
| Support Platform | Agent-assist drafts can be audited while keeping secrets out of logs |
| Billing/Finance | Reconciliation assistant prompts can retain approval evidence safely |

## Next Actions

1. Replace the in-memory ledger with a storage adapter when a hosted gateway exists.
2. Add prompt/response audit event export to Admin/Ops UI.
3. Add LLM adapter shadow evaluation that records audit events for every model call.
