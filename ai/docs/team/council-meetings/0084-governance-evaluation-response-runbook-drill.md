# Council 0084: Governance Evaluation Response Runbook Drill

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Make repeated Governance Evaluation incident response executable and auditable |
| SA AI Engineer | Build deterministic P0/P1 response-drill scenarios from the incident exporter |
| PO/BA | Ensure release-impact communication has a product-facing runbook path |
| Governance Reviewer | Keep response evidence tenant-safe and free of raw principal or request data |
| Admin/Ops | Validate incident commander, acknowledgement, containment and closure steps |

## Decision

Add an executable Governance Evaluation incident response drill. The drill validates that
the structured runbook covers the repeated-failure incident routes added in Council 0083:

| Scenario | Severity | Expected action |
| --- | --- | --- |
| Release-gate drill mismatch | P0 | `escalate_governance_evaluation_release_gate_mismatch` |
| Unexpected Governance Evaluation runtime error | P0 | `triage_governance_evaluation_runtime_error` |
| Guardrail drill gap | P1 | `complete_governance_evaluation_guardrail_drills` |

## Runbook Steps

The structured runbook requires 8 response steps:

1. detect
2. acknowledge
3. assign
4. contain
5. remediate
6. verify
7. communicate
8. close

The drill passes only when every synthetic repeated-failure incident is open, tenant-safe,
routed to Admin/Ops, mapped to the expected action and covered by the required runbook steps.

## Surfaces

| Surface | Result |
| --- | --- |
| Structured runbook | `platform/operations/runbooks/governance-evaluation-incident-response-v1.yaml` |
| Human runbook | `runbooks/governance-evaluation-incident-response.md` |
| Drill report | `platform/operations/reports/governance-evaluation-incident-response-drill-v1.yaml` |
| CLI | `--write-governance-evaluation-incident-response-drill-report` |
| Admin/Ops dashboard | Shows `Gov Eval Runbook` status and response drill panel |
| Freshness manifest | Tracks response drill as the fifth dashboard source report |

## Outcome

The current response drill status is `passed`: 3 scenarios passed, 0 failed, 2 P0 scenarios,
1 P1 scenario, 8 runbook steps and 0 raw identifier markers. Baseline production state remains
quiet with 0 current Governance Evaluation incidents.

## Next Step

Record response-drill acceptance into the delivery state ledger so Admin/Ops can prove the
runbook drill has been accepted, not merely generated.
