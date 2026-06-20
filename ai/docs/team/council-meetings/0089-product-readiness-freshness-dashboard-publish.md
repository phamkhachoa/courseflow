# Council 0089: Product Readiness Freshness Dashboard Publish

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| PO/BA | Let release stakeholders see AI Platform readiness freshness without opening YAML |
| SA AI Platform | Keep dashboard rendering snapshot-backed and avoid rerunning runtime probes on every page render |
| SA AI Engineer | Expose route freshness, runtime request count, audit count and AI spectrum coverage in one panel |
| Governance Reviewer | Keep the dashboard tenant-safe and limited to aggregate checks |
| Admin/Ops | Add the freshness report to dashboard source freshness tracking |

## Decision

Publish `ai-platform-product-readiness-freshness-v1` in the Admin/Ops dashboard. The
dashboard loads the checked-in freshness report, renders a Product Readiness Freshness panel
and adds that report to `admin-ops-dashboard-freshness-v1` source tracking. Runtime probing
remains owned by the freshness report writer so dashboard rendering stays deterministic.

## Runtime Evidence

| Surface | Result |
| --- | --- |
| Dashboard status card | Product Freshness shows `current` |
| Dashboard panel | Product Readiness Freshness lists route, checks, runtime request/audit counters and 8/8 AI spectrum coverage |
| Freshness manifest | Adds Product Readiness Freshness to dashboard source tracking |
| CLI output | `adminOpsDashboard` exposes product readiness freshness status, route status, request count and failed check count |
| Safety | Rendered dashboard contains only aggregate status, route and counter data |

## Outcome

Admin/Ops can now inspect AI Platform product readiness, freshness and runtime serving
evidence from the same dashboard. The remaining hardening step is to export stale or failed
product-readiness freshness checks as tenant-safe incidents.

## Next Step

Add a product-readiness freshness incident export so stale snapshots, route failures or audit
gaps can be routed to Admin/Ops owner views and SLA tracking.
