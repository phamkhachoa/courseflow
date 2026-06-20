# AI Platform Product Council 0008

Date: 2026-06-16

## Topic

Add grounded-answer gates for RAG before enabling LLM generation.

## Decision

Implement a deterministic grounded-answer baseline for LMS RAG Tutor and Support Agent Assist. The baseline answers only from tenant-allowed cited chunks and refuses when source evidence is missing or when the question asks for another tenant's private content.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Support RAG answer golden set | `platform/evaluation/datasets/support-rag-answer-golden.yaml` |
| Course RAG answer golden set | `platform/evaluation/datasets/course-rag-answer-golden.yaml` |
| Support RAG answer eval report | `platform/evaluation/reports/support-rag-answer-v1-eval.yaml` |
| Course RAG answer eval report | `platform/evaluation/reports/course-rag-answer-v1-eval.yaml` |
| Grounded-answer runner | `platform/src/courseflow_ai_platform/evaluation.py` |
| Evaluation tests | `platform/tests/test_evaluation.py` |

## Gate Metrics

| Metric | Purpose |
|---|---|
| Groundedness | Answer text must be supported by cited chunks |
| Answer relevance | Required answer terms must be present |
| Citation precision | Citations must point to expected source chunks |
| Refusal accuracy | Unsupported or cross-tenant-private questions must be refused |
| Hallucination rate | Unsupported generated claims must remain zero |
| Unsafe answer rate | Cross-tenant or should-refuse answers must remain zero |

## Product Impact

| Product | Use case | Gate |
|---|---|---|
| LMS CourseFlow | RAG Tutor | grounded answer, citation, refusal and tenant-private guardrail |
| Support Platform | Support Agent Assist | grounded answer, citation, refusal and HITL-ready answer safety |

## Next Actions

1. Completed via prompt safety, prompt audit and LLM adapter service packaging through Council 0060.
2. Connect live LLM provider credentials and rate limits to `llm-adapter-service`.
3. Harden prompt-gateway, LLM-adapter deployment and prompt/response audit persistence.
