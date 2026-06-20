# AI Platform Agent Operating Model

Tài liệu này định nghĩa đội agent chịu trách nhiệm đưa `ai/` từ một recommendation ML service cổ điển thành AI Platform enterprise-ready cho CourseFlow LMS và các use case tương lai.

## Mission

Đội agent có nhiệm vụ chuyển hóa nhận xét ban đầu thành execution system:

- Hiện trạng: `recommendation-ml-service` mạnh về MLOps/serving/governance nhưng thuật toán chỉ là item-item collaborative filtering viết tay, chưa có deep learning, embeddings, RAG, LLM, feature store hay model artifact serving lớn.
- Đích đến: AI Platform enterprise-ready, demo-scale, có thể xử lý nhiều bài toán LMS và nhiều họ AI qua cùng lifecycle.

## Agent Team

| Agent | Role | Primary accountability | Key artifacts |
|---|---|---|---|
| PO/BA Agent | Product owner and business analyst | Chuyển pain point LMS thành feature, backlog, KPI, acceptance criteria | `docs/product/*`, `use-cases/*`, `products/lms-courseflow/*` |
| SA AI Platform Agent | Solution architect for AI platform | Thiết kế platform capabilities, boundaries, readiness gates, governance | `docs/architecture/*`, `platform/*`, `contracts/*` |
| SA AI Engineer Agent | AI engineer and MLOps architect | Thiết kế model archetypes, training/eval/serving path, dependency and test strategy | `models/*`, `features/*`, `pipelines/*`, `services/*` |
| Data Platform Liaison | DP integration owner | Bảo đảm AI dùng governed features từ `dp`, không tự tạo data truth | `contracts/features/*`, `features/*`, `pipelines/materialization/*` |
| AI Governance Reviewer | Risk, safety and operations reviewer | Privacy, HITL, activation, rollback, audit, LLM safety, drift/cost policy | `platform/governance/*`, `runbooks/*` |

## RACI

| Workstream | PO/BA | SA Platform | SA AI Engineer | DP Liaison | Governance |
|---|---|---|---|---|---|
| Use case discovery | A/R | C | C | C | C |
| Solution blueprint intake | A/R | A/R | R | C | C |
| Product backlog and KPI | A/R | C | C | I | C |
| Platform architecture | C | A/R | R | C | C |
| Feature contracts | C | C | R | A/R | C |
| Model IO contracts | C | A | R | C | C |
| Model implementation | I | C | A/R | C | C |
| Evaluation gates | C | A | R | C | R |
| Activation approval | I | A | R | I | A/R |
| Runbooks and incident response | I | R | R | C | A/R |

`A` = accountable, `R` = responsible, `C` = consulted, `I` = informed.

## Operating Cadence

| Cadence | Owner | Output |
|---|---|---|
| Weekly product triage | PO/BA | Use case priority, KPI, acceptance criteria update |
| Weekly architecture review | SA Platform | Boundary, contract, capability maturity decision |
| Weekly data contract review | Data Platform + SA AI Engineer | Contract coverage, freshness, parity and production hardening queue |
| Per-model design review | SA AI Engineer | Model card draft, data needs, eval plan, dependency plan |
| Release readiness review | SA Platform + Governance | Quality gate evidence, approval, rollback plan |
| Weekly operating cockpit review | SA Platform + Admin/Ops | Delivery health, release health and cross-role next-action queue |
| Weekly delivery backlog review | PO/BA + SA Platform | Backlog priority, owner role, SLA, acceptance criteria and blocked/monitoring split |
| Weekly owner queue review | PO/BA + SA Platform + SA AI Engineer | Owner alias load, overloaded queues, due-soon work and monitoring review dates |
| Weekly runtime roadmap review | SA Platform + SA AI Engineer | Runtime gaps, first runtime candidates, artifact/eval/serving next actions |
| Monthly platform maturity review | Full team | Readiness score, gaps, next enterprise hardening slice |

## Decision Gates

No AI module moves forward unless it passes these gates:

1. Product gate: user, pain point, KPI and success metric are defined.
2. Data gate: feature contract, source owner, freshness and privacy classification exist.
3. Model gate: baseline, model IO contract, eval metric and model card exist.
4. Governance gate: approval, HITL if needed, retention, audit and rollback policy exist.
5. Serving gate: latency, fallback, observability and cost/drift strategy exist.

## Team Backlog Workflow

```text
expert finding
-> PO/BA frames product capability
-> SA Platform maps platform capability and enterprise gates
-> SA AI Engineer maps model archetype and implementation path
-> solution blueprint intake publishes blockers and role workstreams
-> DP Liaison binds feature/data contract
-> Governance Reviewer defines approval/safety/audit
-> module enters roadmap phase
-> delivery SLA and owner views expose accountable execution
-> runtime roadmap selects the next artifact/eval/serving slice
```

## First Enterprise Push

The team should start with Phase 1 because it fills the biggest gaps with high ROI:

1. Semantic search/course embeddings: fixes cold-start and creates vector/RAG foundation.
2. Auto-grading human-in-the-loop: introduces LLM, rubric prompting, HITL and audit.
3. At-risk baseline: introduces feature engineering, supervised ML and explainable intervention.
4. Recommendation upgrade design: keeps item-CF as baseline and prepares ALS/BPR/two-tower/SASRec.
