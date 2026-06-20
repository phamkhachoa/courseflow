# Council 0081: Governance Evaluation Alert SLA Routing

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Convert governance evaluation observability into delivery work |
| SA AI Engineer | Keep cockpit, backlog, SLA, owner views and dashboard generated from one action graph |
| PO/BA | Make release-gate alert drills visible as product execution work |
| Governance Reviewer | Ensure alert evidence excludes identities and secret payloads |
| Admin/Ops | Own the release-gate alert drill in the Admin/Ops queue |

## Decision

Route Governance Evaluation Service release-gate observability into delivery execution.
When `governance_evaluation_ops` is `release_gate_observable`, the operating cockpit now emits:

```text
governance_evaluation_ops:run_governance_evaluation_release_gate_alert_drill:governance-evaluation-service-v1
```

The action is owned by Admin/Ops, priority `p2`, status `ready`, and flows into:

| Surface | Result |
| --- | --- |
| Operating cockpit | action count includes the governance evaluation alert drill |
| Delivery backlog | `AIP-BLG-0021` tracks the drill with governance-review acceptance criteria |
| Delivery SLA | Admin/Ops gets an on-track p2 SLA item |
| Delivery owner views | Admin/Ops queue shows the release-gate alert drill beside provider alert and serving-access work |
| Admin/Ops dashboard | rendered owner queue includes `Run Governance Evaluation Release Gate Alert Drill` |

## Guardrails

- Alert drill evidence must remain tenant-safe.
- Direct identity values and secret values must not appear in report or dashboard payloads.
- Approved, review-required and blocked release decisions must route to expected owners.
- Missing or blocked Governance Evaluation Ops status creates governance remediation work instead of a ready drill.

## Evidence

| Artifact | Path |
| --- | --- |
| Cockpit action builder | `platform/src/courseflow_ai_platform/operating_cockpit.py` |
| Backlog phase and acceptance criteria | `platform/src/courseflow_ai_platform/delivery_backlog.py` |
| Operating cockpit report | `platform/operations/reports/operating-cockpit-v1.yaml` |
| Delivery backlog report | `platform/delivery/reports/delivery-backlog-v1.yaml` |
| Delivery SLA report | `platform/delivery/reports/delivery-sla-v1.yaml` |
| Delivery owner views | `platform/delivery/reports/delivery-owner-views-v1.yaml` |
| Dashboard artifact | `platform/operations/reports/admin-ops-dashboard-v1.html` |
| Tests | `platform/tests/test_operating_cockpit.py`, `platform/tests/test_delivery_backlog.py`, `platform/tests/test_delivery_sla.py`, `platform/tests/test_delivery_owner_views.py`, `platform/tests/test_admin_ops_dashboard.py`, `platform/tests/test_cli.py` |

## Outcome

AI Platform delivery now tracks 21 work items. Admin/Ops owns 5 dashboard items,
including the Governance Evaluation release-gate alert drill. The platform keeps
Governance Evaluation as a reusable enterprise release-control surface rather than
an LMS-specific approval feature.
Council 0082 records the same drill as an accepted delivery-state transition with
evidence refs, so the queue shows operational progress without editing generated reports.
