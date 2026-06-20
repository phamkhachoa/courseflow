# AI Platform Product Council 0012

Date: 2026-06-16

## Topic

Add persisted storage behavior for prompt/response audit evidence.

## Decision

Keep the in-memory `PromptAuditLedger` for tests and local development, and add `JsonlPromptAuditStore` as the first persisted adapter. The adapter writes one sanitized audit event per line, reloads records across process boundaries, supports tenant export/delete and retention purge, and rejects audit payloads that still contain unredacted sensitive values.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Runtime audit storage adapter | `platform/src/courseflow_ai_platform/prompt_audit.py` |
| Persistence and safety tests | `platform/tests/test_prompt_audit.py` |
| Capability registry update | `platform/capabilities/registry.yaml` |
| Prompt safety next-step update | `platform/evaluation/reports/prompt-safety-v1-eval.yaml` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Persisted evidence | Audit events can be appended to and loaded from JSONL |
| Secret-safe write path | Adapter rejects unredacted email, phone, secret, bearer token and raw identifier values |
| Tenant export | Tenant records can be exported from persisted audit storage |
| Tenant deletion | Tenant records can be removed by rewriting the JSONL store |
| Retention purge | Expired records can be purged from persisted audit storage |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | First persisted prompt audit adapter for hosted gateway migration |
| LMS CourseFlow | Tutor and grading prompts can keep auditable evidence without raw learner PII |
| Support Platform | Agent-assist prompt/response evidence can survive service restarts |
| Billing/Finance | Assistant workflows have a safe path for approval and incident evidence |

## Next Actions

1. Add DB/object-storage prompt audit adapter for high-volume production traffic.
2. Add Admin/Ops export and deletion UI on top of the audit store interface.
3. Record prompt audit events during LLM adapter shadow evaluation.
