# 0025 Delivery Owner Views

Date: 2026-06-17

## Decision

Add owner-specific delivery views on top of the AI Platform delivery SLA report.
The platform now groups every backlog item by owner alias and exposes queue
load, SLA status, next due date and monitoring review date.

## Why

The AI Platform already proves coverage across classical ML, deep learning,
NLP/transformers, GenAI/LLM, RAG, CV, speech, RL and extended enterprise
modules. Execution still needs a role-friendly view so PO/BA, SA AI Platform,
SA AI Engineer, Governance and Admin/Ops know what each owner must move next.

## Artifacts

| Artifact | Path |
| --- | --- |
| Owner views projection | `platform/src/courseflow_ai_platform/delivery_owner_views.py` |
| Owner views report | `platform/delivery/reports/delivery-owner-views-v1.yaml` |
| Tests | `platform/tests/test_delivery_owner_views.py`, `platform/tests/test_cli.py` |
| CLI output | `deliveryOwnerViews` top-level key and optional report writer |

## Current Owner Health

| Scope | Value |
| --- | --- |
| Owner aliases | 7 |
| Items | 19 |
| Due-soon owner queues | 5 |
| Monitoring owner queues | 2 |
| Overloaded owner queues | 1 |
| Overdue owner queues | 0 |
| Missing owner aliases | 0 |
| Top owner queue | `sa-ai-platform` |

## Owner Queues

| Owner alias | Items | Due soon | On track | Monitoring | Next due | Next review |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `sa-ai-platform` | 6 | 6 | 0 | 0 | 2026-06-20 |  |
| `sa-ai-engineering` | 4 | 2 | 0 | 2 | 2026-06-20 | 2026-06-24 |
| `data-platform-product-owner` | 3 | 0 | 3 | 0 | 2026-06-27 |  |
| `sa-ai-platform-governance` | 3 | 3 | 0 | 0 | 2026-06-20 |  |
| `admin-ops` | 1 | 0 | 0 | 1 |  | 2026-06-18 |
| `admin-ops-governance` | 1 | 1 | 0 | 0 | 2026-06-20 |  |
| `ai-governance-reviewer` | 1 | 1 | 0 | 0 | 2026-06-20 |  |

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can see which owner queue constrains business delivery |
| SA AI Platform | Can balance platform-runtime and governance reviews |
| SA AI Engineer | Can prioritize evaluation, artifact, simulator and shadow-monitoring work |
| Governance Reviewer | Can separate privacy due-soon work from platform/governance joint review |
| Admin/Ops | Can render per-owner delivery views without recomputing SLA logic |

## Next Moves

1. Render owner views in the Admin/Ops dashboard.
2. Add persisted backlog state transitions so due dates age from item creation.
3. Add escalation report once an owner queue has overdue work.
