# AI Platform Product Council 0037

Date: 2026-06-17

## Topic

Audit-bound model serving gateway.

## Participants

- SA AI Platform: Gateway contract and audit failure policy owner
- SA AI Engineer: Runtime invocation, audit store wiring and metrics owner
- PO/BA: Enterprise evidence and regulated workflow acceptance owner

## Decision

Extend `ModelServingGateway` so hosted adapters can pass a `ModelAuditStore`
directly into the gateway. Every invocation with an audit store now attempts to
append a sanitized model audit record built from the request and response.

The default policy is fail-open: model inference can return successfully even
when audit storage is temporarily unavailable, while audit failures are counted
in gateway metrics. Regulated workflows can configure `audit_failure_mode` as
`fail_closed`, causing an audit write failure to return a human-review error
envelope instead of the model output.

## Evidence

| Capability | Path |
|---|---|
| Gateway audit hook | `platform/src/courseflow_ai_platform/model_serving.py` |
| Model audit ledger | `platform/src/courseflow_ai_platform/model_audit.py` |
| Serving gateway tests | `platform/tests/test_model_serving.py` |
| Audit ledger tests | `platform/tests/test_model_audit.py` |
| Capability registry | `platform/capabilities/registry.yaml` |

## Runtime Behavior

| Mode | Behavior |
|---|---|
| No audit store | Gateway returns inference envelopes and records serving metrics only |
| Audit store + fail-open | Gateway appends audit records; storage errors increment audit-failure metrics while inference remains available |
| Audit store + fail-closed | Storage errors return `status=error`, `error_code=model_audit_failed` and `requiresHumanReview=true` |

## Metrics

`ModelServingMetricsSnapshot` now includes platform-level and per-model counts
for audit records and audit failures. This gives Admin/Ops an operational signal
before the hosted adapter exports the same metrics to Prometheus or
OpenTelemetry.

## Product Impact

| Product | Impact |
|---|---|
| AI Platform | Serving gateway now has a production-ready audit attachment point |
| LMS CourseFlow | Recommendation and learner-risk inference can keep sanitized audit evidence |
| Support Platform | SLA risk and agent-assist calls can choose fail-open or fail-closed audit behavior |
| Billing/Finance | Fraud/document intelligence can run with fail-closed audit policy if required |
| Enterprise Operations | Forecasting and routing predictions share the same audit and metrics path |

## Next Steps

1. Add an HTTP/gRPC adapter that configures `JsonlModelAuditStore` or a DB-backed store.
2. Surface audit failure counts in the AI Platform operating cockpit.
3. Add per-use-case audit policy defaults from model manifests or promotion stages.
