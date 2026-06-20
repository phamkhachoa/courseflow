# AI Platform Product Council 0013

Date: 2026-06-16

## Topic

Add an executable vector-index contract pipeline for both LMS and non-LMS RAG foundations.

## Decision

Create a deterministic, dependency-free vector index builder as the first platform contract for embedding artifacts. This is not the final semantic embedding model. It is a stable baseline that proves chunk coverage, embedding dimensions, metadata, checksum stability and tenant scope before future sentence-transformer, ANN or hybrid retrievers are promoted.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Vector index runtime module | `platform/src/courseflow_ai_platform/vector_index.py` |
| Vector index unit tests | `platform/tests/test_vector_index.py` |
| Course vector-index dataset/report | `platform/evaluation/datasets/course-content-vector-index-golden.yaml`, `platform/evaluation/reports/course-content-vector-index-v1-eval.yaml` |
| Support vector-index dataset/report | `platform/evaluation/datasets/support-knowledge-vector-index-golden.yaml`, `platform/evaluation/reports/support-knowledge-vector-index-v1-eval.yaml` |
| Evaluation registry runner | `platform/evaluation/registry.yaml`, `platform/src/courseflow_ai_platform/evaluation.py` |
| Capability registry update | `platform/capabilities/registry.yaml` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Deterministic artifact | Rebuilding the same corpus/schema produces the same checksum |
| Full chunk coverage | Every governed corpus chunk must appear in the index |
| Dimension conformance | Every vector must match the collection schema dimensions |
| Metadata conformance | Tenant, source, access scope, PII class and text hash are required |
| Tenant scope coverage | Index entries must retain tenant/public scope for retrieval guardrails |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Shared vector artifact contract before production embedding services |
| LMS CourseFlow | Course semantic search/RAG Tutor gets an executable index gate |
| Support Platform | Agent-assist and support RAG get a reusable non-LMS index gate |
| Commerce/HRIS/Risk | Future catalog, skill and risk knowledge indexes can reuse the same contract |

## Next Actions

1. Add a sentence-transformer or managed embedding adapter that must beat this contract baseline.
2. Add ANN/vector-store persistence and promotion manifests for persisted index artifacts.
3. Add hybrid retrieval shadow evaluation against both lexical and vector contract baselines.
