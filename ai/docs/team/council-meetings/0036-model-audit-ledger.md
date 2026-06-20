# AI Platform Product Council 0036

Date: 2026-06-17

## Topic

Model prediction audit ledger.

## Participants

- SA AI Platform: Audit contract, retention and platform boundary owner
- SA AI Engineer: Model serving integration and storage adapter owner
- PO/BA: Enterprise compliance, export and deletion workflow owner

## Decision

Add `courseflow_ai_platform.model_audit` as the shared audit ledger for model
serving gateway calls. The ledger builds sanitized prediction evidence from
`ModelServingRequest` and `ModelServingGatewayResponse`, hashes sanitized
payload/output values, preserves artifact lineage and supports tenant export,
tenant deletion and retention purge.

This closes the first enterprise observability gap after manifest-backed model
serving: Classical ML, deep learning, document/CV, fraud, forecasting, RL and
LLM-backed baselines can now use one audit event shape when they move behind
the gateway.

## Evidence

| Capability | Path |
|---|---|
| Model audit event contract | `contracts/models/model-audit-event.v1.yaml` |
| Runtime model audit ledger | `platform/src/courseflow_ai_platform/model_audit.py` |
| Ledger and JSONL adapter tests | `platform/tests/test_model_audit.py` |
| Serving gateway source | `platform/src/courseflow_ai_platform/model_serving.py` |
| Capability registry | `platform/capabilities/registry.yaml` |

## Governance

- Audit payloads are generated from sanitized model payload and output values.
- Payload and output hashes support evidence matching without raw sensitive logs.
- Records include request ID, tenant ID, model ID, status and artifact manifest
  lineage for incident review and rollback analysis.
- JSONL storage rejects records that still contain unredacted sensitive values.
- Tenant export/delete and retention purge are part of the store interface.

## Product Impact

| Product | Impact |
|---|---|
| AI Platform | Adds reusable model prediction audit evidence for all served baselines |
| LMS CourseFlow | At-risk, recommendation and tutor-adjacent model calls can be audited without raw learner PII |
| Support Platform | Agent assist and SLA risk calls can support case review and deletion workflows |
| Billing/Finance | Fraud/document intelligence calls keep lineage and sanitized evidence |
| Enterprise Operations | Forecasting and routing predictions gain audit-ready evidence |

## Next Steps

1. Use council 0037 gateway wiring as the hosted adapter contract.
2. Export audit counts and retention purge metrics to the platform operating cockpit.
3. Add Admin/Ops UI for tenant-scoped model audit export and deletion.
