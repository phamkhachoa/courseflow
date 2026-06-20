# 0023 Platform Delivery Backlog

Date: 2026-06-17

## Decision

Add a delivery backlog projection that converts AI Platform operating cockpit
actions into trackable work items with owner role, priority, status, delivery
phase, references and acceptance criteria.

## Why

The operating cockpit tells the team what needs attention. The backlog turns
those actions into delivery work that PO/BA, SA AI Platform, SA AI Engineer,
Governance Reviewer, Data Platform and Admin/Ops can pick up without manually
reinterpreting the cockpit each week.

## Artifacts

| Artifact | Path |
| --- | --- |
| Backlog projection | `platform/src/courseflow_ai_platform/delivery_backlog.py` |
| Backlog report | `platform/delivery/reports/delivery-backlog-v1.yaml` |
| Tests | `platform/tests/test_delivery_backlog.py`, `platform/tests/test_cli.py` |
| CLI output | `deliveryBacklog` top-level key and optional report writer |

## Current Backlog

| Scope | Value |
| --- | --- |
| Items | 19 |
| Ready to start | 16 |
| Monitoring items | 3 |
| Blocked items | 0 |
| P1 items | 13 |
| P2 items | 6 |

## Source Breakdown

| Source | Items |
| --- | --- |
| Solution blueprint | 6 |
| Data contract coverage | 3 |
| Promotion intake | 5 |
| Promotion readiness | 4 |
| Serving health | 1 |

## Delivery Phases

| Phase | Purpose |
| --- | --- |
| Solution design | Publish architecture for ready use cases |
| Data contract hardening | Move draft contracts toward production readiness |
| Evaluation design/evidence | Create and run required gates |
| Governance review | Close privacy and approval work |
| Platform runtime build | Turn roadmap/gated taxonomy modules into implementation evidence |
| Runtime observability | Connect serving metrics and audit health into Admin/Ops visibility |
| Promotion/release operations | Review, activate, monitor and keep shadow evidence current |

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Sees business-facing work as backlog items rather than loose notes |
| SA AI Platform | Can prioritize platform runtime build and architecture work |
| SA AI Engineer | Can pick evaluation, artifact and simulator work with acceptance criteria |
| Governance Reviewer | Can track privacy and promotion approvals |
| Admin/Ops | Can track activation, active monitoring and shadow monitoring |

## Next Moves

1. Add backlog state transitions so completed work can update source registries.
2. Add owner-specific dashboard views using the SLA routing report.
3. Render the backlog beside the operating cockpit in an Admin/Ops dashboard.
