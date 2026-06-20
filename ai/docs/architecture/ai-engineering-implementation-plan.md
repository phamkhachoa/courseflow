# AI Engineering Implementation Plan

This plan turns the enterprise direction into an implementation path without breaking the existing recommendation contract.

## Compatibility Rule

Keep all current `/internal/recommendation-ml/...` endpoints and response shapes stable until backend consumers move. New AI capabilities may add sibling services, but they must not break `analytics-service`, gateway routes or the existing recommendation database.

P0 compatibility commitments:

- Preserve existing recommendation endpoints, response fields, reason codes and statuses.
- Preserve existing database tables and Prometheus metrics.
- Keep tenant rollout additive: existing backend calls can continue without immediate contract break, while new model contracts are tenant-aware.
- Keep Docker, compose, workflow and smoke scripts aligned to the canonical path `ai/services/recommendation-ml-service`.

## Package Boundaries

| Boundary | Responsibility | Near-term action |
|---|---|---|
| `services/recommendation-ml-service` | Runtime compatibility for recommendation | Keep existing API, add model-family adapters only inside recommendation |
| `models/` | Model archetype code | Add train/predict/evaluate skeletons per family before runtime service |
| `features/` | Offline/online feature store direction | Add fixtures and materialization contracts |
| `pipelines/` | Train/eval/scoring workflows | Add executable eval runner before new service |
| `platform/` | Lifecycle, governance, quality, vector/registry conventions | Keep as shared contracts/policies first |
| `contracts/` | Feature and model IO contracts | Treat as change-controlled API |

## Model Archetype Roadmap

| Step | Archetype | Why | Dependencies |
|---|---|---|---|
| 1 | `models/embeddings/course_semantic_search` | Highest ROI, unlocks cold-start and RAG | course content, vector collection |
| 2 | `models/deep_learning/sequence_risk_baseline` | Sequence-risk runtime contract gate before trainable DL | learner activity, gradebook |
| 3 | `models/llm/auto_grading` | LLM + HITL + rubric audit | submissions, rubrics |
| 4 | `models/classical/related_courses_als_bpr` | First parameterized recommender beyond item-CF | recsys interactions |
| 5 | `models/deep-learning/sequential_recommender` | Trainable DL upgrade for recommendation | sequences, GPU optional |
| 6 | `models/llm/rag_tutor` | Product-visible AI Mentor experience | embeddings, retrieval eval |
| 7 | `models/deep-learning/knowledge_tracing` | Advanced EdTech AI | skill-level attempts |
| 8 | `models/bandit-rl/next_best_learning_action` | Adaptive path learning | policy simulator, safety gates |

## Dependency Strategy

Do not load every AI dependency into the active recommendation service.

Use optional extras by model family. The current recommendation service keeps only API, DB, security and telemetry dependencies in the base install; model-family dependencies are opt-in:

```toml
[project.optional-dependencies]
classical = ["numpy", "scikit-learn", "scipy"]
embeddings = ["sentence-transformers", "faiss-cpu"]
dl = ["torch"]
llm = ["openai", "instructor"]
eval = ["ragas", "deepeval"]
dev = ["pytest", "ruff", "mypy"]
```

GPU-heavy and LLM-heavy dependencies should stay out of the baseline service image until a runtime service needs them.

## Migration Strategy

1. Keep current recommendation DB tables.
2. Add generic registry tables only after a second model service needs them.
3. Mirror recommendation model metadata into generic registry rather than rename/drop tables.
4. Add artifact manifest table or file only when a model produces external artifacts.
5. Preserve old metrics while adding generic `courseflow_ai_platform_*` metrics.
6. Add `dataset_snapshot_id`, feature contract version and manifest hash to future training requests.
7. Move long-running production training from HTTP event payloads to DP Gold/offline feature snapshots while keeping the current enqueue endpoint as compatibility path.

## Test And Gate Strategy

| Test type | Purpose | First files to add |
|---|---|---|
| Contract tests | Protect current recommendation API | existing `tests/test_service_contract.py` |
| Model archetype tests | Ensure train/predict/evaluate contract | `tests/archetypes/*` later |
| Evaluation tests | Prove gates executable | `pipelines/evaluation/*` |
| Security tests | JWT, scope, PII, prompt redaction | service and LLM tests |
| Integration tests | DB, vector index, registry, activation | per service |
| Load tests | p95 latency and fallback | serving stage |
| CI path tests | Prove AI service gates run from canonical `ai/services` path | product-hardening workflow |
| Tenant isolation tests | Prevent cross-tenant retrieval/recommendation/prompt context | model and service tests |
| Artifact manifest tests | Verify checksum, dependency lock, dataset snapshot and model card links | registry/eval tests |
| Prompt safety tests | Redaction, citation, refusal and cost budget | LLM/RAG tests |

## Current Implementation Slice

The first deep-learning shaped runtime is `models/deep_learning/sequence_risk_baseline`.
It is a deterministic recurrent scorer with model IO contract, artifact
manifest, model card and golden evaluation. It proves the lifecycle path for
learner sequence risk, but it is not yet a trained PyTorch or ONNX model.

## Next Implementation Slice

Build semantic search as the next platform capability:

1. Add synthetic course content fixtures.
2. Add chunking and embedding contract test.
3. Add vector index artifact manifest.
4. Add offline relevance eval.
5. Add model card and quality gate evidence.
6. Add service only after the above is green.

Why next: it addresses the expert's high-ROI retrieval recommendation, fixes
cold-start, and creates foundation for RAG Tutor and hybrid recommendation.
