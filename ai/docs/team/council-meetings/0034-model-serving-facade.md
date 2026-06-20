# AI Platform Product Council 0034

Date: 2026-06-17

## Topic

Manifest-backed model serving facade.

## Participants

- SA AI Platform: Runtime architecture and platform API owner
- SA AI Engineer: Model runtime integration owner
- PO/BA: Enterprise product workflow owner

## Decision

Add `courseflow_ai_platform.model_serving` as the shared runtime facade for
source-algorithm baselines. The facade dispatches by `model_id`, reads artifact
manifests, loads the declared runtime entrypoint and normalizes model output
into a common response envelope.

This is the bridge between runtime libraries and a future hosted model-serving
service. It keeps the platform independent of LMS by serving LMS, support,
finance and enterprise operations baselines through the same path.

## Current Scope

| Capability | Evidence |
|---|---|
| Catalog serveable runtime baselines | `build_model_serving_catalog()` |
| Invoke model by ID | `serve_model(ai_root, model_id, payload)` |
| Supported runtime methods | `predict`, `recommend`, `assist` |
| Normalized response | model ID, artifact ID, manifest path, method, latency, output and HITL flag |
| Tests | `platform/tests/test_model_serving.py` |

## Served Baseline Examples

| Model | Product | Method |
|---|---|---|
| `operations-demand-forecast-baseline-v1` | Enterprise Operations | `predict` |
| `operations-routing-policy-simulator-v1` | Enterprise Operations | `recommend` |
| `finance-payment-fraud-baseline-v1` | Billing/Finance | `predict` |
| `support-agent-assist-baseline-v1` | Support Platform | `assist` |

## Governance

- Only manifest-backed source algorithms are directly served by this facade.
- Vector snapshots and trainer-only artifacts are excluded from online invoke.
- Existing model code still enforces tenant, HITL and policy constraints.
- The response envelope exposes `requiresHumanReview` for downstream workflow
  routing.

## Next Steps

1. Keep the gateway envelope from council 0035 as the API boundary.
2. Add an HTTP/gRPC adapter around the gateway.
3. Add request/response audit integration for high-impact models.
4. Add canary/shadow routing once promotion stages are ready for service traffic.
