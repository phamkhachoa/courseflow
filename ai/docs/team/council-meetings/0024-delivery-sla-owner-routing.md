# 0024 Delivery SLA Owner Routing

Date: 2026-06-17

## Decision

Add delivery SLA and owner routing on top of the AI Platform delivery backlog.
Every backlog item gets an owner alias, escalation role, SLA status, due date or
monitoring review date.

## Why

The delivery backlog makes work visible. Enterprise execution also needs the
platform team to know which items are due soon, which are on track, which are
monitoring-only and whether any owner role is unmapped.

## Artifacts

| Artifact | Path |
| --- | --- |
| SLA policy | `platform/delivery/policies/sla-policy.yaml` |
| SLA projection | `platform/src/courseflow_ai_platform/delivery_sla.py` |
| SLA report | `platform/delivery/reports/delivery-sla-v1.yaml` |
| Tests | `platform/tests/test_delivery_sla.py`, `platform/tests/test_cli.py` |
| CLI output | `deliverySla` top-level key and optional report writer |

## Current SLA Health

| Scope | Value |
| --- | --- |
| Items | 19 |
| Tracked items | 16 |
| Monitoring items | 3 |
| Overdue | 0 |
| Due soon | 13 |
| On track | 3 |
| Missing owner aliases | 0 |

## Owner Routing

| Owner alias | Items |
| --- | --- |
| `sa-ai-platform` | 6 |
| `sa-ai-engineering` | 4 |
| `sa-ai-platform-governance` | 3 |
| `data-platform-product-owner` | 3 |
| `admin-ops` | 1 |
| `admin-ops-governance` | 1 |
| `ai-governance-reviewer` | 1 |

## SLA Policy

| Priority/status | Rule |
| --- | --- |
| P0 | Due in 1 day |
| P1 | Due in 3 days |
| P2 | Due in 10 days |
| P3 | Due in 20 days |
| Active monitoring | Review daily |
| Shadow monitoring | Review every 7 days |

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can see which business-facing work is due soon |
| SA AI Platform | Can route architecture/runtime work to named aliases |
| SA AI Engineer | Can prioritize evaluation, artifact and simulator work |
| Governance Reviewer | Can see due privacy and approval work |
| Admin/Ops | Can see monitoring review cadence |

## Next Moves

1. Add persisted backlog state transitions so SLA aging starts from actual
   creation time.
2. Add owner-specific views for the rendered Admin/Ops dashboard.
3. Add escalation report when an item becomes overdue.
