# Council 0052: Admin/Ops Dashboard Freshness Manifest

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The Admin/Ops dashboard now has a freshness manifest. Admin/Ops can see whether the rendered HTML matches the current dashboard generator and which source report snapshots produced the view.

The platform added:

- `AdminOpsDashboardFreshnessManifest`
- `AdminOpsDashboardFreshnessSource`
- manifest `platform/operations/reports/admin-ops-dashboard-freshness-v1.yaml`
- CLI flag `--write-admin-ops-dashboard-freshness-manifest`
- tests for current, stale-source and writer scenarios

## Current Freshness State

| Scope | Value |
|---|---|
| Freshness status | `current` |
| Dashboard artifact | `platform/operations/reports/admin-ops-dashboard-v1.html` |
| Dashboard matches generated HTML | true |
| Source reports | 3 |
| Present sources | 3 |
| Current sources | 3 |
| Stale sources | 0 |
| Missing sources | 0 |

## Source Reports

| Source | Snapshot |
|---|---|
| Operating cockpit | `platform/operations/reports/operating-cockpit-v1.yaml` |
| Delivery owner views | `platform/delivery/reports/delivery-owner-views-v1.yaml` |
| Serving access incident export | `platform/governance/reports/model-serving-access-incident-export-v1.yaml` |

## Guardrails

- The manifest records `sha256` and byte count for the rendered dashboard.
- The manifest records `sha256`, byte count and `generated_at` for each source snapshot.
- If a source report is missing, stale or generated for a different date, freshness status is not `current`.
- If the dashboard file does not match the generator output for the same date, freshness status is not `current`.
- The manifest contains report paths, checksums and timestamps only; it does not duplicate raw tenant/principal values.

## Next Step

Completed in Council 0053: a persisted delivery state ledger now moves backlog items from ready/waiting/monitoring into `in_progress`, `done` or `accepted` without editing generated reports by hand.
