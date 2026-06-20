# AI Platform Product Council 0040

Date: 2026-06-17

## Topic

Serving adapter authentication and authorization policy.

## Participants

- SA AI Platform: Route-scope and tenant boundary owner
- SA AI Engineer: Adapter enforcement and test owner
- Governance Reviewer: Least-privilege and wildcard-scope policy owner
- Admin/Ops: Metrics/cockpit access owner

## Decision

Add `courseflow_ai_platform.model_serving_auth` as the framework-neutral auth
policy for `ModelServingHostedAdapter`. The adapter remains dependency-light,
but when configured with `ServingAuthPolicy` it enforces principal presence,
route scopes, tenant isolation, model allowlists and wildcard-scope rejection
before invoking model runtime.

## Route Scopes

| Route | Required scope |
|---|---|
| `GET /v1/models` | `internal:ai-platform:model-serving:catalog` |
| `POST /v1/model-invocations` | `internal:ai-platform:model-serving:invoke` |
| `GET /v1/model-serving/metrics` | `internal:ai-platform:model-serving:ops` |
| `GET /v1/model-serving/health` | `internal:ai-platform:model-serving:ops` |
| `GET /v1/model-serving/cockpit` | `internal:ai-platform:model-serving:ops` |

## Evidence

| Capability | Path |
|---|---|
| Auth policy module | `platform/src/courseflow_ai_platform/model_serving_auth.py` |
| Hosted adapter enforcement | `platform/src/courseflow_ai_platform/model_serving_adapter.py` |
| Governance policy scopes | `platform/governance/policies/ai-governance-policy.yaml` |
| Auth tests | `platform/tests/test_model_serving_adapter.py` |

## Controls

- Missing principal returns `401` before model invocation.
- Missing route scope returns `403`.
- Wildcard scope is rejected when governance policy disallows wildcard scopes.
- Invoke requests require principal tenant access.
- Payload tenant must match the request tenant when present.
- Principal model allowlists can restrict which model IDs are invokeable.
- Rejected requests do not increment model serving metrics.

## Product Impact

| Product | Impact |
|---|---|
| AI Platform | Hosted serving boundary now has least-privilege controls |
| LMS CourseFlow | LMS model calls can be tenant-scoped without LMS-specific code |
| Support Platform | Support models can separate invoke and ops access |
| Billing/Finance | Sensitive models can use model allowlists and fail-closed audit mode |
| Enterprise Operations | Forecasting/routing models share the same auth policy |

## Next Steps

1. Bind `ServingPrincipal` to internal JWT claims in a real HTTP/gRPC ingress.
2. Use council 0042 model-serving access policy as the product/tenant/model grant map.
3. Use council 0041 security telemetry as the denial metrics contract.
