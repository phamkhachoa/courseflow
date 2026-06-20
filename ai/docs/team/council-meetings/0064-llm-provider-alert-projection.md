# Council 0064: LLM Provider Alert Projection

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Promote LLM provider runtime probe, cost and latency evidence from a standalone
report into the AI Platform operating cockpit, delivery backlog, owner views and
Admin/Ops dashboard. This keeps provider operations visible as platform product
work, not as an implementation detail of the LMS or adapter service.

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Cockpit projection | `platform/operations/reports/operating-cockpit-v1.yaml` |
| Delivery backlog item | `platform/delivery/reports/delivery-backlog-v1.yaml` |
| SLA and owner routing | `platform/delivery/reports/delivery-sla-v1.yaml` and `platform/delivery/reports/delivery-owner-views-v1.yaml` |
| Admin/Ops dashboard | `platform/operations/reports/admin-ops-dashboard-v1.html` |
| Projection builder | `platform/src/courseflow_ai_platform/operating_cockpit.py` |
| Dashboard renderer | `platform/src/courseflow_ai_platform/admin_ops_dashboard.py` |
| Backlog mapping | `platform/src/courseflow_ai_platform/delivery_backlog.py` |
| Tests | `platform/tests/test_operating_cockpit.py`, `platform/tests/test_delivery_backlog.py`, `platform/tests/test_delivery_sla.py`, `platform/tests/test_delivery_owner_views.py`, `platform/tests/test_admin_ops_dashboard.py`, `platform/tests/test_cli.py` |

## Guardrails

- Provider reports expose provider IDs, rollout status, cost micros and latency
  summaries only; no provider secret refs or prompt payloads are projected.
- Blocked runtime probes create P0 platform actions before live rollout.
- Missing cost or latency monitoring creates P1 runtime observability work.
- Contract-stub observable providers create a P2 Admin/Ops action to configure
  budget and latency alerts before live provider activation.
- Cockpit, backlog, SLA, owner views and dashboard must be regenerated from the
  same probe report to avoid manual drift.

## Product Impact

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | RAG Tutor and auto-grading inherit the same provider alert queue before live LLM rollout |
| Support Platform | Agent assist gets provider cost/latency readiness routed to Admin/Ops |
| Billing/Finance | Finance assistants inherit budget and latency alert governance before external model calls |
| AI Platform | Provider operations now appear in product cockpit, backlog, owner views and dashboard |

## Next Step

Completed in Council 0065: provider budget/latency alert routes are now
configured as policy and validated in a generated alert routing report.

Council 0066 added the secret rotation control plane. Next, enable a live
network provider only after approved secret-manager refs and rotation evidence
exist outside source control.
