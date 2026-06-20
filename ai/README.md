# CourseFlow AI Platform

`ai/` là sản phẩm nền tảng AI độc lập của hệ thống CourseFlow Enterprise. LMS là sản phẩm đầu tiên được onboard; recommendation chỉ là use case đầu tiên, không phải toàn bộ phạm vi AI.

Mục tiêu của thư mục này là biến CourseFlow thành một nơi học và triển khai AI theo kiểu enterprise-ready, demo-scale: kiến trúc, governance, evaluation, security và observability làm nghiêm túc; dữ liệu và tải có thể bắt đầu bằng sample/synthetic trước khi có production traffic thật.

## Source Map

```text
ai/
  README.md
  docs/
    architecture/          Kiến trúc AI platform, context map, folder boundaries
    product/               Product brief, roadmap, scope PO/BA cho AI Mentor
    team/                  Agent operating model cho PO/BA, SA, AI Engineer
    html/                  Tài liệu HTML cũ đã gom lại để tránh nằm rải ở root
  products/
    registry.yaml          Registry sản phẩm dùng AI Platform
    ai-platform/           Product charter cho Enterprise AI Platform
    lms-courseflow/        Product onboarding cho CourseFlow LMS
  use-cases/
    registry.yaml          Registry các AI use case có owner, phase, KPI
    lms-ai-mentor/         Umbrella use case cho LMS
  model-families/          Bản đồ classical ML, DL, embeddings, RAG, LLM, RL, ASR, CV
  models/                  Archetype train/predict/evaluate cho từng họ model
  features/                Offline/online feature store direction
  pipelines/               Training, evaluation, scoring, materialization
  contracts/
    features/              Feature contracts dùng giữa dp, LMS và AI
    models/                Model input/output/SLA contracts
  platform/
    artifacts/             Manifest artifact/model evidence
    capabilities/          Capability registry của nền tảng AI
    intake/                Use-case request registry and solution blueprint reports
    src/                   Tooling kiểm tra registry/governance
    tests/                 Tests cho AI Platform tooling
    lifecycle/             Train, evaluate, register, approve, activate, monitor
    evaluation/            Quality gates, golden sets, eval policies
    governance/            Approval, human-in-the-loop, PII, retention, audit
    model-registry/        Model cards và registry evidence
    operations/            Admin/Ops cockpit reports and rendered dashboard for delivery/release health
    delivery/              Delivery backlog, SLA and owner-view projections from cockpit actions
    data-contracts/        Data contract registry and coverage reports
    vector-store/          Collection schemas cho embeddings/RAG
    coverage/              Business capability coverage, module catalog, capability taxonomy and runtime roadmap
  services/
    recommendation-ml-service/
                            Service hiện có: related-course recommendation, model ops
    model-serving-service/  Shared model-serving service boundary for catalog, invoke, metrics, health, cockpit
    retrieval-service/      Shared lexical/vector/hybrid retrieval service for LMS and Support Platform
    rag-answer-service/     Shared grounded-answer service with citations, refusal, HITL and tenant gates
    nlp-understanding-service/
                            Shared intent, semantic tag, retrieval-query and rubric feedback service
    prompt-gateway-service/ Shared prompt safety gateway for GenAI/LLM/RAG adapters
    llm-adapter-service/    Provider-neutral GenAI/LLM adapter service behind Prompt Gateway and provider grants
    governance-evaluation-service/
                            Shared release, promotion, HITL and safety decision service
  infra/
    docker/                 Independent AI Compose cluster: Postgres, Recommendation ML API, worker and migrator
  runbooks/                Runbook vận hành AI incidents/releases
```

## Platform Principles

- Product first: mỗi model phải phục vụ một pain point của learner, instructor, admin hoặc AI ops.
- Shared lifecycle: mọi model đi qua cùng vòng đời `data contract -> feature -> train -> evaluate -> registry -> approval -> serving -> monitoring -> feedback loop`.
- Recommendation is the benchmark: `IMPLICIT_ITEM_CF_V1` hiện tại là baseline cổ điển để so sánh các model ALS/BPR, two-tower, SASRec.
- Enterprise governance by default: model card, quality gate, maker-checker activation, audit và rollback là chuẩn bắt buộc.
- LMS-specific, platform-shaped: artifact cho LMS nằm dưới `products/lms-courseflow` và `use-cases/lms-ai-mentor`, còn năng lực dùng lại nằm dưới `platform`, `contracts`, `model-families`, `models`, `features` và `pipelines`.
- No raw learner PII in AI payloads: dùng hash, bounded payload, retention policy và audit evidence an toàn.

## Agent Team

AI Platform được điều phối bởi một đội agent có trách nhiệm rõ ràng:

| Agent | Focus | Primary docs |
|---|---|---|
| PO/BA Agent | Product scope, backlog, KPI, acceptance criteria | `docs/product/ai-mentor-enterprise-backlog.md` |
| SA AI Platform Agent | Platform boundaries, capability maturity, enterprise gates | `docs/architecture/enterprise-readiness-assessment.md` |
| SA AI Engineer Agent | Model archetypes, dependency strategy, tests, migration path | `docs/architecture/ai-engineering-implementation-plan.md` |
| Governance Reviewer | HITL, privacy, approval, rollback, safety, audit | `platform/governance/policies/ai-governance-policy.yaml` |

Operating model: `docs/team/agent-operating-model.md`.

## Enterprise AI Platform Product

AI Platform là product riêng có charter tại `products/ai-platform/README.md` và registry sản phẩm tại `products/registry.yaml`.

Nó phục vụ nhiều domain:

- LMS CourseFlow
- Support Platform
- Billing/Finance
- Identity/Risk
- Enterprise Commerce
- HRIS Workforce
- Enterprise Operations

Use-case portfolio nằm ở `use-cases/registry.yaml`; LMS AI Mentor chỉ là umbrella use case đầu tiên.

## AI Family Coverage

Taxonomy chính thức nằm ở `model-families/registry.yaml`; validator kiểm tra mọi `model_family` trong use-case registry phải thuộc taxonomy này.
Business coverage chính thức nằm ở `platform/coverage/business-capability-coverage.yaml`; validator kiểm tra mỗi module AI phải map được cả LMS use case và enterprise use case, đồng thời active/executable module phải có evaluation gate.
AI module catalog nằm ở `platform/coverage/reports/ai-module-catalog-v1.yaml`; capability taxonomy nằm ở `platform/coverage/ai-capability-taxonomy.yaml` và `platform/coverage/reports/ai-capability-taxonomy-v1.yaml`.

Trả lời trực tiếp cho câu hỏi coverage: có. Nền tảng đã được quy hoạch và validate cho chuỗi `classical ML -> deep learning -> NLP/transformers -> GenAI/LLM -> RAG -> CV/speech -> RL`, cộng thêm recommender systems, anomaly/fraud/risk, forecasting/time-series, causal/experimentation, graph/knowledge intelligence và governance/safety/evaluation.
Ngoài các họ model, platform còn có taxonomy riêng cho Responsible AI, MLOps, Feature Store, Evaluation và Serving để AI Platform là sản phẩm độc lập, không chỉ là một feature của LMS.

| Spectrum | Coverage |
|---|---|
| Classical ML | registered, active baseline via recommendation item-CF |
| Deep learning | service-integrated Sequence Risk Service baseline for recurrent sequence risk, with trainable DL still on roadmap |
| NLP/transformers | service-integrated NLP Understanding Service for intent classification, semantic query understanding and rubric feedback, with transformer adapter upgrade path |
| GenAI/LLM | service-integrated prompt gateway and provider-neutral LLM adapter, runtime probes, secret rotation controls and cost/latency cockpit projection with deterministic support-assist baseline and LLM/RAG upgrade path |
| RAG/vector search | service-integrated RAG Answer Service with LMS/support collection contracts, retrieval gates, vector-index contract gates, citations and refusal gates |
| CV/document AI | OCR-token service-integrated baseline for finance/LMS documents through Media Intelligence Service, with approved raw OCR/layout media controls |
| Speech | transcript-segment service-integrated baseline for LMS/support quality workflows through Media Intelligence Service, with approved raw ASR/diarization media controls |
| RL/bandits/optimization | service-integrated Routing Policy Service baseline for constrained routing, safe exploration and next-best-action decisions |
| Extra enterprise families | service-integrated graph/entity evidence, knowledge graph roadmap, anomaly detection, time-series forecasting, causal inference/experimentation, simulation and shared governance evaluation |

Governance Evaluation Service hiện đã có ops projection riêng:
`platform/governance/reports/governance-evaluation-service-v1.yaml` ghi nhận release gate
observable cho LMS và Support, gồm approved/review-required/blocked decisions, direct-identifier
rejection, secret-value rejection và 0 unexpected errors. Các chỉ số này cũng xuất hiện trong
Operating Cockpit và Admin/Ops Dashboard.
Governance Evaluation cũng có incident export riêng tại
`platform/governance/reports/governance-evaluation-incident-export-v1.yaml`: baseline hiện
0 open incidents, tenant-safe, và sẽ mở P0/P1 cho Admin/Ops khi alert drill lỗi lặp đủ ngưỡng.
Runbook response drill tại
`platform/operations/reports/governance-evaluation-incident-response-drill-v1.yaml`
đang `passed` với 3 scenario P0/P1, 8 bước response và 0 raw identifier markers.
Product-readiness projection tại
`platform/product/reports/ai-platform-product-readiness-v1.yaml` đã đưa acceptance này
thành gate bắt buộc cho release stakeholders.

Coverage status means:

- `implemented baseline`: code and tests exist for the first production-style path.
- `executable gate`: golden evaluation exists and is run by the platform validator.
- `registered roadmap`: taxonomy, use-case mapping and governance path exist, but runtime model implementation is still planned. No current module is only in this state after the operations demand forecast baseline.
- `privacy gated`: module exists but needs media/document/audio privacy review before raw-media processing or promotion. No current business capability module remains in this state after the raw-media control evidence approval.
- `simulator required`: decision-policy module exists but still needs simulator and offline policy evaluation before rollout. This remains a valid gate status, but no current module is in this state after the operations-routing simulator baseline.

Runtime status means:

- `service_integrated`: runtime path is integrated into an existing service.
- `runtime_library`: reusable runtime library exists, but not necessarily as a hosted service.
- `shadow_artifact`: artifact/eval path exists for shadow use, but not production serving.
- `tooling`: validator, safety, eval or deterministic tooling exists.
- `registry_only`: module is deliberately registered as roadmap/gated, without runtime artifact yet.
- `production_ready`: reserved for modules with production serving evidence.

Current AI Business Capability Coverage:

| Area | Coverage status | Runtime status |
|---|---|---|
| Classical ML | implemented baseline | service integrated |
| Recommendation and personalization | implemented baseline | service integrated |
| Deep learning and sequence models | executable gate | service integrated |
| NLP and transformers | executable gate | service integrated |
| GenAI and LLM assistants | executable gate | service integrated |
| RAG, retrieval and vector search | executable gate | service integrated |
| Computer vision and document AI | executable gate | service integrated |
| Speech and audio AI | executable gate | service integrated |
| RL, bandits and decision optimization | executable gate | service integrated |
| Anomaly, fraud and risk | executable gate | service integrated |
| Forecasting and planning | executable gate | service integrated |
| Causal inference and experimentation | executable gate | service integrated |
| Graph ML and knowledge intelligence | executable gate | service integrated |
| Governance, safety and evaluation | executable gate | service integrated |

Current AI Runtime Roadmap:

| Scope | Value |
|---|---|
| Runtime-ready modules | 14 |
| Runtime gaps | 0 |
| P1 runtime candidates | 0 |
| P2 runtime candidates | 0 |
| Production-ready modules | 0 |
| Report | `platform/coverage/reports/runtime-roadmap-v1.yaml` |

Current AI Module Catalog:

| Scope | Value |
|---|---|
| Required model spectrum areas | 8/8 covered |
| Extended enterprise modules | 6: recommender, anomaly/fraud/risk, forecasting, causal/experimentation, graph/knowledge, governance/safety |
| Platform readiness | `runtime_ready` |
| First runtime candidates | none; all current coverage modules are service-integrated |
| Report | `platform/coverage/reports/ai-module-catalog-v1.yaml` |

Current AI Capability Taxonomy:

| Scope | Value |
|---|---|
| Required capability areas | 13/13 covered |
| Model areas | 10: 8 required areas plus optional causal/experimentation and graph/knowledge |
| Platform areas | 5: Responsible AI, MLOps, Feature Store, Evaluation, Serving |
| Capability registry entries | 25 |
| P1 gaps | 0 |
| Report | `platform/coverage/reports/ai-capability-taxonomy-v1.yaml` |

Validate platform registries:

```bash
cd ai/platform
python -m pytest
python -m courseflow_ai_platform.cli --ai-root ..
python -m courseflow_ai_platform.cli --ai-root .. --write-delivery-sla-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-delivery-owner-views-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-runtime-roadmap-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-ai-module-catalog-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-ai-capability-taxonomy-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-delivery-backlog-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-delivery-state-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-data-contract-coverage-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-model-serving-metrics-export-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-operating-cockpit-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-admin-ops-dashboard --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-admin-ops-dashboard-freshness-manifest --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-ai-platform-product-readiness-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-ai-platform-product-readiness-freshness-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-incident-export-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-incident-response-drill-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-metrics-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-trend-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-alert-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-alert-drill-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-alert-calibration-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-suppression-policy-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-governance-evaluation-ops-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-governance-evaluation-incident-export-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-governance-evaluation-incident-response-drill-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-solution-blueprint-report --generated-at 2026-06-16
python -m courseflow_ai_platform.cli --ai-root .. --write-promotion-readiness-report --generated-at 2026-06-16
python -m courseflow_ai_platform.cli --ai-root .. --write-promotion-intake-report --generated-at 2026-06-16
python -m courseflow_ai_platform.cli --ai-root .. --write-serving-access-review-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-serving-access-policy-patch-plan --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-serving-access-apply-ledger-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-serving-access-policy-apply-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-serving-access-policy-reconciliation-report --generated-at 2026-06-17
python -m courseflow_ai_platform.cli --ai-root .. --write-serving-access-incident-export-report --generated-at 2026-06-17
```

The validator checks product/use-case/capability registries, solution blueprint intake, business capability coverage, artifact evidence manifests, promotion registry, model cards, evaluation reports, source artifact hashes and vector-index snapshot hashes.
It also runs registered executable evaluations from `platform/evaluation/registry.yaml` and fails if any required evaluation fails.

Current data contract coverage:

| Scope | Value |
|---|---|
| Contracts | 7 total: 3 active, 4 draft, 0 privacy-gated, 0 simulator-gated |
| Blueprint requests covered | 6 total, 5 non-LMS |
| Data domains | 16 mapped, 0 missing |
| Design-ready | 6 requests |
| Production-ready | 3 requests |
| Newly covered enterprise domains | enterprise knowledge, finance payment risk, finance documents, operations routing, operations demand forecasting |

Current AI Platform operating cockpit:

| Scope | Value |
|---|---|
| Platform status | `attention_required` because delivery queues still need action |
| Delivery status | `ready_work_available` |
| Release status | `release_ready` |
| Coverage | 14 modules, 0 missing required areas |
| Evaluations | 20 required, 20 passed |
| Serving health | `healthy`, with model-serving metrics export connected |
| Serving metrics export | 3 requests, 3 successes, 3 audit records, 0 errors, 0 audit failures |
| Serving access governance | `pending_policy_apply`, with 1 approved policy application queued for Admin/Ops |
| Media privacy review | `approved`, with transcript-only, raw OCR/layout and raw ASR/diarization requests approved under controls |
| Control-plane actions | 23 actions across solution blueprint, data contract coverage, promotion intake, promotion readiness, serving access governance, LLM provider ops, Governance Evaluation drills, Product Readiness Freshness response acceptance and response SLO drift-alert policy hardening |
| Enterprise signal | 18 non-LMS use cases, 5 non-LMS solution requests |

Current media privacy review:

| Scope | Value |
|---|---|
| Reviews | 3 total |
| Approved | 3: transcript-only speech, finance raw OCR/layout and speech raw ASR/diarization |
| Waiting controls | 0 |
| Missing controls | 0 |
| Report | `platform/governance/reports/media-privacy-review-v1.yaml` |

Current AI Platform delivery backlog:

| Scope | Value |
|---|---|
| Items | 23 total |
| Ready to start | 16 |
| Monitoring | 3 |
| Blocked | 0 |
| P1/P2 split | 13 P1, 10 P2 |
| Sources | solution blueprint, data contract coverage, promotion intake, promotion readiness, serving access governance, LLM provider ops, Governance Evaluation ops, Governance Evaluation response drill, Product Readiness Freshness response drill and response SLO drift-alert policy hardening |

Current AI Platform delivery state ledger:

| Scope | Value |
|---|---|
| State transitions | 4 |
| Applied transitions | 4 |
| In progress | 1 |
| Accepted | 3 |
| Missing actions | 0 |
| Report | `platform/delivery/reports/delivery-state-v1.yaml` |

Current AI Platform delivery SLA:

| Scope | Value |
|---|---|
| Tracked items | 20 |
| Monitoring items | 3 |
| Due soon | 13 |
| On track | 7 |
| Overdue | 0 |
| Missing owner aliases | 0 |
| Top owner queues | Admin/Ops 6, SA AI Platform 6, SA AI Engineering 4 |

Current AI Platform delivery owner views:

| Scope | Value |
|---|---|
| Owner aliases | 6 |
| Items | 23 |
| Due-soon owner queues | 5 |
| Monitoring owner queues | 2 |
| Overloaded owner queues | 2 |
| Overdue owner queues | 0 |
| Open incidents | 0 currently; stale serving-access apply rolls into `admin-ops` as P1 after 2 days, repeated Governance Evaluation failures roll in as P0/P1, stale product-readiness freshness opens a P1 product incident |
| Top owner alias | `admin-ops` |

Current Admin/Ops dashboard artifact:

| Scope | Value |
|---|---|
| Artifact | `platform/operations/reports/admin-ops-dashboard-v1.html` |
| Freshness manifest | `platform/operations/reports/admin-ops-dashboard-freshness-v1.yaml` |
| Source reports | operating cockpit, delivery owner views, serving access incident export, Governance Evaluation incident export, Governance Evaluation response drill, product readiness freshness, product readiness freshness incident export, product readiness freshness response drill, product readiness freshness response metrics, product readiness freshness response trends, product readiness freshness response SLO drift alerts, product readiness freshness response SLO drift alert drill, product readiness freshness response SLO drift alert calibration, product readiness freshness response SLO drift alert suppression policy, product readiness freshness response SLO drift suppression policy drill, product readiness freshness response SLO drift suppression policy effectiveness, product readiness freshness response SLO drift suppression policy coverage, product readiness freshness response SLO drift suppression policy coverage regression, product readiness freshness response SLO drift suppression policy coverage SLO, product readiness freshness response SLO drift suppression policy coverage release governance, product readiness freshness response SLO drift suppression policy coverage release gate drill, product readiness freshness response SLO drift suppression policy coverage release gate effectiveness, product readiness freshness response SLO drift suppression policy coverage release gate enterprise pattern, product readiness freshness response SLO drift suppression policy coverage release gate enterprise adoption, product readiness freshness response SLO drift suppression policy coverage release gate enterprise adoption SLO |
| Admin/Ops delivery items | 7 |
| Open serving-access incidents | 0 currently |
| Watch serving-access incidents | 1 pending policy apply |
| Open Governance Evaluation incidents | 0 currently; repeated alert drill failures become tenant-safe P0/P1 incidents |
| Governance Evaluation response drill | `passed`, with 3 scenarios, 8 runbook steps and 0 failures |
| Product readiness freshness | `current`, with runtime route 200, 1 request, 1 audit record and 8/8 required AI spectrum coverage |
| Product readiness freshness incidents | 0 open; stale report, route outage or audit gap routes to `admin-ops` as tenant-safe product incidents |
| Product readiness freshness response drill | `passed`, with 5 scenarios, 8 runbook steps and 0 failures |
| Product readiness freshness response metrics | `slo_met`, with live ingest connected, 5 live observations and 0 SLO breaches |
| Product readiness freshness response trends | `trend_ready_with_watch`, with 1 owner role, 5 scenario classes and 1 watch scenario |
| Product readiness freshness response SLO drift alerts | `alerts_configured_with_watch`, with 1 watch scenario and 1 routed Admin/Ops alert |
| Product readiness freshness response SLO drift alert drill | `passed`, with 1 routed alert path replayed and 0 failures |
| Product readiness freshness response SLO drift alert calibration | `calibrated_with_watch`, with 1/1 calibrations passing and 0 noisy alerts |
| Product readiness freshness response SLO drift alert suppression policy | `suppression_policy_codified`, with 1/1 active rules, 30m dedupe and 60m cooldown |
| Product readiness freshness response SLO drift suppression policy drill | `passed`, with 4/4 policy scenarios, 3 suppressed replays and 1 preserved escalation |
| Product readiness freshness response SLO drift suppression policy effectiveness | `effectiveness_monitored`, with 4/4 effective signals, 100% suppression effectiveness and 100% escalation preservation |
| Product readiness freshness response SLO drift suppression policy coverage | `coverage_expanded`, with 5/5 scenario classes covered, 1 active policy scenario and 4 explicit non-watch exclusions |
| Product readiness freshness response SLO drift suppression policy coverage regression | `regression_monitored`, with 7/7 checks passed and 100% coverage preserved |
| Product readiness freshness response SLO drift suppression policy coverage SLO | `coverage_slo_published`, with 4/4 objectives met, 100% coverage target and 30-day review cadence |
| Product readiness freshness response SLO drift suppression policy coverage release governance | `release_governance_attached`, with 5/5 release gates attached and tenant-safe evidence |
| Product readiness freshness response SLO drift suppression policy coverage release gate drill | `passed`, with 5/5 release gate drill scenarios passed and tenant-safe evidence |
| Product readiness freshness response SLO drift suppression policy coverage release gate effectiveness | `effectiveness_monitored`, with 5/5 effective release-gate signals and 100% release gate effectiveness |
| Product readiness freshness response SLO drift suppression policy coverage release gate enterprise pattern | `enterprise_pattern_expanded`, with 6/6 blueprints assigned, 5 non-LMS blueprints, 4 non-LMS products, 9 taxonomy areas and 36 evaluation gates |
| Product readiness freshness response SLO drift suppression policy coverage release gate enterprise adoption | `adoption_monitored`, with 6/6 adoption signals, 100% adoption and tenant-safe evidence |
| Product readiness freshness response SLO drift suppression policy coverage release gate enterprise adoption SLO | `adoption_slo_published`, with 5/5 objectives met, 100% adoption target and 30-day review cadence |
| Product readiness freshness response SLO drift suppression policy coverage release gate enterprise adoption SLO release governance | `enterprise_adoption_slo_release_governance_attached`, with 5/5 release governance gates attached and tenant-safe evidence |
| Product readiness freshness response SLO drift suppression policy coverage release gate enterprise adoption SLO release governance drill | `passed`, with 5/5 release governance drill scenarios passed and tenant-safe evidence |
| Freshness status | `current`, with 27/27 source snapshots present and current |
| Safety behavior | HTML renderer escapes values and uses safe incident refs instead of raw tenant/principal values |

Current AI Platform product readiness:

| Scope | Value |
|---|---|
| Report | `platform/product/reports/ai-platform-product-readiness-v1.yaml` |
| Readiness status | `stakeholder_ready_with_followups` |
| Stakeholder visibility | `current_with_response_acceptance` |
| Required gates | 30/30 passed |
| Action required | 0 blocking actions |
| Runtime route | `GET /v1/model-serving/product-readiness` under model-serving ops scope |
| Runtime freshness | `platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml`, status `current` |
| Freshness incident export | `platform/governance/reports/product-readiness-freshness-incident-export-v1.yaml`, 0 open incidents and tenant safe |
| Freshness response drill | `platform/operations/reports/product-readiness-freshness-incident-response-drill-v1.yaml`, status `passed` |
| Freshness response metrics | `platform/operations/reports/product-readiness-freshness-response-metrics-v1.yaml`, `slo_met` with live ingest connected |
| Freshness response trends | `platform/operations/reports/product-readiness-freshness-response-trends-v1.yaml`, `trend_ready_with_watch` with 1 watch scenario |
| Freshness response SLO drift alerts | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alerts-v1.yaml`, `alerts_configured_with_watch` with 1 routed alert |
| Freshness response SLO drift alert drill | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-drill-v1.yaml`, `passed` with 1/1 routed alert paths replayed |
| Freshness response SLO drift alert calibration | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-calibration-v1.yaml`, `calibrated_with_watch` with 0 noisy alerts |
| Freshness response SLO drift alert suppression policy | `platform/operations/reports/product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml`, `suppression_policy_codified` with 1 active rule |
| Freshness response SLO drift suppression policy drill | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml`, `passed` with 4/4 policy replays |
| Freshness response SLO drift suppression policy effectiveness | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml`, `effectiveness_monitored` with 4/4 effective signals |
| Freshness response SLO drift suppression policy coverage | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml`, `coverage_expanded` with 5/5 scenario classes covered |
| Freshness response SLO drift suppression policy coverage regression | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml`, `regression_monitored` with 7/7 checks passed |
| Freshness response SLO drift suppression policy coverage SLO | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1.yaml`, `coverage_slo_published` with 4/4 objectives met |
| Freshness response SLO drift suppression policy coverage release governance | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-governance-v1.yaml`, `release_governance_attached` with 5/5 release gates attached |
| Freshness response SLO drift suppression policy coverage release gate drill | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-drill-v1.yaml`, `passed` with 5/5 release gate drill scenarios passed |
| Freshness response SLO drift suppression policy coverage release gate effectiveness | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-effectiveness-v1.yaml`, `effectiveness_monitored` with 5/5 effective signals and 100% release gate effectiveness |
| Freshness response SLO drift suppression policy coverage release gate enterprise pattern | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-pattern-v1.yaml`, `enterprise_pattern_expanded` with 6/6 blueprints assigned, 5 non-LMS blueprints, 4 non-LMS products, 9 taxonomy areas and 36 evaluation gates |
| Freshness response SLO drift suppression policy coverage release gate enterprise adoption | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-v1.yaml`, `adoption_monitored` with 6/6 adopted signals and 100% adoption |
| Freshness response SLO drift suppression policy coverage release gate enterprise adoption SLO | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-v1.yaml`, `adoption_slo_published` with 5/5 objectives met and 100% target adoption |
| Freshness response SLO drift suppression policy coverage release gate enterprise adoption SLO release governance | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml`, `enterprise_adoption_slo_release_governance_attached` with 5/5 release gates attached |
| Freshness response SLO drift suppression policy coverage release gate enterprise adoption SLO release governance drill | `platform/operations/reports/product-readiness-freshness-response-slo-drift-suppression-policy-coverage-release-gate-enterprise-adoption-slo-release-governance-drill-v1.yaml`, `passed` with 5/5 drill scenarios passed |
| Serving metrics | connected, 3 requests, 3 audit records, 0 errors, 0 audit failures |
| Governance response runbook | accepted through delivery state ledger and passed response drill |
| Product freshness response acceptance | accepted through delivery state ledger and passed response drill |
| Tenant safety | true, with 0 open incidents and 1 serving-access watch item |
| Follow-up | monitor enterprise release gate pattern adoption SLO release governance effectiveness |

Current enterprise solution blueprint intake:

| Scope | Value |
|---|---|
| Requests | 6 total |
| Ready for solution design | 6 requests: enterprise knowledge assistant, LMS at-risk prediction, support SLA risk, finance document intelligence, operations routing optimization and finance payment fraud scoring |
| Waiting work | 0 requests waiting for privacy review; 0 requests need platform runtime build |
| Non-LMS coverage | 5 requests across AI Platform, support, finance and operations |
| Team workstreams | PO/BA, SA AI Platform and SA AI Engineer actions are generated per request |

Current validated model evidence:

| Model | Product | Status |
|---|---|---|
| `recommendation-item-cf-v1` | `lms-courseflow` | active baseline with executable offline ranking eval |
| `sequence-risk-baseline-v1` | `lms-courseflow` | Sequence Risk Service route with policy-enforced grants, HITL routing and executable golden eval |
| `finance-document-intelligence-baseline-v1` | `billing-finance` | OCR-token Media Intelligence Service route with privacy guardrail eval |
| `finance-payment-fraud-baseline-v1` | `billing-finance` | Payment Fraud Service route plus Graph Entity Service evidence route with policy-enforced grants, entity-link evidence, HITL payment-action guardrails and executable golden eval |
| `operations-demand-forecast-baseline-v1` | `enterprise-operations` | Forecasting Service route with capacity gap, scenario actions, HITL capacity guardrails and executable golden eval |
| `causal-uplift-baseline-v1` | `ai-platform` and `lms-courseflow` | Causal Uplift Service route with aggregate-only snapshots, tenant grants, guardrail/HITL rollout review and executable eval |
| `support-agent-assist-baseline-v1` | `support-platform` | non-LMS baseline with executable golden eval |
| `support-sla-risk-baseline-v1` | `support-platform` | non-LMS classical SLA breach risk runtime library with reason-code eval |
| `speech-quality-baseline-v1` | `support-platform` and `lms-courseflow` | transcript-segment Media Intelligence Service route with privacy guardrail eval |
| `operations-routing-policy-simulator-v1` | `enterprise-operations` | Routing Policy Service route with tenant grants, direct-identifier rejection, constraint HITL guardrails and offline policy eval |

Current shared serving facade:

| Capability | Evidence |
|---|---|
| Manifest-backed model dispatch | `platform/src/courseflow_ai_platform/model_serving.py` |
| Runtime methods | `predict`, `recommend`, `assist` |
| Response envelope | model ID, artifact ID, manifest path, method, latency, output and human-review flag |
| Gateway envelope | request ID, tenant ID, model ID, status, fallback/error metadata and per-model counters |
| Audit hook | optional `ModelAuditStore`, audit retention days, fail-open/fail-closed mode and audit record/failure metrics |
| Hosted adapter | framework-neutral handlers for `/v1/models`, `/v1/model-invocations`, `/v1/model-serving/metrics`, `/v1/model-serving/health` and `/v1/model-serving/cockpit` |
| Service package | `services/model-serving-service` packages the adapter as a policy-enforced CLI/HTTP service boundary |
| LLM adapter package | `services/llm-adapter-service` packages provider-neutral GenAI/LLM generation behind Prompt Gateway, provider grants, health and metrics routes |
| Metrics export | `platform/operations/reports/model-serving-metrics-export-v1.yaml` persists adapter metrics for the operating cockpit |
| Serving auth | optional `ServingAuthPolicy` enforces route scopes, tenant isolation, model allowlists and wildcard-scope rejection |
| Access policy | `platform/governance/policies/model-serving-access-policy.yaml` maps service principals to product, tenant, scope and model grants |
| Access review | `platform/governance/requests/model-serving-access-requests.yaml` and `platform/governance/reports/model-serving-access-review-v1.yaml` gate serving access changes before policy apply |
| Policy patch plan | `platform/governance/reports/model-serving-access-policy-patch-plan-v1.yaml` produces a reviewable proposed policy from approved ready requests |
| Apply ledger | `platform/governance/ledgers/model-serving-access-policy-apply-ledger.yaml` records reviewer identity, timestamps and policy checksums before apply |
| Controlled applier | `platform/governance/reports/model-serving-access-policy-apply-report-v1.yaml` proves readiness and requires an explicit target path before writing proposed policy |
| Reconciliation | `platform/governance/reports/model-serving-access-policy-reconciliation-v1.yaml` compares active policy checksum with source/proposed ledger checksums |
| Incident export | `platform/governance/reports/model-serving-access-incident-export-v1.yaml` turns drift, blocked, stale and pending apply conditions into tenant-safe Admin/Ops handoffs |
| Security telemetry | auth denials are counted by bounded reason, route and status code without raw principal, tenant or token values |
| Tests | `platform/tests/test_model_serving.py`, `platform/tests/test_model_serving_adapter.py`, `platform/tests/test_model_serving_auth.py`, `platform/tests/test_serving_metrics_export.py`, `services/model-serving-service/tests/test_service_contract.py`, `platform/tests/test_serving_access_review.py`, `platform/tests/test_serving_access_policy_plan.py`, `platform/tests/test_serving_access_apply_ledger.py`, `platform/tests/test_serving_access_policy_applier.py`, `platform/tests/test_serving_access_policy_reconciliation.py`, `platform/tests/test_serving_access_incidents.py`, `platform/tests/test_model_audit.py` |

Current model serving access review:

| Scope | Value |
|---|---|
| Requests | 5 total |
| Applied | 2 grants already match active policy |
| Ready for apply | 1 LMS sandbox tenant expansion |
| Needs approval | 1 Enterprise Operations ops-observability scope request needs PO/BA and Admin/Ops approval |
| Blocked | 1 Finance request for Support-owned SLA model is blocked as cross-product access |
| Risk queue | 2 critical, 2 high, 1 medium |

Current model serving policy patch plan:

| Scope | Value |
|---|---|
| Ready requests planned | 1 |
| Operation | merge `tenant-lms-sandbox` into `service:lms-courseflow-serving` |
| Skipped non-ready requests | 4 |
| Proposed principals | 5 |
| Safety behavior | active policy remains unchanged until Admin/Ops accepts the proposal |

Current model serving apply ledger:

| Scope | Value |
|---|---|
| Applications | 1 |
| Ready to apply | 1 approved application for LMS sandbox tenant |
| Pending review | 0 |
| Blocked | 0 |
| Checksum mismatches | 0 |
| Safety behavior | source and proposed policy checksums must match before apply |

Current model serving controlled apply report:

| Scope | Value |
|---|---|
| Apply status | `ready_to_write` |
| Ready applications | 1 |
| Planned operations | 1 |
| Active policy would change | yes, LMS sandbox tenant would be added |
| Safety behavior | CLI report path does not mutate active policy; write API requires an explicit target path |

Current model serving policy reconciliation:

| Scope | Value |
|---|---|
| Applications | 1 |
| Pending apply | 1 |
| Reconciled | 0 |
| Ledger update required | 0 |
| Drift | 0 |
| Next action | run controlled policy applier for the LMS sandbox tenant proposal |

Current model serving access incident export:

| Scope | Value |
|---|---|
| Incidents | 1 tenant-safe handoff |
| Open | 0 |
| Watch | 1 pending policy apply |
| Stale pending apply | 0 at 2026-06-17 |
| P0/P1/P2 split | 0 / 0 / 1 |
| Safety behavior | application refs are hashed and raw tenant, principal, request and credential values are omitted |

Current model audit capability:

| Capability | Product | Status |
|---|---|---|
| `model-audit` | `ai-platform` | sanitized prediction audit ledger with payload/output hashes, artifact lineage, JSONL persistence, gateway audit hook, tenant export/delete and retention purge |

Current validated vector-index artifact evidence:

| Artifact | Product | Status |
|---|---|---|
| `course-content-vector-index-baseline-v1` | `lms-courseflow` | snapshot manifest with corpus/schema/eval lineage and sha256 hash |
| `support-knowledge-vector-index-baseline-v1` | `support-platform` | snapshot manifest with corpus/schema/eval lineage and sha256 hash |

Current artifact promotion evidence:

| Promotion | Product | Status |
|---|---|---|
| `recommendation-item-cf-v1-active-baseline` | `lms-courseflow` | active baseline with rollback target and eval gate |
| `support-agent-assist-baseline-approved` | `support-platform` | approved baseline with human-review guardrail gates |
| `course-content-vector-index-shadow` | `lms-courseflow` | shadow vector index with contract and hybrid retrieval gates |
| `support-knowledge-vector-index-shadow` | `support-platform` | shadow vector index with contract and hybrid retrieval gates |

Current promotion readiness projection:

| Scope | Value |
|---|---|
| Promotions | 4 total: 1 active, 1 approved, 2 shadow |
| Readiness | 4 ready, 0 blocked |
| Gates | 7 required gates, 7 ready |
| Freshness | gate evidence max age 30 days, artifact max age 90 days, 0 stale gates/artifacts |
| Rollback | 2 rollback-required promotions, 2 rollback-ready |
| Non-LMS coverage | 2 support-platform promotions use the same release path |
| Action queue | 1 active monitoring, 1 ready to activate, 2 keep shadow, 0 blocked |

Current promotion request intake:

| Scope | Value |
|---|---|
| Requests | 5 total |
| Ready for approval | 3 requests: support-platform activation, finance document intelligence privacy request and operations-routing simulator shadow promotion |
| Waiting work | 2 requests waiting for artifact, evaluation or privacy review |
| Non-LMS coverage | 4 requests across support, finance and operations |

Current executable retrieval gates:

| Gate | Product | Status |
|---|---|---|
| `course-content-retrieval` | `lms-courseflow` | lexical retrieval baseline for semantic search/RAG |
| `support-knowledge-retrieval` | `support-platform` | lexical retrieval baseline for agent-assist/RAG |

Current retrieval service package:

| Capability | Evidence |
|---|---|
| Service boundary | `services/retrieval-service` |
| Routes | collection catalog, search, health and metrics |
| Modes | lexical, vector and hybrid |
| Access policy | `platform/governance/policies/retrieval-access-policy.yaml` grants principals by scope, tenant and collection |
| Current collections | `course_content_chunks` and `support_knowledge_articles` |
| Tenant safety | tenant-private chunks are filtered before ranking output |
| Tests | `platform/tests/test_retrieval_service.py`, `services/retrieval-service/tests/test_service_contract.py` |

Current RAG answer service package:

| Scope | Value |
|---|---|
| Service boundary | `services/rag-answer-service` |
| Routes | answer, health, metrics |
| Consumers | LMS RAG Tutor, Support Agent Assist, Enterprise Knowledge Assistant |
| Policy | `platform/governance/policies/rag-answer-access-policy.yaml` |
| Runtime module | `platform/src/courseflow_ai_platform/rag_answer_service.py` |
| Tests | `platform/tests/test_rag_answer_service.py`, `services/rag-answer-service/tests/test_service_contract.py` |

Current executable vector-index contract gates:

| Gate | Product | Status |
|---|---|---|
| `course-content-vector-index` | `lms-courseflow` | deterministic vector index contract for course chunks, dimensions, metadata, checksum and tenant scope |
| `support-knowledge-vector-index` | `support-platform` | deterministic vector index contract for support knowledge chunks, dimensions, metadata, checksum and tenant scope |

Current executable hybrid retrieval shadow gates:

| Gate | Product | Status |
|---|---|---|
| `course-content-hybrid-retrieval` | `lms-courseflow` | lexical + vector shadow gate requiring no regression from lexical recall and tenant isolation |
| `support-knowledge-hybrid-retrieval` | `support-platform` | lexical + vector shadow gate requiring no regression from lexical recall and tenant isolation |

Current executable grounded-answer gates:

| Gate | Product | Status |
|---|---|---|
| `course-rag-answer` | `lms-courseflow` | citation, grounding, refusal and tenant-private guardrail baseline |
| `support-rag-answer` | `support-platform` | citation, grounding, refusal and safe agent-assist baseline |

Current executable prompt-safety gate:

| Gate | Product | Status |
|---|---|---|
| `prompt-safety` | `ai-platform` | runtime gateway plus redaction, tenant context filtering, audit safety, cost budget and HITL baseline |
| `llm-adapter-shadow-gateway` | `ai-platform` | Prompt Gateway pre-call check, blocked generation skip, grounded cited answer and tenant-safe context filter |

Current prompt gateway service package:

| Capability | Evidence |
|---|---|
| Service boundary | `services/prompt-gateway-service/service.yaml` |
| Runtime | `platform/src/courseflow_ai_platform/prompt_gateway_service.py` and `services/prompt-gateway-service/src/courseflow_prompt_gateway_service/service.py` |
| Routes | `POST /v1/prompt-gateway/evaluate`, `GET /v1/prompt-gateway/health`, `GET /v1/prompt-gateway/metrics` |
| Policy | `platform/governance/policies/prompt-gateway-access-policy.yaml` scopes principals by product, use case and tenant |
| Tests | `services/prompt-gateway-service/tests/test_service_contract.py` |

Current LLM adapter service package:

| Capability | Evidence |
|---|---|
| Service boundary | `services/llm-adapter-service/service.yaml` |
| Runtime | `platform/src/courseflow_ai_platform/llm_provider_adapter.py` and `services/llm-adapter-service/src/courseflow_llm_adapter_service/service.py` |
| Routes | `POST /v1/llm-adapter/generate`, `GET /v1/llm-adapter/health`, `GET /v1/llm-adapter/metrics` |
| Policy | `platform/governance/policies/llm-adapter-access-policy.yaml` scopes principals by product, use case, tenant and provider |
| Provider ops | `platform/governance/policies/llm-provider-ops-policy.yaml` configures provider rate limits, timeouts, circuit breakers and failover |
| Credential readiness | `platform/governance/reports/llm-provider-readiness-v1.yaml` blocks plaintext live credentials and reports contract-stub or live provider readiness |
| Runtime probes | `platform/operations/reports/llm-provider-runtime-probes-v1.yaml` reports secret probe, egress, cost and latency rollout evidence |
| Provider alert routing | `platform/operations/reports/llm-provider-alert-routing-v1.yaml` validates tenant-safe alert routes, Admin/Ops sink ownership, threshold refs and rotation evidence stance |
| Provider secret rotation | `platform/governance/reports/llm-provider-secret-rotation-v1.yaml` validates secret-manager binding, runtime secret resolution, rotation automation, evidence refs and no plaintext secret leakage |
| Provider alert projection | `platform/operations/reports/operating-cockpit-v1.yaml`, `platform/delivery/reports/delivery-backlog-v1.yaml` and `platform/operations/reports/admin-ops-dashboard-v1.html` surface `llm_provider_ops`, alert routing status and the Admin/Ops alert delivery drill |
| Gateway | every generation calls Prompt Gateway first and skips provider generation when blocked |
| Tests | `platform/tests/test_llm_provider_adapter.py`, `platform/tests/test_llm_provider_readiness.py`, `platform/tests/test_llm_provider_runtime_probes.py` and `services/llm-adapter-service/tests/test_service_contract.py` |

Current prompt audit capability:

| Capability | Product | Status |
|---|---|---|
| `prompt-audit` | `ai-platform` | sanitized audit ledger with hashes, JSONL persistence, tenant export/delete and retention purge |

## CourseFlow AI Mentor

Use case lớn để học và áp dụng nhiều họ AI là `CourseFlow AI Mentor`: một trợ lý học tập thích ứng cho LMS.

Capability chính:

| Module | Tính năng | Họ AI |
|---|---|---|
| M1 | Recommendation nâng cấp | item-CF, ALS/BPR, two-tower, SASRec |
| M2 | Semantic search và cold-start | embeddings, vector search |
| M3 | Learner at-risk prediction | logistic/XGBoost, LSTM/GRU |
| M4 | Knowledge tracing | DKT, SAKT, transformer |
| M5 | Adaptive learning path | optimization, contextual bandit, RL |
| M6 | Auto-grading và feedback | LLM, rubric prompting |
| M7 | AI Tutor course Q&A | RAG, LLM |
| M8 | Quiz/flashcard generation | GenAI |
| M9 | Video transcript và summary | ASR, NLP, LLM |
| M10 | AI governance platform | registry, eval, monitoring, audit |

## Roadmap

Phase 0 - Platform structure:

- Chuẩn hóa folder `ai/`.
- Tạo product brief, architecture, use-case registry, feature/model contracts.
- Tạo agent operating model, enterprise backlog, readiness assessment và implementation plan.
- Giữ recommendation service hiện tại làm service đầu tiên dưới `services/`.

Phase 1 - High ROI AI:

- Semantic search/course embeddings.
- Auto-grading human-in-the-loop.
- At-risk prediction baseline classical ML.
- Model cards, quality gates, evaluation report.

Phase 2 - Deep learning core:

- Recommendation: ALS/BPR -> two-tower hoặc SASRec.
- Learner-risk sequence model khi có đủ clickstream.
- RAG Tutor dùng embeddings từ Phase 1.

Phase 3 - Advanced EdTech AI:

- Knowledge tracing DKT/SAKT.
- Adaptive path bằng contextual bandit.
- Quiz/flashcard generation, video transcript/summary.

Phase 4 - Enterprise hardening:

- Online feature store, canary/shadow serving, drift incident workflow, cost governance.

## Current Production Code

Service đang có đã được đặt lại vào:

```text
ai/services/recommendation-ml-service/
```

Service này hiện mạnh ở MLOps: FastAPI, Postgres repository, migrations, model registry, quality gate, activation governance, internal JWT, telemetry và ops smoke. Thuật toán hiện tại là item-item collaborative filtering cổ điển, dùng làm baseline để nâng cấp lên các model mới.
