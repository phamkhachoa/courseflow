# AI Mentor Enterprise Backlog

This backlog converts the expert review into enterprise-grade LMS capabilities. It assumes a deliberate learning goal: some modules are over-engineered for a small LMS, but each teaches a real AI platform discipline.

## Expert Finding To Product Response

| Finding | Product response |
|---|---|
| Current service has no deep learning | Add deep learning roadmap through sequential recommendation, learner sequence risk and knowledge tracing |
| Current algorithm is only item-item CF | Keep it as baseline and add ALS/BPR, embeddings, two-tower and SASRec stages |
| MLOps/governance is stronger than model layer | Reuse registry, activation, quality gate and audit as the paved road for new modules |
| LMS has rich text/content opportunities | Add semantic search, content cold-start and RAG Tutor |
| Enterprise readiness needs feature store and AI observability | Add feature contracts, online/offline feature direction, drift/cost/quality monitoring |

## Enterprise Epics

### Epic A: AI Platform Foundation

Outcome: all AI modules use a common lifecycle and enterprise gates.

Capabilities:

- Use case registry.
- Feature contracts.
- Model IO contracts.
- Quality gates and evaluation reports.
- Model cards.
- Maker-checker activation.
- Audit, rollback and runbooks.

Acceptance criteria:

- Every module in the roadmap has an owner, phase, KPI and gate.
- No runtime service is created without feature/model contracts.
- Baseline comparison is required before advanced model activation.
- AI decisions are auditable with model version and reason/fallback metadata.
- Admin/Ops can inspect active model, candidate model, approval state, fallback state, cost and safety incidents.
- Tenant-scoped artifacts and audit evidence are mandatory for learner-impacting models.

### Epic B: Learning Discovery And Recommendation

Outcome: learner can discover the right course/lesson through behavior and content understanding.

Capabilities:

- Related-course recommendation baseline.
- Content embeddings for cold-start.
- Semantic search.
- Hybrid recommendation.
- Sequential recommendation with two-tower/SASRec.

Acceptance criteria:

- `IMPLICIT_ITEM_CF_V1` remains the baseline.
- Offline metrics include Recall@K and NDCG@K.
- Product metrics include CTR and enrollment conversion.
- Cold-start courses can be discovered before interaction data exists.
- Deep learning model cannot activate unless it beats baseline quality gate.
- Shadow compare and A/B test plans exist before online rollout.
- Catalog coverage and tenant isolation are measured.

### Epic C: AI Tutor And Content Intelligence

Outcome: learner can ask questions and practice from approved course content.

Capabilities:

- Course content chunking and vector index.
- RAG Tutor with citations.
- Quiz/flashcard generation.
- Lesson/video transcript and summary when media exists.

Acceptance criteria:

- Tutor answers include citations.
- Tutor refuses or asks for clarification when retrieval confidence is low.
- RAG eval covers groundedness, relevance, hallucination and citation precision.
- Generated quizzes are traceable to source content.

### Epic D: Assessment AI

Outcome: instructor gets AI assistance for grading and feedback without losing control of final grade.

Capabilities:

- Rubric-aware auto-grading.
- Suggested score and feedback.
- Instructor review queue.
- Agreement metrics against human grading.

Acceptance criteria:

- AI output is `suggested_grade`, not final grade, unless policy changes.
- Human approval is required for final grade.
- Audit stores rubric version, model version, confidence and reviewer decision.
- Agreement and rubric consistency pass quality gates.

### Epic E: Learner Success Intelligence

Outcome: instructor/admin can intervene early when learner is at risk.

Capabilities:

- At-risk baseline with classical ML.
- Sequence model when clickstream density is sufficient.
- Knowledge tracing when skill-level assessment data exists.
- Recommended intervention actions.

Acceptance criteria:

- Baseline model exists before LSTM/transformer.
- Output includes risk score, risk band, reason codes and recommended action.
- Metrics include AUC, precision@K, recall@K and false positive rate.
- Learner-impacting intervention requires human owner.

### Epic F: Adaptive Learning Path

Outcome: AI recommends the next best learning action safely.

Capabilities:

- Rule/greedy next action.
- Contextual bandit simulator.
- Online policy learning only after safety and traffic gates.

Acceptance criteria:

- No online RL without guardrails, off-policy evaluation and rollback.
- Policy recommendations are explainable.
- Exploration budget is bounded and auditable.

### Epic G: Enterprise LMS Compliance And Integration

Outcome: AI capabilities respect enterprise LMS interoperability, tenant isolation, accessibility, privacy and audit expectations.

Capabilities:

- Tenant-aware AI artifacts, vector collections, prompts, eval data and audit evidence.
- xAPI/Caliper event mapping for AI feedback loops.
- LTI/SCORM awareness for imported learning activities and external tool outcomes.
- SSO/SCIM/SIS dependency mapping for enterprise learner identity.
- Accessibility review for learner/admin AI UX.
- Privacy workflow for deletion/export requests affecting AI data and prompt logs.

Acceptance criteria:

- Every AI event and artifact carries tenant or product boundary metadata where applicable.
- AI data deletion/export procedure is documented before storing prompt/response or learner-level features.
- No cross-tenant retrieval, recommendation or prompt context is allowed.
- Admin/Ops evidence includes model version, source data window, approval actor, checker actor and rollback target.
- Accessibility critical issues for AI UX are zero before learner-facing release.

KPI:

- Tenant leakage incidents = 0.
- Compliance evidence coverage >= 95% for active AI modules.
- Deletion/export SLA is defined before production use.
- AI UX accessibility critical issue count = 0.

## Roadmap

| Phase | Goal | Modules | Enterprise gate |
|---|---|---|---|
| 0 | Foundation | folder structure, use-case registry, contracts, quality gates | artifact completeness |
| 1 | High ROI AI | semantic search, auto-grading, at-risk baseline | eval + governance |
| 2 | Deep learning core | two-tower/SASRec, learner sequence risk, RAG Tutor | artifact serving + quality |
| 3 | Advanced EdTech AI | knowledge tracing, adaptive path, quiz generation, ASR | data sufficiency + safety |
| 4 | Enterprise hardening | feature store online, canary/shadow, drift/cost monitoring | operational readiness |

## KPI Targets And Measurement

| KPI | Initial target | Measurement source | Cadence |
|---|---|---|---|
| Recommendation Recall@10 | Must not regress vs `IMPLICIT_ITEM_CF_V1` | offline eval set | per candidate |
| Recommendation CTR | monitor first, then improve after A/B baseline | `recommendation.tracking` | weekly |
| Search relevance@10 | >= 0.75 | curated search eval set | per index build |
| RAG groundedness | >= 0.85 | golden Q&A eval | per prompt/retriever release |
| RAG hallucination rate | <= 0.05 | golden Q&A + safety eval | per release |
| Auto-grading instructor agreement | >= 0.75 | instructor-reviewed submissions | per candidate |
| At-risk AUC | >= 0.70 | historical learner outcomes | per candidate |
| p95 online inference latency | per model contract | service telemetry | daily |
| Cost/request for LLM modules | budget threshold per module | provider usage + service metrics | daily |
| Tenant leakage incidents | 0 | security/audit tests and incidents | continuous |

## Definition Of Ready

A module is ready for implementation when:

- Product owner, user story, business KPI and learning outcome are defined.
- Feature contract and model IO contract exist.
- Data source, tenant boundary, PII class, retention and deletion/export impact are known.
- Baseline model or baseline heuristic is defined.
- Offline evaluation metric and quality gate are defined.
- Admin/Ops visibility and fallback behavior are defined.

## Definition Of Done

A module is done for enterprise-ready demo-scale when:

- Train/evaluate path is reproducible.
- Model card, eval report and quality gate evidence exist.
- Model activation uses maker-checker or documented HITL policy.
- Runtime output includes model version, confidence/score, reason/fallback metadata.
- Observability covers latency, error, fallback, cost where relevant and quality feedback.
- Tenant isolation, prompt/data retention and audit evidence are verified.
- Rollback path and runbook exist.

## Learning Outcomes

| Module | Builder learns |
|---|---|
| Semantic search | embeddings, vector DB, retrieval evaluation |
| Auto-grading | LLM prompting, structured output, HITL, safety audit |
| At-risk baseline | feature engineering, supervised ML, explainability |
| Sequential recommendation | PyTorch, sequence modeling, ranking metrics |
| RAG Tutor | retrieval, grounding, citations, LLM eval |
| Knowledge tracing | EdTech sequence modeling and transformer variants |
| Adaptive path | optimization, bandit/RL safety, policy evaluation |
