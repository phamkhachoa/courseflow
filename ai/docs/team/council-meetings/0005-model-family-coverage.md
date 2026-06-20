# AI Platform Product Council 0005

Date: 2026-06-16

## Topic

Turn the expert recommendation from "classical ML -> deep learning -> NLP/transformers -> GenAI/LLM -> RAG -> optional CV/speech -> RL" into an enforceable AI Platform taxonomy.

## Council Roles

| Role | Decision lens |
|---|---|
| PO/BA | Which family creates measurable product value and where it appears in the use-case portfolio |
| SA AI Platform | Whether the family belongs in reusable platform capability rather than one LMS module |
| SA AI Engineer | Whether the family has a baseline path, evaluation gate and migration path |
| Governance Reviewer | Whether privacy, HITL, rollback and audit gates are explicit |

## Decision

Create `model-families/registry.yaml` as the source of truth for supported AI families and make `platform/src/courseflow_ai_platform/registry.py` validate every `model_family` reference in `use-cases/registry.yaml`.

## Coverage

| Spectrum | Platform decision |
|---|---|
| Classical ML | Required baseline for tabular risk, anomaly and recommendation quality gates |
| Deep learning | Planned for sequence behavior, ranking and representation learning after data gates |
| NLP/transformers | Required for semantic search, classification, summarization and knowledge tracing |
| GenAI/LLM | Supported with model cards, evaluation, HITL and deterministic baselines |
| RAG | Supported through vector collection contracts, retrieval evaluation and grounded answers |
| CV and speech | Optional capabilities that require privacy review before media processing |
| RL/bandits | Supported only behind simulator/offline policy evaluation gates |
| Extra enterprise AI | Graph ML, knowledge graph, forecasting, causal inference and simulation added for non-LMS domains |

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Model family taxonomy | `model-families/registry.yaml` |
| Taxonomy guide | `model-families/README.md` |
| Registry validation | `platform/src/courseflow_ai_platform/registry.py` |
| Taxonomy tests | `platform/tests/test_registry.py` |
| LMS speech use case | `use-cases/registry.yaml#lms-video-transcript-summary` |
| LMS CV/document use case | `use-cases/registry.yaml#lms-document-vision-ingestion` |

## Product Rule

Every new AI use case must declare a known `model_family`. If a family is missing, the platform council must add it to the taxonomy with maturity, methods, use cases and governance notes before implementation starts.
