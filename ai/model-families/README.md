# AI Model Families

This folder defines the AI family taxonomy for the Enterprise AI Platform. It is not LMS-only: LMS is one product onboarded into a broader platform that also serves support, finance, identity/risk, commerce and workforce use cases.

`registry.yaml` is the machine-readable source of truth. The platform validator checks that every `model_family` referenced by `use-cases/registry.yaml` exists in this taxonomy.

`platform/coverage/business-capability-coverage.yaml` is the business-facing coverage report. It maps these families into validated modules across LMS and non-LMS enterprise use cases, so the platform can distinguish implemented baselines from executable gates, roadmap items, privacy-gated media AI and simulator-required RL.

## Coverage

| Area | Families |
|---|---|
| Classical and predictive ML | `classical_ml`, `classification`, `anomaly_detection`, `time_series_forecasting`, `causal_inference` |
| Recommendation and ranking | `recommender_systems`, `contextual_bandit`, `optimization` |
| Deep learning | `deep_learning`, `sequence_deep_learning`, `transformer` |
| NLP and retrieval | `nlp`, `embeddings`, `vector_search`, `retrieval`, `rag` |
| GenAI and LLM | `llm`, `genai`, `evaluation`, `deterministic_baseline`, `rules` |
| Computer vision, speech and multimodal | `computer_vision`, `speech`, `multimodal` |
| Decision intelligence | `reinforcement_learning`, `contextual_bandit`, `simulation`, `optimization` |
| Relational and domain AI | `graph_ml`, `knowledge_graph`, `edtech_ai` |

## LMS Mapping

| LMS module | First implementation | Advanced path |
|---|---|---|
| Recommendation | item-CF baseline | ALS/BPR, two-tower, SASRec |
| Semantic search and cold-start | embeddings + vector search | fine-tuned multilingual embeddings, hybrid reranking |
| Learner at-risk | logistic/XGBoost baseline | LSTM/GRU, transformer sequence model |
| Knowledge tracing | DKT-style baseline | SAKT/AKT transformer |
| Adaptive path | optimizer/contextual bandit simulator | constrained RL with offline policy evaluation |
| Auto-grading and feedback | structured LLM prompting | rubric eval, fine-tune/adapters if justified |
| AI tutor | RAG with grounded answers | eval-driven RAG, reranking, guardrails |
| Video learning | ASR transcript | chaptering, multimodal summary |
| Integrity/document workflows | OCR/basic CV | only after privacy and governance review |

## Enterprise Mapping

| Product/domain | Example use cases | Families |
|---|---|---|
| Support platform | agent assist, SLA risk | `llm`, `rag`, `classification`, `sequence_deep_learning` |
| Billing/finance | anomaly detection, reconciliation assistant | `classical_ml`, `anomaly_detection`, `retrieval`, `rules`, `llm` |
| Identity/risk | access risk scoring | `graph_ml`, `anomaly_detection`, `classical_ml` |
| Enterprise commerce | personalization, semantic catalog search | `recommender_systems`, `contextual_bandit`, `embeddings`, `vector_search` |
| HRIS workforce | skill intelligence and mobility matching | `embeddings`, `knowledge_graph`, `recommender_systems` |

## Selection Rule

Start with the simplest model that creates a measurable product outcome. Use deep learning, transformers, multimodal AI or RL only when data shape, evaluation maturity and product risk justify the extra complexity. Keep classical and deterministic baselines as quality gates for advanced models.
