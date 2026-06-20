# Enterprise Readiness Assessment

This assessment grades the current `ai/` state against the original target: apply AI to LMS while building a reusable AI platform that can handle many AI problem types.

## Current State Summary

| Area | Current evidence | Maturity | Gap |
|---|---|---|---|
| Recommendation MLOps | `services/recommendation-ml-service` has FastAPI, Postgres, migrations, registry, quality gates, maker-checker activation, JWT, telemetry | Strong | Generic platform extraction not done |
| Model depth | `IMPLICIT_ITEM_CF_V1` item-item CF baseline, `support-sla-risk-baseline-v1` classical risk scorer, `finance-payment-fraud-baseline-v1` Payment Fraud Service and Graph Entity Service routes with anomaly/entity-link risk evidence, deterministic vector-index contract baseline, RAG Answer Service over grounded citation/refusal gates, `sequence-risk-baseline-v1` Sequence Risk Service route over the recurrent baseline, `finance-document-intelligence-baseline-v1` OCR-token Media Intelligence Service route, `speech-quality-baseline-v1` transcript-segment Media Intelligence Service route, `operations-demand-forecast-baseline-v1` Forecasting Service route for demand/capacity planning, `operations-routing-policy-simulator-v1` Routing Policy Service route over the constrained simulator and `causal-uplift-baseline-v1` Causal Uplift Service route over aggregate experiment snapshots | Improving | No trainable PyTorch/ONNX sequence artifact, production semantic embeddings, raw OCR/layout model, raw audio ASR/diarization runtime, trained fraud/anomaly detector, probabilistic forecasting model or online policy learner yet |
| Product scope | AI Mentor product brief, use-case registry, solution blueprint intake, delivery backlog, persisted delivery state ledger, SLA owner routing, owner views, NLP understanding service package, prompt gateway service package, RAG answer service package and governance evaluation service package exist | Good | Needs production deployment hardening |
| Business capability coverage | Coverage report, module catalog and capability taxonomy map classical ML, DL, NLP/transformers, GenAI/LLM, RAG, CV, speech, RL plus Responsible AI, MLOps, Feature Store, Evaluation and Serving to LMS and enterprise use cases; 14/14 current modules are service-integrated | Good | Trainable DL artifacts, hosted raw document OCR/layout adapter, hosted raw audio ASR/diarization adapter, online RL learner and many proposed enterprise use cases are still missing |
| Feature contracts | LMS, support, speech transcript, enterprise knowledge, finance and operations contracts exist with validated data-domain coverage | Improving | No freshness/parity execution against real DP manifests yet |
| Vector/RAG foundation | Course and support collection schemas, lexical retrieval gates, vector-index contract gates, hybrid shadow gates, policy-enforced retrieval service package and policy-enforced RAG answer service package exist | Improving | No production semantic embedding model, ANN index runtime or live LLM RAG generation provider yet |
| Evaluation | Registry runner executes recommendation, support SLA risk, finance payment fraud, sequence-risk, finance-document, speech quality, routing-policy, support-agent, retrieval, grounded-answer, prompt-safety and LLM adapter shadow golden sets, with governance evaluation service projecting gate decisions | Improving | Need production dataset bindings and dashboard surfacing of service metrics |
| Governance | Policy YAML, recommendation activation, prompt safety gates, media privacy review control plane, raw-media control evidence, runtime prompt gateway library, policy-enforced prompt gateway service package, provider-scoped LLM adapter service package, governance evaluation service package, LLM adapter shadow gate, provider credential readiness report, secret rotation control plane, runtime probe cockpit projection and alert routing policy exist | Good | Live network provider activation, hosted persistence adapter and production deployment hardening not implemented |
| Observability | Recommendation metrics, model-serving metrics export, LLM provider runtime probes, provider secret rotation status, provider alert routing, provider cost/latency cockpit projection, prompt audit ledger, operating cockpit projection and rendered Admin/Ops dashboard artifact with freshness manifest exist | Good for first service and platform control plane | Generic drift/model quality views and live provider alert drills pending |
| Service boundaries | Recommendation service, model-serving service package, NLP understanding service package, retrieval service package, RAG answer service package, governance evaluation service package, prompt gateway service package, LLM adapter service package, media intelligence service, sequence-risk service, payment-fraud service, graph-entity service, forecasting service, routing-policy service and causal-uplift service live under `services/` with independent runtime contracts | Good | Production deployment hardening remains |
| Team model | Agent roles, solution blueprint workstreams, delivery backlog, SLA and owner views define PO/BA, SA AI Platform and SA AI Engineer responsibilities | Good | Cadence must be followed as implementation starts |
| Release path | CI/Compose/Docker now point to `ai/services/recommendation-ml-service`; operating cockpit separates release-ready from delivery-attention queues | Improved | Full product-hardening workflow still needs CI execution evidence and UI projection |

## Capability Maturity

| Capability | Target | Current | Next action |
|---|---|---|---|
| Use case portfolio | Managed | Registered plus validated solution blueprint intake, delivery backlog, delivery state ledger, SLA projection, owner views and governance release gate dependencies | Harden production deployment and close proposed-use-case implementation gaps |
| Business capability coverage | Classical-to-RL portfolio visibility | Validated coverage report, module catalog, platform capability taxonomy, runtime roadmap, request-to-module mapping, cockpit projection, rendered Admin/Ops dashboard and freshness manifest with 0 current runtime gaps | Promote runtime-ready modules through production hardening evidence |
| Feature store | Online/offline parity | Contracted with data-domain coverage report | Build materialization, freshness/parity checks and fixtures |
| Vector store | Governed collections | Schemas plus retrieval eval fixtures, deterministic vector-index contract gates, hybrid shadow gates, policy-enforced retrieval service package and RAG answer service package | Implement semantic embedding and ANN index runtime |
| Model registry | Shared across models | Domain-specific active | Extract conventions and generic schemas |
| Evaluation | Executable gates | Registry runner with 20 required evals, checked-in report snapshots and a governance evaluation service for release/promotion decisions | Bind production evals to governed data snapshots and dashboard service metrics |
| Model serving | Online/batch with fallback | Recommendation service plus policy-enforced model-serving service package, NLP understanding service package, retrieval service package, RAG answer service package, governance evaluation service package, prompt gateway service package, LLM adapter service package with provider ops, credential readiness policy and secret rotation control plane, sequence-risk, document-intelligence, speech transcript QA, finance payment fraud, graph entity evidence, operations demand forecasting, routing-policy and causal-uplift service packages, LLM adapter shadow gate, runtime probes, alert routing policy, cost/latency cockpit projection and connected serving metrics export | Harden hosted deployment and enable live network LLM provider only after approved secret-manager refs |
| Governance | Maker-checker + HITL + safety | Strong baseline with approved raw-media privacy review controls and policy-enforced release decision service | Extend raw-media controls to learner-impact reviews and production runtime adapters |
| Observability | Latency, error, drift, cost, quality | Recommendation ops metrics, persisted model-serving metrics export, LLM provider secret rotation status, alert routing and cost/latency projection, persisted prompt audit records, operating cockpit report and static Admin/Ops dashboard with freshness manifest | Add drift, model-quality monitors and live provider alert drills |
| Artifact store | Versioned model and retrieval artifacts | Source algorithm manifests including support SLA risk, finance payment fraud, sequence-risk, finance-document, speech quality, operations demand forecast, causal uplift and operations-routing baselines, vector-index snapshot manifests and promotion registry with sha256 validation | Extend manifests to `.pt`, `.onnx`, tokenizer and object-store artifacts |
| Release/CI gates | Build path aligned to `ai/services` | Partially remediated | Run full Docker and smoke gates in CI |

## Enterprise Gaps And Remediation

### Gap 1: Model layer is too shallow

Risk: AI platform may look enterprise but still lacks trained parametric and neural artifacts.

Remediation:

- Keep item-CF as benchmark.
- Keep sequence-risk baseline as the deep-learning model IO and evaluation contract gate.
- Keep finance-document baseline as the bounded OCR-token IO and privacy guardrail gate.
- Keep operations demand forecast baseline as the forecasting/planning IO and evaluation contract gate.
- Keep Routing Policy Service as the constrained policy IO and offline evaluation gate.
- Keep Causal Uplift Service as the aggregate experiment uplift IO and rollout-review gate.
- Add classical parameterized baseline: ALS/BPR or XGBoost at-risk.
- Replace deterministic hash-vector contract baseline with a semantic embedding model for course content.
- Add PyTorch deep learning archetype for two-tower/SASRec.
- Add online policy learner only after logged-policy data, counterfactual evaluation and safety constraints are accepted.

### Gap 2: Feature store is not real yet

Risk: each model builds features differently and training-serving skew appears.

Remediation:

- Materialize registered data contracts from `dp` gold datasets.
- Add offline fixtures and online serving schema for LMS, support, finance and operations contracts.
- Add feature freshness and parity checks.

### Gap 3: Evaluation gates are not yet fully production-bound

Risk: executable golden gates exist, but reports are still hand-authored and production evals are not yet bound to governed data snapshots.

Remediation:

- Generate eval reports from runner output.
- Bind recommender and retrieval evals to governed `dp` gold snapshots.
- Keep LLM adapter shadow evaluation running against deterministic grounded-answer and prompt-gateway baselines.

### Gap 4: Artifact serving is score-table centric

Risk: DL/LLM/embedding models need files, tokenizers, persisted vector indexes and prompt/eval config.

Remediation:

- Extend artifact manifest contract to model binaries, tokenizers and persisted vector stores.
- Support artifact URI, checksum, model family, runtime, dependency lock.
- Add promotion gates that validate artifact availability, vector index persistence, maker-checker approval and rollback targets.

### Gap 5: LLM safety controls need live provider activation and deployment hardening

Risk: prompt safety, provider-neutral generation, provider ops policy, credential readiness, secret rotation control plane, runtime probe evidence, alert routing policy and cockpit alert projection are available as packaged controls, but future live provider rollout still needs approved network enablement and production deployment evidence.

Remediation:

- Keep prompt gateway service as the enforced network boundary for runtimes that need shared prompt evaluation.
- Add Admin/Ops export UI and DB/object-storage adapter for sanitized prompt/response audit records.
- Keep cost/request rate limits, timeout, circuit-breaker and failover controls in `llm-provider-ops-policy.yaml`.
- Keep plaintext provider credentials blocked through `llm-provider-readiness-v1.yaml`.
- Keep runtime secret probes and provider cost/latency observability reported through `llm-provider-runtime-probes-v1.yaml`.
- Keep provider budget/latency alert routes validated through `llm-provider-alert-routing-v1.yaml`.
- Keep secret-manager binding and rotation automation validated through `llm-provider-secret-rotation-v1.yaml`.
- Enable a live network provider only after product, tenant, secret-manager and deployment approvals are available outside source control.
- Require HITL for final grades and external responses.

### Gap 6: DP Gold snapshot consumption is not implemented

Risk: production training continues to depend on bounded HTTP payloads instead of governed feature snapshots, limiting reproducibility and lineage.

Remediation:

- Add training request support for `dataset_snapshot_id`, manifest URI and manifest hash.
- Bind training runs to feature contract version and source data window.
- Keep current enqueue endpoint for compatibility while adding snapshot-backed training.

### Gap 7: CI/build path must stay aligned after AI platform restructure

Risk: enterprise release gates fail if workflow, Dockerfile, compose or smoke scripts look for the service under the old backend path.

Remediation:

- Keep Docker build context at repo root.
- Keep Dockerfile source copies under `ai/services/recommendation-ml-service`.
- Keep backend smoke scripts pointed at the canonical AI service path.
- Run product-hardening ML job before declaring runtime release-ready.

## Readiness Gates By Phase

| Phase | Exit criteria |
|---|---|
| 0 | Folder, team, product, architecture, contracts, gates and governance artifacts exist |
| 1 | Semantic search, auto-grading and at-risk baseline have executable eval and model cards |
| 2 | Deep learning recommendation and RAG Tutor can run through registry/approval/fallback |
| 3 | Knowledge tracing and adaptive path have data sufficiency, safety and offline policy eval |
| 4 | Feature store, drift/cost monitoring, canary/shadow and runbooks are operational |

## Enterprise Release Gates

| Gate | Required proof |
|---|---|
| Build gate | Python unit/lint/type/integration pass from `ai/services/recommendation-ml-service` |
| Docker gate | Image builds from repo root using `ai/services/recommendation-ml-service/Dockerfile` |
| Data boundary gate | Production training can bind to approved DP Gold snapshot or feature manifest |
| Feature gate | Feature contract has owner, freshness, PII class, tenant boundary and parity report |
| Evaluation gate | Model card, eval report, baseline comparison and YAML gate pass |
| Artifact gate | Candidate has immutable artifact URI/hash, dataset snapshot id and dependency lock |
| Governance gate | Maker-checker, rollback target, HITL where needed, no secret/PII leakage |
| Serving gate | p95 SLA, fallback behavior, readiness and canary/shadow plan |
| Monitoring gate | Latency, error, fallback, model age, drift, feature freshness, cost and safety metrics |

## Architectural Decision

`recommendation-ml-service` must remain the first model service, not become the whole platform. Generic concerns should be extracted gradually into platform conventions and future shared services only when duplication appears.
