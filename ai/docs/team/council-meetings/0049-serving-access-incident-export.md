# Council 0049: Serving Access Incident Export

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Serving access governance now has a tenant-safe incident export. Admin/Ops can hand off drift, blocked apply, stale apply and pending apply watch conditions to incident response without exposing raw tenant IDs, principal IDs, request IDs or credential values.

The platform added:

- `ServingAccessIncident`
- `ServingAccessIncidentExport`
- report `platform/governance/reports/model-serving-access-incident-export-v1.yaml`
- CLI flag `--write-serving-access-incident-export-report`
- hashed `application_ref` values for incident handoff
- stale pending apply escalation after 2 days

## Current Incident State

| Scope | Value |
|---|---:|
| Incidents | 1 |
| Open | 0 |
| Watch | 1 |
| P0 | 0 |
| P1 | 0 |
| P2 | 1 |
| Stale pending apply | 0 |
| Tenant safe | true |

## Guardrails

- Policy drift becomes `open/P0` for Admin/Ops and Governance.
- Blocked apply ledger state becomes `open/P0` for Admin/Ops and Governance.
- Stale pending apply becomes `open/P1` for Admin/Ops after 2 days.
- Non-stale pending apply stays `watch/P2` until the controlled applier runs.
- Incident export suppresses raw tenant, principal, request and credential values.
- Incident export uses deterministic hashed application refs so incident routing remains stable without copying raw governance IDs.

## Next Step

Completed in Council 0050: add incident export rollup into the Admin/Ops owner view so open P0/P1 serving-access incidents appear beside due-soon delivery work.
