# Enterprise AI Platform Product

`ai-platform` là một sản phẩm nền tảng độc lập của hệ thống CourseFlow Enterprise, không phải module phụ của LMS.

Nền tảng này cung cấp paved road để mọi sản phẩm trong enterprise đưa AI use case vào production-grade, demo-scale hoặc production-scale tùy maturity: intake, contracts, feature consumption, model development, evaluation, registry, approval, serving, observability, governance và runbooks.

## Product Mission

Build once, apply many times:

```text
enterprise use case
-> product intake
-> data/feature contract
-> model archetype
-> train/evaluate
-> registry/artifact/model card
-> approval
-> serving/fallback
-> monitoring/feedback
```

## Supported Product Domains

| Domain | Example AI use cases | Platform value |
|---|---|---|
| LMS CourseFlow | AI Mentor, recommendation, RAG tutor, grading, learner risk | personalized learning and instructor productivity |
| Support Platform | case summarization, intent routing, SLA risk, agent assist | faster resolution and quality control |
| Billing/Finance | anomaly detection, reconciliation assistant, payment risk | operational risk reduction |
| Commerce | personalization, next-best-offer, catalog semantic search | conversion and discovery |
| Identity/Risk | access risk scoring, entitlement anomaly, abuse detection | security and compliance |
| Workforce/HRIS | skill inference, workforce learning path, attrition risk | talent intelligence |
| Enterprise Operations | demand forecasting, visual inspection, routing optimization | planning and operational efficiency |

## Platform Product Capabilities

| Capability | Product promise |
|---|---|
| AI portfolio management | Business can see every AI use case, owner, phase, KPI and risk |
| Solution blueprint intake | PO/BA, SA AI Platform and SA AI Engineer can turn a business request into delivery workstreams and blockers |
| Operating cockpit | Admin/Ops can see delivery health, release health and cross-role next actions in one projection |
| Admin/Ops dashboard artifact | Admin/Ops can open one rendered HTML artifact for cockpit, owner queues, tenant-safe incident rollups and product-readiness freshness, backed by a freshness manifest |
| Delivery backlog | Teams can pick up cockpit actions as backlog items with phase, owner, priority and acceptance criteria |
| Delivery SLA and owner routing | Delivery owners can see due-soon, overdue, monitoring and escalation routing |
| Delivery owner views | PO/BA, SA, Governance and Admin/Ops can see each owner queue, next due date, next review date and overloaded queues |
| Feature and model contracts | Teams know exactly what data/model APIs they are depending on, and data domains are mapped to design/production readiness |
| Model family paved roads | Classical ML, embeddings, DL, LLM/RAG, bandit/RL, causal/experimentation and multimodal have clear entry points |
| NLP understanding service boundary | LMS, Support and Enterprise Knowledge can reuse intent, semantic tag, retrieval-query and rubric feedback analysis behind tenant/product/use-case grants |
| Retrieval service boundary | LMS and non-LMS products can search governed corpora through the same tenant-safe lexical/vector/hybrid retrieval service |
| RAG answer service boundary | LMS, Support and Enterprise Knowledge can request grounded answers with required citations, refusal, HITL and tenant/product/use-case grants |
| Governance evaluation service boundary | LMS and enterprise products can ask for release, promotion, safety, HITL and evidence decisions through one tenant/product/use-case scoped service |
| Governance evaluation ops projection | Admin/Ops can see governance release-gate drills, approved/review-required/blocked decisions and privacy rejects in cockpit and dashboard |
| AI business capability coverage | Business can see which AI modules are implemented, executable, roadmap, privacy-gated or simulator-gated, plus the runtime status of each module |
| AI module catalog | Business and architecture reviewers can see the full required model spectrum plus extended enterprise modules in one report |
| AI capability taxonomy | Platform leaders can see Responsible AI, MLOps, Feature Store, Evaluation and Serving alongside model areas |
| AI runtime roadmap | Platform leaders can prioritize which registry/tooling/shadow modules must become runtime artifacts next |
| Media privacy review | Raw document, image, audio and video processing cannot proceed until required controls and evidence refs are accepted |
| Evaluation and quality gates | No model moves without measurable evidence |
| Prompt safety gateway | LLM/GenAI prompts are redacted, tenant-safe, budget-checked and human-reviewed before model calls |
| LLM provider credential readiness | Live provider rollout is blocked unless secret refs, rotation and deployment checks are safe |
| LLM provider runtime probes | Live provider rollout requires secret probe, egress, cost and latency evidence |
| LLM provider secret rotation | Live provider rollout requires secret-manager binding, rotation automation, evidence refs and a passed rotation drill without storing secret values |
| Registry and artifact governance | Active/candidate models are traceable and rollbackable |
| Secure serving | Internal APIs, tenant isolation, fallback and observability are standard |
| Model serving service boundary | Shared model runtimes can be exposed as an independent service package without becoming LMS-owned code |
| Model serving metrics export | Runtime serving counters can be persisted and consumed by operating cockpit health projections |
| Serving access governance | Product principals, tenant/model grants and ops scopes move through approval queues, reviewable patch plans, checksum-bound apply ledgers, controlled appliers and reconciliation after policy apply |
| Serving access incident handoff | Drift, blocked apply and stale apply conditions can be exported as tenant-safe Admin/Ops incident handoffs |
| AI governance | Human-in-the-loop, privacy, safety and audit are built in |

## Platform Customers

- Product teams that need AI capabilities without rebuilding MLOps.
- Data Platform team that publishes governed features for AI consumers.
- Admin/Ops teams that need AI approval, rollback, audit and incident evidence.
- AI Engineers who need a repeatable model lifecycle.
- Business owners who need measurable AI value and risk control.

## Product North Star

Every enterprise AI use case can be onboarded through the same measurable path:

```text
registered -> contracted -> evaluated -> approved -> served -> monitored
```

## Current Proof Points

| Proof point | Product | Evidence |
|---|---|---|
| Recommendation item-CF baseline | LMS CourseFlow | model card, eval report, artifact manifest |
| Sequence Risk Service Package | LMS CourseFlow and AI Platform | `services/sequence-risk-service` packages the deterministic recurrent baseline behind tenant/product/use-case grants, direct-identifier rejection, HITL routing, health and metrics |
| Finance Document Intelligence Baseline | Billing/Finance | bounded OCR-token Media Intelligence Service route, privacy guardrail eval, model card and artifact manifest |
| Payment Fraud Service Package | Billing/Finance and AI Platform | `services/payment-fraud-service` packages fraud scoring behind tenant/product/use-case grants, direct-identifier rejection, entity-link metrics and HITL payment-action guardrails |
| Graph Entity Service Package | Billing/Finance and AI Platform | `services/graph-entity-service` packages pseudonymous entity-link evidence behind tenant/product/use-case grants, direct-identifier rejection, graph-review metrics and no automated adverse action |
| Forecasting Service Package | Enterprise Operations, LMS CourseFlow and AI Platform | `services/forecasting-service` packages demand forecasting and capacity planning behind tenant/product/use-case grants, direct-identifier rejection, capacity HITL metrics and no automated capacity changes |
| Operations Demand Forecast Baseline | Enterprise Operations | time-series planning runtime library, model IO contract, golden eval, model card and artifact manifest |
| Causal Uplift Service Package | LMS CourseFlow and AI Platform | `services/causal-uplift-service` packages aggregate treatment/control uplift evaluation behind tenant/product/use-case grants, direct-identifier rejection, guardrail HITL metrics and no automated rollout |
| Routing Policy Service Package | Enterprise Operations and AI Platform | `services/routing-policy-service` packages constrained routing recommendations behind tenant/product/use-case grants, direct-identifier rejection, constraint HITL metrics and blocked online policy activation |
| Support Agent Assist baseline | Support Platform | feature/model contracts, baseline code, tests, model evidence |
| Support SLA Risk Baseline | Support Platform | classical SLA breach risk runtime library, model IO contract, golden eval, model card and artifact manifest |
| Speech Quality Baseline | Support Platform and LMS CourseFlow | transcript-segment Media Intelligence Service route, privacy guardrail eval, feature/model IO contract, model card and artifact manifest |
| Media Intelligence Service Package | AI Platform | `services/media-intelligence-service` packages bounded document and speech AI behind media privacy controls, product/use-case/tenant grants, health and HITL/privacy metrics |
| Media Privacy Review Control Plane | AI Platform | policy-as-data, raw-media control evidence, review queue and generated report approve transcript, raw OCR/layout and raw ASR/diarization while keeping speaker biometrics blocked |
| Enterprise Solution Blueprint Intake | AI Platform | cross-domain use-case requests are mapped to taxonomy modules, workstreams and data/eval/privacy/simulator/platform-build gaps |
| Data Contract Coverage | AI Platform | 16 requested data domains are mapped across LMS, support, enterprise knowledge, finance and operations contracts with design/production/gated status |
| AI Platform Operating Cockpit | AI Platform | solution blueprint, data contract coverage, promotion intake, promotion readiness, connected serving metrics, serving access governance, LLM provider ops and governance evaluation release gates are aggregated into platform, delivery, runtime and release health |
| AI Platform Delivery Backlog | AI Platform | cockpit actions are converted into 23 delivery work items with owner role, phase, status and acceptance criteria |
| AI Platform Delivery State Ledger | AI Platform | persisted action-level transitions move generated backlog/SLA/owner/dashboard projections into `in_progress`, `done` or `accepted`; 4 applied transitions now track serving-access apply, Governance Evaluation alert drill acceptance, Governance response-runbook acceptance and Product Readiness Freshness response acceptance |
| AI Platform Delivery SLA | AI Platform | 23 backlog items have owner alias, due date or monitoring cadence, with 0 overdue and 0 missing owner aliases |
| AI Platform Delivery Owner Views | AI Platform | 6 owner queues show due-soon, on-track, monitoring, overload, next due, next review and open serving-access incident rollups |
| Admin/Ops Dashboard Artifact | AI Platform | static HTML dashboard combines operating cockpit, Admin/Ops owner queues, tenant-safe serving-access incident rollups, product-readiness freshness, product freshness incident export, response drill, suppression policy drill, effectiveness, coverage, regression, coverage-SLO, release-governance, release-gate-drill, release-gate-effectiveness, enterprise-pattern, enterprise-adoption monitoring, enterprise-adoption-SLO publication, enterprise-adoption-SLO release governance and its drill, with 27/27 source snapshot freshness evidence |
| AI Platform Product Readiness | AI Platform | `platform/product/reports/ai-platform-product-readiness-v1.yaml` gives release stakeholders 30/30 passed gates, response-runbook acceptance, product freshness response acceptance, suppression policy drill, effectiveness, coverage, regression, published coverage-SLO, release-governance, release-gate-drill, release-gate-effectiveness, enterprise-pattern, enterprise-adoption, enterprise-adoption-SLO, enterprise-adoption-SLO release-governance and drill evidence, tenant-safe incident state and serving metrics evidence |
| Runtime Product Readiness Freshness | AI Platform | `platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml` probes `GET /v1/model-serving/product-readiness`, confirms 8/8 required AI spectrum coverage, 1 live runtime request, 1 audit record, 0 errors and publishes `current` freshness in the Admin/Ops dashboard |
| Product Readiness Freshness Incident Export | AI Platform | `platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml` routes stale freshness reports, route outages and audit gaps to `admin-ops` using tenant-safe product refs; baseline is 0 open incidents |
| Product Readiness Freshness Response Drill | AI Platform | `platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml` validates 5 Admin/Ops response scenarios for stale reports, route outages, static snapshot staleness, runtime errors and audit gaps |
| Product Readiness Freshness Response SLO Drift Suppression Policy Drill | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml` exercises under-threshold, dedupe, cooldown and escalation-preservation decisions with 4/4 scenarios passed |
| Product Readiness Freshness Response SLO Drift Suppression Policy Effectiveness | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml` monitors 4/4 effective policy signals, 100% suppression effectiveness and 100% escalation preservation |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml` expands coverage to 5/5 response SLO scenario classes with 1 active policy scenario and 4 explicit non-watch exclusions |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Regression | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml` monitors 7/7 regression checks so coverage, active watch policy, explicit exclusions and tenant safety do not drift |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage SLO | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml` publishes 4/4 coverage SLO objectives for 100% scenario coverage, regression health, tenant safety and 30-day Admin/Ops review cadence |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Governance | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml` attaches 5/5 release gates for SLO publication, objective health, dashboard/readiness visibility, owner cadence and tenant safety |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Gate Drill | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml` exercises 5/5 release gate replay scenarios across SLO publication, objective health, dashboard/readiness visibility, owner cadence and tenant safety |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Gate Effectiveness | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml` monitors 5/5 effective release-gate signals and 100% release gate effectiveness as prerequisite evidence for enterprise pattern adoption |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Gate Enterprise Pattern | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml` expands the release gate pattern across 6/6 solution blueprints, 5 non-LMS blueprints, 4 non-LMS products, 9 taxonomy areas and 36 evaluation gates |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Gate Enterprise Adoption | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml` monitors 6/6 adopted enterprise release gate pattern signals, 100% adoption and tenant-safe evidence before publishing an adoption SLO |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Gate Enterprise Adoption SLO | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml` publishes 5/5 enterprise adoption SLO objectives for 100% adoption, governed intake, enterprise span, tenant safety and 30-day owner cadence |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Gate Enterprise Adoption SLO Release Governance | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml` attaches 5/5 enterprise adoption SLO release governance gates for SLO publication, objective health, enterprise span, owner cadence and tenant safety |
| Product Readiness Freshness Response SLO Drift Suppression Policy Coverage Release Gate Enterprise Adoption SLO Release Governance Drill | AI Platform | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1.yaml` replays 5/5 enterprise adoption SLO release governance gates with tenant-safe drill evidence |
| Product Readiness Freshness Response Acceptance | AI Platform | delivery state ledger records `product-readiness-freshness-response-drill-accepted-20260617`, and product readiness gates it for stakeholder release visibility |
| Governance Evaluation Service Package | AI Platform | `services/governance-evaluation-service` packages release, promotion, HITL, gate-readiness and safety decisions behind tenant/product/use-case grants, direct-identifier rejection and secret-value rejection |
| Governance Evaluation Ops Report | AI Platform | `platform/governance/reports/governance-evaluation-service-v1.yaml` proves release gate observability across LMS and Support with approved, review-required, blocked, direct-identifier rejection and secret-value rejection drills |
| Governance Evaluation Alert Drill | AI Platform | operating cockpit, delivery backlog, SLA, owner views and Admin/Ops dashboard now route `run_governance_evaluation_release_gate_alert_drill` to Admin/Ops |
| Governance Evaluation Alert Drill Acceptance | AI Platform | delivery state ledger records `governance-evaluation-alert-drill-accepted-20260617` with tenant-safe evidence refs across governance report, cockpit, backlog, owner views and dashboard |
| Governance Evaluation Response Runbook Acceptance | AI Platform | delivery state ledger records `governance-evaluation-response-runbook-drill-accepted-20260617`, and product readiness gates it for stakeholder release visibility |
| AI Runtime Roadmap | AI Platform | 14/14 current AI coverage modules are runtime-ready and service-integrated; no P1/P2 runtime candidate remains in the current roadmap |
| Model Serving Gateway | AI Platform | manifest-backed runtime facade and API envelope dispatch source baselines by model ID with latency, artifact, fallback, error, HITL, per-model metrics and configurable audit-store metadata |
| Hosted Model Serving Adapter | AI Platform | framework-neutral route handlers expose model catalog, invocation, metrics, health and cockpit snapshots with JSONL audit persistence, route scopes, tenant policy, policy-as-data principal grants and bounded auth-denial telemetry |
| Model Serving Service Package | AI Platform | `services/model-serving-service` packages catalog, invocation, metrics, health and cockpit routes behind a policy-enforced CLI/HTTP service boundary |
| Prompt Gateway Service Package | AI Platform | `services/prompt-gateway-service` packages prompt redaction, tenant context filtering, token budget, HITL and metrics routes behind policy-enforced product/use-case/tenant grants |
| LLM Adapter Service Package | AI Platform | `services/llm-adapter-service` packages provider-neutral GenAI/LLM generation behind Prompt Gateway, scoped provider grants, health/metrics routes and sanitized prompt audit |
| LLM Provider Ops Policy | AI Platform | `platform/governance/policies/llm-provider-ops-policy.yaml` configures provider rate limits, timeouts, circuit breakers and failover while keeping live credentials out of source |
| LLM Provider Credential Readiness | AI Platform | `platform/governance/reports/llm-provider-readiness-v1.yaml` reports contract-stub/live readiness and blocks plaintext live provider credentials before rollout |
| LLM Provider Runtime Probes | AI Platform | `platform/operations/reports/llm-provider-runtime-probes-v1.yaml` reports runtime secret probe, egress, cost and latency rollout evidence |
| LLM Provider Alert Routing | AI Platform | `platform/operations/reports/llm-provider-alert-routing-v1.yaml` validates tenant-safe provider budget/latency alert routes, Admin/Ops sink ownership and rotation evidence stance |
| LLM Provider Secret Rotation | AI Platform | `platform/governance/reports/llm-provider-secret-rotation-v1.yaml` validates secret-manager refs, runtime resolution, rotation automation, evidence refs and live rotation drill readiness |
| LLM Provider Alert Projection | AI Platform | operating cockpit, delivery backlog, owner views and Admin/Ops dashboard now expose `llm_provider_ops`, alert routing status and the provider alert delivery drill |
| Model Serving Metrics Export | AI Platform | persisted metrics snapshot connects hosted serving adapter counters to the operating cockpit, proving 3 requests, 3 audit records, 0 errors and healthy serving status |
| Serving Access Review | AI Platform | model-serving access change requests are reviewed for approvals, tenant expansion, ops scope and cross-product model grants before policy apply |
| Serving Access Policy Patch Plan | AI Platform | approved ready access requests generate before/after grant operations and a proposed policy without mutating active policy |
| Serving Access Apply Ledger | AI Platform | reviewer identity, timestamps and source/proposed policy checksums are recorded before a policy proposal can be applied |
| Serving Access Controlled Applier | AI Platform | ready proposals can be written only through an explicit target path after ledger and checksum checks pass |
| Serving Access Policy Reconciliation | AI Platform | active policy checksums are reconciled against source/proposed ledger checksums to expose pending apply, ledger update and drift |
| Serving Access Governance Cockpit | AI Platform | pending apply, ledger update and drift queues are promoted into operating cockpit, backlog, SLA and owner views |
| Serving Access Incident Export | AI Platform | serving-access drift, blocked, stale and watch conditions become tenant-safe incident handoffs with hashed application refs |
| Model audit ledger | AI Platform | sanitized prediction audit event contract, runtime ledger, JSONL storage adapter, gateway audit hook, artifact lineage, payload/output hashes and tenant export/delete/retention tests |
| Vector index artifact evidence | AI Platform | LMS and Support vector index snapshot manifests, hashes, corpus/schema lineage and contract gates |
| Artifact promotion registry | AI Platform | source and vector artifacts have maker-checker promotion stage, gates and rollback evidence |
| Promotion Request Intake | AI Platform | cross-domain candidate artifacts are queued as ready for approval or waiting for artifact, evaluation or privacy review evidence |
| Promotion Readiness Report | AI Platform | Admin/Ops can see active, approved and shadow artifacts with gate/artifact freshness, rollback, maker-checker, action queue and blocked/ready status |
| AI Business Capability Coverage Report | AI Platform | classical ML, DL, NLP/transformers, GenAI/LLM, RAG, CV/speech, RL and extended enterprise modules are mapped to LMS and non-LMS use cases with runtime status |
| AI Module Catalog | AI Platform | 8/8 required model spectrum areas and 6 extended enterprise modules are cataloged with `runtime_ready` platform status |
| AI Capability Taxonomy | AI Platform | 13/13 required areas cover the model spectrum plus Responsible AI, MLOps, Feature Store, Evaluation and Serving, with governance/evaluation service evidence |
| Hybrid retrieval shadow gates | AI Platform | LMS and Support retrievers prove vector/hybrid recall, no lexical regression and tenant isolation |
| NLP Understanding Service Package | AI Platform | `services/nlp-understanding-service` exposes intent, semantic tags, retrieval-query shaping and rubric feedback with direct-identifier rejection and HITL controls |
| Retrieval Service Package | AI Platform | `services/retrieval-service` exposes collection catalog, lexical/vector/hybrid search, health and metrics with tenant and collection scoped principals |
| RAG Answer Service Package | AI Platform | `services/rag-answer-service` exposes grounded answers with citations, insufficient-context refusal, HITL and tenant/product/use-case scoped principals |
| Prompt safety baseline | AI Platform | prompt contract, redaction policy, runtime gateway, golden eval, cost gate |
| LLM Adapter Shadow Gateway | AI Platform | required shadow gate proves Prompt Gateway runs before generation, blocked prompts skip generation and allowed answers stay grounded, cited and tenant-safe |
| Prompt audit ledger | AI Platform | sanitized audit event contract, runtime ledger, JSONL storage adapter, retention/export/delete tests |

## Non-goals

- Do not own source-of-truth business transactions.
- Do not bypass product service ownership.
- Do not train from ungoverned raw PII payloads in production.
- Do not put every model dependency into every runtime image.
