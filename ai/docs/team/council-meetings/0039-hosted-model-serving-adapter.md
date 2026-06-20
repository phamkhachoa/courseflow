# AI Platform Product Council 0039

Date: 2026-06-17

## Topic

Hosted model serving adapter.

## Participants

- SA AI Platform: Hosted serving boundary and API contract owner
- SA AI Engineer: Runtime invocation, audit persistence and metrics owner
- PO/BA: Enterprise product workflow and operability acceptance owner
- Admin/Ops: Health, cockpit and incident signal owner

## Decision

Add `courseflow_ai_platform.model_serving_adapter` as a framework-neutral
hosted adapter around `ModelServingGateway`. The adapter keeps platform core
dependency-light while exposing HTTP-style handlers that can be wrapped by
FastAPI, gRPC or another ingress later.

The adapter provides catalog, invocation, metrics, health and cockpit routes.
It supports external JSON envelopes with camelCase fields, persists sanitized
audit records through `JsonlModelAuditStore`, and publishes gateway metrics into
the operating cockpit snapshot.

## Route Contract

| Method | Route | Purpose |
|---|---|---|
| GET | `/v1/models` | List serveable manifest-backed models |
| POST | `/v1/model-invocations` | Invoke a model through the gateway envelope |
| GET | `/v1/model-serving/metrics` | Return request, fallback, error, HITL and audit counters |
| GET | `/v1/model-serving/health` | Return serving health status and HTTP-style status code |
| GET | `/v1/model-serving/cockpit` | Return operating cockpit snapshot with serving metrics connected |

## Evidence

| Capability | Path |
|---|---|
| Hosted adapter | `platform/src/courseflow_ai_platform/model_serving_adapter.py` |
| Gateway runtime | `platform/src/courseflow_ai_platform/model_serving.py` |
| Model audit store | `platform/src/courseflow_ai_platform/model_audit.py` |
| Cockpit integration | `platform/src/courseflow_ai_platform/operating_cockpit.py` |
| Adapter tests | `platform/tests/test_model_serving_adapter.py` |

## Governance

- Bad request envelopes return `400` without incrementing model metrics.
- Unknown models return gateway error envelopes and mark serving health degraded.
- JSONL audit persistence is optional but first-class for hosted deployments.
- Cockpit output receives the live `ModelServingMetricsSnapshot` from the adapter.

## Product Impact

| Product | Impact |
|---|---|
| AI Platform | First hosted serving boundary without coupling platform core to a web framework |
| LMS CourseFlow | LMS models can invoke through the same route contract as non-LMS models |
| Support Platform | Agent-assist and SLA risk can share gateway metrics and audit behavior |
| Billing/Finance | Fraud and document models can use fail-open/fail-closed audit policy |
| Enterprise Operations | Forecasting and routing models can be exposed through the same adapter |

## Next Steps

1. Wrap `ModelServingHostedAdapter` with an actual HTTP or gRPC ingress.
2. Add authN/authZ and tenant policy checks at the ingress boundary.
3. Persist serving metrics beyond process lifetime.
