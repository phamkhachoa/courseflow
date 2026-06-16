# Data Platform Agent Operating Model

Status: active working model

## Purpose

The group-wide enterprise data platform is broad enough to require a small delivery organization, not
a single developer thread. This model defines how senior agents collaborate without turning `df/` into
a collection of disconnected product-specific experiments.

## Core Team

| Role | Primary Accountability | Typical Ownership |
|---|---|---|
| Lead SA / Data Platform Architect | Target architecture, tradeoff decisions, ADRs, production gates. | `df/docs/architecture`, `df/docs/adr`, stack decisions. |
| Product Onboarding SA | Product boundary, source-system onboarding, reusable templates. | `df/products/**`, `df/templates/**`. |
| Senior Data Engineer - Ingestion | Event/topic contracts, CDC/outbox mapping, Bronze onboarding. | `df/contracts/events`, `df/contracts/topics`, ingestion specs. |
| Senior Data Engineer - Lakehouse | Bronze/Silver/Gold transforms, snapshots, manifests, backfill logic. | `df/src/enterprise_df/pipelines`, `df/domains/*/pipeline.md`. |
| Senior Backend Engineer | Source-system mapping, outbox/event producer alignment, service integration. | `df/platform/ingestion/source-systems.md`, backend mapping docs. |
| Senior SRE / DataOps | SLOs, observability, release evidence, runbooks, environment gates. | `df/platform/observability`, `df/platform/environments`, runbooks. |
| Security / Governance SA | PII, masking, tenant isolation, retention, access audit, catalog policy. | `df/platform/security`, `df/platform/governance`. |
| PO / BA | Data product value, business use cases, metric definitions, release priority. | `df/domains/*/README.md`, use-case backlog. |
| QA / Data Quality Engineer | Contract checks, quality gates, regression checks, bad-record scenarios. | `df/tests`, `df/platform/quality`. |

## Work Allocation Rules

- Every task has a named role and file ownership before implementation starts.
- Workers must not edit files outside their assigned ownership unless explicitly asked.
- Shared decisions go through ADRs before implementation broadens.
- Contracts are central and must pass `make check`.
- Product-specific mapping goes under `products/<product-code>/`; platform capability files go under
  `platform/`; enterprise domain semantics go under `domains/`.
- Runtime code and tooling go under `src/enterprise_df/`; sample inputs go under `samples/`.

## Review Loop

1. SA frames the decision or implementation slice.
2. PO/BA confirms business value and priority.
3. DE/BE/SRE workers implement disjoint slices in parallel.
4. Lead SA integrates results and resolves conflicts.
5. `make check` must pass before the slice is considered merged locally.
6. Production readiness is assessed against contracts, quality, observability, security and rollback.

## Current Delivery Squad

| Agent Role | Active Slice | Write Scope |
|---|---|---|
| Enterprise Data Platform Architect | Group-wide platform scope and structure guardrails. | `df/docs/architecture/**`, `df/docs/adr/**`, `df/src/enterprise_df/structure.py`. |
| PO / BA | Enterprise capability map and product onboarding use cases. | `df/docs/**`, `df/products/**`, `df/domains/**`. |
| Senior Data Engineer - Ingestion | P0 contracts for enrollment, course and gradebook events. | `df/contracts/**`, targeted tests. |
| Senior Data Engineer - Lakehouse | Local recommendation pipeline skeleton and manifest. | `df/src/enterprise_df/pipelines/**`, `df/samples/**`, pipeline tests. |
| Senior SRE / DataOps | P0 production SLO and release-gate specs. | `df/platform/observability/**`, `df/platform/environments/**`. |

## Merge Criteria For P0

- Source events have schema contracts.
- Bronze/Silver/Gold data products have owners, privacy classification and quality gates.
- Pipeline code emits reproducible snapshot manifests.
- Production gates document freshness, quality, lineage and rollback evidence.
- Tests prove the validator catches missing structure and broken contracts.
