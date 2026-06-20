# AI Platform Product Council 0014

Date: 2026-06-16

## Topic

Add hybrid retrieval shadow gates for LMS and non-LMS RAG foundations.

## Decision

Introduce `hybrid_retrieval_shadow` as an executable evaluation runner. It compares lexical retrieval, deterministic vector retrieval and weighted hybrid retrieval on the same golden queries. A hybrid retriever can only pass if it preserves tenant isolation and is not worse than the lexical baseline on recall.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Vector search and hybrid rank primitives | `platform/src/courseflow_ai_platform/vector_index.py` |
| Hybrid evaluation runner | `platform/src/courseflow_ai_platform/evaluation.py` |
| Course hybrid dataset/report | `platform/evaluation/datasets/course-content-hybrid-retrieval-golden.yaml`, `platform/evaluation/reports/course-content-hybrid-retrieval-v1-eval.yaml` |
| Support hybrid dataset/report | `platform/evaluation/datasets/support-knowledge-hybrid-retrieval-golden.yaml`, `platform/evaluation/reports/support-knowledge-hybrid-retrieval-v1-eval.yaml` |
| Tests | `platform/tests/test_evaluation.py`, `platform/tests/test_vector_index.py` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| No lexical regression | Hybrid recall must be at least lexical recall for every golden set |
| Vector coverage | Vector retrieval recall is measured independently before combining |
| Tenant isolation | Hybrid results must preserve tenant/public visibility rules |
| Multi-domain reuse | Same runner validates LMS course content and Support knowledge corpora |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Shared shadow gate for future semantic/hybrid retrievers |
| LMS CourseFlow | RAG Tutor retrieval can evolve beyond lexical while preserving safety |
| Support Platform | Agent-assist retrieval can evolve beyond lexical while preserving public/tenant scope |
| Commerce/HRIS/Risk | Future catalog, skill and risk retrieval can reuse the no-regression gate |

## Next Actions

1. Replace deterministic hash vectors with a sentence-transformer or managed embedding adapter.
2. Add ANN/vector-store runtime and latency gates.
3. Persist retriever artifacts and add promotion manifests for shadow-to-candidate rollout.
