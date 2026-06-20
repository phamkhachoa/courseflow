# AI Platform Product Council 0007

Date: 2026-06-16

## Topic

Create executable retrieval quality gates for RAG and semantic search before adding LLM answer generation.

## Decision

Add lexical retrieval baselines for both support knowledge and LMS course content. These are not the final embedding/vector implementation; they are deterministic gates that future embedding or hybrid retrievers must beat while preserving tenant isolation.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Support knowledge corpus | `platform/evaluation/corpora/support-knowledge-corpus.yaml` |
| Course content corpus | `platform/evaluation/corpora/course-content-corpus.yaml` |
| Support retrieval golden set | `platform/evaluation/datasets/support-knowledge-retrieval-golden.yaml` |
| Course retrieval golden set | `platform/evaluation/datasets/course-content-retrieval-golden.yaml` |
| Support retrieval eval report | `platform/evaluation/reports/support-knowledge-retrieval-v1-eval.yaml` |
| Course retrieval eval report | `platform/evaluation/reports/course-content-retrieval-v1-eval.yaml` |
| Shared lexical retrieval runner | `platform/src/courseflow_ai_platform/evaluation.py` |

## Gate Metrics

| Metric | Why it matters |
|---|---|
| Recall@K | Expected evidence must be retrievable |
| Hit-rate@K | Each query needs at least one useful citation |
| Citation precision@K | Retrieved context should not be mostly noise |
| Tenant isolation rate | Retrieval must not cross tenant boundaries |

## Product Impact

| Product | Use case | Gate |
|---|---|---|
| Support Platform | Support Agent Assist | support knowledge retrieval before LLM/RAG upgrade |
| LMS CourseFlow | RAG Tutor and semantic search | course content retrieval before answer generation |

## Next Actions

1. Add embedding index artifacts and compare embedding/hybrid retrieval against this lexical baseline.
2. Add embedding/hybrid retrieval artifacts and compare them against the lexical baseline.
3. Add prompt redaction and cost gates before enabling LLM-generated external responses.
