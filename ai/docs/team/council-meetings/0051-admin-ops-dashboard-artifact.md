# Council 0051: Admin/Ops Dashboard Artifact

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The AI Platform now publishes a rendered Admin/Ops dashboard artifact as static HTML. The dashboard combines the operating cockpit, Admin/Ops owner queues and serving-access incident rollups into one human-readable page without requiring a runtime server.

The platform added:

- `AdminOpsDashboardArtifact`
- renderer `platform/src/courseflow_ai_platform/admin_ops_dashboard.py`
- HTML artifact `platform/operations/reports/admin-ops-dashboard-v1.html`
- CLI flag `--write-admin-ops-dashboard`
- tests for current dashboard rendering and stale serving-access incident rendering

## Current Dashboard State

| Scope | Value |
|---|---:|
| Platform status | attention_required |
| Delivery status | ready_work_available |
| Release status | release_ready |
| Serving status | metrics_not_connected |
| Serving access status | pending_policy_apply |
| Owner queues | 7 |
| Admin/Ops delivery items | 3 |
| Open serving-access incidents | 0 |
| Watch serving-access incidents | 1 |

## Guardrails

- Dashboard rendering escapes report values before writing HTML.
- Raw backlog refs are not rendered in the dashboard work list; delivery rows use backlog ID and safe action label.
- Serving-access incident rows use hashed `application:` refs from the incident export.
- Current watch/P2 incidents are visible in the incident export panel but do not become open Admin/Ops owner handoffs.
- The artifact is generated from validated reports instead of bespoke dashboard state.

## Next Step

Completed in Council 0052: add a lightweight dashboard freshness manifest so Admin/Ops can see which source report snapshots and generation timestamp produced the rendered HTML.
