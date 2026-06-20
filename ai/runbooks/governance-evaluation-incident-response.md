# Governance Evaluation Incident Response

This runbook covers repeated Governance Evaluation release-control failures exported by
`platform/governance/reports/governance-evaluation-incident-export-v1.yaml`.

## Scope

Use this runbook for these tenant-safe incident conditions:

- `governance_evaluation_release_gate_mismatch`
- `governance_evaluation_unexpected_error`
- `governance_evaluation_guardrail_gap`

Do not copy raw tenant IDs, principal IDs, request bodies, credential values or raw drill
payloads into incident notes. Use the exported incident ID and `platform:<hash>` ref.

## Steps

1. Detect the open incident in the Governance Evaluation incident export.
2. Acknowledge the incident in the Admin/Ops queue using the exported incident ID.
3. Assign Admin/Ops incident commander, Governance Reviewer and SA AI Platform owner.
4. Contain release impact by holding affected promotions until release-gate behavior is observable.
5. Remediate the drill, access policy, runtime or privacy-guardrail cause.
6. Verify by re-running Governance Evaluation ops and incident exports.
7. Communicate product release impact without raw tenant, service or credential identifiers.
8. Close or downgrade only after evidence refs show recovered release-control behavior.

## Evidence

- Structured runbook spec: `platform/operations/runbooks/governance-evaluation-incident-response-v1.yaml`
- Drill report: `platform/operations/reports/governance-evaluation-incident-response-drill-v1.yaml`
- Incident export: `platform/governance/reports/governance-evaluation-incident-export-v1.yaml`
- Ops report: `platform/governance/reports/governance-evaluation-service-v1.yaml`
