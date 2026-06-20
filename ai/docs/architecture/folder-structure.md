# AI Folder Structure

`ai/` is organized by enterprise responsibility rather than by algorithm only.

## Canonical Tree

```text
ai/
  docs/              Human-readable product and architecture decisions
    team/            Agent operating model and delivery cadence
  products/          Product-specific onboarding, starting with LMS
  use-cases/         Use case portfolio and module-level definition of done
  model-families/    Learning map for AI families and when to apply them
  models/            Model archetypes with train/predict/evaluate shape
  features/          Offline/online feature store direction
  pipelines/         Training, evaluation, scoring, materialization
  contracts/         Feature and model contracts
  platform/          Reusable platform capabilities and policies
    coverage/        Business capability coverage, module catalog, capability taxonomy and runtime roadmap
    data-contracts/  Data domain to feature/document contract coverage
    delivery/        Delivery backlog, persisted state ledger, SLA policy, owner routing and owner views
    intake/          Product front door requests and solution blueprint reports
    operations/      Admin/Ops cockpit, rendered dashboard and control-plane projections
  services/          Runtime AI services
  runbooks/          AI operation runbooks
```

## Ownership

| Folder | Owner role | Change trigger |
|---|---|---|
| `docs/product` | PO/BA | New business outcome or roadmap change |
| `docs/architecture` | SA AI Platform | Boundary, lifecycle or platform decision |
| `docs/team` | PO/BA + SA AI Platform | Agent responsibilities, cadence, RACI, decision gates |
| `products` | Product owner + SA | Product onboarding or integration scope |
| `use-cases` | PO/BA + AI Engineer | New AI module or KPI change |
| `model-families` | AI Engineer | New algorithm family or learning path |
| `platform/coverage` | PO/BA + SA AI Platform | Business coverage, taxonomy proof, runtime status or roadmap gap changes |
| `platform/data-contracts` | Data Platform + SA AI Engineer | New data-domain contract, design-ready status or production-readiness gate |
| `platform/delivery` | PO/BA + SA AI Platform + Admin/Ops | Delivery backlog, SLA policy, owner views, status, priority and acceptance criteria |
| `platform/intake` | PO/BA + SA AI Platform + SA AI Engineer | New use-case request, solution blueprint, blocker or role workstream |
| `platform/operations` | SA AI Platform + Admin/Ops | Combined delivery health, release health, next-action projection and rendered dashboard artifact |
| `models` | AI Engineer | New model archetype or experiment promoted to reusable shape |
| `features` | AI Engineer + Data Platform | Offline/online feature materialization design |
| `pipelines` | AI Engineer + MLOps | Training, eval, scoring or materialization workflow |
| `contracts` | AI Engineer + Data Platform | Feature/model schema or SLA change |
| `platform` | SA AI Platform + MLOps | Governance, lifecycle, eval, serving policy |
| `services` | AI Engineer | Runtime implementation |
| `runbooks` | SRE + AI Engineer | Incident or release operation |

## Promotion Path

```text
idea
-> platform/intake request
-> solution blueprint report
-> docs/product brief
-> use-cases registry entry
-> contracts/features and contracts/models
-> platform/evaluation quality gate
-> experiment or baseline
-> models archetype
-> pipelines training/evaluation workflow
-> services runtime implementation
-> model registry activation
```
