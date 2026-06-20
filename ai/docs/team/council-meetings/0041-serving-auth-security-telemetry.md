# AI Platform Product Council 0041

Date: 2026-06-17

## Topic

Serving adapter authorization denial telemetry.

## Participants

- SA AI Platform: Serving adapter security telemetry owner
- SA AI Engineer: Metrics shape and adapter integration owner
- Governance Reviewer: Privacy-safe rejection evidence owner
- Admin/Ops: Security signal consumer

## Decision

Extend the serving adapter auth boundary with privacy-safe security telemetry.
`ServingAuthTelemetry` records authorization denials by bounded reason, route
and status code. The telemetry is exposed from the hosted adapter metrics
response beside model-serving metrics.

The adapter does not store raw principal IDs, tenant IDs, model IDs, tokens or
request payload values in security telemetry. It records only bounded labels
such as `scope_forbidden`, `tenant_mismatch`, `wildcard_scope_forbidden` and
route templates like `POST /v1/model-invocations`.

## Evidence

| Capability | Path |
|---|---|
| Security telemetry classes | `platform/src/courseflow_ai_platform/model_serving_auth.py` |
| Metrics response integration | `platform/src/courseflow_ai_platform/model_serving_adapter.py` |
| Auth telemetry tests | `platform/tests/test_model_serving_adapter.py` |
| Governance policy | `platform/governance/policies/ai-governance-policy.yaml` |

## Metrics Shape

| Field | Meaning |
|---|---|
| `denialCount` | Total serving adapter authorization denials |
| `byReason` | Counts by bounded error code |
| `byRoute` | Counts by bounded route template |
| `byStatusCode` | Counts by HTTP-style status code |

## Controls

- Missing principal, invalid principal, missing scope, wildcard scope, tenant
  mismatch and model allowlist denial are all counted.
- Rejected requests do not increment model invocation metrics.
- Metrics remain safe for Admin/Ops and Security review because they contain no
  raw principal, tenant, token or payload values.

## Next Steps

1. Bind denial telemetry to Prometheus/OpenTelemetry in the real HTTP/gRPC ingress.
2. Add alert thresholds for repeated wildcard-scope or tenant-mismatch denials.
3. Add tenant-safe security incident export for Governance Reviewer review.
