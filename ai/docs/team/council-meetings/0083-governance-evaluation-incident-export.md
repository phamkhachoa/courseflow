# Council 0083: Governance Evaluation Incident Export

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Convert repeated Governance Evaluation alert drill failures into tenant-safe incidents |
| SA AI Engineer | Keep incident export deterministic, testable and reusable by owner views |
| PO/BA | Make repeated release-control failures visible as Admin/Ops work, not hidden platform noise |
| Governance Reviewer | Ensure incident payloads suppress tenant IDs, principal IDs and raw drill bodies |
| Admin/Ops | Receive P0/P1 incident handoffs with stable safe refs and action names |

## Decision

Add a standalone Governance Evaluation incident export:

```text
platform/governance/reports/governance-evaluation-incident-export-v1.yaml
```

The export reads:

- `governance-evaluation-service-v1` for the current ops status
- `governance-evaluation-alert-drill-ledger-v1` for prior drill observations
- `governance-evaluation-incident-policy-v1` for repeated-failure thresholds and routes

The default repeated-failure threshold is 2 consecutive failed observations. Baseline
status on 2026-06-17 is `release_gate_observable`, so the export contains 0 open
incidents while preserving the route for future repeated failures.

## Incident Routes

| Ops status | Condition | Severity | Owner | Action |
| --- | --- | --- | --- | --- |
| `blocked_by_release_gate_drill_mismatch` | `governance_evaluation_release_gate_mismatch` | P0 | Admin/Ops | `escalate_governance_evaluation_release_gate_mismatch` |
| `blocked_by_unexpected_governance_evaluation_error` | `governance_evaluation_unexpected_error` | P0 | Admin/Ops | `triage_governance_evaluation_runtime_error` |
| `attention_required_guardrail_drill_gap` | `governance_evaluation_guardrail_gap` | P1 | Admin/Ops | `complete_governance_evaluation_guardrail_drills` |

## Surfaces

| Surface | Result |
| --- | --- |
| CLI | `--write-governance-evaluation-incident-export-report` writes the tenant-safe report |
| Delivery owner views | Open P0/P1 Governance Evaluation incidents roll into `admin-ops` |
| Admin/Ops dashboard | Adds a Governance Evaluation incident panel and open incident metric |
| Freshness manifest | Tracks the incident export as a dashboard source report |
| Capability taxonomy | Replaces the exporter next action with a response-runbook drill |

## Guardrails

- Exported refs use `platform:<hash>` instead of raw tenant, principal or service IDs.
- Incident payloads omit principal IDs, tenant IDs, request bodies, credential values and raw drill payloads.
- A single non-observable status does not open an incident; it must meet the repeated-failure threshold.
- Baseline observable status keeps `incident_count=0`, `open_count=0` and `tenant_safe=true`.

## Evidence

| Artifact | Path |
| --- | --- |
| Exporter | `platform/src/courseflow_ai_platform/governance_evaluation_incidents.py` |
| Policy | `platform/governance/policies/governance-evaluation-incident-policy.yaml` |
| Ledger | `platform/governance/ledgers/governance-evaluation-alert-drill-ledger.yaml` |
| Report | `platform/governance/reports/governance-evaluation-incident-export-v1.yaml` |
| Dashboard | `platform/operations/reports/admin-ops-dashboard-v1.html` |
| Freshness manifest | `platform/operations/reports/admin-ops-dashboard-freshness-v1.yaml` |
| Tests | `platform/tests/test_governance_evaluation_incidents.py`, `platform/tests/test_delivery_owner_views.py`, `platform/tests/test_admin_ops_dashboard.py`, `platform/tests/test_cli.py` |

## Outcome

Repeated Governance Evaluation failures now have an incident path without exposing raw
tenant or service identifiers. Admin/Ops can see these incidents beside delivery work
and serving-access handoffs, while the healthy baseline remains quiet.
