# AI Platform Product Council 0035

Date: 2026-06-17

## Topic

Model serving gateway envelope, fallback and metrics.

## Participants

- SA AI Platform: Serving contract and gateway owner
- SA AI Engineer: Runtime invocation and fallback owner
- PO/BA: Enterprise workflow acceptance owner

## Decision

Extend `courseflow_ai_platform.model_serving` from a model facade into an API
gateway boundary. The gateway accepts a request envelope with `request_id`,
`tenant_id`, `model_id` and payload, then returns a normalized response with
status, artifact lineage, latency, output, human-review flag, fallback metadata
and error metadata.

This keeps LMS, support, finance and operations model invocation on one product
surface before a hosted HTTP/gRPC adapter exists.

## Evidence

| Capability | Path |
|---|---|
| Gateway request/response classes | `platform/src/courseflow_ai_platform/model_serving.py` |
| In-memory serving counters | `ModelServingMetrics` |
| Gateway tests | `platform/tests/test_model_serving.py` |
| Capability registry | `platform/capabilities/registry.yaml` |

## Gateway Contract

| Field | Purpose |
|---|---|
| `request_id` | Idempotency/audit correlation |
| `tenant_id` | Tenant boundary for downstream checks |
| `model_id` | Dispatch key into the manifest-backed facade |
| `payload` | Model-specific payload governed by model IO contract |
| `fallback_output` | Optional request-level fallback when invocation fails |

Response status values:

- `ok`: model invocation succeeded.
- `fallback`: invocation failed but configured fallback output was returned.
- `error`: invocation failed and no fallback was available.

## Metrics

The gateway records request, success, fallback, error and human-review counts,
including per-model counters. This is intentionally in-memory for the platform
library slice; a hosted service can export the same counters to Prometheus or
OpenTelemetry later.

## Governance

- Error and fallback responses default to `requiresHumanReview=true`.
- Response envelopes preserve artifact manifest lineage for audit.
- Unknown model IDs return an error envelope instead of leaking stack traces.
- The model-specific payload remains governed by the existing model IO contract.

## Next Steps

1. Add HTTP/gRPC adapter around the gateway.
2. Persist serving metrics and emit model-age/fallback SLOs.
3. Keep audit store wiring from council 0037 as the adapter contract.
4. Add canary and shadow routing policy once promotion stages are wired to traffic.
